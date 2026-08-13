# Audits

The standing records of what the `*-audit` skill family covers - the handbook↔skills coverage matrix, the `audit-core`↔sweep obligations ledger, and the expected result of every seeded fixture check - alongside the dated records of what happened when the family's tooling entries were actually executed.

## Standing records

| Doc | Description |
|-----|-------------|
| [Handbook traceability matrix](handbook-traceability.md) | Every `##` section of the engineering handbook mapped onto the `*-audit` skill family: a class and a severity per clause, the checks it maps to, and the gap list ordered by severity. The severity × coverage cross-tab answers which high-risk clauses nothing currently checks. Generated from [`handbook-traceability.yaml`](handbook-traceability.yaml) by `scripts/render_handbook_traceability.py` — edit the YAML, never the Markdown |
| [Python fixture expectations](python-fixture-expectations.md) | What every `python:` tooling entry must observe when it runs against the seeded fixture partitions, written down before the run, under both grant states. A fixture whose expected output is not recorded in advance is just a smaller real target: the value of a seeded tree is that a tool which runs cleanly and reports half the truth fails instead of passing. Generated from `scripts/python_fixture_spec.py` by `scripts/render_python_fixture_expectations.py` — edit the module, never the Markdown |
| [Sweep obligations ledger](sweep-obligations.md) | Every obligation `audit-core` states, and how the `audit` sweep discharges it: restated, adapted, delegated to the domain skill, or never reached. The sweep substitutes its own steps for the `audit-core` loop, so it inherits nothing implicitly — and a dropped obligation leaves no trace in the file that dropped it, which is what this record exists to make visible. `tests/test_sweep_obligations.py` checks what is mechanical — each anchor occurring exactly once in `audit-core/SKILL.md`, a disposition from the vocabulary the ledger itself defines, a non-empty justification, and that no row escapes the checked set — but not whether a disposition is true, which is a reading pass |

## Verification records

| Doc | Description |
|-----|-------------|
| [TypeScript lens smoke run](typescript-lens-smoke-run.md) | What happened when every `typescript:` and `any:` tooling entry in `arch`, `deps`, `test` and `security` was executed against a real TypeScript repository, under both grant states: the result per entry, the defects the run exposed in tools that ran and produced nothing usable, and the records it corrected. Unlike the standing records above this one does not track the current tree - it is a dated finding about tool behaviour, and a tool that changes version can invalidate it without anything here failing |

Its subject is the skills, not the audited codebase. Point-in-time audit reports of a specific codebase are that codebase's to keep, not this repository's. The `*-audit` family never writes one into the tree it audited: it writes to a path the caller supplies outside that tree and hands the report over, so the rule holds even when the codebase under audit is this one. This repo holds the handbook, the skills that audit against it, and the record of what they cover.
