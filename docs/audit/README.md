# Audits

The standing records of what the `*-audit` skill family covers: the handbook↔skills coverage matrix, and the `audit-core`↔sweep obligations ledger.

## Standing records

| Doc | Description |
|-----|-------------|
| [Handbook traceability matrix](handbook-traceability.md) | Every `##` section of the engineering handbook mapped onto the `*-audit` skill family: a class and a severity per clause, the checks it maps to, and the gap list ordered by severity. The severity × coverage cross-tab answers which high-risk clauses nothing currently checks. Generated from [`handbook-traceability.yaml`](handbook-traceability.yaml) by `scripts/render_handbook_traceability.py` — edit the YAML, never the Markdown |
| [Sweep obligations ledger](sweep-obligations.md) | Every obligation `audit-core` states, and how the `audit` sweep discharges it: restated, adapted, delegated to the domain skill, or never reached. The sweep substitutes its own steps for the `audit-core` loop, so it inherits nothing implicitly — and a dropped obligation leaves no trace in the file that dropped it, which is what this record exists to make visible. `tests/test_sweep_obligations.py` checks what is mechanical — each anchor occurring exactly once in `audit-core/SKILL.md`, a disposition from the vocabulary the ledger itself defines, a non-empty justification, and that no row escapes the checked set — but not whether a disposition is true, which is a reading pass |

Point-in-time audit reports of a specific codebase are that codebase's to keep, not this repository's. The `*-audit` family never writes one into the tree it audited: it writes to a path the caller supplies outside that tree and hands the report over, so the rule holds even when the codebase under audit is this one. This repo holds the handbook, the skills that audit against it, and the record of what they cover.
