---
id: arch/dead-code
domain: arch
locality: local
handbook:
  - codebase-structure/watch-for-structural-decay-beyond-layering
routes:
  - lang: python
    kind: command
    tool: vulture
    argv: [vulture]
    note: >-
      The record names the tool and no arguments; the paths to scan are an
      operand it names none for. Note the confidence score it reports - it has
      false positives on framework hooks, dynamic dispatch and re-exports, so
      verify each hit against a real reference before deleting.
  - lang: typescript
    kind: procedure
    tool: knip
    needs: target-execution
    note: >-
      Unused files, exports and dependencies. The record names the tool and
      prescribes no command line for it, so there is no argv to declare and a
      `kind: command` route would have to invent one. The tier is the target's
      own tree: knip loads and runs the target's own tool configuration to see
      what is actually exported, so an uninstalled tree does not just limit it
      - it reports genuinely-used source files and imported packages alike as
      unused, a wrong answer at exit 0 that looks exactly like a clean hit
      list.
  - lang: typescript
    kind: procedure
    tool: ts-prune
    note: >-
      The older-setup option, and the safer fallback where the tree is not
      resolved: it needs no install. The record names the tool and prescribes
      no command line for it, so there is no argv to declare. It is not a
      syntax-level pass - it finds references through the TypeScript language
      service, so on an unresolved tree an import it cannot resolve stops
      counting as a reference and the export it pointed at is listed as
      unused. That is over-reporting rather than the silent under-reporting
      above - the hit list grows with resolution failures instead of a wrong
      answer looking clean - which is the safer direction for a check whose
      fix is deletion, and only on the condition that every hit is verified
      against a real reference before anything is deleted rather than read as
      a result.
  - lang: any
    kind: procedure
    note: >-
      With none of them installed, enumerate each module's public symbols and
      grep the tree for references to each; a symbol referenced nowhere
      outside the module that defines it is the candidate. The verify-before-
      deleting caveat matters more here, not less: a hand-rolled sweep sees
      neither dynamic dispatch nor entry points declared in packaging
      metadata, so check both before believing any hit.
---

# Dead code

Unused modules, functions, classes, or exports reachable from nothing.

## Severity

**Important** - a clearly dead public module.

**Minor** - a low-confidence dead-code hit - real but low-cost, fix when touching the area.

## Tooling fallback

**Python** - `vulture` (note its confidence score - it has false positives on framework hooks, dynamic dispatch, and re-exports; verify before deleting).

**TypeScript** - `knip` for unused files, exports and dependencies, or `ts-prune` on older setups (same caveat - verify each hit against framework hooks, dynamic dispatch, and re-exports before deleting). `knip` loads and runs the target's own tool configuration to see what is actually exported, so an uninstalled tree doesn't just limit it - it reports genuinely-used source files and imported packages alike as unused, a wrong answer at exit 0 that looks exactly like a clean hit list; `ts-prune` needs no install and is the safer fallback where the tree isn't resolved, but it is not a syntax-level pass: it finds references through the TypeScript language service, so on an unresolved tree an import it cannot resolve stops counting as a reference and the export it pointed at is listed as unused. That is over-reporting rather than the silent under-reporting above - the hit list grows with resolution failures instead of a wrong answer looking clean - which is the safer direction for a check whose fix is deletion, and only on the condition that every hit is verified against a real reference before anything is deleted rather than read as a result.

**With none of them installed** - enumerate each module's public symbols and grep the tree for references to each; a symbol referenced nowhere outside the module that defines it is the candidate. The caveat above matters more here, not less: a hand-rolled sweep sees neither dynamic dispatch nor entry points declared in packaging metadata, so check both before believing any hit.

## Fix

Delete dead code only after verifying it is truly unreachable (not a plugin entry point, dynamic import, or re-export).

## Review lens

**Deletion safety** - deleted code really was unreachable (checked against entry points, dynamic dispatch, plugin registries, re-exports), not a false positive.
