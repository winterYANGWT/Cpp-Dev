# Scripts

This directory contains project maintenance scripts for the CPP-DEV template.

## `quality.py`

`quality.py` is the local quality gate used by this repository. Run commands from the repository root.

```sh
python3 scripts/quality.py format
python3 scripts/quality.py format --check
python3 scripts/quality.py tidy
python3 scripts/quality.py test
python3 scripts/quality.py package
python3 scripts/quality.py check
```

Use `python` instead of `python3` on platforms where that is the Python 3 executable.

### Commands

- `format` formats project-owned C++ headers and sources with `clang-format`.
- `format --check` verifies formatting without rewriting files.
- `tidy` configures the `quality` CMake preset and runs `clang-tidy` on the library. It does not check the example, which needs the installed package; `check` does.
- `test` configures, builds, and runs CTest through the `quality` preset.
- `package` installs the quality build to a temporary prefix, builds the `examples/universe_answer` downstream project against that installed package, and runs the example CTest suite.
- `check` runs `format --check`, configures once, then runs tests, the package consumer check, and `clang-tidy` on the library and the example.

### CMake Configuration Overrides

Set `CPP_DEV_CMAKE_CONFIGURE_ARGS` to append CMake configure arguments to `cmake --preset quality`.
This is intended for CI and one-off verification of build variants.

```sh
CPP_DEV_CMAKE_CONFIGURE_ARGS="-DBUILD_SHARED_LIBS=ON" python3 scripts/quality.py check
```

`quality.py` reads `build/quality/compile_commands.json` for the strict C++20 check and for `clang-tidy`. Ninja and Makefile generators write it; Visual Studio and Xcode generators do not. Without it, `test` and `package` print a warning and skip the strict C++20 check, while `tidy` and `check` stop right after configuring. Add `-G Ninja` to `CPP_DEV_CMAKE_CONFIGURE_ARGS` to use Ninja, and remove `build/quality` when switching generators.

On macOS, `quality.py` automatically passes the active macOS SDK as `CMAKE_OSX_SYSROOT` when `xcrun` is available. You can set `SDKROOT` yourself to pin the SDK used by CMake and `clang-tidy`:

```sh
export SDKROOT="$(xcrun --sdk macosx --show-sdk-path)"
```

On Windows with vcpkg-provided GTest, run from an MSVC environment and pin CMake to `cl`:

```powershell
$env:CC = "cl"
$env:CXX = "cl"
$env:CPP_DEV_CMAKE_CONFIGURE_ARGS = "-G Ninja -DCMAKE_C_COMPILER=cl -DCMAKE_CXX_COMPILER=cl -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake -DVCPKG_TARGET_TRIPLET=x64-windows"
python scripts/quality.py check
```

To check the clang-cl build, replace `cl` with `clang-cl` in `CC`, `CXX`, and the compiler arguments. CI runs both compilers on Windows.

The template does not fetch GoogleTest automatically. If `find_package(GTest CONFIG)` fails, install GoogleTest with your preferred package manager or build it yourself, then rerun CMake with `CMAKE_PREFIX_PATH` or `GTest_DIR` pointing at the package config location.

### Package Consumer Check

`quality.py package` verifies the installed CMake package contract. It installs
the `Debug` configuration of the current quality build under
`build/quality/package/install`, configures `examples/universe_answer` with that
prefix, builds the downstream `universe_answer_cli` executable, then runs CTest
for the example project.

The example is configured with the same `CPP_DEV_CMAKE_CONFIGURE_ARGS` and macOS
SDK as the library, so both use the same generator, compiler, and toolchain. A
`CMAKE_PREFIX_PATH` in those arguments is appended after the install prefix.

The package step also turns on `universe_answer_WARNINGS_AS_ERRORS` and
`CMAKE_EXPORT_COMPILE_COMMANDS` for the example, overriding any values in
`CPP_DEV_CMAKE_CONFIGURE_ARGS`. Compiler warnings in the example fail the build,
and `check` then runs `clang-tidy` on the example's sources with the example's
own compile database.

### File Scope

The script walks the whole repository and includes project-owned C++ files with these suffixes:

- Headers: `.h`, `.hh`, `.hpp`, `.hxx`
- Sources: `.cc`, `.cpp`, `.cxx`

It skips common build, dependency, generated, and vendor directories such as `build/`, `out/`, `external/`, `third_party/`, and `vendor/`.

### `clang-tidy` Header Checks

`tidy` uses two inputs:

- Real source translation units from `build/quality/compile_commands.json`.
- Generated header smoke translation units under `build/quality/header_smoke/`, one for each public header under `include/`.

Each header smoke file contains a single `#include` for one public header. The script also writes a temporary compile database for these generated `.cc` files, reusing the compile flags of the first entry in the real CMake compile database, usually a library source. This checks public headers that no source in the repository includes, and checks that each one can be parsed on its own as part of a normal C++ translation unit, instead of asking `clang-tidy` to analyze `.h` files directly.

Private headers under `src/` and helper headers under `test/` get no smoke translation unit. `clang-tidy` checks them while it checks the sources that include them, with those sources' own compile flags, so a test header can use definitions and include paths that only the test target has. A private or test header that no source includes is not checked.

`HeaderFilterRegex` in `.clang-tidy` decides which headers `clang-tidy` reports problems in: C++ files under `include/`, `src/`, `test/`, and `tests/`, including private headers in `src/`. Problems in other headers, such as third-party headers, are not reported.

Header smoke checks are useful for standalone include coverage, but they do not replace tests or examples that instantiate templates and exercise runtime behavior.

## Tool Versions

`tool-requirements.txt` lists the recommended versions of clang-format, clang-tidy, and CMake as major.minor pins, plus Ninja. They are recommendations, not requirements; see [docs/tool-versions.md](../docs/tool-versions.md). CI installs the tools from this file with `pip`.

`tool_versions.py` compares the tools on `PATH` with the recommendations:

```sh
python3 scripts/tool_versions.py
python3 scripts/tool_versions.py --strict
python3 scripts/tool_versions.py --strict --tool clang-cl
```

Without `--strict`, a different or missing tool only prints a warning. CI uses `--strict`, which fails instead. `--tool` also checks another LLVM tool, such as `clang-cl`, against the recommended LLVM version. `quality.py` does not check versions itself. When a tool it runs is not on `PATH`, it prints one error line that names the tool and points to `docs/tool-versions.md`, then exits with status 1.

`install_linux_tools.sh` sets up a Debian or Ubuntu system, such as the `debian:13-slim` image that the Linux CI jobs use. It installs a compiler, Python, git, and GoogleTest with `apt-get`, then creates a virtual environment and installs `tool-requirements.txt` into it. With `--doxygen`, it also installs the pinned Doxygen release after checking its SHA-256. Run it as root or with `sudo`, then add the environment's `bin` directory to `PATH`:

```sh
sh scripts/install_linux_tools.sh [--doxygen] /opt/tools
export PATH="/opt/tools/bin:$PATH"
```

On another distribution, replace the `apt-get` step; the rest does not depend on the distribution.

## Pre-commit Hook

`.pre-commit-config.yaml` defines an optional [pre-commit](https://pre-commit.com/) hook that runs `quality.py format --check` before each commit. The hook is not installed automatically. To opt in, install pre-commit, for example with `pipx install pre-commit` or with `python3 -m pip install pre-commit` in a virtual environment, then enable the hook once per clone:

```sh
pre-commit install
```

The hook runs when a commit contains C++ files and, like `format --check`, checks every project-owned C++ file. It does not run `clang-tidy` or the tests, which are too slow for every commit; run `quality.py check` before you push. Run the hook by hand with `pre-commit run --all-files`, and remove it with `pre-commit uninstall`.

## Contract Tests

Scripts named `*_test.py` pin template engineering contracts that the C++ test suite cannot observe, such as compiler flags and preset settings. They use only the Python standard library and run from the repository root. CI runs every one of them in the `Contract tests` job, and the `Docs` job runs `docs_contract_test.py` again with Doxygen installed.

```sh
for test in scripts/*_test.py; do python3 "$test"; done
```

- `ci_cache_contract_test.py` verifies that the `quality` CI job caches vcpkg's binary packages and LLVM for the clang-cl rows in the runner's temporary directory, that the LLVM cache uses the same version as the Chocolatey install, which only runs on a cache miss, that both cases put the cached LLVM on `PATH`, and that a step checks that CMake did not pick tools from another LLVM.
- `cmake_minimum_contract_test.py` verifies that every `cmake_minimum_required` and the `cmakeMinimumRequired` of `CMakePresets.json` declare the recommended CMake version from `tool-requirements.txt` as the minimum, and that `README.md` and `docs/tool-versions.md` state the same version. It also verifies that the preset file format and the CMake features the build uses, such as `cmake -E copy -t`, need no newer CMake than the declared minimum.
- `community_health_contract_test.py` verifies that the contributing guide, security policy, changelog, issue forms, and pull request template exist with their key sections, that the README links to them, and that their relative links resolve.
- `compiler_options_contract_test.py` loads the CMake option and compiler modules in CMake script mode, with the target commands replaced by stand-ins that record their arguments. It verifies that MSVC and clang-cl get MSVC-style options, that GCC, Clang, AppleClang, and clang++ for the MSVC ABI get GNU-style options, that sanitizers apply only to GNU-style compilers, that ThreadSanitizer cannot be combined with AddressSanitizer, and that Windows CI builds with clang-cl. It also runs the example's `CMakeLists.txt` the same way and verifies that the example gets the library's warning options for each compiler. It is skipped when `cmake` is not installed.
- `docs_contract_test.py` loads the CMake option and docs modules in CMake script mode, with `find_package` and `add_custom_target` replaced by stand-ins, and checks the generated Doxyfile: Doxygen reads `include/`, writes only HTML, warns about undocumented namespaces and symbols, and fails on warnings when warnings are errors. It also verifies that the documentation is opt-in, that the `docs` presets build only the documentation target, that CMake warns about Doxygen before 1.13, and that CI generates the documentation on Ubuntu 26.04. When `doxygen` is installed, it runs Doxygen on the public headers and verifies that undocumented API fails. It is skipped when `cmake` is not installed.
- `gitignore_contract_test.py` verifies that user-local files such as `CMakeUserPresets.json` are ignored. It is skipped outside a git work tree.
- `header_smoke_contract_test.py` verifies that `quality.py tidy` generates header smoke translation units only for headers under the top-level `include/` directory, that it runs no header smoke pass when there are no public headers, and that each smoke file includes its header with angle brackets relative to `include/`.
- `license_docs_contract_test.py` verifies that the root `LICENSE` holds the GPL-3.0 text, that `docs/license.md` describes GPL-3.0 as a recommendation, not a requirement, permits libraries created from the template to replace it, lists common alternatives, and names the files to change when replacing it, and that `README.md` links to that page without calling the license choice settled.
- `package_version_contract_test.py` builds and installs the library as a shared library and verifies that the SONAME is `lib{project_name}.so.MAJOR.MINOR`, that the install tree links `lib{project_name}.so` to it and it to the fully versioned file, and that the installed package version file accepts only requests with the same major and minor version. It repeats the checks with the project version set to 1.2.3 in a copy of the repository, so the rule does not change after 1.0. The build checks use Ninja when it is on `PATH` and `CMAKE_GENERATOR` is not set, run only on Linux, and are skipped when `cmake` is not installed. The test also verifies that the README's Install Contract section states the rule.
- `pre_commit_contract_test.py` verifies that the pre-commit hook only runs `quality.py format --check` with pre-commit's Python, and that the hook is documented as opt-in.
- `quality_generator_contract_test.py` verifies that `quality.py` installs and tests the configuration built by the quality presets, configures the package example with the library's CMake arguments plus warnings as errors and a compile database, that `check` runs `clang-tidy` on the example with that database, and that it handles generators without `compile_commands.json`: `test` and `package` warn, while `tidy` and `check` fail before building. It records the commands `quality.py` would run instead of running them.
- `rename_project_contract_test.py` renames a copy of the repository and verifies that `rename_project.py` leaves itself unchanged, including in `--dry-run` output, that every placeholder path is renamed, and that no other file still contains the placeholder.
- `sanitizer_contract_test.py` verifies that the `asan-ubsan` preset enables sanitizers and that every ASan/UBSan compile option block also passes `-fno-sanitize-recover=all`, so UndefinedBehaviorSanitizer reports fail the test run. It also verifies that the `tsan` presets enable only ThreadSanitizer, that CI runs both sanitizer presets, and that the CI job builds and runs the `tsan` tests under `setarch -R` in a container that allows it.
- `template_version_contract_test.py` verifies that the root `TEMPLATE_VERSION` file contains exactly one `vX.Y.Z` line.
- `text_policy_contract_test.py` verifies that `.editorconfig` and `.gitattributes` keep the LF line ending policy, with CRLF for Windows batch scripts and common binary formats marked as binary, and that tracked text files are stored with LF. The `.gitattributes` and index checks are skipped outside a git work tree.
- `tidy_scope_contract_test.py` verifies that `HeaderFilterRegex` in `.clang-tidy` matches every C++ header and source suffix that `quality.py` collects under `include/`, `src/`, `test/`, and `tests/`, with relative and absolute paths, so private headers in `src/` are checked.
- `tool_versions_contract_test.py` verifies that `tool-requirements.txt` pins only major.minor, with the same LLVM version for clang-format and clang-tidy, and that `docs/tool-versions.md` records the same versions as recommendations. It also verifies that every CI job installs and checks the recommended versions with `tool_versions.py --strict`, that CI installs no tool without a version and uses no `-latest` runner label, that clang-cl comes from the recommended LLVM release, and that all Linux jobs run in the same container image. It checks how `tool_versions.py` parses version output and that it only warns without `--strict`. It also runs `quality.py format --check` with an empty `PATH` and verifies that a missing tool produces one readable error and exit status 1 instead of a traceback, while other missing files are not reported as missing tools.

## `rename_project.py`

`rename_project.py` renames the template placeholder project before real library code is added.

```sh
python3 scripts/rename_project.py --dry-run
python3 scripts/rename_project.py
```

With no positional argument, the script infers the new project name from the repository directory by lowercasing it and converting hyphens to underscores. You can also pass an explicit lowercase snake_case name:

```sh
python3 scripts/rename_project.py my_library --dry-run
python3 scripts/rename_project.py my_library
```

The script replaces `project_name` in text files, replaces export macro tokens such as `PROJECT_NAME_EXPORT`, replaces template header guards such as `PROJECT_NAME_PROJECT_NAME_H_`, and renames placeholder paths such as the public include directory, source file, test file, and package config template. It does not replace CMake's `${PROJECT_NAME}` variable, and it leaves its own file unchanged, so the script keeps the template placeholder as its default `--from` value. Use `--dry-run` first, then run `python3 scripts/quality.py check` after renaming.
