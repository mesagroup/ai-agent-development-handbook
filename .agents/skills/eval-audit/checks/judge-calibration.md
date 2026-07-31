---
id: eval/judge-calibration
domain: eval
locality: local
optin: true
handbook: []
handbook_note: >-
  `evaluation/use-the-llm-judge-only-where-it-agrees-with-the-human` already
  grounds `eval/methodology` with the qualitative rule (trust the judge only
  on the dimensions where measured human correlation shows it tracks the
  expert); it states no dedicated calibration-study procedure or a
  human-labeled correlation deliverable. `evaluation/step-by-step-running-an-evaluation`'s
  runbook lists "calibrate the judge" as one process step
  (`grep -n "calibrate the judge" docs/audit/handbook-traceability.yaml` ->
  line 880), but that row carries `class: process` and no `checks:` entry at
  all. Running a full correlation study as a standalone deliverable is this
  opt-in's own scope, not a clause the handbook states.
---

# LLM-judge calibration study

Correlate the automated judge against a human-labeled sample and report agreement, before the judge is trusted for decisions - ask the user; recommend on when a judge gates model selection.
