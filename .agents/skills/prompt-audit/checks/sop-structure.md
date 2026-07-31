---
id: prompt/sop-structure
domain: prompt
locality: local
handbook: []
handbook_note: >-
  implementation-disciplines.md's prompt-and-sop-engineering clause names
  the section set an SOP should carry (`grep -n "Give an SOP a fixed
  shape" docs/engineering/implementation-disciplines.md`), but the matrix
  row citing that clause, `implementation-disciplines/prompt-and-sop-engineering-a`,
  already lists its five checked dimensions and this is not one of them -
  that row's own gap note records that Tier B declared no bolded dimension
  bullets the pre-migration matrix could parse, and this task converts
  existing citations rather than widening that row. To ground this check a
  clause would additionally have to say that the sections appear *in a
  fixed order* and that *every* step carries its own Constraints block -
  the ordering and per-step nesting rule this check actually verifies -
  which the prose paragraph never states.
---

# SOP section structure

Applies to `.sop.md` files only. Required sections present and in order (**Overview**, **Parameters**, **Steps**), each step carrying a **Constraints** block; optional **Examples** / **Troubleshooting** used where they help.

## Severity

**Critical** - a formal SOP missing a required section it needs to function.

**Minor** - a missing-but-recommended Examples/Troubleshooting section.

## Tooling fallback

**SOP-spec conformance check:** read the file against the SOP specification - sections present and ordered, every step has a Constraints block. Each miss is a finding with the exact `file:line`. Skip this read entirely for a general (non-SOP) prompt - do not raise "missing Overview/Parameters/Steps" against something that was never meant to be an SOP.

## Fix

**Bring an SOP to spec:** add the missing required section, give each step its Constraints block. Do not apply these to a general prompt.

## Review lens

**Spec conformance:** the edited SOP now actually matches the specification - sections, constraints blocks - verified against the file, not asserted. This reviewer does not run on a general prompt.
