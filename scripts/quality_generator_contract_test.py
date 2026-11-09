#!/usr/bin/env python3

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import quality


ROOT_DIR = Path(__file__).resolve().parents[1]
PRESETS_FILE = ROOT_DIR / "CMakePresets.json"
# A generator that does not write compile_commands.json.
VISUAL_STUDIO_GENERATOR = "Visual Studio 17 2022"


def quality_preset(presets: dict[str, object], kind: str) -> dict[str, object]:
    return next(preset for preset in presets[kind] if preset["name"] == "quality")


def option_value(command: list[str], option: str) -> str | None:
    if option not in command:
        return None
    index = command.index(option)
    return command[index + 1] if index + 1 < len(command) else None


class QualityGeneratorContractTest(unittest.TestCase):
    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.build_dir = Path(temp_dir.name) / "quality"
        package_dir = self.build_dir / "package"
        self.commands: list[list[str]] = []

        # Record commands instead of running them, and keep every path that
        # quality.py writes to inside the temporary directory.
        patches = [
            mock.patch.object(quality, "BUILD_DIR", self.build_dir),
            mock.patch.object(quality, "PACKAGE_TEST_DIR", package_dir),
            mock.patch.object(quality, "PACKAGE_INSTALL_DIR", package_dir / "install"),
            mock.patch.object(
                quality,
                "PACKAGE_EXAMPLE_BUILD_DIR",
                package_dir / "universe_answer",
            ),
            mock.patch.object(quality, "run", self.commands.append),
            mock.patch.object(quality, "macos_sdkroot", lambda: None),
            mock.patch.dict(os.environ, {quality.CMAKE_CONFIGURE_ARGS_ENV: ""}),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def write_cmake_cache(self, generator: str) -> None:
        self.build_dir.mkdir(parents=True, exist_ok=True)
        (self.build_dir / "CMakeCache.txt").write_text(
            f"CMAKE_GENERATOR:INTERNAL={generator}\n",
            encoding="utf-8",
        )

    def test_quality_configuration_matches_presets(self) -> None:
        presets = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
        configuration = quality.QUALITY_CONFIGURATION

        self.assertEqual(
            quality_preset(presets, "configurePresets")["cacheVariables"][
                "CMAKE_BUILD_TYPE"
            ],
            configuration,
        )
        self.assertEqual(
            quality_preset(presets, "buildPresets")["configuration"],
            configuration,
        )
        self.assertEqual(
            quality_preset(presets, "testPresets")["configuration"],
            configuration,
        )

    def test_package_steps_use_quality_configuration(self) -> None:
        quality.run_package_consumer_test()
        install, configure, build, test = self.commands
        configuration = quality.QUALITY_CONFIGURATION

        self.assertIn("--install", install)
        self.assertEqual(option_value(install, "--config"), configuration)
        self.assertIn(f"-DCMAKE_BUILD_TYPE={configuration}", configure)
        self.assertEqual(option_value(build, "--config"), configuration)
        self.assertEqual(option_value(test, "--build-config"), configuration)

    def test_example_configure_inherits_library_configure_args(self) -> None:
        os.environ[quality.CMAKE_CONFIGURE_ARGS_ENV] = (
            "-G Ninja -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_PREFIX_PATH=/deps"
        )
        with mock.patch.object(quality, "macos_sdkroot", lambda: "/sdk"):
            library_args = quality.cmake_configure_args()
            example = quality.package_example_configure_command()

        for arg in library_args:
            if not arg.startswith("-DCMAKE_PREFIX_PATH="):
                with self.subTest(arg=arg):
                    self.assertIn(arg, example)
        self.assertIn("-DCMAKE_OSX_SYSROOT=/sdk", example)
        self.assertEqual(
            [arg for arg in example if arg.startswith("-DCMAKE_PREFIX_PATH")],
            [f"-DCMAKE_PREFIX_PATH={quality.PACKAGE_INSTALL_DIR};/deps"],
        )

    def test_example_configure_exports_compile_commands_with_warnings_as_errors(
        self,
    ) -> None:
        os.environ[quality.CMAKE_CONFIGURE_ARGS_ENV] = (
            "-DCMAKE_EXPORT_COMPILE_COMMANDS=OFF "
            f"-D{quality.PACKAGE_EXAMPLE_WARNINGS_AS_ERRORS}=OFF"
        )
        example = quality.package_example_configure_command()

        # The last -D for a variable wins, so these must follow the forwarded
        # arguments.
        for name in (
            "CMAKE_EXPORT_COMPILE_COMMANDS",
            quality.PACKAGE_EXAMPLE_WARNINGS_AS_ERRORS,
        ):
            with self.subTest(name=name):
                values = [arg for arg in example if arg.startswith(f"-D{name}=")]
                self.assertEqual(values[-1], f"-D{name}=ON")
        self.assertIn(
            f"option({quality.PACKAGE_EXAMPLE_WARNINGS_AS_ERRORS} ",
            (quality.PACKAGE_EXAMPLE_SOURCE_DIR / "CMakeLists.txt").read_text(
                encoding="utf-8"
            ),
        )

    def test_check_runs_clang_tidy_on_the_package_example(self) -> None:
        steps: list[str] = []
        step_names = (
            "command_format",
            "configure_quality_build",
            "run_quality_tests",
            "run_package_consumer_test",
            "run_quality_tidy",
            "run_package_example_tidy",
        )
        with contextlib.ExitStack() as stack:
            for name in step_names:
                stack.enter_context(
                    mock.patch.object(
                        quality,
                        name,
                        lambda *_, name=name, **__: steps.append(name),
                    )
                )
            quality.command_check(argparse.Namespace())

        # clang-tidy reads the example's compile database, which the package
        # consumer check writes.
        self.assertEqual(steps, list(step_names))

    def test_example_tidy_uses_the_example_compile_database(self) -> None:
        main_file = quality.PACKAGE_EXAMPLE_SOURCE_DIR / "src" / "main.cc"
        quality.PACKAGE_EXAMPLE_BUILD_DIR.mkdir(parents=True)
        (quality.PACKAGE_EXAMPLE_BUILD_DIR / "compile_commands.json").write_text(
            json.dumps(
                [
                    {
                        "directory": str(quality.PACKAGE_EXAMPLE_BUILD_DIR),
                        "command": f"c++ -std=c++20 -c {main_file}",
                        "file": str(main_file),
                    }
                ]
            ),
            encoding="utf-8",
        )
        tidy_commands: list[list[str]] = []

        with mock.patch.object(quality, "run_clang_tidy", tidy_commands.append):
            with contextlib.redirect_stdout(io.StringIO()):
                quality.run_package_example_tidy()

        self.assertEqual(len(tidy_commands), 1)
        command = tidy_commands[0]
        self.assertEqual(
            option_value(command, "-p"), str(quality.PACKAGE_EXAMPLE_BUILD_DIR)
        )
        self.assertIn(str(main_file.relative_to(ROOT_DIR)), command)

    def test_example_tidy_fails_without_example_compile_database(self) -> None:
        with mock.patch.object(quality, "run_clang_tidy") as run_clang_tidy:
            with self.assertRaises(SystemExit):
                quality.run_package_example_tidy()

        run_clang_tidy.assert_not_called()

    def test_test_and_package_warn_without_compile_database(self) -> None:
        self.write_cmake_cache(VISUAL_STUDIO_GENERATOR)

        for command in (quality.command_test, quality.command_package):
            with self.subTest(command=command.__name__):
                self.commands.clear()
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    command(argparse.Namespace())

                self.assertIn(
                    "Warning: skipping the strict C++20 check",
                    output.getvalue(),
                )
                self.assertIn(VISUAL_STUDIO_GENERATOR, output.getvalue())
                self.assertIn(
                    ["cmake", "--build", "--preset", "quality"],
                    self.commands,
                )

    def test_tidy_and_check_fail_before_building_without_compile_database(
        self,
    ) -> None:
        self.write_cmake_cache(VISUAL_STUDIO_GENERATOR)

        with mock.patch.object(quality, "command_format", lambda _: None):
            for command in (quality.command_tidy, quality.command_check):
                with self.subTest(command=command.__name__):
                    self.commands.clear()
                    with self.assertRaises(SystemExit) as raised:
                        command(argparse.Namespace())

                    message = str(raised.exception)
                    self.assertIn(VISUAL_STUDIO_GENERATOR, message)
                    self.assertIn('"-G Ninja"', message)
                    self.assertEqual(
                        self.commands,
                        [quality.cmake_configure_command()],
                    )


if __name__ == "__main__":
    unittest.main()
