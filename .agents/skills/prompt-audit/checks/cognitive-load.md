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
    argv: [python3, "${CLAUDE_PLUGIN_ROOT}/.agents/skills/prompt-audit/scripts/analyze_prompt.py", "<file>"]
    own_runner: true
    note: >-
      **Quantitative scan:**
      `python3 ${CLAUDE_PLUGIN_ROOT}/.agents/skills/prompt-audit/scripts/analyze_prompt.py <file>`
      (or with `--format json`) gives the token budget, per-section
      directive counts and density, the constraint-line count, the
      cross-reference graph + data-flow depth, and the redundancy groups.
      The script is the `prompt-analyzer` skill's scan, vendored into this
      plugin, so it is present wherever the plugin is installed and the
      target need not ship the skill. `python3` is the audit host's own
      interpreter, not the target's, so the route needs no grant; the
      script imports only the standard library, so nothing is fetched. It
      is run through the interpreter rather than by name because it is not
      tracked as executable: with its directory on `PATH`, the bare
      `analyze_prompt.py` fails with `Permission denied`.
    alone_insufficient: >-
      The numbers are the input to the qualitative judgment, not the verdict
      themselves.
  - lang: any
    kind: procedure
    note: >-
      Where the vendored script cannot run, compute the same metrics
      inline: count RFC 2119 keywords per section, estimate tokens
      (~chars/4), and scan for repeated constraint lines - the framework is
      small.
    alone_insufficient: >-
      The numbers are the input to the qualitative judgment, not the verdict
      themselves.
---

# Cognitive load & focus

No section overloaded past what a model tracks in one pass (the prompt-analyzer red flag is >25 directives per section); token budget reasonable for the context it runs in (heavy is >~15% of the working context); mixed concerns ("what to do" tangled with "how to format") split apart; a sane execution model (linear or simply-accumulating is healthy; deep forward-reference chains and graph-like cross-references are a smell).

## Severity

**Important** - a section overloaded past ~25 directives (constraints will be dropped under load); a heavy token budget for the context.

**Minor** - style and hygiene: a prompt style inconsistency, structural redundancy that merely wastes tokens, reference material inline that would read better in an appendix.

## Fix

**Relieve load:** split an overloaded section along its concerns (content-selection vs formatting).

**Restructure for flow:** move inline reference material to an appendix/examples; flatten deep forward-reference chains.
