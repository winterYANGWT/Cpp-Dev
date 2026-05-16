# CPP-DEV

`CPP-DEV` is a baseline template for C++ library projects. It defines the structure, naming, formatting, static analysis, and CMake contract expected by new libraries.

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

After renaming, replace the placeholder header, source, and test content with the real library API and behavior.

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

New libraries should use this structure:

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

## C++ Style

New libraries should follow Google C++ style as the baseline, with the local adjustments encoded in `.clang-format` and `.clang-tidy`.

This is not a strict, unmodified Google C++ style profile. The template accepts most Google C++ conventions while preserving a small set of personal preferences, such as always requiring braces for control statements and keeping a trailing blank line at the end of formatted files.

## CMake Contract

Every library should use CMake `3.21` or newer.

The root CMake project should define one main library target named `{project_name}` and an alias target named `{project_name}::{project_name}`. The alias target is the stable interface used by tests, examples, and downstream consumers.

The template CMake files should prefer `${PROJECT_NAME}` for repeated project-dependent names, including targets, options, exported target files, config files, and install destinations. After creating a new library, changing the root `project(...)` name should update most generated CMake names automatically.

Each library target must expose both build-tree and install-tree include paths. The build interface points at the source tree `include/` directory. The install interface points at the installed include directory.

Install support is required by default. The install option should be named `{project_name}_INSTALL`, and its default should follow whether the project is the top-level CMake project. This keeps standalone builds installable while avoiding unwanted installs when the library is included through `add_subdirectory`.

Installed libraries must be consumable through CMake package config mode. A downstream project should be able to use `find_package({project_name} CONFIG REQUIRED)` and link against `{project_name}::{project_name}`.

## Testing

The template uses CTest as the default test framework.

The baseline test target should stay dependency-free. It should compile a small executable from `test/`, link it against `{project_name}::{project_name}`, and register it with CTest. Projects that need richer assertions may add GoogleTest, Catch2, or another framework locally, but those dependencies are not part of the shared template baseline.

## Quality Commands

The `scripts/` directory provides the standard local quality gate:

```sh
python3 scripts/quality.py check
```

The quality runner formats project-owned C++ files, runs CTest through the
`quality` CMake preset, and runs `clang-tidy` on real source translation units
plus generated header smoke translation units. See [scripts/README.md](scripts/README.md)
for the full command list, file scope rules, and header-check strategy.

Use `python` instead of `python3` on platforms where that is the Python 3 executable.

## Project Rename Workflow

After generating a repository from this template, rename the placeholder project before adding real code.

Use `scripts/rename_project.py` with no argument to infer the project name from the generated repository directory. Use an explicit lowercase snake_case argument when the repository directory is not the desired CMake package name. The script updates file contents and renames placeholder paths such as the public include directory, source file, test file, and package config template.

Run the script in dry-run mode first to inspect planned changes. Then run it without dry-run and finish by running the quality gate. See [scripts/README.md](scripts/README.md) for script usage details.

## Install Contract

Installing a library should install:

- The compiled library target.
- Public headers from `include/`.
- Exported CMake targets under the package namespace `{project_name}::`.
- A package config file for `find_package`.
- A package version file matching the project version.

The install tree should not expose `src/` paths or any source-tree-only include directories.

## License

New libraries created from this template default to GPL-3.0. Projects may intentionally choose another license, but the template baseline keeps GPL-3.0 unless changed by the project owner.

## Template Principles

- Keep this template as a shared starting point, not a complete application framework.
- Add project-specific dependencies only in the project that needs them.
- Keep public API headers under `include/{project_name}/...`.
- Treat `src/` as implementation detail.
- Keep `.clang-format` and `.clang-tidy` inherited from this template unless a project has a clear reason to override them.
