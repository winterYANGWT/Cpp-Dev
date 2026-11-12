#!/usr/bin/env python3

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
CI_WORKFLOW = ROOT_DIR / ".github" / "workflows" / "ci.yml"
STEP_RE = re.compile(r"^      - name: (.+)$", re.M)
USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*(.*)$")
PINNED_ACTION_RE = re.compile(
    r"^(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?:/[A-Za-z0-9_./-]+)?@"
    r"(?P<sha>[0-9a-f]{40}) # v"
    r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$"
)
CONCURRENCY_GROUP = "${{ github.workflow }}-${{ github.ref }}"


def ci_jobs(workflow: str) -> dict[str, str]:
    jobs_section = workflow.split("\njobs:\n", 1)[1]
    parts = re.split(r"^  ([A-Za-z0-9_-]+):\n", jobs_section, flags=re.M)
    return dict(zip(parts[1::2], parts[2::2]))


def job_steps(job: str) -> list[tuple[str, str]]:
    matches = list(STEP_RE.finditer(job))
    steps: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(job)
        steps.append((match.group(1).strip(), job[match.start() : end]))
    return steps


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def top_level_blocks(workflow: str, key: str) -> list[list[str]]:
    """Returns each column-0 `key:` block, up to the next column-0 line."""
    lines = workflow.splitlines()
    blocks: list[list[str]] = []
    for index, line in enumerate(lines):
        if not re.match(rf"^{re.escape(key)}:", line):
            continue
        block = [line]
        for following in lines[index + 1 :]:
            if not following.strip() or following.lstrip().startswith("#"):
                block.append(following)
                continue
            if not following[0].isspace():
                break
            block.append(following)
        blocks.append(block)
    return blocks


def block_entries(block: list[str]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line in block[1:]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^\s+([A-Za-z0-9_-]+):[ \t]*(.*)$", line)
        if match:
            entries.append((match.group(1), unquote(match.group(2).strip())))
    return entries


def step_with_settings(step: str) -> dict[str, str]:
    """Returns the `key: value` lines of a step's `with:` block."""
    settings: dict[str, str] = {}
    in_with = False
    for line in step.splitlines():
        if re.match(r"^        with:\s*$", line):
            in_with = True
            continue
        if not in_with:
            continue
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if len(line) - len(line.lstrip()) <= 8:
            break
        match = re.match(r"^\s+([A-Za-z0-9_-]+):[ \t]*(.*)$", line)
        if match:
            settings[match.group(1)] = unquote(match.group(2).strip())
    return settings


def action_uses(workflow: str) -> list[tuple[str, str, str, str, int]]:
    """Returns (line, repo, sha, version, major) for every `uses:` line."""
    actions: list[tuple[str, str, str, str, int]] = []
    for line in workflow.splitlines():
        match = USES_RE.match(line)
        if not match:
            continue
        value = match.group(1).strip()
        pinned = PINNED_ACTION_RE.match(value)
        if pinned is None:
            actions.append((line.strip(), "", "", "", -1))
            continue
        version = (
            f"v{pinned.group('major')}.{pinned.group('minor')}."
            f"{pinned.group('patch')}"
        )
        actions.append(
            (
                line.strip(),
                pinned.group("repo"),
                pinned.group("sha"),
                version,
                int(pinned.group("major")),
            )
        )
    return actions


class CiHardeningContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = CI_WORKFLOW.read_text(encoding="utf-8")
        self.actions = action_uses(self.workflow)

    def test_token_permissions_are_read_only(self) -> None:
        blocks = top_level_blocks(self.workflow, "permissions")

        self.assertEqual(
            len(blocks),
            1,
            f"Expected exactly one top-level permissions block, found {len(blocks)}.",
        )
        self.assertEqual(
            blocks[0][0].strip(),
            "permissions:",
            f"Expected a mapping permissions block, found {blocks[0][0]!r}.",
        )
        entries = block_entries(blocks[0])
        self.assertEqual(
            entries,
            [("contents", "read")],
            "Expected the top-level permissions block to contain exactly "
            f"'contents: read', found {entries!r}.",
        )
        self.assertNotIn(
            "write-all",
            self.workflow,
            "The workflow must not grant 'write-all' permissions.",
        )

    def test_concurrency_cancels_older_runs(self) -> None:
        blocks = top_level_blocks(self.workflow, "concurrency")

        self.assertEqual(
            len(blocks),
            1,
            f"Expected exactly one top-level concurrency block, found {len(blocks)}.",
        )
        self.assertEqual(
            blocks[0][0].strip(),
            "concurrency:",
            f"Expected a mapping concurrency block, found {blocks[0][0]!r}.",
        )
        settings = dict(block_entries(blocks[0]))
        self.assertEqual(
            settings.get("group"),
            CONCURRENCY_GROUP,
            "Expected concurrency group "
            f"{CONCURRENCY_GROUP!r}, found {settings.get('group')!r}.",
        )
        self.assertEqual(
            settings.get("cancel-in-progress"),
            "true",
            "Expected 'cancel-in-progress: true', found "
            f"{settings.get('cancel-in-progress')!r}.",
        )

    def test_actions_are_pinned_to_commit_shas(self) -> None:
        self.assertTrue(self.actions, "Expected at least one 'uses:' line.")
        for line, repo, _sha, _version, _major in self.actions:
            self.assertTrue(
                repo,
                "Expected '<owner>/<repo>[/<path>]@<40 lowercase hex digits> "
                f"# vX.Y.Z', found {line!r}.",
            )

    def test_each_action_uses_one_version(self) -> None:
        versions: dict[str, set[tuple[str, str]]] = {}
        for _line, repo, sha, version, _major in self.actions:
            if not repo:
                continue
            versions.setdefault(repo, set()).add((sha, version))

        for repo, found in versions.items():
            self.assertEqual(
                len(found),
                1,
                f"Expected one SHA and version for {repo}, found {sorted(found)!r}.",
            )

    def test_actions_do_not_use_node20_releases(self) -> None:
        for line, repo, _sha, version, major in self.actions:
            if repo not in ("actions/checkout", "actions/cache"):
                continue
            self.assertGreaterEqual(
                major,
                5,
                f"Expected {repo} at v5 or later for node24, found {version!r} "
                f"in {line!r}.",
            )

    def test_checkout_does_not_persist_credentials(self) -> None:
        jobs = ci_jobs(self.workflow)
        self.assertTrue(jobs, "Expected at least one job in the workflow.")
        for job_name, job in jobs.items():
            checkouts = [
                block
                for _step_name, block in job_steps(job)
                if "actions/checkout@" in block
            ]
            self.assertEqual(
                len(checkouts),
                1,
                f"Expected exactly one actions/checkout step in job {job_name!r}, "
                f"found {len(checkouts)}.",
            )
            settings = step_with_settings(checkouts[0])
            self.assertEqual(
                settings.get("persist-credentials"),
                "false",
                f"Expected 'persist-credentials: false' under with: in job "
                f"{job_name!r}, found {settings.get('persist-credentials')!r}.",
            )


if __name__ == "__main__":
    unittest.main()
