# Two sections out of the file every path loads

Issue #85. `audit-core/SKILL.md` is loaded on every path through this family - the sweep's nine fan-out subagents each load it, and so does every direct `handbook-audit:<domain>-audit` invocation. Two of its four sections are read by no audit run at all.

**Status.** Written and self-approved under autonomous mode, with no maintainer review gate, as the second nightshift loop's fourth item (ledger #86). Every decision below names the alternative it rejected. The gate that was not granted is the review of the resulting PR.

## Measured on this branch's base, `bb784a0`

| region | words | ledger anchors in it |
|---|---|---|
| `SKILL.md` whole, before | 7,284 | 86 rows resolve |
| `## The loop` steps 3-6 | 515 | 0 |
| `## Authoring a new auditing skill` body | 975 | 1 |
| `SKILL.md` whole, after | **5,961** | 86 rows still resolve |

**The issue's own figure of 6,461 words is stale** - #70, #74 and #77 added to the file after it was filed. #86 predicted 5,794 after both moves; the real figure is 5,961, and the difference is the two pointer paragraphs that replace the moved text. A pointer has to say what the reference holds and when to read it, or the move trades a section nobody read for a section nobody can find, so those words are the cost of the move rather than an overrun.

**Acceptance criterion 3 is therefore left unticked**, with the residual named: 461 words above `skill-creator`'s ~5,500 guideline. That is #86's settled instruction and the reason for it holds - trimming to reach the number is criterion 5's question, it is settled by an eval rather than by taste, and #93 now carries it.

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

## What this change does not touch

No check record, no matrix row, no module under `scripts/`. `## Running a route` and `## Cross-cutting rules` stay where they are. The prose-density question is #93's.
