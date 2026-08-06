---
id: arch/hidden-coupling
domain: arch
locality: global
handbook: []
handbook_note: >-
  Deliberately beyond the handbook: the structural-decay section lists five
  decay signals, none of them coupling that never reaches the import graph at
  all, which is what this check exists for. The matrix records the addition in
  the note on codebase-structure/watch-for-structural-decay-beyond-layering.
tooling:
  python: [grimp]
  typescript: [eslint, knip]
needs:
  target-execution: [eslint, knip]
ungranted_note: >-
  The tells this check looks for are patterns in source, and the TypeScript half lists
  the same ones the Python half greps for: mutable module-level exports, string-keyed
  container lookups, side-effectful top-level code, and dynamic `import()`. Reading
  TypeScript source for them needs nothing installed. What a withheld grant costs is
  `knip`'s usage analysis: its issue types stop at whether an export is referenced
  anywhere at all (unused exports) and whether the same binding is exported more than
  once (duplicate exports) - not at who writes to it once imported, since an ESM import
  binding is read-only and knip has no "written from another module" signal to report.
  What it adds here is confirming that a flagged mutable export actually crosses a
  module boundary (is used elsewhere) rather than sitting unused - so the single-module
  tells survive and that cross-module usage confirmation does not.
---

# Hidden coupling / implicit dependencies

Coupling that does **not** travel through an `import`, so the import graph (the evidence source every other structural check rests on) silently misses it. Two modules can be tightly coupled with zero import edges between them: shared **module-level mutable global state** or a singleton both read and write, a **service-locator / registry** lookup by string (`get_thing("name")`) that hides who depends on whom, **import-time side effects** (a module that on import mutates a global registry, opens a connection, or monkeypatches), and **dynamic imports** / runtime monkeypatching. This check exists because the skill's own method has a blind spot - an unreported hidden edge is a false *negative*, which is worse than a false positive.

## Severity

**Critical** - A **hidden dependency that masks a documented layering violation** - a lower tier reaching a higher one through shared global state or a service locator, invisible to the import check - is equally Critical, and arguably worse because it evades the enforcement.

**Important** - **hidden coupling through shared mutable state or an import-time side effect** that creates an implicit ordering/initialisation dependency between modules a reader can't see from the imports.

## Tooling fallback

**Python** - the import graph won't show this, so grep the AST for the tells and read each hit. Flag **module-level mutable globals** and `global` statements written from more than one module; **singleton** patterns (a module-level instance others import and mutate); **service-locator / registry** lookups by string key (`get(...)`, `resolve(...)`, `registry["..."]`) that stand in for an explicit dependency; **import-time side effects** (top-level code with I/O, network, registration, or monkeypatching - anything beyond definitions and cheap constants); and **dynamic imports** (`importlib`, in-function `import`) and runtime monkeypatching. Record the `file:line` of the shared state / lookup / side effect, and name the two modules it couples. A finding needs a **read** confirming the modules genuinely depend on each other through it (a module-level constant or a logger is not hidden coupling) - the pattern is the trigger, the coupling is the finding.

**TypeScript** - the same tells, from ESLint's AST and `knip`'s export graph rather than the import graph: mutable module-level exports and exported singletons more than one module writes; string-keyed container / service-locator lookups; side-effectful top-level code and side-effect-only imports; and dynamic `import()` or runtime patching. Record the `file:line` of the shared state / lookup / side effect, and name the two modules it couples. The same read requirement applies - the pattern is the trigger, the coupling is the finding. Both tools need the tree to run at all, but not the same way: ESLint's flat config imports its plugins from the target's own `node_modules` and aborts with `ERR_MODULE_NOT_FOUND` without them, while `knip` degrades quietly - on an uninstalled tree it reports genuine source and imported packages as unused rather than refusing, so a clean `knip` run over an unresolved tree is not evidence of anything.

## Fix

Make a hidden dependency explicit: replace a reach-through-global or service-locator lookup with an injected dependency (pass it as an argument / constructor parameter), so the edge shows up in the import graph and the layering check can see it; move genuinely shared state into an explicit module both sides import; move import-time side effects into an explicit initialisation call so import order stops being a hidden contract. If the hidden edge was masking a layering violation, fixing it may *surface* a Critical - that is the point, resolve it like any other illegal edge.

## Review lens

**Hidden-coupling-fix adequacy** - a hidden-coupling fix turned the implicit dependency into an explicit, import-graph-visible one (injected/imported), rather than swapping one invisible channel for another; and any layering violation it surfaced was resolved, not re-buried.
