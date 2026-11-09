#!/usr/bin/env python3

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
LICENSE = ROOT_DIR / "LICENSE"
LICENSE_DOC = ROOT_DIR / "docs" / "license.md"
README = ROOT_DIR / "README.md"

LICENSE_TEXT_MARKERS = ("GNU GENERAL PUBLIC LICENSE", "Version 3, 29 June 2007")
RECOMMENDATION_STATEMENT = "GPL-3.0 is a recommendation, not a requirement."
LICENSE_DOC_PHRASES = (
    "encourage open source",
    "may replace it with another license",
    "permits projects created from it to use the template's files under "
    "the license that the project chooses",
)
OTHER_LICENSE_ROWS = ("| LGPL-3.0 |", "| MPL-2.0 |", "| Apache-2.0 |", "| MIT |")
REPLACEMENT_FILES = (
    "`LICENSE`",
    "`README.md`",
    "`scripts/license_docs_contract_test.py`",
)
README_LICENSE_SECTION_PHRASES = ("GPL-3.0", "not a requirement", "(docs/license.md)")
REMOVED_README_PHRASES = ("do not reopen", "settled template default")


def read_text(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"{path} was not found")
    return path.read_text(encoding="utf-8")


def one_line(text: str) -> str:
    return " ".join(text.split())


def section_body(text: str, heading: str, document: Path) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}[ \t]*\n(.*?)(?=^## |\Z)", text, re.M | re.S
    )
    if match is None:
        raise AssertionError(f"{document.name} has no '## {heading}' section")
    return match.group(1)


class LicenseDocsContractTest(unittest.TestCase):
    def test_license_file_contains_the_gpl_3_0_text(self) -> None:
        text = read_text(LICENSE)

        for marker in LICENSE_TEXT_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, text, f"LICENSE is missing {marker!r}")

    def test_license_doc_states_gpl_is_not_a_requirement(self) -> None:
        text = one_line(read_text(LICENSE_DOC))

        self.assertIn(
            RECOMMENDATION_STATEMENT,
            text,
            f"docs/license.md is missing {RECOMMENDATION_STATEMENT!r}",
        )

    def test_license_doc_allows_replacing_the_license(self) -> None:
        text = one_line(read_text(LICENSE_DOC))

        for phrase in LICENSE_DOC_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertIn(
                    phrase, text, f"docs/license.md is missing {phrase!r}"
                )

    def test_license_doc_lists_other_common_licenses(self) -> None:
        text = read_text(LICENSE_DOC)

        for row in OTHER_LICENSE_ROWS:
            with self.subTest(row=row):
                self.assertRegex(
                    text,
                    rf"(?m)^{re.escape(row)}",
                    f"docs/license.md has no table row starting with {row!r}",
                )

    def test_license_doc_replacing_section_names_the_files_to_update(self) -> None:
        body = section_body(
            read_text(LICENSE_DOC), "Replacing the License", LICENSE_DOC
        )

        for name in REPLACEMENT_FILES:
            with self.subTest(name=name):
                self.assertIn(
                    name,
                    body,
                    f"'## Replacing the License' does not mention {name}",
                )

    def test_readme_documentation_section_links_to_the_license_page(self) -> None:
        body = one_line(section_body(read_text(README), "Documentation", README))

        self.assertIn(
            "(docs/license.md)",
            body,
            "'## Documentation' in README.md does not link to docs/license.md",
        )

    def test_readme_license_section_states_the_default_and_links_the_page(self) -> None:
        body = one_line(section_body(read_text(README), "License", README))

        for phrase in README_LICENSE_SECTION_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertIn(
                    phrase, body, f"'## License' in README.md is missing {phrase!r}"
                )

    def test_readme_drops_the_settled_default_wording(self) -> None:
        readme = one_line(read_text(README)).lower()

        for phrase in REMOVED_README_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertNotIn(
                    phrase, readme, f"README.md still contains {phrase!r}"
                )


if __name__ == "__main__":
    unittest.main()
