#!/usr/bin/env python3

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import quality
import rename_project


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_RELATIVE_PATH = Path("scripts") / "rename_project.py"
# Keep the placeholder literal here: renaming a generated repository rewrites
# this file too, so the test follows the new placeholder in that copy.
OLD_NAME = "mylib"
OLD_UPPER = OLD_NAME.upper()
NEW_NAME = "contract_probe"
NEW_UPPER = NEW_NAME.upper()


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
        self.temp_dir = Path(temp_dir.name)
        # Rename a copy of the repository, never the repository itself.
        self.root = self.temp_dir / "repo"
        shutil.copytree(ROOT_DIR, self.root, ignore=ignore_when_copying)
        self.script = self.root / SCRIPT_RELATIVE_PATH

    def rename(self, *args: str) -> str:
        result = subprocess.run(
            [
                sys.executable,
                str(self.script),
                NEW_NAME,
                "--from",
                OLD_NAME,
                *args,
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def iter_texts(self):
        for path in rename_project.iter_files(self.root):
            if path == self.script:
                continue
            text = rename_project.read_text(path)
            if text is not None:
                yield path, text

    def count_token(self, token: str) -> int:
        return sum(text.count(token) for _, text in self.iter_texts())

    def renamed_path(self, relative: Path) -> Path:
        name = str(relative)
        for old, new in rename_project.replacement_pairs(OLD_NAME, NEW_NAME):
            name = name.replace(old, new)
        return Path(name)

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
            for path in rename_project.candidate_paths(self.root, OLD_NAME, NEW_NAME)
        ]

        self.rename()

        for old_path in old_paths:
            new_path = self.renamed_path(old_path)
            with self.subTest(path=str(old_path)):
                self.assertFalse((self.root / old_path).exists())
                self.assertTrue((self.root / new_path).exists())
        leftovers = [
            str(path.relative_to(self.root))
            for path, text in self.iter_texts()
            if OLD_NAME in text or OLD_UPPER in text
        ]
        self.assertEqual(leftovers, [])

    def test_path_names_use_both_replacement_rules(self) -> None:
        docs = self.root / "docs"
        upper_file = docs / f"{OLD_UPPER}_NOTES.md"
        upper_file.write_text("notes\n", encoding="utf-8")
        mixed_dir = docs / f"{OLD_UPPER}_{OLD_NAME}_mixed"
        mixed_dir.mkdir()
        old_paths = [
            upper_file.relative_to(self.root),
            mixed_dir.relative_to(self.root),
        ]
        new_paths = [self.renamed_path(path) for path in old_paths]

        output = self.rename("--dry-run")
        for old_path, new_path in zip(old_paths, new_paths):
            with self.subTest(path=str(old_path)):
                self.assertIn(f"{old_path} -> {new_path}", output)

        self.rename()
        for old_path, new_path in zip(old_paths, new_paths):
            with self.subTest(path=str(old_path)):
                self.assertFalse((self.root / old_path).exists())
                self.assertTrue((self.root / new_path).exists())

    def test_new_uppercase_name_appears_in_the_header_macros(self) -> None:
        self.rename()

        header = self.root / "include" / NEW_NAME / f"{NEW_NAME}.h"
        text = header.read_text(encoding="utf-8")

        self.assertIn(f"{NEW_UPPER}_EXPORT", text)
        self.assertIn(f"{NEW_UPPER}_{NEW_UPPER}_H_", text)

    def test_cmake_variable_tokens_are_unchanged(self) -> None:
        tokens = ("${PROJECT_NAME}", "@PROJECT_NAME@")
        before = {token: self.count_token(token) for token in tokens}

        self.rename()

        after = {token: self.count_token(token) for token in tokens}
        self.assertEqual(after, before)

    def test_skip_list_is_shared_with_quality(self) -> None:
        self.assertIs(
            rename_project.SKIPPED_DIRECTORY_NAMES,
            quality.SKIPPED_DIRECTORY_NAMES,
        )
        for name in (".venv", "venv", "node_modules", "third_party"):
            with self.subTest(directory=name):
                self.assertIn(name, rename_project.SKIPPED_DIRECTORY_NAMES)

    def test_skipped_directories_keep_their_contents(self) -> None:
        contents = f"{OLD_NAME}\n{OLD_UPPER}\n"
        paths = []
        for name in (".venv", "node_modules", "third_party"):
            path = self.root / name / "x.txt"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding="utf-8")
            paths.append(path)

        self.rename()

        for path in paths:
            with self.subTest(path=str(path.relative_to(self.root))):
                self.assertEqual(path.read_text(encoding="utf-8"), contents)

    def test_symlinks_are_not_followed_or_rewritten(self) -> None:
        outside = self.temp_dir / "outside.txt"
        outside_contents = f"{OLD_NAME}\n{OLD_UPPER}\n"
        outside.write_text(outside_contents, encoding="utf-8")
        dangling = self.root / "dangling-link.txt"
        dangling.symlink_to(self.root / "missing-target.txt")
        external_link = self.root / "external-link.txt"
        external_link.symlink_to(outside)
        named_link = self.root / f"{OLD_NAME}-link.txt"
        named_link.symlink_to(outside)

        self.rename("--dry-run")
        self.rename()

        self.assertEqual(outside.read_text(encoding="utf-8"), outside_contents)
        self.assertTrue(dangling.is_symlink())
        self.assertTrue(external_link.is_symlink())
        self.assertFalse(named_link.exists())
        self.assertTrue((self.root / f"{NEW_NAME}-link.txt").is_symlink())


if __name__ == "__main__":
    unittest.main()
