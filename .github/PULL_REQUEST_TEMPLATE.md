<!--
Organisation-wide default. A repository that ships its own template overrides
this one entirely.
-->

## What this changes

<!-- One or two sentences. What is different for a user after this lands? -->

## Why

<!-- The problem it solves. Link an issue if there is one: Fixes #123 -->

## What breaks if this is wrong

<!--
The sentence a reviewer needs and the hardest one to reconstruct from a diff.
"Nothing, it is documentation only" is a perfectly good answer.
-->

## Checklist

- [ ] Lint and formatting pass
- [ ] The test suite passes
- [ ] Tests cover the new behaviour, named after the guarantee they protect
- [ ] `CHANGELOG.md` updated under `## Unreleased`, if the repository keeps one
- [ ] Docs updated if this changes an API or a default — English and Russian, or
      the pull request says which one is pending
- [ ] No new required dependency in the core (optional ones go behind an extra)

## Notes for the reviewer

<!-- Anything non-obvious: a trade-off you made, an alternative you rejected,
     a place you would like a second opinion. -->
