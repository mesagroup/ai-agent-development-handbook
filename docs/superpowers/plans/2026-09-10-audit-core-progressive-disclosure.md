# Plan: two sections out of the file every path loads

Issue #85. Design: [../specs/2026-09-10-audit-core-progressive-disclosure-design.md](../specs/2026-09-10-audit-core-progressive-disclosure-design.md).

In the order that keeps each step's failure legible: move the text, watch the ledger's guard fail where it should, widen it, then guard the failure the move introduces.

## 1. Extract both sections verbatim into `references/`

`## The loop` steps 3-6 to `references/remediation-loop.md`, the `## Authoring a new auditing skill` body to `references/authoring-a-new-auditing-skill.md`. Extracted by slicing the source lines rather than retyping them, so the move cannot alter a word, with an assertion on each boundary line before the slice is taken.

Each file opens with when to read it and, for the remediation half, that the step numbering continues `SKILL.md`'s.

## 2. Replace both regions in `SKILL.md` with pointers

The remediation pointer sits where the four steps were, immediately after the report-only stop. The authoring section keeps its heading and its pointer says the section is not for a run.

## 3. Widen the ledger's anchor search, after watching it fail

The one anchor in the authoring section fails as soon as the section moves, which is the coupling working. Then `tests/test_sweep_obligations.py` searches `SKILL.md` plus every `references/*.md`, globbed rather than listed, counted as one corpus.

## 4. Guard the failure the move introduces

`tests/test_audit_core_references_are_reachable.py`: every reference linked, every link resolving, no rule-length line in both a reference and `SKILL.md`, and the directory non-empty so the rest cannot go vacuous. Mutation-check by orphaning a reference and by leaving a copy inline.

## 5. Blast-radius prose

`docs/audit/sweep-obligations.md`'s re-run instruction says to read `SKILL.md` whole; it now says to read the references with it, and its description of the mechanical half says the anchor search covers both. `CLAUDE.md`'s layout section gains the directory.

## Gates

The six runnable gates. The word count is recomputed and reported rather than taken from the issue or from #86, since both figures are now stale for different reasons.
