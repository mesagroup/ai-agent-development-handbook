---
id: prompt/instruction-precision
domain: prompt
locality: local
handbook:
  - implementation-disciplines/prompt-and-sop-engineering-a
---

# Instruction precision

Directives are specific and unambiguous, not vague filler ("be helpful", "use good judgment", "as appropriate") where a concrete rule is needed; and the *strength* of each requirement is legible, whether through RFC 2119 keywords or plain firm language.

## Severity

**Important** - a vague directive ("use good judgment") where a concrete rule is needed; wrong requirement strength (a soft "should" guarding something that must hold).

## Tooling fallback

**Well-specified-prompt read:** work the Tier A principles against the text - are instructions precise rather than vague filler.

## Fix

**Replace vague filler:** replace vague filler with a concrete rule.

**Repair constraint hygiene:** make the requirement strength legible (plain firm language elsewhere) and downgrade/upgrade a mis-leveled requirement.

## Review lens

**Well-specified** - the edit actually improved specification - vague filler replaced by concrete rules.

**Constraint correctness** - requirement strength is right and consistent; no new vague directive was introduced.
