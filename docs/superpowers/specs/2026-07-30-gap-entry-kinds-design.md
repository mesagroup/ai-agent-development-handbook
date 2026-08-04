# Gap-entry kinds in the traceability matrix (lidia-tech/lidia-agents#553 + lidia-tech/lidia-agents#554)

**Status:** draft 2026-07-30. Closes the two matrix stragglers filed during [lidia-tech/lidia-agents#552](https://github.com/lidia-tech/lidia-agents/issues/552) and [lidia-tech/lidia-agents#551](https://github.com/lidia-tech/lidia-agents/issues/551), ahead of the wave-1 skill sweep in [#1](https://github.com/mesagroup/ai-agent-development-handbook/issues/1).

## Problem

The two issues read as unrelated. lidia-tech/lidia-agents#553 is about legibility: the severity-grouped gap list renders a row nothing checks and a row a check partly reaches as identical bullets. lidia-tech/lidia-agents#554 is about arithmetic: the coverage summary's closing total counts every gap-carrying row, while the fully / partially / unmapped breakdown above it partitions auditable rows only.

They are the same latent bug seen from two angles, and the thing that joins them is a row shape that does not exist yet.

A `process` row may carry a `gap`. That permission is deliberate: the taxonomy's `report-only` recommendation exists for exactly the claim that is auditable in principle but belongs in report prose rather than in any skill's matrix. Such a row would be a **third kind** of gap-list entry, and it breaks both issues at once:

- It carries no `checks`, so a two-way rule ("has checks means residue, otherwise unchecked") files it under *unchecked*. That breaks lidia-tech/lidia-agents#553's own acceptance criterion, which requires a band's unchecked count to match the cross-tab's Unmapped column, and the Unmapped column counts auditable rows only.
- It is counted by the closing `len(gaps)` total but excluded from the components above it, which is lidia-tech/lidia-agents#554 verbatim.

So one three-way classification closes both, and neither can be closed correctly on its own.

## The invariant holds only by absence

Measured on the matrix as of `29499564`:

| Band | Bullets | Unchecked | Residue | Process gaps | Cross-tab Unmapped |
|---|---|---|---|---|---|
| Critical | 4 | 4 | 0 | 0 | 4 |
| Important | 47 | 30 | 17 | 0 | 30 |
| Minor | 17 | 13 | 4 | 0 | 13 |
| **Total** | **68** | **47** | **21** | **0** | **47** |

Unchecked matches Unmapped in every band, and all 68 gaps sit on `static` or `artifact` rows. Nothing enforces either fact. This is the same failure family as the three silent-pass bugs lidia-tech/lidia-agents#543 closed in this renderer: arithmetic that is correct only because the case that breaks it has not been written yet.

## Decisions

### 1. Three kinds, tagged on every bullet

Every gap-list bullet carries an explicit kind tag between its link and its recommendation:

| Tag | Row shape | Where it is counted in the cross-tab |
|---|---|---|
| `(unchecked)` | auditable, no `checks` | Unmapped |
| `(residue)` | auditable, has `checks` | Partial |
| `(process)` | `class: process` | Process |

Tag every bullet, including the majority `unchecked` case, rather than tagging only the exceptions. An untagged bullet is ambiguous between "unchecked" and "written before the tag existed", and the gap list is the one part of this document a reader is expected to consume an entry at a time.

That last point is the load-bearing argument for a tag over pure ordering. #9 will emit issues from these entries, and an ordering is a property of the list that is lost the moment an entry is extracted. A bullet has to carry its own kind.

### 2. Per-band count line, with zero terms suppressed

Each severity band opens with a line stating its split: `30 unchecked, 17 residues.` Zero terms are omitted, so the Critical band reads `4 unchecked.` rather than padding two zeroes a reader has to skip.

This is what makes lidia-tech/lidia-agents#553's second acceptance criterion mechanical instead of a counting exercise: the unchecked figure is printed, and it is the same number as the band's Unmapped column.

### 3. Unchecked first, then residue, then process

Within a band, order by kind, and within a kind keep handbook order. A reader triaging work wants the unchecked clauses, and they are what the cross-tab points at.

### 4. The computed Critical-purity note is removed

lidia-tech/lidia-agents#552 added `_critical_purity_note`, a sentence computed per render saying whether the Critical band's entries are all unchecked. Its purpose was to stop the page asserting a coincidence: the band is clean today only because it happens to have no partials.

The per-band count line subsumes it exactly, and generalizes it to all three bands. Keeping both would print the same fact twice in two different shapes, and the narrower one would be the stale-looking one.

Recorded explicitly because this deletes a mechanism two PRs after it shipped. It is a replacement, not a retreat: the guarantee lidia-tech/lidia-agents#552 wanted (the page stops making the claim the moment a Critical row gains a check) is strictly stronger under a printed count than under a sentence that switches between three phrasings.

### 5. The closing summary reconciles visibly

The summary's last sentence currently ends `{len(gaps)} rows carry a gap entry in total`, a figure drawn from a different population than the components before it. It is replaced by a sentence that names the populations and adds up:

- When no process row carries a gap (today): `All 68 gap entries sit on auditable rows: the 47 unmapped ones plus the 21 partial.`
- When two do (today's rows plus two such rows): `68 of the 70 gap entries sit on auditable rows (all 47 unmapped, plus the 21 partial); the other 2 sit on process rows, whose claim is auditable in principle but belongs in report prose rather than in any skill's matrix.`

The process clause renders only when the count is non-zero, so the common path stays readable. The absent case is exactly what the test fixture supplies, which is lidia-tech/lidia-agents#554's stated point: the arithmetic is currently correct only because the case is missing.

### 6. #9 treats the three kinds as different work

Recorded here because lidia-tech/lidia-agents#553's fourth acceptance criterion asks for the decision either way, and the answer is yes, they differ:

- `unchecked` is new capability. Nothing reaches the claim, so closing it means a new dimension or a new domain.
- `residue` is widening something that already runs. A dimension reaches part of the claim, so the work is scoped by what it already does and lands in an existing skill.
- `process` is never skill work at all. It closes by appearing in report prose and an adoption roadmap, and an issue that asks a skill to check it is a mis-filed issue.

An emitter that flattens the three produces a backlog whose items are not comparable in size or in kind. The tag from decision 1 is what carries this downstream.

## Rejected

**Sub-headings per band.** Splitting each band into labelled subsections is the most scannable option on the page, but it pushes the gap list to four heading levels, needs an explicit `none` placeholder for empty groups, and an extracted bullet loses its kind entirely, which defeats decision 6.

**Forbidding `gap` on `process` rows.** The tempting one-line validation fix, and wrong twice over: it removes a shape the taxonomy is designed to express, and it treats a reporting defect as a schema defect. lidia-tech/lidia-agents#554 says so directly, and this spec follows it.

**Requiring `recommendation: report-only` on a process row's gap.** Considered and deferred. The rule is arguably coherent, since a row that no skill can check should not recommend extending a skill, but neither issue asks for it, and a validation rule that forbids a shape nobody has tried yet is how the previous over-constraint would have been introduced. Noted here so a future reader knows it was weighed rather than missed.

## Scope boundary

The severity x coverage cross-tab is **not** changed. Its Process column counts process rows by severity, a different population from its four auditable columns, and its preamble already says so in as many words. It was checked for the same mismatch lidia-tech/lidia-agents#554 describes and does not have it.

## Files

| File | Change |
|---|---|
| `scripts/render_handbook_traceability.py` | Three-way kind classification; per-band count line; kind tag and ordering in the gap list; reconciling closing sentence; `_critical_purity_note` removed |
| `tests/scripts/test_render_handbook_traceability.py` | Fixture with a `process` row carrying a `report-only` gap; tests pinning the kind tags, the per-band counts against the cross-tab, and the reconciling total in both branches |
| `docs/audit/handbook-traceability.md` | Regenerated |

The matrix YAML is unchanged: no row's data is wrong, only how the renderer reports it.

Gates: `render_handbook_traceability.py --check`, the renderer's pytest module, `mkdocs build --strict`, `check_site_links.py`.
