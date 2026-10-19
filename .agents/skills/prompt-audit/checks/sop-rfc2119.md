---
id: prompt/sop-rfc2119
domain: prompt
locality: local
handbook:
  - implementation-disciplines/prompt-and-sop-engineering-a
routes:
  - lang: any
    kind: procedure
    applies_when: >-
      The file is an SOP, a `.sop.md` file. Skip this read entirely for a
      general (non-SOP) prompt - do not raise "missing
      Overview/Parameters/Steps" against something that was never meant to be
      an SOP.
    note: >-
      **SOP-spec conformance check:** read the file against the SOP
      specification - RFC 2119 vocabulary used. Each miss is a finding with
      the exact `file:line`.
---

# SOP RFC 2119 vocabulary

Applies to `.sop.md` files only. Constraints expressed with the RFC 2119 keyword vocabulary (**MUST** / **SHOULD** / **MAY** and negatives) the spec mandates.

## Fix

**Repair constraint hygiene:** make the requirement strength legible (the right RFC 2119 keyword in an SOP) and downgrade/upgrade a mis-leveled requirement.

## Review lens

**Spec conformance** - the edited SOP now actually matches the specification - RFC 2119 vocabulary - verified against the file, not asserted. This reviewer does not run on a general prompt.

**Constraint correctness** - requirement strength is right and consistent.
