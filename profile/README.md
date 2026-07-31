# DrobyshevDev

**Сайт:** [https://DrobyshevDev.github.io/drobyshevdev-demo/](https://DrobyshevDev.github.io/drobyshevdev-demo/)

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Деплой-blue?style=flat-square&logo=githubpages)](https://DrobyshevDev.github.io/drobyshevdev-demo/)

**Frameworks and tooling for machine learning, LLM agents, and operational
decision systems.**

We build the layer between a research result and something a team can run: the
project structure, the tracking, the interface, and the tests that keep a number
honest six months after it was measured. Everything here is open source, typed,
and tested in CI on Linux, macOS and Windows.

---

## Projects

### [mlango](https://github.com/DrobyshevDev/mlango) · a framework for ML, analytics and LLM agents

Django's philosophy, applied to machine learning. You declare datasets, models,
agents and evaluations; the framework runs them, versions them, records them and
shows them to you. One class body becomes an admin page, a documented API
endpoint, a migration and a CLI target at once.

```bash
pip install "mlango[sklearn]"
mlango startproject myproject
```

Agents are a first-class family beside models, sharing one metastore, one admin
and one evaluation system. Most tools in this space are for classical ML *or*
for LLMs; most teams are doing both.

`Python` · [documentation](https://drobyshevdev.github.io/mlango/) ·
[PyPI](https://pypi.org/project/mlango/) · MIT

### [decisionrl](https://github.com/DrobyshevDev/decisionrl) · reinforcement learning for operational decisions

Pricing, inventory, energy, queues and supply chains: the decisions a business
makes thousands of times a day, where a small policy improvement compounds.
Thirty-one algorithms, typed and tested, aimed at problems that have a cost
function rather than a leaderboard.

`Python` · MIT

---

## How we work

**Errors teach.** A message is read at the worst possible moment by someone who
does not have the source open. It should say what went wrong *and* what to do
next, and list the alternatives when there are any.

**Tests are named after the guarantee they protect.**
`test_assignment_is_stable_when_rows_are_added`, not `test_split`. A test whose
name does not survive being read aloud is not documenting anything.

**Verification beats assertion.** A green pipeline on one machine is not
evidence. Every claim we publish — an accuracy, a benchmark, a "this works on
Windows" — is measured on the run it describes, and the numbers in a README are
pinned by tests, because prose rots quietly and a failing test does not.

**Comments explain why.** The code already says what it does. The comment is for
the constraint a reader cannot see.

**No hidden control flow.** If a framework does something on your behalf, it
should be possible to find the line where it happens.

---

## Contributing

Issues and pull requests are welcome on any project. Each repository has a
`CONTRIBUTING.md` with the setup, the checks CI will run, and the layering rules
review will hold you to. Security reports go through GitHub's private
vulnerability reporting rather than a public issue.

Documentation is written in English and Russian, structured so a third language
is one file per page rather than a fork.
