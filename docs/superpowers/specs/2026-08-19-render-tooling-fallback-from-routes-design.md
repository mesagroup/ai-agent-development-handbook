# Render `## Tooling fallback` from `routes:`

**Issue:** #61. **Part of:** #58. **Builds on:** #59 / PR #60, merged as `5df399f`.

## The problem

The arch pilot derived each record's `routes:` *from* its `## Tooling fallback` prose and left the prose in place. Measured across the eleven migrated records on 2026-08-19: **49,699 bytes of frontmatter beside 39,056 bytes of `## Tooling fallback` prose**, in bodies totalling 51,951 bytes. Nothing deletes the prose, nothing binds it, and no test compares the two copies.

The sharpest operational claims now exist in both places at once. `arch/complexity-gate`'s `C901`-needs-`mccabe`-configured warning is in a route field and in the body. So is `arch/cycles`' `--show-cycles`-has-no-textual-output-channel, and `arch/dead-code`'s vulture-confidence-score caveat. Either copy can be edited without the other.

## The decision

The frontmatter is the only source of truth. `## Tooling fallback` on a record declaring `routes:` becomes a **generated render of those routes**, rewritten in place by a script and held by a `--check` gate, in the pattern `docs/audit/handbook-traceability.md` and `docs/audit/python-fixture-expectations.md` already follow.

A generated section is a build artifact, not a rival copy, so it does not reintroduce the second source of truth. It is kept rather than deleted outright because two live contracts want the section present, and a generated one satisfies both:

- `test_a_record_that_classifies_a_tool_states_a_fallback` requires `^## Tooling fallback\n\s*\S` on every record whose `needs` is non-empty. All eleven arch records project a non-empty `needs`, so all eleven need the section.
- `audit-core/SKILL.md` names `## Tooling fallback` as where an executing agent reads what to do when a tool is unavailable.

*Alternative recorded and not taken:* delete the section outright and let the frontmatter stand alone. It would need both contracts above rewritten, and it would put schema prose into `audit-core/SKILL.md`, which drags `docs/audit/sweep-obligations.md` into scope.

## The one schema addition: `evidence:`

Some fallback prose belongs to the check rather than to any route. `arch/size` opens with "Line counts per file; flag outliers and anything over a documented norm."; `arch/complexity-gate` opens with "**Read the project's configured threshold before measuring, and treat its absence as a finding in its own right.**". Both are check-level directives that no route owns, and they are the only two of the eleven whose fallback section has an unlabelled paragraph.

The shape is not confined to those two. `arch/coupling`'s **Python** paragraph opens with "compute afferent/efferent counts per module from the same edge set; flag the top hubs", which is the check's measurement instruction sitting inside a language-labelled paragraph. `arch/martin-metrics` and `arch/over-decomposition` do the same.

So the record gains one optional record-level frontmatter field, `evidence:` - a short statement of what to measure and what counts as evidence. The name is the family's own word: these records already write "the counts are the evidence", "`D` is the evidence", "Record the ratio ... as the evidence". The generator renders it as the section's lead paragraph, before any route paragraph.

Without this field the check-level instruction has nowhere to go, and the prose cannot be deleted without losing it. That makes the addition a requirement of #61 rather than scope creep, and it is the only schema change here.

## What the generator renders

`scripts/render_check_tooling_fallback.py`, keyed on **the schema the record declares** and never on `domain == arch`, so the eight unmigrated domains are untouched today and covered automatically as they migrate.

Structure of the rendered section:

1. An HTML comment marker naming the generator and saying the frontmatter is what to edit.
2. The `evidence:` line as the lead paragraph, where the record has one.
3. One paragraph per route, in declaration order, because declaration order already carries the precedence that `## Tooling fallback` prose used to state.

Each route paragraph is `**<Label>** - <parenthetical>. <body>`, one source line, where:

- **Label** derives from `lang`: `Python`, `TypeScript`, `Any language`, `With no language-specific tool`. It is derived, never free text.
- **Parenthetical** states `kind`; the `argv` as a command span, with each `argv_by_manager` spelling where present; the `needs` tier in words ("needs the target's dependency graph materialized", "needs to run the target's own code"); and the `disposition` where it is not `runs`.
- **Body** is `applies_when`, then `alone_insufficient`, then `note`, in that fixed order, each as its own sentence group.

A `disposition: forbidden` route renders as a warning against itself rather than as an option, because that is what it is: `arch/coupling` documents `depcruise` in order to say a bare `dlx depcruise` fetches an npm dependency-confusion placeholder that exits 0 having done nothing.

The output obeys the record conventions: one paragraph is one source line, ` - ` never U+2014, and any repository link is an absolute GitHub URL because the file ships in a plugin.

## Evidence triage - the only place information can be silently destroyed

A token-level diff of each record's fallback prose against its frontmatter splits the eleven:

| population | records | prose-only tokens |
|---|---|---|
| pure duplication | `complexity-gate`, `martin-metrics`, `complexity`, `dead-code`, `hidden-coupling`, `size` | 0, 5, 6, 6, 7, 12 |
| prose carries more | `over-abstraction`, `cycles`, `coupling`, `layering`, `over-decomposition` | 50, 116, 120, 147, 174 |

The excess in the second population is measured smoke-run observation: 1090 edges thinning to 122, dependency-cruiser 18.2.0, pnpm 9.15.9 against 11, `--no-config` discarding `--ts-config`, `.madgerc`, `tsconfig.app.json`. `docs/audit/typescript-lens-smoke-run.md` already carries all of it - 9.15.9, 18.2.0, `--no-config`, 281, `totalCruised`, 1090, `tsconfig.app.json`, 45 warnings and 31 warnings all occur in that file - and the prose being deleted already links to it.

**The rule, and it is absolute: no record body is touched until every claim in its fallback prose is traced.** Each claim resolves to one of three dispositions, recorded per record:

- **operative and present in a route field** - nothing to do.
- **operative and missing** - it goes into the route field it belongs to, before the prose is deleted.
- **measurement** - it belongs in the smoke-run doc. Present there, nothing to do; missing, it is added there first.

Anything that fits none of the three is a conscious drop and is recorded as one. The six pure-duplication records go first, because they prove the generator with no triage risk.

## The obstacle: the transcription guards are anchored on hand-written sentences

`tests/scripts/test_python_fixture_harness.py` anchors **19 of its 50 `INVOCATIONS` - the whole arch set** - on paragraphs of `## Tooling fallback`, through `_fallback_paragraphs`, which raises by design when a record has no such section. Each entry carries a `record_quote` lifted verbatim from that prose.

Those quotes are hand-written prose sentences, not command strings, and **15 of the 19 carry no `argv` at all**. `arch/layering/grimp`'s quote is "Record the offending `file:line` for each violation."; `arch/complexity-gate/xenon`'s is the bolded threshold directive. Regenerating the section breaks every one of them unless the generator reproduces each sentence character-for-character, which would put the generator's wording on a treadmill against 19 test constants and would make the routes answer to the prose again - the inversion this issue exists to end.

These properties are **prose-drift instruments**. They exist to catch a prescription in prose diverging from the declared forms. Under generation that divergence is structurally impossible, because the prose *is* the routes; and for a migrated record the routes-to-`INVOCATIONS` oracle already owns the binding, in both directions across `argv` and `forms`.

So every property anchored on a fallback paragraph or on the `record_quote` source line is scoped to records still declaring `tooling:`, through one helper stated once rather than a condition repeated per property. The arch `INVOCATIONS` entries stay - the oracle needs them, and `record_quote` stays on them as the record-provenance note it will still be for the unmigrated domains.

Two things verified before committing to this:

- The `assert skipped` sibling-lens dead-code guard is fed **exclusively by four `security/*` semgrep entries**, so exempting arch does not turn it into dead code.
- All eleven arch records project a non-empty `tooling`, so `test_every_tooling_record_offers_a_typescript_lens` and the empty-tooling branch of the fallback-section test are unaffected either way.

What the prose properties watched and the oracle does not is a gap this narrows rather than closes: the oracle binds command routes, so a `procedure` or `library` route's prose was watched by the prose properties and is watched by nothing after generation. Under generation there is no prose to watch - the route note *is* the prose - so the residual risk is a wrong route note, not a drifted one. Nothing in this issue closes that, and #58 already carries it as the epic's main residual risk.

## What this changes about #54

#54 asks the transcription guards to watch the whole record rather than one section, because a prescription written in `## Fix` is invisible to them. On a migrated record there is no longer any prescription outside the frontmatter for them to watch, so #54's scope shrinks to the records still declaring `tooling:` as they wait to migrate. It is not resolved and it is not unaffected; the issue gets a comment saying which.

## Acceptance criteria

- [ ] `scripts/render_check_tooling_fallback.py` renders `## Tooling fallback` in place from `routes:`, keyed on the declared schema, with a `--check` mode wired beside the two existing integrity gates
- [ ] The rendered section carries a marker saying it is generated and that the frontmatter is what to edit
- [ ] `evidence:` is specified and validated in `audit_checks.py` as an optional record-level field, rejected empty where present
- [ ] Evidence triage recorded per record, every claim traced to a route field, a smoke-run doc, or a recorded drop
- [ ] All eleven arch record bodies carry the generated section and no hand-written duplicate
- [ ] The fallback-paragraph and `record_quote` properties are scoped to records declaring `tooling:` through one helper
- [ ] The arch `INVOCATIONS` entries are retained and the routes oracle still binds them in both directions
- [ ] `test_a_record_that_classifies_a_tool_states_a_fallback` passes on the generated sections
- [ ] The generator ships with unit tests and does not lower coverage
- [ ] `--check` is mutation-verified: an edited generated section fails it, and an edited route changes what it renders
- [ ] Full suite green, ruff clean, all three integrity gates exit 0
- [ ] #54 carries a comment recording what this changed about its scope

## Out of scope

The eight unmigrated domains (the generator covers them the moment they declare `routes:`, and none does today). Deleting the harness's Markdown-parsing helpers, which still hold the 66 legacy records. Closing the wrong-route-note risk, which is #58's.
