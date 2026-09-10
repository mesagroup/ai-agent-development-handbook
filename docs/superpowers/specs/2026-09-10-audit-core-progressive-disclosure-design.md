# Two sections out of the file every path loads

Issue #85. `audit-core/SKILL.md` is loaded on every path through this family - the sweep's nine fan-out subagents each load it, and so does every direct `handbook-audit:<domain>-audit` invocation. Two of its four sections are read by no audit run at all.

**Status.** Written and self-approved under autonomous mode, with no maintainer review gate, as the second nightshift loop's fourth item (ledger #86). Every decision below names the alternative it rejected. The gate that was not granted is the review of the resulting PR.

## Measured on this branch's base, `bb784a0`

| region | words | ledger anchors in it |
|---|---|---|
| `SKILL.md` whole, before | 7,284 | 86 rows resolve |
| `## The loop` steps 3-6 | 515 | 0 |
| `## Authoring a new auditing skill` body, without its heading | 969 | 1 |
| the two pointers that replace them | 161 | - |
| `SKILL.md` whole, after | **5,997** | 86 rows still resolve |

The arithmetic reconciles exactly: 7,284 - 515 - 969 + 161 = 5,961 after the move, and review then added 36 words to `SKILL.md` for two reasons below - the line-number justification that had left the file with the section, and a clause sending a fix-mode reader back to the cross-cutting rules. **5,997.**

**Two counts here were wrong in the first version, and both came from carrying a figure forward rather than computing it.** The authoring body is 969 words, not the 975 #86 records, because #86's figure includes the `## ` heading and the heading stays in `SKILL.md` as the pointer's home. And the pointers are 161 words, not the 167 the difference implied, the remaining 6 being that retained heading. The rule against uncomputed counts exists for exactly this: the number was right for #86's assumption and wrong for what shipped.

**The issue's own figure of 6,461 words is stale** - #70, #74 and #77 added to the file after it was filed. #86 predicted 5,794, which is the arithmetic of the move without the pointers. A pointer has to say what the reference holds and when to read it, or the move trades a section nobody read for a section nobody can find, so those words are the cost of the move rather than an overrun.

**Acceptance criterion 3 is therefore left unticked**, with the residual named: 497 words above `skill-creator`'s ~5,500 guideline. That is #86's settled instruction and the reason for it holds - trimming to reach the number is criterion 5's question, it is settled by an eval rather than by taste, and #93 now carries it.

## What moves, and what the pointer has to carry

**`## The loop` steps 3-6** to `references/remediation-loop.md`. `SKILL.md` keeps steps 0 to 2 and the report-only stop, and the pointer replaces the four steps after it. The sweep in `audit/SKILL.md` is report-only by construction and stops at the findings matrix, so its nine fan-out agents were carrying four steps they could never reach - which `docs/audit/sweep-obligations.md` already dispositions `out of scope` for that reason, reached from the ledger's side rather than the file's.

**`## Authoring a new auditing skill`** to `references/authoring-a-new-auditing-skill.md`. It serves exactly one task and no audit run performs it: a run consumes records it did not write.

Each pointer says **when** to read the file, not just that it exists. The remediation pointer fires on fix mode and says the numbering continues, so a reader following it does not meet a step 3 with no step 2. The authoring pointer says it is not for a run at all.

**`## Running a route` stays inline**, confirmed rather than assumed: all 13 contract sentences in `tests/test_route_instruction_reaches_a_direct_invocation.py` resolve inside it, and it is the section that exists so a directly invoked domain skill reads it without a second hop. It is the second largest section and moving it would undo #70.

## The ledger's anchor search widens, which criterion 1 had already decided

`tests/test_sweep_obligations.py` searched `SKILL.md` alone, so the one anchor in the authoring section failed the moment the section moved. It ran and failed exactly there, which is the useful half of that coupling.

The search now covers `SKILL.md` plus every `references/*.md`, discovered by glob rather than listed - a reference nobody added to a constant would be a section of `audit-core` the ledger does not read, which is the silent half of the same failure. It counts them as **one corpus** rather than per file, so a sentence duplicated across two of them cannot satisfy the exactly-once rule twice. The verbatim-quote guard widens the same way.

Rejected: rewriting the row to anchor on something still in `SKILL.md`. The obligation did not change and the row's disposition is still true; only the file its text sits in changed, and criterion 1 says as much - "a move that changes the file an anchor lives in has to be reflected".

## Progressive disclosure trades one silent failure for another, so it ships with a guard

Before, `SKILL.md` carried sections most runs loaded and no run read. After, a section is read only if something points at it - so the new failure is a reference nobody links, which is the #70 defect wearing different clothes: the file exists, the prose is correct, and no run ever sees it.

`tests/test_audit_core_references_are_reachable.py` holds three properties and one vacuity guard: every reference is linked from `SKILL.md`, every link resolves, no line long enough to be a rule sits in both a reference and `SKILL.md`, and the directory is not empty. The third is what stops the move from becoming two authorities for one rule, which is the shape the record schema exists to avoid. Both directions are mutation-checked.

What none of them can check is whether a pointer says enough for a reader to know when to follow it. That is a reading pass, and it is the one thing this change genuinely risks.

## Links are relative, which is the narrow reading of the absolute-URL rule

`CLAUDE.md` says links in `.agents/skills/` to files in this repo are absolute GitHub URLs, because a relative path resolves to nothing from a plugin cache. `references/` ships inside the plugin - `plugin.json` points at `.agents/skills/` - so a relative link from `SKILL.md` to a file beside it resolves in the cache, which is why every domain skill already links `../audit-core/SKILL.md` relatively. The rule's reason is about files the plugin does not ship, and these are shipped.

## The queue's disjoint-files property does not hold here

#86 chose its four items so no PR would need a rebase under another. That was true when the queue was written. **PR #88, this loop's first item, adds three authoring sentences to the section this branch moves into `references/`.** Whichever merges second needs a rebase that relocates those sentences into the reference file rather than a textual merge, and the PR body says so. Nothing here depends on #88, so the branch is cut from freshly fetched `origin/main` and this is not stacking.

## What review changed

Two reviewers, both pinned to this tree, one reading the diff and one reading the prose cold. The move itself came out clean: both agents verified the extracted text is byte-identical to what `origin/main` carried, so nothing was dropped or altered. What they found instead was the class of defect a move produces around its edges.

**Two references only worked from the old location.** `../arch-audit/checks/` resolved from `SKILL.md` and resolves to nothing from `references/`, so an author sent to the section's one concrete example got a dead path - and no test sees it, because it is backticked text rather than a Markdown link. And the justification for citing a stable identifier rather than a line number had left `SKILL.md` with the authoring section, so step 2 deferred a reason to a file its own pointer tells a run not to open. That reason is inlined now.

**A pointer's threshold was too high to catch what it guards.** `_MIN_DUPLICATE` was 120 characters. The references' shortest instruction lines are 93 and 94 characters, so re-inlining either left the duplicate test green - verified by mutation, then re-verified at 80, which catches both and stays clear of the 32- and 34-character headings.

**Four stale numbers came with the moved text**, and the move made them quieter by putting them in a file no `SKILL.md` reader passes through. A comment on #85 from an earlier tick had flagged them and said whoever moves the section has to re-measure; this branch is that move. Recomputed, the header range the sentence quoted was wrong in three of four figures and its superlative was falsified by a domain 2.4 times the size of the one it named. Rather than restate a range that rots on the next edit, the sentence now says to measure your own domain and nothing more - which is this repository's own preference for a claim that cannot go stale.

**Several deictics stopped resolving once the text moved:** "the loop above", "a shared tree here", "the Phase-1 evidence", "this section's own obligation". Each is now named rather than pointed at. And a bare `docs/audit/sweep-obligations.md` path in a skill file is an absolute GitHub URL, per the rule that a relative path out of a plugin cache resolves to nothing for a file the plugin does not ship.

**Reworking the line-number sentence broke a ledger anchor**, which is the trap the previous loop recorded: an anchor quoting a sentence you improve still breaks. The row's anchor moved with the prose in the same commit, and the replacement carries no nested backticks - the other trap from that loop.

**One instruction was missing from the reference read as its own document.** Four of `SKILL.md`'s cross-cutting rules are load-bearing for steps 3-6, and the reference prescribed plans and implementer subagents without them. Both the pointer and the reference now say so.

**The ledger gained a block-disposition paragraph for the two reference files.** Its re-run instruction now sends a reader through `references/`, and `remediation-loop.md` holds a dozen imperative sentences with no rows - which would read as a dozen missing rows every time the pass is run. The paragraph dispositions each file as a block, the way `## Running a route` already gets one, so a sentence wanting a row of its own is answered by arguing the block rather than by adding a row beside it.

## What this change does not touch

No check record, no matrix row, no module under `scripts/`. `## Running a route` and `## Cross-cutting rules` stay where they are. The prose-density question is #93's.
