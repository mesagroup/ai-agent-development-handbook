# A clause on runtime count, and the half of it a snapshot can check

Issue #18. The handbook says nothing about how many runtimes or language stacks a project should carry, so a finding about a casually-wired second stack has no clause to cite - and an uncited finding is the consultant's opinion, which is what the citation binding exists to eliminate.

**Status.** Written and self-approved under autonomous mode, with no maintainer review gate, as the second nightshift loop's third item (ledger #86). Every decision below names the alternative it rejected, so any one of them can be reopened on evidence rather than on recollection. The gate that was not granted is the review of the resulting PR.

## The clause goes in Part 3, after the decay section

`docs/engineering/codebase-structure.md`. The part's tier list is written for one language stack, and each additional runtime brings its own dependency graph and lockfile, its own test suite and gate, its own vulnerability and licence surface, and its own upgrade cadence.

**It sits after `## Watch for structural decay beyond layering`, which is a correction.** The first version put it directly after the tier table, on the argument that it qualifies the assumption the table makes. Both reviewers read the part start to finish and found that this splits what the part's own opening paragraph promises as a pair: an organizing idea, then one invariant that holds it in place. `## Why the rule matters` then reaches back to the invariant's diagram. Placing the clause after the decay section keeps that run contiguous and puts the two sections that step outside the layering argument side by side - beyond layering, then beyond one stack. The hook to the tier list survives as a sentence rather than as adjacency.

Rejected: Part 2, where the concrete costs live. The tests, the gate and the lockfile each already have a home there or in Part 9, and this clause governs only the count and the declaration - putting it beside the costs would invite it to re-legislate them.

## The clause splits into two matrix rows, because its two halves have different classes

This is the decision worth reading closely, since #86 settled the default the other way.

**#86's decision** was to default the decidability statement to process-only with a gap entry, and it granted a tick the auditable reading only on naming the snapshot-decidable form: "A tick may mark the clause auditable only by naming the snapshot-decidable form in the PR body; 'probably auditable' is not that." So what follows is inside that grant rather than a reopening of it.

**The named form.** The runtimes present are detectable from manifests and lockfiles, which is the same detection `audit-core` step 1 already performs when it partitions a target by language. The runtimes declared are a named list in the binding-rules file. The finding is the set difference, plus a declaration missing what the clause requires it to carry - what the runtime buys, and who maintains it.

**The clause requires the declaration to mark its own primary, and that is a correction review forced.** The first version exempted "the primary" runtime without saying who decides which one that is. The primary is present and, being exempt, need not be declared, so the set difference always contained it and every project failed - and in a repository with a `pyproject.toml` and a `package.json` both at the root, which is the shape that prompted #18, no rule short of a judgment picks one. Requiring the declaration to name every runtime and mark its own primary moves that decision to the project, where it belongs, and leaves the check a set difference with nothing to decide. The justification half then attaches to the runtimes the declaration itself marks as not primary.

**What stays process.** Whether a second stack could be replaced by the primary one turns on which libraries exist and who the team can staff, neither of which is in the tree. That is the snapshot-undecidability reason `docs/superpowers/specs/2026-08-05-audit-foreign-target-design.md` gave for rejecting an `arch/guest-stack` check, recorded on #8, and it is untouched. #18's own body attributes that rejection to PR #17; the reasoning is not in that PR, which is worth noting so the citation is not copied forward again.

So the section carries two rows under the `-a`/`-b` split the matrix already uses for a section with more than one claim: `-a` `process`, the judgment; `-b` `static` with an `extend-skill` gap, the declaration. Bundling them into one row would have hidden whichever half was written second, which is exactly what the rendered severity notes say a split exists to prevent.

**A gap entry on a `process` row is a shape this tree models and does not use, which review corrected from the first version of this paragraph.** The first version said nothing in the tree modelled it. That was false, and it contradicted a spec that had rejected the idea by name: `render_handbook_traceability.py`'s `_gap_kind` returns `process` as one of three gap kinds, `KIND_LABELS` gives it a label, the per-band split counts it, tests cover it, and `docs/superpowers/specs/2026-07-30-gap-entry-kinds-design.md` lists "Forbidding `gap` on `process` rows" under its rejected options as "wrong twice over: it removes a shape the taxonomy is designed to express". A claim about a sibling, made without checking it, which is what this repository's rule against them is for.

What is true, and what the split rests on instead: computed over the 136 rows before this change, 23 rows are `process` and **none carries a gap**, and every one of the 72 rows that does is `static` or `artifact`. More decisive than the count is which recommendation the declaration needs. It needs `extend-skill`, because `arch-audit` is a natural owner and the fix is one check record - and `extend-skill` is the recommendation that makes least sense on a row no check can own, which the 2026-07-30 spec noticed from the other direction when it weighed and deferred requiring `report-only` on a process row's gap. A `static` row also carries the declaration into the coverage arithmetic as an auditable row awaiting a check, where a `process` row would leave it outside the count of what the family could check and does not.

So the split satisfies #18's criterion - "if auditable, a follow-up issue for the check; if not, a gap entry recording why" - by giving the auditable half the gap and the issue, and the process half a note saying why no snapshot can reach it.

## The check is filed rather than written: #91

`arch-audit` is the owner, `locality: global`, because a runtime count is a whole-repository fact a per-partition agent cannot see. The issue records the two questions the record has to answer rather than leaving them to the agent - how the binding-rules file is resolved when the handbook names it by role rather than by path, and what separates a runtime from a language a single file happens to be written in.

It also records what the check must not do. **It must not rate the stack**, because the individual costs of an undeclared runtime already have owners - untested guest code to `test`, a stack CI never exercises to `ci`, an unlocked declaration file and an unscanned second vulnerability surface to `deps`. That is the double-counting reason from the same spec, and it applies to any check asking whether the stack is good rather than whether it is declared. The third reason it gave - that a guest-stack check would carry no handbook citation - is the one this branch dissolves, since the clause now exists and the `-b` row is what #91's record will cite.

## The part's checklist gains a line, reversing this spec's first answer

The first version rejected it, on the grounds that the checklist is scoped to placing code and reviewing an import and that widening it might move the recap row's severity. The stale-prose pass argued the other way and computed the objection away, and it is right on both counts.

An unowned stack arrives as exactly the event the checklist covers: somebody places new code, in a new language, in a pull request, and until #91's check exists a human ticking a list is the only enforcement there is. And the severity does not move: a recap takes the maximum of what it recaps, Part 3's rows are eight `important` and five `minor` with no `critical` among them, and the new clause is `important`.

The item recaps **only the declaration half**, because the judgment half is not something a reviewer can tick against a diff. The recap row's claim goes from seven items to eight and its note says which half the new item covers.

## What this change does not touch

No check record changes, so no record's `handbook` list moves and the edge set stays consistent in both directions - the `-b` row's grounding is a gap rather than a citation until #91 lands. `docs/audit/handbook-traceability.md` is regenerated rather than edited. No module under `scripts/`, so `[tool.deptry] known_first_party` is unchanged.
