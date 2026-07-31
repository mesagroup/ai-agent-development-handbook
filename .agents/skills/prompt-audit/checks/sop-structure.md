---
id: prompt/sop-structure
domain: prompt
locality: local
handbook:
  - implementation-disciplines/prompt-and-sop-engineering-a
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
