# The tier reads routes, the enumeration composes notes, and a tool-less route must prescribe

Issues #75, #76 and #73. Three schema gaps found while migrating `deps` and `test` in #67, filed rather than fixed there because each is a loader or enumeration rule with no record content in it, and folding a schema change into a migration diff puts two review surfaces in one.

They share a branch because all three are rules over the same object - a `Route` - and each would otherwise rebase over the other two in the same two files. They do not share a mechanism, and nothing below is a common fix.

**Status.** The two decisions with a real fork were put to the user and confirmed before implementation: #75 takes the tool-naming split, #76 takes note composition. #73's fork was between a non-empty rule and a length floor, and the issue's own design note had already argued the floor invites padding.

## What the three have in common, and where that stops

Each is a place where a route can say something true that a consumer downstream cannot read, and in all three directions the failure is silent:

- #75: a route can carry a tier the derivation cannot see per route, so declaring one changes what the record claims record-wide.
- #76: a group of routes can explain the absence of a command in more than one way, and the enumeration refuses to build the row rather than carrying both.
- #73: a tool-less route can carry no prescription at all, and reads through every set guard exactly like one that works.

That is the whole of the overlap. #75 is a derivation over tiers, #76 a composition over prose, #73 a loader rejection.

## #75: the tiered half reads routes, over the routes that name a tool

`deps/inventory`'s `cyclonedx-py environment` route reads the installed environment and its own note says so: it "answers nothing on a read-only clone". CLAUDE.md makes the absent tier a positive claim - "An omitted tier is a positive claim that no tool here needs it" - so the route contradicts its own note. Declaring the tier was tried in #67 and reverted.

**What the revert was about.** `test_the_ungranted_answer_is_stated_exactly_where_the_grant_changes_it` derives, per expectation, whether the grant changes what the check answers, from three conditions: the check offers Python tooling, every one of those tools is tiered, and something still answers ungranted. The second condition reads the projected `tooling`/`needs` pair, and the projection is **per tool**. `cyclonedx-py` is the only Python tool `deps/inventory` names, across two routes - an untiered `runs` route carrying the per-partition subcommands, and the `alternative` `environment` route. Tiering the second tiers the tool, so the record's Python side reads as fully tiered while an untiered answering route is still there, and the gate then demands an `ungranted` claim for the uv partition. Writing one means asserting what `uv export --format=cyclonedx1.5 --frozen` produces at `--grant none` without having run it, and a claim in the expectations that no run has graded reads exactly like one that has.

**The gate is right and the derivation is wrong.** Nothing about what `deps/inventory` answers changes when the grant is withheld: the route it prescribes by default is untiered.

**The fix is not the naive one.** Reading the tiered half as "every answering route in this language is tiered" makes it the exact complement of the third condition, because that condition is `_routes_answering_ungranted` returning a non-empty tuple and that function returns precisely the untiered answering routes. `differs` would then be unsatisfiable, and all eight expectations carrying an `ungranted` claim today would lose it - `deps/freshness`, `deps/licenses`, `deps/transitive-licenses`, `deps/hygiene` twice, `test/coverage-reach`, `test/determinism` and `test/isolation`. Every one of those is measured. A refactor that silently drops eight graded claims is the failure this suite exists to catch, arriving through the gate meant to prevent it.

**The two halves are not over the same set, and that is the answer.** What distinguishes the eight from `deps/inventory` is where the untiered escape lives:

| check | tool-naming answering routes | the untiered escape |
|---|---|---|
| `deps/freshness` | `uv`, `uv`, `pip`, all `resolved-tree` | a tool-less `procedure` route |
| `deps/licenses` | `pip-licenses` twice, both `resolved-tree` | a tool-less `procedure` route |
| `deps/transitive-licenses` | `pip-licenses`, `resolved-tree` | a tool-less `procedure` route |
| `deps/hygiene` | `deptry`, `resolved-tree` | a tool-less `lang: any` `procedure` route |
| `test/coverage-reach` | `pytest-cov`, `coverage.py`, both `target-execution` | a tool-less `procedure` route |
| `test/determinism` | `pytest-randomly` twice, `pytest-rerunfailures`, all `target-execution` | a tool-less `lang: any` `procedure` route |
| `test/isolation` | `pytest-timeout`, `target-execution` | a tool-less `lang: any` `procedure` route |
| `deps/inventory` | `cyclonedx-py` **untiered**, `cyclonedx-py` tiered | a route naming a tool |

In all eight the tools are gone once the grant is withheld and what is left is a reading. In `deps/inventory` a tool still answers, and it is the route the record runs by default. So the tiered half becomes **every answering-kind, non-forbidden route that names a tool carries a tier**, read per route. The third condition stays what it is, over every untiered answering route including the tool-less ones. Not complements, so `differs` stays satisfiable, and it stays true on all eight.

`_languages_whose_tools_all_need_a_grant` is that predicate, a sibling of `_routes_answering_ungranted` in `audit_checks.py` rather than a local in the test, because it is a fact about routes and the loader is where facts about routes live. It applies the same three exclusions for the same reasons: a `kind: subject` route names what the check inspects rather than what runs it, so counting `arch/complexity-gate`'s untiered `ruff`, `radon` and `xenon` as tools that answer would read that record as unaffected by a grant it never claimed to need; a `disposition: forbidden` route is one the record warns against; and an untiered route under one of `UNIVERSAL_ROUTE_LANGS` spreads into every language the record answers for, because that is what those values mean.

A language naming no tool at all is excluded, mirroring `_fully_tiered_languages`' own rule that a language offering no tools has said nothing about grants - `all()` over an empty list is not a claim.

**Three states, not two.** With the new predicate beside `_silenced_languages` the schema distinguishes: a language where some untiered route still runs a tool, so the grant changes nothing; one where the tools are all tiered but an untiered reading survives, so an `ungranted` claim is required; and one where no answering route is untiered at all, so it is silenced and carries `answers_ungranted: none`. `_silenced_languages` decides the third and is untouched, which is why declaring the tier does not make `deps/inventory` demand that sentinel.

**Then the record edit.** `deps/inventory`'s `environment` route declares `needs: resolved-tree`, and the route stops claiming no tool there needs a grant. No expectation gains an unmeasured claim, and the legacy branch of the derivation is unchanged: no record still declaring `tooling` reaches `differs` at all today.

**Not schema-neutral any more, and the docstring has to stop saying it is.** That test's docstring currently argues the first two conditions read the same off either schema and only the third differs. The second condition is what this changes, so two of three now branch.

## #76: the enumeration composes the notes of the routes the record prescribes

`routed_invocations` builds one row per `(check, tool)` and raises where a group prescribes no command and declares more than one route, because the row's `note` would otherwise be whichever route came first.

**The issue's premise is wrong in a way that decides the outcome.** It reports two groups tripping the guard. Computed over every route in the tree rather than over the `lang: python` selection the enumeration makes: 91 tool-bearing groups, 50 of which prescribe no command, and **three** of those declare more than one route. The third is `arch/complexity`/`eslint`, named in #58's stage-3 comment as "the one group with two routes" and not carried into #76. The three are distinguished by three different axes:

| group | distinguished by |
|---|---|
| `arch/complexity`/`eslint` | `needs` - the same two ESLint rules under an audit-owned flat config (untiered) or under the target's own (`target-execution`) |
| `test/coverage-reach`/`c8` | `applies_when` - refuse `c8` around a Vitest command, keep its plain form for a runner it can observe |
| `test/mutation`/`@stryker-mutator/core` | `disposition` - a `procedure: runs` install-and-run beside a `command: alternative` one-shot |

So of the issue's three candidate resolutions, letting `applies_when` disambiguate reaches one group, reading the disposition first reaches one, and **requiring records to merge such notes into one route is not available at all**. A route carries one `needs`. Merging `arch/complexity`'s two `eslint` routes means dropping one of the two tiers, and the untiered one is exactly what keeps `typescript` out of `_silenced_languages` for that record. That route's own note already states the problem: "It is the same tool as the route above and a different invocation mode, which is the whole distinction between them; the schema carries the two tiers and the two notes, and nothing machine-readable tells the modes apart."

**So the guard's premise is what the tree has outgrown, and the rule inverts.** The reason a row prescribes no command comes from the routes the record prescribes by default, and where there is more than one of those the row carries each of them:

- Candidates are the group's `disposition: runs` routes. Where the group has none - 7 groups today, the four `depcruise` and one `cyclonedx-npm` `forbidden` routes, `deps/vulnerabilities`' `yarn audit`, and `arch/size`'s `wc` `alternative` - the candidates are every route in the group, which is what the current single-route branch already does for each of them.
- One candidate contributes its note unchanged.
- Several contribute all of their notes, each prefixed by its `applies_when` where it has one, joined. The prefix is what stops the composition being incoherent: `c8`'s second note opens "`c8`'s plain form remains the measurement **there**", and "there" is its `applies_when`. Prefixing only when composing is deliberate - with one candidate nothing needs distinguishing, and prefixing unconditionally would rewrite the notes of the three live rows whose single route carries an `applies_when` (`arch/cycles` and `arch/layering`'s `import-linter`, and `arch/layering`'s `tach`).

**The raise survives, with a different subject.** It fires where no candidate carries a note at all, which is the row reaching the artifact with an empty explanation - the thing `test_a_routed_row_prescribing_no_command_carries_the_records_reason` holds. #73 requires a note on a tool-less route; these routes all name tools, so nothing else covers them.

**No live row changes.** Every one of the 50 no-command groups under `lang: python` declares exactly one route, so every python candidate list has one member and every note is what it is today. The three multi-route groups are all `lang: typescript`, which is why the crash was going to arrive in whoever built that lens rather than here.

## #73: a tool-less route's note is its prescription, so the loader requires one

A `kind: procedure` route may name no tool. That is what a record writes when what answers is a reading rather than a command, and for such a route the note is the whole prescription. The loader validates `note` only as a string, so a tool-less route with no note loads clean, and it reads through the projected `tooling`/`needs` pair and every set guard over the family exactly like a route that works. It is also the one route kind where nothing downstream stands in: a `kind: command` route with no note still has its `argv`.

Measured on this tree: 21 tool-less routes, every one of them `kind: procedure`, every one carrying a note, the shortest 194 characters. So the requirement holds today by care rather than by the gate, and CLAUDE.md's own rule applies - "Where a consistency property can move out of prose and into the validator, move it."

**Non-empty rather than a length floor.** A floor invites padding, and the population guard is the better second half of the pair: it holds the number of tool-less routes, so the rule cannot become vacuous by the shape leaving the tree, which is the failure a floor does not address either.

The rejection goes beside the block that already refuses a tool-less route of any kind but `procedure`, and fires only where `kind` is `procedure` - a tool-less `command` route is already named by that block, and a second error on one mistake is noise. Its message says why the note is required rather than only that it is missing.

## What the loader and the enumeration reject afterwards

- A `kind: procedure` route naming no tool and carrying no note, or a blank one, named by record and route position.
- A no-command group whose candidate routes carry no note between them, named by check and tool.

## How each new rule is exercised

The three record shapes involved are all currently compliant, so every rejection is exercised on a constructed record rather than on the tree - which is also what keeps the guards honest as the tree changes. Against that, three properties hold the live population: the count of tool-less routes, the eight expectations carrying an `ungranted` claim, and the identity of the three multi-route no-command groups. The last is the regression check #76 asks for, and it is stated as the groups' own identities rather than by relabelling them `lang: python` in a scratch copy: a synthetic record cannot go stale against the tree, and a relabelled copy proves nothing a synthetic one does not once the rule stops raising.

## What this does not do

- **It does not widen the enumeration's selection.** `routed_invocations` still reads `lang: python` routes only, so the three composing groups still build no row. Widening is #44's and #69's, and this change is what stops it arriving as a crash.
- **It does not give `arch/complexity`'s two `eslint` routes a machine-readable distinction.** Their note says nothing tells the modes apart, and that stays true: the composed note carries both, in record order, which is honest rather than resolved. Naming the invocation mode as a field is #31's territory.
- **It does not annotate the tool-less routes with anything beyond the note they already carry.**
- **It does not change what any expectation claims.** The point of #75's shape is that no `ungranted` claim is added or removed.

## Verification

`uv run pytest tests/ -q`, both integrity gates, `ruff check` and `ruff format --check`. The suite is 696 on `main` at the branch point. Beyond the gates, two computations decide whether the change did what it says: the set of expectations for which `differs` is true, which must stay the eight listed above with `deps/inventory` absent from it, and the notes of every row `routed_invocations` builds, which must be unchanged.
