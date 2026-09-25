---
id: eval/adversarial
domain: eval
locality: global
optin: true
handbook: []
handbook_note: >-
  The handbook's only injection-resistance clause - matrix row
  `evaluation/measure-the-behaviors-that-matter-a`, reproducible with
  `grep -n "adversarial injection-resistance"
  docs/audit/handbook-traceability.yaml` - already grounds `eval/coverage`
  and `eval/prompt-quality`: it says to make injection-resistance an eval
  dimension, not to run a dedicated red-team/adversarial-suite as its own
  procedure. No other row names adversarial or red-team testing, so mapping
  this opt-in to that same row would cite one instruction under a third
  check rather than ground a distinct clause.
answers_ungranted: none
routes:
  - lang: any
    kind: procedure
    needs: target-execution
    note: >-
      No tool in this domain's evidence pass runs a red-team or adversarial suite: probe prompt-injection and jailbreak resistance as a behavioral suite by hand, and frame the security overlap for the report rather than re-deciding it here. Probing is running the target's agent, so this route needs the `target-execution` grant.
---

# Adversarial / red-team eval

Probe prompt-injection and jailbreak resistance as a behavioral suite (the security overlap is noted for the report here, not re-decided) - enable via argument or ask the user.
