---
id: eval/coverage
domain: eval
locality: global
handbook:
  - three-layer-model/why-this-is-the-organizing-principle-not-just-a-document-feature
  - evaluation/measure-the-behaviors-that-matter-a
  - evaluation/evaluate-a-multi-agent-system-unit-by-unit
  - evaluation/name-the-anti-patterns-out-loud
routes:
  - lang: any
    kind: procedure
    note: >-
      **Coverage map (the load-bearing step):** list the behaviors-that-matter, then map each to the eval(s) that exercise it by reading the eval configs/datasets - not by trusting a summary. The unmapped behaviors are the gap rows. A capability with a leaderboard entry but no test case for its key failure mode is still a gap.
---

# Eval coverage

For each behavior-that-matters, is there an eval that exercises it? Uncovered capabilities, failure modes with no test case, dimensions asserted in docs but never measured.

## Severity

**Critical** - a product-critical behavior with **no** eval.

**Minor** - a nice-to-have dimension not yet measured.

## Fix

**Close a coverage gap:** add a dataset / test case exercising the behavior (especially the failure mode), with a metric that tracks the quality dimension, not a gameable proxy.

## Review lens

**Coverage honesty** - is each "now evaluated" claim backed by a dataset that exercises the real behavior/failure mode, not a trivial happy-path case?
