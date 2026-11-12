#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

from quality import SKIPPED_DIRECTORY_NAMES


DEFAULT_FROM = "mylib"
SCRIPT_PATH = Path(__file__).resolve()
NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rename the cpp-library-template placeholder project name."
    )
    parser.add_argument(
        "new_name",
        nargs="?",
        help=(
            "New lowercase snake_case project name. If omitted, the current "
            "repository directory name is lowercased and '-' is converted to '_'."
        ),
    )
    parser.add_argument(
        "--from",
        dest="old_name",
        default=DEFAULT_FROM,
        help=f"Existing placeholder name to replace. Defaults to {DEFAULT_FROM}.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without modifying files.",
    )
    return parser.parse_args()


def infer_name(root: Path) -> str:
    return root.name.lower().replace("-", "_")


def validate_name(name: str, label: str) -> None:
    if not NAME_RE.fullmatch(name):
        raise SystemExit(
            f"{label} must use lowercase snake_case, for example: my_library"
        )


def should_skip_dir(path: Path) -> bool:
    return path.name in SKIPPED_DIRECTORY_NAMES or path.name.endswith(".dir")


def walk_tree(root: Path):
    """Yield each directory without descending into skipped or linked dirs."""
    for current_root, dirs, filenames in os.walk(root):
        current = Path(current_root)
        dirs[:] = [name for name in dirs if not should_skip_dir(current / name)]
        yield current, dirs, filenames


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current, _, filenames in walk_tree(root):
        for filename in filenames:
            files.append(current / filename)
    return files


def read_text(path: Path) -> str | None:
    # Never follow a symlink: a dangling link would fail, and a link to an
    # external file must keep its contents untouched.
    if path.is_symlink():
        return None
    data = path.read_bytes()
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def replacement_pairs(old_name: str, new_name: str) -> list[tuple[str, str]]:
    return [
        (old_name, new_name),
        (old_name.upper(), new_name.upper()),
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


def candidate_paths(root: Path, old_name: str, new_name: str) -> list[Path]:
    replacements = replacement_pairs(old_name, new_name)
    paths: list[Path] = []
    for current, dirs, filenames in walk_tree(root):
        for name in dirs:
            if any(old in name for old, _ in replacements):
                paths.append(current / name)
        for name in filenames:
            if any(old in name for old, _ in replacements):
                paths.append(current / name)
    return sorted(paths, key=lambda path: len(path.parts), reverse=True)


def rename_paths(
    paths: list[Path], old_name: str, new_name: str, dry_run: bool
) -> list[tuple[Path, Path]]:
    replacements = replacement_pairs(old_name, new_name)
    renamed: list[tuple[Path, Path]] = []
    for path in paths:
        target_name = path.name
        for old, new in replacements:
            target_name = target_name.replace(old, new)
        target = path.with_name(target_name)
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
    old_name = args.old_name

    validate_name(old_name, "Old project name")

    root = SCRIPT_PATH.parents[1]
    if args.new_name is None:
        new_name = infer_name(root)
        print(f"Inferred new project name: {new_name}")
    else:
        new_name = args.new_name

    validate_name(new_name, "New project name")

    if old_name == new_name:
        raise SystemExit("Old and new project names are the same.")

    paths_to_rename = candidate_paths(root, old_name, new_name)
    renamed_paths = rename_paths(paths_to_rename, old_name, new_name, args.dry_run)
    # Leave this script unchanged so that it keeps the template placeholder as
    # its default and its own names stay readable.
    files = [path for path in iter_files(root) if path != SCRIPT_PATH]
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
