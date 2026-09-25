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
routes:
  - lang: any
    kind: procedure
    needs: target-execution
    note: >-
      Re-run a small eval slice if feasible and confirm the number reproduces. Running the slice executes the target's own eval code, so this route needs the `target-execution` grant; where it is withheld, the untiered reading route answers.
  - lang: any
    kind: procedure
    alone_insufficient: >-
      A clean reading shows that what a number depends on is fixed, not that the number regenerates; only the re-run shows that, so a row answered by this route alone says the re-run was not made.
    note: >-
      Read whether a reported number can be regenerated from what the repository fixes: frozen datasets or queries, pinned model versions, fixed seeds and temperature where feasible, and recorded config. Non-determinism that nothing acknowledges is the finding this reading reaches without running anything.
---

# Reproducibility

Frozen datasets/queries, pinned model versions, fixed seeds/temperature where feasible, recorded config; can a reported number be regenerated? Non-determinism that isn't acknowledged.

## Severity

**Important** - an unreproducible headline number.
