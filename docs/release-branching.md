# Release Branching Contract

This project uses SemVer tags and a small set of long-lived branch roles. The
contract keeps `main` tied to the latest published release while allowing normal
development, release preparation, and old-version patch maintenance to happen
without version-order ambiguity.

## Branch Roles

| Branch pattern | Purpose | Lifetime |
| --- | --- | --- |
| `main` | Latest published release. | Long-lived. |
| `dev` | Integration branch for the next release. | Long-lived. |
| `feature/<name>` | Ordinary feature work. | Short-lived. |
| `fix/<name>` | Ordinary fixes for unreleased work. | Short-lived. |
| `release/vX.Y.Z` | Release preparation for SemVer version `vX.Y.Z`. | Short-lived. |
| `hotfix/vX.Y.Z` | Patch work for an already published version. | Short-lived. |
| `support/vX.Y.x` | Maintenance line for an older minor version. | Long-lived only when old-version support is needed. |

## Core Rules

- `main` always points at the latest published release.
- Published releases are immutable SemVer tags named `vX.Y.Z`.
- `dev` may be ahead of `main`; it is the integration branch for the next release.
- Normal features branch from `dev` and merge back to `dev`.
- `release/vX.Y.Z` branches from `dev` and is used only for release preparation.
- A hotfix for the latest release branches from `main`.
- A hotfix for an older release branches from the matching `support/vX.Y.x` line.
- Hotfix changes must be synchronized forward to `dev` and any active
  `release/*` branch that needs the fix.

## CI Policy

The default GitHub Actions CI trigger is intentionally release-oriented:

- CI runs when `main` is updated.
- CI runs when a `release/**` branch is updated.
- CI runs for pull requests targeting `main` or `release/**`.
- CI can be started manually with `workflow_dispatch`.
- `dev` does not run CI by default.

The `dev` branch is an integration branch for upcoming work, but this template
does not force every update to run the full CI matrix. Developers are expected
to run the local quality gate before publishing changes when practical:

```sh
python3 scripts/quality.py check
```

Projects that want stricter integration can opt in by adding `dev` to the
workflow branch filters. Projects that actively maintain old support lines can
also add `support/**` to the same filters.

## Normal Development

Create feature and ordinary fix branches from `dev`:

```text
dev
  -> feature/<name>
  -> dev
```

Use `fix/<name>` for fixes to unreleased work:

```text
dev
  -> fix/<name>
  -> dev
```

Do not merge ordinary feature or fix branches directly into `main`.

## Normal Release

When `dev` is ready for a SemVer release:

```text
dev
  -> release/v1.4.0
  -> main
  -> tag v1.4.0
```

The `release/v1.4.0` branch should contain only release preparation changes:
version updates, changelog updates, packaging checks, documentation corrections,
CI corrections, and blocking bug fixes.

If blocking fixes are made on the release branch, synchronize them back to `dev`
after the release:

```text
release/v1.4.0
  -> main
  -> tag v1.4.0
  -> dev
```

Delete the `release/v1.4.0` branch after the release is complete unless there is
a specific operational reason to keep it temporarily.

## Latest-Release Hotfix

If `main` currently points at `v1.4.0` and the project must publish `v1.4.1`:

```text
main
  -> hotfix/v1.4.1
  -> main
  -> tag v1.4.1
  -> dev
```

If an active `release/v1.5.0` branch exists, synchronize the same fix there too:

```text
hotfix/v1.4.1
  -> release/v1.5.0
```

The active release branch is not the default target for a hotfix. It receives
the fix only when it exists and would otherwise miss a required correction.

## Old-Version Hotfix

If `main` has already moved to `v1.4.0` and the project must publish a patch for
the older `v1.3.x` line, do not branch from `main` and do not merge that patch
release back into `main` as a version rollback.

Create or reuse a support branch from the old release tag:

```text
tag v1.3.0
  -> support/v1.3.x
  -> hotfix/v1.3.1
  -> support/v1.3.x
  -> tag v1.3.1
```

Then synchronize the fix forward where it is still relevant:

```text
hotfix/v1.3.1
  -> dev
  -> active release/* if needed
  -> main only if the latest release also needs this exact fix
```

Prefer cherry-picking the small fix forward when the old support line has
diverged from newer versions. Do not merge an entire old support line into a
newer branch unless that history relationship is intentional and reviewed.

## Naming Summary

```text
main              latest published release
dev               next release integration branch
feature/<name>    ordinary feature work from dev
fix/<name>        ordinary unreleased fix from dev or release/*
release/vX.Y.Z    release preparation branch
hotfix/vX.Y.Z     patch work branch for a published version
support/vX.Y.x    old minor maintenance line
tag vX.Y.Z        immutable published release
```
