# Handbook traceability matrix — design (#543)

**Issue:** [#543](https://github.com/lidia-tech/lidia-agents/issues/543), first sub-issue of the external-audit epic [#542](https://github.com/lidia-tech/lidia-agents/issues/542).

**Goal:** map every part of the engineering handbook (`docs/engineering/`) onto the `*-audit` skill family, clause by clause, so that "do the skills cover the handbook?" is answered by evidence rather than opinion. The matrix's gap list re-scopes the downstream issues (#516 observability domain, #518 data-protection domain, #519 TypeScript support, #544 citation binding).

## Context (measured, 2026-07-29)

- The handbook is ~24k words across 12 files with 89 `##` sections total.
- The stable referenceable unit on the skill side is the **dimension**: each domain skill declares its findings-matrix columns under a `## Dimensions` heading (e.g. `security-audit` → "Injection"). `audit-core` defines the shared matrix shape (item × dimension × status × severity).
- As of today the `*-audit` skills contain **zero references to the handbook** — they were built in #499 from generic quality domains, in parallel to the handbook. Nobody has mapped one onto the other before.

## Decisions

### Granularity: adaptive sections

One matrix row per handbook `##` section (~89 rows baseline). A section is split into sub-rows **only** when its claims fall into different auditability classes or map to different skills. Row IDs are `<part>/<section-anchor>` with a `-a`/`-b` suffix on splits, so rows double as link targets for #544 citations.

Rejected: strict section-level (mixed sections would get one muddy classification) and claim-level with synthetic IDs like `EVAL-03` (300–600 rows, expensive, and IDs drift whenever handbook prose is edited).

### Format: YAML source of truth, rendered Markdown

The YAML is hand-maintained; the Markdown is generated and never hand-edited. Machine-readability was chosen deliberately (over Markdown-only) to enable automation: the staleness guard below comes nearly free, and future consumers (#546 issue emitter, a programmatic citation check) can read the YAML directly.

### Classification: four classes

| Class | Meaning | Handling |
|---|---|---|
| `static` | Statically auditable from a repo snapshot (layering, pinned deps, secrets, SOP structure) | must map to a skill check or carry a gap entry |
| `artifact` | Auditable only via artifacts (eval runs, CI history, issue/PR trail) | skill check with absence-is-a-finding semantics; never `pass` on no evidence |
| `process` | Process/culture, not verifiable from the repo (spec-before-code, review discipline) | audit-report prose + adoption recommendation; never fake-automated |
| `informative` | Non-normative (README spine, coda, the troubleshooting symptom index) | row exists so every part is accounted for; maps to nothing |

## Artifacts

| File | Role |
|---|---|
| `docs/audit/handbook-traceability.yaml` | Source of truth, hand-maintained |
| `docs/audit/handbook-traceability.md` | Rendered output with a generated-file header; committed |
| `scripts/render_handbook_traceability.py` | Renders the md from the YAML and verifies coverage; non-zero exit on drift |
| `tests/scripts/test_render_handbook_traceability.py` | Unit tests for the pure helpers + the CI staleness gate |

## YAML schema

One entry per row:

```yaml
- id: evaluation/the-staged-screening-funnel  # <part>/<section-anchor>, + "-a"/"-b" on splits
  section: "The staged screening funnel"      # heading text, verbatim
  claim: one-line paraphrase of the normative claim(s) the row covers
  class: static | artifact | process | informative
  checks:                                     # required for static/artifact unless gap present
    - skill: eval-audit
      dimension: "dimension name exactly as in the skill's Dimensions section"
  gap:                                        # present when auditable but unmapped
    recommendation: extend-skill | new-domain | report-only
    target: "#516"                            # issue ref when known; omit if none yet
    note: one line
  note: optional free text
```

Validation rules enforced by the renderer:

- `class: static` or `artifact` requires `checks` non-empty **or** a `gap` entry — an auditable row may not be silently unmapped.
- `class: process` and `informative` must have no `checks` (a process row with a check is a misclassification).
- `checks[].skill` must name a skill directory that exists under `.agents/skills/`; `dimension` must match a dimension bullet in that skill's `## Dimensions` section (matched by the bolded lead phrase).
- `id` must be unique; its `<part>` must be a real handbook file; its anchor (minus split suffix) must resolve to a real `##` heading in that file.

## Renderer behavior

`uv run python scripts/render_handbook_traceability.py` (no args) reads the YAML, verifies, and writes the md. `--check` verifies without writing and additionally fails if the committed md differs from a fresh render. Failure modes, each with its own message: handbook section with no row (coverage hole), row anchor with no heading (stale row), schema violation (rules above), md out of date.

The pytest test runs the `--check` path, so CI guards staleness with no workflow change. Pure helpers (YAML row validation, anchor slugging, heading extraction from the handbook files, dimension lookup in skills, table rendering) are unit-tested via the `importlib.util.spec_from_file_location` pattern used by the other `scripts/` tests.

Slugging matches the handbook's own heading-anchor convention (GitHub-style: lowercase, punctuation stripped, spaces to hyphens) so row IDs and md heading links agree.

## Rendered md layout

1. Generated-file header (edit the YAML, run the renderer) + legend explaining the four classes, including the absence-is-a-finding semantics of `artifact`.
2. One table per handbook part, in the handbook's own reading order: columns *Section / claim / Class / Mapped checks / Gap / Notes*. The first cell carries the linked heading, the split marker (`(a)`, `(b)`, …) and the row's `claim`, so a split row says what it covers without opening the YAML; the last carries the row's `note`, the rationale for its class and for what a mapping deliberately leaves to the gap.
3. **Gap list** — the consolidated section that re-scopes downstream work: all `gap` entries grouped by `recommendation` (`extend-skill` / `new-domain` / `report-only`), each with its row ID (linked to the handbook section) and target issue.
4. **Coverage summary** — row counts per class, then the auditable rows split three ways: fully mapped (checks, no gap), partially mapped (checks *and* a residual gap), and unmapped. Counting a partial row as mapped would overstate coverage, so the headline percentage is the fully-mapped one. Closes with the non-auditable `process` + `informative` counts — the honest record of what cannot be audited from a snapshot.

Handbook links are absolute GitHub URLs (`https://github.com/lidia-tech/lidia-agents/blob/main/docs/engineering/…`), not repo-relative ones: `mkdocs.yml` excludes `docs/engineering/` from the built site, so a relative link resolves on GitHub but 404s on the site. `mkdocs build --strict` logs that at INFO rather than failing, so the guard is `scripts/check_site_links.py`, which CI runs separately.

## Content rules for the walk

- Every `##` section of every part gets at least one row; parts with no `##` sections (coda) get one whole-file row.
- README, coda, and troubleshooting default to `informative` unless a section carries a normative claim in its own right.
- The `claim` field paraphrases; it never quotes long handbook passages (the ID is the pointer, the handbook stays the source of truth).
- If the walk surfaces a handbook clause that seems wrong or outdated, file a separate issue; the matrix records the handbook as it is.

## Out of scope

- Binding citations into the skills' lens text (#544).
- Building new audit domains (#516, #518) or language support (#519).
- Any edit to `docs/engineering/` prose.
- Automation beyond the renderer + check (no CI workflow changes; pytest already runs in CI).

## Acceptance criteria (from #543)

- Every part of `docs/engineering/` covered clause by clause with a classification — enforced mechanically by the renderer's coverage check.
- Each auditable clause mapped to a concrete existing check or flagged as a gap — enforced by the schema validation rule.
- Gap list produced with a recommendation per gap — the rendered Gap list section.
- The matrix confirms or corrects the scope of #516, #518, #519, #544 — read out of the Gap list at review time.
- Matrix committed under `docs/audit/` and linked from the `audit` front-door skill — one pointer line added to `.agents/skills/audit/SKILL.md`.
