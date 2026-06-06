# CPP-DEV

`CPP-DEV` is a baseline template for C++ library projects. It defines the structure, naming, formatting, static analysis, test framework, and CMake package contract expected by new libraries.

The template should stay small. Individual libraries may add their own dependencies, modules, examples, tools, and platform-specific build logic, but they should keep the public layout and package interface consistent.

## Quick Start

Create a new repository from GitHub's `Use this template` button, then initialize the placeholder project name before adding real code.

Linux, macOS, WSL, or Git Bash:

```sh
git clone <new-repository-url>
cd <new-repository-directory>
python3 scripts/rename_project.py --dry-run
python3 scripts/rename_project.py
python3 scripts/quality.py check
```

Windows PowerShell:

```powershell
git clone <new-repository-url>
Set-Location <new-repository-directory>
python scripts/rename_project.py --dry-run
python scripts/rename_project.py
python scripts/quality.py check
```

When no project name is provided, `rename_project.py` infers it from the repository directory name. GitHub repository names may use hyphens; inferred names convert hyphens to underscores and lowercase the result.

You can also pass the project name explicitly:

```sh
python3 scripts/rename_project.py my_library --dry-run
python3 scripts/rename_project.py my_library
```

`my_library` is only an example. Explicit project names must already use lowercase snake_case.

After renaming, replace the placeholder header, source, test content, and README with the real library API, behavior, and project description.

## Required Local Tools

The quality gate expects CMake, a C++20 compiler, `clang-format`, `clang-tidy`, and GoogleTest.

Ubuntu or Debian:

```sh
sudo apt-get update
sudo apt-get install -y cmake clang-format clang-tidy libgtest-dev
```

macOS with Homebrew:

```sh
brew install cmake googletest llvm
export PATH="$(brew --prefix llvm)/bin:$PATH"
export SDKROOT="$(xcrun --sdk macosx --show-sdk-path)"
```

Windows with MSVC Build Tools, Chocolatey, and vcpkg:

```powershell
choco install llvm ninja -y
vcpkg install gtest:x64-windows
$env:CC = "cl"
$env:CXX = "cl"
$env:CPP_DEV_CMAKE_CONFIGURE_ARGS = "-G Ninja -DCMAKE_C_COMPILER=cl -DCMAKE_CXX_COMPILER=cl -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake -DVCPKG_TARGET_TRIPLET=x64-windows"
python scripts/quality.py check
```

## Naming

Project names use lowercase English words separated by underscores.

Examples of the naming style:

- Project name: `{project_name}`
- Optional subproject name: `{optional_subproject}`
- CMake package name: `{project_name}`
- Main target name: `{project_name}`
- Exported target name: `{project_name}::{project_name}`

Do not use PascalCase project names for new libraries.

## Layout

Compiled libraries should use this structure:

```text
.
├── CMakeLists.txt
├── cmake/
├── include/
│   └── {project_name}/
│       └── {optional_subproject}/
├── src/
└── test/
```

Rules:

- Public headers must live under `include/{project_name}/...`.
- Optional public submodules must live under `include/{project_name}/{optional_subproject}/...`.
- Implementation files belong in `src/` and should use the `.cc` extension.
- Test files belong in `test/`; use the singular directory name and the `.cc` extension for C++ test sources.
- Public headers should not be placed directly under the root of `include/`.

Header-only libraries may remove `src/` and use an `INTERFACE` library target instead of a compiled target. Keep the same package name, alias target, install-tree include directory, and `find_package({project_name} CONFIG REQUIRED)` contract. Use `project_name_configure_cxx_interface_target(${PROJECT_NAME})` for the main header-only target; concrete test or tool executables should still use `project_name_configure_cxx_target(...)`.

## C++ Style

New libraries should follow Google C++ style as the baseline, with the local adjustments encoded in `.clang-format` and `.clang-tidy`.

This is not a strict, unmodified Google C++ style profile. The template accepts most Google C++ conventions while preserving a small set of personal preferences, such as always requiring braces for control statements and keeping a trailing blank line at the end of formatted files.

Use Doxygen comments for public API documentation. Prefer `/** ... */` block comments placed on their own line immediately before the symbol they document. Avoid trailing Doxygen forms after declarations or statements.

Use standard include guards for public headers. Do not use non-standard pragma-based header guards. Guard names should follow the installed include path, be uppercase, and end in `_H_`, such as `PROJECT_NAME_PROJECT_NAME_H_` for `include/project_name/project_name.h`.

## CMake Contract

Every library should use CMake `3.21` or newer and build as strict C++20. Project-owned compiled C++ targets must set `CXX_STANDARD 20`, `CXX_STANDARD_REQUIRED ON`, and `CXX_EXTENSIONS OFF` so CMake emits `-std=c++20` rather than a compiler-extension mode such as `-std=gnu++20`. Header-only `INTERFACE` targets should use `target_compile_features(... INTERFACE cxx_std_20)` through `project_name_configure_cxx_interface_target(...)`.

The root CMake project should define one main library target named `{project_name}` and an alias target named `{project_name}::{project_name}`. The alias target is the stable interface used by tests, examples, and downstream consumers.

The template CMake files should prefer `${PROJECT_NAME}` for repeated project-dependent names, including targets, options, exported target files, config files, and install destinations. After creating a new library, changing the root `project(...)` name should update most generated CMake names automatically.

Each library target must expose both build-tree and install-tree include paths. The build interface points at the source tree `include/` directory and the generated export-header include directory. The install interface points at the installed include directory.

Compiled libraries must generate and install an export header named `<{project_name}/export.h>`. Public API declarations exported from a shared library should use the generated `{PROJECT_NAME}_EXPORT` macro. Targets should use hidden default visibility so shared-library exports are intentional on Windows, macOS, and ELF platforms.

Install support is required by default. The install option should be named `{project_name}_INSTALL`, and its default should follow whether the project is the top-level CMake project. This keeps standalone builds installable while avoiding unwanted installs when the library is included through `add_subdirectory`.

Installed libraries must be consumable through CMake package config mode. A downstream project should be able to use `find_package({project_name} CONFIG REQUIRED)` and link against `{project_name}::{project_name}`.

## Testing

The template uses GoogleTest as the baseline test framework. Tests should resolve it with `find_package(GTest CONFIG REQUIRED)` and `include(GoogleTest)` in the test `CMakeLists.txt`.

Link every GTest executable to `GTest::gtest_main` and register it with `gtest_discover_tests(<target>)`. Do not call `add_test(NAME ... COMMAND ...)` directly for GTest binaries.

Place tests in `test/` using `.cc` files. Name cases `TEST(Suite, Case)` so CTest produces clear, unique names. Pass build-time-known inputs through `target_compile_definitions()` instead of per-test command-line arguments so discovery works without custom argv.

## Quality Commands

The `scripts/` directory provides the standard local quality gate:

```sh
python3 scripts/quality.py check
```

The quality runner formats project-owned C++ files, verifies strict C++20 compile flags, runs CTest through the `quality` CMake preset, and runs `clang-tidy` on real source translation units plus generated header smoke translation units. See [scripts/README.md](scripts/README.md) for the full command list, file scope rules, header-check strategy, and `CPP_DEV_CMAKE_CONFIGURE_ARGS` override.

Use `python` instead of `python3` on platforms where that is the Python 3 executable.

Useful build-variant checks:

```sh
CPP_DEV_CMAKE_CONFIGURE_ARGS="-DBUILD_SHARED_LIBS=ON" python3 scripts/quality.py check
cmake --preset asan-ubsan
cmake --build --preset asan-ubsan
ctest --preset asan-ubsan
```

## Project Rename Workflow

After generating a repository from this template, rename the placeholder project before adding real code.

Use `scripts/rename_project.py` with no argument to infer the project name from the generated repository directory. Use an explicit lowercase snake_case argument when the repository directory is not the desired CMake package name. The script updates file contents, updates generated export macro references such as `PROJECT_NAME_EXPORT`, updates template header guards such as `PROJECT_NAME_PROJECT_NAME_H_`, and renames placeholder paths such as the public include directory, source file, test file, and package config template.

Run the script in dry-run mode first to inspect planned changes. Then run it without dry-run, replace the template README with the new library's own README, and finish by running the quality gate. See [scripts/README.md](scripts/README.md) for script usage details.

## Install Contract

Installing a compiled library should install:

- The compiled library target.
- Public headers from `include/`.
- The generated export header under `include/{project_name}/export.h`.
- Exported CMake targets under the package namespace `{project_name}::`.
- A package config file for `find_package`.
- A package version file matching the project version.

The install tree should not expose `src/` paths or any source-tree-only include directories.

## License

New libraries created from this template use GPL-3.0 by default. Treat GPL-3.0 as the settled template default, and do not reopen the license choice during routine template reuse unless the project owner explicitly requests a different license.

## Template Principles

- Keep this template as a shared starting point, not a complete application framework.
- Add project-specific dependencies only in the project that needs them.
- Keep public API headers under `include/{project_name}/...`.
- Treat `src/` as implementation detail.
- Keep `.clang-format` and `.clang-tidy` inherited from this template unless a project has a clear reason to override them.
