---
id: prompt/positive-framing
domain: prompt
locality: local
handbook:
  - implementation-disciplines/prompt-and-sop-engineering-a
---

# Positive framing, prohibitions with reasons

The prompt says what *to do*, not only a wall of don'ts; and every prohibition that remains states its **reason inline** ("don't do X *because Y*"). This is the transferable core of the SOP negative-constraint rule, applied to *any* prompt: a reasoned prohibition is one the model won't quietly reintroduce.

## Severity

**Critical** - a prohibition with no reason on a safety- or correctness-critical rule.

**Important** - a wall of prohibitions with no positive statement of what to do.

## Tooling fallback

**Well-specified-prompt read:** work the Tier A principles against the text - is the framing positive with every prohibition carrying its reason.

A prohibition with no reason, and a missing output contract a consumer depends on, are the signature defects this audit exists to catch - record each with its `file:line`.

## Fix

**Flip prohibitions to positives, with reasons:** state the desired behavior rather than only the ban, and give each remaining prohibition its inline reason ("… because …" / "… since …"). Applies to any prompt, not just SOPs.

## Review lens

**Well-specified** - the edit actually improved specification - prohibitions flipped to positives and carrying reasons.

**Constraint correctness** - every prohibition now carries a reason.
