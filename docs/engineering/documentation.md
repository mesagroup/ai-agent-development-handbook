# Part 7 — Documentation & Knowledge Capture

This is the operational side of the second throughline: **capture the trail.** In an evidence-driven, agent-built codebase, a decision is only as durable as its record. If the reasoning and the evidence behind a choice are not written down, they are lost — and the next person, or the same person in six months, or a subagent dispatched with zero context, will re-litigate a settled question or, worse, quietly reverse it without knowing why. Documentation here is not an afterthought to the code; it is where the *why* lives, and it is held to nearly the same standard as the code.

## Why docs are load-bearing (and drift is worse than absence)

A doc that has drifted out of sync with the code is worse than no doc at all. An empty spot invites you to go read the source; a confidently wrong doc launders a stale belief into an authoritative-looking claim and stops you looking. So the governing rule is the same one that governs a test: **a claim in the docs must be verifiable, and it must have been verified.** A cross-link that points at a moved file, an import path that no longer resolves, a CLI flag that was renamed — each is a silent liability, and we treat finding and fixing them as real work, not tidying.

## The architecture-vs-research split

Two folders under `docs/` look similar and mean opposite things; keeping them distinct is a standing discipline.

- **[`docs/architecture/`](../architecture/)** documents **what is actually implemented** — the design patterns, contracts, and mechanisms a reader can verify against the source. These are prescriptive and must stay in sync with the code. The folder is kept clean: every doc maps to real, current behaviour.
- **[`docs/research/`](../research/)** holds **background investigations and industry analysis** that *informed* decisions — reference material, not prescriptive, including artifacts that have since been partly superseded. It is explicitly **not authoritative for current behaviour**.

When an investigation produces a decision that lands in code, the codebase-facing explanation goes in `architecture/` and the raw exploration stays (or moves) in `research/`, with the two cross-linked. Research transcripts must not accumulate under `architecture/` — that is how a prescriptive folder rots into a pile of maybe-true history.

## docs/ is organized by audience and concern

The navigable index is [`docs/README.md`](../README.md). The main sections and what each is for:

- **[`agents/`](../agents/)** — per-agent functional specs, architecture, configuration, eval harness, and SOP analyses.
- **[`architecture/`](../architecture/)** — cross-cutting patterns as implemented (core tier, capabilities tier, multi-agent decomposition, config, structured output, URL/reference handling).
- **[`capabilities/`](../document-model/)** and **[`services/`](../services/)** — capability measurements and external-integration references.
- **[`eval/`](../eval/)** — the decision methodology (start at [Data-Driven Development](../eval/data-driven-development.md)) and the concrete method docs.
- **[`leaderboards/`](../leaderboards/)** — empirical results plus the running [evaluation history](../leaderboards/evaluation-history.md).
- **[`claude-code/`](../claude-code/)** — the working references (env vars, key files, eval reference, skills discovery).
- **`stories/`, `experiments/`, `superpowers/` (specs + plans), `audit/`** — the decision-trail artifacts, below.

## The decision-trail artifacts

Different records serve different moments in a piece of work. Some look *forward* (what we're about to do); some look *back* (what we did and learned). Together they are how a decision plus its evidence survive the moment.

| Artifact | Location | What it captures | Direction |
|---|---|---|---|
| **Spec** | [`docs/superpowers/specs/`](../superpowers/specs/) | The design agreed *before* code — architecture, components, data flow, testing. The always-on spec-review gate stops here. | Forward |
| **Plan** | [`docs/superpowers/plans/`](../superpowers/plans/) | The implementation blueprint — file structure, right-sized tasks, bite-sized TDD steps with complete code. | Forward |
| **Story** | [`docs/stories/`](../stories/) | A narrative write-up *after* a piece of work lands — what, why, findings, lessons. E.g. the [three-layer knowledge-model story](../stories/2026-06-15-three-layer-knowledge-model.md). | Back |
| **Experiment** | [`docs/experiments/`](../experiments/) | An experiment write-up: setup, results, conclusion. | Back |
| **Leaderboard + evaluation history** | [`docs/leaderboards/`](../leaderboards/) | The running record of every eval result and the decision it drove. | Back |

The spec and the plan are how the lifecycle in [Part 1](lifecycle.md) front-loads judgment; the story and the leaderboard are how a result and its evidence outlive the run that produced them (they feed the loop in [Part 5](evaluation.md)). A spec without a later story is a plan nobody closed the loop on; a leaderboard number without an evaluation-history line is a result nobody can trace.

## Maintenance rules

These are binding (from [`CLAUDE.md`](../../CLAUDE.md)); they keep the trail current instead of letting it fossilize:

- When adding or modifying agent functionality, update the corresponding docs under `docs/agents/<agent>/`.
- When running eval experiments, update the relevant leaderboard **and** add an [evaluation-history](../leaderboards/evaluation-history.md) entry.
- When adding a new service integration, create a reference doc under [`docs/services/`](../services/).
- When merging a PR that touches `docs/`, verify the [`docs/README.md`](../README.md) index entries are up to date.
- Keep module docstrings current — every module describes what it does and how to use it (a coding rule; see [Part 1](lifecycle.md)).
- A commit that changes an LLM/agentic prompt must explain **why** in the message, preferably in its own commit separate from code.

## Cross-reference sanity: the docs audit

Because docs make verifiable claims, they get audited like a test suite. A **docs audit** re-reads the documentation against the source and fixes what has drifted: broken or mislabelled cross-links, stale import paths, renamed CLI flags, claims that no longer match the code. The most recent pass is captured in [`docs/audit/2026-07-20-docs-audit.md`](../audit/2026-07-20-docs-audit.md), and the work was run in phases tracked under issue #488 — see the phased plans under [`docs/superpowers/plans/`](../superpowers/plans/) (the `2026-07-*-docs-audit-phase*.md` series, covering core, capabilities, document-model, agents, and services/config/meta/eval). Treat the audit as the docs equivalent of running the tests: the value is not the tidy diff, it is the guarantee that every claim was checked against reality.

## A note on Markdown source style

One paragraph is one line in the `.md` source — no hard-wrapping. Let the renderer wrap; never reflow prose to a column, and never reflow code blocks or diagrams. This keeps diffs meaningful (a one-word edit is a one-line change, not a reflowed paragraph) and is the house convention across the repo.

## See also

- [Part 1 — Development lifecycle](lifecycle.md) — where specs and plans are produced and the review gates live.
- [Part 5 — Evaluation](evaluation.md) — the loop that leaderboards and stories feed.
- [`docs/README.md`](../README.md) — the master documentation index · [`CLAUDE.md`](../../CLAUDE.md) — the binding rules.
- [Handbook index](README.md).
