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
    note: >-
      The same tells from ESLint's AST rather than the import graph, under a
      flat config the audit supplies rather than the target's. Core
      `no-restricted-syntax` takes AST selectors and needs no plugin and no type
      information, so pointed at an audit-owned flat config with `--config` and
      `--no-config-lookup` it reads the target's source with no `node_modules`
      in the target at all. One selector per tell, each reporting its own
      message. A mutable module-level export takes two, because the binding
      and the value are different things:
      `ExportNamedDeclaration > VariableDeclaration[kind!='const']` for a
      rebindable export, and
      `ExportNamedDeclaration > VariableDeclaration > VariableDeclarator:matches([init.type='ObjectExpression'],[init.type='ArrayExpression'],[init.type='NewExpression'],[init.expression.type='ObjectExpression'],[init.expression.type='ArrayExpression'],[init.expression.type='NewExpression'])`
      for an exported singleton or container - `export const` of an object, an
      array or a `new` instance. The second is the one that matters more here
      and the first alone would miss it: an ESM import binding is read-only, as
      the `knip` route below says, so another module cannot reassign an
      `export let` and couples by mutating the exported value instead. Its
      `init.expression` half is why it is six clauses rather than three: a
      TypeScript `as` or `satisfies` wrapper makes the initialiser a
      `TSAsExpression` or `TSSatisfiesExpression` holding the literal, so
      `{} as Registry` - the typed empty registry this check exists for, with
      whatever type the target spells there - reads as neither an object nor an
      array to a selector matching `init.type` alone. The example is written
      without its type arguments on purpose: a generic in a backtick span is a
      `<` glued to a name, which this family's form extractor reads as a
      placeholder and refuses. Then
      `ImportDeclaration[specifiers.length=0]`
      for a side-effect-only import, `ImportExpression` for a dynamic import,
      `MemberExpression[computed=true][property.type='Literal'][property.raw=/^["']/]`
      for a string-keyed lookup, and
      `Program > ExpressionStatement > CallExpression` for a top-level side
      effect. The `property.raw` test is what keeps the string-key selector to
      string keys: a `Literal` property also covers `arr[0]` and `arr[true]`,
      so without it ordinary index access reports as a service-locator lookup
      and the reading pass drowns in hits the tell does not describe. Matching
      the raw source rather than the value is what distinguishes them, since
      the quote is in the source text and not in the parsed value. The record names the rule and its selectors
      and prescribes no command line, and `--config` takes a config path the
      record names no value for, so there is no argv to declare and a
      `kind: command` route would have to invent one. Install ESLint and the
      TypeScript parser into an audit-owned directory and keep that config in
      it: without the parser ESLint reports `Parsing error: Unexpected token :`
      on a TypeScript file rather than any rule result, and a parser handed to a
      one-shot runner instead is not resolvable from a config living outside the
      runner's sandbox. What the install needs is network rather than the
      target's tree, which is why this route carries no tier and survives a
      withheld grant.
    alone_insufficient: >-
      Every selector here is a single-file pattern, and no ESLint invocation
      changes that: a linter reads one file's AST at a time and cross-file
      understanding is a type checker's, which is why the cross-module half of
      this check belongs to the `knip` route below and to the reading pass, not
      to a better rule set. So a hit says a tell is present in one module and
      never says a second module shares it, which is the finding. **The
      selector list is a floor and not the definition of the tells**, which the
      tool-less TypeScript route states in prose and keeps as the authority: a
      fixed set of AST patterns misses whatever spelling it was not written
      against, and this one has already been widened twice for a form it did
      not anticipate - a numeric index reading as a string key, and a mutable
      value behind a `const` binding or behind a type assertion. Widen it for
      the dialect in front of you rather than reading a clean ESLint run as an
      answer, and treat a partition whose source style these selectors were not
      written against as unmeasured on this axis rather than clean.
  - lang: typescript
    kind: procedure
    tool: eslint
    needs: target-execution
    note: >-
      The same tells run under the target's own flat config, which is what the
      grant buys: the project's own configured rules and plugins, including any
      it already has for these patterns, and its parser settings rather than the
      audit's. That config loads its plugins from the target's own
      `node_modules`, and without it ESLint aborts with `ERR_MODULE_NOT_FOUND`
      rather than reporting anything. It is the same tool as the route above and
      a different invocation mode, which is the whole distinction between them;
      the schema carries the two tiers and the two notes, and nothing
      machine-readable tells the modes apart. What the grant does not buy is the
      cross-module confirmation - that is not a configuration question, and the
      route above says why.
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
      source for them needs nothing installed, so the tells survive a withheld
      grant, and so does the cross-module confirmation when it is done by
      reading: follow the flagged binding into the modules that import it and
      read whether a second one writes to or resolves through it. What the
      grant buys is `knip`'s tool-backed form of that same confirmation, as the
      `knip` route says, not the confirmation itself. Record the `file:line` of
      the shared state / lookup / side effect, and name the two modules it
      couples.
    alone_insufficient: >-
      A hit says a tell is present in one module. The finding is that a second
      module shares it, which this read confirms by reading the importing
      modules, or `knip` confirms by tool under its grant, on the same split
      the `eslint` route's `alone_insufficient` states. A tell confirmed in one
      module only is reported as a tell, not as coupling: the pattern is the
      trigger, the coupling is the finding.
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
