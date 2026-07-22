---
name: arch-audit
description: "Audit a Python project's structure: layering / dependency-rule conformance (no illegal cross-tier imports, no cycles), module cohesion and coupling, per-module complexity, dead code, and oversized files. Use when a codebase has grown organically and the boundaries have blurred, before a refactor, when import cycles or god-modules are suspected, or when the user asks to audit architecture / structure / layering. Works on any Python project. Runs on the audit-core engine."
---

# Architecture Audit (structure, layering, coupling)

A domain specialization of **[audit-core](../audit-core/SKILL.md)** — read that first; it owns the loop (scope → parallel evidence → findings matrix → plan → subagent-driven fixes → review → PR) and the cross-cutting rules. This skill supplies the structural lens.

**Core principle:** a well-structured codebase has boundaries a reader can name and the import graph actually respects. The audit measures the distance between the *declared* architecture (the layering the contributor guide describes) and the *real* one (what the imports do), and surfaces the modules that have drifted, tangled, or grown past the point of being understandable in one sitting.

**Announce:** "I'm using the arch-audit skill (on the audit-core engine) to audit the project structure."

**Bash rule:** never pass a line starting with `#` to the Bash tool (you or any subagent).

## When to use

- A package tree grew organically and no one is sure the layering still holds (a low tier importing a high one, a service reaching into an agent).
- Import cycles are suspected, or a refactor keeps rippling further than expected (a sign of high coupling).
- A few modules have become god-files that everything depends on and nothing can be changed safely.
- The user asks to audit architecture, structure, layering, coupling, or dead code.

**Not for:** a single new module's design review (just review it), or a pure performance/security question (those are other lenses).

## 1. Subject & scope

The package tree (the importable source under `src/`, the top-level package, or wherever the project keeps its code) and its import graph. Establish the **declared architecture first**, because it is the spec every layering finding is judged against:

- Read the contributor guide (CLAUDE.md / AGENTS.md / CONTRIBUTING) for a stated tier/layer structure and dependency rules ("A may import B, never the reverse; no cycles"). If it states them, they are the rubric.
- If no rules are documented, **infer** the intended layers from the directory structure and confirm the inferred rules with the user before flagging violations — don't invent an architecture the team never agreed to.

Slice the parallel evidence pass **by top-level package/tier** — one read-only agent per tier — so each agent maps one slice's outgoing imports and internal shape.

## 2. Dimensions (findings-matrix columns)

- **Layering / dependency-rule conformance** — every import that crosses a tier boundary the wrong way (a lower tier importing a higher one), or an edge the documented rules forbid. This is the highest-value axis when the project documents its layers.
- **Cycles** — import cycles between modules or packages (they defeat isolation and make the graph un-orderable).
- **Coupling & cohesion** — modules with too many afferent/efferent dependencies (a hub everything imports, or a module that reaches into everything); modules whose contents don't belong together (grab-bag `utils`).
- **Complexity** — functions/modules with high cyclomatic complexity or deep nesting that resist understanding and testing.
- **Dead code** — unused modules, functions, classes, or exports reachable from nothing.
- **File / module size** — files grown past the point of holding in context at once (the contributor guide may state a norm; otherwise flag outliers relative to the repo).

## 3. Evidence sources & tooling

**Detect** what the project already has (check `pyproject.toml` / config): a layering enforcer (`import-linter` / `tach`), a graph tool (`pydeps` / `grimp`), a complexity linter (`ruff` `C901` / `radon` / `xenon`), a dead-code finder (`vulture`), and an import-hygiene tool (`deptry`). Prefer a tool the project already runs; fall back otherwise. Instruct subagents: never pass `#`-comment lines to Bash.

Run in the parallel evidence pass:
- **Layering:** `import-linter` if a `.importlinter` contract exists, or `tach`. If neither, build the ground-truth edge set yourself — parse each module's `import` / `from ... import` statements (`grimp`, or an AST/`ast`-based walk, or a scoped grep) and check every cross-tier edge against the §1 rules. Record the offending `file:line` for each violation.
- **Cycles:** `import-linter`'s cycle contract, `pydeps --show-cycles`, or `grimp`'s cycle detection on the built graph.
- **Coupling:** compute afferent/efferent counts per module from the same edge set; flag the top hubs. `pydeps` gives a visual; the counts are the evidence.
- **Complexity:** `ruff check --select C901` (needs `mccabe` max-complexity set) or `radon cc` / `xenon`. Capture the metric per function.
- **Dead code:** `vulture` (note its confidence score — it has false positives on framework hooks, dynamic dispatch, and re-exports; verify before deleting).
- **Size:** line counts per file; flag outliers and anything over a documented norm.

Read the contributor guide's architecture section and any existing layering config as the rule source. Record the exact metric or `file:line` as the evidence pointer for every row.

## 4. Status scale + severity rubric

Status per row: **ok / warn / violation** (for a documented rule: conforms / borderline / violates).

- **Critical** — an import that violates a documented dependency rule (e.g. a lower tier importing a higher one), or an import cycle across package boundaries. These break the architecture the team committed to.
- **Important** — a god-module with runaway coupling that blocks safe change; a function whose complexity makes it untestable; a cycle within a package; a clearly dead public module.
- **Minor** — an oversized-but-cohesive file, a moderately complex function, a low-confidence dead-code hit, a grab-bag `utils` that should be split.

Suppressions (an intentionally allowed edge, a framework hook `vulture` can't see) must be explicit and recorded with a reason — never silently dropped.

## 5. Fix patterns (and CI implications)

Structural fixes **touch code** (moving code between modules, inverting a dependency, splitting a file, deleting dead code), so they are **not** docs-only: the domain gate is "imports resolve, the type checker passes, **and** the test suite passes" — run the normal install + lint/typecheck/test CI, and the code-review gate.
- **Invert or cut an illegal edge:** move the shared type down to a lower tier both sides may import, introduce an interface/protocol the lower tier defines and the higher tier implements, or relocate the misplaced module. Re-run the layering check to green.
- **Break a cycle:** extract the shared piece into a new lower module, or convert an import-time dependency into a lazy/local import only when extraction genuinely doesn't fit (note the trade-off).
- **Split a god-module / oversized file** along its cohesion seams (files that change together stay together); update all importers in the same change, and drop back-compat re-export shims unless the project maintains a public API.
- **Delete dead code** only after verifying it is truly unreachable (not a plugin entry point, dynamic import, or re-export).
- **Highest-leverage fix:** add a layering contract (`import-linter` / `tach`) and wire it into CI so the violation can't silently recur.
- Docs-only output: the findings report and any architecture-diagram update.

## 6. Review dimensions (Phase-5 specialized reviewers)

- **Layering correctness** — is each flagged edge genuinely a violation of the documented (or confirmed) rules, and does each fix actually remove the edge rather than hide it (e.g. a lazy import that still couples the tiers)?
- **No behavior change** — a structural refactor must be behavior-preserving; the moved/split code does the same thing, and tests still pass.
- **Graph correctness** — direct vs transitive coupling attributed correctly; a cycle "fix" doesn't just relocate the cycle.
- **Dead-code safety** — deleted code really was unreachable (checked against entry points, dynamic dispatch, plugin registries, re-exports), not a false positive.
- **No regression** — imports resolve, type check clean, tests pass after every move/split/deletion.

## 7. Opt-in sub-audits

- **Layering-contract bootstrap** — generate an `import-linter` / `tach` config that encodes the confirmed rules, as a deliverable — enable via argument or ask the user.
- **Full complexity/coupling metric report** (whole tree, not just outliers) with a dependency graph render — ask the user; default off for a quick pass.
