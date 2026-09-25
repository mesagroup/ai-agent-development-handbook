---
id: eval/methodology
domain: eval
locality: local
handbook:
  - observability/account-for-the-full-cost-not-the-convenient-part
  - evaluation/measure-the-behaviors-that-matter-b
  - evaluation/build-a-dataset-you-can-trust
  - evaluation/measure-honestly-c
  - evaluation/use-the-llm-judge-only-where-it-agrees-with-the-human
  - evaluation/name-the-anti-patterns-out-loud
routes:
  - lang: any
    kind: procedure
    note: >-
      **Methodology inspection:** read the metric/scorer/judge implementation and the ground-truth data. Check sample size, judge rubric stability, whether a judge was correlated against human evals, and whether errors/refusals are excluded from quality scores.
---

# Methodology soundness

Do metrics actually track quality (vs. a proxy that can be gamed)? Is the sample size adequate; are ground-truth labels correct; is an LLM-judge validated against human labels and run with a stable rubric; are refusals/API errors separated from genuine quality failures (so a sub-agent refusal doesn't penalize a model)?

## Severity

**Critical** - a metric or judge that does not track real quality (so the leaderboard is misleading).

**Important** - an under-powered eval (too few samples to distinguish models); an unvalidated LLM-judge used for decisions; refusals/errors polluting quality scores.

## Fix

**Fix the instrument:** correct a scorer's math or an id-mapping; validate the LLM-judge against human labels and stabilize its rubric; separate refusals/errors from quality; increase sample size to a power that distinguishes candidates.

## Review lens

**Metric validity** - does each metric/judge actually measure the quality dimension it claims, and does the fix improve the instrument rather than the number? (Highest-value catch: a change that raises the score without improving behavior.)
