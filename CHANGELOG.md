# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!--
Template: the entries below record changes to the CPP-DEV template itself.
Projects created from the template should replace them with their own history,
starting from an empty Unreleased section.
-->

## [Unreleased]

### Added

- `TEMPLATE_VERSION` file that records which template version a project is
  based on.
- `.gitattributes` and `.editorconfig` with an LF line ending policy.
- `tsan` preset and `project_name_ENABLE_THREAD_SANITIZER` option for
  ThreadSanitizer, with a CI job.
- clang-cl builds in the Windows CI matrix.
- Optional pre-commit hook that checks formatting.
- Contributing guide, security policy, changelog, and issue and pull request
  templates.
- Contract tests in `scripts/` for template conventions, run by the
  `Contract tests` CI job.
- Warning options for the `universe_answer` example, with a
  `universe_answer_WARNINGS_AS_ERRORS` option.
- `docs` preset and `project_name_BUILD_DOCS` option that generate API
  documentation with Doxygen, with a CI job that fails on undocumented public
  API.
- Recommended tool versions in `docs/tool-versions.md`: clang-format and
  clang-tidy 21.1, CMake 4.2, and Doxygen 1.15. They are recommendations, not
  requirements. `scripts/tool_versions.py` compares the installed tools with
  them.
- `scripts/install_linux_tools.sh`, which sets up a Debian or Ubuntu image for
  the quality gate.
- `docs/license.md`, which explains why the template recommends GPL-3.0, what
  it means for users of a library, and how to replace it.

### Changed

- The Windows CI jobs cache pip downloads, the GoogleTest package that vcpkg
  builds, and LLVM for clang-cl, to shorten the slowest jobs.
- CMake 4.2 or newer is required, the same version that is recommended. The
  CMake files declared 3.21, but the build already needed 3.26 for
  `cmake -E copy -t`.
- C++20 module scanning is turned off. With CMake 4.2 policies it is on by
  default, and with GCC it adds flags that `clang-tidy` cannot read.
- GPL-3.0 is described as a recommendation, not a requirement: libraries
  created from the template may replace the license.
- Compiler options are chosen by the compiler frontend, so clang-cl gets
  MSVC-style options instead of GCC-style ones.
- `quality.py package` installs and tests the configuration built by the
  quality presets, and configures the package example with the same CMake
  arguments as the library.
- `quality.py tidy` and `quality.py check` stop with an explanation when the
  CMake generator does not write `compile_commands.json`; `test` and `package`
  print a warning instead.
- `quality.py check` runs `clang-tidy` on the example as well, and the package
  consumer check builds the example with warnings as errors.
- `project_name_WARNINGS_AS_ERRORS` also turns Doxygen warnings into errors.
- CI installs the recommended tool versions and fails when a job runs other
  versions. Linux jobs run in a `debian:13-slim` container, and runner labels
  are pinned instead of `-latest`.
- The ThreadSanitizer CI job disables address space randomization with
  `setarch` instead of changing the kernel setting.

### Fixed

- UndefinedBehaviorSanitizer findings now fail the test run.
- `quality.py` reports a tool missing from `PATH` with one error line and
  exit status 1 instead of a Python traceback.
- `CMakeUserPresets.json` is ignored by git.
