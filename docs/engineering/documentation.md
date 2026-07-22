# Part 7 — Documentation & Knowledge Capture

This is the "capture the trail" throughline made concrete. We develop with agents and across long time horizons, so a decision — and the evidence that justified it — must be recoverable by someone who wasn't there: a new teammate, a future self, or a subagent dispatched with zero conversation history. Documentation is not an afterthought to the code; it is where the *why* lives, and it is held to nearly the same standard as the code.

## Why: drifted docs are worse than none

The bar we aim for: **the docs alone should convey what the system does and how it is built, without reading the source** — if the team stopped for six months, we should be able to restart from the docs. Everything below is in service of that.

A doc that has drifted out of sync with the code does more damage than a missing one. An empty spot invites you to go read the source; a confidently wrong doc launders a stale belief into an authoritative-looking claim and stops you looking. So the governing rule is the same one that governs a test: **a claim in the docs must be verifiable, and it must have been verified.** A cross-link that points at a moved file, an import path that no longer resolves, a flag that was renamed — each is a silent liability, and finding and fixing them is real work, not tidying. The enforcement is that a change and its documentation move together, in the same PR — not "later."

## The architecture-vs-research split

Keep two kinds of writing distinct, because they look similar and mean opposite things:

- **Architecture docs** describe **what is actually implemented** — the design patterns, contracts, and mechanisms a reader can verify against the source. These are prescriptive and must stay in sync with the code. Keep this set clean: every doc maps to real, current behaviour.
- **Research docs** hold **background investigations and industry analysis** that *informed* decisions — reference material, not prescriptive, including artifacts that have since been partly superseded. They are explicitly **not authoritative for current behaviour.**

When an investigation produces a decision that lands in code, the codebase-facing explanation goes in the architecture set and the raw exploration stays in the research set, cross-linked. Research transcripts must not accumulate among the prescriptive docs — that is how an authoritative folder rots into a pile of maybe-true history. Organize the whole docs tree by audience and concern, and give it a navigable index that every docs PR keeps current.

## The decision-trail artifacts

Different records serve different moments in a piece of work. Some look *forward* (what we're about to do); some look *back* (what we did and learned). Together they are how a decision plus its evidence survive the moment.

| Artifact | What it captures | Direction |
|---|---|---|
| **Spec** | The design agreed *before* code — architecture, components, data flow, testing. The always-on spec-review gate stops here. | Forward |
| **Plan** | The implementation blueprint — file structure, right-sized tasks, bite-sized TDD steps with complete code. | Forward |
| **Story** | A narrative write-up *after* a piece of work lands — what, why, findings, lessons. | Back |
| **Experiment** | A dated experiment write-up: setup, results, conclusion. | Back |
| **Results log / leaderboard** | The running record of every eval result and the decision it drove. | Back |

The **story** is the one most easily skipped and most valuable. A diff records *what* changed; a story records the *why*, the surprises, and the "don't do it this way" that the diff cannot. It is where tacit knowledge — the calibration that collapsed a schema, the finding that a metric measured the wrong thing — survives past the memory of whoever ran it. The **results log** is the evidence half of "evidence over intuition" ([Part 5](evaluation.md)): a decision is not done until its result is recorded where the next person can find it and build on it.

## Cross-reference sanity: audit docs like a test suite

Docs drift, links rot, and examples go stale even under the same-PR rule, because a change three directories away can invalidate a claim elsewhere. So run periodic **docs-audit** passes that re-read the documentation against the source and fix what has drifted: broken or mislabelled cross-links, stale paths, renamed flags, claims that no longer match the code. Treat an audit as the docs equivalent of running the tests — the value is not the tidy diff, it is the guarantee that every claim was checked against reality. A fabricated flag or a wrong path is a correctness bug for the reader who trusts it, human or agent.

Such a pass looks at three axes. **Organization** — is anything misfiled, duplicated, or deprecated, and (sparingly, because moving docs breaks links) is the tree shaped right? **Cross-referencing** — does every internal link resolve, is every doc reachable from an index (no *orphans*), and do the pairs that should point at each other do so (background ↔ prescriptive, especially)? **Coverage** — for each code component, is it *documented* (a real dedicated doc), *partial* (only a passing mention or a design spec, no prescriptive reference), or a *gap* (nothing)? The partial and gap rows are the work list. The cheapest guardrail is a link-and-index checker wired into CI (the [make-the-standard-executable](lifecycle.md) move), so a dead link or an unindexed doc fails the build instead of rotting quietly.

## Living docs: module docstrings, the rules file, and prompts

Documentation is not only the prose tree.

- **Module and symbol docstrings** are kept current: every module and public symbol has a docstring describing what it does and how to use it — usage patterns plus minimal architecture notes — updated whenever the purpose or interface changes. Docstrings drift the same way prose does, so they audit the same two ways: *coverage* (which public modules/classes/functions have none) and *staleness* (a docstring that names a parameter the function no longer takes, or an example that would now fail). Because a docstring lives in code, fixing one goes through the normal code gate, not the lighter docs-only path.
- **The project's binding-rules file** (the one your team and your coding agents both read as authoritative) holds the coding rules, review thresholds, and git workflow, and is itself maintained. When this handbook and that file disagree, the rules file wins and the handbook is the bug.
- **Prompt / SOP changes** are documented in their commit message with the *why*, not just the *what*, and preferably kept in their own commit (see [Part 1](lifecycle.md)).

## House rule: no hard-wrapping in Markdown source

One paragraph is one line in the source; let the renderer wrap. Never hard-wrap prose to a column, and never reflow code blocks or diagrams. This keeps diffs meaningful (a one-word edit is a one-line change, not a reflowed paragraph) and the source readable in tools that soft-wrap.

## See also

- [Part 1 — Development lifecycle](lifecycle.md) — where specs and plans are produced and the review gates live.
- [Part 5 — Evaluation](evaluation.md) — the loop that the results log and stories feed.
- [Handbook index](README.md).
