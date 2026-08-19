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
routes:
  - lang: python
    kind: subject
    tool: grimp
    note: >-
      The import graph won't show this. Coupling that never travels through an
      `import` is what this check exists for, so a clean graph from the tool
      that builds it is not evidence about this check at all - an unreported
      hidden edge is a false negative, which is worse than a false positive.
      The graph is the blind spot, not the lens, which is the definition of a
      subject rather than an instrument, and is why this record's kind differs
      from the `library` its siblings give the same tool: they compute over the
      graph `grimp` builds and it is their evidence, while here it is the one
      place the coupling this check looks for is guaranteed not to appear.
      Nothing to pair it with, either - `alone_insufficient` would say a clean
      result needs supplementing, and a subject route contributes no result to
      supplement.
  - lang: python
    kind: procedure
    note: >-
      Grep the AST for the tells and read each hit. Flag module-level mutable
      globals and `global` statements written from more than one module;
      singleton patterns (a module-level instance others import and mutate);
      service-locator / registry lookups by string key (`get(...)`,
      `resolve(...)`, `registry["..."]`) that stand in for an explicit
      dependency; import-time side effects (top-level code with I/O, network,
      registration, or monkeypatching - anything beyond definitions and cheap
      constants); and dynamic imports (`importlib`, in-function `import`) and
      runtime monkeypatching. Record the `file:line` of the shared state /
      lookup / side effect, and name the two modules it couples. These are
      patterns in source, so the pass needs nothing installed.
    alone_insufficient: >-
      A finding needs a read confirming the modules genuinely depend on each
      other through the hit - a module-level constant or a logger is not hidden
      coupling. The pattern is the trigger, the coupling is the finding.
  - lang: typescript
    kind: procedure
    tool: eslint
    needs: target-execution
    note: >-
      The same tells from ESLint's AST rather than the import graph. The record
      names the tool and prescribes no command line for it, so there is no argv
      to declare and a `kind: command` route would have to invent one. The tier
      is the target's own tree: ESLint's flat config imports its plugins from
      the target's own `node_modules` and aborts with `ERR_MODULE_NOT_FOUND`
      without them.
  - lang: typescript
    kind: procedure
    tool: knip
    needs: target-execution
    note: >-
      What knip adds is whether a flagged mutable export is referenced from
      another module at all, which is what makes it cross-module coupling
      rather than an unused binding. Its issue types stop at usage and
      duplication and never report who writes to a binding, since an ESM import
      binding is read-only. The record names the tool and prescribes no command
      line for it. The tier is the target's own tree, and knip degrades quietly
      rather than refusing: on an uninstalled tree it reports genuine source and
      imported packages as unused, so a clean knip run over an unresolved tree
      is not evidence of anything.
  - lang: typescript
    kind: procedure
    note: >-
      The tells are patterns in source and the TypeScript half lists the same
      ones the Python half greps for: mutable module-level exports and exported
      singletons more than one module writes, string-keyed container /
      service-locator lookups, side-effectful top-level code and side-effect-only
      imports, and dynamic `import()` or runtime patching. Reading TypeScript
      source for them needs nothing installed, so the single-module tells survive
      a withheld grant; what the grant costs is the cross-module usage
      confirmation above. Record the `file:line` of the shared state / lookup /
      side effect, and name the two modules it couples.
    alone_insufficient: >-
      The same read requirement as the Python pass - the pattern is the trigger,
      the coupling is the finding.
---

# Hidden coupling / implicit dependencies

Coupling that does **not** travel through an `import`, so the import graph (the evidence source every other structural check rests on) silently misses it. Two modules can be tightly coupled with zero import edges between them: shared **module-level mutable global state** or a singleton both read and write, a **service-locator / registry** lookup by string (`get_thing("name")`) that hides who depends on whom, **import-time side effects** (a module that on import mutates a global registry, opens a connection, or monkeypatches), and **dynamic imports** / runtime monkeypatching. This check exists because the skill's own method has a blind spot - an unreported hidden edge is a false *negative*, which is worse than a false positive.

## Severity

**Critical** - A **hidden dependency that masks a documented layering violation** - a lower tier reaching a higher one through shared global state or a service locator, invisible to the import check - is equally Critical, and arguably worse because it evades the enforcement.

**Important** - **hidden coupling through shared mutable state or an import-time side effect** that creates an implicit ordering/initialisation dependency between modules a reader can't see from the imports.

## Fix

Make a hidden dependency explicit: replace a reach-through-global or service-locator lookup with an injected dependency (pass it as an argument / constructor parameter), so the edge shows up in the import graph and the layering check can see it; move genuinely shared state into an explicit module both sides import; move import-time side effects into an explicit initialisation call so import order stops being a hidden contract. If the hidden edge was masking a layering violation, fixing it may *surface* a Critical - that is the point, resolve it like any other illegal edge.

## Review lens

**Hidden-coupling-fix adequacy** - a hidden-coupling fix turned the implicit dependency into an explicit, import-graph-visible one (injected/imported), rather than swapping one invisible channel for another; and any layering violation it surfaced was resolved, not re-buried.
