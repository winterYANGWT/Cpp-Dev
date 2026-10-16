#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
COMPILER_MODULE = ROOT_DIR / "cmake" / "project_nameCompiler.cmake"
PRESETS_FILE = ROOT_DIR / "CMakePresets.json"
CI_WORKFLOW = ROOT_DIR / ".github" / "workflows" / "ci.yml"
COMPILE_OPTIONS_RE = re.compile(r"target_compile_options\(([^()]*)\)")
ASAN_UBSAN_FLAG = "-fsanitize=address,undefined"
NO_RECOVER_FLAG = "-fno-sanitize-recover=all"


class SanitizerContractTest(unittest.TestCase):
    def test_ubsan_findings_fail_the_process(self) -> None:
        text = COMPILER_MODULE.read_text(encoding="utf-8")
        sanitizer_blocks = [
            block
            for block in COMPILE_OPTIONS_RE.findall(text)
            if ASAN_UBSAN_FLAG in block
        ]

        self.assertTrue(
            sanitizer_blocks,
            f"No {ASAN_UBSAN_FLAG} compile options found in {COMPILER_MODULE.name}.",
        )
        for block in sanitizer_blocks:
            self.assertIn(
                NO_RECOVER_FLAG,
                block,
                "UBSan is recoverable by default; every ASan/UBSan compile option "
                f"block must also pass {NO_RECOVER_FLAG}.",
            )

    def test_asan_ubsan_preset_enables_sanitizers(self) -> None:
        presets = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
        configure_presets = {
            preset["name"]: preset for preset in presets["configurePresets"]
        }

        cache_variables = configure_presets["asan-ubsan"]["cacheVariables"]
        self.assertEqual(cache_variables.get("project_name_ENABLE_SANITIZERS"), "ON")

    def test_tsan_preset_enables_only_thread_sanitizer(self) -> None:
        presets = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
        configure_presets = {
            preset["name"]: preset for preset in presets["configurePresets"]
        }

        cache_variables = configure_presets["tsan"]["cacheVariables"]
        self.assertEqual(
            cache_variables.get("project_name_ENABLE_THREAD_SANITIZER"),
            "ON",
        )
        self.assertNotEqual(cache_variables.get("project_name_ENABLE_SANITIZERS"), "ON")
        for kind in ("buildPresets", "testPresets"):
            with self.subTest(kind=kind):
                self.assertIn("tsan", [preset["name"] for preset in presets[kind]])

    def test_ci_runs_both_sanitizer_presets(self) -> None:
        workflow = CI_WORKFLOW.read_text(encoding="utf-8")

        for preset in ("asan-ubsan", "tsan"):
            with self.subTest(preset=preset):
                self.assertIn(f"ctest --preset {preset}", workflow)


if __name__ == "__main__":
    unittest.main()
