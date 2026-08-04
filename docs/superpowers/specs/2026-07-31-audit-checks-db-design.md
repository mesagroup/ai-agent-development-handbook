# The audit family on a checks database (lidia-tech/lidia-agents#559)

**Status:** draft 2026-07-31. Restructures wave 1 of [#1](https://github.com/lidia-tech/lidia-agents/issues/542), delivering [#7](https://github.com/lidia-tech/lidia-agents/issues/544), [#5](https://github.com/lidia-tech/lidia-agents/issues/519) and [#8](https://github.com/lidia-tech/lidia-agents/issues/545) by a different mechanism than the eight-file sweep those issues describe.

## Problem

Wave 1 was scoped as one pass per skill across eight `SKILL.md` files, binding each skill's dimensions to handbook citations, removing repo parochialisms, and adding TypeScript evidence patterns. Sizing the work first showed the shape is wrong.

Every one of those three issues *adds* content to a file that eight parallel subagents each read in full, and the family is already far past any sane budget:

| | words |
|---|---|
| `arch-audit/SKILL.md` | 3,335 |
| `prompt-audit/SKILL.md` | 2,877 |
| `eval-audit/SKILL.md` | 1,786 |
| `audit-core/SKILL.md` (every agent reads it too) | 1,484 |
| `superpowers:writing-skills` target for an ordinary skill | **under 500** |

An `/audit all` sweep dispatches one subagent per domain, each reading its own `SKILL.md` plus `audit-core`, so the floor today is roughly 2,300 to 4,800 words per agent before any evidence is gathered. #5 is the worst offender: per-domain TypeScript tooling matrices alongside the Python ones means every Python audit pays for TS prose it will never use, and every TS audit pays for the Python half.

## The structural finding

All eight domain skills carry the **identical** seven-slot skeleton, because `audit-core` mandates it. The *how* is therefore already centralised; only the fill varies. Sorting the slots by what they actually vary with:

| Slot | Varies with |
|---|---|
| §2 Dimensions | the check |
| §3 Evidence sources and tooling | the check x the language |
| §4 Severity rubric | the check |
| §5 Fix patterns | the check |
| §6 Review lenses | the check |
| §1 Subject, scope, fan-out axis | the **domain** |
| §7 Opt-in sub-audits | the **domain** |
| `description` / When to use | the **domain** (discovery) |

Five of eight slots are per-check attributes wearing a domain costume. `arch-audit` §5's "invert or cut an illegal edge" is not architecture knowledge; it is the fix pattern belonging to the layering check. Its Critical rubric line and its "layering correctness" review lens belong to the same check. They sit in four different sections of one file only because markdown has no way to express a record.

Measured on `arch-audit`, 2,379 of its 3,335 words (71%) are per-check attributes.

The consequence is that the same five attributes are re-authored eight times, in eight files, with no mechanism keeping them consistent, and a change to how the family expresses (say) a severity rubric requires eight edits.

## The unlock

`docs/audit/handbook-traceability.yaml` already stores `checks: [{skill, dimension}]` on 41 of its 125 rows: **80 foreign keys into a checks table that does not exist**. [lidia-tech/lidia-agents#543](https://github.com/lidia-tech/lidia-agents/issues/543)'s validator resolves that key by parsing bolded lead phrases out of `## N. Dimensions` markdown bullets.

Making the table real turns a markdown-parse heuristic into genuine referential integrity, and collapses the three wave-1 issues from prose sweeps into schema fields:

- **#7** becomes a frontmatter field. The matrix row and the check record become two views of one edge, so they cannot disagree.

  This fixes the `checks[]` half of #7 and **not** the prose half. That issue's review comment raised two things: 80 unresolvable foreign keys in the structured `checks[]` field, and roughly 60 `note:` / `gap.note:` fields naming skills and dimensions in free prose that no validator reads. A checks database closes the first completely and leaves the second exactly where it was. The renaming of `Coupling & cohesion` in this very migration made the point: two `note:` fields had to be hand-corrected because the dimension they named no longer existed, and nothing would have caught either one. The prose half still needs the decision that comment asked for - make the references checkable, or forbid naming a dimension outside `checks[]` - and #7 stays open for it.
- **#5** becomes a tooling key. Agents load only the detected language's slice.
- **#8** becomes one place to de-parochialise plus a grounding input, rather than eight prose files to hunt through.

## Decisions

### 1. One markdown file per check, inside the domain's own skill

A per-domain file would reintroduce the problem one level down. A single `checks/arch.yaml` would hold 2,379 words of Python-only content, about 3,100 once TypeScript is added, plus the 250-word domain header: exactly today's 3,335. The restructure would buy nothing.

The saving exists only if an agent loads a **subset**, and `audit-core` already fans out sub-domain: one agent per package for local dimensions, one agent per global dimension over the whole graph. So file granularity must match dispatch granularity.

```
.agents/skills/arch-audit/checks/
  layering.md              local
  complexity.md            local
  dead-code.md             local
  size.md                  local
  cycles.md                global
  coupling.md              global
  over-decomposition.md    global
  hidden-coupling.md       global
  martin-metrics.md        global   optin
  ...                                        see decision 4 for the full inventory
```

| agent | reads today | reads after |
|---|---|---|
| per-package local agent | 3,335 | domain header + 4 local checks, about 1,450 |
| per-global-dimension agent | 3,335 | domain header + 1 check, about 550 |

Per-check files also make the bulk migration parallelisable: seven domains migrating at once never touch the same file, so subagent implementers cannot collide.

**The records live in the domain's own skill, not in a shared tree under `audit-core`.** The engine owns the record *schema*; each skill owns its *instances*. Three reasons, in increasing weight. A domain becomes one directory to add or remove. A domain becomes portable, which matters because #1's premise is running this family against other repositories - a repo adopting three of the eight copies three skill directories plus the engine, rather than cherry-picking subdirectories out of a shared tree. And a shared tree would end up holding ~68 records for eight skills that own them, a hub directory everything reaches into and nothing owns, which is precisely what `arch/coupling` exists to flag: the family would fail its own audit.

Anthropic's skill-authoring guidance backs the shape twice over. Its **Pattern 2, "Domain-specific organization"** is this design under another name - "organize content by domain to avoid loading irrelevant context... This keeps token usage low and context focused" - with `SKILL.md` as overview-and-navigation over per-domain files loaded selectively. And its **"avoid deeply nested references"** anti-pattern warns that agents "may partially read files when they're referenced from other referenced files", previewing with `head -100` rather than reading in full. A header pointing into a sibling skill's subdirectory is exactly that nesting; a header pointing at `checks/` beside it is one hop.

### 2. Markdown with YAML frontmatter, not pure YAML

The machine-checkable fields go in frontmatter; the judgment prose stays prose in the body. This matches how every skill in the repo is already written, and avoids turning 300-word paragraphs into YAML block scalars that are awkward to write and to diff.

```markdown
---
id: arch/layering
domain: arch
locality: local
handbook:
  - codebase-structure/point-every-dependency-toward-the-core-and-never-cycle-a
tooling:
  python: [import-linter, tach]
  typescript: [dependency-cruiser, madge]
---

# Layering / dependency-rule conformance

Every import that crosses a tier boundary the wrong way (a lower tier importing a higher one), or an edge the documented rules forbid. This is the highest-value axis when the project documents its layers.

## Severity

**Critical** - an import that violates a documented dependency rule.

## Tooling fallback

**Python** - build the edge set yourself: parse each module's import statements (`grimp`, an `ast` walk, or a scoped grep) and check every cross-tier edge against the declared rules. Record the offending `file:line`.

**TypeScript** - read `tsconfig` path aliases and project references as the declared boundaries; walk import specifiers and check each cross-boundary edge.

## Fix

Invert or cut the illegal edge: move the shared type down to a lower tier both sides may import, introduce an interface the lower tier defines and the higher tier implements, or relocate the misplaced module. Re-run the layering check to green.

## Review lens

Is each flagged edge genuinely a violation of the documented rules, and does each fix remove the edge rather than hide it (a lazy import that still couples the tiers)?
```

**Frontmatter fields.** `id` (stable, `<domain>/<slug>`), `domain`, `locality` (`local` | `global`), `handbook`, `handbook_note`, `tooling` (a map of language to preferred tools, plus `any` for language-agnostic tooling), `optin` (boolean, default false).

`handbook` is required and is a **list** of matrix row ids, possibly empty. A list rather than a scalar because a check is commonly grounded in several clauses - `arch/layering` in six, `arch/over-abstraction` in two - and a single field would force an arbitrary primary and under-report the grounding an agent reading only the record needs. When the list is empty, `handbook_note` is required and states why the check deliberately exceeds the handbook. This is #7's fourth acceptance criterion expressed as a schema rule: 9 of the 50 current dimensions are cited by no matrix row, and that is correct rather than a gap, since skills may check more than the handbook states.

The list need not be exhaustive - the matrix is the authoritative edge set - but three rules make what it says true. Every anchor must resolve to a real handbook heading; every anchor must be a row that actually cites the check; and a check some row cites may not declare itself ungrounded, nor may a check nothing cites claim a grounding. The validator rejects an empty list without a note, and a note alongside anchors.

**Body sections.** The claim as the lead prose, then `## Severity`, `## Tooling fallback`, `## Fix`, `## Review lens`. A check omits a section it has nothing to say in.

### 3. Stable ids, not `{skill, dimension}` pairs

The matrix migrates from `checks: [{skill: arch-audit, dimension: "Layering / dependency-rule conformance"}]` to `checks: [arch/layering]`: 80 references, scripted. `skill_dimensions()` is replaced by a frontmatter index, and the renderer resolves the id to its display name from the check file.

The compound natural key works today, but it is prose text: renaming a dimension churns matrix rows. A stable id decouples the two, and [#9](https://github.com/lidia-tech/lidia-agents/issues/546)'s issue emitter needs stable ids to emit from anyway.

### 4. A check produces findings-matrix rows; a deliverable does not

This rule is what keeps the file count honest. Of the 24 opt-in bullets across the family, roughly half are checks (`docs-audit`'s docstring Coverage / Staleness / Standard, `arch-audit`'s Martin package metrics, `deps-audit`'s transitive-license deep dive) and become files with `optin: true`. The rest are **deliverables**: SBOM generation, the `import-linter` contract bootstrap, a full metric report with a rendered graph. They produce an artifact, not findings, so they stay as lines in the domain header.

Without the rule the migration turns every bullet it meets into a file, landing near 90 records, a directory full of things that can never appear in a findings matrix.

Expected inventory, about 68 checks:

| source | count |
|---|---|
| `## N. Dimensions` bullets | 50 |
| `prompt-audit` Tier B (currently a semicolon list under one heading) | 3 |
| opt-in sub-audits that produce findings | about 12 |
| `docs-audit`'s trailing domain rule, `audit-core` cross-cutting checks | about 3 |

Per domain that is roughly: arch 11, prompt 11, ci 8, eval 8, security 7, test 7, docs 7, deps 6.

### 5. Prose moves verbatim

The migration constraint, stated as a rule rather than an intention: **no summarising a judgment paragraph into a bullet**.

`arch-audit`'s over-abstraction dimension is 300 words of judgment ending "a finding needs a read confirming (a) no second consumer or second value is imminent in-tree and (b) collapsing the construct removes indirection without losing a genuine seam." That nuance is the product. A record can hold a prose field of any length, so nothing forces the loss, but restructuring tempts terseness.

The gate: PR review diffs per-check word counts against the source sections and flags any shrinkage for justification.

### 6. Domains keep a thin skill; dispatch stays per-domain

Each domain retains a `SKILL.md` of roughly 250 words holding what did not dissolve:

```markdown
---
name: arch-audit
description: "Use when a codebase has grown organically and boundaries have blurred, before a refactor, when import cycles or god-modules are suspected..."
---

Scope: the package tree and its import graph. Establish the declared architecture first - it is the spec every layering finding is judged against. Read the contributor guide for stated tiers; if absent, infer and confirm with the user before flagging.

Ground truth: build the import edge set plus per-module symbol/LOC counts ONCE; every agent consumes it rather than re-parsing.

Status scale: ok / warn / violation.

Opt-in deliverables: layering-contract bootstrap; full metric report with a rendered graph.

Load audit-core, then the checks in checks/ beside this file (locality drives the sub-fan).
```

The domain remains the dispatch and reporting unit, exactly as today, so the consolidated report shape is unchanged. `locality` drives the sub-fan *within* a domain, which makes `audit-core`'s existing fan-out rule mechanical instead of a paragraph each domain restates.

Keeping the per-domain file is a deliberate departure from full collapse into a single `audit` skill. The residue is real (scope, ground-truth artifact, opt-in deliverables differ sharply between `arch` and `deps`), and eight targeted `description` fields buy discovery that one description covering licenses, CVEs, layering, coverage, GDPR, prompts and CI could not. The header costs nothing at execution time: the executing agent reads `audit-core` plus its checks.

## What this also fixes

- **Un-citable coverage.** `prompt-audit`'s Tier B, `docs-audit` §7 and `audit-core`'s own cross-cutting rules are real coverage that no matrix row can reference today, because the validator only sees what a heading parser sees. A database has no such limit. Surfacing these is a migration deliverable, not scope creep.
- **Run-on severity rubrics.** `arch-audit`'s Critical entry is one sentence covering layering, cycles, hidden coupling and over-abstraction, with an exception clause tacked on for the last. Split per check, the exception attaches to the check it qualifies. This is the fiddliest hour of the migration and the highest-value part.
- **Stable ids for #9.** An emitted issue can reference the check that produced it.

## Sequencing

**PR 1 - schema and pilot.** Define the frontmatter schema, write the validator and the loader, migrate `arch` end to end (11 checks), rewire its 7 matrix references, and reduce `arch-audit/SKILL.md` to its header. Verify by running `/arch-audit` on this repo and diffing the findings against the [lidia-tech/lidia-agents#508](https://github.com/lidia-tech/lidia-agents/issues/508) baseline.

`arch` is the right pilot: the most checks, the densest prose, and both localities. A schema that survives `arch` survives the rest.

**PR 2 - the remaining seven domains.** Parallelisable, since per-check files do not collide. Rewires the other 73 matrix references.

**PR 3 - retire the old path.** Remove `skill_dimensions()` and the markdown-bullet validation.

## Testing

`superpowers:writing-skills` states an Iron Law: no skill edit without a failing test first. Eight rewrites have no test budget, and these are reference and technique skills rather than discipline skills, so the appropriate test form is retrieval and application rather than pressure scenarios.

The pilot is the answer. Running `/arch-audit` against the lidia-tech/lidia-agents#508 baseline before the other seven domains move is a real application test at one eighth the cost of discovering the schema is wrong after 68 records. #8's criterion 3 (a Mesa PoC run in report-only mode) and [#10](https://github.com/lidia-tech/lidia-agents/issues/547)'s dry run remain the end-to-end gates.

New code (validator, loader, id rewiring) ships with unit tests. `scripts/` is not exempt: follow the `importlib.util.spec_from_file_location` pattern in `tests/reference_extraction/test_sweep.py`, with `scripts/` on `sys.path` via a package `conftest.py`.

## Rejected

**Full collapse into a single `audit` skill.** Tempting, and it matches the project's no-backward-compatibility-wrappers rule, but it discards eight targeted discovery descriptions and leaves the per-domain scope and fan-out residue with nowhere natural to live. The thin header is not a compatibility wrapper; it is the 20% that genuinely did not dissolve.

**Progressive disclosure without a database.** Keeping eight skills and moving language tooling into `references/` would shrink the files, but leaves severity rubrics, fix patterns and review lenses duplicated across eight files in four sections each, and leaves the matrix parsing markdown bullets. It solves the token problem and none of the structural one.

**Runtime lookup of the matrix for citations.** Considered and rejected on measurement: `handbook-traceability.yaml` is 13,094 words, ten times a skill. Having each agent read it to resolve a citation is the most expensive option available.

**Per-domain check files.** Rejected on measurement, see decision 1.

## Files

| File | Change |
|---|---|
| `.agents/skills/<domain>-audit/checks/<check>.md` | New, about 68 files |
| `.agents/skills/audit-core/SKILL.md` | "Authoring a new auditing skill" rewritten from seven slots to the check record plus domain header |
| `.agents/skills/<domain>-audit/SKILL.md` | Reduced to the domain header (8 files) |
| `.agents/skills/audit/SKILL.md` | Detect domains from the checks tree rather than skill directories |
| `scripts/render_handbook_traceability.py` | `skill_dimensions()` replaced by a frontmatter check index; renderer resolves id to display name |
| `docs/audit/handbook-traceability.yaml` | 80 `checks[]` references rewired to stable ids |
| `docs/audit/handbook-traceability.md` | Regenerated |
| `tests/scripts/test_render_handbook_traceability.py` | Coverage for the check index and id resolution |
| New validator plus its tests | Frontmatter shape, id uniqueness, `locality` enum, `handbook` anchors resolve |

Gates: the new check validator, `render_handbook_traceability.py --check`, the renderer's pytest module, `mkdocs build --strict`, `check_site_links.py`.
