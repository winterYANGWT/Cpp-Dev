#!/usr/bin/env python3

from __future__ import annotations

import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
CI_WORKFLOW = ROOT_DIR / ".github" / "workflows" / "ci.yml"


class CiCacheContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    def test_workflow_does_not_use_ccache_or_sccache(self) -> None:
        for tool in ("ccache", "sccache"):
            with self.subTest(tool=tool):
                self.assertNotIn(tool, self.workflow.lower())


if __name__ == "__main__":
    unittest.main()
