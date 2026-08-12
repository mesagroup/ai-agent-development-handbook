# Handbook Part 10: Data Protection & Privacy. Design Spec

**Issue:** [#47](https://github.com/mesagroup/ai-agent-development-handbook/issues/47) · **Date:** 2026-08-12 · **Status:** approved design, pending implementation plan

## Context

The handbook (`docs/engineering/`) is nine parts plus a README spine, a troubleshooting companion and a coda. [Issue #4](https://github.com/mesagroup/ai-agent-development-handbook/issues/4) asks for a `data-protection-audit` domain skill on the `audit-core` engine, covering provider DPAs, EU residency, PII minimization at the trust boundary, retention and deletion, personal data in logs and eval artifacts, and a sub-processor inventory as a deliverable.

The handbook grounds that family. Every check record carries a `handbook:` list of matrix row ids, validated in both directions against `docs/audit/handbook-traceability.yaml`; a record that deliberately exceeds the handbook carries an empty list plus a `handbook_note` saying why.

## Problem

The handbook says one sentence about data protection. It is the closing clause of "Depend only on what you can account for" in Part 9 (`security-supply-chain.md`), plus one checklist line. The matrix already carries it as row `security-supply-chain/depend-only-on-what-you-can-account-for-c`, classed `artifact`, severity `critical`, with `gap: {recommendation: new-domain, target: "#4"}`.

Seven of the eight dimensions #4 enumerates have no clause at all. Built today, `data-protection-audit` would be a domain skill whose records almost all declare themselves beyond the handbook: a lens sitting outside the normative tree it exists to verify, and eight `handbook_note`s arguing for a position the handbook never took. The `handbook_note` mechanism exists for the genuinely-beyond-handbook check, not for a whole missing subject.

The subject is also genuinely missing rather than merely under-written. The handbook asks for a run trail (Part 6), for eval datasets built from real inputs (Part 7), and for a documented decision trail (Part 8), and each of those artifacts is a store of personal data when the product processes personal documents. Nothing in the nine parts notices the collision.

## Goals

- Give the handbook a normative account of data protection, in its own voice: directives backed by their reasons, checklists as the working surface.
- Ground every dimension #4 names, so its check records cite real anchors rather than notes.
- Keep Part 9 whole: what Part 10 takes, Part 9 cross-links rather than repeats.
- Leave the repo's part-count and part-list assertions consistent, and both renderers and the traceability gate green.

## Non-goals

- **No audit skill in this change.** `data-protection-audit` is #4 and stays there. This spec adds no check record and no `checks:` entry to any new matrix row; every new row carries a gap pointing at #4.
- **No legal advice.** The handbook states engineering obligations that a data-protection regime creates, and names GDPR as the regime it is written against. It does not attempt to be a compliance manual, and it says so.
- **No reorder or renumber of Parts 1 to 9.** Part 10 appends.
- **No new troubleshooting symptom.** A symptom entry is its own matrix row and its own routing decision; it can follow later.

## Design

### Why a new part rather than sections inside Part 9

Part 9's frame is three surfaces of *safety* - first-party code, what you depend on, the pipeline that builds you - and its title names them. Three things make data protection a poor fit inside it.

**The subject differs.** Part 9 protects the system from an attacker. Part 10 protects a data subject from the system, including from the system working exactly as designed. A section arguing that inside a part whose organizing question is "what could a malicious pull request do with this pipeline's permissions?" reads as a footnote to the wrong argument.

**The evidence differs.** Part 9's surfaces are all in the repo: source, the resolved graph, workflow files. Part 10's central artifact is a register whose backing evidence - a signed DPA, a provider's retention terms - lives outside the repo entirely, and the engineering directive is therefore about the register and its agreement with the code rather than about the contract. That distinction needs stating once, at the top of a part, not buried in a bullet.

**The reach differs.** Part 10 has to reach into Part 6 (the trail is a store of personal data) and Part 7 (an eval dataset built from real user documents is a store of personal data). A sub-clause of the supply-chain part cannot carry a claim about observability from where it sits.

The cost is real and bounded: a new part file is asserted in a fixed, enumerable set of places, listed under **Blast radius** below, and the traceability gate fails loudly on the two that matter (`PART_ORDER`, and a row per `##` section).

### Placement in the story

Part 10 sits after Part 9 as the **second standing obligation**. Part 9 is introduced in the README spine as "the obligation that no test and no eval will enforce: keeping the machine safe"; Part 10 is its twin, keeping the data lawful for the people it belongs to. Part 9's closing line currently hands off to the coda; it hands off to Part 10 instead, and Part 10 hands off to the coda.

The pairing is also the honest description of when a reader needs it: neither part is a station the change passes through, both stand over every change.

### Sections

Eight `##` sections, matching Part 9's shape (seven substantive, a checklist, a see-also). Each becomes one matrix row unless the claim splits.

**1. Know what personal data you hold, and where it goes.** The data-flow map, which a data-protection regime knows as records of processing. Directive: keep it as a maintained artifact next to the code, enumerating where personal data enters (uploads, forms, integrations, the model's own inputs), where it rests (primary store, object store, vector index, caches, logs, eval datasets, backups), and every outbound edge that leaves the trust boundary. The reason: every later directive in the part is a question asked of one edge or one store, and a team that cannot enumerate them is answering about the ones it happens to remember. Class `artifact` - absence of the map is itself the finding.

**2. Every processor needs a legal basis, and the register must match the code.** Every third party that sees personal data on your behalf is a processor: the model APIs, but also search, OCR and extraction services, hosting, and the ones teams forget - tracing and observability SaaS, error trackers, and eval platforms, all of which receive prompts, and prompts carry the personal data. For each: a signed DPA, whether the provider trains on your data, and the retention window. The engineering directive is the **register**, and that the register is checked against what the code actually calls: a provider reachable from the code and absent from the register is the finding, and it is the only half of this a repo can settle. Class `artifact`, severity `critical`. This is where `security-supply-chain.md`'s current GDPR clause moves to, widened.

**3. Keep the data where the law lets it be.** Residency and lawful transfer: the data stays in the permitted region, or reaches a destination covered by an adequacy decision or standard contractual clauses. Directive: pin the region explicitly in configuration and fail startup when it is unset, rather than accepting a provider SDK's default. The reason is the handbook's own required-never-defaulted argument applied to a border: a defaulted region is how personal data crosses one without anyone deciding to. Class `static` - a region string is in the config, and its absence is readable.

**4. Minimize before the boundary.** The cheapest personal data to protect is the personal data you never sent. Redact, pseudonymize, or truncate before the trust boundary, and prefer sending a reference over a payload where the task allows it. The honest tension, which the section must state rather than hide: redaction can make an agent worse, and the handbook's own answer is that this is measurable - make it an eval dimension (Part 7) rather than a guess in either direction. Class `static`.

**5. Retention and deletion are design decisions, not cleanup.** Give every store holding personal data a retention limit chosen deliberately, and build the deletion path as a feature rather than discovering it under a request. The agentic trap this section exists for: derived copies. An embedding of a personal document is personal data; so is an eval dataset built from real user documents, a cached model response, a run artifact, and a backup. A deletion that reaches the primary store and none of those is a deletion in name. Class `static`.

**6. Personal data does not belong in the trail.** Logs, traces, error messages, run artifacts, eval fixtures. This is the section where the handbook's own "capture the trail" throughline collides with data protection, and the resolution is not to stop capturing: capture the trail, redact the payload - log an identifier you can join back to the record, not the record. Cross-links Part 6 and Part 7, and cross-links Part 9's `security/sensitive-data` surface rather than restating it. Class `static`.

**7. Verify against the real artifacts.** Part 9's standing-check section has a twin here, and it names what the standing check actually reads: the register against the outbound calls the code makes, the retention limits against the stores that exist, a scan of logs and fixtures for personal data. It says plainly which half no repo snapshot can settle - whether a DPA was signed, whether a provider honoured a deletion - so a report distinguishes "unverifiable here" from "clean". Class `artifact`.

**8. Checklist: a data-protection sweep**, then **See also**, matching every other part.

A d2 diagram belongs in section 1 or 4: personal data crossing the trust boundary, with minimization on the outbound edge. The handbook already carries d2 fences and the artifact renderer renders them.

### What Part 9 gives up

Cross-link, don't duplicate. Two edits:

- `security-supply-chain.md`, "Depend only on what you can account for": the sentence beginning "Where you operate under a data-protection regime" shrinks to a pointer at Part 10. The model-and-provider-as-dependencies claim and the retention-terms clause stay, because they are supply-chain claims that hold with no personal data anywhere.
- Part 9's checklist line "Models/providers pinned and recorded; retention terms and (where applicable) **DPA/GDPR basis** confirmed" keeps the pinning and retention half and points at Part 10's checklist for the DPA half.

Consequences in the matrix:

- Row `security-supply-chain/depend-only-on-what-you-can-account-for-c` **retires**. Its claim moves into Part 10 section 2, and its `gap: {new-domain, target: "#4"}` moves with it. Rows `-a` and `-b` still cover the section, so no coverage hole opens.
- Row `security-supply-chain/checklist-a-security--supply-chain-sweep` restates the fifteen checklist items in its `claim`; the dependencies group's wording updates to match the edited line.

### The matrix rows

One row per new `##` section, `part` stem `data-protection`. Every row is auditable (`static` or `artifact`) except the checklist recap (`process`) and See also (`informative`), and every auditable row carries `gap: {recommendation: new-domain, target: "#4"}` - because no domain owns this yet, which is the whole point of #4.

The one exception to consider on its merits: section 6 (personal data in the trail) is partly reached today by `security/sensitive-data`, whose stated subject is "secrets/PII written to logs or error messages". The near-miss rule governs. That check would *flag* a violation of section 6's log clause rather than pass it, so section 6 maps `security/sensitive-data` and records the residue - eval fixtures, run artifacts and stored traces are outside that check's reach - as a gap on the same row. Mapping it also creates the reciprocal edge, so `security/sensitive-data`'s record gains the new anchor in its `handbook:` list, in the same commit, per the one-edge-set rule.

Severities, on the matrix's own rubric (critical = exposure that is hard to undo or reaches beyond the team; the rendered legend's test is "could this appear in an incident report or a legal review?"): sections 2, 3, 5 and 6 are `critical` - each is a route by which personal data reaches somewhere it may not be, or fails to leave somewhere it must. Sections 1, 4 and 7 are `important`: absence of a map, of minimization, or of a standing check does not itself expose data, it destroys the ability to know whether it is exposed.

### Blast radius

Every place that asserts the part count, the part list, or a claim this change falsifies:

| File | What changes |
|---|---|
| `docs/engineering/data-protection.md` | New. `# Part 10. Data protection & privacy`. |
| `docs/engineering/README.md` | "the nine parts" in the story; the story's closing paragraph, which currently ends on Part 9; the parts-at-a-glance table; the throughlines table (a row 10); the Part 9 pointer in "Starting from zero". |
| `docs/engineering/security-supply-chain.md` | The two clauses above; the closing hand-off, which now points at Part 10; See also. |
| `docs/engineering/documentation.md` | Its hand-off line reads "the **one** obligation that stands over every change", which this change falsifies by making Part 10 the second. The line leads into two parts now. |
| `docs/engineering/observability.md`, `evaluation.md` | See-also cross-links, since Part 10 reaches into both. |
| `docs/engineering/troubleshooting.md` | "The nine parts" in its opening italic. |
| `docs/engineering/coda.md` | Read it; likely unchanged. |
| `scripts/render_handbook_artifact.py` | The `PARTS` list (a `p10` entry before `troubleshooting`) and the comment saying the nine parts follow. |
| `scripts/render_handbook_traceability.py` | `PART_ORDER` and `PART_TITLES`; `validate_parts` fails on a part file absent from either. |
| `docs/audit/handbook-traceability.yaml` | The new rows, the retiring row, the two edited Part 9 claims, and any row whose own `claim` asserts the part count or quotes prose this change edits - `README/the-story-of-a-change` says "through the nine parts" today. Re-render `handbook-traceability.md`. |
| `.agents/skills/security-audit/checks/sensitive-data.md` | The reciprocal `handbook:` anchor for the section-6 mapping. |
| `CLAUDE.md`, root `README.md` | "nine parts". |

The gate does not help with two rows of that table. Nothing validates a matrix row's `claim` text against the prose it paraphrases, and nothing validates a hand-off sentence against the parts it hands off to, so a stale claim and a falsified "the one obligation" both leave the whole suite green. They are found by reading, which is why the verification below ends with a stale-prose pass rather than with a command.

Not in the blast radius, checked: the `*-audit` skills name domains rather than handbook parts, so none of them enumerates nine; `docs/audit/sweep-obligations.md` tracks `audit-core` obligations against the `audit` sweep and neither file changes here; `tests/scripts/test_render_handbook_traceability.py` monkeypatches `PART_ORDER` and `PART_TITLES` in every test that touches them, so no test hardcodes the real list.

### Voice and constraints

The handbook's house rules apply and are load-bearing here:

- No em-dash (U+2014) anywhere in `docs/engineering/` or in this spec and its plan. Use ` - `.
- Markdown is never hard-wrapped: one paragraph is one source line.
- Links to files in this repo are absolute GitHub URLs where a skill would read them; inside `docs/engineering/` the parts link to each other relatively, as they already do.
- No environment-specific values, and no fabricated citation. Where the part cites a regime or a mechanism (GDPR, adequacy decisions, standard contractual clauses), cite the primary source, as Part 9 does for GDPR and for the lethal trifecta.
- Directives backed by reasons, checklist at the end, See-also footer. A reader landing on Part 10 cold, mid-task, can use it.

Length: Part 9 is about 1650 words; Parts 6 and 8 are about 1265 and 1640. Part 10 should land in the same band, roughly 1400 to 1800 words. It is a normative part, not a compliance manual, and the discipline that keeps it there is that every directive must be something an engineer *does to the repo*.

**Amended after implementation: the part is about 2970 words, and the band above was a bad estimate rather than a target it missed.** Three things it did not account for. Part 10 carries **seven** substantive sections against Part 9's seven-in-1690, but each of its sections has to establish what the artifact under discussion *is* before it can give a directive about it, because none of them (a data-flow map, a processor register, a retention limit, a deletion path) is something a reader already has. Part 9's sections address artifacts the reader unambiguously already has: their code, their lockfile, their workflow files. Second, four dimensions the issue named needed a **term of art kept straight** in prose - a legal basis is not a processor contract, a data-flow map is not a full record of processing, adequacy is not the only lawful transfer route - and each correction is a clause that a part written without the legal surface would not carry. Third, the checklist is 16 items where Part 9's is 15, and it groups per section, so it is longer per item. A trim pass ran over the two paragraphs a reviewer identified as arguing rather than instructing, which is the right test; what remains is directive-plus-reason throughout, and cutting further would remove reasons the handbook calls load-bearing. Compare against `implementation-disciplines.md` (about 2800) rather than against Part 9: that is the band a part lands in when its sections have to define their subject.

## Verification

- `uv run python scripts/render_handbook_traceability.py --check` passes, which is the gate that catches a missing `PART_ORDER` entry, a `##` section with no row, and a record/matrix edge that exists in only one direction.
- `uv run python scripts/render_handbook_artifact.py` builds with the new part in place (needs the d2 CLI). The one expected warning about an unmapped `engineering-notes.md` link is pre-existing.
- `uv run pytest tests/ -q`, `uv run ruff check .`, `uv run ruff format --check .`.
- A read-through of the new part against #4's eight dimensions: each one names the section that grounds it, or is deliberately recorded as out of scope.
- A stale-prose pass over the blast-radius table, dispatched to an agent that has not seen the new part.

## Open questions

None. The two decisions that shaped this - handbook before skill, and a new part rather than sections in Part 9 - were settled with the user before this spec was written.
