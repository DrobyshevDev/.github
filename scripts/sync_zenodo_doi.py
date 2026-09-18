"""Put the Zenodo DOI a repository already has into the places that claim it.

Every code repository in the organisation ships `.zenodo.json` and a
`CITATION.cff`, which is the work of being citable. None of them carried a DOI,
because the badge and the citation file have to be written after the first
archive exists, and that step was never taken. This script takes it, and takes
it again whenever a new repository is archived, so the answer to "how do I cite
this" is never a README that predates the record.

It reads the organisation's Zenodo community, matches each record to a
repository by the GitHub URL in its related identifiers, and writes the *concept*
DOI — the one that always resolves to the newest version — into:

  * a DOI badge in README.md (and README.ru.md / README.en.md where they exist)
  * the `doi:` field and `identifiers:` block of CITATION.cff

Nothing is invented: a repository with no record on Zenodo is reported as such
and left untouched. Run it after enabling the GitHub integration and publishing
a release; the first run is the one that fills everything in.

Usage:
    python scripts/sync_zenodo_doi.py --root ..    # write
    python scripts/sync_zenodo_doi.py --root .. --check   # report only, exit 1 if stale
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import urllib.request

COMMUNITY = "drobyshevdev"
# 25 is the ceiling for an unauthenticated request; the community holds papers
# as well as software, so paging is not hypothetical.
API = f"https://zenodo.org/api/communities/{COMMUNITY}/records?size=25"
ORG = "DrobyshevDev"

# The repositories that are meant to be citable. A repository absent from this
# list is not "missing a DOI", it is deliberately not archived.
REPOS = ["decisionrl", "glia", "mlango", "praxis", "stadion", "research", "lemma"]

READMES = ["README.md", "README.ru.md", "README.en.md"]

_BADGE = re.compile(r"\[!\[DOI\]\(https://zenodo\.org/badge/DOI/[^)]+\)\]\([^)]+\)\n?")


def fetch_records() -> list[dict]:
    """Every record in the community, following Zenodo's paging."""
    records: list[dict] = []
    url = API
    while url:
        with urllib.request.urlopen(url, timeout=30) as response:
            page = json.load(response)
        records.extend(page.get("hits", {}).get("hits", []))
        url = page.get("links", {}).get("next")
    return records


def concept_doi_by_repo(records: list[dict]) -> dict[str, str]:
    """Map repository name to concept DOI, by the GitHub URL Zenodo stored."""
    found: dict[str, str] = {}
    for record in records:
        doi = record.get("conceptdoi")
        if not doi:
            continue
        haystack = json.dumps(record.get("metadata", {}).get("related_identifiers") or [])
        for repo in REPOS:
            if f"github.com/{ORG}/{repo}" in haystack:
                found[repo] = doi
    return found


def badge_for(doi: str) -> str:
    return f"[![DOI](https://zenodo.org/badge/DOI/{doi}.svg)](https://doi.org/{doi})\n"


def patch_readme(path: pathlib.Path, doi: str) -> bool:
    """Append the DOI badge to the first run of badges, or refresh a stale one.

    Returns True when the file needed changing, whether or not it was written.
    """
    text = path.read_text(encoding="utf-8")
    badge = badge_for(doi)
    if badge in text:
        return False
    if _BADGE.search(text):  # a DOI from an earlier record: replace it
        return True
    return _insertion_point(text) is not None


def _insertion_point(text: str) -> int | None:
    """The line index after the last badge of the first contiguous badge run."""
    lines = text.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if line.startswith("[![")), None)
    if start is None:
        return None
    end = start
    while end + 1 < len(lines) and lines[end + 1].startswith("[!["):
        end += 1
    return end + 1


def write_readme(path: pathlib.Path, doi: str) -> None:
    text = path.read_text(encoding="utf-8")
    badge = badge_for(doi)
    if _BADGE.search(text):
        text = _BADGE.sub(badge, text, count=1)
    else:
        at = _insertion_point(text)
        if at is None:
            return
        lines = text.splitlines(keepends=True)
        lines.insert(at, badge)
        text = "".join(lines)
    path.write_text(text, encoding="utf-8", newline="\n")


def patch_citation(path: pathlib.Path, doi: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if f"doi: {doi}" in text:
        return False
    text = re.sub(r"^doi: .*\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"^identifiers:\n(?:  - .*\n|    .*\n)+", "", text, flags=re.MULTILINE)
    # After `license:`, which every file in the organisation has.
    text = re.sub(
        r"^(license: .*\n)",
        rf"\1doi: {doi}\n"
        "identifiers:\n"
        "  - type: doi\n"
        f"    value: {doi}\n"
        "    description: The concept DOI, which always resolves to the latest version.\n",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="..", help="directory holding the repository clones")
    parser.add_argument("--check", action="store_true", help="report only; exit 1 if anything is stale")
    args = parser.parse_args()

    root = pathlib.Path(args.root).resolve()
    dois = concept_doi_by_repo(fetch_records())

    stale, missing, done = [], [], []
    for repo in REPOS:
        doi = dois.get(repo)
        if not doi:
            missing.append(repo)
            continue
        checkout = root / repo
        if not checkout.is_dir():
            print(f"  {repo}: no checkout at {checkout}", file=sys.stderr)
            continue

        changed = []
        for name in READMES:
            path = checkout / name
            if path.exists() and patch_readme(path, doi):
                changed.append(name)
                if not args.check:
                    write_readme(path, doi)

        citation = checkout / "CITATION.cff"
        if citation.exists() and f"doi: {doi}" not in citation.read_text(encoding="utf-8"):
            changed.append("CITATION.cff")
            if not args.check:
                patch_citation(citation, doi)

        (stale if changed else done).append((repo, doi, changed))

    for repo, doi, changed in done:
        print(f"  {repo}: {doi} — already stated everywhere")
    for repo, doi, changed in stale:
        verb = "would update" if args.check else "updated"
        print(f"  {repo}: {doi} — {verb} {', '.join(changed)}")
    if missing:
        print(f"\n  no Zenodo record yet: {', '.join(missing)}")
        print(f"  enable the GitHub integration at https://zenodo.org/account/settings/github/")
        print(f"  and publish a release; the DOI appears here on the next run.")

    return 1 if (args.check and stale) else 0


if __name__ == "__main__":
    raise SystemExit(main())
