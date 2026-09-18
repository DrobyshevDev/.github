#!/usr/bin/env python3
"""Pin every GitHub Action in a checkout to a commit, keeping the tag as a comment.

A tag is a label somebody else can move. `actions/checkout@v7` means "whatever
the owner of that repository decides v7 points at, at the moment our workflow
runs" -- and our workflows run with a token that can write to the repository.
`pypa/gh-action-pypi-publish@release/v1` is worse: a branch, which moves by
design, and it is the step that publishes to PyPI.

Pinning to a commit fixes what runs. The tag stays on the line as a comment so
the file is still readable, and Dependabot understands this form: it bumps the
commit and rewrites the comment together, which is why this is maintainable
rather than a snapshot that rots.

    python scripts/pin_actions.py ../decisionrl            # rewrite
    python scripts/pin_actions.py ../decisionrl --dry-run  # show what would change
    python scripts/pin_actions.py ../decisionrl --check    # exit 1 if anything is unpinned

Resolution goes through `gh`, so it inherits whatever token is in the
environment. A reference that cannot be resolved is reported and left alone --
guessing a commit is the one failure mode this script must not have.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

# uses: owner/repo[/path]@ref  with an optional trailing comment
USES = re.compile(
    r"^(?P<indent>\s*(?:-\s*)?)uses:\s*(?P<action>[A-Za-z0-9._-]+/[A-Za-z0-9._/-]+)@(?P<ref>[^\s#]+)"
    r"(?P<rest>\s*(?:#.*)?)$"
)
SHA = re.compile(r"^[0-9a-f]{40}$")

_cache: dict[tuple[str, str], str] = {}


def resolve(action: str, ref: str) -> str | None:
    """The commit a tag or branch points at, or None if it cannot be read.

    Only successes are cached. Caching a failure would let one timed-out request
    decide that an action is unresolvable for the rest of the run, and the same
    reference appears dozens of times in a repository -- so a single blip would
    silently leave most of the file unpinned.
    """
    owner_repo = "/".join(action.split("/")[:2])
    key = (owner_repo, ref)
    if key in _cache:
        return _cache[key]
    for _ in range(3):
        result = subprocess.run(
            ["gh", "api", f"repos/{owner_repo}/commits/{ref}", "--jq", ".sha"],
            capture_output=True, text=True, check=False,
        )
        sha = result.stdout.strip()
        if SHA.match(sha):
            _cache[key] = sha
            return sha
    return None


def workflows(root: pathlib.Path) -> list[pathlib.Path]:
    directory = root / ".github" / "workflows"
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir() if p.suffix in {".yml", ".yaml"})


def process(path: pathlib.Path, *, write: bool) -> tuple[int, int, list[str]]:
    """Returns (pinned already, newly pinned, unresolved)."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    already = changed = 0
    unresolved: list[str] = []

    for index, line in enumerate(lines):
        match = USES.match(line.rstrip("\n"))
        if not match:
            continue
        action, ref = match["action"], match["ref"]
        if SHA.match(ref):
            already += 1
            continue
        sha = resolve(action, ref)
        if sha is None:
            unresolved.append(f"{action}@{ref}")
            continue
        newline = "\n" if line.endswith("\n") else ""
        lines[index] = f"{match['indent']}uses: {action}@{sha} # {ref}{newline}"
        changed += 1
        print(f"    {action}@{ref} -> {sha[:12]}…")

    if write and changed:
        path.write_text("".join(lines), encoding="utf-8", newline="\n")
    return already, changed, unresolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", help="checkout to rewrite")
    parser.add_argument("--dry-run", action="store_true", help="report without writing")
    parser.add_argument("--check", action="store_true", help="exit 1 if anything is unpinned")
    args = parser.parse_args()

    root = pathlib.Path(args.root).resolve()
    files = workflows(root)
    if not files:
        print(f"  no workflows under {root}", file=sys.stderr)
        return 2

    totals = [0, 0]
    unresolved: list[str] = []
    for path in files:
        print(f"  {path.relative_to(root)}")
        already, changed, missing = process(path, write=not (args.dry_run or args.check))
        totals[0] += already
        totals[1] += changed
        unresolved.extend(missing)

    print(f"\n  {totals[0]} already pinned, {totals[1]} {'to pin' if args.dry_run or args.check else 'pinned'}")
    if unresolved:
        print("  could not resolve (left alone):")
        for item in sorted(set(unresolved)):
            print(f"    {item}")
    if args.check:
        return 1 if totals[1] or unresolved else 0
    return 1 if unresolved else 0


if __name__ == "__main__":
    raise SystemExit(main())
