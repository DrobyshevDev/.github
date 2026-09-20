"""Weekly maintenance triage across the DrobyshevDev organisation.

Answers one question: what needs a decision this week. Ordered by that, not by
repository — a report sorted by repository makes the reader do the sorting.

Runs on `gh`, so it inherits whatever token is in the environment. The default
`GITHUB_TOKEN` of a workflow in the `.github` repository can read public
repositories across GitHub but not private ones, and cannot read code scanning
alerts anywhere but its own repository. Both limits are reported rather than
worked around: a repository that could not be read is listed as unread, never
silently counted as quiet.

Usage:
    python scripts/org_triage.py            # print the report
    python scripts/org_triage.py --json     # the same data, machine-readable
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request

ORG = "DrobyshevDev"

# Default branch per repository. Hard-coded rather than looked up: the lookup is
# one API call per repository to learn something that changes about once a
# decade, and a wrong answer here is visible in the report immediately.
REPOS = {
    "mlango": "master",
    "praxis": "master",
    "glia": "master",
    "decisionrl": "main",
    "stadion": "main",
    "lemma": "main",
    "research": "main",
    "DrobyshevDev.github.io": "main",
    ".github": "master",
}

STALE_DAYS = 30
NOW = dt.datetime.now(dt.timezone.utc)

#: Codecov's public API. No token: this asks only what a visitor of the badge
#: would see, which is exactly the question.
CODECOV = "https://api.codecov.io/api/v2/github/{org}/repos/{repo}/"


def gh(*args: str) -> object | None:
    """Run a gh command and parse its JSON. None means the call failed."""
    try:
        out = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    if not out.strip():
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


def gh_text(*args: str) -> str | None:
    """Run a gh command and return its output as text. None means it failed.

    gh() parses JSON, which is right for every other call here and wrong for a
    workflow file. Reading one through gh() silently produced None, so the first
    version of the pin check reported every repository as fully pinned -- a
    security check that answers "all clear" when it cannot read anything is
    worse than no check.
    """
    try:
        out = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return out or None


def age_days(timestamp: str) -> int:
    stamp = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return (NOW - stamp).days


def collect(repo: str, branch: str) -> dict:
    """Everything worth knowing about one repository, or a note that it is unread."""
    full = f"{ORG}/{repo}"
    report: dict = {
        "repo": repo, "unread": False, "pulls": [], "stale_issues": [],
        "ci": None, "unpinned": [], "coverage": "",
    }

    pulls = gh(
        "pr", "list", "--repo", full, "--state", "open", "--limit", "50",
        "--json", "number,title,author,createdAt,url,statusCheckRollup,isDraft",
    )
    if pulls is None:
        # Either private and out of this token's reach, or gh is not authenticated.
        # The caller distinguishes those; from here both mean the same thing.
        report["unread"] = True
        return report

    for pull in pulls:
        rollup = pull.get("statusCheckRollup") or []
        states = {
            check.get("conclusion") or check.get("state")
            for check in rollup
            if isinstance(check, dict)
        }
        if {"FAILURE", "TIMED_OUT", "CANCELLED", "ERROR"} & states:
            checks = "red"
        elif not rollup:
            checks = "none"
        elif states <= {"SUCCESS", "NEUTRAL", "SKIPPED", "COMPLETED"}:
            checks = "green"
        else:
            checks = "running"

        report["pulls"].append(
            {
                "number": pull["number"],
                "title": pull["title"],
                "author": (pull.get("author") or {}).get("login", "unknown"),
                "age": age_days(pull["createdAt"]),
                "url": pull["url"],
                "checks": checks,
                "draft": pull.get("isDraft", False),
                # Dependabot is the only author whose pull requests are expected
                # to arrive unread, which is what makes them worth separating.
                "bot": (pull.get("author") or {}).get("login", "") == "app/dependabot",
            }
        )

    issues = gh(
        "issue", "list", "--repo", full, "--state", "open", "--limit", "50",
        "--json", "number,title,createdAt,url",
    )
    for issue in issues or []:
        if age_days(issue["createdAt"]) >= STALE_DAYS:
            report["stale_issues"].append(
                {
                    "number": issue["number"],
                    "title": issue["title"],
                    "age": age_days(issue["createdAt"]),
                    "url": issue["url"],
                }
            )

    # Completed runs only, and the aggregate `CI` workflow by preference.
    #
    # Both filters are corrections to a report that cried wolf on its first run.
    # `gh run list` gives an in-flight run an empty conclusion rather than null,
    # which read as "not success" and put every still-running workflow under
    # "needs you" — including this triage reporting its own run, which would
    # have happened every week forever. And taking whatever ran last picked up
    # GitHub's own `pages-build-deployment` on the site repository rather than
    # its CI.
    runs = gh(
        "run", "list", "--repo", full, "--branch", branch,
        "--status", "completed", "--limit", "20",
        "--json", "conclusion,displayTitle,url,workflowName",
    ) or []
    aggregate = [run for run in runs if run.get("workflowName") == "CI"]
    if aggregate:
        report["ci"] = aggregate[0]
    elif runs:
        report["ci"] = runs[0]

    report["unpinned"] = unpinned_actions(full)
    report["coverage"] = coverage_badge(full, repo)

    return report


def _retry(call, expected: type, attempts: int = 3):
    """Call something up to `attempts` times, returning the first result of `expected`.

    The API drops a request now and then. Reporting that as "could not read"
    every time would make a truthful check into weekly noise, and silently
    treating it as "nothing found" is what this function exists to prevent, so
    the middle answer is to ask again before giving up.
    """
    for _ in range(attempts):
        result = call()
        if isinstance(result, expected):
            return result
    return None


def unpinned_actions(full: str) -> list[str] | None:
    """Actions still referenced by a tag or a branch rather than by a commit.

    A tag is a label its owner can move, and these workflows run with a token
    that can write to the repository. Pinning happened once, by hand; this is
    what notices the next workflow added with `@v4` on it. Local actions
    (`./.github/...`) and reusable workflows in this organisation are skipped --
    those move only when somebody here moves them.

    Returns None when the workflows could not be read, and never an empty list
    in that case. The distinction is the whole point: the first version returned
    [] on a failed request, so a single timed-out call reported a repository with
    twenty-one loose references as fully pinned. That is this file's own stated
    rule -- a repository that could not be read is unread, never quiet -- broken
    by the check added to enforce another one.
    """
    listing = _retry(lambda: gh("api", f"repos/{full}/contents/.github/workflows"), list)
    if listing is None:
        return None
    names = [
        entry.get("name")
        for entry in listing
        if isinstance(entry, dict) and str(entry.get("name", "")).endswith((".yml", ".yaml"))
    ]
    loose: list[str] = []
    for name in names:
        body = _retry(
            lambda name=name: gh_text(
                "api", f"repos/{full}/contents/.github/workflows/{name}",
                "-H", "Accept: application/vnd.github.raw",
            ),
            str,
        )
        if body is None:
            return None
        for match in re.finditer(r"uses:\s*([^\s#]+)", body):
            ref = match.group(1)
            if ref.startswith(("./", f"{ORG}/")) or "@" not in ref:
                continue
            if not re.fullmatch(r"[0-9a-f]{40}", ref.split("@", 1)[1]):
                loose.append(f"{name}: {ref}")
    return loose


def _fetch(url: str) -> str | None:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "drobyshevdev-triage"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return None


def coverage_badge(full: str, repo: str) -> str | None:
    """Whether the coverage badge a repository publishes has anything behind it.

    A badge is a claim, and this one can be empty without anything going red.
    The upload step runs with `fail_ci_if_error: false` -- correct, because a
    Codecov outage is not a reason to fail somebody's pull request -- so a
    rejected upload leaves the job green, and the only trace is a line in a log
    nobody opens. Meanwhile the badge renders "unknown" to every visitor of the
    README.

    That is how four repositories came to publish an "unknown" coverage badge
    while their coverage jobs were green: Codecov answered
    `Token required - not valid tokenless upload` and the run carried on.

    Asks Codecov the same question a visitor's browser asks, with no token.

    Returns None when something could not be read -- unknown rather than fine --
    "" when the repository makes no claim, "ok N%" when the claim has a figure
    behind it, and "empty" when the badge is published and Codecov has nothing.
    """
    listing = _retry(lambda: gh("api", f"repos/{full}/contents"), list)
    if listing is None:
        return None
    readmes = [
        entry.get("name")
        for entry in listing
        if isinstance(entry, dict) and str(entry.get("name", "")).startswith("README")
    ]

    claimed = False
    for name in readmes:
        body = _retry(
            lambda name=name: gh_text(
                "api", f"repos/{full}/contents/{name}",
                "-H", "Accept: application/vnd.github.raw",
            ),
            str,
        )
        if body is None:
            return None
        if f"codecov.io/gh/{ORG}/{repo}" in body:
            claimed = True
    if not claimed:
        return ""

    body = _fetch(CODECOV.format(org=ORG, repo=repo))
    if body is None:
        return None
    try:
        totals = json.loads(body).get("totals") or {}
    except json.JSONDecodeError:
        return None
    coverage = totals.get("coverage")
    return f"ok {float(coverage):.1f}%" if coverage is not None else "empty"


def render(reports: list[dict]) -> tuple[str, bool]:
    """The report, and whether anything in it needs a decision."""
    urgent: list[str] = []
    ready: list[str] = []
    waiting: list[str] = []
    quiet: list[str] = []
    drifting: list[str] = []
    unread: list[str] = []

    for report in reports:
        repo = report["repo"]
        if report["unread"]:
            unread.append(repo)
            continue

        interesting = False

        for pull in report["pulls"]:
            line = f"[{repo}#{pull['number']}]({pull['url']}) — {pull['title']}"
            if pull["checks"] == "red":
                who = "a dependency bump" if pull["bot"] else f"a change by {pull['author']}"
                urgent.append(f"{line}\n  Checks are red on {who}, {pull['age']} days old.")
                interesting = True
            elif pull["bot"]:
                waiting.append(f"{line} — {pull['age']}d, checks {pull['checks']}")
                interesting = True
            elif pull["checks"] in ("green", "none") and not pull["draft"]:
                # Green, not a draft, author is not a bot: everything that can be
                # automated has happened and the only thing left is somebody
                # deciding. That is the question this report asks, so it belongs
                # here rather than waiting for STALE_DAYS.
                #
                # It was not here before, and decisionrl#31 is why: green on every
                # leg including the forty-minute learning job, open twenty-four
                # days, and this report called the repository quiet -- because red
                # checks were the only thing that counted as needing you, and
                # thirty days the only thing that counted as old.
                # "none" means no check ever ran, which in a repository without
                # CI is every pull request in it. .github#7 has been open and
                # cleanly mergeable for forty-one days on exactly that basis, and
                # calling it unchecked rather than green is the honest wording.
                state = "Green" if pull["checks"] == "green" else "No checks ran, and mergeable,"
                ready.append(
                    f"{line}\n  {state} for {pull['age']} days and waiting on a decision."
                )
                interesting = True
            elif pull["age"] >= STALE_DAYS:
                drifting.append(f"{line} — open {pull['age']} days, checks {pull['checks']}")
                interesting = True

        ci = report["ci"]
        # The empty string is what an unfinished run reports. Only a run that
        # finished, and finished badly, belongs here.
        if ci and ci.get("conclusion") not in ("", None, "success", "skipped"):
            urgent.append(
                f"[{repo}]({ci['url']}) — {ci['workflowName']} is "
                f"{ci['conclusion']} on the default branch."
            )
            interesting = True

        coverage = report["coverage"]
        if coverage is None:
            drifting.append(
                f"{repo} — could not check its coverage badge, so whether anything "
                "is behind it is unknown rather than fine."
            )
            interesting = True
        elif coverage == "empty":
            # Urgent, not drifting: this one is on the README right now, being
            # read by anyone deciding whether to trust the project, and it says
            # nothing at all. The job that should have filled it is green.
            urgent.append(
                f"{repo} — publishes a coverage badge and Codecov has no coverage for it, "
                "so the badge renders \"unknown\" to every visitor while the job that "
                "should have filled it is green. Codecov rejects the upload "
                "(`Token required - not valid tokenless upload`) and the step is not "
                "allowed to fail on an outage, so nothing turns red. decisionrl uploads "
                "fine, and no repository here has a secret of its own, so the likely "
                "difference is an organisation `CODECOV_TOKEN` not shared with this "
                "repository, or the repository never activated on Codecov — both need "
                "a login to tell apart."
            )
            interesting = True

        unpinned = report["unpinned"]
        if unpinned is None:
            drifting.append(
                f"{repo} — could not read the workflows, so whether its actions are "
                "pinned is unknown rather than fine."
            )
            interesting = True
        elif unpinned:
            count = len(unpinned)
            drifting.append(
                f"{repo} — {count} action{'s' if count != 1 else ''} still on a moving tag: "
                + ", ".join(sorted({line.split(': ', 1)[1] for line in unpinned}))
            )
            interesting = True

        for issue in report["stale_issues"]:
            drifting.append(
                f"[{repo}#{issue['number']}]({issue['url']}) — {issue['title']} "
                f"({issue['age']}d)"
            )
            interesting = True

        if not interesting:
            quiet.append(repo)

    def section(title: str, lines: list[str]) -> str:
        # An empty section keeps its heading. Omitting it reads as an oversight
        # rather than as good news.
        body = "\n".join(f"- {line}" for line in lines) if lines else "None."
        return f"## {title}\n\n{body}\n"

    parts = [
        f"_Generated {NOW:%Y-%m-%d %H:%M} UTC._\n",
        section("Needs you this week", urgent),
        section("Green and waiting on you", ready),
        section("Waiting on review", waiting),
        section("Quiet", [", ".join(quiet)] if quiet else []),
        section("Drifting", drifting),
    ]
    if unread:
        parts.append(
            section(
                "Not read",
                [
                    f"{', '.join(unread)} — the token running this cannot see them. "
                    "Private repositories need a token with `repo` scope; without one "
                    "they are unread, not quiet."
                ],
            )
        )

    return "\n".join(parts), bool(urgent or ready)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit the raw data instead.")
    args = parser.parse_args()

    if gh("auth", "status") is None and subprocess.run(
        ["gh", "auth", "status"], capture_output=True
    ).returncode != 0:
        print("gh is not authenticated; a triage built on missing data is worse than none.")
        return 1

    reports = [collect(repo, branch) for repo, branch in REPOS.items()]

    if args.json:
        print(json.dumps(reports, indent=2))
        return 0

    body, urgent = render(reports)
    print(body)
    # Exit code carries the one bit a workflow needs to decide whether to notify.
    return 2 if urgent else 0


if __name__ == "__main__":
    sys.exit(main())
