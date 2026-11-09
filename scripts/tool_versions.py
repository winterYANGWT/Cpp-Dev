#!/usr/bin/env python3

"""Compare the installed tools with the recommended versions.

The recommended versions are the major.minor pins in tool-requirements.txt. A
different version only prints a warning, unless --strict is given, which CI
uses to make sure that it runs the recommended versions.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
REQUIREMENTS_FILE = ROOT_DIR / "scripts" / "tool-requirements.txt"
PIN_RE = re.compile(r"^([A-Za-z0-9_.-]+)==(\d+)\.(\d+)\.\*$")
VERSION_RE = re.compile(r"version (\d+\.\d+(?:\.\d+)?)")
# LLVM tools that are not installed from PyPI share clang-format's version.
LLVM_TOOLS = {"clang", "clang++", "clang-cl"}
LLVM_REFERENCE_TOOL = "clang-format"


def recommended_versions(
    requirements_file: Path = REQUIREMENTS_FILE,
) -> dict[str, tuple[int, int]]:
    versions: dict[str, tuple[int, int]] = {}
    for line in requirements_file.read_text(encoding="utf-8").splitlines():
        match = PIN_RE.match(line.strip())
        if match:
            name, major, minor = match.groups()
            versions[name] = (int(major), int(minor))
    return versions


def parse_version(output: str) -> str | None:
    match = VERSION_RE.search(output)
    return match.group(1) if match else None


def major_minor(version: str) -> tuple[int, int]:
    major, minor = version.split(".")[:2]
    return int(major), int(minor)


def installed_version(tool: str) -> tuple[str | None, str | None]:
    path = shutil.which(tool)
    if path is None:
        return None, None
    try:
        result = subprocess.run(
            [path, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    except OSError:
        return path, None
    return path, parse_version(result.stdout)


def format_version(version: tuple[int, int]) -> str:
    return f"{version[0]}.{version[1]}"


def check_tools(extra_tools: list[str], strict: bool) -> int:
    recommended = recommended_versions()
    for tool in extra_tools:
        if tool not in LLVM_TOOLS:
            raise SystemExit(
                f"No recommended version for {tool}. Known extra tools: "
                + ", ".join(sorted(LLVM_TOOLS))
            )
        recommended[tool] = recommended[LLVM_REFERENCE_TOOL]

    print(
        "Recommended tool versions (docs/tool-versions.md). They are "
        "recommendations, not requirements.",
        flush=True,
    )
    problems: list[str] = []
    for tool, expected in recommended.items():
        path, version = installed_version(tool)
        if path is None:
            status = "not found"
            problems.append(f"{tool} is not installed or not on PATH.")
        elif version is None:
            status = f"unknown version at {path}"
            problems.append(f"Could not read the version of {tool} at {path}.")
        elif major_minor(version) != expected:
            status = f"found {version} at {path}"
            problems.append(
                f"{tool} {version} at {path} differs from the recommended "
                f"{format_version(expected)}."
            )
        else:
            status = f"found {version} at {path}"
        print(f"  {tool:<13} {format_version(expected):<6} {status}", flush=True)

    if not problems:
        return 0
    label = "Error" if strict else "Warning"
    for problem in problems:
        print(f"{label}: {problem}", flush=True)
    if strict:
        return 1
    print(
        "Other versions usually work, but formatting and clang-tidy results "
        "can differ from CI.",
        flush=True,
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when a tool is missing or differs from the recommendation.",
    )
    parser.add_argument(
        "--tool",
        action="append",
        default=[],
        metavar="NAME",
        help="Also check an LLVM tool from the same release, such as clang-cl.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return check_tools(args.tool, args.strict)


if __name__ == "__main__":
    sys.exit(main())
