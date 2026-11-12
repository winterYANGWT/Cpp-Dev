#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import quality


ROOT_DIR = Path(__file__).resolve().parents[1]
# Must match the binaryDir of the coverage preset in CMakePresets.json.
BUILD_DIR = ROOT_DIR / "build" / "coverage"
REPORT_DIR = ROOT_DIR / "build" / "coverage-report"


class CoverageError(Exception):
    """An error that coverage.py reports as one line, without a traceback."""


def gcov_command(
    compiler_id: str,
    compiler_path: str,
    compiler_version: str,
    search_path: str | None = None,
) -> list[str]:
    """Return the gcov command that matches the configured C++ compiler."""
    compiler = Path(compiler_path)
    if compiler_id not in (
        "GNU",
        "Clang",
        "AppleClang",
    ):
        raise CoverageError(
            "coverage is only supported with GCC and Clang, "
            f"not with {compiler_id} ({compiler_path})"
        )

    major = compiler_version.partition(".")[0]
    searched: list[str] = []

    def which(name: str, path: str | None) -> str | None:
        if name not in searched:
            searched.append(name)
        if path is None:
            return shutil.which(name)
        return shutil.which(name, path=path)

    if compiler_id == "GNU":
        names = [f"gcov-{major}"] if major else []
        names.append("gcov")
        for name in names:
            found = which(name, str(compiler.parent))
            if found:
                return [found]
            found = which(name, search_path)
            if found:
                return [found]
    else:
        # Prefer the llvm-cov next to the real compiler: a symlink such as
        # /usr/bin/clang++ may point into /usr/lib/llvm-21/bin, where the
        # matching llvm-cov lives.
        for directory in (str(compiler.resolve().parent), str(compiler.parent)):
            found = which("llvm-cov", directory)
            if found:
                return [found, "gcov"]
        names = [f"llvm-cov-{major}"] if major else []
        names.append("llvm-cov")
        for name in names:
            found = which(name, search_path)
            if found:
                return [found, "gcov"]

    raise CoverageError(
        "could not find a gcov tool; looked for "
        + ", ".join(searched)
        + ". Use --gcov-executable to specify one, for example: "
        '--gcov-executable "xcrun llvm-cov gcov"'
    )


def gcov_executable_string(gcov_tool: list[str]) -> str:
    """Join a gcov command so that gcovr splits it back into the same words."""
    # gcovr 8.8 parses --gcov-executable with shlex.split (GcovProgram.__init__
    # in gcovr/formats/gcov/read.py), so shlex.join is the inverse operation.
    return shlex.join(gcov_tool)


def gcovr_command(gcov_executable: str) -> list[str]:
    """Return the gcovr command for the coverage report."""
    return [
        "gcovr",
        "--root",
        str(ROOT_DIR),
        "--filter",
        "src/",
        "--filter",
        "include/",
        "--gcov-executable",
        gcov_executable,
        "--exclude-throw-branches",
        "--exclude-unreachable-branches",
        "--print-summary",
        "--txt",
        str(REPORT_DIR / "coverage.txt"),
        "--html-details",
        str(REPORT_DIR / "coverage.html"),
        str(BUILD_DIR),
    ]


def register_file_api_query(build_dir: Path) -> None:
    query_dir = build_dir / ".cmake" / "api" / "v1" / "query"
    query_dir.mkdir(parents=True, exist_ok=True)
    (query_dir / "toolchains-v1").touch()


def cxx_compiler_from_file_api(build_dir: Path) -> dict[str, str]:
    """Read the C++ compiler description from the CMake File API reply."""
    reply_dir = build_dir / ".cmake" / "api" / "v1" / "reply"
    indexes = list(reply_dir.glob("index-*.json"))
    if not indexes:
        raise CoverageError(
            "CMake did not write a File API index in "
            f"{reply_dir}; remove {build_dir} and try again"
        )
    index_path = max(indexes, key=lambda path: path.stat().st_mtime_ns)

    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise CoverageError(f"could not read {index_path}: {error}") from error

    objects = index.get("objects")
    if not isinstance(objects, list):
        objects = []
    for entry in objects:
        if not isinstance(entry, dict) or entry.get("kind") != "toolchains":
            continue
        json_file = entry.get("jsonFile")
        if not isinstance(json_file, str):
            continue
        toolchains_path = index_path.parent / json_file
        try:
            reply = json.loads(toolchains_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise CoverageError(
                f"could not read {toolchains_path}: {error}"
            ) from error

        toolchains = reply.get("toolchains")
        if not isinstance(toolchains, list):
            continue
        for toolchain in toolchains:
            if not isinstance(toolchain, dict) or toolchain.get("language") != "CXX":
                continue
            compiler = toolchain.get("compiler")
            if not isinstance(compiler, dict):
                continue
            compiler_id = compiler.get("id")
            compiler_path = compiler.get("path")
            compiler_version = compiler.get("version")
            if (
                isinstance(compiler_id, str)
                and isinstance(compiler_path, str)
                and isinstance(compiler_version, str)
            ):
                return {
                    "id": compiler_id,
                    "path": compiler_path,
                    "version": compiler_version,
                }

    raise CoverageError(
        f"CMake did not report a C++ compiler in {reply_dir}"
    )


def remove_gcda_files(build_dir: Path) -> None:
    """Remove counters left by earlier runs and by test discovery at build time."""
    for path in build_dir.rglob("*.gcda"):
        path.unlink()


def run_coverage(gcov_executable: str | None) -> None:
    # Report a missing gcovr before spending time on the build.
    if shutil.which("gcovr") is None:
        raise quality.ToolNotFoundError("gcovr")
    # The File API query must exist before CMake configures the build.
    register_file_api_query(BUILD_DIR)
    quality.run(
        ["cmake", "--preset", "coverage", *quality.cmake_configure_args()]
    )

    if gcov_executable is None:
        compiler = cxx_compiler_from_file_api(BUILD_DIR)
        gcov_executable = gcov_executable_string(
            gcov_command(
                compiler["id"],
                compiler["path"],
                compiler["version"],
            )
        )

    quality.run(["cmake", "--build", "--preset", "coverage"])
    # The build runs the test executable to discover tests, so its counters
    # must be removed before the real test run.
    remove_gcda_files(BUILD_DIR)
    quality.run(["ctest", "--preset", "coverage"])

    if REPORT_DIR.exists():
        shutil.rmtree(REPORT_DIR)
    REPORT_DIR.mkdir(parents=True)
    quality.run(gcovr_command(gcov_executable))

    print(f"Coverage text report: {REPORT_DIR / 'coverage.txt'}")
    print(f"Coverage HTML report: {REPORT_DIR / 'coverage.html'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build and test the coverage preset, then write a gcovr report."
    )
    parser.add_argument(
        "--gcov-executable",
        metavar="CMD",
        help=(
            "gcov command to use, for example "
            '"llvm-cov gcov" or "xcrun llvm-cov gcov".'
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        run_coverage(args.gcov_executable)
    except quality.ToolNotFoundError as error:
        print(
            f"error: {error.tool} was not found on PATH. "
            "Install the recommended tools (see docs/tool-versions.md) and check "
            "them with: python3 scripts/tool_versions.py",
            file=sys.stderr,
        )
        return 1
    except CoverageError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        return error.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
