---
id: prompt/sop-naming
domain: prompt
locality: local
handbook: []
handbook_note: >-
  The same prompt-and-sop-engineering clause names the `.sop.md` file
  and `snake_case`, required-or-optional parameters (`grep -n
  "snake_case" docs/engineering/implementation-disciplines.md`), but it
  never says the filename must be kebab-case, nor that required
  parameters must be *listed before* optional ones - the two rules this
  check verifies beyond what the clause states. And the matrix row that
  clause already grounds,
  `implementation-disciplines/prompt-and-sop-engineering-a`, does not cite
  this record (see `prompt/sop-structure`'s note on the same row); widening
  that citation is outside what this task touches.
---

# SOP naming & parameter form

Applies to `.sop.md` files only. Correct `.sop.md` extension and kebab-case filename; `snake_case` parameter names, each marked `(required)` / `(optional[, default: …])`, with required listed before optional.

## Severity

**Important** - SOP parameters mis-ordered or not `snake_case`.

**Minor** - a filename not in kebab-case.

## Tooling fallback

**SOP-spec conformance check:** read the file against the SOP specification - parameters well-formed and ordered, filename/extension correct. Each miss is a finding with the exact `file:line`. Skip this read entirely for a general (non-SOP) prompt - do not raise "missing Overview/Parameters/Steps" against something that was never meant to be an SOP.

## Fix

**Bring an SOP to spec:** fix parameter naming/ordering, rename to `.sop.md` / kebab-case. Do not apply these to a general prompt.

## Review lens

**Spec conformance:** the edited SOP now actually matches the specification - parameter form - verified against the file, not asserted. This reviewer does not run on a general prompt.
