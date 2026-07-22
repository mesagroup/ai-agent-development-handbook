---
name: docs-audit
description: "Audit a project's documentation for organization, cross-referencing, and coverage, then fill the gaps to a consistent functional + architecture standard. Use when docs have drifted from the code, when a tree has grown organically and needs a structured review, when onboarding requires the docs alone to explain the system, or when the user asks to audit/reorganize/complete documentation. Works on any Python project. Optionally also audits docstrings."
---

# Documentation Audit and Gap-Filling

A reusable, project-agnostic workflow for auditing a documentation tree and then bringing it up to a consistent standard: audit → coverage matrix → plan → subagent-driven writing with review → merge. Proven on a six-phase real-world audit.

**Core principle:** the docs alone should convey what the system does and how it is built, without reading the source. The audit measures the distance from that goal; the fill-gaps phase closes it. Every written claim must be verifiable against current source — a confident, wrong doc is worse than a missing one.

**Announce at start:** "I'm using the docs-audit skill to audit and complete the documentation."

**Bash rule (applies to you and every subagent you dispatch):** never pass a line starting with `#` to the Bash tool — hash comments confuse the tool-permission subsystem. Put commit messages in heredoc files or use `-m`.

## When to use

- Documentation has drifted from the code (stale entry points, removed APIs still documented, wrong defaults).
- A `docs/` tree grew organically and no one is sure what is covered, what is orphaned, or whether the index is complete.
- You want the docs to stand alone for onboarding ("if we stopped for six months, could we restart from the docs?").
- The user asks to audit, reorganize, cross-link, or complete documentation.

**Not for:** writing a single new doc for a single new feature (just write it), or a pure prose copy-edit with no coverage/structure question.

## Scope and arguments

Resolve two things before doing anything else:

1. **Target scope.** Which documentation tree and which code does it document? Default to the repo's docs directory (`docs/`, `documentation/`, a `README` tree, or a docs site source) and the package(s) under audit. If the repo is large, the user may scope to one tier/package.
2. **Docstring auditing (opt-in).** If the invocation passed an argument enabling it (e.g. `--docstrings`, `docstrings`, `+docstrings`), include the docstring phase. If no such argument was passed, **ask the user once**: "Should I also audit docstrings (module/class/function coverage + staleness), or just the prose docs?" Do not assume — it materially changes the work.

For a multi-tier or large tree, plan to deliver in **phases** (one tier or coherent group per PR) rather than one enormous change. Each phase is its own audit-informed plan + PR.

## The workflow

This skill adapts the planning / spec / subagent-driven-development / review / finish steps from the issue-to-merge family, keeping the doc-relevant parts and dropping the code-only ones. If those skills are available in the environment, invoke them at the marked points; if not, follow the inline instructions.

The steps run in order, each feeding the next:

0. **Scope + docstring decision** (see the section above) →
1. **Audit** — parallel read-only source-mapping → a coverage matrix + findings report + reorganization plan →
2. **Write the plan** — one task per doc, forward-link-safe ordering →
3. **Subagent-driven writing + per-task review** — fresh implementer per doc, reviewed against source →
4. **Whole-branch review** — cross-doc consistency and residual inaccuracy →
5. **Finish** — open the docs-only PR.

### Phase 1 — Audit

Goal: a findings report and a **coverage matrix** grounded in *current source*, not in the existing docs (which may be exactly what has drifted).

- **Discover the layout.** Enumerate the code components (packages, modules, tiers) and the docs tree. Note the project's dependency/architecture rules if documented (e.g. a CONTRIBUTING or CLAUDE/AGENTS file).
- **Detect the link/index checker.** If the project has a docs link-checker or index-completeness script, use it as the gate. If not, do a dead-link + orphan scan yourself (every relative link resolves; every doc is reachable from an index). Consider proposing a small checker as part of the deliverable.
- **Fan out read-only source-mapping subagents — one per tier/package, in parallel.** This is the load-bearing step: a fresh reader agent maps each component's real interfaces (public classes/functions + signatures, entry points, config/env vars, key mechanisms) directly from source and reports a structured map. Do this even when a doc already exists, so you can compare doc-vs-reality. Also dispatch one agent to extract the **doc standard** (the section skeleton existing good docs use) and the **overlap map** (what each existing doc already owns, so later writing cross-links instead of duplicating).
- **Build the coverage matrix.** For every component: the doc(s) that cover it and a status — `documented` (a real dedicated doc), `partial` (only a passing mention / entry-level note / design-spec, no prescriptive reference), or `gap` (nothing). Summarize counts per tier.
- **Findings on all three axes:**
  - *Organization* — is the folder structure right? Flag folders to split/merge/rename/archive, misfiled docs, and deprecated/duplicate content. Prefer minimal moves; relocating docs breaks links for cosmetic gain, so recommend a move only when it clearly pays for itself.
  - *Cross-referencing* — index → doc completeness, dead links, orphaned docs, and missing reciprocal links (e.g. background/research ↔ prescriptive/architecture).
  - *Coverage* — the gap/partial list from the matrix is the fill-gaps work list.
- **Save** the audit report under the docs tree (e.g. `docs/audit/<date>-docs-audit.md`) so it is itself linkable, and record any policy decisions (retention/archival, what stays un-indexed) so they are not re-litigated later.

If the codebase is large, this is a good place to invoke a brainstorming/spec step to agree scope and the doc standard with the user before planning.

### Phase 2 — Write the plan

Invoke the writing-plans skill if available; otherwise write a plan file under the project's plans location (e.g. `docs/superpowers/plans/<date>-docs-audit-<scope>.md`).

- **One task per doc** (or per tightly-coupled small group). Each task = create/rewrite one doc + its index entry, verifiable independently.
- **Global constraints block** (copied verbatim into every task): docs-only (no code edits unless the scope explicitly includes them); the doc standard (section order); cross-link-don't-duplicate; verify-every-claim-against-source; the link-checker gate; markdown/style conventions; no environment-specific values (no absolute machine paths, personal profiles, hostnames — use placeholders); commit-message/trailer conventions.
- **Forward-link-safe ordering.** Order tasks so no doc links a doc created in a *later* task. The reliable rule: **each doc-creation task ships its own index entry in the same commit**, so the link-checker stays green after every task. (Only isolate index changes to a final task when the new docs already sit under an existing directory-link that auto-covers them.)
- Ground each task's spec in the Phase-1 source maps: list the exact interfaces/facts to cover (with source file:line references) and the exact cross-links — so the implementer verifies rather than invents.

### Phase 3 — Subagent-driven writing with per-task review

Invoke the subagent-driven-development skill if available; otherwise follow this loop per task. Track progress in a durable ledger file so the run survives interruption.

For each task:
1. **Dispatch a fresh implementer subagent** with: where the doc fits, the task brief (its requirements + source references), the global constraints, and the report-file path. Instruct it to read source and confirm every fact, write the doc to the standard, add the index entry, run the link-checker to green, commit (docs-only), and self-review. Remind it of the Bash-no-`#` rule.
2. **Review against source (two verdicts).** Dispatch a reviewer subagent (or review inline if subagents are unstable): *spec compliance* (all required content, nothing extra) and *quality*. The reviewer's first duty is to **open the source files and spot-verify the doc's specific claims** — names, signatures, defaults, env vars, "currently does X" statements. Fabrication or drift is the highest-value catch. Also check: doc-standard order, cross-link-don't-duplicate, link-checker green, no env-specific values. (The whole-branch gate in Phase 4 runs the fuller multi-reviewer pass — the per-task review is the lighter, single-reviewer gate.)
3. **Resolve findings.** Fix Critical/Important before advancing; apply easy, correct Minor fixes too. Resolve any "cannot verify from the diff" item yourself against source — these often hide real defects (a plausible-but-wrong default, a dropped flag).
4. **Record** the task as complete in the ledger and move on.

Do not run implementers in parallel (they collide on the index and shared files). One task at a time.

### Phase 4 — Whole-branch review

After all tasks, run the project's canonical code-review skill over the whole branch, **adapted for documentation**. If a `/code-review:code-review` skill (or an `implement-and-review`-style review phase) exists, invoke it; otherwise reproduce its shape inline. That shape is: **several specialized reviewer subagents in parallel, then confidence-score each finding and act on it by threshold** — the same multi-subagent review used on the source-of-this-skill PRs.

Adapt the specialized reviewers to documentation dimensions (one subagent each, run in parallel):
- **Source accuracy** — open the code and verify the docs' concrete claims (names, signatures, defaults, env vars, "does X now"). This is where fabricated defaults, dropped flags, and wrong import paths get caught.
- **Cross-doc consistency** — the new docs agree with each other and with pre-existing docs (no two docs contradicting on the same fact).
- **Cross-link integrity** — every internal link resolves, no forward links, link-checker green; cross-link-don't-duplicate holds.
- **Doc-standard + conventions** — section order, markdown/style rules, no environment-specific values, commit-message/trailer conventions across all commits.
- **Coverage vs plan** — every planned gap/partial is actually addressed; nothing silently dropped.

Then, per the project's review convention, **score each finding for confidence** (real vs. false positive) and act by threshold — fix the confident ones (and easy correct minor ones), and report the full findings list with dispositions. Resolve any "cannot verify from the diff" item yourself against source. Fix everything real in a single follow-up pass. Use the most capable model available for this gate.

### Phase 5 — Finish

Invoke the finishing-a-development-branch skill (or open a PR directly). The PR is docs-only, which usually keeps it off the heavy CI gates that guard runtime code — call that out. Update the tracking issue and its acceptance criteria (tick only what was verified). **Do not merge without explicit user approval.**

## Optional phase — Docstring audit

Run only if enabled (argument or the user's answer from the scope step). Treat it as a distinct phase, sequenced after or alongside the prose audit.

- **Coverage:** which public modules/classes/functions lack docstrings. A quick pass with a tool (e.g. `ruff` `D` rules, `pydocstyle`, `interrogate`) if the project has one, else an AST/grep sweep. Report coverage per package.
- **Staleness:** docstrings that contradict the code they describe — wrong parameter names, removed return types, "raises X" that the code no longer raises, examples that would fail. This needs reading, not just tooling; use source-mapping subagents the same way as the prose audit.
- **Standard:** confirm each module/`__init__` and public symbol has a docstring describing what it does and how to use it, consistent with the project's convention. Fix or file, following the same subagent-driven + review loop. Docstring fixes touch code, so they are **not** a docs-only change — they need the project's normal code CI (lint/typecheck/tests) and may need the code-review gate.

## Quality rules to bake in (hard-won)

- **Verify against source, always.** Reviews on a real audit caught a fabricated config default, a dropped runtime guard, an overstated "it does X now" claim, and a copy-paste-failing import path — all in docs that read fluently. Prose fluency is not correctness.
- **Cross-link, don't duplicate.** If another doc already owns a topic, link it. Duplicated content drifts out of sync and doubles the maintenance.
- **Attribution honesty.** For vendored/third-party code, record real provenance; never fabricate an upstream URL or license. "Provenance tracked in issue #N, upstream unverified" is an honest and acceptable outcome.
- **Fix pre-existing issues you touch.** If the audit surfaces a small, real defect in an adjacent existing doc (a broken link, a wrong import), fix it in the same change rather than stepping around it. Discuss larger pre-existing problems before expanding scope.
- **Keep the checker green per task**, so a regression is attributable to the task that caused it — not discovered as a pile at the end.
- **No environment-specific values** in committed docs — placeholders (`<your-profile>`, `<path/...>`) with prose explaining what they resolve to.
- **Distinguish prescriptive from background.** Keep "how it actually works, verifiable against source" docs separate from "background investigation / research" material, and cross-link the two. Don't let exploration accumulate in the prescriptive tree.

## Adapting to any Python project

- Don't hardcode package names or tree shapes — discover them (`pyproject.toml`/`setup.cfg` for packages; the docs directory by convention or by asking).
- Use the project's existing doc standard if one exists (extract it from the best current docs); only impose a standard if none exists, and confirm it with the user.
- Use the project's link-checker/plan-location/commit conventions if present; fall back to sensible defaults (a local dead-link scan, `docs/plans/`, conventional-commit messages) otherwise.
- If the project's contributor guide (CLAUDE.md / AGENTS.md / CONTRIBUTING) states architecture or dependency rules, treat them as authoritative and keep the docs in sync with them.
