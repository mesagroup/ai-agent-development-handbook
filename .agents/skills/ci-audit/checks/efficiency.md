---
id: ci/efficiency
domain: ci
locality: local
handbook: []
handbook_note: >-
  No clause anywhere in the handbook addresses pipeline performance. The
  only "cache" and "caching" hits in docs/engineering/ are in
  observability.md and troubleshooting.md, and both mean the LLM
  prompt-cache read/write tokens on a model call - a full-cost-accounting
  concern, not the CI dependency-cache this check looks for. Same word,
  unrelated subject, so it is not a near miss of an existing clause; the
  handbook simply never discusses workflow runtime, matrix sizing, or
  run-cancellation.
---

# Efficiency

Missing dependency caching, no concurrency cancellation for superseded runs, an over-broad matrix, redundant re-installs.

## Severity

**Minor** - missing caching / concurrency cancellation, an over-broad matrix.

## Tooling fallback

Needs reading - no tool in this domain's evidence pass targets pipeline efficiency; read each workflow's job/step definitions for a missing dependency-cache action, an absent `concurrency:` block, and a matrix whose dimensions do not earn their added runtime.

## Fix

Add dependency caching, `concurrency:` with `cancel-in-progress`, and trim the matrix.
