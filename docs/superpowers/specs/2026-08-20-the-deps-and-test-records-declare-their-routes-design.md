# The deps and test records declare their routes

Issue #67. Stage 4's second unit on epic #58, and the first one that migrates records rather than extending the schema they are written in.

**Status.** Written and executed without the user's spec review gate, at their explicit instruction, as #66 was. Three decisions below were put to them before the spec was written and are recorded with their answer: where the schema hole this unit hits gets fixed, whether `argv_by_manager` keeps its name, and whether the round runs autonomously. Every other decision records the alternative it rejected and the measurement that decided it.

## The problem, measured

`deps` holds 6 records and `test` holds 7. Counted on `main`:

```
hand-written rows: 31 over 16 checks
by domain, rows:   deps 8, docs 3, security 12, test 8
by domain, checks: deps 6, docs 1, security 4, test 5
routed rows:       19 over 10 checks
records:           77, of which 11 declare routes (all arch)
```

So these two domains own **11 of the 16 transcribed checks and 16 of the 31 rows**. The issue body said 8 of 16 when it was filed, from memory rather than from a count, and #68's "the other 8" was the same mistake: `docs` and `security` own 5 checks and 15 rows, the four `security` checks naming three tools each. Both bodies are corrected.

Two of the 13 records carry no python tooling at all and so no row: `test/assertion-strength` declares neither `tooling` nor `needs` and states its review procedure in prose, and `test/new-code-coverage` declares `tooling: {any: [diff-cover]}`.

## Scope

Migrate all 13 records to `routes:`, delete each one's `## Tooling fallback` section, and delete the 16 rows those records contributed to `INVOCATIONS`, which is left holding the 15 rows of `docs` and `security`. The harness then reads every `deps` and `test` command from the record that prescribes it.

Three mechanism changes come with them, each with its first users in this unit rather than ahead of them: a command route that prescribes a command for some partitions and none for others, forms derived from those per-partition commands, and a round-owned home for a supplied route.

## The schema hole: a partition the record prescribes nothing for

`deps/inventory` prescribes a `cyclonedx-py` subcommand per dependency file and **nothing at all** for a PEP 751 partition. `deps/vulnerabilities` prescribes `pip-audit --locked .` for that same partition, the `-r` mode where a requirements file exists, and nothing for a uv, poetry or pipenv tree. The transcription expresses this directly: `argv_by_partition` pairs the partition with `()`.

A route cannot say it. The loader requires a non-empty `argv` on every `kind: command` route, and `argv_by_manager` is an override map read as default-plus-overrides, so a partition the map does not name inherits the shared command rather than having none. #66 recorded this as a third schema question, found while threading the first two.

**Decided: the shared `argv` becomes optional on a command route that carries per-partition commands, and an unnamed partition then has no command.** The loader keeps rejecting a command route that carries neither. This threads with no further change: `_argv_by_partition` already reads `route.argv_by_manager.get(partition, route.argv)`, which with an empty shared argv yields `()` for every unnamed partition, which is the shape the transcription carries today.

Rejected: a separate field naming the partitions with no command, which states in a second place what an absent key already states, and is a key whose deletion is silent; and inventing a shared argv for these two routes, which would prescribe `cyclonedx-py requirements` for a partition carrying no requirements file and `pip-audit --locked .` for one carrying no PEP 751 lock, both of which run and answer about nothing.

One shape stays unexpressed, stated here rather than given a spelling for nobody: a route with a shared `argv` **and** one partition that must have no command. No record in the tree is that shape. `deps/hygiene`'s pipenv case is not it - `deptry` there is a command that runs and raises, which the record says and the harness records.

## A second shape stays unexpressed: a tool the record refuses with no command line to refuse

Found while migrating `test/coverage-reach`, and recorded here because the decision was taken during the migration rather than ahead of it. The record forbids reaching for `c8` around a Vitest command, and backs the prohibition with measurement: `c8` there reported 96.35% statements and 69.56% branches over three files where the provider-based measurement of the same tree reported 8.05% and 5.86% over 339, which the record calls a false clean worse than `no-evidence`. It also keeps `c8`'s plain form as the measurement for a runner whose tests run in the process it wrapped. So one tool, two routes, opposite dispositions.

The schema cannot carry that. `disposition: forbidden` is valid only on a `kind: command` route, because a route prescribing no command has nothing for a consumer to run instead of, and the record writes no `c8` command line for either case - not the wrapping it refuses, and not the plain form it keeps. Writing an argv to earn the label would invent a command, which migration-is-not-correction forbids. The three requirements cannot all hold, and the two kept are the loader's rule and the no-invented-argv constraint.

So the two `c8` routes are `kind: procedure`, separated by `applies_when`, both tiered, with the prohibition as the bolded first sentence of the refusing route's note and that route written first. Nothing is lost to a reader. What is absent is a field a consumer can filter on: a record can say "here is a command, never run it" and cannot say "here is a tool, never reach for it in this situation" as anything but prose. `test/mutation`'s bare-name hazard is the same shape and is stated the same way.

Rejected: relaxing the loader's rule so a procedure route may carry a disposition. Every non-command route in the tree carries the default today, so the field conveys nothing there and would start conveying something in one record only. That is a schema change, and this unit's schema change was decided and landed before any record migrated, deliberately.

## `argv_by_manager` is renamed to `argv_by_partition`

A python route's keys have to be the fixture lens's partition names, because `_argv_by_partition` raises on a key outside `PARTITIONS` rather than threading a command that silently never runs. Four of those five names are package managers and `pylock` is a lockfile standard, so the field's name is wrong on the key this unit has to write. #66 filed the mismatch as an open question to answer before these records were written.

**Decided by the user, against the recommendation this spec offered: rename the field to `argv_by_partition`.** The recommendation was to keep the name and document the exception; the rename was chosen instead, so the reasoning that supports it is recorded here rather than the reasoning that was rejected. A partition is the axis a language's targets split along: the package manager where one distinguishes the case, the lock standard where none does. That reading covers the existing `pnpm` and `yarn` keys and the new `pylock` one under a single word, and it removes a rename at the loader-to-harness boundary, where `Invocation.argv_by_partition` already carried the other name for the same thing.

The cost is a merged pilot's records edited for a naming change: `argv_by_manager` occurs once in each of four `arch` records, once in `CLAUDE.md`, once in `.agents/skills/audit/SKILL.md`, and in the loader, the harness and both test modules. It lands in its own commit, before any record migrates, so a rename and a migration are never in one diff. The `#66` spec and plan keep the old name: they record decisions as they were taken, and rewriting them would edit that record.

## Forms are derived from every command the route prescribes

Stage 3 derives a row's `forms` from its command routes' `(joined argv, disposition)` pairs, and #66 added the `then`. Neither reads `argv_by_partition`, because no python route has ever carried one. A route with no shared argv would therefore produce the empty string as a form, which `Invocation._check_forms` raises on - loudly, which is the only reason this is a design decision rather than a defect waiting in the fixture run.

**Decided: `_forms_for` returns one form per distinct command the route prescribes** - the shared argv where it has one, each per-partition command, and the `then` - each taking the route's disposition. The 19 `arch` rows are unaffected: no `lang: python` route among them carries per-partition commands.

This closes a gap in the transcription rather than reproducing it. `deps/inventory` declares three forms today and prescribes four commands: `cyclonedx-py requirements` and `cyclonedx-py pipenv` are commands the row runs on two partitions and declares nowhere, and the guard that would catch a `runs` form no command carries cannot see a command no form declares. The derived set carries all four. `cyclonedx-py environment`, which the record names as the more accurate option where a tree exists and which no partition runs, becomes a `disposition: alternative` route and keeps its form.

## A supplied route needs a round-owned home

`deps/inventory` and `deps/vulnerabilities` each carry a **supplied** route: a command this round contributed for a partition the record prescribes none for, held apart from the record's own so that the results never render it as `record_argv`. Stage 3's round-owned overlay carries `COMPLETIONS` only, so a migrated record's supplied route has nowhere to live.

**Decided: a `SUPPLIED` mapping keyed `(check, tool)`, beside `COMPLETIONS` and read by `routed_invocations` the same way.** It carries the steps and the note; `Invocation._check_supplied` already rejects an unexplained supplied route, a partition carrying both a prescribed and a supplied route, and a supplied route beside `in_env`, so the overlay needs no validation of its own.

Rejected: a `supplied:` field on the route. A supplied route is by definition one the record does not prescribe, so a record declaring it would be prescribing it, and the distinction the field exists to preserve is gone.

## Migration is not correction

A record whose prescribed command is incomplete stays incomplete. The gap is this round's finding, and the completion that fills it is round-owned: `COMPLETIONS` holds four entries today and every one of them is for a **migrated** `arch` record, so the pilot already settled this by example. `arch/complexity`'s `radon` route still reads `argv: [radon, cc]` with no path, and `src` still arrives from the overlay.

So four of the 16 migrated rows keep their completion and `COMPLETIONS` grows from four entries to eight: `deps/freshness`'s `uv` interpreter path, `deps/hygiene`'s `deptry` scan root, `test/coverage-reach`'s `--cov=<pkg>` fill, and `test/isolation`'s timeout. The route prescribes what the prose prescribed, to the token.

Two consequences worth stating, because both look like oversights:

- **A placeholder stays where the transcription put it.** `deps/vulnerabilities` writes `<requirements>` in prose and the pip partition's transcribed argv carries the literal `requirements.txt`, with no completion and a note saying the placeholder resolved to the fixture's own file. The route carries the same literal. Moving it into a completion would need a per-partition completion mechanism that nothing else wants, and it would move a token out of `argv`, changing the provenance of a command that runs today. `requirements.txt` is the conventional name rather than a value naming anyone's environment.
- **A tool the record warns against is not `disposition: forbidden` merely because it cannot run.** `_project_tooling` drops a `forbidden` route's tool, so declaring one would shrink `tools_named_in_records()` and delete a row the exact-set guard expects. `safety` is unusable unauthenticated and `cosmic-ray` needs a session config the record does not write; both stay offered routes that prescribe no command, which is what their rows say today.

## `ungranted_note` becomes routes, not prose

Seven of the 13 records carry a long `ungranted_note` describing what still answers when a grant is withheld: a registry comparison per pinned package for `deps/freshness` and `deps/licenses`, a manifest and lockfile read for `deps/hygiene`, a coverage-exclusion config read for `test/coverage-reach`, a non-determinism grep for `test/determinism`, an I/O read for `test/isolation`, and `deps/transitive-licenses`' delegation to its sibling.

`answers_ungranted` accepts only the sentinel `none`. There is no prose slot on the routes schema, and that is the point: **each of those notes becomes an untiered answering route**, `kind: procedure`, carrying the note's own prose. `_silenced_languages` counts a procedure route as answering, so an untiered one un-silences the language exactly as the note claimed, and the claim is now a route the harness enumerates rather than a paragraph nothing reads. `test/mutation`'s `ungranted_note: none` becomes `answers_ungranted: none`.

A route's `kind` follows what the record prescribes, not what the tool is: `command` where the record writes a command line, `library` where the tool is imported inside the target's own code, `procedure` where the record prescribes an operation and no command line, `subject` where the route only inspects what the check is about.

## What the loader rejects, changed

| shape | disposition |
|---|---|
| `kind: command` with neither `argv` nor `argv_by_partition` | still rejected: a command route with no command |
| `kind: command` with `argv_by_partition` and no `argv` | now accepted: the partitions it does not name have no command |
| `own_runner` naming a partition absent from `argv_by_partition` | unchanged, reworded for the rename |
| `then` repeating a command the route prescribes | unchanged, and now compared against the per-partition commands too |

## What this does not do

- **It does not delete the prose parser.** `docs` and `security` still transcribe, so `PROSE_FALLBACK_CHECKS` shrinks to their 5 checks and every property scoped by it keeps a subject. #68's.
- **It does not touch `record_quote`.** The field is still carried by 15 rows. #68 retires it.
- **It does not rename `argv_by_partition` in the `#66` spec or plan**, for the reason stated above.
- **It does not close the reach hole.** A route that parses is not a route that runs, which is why this unit runs the fixtures on a migrated check in each domain rather than resting on the suite. #44's.

## Verification

- The 16 migrated rows are compared field by field against their pre-change values: `argv`, `argv_by_partition`, `own_runner`, `completion`, `then`, `in_env`, `findings_stream` and the supplied steps identical; `record_quote` empty; `forms` and `note` as this design states, with every difference named and justified rather than absorbed.
- The 19 `arch` rows are compared and must be byte-identical, which is the claim a green suite cannot make.
- `INVOCATIONS` holds exactly 15 rows over the 5 `docs` and `security` checks, asserted rather than eyeballed.
- Every property this unit narrows or widens is proven non-vacuous, by mutation where it reads a population and by deletion where it reads a guard. A property whose premise this migration falsifies is repaired against the new premise rather than left green.
- A live fixture run on the seeded partitions for at least one migrated `deps` check and one migrated `test` check.
- `uv run pytest tests/ -q`, `ruff check`, `ruff format --check`, and all four `--check` renderers.
