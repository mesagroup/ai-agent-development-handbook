# What a check can still answer when a grant is withheld ([#26](https://github.com/mesagroup/ai-agent-development-handbook/issues/26))

**Status:** draft 2026-08-06. Follows [#19](https://github.com/mesagroup/ai-agent-development-handbook/issues/19), which introduced `needs:` and the rule this spec corrects. Should land before [#5](https://github.com/mesagroup/ai-agent-development-handbook/issues/5), which gives fourteen `test-audit` and `security-audit` records their first TypeScript tooling and would otherwise author them against the defect described here.

## Problem

[#19](https://github.com/mesagroup/ai-agent-development-handbook/issues/19) gave each `tooling:` name a tier saying what must be present in the target before that tool can answer. `audit-core` then derives a conclusion about the *check* from those facts about its *tools*: "Where the run holds no grant, the checks whose only tools need one are `no-evidence`, never clean." The sweep repeats it twice more, in its step 0 grants bullet and in its fan-out brief.

The derivation is wrong whenever a check has an axis that needs no tool at all, and three records already say so in prose:

| Record | Frontmatter implies | Prose says | Why the derivation fails |
|---|---|---|---|
| `arch/complexity-gate` | `no-evidence (not-permitted)` on a TypeScript partition | "The gate question itself needs no grant" | The tools are named as the gate's *subject*. Whether a threshold is configured and enforced is read from the linter config and the CI workflow, both present on a read-only clone. |
| `test/determinism` | the same | "only the grep pass answers" | The tier is true - the randomized-order and repeat-run passes do run the suite - but grepping for `time.time()`, `datetime.now()`, unseeded `random.` and live network calls answers the non-determinism axis with nothing installed. |
| `test/isolation` | the same | "answered on the I/O axis with the timing evidence missing" | The same shape: the `--durations` pass needs the grant, reading test source for real I/O does not. |

[#26](https://github.com/mesagroup/ai-agent-development-handbook/issues/26) framed this as a collision between two `needs:` rules, on the strength of `arch/complexity-gate` alone. The wider reading is that a check-level claim is being *derived* from tool-level data and is unexpressible when the derivation is wrong, so the only place to correct it is prose that contradicts the frontmatter beside it.

The exposure is measurable rather than estimated. Applying the rule per language partition silences a (record, language) pair whose every tool carries a tier. There are **12 such pairs across 11 records** - `deps/hygiene` is silenced in both of its languages - of which three carry overriding prose and eight are silenced with nothing recording whether that is correct:

| Record | Language | Overriding prose today |
|---|---|---|
| `arch/complexity` | typescript | no |
| `arch/complexity-gate` | typescript | yes |
| `arch/hidden-coupling` | typescript | no |
| `deps/freshness` | python | no |
| `deps/hygiene` | python, typescript | no |
| `deps/licenses` | python | no |
| `deps/transitive-licenses` | python | no |
| `test/coverage-reach` | python | no |
| `test/determinism` | python | yes |
| `test/isolation` | python | yes |
| `test/mutation` | python | no |

## Decisions

### 1. The check-level claim gets its own field

One optional string per record, `ungranted_note`, answering the question `needs:` cannot: when this record's tools need a grant this run does not hold, what can still be answered?

```yaml
tooling:
  python: [pytest-randomly, pytest-rerunfailures]
needs:
  target-execution: [pytest-randomly, pytest-rerunfailures]
ungranted_note: >-
  Grepping tests for `time.time()`, `datetime.now()`, unseeded `random.` and live
  network calls answers the non-determinism axis with no tool. The randomized-order
  and repeat-run passes do not survive a withheld grant.
```

`tooling:`, `needs:` and `test_a_tool_has_one_tier_across_the_family` are untouched. A tier stays a property of the tool; this is a property of the check, and the two were only in conflict because one of them had nowhere to live.

### 2. Required exactly where the derivation would otherwise bite

The field is required on a record where every tool in at least one language carries a tier, and rejected as vacuous on any other.

This is `handbook_note`'s shape, for `handbook_note`'s reason: demand the field precisely where the default inference is load-bearing, so it cannot be left to a silent default. The eight records above that today say nothing are not making a claim - nobody examined them - and after this change the file cannot be in that state.

The rejection half matters as much as the requirement. A note on a record that keeps an untiered tool describes a situation that cannot arise, and a reader who finds one has no way to tell it from a note that is doing work.

### 3. A sentinel for the genuinely blocked case

A record with nothing to add writes `ungranted_note: none`. Eight paraphrases of "both passes run the target's suite, so nothing answers" is duplication the validator should absorb.

The loader accepts exactly the lowercase string `none`. `None` and `NONE` are rejected by name, because YAML leaves them as ordinary strings that would read as a real fallback claim rather than as the sentinel; `null` and an empty value are rejected because YAML turns them into nothing at all, which is indistinguishable from an omitted field.

### 4. All three statements of the derived rule defer to the field

`audit-core` step 1, the sweep's step 0 grants bullet, and the sweep's fan-out brief each gain the same conditional: a fully-tiered check under a withheld grant is `no-evidence (not-permitted)` **unless its `ungranted_note` names what still answers**. Because decision 2 makes the field required on exactly those records, the answer is always there to read rather than inferred.

A record carrying `none` is the blocked case and reports `no-evidence (not-permitted)`. A record carrying prose answers on the axis the note names and reports the domain's own status with the missing evidence stated - which is what `test/determinism` already tells an agent to do, now said once in the engine instead of once per record.

### 5. Verify each of the twelve rather than transcribe the current belief

Writing `none` asserts that nothing answers. Eight of those assertions have never been examined, and #19 is the precedent for what examining them is worth: its tier sweep was expected to be annotation and turned out to be four corrections, each a record sending an agent to a tool that could not answer where it was sent.

So each pair is checked against the question the record actually asks, not against what its current tooling happens to offer. `deps/freshness` on Python is the case to expect something from: it is silenced only because `uv` and `pip` both read installed state, while comparing lockfile pins against the registry is exactly what `npm-check-updates` does on the JavaScript side, and that tool is untiered.

Where verification finds such a path, the fix is to give the record that tool or that prose. The record then has an untiered tool, drops out of the fully-tiered set, and by decision 2 may no longer carry `ungranted_note` at all. The field retreats as the underlying gaps close rather than accumulating beside them.

### 6. `arch/complexity-gate` keeps its tier

The record keeps `target-execution` on `eslint` and `eslint-plugin-sonarjs`, and its contradiction dissolves because the two claims are now separable: running ESLint there really would need the execution grant, and the gate question really is answerable without running it.

This reinterprets the first acceptance criterion of #26, which asks for a way to name "a tool it does not run" without "asserting a false tier". On the evidence the tier is not false, only not load-bearing, and building a run-versus-inspect split in `tooling:` to satisfy the original wording would leave `test/determinism` and `test/isolation` exactly where they are - their tiers are true and their fallback is source-reading, so no reclassification of tools reaches them.

## Scope

| File or group | Change |
|---|---|
| `scripts/audit_checks.py` | The field, the `Check` member, the required-iff / vacuous / sentinel-casing rules, the frontmatter table and a docstring paragraph on what the field claims |
| `tests/scripts/test_audit_checks.py` | A case per validation rule, plus a floor on the number of records carrying a prose note, so replacing them all with `none` fails instead of passing quietly |
| `.agents/skills/audit-core/SKILL.md` | The step 1 conditional, and `ungranted_note` in the authoring frontmatter list |
| `.agents/skills/audit/SKILL.md` | The step 0 grants bullet and the fan-out brief, both of which restate the derived rule |
| The 11 records | Verify per decision 5, then write prose, write `none`, or close the gap and write neither |
| `docs/audit/sweep-obligations.md` | A row per obligation this adds to `audit-core` |
| `CLAUDE.md` | The check-records paragraph |

No traceability matrix rows change. This is skill mechanics rather than a handbook clause, so no check gains or loses a `handbook:` citation and the edge set is untouched.

## Verification

The mechanical half is covered by the existing gates: each loader rule gets a unit test, the integrity gate runs `--check` over the real tree so a missing or vacuous note fails there, and `tests/test_sweep_obligations.py` holds the new ledger rows to the same anchor-and-quotation standard as the rest.

Two things the validator cannot reach, both stated here rather than discovered later.

**It can check that a note is present, never that it is true.** A record could describe a fallback that does not exist, or write `none` where a path does exist. Nothing mechanical distinguishes either from the honest case. The sweep in decision 5 is what stands behind the eleven claims, and it is a reading pass that CI cannot repeat - the same standing limit `needs:` has, for the same reason.

**There is no foreign target in this repository, so nothing exercises an ungranted run end to end.** Decision 4 is prose an agent reads at run time. What is gated is that the obligations are stated, that the ledger accounts for each, and that no record's note contradicts its own `tooling:` and `needs:`.

The prose-note floor in the test suite is the one guard against the failure mode this change could introduce: a later author who finds the required field inconvenient and satisfies it with `none` everywhere. It cannot tell a correct `none` from a lazy one, only that the three known prose notes have not all evaporated.

## Acceptance criteria, mapped

| Criterion (from [#26](https://github.com/mesagroup/ai-agent-development-handbook/issues/26)) | Where it is met |
|---|---|
| A record that names a tool it does not run can express that without asserting a false tier | Decisions 1 and 6, with the criterion reinterpreted: the record expresses that the *check* does not need the tool, and the tier stays because it is true of the tool |
| The consistency guard still catches a record that forgot to classify a tool it does run | Decision 1 leaves `test_a_tool_has_one_tier_across_the_family` untouched |
| `arch/complexity-gate` no longer needs prose to contradict its own frontmatter | Decision 6: the prose moves into `ungranted_note`, where it is a claim about the check rather than a rebuttal of the frontmatter |
| The chosen rule is stated wherever the schema is documented | Scope: `audit-core`'s authoring section, `scripts/audit_checks.py`'s docstring, and `CLAUDE.md` |

The issue also asks that the "an absent key is a positive claim" hazard be revisited alongside this. It is, for this field only: decision 2 removes it here by making absence illegal wherever the claim would matter. It remains for `needs:` itself, where a record nobody examined still reads as one deliberately left at the default, and this spec does not close that.

## Related

- [#19](https://github.com/mesagroup/ai-agent-development-handbook/issues/19) introduced `needs:` and the derived rule, and its PR patched all three of the contradicting records in prose.
- [#5](https://github.com/mesagroup/ai-agent-development-handbook/issues/5) authors TypeScript tooling for fourteen records; every one that ends up fully tiered will need this field, which is why this lands first.
