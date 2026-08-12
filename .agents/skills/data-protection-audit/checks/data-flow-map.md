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

**Critical** - no map at all, where a personal-data surface is established. Part 10 puts the map ahead of its other directives because each of them is a question asked of one edge or one store, and none can be answered against a list that does not exist, so this row decides whether the rest of the domain measured the system or the part of it somebody remembered.

What establishes a surface, and the line the inferred-surface guard below actually draws: **inference is licensed to establish *that* a surface exists, and forbidden to establish *what it contains*.** An authentication table, an upload endpoint, a store of customer documents, a provider that receives user text - any of those establishes a surface, and so does the operator's declaration at scope time. None of them licenses a claim about which fields hold personal data, because that claim is what a finding would have to cite and no artifact documents it. Where neither the declaration nor evidence of that kind establishes a surface, this row is **Important** and reports that the surface is undocumented, never Critical: the absence of a map is still worth reporting, and a Critical resting on an invented surface is the row the guard withdraws.

**Important** - a map that exists and is demonstrably stale: it omits a store, an outbound edge, or an entry point the code shows. Cite the omission at a `file:line`, because "stale" with nothing under it is an impression rather than a finding. Entry points are the weakest of the three against the code, for the reason the reading pass gives, so an ingress omission is reported as the map naming no entry points at all rather than as a specific one being missing.

**Minor** - a map that is complete but on a path nothing brings to a reviewer's attention, so its accuracy is a matter of luck rather than of maintenance. The test is documented custody, which is decidable from the clone: the contributor guide, the pull-request template or a code-owners file names the map as something a change is expected to update, or it sits beside the code it describes. Where none of those holds, this row applies.

## Tooling fallback

No detector decides this check, and the reason is structural rather than a fact about which scanners exist: the question is whether an artifact exists beside the code and matches it, and no scan of the code can establish that a document is absent. So there is nothing to detect before prescribing, and this is a reading pass. Read four things.

**For the outbound edges**, take the shared outbound-provider surface the skill file defines and builds once, rather than re-deriving it here, so this row and `data-protection/provider-surface` cannot disagree about the edge list. **For the stores**, read the deployment and infrastructure configuration, and look specifically for the kinds that get missed because they are an implementation detail of something else: a managed vector index, a cache, an object bucket of uploads, a queue, the log and trace retention on an observability backend, and the backup schedule. **For the entry points**, read the request handlers, upload and file-intake paths, scheduled importers and any integration that pulls from a customer's system - and treat this as the weakest of the three against the code, because an entry point is where personal data *may* arrive and the code shows the channel rather than what comes down it, which is why the handbook's own derivation sentence claims only stores and edges. Check that the map names entry points; do not claim a specific one is missing unless the channel is plainly an intake path. **For the map itself**, read the repository's documentation tree, including a compliance or privacy directory if there is one, and the contributor guide, which is where a project records which documents a change is expected to update.

Where no map is documented, **report the absence as the finding**. Do not infer a map from field names or file paths and then flag the code against it: that is the no-inferred-rubric failure `audit/SKILL.md` forbids, and the row it produces cannot be fixed even in principle, because the standard it cites is one nobody agreed to.

## Fix

Add the map beside the code, derived from the repository rather than from memory: the entry points, the stores, and the outbound edges with what crosses each one. Put it where a reviewer sees it go stale - next to the code, or on a path the contributor guide already asks a change to update - because a map maintained beside the code is falsifiable against the code, which is the property that makes it worth keeping at all. Say in the report that a data-protection regime asks for a superset it calls records of processing, wanting the purposes, the categories of people and of data, and the erasure limits as well, so the map is the engineering half rather than the whole obligation. The audit can derive the store and edge list from the repository; the audited team owns the purposes and the categories, so name them in the remediation plan.

## Review lens

**Derivation honesty** - every store and every edge the row claims is missing from the map is cited at a `file:line` in the target, expressed relative to `target_root` rather than to any scratch copy, so the audited team can check the claim against the tree they have.

**Inferred-surface guard** - the finding is the absence or the staleness of the map, never a violation of a map the audit invented. Check the row against the line the severity bands draw: inference may establish *that* a surface exists, which is what selects the band, and may not establish *what it contains*, which is what a finding cites. A row whose cited content came from inference rather than from an artifact is withdrawn rather than downgraded.
