# Audits

The standing handbook↔skills coverage record.

## Standing records

| Doc | Description |
|-----|-------------|
| [Handbook traceability matrix](handbook-traceability.md) | Every `##` section of the engineering handbook mapped onto the `*-audit` skill family: a class and a severity per clause, the checks it maps to, and the gap list ordered by severity. The severity × coverage cross-tab answers which high-risk clauses nothing currently checks. Generated from [`handbook-traceability.yaml`](handbook-traceability.yaml) by `scripts/render_handbook_traceability.py` — edit the YAML, never the Markdown |

Point-in-time audit reports of a specific codebase are that codebase's to keep, not this repository's. The `*-audit` family never writes one into the tree it audited: it writes to a path the caller supplies outside that tree and hands the report over, so the rule holds even when the codebase under audit is this one. This repo holds the handbook, the skills that audit against it, and the record of what they cover.
