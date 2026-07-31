---
id: prompt/cross-prompt-consistency
domain: prompt
locality: global
optin: true
handbook: []
handbook_note: >-
  No clause in the handbook asks for a standing sweep across a prompt
  library as a set; its prompt-and-sop-engineering clause, and every other
  prompt-adjacent clause, is written per-artifact ("an SOP", "a prompt"),
  never "the prompt library" or "every prompt sharing a convention" -
  `grep -rn "prompt librar\|shared convention" docs/engineering/*.md`
  returns nothing. Nothing grounds a check whose entire subject is prompts
  audited together rather than one at a time.
---

# Cross-prompt consistency sweep

When the project has many prompts sharing conventions (a house style for tool descriptions, a shared safety preamble), audit them as a set for drift. Ask the user; useful before standardizing a prompt library.

## Tooling fallback

No dedicated tool: read every prompt/SOP in the library side by side and diff the shared convention (a house style, a safety preamble) across instances.
