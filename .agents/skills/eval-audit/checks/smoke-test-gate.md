---
id: eval/smoke-test-gate
domain: eval
locality: global
handbook:
  - lifecycle/make-the-standard-executable-and-audit-periodically-a
  - implementation-disciplines/when-to-add-an-end-to-end-agent-quality-gate
  - evaluation/grow-the-eval-into-a-gate
---

# Smoke-test gate

Is there a cheap behavioral pre-merge check, does it run on the paths that can regress behavior, and does it actually fail on a real regression (vs. a threshold set so low nothing trips it)?

## Severity

**Critical** - a smoke-test gate whose threshold cannot fail on a genuine regression.

## Tooling fallback

**Smoke-test inspection:** read the smoke-test workflow and its pass threshold; confirm it runs on the right triggers/paths and that its threshold would actually catch a real regression (cross-check with `ci/gate-enforcement` for the gate-enforcement mechanics).

## Fix

**Smoke-test fixes:** set a threshold that trips on a real regression, run it on the paths that can change behavior (coordinate with `ci/gate-enforcement` on making it a required gate).
