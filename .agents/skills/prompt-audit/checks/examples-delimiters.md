---
id: prompt/examples-delimiters
domain: prompt
locality: local
handbook: []
handbook_note: >-
  The handbook states no clause about few-shot examples or about
  delimiting instructions from data in a prompt - `grep -n
  "delimiter\|few-shot" docs/engineering/*.md` returns nothing. Nothing
  grounds a check whose entire subject is example/delimiter hygiene.
---

# Examples & delimiters

Where the task is format-sensitive or easy to misread, few-shot examples and clear delimiters separate instructions from data, and the examples are **consistent** with the instructions, since an example that contradicts the rules is worse than none.

## Severity

**Important** - missing examples/delimiters on a format-sensitive or untrusted-input prompt.

**Minor** - an example that would aid clarity.

## Tooling fallback

**Well-specified-prompt read:** work the Tier A principles against the text - are examples/delimiters used and consistent with the instructions.

## Fix

**Add examples/delimiters:** where the prompt is format-sensitive or takes untrusted input, add a few-shot example and clear delimiters between instructions and data, keeping the example consistent with the instructions.

## Review lens

**Well-specified:** the edit actually improved specification - examples consistent with the instructions.
