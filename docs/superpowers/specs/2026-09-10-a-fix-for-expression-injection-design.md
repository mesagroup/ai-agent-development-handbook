# A fix for expression injection, and the detection the record did not list

Issue #13. `ci/workflow-correctness` detects two unrelated faults and its `## Fix` only ever addressed one of them: it says "Make failures actually fail" and nothing at all about repairing an expression injection, which is the more dangerous of the two and the one its own `## Severity` calls Critical.

**Status.** Written and self-approved under autonomous mode, with no maintainer review gate, as the second nightshift loop's second item (ledger #86). Every decision below names the alternative it rejected, so any one of them can be reopened on evidence rather than on recollection. The gate that was not granted is the review of the resulting PR.

## The issue's premise is wrong about this record, and that is a second gap

#13 says "the detection tool already listed - `zizmor` flags template injection - so this is a missing *fix*, not a missing detection". `zizmor` is **not** listed on this record. Computed over `ci-audit/checks/`: `zizmor` appears in the `tooling` of `ci/trigger-safety`, `ci/permissions-secrets` and `ci/action-supply-chain`, and `ci/workflow-correctness` carries `tooling: any: [actionlint]` alone.

That matters because of what this skill's own detect list assigns to each tool. `ci-audit/SKILL.md` reads: "`actionlint` (workflow correctness + shellcheck of `run:` blocks), `zizmor` (GHA security auditor - trigger safety, injection, permissions, unpinned actions)". So injection detection is `zizmor`'s by the family's own account, and a run of this check reaching for `actionlint` alone answers the syntax and quoting halves and reports nothing for the half the record calls Critical - a tool that ran and found nothing, indistinguishable from a clean workflow.

**This is stated as the family's assignment rather than as a claim about `actionlint`'s upstream feature set**, which is the boundary this repository's verify-against-the-tool's-own-documentation rule draws: what can be checked from here is what the skill says each tool answers, and the skill says injection is `zizmor`'s.

So `zizmor` joins `tooling: any:` and the fallback prose says which tool answers which half. Nothing pins the tool lists from outside: the two tests naming `ci/workflow-correctness` hold the set of record ids and the set of records still on the legacy schema, and this record stays in both. `zizmor` is untiered on all three siblings and is untiered here, so `test_a_tool_has_one_tier_across_the_family` sees no disagreement.

## The fix, and why quoting is not it

Bind the untrusted value into `env:` on the step and reference it as `"$VAR"` in the `run:` body, so it arrives as data in the environment rather than as text spliced into the script before the shell sees it. Prefer an action input over shell interpolation where the action offers one.

The record says explicitly that quoting the interpolation is not the fix. `"${{ github.event.issue.body }}"` is substituted into the script text before the shell parses it, so the quotes are part of the attacker's input, not a boundary around it. That sentence is in the record because a fix pattern that a reader can satisfy incorrectly is worse than none: the wrong version looks like the right one in a diff.

## Three severity tiers, because the exit-code half had none

The rubric was **Critical** for an injection sink and **Minor** for a cosmetic lint finding, with the masked-exit-code case falling between them and named by neither. A job that reports green over a step that failed is not cosmetic - it is the gate not gating - and it is not an attacker path either. It gets **Important**, which is what #13's second criterion asks for: the two halves distinguished as a correctness bug and an attacker path rather than sharing a tier.

## Rejected, and by whom

**A separate record for expression injection** - rejected in #86 before this tick began, and this tick implements that rather than reopening it. A split needs a new handbook edge and a matrix row in both directions, and the severity rubric above achieves the separation the issue asks for without a second record.

**A handbook citation on this record.** Left deliberately, and this is the one judgment worth reversing if the maintainer disagrees. The obvious candidate is `security-supply-chain/treat-the-pipeline-as-a-privileged-environment`, which the two sibling records cite. Read against the clause, injection is not one of its four elements: a read-only default token, actions pinned to a commit SHA, never running untrusted pull-request code with secrets in scope, and short-lived federated credentials over stored ones. Interpolating attacker-controlled *data* into a step that is otherwise trusted is none of those - the third is `ci/trigger-safety`'s `pull_request_target` case, which is untrusted *code*. The matrix row's own note says each of its four clauses is named inside one of the three checks that cite it, so adding a fourth check would put a citation on the row for a fault the clause does not state. The handbook not raising template injection anywhere is a real gap; #18 is the precedent for how this repository fills one, which is a clause first and a check afterwards.

**Stating each tool's kind in the fallback prose.** The three-kinds rule asks a `tooling:` record to distinguish a registry package a one-shot runner can fetch from a package-manager subcommand from a standalone binary. Neither this record nor its three siblings does that for `zizmor` today, and doing it here means asserting install mechanics for two tools that cannot be verified from this repository. Left as the siblings have it, so the whole family changes together when it changes.

## What the `handbook_note` claimed, and what it says now

The note justified the empty `handbook` list by calling all four faults "a mechanical authoring-correctness question the handbook does not raise anywhere". Its conclusion is right and its reason lumped the injection sink in with syntax errors. It now separates them: well-formedness, which the handbook does not raise, and the injection sink, which is a security fault whose absence from the privileged-environment clause is stated by naming the clause's four elements rather than asserted.

## What this change does not touch

No `handbook` entry changes, so the matrix is untouched and the edge-set rule has nothing to hold. No module under `scripts/`, so `[tool.deptry] known_first_party` is unchanged - run anyway rather than reasoned about. The record stays on the legacy `tooling:` schema, so `## Tooling fallback` prose remains its source of truth and no route is written.
