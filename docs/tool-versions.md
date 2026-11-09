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
  Ninja from PyPI, and with `--doxygen`, the pinned Doxygen release, checked
  against its SHA-256. This part is the same on every Linux image with glibc
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
   the Chocolatey LLVM version in `.github/workflows/ci.yml`; for Doxygen,
   update the version and SHA-256 in `scripts/install_linux_tools.sh`. For
   CMake, the recommendation is also the minimum version: update
   `cmake_minimum_required` in `CMakeLists.txt` and
   `examples/universe_answer/CMakeLists.txt`, `cmakeMinimumRequired` in
   `CMakePresets.json`, and the CMake Contract in `README.md`.
   `scripts/cmake_minimum_contract_test.py` checks that they agree.
2. Run `python3 scripts/quality.py check` with the new versions and fix new
   formatting differences and clang-tidy findings in the same change.
3. Record the change in `CHANGELOG.md`.
