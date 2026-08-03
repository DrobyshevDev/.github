# DrobyshevDev

**Frameworks, products and tooling for machine learning, LLM agents, and
operational decision systems.**

We build the layer between a research result and something a team can run: the
project structure, the tracking, the interface, and the tests that keep a number
honest six months after it was measured. Everything here is open source, typed,
and tested in CI on Linux, macOS and Windows.

[**drobyshevdev.github.io**](https://drobyshevdev.github.io/) · [Русская версия](https://drobyshevdev.github.io/ru/)

---

## Projects

| | What it is | Install |
|---|---|---|
| [**praxis**](https://github.com/DrobyshevDev/praxis) | A legal assistant whose citations are checked, not asserted | `docker compose up app` |
| [**mlango**](https://github.com/DrobyshevDev/mlango) | A framework for ML, analytics and LLM agents | `pip install "mlango[sklearn]"` |
| [**glia**](https://github.com/DrobyshevDev/glia) | A glass-box, minimal library for building LLM agents | `pip install glia-agents` |
| [**decisionrl**](https://github.com/DrobyshevDev/decisionrl) | Reinforcement learning for operational decisions | `pip install decisionrl` |
| [**sextant**](https://github.com/DrobyshevDev/sextant) | A free course: the whole road into ML, DL and RL, from zero to reading and reproducing research | [начать](https://drobyshevdev.github.io/sextant/) |

### [praxis](https://github.com/DrobyshevDev/praxis) · a legal assistant you can check

Answers a question about Russian law and returns the specific articles it rests
on, with every citation verified. Retrieval is hybrid — lexical plus dense search
with a cross-encoder reranker — and an NLI model checks that each cited norm
actually supports the claim, so a plausible-but-wrong reference is caught rather
than shipped. The default answer is extractive, the text of the law itself, and
cannot hallucinate; an optional LLM layer passes the same check.

The full Civil Code ships in the repository — 1,712 articles, 4,717 provisions —
together with a cross-reference graph between articles and a parser for the
official text at pravo.gov.ru, which is how the remaining codes are added.
Judicial practice is the next pipeline rather than something already shipped.
Retrieval quality is pinned by an eval on a golden set: recall@5 0.92, MRR 0.94
on the full corpus, tracked run over run.

```bash
docker compose up app        # → http://localhost:8077, no keys required
```

`Python 3.12` · FastAPI · Postgres + pgvector · [releases](https://github.com/DrobyshevDev/praxis/releases) · Apache-2.0

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

`Python 3.10+` · [documentation](https://drobyshevdev.github.io/mlango/) ·
[PyPI](https://pypi.org/project/mlango/) · MIT

### [glia](https://github.com/DrobyshevDev/glia) · a glass-box, minimal library for LLM agents

Every model call, tool call and state transition is a plain object you can log,
snapshot and replay. No hidden control flow; the whole loop fits in one file you
can read in an afternoon.

```bash
pip install glia-agents
```

The crowded agent-framework field has one consistent complaint: too much
abstraction, hidden control flow, painful to debug. glia is the opposite bet. It
ships the modern techniques — tools, structured outputs, context compaction,
durable checkpoints, guardrails, subagents, evals-as-tests — as opt-in primitives
you can read, not a monolith you must trust. If you want a graph engine, use
LangGraph. If you want a small, transparent loop you fully understand, use this.

`Python 3.10+` · zero required dependencies · [documentation](https://drobyshevdev.github.io/glia/) ·
[PyPI](https://pypi.org/project/glia-agents/) · MIT

### [decisionrl](https://github.com/DrobyshevDev/decisionrl) · reinforcement learning for operational decisions

Pricing, inventory, energy, queues and supply chains: the decisions a business
makes thousands of times a day, where a small policy improvement compounds.
Thirty-one algorithms and twenty-two environments — nine of them applied — typed
and tested, aimed at problems that have a cost function rather than a
leaderboard.

```bash
pip install decisionrl
```

Every applied environment ships with the classical operations-research baseline
beside it, so a learned policy is measured against the standard method rather
than asserted to be better. Where the classical method is already optimal, the
README says so and shows the learned policy matching it.

`Python 3.9+` · [documentation](https://drobyshevdev.github.io/decisionrl/) ·
[PyPI](https://pypi.org/project/decisionrl/) · MIT

### [sextant](https://github.com/DrobyshevDev/sextant) · the whole road into ML, DL and RL, free

A complete roadmap through machine learning, neural networks, reinforcement
learning and recommender systems: twenty-seven modules from the arithmetic of a
mean to reproducing a recent paper. No sign-up, no first-module-free, no
instalments.

The central skill is checking a claim rather than launching a training run. The
field moves through papers, most of the improvements they announce do not survive
a change of random seed or a comparison against a tuned baseline, and someone who
can train a model but cannot check a claim builds on noise. Module 1 is about
baselines and confidence intervals, before any machine learning at all.

Written in Russian; the notebooks run on a CPU in seconds and are executed in CI
on Linux and Windows, because a reader whose notebook does not start has no
course.

[**drobyshevdev.github.io/sextant**](https://drobyshevdev.github.io/sextant/) ·
prose CC BY 4.0 · code MIT

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

Issues and pull requests are welcome on any project. Every repository has a
`CONTRIBUTING.md` — its own, or the
[organisation-wide default](https://github.com/DrobyshevDev/.github/blob/master/CONTRIBUTING.md) —
with the checks CI will run and the standards review will hold you to. Security
reports go through GitHub's [private vulnerability
reporting](https://github.com/DrobyshevDev/.github/blob/master/SECURITY.md)
rather than a public issue.

Documentation is written in English and Russian, structured so a third language
is one file per page rather than a fork.
