#!/usr/bin/env python3

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
OPTIONS_MODULE = ROOT_DIR / "cmake" / "project_nameOptions.cmake"
COMPILER_MODULE = ROOT_DIR / "cmake" / "project_nameCompiler.cmake"
CI_WORKFLOW = ROOT_DIR / ".github" / "workflows" / "ci.yml"
EXAMPLE_LISTS = ROOT_DIR / "examples" / "universe_answer" / "CMakeLists.txt"
CONFIGURE_FUNCTIONS = (
    "project_name_configure_cxx_target",
    "project_name_configure_cxx_interface_target",
)
BUILD_INTERFACE_RE = re.compile(r"^\$<BUILD_INTERFACE:(.*)>$")

# Compiler variables as CMake sets them for each compiler.
GNU_STYLE_COMPILERS = {
    "GCC": {
        "CMAKE_CXX_COMPILER_ID": "GNU",
        "CMAKE_CXX_COMPILER_FRONTEND_VARIANT": "GNU",
    },
    "Clang": {
        "CMAKE_CXX_COMPILER_ID": "Clang",
        "CMAKE_CXX_COMPILER_FRONTEND_VARIANT": "GNU",
    },
    "AppleClang": {
        "CMAKE_CXX_COMPILER_ID": "AppleClang",
        "CMAKE_CXX_COMPILER_FRONTEND_VARIANT": "GNU",
    },
    # clang++ targeting the MSVC ABI simulates MSVC but takes GNU-style options.
    "clang++ for the MSVC ABI": {
        "CMAKE_CXX_COMPILER_ID": "Clang",
        "CMAKE_CXX_COMPILER_FRONTEND_VARIANT": "GNU",
        "CMAKE_CXX_SIMULATE_ID": "MSVC",
    },
}
MSVC_STYLE_COMPILERS = {
    "MSVC": {
        "CMAKE_CXX_COMPILER_ID": "MSVC",
        "CMAKE_CXX_COMPILER_FRONTEND_VARIANT": "MSVC",
    },
    # CMake before 3.26 leaves the frontend variant empty for MSVC.
    "MSVC with CMake before 3.26": {
        "CMAKE_CXX_COMPILER_ID": "MSVC",
        "CMAKE_CXX_COMPILER_FRONTEND_VARIANT": "",
    },
    "clang-cl": {
        "CMAKE_CXX_COMPILER_ID": "Clang",
        "CMAKE_CXX_COMPILER_FRONTEND_VARIANT": "MSVC",
        "CMAKE_CXX_SIMULATE_ID": "MSVC",
    },
}

# Target commands are not available in CMake script mode, so the probe defines
# stand-ins that record each call as one line of PROBE_OUTPUT. With
# PROBE_EXAMPLE_LISTS set, it runs the example's CMakeLists.txt instead of a
# configure function.
PROBE_SCRIPT = r"""
function(record_call command)
  string(JOIN " " args ${ARGN})
  file(APPEND "${PROBE_OUTPUT}" "${command} ${args}\n")
endfunction()

function(set_target_properties)
  record_call(set_target_properties ${ARGN})
endfunction()

function(target_compile_features)
  record_call(target_compile_features ${ARGN})
endfunction()

function(target_compile_options)
  record_call(target_compile_options ${ARGN})
endfunction()

function(target_link_options)
  record_call(target_link_options ${ARGN})
endfunction()

# Other commands that the example calls; the probe does not check them.
foreach(command IN ITEMS
    project find_package add_executable target_link_libraries
    add_custom_command enable_testing add_test set_tests_properties)
  cmake_language(EVAL CODE "function(${command})\nendfunction()")
endforeach()

file(WRITE "${PROBE_OUTPUT}" "")
if(DEFINED PROBE_EXAMPLE_LISTS)
  include("${PROBE_EXAMPLE_LISTS}")
else()
  set(PROJECT_NAME project_name)
  set(PROJECT_IS_TOP_LEVEL ON)
  include("${OPTIONS_MODULE}")
  include("${COMPILER_MODULE}")
  cmake_language(CALL "${PROBE_FUNCTION}" probe_target)
endif()
"""


class ProbeResult:
    def __init__(self, returncode: int, output: str, stderr: str) -> None:
        self.returncode = returncode
        # CMake wraps messages at about 80 columns; join the lines again.
        self.stderr = " ".join(stderr.split())
        self.compile_options: list[str] = []
        self.link_options: list[str] = []
        for line in output.splitlines():
            command, _, args = line.partition(" ")
            # Drop the target name and the PRIVATE or INTERFACE keyword.
            values = [unwrap_build_interface(arg) for arg in args.split()[2:]]
            if command == "target_compile_options":
                self.compile_options.extend(values)
            elif command == "target_link_options":
                self.link_options.extend(values)


def unwrap_build_interface(option: str) -> str:
    match = BUILD_INTERFACE_RE.match(option)
    return match.group(1) if match else option


@unittest.skipIf(shutil.which("cmake") is None, "cmake is not installed")
class CompilerOptionsContractTest(unittest.TestCase):
    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.temp_dir = Path(temp_dir.name)
        self.probe_script = self.temp_dir / "probe.cmake"
        self.probe_script.write_text(PROBE_SCRIPT, encoding="utf-8")

    def probe(
        self,
        function: str,
        compiler: dict[str, str],
        **options: str,
    ) -> ProbeResult:
        return self.run_probe(
            {
                "PROBE_FUNCTION": function,
                "OPTIONS_MODULE": OPTIONS_MODULE.as_posix(),
                "COMPILER_MODULE": COMPILER_MODULE.as_posix(),
                "project_name_WARNINGS_AS_ERRORS": "ON",
                **compiler,
                **{f"project_name_{name}": value for name, value in options.items()},
            }
        )

    def probe_example(
        self, compiler: dict[str, str], warnings_as_errors: str
    ) -> ProbeResult:
        return self.run_probe(
            {
                "PROBE_EXAMPLE_LISTS": EXAMPLE_LISTS.as_posix(),
                "universe_answer_WARNINGS_AS_ERRORS": warnings_as_errors,
                **compiler,
            }
        )

    def run_probe(self, variables: dict[str, str]) -> ProbeResult:
        output_file = self.temp_dir / "calls.txt"
        output_file.unlink(missing_ok=True)
        variables = {"PROBE_OUTPUT": output_file.as_posix(), **variables}
        result = subprocess.run(
            [
                "cmake",
                *[f"-D{name}={value}" for name, value in variables.items()],
                "-P",
                str(self.probe_script),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        output = ""
        if output_file.exists():
            output = output_file.read_text(encoding="utf-8")
        return ProbeResult(result.returncode, output, result.stderr)

    def test_gnu_style_compilers_get_gnu_style_options(self) -> None:
        for compiler_name, compiler in GNU_STYLE_COMPILERS.items():
            for function in CONFIGURE_FUNCTIONS:
                with self.subTest(compiler=compiler_name, function=function):
                    result = self.probe(function, compiler)

                    self.assertEqual(result.returncode, 0, result.stderr)
                    for option in ("-Wall", "-Wextra", "-Wpedantic", "-Werror"):
                        self.assertIn(option, result.compile_options)
                    options = result.compile_options
                    msvc_options = [value for value in options if value.startswith("/")]
                    self.assertFalse(
                        msvc_options,
                        "GNU-style compilers must not get MSVC-style options.",
                    )
                    if function.endswith("_interface_target"):
                        self.assertIn("-std=c++20", result.compile_options)

    def test_msvc_style_compilers_get_msvc_style_options(self) -> None:
        for compiler_name, compiler in MSVC_STYLE_COMPILERS.items():
            for function in CONFIGURE_FUNCTIONS:
                with self.subTest(compiler=compiler_name, function=function):
                    result = self.probe(function, compiler)

                    self.assertEqual(result.returncode, 0, result.stderr)
                    for option in ("/W4", "/permissive-", "/WX"):
                        self.assertIn(option, result.compile_options)
                    # clang-cl reads -Wall as -Weverything, so no GNU-style
                    # option may reach an MSVC-style compiler.
                    options = result.compile_options
                    gnu_options = [value for value in options if value.startswith("-")]
                    self.assertFalse(
                        gnu_options,
                        "MSVC-style compilers must not get GNU-style options.",
                    )
                    if function.endswith("_interface_target"):
                        self.assertIn("/std:c++20", result.compile_options)

    def test_sanitizers_apply_to_gnu_style_compilers(self) -> None:
        cases = {
            "ENABLE_SANITIZERS": "-fsanitize=address,undefined",
            "ENABLE_THREAD_SANITIZER": "-fsanitize=thread",
        }
        for option, flag in cases.items():
            for compiler_name, compiler in GNU_STYLE_COMPILERS.items():
                for function in CONFIGURE_FUNCTIONS:
                    with self.subTest(
                        option=option, compiler=compiler_name, function=function
                    ):
                        result = self.probe(function, compiler, **{option: "ON"})

                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertIn(flag, result.compile_options)
                        self.assertIn("-fno-omit-frame-pointer", result.compile_options)
                        self.assertIn(flag, result.link_options)

    def test_sanitizers_warn_for_msvc_style_compilers(self) -> None:
        for option in ("ENABLE_SANITIZERS", "ENABLE_THREAD_SANITIZER"):
            for compiler_name, compiler in MSVC_STYLE_COMPILERS.items():
                for function in CONFIGURE_FUNCTIONS:
                    with self.subTest(
                        option=option, compiler=compiler_name, function=function
                    ):
                        result = self.probe(function, compiler, **{option: "ON"})
                        options = (*result.compile_options, *result.link_options)
                        sanitizer_options = [
                            value for value in options if value.startswith("-fsanitize")
                        ]

                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertFalse(sanitizer_options)
                        self.assertIn(
                            f"project_name_{option} is only supported",
                            result.stderr,
                        )

    def test_thread_sanitizer_cannot_be_combined_with_address_sanitizer(self) -> None:
        result = self.probe(
            CONFIGURE_FUNCTIONS[0],
            GNU_STYLE_COMPILERS["GCC"],
            ENABLE_SANITIZERS="ON",
            ENABLE_THREAD_SANITIZER="ON",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot both be ON", result.stderr)

    def test_example_gets_the_library_warning_options(self) -> None:
        # The example cannot use the library's CMake modules, so it repeats
        # their warning options for each compiler.
        compilers = {**GNU_STYLE_COMPILERS, **MSVC_STYLE_COMPILERS}
        for compiler_name, compiler in compilers.items():
            for warnings_as_errors in ("ON", "OFF"):
                with self.subTest(
                    compiler=compiler_name, warnings_as_errors=warnings_as_errors
                ):
                    library = self.probe(
                        CONFIGURE_FUNCTIONS[0],
                        compiler,
                        WARNINGS_AS_ERRORS=warnings_as_errors,
                    )
                    example = self.probe_example(compiler, warnings_as_errors)

                    self.assertEqual(example.returncode, 0, example.stderr)
                    self.assertTrue(example.compile_options)
                    self.assertEqual(example.compile_options, library.compile_options)

    def test_coverage_applies_to_gnu_style_compilers(self) -> None:
        for compiler_name, compiler in GNU_STYLE_COMPILERS.items():
            for function in CONFIGURE_FUNCTIONS:
                with self.subTest(compiler=compiler_name, function=function):
                    result = self.probe(function, compiler, ENABLE_COVERAGE="ON")

                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("--coverage", result.compile_options)
                    self.assertIn("-O0", result.compile_options)
                    self.assertIn("--coverage", result.link_options)

    def test_coverage_warns_for_msvc_style_compilers(self) -> None:
        for compiler_name, compiler in MSVC_STYLE_COMPILERS.items():
            for function in CONFIGURE_FUNCTIONS:
                with self.subTest(compiler=compiler_name, function=function):
                    result = self.probe(function, compiler, ENABLE_COVERAGE="ON")
                    options = (*result.compile_options, *result.link_options)

                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertNotIn("--coverage", options)
                    self.assertNotIn("-O0", options)
                    self.assertIn(
                        "project_name_ENABLE_COVERAGE is only supported",
                        result.stderr,
                    )

    def test_coverage_is_disabled_by_default(self) -> None:
        compilers = {**GNU_STYLE_COMPILERS, **MSVC_STYLE_COMPILERS}
        for compiler_name, compiler in compilers.items():
            for function in CONFIGURE_FUNCTIONS:
                with self.subTest(compiler=compiler_name, function=function):
                    result = self.probe(function, compiler)

                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertNotIn("--coverage", result.compile_options)
                    self.assertNotIn("--coverage", result.link_options)

    def test_windows_ci_builds_with_clang_cl(self) -> None:
        workflow = CI_WORKFLOW.read_text(encoding="utf-8")

        self.assertRegex(
            workflow,
            r"- os: windows-\S+\s+shared: OFF\s+compiler: clang-cl",
        )
        self.assertRegex(
            workflow,
            r"- os: windows-\S+\s+shared: ON\s+compiler: clang-cl",
        )


if __name__ == "__main__":
    unittest.main()
