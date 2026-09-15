# AI Agent Development Handbook: Narrative Restructure. Design Spec

**Issue:** `<origin-repo>#531` · **Date:** 2026-07-27 · **Status:** approved design, pending implementation plan

## Context

The AI Agent Development Handbook (`docs/engineering/`, authored in `<origin-repo>#501`) is a project-agnostic guide of nine files: a README (overview and stance) plus eight numbered parts. It is excluded from the MkDocs site (`<origin-repo>#529`) and ships as a single self-contained HTML page rendered by `scripts/render_handbook_artifact.py`, whose `PARTS` list fixes the section order.

## Problem

The handbook is strong at the item level but reads as a collection of more-or-less independent best-practice items. A critical read found five specific defects:

1. **The part order is almost a causal chain, but nobody says so.** The latent argument (delegation needs gates; the process scales only on clean seams; seams enable a shared harness; the harness gives you eyes; eyes make decisions falsifiable; decisions must be recorded; the machine must be safe) is never narrated. The README presents the parts as a flat table.
2. **Part 6 (three-layer document model) interrupts the sequence.** It is the only domain-specific part and sits between two general-practice parts (evaluation, documentation). Its strongest conceptual link is to Part 2 (codebase structure): the same reusable-core-vs-task-layer idea.
3. **The README undersells its own motifs.** It claims two throughlines, but the parts run on four: *evidence over intuition* and *capture the trail* (named), plus *reusable core vs. disposable task layer* (carries Parts 2, 3, 6, uncredited) and *make the standard executable* (recurs in Parts 1, 7, 8, named only in passing).
4. **Connective tissue is association, not narrative.** Cross-links and "See also" footers say "related", never "therefore". No part hands off to the next.
5. **Within parts, the same flatness recurs**, most visibly in Part 1 (TDD / CI / review / quality gate / hygiene / prompt-SOP as siblings without an arc) and Part 4 (observability sections as parallel items).

## Goals

- Give the handbook a narrative thread a cover-to-cover reader can follow, while keeping every directive stateable as a single item.
- Preserve each part as an independently consultable reference (directive voice, checklists intact).
- Make the four throughlines explicit and navigable.
- Result quality is the priority; a moderate length increase (~1.5–2k words) is acceptable.

## Non-goals

- No change to the binding-rules relationship (CLAUDE.md stays authoritative; the handbook explains).
- No full prose sweep of all parts (comma-splice cleanup is scoped to new prose and Parts 1 and 4 only).
- No change to the MkDocs site (the handbook stays excluded) and no renaming of the markdown files.
- No new parts and no removal of existing content items.

## Design: the composite approach

Three frames were evaluated (causal-chain bridges; four-throughlines grouping; lifecycle-as-spine). Evaluated on final-result quality rather than effort, lifecycle-as-spine produces the best book, the throughline inventory is the best concept map, and part-integrity is the best consultability guarantee. The design combines all three.

### 1. The spine: the life of one change

The organizing narrative is one change followed end to end: an idea becomes an issue, gets specced, planned, implemented, reviewed, merged; then it ships, runs, is observed and measured; and what it teaches becomes the next issue. The story closes into a loop, embodying the handbook's own claim that the improvement loop does not terminate.

Parts are ordered by where the change first touches them. Standing preconditions (codebase structure, the harness) are introduced as the scenery the change moves through, at the moment of first contact, not forced into being "steps".

| # | Part (file) | Role in the story |
|---|---|---|
| — | README | The story itself (compact), the four throughlines, the matrix |
| 1 | Development lifecycle (`lifecycle.md`) | The spine, in operational detail |
| 2 | Codebase structure (`codebase-structure.md`) | The change needs a home; why the home is shaped like this |
| 3 | Three-layer document model (`three-layer-model.md`) | The same shape in the domain the change manipulates |
| 4 | The extended agent harness (`agent-harness.md`) | The machinery the change runs on |
| 5 | Observability (`observability.md`) | The change ships; now you watch it |
| 6 | Evaluation (`evaluation.md`) | Was it actually better? The loop closes here |
| 7 | Documentation & knowledge capture (`documentation.md`) | What the change leaves behind |
| 8 | Security, dependencies & supply chain (`security-supply-chain.md`) | The standing obligation across all changes |

The only reorder is three-layer-model: position 6 → 3, adjacent to its sibling idea. Parts 7 and 8 keep their positions, but their bridges are framed honestly: documentation as *what remains when the loop closes*, security as *a standing obligation*, not causal consequences of evaluation.

### 2. README rewrite

The README becomes three layers, in this order:

1. **The story** (~600–900 words). The narrative arc of one change, written once, well: second person, restrained, each stage linking to its part. Replaces the flat "The parts" table as the primary tour. A compact reference table of parts (number, title, one-line role) is kept below the story for scanners.
2. **The four throughlines**, each introduced with the three-beat pattern (what it is in one sentence; why it matters; how it connects to the parts):
   - *Evidence over intuition* (existing text, tightened)
   - *Capture the trail* (existing text, tightened)
   - *Reusable core vs. disposable task layer* (new; distilled from Parts 2/3/4)
   - *Make the standard executable* (new; distilled from Parts 1/7/8)
3. **The throughline × part matrix**, a plain markdown table (no mermaid dependency; renders in the artifact pipeline and on GitHub). ● = the part is a primary home of the throughline; ○ = the part draws on it.

| Part | Evidence over intuition | Capture the trail | Core vs. task layer | Executable standards |
|---|:-:|:-:|:-:|:-:|
| 1 Lifecycle | ○ | ● | | ● |
| 2 Codebase structure | | | ● | ○ |
| 3 Three-layer model | ○ | | ● | |
| 4 Agent harness | ○ | | ● | |
| 5 Observability | ● | ○ | | |
| 6 Evaluation | ● | ○ | | |
| 7 Documentation | | ● | | ○ |
| 8 Security | ○ | | | ● |

The existing "How to use this handbook" and "Where the binding rules live" sections stay, trimmed. The "stance" section (you develop *with* agents) is folded into the story's framing rather than kept as a separate essay.

### 3. The dual-register rule

**Narrative lives in the connective tissue; reference lives in the bodies.**

- Each part **opens** with a *you-are-here* bridge: 2–4 sentences giving the change's state in the story, the problem the part addresses, and the throughline(s) it cashes in. Visually set off from the body as an *italicized paragraph*, the same convention in all eight parts (not a blockquote: the handbook already uses blockquotes for operational side-notes, e.g. the subagent-shell note in Part 1, and the two must stay distinguishable).
- Each part **closes** with a one-line hand-off to the next part (placed before or in place of the "See also" footer; "See also" links are kept for reference navigation).
- Part **bodies** keep their directive voice, checklists, and standalone readability. A reader landing cold on any part loses nothing. The story frame never infects the directives.

### 4. Voice and style rules

Derived from the author's personal technical-writing style guidelines (provided as an input; applied selectively, genre-appropriate):

- **Voice split by register.** Narrative tissue (README story, bridges): "we" when walking through the process, "you" for what the reader experiences, occasional rhetorical-question pivots ("The change is merged. Is the product better?"), an occasional short conversational pace-changer. Directive bodies: the existing clipped imperative.
- **No em-dashes anywhere** (already a handbook-wide rule, enforced by the render script's counter).
- **No comma splices in new or retouched prose.** Where the em-dash removal in `<origin-repo>#501` left comma splices, prefer a colon, parentheses, or a restructured sentence. Scope: all new prose, plus Parts 1 and 4 (reworked anyway). Other parts: out of scope, possible follow-up.
- **Italicize key domain terms on first introduction; bold sparingly** (list lead-ins and feature names).
- Not imported (wrong genre for an internal handbook): About-the-author, header images, external-link generosity, "Stay tuned" closings, acronym-spell-out retrofits.

### 5. Within-part rework (Parts 1 and 4 only)

- **Part 1 (lifecycle):** order the sections along the spine itself (they already almost are) and add one-line connectors so TDD → CI → review protocol → quality gate → hygiene → prompt-SOP read as stations on the change's path, not siblings. Content items are preserved; only ordering and connective sentences change.
- **Part 4 (observability):** connect the sections as one argument: see (instrument) → attribute (per-agent usage) → cost (full accounting) → diagnose (errors) → feed back (production loop). Same constraint: items preserved, mortar added.
- All other parts: bridge + hand-off only; bodies untouched except renumbering references.

### 6. Mechanical consequences

- **Renumbering sweep.** Filenames are unnumbered (no renames, no link breakage). The renumbering touches: each part's H1 ("Part N. Title"), every "Part N" prose mention and `[Part N](file.md)` link text across all 9 files, and the "See also" footers. Three-layer becomes Part 3; parts formerly 3, 4, 5 become 4, 5, 6.
- **Render script.** `scripts/render_handbook_artifact.py`: reorder the `PARTS` list to match; sidebar labels updated if part titles change. The script's link-map validation (0 unmapped `.md` hrefs) and em-dash counter (must stay 0) are regression checks.
- **Verification gates.** `uv run scripts/render_handbook_artifact.py` (clean render: 9 sections, 0 unmapped, 0 em-dashes); `uv run python scripts/check_docs.py` (no dead links, index coverage); existing unit tests for the render script's pure transforms (`tests/scripts/`) still pass; `ruff` clean (script edit). No MkDocs impact: the handbook is excluded from the site.
- **Consistency check (manual, review-time):** every "Part N" mention in prose resolves to the correct file after renumbering; the matrix's ●/○ assignments match what each part's bridge claims.

## Risks and mitigations

- **Gimmick risk:** a sustained story frame across ~15k words can tip into cuteness. Mitigation: the dual-register rule confines narrative to the README story and the bridges; bridges are capped at 2–4 sentences.
- **Standalone-consultability regression:** bridges that assume the story has been read would break mid-book entry. Mitigation: each bridge must state the part's problem in its own words, not only by story reference; review each part cold.
- **Renumbering misses:** a stale "Part 5" reference after the reorder is a correctness bug for the reader. Mitigation: grep-driven sweep for `Part [0-9]` and `](.*\.md)` across `docs/engineering/`, verified in review.
- **Matrix drift:** the ●/○ table can silently drift from the parts. Mitigation: the matrix is anchored to the bridges (each bridge names its throughlines); checking the two against each other is a review-checklist item.
