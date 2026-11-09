#!/usr/bin/env python3

"""Check that the CMake minimum version matches the recommended version.

The CMake files and CMakePresets.json must declare the major.minor version
that scripts/tool-requirements.txt recommends. The check also ensures that
the preset format version and the CMake features in use are supported by that
minimum version, and that the documentation records the minimum.
"""

from __future__ import annotations

import json
import os
import re
import unittest
from pathlib import Path

import tool_versions


ROOT_DIR = Path(__file__).resolve().parents[1]
README = ROOT_DIR / "README.md"
VERSIONS_DOC = ROOT_DIR / "docs" / "tool-versions.md"
PRESETS = ROOT_DIR / "CMakePresets.json"
REQUIRED_CMAKELISTS = (
    ROOT_DIR / "CMakeLists.txt",
    ROOT_DIR / "examples" / "universe_answer" / "CMakeLists.txt",
)
# Match every call and capture its full argument text, so that unsupported
# arguments such as FATAL_ERROR are reported instead of being skipped.
MINIMUM_CALL_RE = re.compile(
    r"cmake_minimum_required\s*\(([^)]*)\)", re.IGNORECASE
)
# A declaration is valid only when its argument is exactly VERSION major.minor.
MINIMUM_ARGUMENT_RE = re.compile(r"VERSION\s+(\d+)\.(\d+)")
# The first CMake version that understands each CMakePresets.json format version.
PRESET_VERSION_CMAKES: dict[int, tuple[int, int]] = {
    3: (3, 21),
    4: (3, 23),
    5: (3, 24),
    6: (3, 25),
    7: (3, 27),
    8: (3, 28),
    9: (3, 30),
    10: (3, 31),
}
# CMake features in use and the first CMake version that provides them.
FEATURE_CMAKES: dict[str, tuple[int, int]] = {
    "-E copy -t": (3, 26),
    "TARGET_RUNTIME_DLLS": (3, 21),
}
# CMake 3.28 introduced CMP0155, which makes C++20 targets scan for modules.
MODULE_SCANNING_POLICY_CMAKE = (3, 28)
MODULE_SCANNING_OFF_RE = re.compile(
    r"^[ \t]*set[ \t]*\([ \t]*CMAKE_CXX_SCAN_FOR_MODULES[ \t]+OFF[ \t]*\)"
    r"[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
TARGET_DEFINITION_RE = re.compile(
    r"\badd_(?:library|executable)\s*\(", re.IGNORECASE
)


def format_version(version: tuple[int, int]) -> str:
    return f"{version[0]}.{version[1]}"


def minimum_arguments(text: str) -> list[str]:
    """Return the stripped argument text of every minimum-version call."""
    return [match.group(1).strip() for match in MINIMUM_CALL_RE.finditer(text)]


def parse_minimum_argument(argument: str) -> tuple[int, int] | None:
    """Parse a plain VERSION major.minor argument, or return None."""
    match = MINIMUM_ARGUMENT_RE.fullmatch(argument.strip())
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def declared_version(text: str) -> tuple[int, int] | None:
    """Return the version of the single minimum-version call in text."""
    arguments = minimum_arguments(text)
    if len(arguments) != 1:
        return None
    return parse_minimum_argument(arguments[0])


def required_cmake_version(text: str) -> tuple[int, int] | None:
    """Return the oldest CMake version that supports the features in text."""
    required: tuple[int, int] | None = None
    for feature, version in FEATURE_CMAKES.items():
        if feature in text:
            required = version if required is None else max(required, version)
    return required


def disables_module_scanning_before_targets(text: str) -> bool:
    """Return whether module scanning is turned off before any target exists."""
    disabled = MODULE_SCANNING_OFF_RE.search(text)
    if disabled is None:
        return False
    target = TARGET_DEFINITION_RE.search(text)
    return target is None or disabled.start() < target.start()


def preset_cmake_version(version: int) -> tuple[int, int]:
    """Return the oldest CMake version that reads this preset format version."""
    if version not in PRESET_VERSION_CMAKES:
        raise ValueError(
            f"Unknown CMakePresets.json format version {version}; add it to "
            "PRESET_VERSION_CMAKES."
        )
    return PRESET_VERSION_CMAKES[version]


def cmake_lists_files(root: Path = ROOT_DIR) -> list[Path]:
    """Find every CMakeLists.txt under root, skipping build and dot directories."""
    files: list[Path] = []
    for directory, dirnames, filenames in os.walk(root):
        # Do not follow symlinked directories such as the review checkout.
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name != "build"
            and not name.startswith(".")
            and not (Path(directory) / name).is_symlink()
        )
        if "CMakeLists.txt" in filenames:
            files.append(Path(directory) / "CMakeLists.txt")
    return sorted(files)


def relative(path: Path) -> str:
    return path.relative_to(ROOT_DIR).as_posix()


class CMakeMinimumContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.recommended = tool_versions.recommended_versions().get("cmake")
        self.assertIsNotNone(
            self.recommended,
            "scripts/tool-requirements.txt has no cmake==X.Y.* pin.",
        )
        self.expected = format_version(self.recommended)

    def test_every_cmake_lists_declares_the_recommended_minimum(self) -> None:
        found = cmake_lists_files()
        for path in REQUIRED_CMAKELISTS:
            self.assertIn(
                path,
                found,
                f"{relative(path)} is missing; it must declare "
                f"cmake_minimum_required(VERSION {self.expected}).",
            )
        for path in found:
            name = relative(path)
            arguments = minimum_arguments(path.read_text(encoding="utf-8"))
            if path in REQUIRED_CMAKELISTS:
                self.assertEqual(
                    len(arguments),
                    1,
                    f"{name} must contain exactly one "
                    "cmake_minimum_required(...) call, but found "
                    f"{len(arguments)}.",
                )
            elif not arguments:
                # Files other than the required ones may omit the declaration.
                continue
            for argument in arguments:
                self.assertEqual(
                    argument,
                    f"VERSION {self.expected}",
                    f"{name} declares cmake_minimum_required({argument}); "
                    f"expected exactly cmake_minimum_required(VERSION "
                    f"{self.expected}), with no FATAL_ERROR, version range, "
                    "patch version, or other arguments.",
                )

    def test_preset_minimum_matches_the_recommended_minimum(self) -> None:
        presets = json.loads(PRESETS.read_text(encoding="utf-8"))
        major, minor = self.recommended
        self.assertEqual(
            presets.get("cmakeMinimumRequired"),
            {"major": major, "minor": minor, "patch": 0},
            "CMakePresets.json cmakeMinimumRequired does not match "
            f"{major}.{minor}.0 from scripts/tool-requirements.txt.",
        )

    def test_preset_file_version_is_supported_by_the_declared_minimum(self) -> None:
        presets = json.loads(PRESETS.read_text(encoding="utf-8"))
        minimum = presets.get("cmakeMinimumRequired")
        self.assertIsNotNone(
            minimum,
            "CMakePresets.json has no cmakeMinimumRequired object.",
        )
        declared = (int(minimum["major"]), int(minimum["minor"]))
        required = preset_cmake_version(int(presets["version"]))
        self.assertLessEqual(
            required,
            declared,
            f"CMakePresets.json format version {presets['version']} needs CMake "
            f"{format_version(required)}, but the declared minimum is "
            f"{format_version(declared)}.",
        )

    def test_used_cmake_features_fit_the_declared_minimum(self) -> None:
        declared = declared_version(
            (ROOT_DIR / "CMakeLists.txt").read_text(encoding="utf-8")
        )
        self.assertIsNotNone(
            declared,
            "CMakeLists.txt must contain exactly one "
            f"cmake_minimum_required(VERSION {self.expected}) declaration.",
        )
        paths = cmake_lists_files() + sorted((ROOT_DIR / "cmake").glob("*.cmake"))
        for path in paths:
            text = path.read_text(encoding="utf-8")
            required = required_cmake_version(text)
            if required is None:
                continue
            self.assertLessEqual(
                required,
                declared,
                f"{relative(path)} uses a CMake feature that needs CMake "
                f"{format_version(required)}, but the declared minimum is "
                f"{format_version(declared)}.",
            )

    def test_module_scanning_is_disabled_before_targets(self) -> None:
        declared = declared_version(
            (ROOT_DIR / "CMakeLists.txt").read_text(encoding="utf-8")
        )
        self.assertIsNotNone(
            declared,
            "CMakeLists.txt must contain exactly one "
            f"cmake_minimum_required(VERSION {self.expected}) declaration.",
        )
        if declared < MODULE_SCANNING_POLICY_CMAKE:
            self.skipTest(
                f"CMake {format_version(declared)} predates CMP0155, so module "
                "scanning is not enabled by the declared minimum."
            )
        for path in REQUIRED_CMAKELISTS:
            self.assertTrue(
                disables_module_scanning_before_targets(
                    path.read_text(encoding="utf-8")
                ),
                f"{relative(path)} must contain "
                "'set(CMAKE_CXX_SCAN_FOR_MODULES OFF)' before its first "
                "add_library() or add_executable(). CMP0155, introduced in "
                f"CMake {format_version(MODULE_SCANNING_POLICY_CMAKE)}, makes "
                "C++20 targets scan for modules; the GCC-only scanning flags "
                "in compile_commands.json are unknown arguments to clang-tidy. "
                "The setting must come before any target is defined to affect "
                "it.",
            )

    def test_readme_cmake_contract_states_the_recommended_minimum(self) -> None:
        readme = README.read_text(encoding="utf-8")
        section = re.search(
            r"^## CMake Contract\s*$(.*?)(?=^## |\Z)", readme, re.M | re.S
        )
        self.assertIsNotNone(
            section,
            "README.md has no '## CMake Contract' section.",
        )
        self.assertIn(
            f"CMake `{self.expected}` or newer",
            section.group(1),
            "The README.md CMake Contract section does not say "
            f"'CMake `{self.expected}` or newer'.",
        )

    def test_tool_versions_doc_records_the_minimum(self) -> None:
        doc = VERSIONS_DOC.read_text(encoding="utf-8")
        self.assertIn(
            f"`cmake_minimum_required(VERSION {self.expected})`",
            doc,
            "docs/tool-versions.md does not contain "
            f"'`cmake_minimum_required(VERSION {self.expected})`'.",
        )


class RequiredVersionFunctionsTest(unittest.TestCase):
    def test_minimum_declaration_parsing(self) -> None:
        self.assertEqual(
            minimum_arguments("cmake_minimum_required(VERSION 4.2)"),
            ["VERSION 4.2"],
        )
        self.assertEqual(
            minimum_arguments("CMAKE_MINIMUM_REQUIRED(VERSION 4.2)"),
            ["VERSION 4.2"],
        )
        self.assertEqual(parse_minimum_argument(" VERSION 4.2 "), (4, 2))
        self.assertEqual(
            minimum_arguments("cmake_minimum_required(VERSION 4.2 FATAL_ERROR)"),
            ["VERSION 4.2 FATAL_ERROR"],
        )
        self.assertEqual(
            minimum_arguments("cmake_minimum_required(VERSION 3.26...4.2)"),
            ["VERSION 3.26...4.2"],
        )
        self.assertEqual(
            minimum_arguments("cmake_minimum_required(VERSION 4.2.3)"),
            ["VERSION 4.2.3"],
        )
        self.assertEqual(minimum_arguments("project(example)"), [])
        for argument in (
            "VERSION 4.2 FATAL_ERROR",
            "VERSION 3.26...4.2",
            "VERSION 4.2.3",
            "4.2",
        ):
            with self.subTest(argument=argument):
                self.assertIsNone(parse_minimum_argument(argument))
        self.assertIsNone(declared_version("project(example)"))

    def test_feature_detection_uses_the_highest_required_version(self) -> None:
        copy_t = "${CMAKE_COMMAND} -E copy -t $<TARGET_FILE_DIR:app> file"
        both = copy_t + " $<TARGET_RUNTIME_DLLS:app>"
        plain = "add_library(example STATIC example.cc)"

        self.assertEqual(required_cmake_version(copy_t), (3, 26))
        self.assertIsNone(required_cmake_version(plain))
        self.assertEqual(required_cmake_version(both), (3, 26))

    def test_module_scanning_switch_must_precede_targets(self) -> None:
        switch = "set(CMAKE_CXX_SCAN_FOR_MODULES OFF)"
        target = "add_library(example example.cc)"
        self.assertTrue(
            disables_module_scanning_before_targets(f"{switch}\n{target}")
        )
        self.assertFalse(disables_module_scanning_before_targets(target))
        self.assertFalse(
            disables_module_scanning_before_targets(f"{target}\n{switch}")
        )
        self.assertFalse(
            disables_module_scanning_before_targets(
                "set(CMAKE_CXX_SCAN_FOR_MODULES ON)\n" + target
            )
        )

    def test_preset_version_lookup(self) -> None:
        for version, expected in PRESET_VERSION_CMAKES.items():
            with self.subTest(version=version):
                self.assertEqual(preset_cmake_version(version), expected)
        with self.assertRaisesRegex(ValueError, "99"):
            preset_cmake_version(99)


if __name__ == "__main__":
    unittest.main()
