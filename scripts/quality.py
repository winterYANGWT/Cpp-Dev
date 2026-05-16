#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT_DIR / "build" / "quality"
FORMAT_DIRECTORIES = ["include", "src", "test", "tests", "examples"]
TIDY_DIRECTORIES = ["src", "test", "tests", "examples"]
CPP_SUFFIXES = (".h", ".cc", ".cpp")


def run(command: list[str]) -> None:
    print("+ " + " ".join(command))
    subprocess.run(command, cwd=ROOT_DIR, check=True)


def collect_files(directories: list[str], suffixes: tuple[str, ...]) -> list[str]:
    files: list[Path] = []
    for directory in directories:
        root = ROOT_DIR / directory
        if not root.is_dir():
            continue
        files.extend(path for path in root.rglob("*") if path.is_file())

    return [
        str(path.relative_to(ROOT_DIR))
        for path in sorted(files)
        if path.suffix in suffixes
    ]


def compile_database_files() -> set[Path] | None:
    database = BUILD_DIR / "compile_commands.json"
    if not database.is_file():
        return None

    entries = json.loads(database.read_text(encoding="utf-8"))
    return {Path(entry["file"]).resolve() for entry in entries}


def filter_tidy_files(files: list[str]) -> list[str]:
    database_files = compile_database_files()
    if database_files is None:
        return files

    return [
        file
        for file in files
        if (ROOT_DIR / file).resolve() in database_files
    ]


def command_format(args: argparse.Namespace) -> None:
    files = collect_files(FORMAT_DIRECTORIES, CPP_SUFFIXES)
    if not files:
        print("No C++ files found.")
        return

    if args.check:
        run(["clang-format", "--dry-run", "--Werror", *files])
    else:
        run(["clang-format", "-i", *files])


def command_test(_: argparse.Namespace) -> None:
    run(["cmake", "--preset", "quality"])
    run(["cmake", "--build", "--preset", "quality"])
    run(["ctest", "--preset", "quality"])


def command_tidy(_: argparse.Namespace) -> None:
    run(["cmake", "--preset", "quality"])

    files = filter_tidy_files(collect_files(TIDY_DIRECTORIES, (".cc", ".cpp")))
    if not files:
        print("No C++ source files found in the compile database.")
        return

    run(["clang-tidy", "-p", str(BUILD_DIR), *files])


def command_check(_: argparse.Namespace) -> None:
    command_format(argparse.Namespace(check=True))
    command_test(argparse.Namespace())
    command_tidy(argparse.Namespace())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CPP-DEV quality commands.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    format_parser = subparsers.add_parser("format", help="Format C++ files.")
    format_parser.add_argument(
        "--check",
        action="store_true",
        help="Verify formatting without rewriting files.",
    )
    format_parser.set_defaults(func=command_format)

    test_parser = subparsers.add_parser("test", help="Build and run CTest.")
    test_parser.set_defaults(func=command_test)

    tidy_parser = subparsers.add_parser("tidy", help="Run clang-tidy.")
    tidy_parser.set_defaults(func=command_tidy)

    check_parser = subparsers.add_parser("check", help="Run the full quality gate.")
    check_parser.set_defaults(func=command_check)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        args.func(args)
    except subprocess.CalledProcessError as error:
        return error.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
