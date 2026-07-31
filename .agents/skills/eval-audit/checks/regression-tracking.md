---
id: eval/regression-tracking
domain: eval
locality: global
handbook:
  - implementation-disciplines/when-to-add-an-end-to-end-agent-quality-gate
  - agent-harness/offer-cheap-and-mock-backends-a-fast-inner-loop-is-a-discipline
  - evaluation/run-the-loop-b
  - documentation/keep-the-decision-trail-artifacts-a
---

# Regression tracking & cost

Are results tracked over time (leaderboard/history) so drift is visible; is there a cheap/mock eval mode so cost doesn't suppress running evals.

## Severity

**Minor** - a missing cheap/mock mode; a stale leaderboard entry.

## Tooling fallback

Needs reading - no tool in this domain's evidence pass reaches this: read the leaderboard/eval-history artifact for recency, and the eval runner/CLI for a cheap or mock execution mode.

## Fix

Track results over time (leaderboard/history) so behavioral drift is visible rather than discovered in production.
