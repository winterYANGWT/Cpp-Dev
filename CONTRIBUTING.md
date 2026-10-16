# Contributing

<!--
Template: projects created from CPP-DEV should review this guide and adjust
the branch flow, required checks, and commit conventions to match the project.
-->

Thank you for helping improve this project. This guide covers the checks to run
before submitting a change and how branches, commits, and pull requests are
organized.

## Setup

Install the tools listed in [Required Local Tools](README.md#required-local-tools):
CMake, a C++20 compiler, `clang-format`, `clang-tidy`, and GoogleTest.

## Checks

Run the full quality gate from the repository root before you submit a change:

```sh
python3 scripts/quality.py check
```

It checks formatting, verifies strict C++20 compile flags, builds and runs the
tests, verifies the installed CMake package, and runs `clang-tidy`. Use `python`
instead of `python3` where that is the Python 3 executable. See
[scripts/README.md](scripts/README.md) for the individual commands.

For changes that affect memory safety or concurrency, also run the sanitizer
presets:

```sh
cmake --preset asan-ubsan
cmake --build --preset asan-ubsan
ctest --preset asan-ubsan

cmake --preset tsan
cmake --build --preset tsan
ctest --preset tsan
```

To check formatting automatically before each commit, you can install the
optional [pre-commit hook](scripts/README.md#pre-commit-hook).

## Branches

Follow the [Release Branching Contract](docs/release-branching.md). In short:

- Branch features from `dev` as `feature/<name>` and fixes for unreleased work
  as `fix/<name>`, and merge them back to `dev`.
- Do not merge feature or fix branches directly into `main`; `main` always
  points at the latest published release.
- Hotfixes for published versions use `hotfix/vX.Y.Z` branches as described in
  the contract.

## Commits

Start the commit subject with a type prefix, followed by a short summary in the
imperative mood:

```text
feat: add a JSON writer
fix: handle empty input when parsing versions
docs: document the package consumer check
```

Common prefixes are `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `build:`,
`ci:`, and `chore:`.

## Pull Requests

- Keep each pull request focused on a single change.
- Add or update tests for behavior changes.
- Update the documentation when user-visible behavior changes.
- Add an entry under `Unreleased` in [CHANGELOG.md](CHANGELOG.md) for notable
  changes.
- Complete the checklist in the pull request template.

## Reporting Issues

Use the bug report or feature request form when you open an issue. Do not
report security vulnerabilities in public issues; follow
[SECURITY.md](SECURITY.md) instead.
