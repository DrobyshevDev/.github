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
import subprocess
import sys

ORG = "DrobyshevDev"

# Default branch per repository. Hard-coded rather than looked up: the lookup is
# one API call per repository to learn something that changes about once a
# decade, and a wrong answer here is visible in the report immediately.
REPOS = {
    "mlango": "master",
    "praxis": "master",
    "glia": "master",
    "decisionrl": "main",
    "lemma": "main",
    "dokimos": "master",
    "DrobyshevDev.github.io": "main",
    ".github": "master",
}

STALE_DAYS = 30
NOW = dt.datetime.now(dt.timezone.utc)


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


def age_days(timestamp: str) -> int:
    stamp = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return (NOW - stamp).days


def collect(repo: str, branch: str) -> dict:
    """Everything worth knowing about one repository, or a note that it is unread."""
    full = f"{ORG}/{repo}"
    report: dict = {"repo": repo, "unread": False, "pulls": [], "stale_issues": [], "ci": None}

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

    runs = gh(
        "run", "list", "--repo", full, "--branch", branch, "--limit", "1",
        "--json", "conclusion,displayTitle,url,workflowName",
    )
    if runs:
        report["ci"] = runs[0]

    return report


def render(reports: list[dict]) -> tuple[str, bool]:
    """The report, and whether anything in it needs a decision."""
    urgent: list[str] = []
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
            elif pull["age"] >= STALE_DAYS:
                drifting.append(f"{line} — open {pull['age']} days")
                interesting = True

        ci = report["ci"]
        if ci and ci.get("conclusion") not in (None, "success", "skipped"):
            urgent.append(
                f"[{repo}]({ci['url']}) — {ci['workflowName']} is "
                f"{ci['conclusion']} on the default branch."
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

    return "\n".join(parts), bool(urgent)


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
