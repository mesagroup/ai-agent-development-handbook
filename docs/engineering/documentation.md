# Part 7. Documentation & Knowledge Capture

*The change shipped and the verdict is in. What survives of it now (for a teammate, a future you, or an agent dispatched with zero conversation history) is only what was written down. This part is about the artifacts that make a decision and its evidence recoverable, and about keeping every written claim true against the code it describes.*

This is the "capture the trail" throughline made concrete. You develop with agents and across long time horizons, so make a decision, and the evidence that justified it, recoverable by someone who wasn't there: a new teammate, a future self, or a subagent dispatched with zero conversation history. Don't treat documentation as an afterthought to the code; it is where the *why* lives, so hold it to nearly the same standard as the code.

## Aim for docs that stand alone; drifted docs are worse than none

Aim high: **the docs alone should convey what the system does and how it is built, without reading the source**: if the team stopped for six months, you should be able to restart from the docs. Everything below is in service of that.

A doc that has drifted out of sync with the code does more damage than a missing one. An empty spot invites you to go read the source; a confidently wrong doc launders a stale belief into an authoritative-looking claim and stops you looking. So hold docs to the same rule that governs a test: **a claim in the docs must be verifiable, and it must have been verified.** A cross-link that points at a moved file, an import path that no longer resolves, a flag that was renamed, treat each as a silent liability, and finding and fixing them as real work, not tidying. Enforce it by moving a change and its documentation together, in the same PR, not "later."

## Keep the architecture-vs-research split

Keep two kinds of writing distinct, because they look similar and mean opposite things:

- **Architecture docs** describe **what is actually implemented**: the design patterns, contracts, and mechanisms a reader can verify against the source. Keep these prescriptive and in sync with the code; every doc maps to real, current behaviour.
- **Research docs** hold **background investigations and industry analysis** that *informed* decisions, reference material, not prescriptive, including artifacts that have since been partly superseded. Mark them explicitly **not authoritative for current behaviour.**

When an investigation produces a decision that lands in code, put the codebase-facing explanation in the architecture set and leave the raw exploration in the research set, cross-linked. Don't let research transcripts accumulate among the prescriptive docs, that is how an authoritative folder rots into a pile of maybe-true history. Organize the whole docs tree by audience and concern, and give it a navigable index that every docs PR keeps current.

## Keep the decision-trail artifacts

Different records serve different moments in a piece of work. Some look *forward* (what you're about to do); some look *back* (what you did and learned). Together they are how a decision plus its evidence survive the moment.

| Artifact | What it captures | Direction |
|---|---|---|
| **Spec** | The design agreed *before* code, architecture, components, data flow, testing. The always-on spec-review gate stops here. | Forward |
| **Plan** | The implementation blueprint, file structure, right-sized tasks, bite-sized TDD steps with complete code. | Forward |
| **[ADR](https://adr.github.io/)** | One durable architectural decision, its alternatives, and the rationale for the choice, socialized with 1-3 readers before implementation. | Forward |
| **Story** | A narrative write-up *after* a piece of work lands, what, why, findings, lessons. | Back |
| **Experiment** | A dated experiment write-up: setup, results, conclusion. | Back |
| **Results log / leaderboard** | The running record of every eval result and the decision it drove. | Back |

An ADR is not a spec and not a story: a spec scopes one change and its acceptance, a story looks back at what a piece of work taught, and an ADR records a decision meant to *outlive* both, the kind a future contributor would otherwise reverse without knowing why it was made. Keep the boundary clean: architectural rationale (why this boundary, why this datastore, why not the obvious alternative) goes in the ADR; implementation-level rationale stays in the story.

Treat the data model itself as a first-class context artifact alongside these: a versioned, explicit description of the schemas the system works over, plus their known quirks and invariants, that both people and agents are pointed at. An agent left to infer the data model from scattered code will reinvent it wrong, and an undocumented quirk is a bug waiting for the next author who does not know it is there.

Don't skip the **story**: it is the one most easily skipped and most valuable. A diff records *what* changed; a story records the *why*, the surprises, and the "don't do it this way" that the diff cannot. It is where tacit knowledge, the calibration that collapsed a schema, the finding that a metric measured the wrong thing, survives past the memory of whoever ran it. And treat the **results log** as the evidence half of "evidence over intuition" ([Part 6](evaluation.md)): a decision is not done until its result is recorded where the next person can find it and build on it.

## Audit docs like a test suite

Docs drift, links rot, and examples go stale even under the same-PR rule, because a change three directories away can invalidate a claim elsewhere. So run periodic **docs-audit** passes that re-read the documentation against the source and fix what has drifted: broken or mislabelled cross-links, stale paths, renamed flags, claims that no longer match the code. Treat an audit as the docs equivalent of running the tests, the value is not the tidy diff, it is the guarantee that every claim was checked against reality. A fabricated flag or a wrong path is a correctness bug for the reader who trusts it, human or agent.

Look along three axes:

- **Organization**: is anything misfiled, duplicated, or deprecated, and (sparingly, because moving docs breaks links) is the tree shaped right?
- **Cross-referencing**: does every internal link resolve, is every doc reachable from an index (no *orphans*), and do the pairs that should point at each other do so (background ↔ prescriptive, especially)?
- **Coverage**: for each code component, is it *documented* (a real dedicated doc), *partial* (only a passing mention or a design spec, no prescriptive reference), or a *gap* (nothing)? The partial and gap rows are the work list.

The cheapest guardrail is a link-and-index checker wired into CI (the [make-the-standard-executable](lifecycle.md) move), so a dead link or an unindexed doc fails the build instead of rotting quietly.

## Keep the living docs current too

Documentation is not only the prose tree.

- **Module and symbol docstrings**: keep every module and public symbol carrying a docstring describing what it does and how to use it (usage patterns plus minimal architecture notes), updated whenever the purpose or interface changes. Docstrings drift the same way prose does, so audit them the same two ways: *coverage* (which public modules/classes/functions have none) and *staleness* (a docstring that names a parameter the function no longer takes, or an example that would now fail). Because a docstring lives in code, route fixing one through the normal code gate, not the lighter docs-only path.
- **The project's binding-rules file** (the one your team and your coding agents both read as authoritative), hold the coding rules, review thresholds, and git workflow here and maintain it. When this handbook and that file disagree, the rules file wins and the handbook is the bug.
- **Prompt / SOP changes**: document them in their commit message with the *why*, not just the *what*, and keep them in their own commit where you can (see [Part 1](lifecycle.md)).
- **Diagrams as code, generated from source**: keep any generated diagram in a text metalanguage ([Mermaid](https://mermaid.js.org/), [PlantUML](https://plantuml.com/), [D2](https://d2lang.com/)) rather than a binary image, and regenerate it from the source of truth on merge. A diagram drawn by hand or by a model drifts from the code the moment either changes; one generated from the code cannot, and it stays diffable in review like the rest of the source.

## House rule: don't hard-wrap Markdown source

Write one paragraph as one line in the source; let the renderer wrap. Never hard-wrap prose to a column, and never reflow code blocks or diagrams. This keeps diffs meaningful (a one-word edit is a one-line change, not a reflowed paragraph) and the source readable in tools that soft-wrap.

## Checklist: shipping documentation

- [ ] Every code change moves its docs in the **same PR**, not "later."
- [ ] Each claim (path, flag, import, cross-link) was **verified against the source**, not assumed.
- [ ] Prescriptive content sits in **architecture** docs; superseded exploration sits in **research** docs, cross-linked.
- [ ] The relevant decision-trail artifact exists (spec/plan forward; **story**/experiment/results-log back).
- [ ] Touched docs are reachable from an **index** (no orphans); reciprocal links present.
- [ ] Module / symbol **docstrings** updated for any changed purpose or interface.
- [ ] Markdown source is **not hard-wrapped**.
- [ ] A **link-and-index checker** guards this in CI where possible.

*Next: the one obligation that stands over every change rather than following any single one. [Part 8. Security, dependencies & supply chain](security-supply-chain.md).*

## See also

- [Part 1. Development lifecycle](lifecycle.md), where specs and plans are produced and the review gates live.
- [Part 6. Evaluation](evaluation.md), the loop that the results log and stories feed.
- [Handbook index](README.md).
