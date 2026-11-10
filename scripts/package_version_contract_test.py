#!/usr/bin/env python3

"""Check the shared-library SOVERSION and package version contract.

The installed shared library and the installed package version file must use
the same rule: only patch releases are ABI compatible, before and after 1.0.
These checks run on Linux because they inspect SONAMEs and `.so` symlinks.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import rename_project


ROOT_DIR = Path(__file__).resolve().parents[1]
CMAKE_LISTS = ROOT_DIR / "CMakeLists.txt"
README = ROOT_DIR / "README.md"
FUTURE_VERSION = (1, 2, 3)

PROJECT_RE = re.compile(
    r"\bproject\s*\(\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s+VERSION\s+"
    r"(?P<version>\d+\.\d+\.\d+)",
    re.IGNORECASE,
)
INSTALL_CONTRACT_RE = re.compile(
    r"^## Install Contract[ \t]*$(.*?)(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)


def format_version(version: tuple[int, int, int]) -> str:
    return ".".join(str(part) for part in version)


def format_series(version: tuple[int, int, int]) -> str:
    return f"{version[0]}.{version[1]}"


def read_project(cmake_lists: Path) -> tuple[str, tuple[int, int, int]]:
    text = cmake_lists.read_text(encoding="utf-8")
    match = PROJECT_RE.search(text)
    if match is None:
        raise AssertionError(
            f"{cmake_lists} has no project(<name> VERSION X.Y.Z) declaration."
        )
    major, minor, patch = (
        int(part) for part in match.group("version").split(".")
    )
    return match.group("name"), (major, minor, patch)


def set_project_version(
    cmake_lists: Path, version: tuple[int, int, int]
) -> None:
    text = cmake_lists.read_text(encoding="utf-8")
    match = PROJECT_RE.search(text)
    if match is None:
        raise AssertionError(
            f"{cmake_lists} has no project(<name> VERSION X.Y.Z) declaration."
        )
    updated = (
        text[: match.start("version")]
        + format_version(version)
        + text[match.end("version") :]
    )
    cmake_lists.write_text(updated, encoding="utf-8")


def ignore_when_copying(directory: str, names: list[str]) -> set[str]:
    # Skip what the rename skips, and local symlinks such as `review`, whose
    # targets lie outside the repository.
    return {
        name
        for name in names
        if rename_project.should_skip_dir(Path(directory) / name)
        or (Path(directory) / name).is_symlink()
    }


def run_checked(command: list[str], cwd: Path | None = None) -> None:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"Command failed with exit code {result.returncode}: "
            f"{' '.join(command)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def generator_arguments() -> list[str]:
    # The CI contract job installs only Ninja from PyPI and has no make, while
    # a local machine may have only make. An explicit generator wins.
    if "CMAKE_GENERATOR" in os.environ:
        return []
    if shutil.which("ninja") is not None:
        return ["-G", "Ninja"]
    return []


def build_and_install(
    source: Path,
    build: Path,
    install: Path,
    name: str,
) -> Path:
    run_checked(
        [
            "cmake",
            "-S",
            str(source),
            "-B",
            str(build),
            *generator_arguments(),
            "-DBUILD_SHARED_LIBS=ON",
            f"-D{name}_BUILD_TESTS=OFF",
            "-DCMAKE_BUILD_TYPE=Release",
        ]
    )
    run_checked(["cmake", "--build", str(build), "--config", "Release"])
    run_checked(
        [
            "cmake",
            "--install",
            str(build),
            "--config",
            "Release",
            "--prefix",
            str(install),
        ]
    )
    return install


def installed_library_files(install_dir: Path, name: str) -> list[Path]:
    return sorted(install_dir.glob(f"lib*/lib{name}.so*"))


def expected_library_names(
    name: str, version: tuple[int, int, int]
) -> tuple[str, str, str]:
    return (
        f"lib{name}.so",
        f"lib{name}.so.{format_series(version)}",
        f"lib{name}.so.{format_version(version)}",
    )


def soname_tool() -> str | None:
    for tool in ("objdump", "readelf"):
        if shutil.which(tool) is not None:
            return tool
    return None


def read_soname(library: Path, tool: str) -> str:
    if tool == "objdump":
        result = subprocess.run(
            ["objdump", "-p", str(library)],
            capture_output=True,
            text=True,
            check=False,
        )
        output = result.stdout + result.stderr
        if result.returncode != 0:
            raise AssertionError(
                f"objdump failed for {library} with exit code "
                f"{result.returncode}:\n{output}"
            )
        for line in result.stdout.splitlines():
            fields = line.split()
            if fields and fields[0] == "SONAME":
                return fields[-1]
    else:
        result = subprocess.run(
            ["readelf", "-d", str(library)],
            capture_output=True,
            text=True,
            check=False,
        )
        output = result.stdout + result.stderr
        if result.returncode != 0:
            raise AssertionError(
                f"readelf failed for {library} with exit code "
                f"{result.returncode}:\n{output}"
            )
        for line in result.stdout.splitlines():
            match = re.search(r"\(SONAME\).*\[(?P<soname>[^\]]+)\]", line)
            if match is not None:
                return match.group("soname")
    raise AssertionError(f"Could not read a SONAME from {library} with {tool}.")


def check_soname(
    case: unittest.TestCase,
    install_dir: Path,
    name: str,
    version: tuple[int, int, int],
) -> None:
    tool = soname_tool()
    if tool is None:
        case.skipTest("Neither objdump nor readelf is available.")
    expected = f"lib{name}.so.{format_series(version)}"
    full_name = expected_library_names(name, version)[2]
    files = installed_library_files(install_dir, name)
    library = next((path for path in files if path.name == full_name), None)
    if library is None:
        case.fail(
            f"Expected an installed library named {full_name} under "
            f"{install_dir}, but found "
            f"{[path.name for path in files]}."
        )
    actual = read_soname(library, tool)
    case.assertEqual(
        actual,
        expected,
        f"SONAME mismatch for {library}: expected {expected!r}, "
        f"got {actual!r}.",
    )


def check_symlink_chain(
    case: unittest.TestCase,
    install_dir: Path,
    name: str,
    version: tuple[int, int, int],
) -> None:
    unversioned_name, series_name, full_name = expected_library_names(
        name, version
    )
    files = installed_library_files(install_dir, name)
    actual_names = [path.name for path in files]
    case.assertEqual(
        sorted(actual_names),
        sorted([unversioned_name, series_name, full_name]),
        f"Expected exactly three library entries under {install_dir}: "
        f"{[unversioned_name, series_name, full_name]}; got {actual_names}.",
    )
    by_name = {path.name: path for path in files}
    unversioned = by_name[unversioned_name]
    series = by_name[series_name]
    full = by_name[full_name]

    case.assertTrue(
        unversioned.is_symlink(),
        f"{unversioned_name} must be a symbolic link, but it is a regular "
        "file.",
    )
    case.assertTrue(
        series.is_symlink(),
        f"{series_name} must be a symbolic link, but it is a regular file.",
    )
    case.assertFalse(
        full.is_symlink(),
        f"{full_name} must be a regular file, but it is a symbolic link.",
    )
    case.assertTrue(
        full.is_file(),
        f"{full_name} must be a regular file, but it does not exist.",
    )
    case.assertEqual(
        unversioned.readlink().name,
        series_name,
        f"{unversioned_name} must point to {series_name}, but it points to "
        f"{unversioned.readlink()}.",
    )
    case.assertEqual(
        series.readlink().name,
        full_name,
        f"{series_name} must point to {full_name}, but it points to "
        f"{series.readlink()}.",
    )


def compatibility_requests(
    version: tuple[int, int, int],
) -> tuple[list[str], list[str]]:
    major, minor, patch = version
    compatible = [f"{major}.{minor}", format_version(version)]
    incompatible = [
        f"{major}.{minor}.{patch + 1}",
        f"{major}.{minor + 1}",
        f"{major + 1}.{minor}",
    ]
    if minor > 0:
        incompatible.append(f"{major}.{minor - 1}")
    return compatible, incompatible


def find_config_version(install_dir: Path, name: str) -> Path:
    matches = sorted(install_dir.rglob(f"{name}ConfigVersion.cmake"))
    if len(matches) != 1:
        relative = [
            str(path.relative_to(install_dir)) for path in matches
        ]
        raise AssertionError(
            f"Expected exactly one installed {name}ConfigVersion.cmake under "
            f"{install_dir}, but found {relative}."
        )
    return matches[0]


def probe_config_version(
    version_file: Path,
    requests: list[str],
    temp_dir: Path,
) -> dict[str, bool]:
    lines: list[str] = []
    for request in requests:
        components = [int(part) for part in request.split(".")]
        count = len(components)
        while len(components) < 3:
            components.append(0)
        major, minor, patch = components
        lines.extend(
            [
                f'set(PACKAGE_FIND_VERSION "{request}")',
                f"set(PACKAGE_FIND_VERSION_MAJOR {major})",
                f"set(PACKAGE_FIND_VERSION_MINOR {minor})",
                f"set(PACKAGE_FIND_VERSION_PATCH {patch})",
                f"set(PACKAGE_FIND_VERSION_COUNT {count})",
                "unset(PACKAGE_VERSION_COMPATIBLE)",
                "unset(PACKAGE_VERSION_UNSUITABLE)",
                f'include("{version_file.as_posix()}")',
                "if(PACKAGE_VERSION_COMPATIBLE)",
                f'  message("RESULT|{request}|TRUE")',
                "else()",
                f'  message("RESULT|{request}|FALSE")',
                "endif()",
            ]
        )

    script = temp_dir / "probe_config_version.cmake"
    script.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = subprocess.run(
        ["cmake", "-P", str(script)],
        cwd=temp_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        raise AssertionError(
            f"cmake -P failed with exit code {result.returncode}:\n{output}"
        )

    results: dict[str, bool] = {}
    for line in output.splitlines():
        if not line.startswith("RESULT|"):
            continue
        _, request, value = line.split("|")
        results[request] = value == "TRUE"
    return results


def check_config_version(
    case: unittest.TestCase,
    install_dir: Path,
    name: str,
    version: tuple[int, int, int],
) -> None:
    version_file = find_config_version(install_dir, name)
    compatible, incompatible = compatibility_requests(version)
    expected = {request: True for request in compatible}
    expected.update({request: False for request in incompatible})
    with tempfile.TemporaryDirectory(
        prefix="package-version-probe-"
    ) as temp:
        actual = probe_config_version(
            version_file, list(expected), Path(temp)
        )
    case.assertEqual(
        actual,
        expected,
        f"Version compatibility mismatch for {version_file}: "
        f"expected {expected}, got {actual}.",
    )


def check_readme_install_contract(case: unittest.TestCase) -> None:
    text = README.read_text(encoding="utf-8")
    match = INSTALL_CONTRACT_RE.search(text)
    if match is None:
        case.fail("README.md has no '## Install Contract' section.")
    section = match.group(1)
    for required in ("`SOVERSION`", "`major.minor`", "`SameMinorVersion`"):
        case.assertIn(
            required,
            section,
            "The README.md Install Contract section must mention "
            f"{required}.",
        )


class InstallContractDocsTest(unittest.TestCase):
    def test_readme_documents_the_install_contract(self) -> None:
        check_readme_install_contract(self)


@unittest.skipUnless(
    sys.platform.startswith("linux"),
    "SONAME and .so naming checks require Linux.",
)
@unittest.skipUnless(
    shutil.which("cmake") is not None,
    "cmake is not on PATH.",
)
class PackageVersionContractTest(unittest.TestCase):
    name: str
    version: tuple[int, int, int]
    current_install: Path
    future_install: Path

    @classmethod
    def setUpClass(cls) -> None:
        temp_dir = tempfile.TemporaryDirectory(
            prefix="package-version-contract-"
        )
        cls.addClassCleanup(temp_dir.cleanup)
        base = Path(temp_dir.name)
        cls.name, cls.version = read_project(CMAKE_LISTS)

        cls.current_install = build_and_install(
            ROOT_DIR,
            base / "current" / "build",
            base / "current" / "install",
            cls.name,
        )

        future_root = base / "future" / "repo"
        shutil.copytree(ROOT_DIR, future_root, ignore=ignore_when_copying)
        set_project_version(future_root / "CMakeLists.txt", FUTURE_VERSION)
        cls.future_install = build_and_install(
            future_root,
            base / "future" / "build",
            base / "future" / "install",
            cls.name,
        )

    def test_soname_matches_major_minor(self) -> None:
        for install_dir, version in (
            (self.current_install, self.version),
            (self.future_install, FUTURE_VERSION),
        ):
            with self.subTest(version=format_version(version)):
                check_soname(self, install_dir, self.name, version)

    def test_symlink_chain_uses_the_full_version(self) -> None:
        for install_dir, version in (
            (self.current_install, self.version),
            (self.future_install, FUTURE_VERSION),
        ):
            with self.subTest(version=format_version(version)):
                check_symlink_chain(self, install_dir, self.name, version)

    def test_package_version_file_accepts_only_the_same_minor(self) -> None:
        for install_dir, version in (
            (self.current_install, self.version),
            (self.future_install, FUTURE_VERSION),
        ):
            with self.subTest(version=format_version(version)):
                check_config_version(self, install_dir, self.name, version)


if __name__ == "__main__":
    unittest.main()
