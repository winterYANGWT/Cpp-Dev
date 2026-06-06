#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


DEFAULT_FROM = "project_name"
NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
SKIP_DIRS = {
    ".cache",
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    "build",
    "cmake-build-debug",
    "cmake-build-release",
    "dist",
    "out",
    "temp",
    "tmp",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rename the CPP-DEV template project placeholder."
    )
    parser.add_argument(
        "new_project_name",
        nargs="?",
        help=(
            "New lowercase snake_case project name. If omitted, the current "
            "repository directory name is lowercased and '-' is converted to '_'."
        ),
    )
    parser.add_argument(
        "--from",
        dest="old_project_name",
        default=DEFAULT_FROM,
        help=f"Existing placeholder name to replace. Defaults to {DEFAULT_FROM}.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without modifying files.",
    )
    return parser.parse_args()


def infer_project_name(root: Path) -> str:
    return root.name.lower().replace("-", "_")


def validate_name(name: str, label: str) -> None:
    if not NAME_RE.fullmatch(name):
        raise SystemExit(
            f"{label} must use lowercase snake_case, for example: my_library"
        )


def should_skip_dir(path: Path) -> bool:
    return path.name in SKIP_DIRS or path.name.endswith(".dir")


def has_skipped_relative_parent(root: Path, path: Path) -> bool:
    relative = path.relative_to(root)
    return any(part in SKIP_DIRS or part.endswith(".dir") for part in relative.parts[:-1])


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current_root, dirs, filenames in os.walk(root):
        current = Path(current_root)
        dirs[:] = [name for name in dirs if not should_skip_dir(current / name)]
        for filename in filenames:
            files.append(current / filename)
    return files


def read_text(path: Path) -> str | None:
    data = path.read_bytes()
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def export_macro_name(project_name: str) -> str:
    return f"{project_name.upper()}_EXPORT"


def header_guard_name(project_name: str) -> str:
    return f"{project_name.upper()}_{project_name.upper()}_H_"


def replacement_pairs(old_name: str, new_name: str) -> list[tuple[str, str]]:
    return [
        (old_name, new_name),
        (export_macro_name(old_name), export_macro_name(new_name)),
        (header_guard_name(old_name), header_guard_name(new_name)),
    ]


def replace_file_contents(
    files: list[Path], old_name: str, new_name: str, dry_run: bool
) -> list[Path]:
    replacements = replacement_pairs(old_name, new_name)
    changed: list[Path] = []
    for path in files:
        text = read_text(path)
        if text is None or not any(old in text for old, _ in replacements):
            continue
        changed.append(path)
        if dry_run:
            continue
        updated = text
        for old, new in replacements:
            updated = updated.replace(old, new)
        path.write_text(updated, encoding="utf-8")
    return changed


def candidate_paths(root: Path, old_name: str) -> list[Path]:
    paths = [path for path in root.rglob("*") if old_name in path.name]
    paths = [path for path in paths if not has_skipped_relative_parent(root, path)]
    return sorted(paths, key=lambda path: len(path.parts), reverse=True)


def rename_paths(
    paths: list[Path], old_name: str, new_name: str, dry_run: bool
) -> list[tuple[Path, Path]]:
    renamed: list[tuple[Path, Path]] = []
    for path in paths:
        target = path.with_name(path.name.replace(old_name, new_name))
        if target == path:
            continue
        if target.exists():
            raise SystemExit(f"Cannot rename {path} to {target}: target already exists.")
        renamed.append((path, target))
        if not dry_run:
            path.rename(target)
    return renamed


def main() -> int:
    args = parse_args()
    old_name = args.old_project_name

    validate_name(old_name, "Old project name")

    root = Path(__file__).resolve().parents[1]
    if args.new_project_name is None:
        new_name = infer_project_name(root)
        print(f"Inferred new project name: {new_name}")
    else:
        new_name = args.new_project_name

    validate_name(new_name, "New project name")

    if old_name == new_name:
        raise SystemExit("Old and new project names are the same.")

    paths_to_rename = candidate_paths(root, old_name)
    renamed_paths = rename_paths(paths_to_rename, old_name, new_name, args.dry_run)
    files = iter_files(root)
    changed_files = replace_file_contents(files, old_name, new_name, args.dry_run)

    action = "Would update" if args.dry_run else "Updated"
    for path in changed_files:
        print(f"{action} file content: {path.relative_to(root)}")

    action = "Would rename" if args.dry_run else "Renamed"
    for source, target in renamed_paths:
        print(f"{action}: {source.relative_to(root)} -> {target.relative_to(root)}")

    if not changed_files and not renamed_paths:
        print(f"No occurrences of {old_name!r} found.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
