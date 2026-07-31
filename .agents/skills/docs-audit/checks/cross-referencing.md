---
id: docs/cross-referencing
domain: docs
locality: global
handbook:
  - documentation/aim-for-docs-that-stand-alone-drifted-docs-are-worse-than-none-a
  - documentation/keep-the-architecture-vs-research-split
  - documentation/audit-docs-like-a-test-suite-a
---

# Cross-referencing

Index → doc completeness, dead links, orphaned docs (reachable from nothing), and missing reciprocal links (e.g. background/research ↔ prescriptive/architecture). Cross-link the two.

## Severity

**Important** - a dead link in the index; an orphaned key doc.

**Minor** - a missing reciprocal link.

## Tooling fallback

If the project has a docs link-checker / index-completeness script, use it. If not, do a dead-link + orphan scan yourself (every relative link resolves; every doc reachable from an index).

## Fix

Reconcile the index, repair dead links, add reciprocal research↔architecture links.

Ground each writing task in the Phase-1 source maps: the exact cross-links, so the implementer verifies rather than invents.

## Review lens

Every internal link resolves, no forward links, checker green, cross-link-don't-duplicate holds.
