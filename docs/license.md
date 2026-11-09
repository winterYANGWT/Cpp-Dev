# License

New libraries created from this template use the GNU General Public License
version 3 (GPL-3.0) by default. The full text is in the root `LICENSE` file.

**GPL-3.0 is a recommendation, not a requirement.** The template recommends it
to encourage open source. A library created from this template may replace it
with another license. The author of this template permits projects created from
it to use the template's files under the license that the project chooses.

This page is not legal advice. Read the license texts, and ask a lawyer when
the choice matters for your project.

## Why GPL-3.0

GPL-3.0 keeps the library and the programs built on it open. Anyone who
distributes a program that uses the library must also make the program's
source code available under GPL-3.0-compatible terms. Improvements to the
library therefore stay open, and other people can study, reuse, and contribute
to them.

## What GPL-3.0 Means for Users of a Library

- A program that links the library, statically or dynamically, and is
  distributed must be released under GPL-3.0-compatible terms, together with
  its source code.
- Closed-source programs, and programs under licenses that are incompatible
  with GPL-3.0, cannot use the library.
- Using or modifying the library without distributing the result does not
  require releasing source code.

For a library, these terms are strict: they decide which programs can use it at
all. If that excludes users you want to reach, choose another license.

## Other Common Licenses

| License | What it asks of programs that use the library | Suits |
| --- | --- | --- |
| LGPL-3.0 | Programs may use any license. Changes to the library itself stay under LGPL-3.0, and users must be able to replace the library in the program with a modified version, which needs extra steps for static linking. | Libraries that should stay open themselves but be usable by closed-source programs. |
| MPL-2.0 | Programs may use any license. Changed files of the library stay under MPL-2.0. Static and dynamic linking are treated alike. | The same goal as LGPL-3.0, with simpler rules for static linking. |
| Apache-2.0 | Programs may use any license. Copies keep the license and notices, and contributors grant a patent license. | Libraries aimed at wide use, including commercial use, where patent terms matter. |
| MIT | Programs may use any license. Copies keep the copyright and license notice. | Small libraries aimed at the widest possible use. |

## Replacing the License

In a library created from this template:

1. Replace the root `LICENSE` file with the full text of the new license. Fill
   in the copyright line if the license has one, as MIT does. LGPL-3.0 adds
   permissions on top of GPL-3.0, so ship the GPL-3.0 text as well, for example
   as `COPYING` next to `COPYING.LESSER`.
2. Update the License section of `README.md`.
3. Rewrite this page for the new license, or delete it together with its links
   in `README.md`.
4. Update or delete `scripts/license_docs_contract_test.py`, which checks that
   `LICENSE`, this page, and `README.md` describe GPL-3.0 as the default.
5. If the project has added license information elsewhere, such as
   `SPDX-License-Identifier` comments in source files or license fields in
   packaging files, update it too. The template itself has neither.
