---
id: arch/size
domain: arch
locality: local
evidence: >-
  Line counts per file; flag outliers and anything over a documented norm.
handbook:
  - codebase-structure/watch-for-structural-decay-beyond-layering
routes:
  - lang: any
    kind: command
    tool: cloc
    registry: npm
    argv: [cloc]
    note: >-
      `cloc` is on the npm registry, which `registry: npm` states as a field
      rather than leaving to be read here, so a one-shot runner reaching that
      registry fetches it whatever the partition's language. The argv names
      the command and not the runner, which is the split the two fields
      exist to keep: spell a runner into the argv and whatever the runner
      rule puts in front of it fetches a runner.
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
    own_runner: true
    disposition: alternative
    note: >-
      Reached once neither `cloc` nor `tokei` is available, which is where
      this route sits in the precedence rather than a precondition the target
      carries - `applies_when` states the second, so availability belongs
      here. The record quotes this command verbatim and says it answers the
      check once neither other tool is available. The file list to run it
      over is an operand the record names none for. `own_runner: true`
      because `wc` is coreutils: it belongs to no registry, nothing fetches
      it, and a one-shot runner in front of it would go looking for a
      package named `wc` and fail the way a missing tool fails - on the one
      route this record calls the last thing that works.
---

# File / module size

Files grown past the point of holding in context at once (the contributor guide may state a norm; otherwise flag outliers relative to the repo).

## Severity

**Minor** - an oversized-but-cohesive file - real but low-cost, fix when touching the area.

## Fix

Split an oversized file along its cohesion seams (files that change together stay together); update all importers in the same change, and drop back-compat re-export shims unless the project maintains a public API.

## Review lens

**Split-fix cohesion** - a split fix didn't fragment a cohesive unit into ravioli.
