# Tool Versions

This page lists the tool versions that this repository recommends and that CI
uses.

**These versions are recommendations, not requirements.** The quality gate runs
with whatever versions are on your `PATH`, and other versions usually work. The
recommendations exist because formatting and static analysis results change
between tool releases: with other versions, `clang-format` can reformat code
that CI accepts, and `clang-tidy` can report findings that CI does not, or miss
findings that CI reports. Use the recommended versions when you want local
results to match CI.

**The exception is the CMake minimum.** The CMake files require CMake 4.2 or
newer, the same version that is recommended, so CI always builds with the
minimum version. Newer CMake releases work.

## Recommended Versions

| Tool | Recommended | Notes |
| --- | --- | --- |
| clang-format | 21.1 | Formatting output differs between minor releases. |
| clang-tidy | 21.1 | New releases add and extend checks, and `.clang-tidy` treats every warning as an error. |
| CMake | 4.2 | The version that CI builds with, and also the minimum: the CMake files declare `cmake_minimum_required(VERSION 4.2)`. Newer versions work. |
| Doxygen | 1.15 | Only needed for the `docs` preset. Use 1.13 or newer: older versions do not report undocumented namespaces. |
| gcovr | 8.8 | Only needed for coverage reports (`scripts/coverage.py`). Needs Python 3.10 or newer. |
| Ninja | any | The version does not affect results. |

Only major.minor matters. Patch releases of clang-format 21.1 and clang-tidy
21.1 give the same results, so any 21.1.x is fine. LLVM publishes only N.1.x
releases for each major version, so 21.1 also means LLVM 21.

`scripts/tool-requirements.txt` holds the recommended versions of the tools
that come from PyPI. CI installs from that file, and the contract tests check
that this page, the file, and CI agree.

## Check Your Tools

```sh
python3 scripts/tool_versions.py
```

The script prints the version of each tool on `PATH` next to the recommended
version. A different or missing tool only produces a warning, and the script
exits with status 0. CI runs it with `--strict`, which fails instead.
`--tool clang-cl` also checks clang-cl, which comes from the same LLVM release.

## Install the Recommended Versions

On any platform, install clang-format, clang-tidy, CMake, and Ninja from PyPI
into a virtual environment, then put its `bin` directory (`Scripts` on Windows)
first on `PATH`:

```sh
python3 -m venv ~/.venvs/cpp-dev-tools
~/.venvs/cpp-dev-tools/bin/pip install -r scripts/tool-requirements.txt
export PATH="$HOME/.venvs/cpp-dev-tools/bin:$PATH"
```

Keep the virtual environment outside the repository: `quality.py` checks every
C++ file under the repository root, and some packages contain C++ headers.

Platform packages also provide the recommended versions:

- Ubuntu 26.04: `sudo apt-get install clang-format clang-tidy cmake doxygen`
  installs clang-format and clang-tidy 21.1, CMake 4.2, and Doxygen 1.15.
- macOS: `brew install llvm@21`, then add `$(brew --prefix llvm@21)/bin` to
  `PATH`.
- Windows: `choco install llvm --version=21.1.8`, which also installs clang-cl.
- Doxygen: the [release binaries](https://github.com/doxygen/doxygen/releases)
  run on any platform.

Older distributions ship a CMake below the 4.2 minimum, for example Ubuntu
24.04 (3.28) and Debian 13 (3.31), and the CMake that comes with Visual Studio
can be older too. Install CMake from PyPI on those systems.

## What CI Uses

Every CI job installs the recommended versions and runs
`tool_versions.py --strict` before it builds anything.

| Platform | Runner | Compiler | Tools |
| --- | --- | --- | --- |
| Linux | `debian:13-slim` container on `ubuntu-24.04` | GCC 14 from Debian | PyPI; Doxygen 1.15.0 release |
| macOS | `macos-26` | AppleClang from Xcode | PyPI |
| Windows | `windows-2025` | MSVC; clang-cl from LLVM 21.1.8 | PyPI |

GoogleTest comes from the platform's package manager: Debian, Homebrew, or
vcpkg. Its version does not affect results.

### Actions and Token

The workflow uses four actions: `actions/checkout`, `actions/cache`,
`actions/upload-artifact` for the coverage report, and on Windows
`step-security/msvc-dev-cmd`. Each is pinned to the full commit SHA of
a release, with the release in a trailing comment, so that moving a tag cannot
change what runs. To update an action, look up the commit of the new release,
for example with
`git ls-remote --tags https://github.com/actions/checkout v7.0.1` (for an
annotated tag, use the line that ends in `^{}`), and change both the SHA and
the comment. Use one release of each action in the whole workflow;
`scripts/ci_hardening_contract_test.py` checks this.

`step-security/msvc-dev-cmd` is StepSecurity's maintained fork of
`ilammy/msvc-dev-cmd`, which is no longer maintained. It is free for public
repositories. In a private repository it needs a StepSecurity subscription,
and without one the step fails. A private project can subscribe, or replace
the step with one that runs Visual Studio's `vcvars64.bat` and writes the
environment to `GITHUB_ENV`.

Every job's `GITHUB_TOKEN` can only read the repository, whatever the
repository or organization default is: the workflow sets
`permissions: contents: read`. Checkout runs with
`persist-credentials: false`, so the token is not left in the git
configuration for the tools and tests that run after it. A job that needs more,
for example to publish documentation, should declare it in its own
`permissions` block instead of widening the workflow's.

### Caches

The Windows jobs spend most of their time setting up tools, and the slowest job
decides how long CI takes. The `quality` job therefore caches that work with
`actions/cache`. The caches live in the runner's temporary directory, never in
the workspace or in `build/`:

- the GoogleTest package that vcpkg builds on Windows, through vcpkg's binary
  cache, keyed by the runner image version;
- on the clang-cl rows, the parts of LLVM 21.1.8 that clang-cl needs. Every
  Windows runner image comes with LLVM 20, so on a cache miss the job installs
  LLVM 21.1.8 with Chocolatey and copies those files into the cache directory.
  Either way, the build uses the copy in the cache directory. A later step
  checks that the linker and the other LLVM tools that CMake picked come from
  the same directory as clang-cl, so that the preinstalled LLVM 20 on `PATH`
  is never mixed in.

The first run after a cache key changes fills the cache and takes about as
long as a run without caches. pip downloads are not cached: installing the
PyPI tools takes about the same time with a cache, because most of it goes into
creating the virtual environment and installing the packages.

### Linux Image

Linux jobs run in the `debian:13-slim` image instead of directly on the
runner's Ubuntu image. The slim image contains only a minimal Debian system,
and `scripts/install_linux_tools.sh` installs everything the jobs need, so the
CI environment is defined in this repository rather than by the runner image.

The script has two parts:

- **Distribution packages**: a C++ compiler, Python, git, and GoogleTest, from
  `apt-get`. Their versions do not need to match a recommendation. The script
  works on Debian and Ubuntu images, such as `debian:13-slim`, `ubuntu:24.04`,
  and `ubuntu:26.04`; for another distribution, replace this part with its
  package manager.
- **Tools with recommended versions**: clang-format, clang-tidy, CMake, and
  Ninja from PyPI; with `--doxygen`, the pinned Doxygen release, checked
  against its SHA-256; and with `--gcovr`, the pinned gcovr release from PyPI. This part is the same on every Linux image with glibc
  2.28 or newer; the Doxygen release needs glibc 2.34 or newer, which Debian
  12, Ubuntu 22.04, and later releases provide.

To reproduce a Linux CI job locally with Docker:

```sh
docker run --rm -it -v "$PWD:/work" -w /work debian:13-slim
# Inside the container:
apt-get update && apt-get install -y --no-install-recommends ca-certificates git
sh scripts/install_linux_tools.sh /opt/tools
export PATH="/opt/tools/bin:$PATH"
python3 scripts/tool_versions.py --strict
CPP_DEV_CMAKE_CONFIGURE_ARGS="-G Ninja" python3 scripts/quality.py check
```

The container builds in the mounted `build/` directory. Remove `build/quality`
before and after, or mount a separate clone, because a CMake build directory
cannot be shared between the host and the container.

The script can also set up another Linux image for this repository, for
example as a `RUN` step in a Dockerfile.

ThreadSanitizer aborts when the kernel's mmap randomization breaks its memory
layout. The CI job therefore runs the `tsan` build and tests under
`setarch "$(uname -m)" -R`, which turns randomization off for those processes.
Docker's default seccomp profile blocks this, so the container is started with
`--security-opt seccomp=unconfined`; add that option to `docker run` to run
the `tsan` preset locally.

## Change a Recommendation

1. Update `scripts/tool-requirements.txt` and this page. For LLVM, also update
   the Chocolatey LLVM version and the version in the LLVM cache key and
   directory in `.github/workflows/ci.yml`, which
   `scripts/ci_cache_contract_test.py` checks; for Doxygen,
   update the version and SHA-256 in `scripts/install_linux_tools.sh`, and for
   gcovr, `gcovr_version` in the same script. For
   CMake, the recommendation is also the minimum version: update
   `cmake_minimum_required` in `CMakeLists.txt` and
   `examples/universe_answer/CMakeLists.txt`, `cmakeMinimumRequired` in
   `CMakePresets.json`, and the CMake Contract in `README.md`.
   `scripts/cmake_minimum_contract_test.py` checks that they agree.
2. Run `python3 scripts/quality.py check` with the new versions and fix new
   formatting differences and clang-tidy findings in the same change.
3. Record the change in `CHANGELOG.md`.
