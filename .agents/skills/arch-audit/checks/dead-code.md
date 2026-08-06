---
id: arch/dead-code
domain: arch
locality: local
handbook:
  - codebase-structure/watch-for-structural-decay-beyond-layering
tooling:
  python: [vulture]
  typescript: [knip, ts-prune]
needs:
  target-execution: [knip]
---

# Dead code

Unused modules, functions, classes, or exports reachable from nothing.

## Severity

**Important** - a clearly dead public module.

**Minor** - a low-confidence dead-code hit - real but low-cost, fix when touching the area.

## Tooling fallback

**Python** - `vulture` (note its confidence score - it has false positives on framework hooks, dynamic dispatch, and re-exports; verify before deleting).

**TypeScript** - `knip` for unused files, exports and dependencies, or `ts-prune` on older setups (same caveat - verify each hit against framework hooks, dynamic dispatch, and re-exports before deleting). `knip` loads and runs the target's own tool configuration to see what is actually exported, so an uninstalled tree doesn't just limit it - it reports genuinely-used source files and imported packages alike as unused, a wrong answer at exit 0 that looks exactly like a clean hit list; `ts-prune` needs no install for its syntax-level pass and is the safer fallback where the tree isn't resolved.

**With none of them installed** - enumerate each module's public symbols and grep the tree for references to each; a symbol referenced nowhere outside the module that defines it is the candidate. The caveat above matters more here, not less: a hand-rolled sweep sees neither dynamic dispatch nor entry points declared in packaging metadata, so check both before believing any hit.

## Fix

Delete dead code only after verifying it is truly unreachable (not a plugin entry point, dynamic import, or re-export).

## Review lens

**Deletion safety** - deleted code really was unreachable (checked against entry points, dynamic dispatch, plugin registries, re-exports), not a false positive.
