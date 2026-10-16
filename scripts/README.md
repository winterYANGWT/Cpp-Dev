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
- `tidy` configures the `quality` CMake preset and runs `clang-tidy`.
- `test` configures, builds, and runs CTest through the `quality` preset.
- `package` installs the quality build to a temporary prefix, builds the `examples/universe_answer` downstream project against that installed package, and runs the example CTest suite.
- `check` runs `format --check`, configures once, then runs tests, the package consumer check, and `clang-tidy`.

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

### File Scope

The script walks the whole repository and includes project-owned C++ files with these suffixes:

- Headers: `.h`, `.hh`, `.hpp`, `.hxx`
- Sources: `.cc`, `.cpp`, `.cxx`

It skips common build, dependency, generated, and vendor directories such as `build/`, `out/`, `external/`, `third_party/`, and `vendor/`.

### `clang-tidy` Header Checks

`tidy` uses two inputs:

- Real source translation units from `build/quality/compile_commands.json`.
- Generated header smoke translation units under `build/quality/header_smoke/`.

Each header smoke file contains a single `#include` for one project header. The script also writes a temporary compile database for these generated `.cc` files, reusing compile flags from the real CMake compile database. This checks that headers can be parsed as part of a normal C++ translation unit instead of asking `clang-tidy` to analyze `.h` files directly.

Header smoke checks are useful for standalone include coverage, but they do not replace tests or examples that instantiate templates and exercise runtime behavior.

## Pre-commit Hook

`.pre-commit-config.yaml` defines an optional [pre-commit](https://pre-commit.com/) hook that runs `quality.py format --check` before each commit. The hook is not installed automatically. To opt in, install pre-commit, for example with `pipx install pre-commit` or with `python3 -m pip install pre-commit` in a virtual environment, then enable the hook once per clone:

```sh
pre-commit install
```

The hook runs when a commit contains C++ files and, like `format --check`, checks every project-owned C++ file. It does not run `clang-tidy` or the tests, which are too slow for every commit; run `quality.py check` before you push. Run the hook by hand with `pre-commit run --all-files`, and remove it with `pre-commit uninstall`.

## Contract Tests

Scripts named `*_test.py` pin template engineering contracts that the C++ test suite cannot observe, such as compiler flags and preset settings. They use only the Python standard library and run from the repository root. CI runs every one of them in the `Contract tests` job.

```sh
for test in scripts/*_test.py; do python3 "$test"; done
```

- `community_health_contract_test.py` verifies that the contributing guide, security policy, changelog, issue forms, and pull request template exist with their key sections, that the README links to them, and that their relative links resolve.
- `compiler_options_contract_test.py` loads the CMake option and compiler modules in CMake script mode, with the target commands replaced by stand-ins that record their arguments. It verifies that MSVC and clang-cl get MSVC-style options, that GCC, Clang, AppleClang, and clang++ for the MSVC ABI get GNU-style options, that sanitizers apply only to GNU-style compilers, that ThreadSanitizer cannot be combined with AddressSanitizer, and that Windows CI builds with clang-cl. It is skipped when `cmake` is not installed.
- `gitignore_contract_test.py` verifies that user-local files such as `CMakeUserPresets.json` are ignored. It is skipped outside a git work tree.
- `pre_commit_contract_test.py` verifies that the pre-commit hook only runs `quality.py format --check` with pre-commit's Python, and that the hook is documented as opt-in.
- `quality_generator_contract_test.py` verifies that `quality.py` installs and tests the configuration built by the quality presets, configures the package example with the library's CMake arguments, and handles generators without `compile_commands.json`: `test` and `package` warn, while `tidy` and `check` fail before building. It records the commands `quality.py` would run instead of running them.
- `sanitizer_contract_test.py` verifies that the `asan-ubsan` preset enables sanitizers and that every ASan/UBSan compile option block also passes `-fno-sanitize-recover=all`, so UndefinedBehaviorSanitizer reports fail the test run. It also verifies that the `tsan` presets enable only ThreadSanitizer and that CI runs both sanitizer presets.
- `template_version_contract_test.py` verifies that the root `TEMPLATE_VERSION` file contains exactly one `vX.Y.Z` line.
- `text_policy_contract_test.py` verifies that `.editorconfig` and `.gitattributes` keep the LF line ending policy, with CRLF for Windows batch scripts and common binary formats marked as binary, and that tracked text files are stored with LF. The `.gitattributes` and index checks are skipped outside a git work tree.

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

The script replaces `project_name` in text files, replaces export macro tokens such as `PROJECT_NAME_EXPORT`, replaces template header guards such as `PROJECT_NAME_PROJECT_NAME_H_`, and renames placeholder paths such as the public include directory, source file, test file, and package config template. It does not replace CMake's `${PROJECT_NAME}` variable. Use `--dry-run` first, then run `python3 scripts/quality.py check` after renaming.
