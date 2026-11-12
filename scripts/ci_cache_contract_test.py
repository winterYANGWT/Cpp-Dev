#!/usr/bin/env python3

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
CI_WORKFLOW = ROOT_DIR / ".github" / "workflows" / "ci.yml"
CACHE_ACTION = "actions/cache@"
STEP_RE = re.compile(r"^      - name: (.+)$", re.M)


def ci_jobs(workflow: str) -> dict[str, str]:
    jobs_section = workflow.split("\njobs:\n", 1)[1]
    parts = re.split(r"^  ([A-Za-z0-9_-]+):\n", jobs_section, flags=re.M)
    return dict(zip(parts[1::2], parts[2::2]))


def job_steps(job: str) -> list[tuple[str, str]]:
    matches = list(STEP_RE.finditer(job))
    steps: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(job)
        steps.append((match.group(1).strip(), job[match.start() : end]))
    return steps


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def step_property(step: str, name: str) -> str:
    match = re.search(rf"^        {re.escape(name)}:[ \t]*(.+)$", step, re.M)
    return unquote(match.group(1).strip()) if match else ""


def step_field(step: str, name: str) -> str:
    match = re.search(rf"^          {re.escape(name)}:[ \t]*(.+)$", step, re.M)
    return unquote(match.group(1).strip()) if match else ""


class CiCacheContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = CI_WORKFLOW.read_text(encoding="utf-8")
        self.jobs = ci_jobs(self.workflow)
        self.quality_steps = job_steps(self.jobs["quality"])
        self.steps = dict(self.quality_steps)
        # All cache actions in the quality job; the tests below require two.
        self.caches = [
            block
            for _, block in self.quality_steps
            if "actions/cache@" in block
        ]

    def cache_with(self, marker: str) -> str:
        matches = [
            block for block in self.caches if marker in step_field(block, "path")
        ]
        self.assertEqual(len(matches), 1, f"Expected one cache for {marker}.")
        return matches[0]

    def test_caches_live_under_the_runner_temp_directory(self) -> None:
        self.assertEqual(len(self.caches), 2)
        for block in self.caches:
            path = step_field(block, "path")
            with self.subTest(path=path):
                self.assertIn(CACHE_ACTION, block)
                self.assertTrue(path.startswith("${{ runner.temp }}"))
                self.assertNotIn("github.workspace", path)
                self.assertNotIn("build/", path)

    def test_vcpkg_cache_matches_the_binary_sources_directory(self) -> None:
        cache = self.cache_with("vcpkg-cache")
        path = step_field(cache, "path")
        key = step_field(cache, "key")

        self.assertIn("vcpkg-", key)
        self.assertEqual(step_field(cache, "restore-keys"), "vcpkg-${{ runner.os }}-")
        self.assertIn("steps.image-version.outputs.version", key)
        version_steps = [
            block
            for _, block in self.quality_steps
            if step_property(block, "id") == "image-version"
        ]
        self.assertEqual(len(version_steps), 1)
        self.assertIn("$env:ImageVersion", version_steps[0])
        self.assertIn("GITHUB_OUTPUT", version_steps[0])
        install = self.steps["Install GoogleTest"]
        self.assertEqual(
            step_field(install, "VCPKG_BINARY_SOURCES"),
            f"clear;files,{path},readwrite",
        )
        self.assertIn("New-Item", install)
        self.assertIn("vcpkg-cache", install)

    def test_llvm_cache_version_matches_the_choco_install(self) -> None:
        choco = re.search(
            r"choco upgrade llvm --version=(\d+\.\d+\.\d+)\b", self.workflow
        )
        self.assertIsNotNone(choco)
        version = choco.group(1)
        cache = self.cache_with("llvm-")
        path = step_field(cache, "path")
        key = step_field(cache, "key")

        self.assertEqual(path, f"${{{{ runner.temp }}}}/llvm-{version}")
        self.assertEqual(key, f"llvm-{version}-${{{{ runner.os }}}}-clang-cl-v1")
        install = self.steps["Install LLVM for clang-cl"]
        self.assertIn("cache-hit != 'true'", step_property(install, "if"))
        self.assertIn(f'"llvm-{version}"', install)
        use = self.steps["Use LLVM for clang-cl"]
        use_if = step_property(use, "if")
        self.assertIn("matrix.compiler == 'clang-cl'", use_if)
        self.assertNotIn("cache-hit", use_if)
        self.assertIn(rf"llvm-{version}\bin", use)
        self.assertIn("GITHUB_PATH", use)
        for line in self.workflow.splitlines():
            if "GITHUB_PATH" in line:
                self.assertNotIn(r"Program Files\LLVM\bin", line)

    def test_llvm_mixing_check_runs_after_the_quality_gate(self) -> None:
        name = "Check for mixed LLVM installations"
        names = [step_name for step_name, _ in self.quality_steps]
        self.assertIn(name, names)
        gate_indexes = [
            index for index, step in enumerate(names) if step == "Run quality gate"
        ]
        self.assertTrue(gate_indexes)
        self.assertGreater(names.index(name), max(gate_indexes))
        step = self.steps[name]
        condition = step_property(step, "if")

        self.assertIn("matrix.compiler == 'clang-cl'", condition)
        self.assertIn("CMakeCache.txt", step)
        self.assertIn("clang-cl.exe", step)
        for variable in (
            "CMAKE_CXX_COMPILER",
            "CMAKE_LINKER",
            "CMAKE_AR",
            "CMAKE_MT",
            "CMAKE_RC_COMPILER",
        ):
            with self.subTest(variable=variable):
                self.assertIn(variable, step)

    def test_workflow_does_not_use_ccache_or_sccache(self) -> None:
        for tool in ("ccache", "sccache"):
            with self.subTest(tool=tool):
                self.assertNotIn(tool, self.workflow.lower())


if __name__ == "__main__":
    unittest.main()
