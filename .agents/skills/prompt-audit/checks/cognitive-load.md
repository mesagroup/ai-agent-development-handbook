---
id: prompt/cognitive-load
domain: prompt
locality: local
handbook:
  - implementation-disciplines/prompt-and-sop-engineering-a
routes:
  - lang: any
    kind: command
    tool: analyze_prompt.py
    argv: [analyze_prompt.py, "<file>"]
    own_runner: true
    applies_when: >-
      The project or the audit environment ships the `prompt-analyzer` skill,
      whose quantitative scan this script is.
    note: >-
      **Quantitative scan:** `analyze_prompt.py <file>` (or with `--format
      json`) gives the token budget, per-section directive counts and
      density, the constraint-line count, the cross-reference graph +
      data-flow depth, and the redundancy groups. The numbers are the input
      to the qualitative judgment, not the verdict themselves.
  - lang: any
    kind: procedure
    note: >-
      Where `analyze_prompt.py` is not available, compute the same metrics
      inline: count RFC 2119 keywords per section, estimate tokens
      (~chars/4), and scan for repeated constraint lines - the framework is
      small and the numbers are the input to the qualitative judgment, not
      the verdict themselves.
---

# Cognitive load & focus

No section overloaded past what a model tracks in one pass (the prompt-analyzer red flag is >25 directives per section); token budget reasonable for the context it runs in (heavy is >~15% of the working context); mixed concerns ("what to do" tangled with "how to format") split apart; a sane execution model (linear or simply-accumulating is healthy; deep forward-reference chains and graph-like cross-references are a smell).

## Severity

**Important** - a section overloaded past ~25 directives (constraints will be dropped under load); a heavy token budget for the context.

**Minor** - style and hygiene: a prompt style inconsistency, structural redundancy that merely wastes tokens, reference material inline that would read better in an appendix.

## Fix

**Relieve load:** split an overloaded section along its concerns (content-selection vs formatting).

**Restructure for flow:** move inline reference material to an appendix/examples; flatten deep forward-reference chains.
