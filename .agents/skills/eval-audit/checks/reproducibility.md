---
id: eval/reproducibility
domain: eval
locality: local
handbook:
  - implementation-disciplines/when-to-add-an-end-to-end-agent-quality-gate
  - evaluation/build-a-dataset-you-can-trust
  - evaluation/measure-honestly-c
  - evaluation/name-the-anti-patterns-out-loud
  - security-supply-chain/depend-only-on-what-you-can-account-for-b
---

# Reproducibility

Frozen datasets/queries, pinned model versions, fixed seeds/temperature where feasible, recorded config; can a reported number be regenerated? Non-determinism that isn't acknowledged.

## Severity

**Important** - an unreproducible headline number.

## Tooling fallback

Re-run a small eval slice if feasible and confirm the number reproduces.
