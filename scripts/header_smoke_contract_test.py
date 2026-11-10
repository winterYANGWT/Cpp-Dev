#!/usr/bin/env python3

"""Check that header smoke translation units cover only public headers."""

from __future__ import annotations

import contextlib
import unittest
from pathlib import Path
from unittest import mock

import quality


class HeaderSmokeContractTest(unittest.TestCase):
    def test_public_header_files_selects_include_headers_in_order(self) -> None:
        header_files = [
            "include/mylib/a.h",
            "include/mylib/sub/b.hpp",
            "src/detail.h",
            "test/helper.h",
            "tests/fixture.hpp",
            "examples/demo/include/demo.h",
            "tools/include/x.h",
        ]
        expected = ["include/mylib/a.h", "include/mylib/sub/b.hpp"]

        self.assertEqual(
            quality.public_header_files(header_files),
            expected,
            "public_header_files() should keep only first-level include/ "
            f"headers from {header_files!r}.",
        )

        native_paths = [str(Path(header_file)) for header_file in header_files]
        self.assertEqual(
            quality.public_header_files(native_paths),
            native_paths[:2],
            "public_header_files() should use path parts, not string prefixes, "
            f"for native paths {native_paths!r}.",
        )

    def test_run_quality_tidy_only_smokes_public_headers(self) -> None:
        source_files = [str(Path("src") / "library.cc")]
        source_path = quality.ROOT_DIR / source_files[0]
        entries: list[dict[str, object]] = [
            {
                "directory": str(quality.ROOT_DIR),
                "file": str(source_path),
                "arguments": ["clang++", "-c", str(source_path)],
            }
        ]
        header_files = [
            "include/mylib/a.h",
            "include/mylib/sub/b.hpp",
            "src/detail.h",
            "test/helper.h",
            "tests/fixture.hpp",
            "examples/demo/include/demo.h",
            "tools/include/x.h",
        ]
        clang_tidy_calls: list[list[str]] = []
        smoke_calls: list[tuple[list[str], list[dict[str, object]] | None]] = []
        fake_smoke_paths: list[Path] = []

        def fake_collect(suffixes: tuple[str, ...]) -> list[str]:
            if suffixes == quality.CXX_SOURCE_SUFFIXES:
                return list(source_files)
            if suffixes == quality.CXX_HEADER_SUFFIXES:
                return list(header_files)
            raise AssertionError(f"unexpected suffixes passed to collect: {suffixes!r}")

        def fake_write_header_smoke_database(
            selected_headers: list[str],
            received_entries: list[dict[str, object]] | None,
        ) -> list[Path]:
            smoke_calls.append((list(selected_headers), received_entries))
            fake_smoke_paths[:] = [
                Path("/tmp/header_smoke") / f"unit{index}.cc"
                for index, _ in enumerate(selected_headers)
            ]
            return list(fake_smoke_paths)

        with contextlib.ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(quality, "collect_project_files", fake_collect)
            )
            stack.enter_context(
                mock.patch.object(
                    quality, "compile_database_entries", return_value=entries
                )
            )
            stack.enter_context(
                mock.patch.object(quality, "run_clang_tidy", clang_tidy_calls.append)
            )
            stack.enter_context(
                mock.patch.object(
                    quality,
                    "write_header_smoke_compile_database",
                    fake_write_header_smoke_database,
                )
            )
            quality.run_quality_tidy()

        expected_headers = ["include/mylib/a.h", "include/mylib/sub/b.hpp"]
        self.assertEqual(
            len(smoke_calls),
            1,
            "run_quality_tidy() should build one header smoke database.",
        )
        selected_headers, received_entries = smoke_calls[0]
        self.assertEqual(
            selected_headers,
            expected_headers,
            "header smoke should receive exactly the public headers, got "
            f"{selected_headers!r}.",
        )
        self.assertIs(
            received_entries,
            entries,
            "header smoke should receive the exact compile_database_entries() "
            f"result, got {received_entries!r}.",
        )

        self.assertEqual(
            len(clang_tidy_calls),
            2,
            "run_quality_tidy() should run clang-tidy once for sources and "
            f"once for header smoke, got {clang_tidy_calls!r}.",
        )
        self.assertEqual(
            clang_tidy_calls[0],
            ["clang-tidy", "--quiet", "-p", str(quality.BUILD_DIR), *source_files],
            "the source clang-tidy invocation should keep the original files "
            f"and arguments, got {clang_tidy_calls[0]!r}.",
        )
        self.assertEqual(
            clang_tidy_calls[1],
            [
                "clang-tidy",
                "--quiet",
                "-p",
                str(quality.HEADER_SMOKE_DIR),
                *[str(path) for path in fake_smoke_paths],
            ],
            "the header smoke clang-tidy invocation should use the generated "
            f"smoke files, got {clang_tidy_calls[1]!r}.",
        )

    def test_run_quality_tidy_skips_smoke_without_public_headers(self) -> None:
        source_files = ["src/library.cc"]
        header_files = ["src/detail.h", "test/helper.h"]
        clang_tidy_calls: list[list[str]] = []

        def fake_collect(suffixes: tuple[str, ...]) -> list[str]:
            if suffixes == quality.CXX_SOURCE_SUFFIXES:
                return list(source_files)
            if suffixes == quality.CXX_HEADER_SUFFIXES:
                return list(header_files)
            raise AssertionError(f"unexpected suffixes passed to collect: {suffixes!r}")

        with contextlib.ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(quality, "collect_project_files", fake_collect)
            )
            stack.enter_context(
                mock.patch.object(quality, "compile_database_entries", return_value=None)
            )
            stack.enter_context(
                mock.patch.object(quality, "run_clang_tidy", clang_tidy_calls.append)
            )
            write_smoke = stack.enter_context(
                mock.patch.object(quality, "write_header_smoke_compile_database")
            )
            quality.run_quality_tidy()

        write_smoke.assert_not_called()
        self.assertEqual(
            clang_tidy_calls,
            [
                [
                    "clang-tidy",
                    "--quiet",
                    "-p",
                    str(quality.BUILD_DIR),
                    *source_files,
                ]
            ],
            "without public headers, clang-tidy should only check source files, "
            f"got {clang_tidy_calls!r}.",
        )

    def test_header_include_directive_uses_angle_brackets_with_forward_slashes(
        self,
    ) -> None:
        self.assertEqual(
            quality.header_include_directive("include/mylib/a.h"),
            "#include <mylib/a.h>",
            "a public header should be included relative to include/ with "
            "angle brackets.",
        )
        native_path = str(Path("include/mylib/sub/b.hpp"))
        self.assertEqual(
            quality.header_include_directive(native_path),
            "#include <mylib/sub/b.hpp>",
            "native path separators should not leak into the include directive "
            f"for {native_path!r}.",
        )


if __name__ == "__main__":
    unittest.main()
