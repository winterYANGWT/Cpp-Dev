#!/usr/bin/env python3

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
README = ROOT_DIR / "README.md"
CONTRIBUTING = ROOT_DIR / "CONTRIBUTING.md"
SECURITY = ROOT_DIR / "SECURITY.md"
CHANGELOG = ROOT_DIR / "CHANGELOG.md"
PULL_REQUEST_TEMPLATE = ROOT_DIR / ".github" / "pull_request_template.md"
ISSUE_FORMS = {
    ROOT_DIR / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml": (
        "version",
        "problem",
        "reproduction",
        "environment",
    ),
    ROOT_DIR / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml": (
        "problem",
        "proposal",
    ),
}
MARKDOWN_FILES = (README, CONTRIBUTING, SECURITY, CHANGELOG, PULL_REQUEST_TEMPLATE)
MARKDOWN_LINK_RE = re.compile(r"\]\(([^)\s]+)\)")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class CommunityHealthContractTest(unittest.TestCase):
    def test_readme_links_to_community_files(self) -> None:
        readme = read(README)

        for path in (CONTRIBUTING, SECURITY, CHANGELOG):
            with self.subTest(path=path.name):
                self.assertIn(f"]({path.name})", readme)

    def test_relative_links_resolve(self) -> None:
        for markdown in MARKDOWN_FILES:
            for target in MARKDOWN_LINK_RE.findall(read(markdown)):
                if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                    continue
                with self.subTest(file=markdown.name, link=target):
                    path = (markdown.parent / target.split("#", 1)[0]).resolve()
                    self.assertTrue(path.exists(), f"{target} does not exist")

    def test_contributing_guide_covers_checks_and_branches(self) -> None:
        contributing = read(CONTRIBUTING)

        self.assertIn("python3 scripts/quality.py check", contributing)
        self.assertIn("docs/release-branching.md", contributing)
        self.assertIn("SECURITY.md", contributing)

    def test_security_policy_asks_for_private_reports(self) -> None:
        security = read(SECURITY)

        self.assertIn("## Supported Versions", security)
        self.assertIn("## Reporting a Vulnerability", security)
        self.assertIn("Report a vulnerability", security)

    def test_changelog_has_unreleased_section(self) -> None:
        self.assertRegex(read(CHANGELOG), r"(?m)^## \[Unreleased\]$")

    def test_issue_forms_collect_required_fields(self) -> None:
        for form, field_ids in ISSUE_FORMS.items():
            text = read(form)
            for key in ("name", "description", "body"):
                with self.subTest(form=form.name, key=key):
                    self.assertRegex(text, rf"(?m)^{key}:")
            for field_id in field_ids:
                with self.subTest(form=form.name, field=field_id):
                    self.assertRegex(text, rf"(?m)^\s+id: {field_id}$")

    def test_pull_request_checklist(self) -> None:
        template = read(PULL_REQUEST_TEMPLATE)

        self.assertIn("- [ ] `python3 scripts/quality.py check` passes", template)
        self.assertIn("CHANGELOG.md", template)


if __name__ == "__main__":
    unittest.main()
