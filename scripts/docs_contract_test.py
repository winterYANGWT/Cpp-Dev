#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
OPTIONS_MODULE = ROOT_DIR / "cmake" / "project_nameOptions.cmake"
DOCS_MODULE = ROOT_DIR / "cmake" / "project_nameDocs.cmake"
DOXYFILE_TEMPLATE = ROOT_DIR / "docs" / "Doxyfile.in"
ROOT_LISTS = ROOT_DIR / "CMakeLists.txt"
PRESETS_FILE = ROOT_DIR / "CMakePresets.json"
CI_WORKFLOW = ROOT_DIR / ".github" / "workflows" / "ci.yml"
LINUX_TOOLS_SCRIPT = ROOT_DIR / "scripts" / "install_linux_tools.sh"
DOCS_TARGET = "project_name_docs"
# Doxygen before 1.13 does not report undocumented namespaces.
NAMESPACE_CHECK_VERSION = (1, 13)

# find_package() and add_custom_target() are not available in CMake script
# mode, so the probe defines stand-ins that record each call as one line of
# PROBE_OUTPUT. configure_file() runs for real and writes the Doxyfile.
PROBE_SCRIPT = r"""
function(record_call command)
  string(JOIN " " args ${ARGN})
  file(APPEND "${PROBE_OUTPUT}" "${command} ${args}\n")
endfunction()

function(find_package)
  record_call(find_package ${ARGN})
  set(DOXYGEN_VERSION "${PROBE_DOXYGEN_VERSION}" PARENT_SCOPE)
endfunction()

function(add_custom_target)
  record_call(add_custom_target ${ARGN})
endfunction()

file(WRITE "${PROBE_OUTPUT}" "")
set(PROJECT_NAME project_name)
set(PROJECT_VERSION 0.1.0)
set(PROJECT_IS_TOP_LEVEL ON)
include("${OPTIONS_MODULE}")
include("${DOCS_MODULE}")
project_name_add_docs_target()
"""


class ProbeResult:
    def __init__(
        self, returncode: int, calls: str, stderr: str, binary_dir: Path
    ) -> None:
        self.returncode = returncode
        self.calls = calls.splitlines()
        # CMake wraps messages at about 80 columns; join the lines again.
        self.stderr = " ".join(stderr.split())
        self.binary_dir = binary_dir
        self.doxyfile_path = binary_dir / "Doxyfile"
        self.doxyfile: dict[str, str] = {}
        if self.doxyfile_path.is_file():
            for line in self.doxyfile_path.read_text(encoding="utf-8").splitlines():
                name, separator, value = line.partition("=")
                if separator and not line.startswith("#"):
                    self.doxyfile[name.strip()] = value.strip().strip('"')


def doxygen_version() -> tuple[int, ...] | None:
    if shutil.which("doxygen") is None:
        return None
    result = subprocess.run(
        ["doxygen", "--version"], capture_output=True, text=True, check=False
    )
    match = re.match(r"(\d+)\.(\d+)", result.stdout)
    return tuple(int(part) for part in match.groups()) if match else None


def ci_job(workflow: str, job: str) -> str:
    match = re.search(rf"^  {job}:\n(.*?)(?=^  \S|\Z)", workflow, re.M | re.S)
    return match.group(1) if match else ""


@unittest.skipIf(shutil.which("cmake") is None, "cmake is not installed")
class DocsContractTest(unittest.TestCase):
    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.temp_dir = Path(temp_dir.name)
        self.probe_script = self.temp_dir / "probe.cmake"
        self.probe_script.write_text(PROBE_SCRIPT, encoding="utf-8")

    def probe(
        self,
        source_dir: Path = ROOT_DIR,
        doxygen_version: str = "1.15.0",
        warnings_as_errors: str = "ON",
    ) -> ProbeResult:
        output_file = self.temp_dir / "calls.txt"
        binary_dir = self.temp_dir / "build"
        shutil.rmtree(binary_dir, ignore_errors=True)
        binary_dir.mkdir()
        variables = {
            "PROBE_OUTPUT": output_file.as_posix(),
            "PROBE_DOXYGEN_VERSION": doxygen_version,
            "OPTIONS_MODULE": OPTIONS_MODULE.as_posix(),
            "DOCS_MODULE": DOCS_MODULE.as_posix(),
            "PROJECT_SOURCE_DIR": source_dir.as_posix(),
            "PROJECT_BINARY_DIR": binary_dir.as_posix(),
            "project_name_WARNINGS_AS_ERRORS": warnings_as_errors,
        }
        result = subprocess.run(
            [
                "cmake",
                *[f"-D{name}={value}" for name, value in variables.items()],
                "-P",
                str(self.probe_script),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        calls = output_file.read_text(encoding="utf-8") if output_file.exists() else ""
        return ProbeResult(result.returncode, calls, result.stderr, binary_dir)

    def run_doxygen(self, header: str) -> tuple[subprocess.CompletedProcess, Path]:
        source_dir = self.temp_dir / "source"
        (source_dir / "docs").mkdir(parents=True)
        shutil.copy(DOXYFILE_TEMPLATE, source_dir / "docs" / "Doxyfile.in")
        header_dir = source_dir / "include" / "project_name"
        header_dir.mkdir(parents=True)
        (header_dir / "api.h").write_text(header, encoding="utf-8")
        probe = self.probe(source_dir)
        self.assertEqual(probe.returncode, 0, probe.stderr)
        return self.run_doxyfile(probe), probe.binary_dir

    def run_doxyfile(self, probe: ProbeResult) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["doxygen", str(probe.doxyfile_path)],
            cwd=probe.binary_dir,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_docs_are_opt_in(self) -> None:
        self.assertRegex(
            OPTIONS_MODULE.read_text(encoding="utf-8"),
            r'option\(\$\{PROJECT_NAME\}_BUILD_DOCS "[^"]*" OFF\)',
        )
        # Doxygen is only looked for when the documentation is enabled.
        self.assertRegex(
            ROOT_LISTS.read_text(encoding="utf-8"),
            r"if\(\$\{PROJECT_NAME\}_BUILD_DOCS\)\s+project_name_add_docs_target\(\)\s+endif\(\)",
        )

    def test_docs_target_runs_doxygen_on_the_public_headers(self) -> None:
        result = self.probe()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("find_package Doxygen REQUIRED COMPONENTS doxygen", result.calls)
        targets = [call for call in result.calls if call.startswith("add_custom_target")]
        self.assertEqual(len(targets), 1)
        self.assertRegex(
            targets[0],
            rf"^add_custom_target {DOCS_TARGET} COMMAND Doxygen::doxygen "
            rf"{re.escape(result.doxyfile_path.as_posix())} ",
        )
        expected = {
            "INPUT": (ROOT_DIR / "include").as_posix(),
            "OUTPUT_DIRECTORY": (result.binary_dir / "doxygen").as_posix(),
            "RECURSIVE": "YES",
            # EXTRACT_ALL turns off the warnings for undocumented symbols.
            "EXTRACT_ALL": "NO",
            "WARN_IF_UNDOCUMENTED": "YES",
            "HIDE_UNDOC_NAMESPACES": "NO",
            "GENERATE_HTML": "YES",
            "GENERATE_LATEX": "NO",
        }
        for name, value in expected.items():
            with self.subTest(setting=name):
                self.assertEqual(result.doxyfile.get(name), value)
        self.assertIn("PROJECT_NAME_EXPORT=", result.doxyfile["PREDEFINED"].split())
        self.assertNotRegex(
            result.doxyfile_path.read_text(encoding="utf-8"), r"@[A-Za-z_]+@"
        )

    def test_doxygen_warnings_follow_warnings_as_errors(self) -> None:
        for warnings_as_errors, expected in (("ON", "FAIL_ON_WARNINGS"), ("OFF", "NO")):
            with self.subTest(warnings_as_errors=warnings_as_errors):
                result = self.probe(warnings_as_errors=warnings_as_errors)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.doxyfile["WARN_AS_ERROR"], expected)

    def test_old_doxygen_gets_a_warning(self) -> None:
        for version, warns in (("1.9.8", True), ("1.13.0", False), ("1.15.0", False)):
            with self.subTest(version=version):
                result = self.probe(doxygen_version=version)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    "does not report undocumented namespaces" in result.stderr, warns
                )

    def test_docs_preset_builds_only_the_docs_target(self) -> None:
        presets = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
        configure = next(
            preset for preset in presets["configurePresets"] if preset["name"] == "docs"
        )
        build = next(
            preset for preset in presets["buildPresets"] if preset["name"] == "docs"
        )

        self.assertEqual(
            configure["cacheVariables"],
            {
                "project_name_BUILD_DOCS": "ON",
                "project_name_BUILD_TESTS": "OFF",
                "project_name_INSTALL": "OFF",
                "project_name_WARNINGS_AS_ERRORS": "ON",
            },
        )
        self.assertEqual(configure["binaryDir"], "${sourceDir}/build/docs")
        self.assertEqual(build["configurePreset"], "docs")
        self.assertEqual(build["targets"], [DOCS_TARGET])

    def test_ci_generates_docs_with_doxygen_1_13_or_newer(self) -> None:
        job = ci_job(CI_WORKFLOW.read_text(encoding="utf-8"), "docs")
        match = re.search(
            r"^doxygen_version=(\d+)\.(\d+)\.\d+$",
            LINUX_TOOLS_SCRIPT.read_text(encoding="utf-8"),
            re.M,
        )

        # Distribution packages are often older, such as 1.9.8 in Debian 13,
        # so CI installs the release pinned in the script.
        self.assertIn("install_linux_tools.sh --doxygen", job)
        self.assertIsNotNone(match)
        self.assertGreaterEqual(
            tuple(int(part) for part in match.groups()), NAMESPACE_CHECK_VERSION
        )
        self.assertIn("python3 scripts/docs_contract_test.py", job)
        self.assertIn("cmake --preset docs", job)
        self.assertIn("cmake --build --preset docs", job)

    @unittest.skipIf(doxygen_version() is None, "doxygen is not installed")
    def test_doxygen_accepts_the_public_headers(self) -> None:
        probe = self.probe()
        result = self.run_doxyfile(probe)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        html_dir = probe.binary_dir / "doxygen" / "html"
        self.assertTrue((html_dir / "index.html").is_file())
        # Without documented scopes, Doxygen succeeds but writes no API pages.
        api_pages = [
            page
            for pattern in ("namespace*.html", "class*.html", "struct*.html")
            for page in html_dir.glob(pattern)
        ]
        self.assertTrue(api_pages, "Doxygen generated no namespace or class pages.")

    @unittest.skipIf(doxygen_version() is None, "doxygen is not installed")
    def test_doxygen_rejects_undocumented_public_api(self) -> None:
        result, _ = self.run_doxygen(
            "/** @brief Documented namespace. */\n"
            "namespace project_name {\n"
            "int Undocumented();\n"
            "}  // namespace project_name\n"
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Undocumented() (function)", result.stdout + result.stderr)

    @unittest.skipIf(
        (doxygen_version() or (0,)) < NAMESPACE_CHECK_VERSION,
        "doxygen 1.13 or newer is not installed",
    )
    def test_doxygen_rejects_undocumented_namespace(self) -> None:
        result, _ = self.run_doxygen(
            "namespace project_name {\n"
            "/** @brief Documented function. */\n"
            "int Documented();\n"
            "}  // namespace project_name\n"
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "Namespace project_name is not documented", result.stdout + result.stderr
        )


if __name__ == "__main__":
    unittest.main()
