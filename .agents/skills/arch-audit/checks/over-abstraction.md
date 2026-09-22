---
id: arch/over-abstraction
domain: arch
locality: global
evidence: >-
  Every count this check takes is read against the same trigger: one
  concrete subclass, one call site, one registrant or arm, one distinct
  bound value - or zero - is the trigger, and more than one is not. Record
  the count and the `file:line` of both the abstraction and its lone
  consumer. The shim axis is the other half of this check's evidence, and it
  is not a count: the forbidden-shim marker hit with its `file:line`, beside
  the contributor guide's stated policy, read by the Python procedure route
  below. The shim axis is read per partition and each hit is carried on the
  row of the scope that owns its module, so every scope row names both axes.
  TypeScript declares no shim axis, so a TypeScript row is the counts' status,
  with its evidence stating that the shim policy was not read there.
handbook:
  - implementation-disciplines/coding-hygiene-rules-that-surface-at-review-b
  - codebase-structure/why-the-rule-matters-a
routes:
  - lang: python
    kind: library
    answers: fan-in
    tool: grimp
    note: >-
      The fan-in-to-abstraction signal - subclasses per abstraction, call
      sites per single-function module or one-method wrapper class,
      registrants or `match` arms per registry / entry point /
      `match`-dispatch, and distinct values bound per
      parameter/flag/config field - is computed from the same edge/AST set built for layering. An
      abstraction is an `ABC` base, a `Protocol` base, or any class carrying
      `@abstractmethod`, and the subclass count is of concrete subclasses
      across the tree; `grimp` refs, counted from the built graph rather
      than from a command run for this check specifically, or a scoped grep,
      source the call-site count for a single-function module or one-method
      wrapper class. The AST of the call arguments, or a grep of the setter
      where the value is assigned rather than passed, sources the
      distinct-values count, which is of the values bound across all of a
      parameter's, flag's or config field's call sites rather than at any
      one of them.
    alone_insufficient: >-
      The count is the evidence, but "a row only becomes a finding after a
      read confirms (a) no second consumer or second value is imminent
      in-tree and (b) collapsing the construct (inlining the abstraction,
      dropping the knob) removes indirection without losing a genuine
      seam." "A planned, documented extension point - one implementer, or
      one config value, today - is a suppression, not a finding, recorded
      with its reason."
  - lang: python
    kind: procedure
    answers: shims
    note: >-
      Grep the project's forbidden-shim markers (`backward compat`,
      `deprecated`, `re-export`, a function body that is a single call to a
      renamed symbol) against the contributor guide's stated policy.
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
    alone_insufficient: >-
      The record has this route "apply the same read confirmation and
      suppression rule" as the Python fan-in counts "before a count becomes
      a finding": a row only becomes a finding after a read confirms no
      second consumer or second value is imminent in-tree and that
      collapsing the construct removes indirection without losing a genuine
      seam. A planned, documented extension point is a suppression, not a
      finding, recorded with its reason.
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
      one-shot fetch. The counts this produced on the target it was first
      run against are recorded in [the smoke
      run](https://github.com/mesagroup/ai-agent-development-handbook/blob/main/docs/audit/typescript-lens-smoke-run.md).
    alone_insufficient: >-
      The same "read confirmation and suppression rule" the record applies
      to the Python fan-in counts: a row only becomes a finding after a
      read confirms no second consumer or second value is imminent in-tree
      and that collapsing the construct removes indirection without losing
      a genuine seam. A planned, documented extension point is a
      suppression, not a finding, recorded with its reason.
---

# Over-abstraction / speculative generality

Structure that exceeds the problem it solves: an interface/ABC/protocol with a single implementer, an indirection layer (wrapper module, forwarding function, adapter) with a single caller that only delegates, a registry/plugin/config-dispatch mechanism with one registrant, a generic/type-parameter only ever bound to one type, a deep inheritance chain with one leaf, or **unexercised configurability** - a parameter, flag, or config option that takes exactly one value across every call site (a knob no caller turns). This is the residue of a **YAGNI** violation ("You Aren't Gonna Need It"): generality built for an anticipated second use that never arrived. You can't apply YAGNI to code that already exists, but you can find where it was ignored - the tell is that the anticipated variation never materialised (a second implementer, a second caller, a second config value). In a project whose contributor guide forbids them, **back-compat re-export shims and compatibility wrappers** are violations of this axis, not neutral. This is the inverse of the coupling/complexity axes: the code is individually simple and "clean", which is why complexity linters sail past it - the cost is the reader tracing N hops that collapse to one.

## Severity

**Critical** - Over-abstraction reaches Critical **only** when the contributor guide explicitly bans the construct (e.g. a back-compat shim in a stated no-shim project) - then it is a documented-rule violation like any other; over-abstraction is otherwise a tax on the architecture, not a break in it.

**Important** - a registry / plugin / config-dispatch mechanism serving a single case, or a multi-module indirection layer every call threads through to reach one implementation, where the machinery actively blocks a reader from following the call path.

**Minor** - a single-implementer interface/ABC, a one-caller forwarding wrapper, an unused generic parameter, an unexercised knob (a parameter/flag/config option with one value everywhere) - real but low-cost, fix when touching the area.

## Fix

Collapse an over-abstraction: inline the single-implementer interface into its one implementer, replace a one-caller forwarding wrapper with a direct call, drop a one-entry registry for a direct reference, remove an unexercised knob (delete the parameter/flag and inline its single value), delete a back-compat shim and update its callers in the same change (per a no-shim project rule). This is a behavior-preserving refactor - same domain gate as the other structural fixes (tests + typecheck green). Do **not** collapse a seam that has a second consumer imminent or that isolates a genuinely volatile boundary; note it as an intentional extension point instead.

## Review lens

**Abstraction-removal adequacy** - for each collapsed indirection, confirm the removed layer had no second consumer and no volatile-boundary role (i.e. the fix didn't delete a legitimate seam just to satisfy a count), and that inlining genuinely shortened the call path a reader must trace.
