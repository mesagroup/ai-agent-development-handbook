---
id: prompt/grounding
domain: prompt
locality: local
handbook:
  - implementation-disciplines/prompt-and-sop-engineering-a
  - observability/keep-observability-out-of-the-models-context
routes:
  - lang: any
    kind: procedure
    note: >-
      **Well-specified-prompt read:** work the Tier A principles against the
      text - is grounding and unknown-handling present.
---

# Grounding & handling the unknown

The prompt supplies the context the task needs (and not a pile it doesn't), and says how to handle missing information, uncertainty, and untrusted or tool-returned content; for factual tasks, explicit guidance against fabrication.
