---
id: arch/size
domain: arch
locality: local
handbook:
  - codebase-structure/watch-for-structural-decay-beyond-layering
routes:
  - lang: any
    kind: command
    tool: cloc
    argv: [npx, cloc]
    note: >-
      `cloc` is on the npm registry, so a one-shot runner fetches it
      whatever the partition's language.
  - lang: any
    kind: procedure
    tool: tokei
    note: >-
      `tokei` is a standalone binary in no language registry, and an audit
      environment expected to use it needs it installed in advance - the
      record prescribes no working invocation for it. `npx tokei` resolves
      an unrelated package that declares no bin and fails with `could not
      determine executable to run`, which looks like a missing tool rather
      than the wrong one, so it is not a route this record offers.
  - lang: any
    kind: command
    tool: wc
    argv: [wc, "-l"]
    applies_when: >-
      Neither `cloc` nor `tokei` is available.
    note: >-
      The record quotes this command verbatim and says it answers the
      check once neither other tool is available. The file list to run it
      over is an operand the record names none for.
---

# File / module size

Files grown past the point of holding in context at once (the contributor guide may state a norm; otherwise flag outliers relative to the repo).

## Severity

**Minor** - an oversized-but-cohesive file - real but low-cost, fix when touching the area.

## Tooling fallback

Line counts per file; flag outliers and anything over a documented norm. The two tools are not the same kind: `cloc` is on the npm registry, so a one-shot runner fetches it (`npx cloc`) whatever the partition's language, while `tokei` is a standalone binary in no language registry and an audit environment expected to use it needs it installed in advance - `npx tokei` resolves an unrelated package that declares no bin and fails with `could not determine executable to run`, which looks like a missing tool rather than the wrong one. Where neither is available, `wc -l` over the file list answers this check.

## Fix

Split an oversized file along its cohesion seams (files that change together stay together); update all importers in the same change, and drop back-compat re-export shims unless the project maintains a public API.

## Review lens

**Split-fix cohesion** - a split fix didn't fragment a cohesive unit into ravioli.
