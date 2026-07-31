---
id: arch/dead-code
domain: arch
locality: local
handbook:
  - codebase-structure/watch-for-structural-decay-beyond-layering
tooling:
  python: [vulture]
  typescript: [knip, ts-prune]
---

# Dead code

Unused modules, functions, classes, or exports reachable from nothing.

## Severity

**Important** - a clearly dead public module.

**Minor** - a low-confidence dead-code hit - real but low-cost, fix when touching the area.

## Tooling fallback

**Python** - `vulture` (note its confidence score - it has false positives on framework hooks, dynamic dispatch, and re-exports; verify before deleting).

**TypeScript** - `knip` for unused files, exports and dependencies, or `ts-prune` on older setups (same caveat - verify each hit against framework hooks, dynamic dispatch, and re-exports before deleting).

## Fix

Delete dead code only after verifying it is truly unreachable (not a plugin entry point, dynamic import, or re-export).

## Review lens

Deleted code really was unreachable (checked against entry points, dynamic dispatch, plugin registries, re-exports), not a false positive.
