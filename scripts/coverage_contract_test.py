#!/usr/bin/env python3

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"
COVERAGE_SCRIPT = SCRIPTS_DIR / "coverage.py"
OPTIONS_MODULE = ROOT_DIR / "cmake" / "project_nameOptions.cmake"
PRESETS_FILE = ROOT_DIR / "CMakePresets.json"
CI_WORKFLOW = ROOT_DIR / ".github" / "workflows" / "ci.yml"
QUALITY_SCRIPT = SCRIPTS_DIR / "quality.py"
INSTALL_SCRIPT = SCRIPTS_DIR / "install_linux_tools.sh"
TOOL_VERSIONS_DOC = ROOT_DIR / "docs" / "tool-versions.md"
README = ROOT_DIR / "README.md"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

SPEC = importlib.util.spec_from_file_location("coverage_script", COVERAGE_SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load {COVERAGE_SCRIPT}")
coverage_script = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(coverage_script)


def ci_job(workflow: str, name: str) -> str:
    match = re.search(
        rf"^  {re.escape(name)}:\n(.*?)(?=^  \S|\Z)",
        workflow,
        re.M | re.S,
    )
    if match is None:
        raise AssertionError(f"No {name} job found in the CI workflow.")
    return match.group(1)


class CoverageContractTest(unittest.TestCase):
    def make_temp_dir(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def make_executable(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        path.chmod(0o755)
        return path

    def test_option_defaults_to_off(self) -> None:
        text = OPTIONS_MODULE.read_text(encoding="utf-8")

        self.assertRegex(
            text,
            r'option\(\$\{PROJECT_NAME\}_ENABLE_COVERAGE\s+"[^"]*"\s+OFF\)',
            "The ENABLE_COVERAGE option must be declared with the default OFF.",
        )

    def test_coverage_preset_enables_coverage(self) -> None:
        presets = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
        configure_presets = {
            preset["name"]: preset for preset in presets["configurePresets"]
        }

        self.assertIn(
            "coverage",
            configure_presets,
            "CMakePresets.json must define a coverage configure preset.",
        )
        coverage = configure_presets["coverage"]
        self.assertEqual(coverage.get("displayName"), "Coverage")
        self.assertEqual(
            coverage.get("description"),
            "Configure a Debug build with gcov coverage instrumentation.",
        )
        self.assertEqual(coverage.get("binaryDir"), "${sourceDir}/build/coverage")
        self.assertEqual(
            coverage.get("cacheVariables"),
            {
                "BUILD_SHARED_LIBS": "OFF",
                "CMAKE_BUILD_TYPE": "Debug",
                "CMAKE_EXPORT_COMPILE_COMMANDS": "ON",
                "project_name_ENABLE_COVERAGE": "ON",
                "project_name_WARNINGS_AS_ERRORS": "ON",
            },
        )

        binary_dir = Path(
            str(coverage["binaryDir"]).replace("${sourceDir}", str(ROOT_DIR))
        )
        self.assertEqual(
            binary_dir,
            coverage_script.BUILD_DIR,
            "The coverage preset binaryDir and coverage.py BUILD_DIR must match.",
        )

        for kind in ("buildPresets", "testPresets"):
            with self.subTest(kind=kind):
                named = {preset["name"]: preset for preset in presets[kind]}
                self.assertIn(
                    "coverage",
                    named,
                    f"CMakePresets.json must define a coverage {kind} preset.",
                )
                preset = named["coverage"]
                self.assertEqual(preset.get("configurePreset"), "coverage")
                self.assertEqual(preset.get("configuration"), "Debug")
                if kind == "testPresets":
                    self.assertTrue(
                        preset.get("output", {}).get("outputOnFailure"),
                        "The coverage test preset must set outputOnFailure.",
                    )

        for name, preset in configure_presets.items():
            if name == "coverage":
                continue
            cache_variables = preset.get("cacheVariables", {})
            self.assertNotEqual(
                cache_variables.get("project_name_ENABLE_COVERAGE"),
                "ON",
                f"The {name} configure preset must not enable coverage.",
            )

    def test_gcov_command_prefers_versioned_gnu_gcov(self) -> None:
        directory = self.make_temp_dir()
        compiler = self.make_executable(directory / "g++")
        versioned = self.make_executable(directory / "gcov-14")
        self.make_executable(directory / "gcov")
        empty_path = directory / "empty"
        empty_path.mkdir()

        command = coverage_script.gcov_command(
            "GNU", str(compiler), "14.2.0", search_path=str(empty_path)
        )

        self.assertEqual(command, [str(versioned)])

    def test_gcov_command_falls_back_to_unversioned_gnu_gcov(self) -> None:
        directory = self.make_temp_dir()
        compiler = self.make_executable(directory / "g++")
        gcov = self.make_executable(directory / "gcov")
        empty_path = directory / "empty"
        empty_path.mkdir()

        command = coverage_script.gcov_command(
            "GNU", str(compiler), "14.2.0", search_path=str(empty_path)
        )

        self.assertEqual(command, [str(gcov)])

    def test_gcov_command_resolves_clang_symlink_for_llvm_cov(self) -> None:
        directory = self.make_temp_dir()
        real_dir = directory / "llvm" / "bin"
        llvm_cov = self.make_executable(real_dir / "llvm-cov")
        real_clang = self.make_executable(real_dir / "clang++")
        link_dir = directory / "usr" / "bin"
        link_dir.mkdir(parents=True)
        link = link_dir / "clang++"
        link.symlink_to(real_clang)
        empty_path = directory / "empty"
        empty_path.mkdir()

        for compiler_id in ("Clang", "AppleClang"):
            with self.subTest(compiler_id=compiler_id):
                command = coverage_script.gcov_command(
                    compiler_id,
                    str(link),
                    "21.1.8",
                    search_path=str(empty_path),
                )

                self.assertEqual(command, [str(llvm_cov), "gcov"])

    def test_gcov_command_finds_versioned_llvm_cov_on_path(self) -> None:
        directory = self.make_temp_dir()
        compiler = self.make_executable(directory / "compiler" / "clang++")
        tools = directory / "tools"
        versioned = self.make_executable(tools / "llvm-cov-21")

        for compiler_id in ("Clang", "AppleClang"):
            with self.subTest(compiler_id=compiler_id):
                command = coverage_script.gcov_command(
                    compiler_id,
                    str(compiler),
                    "21.1.8",
                    search_path=str(tools),
                )

                self.assertEqual(command, [str(versioned), "gcov"])

    def test_gcov_command_reports_missing_tool(self) -> None:
        directory = self.make_temp_dir()
        compiler = self.make_executable(directory / "g++")
        empty_path = directory / "empty"
        empty_path.mkdir()

        with self.assertRaises(coverage_script.CoverageError) as context:
            coverage_script.gcov_command(
                "GNU", str(compiler), "14.2.0", search_path=str(empty_path)
            )

        self.assertIn("--gcov-executable", str(context.exception))

    def test_gcov_command_rejects_other_compilers(self) -> None:
        cases = (
            ("MSVC", "cl"),
            ("IntelLLVM", "icpx"),
        )
        for compiler_id, compiler_name in cases:
            with self.subTest(compiler_id=compiler_id):
                with self.assertRaises(coverage_script.CoverageError) as context:
                    coverage_script.gcov_command(
                        compiler_id,
                        compiler_name,
                        "19.0.0",
                        search_path="",
                    )

                self.assertIn("GCC and Clang", str(context.exception))

    def test_gcovr_command_uses_project_filters_and_no_threshold(self) -> None:
        gcov_executable = "/usr/lib/llvm-21/bin/llvm-cov gcov"
        command = coverage_script.gcovr_command(gcov_executable)

        self.assertEqual(command[0], "gcovr")
        self.assertEqual(command[command.index("--root") + 1], str(ROOT_DIR))
        filters = [
            command[index + 1]
            for index, argument in enumerate(command)
            if argument == "--filter"
        ]
        self.assertEqual(filters, ["src/", "include/"])
        self.assertEqual(
            command[command.index("--gcov-executable") + 1],
            gcov_executable,
        )
        self.assertEqual(command[-1], str(coverage_script.BUILD_DIR))
        for option, filename in (
            ("--txt", "coverage.txt"),
            ("--html-details", "coverage.html"),
        ):
            report_path = Path(command[command.index(option) + 1])
            self.assertEqual(report_path.parent, coverage_script.REPORT_DIR)
            self.assertEqual(report_path.name, filename)
        self.assertFalse(
            [argument for argument in command if argument.startswith("--fail-under")],
            "The gcovr command must not impose a coverage threshold.",
        )

    def test_coverage_runs_configure_build_test_then_gcovr(self) -> None:
        directory = self.make_temp_dir()
        build_dir = directory / "build" / "coverage"
        report_dir = directory / "build" / "coverage-report"
        reply_dir = build_dir / ".cmake" / "api" / "v1" / "reply"
        reply_dir.mkdir(parents=True)
        (reply_dir / "index-0001.json").write_text(
            json.dumps(
                {
                    "objects": [
                        {"kind": "toolchains", "jsonFile": "toolchains-1.json"}
                    ]
                }
            ),
            encoding="utf-8",
        )
        (reply_dir / "toolchains-1.json").write_text(
            json.dumps(
                {
                    "toolchains": [
                        {
                            "language": "CXX",
                            "compiler": {
                                "id": "GNU",
                                "path": "/usr/bin/g++",
                                "version": "14.2.0",
                            },
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        commands: list[list[str]] = []
        gcda_path = build_dir / "tests" / "unit.gcda"
        gcda_created_at_build: list[bool] = []
        gcda_present_at_ctest: list[bool] = []
        query_registered_at_configure: list[bool] = []
        query_file = (
            build_dir
            / ".cmake"
            / "api"
            / "v1"
            / "query"
            / "toolchains-v1"
        )

        def fake_run(command: list[str]) -> None:
            commands.append(list(command))
            if command[:4] == ["cmake", "--build", "--preset", "coverage"]:
                gcda_path.parent.mkdir(parents=True, exist_ok=True)
                gcda_path.write_text("", encoding="utf-8")
                gcda_created_at_build.append(gcda_path.is_file())
            elif command[:3] == ["cmake", "--preset", "coverage"]:
                query_registered_at_configure.append(query_file.is_file())
            elif command[:3] == ["ctest", "--preset", "coverage"]:
                gcda_present_at_ctest.append(gcda_path.exists())

        with contextlib.ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(coverage_script, "BUILD_DIR", build_dir)
            )
            stack.enter_context(
                mock.patch.object(coverage_script, "REPORT_DIR", report_dir)
            )
            stack.enter_context(
                mock.patch.object(
                    coverage_script.quality, "run", side_effect=fake_run
                )
            )
            stack.enter_context(
                mock.patch.object(
                    coverage_script.quality,
                    "cmake_configure_args",
                    return_value=[],
                )
            )
            stack.enter_context(
                mock.patch.object(
                    coverage_script,
                    "gcov_command",
                    return_value=["/fake/gcov-14"],
                )
            )
            stack.enter_context(
                mock.patch.object(
                    coverage_script.shutil, "which", return_value="/fake/gcovr"
                )
            )
            stack.enter_context(
                mock.patch.object(sys, "argv", ["coverage.py"])
            )
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = coverage_script.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            [command[0] for command in commands],
            ["cmake", "cmake", "ctest", "gcovr"],
            "coverage.py must configure, build, test, and then run gcovr.",
        )
        self.assertEqual(commands[0][:3], ["cmake", "--preset", "coverage"])
        self.assertEqual(
            commands[1][:4], ["cmake", "--build", "--preset", "coverage"]
        )
        self.assertEqual(commands[2][:3], ["ctest", "--preset", "coverage"])
        self.assertEqual(
            commands[3][commands[3].index("--gcov-executable") + 1],
            "/fake/gcov-14",
        )
        self.assertEqual(query_registered_at_configure, [True])
        self.assertEqual(gcda_created_at_build, [True])
        self.assertEqual(
            gcda_present_at_ctest,
            [False],
            "The .gcda files from the build must be removed before ctest.",
        )
        self.assertTrue(report_dir.is_dir())

    def test_missing_tool_reports_one_error_line(self) -> None:
        coverage_build_dir = ROOT_DIR / "build" / "coverage"
        build_dir_existed = coverage_build_dir.exists()
        empty_path = self.make_temp_dir()
        env = os.environ.copy()
        # An empty PATH directory avoids the cmake/ source directory in the
        # repository root, which a PATH="" entry would search as the cwd.
        env["PATH"] = str(empty_path)

        result = subprocess.run(
            [sys.executable, str(COVERAGE_SCRIPT)],
            cwd=str(ROOT_DIR),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if not build_dir_existed:
            shutil.rmtree(coverage_build_dir, ignore_errors=True)

        self.assertEqual(result.returncode, 1, result.stderr)
        stderr_lines = result.stderr.splitlines()
        self.assertEqual(
            len(stderr_lines),
            1,
            f"Expected one error line, got: {result.stderr!r}",
        )
        self.assertIn("not found", stderr_lines[0])
        # gcovr is checked first, so that a missing gcovr fails before the build.
        self.assertIn("gcovr", stderr_lines[0])
        self.assertNotIn("Traceback", result.stderr)

    def test_quality_gate_does_not_run_coverage(self) -> None:
        text = QUALITY_SCRIPT.read_text(encoding="utf-8")

        for reference in ("coverage.py", "--preset coverage", '"coverage"'):
            with self.subTest(reference=reference):
                self.assertNotIn(
                    reference,
                    text,
                    "scripts/quality.py must not invoke the coverage preset.",
                )

    def test_ci_coverage_job_uploads_report(self) -> None:
        workflow = CI_WORKFLOW.read_text(encoding="utf-8")
        job = ci_job(workflow, "coverage")

        self.assertIn("install_linux_tools.sh --gcovr", job)
        self.assertIn("python3 scripts/coverage.py", job)
        self.assertIn("actions/upload-artifact", job)
        self.assertIn("build/coverage-report/", job)
        self.assertIn("if-no-files-found: error", job)
        self.assertNotIn("--fail-under", workflow)
        self.assertNotIn("codecov", workflow.lower())

    def test_gcovr_version_matches_documentation(self) -> None:
        install_text = INSTALL_SCRIPT.read_text(encoding="utf-8")
        match = re.search(r"^gcovr_version=(\d+\.\d+)$", install_text, re.M)
        self.assertIsNotNone(
            match, "install_linux_tools.sh must pin gcovr_version=X.Y."
        )
        version = match.group(1)

        self.assertIn('"gcovr==$gcovr_version.*"', install_text)
        self.assertRegex(
            TOOL_VERSIONS_DOC.read_text(encoding="utf-8"),
            rf"(?m)^\| gcovr \| {re.escape(version)} \|",
            "docs/tool-versions.md must list the same gcovr version.",
        )

    def test_readme_documents_coverage_script(self) -> None:
        self.assertIn(
            "python3 scripts/coverage.py",
            README.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
