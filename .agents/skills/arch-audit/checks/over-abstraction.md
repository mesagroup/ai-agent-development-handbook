---
id: arch/over-abstraction
domain: arch
locality: global
handbook:
  - implementation-disciplines/coding-hygiene-rules-that-surface-at-review-b
  - codebase-structure/why-the-rule-matters-a
routes:
  - lang: python
    kind: library
    tool: grimp
    note: >-
      The fan-in-to-abstraction signal - subclasses per `ABC`/`Protocol`,
      call sites per single-function module or one-method wrapper class,
      registrants per registry/dispatch, distinct values bound per
      parameter/flag/config field - is computed from the same edge/AST set
      built for layering; `grimp` refs are counted from the built graph
      rather than from a command run for this check specifically.
  - lang: typescript
    kind: procedure
    tool: knip
    needs: target-execution
    note: >-
      The record prescribes no knip command line; it reads knip's own
      report of unused files and exports and single-use exports as one of
      the two inputs to the fan-in counts. Needs the tree to be accurate,
      not merely present - on an uninstalled one it reports first-party
      files and imported packages alike as unused, inflating the
      fan-in-to-abstraction counts this check is built on.
  - lang: typescript
    kind: library
    tool: ts-morph
    note: >-
      A `ts-morph` walk of the AST counts implementers per interface or
      abstract class, call sites per wrapper module or forwarding function,
      registrants per registry or dispatch table, type arguments bound per
      generic, and distinct values bound per parameter/flag/config field.
      Needs nothing installed in the target for a syntax-level walk - it
      serves its own `lib.d.ts` from memory - but the moment it reaches
      into a dependency's own types to resolve an implementer or a bound
      generic, that resolution degrades silently without the tree, so the
      record keeps this pass syntactic rather than type-aware. `ts-morph`
      is a library rather than a bin, so a one-shot runner cannot supply it
      to a script living outside the runner's sandbox - `npx --package
      ts-morph -- <script>` aborts with `ERR_MODULE_NOT_FOUND: Cannot find
      package 'ts-morph'` - so it needs installing somewhere the walking
      script can import it from, an audit-owned directory rather than a
      one-shot fetch.
---

# Over-abstraction / speculative generality

Structure that exceeds the problem it solves: an interface/ABC/protocol with a single implementer, an indirection layer (wrapper module, forwarding function, adapter) with a single caller that only delegates, a registry/plugin/config-dispatch mechanism with one registrant, a generic/type-parameter only ever bound to one type, a deep inheritance chain with one leaf, or **unexercised configurability** - a parameter, flag, or config option that takes exactly one value across every call site (a knob no caller turns). This is the residue of a **YAGNI** violation ("You Aren't Gonna Need It"): generality built for an anticipated second use that never arrived. You can't apply YAGNI to code that already exists, but you can find where it was ignored - the tell is that the anticipated variation never materialised (a second implementer, a second caller, a second config value). In a project whose contributor guide forbids them, **back-compat re-export shims and compatibility wrappers** are violations of this axis, not neutral. This is the inverse of the coupling/complexity axes: the code is individually simple and "clean", which is why complexity linters sail past it - the cost is the reader tracing N hops that collapse to one.

## Severity

**Critical** - Over-abstraction reaches Critical **only** when the contributor guide explicitly bans the construct (e.g. a back-compat shim in a stated no-shim project) - then it is a documented-rule violation like any other; over-abstraction is otherwise a tax on the architecture, not a break in it.

**Important** - a registry / plugin / config-dispatch mechanism serving a single case, or a multi-module indirection layer every call threads through to reach one implementation, where the machinery actively blocks a reader from following the call path.

**Minor** - a single-implementer interface/ABC, a one-caller forwarding wrapper, an unused generic parameter, an unexercised knob (a parameter/flag/config option with one value everywhere) - real but low-cost, fix when touching the area.

## Tooling fallback

**Python** - the signal is *fan-in to an abstraction*, computed from the same edge/AST set built for layering. For each `ABC`/`Protocol`/class with `@abstractmethod`, count concrete subclasses across the tree; **one** (or zero) is the trigger. For each single-function module or one-method wrapper class, count call sites (`grimp` refs or a scoped grep); **one** is the trigger. For each registry / entry-point / `match`-dispatch, count registrants/arms; **one** is the trigger. For each function parameter, feature flag, or settings field, count the **distinct values** bound across all call sites (AST of the call arguments, or a grep of the setter); a single value everywhere is the trigger - the knob is unexercised (YAGNI residue). Grep the project's forbidden-shim markers (`backward compat`, `deprecated`, `re-export`, a function body that is a single call to a renamed symbol) against the contributor guide's stated policy. **Record the count and the `file:line` of both the abstraction and its lone consumer** - the count is the evidence, but a row only becomes a finding after a read confirms (a) no second consumer or second value is imminent in-tree and (b) collapsing the construct (inlining the abstraction, dropping the knob) removes indirection without losing a genuine seam. A planned, documented extension point - one implementer, or one config value, *today* - is a suppression, not a finding, recorded with its reason.

**TypeScript** - the same fan-in counts, from `knip` (unused files and exports, single-use exports) and a `ts-morph` walk of the AST: implementers per interface or abstract class, call sites per wrapper module or forwarding function, registrants per registry or dispatch table, type arguments bound per generic, and the distinct values bound to each parameter, flag, or config field across every call site. Record the count and the `file:line` of both the abstraction and its lone consumer, and apply the same read confirmation and suppression rule before a count becomes a finding. `knip` needs the tree to be accurate, not merely present - on an uninstalled one it reports first-party files and imported packages alike as unused, inflating the fan-in-to-abstraction counts this check is built on; `ts-morph` needs nothing installed *in the target* for a syntax-level walk, serving its own `lib.d.ts` from memory, but the moment it reaches into a dependency's own types to resolve an implementer or a bound generic, that resolution degrades silently without the tree, so keep this pass syntactic rather than type-aware. It does need to be installed somewhere the walking script can import it from: `ts-morph` is a library rather than a bin, so a one-shot runner cannot supply it to a script that lives outside the runner's sandbox - `npx --package ts-morph -- <script>` aborts with `ERR_MODULE_NOT_FOUND: Cannot find package 'ts-morph'`. Install it into an audit-owned directory and run the walk from there, which is how the counts on the target this was first run against were produced: 502 interfaces, 484 of them with no implementer at all, and 150 single-export modules, none of which a `knip` run without the tree could have been trusted to corroborate.

## Fix

Collapse an over-abstraction: inline the single-implementer interface into its one implementer, replace a one-caller forwarding wrapper with a direct call, drop a one-entry registry for a direct reference, remove an unexercised knob (delete the parameter/flag and inline its single value), delete a back-compat shim and update its callers in the same change (per a no-shim project rule). This is a behavior-preserving refactor - same domain gate as the other structural fixes (tests + typecheck green). Do **not** collapse a seam that has a second consumer imminent or that isolates a genuinely volatile boundary; note it as an intentional extension point instead.

## Review lens

**Abstraction-removal adequacy** - for each collapsed indirection, confirm the removed layer had no second consumer and no volatile-boundary role (i.e. the fix didn't delete a legitimate seam just to satisfy a count), and that inlining genuinely shortened the call path a reader must trace.
