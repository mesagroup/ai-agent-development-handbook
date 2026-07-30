# Audits

Audit artifacts: the standing handbook↔skills coverage record, plus point-in-time audits of the `docs/` tree (coverage, staleness, and structural findings).

## Standing records

| Doc | Description |
|-----|-------------|
| [Handbook traceability matrix](handbook-traceability.md) | Every `##` section of the engineering handbook mapped onto the `*-audit` skill family: a class and a severity per clause, the checks it maps to, and the gap list ordered by severity. The severity × coverage cross-tab answers which high-risk clauses nothing currently checks. Generated from [`handbook-traceability.yaml`](handbook-traceability.yaml) by `scripts/render_handbook_traceability.py` — edit the YAML, never the Markdown |

## Point-in-time audits

| Doc | Description |
|-----|-------------|
| [Docs audit — 2026-07-20](2026-07-20-docs-audit.md) | Full documentation audit: coverage gaps, stale entries, structural findings |
