#!/usr/bin/env python3

from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
USER_LOCAL_PATHS = ("CMakeUserPresets.json",)


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


class GitignoreContractTest(unittest.TestCase):
    def test_user_local_files_are_ignored(self) -> None:
        git = git_command()
        if git is None:
            self.skipTest("Not running inside a git work tree.")

        for path in USER_LOCAL_PATHS:
            result = subprocess.run(
                [git, "check-ignore", "--no-index", "--quiet", path],
                cwd=ROOT_DIR,
                check=False,
            )
            self.assertEqual(
                result.returncode,
                0,
                f"{path} is a user-local file and must be ignored by .gitignore.",
            )


if __name__ == "__main__":
    unittest.main()
