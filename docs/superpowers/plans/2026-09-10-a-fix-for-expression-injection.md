# Plan: a fix for expression injection

Issue #13. Design: [../specs/2026-09-10-a-fix-for-expression-injection-design.md](../specs/2026-09-10-a-fix-for-expression-injection-design.md).

One record changes, in the order that keeps each claim checkable: the detection it needs, then the fix, then the severity that separates the two faults, then the lens that judges the new fix.

## 1. `zizmor` joins the tooling, and the fallback says which tool answers which half

`ci/workflow-correctness` carries `actionlint` alone, and this skill's own detect list assigns injection to `zizmor`. Without that entry the record prescribes a fix for a finding its tooling cannot produce, and a run answers the syntax half while reporting nothing for the half the record calls Critical.

## 2. `## Fix` gains the injection pattern beside the exit-code one

Bind the untrusted value into `env:` and reference `"$VAR"` in `run:`; prefer an action input where one exists; and state that quoting the interpolation is not the fix, because that is the wrong version a reader can satisfy while believing they complied.

Both fixes get a bold lead, which is how the sibling records write a `## Fix` with more than one paragraph.

## 3. `## Severity` gains the tier the exit-code half never had

**Critical** injection sink, **Important** masked exit code, **Minor** cosmetic lint. The middle tier is the whole of #13's second criterion: a gate that stops gating is neither cosmetic nor an attacker path.

## 4. `## Review lens` gains the paragraph that judges the new fix

The family's `**Pipeline-security correctness**` paragraph, verbatim as the three sibling records carry it, because consistency across them is the convention and the migration rule is that a record's lens reviews that record's own fix. `**No pipeline regression**` stays and judges the exit-code fix.

## 5. The `handbook_note` stops lumping the two faults together

Its conclusion - no handbook citation - holds. Its reason called an injection sink a mechanical authoring-correctness question, and it now names the privileged-environment clause's four elements to show the fault is absent from them rather than asserting it.

## Gates

The six runnable gates, the artifact renderer being excluded because it needs the `d2` CLI. No code changes here, so there is no new unit test: what the change asserts is prose, and the guards that read it - the review-lens label property, the one-tier-per-tool property, the record loader - already exist and must stay green. A stale-prose pass over anything claiming this record runs `actionlint` alone.
