---
id: prompt/cognitive-load
domain: prompt
locality: local
handbook:
  - implementation-disciplines/prompt-and-sop-engineering-a
tooling:
  any: [analyze_prompt.py]
---

# Cognitive load & focus

No section overloaded past what a model tracks in one pass (the prompt-analyzer red flag is >25 directives per section); token budget reasonable for the context it runs in (heavy is >~15% of the working context); mixed concerns ("what to do" tangled with "how to format") split apart; a sane execution model (linear or simply-accumulating is healthy; deep forward-reference chains and graph-like cross-references are a smell).

## Severity

**Important** - a section overloaded past ~25 directives (constraints will be dropped under load); a heavy token budget for the context.

**Minor** - style and hygiene: a prompt style inconsistency, structural redundancy that merely wastes tokens, reference material inline that would read better in an appendix.

## Tooling fallback

**Quantitative scan:** run `analyze_prompt.py <file>` (or `--format json`) to get the token budget, per-section directive counts and density, the constraint-line count, the cross-reference graph + data-flow depth, and the redundancy groups. If it is not available, compute the same metrics inline: count RFC 2119 keywords per section, estimate tokens (~chars/4), and scan for repeated constraint lines - the framework is small and the numbers are the input to the qualitative judgment, not the verdict themselves.

## Fix

**Relieve load:** split an overloaded section along its concerns (content-selection vs formatting).

**Restructure for flow:** move inline reference material to an appendix/examples; flatten deep forward-reference chains.
