# A route names the registry its tool comes from, so the runner stops being guessed

Issue #77, which also closes #28. A route's `lang` says which of the target's languages it applies to. Nothing says which registry its tool is published in, and the runner instruction picks a runner from the partition's package manager - so a `lang: any` route naming a PyPI package gets fetched from npm.

**Status.** Written and self-approved under autonomous mode, with no maintainer review gate. Every decision below records the alternative it rejected and how it was settled, so any one of them can be reopened on evidence rather than on recollection. The gate that was not granted is the review of the resulting PR.

## The decision was already taken: a field, not a convention in the argv

The nightshift ledger, issue #78, records it: `registry:` beside `package`, defaulting from `lang` where `lang` names a language, required on a `lang: any` or `lang: none` command route whose tool has to be fetched, with the loader rejecting a value outside a known vocabulary. Rejected there: baking the runner into the argv the way `arch/size`'s `npx cloc` does, because that is the infer-a-claim-from-a-string mechanism #66's spec rejected for `own_runner`, and nothing can validate it. That decision was posted to #77 during an earlier tick, so the tracker carries it too.

## Criterion 4's audit decides the field's population, so it was done first

"Every `lang: any` and `lang: none` command route in the family audited for the same shape." Computed over every route in the tree: 13 universal routes, of which exactly **three** are `kind: command`. The other ten are `kind: procedure`, nine naming no tool at all, so nothing about them is fetchable.

| route | tool | argv on `main` | what it is |
|---|---|---|---|
| `test/new-code-coverage[0]` | `diff-cover` | `[diff-cover, <report>, --compare-branch=origin/main]` | a PyPI package with a working, unrelated npm namesake - the hazard #77 is filed about |
| `arch/size[0]` | `cloc` | `[npx, cloc]` | an npm package with the runner baked into the argv - the convention #78 rejected |
| `arch/size[2]` | `wc` | `[wc, -l]` | a standalone binary in no registry at all |

So the field is required on two routes and impossible on the third, and that third is what needed a ruling the issue does not make.

## The rule, written so the loader can check it

`registry` is optional on a `kind: command` route and rejected on every other kind, since nothing else prescribes a command to put a runner in front of. Then:

- **Required** where `lang` is `any` or `none` and `own_runner` is not `true`. There and only there is the registry underivable: no language implies it, and the route does prescribe a command whose tool has to come from somewhere.
- **Rejected beside `own_runner: true`.** That field says the prescribed command is complete as written, so nothing is fetched and a registry names where a fetch that never happens would have gone. The loader already refuses `own_runner` beside `in_env` on the same logic - "an `in_env` route needs the launcher's prefix to reach the materialized environment, so suppressing it is not a command that runs as written, it is one that never arrives" - and this is that rule pointed the other way.
- **Rejected where it disagrees with `lang`.** A `lang: python` route declaring `registry: npm` is either a real foreign-registry case, in which case the record's `lang` is wrong and should be `any`, or a typo. Accepting it silently is how the field stops meaning anything. This is the pattern the loader already applies to `needs`, whose tool names must repeat the ones in `tooling`.
- **Rejected outside the vocabulary**, which is `pypi` and `npm` and nothing else, because those are the only registries any route in the tree fetches from. A member nothing uses is the vacuity this repository holds floors against.

**Rejected: a `registry: none` sentinel for the standalone-binary case.** It would be a second field saying what `own_runner: true` already says, and two fields for one fact drift apart. `arch/size`'s `wc -l` route declares `own_runner: true` instead, which is both the existing vocabulary for "nothing is fetched" and a fix in its own right - see below.

**Rejected: deriving and storing a registry on every language-specific command route.** `deps/vulnerabilities`' `pnpm audit` is a `lang: typescript` command route, and nothing about it is fetched: it is a subcommand of the target's own package manager, the second of the taxonomy's three kinds. A derived `npm` there would be inert at best and would suggest a fetch that must never happen. So the derivation is what a consumer computes when it needs a registry for a tool it is about to fetch, not a value written onto routes that fetch nothing.

## Two record edits, and why each is in scope

**`arch/size[0]`: `argv: [npx, cloc]` becomes `argv: [cloc]` with `registry: npm`.** #78's decision names this exact route as the rejected convention, so removing it is implementing that decision rather than widening it. It is also a defect on its own terms: the argv is a complete runner invocation and the route carries no `own_runner`, so the runner rule as written puts a second one-shot runner in front of it and a field reader gets a runner fetching a runner.

**`arch/size[2]`: the `wc -l` route declares `own_runner: true`.** Forced by the rule above rather than chosen: without it the loader would demand a registry for coreutils. It is also the fix for a live defect criterion 4's audit found - as declared, the runner rule fronts `wc -l` with a fetcher for a package named `wc`, which fails the way a missing tool fails, and this is the route the record's own note calls the one reached "once neither `cloc` nor `tokei` is available". The last thing that works was the one thing that could not.

## A broader inconsistency this deliberately does not fix

Computed while auditing: every route in the tree whose argv begins with a runner token carries `own_runner` absent rather than `true` - the four `dependency-cruiser` routes, their four `depcruise` `forbidden` siblings, `test/mutation`'s Stryker route, and `arch/size`'s `cloc`. A test docstring in `tests/scripts/test_audit_checks.py` argues about those very routes that "every command in them is complete as written", which is the claim `own_runner: true` exists to make, and none of them makes it.

That is not #77's subject and it is not fixed here. It spans six records and its right answer depends on whether the runner rule double-fronts a runner-led argv in practice, which is a question about the lens and the sweep rather than about the registry. Named here, in the PR body and on the ledger so an attended session can pick it up, rather than turned into a speculative issue or folded into this change. The one route this branch does touch, `cloc`, stops being an instance of it by losing its baked-in runner.

## What changes

- **`scripts/audit_checks.py`**: `registry` joins `ROUTE_FIELDS` and `Route`, with the four rules above and a `registry_for(route)` helper so the derivation has one implementation rather than one per consumer.
- **Two check records**: `test/new-code-coverage` gains `registry: pypi`; `arch/size`'s `cloc` route loses `npx` and gains `registry: npm`, and its `wc` route gains `own_runner: true`.
- **`audit/SKILL.md`**: the runner instruction derives the runner from the route's registry rather than telling an agent to read the note, which is criterion 3; and the three-kinds taxonomy is corrected so the runner comes from the tool's registry rather than the partition's language, which is what closes #28.
- **`CLAUDE.md`**'s record-schema paragraph documents the field, since it documents every other route field.
- **`docs/audit/sweep-obligations.md`**: the reading pass, and rows for whatever obligations the `audit/SKILL.md` edit adds.
- **Tests** for each rule, plus a population guard so the required case cannot go vacuous by the shape leaving the tree.

## What this enables next, and does not do here

`scripts/run_python_fixture_lens.py` hardcodes `uvx` and `uv run --with` for its probes, which is correct today because every route it runs is `lang: python` and python implies PyPI. Once a consumer needs a registry for a `lang: any` route, `registry_for` is what it should read rather than growing a second copy of the derivation. Out of scope for this branch, and named so the next change does not reinvent it.

## Conflicts with three open PRs

Cut from `main`, based on none of them. `scripts/audit_checks.py` is edited by **no** open PR, so the code collides with nothing. The prose collides twice, and the merge order stays #80, #81, #82, then this:

- **`audit/SKILL.md`'s three-kinds paragraph** is in the line #80 and #82 both edit. All three edits are additive to different sentences of one paragraph.
- **The route contract that documents a new route field** is in the line **#81 deletes**, having relocated it into `audit-core`'s `## Running a route`. The field's contract sentence is therefore written as a self-contained clause rather than woven into its neighbours, so the resolution is to paste it into the relocated paragraph rather than to reconstruct it.

## Verification

The four gates, `tests/test_sweep_obligations.py` read rather than merely run, the new tests, and the reading pass over `audit-core`. Then a stale-prose pass by an agent that has not seen the change, scoped by the sentences that carry a decision: every sentence that chooses a runner, every mention of `lang: any`, and every place the three-kinds taxonomy is stated or summarised.
