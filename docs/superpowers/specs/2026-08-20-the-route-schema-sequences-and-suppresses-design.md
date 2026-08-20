# The route schema sequences a second command and suppresses a runner

Issue #66. Stage 4's first unit on epic #58, and the one the other three wait on.

**Status.** Written and executed without the user's review gate, at their explicit instruction. Every decision below therefore records the alternative it rejected and the measurement that decided it, so a reader can re-open any one of them on evidence rather than on recollection.

## The problem, measured

Stage 4 migrates the 66 records still declaring `tooling:`/`needs:` to `routes:`. Two of them cannot be migrated at all. Counted over `INVOCATIONS` on `main`:

```
hand-written entries: 31 over 16 checks
routed rows: 19 over 10 checks
then:        [('test/coverage-reach', 'coverage.py')]
own_runner:  [('deps/inventory', 'cyclonedx-py', ('uv',))]
```

`test/coverage-reach` prescribes `coverage run -m pytest` followed by `coverage report --show-missing` as one route. Dropping the half that prints the report leaves a route that looks like a tool which produced nothing. `deps/inventory` prescribes `uv export --format=cyclonedx1.5 --frozen` on a uv-locked partition - a command of a different tool from the one the row is keyed on - and the launcher must put nothing in front of it, or the row reports the fetched package's version as the one that answered.

A `Route` today carries `lang`, `kind`, `tool`, `package`, `argv`, `argv_by_manager`, `disposition`, `needs`, `in_env`, `findings_stream`, `applies_when`, `alone_insufficient` and `note`. None of them says either thing.

## Scope

This unit adds the two fields, validates them, and threads them through the enumeration the harness already reads. **It migrates no record.** The first real users arrive in #67 with `deps` and `test`.

That separation is a decision, not an accident of sequencing. The alternative - land each field with its first user in one PR - is the better instinct in general and wrong here: `test/coverage-reach` and `deps/inventory` are two of the heaviest record migrations in the family (the first carries the whole `c8` false-clean measurement in its TypeScript prose, the second three paragraphs of measured `cyclonedx-py` subcommand behaviour), and a schema change entangled with them is one review surface where there should be two.

The cost of the separation is a field with no in-tree user, which is `arch/over-abstraction`'s unexercised-configurability finding pointed straight at this change. That check's own `alone_insufficient` answers it: "a planned, documented extension point - one implementer, or one config value, today - is a suppression, not a finding, recorded with its reason." The reason goes in the field docstrings, naming the first users and the issue that migrates them.

## `own_runner` has five candidate users today, which decides its shape

`own_runner` looked like a one-record field. Computed over every route in the tree, **nine routes carry a runner-led shared `argv`, and five of them are candidates to annotate**: the `dependency-cruiser` route of `arch/coupling`, `arch/cycles`, `arch/layering` and `arch/over-decomposition`, each `npx --package typescript@^5 --package dependency-cruiser ...`, plus `arch/size`'s `npx cloc`. The other four are those same records' `dlx depcruise` routes, which they declare `disposition: forbidden` - a route named only to warn against is never run, so it needs no claim about what would go in front of it. Every one of the five argvs is complete as written, in exactly this field's sense, and none says so.

Nothing observes the silence: the Python lens selects `lang: python` only, and `arch/size` carries no python tooling. So it is a silence that happens to be harmless rather than a correct absence, and a TypeScript launcher would mis-prefix all five.

So the field takes two shapes:

- `own_runner: true` - every command the route prescribes is complete as written, its shared `argv` and its per-manager overrides alike. The five above, four of which carry runner-led `pnpm` and `yarn` overrides beside their runner-led shared argv.
- `own_runner: [<manager>, ...]` - only the named managers' overrides are complete - `deps/inventory`'s `uv`, where the other three subcommands are fetched normally.

Rejected: a single list-only shape, which cannot say the five; and deriving the flag from whether the argv's first token is the route's tool, which would be correct on all five and on `deps/inventory` today and is still the wrong mechanism - inferring a claim from the shape of a string is what this epic exists to delete.

**Corrected during implementation, and the correction is the interesting part.** This section first said `true` belonged to a route carrying a shared `argv` and was *rejected* beside `argv_by_manager`, on the reading that a blanket claim beside per-manager commands is ambiguous. The record set refutes it: four of the five candidates carry `pnpm` and `yarn` overrides that are runner-led too, so that rule refused `true` on them and left a manager list able to name only `pnpm` and `yarn` - while the shared `npx` form, which is what an unnamed manager runs, had no way to say it was complete at all. A validator that forbids the field's own users from using it reintroduces exactly the silence the field exists to delete, so the rule went and `true` became a claim about every command the route prescribes.

One shape neither spelling reaches: a route whose shared `argv` needs no runner while one manager's override does. `true` over-claims it and a list cannot name the shared command. No route in the tree is that shape, so it stays unexpressed rather than acquiring a third spelling for nobody.

**This unit does not annotate the five.** Doing so reopens a merged pilot's eleven records to add a flag whose effect nothing can measure until a TypeScript harness exists. Recorded as a gap this leaves open rather than one it closes.

## `then` contributes a form

Stage 3's enumeration derives a row's `forms` from its command routes' `(joined argv, disposition)` pairs. The hand-written `test/coverage-reach` entry carries **both** of its commands as `runs` forms. A `then` contributing no form would therefore drop `coverage report --show-missing` from the migrated row's forms in #67, and every property reading forms would still pass - the failure mode this epic keeps producing.

So each command route contributes its argv's form and, where it carries one, its `then`'s form, both taking the route's disposition. `Invocation._check_forms` already rejects a duplicate form string, so two routes whose `then` collides fail as the ambiguity they are.

The row's executed `then` comes from the single `disposition: runs` route, the same one its `argv` comes from. A `then` on a `superseded` or `alternative` route is a form the record names, not a command this round runs, and it is not rejected: forms are what the record offers, `then` executed is what ran.

## Threading `own_runner`'s list shape forces `argv_by_manager` through with it

The enumeration builds a row's `argv` from `runs[0].argv` and reads `argv_by_manager` not at all - no `lang: python` route has ever carried one. So `own_runner: [uv]` threaded on its own would name a partition with no prescribed command, which `Invocation._check_own_runner` rejects by design: "the suppressed prefix applies to nothing."

This unit therefore also threads `argv_by_manager` into `Invocation.argv_by_partition`. Three things make that more than a rename:

- **A route may carry both a shared `argv` and `argv_by_manager`** - the loader requires a non-empty `argv` on every command route, and the four `arch` `dependency-cruiser` routes carry both. The route semantics are default-plus-overrides; `Invocation` admits `argv` or `argv_by_partition` and not both. So a route carrying both expands to one entry per partition, each the override where the manager names one and the shared argv otherwise.
- **A python route's manager keys must be the lens's partitions.** `argv_by_manager` has only ever been written for `pnpm` and `yarn`. A python route naming a manager outside `PARTITIONS` would thread into an `argv_by_partition` entry `prescribed()` never finds - a command that silently never runs. The enumeration raises on it, which is also the answer to the vocabulary question #66 filed as open: for a python route, the keys are partition names, `pylock` included, even though `pylock` names a lockfile standard rather than a manager. Renaming the field across the records is not in this unit.
- **Nothing existing changes.** The 19 routed rows come from `lang: python` routes, none of which carries an `argv_by_manager`, so the enumeration's output is unchanged. That is an assertion this round verifies rather than assumes: the 19 rows are compared field by field before and after.

## What the loader rejects

Each rejection names the route and says what the shape would mean, in the style of the existing route errors.

| shape | why it is rejected |
|---|---|
| `then` or `own_runner` on a non-`command` route | nothing to sequence after, and no launcher prefix to suppress |
| `then` present but empty, or not a list of strings | an empty follow-up is the absence the field exists to prevent |
| `own_runner: [<manager>]` with no `argv_by_manager` | names managers the route does not distinguish |
| `own_runner: []` | loads to exactly what an absent key loads to, so it claims nothing while reading as a claim - and it is what deleting the last name from a list leaves behind |
| `then` repeating a command the route already prescribes | the two halves of the sequence are one command written twice, so the route's declared forms carry the same string twice - the ambiguity a form list cannot hold |
| a manager in `own_runner` absent from `argv_by_manager` | the suppression applies to no command |
| `own_runner` beside `in_env: true` | an `in_env` route needs the launcher's prefix to reach the materialized environment, so suppressing it is not a command that runs as written, it is one that never arrives |
| `own_runner` neither `true` nor a list of strings | `false` is rejected too: the field's absence already says the launcher applies, so writing it means a claim, and `false` is the same claim spelled as its own opposite |

The last two rows mirror invariants `Invocation` already enforces on its own field, deliberately: the same rule stated in both places is the pattern `needs` and `tooling` already follow, and the validator checks the repetition rather than trusting it.

## How the new rejections are exercised

By synthetic records, not by real ones. Stage 3 established the pattern for raises that fire on data no record carries: substitute the record loader, clear the enumeration's cache on both sides, assert the message. No record in the tree carries either field until #67, so every guard here is in that category, and a guard nothing exercises is the one that turns out not to fire.

## What this does not do

- **It does not close the reach hole.** A route that parses is not a route that runs; `arch/size`'s `cloc` argv and `arch/coupling`'s `typescript@^5` pin remain mutable with the suite green. #44's.
- **It does not let a route say a manager has no command.** `deps/inventory` prescribes nothing at all for a PEP 751 partition, and a command route must carry a non-empty `argv`, so absence-for-one-manager is unexpressible: an unnamed manager inherits the shared argv rather than having none. #67 needs that, and it is a third schema question rather than a consequence of these two. Recorded here because it was found here.
- **It does not move the round-owned overlay.** `deps/inventory` and `deps/vulnerabilities` both carry a supplied route this round contributed, and the stage 3 overlay carries `completion` and its note only. Extending it is #67's, with its users.

## Verification

- Every rejection above has a test asserting the message, each shown to fail on the mutation that removes its guard.
- The 19 routed rows are compared field by field against their pre-change values, to hold "nothing existing changes" to something measured.
- `docs/audit/python-fixture-expectations.md` re-renders byte-identical, reported as a gate that ran and not as evidence: neither it nor `python_fixture_spec.py` imports the lens.
- `uv run pytest tests/ -q`, `ruff check`, `ruff format --check` and both `--check` renderers.
