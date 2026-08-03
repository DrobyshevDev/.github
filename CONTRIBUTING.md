# Contributing

This is the organisation-wide default. A repository that ships its own
`CONTRIBUTING.md` overrides it, and its version wins wherever the two disagree.

## Before you write code

Open an issue describing the change. For a bug, the reproduction matters more
than the diagnosis; for a feature, the use case matters more than the API you
have in mind. A short issue first is cheaper than a large pull request that has
to be rewritten.

Small, obvious fixes — a broken link, a typo, a wrong type annotation — do not
need an issue. Send the pull request.

## The pull request

- One change per pull request. A refactor bundled with a fix makes both harder
  to review and impossible to revert separately.
- Say what breaks if the change is wrong. That is the sentence a reviewer needs
  and the hardest one to reconstruct from a diff.
- CI runs on Linux, macOS and Windows. It has to be green before review, not
  after — a red pipeline means the reviewer is reading code that does not run.

## What review will hold you to

These are the standards behind every repository here, so they are worth reading
once rather than discovering one comment at a time.

**Errors teach.** A message is read at the worst possible moment by someone who
does not have the source open. It should say what went wrong *and* what to do
next, and list the alternatives when there are any.

**Tests are named after the guarantee they protect.**
`test_assignment_is_stable_when_rows_are_added`, not `test_split`. A test whose
name does not survive being read aloud is not documenting anything.

**Verification beats assertion.** A green pipeline on one machine is not
evidence. A number in a README — an accuracy, a benchmark, a "this works on
Windows" — is pinned by a test or by the script that produced it, because prose
rots quietly and a failing test does not.

**Comments explain why.** The code already says what it does. The comment is for
the constraint a reader cannot see.

**No hidden control flow.** If a framework does something on your behalf, it
should be possible to find the line where it happens.

## Documentation

Documentation is written in English and Russian. A change to user-facing
behaviour updates both, or says in the pull request which one is pending — a
translation that silently falls behind is worse than one that is openly missing.

## Security

Do not open a public issue for a vulnerability. Follow [SECURITY.md](SECURITY.md).
