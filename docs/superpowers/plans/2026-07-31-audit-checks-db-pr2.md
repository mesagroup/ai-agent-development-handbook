# Audit checks database, PR 2: the remaining seven domains and the front door

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `deps`, `docs`, `security`, `test`, `ci`, `eval` and `prompt` onto check records, rewire the last 65 legacy `{skill, dimension}` matrix references onto stable check ids, split `arch/complexity`'s repo-global fact into its own global check, and switch the `/audit` front door to detecting domains from the checks tree.

**Architecture:** Unchanged from PR 1. A check record is a Markdown file with YAML frontmatter under `.agents/skills/<domain>-audit/checks/<slug>.md`; `scripts/audit_checks.py` loads and validates records in isolation; `scripts/render_handbook_traceability.py` validates the matrix and the records against each other. This PR authors records and shrinks headers - it adds no schema fields and changes no loader behaviour. The dual `checks[]` path (bare string = id, mapping = legacy pair) stays until PR 3, so a domain can be rolled back independently.

**Tech Stack:** Markdown with YAML frontmatter, Python 3.11+, `pyyaml`, `pytest`, `ruff`, `pyright`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-07-31-audit-checks-db-design.md`. Predecessor plan: `docs/superpowers/plans/2026-07-31-audit-checks-db-pr1.md` (merged as PR #560). Issue: [#559](https://github.com/lidia-tech/lidia-agents/issues/559).

## Two decisions taken before this plan

Both were flagged as open in PR #560's body and answered by the user on 2026-07-31.

1. **`arch/complexity`'s repo-global fact splits into its own `global` check** (Task 1). The record currently mitigates with the prose instruction "Report this once for the repo, not once per package" - an instruction that asks N independent per-package agents to coordinate, which they cannot. `audit-core` gains the general rule, so the seven domains migrating in this PR apply it rather than re-inventing the mitigation. This makes `arch` eleven records, matching the spec's original estimate.
2. **Removing `skill_dimensions()` stays PR 3.** After Task 9 nothing cites the legacy form, but the code path stays, so this PR ends at a checkpoint where both reference forms still resolve. Do **not** add a validator rule forbidding the legacy mapping - that would hard-enforce the id-only world a PR early and remove the rollback the sequencing exists for.

## Sizing measured before planning

| domain | `SKILL.md` words | `## 2` dimensions | opt-in records | records | matrix refs |
|---|---|---|---|---|---|
| `deps-audit` | 850 | 5 | 2 | 6 | 4 |
| `docs-audit` | 1,175 | 3 | 3 | 6 | 8 |
| `security-audit` | 1,462 | 6 | 1 | 7 | 6 |
| `test-audit` | 1,532 | 6 | 2 | 7 | 6 |
| `ci-audit` | 1,566 | 7 | 2 | 9 | 10 |
| `eval-audit` | 1,786 | 7 | 3 | 10 | 25 |
| `prompt-audit` | 2,877 | 8 + 3 (Tier B) | 1 | 12 | 6 |
| **total** | **11,248** | | | **57** | **65** |

With `arch`'s eleven that is **68 records**, the number the spec estimated. The 65 references resolve to **34 distinct `{skill, dimension}` pairs**; every pair must land on exactly one check id.

## Global Constraints

Copied verbatim into every task's dispatch.

- **Work in `<worktree-root>`**, the absolute path of the worktree this plan is executed from. The dispatcher resolves it once with `git rev-parse --show-toplevel` and interpolates it into every task dispatch; each agent confirms its own `--show-toplevel` matches before reading or editing anything. Do not `cd` to the primary checkout.
- **Never pass a line starting with `#` to the Bash tool.**
- **Never `git add -A`, `git add .`, or `git commit -a`.** Run `git status --short`, then `git add` the exact paths you changed.
- **Prose moves verbatim.** When migrating text out of a `SKILL.md`, move the sentences unchanged. Do not summarise a judgment paragraph into a bullet, do not shorten, do not "tighten". The only permitted edits are: (a) replacing an em-dash `—` with ` - `, (b) changing a leading bold label when the sentence acquires its own heading, and (c) splitting a sentence at a clause boundary when the source sentence covers several checks and each clause moves to a different file. Everything else is a defect. **The reviewer diffs per-check word counts against the source sections and treats shrinkage as a finding.**
- **A shared trailing qualifier duplicates only if it distributes.** When a source sentence covering several checks ends in a qualifier, copy that qualifier into every record it genuinely applies to - but an **anaphoric** tail ("the former", "in that last case", "this second kind") refers back to one enumerated item and must land in that record only. Duplicating an anaphoric tail makes the other records claim something the source never said.
- **A record's `## Review lens` reviews that record's own `## Fix`.** When a source review bullet reviews a fix that now belongs to a different record, it moves to *that* record, not to the one whose dimension the bullet was filed under.
- **A `handbook_note` is an argument, not a formula.** It says why no clause grounds this check - a near miss the matrix's rule forbids, a quantitative restatement of a clause that states no threshold, a concern the handbook simply does not raise. Two records carrying the same sentence is a defect: if the reason really is identical, one of them is probably mis-scoped.
- **No em-dash (`—`) in any file this PR writes.** Use ` - `. The single exception is each domain's existing `description:` string, which is moved verbatim because it is the skill-discovery surface.
- **Markdown: one paragraph per source line.** Never hard-wrap prose, and never reflow a neighbouring line you did not otherwise change.
- **No environment-specific values** in committed files: no absolute personal paths, AWS/browser profile names, hostnames, emails, bucket names. Use placeholders and say in prose what they resolve to.
- **Docstrings are Google style** (`Args:` / `Returns:` / `Raises:`), no reStructuredText roles or directives, types from the annotations only.
- **Every commit runs `uv run ruff check .` and `uv run ruff format --check .` clean** before it is made. Run `uv run pyright` for any task touching `scripts/` or `tests/`.
- **The domain gate for every task is:** `uv run pytest tests/scripts/ -q` green **and** `uv run python scripts/render_handbook_traceability.py --check` exit 0.
- **Re-render the Markdown view** with `uv run python scripts/render_handbook_traceability.py` in any task that edits `docs/audit/handbook-traceability.yaml`, and commit both files together.
- **Reference the issue in every commit message:** `Refs #559`. No Claude credits, no co-author trailers naming an assistant.
- **Do not open a PR and do not merge.** The controller handles both.

## The record schema (unchanged from PR 1)

Frontmatter fields, all validated by `scripts/audit_checks.py`:

| field | required | meaning |
|---|---|---|
| `id` | yes | `<domain>/<slug>`; must equal the path-derived id |
| `domain` | yes | must equal the skill directory's `<domain>` prefix |
| `locality` | yes | `local` (decidable from one partition) or `global` (needs the whole subject) |
| `handbook` | yes | list of matrix row ids grounding the check; may be `[]` |
| `handbook_note` | iff `handbook` is `[]` | why no clause grounds it |
| `tooling` | no | language key -> tool list; `any` for language-independent. Omit it when the check's detection is reading rather than running something - but then say so in `## Tooling fallback`, because a record with neither leaves the agent no procedure at all |
| `optin` | no (default `false`) | `true` if the check runs only when the user enables it |

Body: the claim as lead prose under a `# Title`, then `## Severity`, `## Tooling fallback`, `## Fix`, `## Review lens` - **omitting any section the check has nothing to say in**. Read `.agents/skills/arch-audit/checks/over-decomposition.md` and `.agents/skills/arch-audit/checks/martin-metrics.md` as the reference records before authoring.

**The bidirectional rule is the one that fails the gate.** A check cited by a matrix row must list that row's id in `handbook`; a check no row cites must have `handbook: []` plus a `handbook_note`. The renderer checks both directions, so getting one wrong is caught, not silently absorbed.

## What stays in a domain header

Only what does not vary by check: the verbatim `description:`, the announce line, the subject and how to slice it, the ground-truth artifact to build once (if the domain has one), the status scale, cross-domain handoffs, and opt-in **deliverables**. `audit-core` records 520 words of body as the family ceiling, set by `arch` as the densest domain - every header in this PR should land well under it.

**A check produces findings-matrix rows; a deliverable does not.** An opt-in that emits rows becomes a record with `optin: true`; an opt-in that produces an artifact (an SBOM, a decomposition diagram, a recommendation) stays as a line in the header. A pure handoff to another domain ("hand this off to `security-audit`") is neither - it stays in the header.

---

### Task 1: Split `arch/complexity`'s repo-global fact, and state the rule

**Files:**
- Modify: `.agents/skills/arch-audit/checks/complexity.md`
- Create: `.agents/skills/arch-audit/checks/complexity-gate.md`
- Modify: `.agents/skills/audit-core/SKILL.md`

**Interfaces:**
- Produces, for Tasks 2-8: the locality rule those tasks apply when a check they are authoring carries a repo-global fact.

`arch/complexity` currently carries two unrelated judgments. The per-function one is genuinely `local`. The other - "the threshold is unconfigured, so complexity is ungated" - is a single repo-level fact, mitigated by the sentence "Report this once for the repo, not once per package." That sentence asks N per-package agents, which never see each other, to agree on which of them reports it.

- [ ] **Step 1: Create `arch/complexity-gate`**

`locality: global`, `optin: false`, `domain: arch`. Move into it, verbatim: the second `## Severity` paragraph (`**Important** - the threshold is unconfigured…`), minus the trailing "Report this once for the repo, not once per package." sentence, which the `global` locality now makes true structurally rather than by instruction. Move the `## Tooling fallback` paragraph that begins **"Read the project's configured threshold before measuring…"**, which is the detection procedure for exactly this fact. Give it a `## Fix` (configure the threshold and wire it into CI) and a `## Review lens` reviewing that fix.

Its `handbook` is `[]` - no matrix row cites a complexity-gate dimension - with a `handbook_note` arguing why. The handbook's structural-decay clause states the decay, not that a threshold must be configured and enforced; the enforcement half is `ci-audit`'s territory and the matrix routes gate-enforcement rows there. Do not paste that reasoning as given: verify it against `docs/engineering/` and the matrix, then write the argument you can support.

- [ ] **Step 2: Reduce `arch/complexity` to the local check**

Remove the two moved passages. `handbook` stays as it is - the row citing `arch/complexity` cites the per-function complexity claim, which stays here. Verify that after the edit the remaining lead prose still describes the whole record.

- [ ] **Step 3: Add the rule to `audit-core/SKILL.md`**

In the "Checks are records, not prose" section, one sentence after the `locality` explanation: a check that is decidable per-partition **except** for one repo-global fact splits into a `local` check and a `global` one, because "report this once" is not something N parallel agents can honour. Keep it to one sentence - this section is already the longest in the file.

- [ ] **Step 4: Gate and commit**

```bash
uv run python scripts/render_handbook_traceability.py --check
uv run pytest tests/scripts/ -q
git status --short
git add .agents/skills/arch-audit/checks/complexity.md .agents/skills/arch-audit/checks/complexity-gate.md .agents/skills/audit-core/SKILL.md
git commit -m "refactor(#559): split arch/complexity's repo-global fact into its own check

A local check cannot honour 'report this once for the repo' - the N
per-package agents that run it never see each other. Splitting the
threshold-configured fact into a global check makes the once-ness
structural. Refs #559"
```

---

### Task 2: Migrate `deps-audit`

**Files:**
- Create: `.agents/skills/deps-audit/checks/{licenses,vulnerabilities,freshness,hygiene,inventory,transitive-licenses}.md`
- Modify: `.agents/skills/deps-audit/SKILL.md`
- Modify: `docs/audit/handbook-traceability.yaml`, `docs/audit/handbook-traceability.md`

**Interfaces:**
- Consumes: the locality rule from Task 1.
- Produces: the worked example Tasks 3-8 follow. It is first because it is the smallest domain (850 words, 4 references), so the recipe is proved off `arch` before it is applied to a 2,877-word one.

**Check ids** - every `## 2` dimension plus the opt-ins that emit rows:

| source | id | locality | optin |
|---|---|---|---|
| License compatibility | `deps/licenses` | global | no |
| Known vulnerabilities | `deps/vulnerabilities` | global | no |
| Freshness | `deps/freshness` | global | no |
| Hygiene | `deps/hygiene` | global | no |
| Inventory (optional) - SBOM completeness | `deps/inventory` | global | **yes** |
| §7 Transitive-license deep dive | `deps/transitive-licenses` | global | **yes** |

Every `deps` check is `global`: the subject is one resolved dependency set, not a partitioned tree, so there is no per-partition slice to fan out to. Say so in the header's fan-out line rather than repeating it in six records.

**§7 SBOM generation is a deliverable** - it produces a CycloneDX file, not matrix rows. It stays as a line in the header. `deps/inventory` (is the SBOM complete?) is the check; they are not the same thing.

**Matrix references to rewire** - 4 references, 4 distinct pairs, one each:

| legacy pair | id |
|---|---|
| `{skill: deps-audit, dimension: License compatibility}` | `deps/licenses` |
| `{skill: deps-audit, dimension: Known vulnerabilities}` | `deps/vulnerabilities` |
| `{skill: deps-audit, dimension: Freshness}` | `deps/freshness` |
| `{skill: deps-audit, dimension: Hygiene}` | `deps/hygiene` |

Each of those four gets the citing row's id in its `handbook`. The two opt-ins are cited by nobody, so both need `handbook: []` and a `handbook_note` - and per the global constraints those two notes must differ, because the reasons differ (an SBOM's completeness versus a transitive-graph depth the handbook never asks for).

**`deptry`, the question PR #560 left open.** PR 1 dropped `deptry` from `arch`'s detect list as an orphan no arch check consumed, noting `deps-audit` already claimed it. Confirm that here: `deptry` detects declared-but-unused and used-but-undeclared imports, which is exactly `deps/hygiene`. If it belongs in `deps/hygiene`'s `tooling.python`, put it there and say so in the commit message; if the source `§3` never listed it, say that instead. Either way, resolve it - do not carry it forward as open.

- [ ] **Step 1: Read the sources**

Read `.agents/skills/deps-audit/SKILL.md` in full, and both reference records named in the schema section above. Map every sentence of `§2`-`§7` to its destination before writing anything: a record, the header, or (for a handoff) the header's cross-domain line. A sentence with no destination is a signal you have the wrong record set - report it rather than dropping it.

- [ ] **Step 2: Write the six records**

Severity paragraphs come from `§4`, tooling from `§3`, fixes from `§5`, review lenses from `§6`. Add a `typescript:` tooling key alongside `python:` where the domain's tools have TypeScript equivalents (`npm audit` / `osv-scanner` / `license-checker` / `depcheck`), which is #519's half of this work. Where a check is genuinely language-independent, use `any:`.

- [ ] **Step 3: Reduce `SKILL.md` to a header**

Keep: the verbatim `description:`, the announce line, `§1` subject and scope, the `§4` **status scale** (not the per-check severities), the SBOM deliverable, and a pointer reading "The checks are records in [`checks/`](checks/) beside this file; load the ones your slice needs, not the directory." Follow `.agents/skills/arch-audit/SKILL.md` as the shape.

- [ ] **Step 4: Rewire the matrix and re-render**

Replace the four mappings with bare id strings. Then `grep -c "skill: deps-audit" docs/audit/handbook-traceability.yaml` must print `0`.

- [ ] **Step 5: Gate and commit**

Run the gate, then stage the exact paths and commit with `feat(#559): migrate deps-audit to check records`.

---

### Task 3: Migrate `docs-audit`

**Files:**
- Create: `.agents/skills/docs-audit/checks/{organization,cross-referencing,coverage,docstring-coverage,docstring-staleness,docstring-standard}.md`
- Modify: `.agents/skills/docs-audit/SKILL.md`
- Modify: `docs/audit/handbook-traceability.yaml`, `docs/audit/handbook-traceability.md`

| source | id | locality | optin |
|---|---|---|---|
| Organization | `docs/organization` | global | no |
| Cross-referencing | `docs/cross-referencing` | global | no |
| Coverage | `docs/coverage` | global | no |
| §7 docstrings - Coverage | `docs/docstring-coverage` | local | **yes** |
| §7 docstrings - Staleness | `docs/docstring-staleness` | local | **yes** |
| §7 docstrings - Standard | `docs/docstring-standard` | local | **yes** |

The three prose dimensions are `global`: an orphaned doc, a dead link and an index gap are all properties of the whole doc tree. The three docstring dimensions are `local` - the source says "Report per package" - and each has its own detection, severity and fix, so each is its own record rather than one `docs/docstrings`.

**The `§7` CI note is a property of all three docstring records:** docstring fixes touch code, so they need the lint/typecheck/test gate rather than the docs-only path. That qualifier **distributes** - copy it into all three.

**The "Documentation-specific rule" section** (keep prescriptive and background separate, cross-link the two) is the criterion `docs/organization` judges misfiling by, so it moves into that record's body. If on reading it you find the cross-linking half belongs to `docs/cross-referencing` instead, split it at the clause boundary and put each half where it belongs - that is permitted edit (c). Do not leave it in the header: it is a check's criterion, not a domain-level rule.

**Matrix references** - 8 references, 3 distinct pairs:

| legacy pair | id | refs |
|---|---|---|
| `{docs-audit, Coverage}` | `docs/coverage` | 3 |
| `{docs-audit, Cross-referencing}` | `docs/cross-referencing` | 3 |
| `{docs-audit, Organization}` | `docs/organization` | 2 |

`docs/coverage`'s `handbook` therefore lists three row ids, `docs/cross-referencing` three, `docs/organization` two. The three docstring records are cited by nobody: `handbook: []` plus three genuinely different notes.

Steps as Task 2 (read and map, write records, reduce header, rewire, gate). `grep -c "skill: docs-audit"` must print `0`. Commit: `feat(#559): migrate docs-audit to check records`.

---

### Task 4: Migrate `security-audit`

**Files:**
- Create: `.agents/skills/security-audit/checks/{dangerous-calls,injection,secrets-in-code,crypto,unsafe-io,sensitive-data,secret-history}.md`
- Modify: `.agents/skills/security-audit/SKILL.md`
- Modify: `docs/audit/handbook-traceability.yaml`, `docs/audit/handbook-traceability.md`

| source | id | locality | optin |
|---|---|---|---|
| Dangerous calls / code execution | `security/dangerous-calls` | local | no |
| Injection | `security/injection` | local | no |
| Secrets in code | `security/secrets-in-code` | local | no |
| Crypto & randomness | `security/crypto` | local | no |
| Unsafe I/O & deserialization | `security/unsafe-io` | local | no |
| Sensitive-data handling | `security/sensitive-data` | local | no |
| §7 Git-history secret scan | `security/secret-history` | global | **yes** |

Six pattern-matching checks are `local` - each is decidable from one package's source. The history scan is `global` and cannot be otherwise: git history is one object per repo.

**Injection is the one to watch.** `security/injection` covers command, SQL, path traversal, template/SSTI and SSRF, and the source's severity and fix prose for it is source-to-sink reasoning that must survive intact. If `§4`/`§5` treat SSRF differently from the rest, that is a signal it wants its own record - report the finding rather than flattening the difference away.

**Two `§7` entries are handoffs, not checks:** the dependency-CVE cross-check goes to `deps-audit` and the CI/secret-hardening cross-check to `ci-audit`. Both stay as header lines. Note that `deps/vulnerabilities` already exists from Task 2, so the handoff can name the check id rather than a skill and a dimension.

**Matrix references** - 6 references, 5 distinct pairs:

| legacy pair | id | refs |
|---|---|---|
| `{security-audit, Sensitive-data handling}` | `security/sensitive-data` | 2 |
| `{security-audit, Dangerous calls / code execution}` | `security/dangerous-calls` | 1 |
| `{security-audit, Injection}` | `security/injection` | 1 |
| `{security-audit, Secrets in code}` | `security/secrets-in-code` | 1 |
| `{security-audit, Unsafe I/O & deserialization}` | `security/unsafe-io` | 1 |

`security/crypto` and `security/secret-history` are cited by nobody and need `handbook: []` plus notes.

Steps as Task 2. `grep -c "skill: security-audit"` must print `0`. Commit: `feat(#559): migrate security-audit to check records`.

---

### Task 5: Migrate `test-audit`

**Files:**
- Create: `.agents/skills/test-audit/checks/{coverage-reach,new-code-coverage,assertion-strength,determinism,isolation,mutation,property-based-gap}.md`
- Modify: `.agents/skills/test-audit/SKILL.md`
- Modify: `docs/audit/handbook-traceability.yaml`, `docs/audit/handbook-traceability.md`

| source | id | locality | optin |
|---|---|---|---|
| Coverage reach | `test/coverage-reach` | local | no |
| TDD adherence / new-code coverage | `test/new-code-coverage` | global | no |
| Assertion strength | `test/assertion-strength` | local | no |
| Determinism / flakiness | `test/determinism` | local | no |
| Isolation & speed | `test/isolation` | local | no |
| Effectiveness (optional) **and** §7 Mutation testing | `test/mutation` | local | **yes** |
| §7 Property-based testing gap | `test/property-based-gap` | local | **yes** |

**`§2` "Effectiveness (optional)" and `§7` "Mutation testing" are one check, not two.** `§2` says "see §7" - they are the same dimension described twice, which is exactly the scattering this migration exists to end. Merge both passages into `test/mutation`. The matrix cites the pair `{test-audit, Effectiveness (optional)}`, so that reference lands on `test/mutation`.

**`test/new-code-coverage` is `global`.** It measures coverage **on the diff** - a property of the change set, not of any one package - so a per-package agent cannot compute it. This is Task 1's rule in a second domain.

**§7 behavioral/eval cross-check is a handoff** to `eval-audit`; it stays a header line.

**Matrix references** - 6 references, 6 distinct pairs, one each: `Coverage reach` -> `test/coverage-reach`, `TDD adherence / new-code coverage` -> `test/new-code-coverage`, `Assertion strength` -> `test/assertion-strength`, `Determinism / flakiness` -> `test/determinism`, `Isolation & speed` -> `test/isolation`, `Effectiveness (optional)` -> `test/mutation`.

Every `test` check except `test/property-based-gap` is cited, so only that one needs a `handbook_note`.

Steps as Task 2. `grep -c "skill: test-audit"` must print `0`. Commit: `feat(#559): migrate test-audit to check records`.

---

### Task 6: Migrate `ci-audit`

**Files:**
- Create: `.agents/skills/ci-audit/checks/{gate-enforcement,trigger-safety,permissions-secrets,action-supply-chain,workflow-correctness,efficiency,deploy-safety,branch-protection,self-hosted-runners}.md`
- Modify: `.agents/skills/ci-audit/SKILL.md`
- Modify: `docs/audit/handbook-traceability.yaml`, `docs/audit/handbook-traceability.md`

| source | id | locality | optin |
|---|---|---|---|
| Gate enforcement | `ci/gate-enforcement` | global | no |
| Trigger safety | `ci/trigger-safety` | local | no |
| Permissions / secrets | `ci/permissions-secrets` | local | no |
| Action supply chain | `ci/action-supply-chain` | local | no |
| Correctness | `ci/workflow-correctness` | local | no |
| Efficiency | `ci/efficiency` | local | no |
| Deploy safety | `ci/deploy-safety` | global | no |
| §7 Branch-protection & environment review | `ci/branch-protection` | global | **yes** |
| §7 Self-hosted-runner hardening | `ci/self-hosted-runners` | global | **yes** |

The partition here is **one workflow file**, so most checks are `local` to a workflow. Two are not: `ci/gate-enforcement` compares what the contributor guide claims CI enforces against what the workflows plus branch protection actually enforce - which needs every workflow at once plus repo settings - and `ci/deploy-safety` reasons about the release path across workflows. State the partition in the header's fan-out line.

**`ci/gate-enforcement` carries 7 of this PR's 65 references** - the most-cited check in the family. Its `handbook` lists seven row ids. Get this one right before the others; if the gate fails after this task, it is almost certainly here.

**§7 pipeline-secret history is a handoff** to `security-audit` - and after Task 4 it can name `security/secret-history` directly.

**Matrix references** - 10 references, 4 distinct pairs:

| legacy pair | id | refs |
|---|---|---|
| `{ci-audit, Gate enforcement}` | `ci/gate-enforcement` | 7 |
| `{ci-audit, Action supply chain}` | `ci/action-supply-chain` | 1 |
| `{ci-audit, Permissions / secrets}` | `ci/permissions-secrets` | 1 |
| `{ci-audit, Trigger safety}` | `ci/trigger-safety` | 1 |

Five records are cited by nobody: `workflow-correctness`, `efficiency`, `deploy-safety`, `branch-protection`, `self-hosted-runners`. Five distinct `handbook_note`s. If two of them come out identical, re-read the handbook for the one you are about to duplicate - the notes are where the gap analysis actually lives, and #518's scope is read off them.

Steps as Task 2. `grep -c "skill: ci-audit"` must print `0`. Commit: `feat(#559): migrate ci-audit to check records`.

---

### Task 7: Migrate `eval-audit`

**Files:**
- Create: `.agents/skills/eval-audit/checks/{coverage,methodology,reproducibility,contamination,prompt-quality,smoke-test-gate,regression-tracking,adversarial,judge-calibration,cost-latency}.md`
- Modify: `.agents/skills/eval-audit/SKILL.md`
- Modify: `docs/audit/handbook-traceability.yaml`, `docs/audit/handbook-traceability.md`

| source | id | locality | optin |
|---|---|---|---|
| Eval coverage | `eval/coverage` | global | no |
| Methodology soundness | `eval/methodology` | local | no |
| Reproducibility | `eval/reproducibility` | local | no |
| Contamination / leakage | `eval/contamination` | local | no |
| Prompt / SOP quality | `eval/prompt-quality` | local | no |
| Smoke-test gate | `eval/smoke-test-gate` | global | no |
| Regression tracking & cost | `eval/regression-tracking` | global | no |
| §7 Adversarial / red-team eval | `eval/adversarial` | global | **yes** |
| §7 LLM-judge calibration study | `eval/judge-calibration` | local | **yes** |
| §7 Cost/latency profile | `eval/cost-latency` | global | **yes** |

The partition is **one eval suite**. `eval/coverage` is global because "is every behavior-that-matters covered?" is answered against the whole capability set, not one suite; `eval/smoke-test-gate` and `eval/regression-tracking` are repo-level facts (one gate, one leaderboard).

**`eval/prompt-quality` is a boundary, and the source already draws it.** It owns the *behavioral* facets (drift vs. current code and tools, versioning, injection-resistance) and explicitly defers the *static* authoring facets to `prompt-audit`. That deferral sentence moves into the record verbatim - after Task 8 it can name the `prompt/*` ids it defers to, but this task runs first, so leave it naming `prompt-audit` and let Task 8's reviewer decide whether to sharpen it. Do not silently widen the record to cover what it defers.

**This domain carries 25 of the 65 references** - more than a third of the PR - across 7 distinct pairs:

| legacy pair | id | refs |
|---|---|---|
| `{eval-audit, Methodology soundness}` | `eval/methodology` | 6 |
| `{eval-audit, Reproducibility}` | `eval/reproducibility` | 5 |
| `{eval-audit, Eval coverage}` | `eval/coverage` | 4 |
| `{eval-audit, Regression tracking & cost}` | `eval/regression-tracking` | 4 |
| `{eval-audit, Smoke-test gate}` | `eval/smoke-test-gate` | 3 |
| `{eval-audit, Contamination / leakage}` | `eval/contamination` | 2 |
| `{eval-audit, Prompt / SOP quality}` | `eval/prompt-quality` | 1 |

Only the three opt-ins are uncited and need notes.

Steps as Task 2. `grep -c "skill: eval-audit"` must print `0`. Commit: `feat(#559): migrate eval-audit to check records`.

---

### Task 8: Migrate `prompt-audit`

**Files:**
- Create: `.agents/skills/prompt-audit/checks/{role-objective,output-contract,instruction-precision,positive-framing,grounding,examples-delimiters,internal-consistency,cognitive-load,sop-structure,sop-naming,sop-rfc2119,cross-prompt-consistency}.md`
- Modify: `.agents/skills/prompt-audit/SKILL.md`
- Modify: `docs/audit/handbook-traceability.yaml`, `docs/audit/handbook-traceability.md`

The largest header in the family (2,877 words) and the only one with a two-tier structure. It runs last because its Tier A/Tier B question is the one most likely to need a ruling, and by now six domains have set the pattern.

**Tier A** - eight checks, all `local` (the partition is one prompt or SOP file):

| source bullet | id |
|---|---|
| Role, objective & task framing | `prompt/role-objective` |
| Output contract | `prompt/output-contract` |
| Instruction precision | `prompt/instruction-precision` |
| Positive framing, prohibitions with reasons | `prompt/positive-framing` |
| Grounding & handling the unknown | `prompt/grounding` |
| Examples & delimiters | `prompt/examples-delimiters` |
| Internal consistency | `prompt/internal-consistency` |
| Cognitive load & focus | `prompt/cognitive-load` |

**Tier B** - three checks, all `local`, applying to `.sop.md` files only:

| source bullet | id |
|---|---|
| required sections present and in order, each step carrying a Constraints block | `prompt/sop-structure` |
| `.sop.md` extension, kebab-case filename, `snake_case` parameters with required/optional marking and ordering | `prompt/sop-naming` |
| constraints expressed in the RFC 2119 keyword vocabulary | `prompt/sop-rfc2119` |

**The tier gate is prose, not a new frontmatter field.** The schema has no `applies_to`, and this PR adds none - `locality` exists to drive fan-out, and artifact-type scoping is a judgment the agent makes when it reads the record. Each Tier B record opens by stating it applies to `.sop.md` files only. The **rule** that a general prompt is judged on Tier A only and is *never* penalized for lacking SOP sections, parameters or RFC 2119 vocabulary is domain-level - it says which records apply to which slice of the subject - so it stays in the header, verbatim, as part of the subject-and-how-to-slice-it paragraph. Getting this backwards (dropping the rule into twelve records, or inventing a schema field) is the failure mode for this task.

**Opt-ins:** `§7` cross-prompt consistency sweep becomes `prompt/cross-prompt-consistency` (`global`, `optin: true`) - it audits a prompt library as a set for drift, which no single-file agent can see. The other two `§7` entries are **deliverables**: sub-agent decomposition analysis produces a decomposition diagram and handoff contracts, and reasoning-token strategy produces a per-step recommendation. Neither emits findings-matrix rows; both stay as header lines.

**The `## See also` section stays in the header** - it is cross-domain routing, and `audit-core`'s "cross-link, don't duplicate" rule is what it implements.

**Matrix references** - 6 references, 5 distinct pairs:

| legacy pair | id | refs |
|---|---|---|
| `{prompt-audit, Grounding & handling the unknown}` | `prompt/grounding` | 2 |
| `{prompt-audit, Cognitive load & focus}` | `prompt/cognitive-load` | 1 |
| `{prompt-audit, Instruction precision}` | `prompt/instruction-precision` | 1 |
| `{prompt-audit, Positive framing, prohibitions with reasons}` | `prompt/positive-framing` | 1 |
| `{prompt-audit, Role, objective & task framing}` | `prompt/role-objective` | 1 |

Seven records are uncited: `output-contract`, `examples-delimiters`, `internal-consistency`, the three `sop-*`, and `cross-prompt-consistency`. That is the largest block of `handbook_note`s in the PR, and the three `sop-*` notes are the ones most likely to come out identical - the handbook does not carry the SOP spec, which is a single reason covering three records. If that is genuinely the situation, say it three times in three different words, each naming what *that* record checks; do not paste one sentence three times, and do not merge the three records to dodge the problem.

Steps as Task 2. `grep -c "skill: prompt-audit"` must print `0`. Commit: `feat(#559): migrate prompt-audit to check records`.

---

### Task 9: Switch the front door to the checks tree, and close the transition

**Files:**
- Modify: `.agents/skills/audit/SKILL.md`
- Modify: `.agents/skills/audit-core/SKILL.md`
- Modify: `tests/scripts/test_audit_checks.py`

**Interfaces:**
- Consumes: all eight domains now have a non-empty `checks/` directory (Tasks 1-8).

This is the acceptance criterion PR 1 deliberately deferred: with one domain in the tree and eight skills on disk, detecting from the tree would have silently dropped seven domains from `/audit all`. The tree is now complete, so it is safe.

- [ ] **Step 1: Write the failing test**

In `tests/scripts/test_audit_checks.py`, add a test over the **real** skills directory (not a fixture): every `*-audit` skill directory has a non-empty `checks/`, `load_checks(SKILLS_DIR)` returns zero errors, and the loaded records cover all eight domain names. This is the regression net that catches a malformed record or an un-migrated domain landing later.

- [ ] **Step 2: Run it and watch it pass**

It should already pass after Tasks 1-8. If it fails, a task left a domain incomplete - fix that domain before continuing, and say which in the commit message. A test written last that passes first time still earns its place as the net; do not weaken it to match whatever the tree happens to contain.

- [ ] **Step 3: Rewrite `audit/SKILL.md` §0 detection**

The scope bullet currently says "**Detect which `*-audit` skills actually exist** under the skills dir and only run those". Change the detection to the checks tree: a domain is available when `.agents/skills/<domain>-audit/checks/` exists and holds at least one record. Keep every surrounding rule intact - the argument-first scoping, the "tell them it was skipped (and why)" requirement, the 4-option cap on the ask-the-user tool, and `Default = all`. The change is the detection predicate, nothing else.

- [ ] **Step 4: Update the §1 fan-out instruction**

The line handed to each domain subagent currently says to read the whole domain `SKILL.md` plus `audit-core`. Change it to: read the domain header and `audit-core`, then load from `checks/` only the records the slice needs - `local` records per partition, one `global` record per agent. This is where the measured 36-50% context reduction actually gets spent; leaving the instruction as "read the SKILL.md" would keep the old cost with none of the benefit, since the header no longer contains the checks.

- [ ] **Step 5: Remove `audit-core`'s transitional paragraph**

Delete the "**Domains not yet migrated** (everything but `arch`, until #559 PR 2)…" paragraph and its seven-slot list. Nothing is unmigrated now. Update the sentence pointing at `../arch-audit/checks/` as the reference set if a better example now exists.

- [ ] **Step 6: Verify the whole PR's completion claim**

```bash
grep -c "skill: " docs/audit/handbook-traceability.yaml
uv run python scripts/render_handbook_traceability.py --check
uv run pytest tests/scripts/ -q
```

The first must print `0`. Record the final record count and the per-domain header word counts in the commit message - the PR body reports them and they must come from a measurement, not an estimate.

- [ ] **Step 7: Gate and commit**

Commit: `feat(#559): detect audit domains from the checks tree`.

---

## Self-review notes

**Spec coverage.** Of the spec's acceptance criteria, this plan delivers: all remaining checks migrated (Tasks 2-8), the last 65 matrix references rewired (Tasks 2-8), every domain `SKILL.md` reduced to a header (Tasks 2-8), and the `audit` front door detecting from the checks tree (Task 9). It does **not** deliver the `skill_dimensions()` removal - that is PR 3 by explicit decision, recorded above.

**Forward-safe ordering.** Task 1 states the locality rule before any domain needs it. Tasks 2-8 are mutually independent - they touch disjoint skill directories and disjoint matrix rows - and each leaves the gate green, so a failure is attributable to the domain that caused it and any single domain can be reverted without touching the others. Task 9 depends on all of them and is the only task that asserts across domains.

**Task 2 is deliberately the smallest domain.** The recipe has been proved once, on `arch`, by a different set of agents in a different PR. Re-proving it on 850 words before applying it to 2,877 costs one task ordering decision and nothing else.

**The known failure modes**, all from PR 1's review and pilot: prose quietly summarised instead of moved (guarded by the word-count diff), an anaphoric tail duplicated across records (guarded by the distributive rule), a review lens filed under the dimension it came from instead of the fix it reviews (guarded by the review-lens rule), and boilerplate `handbook_note`s (guarded by the distinctness rule, and called out again in Tasks 6 and 8 where the risk is highest).
