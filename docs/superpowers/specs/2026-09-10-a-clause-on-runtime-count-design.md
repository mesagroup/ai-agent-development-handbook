# A clause on runtime count, and the half of it a snapshot can check

Issue #18. The handbook says nothing about how many runtimes or language stacks a project should carry, so a finding about a casually-wired second stack has no clause to cite - and an uncited finding is the consultant's opinion, which is what the citation binding exists to eliminate.

**Status.** Written and self-approved under autonomous mode, with no maintainer review gate, as the second nightshift loop's third item (ledger #86). Every decision below names the alternative it rejected, so any one of them can be reopened on evidence rather than on recollection. The gate that was not granted is the review of the resulting PR.

## The clause goes in Part 3, immediately after the tier table

`docs/engineering/codebase-structure.md`. The part's own tier table is written for one language stack, and each additional runtime duplicates almost all of it: a dependency graph and lockfile, a test runner and coverage story, a CI lane, a vulnerability and licence surface, an upgrade cadence. Placing the clause directly after the table makes it qualify the assumption the table makes rather than arriving as a free-standing opinion later in the part.

Rejected: Part 2, where the concrete costs live. The tests, the gate and the lockfile each already have a home there or in Part 9, and this clause adds only the count and the decision - putting it beside the costs would invite it to re-legislate them.

## The clause splits into two matrix rows, because its two halves have different classes

This is the decision worth reading closely, since #86 settled the default the other way.

**#86's decision** was to default the decidability statement to process-only with a gap entry, and it granted a tick the auditable reading only on naming the snapshot-decidable form: "A tick may mark the clause auditable only by naming the snapshot-decidable form in the PR body; 'probably auditable' is not that." So what follows is inside that grant rather than a reopening of it.

**The named form.** The runtimes present are detectable from manifests and lockfiles, which is the same detection `audit-core` step 1 already performs when it partitions a target by language. The runtimes declared are a named list in the binding-rules file. The finding is the set difference, plus a declaration missing what the clause requires it to carry - what the runtime buys, and who maintains it. No judgment enters any of those three steps.

**What stays process.** Whether a second stack could be replaced by the primary one turns on which libraries exist and who the team can staff, neither of which is in the tree. That is the second of PR #17's three reasons for rejecting an `arch/guest-stack` check, and it is untouched.

So the section carries two rows under the `-a`/`-b` split the matrix already uses for a section with more than one claim: `-a` `process`, the judgment; `-b` `static` with an `extend-skill` gap, the declaration. Bundling them into one row would have hidden whichever half was written second, which is exactly what the rendered severity notes say a split exists to prevent.

**A gap entry on a `process` row is what #86's wording implies and the matrix does not do.** Computed over the 136 rows before this change: 23 rows are `process` and **none carries a gap**, and every one of the 72 rows that does carry a gap is `static` or `artifact`. The three gap recommendations all presuppose an auditable claim - `extend-skill` names the skill that would own the check, `new-domain` the domain that does not exist yet, `report-only` a claim auditable but belonging in report prose. A `process` row has no check to be missing, so a gap on one would be a new combination the validator happens to permit and nothing in the tree models. The split satisfies #18's criterion - "if auditable, a follow-up issue for the check; if not, a gap entry recording why" - honestly: the auditable half gets the gap and the issue, the process half gets a note saying why no snapshot can reach it.

## The check is filed rather than written: #91

`arch-audit` is the owner, `locality: global`, because a runtime count is a whole-repository fact a per-partition agent cannot see. The issue records the two questions the record has to answer rather than leaving them to the agent - how the binding-rules file is resolved when the handbook names it by role rather than by path, and what separates a runtime from a language a single file happens to be written in.

It also records what the check must not do. **It must not rate the stack**, because the individual costs of an undeclared runtime already have owners - untested guest code to `test`, a stack CI never exercises to `ci`, an unlocked declaration file and an unscanned second vulnerability surface to `deps`. That double counting is the first of PR #17's three reasons, and it applies to any check asking whether the stack is good rather than whether it is declared. The third reason - that a guest-stack check would carry no handbook citation - is the one this branch dissolves, since the clause now exists and the `-b` row is what #91's record will cite.

## Rejected: adding a line to the part's checklist

`## Checklist: placing new code / reviewing an import` is scoped to two acts, and declaring a runtime is neither. A checklist row in the matrix also takes the maximum severity of everything it recaps, so widening the checklist would move that row's severity for a clause the reader does not meet while placing code.

## What this change does not touch

No check record changes, so no record's `handbook` list moves and the edge set stays consistent in both directions - the `-b` row's grounding is a gap rather than a citation until #91 lands. `docs/audit/handbook-traceability.md` is regenerated rather than edited. No module under `scripts/`, so `[tool.deptry] known_first_party` is unchanged.
