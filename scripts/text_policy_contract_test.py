#!/usr/bin/env python3

from __future__ import annotations

import configparser
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
EDITORCONFIG_FILE = ROOT_DIR / ".editorconfig"
PREAMBLE_SECTION = "preamble"
EXPECTED_EDITORCONFIG = {
    PREAMBLE_SECTION: {"root": "true"},
    "*": {
        "charset": "utf-8",
        "end_of_line": "lf",
        "insert_final_newline": "true",
        "trim_trailing_whitespace": "true",
        "indent_style": "space",
        "indent_size": "2",
    },
    "*.py": {"indent_size": "4"},
    "*.md": {"trim_trailing_whitespace": "false"},
    "*.{bat,cmd}": {"end_of_line": "crlf"},
}
# Sample paths do not need to exist; git check-attr only matches patterns.
EXPECTED_CHECKOUT_EOL = {
    "CMakeLists.txt": "lf",
    "include/sample.h": "lf",
    "scripts/sample.py": "lf",
    "scripts/sample.bat": "crlf",
    "scripts/sample.cmd": "crlf",
}
BINARY_SAMPLE_PATHS = ("docs/sample.png", "docs/sample.pdf", "sample.zip")


def git_command() -> str | None:
    git = shutil.which("git")
    if git is None:
        return None
    result = subprocess.run(
        [git, "rev-parse", "--is-inside-work-tree"],
        cwd=ROOT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return git if result.returncode == 0 else None


def check_attributes(git: str, path: str, *names: str) -> dict[str, str]:
    output = subprocess.run(
        [git, "check-attr", "-z", *names, "--", path],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    fields = output.split("\0")[:-1]
    return {fields[i + 1]: fields[i + 2] for i in range(0, len(fields), 3)}


class TextPolicyContractTest(unittest.TestCase):
    def test_editorconfig_matches_text_policy(self) -> None:
        parser = configparser.ConfigParser(interpolation=None)
        # Properties before the first section belong to an implicit preamble.
        parser.read_string(
            f"[{PREAMBLE_SECTION}]\n"
            + EDITORCONFIG_FILE.read_text(encoding="utf-8")
        )

        for section, properties in EXPECTED_EDITORCONFIG.items():
            for name, value in properties.items():
                with self.subTest(section=section, name=name):
                    self.assertEqual(
                        parser.get(section, name, fallback="").lower(),
                        value,
                    )

    def test_gitattributes_set_checkout_line_endings(self) -> None:
        git = git_command()
        if git is None:
            self.skipTest("Not running inside a git work tree.")

        for path, eol in EXPECTED_CHECKOUT_EOL.items():
            with self.subTest(path=path):
                attributes = check_attributes(git, path, "text", "eol")
                self.assertIn(attributes["text"], ("auto", "set"))
                self.assertEqual(attributes["eol"], eol)

    def test_gitattributes_mark_binary_files(self) -> None:
        git = git_command()
        if git is None:
            self.skipTest("Not running inside a git work tree.")

        for path in BINARY_SAMPLE_PATHS:
            with self.subTest(path=path):
                attributes = check_attributes(git, path, "text", "diff", "merge")
                self.assertEqual(
                    attributes,
                    {"text": "unset", "diff": "unset", "merge": "unset"},
                )

    def test_tracked_text_files_are_stored_with_lf(self) -> None:
        git = git_command()
        if git is None:
            self.skipTest("Not running inside a git work tree.")

        output = subprocess.run(
            [git, "ls-files", "--eol", "-z"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        crlf_paths = [
            path
            for info, path in (
                entry.split("\t", 1) for entry in output.split("\0") if entry
            )
            if info.startswith(("i/crlf", "i/mixed"))
        ]

        self.assertEqual(
            crlf_paths,
            [],
            "Tracked text files must be stored with LF line endings. "
            "Run `git add --renormalize .` and commit the result.",
        )


if __name__ == "__main__":
    unittest.main()
