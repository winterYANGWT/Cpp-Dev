#!/usr/bin/env python3

from __future__ import annotations

import contextlib
import io
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import quality
import tool_versions


ROOT_DIR = Path(__file__).resolve().parents[1]
REQUIREMENTS_FILE = ROOT_DIR / "scripts" / "tool-requirements.txt"
LINUX_TOOLS_SCRIPT = ROOT_DIR / "scripts" / "install_linux_tools.sh"
VERSIONS_DOC = ROOT_DIR / "docs" / "tool-versions.md"
README = ROOT_DIR / "README.md"
CI_WORKFLOW = ROOT_DIR / ".github" / "workflows" / "ci.yml"
DOC_TOOL_NAMES = {"clang-format": "clang-format", "clang-tidy": "clang-tidy", "cmake": "CMake"}
UNPINNED_INSTALL_RE = re.compile(
    r"(apt-get install|brew install)[^\n]*\b(clang-format|clang-tidy|cmake|llvm|ninja)\b"
)
CHOCO_LLVM_RE = re.compile(r"choco \w+ llvm\b[^\n]*")

# `--version` output of the tool builds that the script has to understand.
VERSION_OUTPUTS = {
    "clang-format version 21.1.8": "21.1.8",
    "Ubuntu clang-format version 21.1.8 (1)": "21.1.8",
    "Homebrew clang-format version 21.1.8": "21.1.8",
    "LLVM (http://llvm.org/):\n  LLVM version 21.1.6\n  Optimized build.": "21.1.6",
    "Ubuntu LLVM version 21.1.8\n  Optimized build.": "21.1.8",
    "clang version 21.1.8\nTarget: x86_64-pc-windows-msvc": "21.1.8",
    "cmake version 4.2.3\n\nCMake suite maintained and supported by Kitware": "4.2.3",
}


def ci_jobs(workflow: str) -> dict[str, str]:
    jobs_section = workflow.split("\njobs:\n", 1)[1]
    parts = re.split(r"^  ([A-Za-z0-9_-]+):\n", jobs_section, flags=re.M)
    return dict(zip(parts[1::2], parts[2::2]))


def container_image(job: str) -> str | None:
    match = re.search(r"^    container:(?:\s*image:)?\s*(\S+)$", job, re.M)
    return match.group(1) if match else None


class ToolVersionsContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.recommended = tool_versions.recommended_versions()
        self.workflow = CI_WORKFLOW.read_text(encoding="utf-8")
        self.jobs = ci_jobs(self.workflow)

    def test_requirements_pin_only_major_minor(self) -> None:
        self.assertEqual(set(self.recommended), {"clang-format", "clang-tidy", "cmake"})
        # clang-format and clang-tidy come from the same LLVM release.
        self.assertEqual(self.recommended["clang-format"], self.recommended["clang-tidy"])
        for line in REQUIREMENTS_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                with self.subTest(requirement=line):
                    self.assertRegex(line, r"^[A-Za-z0-9_.-]+(==\d+\.\d+\.\*)?$")

    def test_doc_records_the_recommendations_as_recommendations(self) -> None:
        doc = VERSIONS_DOC.read_text(encoding="utf-8")

        self.assertIn("recommendations, not requirements", doc)
        for tool, (major, minor) in self.recommended.items():
            with self.subTest(tool=tool):
                self.assertRegex(
                    doc,
                    rf"\n\| {re.escape(DOC_TOOL_NAMES[tool])} \| {major}\.{minor} \|",
                )
        doxygen = re.search(
            r"^doxygen_version=(\d+\.\d+)\.\d+$",
            LINUX_TOOLS_SCRIPT.read_text(encoding="utf-8"),
            re.M,
        )
        self.assertIsNotNone(doxygen)
        self.assertRegex(doc, rf"\n\| Doxygen \| {re.escape(doxygen.group(1))} \|")
        self.assertIn("(docs/tool-versions.md)", README.read_text(encoding="utf-8"))

    def test_every_ci_job_installs_and_verifies_the_recommended_versions(self) -> None:
        self.assertTrue(self.jobs)
        for name, job in self.jobs.items():
            with self.subTest(job=name):
                self.assertTrue(
                    "install_linux_tools.sh" in job
                    or "-r scripts/tool-requirements.txt" in job
                )
                self.assertIn("python scripts/tool_versions.py --strict", job)

    def test_ci_installs_no_unpinned_tools(self) -> None:
        self.assertIsNone(UNPINNED_INSTALL_RE.search(self.workflow))
        self.assertNotIn("-latest", self.workflow)
        major, minor = self.recommended["clang-format"]
        choco_lines = CHOCO_LLVM_RE.findall(self.workflow)
        self.assertTrue(choco_lines)
        for line in choco_lines:
            with self.subTest(line=line):
                self.assertRegex(line, rf"--version={major}\.{minor}\.\d+\b")

    def test_clang_cl_rows_check_the_clang_cl_version(self) -> None:
        quality = self.jobs["quality"]

        self.assertIn("matrix.compiler == 'clang-cl' && '--tool clang-cl'", quality)
        self.assertIn("if: matrix.compiler == 'clang-cl'", quality)

    def test_linux_jobs_share_one_container_image(self) -> None:
        linux_jobs = {
            name: job
            for name, job in self.jobs.items()
            if re.search(r"^    runs-on: ubuntu-", job, re.M)
        }
        images = {name: container_image(job) for name, job in linux_jobs.items()}

        self.assertGreaterEqual(len(linux_jobs), 5)
        self.assertEqual(len(set(images.values())), 1, images)
        image = next(iter(images.values()))
        self.assertIsNotNone(image)
        self.assertIn(f"`{image}`", VERSIONS_DOC.read_text(encoding="utf-8"))

    def test_linux_tools_script_installs_the_requirements(self) -> None:
        script = LINUX_TOOLS_SCRIPT.read_text(encoding="utf-8")

        self.assertIn('-r "$script_dir/tool-requirements.txt"', script)
        self.assertRegex(script, r"\ndoxygen_sha256=[0-9a-f]{64}\n")
        self.assertIn("sha256sum -c -", script)

    def test_version_parsing(self) -> None:
        for output, version in VERSION_OUTPUTS.items():
            with self.subTest(output=output.splitlines()[0]):
                self.assertEqual(tool_versions.parse_version(output), version)
        self.assertIsNone(tool_versions.parse_version("no version here"))

    def recommended_installed(self) -> dict[str, str | None]:
        return {
            tool: f"{major}.{minor}.7" for tool, (major, minor) in self.recommended.items()
        }

    def check(
        self, installed: dict[str, str | None], strict: bool, *tools: str
    ) -> tuple[int, str]:
        def fake_installed_version(tool: str) -> tuple[str | None, str | None]:
            if tool not in installed:
                return None, None
            return f"/fake/bin/{tool}", installed[tool]

        output = io.StringIO()
        with mock.patch.object(tool_versions, "installed_version", fake_installed_version):
            with contextlib.redirect_stdout(output):
                returncode = tool_versions.check_tools(list(tools), strict)
        return returncode, output.getvalue()

    def test_matching_versions_pass(self) -> None:
        for strict in (False, True):
            with self.subTest(strict=strict):
                returncode, output = self.check(self.recommended_installed(), strict)

                self.assertEqual(returncode, 0)
                self.assertNotIn("Warning", output)
                self.assertNotIn("Error", output)

    def test_other_versions_only_warn_unless_strict(self) -> None:
        installed = self.recommended_installed()
        installed["clang-tidy"] = "99.0.1"

        returncode, output = self.check(installed, strict=False)
        self.assertEqual(returncode, 0)
        self.assertIn("Warning: clang-tidy 99.0.1", output)

        returncode, output = self.check(installed, strict=True)
        self.assertEqual(returncode, 1)
        self.assertIn("Error: clang-tidy 99.0.1", output)

    def test_unreadable_versions_are_problems(self) -> None:
        installed = self.recommended_installed()
        installed["cmake"] = None

        returncode, output = self.check(installed, strict=True)
        self.assertEqual(returncode, 1)
        self.assertIn("Could not read the version of cmake", output)

    def test_missing_tools_are_reported_without_a_traceback(self) -> None:
        installed = self.recommended_installed()
        del installed["cmake"]

        for strict, returncode in ((False, 0), (True, 1)):
            with self.subTest(strict=strict):
                result, output = self.check(installed, strict)

                self.assertEqual(result, returncode)
                self.assertIn("cmake is not installed or not on PATH.", output)

    def test_clang_cl_is_expected_to_match_clang_format(self) -> None:
        installed = self.recommended_installed()
        installed["clang-cl"] = "99.0.1"

        returncode, output = self.check(installed, True, "clang-cl")
        self.assertEqual(returncode, 1)
        self.assertIn("clang-cl 99.0.1", output)

        installed["clang-cl"] = installed["clang-format"]
        self.assertEqual(self.check(installed, True, "clang-cl")[0], 0)
        with self.assertRaises(SystemExit):
            self.check(installed, True, "gcc")


class QualityMissingToolContractTest(unittest.TestCase):
    def test_missing_format_tool_reports_one_line_without_a_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as empty_path:
            env = os.environ.copy()
            env["PATH"] = empty_path
            result = subprocess.run(
                [sys.executable, "scripts/quality.py", "format", "--check"],
                cwd=ROOT_DIR,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("clang-format was not found on PATH", result.stderr)
        self.assertIn("docs/tool-versions.md", result.stderr)
        self.assertNotIn("Traceback", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_clang_tidy_missing_tool_is_converted(self) -> None:
        with mock.patch.object(quality, "macos_sdkroot", lambda: None):
            with mock.patch.object(
                quality.subprocess,
                "run",
                side_effect=FileNotFoundError(2, "No such file or directory", "clang-tidy"),
            ):
                with self.assertRaises(quality.ToolNotFoundError) as context:
                    quality.run_clang_tidy(["clang-tidy", "--quiet"])

        self.assertEqual(context.exception.tool, "clang-tidy")

    def test_main_reports_tool_not_found_and_returns_one(self) -> None:
        args = mock.Mock()
        args.func.side_effect = quality.ToolNotFoundError("clang-format")
        stderr = io.StringIO()

        with mock.patch.object(quality, "parse_args", return_value=args):
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(quality.main(), 1)

        self.assertIn(
            "error: clang-format was not found on PATH. "
            "Install the recommended tools (see docs/tool-versions.md)",
            stderr.getvalue(),
        )
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_main_does_not_misreport_other_missing_files(self) -> None:
        args = mock.Mock()
        args.func.side_effect = FileNotFoundError(2, "No such file or directory")
        stderr = io.StringIO()

        with mock.patch.object(quality, "parse_args", return_value=args):
            with contextlib.redirect_stderr(stderr):
                with self.assertRaises(FileNotFoundError):
                    quality.main()

        self.assertNotIn("was not found on PATH", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
