---
id: data-protection/data-flow-map
domain: data-protection
locality: global
handbook:
  - data-protection/know-what-personal-data-you-hold-and-where-it-goes
---

# Data-flow map

Whether a data-flow map exists beside the code, answering where personal data enters, every store it rests in and every outbound edge that leaves the trust boundary - and whether it is falsifiable against the code rather than a document produced once for an audit and true only on the day somebody wrote it.

## Severity

**Critical** - no map at all, in a project whose code plainly shows a personal-data surface. Every other check in this domain is a question asked of one edge or one store, and none of them can be answered against a list that does not exist, so this row decides whether the rest of the domain measured the system or the part of it somebody remembered.

**Important** - a map that exists and is demonstrably stale: it omits a store or an outbound edge the code shows. Cite the omission at a `file:line`, because "stale" with nothing under it is an impression rather than a finding.

**Minor** - a map that is complete but kept somewhere a reviewer will not see it go stale, so its accuracy is a matter of luck rather than of maintenance. A map on a path no change ever touches is the shape this covers.

## Tooling fallback

No tool enumerates a project's personal-data surface, so there is nothing to detect before prescribing and this check is a reading pass. Read three things.

**For the outbound edges**, take the shared outbound-provider derivation the skill file says to build once - SDK imports, configured base URLs, MCP servers and tool endpoints, and the credential names the deployment carries - rather than re-deriving it here, so this row and `data-protection/provider-surface` cannot disagree about the edge list. **For the stores**, read the deployment and infrastructure configuration, and look specifically for the kinds that get missed because they are an implementation detail of something else: a managed vector index, a cache, an object bucket of uploads, a queue, the log and trace retention on an observability backend, and the backup schedule. **For the map itself**, read the repository's documentation tree, including a compliance or privacy directory if there is one, and the contributor guide, which is where a project records which documents a change is expected to update.

Where no map is documented, **report the absence as the finding**. Do not infer a map from field names or file paths and then flag the code against it: that is the no-inferred-rubric failure `audit/SKILL.md` forbids, and the row it produces cannot be fixed even in principle, because the standard it cites is one nobody agreed to.

## Fix

Add the map beside the code, derived from the repository rather than from memory: the entry points, the stores, and the outbound edges with what crosses each one. Put it where a reviewer sees it go stale - next to the code, or on a path the contributor guide already asks a change to update - because a map maintained beside the code is falsifiable against the code, which is the property that makes it worth keeping at all. Say in the report that a data-protection regime asks for a superset it calls records of processing, wanting the purposes, the categories of people and of data, and the erasure limits as well, so the map is the engineering half rather than the whole obligation. The audit can derive the store and edge list from the repository; the audited team owns the purposes and the categories, so name them in the remediation plan.

## Review lens

**Derivation honesty** - every store and every edge the row claims is missing from the map is cited at a `file:line` in the target, expressed relative to `target_root` rather than to any scratch copy, so the audited team can check the claim against the tree they have.

**Inferred-surface guard** - the finding is the absence or the staleness of the map, never a violation of a map the audit invented; a row that flags the code against a surface no artifact documents is withdrawn rather than downgraded.
