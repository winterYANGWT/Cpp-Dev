#!/usr/bin/env python3

from __future__ import annotations

import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
PRE_COMMIT_CONFIG = ROOT_DIR / ".pre-commit-config.yaml"
SCRIPTS_README = ROOT_DIR / "scripts" / "README.md"
FORMAT_CHECK_ENTRY = "python scripts/quality.py format --check"


def hook_settings(config: str) -> dict[str, str]:
    """Returns the `key: value` lines of the single local hook."""
    settings: dict[str, str] = {}
    in_hooks = False
    for line in config.splitlines():
        stripped = line.split("#", 1)[0].strip()
        if stripped == "hooks:":
            in_hooks = True
            continue
        if not in_hooks or ":" not in stripped:
            continue
        key, _, value = stripped.removeprefix("- ").partition(":")
        settings[key.strip()] = value.strip()
    return settings


class PreCommitContractTest(unittest.TestCase):
    def test_hook_only_checks_formatting(self) -> None:
        config = PRE_COMMIT_CONFIG.read_text(encoding="utf-8")
        settings = hook_settings(config)

        self.assertIn("repo: local", config)
        self.assertEqual(settings.get("entry"), FORMAT_CHECK_ENTRY)
        # pre-commit provides the interpreter, so `python` works on every
        # platform, including those where the system calls it python3.
        self.assertEqual(settings.get("language"), "python")
        self.assertEqual(settings.get("pass_filenames"), "false")
        self.assertNotIn("tidy", config)

    def test_hook_is_documented_as_opt_in(self) -> None:
        readme = SCRIPTS_README.read_text(encoding="utf-8")

        self.assertIn("## Pre-commit Hook", readme)
        self.assertIn("pre-commit install", readme)
        self.assertIn("not installed automatically", readme)


if __name__ == "__main__":
    unittest.main()
