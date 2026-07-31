---
id: prompt/sop-rfc2119
domain: prompt
locality: local
handbook: []
handbook_note: >-
  The same clause names the RFC 2119 keyword vocabulary itself (`grep -n
  "RFC 2119" docs/engineering/implementation-disciplines.md`) and "give
  every negative constraint its reason inline" - the reason-inline half is
  already carried by the mapped `prompt/positive-framing` check. What is
  left after that is this check's own scope: that the vocabulary is
  actually *used* to mark a constraint's stated strength, a narrower
  procedural check that the clause's citing row,
  `implementation-disciplines/prompt-and-sop-engineering-a` - again not
  widened by this task - does not list.
---

# SOP RFC 2119 vocabulary

Applies to `.sop.md` files only. Constraints expressed with the RFC 2119 keyword vocabulary (**MUST** / **SHOULD** / **MAY** and negatives) the spec mandates.

## Tooling fallback

**SOP-spec conformance check:** read the file against the SOP specification - RFC 2119 vocabulary used. Each miss is a finding with the exact `file:line`. Skip this read entirely for a general (non-SOP) prompt - do not raise "missing Overview/Parameters/Steps" against something that was never meant to be an SOP.

## Fix

**Repair constraint hygiene:** make the requirement strength legible with the right RFC 2119 keyword in an SOP, and downgrade/upgrade a mis-leveled requirement.

## Review lens

**Spec conformance:** the edited SOP now actually matches the specification - RFC 2119 vocabulary - verified against the file, not asserted. This reviewer does not run on a general prompt.

**Constraint correctness:** requirement strength is right and consistent.
