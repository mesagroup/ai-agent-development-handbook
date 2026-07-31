---
id: arch/size
domain: arch
locality: local
handbook:
  - codebase-structure/watch-for-structural-decay-beyond-layering
tooling:
  any: [cloc, tokei]
---

# File / module size

Files grown past the point of holding in context at once (the contributor guide may state a norm; otherwise flag outliers relative to the repo).

## Severity

**Minor** - an oversized-but-cohesive file - real but low-cost, fix when touching the area.

## Tooling fallback

Line counts per file; flag outliers and anything over a documented norm.

## Fix

Split an oversized file along its cohesion seams (files that change together stay together); update all importers in the same change, and drop back-compat re-export shims unless the project maintains a public API.

## Review lens

A split fix didn't fragment a cohesive unit into ravioli.
