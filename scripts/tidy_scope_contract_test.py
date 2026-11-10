#!/usr/bin/env python3

"""Check that clang-tidy checks private headers under src/.

The HeaderFilterRegex in .clang-tidy must match the header and source
suffixes used by scripts/quality.py in include/, src/, test/, and tests/.
Private headers such as src/detail.h are the reason src/ must be covered.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import quality


ROOT_DIR = Path(__file__).resolve().parents[1]
CLANG_TIDY = ROOT_DIR / ".clang-tidy"
HEADER_FILTER_LINE_RE = re.compile(
    r'^[ \t]*HeaderFilterRegex[ \t]*:[ \t]*"((?:[^"\\]|\\.)*)"[ \t]*$',
    re.MULTILINE,
)
DIRECTORIES = ("include/mylib", "src", "src/detail", "test", "tests")
ABSOLUTE_PREFIX = "/home/user/repo/"


def read_header_filter_regex(path: Path = CLANG_TIDY) -> str:
    """Return HeaderFilterRegex with YAML double-quote escapes restored."""
    text = path.read_text(encoding="utf-8")
    match = HEADER_FILTER_LINE_RE.search(text)
    if match is None:
        raise AssertionError(
            f"{path} has no HeaderFilterRegex: \"...\" line; clang-tidy "
            "would use its default header filter."
        )
    # The file contains \\. for a literal backslash plus a dot; clang-tidy
    # needs the regex escape \. instead.
    return match.group(1).replace("\\\\", "\\")


class TidyScopeContractTest(unittest.TestCase):
    def test_header_filter_regex_is_declared(self) -> None:
        regex = read_header_filter_regex()
        self.assertTrue(
            regex,
            f"{CLANG_TIDY} declares an empty HeaderFilterRegex.",
        )

    def test_cxx_paths_match_the_header_filter_regex(self) -> None:
        regex = read_header_filter_regex()
        suffixes = (*quality.CXX_HEADER_SUFFIXES, *quality.CXX_SOURCE_SUFFIXES)
        for directory in DIRECTORIES:
            for suffix in suffixes:
                relative_path = f"{directory}/header{suffix}"
                for path in (relative_path, f"{ABSOLUTE_PREFIX}{relative_path}"):
                    with self.subTest(path=path):
                        self.assertIsNotNone(
                            re.search(regex, path),
                            f"{path!r} does not match HeaderFilterRegex "
                            f"{regex!r}; clang-tidy ignores this file.",
                        )

    def test_non_cxx_paths_do_not_match_the_header_filter_regex(self) -> None:
        regex = read_header_filter_regex()
        for directory in DIRECTORIES:
            for suffix in (".txt", ".cmake", ".md"):
                relative_path = f"{directory}/notes{suffix}"
                for path in (relative_path, f"{ABSOLUTE_PREFIX}{relative_path}"):
                    with self.subTest(path=path):
                        self.assertIsNone(
                            re.search(regex, path),
                            f"{path!r} unexpectedly matches "
                            f"HeaderFilterRegex {regex!r}.",
                        )


if __name__ == "__main__":
    unittest.main()
