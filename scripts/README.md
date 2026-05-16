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
- `check` runs `format --check`, `test`, and `tidy` in that order.

### File Scope

The script walks the whole repository and includes project-owned C++ files with these suffixes:

- Headers: `.h`, `.hh`, `.hpp`, `.hxx`
- Sources: `.cc`, `.cpp`, `.cxx`

It skips common build, dependency, generated, and vendor directories such as `build/`, `out/`, `external/`, `third_party/`, and `vendor/`.

`--include-examples` is retained only as a deprecated compatibility flag. Project-owned examples are included by default.

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

The script replaces `project_name` in text files and renames placeholder paths such as the public include directory, source file, test file, and package config template. Use `--dry-run` first, then run `python3 scripts/quality.py check` after renaming.
