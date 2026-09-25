---
id: eval/cost-latency
domain: eval
locality: global
optin: true
handbook: []
handbook_note: >-
  `observability/account-for-the-full-cost-not-the-convenient-part` already
  grounds `eval/methodology` (pair an efficiency number with an independent
  quality check) and
  `agent-harness/offer-cheap-and-mock-backends-a-fast-inner-loop-is-a-discipline`
  already grounds `eval/regression-tracking` (offer a cheap/mock backend).
  `evaluation/measure-honestly-b` states the same full-cost-accounting claim
  but carries no `checks:` entry (`grep -n "evaluation/measure-honestly-b" -A8
  docs/audit/handbook-traceability.yaml` shows a `gap:` block targeting issue
  #2, not a `checks:` list). None of these asks for a dedicated per-eval
  cost/latency profile as its own artifact; producing one is this opt-in's own
  scope, not a clause the handbook states.
routes:
  - lang: any
    kind: procedure
    needs: target-execution
    answers: profile
    note: >-
      No tool in this domain's evidence pass reaches this: measure per-eval cost and latency by hand. Measuring them runs the target's evals, so this route needs the `target-execution` grant.
  - lang: any
    kind: procedure
    answers: cheap-mode
    note: >-
      Identify a mock or cheap mode by reading the eval runner or CLI for one. This half needs no grant.
---

# Cost/latency profile

Measure per-eval cost and latency and identify a mock/cheap mode - ask the user; useful when eval cost is suppressing how often evals run.
