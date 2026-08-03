# Security policy

This is the organisation-wide default. A repository that ships its own
`SECURITY.md` overrides it.

## Reporting a vulnerability

**Do not open a public issue.** Use GitHub's private vulnerability reporting on
the affected repository: **Security → Report a vulnerability**. That opens a
private thread visible only to the maintainers, and it keeps the report attached
to the code it concerns.

Please include:

- the repository and the version or commit you tested,
- what an attacker can do, not only what is wrong,
- the smallest set of steps that reproduces it,
- the platform, if it matters — the projects are tested on Linux, macOS and
  Windows and a finding can be specific to one.

## What to expect

- An acknowledgement that the report was read, with a first assessment.
- A fix, or an explanation of why the behaviour is intended, before the report
  is closed.
- Credit in the release notes, unless you would rather not be named.

These are intentions, not a contractual SLA — this is a small open-source
organisation, and promising a response window we cannot hold to would be worse
than saying so plainly.

## Scope

In scope: the code in this organisation's repositories, its published packages
on PyPI, and the documentation sites.

Out of scope: findings in third-party dependencies (report those upstream, and
tell us so we can pin or patch), and vulnerabilities that require an attacker to
already control the machine running the code.

## Supported versions

Fixes land on the default branch and in the next release. Older releases are not
patched — the projects are pre-1.0 and the upgrade path is short.
