---
id: prompt/output-contract
domain: prompt
locality: local
handbook: []
handbook_note: >-
  The handbook's only sentence naming an output schema -
  implementation-disciplines.md's "reserve an SOP for judgment ... enforce
  it in the harness instead: a schema on the output, a validator in the
  tool, a guard in the pipeline" (`grep -n "a schema on the output"
  docs/engineering/implementation-disciplines.md`) - is about moving a
  checkable constraint out of the prompt into deterministic code, not about
  the prompt itself stating its output shape. Citing it here would be the
  near miss the matrix's own rule forbids: a prompt that never specifies
  its output contract but happens to sit in front of a harness-level schema
  validator would pass, which is exactly the gap this check flags.
---

# Output contract

Where the output shape matters it is specified (format, structure, schema, length) and *shown* when it must be strict; where it does not matter it is left free rather than over-constrained. A downstream parser depending on an unspecified format is a latent break.

## Severity

**Critical** - a missing output contract that a downstream consumer parses.

## Tooling fallback

**Well-specified-prompt read:** work the Tier A principles against the text - is the output contract specified where it matters.

A prohibition with no reason, and a missing output contract a consumer depends on, are the signature defects this audit exists to catch - record each with its `file:line`.

## Fix

**Pin the output contract:** pin the output contract (format/schema, shown when it must be strict).

## Review lens

**Well-specified** - the edit actually improved specification - a real output contract where it was missing.
