# The routes are the tooling fallback

**Issue:** #61. **Part of:** #58. **Builds on:** #59 / PR #60, merged as `5df399f`.

## The problem

The arch pilot derived each record's `routes:` *from* its `## Tooling fallback` prose and left the prose in place. Measured across the eleven migrated records on 2026-08-19: **49,699 bytes of frontmatter beside 39,056 bytes of `## Tooling fallback` prose**, in bodies totalling 51,951 bytes. Nothing deletes the prose, nothing binds it, and no test compares the two copies.

The sharpest operational claims now exist in both places at once. `arch/complexity-gate`'s `C901`-needs-`mccabe`-configured warning is in a route field and in the body. So is `arch/cycles`' `--show-cycles`-has-no-textual-output-channel, and `arch/dead-code`'s vulture-confidence-score caveat. Either copy can be edited without the other.

## The decision

**A record declaring `routes:` carries its tooling fallback in its routes and has no `## Tooling fallback` section.** The prose is deleted, not regenerated. The frontmatter is the only source of truth.

Three facts make this the smaller change rather than the larger one.

**The section was never mandatory.** `audit-core/SKILL.md` already instructs a record to omit "any section the check has nothing to say in", and one legacy record already has none. Deleting it on eleven records is the existing rule applied, not an exception carved.

**The guard that wanted it has already been rebuilt as validation.** `test_a_record_that_classifies_a_tool_states_a_fallback` binds the 22 records whose `needs` is non-empty, and it exists because a `needs:` tier says nothing about what to do instead. On a record declaring `routes:` the schema answers that directly: `_silenced_languages` and `answers_ungranted` are the machine-enforced form of "states a fallback", and a route's `note` and `alone_insufficient` are where the what-to-do-instead lives. Scoping that test to records declaring `tooling:` recognises a guard that #59 promoted from prose to validation; it does not weaken one.

**Generation would automate the redundancy rather than remove it.** A renderer would run at dev time, like `render_handbook_traceability.py` and `render_python_fixture_expectations.py`, and its output would be committed - so the plugin would ship 39,056 bytes of machine-maintained prose restating frontmatter that the reading agent already has. It would also make each record file part-generated on a condition invisible in the file: a contributor editing `## Tooling fallback` would hit a gate failure on eleven records and correct behaviour on sixty-six, with nothing in the file's name or location to distinguish them. Under deletion the condition is visible in the file itself - the section is there or it is not - and it disappears entirely once every record has migrated.

*Alternative recorded and not taken:* render the section from the routes and hold it with a `--check` gate. It keeps the section in step with the routes by construction and leaves both `SKILL.md` sentences below true unedited. It loses on the three facts above.

## The one schema addition: `evidence:`

Some fallback prose belongs to the check rather than to any route. `arch/size` opens with "Line counts per file; flag outliers and anything over a documented norm."; `arch/complexity-gate` opens with "**Read the project's configured threshold before measuring, and treat its absence as a finding in its own right.**". Both are check-level directives that no route owns, and they are the only two of the eleven whose fallback section has an unlabelled paragraph.

The shape is not confined to those two. `arch/coupling`'s **Python** paragraph opens with "compute afferent/efferent counts per module from the same edge set; flag the top hubs", which is the check's measurement instruction sitting inside a language-labelled paragraph. `arch/martin-metrics` and `arch/over-decomposition` do the same.

So the record gains one optional record-level frontmatter field, `evidence:` - a short statement of what to measure and what counts as evidence, validated as present-and-non-empty or absent. The name is the family's own word: these records already write "the counts are the evidence", "`D` is the evidence", "Record the ratio ... as the evidence".

The alternative was to fold that content into the record's lead prose above `## Severity`. It is rejected because the lead prose is the *claim* - what the check is looking for - while this is the *measurement*: what to compute and what to record as the finding's evidence. Putting it in body prose also leaves an operative instruction outside the frontmatter, which is the thing this issue exists to end.

## Evidence triage - the only place information can be silently destroyed

A token-level diff of each record's fallback prose against its frontmatter splits the eleven:

| population | records | prose-only tokens |
|---|---|---|
| pure duplication | `complexity-gate`, `martin-metrics`, `complexity`, `dead-code`, `hidden-coupling`, `size` | 0, 5, 6, 6, 7, 12 |
| prose carries more | `over-abstraction`, `cycles`, `coupling`, `layering`, `over-decomposition` | 50, 116, 120, 147, 174 |

The excess in the second population is measured smoke-run observation: 1090 edges thinning to 122, dependency-cruiser 18.2.0, pnpm 9.15.9 against 11, `--no-config` discarding `--ts-config`, `.madgerc`, `tsconfig.app.json`. `docs/audit/typescript-lens-smoke-run.md` already carries all of it - 9.15.9, 18.2.0, `--no-config`, 281, `totalCruised`, 1090, `tsconfig.app.json`, 45 warnings and 31 warnings all occur in that file - and the prose being deleted already links to it.

**The rule, and it is absolute: no record body is touched until every claim in its fallback prose is traced.** Each claim resolves to one of three dispositions, recorded per record:

- **operative and present in a route field or in `evidence:`** - nothing to do.
- **operative and missing** - it goes into the field it belongs to, before the prose is deleted.
- **measurement** - it belongs in the smoke-run doc. Present there, nothing to do; missing, it is added there first.

Anything that fits none of the three is a conscious drop and is recorded as one. The six pure-duplication records go first, because they carry no triage risk and prove the deletion end to end.

## The obstacle: the transcription guards are anchored on hand-written sentences

`tests/scripts/test_python_fixture_harness.py` anchors **19 of its 50 `INVOCATIONS` - the whole arch set** - on paragraphs of `## Tooling fallback`, through `_fallback_paragraphs`, which raises by design when a record has no such section. Each entry carries a `record_quote` lifted verbatim from that prose, and **15 of the 19 carry no `argv` at all**: `arch/layering/grimp`'s quote is "Record the offending `file:line` for each violation.", and `arch/complexity-gate/xenon`'s is the bolded threshold directive.

These properties are **prose-drift instruments**. They exist to catch a prescription written in prose diverging from the declared forms. Once the prose is gone there is no second copy to drift, and for a migrated record the routes-to-`INVOCATIONS` oracle already owns the binding, in both directions across `argv` and `forms`.

So every property anchored on a fallback paragraph or on the `record_quote` source line is scoped to records still declaring `tooling:`, through **one predicate stated once** rather than a condition repeated per property. It is the same predicate the fallback-section test needs, so the two are one mechanism.

The arch `INVOCATIONS` entries stay: the oracle binds them, and `record_quote` stays on them as the record-provenance note it remains for the unmigrated domains.

Two things verified before committing to this:

- The `assert skipped` sibling-lens dead-code guard is fed **exclusively by four `security/*` semgrep entries**, so exempting arch does not turn it into dead code.
- All eleven arch records project a non-empty `tooling`, so the empty-tooling branch of the fallback-section test and `test_every_tooling_record_offers_a_typescript_lens` are unaffected.

What the prose properties watched and the oracle does not is a gap this narrows rather than closes: the oracle binds command routes, so a `procedure` or `library` route's note was watched by the prose properties and is watched by nothing afterwards. Deletion removes *drift* as a failure mode, not a *wrong note*. Nothing here closes that, and #58 already carries it as the epic's main residual risk.

## The two prompt sentences

Both are live instructions that stop being true for a migrated record, and both are prompt changes: their own commit, stating why.

- `audit/SKILL.md` tells an agent "if it has none, fall back to the record's `## Tooling fallback`". On a routes record there is no such section, and what it should read is the record's routes.
- `audit-core/SKILL.md` names `## Tooling fallback` in the list of body sections and again in the detects-before-it-prescribes rule. Both need the routes case.

The passage in `audit-core/SKILL.md` that decides the withheld-grant outcome is re-read for any sentence that assumes the section exists on a migrated record, since that is the passage a missed edit silences a check in.

Verified: no renderer reads a record body section, and `docs/audit/sweep-obligations.md` names `## Tooling fallback` in zero rows. Editing `audit-core/SKILL.md` still obliges a read of that file, which happens regardless.

## What this changes about #54

#54 asks the transcription guards to watch the whole record rather than one section, because a prescription written in `## Fix` is invisible to them. On a migrated record there is no prescription outside the frontmatter left to watch, so #54's scope shrinks to the records still declaring `tooling:` while they wait to migrate. It is neither resolved nor unaffected; the issue gets a comment saying which.

## Acceptance criteria

- [ ] `evidence:` is specified and validated in `audit_checks.py` as an optional record-level field, rejected empty where present
- [ ] Evidence triage recorded per record: every claim traced to a route field, to `evidence:`, to a smoke-run doc, or to a recorded drop
- [ ] None of the eleven arch records has a `## Tooling fallback` section, and no claim was lost
- [ ] One predicate scopes the fallback-section test and the harness's fallback-paragraph and `record_quote` properties to records declaring `tooling:`
- [ ] The arch `INVOCATIONS` entries are retained and the routes oracle still binds them in both directions
- [ ] `audit/SKILL.md` and `audit-core/SKILL.md` state that a routes record carries its fallback in its routes, in a commit of their own that says why
- [ ] The scoping is mutation-verified: reintroducing a section on a migrated record, and removing one from a legacy record with a tiered tool, each fail
- [ ] New code ships with unit tests and coverage does not drop
- [ ] Full suite green, ruff clean, both integrity gates exit 0
- [ ] #54 carries a comment recording what this changed about its scope

## Out of scope

The eight unmigrated domains: their 66 records keep their prose, because prose is still their source of truth and there are no routes to carry it. Deleting the harness's Markdown-parsing helpers, which those records still need. Closing the wrong-route-note risk, which is #58's.
