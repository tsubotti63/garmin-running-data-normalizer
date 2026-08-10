# Main Branch Protection

The repository's default branch, `main`, is governed by the active GitHub
Ruleset `main-protection`.

## Merge requirements

- Changes to `main` must arrive through a pull request.
- Required approvals are set to `0` for the solo-maintainer workflow.
- The exact required CI checks are `test` and `windows-runtime`.
- Branches are not required to be up to date with `main` initially.
- Conversation resolution is not required initially.

## History protection

- Force pushes to `main` are blocked.
- Deletion of `main` is restricted.
- No routine bypass actor is configured; administrator enforcement remains
  active.

## Release boundary

PyPI/TestPyPI publication, OIDC Trusted Publishing, Environment reviewers,
tags, and GitHub Releases are separate release operations. The release
workflow is not a Required Check for ordinary pull requests.

This document records repository governance. It does not redefine Product
runtime, dataset, schema, or release contracts.
