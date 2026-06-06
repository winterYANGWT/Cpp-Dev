# Scripts

This directory contains project maintenance scripts for the CPP-DEV template.

## `quality.py`

`quality.py` is the local quality gate used by this repository. Run commands from the repository root.

```sh
python3 scripts/quality.py format
python3 scripts/quality.py format --check
python3 scripts/quality.py tidy
python3 scripts/quality.py test
python3 scripts/quality.py check
```

Use `python` instead of `python3` on platforms where that is the Python 3 executable.

### Commands

- `format` formats project-owned C++ headers and sources with `clang-format`.
- `format --check` verifies formatting without rewriting files.
- `tidy` configures the `quality` CMake preset and runs `clang-tidy`.
- `test` configures, builds, and runs CTest through the `quality` preset.
- `check` runs `format --check`, configures once, then runs tests and `clang-tidy`.

### CMake Configuration Overrides

Set `CPP_DEV_CMAKE_CONFIGURE_ARGS` to append CMake configure arguments to `cmake --preset quality`.
This is intended for CI and one-off verification of build variants.

```sh
CPP_DEV_CMAKE_CONFIGURE_ARGS="-DBUILD_SHARED_LIBS=ON" python3 scripts/quality.py check
```

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
