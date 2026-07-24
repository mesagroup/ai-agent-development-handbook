---
name: arch-audit
description: "Audit a Python project's structure: layering / dependency-rule conformance (no illegal cross-tier imports, no cycles), module cohesion and coupling, per-module complexity, dead code, oversized files, and over-abstraction / speculative generality (single-implementer interfaces, one-caller wrappers, one-case registries, back-compat shims). Use when a codebase has grown organically and the boundaries have blurred, before a refactor, when import cycles or god-modules are suspected, when the structure feels heavier than the problem, or when the user asks to audit architecture / structure / layering. Works on any Python project. Runs on the audit-core engine."
---

# Architecture Audit (structure, layering, coupling)

A domain specialization of **[audit-core](../audit-core/SKILL.md)** — read that first; it owns the loop (scope → parallel evidence → findings matrix → plan → subagent-driven fixes → review → PR) and the cross-cutting rules. This skill supplies the structural lens.

**Core principle:** a well-structured codebase has boundaries a reader can name and the import graph actually respects, and no more structure than the problem needs. The audit measures the distance between the *declared* architecture (the layering the contributor guide describes) and the *real* one (what the imports do), and surfaces the modules that have drifted, tangled, or grown past the point of being understandable in one sitting — and, in the other direction, the abstractions that cost a reader more than they earn.

**Announce:** "I'm using the arch-audit skill (on the audit-core engine) to audit the project structure."

**Bash rule:** never pass a line starting with `#` to the Bash tool (you or any subagent).

## When to use

- A package tree grew organically and no one is sure the layering still holds (a low tier importing a high one, a service reaching into an agent).
- Import cycles are suspected, or a refactor keeps rippling further than expected (a sign of high coupling).
- A few modules have become god-files that everything depends on and nothing can be changed safely.
- The structure feels heavier than the problem — layers, interfaces, or a plugin/registry mechanism that each call threads through to reach a single implementation.
- The user asks to audit architecture, structure, layering, coupling, dead code, or over-engineering.

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
- **Over-abstraction / speculative generality** — structure that exceeds the problem it solves: an interface/ABC/protocol with a single implementer, an indirection layer (wrapper module, forwarding function, adapter) with a single caller that only delegates, a registry/plugin/config-dispatch mechanism with one registrant, a generic/type-parameter only ever bound to one type, a deep inheritance chain with one leaf, or **unexercised configurability** — a parameter, flag, or config option that takes exactly one value across every call site (a knob no caller turns). This is the residue of a **YAGNI** violation ("You Aren't Gonna Need It"): generality built for an anticipated second use that never arrived. You can't apply YAGNI to code that already exists, but you can find where it was ignored — the tell is that the anticipated variation never materialised (a second implementer, a second caller, a second config value). In a project whose contributor guide forbids them, **back-compat re-export shims and compatibility wrappers** are violations of this axis, not neutral. This is the inverse of the coupling/complexity axes: the code is individually simple and "clean", which is why complexity linters sail past it — the cost is the reader tracing N hops that collapse to one.

## 3. Evidence sources & tooling

**Detect** what the project already has (check `pyproject.toml` / config): a layering enforcer (`import-linter` / `tach`), a graph tool (`pydeps` / `grimp`), a complexity linter (`ruff` `C901` / `radon` / `xenon`), a dead-code finder (`vulture`), and an import-hygiene tool (`deptry`). Prefer a tool the project already runs; fall back otherwise. Instruct subagents: never pass `#`-comment lines to Bash.

Run in the parallel evidence pass:
- **Layering:** `import-linter` if a `.importlinter` contract exists, or `tach`. If neither, build the ground-truth edge set yourself — parse each module's `import` / `from ... import` statements (`grimp`, or an AST/`ast`-based walk, or a scoped grep) and check every cross-tier edge against the §1 rules. Record the offending `file:line` for each violation.
- **Cycles:** `import-linter`'s cycle contract, `pydeps --show-cycles`, or `grimp`'s cycle detection on the built graph.
- **Coupling:** compute afferent/efferent counts per module from the same edge set; flag the top hubs. `pydeps` gives a visual; the counts are the evidence.
- **Complexity:** `ruff check --select C901` (needs `mccabe` max-complexity set) or `radon cc` / `xenon`. Capture the metric per function.
- **Dead code:** `vulture` (note its confidence score — it has false positives on framework hooks, dynamic dispatch, and re-exports; verify before deleting).
- **Size:** line counts per file; flag outliers and anything over a documented norm.
- **Over-abstraction:** the signal is *fan-in to an abstraction*, computed from the same edge/AST set built for layering. For each `ABC`/`Protocol`/class with `@abstractmethod`, count concrete subclasses across the tree; **one** (or zero) is the trigger. For each single-function module or one-method wrapper class, count call sites (`grimp` refs or a scoped grep); **one** is the trigger. For each registry / entry-point / `match`-dispatch, count registrants/arms; **one** is the trigger. For each function parameter, feature flag, or settings field, count the **distinct values** bound across all call sites (AST of the call arguments, or a grep of the setter); a single value everywhere is the trigger — the knob is unexercised (YAGNI residue). Grep the project's forbidden-shim markers (`backward compat`, `deprecated`, `re-export`, a function body that is a single call to a renamed symbol) against the contributor guide's stated policy. **Record the count and the `file:line` of both the abstraction and its lone consumer** — the count is the evidence, but a row only becomes a finding after a read confirms (a) no second consumer or second value is imminent in-tree and (b) collapsing the construct (inlining the abstraction, dropping the knob) removes indirection without losing a genuine seam. A planned, documented extension point — one implementer, or one config value, *today* — is a suppression, not a finding, recorded with its reason.

Read the contributor guide's architecture section and any existing layering config as the rule source. Record the exact metric or `file:line` as the evidence pointer for every row.

## 4. Status scale + severity rubric

Status per row: **ok / warn / violation** (for a documented rule: conforms / borderline / violates).

- **Critical** — an import that violates a documented dependency rule (e.g. a lower tier importing a higher one), or an import cycle across package boundaries. These break the architecture the team committed to. Over-abstraction reaches Critical **only** when the contributor guide explicitly bans the construct (e.g. a back-compat shim in a stated no-shim project) — then it is a documented-rule violation like any other; over-abstraction is otherwise a tax on the architecture, not a break in it.
- **Important** — a god-module with runaway coupling that blocks safe change; a function whose complexity makes it untestable; a cycle within a package; a clearly dead public module; a registry / plugin / config-dispatch mechanism serving a single case, or a multi-module indirection layer every call threads through to reach one implementation, where the machinery actively blocks a reader from following the call path.
- **Minor** — an oversized-but-cohesive file, a moderately complex function, a low-confidence dead-code hit, a grab-bag `utils` that should be split; a single-implementer interface/ABC, a one-caller forwarding wrapper, an unused generic parameter, or an unexercised knob (a parameter/flag/config option with one value everywhere) — real but low-cost, fix when touching the area.

Suppressions (an intentionally allowed edge, a framework hook `vulture` can't see) must be explicit and recorded with a reason — never silently dropped.

## 5. Fix patterns (and CI implications)

Structural fixes **touch code** (moving code between modules, inverting a dependency, splitting a file, deleting dead code), so they are **not** docs-only: the domain gate is "imports resolve, the type checker passes, **and** the test suite passes" — run the normal install + lint/typecheck/test CI, and the code-review gate.
- **Invert or cut an illegal edge:** move the shared type down to a lower tier both sides may import, introduce an interface/protocol the lower tier defines and the higher tier implements, or relocate the misplaced module. Re-run the layering check to green.
- **Break a cycle:** extract the shared piece into a new lower module, or convert an import-time dependency into a lazy/local import only when extraction genuinely doesn't fit (note the trade-off).
- **Split a god-module / oversized file** along its cohesion seams (files that change together stay together); update all importers in the same change, and drop back-compat re-export shims unless the project maintains a public API.
- **Delete dead code** only after verifying it is truly unreachable (not a plugin entry point, dynamic import, or re-export).
- **Collapse an over-abstraction:** inline the single-implementer interface into its one implementer, replace a one-caller forwarding wrapper with a direct call, drop a one-entry registry for a direct reference, remove an unexercised knob (delete the parameter/flag and inline its single value), delete a back-compat shim and update its callers in the same change (per a no-shim project rule). This is a behavior-preserving refactor — same domain gate as the other structural fixes (tests + typecheck green). Do **not** collapse a seam that has a second consumer imminent or that isolates a genuinely volatile boundary; note it as an intentional extension point instead.
- **Highest-leverage fix:** add a layering contract (`import-linter` / `tach`) and wire it into CI so the violation can't silently recur.
- Docs-only output: the findings report and any architecture-diagram update.

## 6. Review dimensions (Phase-5 specialized reviewers)

- **Layering correctness** — is each flagged edge genuinely a violation of the documented (or confirmed) rules, and does each fix actually remove the edge rather than hide it (e.g. a lazy import that still couples the tiers)?
- **No behavior change** — a structural refactor must be behavior-preserving; the moved/split code does the same thing, and tests still pass.
- **Graph correctness** — direct vs transitive coupling attributed correctly; a cycle "fix" doesn't just relocate the cycle.
- **Dead-code safety** — deleted code really was unreachable (checked against entry points, dynamic dispatch, plugin registries, re-exports), not a false positive.
- **No regression** — imports resolve, type check clean, tests pass after every move/split/deletion.
- **Abstraction earns its keep** — for each collapsed indirection, confirm the removed layer had no second consumer and no volatile-boundary role (i.e. the fix didn't delete a legitimate seam just to satisfy a count), and that inlining genuinely shortened the call path a reader must trace.

## 7. Opt-in sub-audits

- **Layering-contract bootstrap** — generate an `import-linter` / `tach` config that encodes the confirmed rules, as a deliverable — enable via argument or ask the user.
- **Full complexity/coupling metric report** (whole tree, not just outliers) with a dependency graph render — ask the user; default off for a quick pass.
