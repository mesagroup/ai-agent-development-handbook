---
name: arch-audit
description: "Audit a Python project's structure: layering / dependency-rule conformance (no illegal cross-tier imports, no cycles), module cohesion and coupling (god-modules and the opposite — over-decomposition / ravioli code), per-module complexity, dead code, oversized files, over-abstraction / speculative generality (single-implementer interfaces, one-caller wrappers, one-case registries, back-compat shims), and hidden coupling that bypasses the import graph (shared global state, service locators, import-time side effects). Use when a codebase has grown organically and the boundaries have blurred, before a refactor, when import cycles or god-modules are suspected, when the structure feels heavier than the problem, or when the user asks to audit architecture / structure / layering. Works on any Python project. Runs on the audit-core engine."
---

# Architecture Audit (structure, layering, coupling)

A domain specialization of **[audit-core](../audit-core/SKILL.md)** - read that first; it owns the loop and the cross-cutting rules. The checks are records in [`checks/`](checks/) beside this file; load the ones your slice needs, not the directory.

**One pairing:** `arch/coupling` and `arch/over-decomposition` are the same granularity question in opposite directions - too coarse and too fine - so neither alone answers whether the granularity is right.

**Announce:** "I'm using the arch-audit skill (on the audit-core engine) to audit the project structure."

**Subject:** the package tree (the importable source under `src/`, the top-level package, or wherever the project keeps its code) and its import graph.

**Not for:** a single new module's design review (just review it), or a pure performance/security question (those are other lenses).

**Establish the declared architecture first**, because it is the spec every layering finding is judged against. Read the contributor guide (CLAUDE.md / AGENTS.md / CONTRIBUTING) for a stated tier/layer structure and dependency rules ("A may import B, never the reverse; no cycles"). If it states them, they are the rubric. If no rules are documented, **infer** the intended layers from the directory structure and confirm the inferred rules with the user before flagging violations - don't invent an architecture the team never agreed to.

**Build the graph once, first.** Produce the ground-truth artifact every downstream agent consumes - the import edge set plus per-module symbol/LOC counts - so agents read it rather than each re-parsing the tree and rebuilding a (possibly inconsistent) graph.

**Fan out by each check's `locality`.** One read-only agent per top-level package/tier for the `local` checks, each mapping its slice's outgoing imports and internal shape; one agent per `global` check over the whole graph artifact, because a per-tier agent sees only its slice's edges and *cannot* compute a whole-graph property. Do **not** fan a cheap local check out to its own agent - that over-fans the work and duplicates the graph build.

**Status per row:** ok / warn / violation (for a documented rule: conforms / borderline / violates). Suppressions - an intentionally allowed edge, a framework hook a dead-code tool can't see - must be explicit and recorded with a reason, never silently dropped.

**Fixes touch code**, so the domain gate is "imports resolve, the type checker passes, **and** the test suite passes" - run the normal install + lint/typecheck/test CI, and the code-review gate. Every fix in this domain is a **behavior-preserving refactor**: the moved, split, merged or deleted code does the same thing afterwards, and a review lens that says so applies to every check here whether or not the check restates it. The highest-leverage fix in this domain is a layering contract (`import-linter` / `tach`) wired into CI so the violation can't silently recur. Docs-only output: the findings report and any architecture-diagram update.

**Opt-in deliverables** (ask the user, or take from an argument; default off): a layering-contract bootstrap that encodes the confirmed rules as an `import-linter` / `tach` config, and a full complexity/coupling metric report over the whole tree with a dependency-graph render. The opt-in *check* - package stability metrics - is `arch/martin-metrics`, loaded like any other.
