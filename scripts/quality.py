#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT_DIR / "build" / "quality"
FORMAT_DIRECTORIES = ("include", "src", "test", "tests")
TIDY_DIRECTORIES = ("src", "test", "tests")
EXAMPLE_DIRECTORIES = ("example", "examples")
CPP_SUFFIXES = (".h", ".cc", ".cpp")
SKIPPED_DIRECTORY_NAMES = {
    ".cache",
    ".deps",
    ".git",
    "__pycache__",
    "_deps",
    "build",
    "cmake-build-debug",
    "cmake-build-release",
    "deps",
    "external",
    "generated",
    "out",
    "third_party",
    "vendor",
}


def run(command: list[str]) -> None:
    print("+ " + " ".join(command))
    subprocess.run(command, cwd=ROOT_DIR, check=True)


def is_clang_tidy_noise(line: str) -> bool:
    stripped = line.strip()
    parts = stripped.split()
    if (
        len(parts) == 3
        and parts[0].isdigit()
        and parts[1] in {"warning", "warnings"}
        and parts[2] == "generated."
    ):
        return True
    if stripped.startswith("Suppressed ") and " in non-user code" in stripped:
        return True
    if stripped.startswith("Use -header-filter="):
        return True
    return False


def run_clang_tidy(command: list[str]) -> None:
    print("+ " + " ".join(command))
    result = subprocess.run(
        command,
        cwd=ROOT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    for line in result.stdout.splitlines():
        if not is_clang_tidy_noise(line):
            print(line)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, command)


def is_project_owned_file(path: Path) -> bool:
    relative_path = path.relative_to(ROOT_DIR)
    return not any(part in SKIPPED_DIRECTORY_NAMES for part in relative_path.parts)


def collect_files(
    directories: tuple[str, ...],
    suffixes: tuple[str, ...],
) -> list[str]:
    files: list[Path] = []
    for directory in directories:
        root = ROOT_DIR / directory
        if not root.is_dir():
            continue
        files.extend(
            path
            for path in root.rglob("*")
            if path.is_file() and is_project_owned_file(path)
        )

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
    return {
        Path(entry["file"]).resolve()
        for entry in entries
        if "file" in entry
    }


def filter_tidy_files(files: list[str]) -> list[str]:
    database_files = compile_database_files()
    if database_files is None:
        return files

    return [
        file
        for file in files
        if (ROOT_DIR / file).resolve() in database_files
    ]


def selected_directories(
    directories: tuple[str, ...],
    include_examples: bool,
) -> tuple[str, ...]:
    if not include_examples:
        return directories
    return (*directories, *EXAMPLE_DIRECTORIES)


def command_format(args: argparse.Namespace) -> None:
    files = collect_files(
        selected_directories(FORMAT_DIRECTORIES, args.include_examples),
        CPP_SUFFIXES,
    )
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


def command_tidy(args: argparse.Namespace) -> None:
    run(["cmake", "--preset", "quality"])

    files = filter_tidy_files(
        collect_files(
            selected_directories(TIDY_DIRECTORIES, args.include_examples),
            (".cc", ".cpp"),
        ),
    )
    if not files:
        print("No C++ source files found in the compile database.")
        return

    run_clang_tidy(["clang-tidy", "--quiet", "-p", str(BUILD_DIR), *files])


def command_check(args: argparse.Namespace) -> None:
    command_format(
        argparse.Namespace(
            check=True,
            include_examples=args.include_examples,
        ),
    )
    command_test(argparse.Namespace())
    command_tidy(argparse.Namespace(include_examples=args.include_examples))


def add_include_examples_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--include-examples",
        action="store_true",
        help="Also include example sources in format and clang-tidy checks.",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CPP-DEV quality commands.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    format_parser = subparsers.add_parser("format", help="Format C++ files.")
    format_parser.add_argument(
        "--check",
        action="store_true",
        help="Verify formatting without rewriting files.",
    )
    add_include_examples_option(format_parser)
    format_parser.set_defaults(func=command_format)

    test_parser = subparsers.add_parser("test", help="Build and run CTest.")
    test_parser.set_defaults(func=command_test)

    tidy_parser = subparsers.add_parser("tidy", help="Run clang-tidy.")
    add_include_examples_option(tidy_parser)
    tidy_parser.set_defaults(func=command_tidy)

    check_parser = subparsers.add_parser("check", help="Run the full quality gate.")
    add_include_examples_option(check_parser)
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
