# CPP-DEV

`CPP-DEV` is a baseline template for C++ library projects. It defines the structure, naming, formatting, static analysis, and CMake contract expected by new libraries.

The template should stay small. Individual libraries may add their own dependencies, modules, examples, tools, and platform-specific build logic, but they should keep the public layout and package interface consistent.

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

## Install Contract

Installing a library should install:

- The compiled library target.
- Public headers from `include/`.
- Exported CMake targets under the package namespace `{project_name}::`.
- A package config file for `find_package`.
- A package version file matching the project version.

The install tree should not expose `src/` paths or any source-tree-only include directories.

## Template Principles

- Keep this template as a shared starting point, not a complete application framework.
- Add project-specific dependencies only in the project that needs them.
- Keep public API headers under `include/{project_name}/...`.
- Treat `src/` as implementation detail.
- Keep `.clang-format` and `.clang-tidy` inherited from this template unless a project has a clear reason to override them.
