#!/usr/bin/env python3

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import rename_project


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_RELATIVE_PATH = Path("scripts") / "rename_project.py"
OLD_NAME = rename_project.DEFAULT_FROM
NEW_NAME = "contract_probe"


def ignore_when_copying(directory: str, names: list[str]) -> set[str]:
    # Skip what the rename skips, and local symlinks such as `review`, whose
    # targets lie outside the repository.
    return {
        name
        for name in names
        if rename_project.should_skip_dir(Path(directory) / name)
        or (Path(directory) / name).is_symlink()
    }


class RenameProjectContractTest(unittest.TestCase):
    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        # Rename a copy of the repository, never the repository itself.
        self.root = Path(temp_dir.name) / "repo"
        shutil.copytree(ROOT_DIR, self.root, ignore=ignore_when_copying)
        self.script = self.root / SCRIPT_RELATIVE_PATH

    def rename(self, *args: str) -> str:
        result = subprocess.run(
            [sys.executable, str(self.script), NEW_NAME, *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_rename_leaves_the_script_unchanged(self) -> None:
        script_before = self.script.read_bytes()

        output = self.rename()

        self.assertEqual(self.script.read_bytes(), script_before)
        self.assertNotIn(str(SCRIPT_RELATIVE_PATH), output)

    def test_dry_run_does_not_list_the_script(self) -> None:
        output = self.rename("--dry-run")

        self.assertNotIn(str(SCRIPT_RELATIVE_PATH), output)

    def test_rename_replaces_every_other_occurrence(self) -> None:
        old_paths = [
            path.relative_to(self.root)
            for path in rename_project.candidate_paths(self.root, OLD_NAME)
        ]

        self.rename()

        for old_path in old_paths:
            new_path = Path(str(old_path).replace(OLD_NAME, NEW_NAME))
            with self.subTest(path=str(old_path)):
                self.assertFalse((self.root / old_path).exists())
                self.assertTrue((self.root / new_path).exists())
        leftovers = [
            str(path.relative_to(self.root))
            for path in rename_project.iter_files(self.root)
            if path != self.script
            and OLD_NAME in (rename_project.read_text(path) or "")
        ]
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
