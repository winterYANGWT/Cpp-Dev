#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT_DIR / "build" / "quality"
HEADER_SMOKE_DIR = BUILD_DIR / "header_smoke"
CXX_HEADER_SUFFIXES = (".h", ".hh", ".hpp", ".hxx")
CXX_SOURCE_SUFFIXES = (".cc", ".cpp", ".cxx")
CXX_SUFFIXES = (*CXX_HEADER_SUFFIXES, *CXX_SOURCE_SUFFIXES)
OUTPUT_OPTIONS_WITH_VALUE = {"-o", "-MF", "-MT", "-MQ", "-MJ", "/Fo"}
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
    print("+ " + " ".join(command), flush=True)
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
    print("+ " + " ".join(command), flush=True)
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
    try:
        relative_path = path.relative_to(ROOT_DIR)
    except ValueError:
        return False
    return not any(part in SKIPPED_DIRECTORY_NAMES for part in relative_path.parts)


def collect_project_files(suffixes: tuple[str, ...]) -> list[str]:
    return [
        str(path.relative_to(ROOT_DIR))
        for path in sorted(ROOT_DIR.rglob("*"))
        if path.is_file()
        and path.suffix in suffixes
        and is_project_owned_file(path)
    ]


def compile_database_entries() -> list[dict[str, object]] | None:
    database = BUILD_DIR / "compile_commands.json"
    if not database.is_file():
        return None

    entries = json.loads(database.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def compile_database_source_files(
    entries: list[dict[str, object]] | None,
) -> list[str] | None:
    if entries is None:
        return None

    files = {
        path
        for entry in entries
        if isinstance(entry.get("file"), str)
        for path in (Path(str(entry["file"])).resolve(),)
        if path.suffix in CXX_SOURCE_SUFFIXES and is_project_owned_file(path)
    }
    return [
        str(path.relative_to(ROOT_DIR))
        for path in sorted(files)
    ]


def compile_command_tokens(entry: dict[str, object]) -> list[str] | None:
    arguments = entry.get("arguments")
    if isinstance(arguments, list):
        return [str(argument) for argument in arguments]

    command = entry.get("command")
    if isinstance(command, str):
        return shlex.split(command)

    return None


def compile_command_directory(entry: dict[str, object] | None) -> Path:
    if entry is None:
        return ROOT_DIR

    directory = entry.get("directory")
    if isinstance(directory, str):
        return Path(directory)
    return ROOT_DIR


def compile_command_file(entry: dict[str, object]) -> Path | None:
    file = entry.get("file")
    if not isinstance(file, str):
        return None
    return Path(file).resolve()


def token_matches_path(token: str, path: Path, base_dir: Path) -> bool:
    try:
        candidate = Path(token)
        if not candidate.is_absolute():
            candidate = base_dir / candidate
        return candidate.resolve() == path.resolve()
    except (OSError, RuntimeError):
        return False


def fallback_smoke_compile_tokens(smoke_file: Path) -> list[str]:
    return [
        "c++",
        "-std=c++20",
        "-I",
        str(ROOT_DIR / "include"),
        "-c",
        str(smoke_file),
    ]


def smoke_compile_tokens(
    base_entry: dict[str, object] | None,
    smoke_file: Path,
) -> list[str]:
    if base_entry is None:
        return fallback_smoke_compile_tokens(smoke_file)

    tokens = compile_command_tokens(base_entry)
    if not tokens:
        return fallback_smoke_compile_tokens(smoke_file)

    source_file = compile_command_file(base_entry)
    base_dir = compile_command_directory(base_entry)
    compiler = tokens[0]
    flags: list[str] = []
    skip_next = False

    for token in tokens[1:]:
        if skip_next:
            skip_next = False
            continue
        if token in OUTPUT_OPTIONS_WITH_VALUE:
            skip_next = True
            continue
        if token.startswith("-o") and token != "-o":
            continue
        if token.startswith("/Fo") and token != "/Fo":
            continue
        if source_file is not None and token_matches_path(token, source_file, base_dir):
            continue
        flags.append(token)

    if "-c" not in flags and "/c" not in flags:
        flags.append("-c")

    return [compiler, *flags, str(smoke_file)]


def first_compile_database_entry(
    entries: list[dict[str, object]] | None,
) -> dict[str, object] | None:
    if entries is None:
        return None
    for entry in entries:
        if compile_command_tokens(entry):
            return entry
    return None


def header_include_directive(header_file: str) -> str:
    header_path = Path(header_file)
    if header_path.parts and header_path.parts[0] == "include":
        include_path = Path(*header_path.parts[1:])
        return f"#include <{include_path.as_posix()}>"
    return f'#include "{(ROOT_DIR / header_path).as_posix()}"'


def write_header_smoke_files(header_files: list[str]) -> list[Path]:
    if HEADER_SMOKE_DIR.exists():
        shutil.rmtree(HEADER_SMOKE_DIR)
    HEADER_SMOKE_DIR.mkdir(parents=True)

    smoke_files: list[Path] = []
    for header_file in header_files:
        header_path = Path(header_file)
        smoke_path = HEADER_SMOKE_DIR / header_path.with_suffix(
            header_path.suffix + ".cc"
        )
        smoke_path.parent.mkdir(parents=True, exist_ok=True)
        smoke_path.write_text(
            "// Generated by scripts/quality.py for clang-tidy header checks.\n"
            f"{header_include_directive(header_file)}\n",
            encoding="utf-8",
        )
        smoke_files.append(smoke_path)

    return smoke_files


def write_header_smoke_compile_database(
    header_files: list[str],
    entries: list[dict[str, object]] | None,
) -> list[Path]:
    smoke_files = write_header_smoke_files(header_files)
    base_entry = first_compile_database_entry(entries)
    directory = compile_command_directory(base_entry)
    smoke_entries = [
        {
            "directory": str(directory),
            "command": shlex.join(smoke_compile_tokens(base_entry, smoke_file)),
            "file": str(smoke_file),
        }
        for smoke_file in smoke_files
    ]
    (HEADER_SMOKE_DIR / "compile_commands.json").write_text(
        json.dumps(smoke_entries, indent=2) + "\n",
        encoding="utf-8",
    )
    return smoke_files


def command_format(args: argparse.Namespace) -> None:
    files = collect_project_files(CXX_SUFFIXES)
    if not files:
        print("No C++ files found.", flush=True)
        return

    action = "Checking format for" if args.check else "Formatting"
    file_word = "file" if len(files) == 1 else "files"
    print(f"{action} {len(files)} C++ {file_word}.", flush=True)

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

    entries = compile_database_entries()
    source_files = compile_database_source_files(entries)
    if source_files is None:
        source_files = collect_project_files(CXX_SOURCE_SUFFIXES)
    header_files = collect_project_files(CXX_HEADER_SUFFIXES)

    if not source_files and not header_files:
        print("No C++ source or header files found.", flush=True)
        return

    if source_files:
        file_word = "file" if len(source_files) == 1 else "files"
        print(
            f"Running clang-tidy on {len(source_files)} C++ source {file_word}.",
            flush=True,
        )
        run_clang_tidy(["clang-tidy", "--quiet", "-p", str(BUILD_DIR), *source_files])
    if header_files:
        smoke_files = write_header_smoke_compile_database(header_files, entries)
        file_word = "unit" if len(smoke_files) == 1 else "units"
        print(
            "Running clang-tidy on "
            f"{len(smoke_files)} C++ header smoke translation {file_word}.",
            flush=True,
        )
        run_clang_tidy(
            [
                "clang-tidy",
                "--quiet",
                "-p",
                str(HEADER_SMOKE_DIR),
                *[str(smoke_file) for smoke_file in smoke_files],
            ],
        )


def command_check(_: argparse.Namespace) -> None:
    command_format(
        argparse.Namespace(
            check=True,
        ),
    )
    command_test(argparse.Namespace())
    command_tidy(argparse.Namespace())


def add_include_examples_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--include-examples",
        action="store_true",
        help=(
            "Deprecated compatibility flag; project-owned C++ files are "
            "checked by default."
        ),
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
