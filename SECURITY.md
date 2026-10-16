# Security Policy

<!--
Template: projects created from CPP-DEV should list the versions they support
and enable private vulnerability reporting in the repository settings
(Settings > Code security > Private vulnerability reporting).
-->

## Supported Versions

Security fixes are made for the latest published release. An older minor
version receives fixes only while it has an active `support/vX.Y.x` branch, as
described in the [Release Branching Contract](docs/release-branching.md).

| Version | Supported |
| --- | --- |
| Latest release | Yes |
| Older releases | Only while a `support/vX.Y.x` branch is active |

## Reporting a Vulnerability

Do not report security vulnerabilities through public issues, pull requests, or
discussions.

Report them privately through GitHub Security Advisories: open the repository's
**Security** tab and select **Report a vulnerability**. If that option is not
available, open a public issue that asks the maintainers for a private contact,
without including any details about the vulnerability.

Please include:

- The affected version or commit.
- A description of the vulnerability and its impact.
- Steps or code to reproduce it.

The maintainers will acknowledge the report, investigate it, and coordinate a
fix and its disclosure with you.
