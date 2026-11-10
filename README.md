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

On Windows, set the environment variables from [Required Local Tools](#required-local-tools) before running `quality.py`. Without `-G Ninja`, CMake uses the Visual Studio generator, which does not write the `compile_commands.json` that `clang-tidy` needs, so `quality.py check` stops after configuring.

When no project name is provided, `rename_project.py` infers it from the repository directory name. GitHub repository names may use hyphens; inferred names convert hyphens to underscores and lowercase the result.

You can also pass the project name explicitly:

```sh
python3 scripts/rename_project.py my_library --dry-run
python3 scripts/rename_project.py my_library
```

`my_library` is only an example. Explicit project names must already use lowercase snake_case.

After renaming, replace the placeholder header, source, test content, and README with the real library API, behavior, and project description. Keep `TEMPLATE_VERSION`; it records which template version the project started from. See [Template Version](#template-version).

Also replace the template's entries in `CHANGELOG.md` with the project's own history, and review the `Template:` notes in `CONTRIBUTING.md`, `SECURITY.md`, and the issue forms under `.github/ISSUE_TEMPLATE/`.

## Documentation

- [Release Branching Contract](docs/release-branching.md): branch roles,
  SemVer release flow, hotfix flow, and old-version support flow.
- [Tool Versions](docs/tool-versions.md): recommended versions of
  clang-format, clang-tidy, CMake, and Doxygen, and the environments CI uses.
- [License](docs/license.md): why the template recommends GPL-3.0, what it
  means for users of a library, and how to replace it.
- [Contributing](CONTRIBUTING.md): checks to run before submitting a change,
  branch and commit conventions, and pull requests.
- [Security Policy](SECURITY.md): supported versions and private vulnerability
  reporting.
- [Changelog](CHANGELOG.md): notable changes, in Keep a Changelog format.

Issue forms and the pull request template live under `.github/`.

## Required Local Tools

The quality gate expects CMake, a C++20 compiler, `clang-format`, `clang-tidy`, and GoogleTest.

CMake 4.2 or newer is required: the CMake files declare it as their minimum version. This repository recommends clang-format and clang-tidy 21.1 and CMake 4.2, the versions that CI uses. Apart from the CMake minimum, these are recommendations, not requirements: other versions usually work, but formatting and `clang-tidy` results can differ from CI. See [Tool Versions](docs/tool-versions.md) for the reasons and for installing the recommended versions from PyPI on any platform. To compare your tools with the recommendations, run:

```sh
python3 scripts/tool_versions.py
```

Ubuntu or Debian:

```sh
sudo apt-get update
sudo apt-get install -y cmake clang-format clang-tidy libgtest-dev
```

On Ubuntu 26.04 these packages have the recommended versions. Older releases, such as Ubuntu 24.04 and Debian 13, provide a CMake older than 4.2, which is too old for the build: install CMake from PyPI instead, as described in [Tool Versions](docs/tool-versions.md), and clang-format and clang-tidy as well if you want to match CI.

macOS with Homebrew:

```sh
brew install cmake googletest llvm@21
export PATH="$(brew --prefix llvm@21)/bin:$PATH"
export SDKROOT="$(xcrun --sdk macosx --show-sdk-path)"
```

Windows with MSVC Build Tools, Python, Chocolatey, and vcpkg. The CMake that comes with Visual Studio can be older than 4.2, so install CMake, Ninja, clang-format, and clang-tidy from PyPI, as CI does:

```powershell
python -m venv $HOME\.venvs\cpp-dev-tools
& $HOME\.venvs\cpp-dev-tools\Scripts\pip install -r scripts/tool-requirements.txt
$env:PATH = "$HOME\.venvs\cpp-dev-tools\Scripts;$env:PATH"
choco install llvm --version=21.1.8 -y
vcpkg install gtest:x64-windows
$env:CC = "cl"
$env:CXX = "cl"
$env:CPP_DEV_CMAKE_CONFIGURE_ARGS = "-G Ninja -DCMAKE_C_COMPILER=cl -DCMAKE_CXX_COMPILER=cl -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake -DVCPKG_TARGET_TRIPLET=x64-windows"
python scripts/quality.py check
```

The LLVM package provides clang-cl. To build with clang-cl, use `clang-cl` in place of `cl` in `CC`, `CXX`, and the compiler arguments.

The template does not download GoogleTest for you. If CMake cannot find
`GTest CONFIG`, install GoogleTest with your package manager or build it
yourself, then pass the package location through `CMAKE_PREFIX_PATH` or
`GTest_DIR`.

Doxygen is optional. Only the `docs` preset needs it; see
[API Documentation](#api-documentation).

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

Document each public namespace as well as its members, because Doxygen does not check the members of an undocumented namespace. Wrap implementation details in public headers, such as an `internal` namespace, in `/** @cond INTERNAL */` and `/** @endcond */` to leave them out of the documentation and its checks.

Use standard include guards for public headers. Do not use non-standard pragma-based header guards. Guard names should follow the installed include path, be uppercase, and end in `_H_`, such as `PROJECT_NAME_PROJECT_NAME_H_` for `include/project_name/project_name.h`.

## CMake Contract

Every library should use CMake `4.2` or newer and build as strict C++20. Project-owned compiled C++ targets must set `CXX_STANDARD 20`, `CXX_STANDARD_REQUIRED ON`, and `CXX_EXTENSIONS OFF` so CMake emits `-std=c++20` rather than a compiler-extension mode such as `-std=gnu++20`. Header-only `INTERFACE` targets should use `target_compile_features(... INTERFACE cxx_std_20)` through `project_name_configure_cxx_interface_target(...)`.

C++20 module scanning is off: the root `CMakeLists.txt` and the example's `CMakeLists.txt` set `CMAKE_CXX_SCAN_FOR_MODULES` to `OFF` right after `project()`, before any target is created. The template does not use modules, and since CMake 3.28 (policy CMP0155), scanning is on by default for C++20 targets; with GCC it adds flags to `compile_commands.json` that `clang-tidy` cannot read. A project that adopts modules can turn scanning back on, but should then run `clang-tidy` against a Clang build.

The configure functions choose compiler options by the compiler frontend, not by the compiler ID. MSVC and clang-cl get `/W4 /permissive-`, plus `/WX` when warnings are errors. GCC, Clang, and AppleClang get `-Wall -Wextra -Wpedantic`, plus `-Werror`. Sanitizers are only applied with GCC and Clang; MSVC and clang-cl get a configure warning instead.

The root CMake project should define one main library target named `{project_name}` and an alias target named `{project_name}::{project_name}`. The alias target is the stable interface used by tests, examples, and downstream consumers.

The template CMake files should prefer `${PROJECT_NAME}` for repeated project-dependent names, including targets, options, exported target files, config files, and install destinations. After creating a new library, changing the root `project(...)` name should update most generated CMake names automatically.

Each library target must expose both build-tree and install-tree include paths. The build interface points at the source tree `include/` directory and the generated export-header include directory. The install interface points at the installed include directory.

Compiled libraries must generate and install an export header named `<{project_name}/export.h>`. Public API declarations exported from a shared library should use the generated `{PROJECT_NAME}_EXPORT` macro. Targets should use hidden default visibility so shared-library exports are intentional on Windows, macOS, and ELF platforms.

Install support is required by default. The install option should be named `{project_name}_INSTALL`, and its default should follow whether the project is the top-level CMake project. This keeps standalone builds installable while avoiding unwanted installs when the library is included through `add_subdirectory`.

Installed libraries must be consumable through CMake package config mode. A downstream project should be able to use `find_package({project_name} CONFIG REQUIRED)` and link against `{project_name}::{project_name}`.

## Testing

The `test/` directory contains GoogleTest-based tests for the template. See
[test/README.md](test/README.md) for the test target contract, GTest dependency
guidance, and commands for running tests.

## Examples

The `examples/` directory contains small downstream projects that exercise the
template's public package contract. See [examples/README.md](examples/README.md)
for the current example list and build commands.

## Quality Commands

The `scripts/` directory provides the standard local quality gate:

```sh
python3 scripts/quality.py check
```

The quality runner formats project-owned C++ files, verifies strict C++20 compile flags, runs CTest through the `quality` CMake preset, installs the library, builds the installed-package example, and runs `clang-tidy` on real source translation units, generated header smoke translation units, and the example's sources. See [scripts/README.md](scripts/README.md) for the full command list, file scope rules, header-check strategy, and `CPP_DEV_CMAKE_CONFIGURE_ARGS` override.

Use `python` instead of `python3` on platforms where that is the Python 3 executable.

Useful build-variant checks:

```sh
CPP_DEV_CMAKE_CONFIGURE_ARGS="-DBUILD_SHARED_LIBS=ON" python3 scripts/quality.py check
cmake --preset asan-ubsan
cmake --build --preset asan-ubsan
ctest --preset asan-ubsan
cmake --preset tsan
cmake --build --preset tsan
ctest --preset tsan
```

The `asan-ubsan` preset compiles with `-fno-sanitize-recover=all`, so any UndefinedBehaviorSanitizer report fails the test instead of only printing a diagnostic.

The `tsan` preset builds with ThreadSanitizer, which makes a test fail when it reports a data race. ThreadSanitizer cannot be combined with AddressSanitizer, so configuring with both `project_name_ENABLE_SANITIZERS` and `project_name_ENABLE_THREAD_SANITIZER` turned on fails. If ThreadSanitizer aborts with `unexpected memory mapping` or `incompatible memory layout`, the kernel's mmap randomization breaks its memory layout. Run the build and the tests under `setarch "$(uname -m)" -R`, which turns randomization off for them and does not need root, as the CI job does. The build needs it too, because it runs the test executable to list the tests. In a Docker container, `setarch` also needs `--security-opt seccomp=unconfined`. Lowering the randomization for the whole system with `sudo sysctl vm.mmap_rnd_bits=28` works as well.

To check formatting before each commit, you can opt in to the [pre-commit hook](scripts/README.md#pre-commit-hook).

## API Documentation

The `docs` preset generates HTML documentation for the public headers in `include/` with Doxygen:

```sh
cmake --preset docs
cmake --build --preset docs
```

The output is written to `build/docs/doxygen/html/index.html`. The preset treats Doxygen warnings as errors, so the build fails when a public namespace, class, or member is undocumented, when a function documents some of its parameters but not all, or when a comment names a parameter that does not exist. Only this preset looks for Doxygen; other builds do not need it.

Use Doxygen 1.13 or newer. Older versions do not report undocumented namespaces and therefore skip the checks for their members; CMake prints a warning when it finds one. CI generates the documentation on Ubuntu 26.04, which provides Doxygen 1.15.

To generate the documentation from another build tree, configure it with `-Dproject_name_BUILD_DOCS=ON` and build the `project_name_docs` target. Doxygen warnings are errors there only when `project_name_WARNINGS_AS_ERRORS` is also ON.

## Project Rename Workflow

After generating a repository from this template, rename the placeholder project before adding real code.

Use `scripts/rename_project.py` with no argument to infer the project name from the generated repository directory. Use an explicit lowercase snake_case argument when the repository directory is not the desired CMake package name. The script updates file contents, updates generated export macro references such as `PROJECT_NAME_EXPORT`, updates template header guards such as `PROJECT_NAME_PROJECT_NAME_H_`, and renames placeholder paths such as the public include directory, source file, test file, and package config template.

Run the script in dry-run mode first to inspect planned changes. Then run it without dry-run, replace the template README with the new library's own README, and finish by running the quality gate. See [scripts/README.md](scripts/README.md) for script usage details.

## Template Version

The root `TEMPLATE_VERSION` file records a CPP-DEV template version as a single `vX.Y.Z` line, such as `v0.1.0`.

- In the template repository, it is the template's own release version. Update it for every template release, and tag the release commit with the same `vX.Y.Z` value.
- In a generated project, it records the template version the project was created from or last synchronized with. Keep the file after renaming, and update it only when you adopt changes from a newer template release.

`TEMPLATE_VERSION` is independent of the library version in `project(... VERSION ...)`. The library version describes the generated library's own API and package. The template version only describes which template baseline the build, quality, and packaging infrastructure follows.

The template does not generate a version header. Whether a library exposes its own version in a header is a decision for that library.

## Install Contract

Installing a compiled library should install:

- The compiled library target.
- Public headers from `include/`.
- The generated export header under `include/{project_name}/export.h`.
- Exported CMake targets under the package namespace `{project_name}::`.
- A package config file for `find_package`.
- A package version file matching the project version.

The install tree should not expose `src/` paths or any source-tree-only include directories.

### Library Versioning

The shared library's `SOVERSION` is the `major.minor` of the project version, before and after 1.0. A patch release keeps the ABI and the SONAME, so programs built against an earlier patch release load it without a rebuild. A minor or major release may break the ABI and gets a new SONAME, so it can be installed next to the previous one:

| Project version | Library file | SONAME |
| --- | --- | --- |
| `0.1.0` | `lib{project_name}.so.0.1.0` | `lib{project_name}.so.0.1` |
| `0.1.1` | `lib{project_name}.so.0.1.1` | `lib{project_name}.so.0.1` |
| `1.2.3` | `lib{project_name}.so.1.2.3` | `lib{project_name}.so.1.2` |

The package version file uses `SameMinorVersion` for the same reason: `find_package({project_name} 0.1)` accepts 0.1.x releases, and rejects 0.2 and 1.0.

C++ makes ABI breaks easy to introduce, for example by adding a data member to a class or changing an inline function, and the template does not check the ABI. A library that adds an ABI check can relax this after 1.0 to a `major` `SOVERSION` and `SameMajorVersion`.

On macOS, the dylib name carries the same versions. Windows DLL names carry none.

## License

New libraries created from this template use GPL-3.0 by default. The template recommends GPL-3.0 to encourage open source, but it is not a requirement: a library created from this template may replace it with another license. See [License](docs/license.md) for what GPL-3.0 means for users of a library, common alternatives, and how to replace the license.

## Template Principles

- Keep this template as a shared starting point, not a complete application framework.
- Add project-specific dependencies only in the project that needs them.
- Keep public API headers under `include/{project_name}/...`.
- Treat `src/` as implementation detail.
- Keep `.clang-format` and `.clang-tidy` inherited from this template unless a project has a clear reason to override them.
