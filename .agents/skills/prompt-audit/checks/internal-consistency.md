---
id: prompt/internal-consistency
domain: prompt
locality: local
handbook: []
handbook_note: >-
  The handbook's only "internal consistency" phrase - lifecycle.md's
  spec self-review checklist ("placeholder scan, internal consistency,
  scope, ambiguity"), reproducible with `grep -n "internal consistency"
  docs/engineering/lifecycle.md` - reviews a design-spec document before
  code is written, not the prompt/SOP artifact this check reads. Its only
  prose about a model resolving contradictory instructions sits in
  troubleshooting.md's Output quality section ("What is left may still
  contradict itself ..."; `grep -n contradict
  docs/engineering/troubleshooting.md`), which the matrix carries as row
  `troubleshooting/output-quality`, an `informative` row that cites no
  check at all. Neither clause grounds a check on contradictions or dead
  references within a shipped prompt or SOP.
---

# Internal consistency

No two instructions contradict; no dead instruction (references a tool, step, or section that no longer exists); each rule stated once canonically rather than in drifting copies.

## Severity

**Critical** - an internal contradiction between two instructions; an instruction that references a tool/step/artifact that no longer exists (dead directive the model may still act on).

**Important** - copy-paste drift of a rule across sections (will diverge).

## Tooling fallback

**Consistency read:** cross-check instructions within the file (and, at consolidation, across sibling prompts) for contradictions, dead references, and ambiguity. Where the prompt references tools/steps, check they still exist (a light drift check; deep tool-drift is `eval-audit`).

## Fix

**Fix a contradiction / dead directive:** reconcile the two instructions or delete the stale one; if a tool/step was removed, remove every instruction that referenced it.

**Consolidate redundant rules:** extract a 3+-times golden rule to a preamble and reference it; consolidate structural redundancy to one canonical location, keeping at most 2-3 deliberate reinforcements of a truly critical rule.

## Review lens

**Intent preservation:** does each edit keep the prompt's intended behavior? A cleanup that removes a load-bearing instruction, or "fixes" a contradiction by deleting the wrong side, is worse than the original.

**No new contradiction / drift:** the edit did not introduce a fresh internal contradiction or a reference to something that doesn't exist.
