---
name: docs-audit
description: "Audit a project's documentation for organization, cross-referencing, and coverage, then fill the gaps to a consistent functional + architecture standard. Use when docs have drifted from the code, when a tree has grown organically and needs a structured review, when onboarding requires the docs alone to explain the system, or when the user asks to audit/reorganize/complete documentation. Works on any codebase. Optionally also audits docstrings. Runs on the audit-core engine."
---

# Documentation Audit and Gap-Filling

A domain specialization of **[audit-core](../audit-core/SKILL.md)** - read that first; it owns the loop (scope → parallel evidence → findings matrix → plan → subagent-driven fixes → review → PR), the `## Running a route` contract that turns this skill's records into commands, and the cross-cutting rules. The checks are records in [`checks/`](checks/) beside this file; load the ones your slice needs, not the directory. This skill supplies the documentation lens.

**Core principle:** the docs alone should convey what the system does and how it is built, without reading the source. The audit measures the distance from that goal; the fill-gaps phase closes it. Every written claim must be verifiable against current source - a confident, wrong doc is worse than a missing one.

**Announce:** "I'm using the docs-audit skill (on the audit-core engine) to audit and complete the documentation."

**Not for:** writing a single new doc for a single new feature (just write it), or a pure prose copy-edit with no coverage/structure question.

**Subject:** the documentation tree (`docs/`, `documentation/`, a `README` tree, or a docs-site source) and the code it documents. Slice the parallel evidence pass **by code tier/package** - one source-mapping agent per tier. For a large tree, deliver in **increments** (one tier or coherent group per PR); each increment is its own audit-informed plan + PR. `docs/coverage`, `docs/cross-referencing`, `docs/organization` and `docs/source-wrapping` are `global` - each is answered against the whole docs tree at once, the last of them because its subject is the docs tree and the fan-out above slices code tiers rather than docs, so there is no slice to give it. The three opt-in docstring checks named below are `local` to a source slice.

**Opt-in - docstring auditing:** if the invocation passed an enabling argument (e.g. `--docstrings`), include the docstring phase. If not, **ask the user once**: "Also audit docstrings (module/class/function coverage + staleness), or just the prose docs?" It materially changes the work - don't assume. Distinct phase, sequenced after or alongside the prose audit. The opt-in checks are `docs/docstring-coverage`, `docs/docstring-staleness` and `docs/docstring-standard`, loaded like any other.

**Build the source maps once, first.** Enumerate code components (packages/modules/tiers) and the docs tree; note the project's architecture/dependency rules if a contributor guide states them (CLAUDE.md / AGENTS.md / CONTRIBUTING). One read-only agent per tier maps each component's *real* interfaces from source (public classes/functions + signatures, entry points, config/env vars, key mechanisms), even when a doc already exists, so you can compare doc-vs-reality. Also dispatch one agent to extract the **doc standard** (the section skeleton the best existing docs use) and the **overlap map** (what each existing doc already owns, so writing cross-links instead of duplicating).

Status per row: **ok / warn / violation** (coverage: documented / partial / gap).

Prose-doc fixes are **docs-only**, which usually keeps the PR off the heavy code gates - call that out. The domain gate is **the link/index checker green**.

**Opt-in deliverable:** consider proposing a small checker as a deliverable.

Write the findings report to the `out_path` resolved in `audit-core` step 0, never under `target_root` - this domain audits a docs tree and so is the one most tempted to file its report inside that tree - and record policy decisions (retention/archival, what stays un-indexed) so they aren't re-litigated.
