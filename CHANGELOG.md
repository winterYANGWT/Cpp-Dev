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

### Changed

- Compiler options are chosen by the compiler frontend, so clang-cl gets
  MSVC-style options instead of GCC-style ones.
- `quality.py package` installs and tests the configuration built by the
  quality presets, and configures the package example with the same CMake
  arguments as the library.
- `quality.py tidy` and `quality.py check` stop with an explanation when the
  CMake generator does not write `compile_commands.json`; `test` and `package`
  print a warning instead.

### Fixed

- UndefinedBehaviorSanitizer findings now fail the test run.
- `CMakeUserPresets.json` is ignored by git.
