# The Python fixture harness reads its routes from the records

Issue: #63. Stage 3 of epic #58, in the form the record set makes executable today.

## Goal

The pilot put `routes:` on the eleven `arch` records and deleted the prose the routes replaced. The harness did not move with it: `scripts/run_python_fixture_lens.py` still hand-maintains an `Invocation` table, and the comment at `run_python_fixture_lens.py:642` says outright that on a migrated record `record_quote` is no longer a citation, because the prose it was lifted from is gone. It stays only because it is the last thing an argv is held against.

So a migrated record's prescription exists twice: as data in the record, and as a transcription in a Python table, with an oracle asserting the two agree. This spec removes the second copy for the records that have migrated, and leaves it standing for the records that have not.

## The staging correction this spec is built on

#58's stage 3 says the Markdown-parsing helpers and the properties built on them go. Measured against this tree, they cannot: `INVOCATIONS` holds 50 entries over 26 distinct checks, of which 10 are migrated `arch` records and **16 are still prose-anchored** - the six `deps` checks, `docs/docstring-coverage`, four `security` checks and five `test` checks. Those 16 transcriptions are held against their records by exactly the properties stage 3 proposes to delete, so deleting the parser would remove the only guard on 16 live transcriptions in the same round that removes the guard's subject for the other 10.

The parser therefore survives this work, scoped to the 66 unmigrated records, and goes when stage 4 has migrated `deps`, `docs`, `security` and `test`. `#54` and `#56` close there rather than here. `fallback_lives_in_prose()` already keys on the schema a record declares rather than on whether a section is present, so the two populations coexist by design rather than by accident.

## The enumeration rule

For each migrated check, group its `lang: python` routes by `tool`, dropping any route naming no tool. Each group is one row.

- The row's argv is the argv of its `kind: command`, `disposition: runs` route where it has one, and otherwise the row prescribes no command and is recorded as such rather than run.
- The row's forms are the `(argv, disposition)` pairs of every `kind: command` route in the group.

Two properties of the rule are load-bearing and neither is incidental.

**Rows key on `(check, tool)`, not on route.** `arch/cycles` declares four `python` routes and has three rows, because its `superseded` `pydeps --show-cycles` is a second form of the same tool rather than a second row. A rule keyed on routes would run a superseded form as though the record prescribed it.

**A non-`command` kind still produces a row.** `arch/complexity-gate`'s three `subject` routes are three rows recorded as prescribing no command. The engine already models that outcome and grades it, so dropping those rows would silently shrink the round's evidence rather than simplify it.

`arch/size` declares no `python` route and so has no rows, which is what the table says today.

### Verified against the table before being written

The rule was run against the eleven migrated records and compared with the 19 table entries belonging to them, on argv and on forms:

```
derived rows: 19   table rows: 19
keys only in derived: []
keys only in table:   []
mismatching rows: 0
```

Extended to the two other fields a row carries from its route, over all 19 rows rather than the command ones alone, `findings_stream` and `in_env` agree with zero mismatches.

That is the evidence the rule is a derivation of the existing table rather than a re-authoring of it.

## Route selection: `lang: python` only

The harness selects `lang: python` routes and no others.

The alternative considered was `python` plus `lang: any`, which has a real argument behind it: `arch/size`'s `cloc` route says in its own note that a one-shot runner fetches the tool whatever the partition's language, so an `any` route is applicable to a python partition by the record's own claim. Selecting it would bring `arch/size` into the round and make its argv the thing that actually executes, which is the only way a mutation to that argv gets caught.

It is rejected here for two reasons. It gives the Python lens a node dependency, so a partition without node grades the row `no-evidence (tool-unavailable)` and the generated expectations become a fact about the machine rather than about the fixture. And it changes the set of checks the round runs: `arch/size` carries no `python` tooling, so it is absent from both the expectations' declared scope and the three-way equality below, and enumerating it would mean editing the expectations to admit a check whose route no fixture verifies. Widening the selection is a scope decision that belongs with `#44`, where running a route against a seeded fixture is the deliverable.

A third option - selecting `any` routes that need no registry fetch, so `wc -l` runs and `npx cloc` does not - is rejected outright: `wc` carries `disposition: alternative`, reached only once neither `cloc` nor `tokei` is available, so running it unconditionally would contradict the record's own precedence.

## Three ownership lines

#58 draws record-owned against round-owned. A third line is needed, and naming it is part of this work.

**Record-owned.** What to run: argv, forms and their dispositions, `findings_stream`, `in_env`, `needs`. Read from the record, never transcribed.

**Round-owned.** What a partition needed that the record did not say: `completion`, `supplied_by_partition`, `supplied_note`. These stay in the harness because they are the round's actual deliverable, and #58 is explicit that moving them into the record destroys the finding the harness exists to produce.

**Engine-owned.** How to grade what came back, and how to obtain a version: `NONZERO_EXIT_MEANING`, `VERSION_PROBE`, `TOOL_PACKAGES`. These are keyed by tool rather than by check, and that is the reason they stay: `grimp` is named by six `arch` records, so a per-tool fact carried in a per-check record is six copies to keep in step, needing a family-wide agreement guard of the kind `needs` already has. The properties over these tables are re-derived from the routes rather than from the table, so a tool that a route runs and no table grades still fails.

The line between record-owned and engine-owned is prescription against interpretation. A record says what to run. Whether a nonzero exit from that command means findings, a failure or something ambiguous is the engine's grading vocabulary, and the engine owns its own vocabulary.

## What the table becomes

The 19 entries belonging to migrated checks go. Four survive, as an overlay keyed `(check, tool)` carrying a `completion` and the reason it was needed:

| check | tool |
|---|---|
| `arch/complexity` | `radon` |
| `arch/complexity` | `xenon` |
| `arch/cycles` | `pydeps` |
| `arch/dead-code` | `vulture` |

The reason is not decoration and not prose that could live in the record: each of the four reads as a finding about what the record failed to say - `radon cc` takes a path and the record names none, `xenon` needs both a threshold and a path, `vulture` needs both trees passed because a symbol referenced only by a test is not dead. That is the round's deliverable in one sentence, and `test_a_completed_argv_says_why_it_had_to_be_completed` already refuses a completion travelling without it. None of the 19 uses `argv_by_partition`, `own_runner`, `then`, `supplied_by_partition` or `supplied_note`, so the overlay needs no field beyond those two today. It is a mapping rather than a dataclass: a four-entry overlay beside a 31-entry `INVOCATIONS` is two shapes, and the alternative - one dataclass with most fields unused on migrated rows - keeps a slot for every prescription field on exactly the rows that must not carry one.

`INVOCATIONS` keeps its 31 entries for the 16 prose-anchored checks, `record_quote` included, because that field is still the only thing holding those transcriptions to their records.

**A property asserts that no migrated check has an `INVOCATIONS` entry.** Without it the two enumeration paths can both claim a row, and the failure is silent in the direction that matters: a stale entry keeps a check running after its record stops being the source, so an edit to the record has no effect and the suite stays green.

## The parser stays, scoped, and the scoping is asserted in both directions

`PROSE_FALLBACK_CHECKS` narrows the prose-anchored properties by the schema a record declares, and `test_the_prose_fallback_scope_is_not_empty_and_holds_no_migrated_record` already asserts a migrated record is not in it. That is one direction.

The other direction is new and is the one this change opens: a check that migrates out from under a live table row must fail loudly rather than quietly stop being read by anything. The property above - no `INVOCATIONS` entry for a migrated check - is that assertion, and it is why it is a property rather than a convention.

Every prose-parsing helper is then either still reached by a property covering the 66 unmigrated records, or deleted. A helper reached by nothing is not left in place against a later stage that might want it: the record set is in git, and a helper with no caller is indistinguishable from a helper whose caller was deleted by mistake. The module has 24 private module-level helpers, of which the prose-parsing set is a subset this spec deliberately does not fix a number for: which of them survive is settled by which properties survive, so the count is an output of this work rather than an input to it, and #58's figure is not carried over.

## The oracle dissolves, with its reason recorded

`test_a_migrated_records_routes_agree_with_the_verified_table` exists to catch two copies of one prescription disagreeing. With one copy it has no subject, so it is deleted rather than weakened, and the reason is written where the next reader will look for it rather than left in a commit message. `test_every_migrated_record_is_in_the_domain_the_oracle_covers` guards one of that oracle's three reach dimensions and goes with it.

Both docstrings state that the reach hole is `#44`'s and `#58`'s territory, and that stays exactly as true afterwards. `arch/size`'s `cloc` argv and `arch/coupling`'s `typescript@^5` pin can each be mutated with the suite green today, and can afterwards. What changes is the hole's shape rather than its size: with one copy instead of two, a wrong argv is a wrong route rather than a disagreement between a transcription and a record, and whether a route is true is answered by running it against a seeded fixture. This buys simplicity, not defect-finding power, and no acceptance criterion here may be read as claiming otherwise.

## The guard, and the guard this is not

The obvious candidate was a byte-identical re-render of `docs/audit/python-fixture-expectations.md`. It is not a guard on this change and the spec does not use it as one: `render_python_fixture_expectations.py` reads `python_fixture_spec.py` and neither imports `run_python_fixture_lens.py`, so that file re-renders identically whatever the enumeration does. It stays a gate that must pass, as it must for every change, and it proves nothing about this one.

What does bridge the two is `test_the_harness_runs_exactly_the_checks_the_expectations_declare`, which holds three views of one set equal: the records carrying `python` tooling, the checks the harness runs, and the checks the expectations grade. It reads `INVOCATIONS` directly, so enumerating migrated checks elsewhere breaks it, and restating it is part of this work rather than a consequence to absorb. Its new form is a union over the two enumeration paths, verified against this tree before being written:

```
records with python tooling: 26
enumerated from routes: 10
table rows for prose checks: 16
union == with_python: True
missing from union: []   extra in union: []
```

A check dropped by the enumeration, invented by it, or claimed by both paths at once fails that equality. That is the property the change actually rests on.

The row-level derivation comparison stays evidence rather than becoming a test. Frozen into the suite as a literal expected set it would be a second copy of the prescription, which is the defect this whole stage removes; so it runs once against the pre-change table, its output goes in the PR, and what remains in the suite are the properties that hold shape rather than content.

## Acceptance criteria

- [ ] Every migrated check's executed command is derived from that record's `routes`. No migrated check's argv appears twice in the tree.
- [ ] The enumeration rule reproduces the 19 rows, keyed `(check, tool)`, on argv, forms, `findings_stream` and `in_env`, with non-`command` kinds producing no-command rows and grouped forms carrying every `kind: command` route's `(argv, disposition)` pair. The comparison runs against the pre-change table and its output goes in the PR.
- [ ] `record_quote` is gone from every migrated check's data, and the four surviving overlay entries carry a completion and the reason it was needed, and nothing else.
- [ ] A property fails if a migrated check has an `INVOCATIONS` entry.
- [ ] `NONZERO_EXIT_MEANING`, `VERSION_PROBE` and `TOOL_PACKAGES` stay engine-owned, and the properties over them read the tools a route runs rather than the tools the table names.
- [ ] The routes oracle and its domain guard are deleted, each with its reason recorded in the module.
- [ ] `PROSE_FALLBACK_CHECKS` still covers every unmigrated invoked check, and every surviving prose-parsing helper is reached by a property covering the 66 unmigrated records.
- [ ] `test_the_harness_runs_exactly_the_checks_the_expectations_declare` is restated as a union over the two enumeration paths and still holds all three views equal, so a check dropped, invented or double-claimed fails it.
- [ ] `uv run pytest tests/ -q` green, `ruff check`, `ruff format --check`, `render_handbook_traceability.py --check` and `render_python_fixture_expectations.py --check` green.
- [ ] The harness's mutation table is re-run under `PYTHONDONTWRITEBYTECODE=1`, and any mutation this change makes unreachable is recorded as such rather than deleted.
- [ ] #58's staging is corrected on the epic: the parser's deletion is stage 4's deliverable, stage 4 takes `deps`, `docs`, `security` and `test` first, and #54 and #56 close there.

## Out of scope

- Migrating any of the 66 remaining records. That is stage 4.
- Deleting the prose parser. That follows stage 4's first four domains.
- Widening route selection beyond `lang: python`. That is `#44`'s territory, and it changes what runs.
- Closing the reach hole on `arch/size`'s `cloc` argv or `arch/coupling`'s `typescript@^5` pin.
- The 38 command spans in the eleven `SKILL.md` files, and `#42`'s `yarn dlx` claim. That is stage 5.

## Testing

The behavioural guard is the three-way check-set equality above, restated as a union and held against the expectations' own declared scope. It is a live guard, unlike the re-render, and it is the reason route selection staying `lang: python` matters: widening it puts a check in the harness that the expectations do not grade, and the equality fails rather than the round quietly growing a row nothing checks.

Three further properties carry the design's invariants rather than its behaviour: no `INVOCATIONS` entry for a migrated check, every surviving prose helper reachable from a property over the unmigrated records, and every tool a route runs carrying an engine-owned grading rule. Each fails on a plausible future edit rather than only on a deliberate one.

The row-level derivation is verification, not a test, for the reason given above: kept in the suite it would reintroduce the second copy.
