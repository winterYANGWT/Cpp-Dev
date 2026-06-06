#!/usr/bin/env python3

from __future__ import annotations

import argparse
import ctypes
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT_DIR / "build" / "quality"
HEADER_SMOKE_DIR = BUILD_DIR / "header_smoke"
CXX_HEADER_SUFFIXES = (".h", ".hh", ".hpp", ".hxx")
CXX_SOURCE_SUFFIXES = (".cc", ".cpp", ".cxx")
CXX_SUFFIXES = (*CXX_HEADER_SUFFIXES, *CXX_SOURCE_SUFFIXES)
STRICT_CXX20_FLAGS = {"-std=c++20", "-std:c++20", "/std:c++20"}
CMAKE_CONFIGURE_ARGS_ENV = "CPP_DEV_CMAKE_CONFIGURE_ARGS"
MACOS_SDKROOT_ENV = "SDKROOT"
OUTPUT_OPTIONS_WITH_VALUE = {"-o", "-MF", "-MT", "-MQ", "-MJ", "/Fo", "/Fd"}
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


def macos_sdkroot() -> str | None:
    if sys.platform != "darwin":
        return None

    sdkroot = os.environ.get(MACOS_SDKROOT_ENV, "").strip()
    if sdkroot:
        return sdkroot

    xcrun = shutil.which("xcrun")
    if xcrun is None:
        return None

    result = subprocess.run(
        [xcrun, "--sdk", "macosx", "--show-sdk-path"],
        cwd=ROOT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None

    sdkroot = result.stdout.strip()
    return sdkroot if sdkroot else None


def command_environment() -> dict[str, str]:
    env = os.environ.copy()
    sdkroot = macos_sdkroot()
    if sdkroot and not env.get(MACOS_SDKROOT_ENV):
        env[MACOS_SDKROOT_ENV] = sdkroot
    return env


def run(command: list[str]) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT_DIR, env=command_environment(), check=True)


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
        env=command_environment(),
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


def compile_database_cpp_entries(
    entries: list[dict[str, object]] | None,
) -> list[tuple[Path, list[str]]]:
    if entries is None:
        return []

    compile_entries: list[tuple[Path, list[str]]] = []
    for entry in entries:
        file = compile_command_file(entry)
        tokens = compile_command_tokens(entry)
        if file is None or tokens is None or file.suffix not in CXX_SOURCE_SUFFIXES:
            continue
        if not is_project_owned_file(file):
            continue
        compile_entries.append((file, tokens))
    return compile_entries


def describe_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def verify_standard_cpp() -> None:
    entries = compile_database_entries()
    compile_entries = compile_database_cpp_entries(entries)
    if not compile_entries:
        print("No C++ compile commands found; skipping standard check.", flush=True)
        return

    extension_entries: list[str] = []
    missing_standard_entries: list[str] = []
    for file, tokens in compile_entries:
        if any(token.startswith("-std=gnu++") for token in tokens):
            extension_entries.append(describe_path(file))
        if not any(token in STRICT_CXX20_FLAGS for token in tokens):
            missing_standard_entries.append(describe_path(file))

    if extension_entries:
        raise SystemExit(
            "GNU C++ extension mode is not allowed. Offending files:\n"
            + "\n".join(f"  {path}" for path in extension_entries)
        )
    if missing_standard_entries:
        raise SystemExit(
            "Expected strict C++20 compile flags. Missing for files:\n"
            + "\n".join(f"  {path}" for path in missing_standard_entries)
        )

    print("Strict C++20 compile mode verified.", flush=True)


def windows_command_line_tokens(command: str) -> list[str] | None:
    if os.name != "nt":
        return None

    try:
        argc = ctypes.c_int()
        shell32 = ctypes.windll.shell32
        shell32.CommandLineToArgvW.argtypes = [
            ctypes.c_wchar_p,
            ctypes.POINTER(ctypes.c_int),
        ]
        shell32.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
        kernel32 = ctypes.windll.kernel32
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        argv = shell32.CommandLineToArgvW(command, ctypes.byref(argc))
        if not argv:
            return None
        try:
            return [argv[index] for index in range(argc.value)]
        finally:
            kernel32.LocalFree(ctypes.cast(argv, ctypes.c_void_p))
    except (AttributeError, OSError, ValueError):
        return None


def compile_command_tokens(entry: dict[str, object]) -> list[str] | None:
    arguments = entry.get("arguments")
    if isinstance(arguments, list):
        return [str(argument) for argument in arguments]

    command = entry.get("command")
    if isinstance(command, str):
        windows_tokens = windows_command_line_tokens(command)
        if windows_tokens is not None:
            return windows_tokens
        return shlex.split(command, posix=os.name != "nt")

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
        if token.startswith("/Fd") and token != "/Fd":
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
            "arguments": smoke_compile_tokens(base_entry, smoke_file),
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


def has_cmake_cache_arg(args: list[str], name: str) -> bool:
    return any(
        arg == f"-D{name}"
        or arg.startswith(f"-D{name}=")
        or arg.startswith(f"-D{name}:")
        for arg in args
    )


def cmake_configure_command() -> list[str]:
    extra_args = os.environ.get(CMAKE_CONFIGURE_ARGS_ENV, "").strip()
    configure_args = shlex.split(extra_args, posix=os.name != "nt") if extra_args else []
    sdkroot = macos_sdkroot()
    if sdkroot and not has_cmake_cache_arg(configure_args, "CMAKE_OSX_SYSROOT"):
        configure_args.append(f"-DCMAKE_OSX_SYSROOT={sdkroot}")
    return ["cmake", "--preset", "quality", *configure_args]


def configure_quality_build() -> None:
    run(cmake_configure_command())
    verify_standard_cpp()


def run_quality_tests() -> None:
    run(["cmake", "--build", "--preset", "quality"])
    run(["ctest", "--preset", "quality"])


def run_quality_tidy() -> None:
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


def command_test(_: argparse.Namespace) -> None:
    configure_quality_build()
    run_quality_tests()


def command_tidy(_: argparse.Namespace) -> None:
    configure_quality_build()
    run_quality_tidy()


def command_check(_: argparse.Namespace) -> None:
    command_format(
        argparse.Namespace(
            check=True,
        ),
    )
    configure_quality_build()
    run_quality_tests()
    run_quality_tidy()


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
