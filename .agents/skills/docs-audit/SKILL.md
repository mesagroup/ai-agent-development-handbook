---
name: docs-audit
description: "Audit a project's documentation for organization, cross-referencing, and coverage, then fill the gaps to a consistent functional + architecture standard. Use when docs have drifted from the code, when a tree has grown organically and needs a structured review, when onboarding requires the docs alone to explain the system, or when the user asks to audit/reorganize/complete documentation. Works on any Python project. Optionally also audits docstrings. Runs on the audit-core engine."
---

# Documentation Audit and Gap-Filling

A domain specialization of **[audit-core](../audit-core/SKILL.md)** — read that first; it owns the loop (scope → parallel evidence → findings matrix → plan → subagent-driven fixes → review → PR) and the cross-cutting rules. This skill supplies the documentation lens.

**Core principle:** the docs alone should convey what the system does and how it is built, without reading the source. The audit measures the distance from that goal; the fill-gaps phase closes it. Every written claim must be verifiable against current source — a confident, wrong doc is worse than a missing one.

**Announce:** "I'm using the docs-audit skill (on the audit-core engine) to audit and complete the documentation."

**Bash rule:** never pass a line starting with `#` to the Bash tool (you or any subagent).

## When to use

- Documentation has drifted from the code (stale entry points, removed APIs still documented, wrong defaults).
- A `docs/` tree grew organically and no one is sure what is covered, what is orphaned, or whether the index is complete.
- You want the docs to stand alone for onboarding ("if we stopped for six months, could we restart from the docs?").
- The user asks to audit, reorganize, cross-link, or complete documentation.

**Not for:** writing a single new doc for a single new feature (just write it), or a pure prose copy-edit with no coverage/structure question.

## 1. Subject & scope

The documentation tree (`docs/`, `documentation/`, a `README` tree, or a docs-site source) and the code it documents. Slice the parallel evidence pass **by code tier/package** — one source-mapping agent per tier. For a large tree, deliver in **increments** (one tier or coherent group per PR); each increment is its own audit-informed plan + PR.

**Opt-in — docstring auditing:** if the invocation passed an enabling argument (e.g. `--docstrings`), include the docstring phase (below). If not, **ask the user once**: "Also audit docstrings (module/class/function coverage + staleness), or just the prose docs?" It materially changes the work — don't assume.

## 2. Dimensions (findings-matrix columns)

Three axes:
- **Organization** — is the folder structure right? Folders to split/merge/rename/archive, misfiled docs, deprecated/duplicate content. Prefer minimal moves — relocating docs breaks links for cosmetic gain, so recommend a move only when it clearly pays for itself.
- **Cross-referencing** — index → doc completeness, dead links, orphaned docs (reachable from nothing), and missing reciprocal links (e.g. background/research ↔ prescriptive/architecture).
- **Coverage** — for every code component, the doc(s) covering it and a status: **documented** (a real dedicated doc), **partial** (only a passing mention / entry-level note / design-spec, no prescriptive reference), or **gap** (nothing). The partial/gap rows are the fill-gaps work list.

## 3. Evidence sources & tooling

- **Layout discovery** — enumerate code components (packages/modules/tiers) and the docs tree; note the project's architecture/dependency rules if a contributor guide states them (CLAUDE.md / AGENTS.md / CONTRIBUTING).
- **Source-mapping subagents (the load-bearing evidence pass)** — one read-only agent per tier maps each component's *real* interfaces from source (public classes/functions + signatures, entry points, config/env vars, key mechanisms), even when a doc already exists, so you can compare doc-vs-reality. Also dispatch one agent to extract the **doc standard** (the section skeleton the best existing docs use) and the **overlap map** (what each existing doc already owns, so writing cross-links instead of duplicating).
- **Link/index checker (the domain gate)** — if the project has a docs link-checker / index-completeness script, use it. If not, do a dead-link + orphan scan yourself (every relative link resolves; every doc reachable from an index), and consider proposing a small checker as a deliverable.
- Save the findings report under the docs tree (e.g. `docs/audit/<date>-docs-audit.md`) and record policy decisions (retention/archival, what stays un-indexed) so they aren't re-litigated.

## 4. Status scale + severity rubric

Coverage status per component: **documented / partial / gap** (above). Finding severity: **Critical** — a doc that actively misdescribes the system (removed API still documented, wrong default/signature that would mislead a reader); **Important** — an uncovered load-bearing component, a dead link in the index, an orphaned key doc; **Minor** — a partial that has a passing mention, a stylistic inconsistency, a missing reciprocal link.

## 5. Fix patterns (and CI implications)

Prose-doc fixes are **docs-only**, which usually keeps the PR off the heavy code gates — call that out. The domain gate is **the link/index checker green**.
- Write the missing doc to the project's doc standard (Overview → Functional → Architecture → Configuration → See also, or whatever the extracted standard is), grounded in the source maps.
- **Each doc-creation task ships its own index entry in the same commit** (forward-link-safe: no task links a doc a later task creates; the checker stays green per task). Only isolate index changes to a final task when the new docs sit under an existing directory-link that auto-covers them.
- Reconcile the index, repair dead links, add reciprocal research↔architecture links, consolidate deprecated/duplicate docs per an explicit policy.
- Ground each writing task in the Phase-1 source maps: the exact interfaces/facts to cover (with `file:line`) and the exact cross-links, so the implementer verifies rather than invents.

## 6. Review dimensions (Phase-5 specialized reviewers)

- **Source accuracy** — open the code and verify the docs' concrete claims (names, signatures, defaults, env vars, "does X now"). Highest-value catch: fabricated defaults, dropped flags, wrong import paths.
- **Cross-doc consistency** — new docs agree with each other and with pre-existing docs.
- **Cross-link integrity** — every internal link resolves, no forward links, checker green, cross-link-don't-duplicate holds.
- **Doc-standard + conventions** — section order, markdown/style, no env-specific values.
- **Coverage vs plan** — every planned gap/partial actually addressed; nothing silently dropped.

## 7. Opt-in sub-audit — docstrings

Run only if enabled (argument or the user's answer in §1). Distinct phase, sequenced after or alongside the prose audit.
- **Coverage** — which public modules/classes/functions lack docstrings (`ruff` `D` rules / `pydocstyle` / `interrogate` if present, else an AST/grep sweep). Report per package.
- **Staleness** — docstrings that contradict the code (wrong parameter names, removed return types, "raises X" the code no longer raises, examples that would fail). Needs reading — use source-mapping subagents as in the prose audit.
- **Standard** — each module/`__init__` and public symbol has a docstring describing what it does and how to use it, per the project's convention.
- **CI note:** docstring fixes **touch code**, so they are **not** docs-only — they need the normal lint/typecheck/test gate and may need the code-review gate.

## Documentation-specific rule (beyond the audit-core cross-cutting rules)

- **Distinguish prescriptive from background.** Keep "how it actually works, verifiable against source" docs separate from "background investigation / research" material, and cross-link the two. Don't let exploration accumulate in the prescriptive tree.
