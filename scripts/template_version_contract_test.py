#!/usr/bin/env python3

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_VERSION_FILE = ROOT_DIR / "TEMPLATE_VERSION"
VERSION_RE = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")


class TemplateVersionContractTest(unittest.TestCase):
    def test_template_version_is_a_single_semver_tag(self) -> None:
        self.assertTrue(
            TEMPLATE_VERSION_FILE.is_file(),
            "TEMPLATE_VERSION must exist at the repository root.",
        )

        text = TEMPLATE_VERSION_FILE.read_text(encoding="utf-8")
        self.assertTrue(
            text.endswith("\n") and not text.endswith("\n\n"),
            "TEMPLATE_VERSION must end with exactly one newline.",
        )
        self.assertIsNotNone(
            VERSION_RE.fullmatch(text[:-1]),
            f"TEMPLATE_VERSION must contain one vX.Y.Z version, got {text!r}.",
        )


if __name__ == "__main__":
    unittest.main()
