# The routes schema, and the arch pilot

Design for #59, the first three stages of #58. A check record declares what it runs as data in its frontmatter; the verification harness reads that data instead of parsing the record's prose. This specifies the schema, the validator, and the migration of the eleven `arch` records that proves both.

Every count below was computed against this tree on 2026-08-18 rather than estimated.

## What reading `arch` changed about the schema

#58 proposed a `routes:` list carrying roughly the fields the harness's `Invocation` already has. Reading all eleven records moved three things.

**Most routes run nothing, and not for one reason.** Of the 19 arch invocations, 14 prescribe no command. `grimp` is a library a scripted pass computes a graph with. `import-linter` and `tach` are commands conditional on a target artifact - a `.importlinter` contract, a `tach` configuration - that the target may not have. On `arch/complexity-gate` the three tools are "the gate's subject rather than its instrument": the check reads the configured threshold, and running a tool answers `arch/complexity` instead. `arch/coupling` offers `pydeps` as a visual while saying the counts are the evidence. A single `tooling:` list of names cannot tell these apart, so the harness carries a hand-written note on each explaining why there is no command - record knowledge stored in the test suite.

**`forms` collapses into `routes`.** A form the record names as superseded or as an alternative is not a property of a route; it is a route the harness does not take. Declaring it as a route with a disposition removes a whole nested structure and, with it, the class of defect #55 closed: a disposition can no longer act as a per-form off-switch on a coverage property, because the property reads routes and a route is what a disposition is attached to. This also answers #58's open question about a fourth disposition. `forbidden` is needed and is a route: the npm `semgrep` placeholder and the bare `dlx depcruise` are both commands a record names in order to forbid, and both currently sit in prose that only a reader enforces.

**`ungranted_note` dissolves.** It answers "what does this check still answer when the grant is withheld", which under per-route tiers is exactly "the routes carrying no tier". Verified against all three arch records that carry one. `arch/complexity`'s names a branch-point count needing nothing installed - a procedure route - and an ESLint invocation under an audit-owned config, which is a second invocation mode of a tool whose other mode is tiered, and which is #31. `arch/hidden-coupling`'s names source patterns readable with nothing installed - a procedure route. `arch/complexity-gate`'s names reading the linter configuration and the CI workflow files - a procedure route - and then says the tiered tools are the gate's subject rather than its instrument, which is a kind rather than a note.

## The schema

One `routes:` list per record, replacing `tooling:`, `needs:` and `ungranted_note:`. Each route is one way of answering the check in one language.

```yaml
routes:
  - lang: python              # python | typescript | any | none
    kind: command             # command | library | procedure | subject
    tool: pydeps              # the name the record calls it by
    package: pydeps           # optional; the installable name where it differs from `tool`
    argv: [pydeps, --show-cycles, --show-dot]
    argv_by_manager:          # optional; where a package manager needs a different spelling
      pnpm: [pnpm, "--package=typescript@^5", "--package=dependency-cruiser", dlx, depcruise]
    disposition: runs         # runs | alternative | superseded | forbidden
    needs: resolved-tree      # optional; absent means a read-only clone answers
    in_env: false             # optional; runs inside the target's environment
    findings_stream: stdout   # optional; stdout | stderr
    applies_when: >-          # optional; what the target must carry for this route to apply
      The partition carries a `.importlinter` contract.
    alone_insufficient: >-    # optional; a clean result here does not answer the check, and why
      ...
    note: >-
      ...
```

**Three axes, deliberately separate.** `kind` says what the thing is. `disposition` says whether the harness takes this route. `applies_when` says what the target must carry for the route to be available at all. Prose let all three be written as one sentence, which is why the harness's notes conflate them.

**Field rules the validator holds.**

- `argv` is required where `kind: command` and rejected on every other kind. A library, a procedure and a subject have no command by definition, so an `argv` on one is a miscategorised route rather than a harmless extra.
- `disposition` defaults to `runs` and may be non-default only where `kind: command`. There is nothing for a library to supersede.
- `package` defaults to `tool` and is written only where they differ, so the name that resolves a binary is stated once, in the place that resolves it. This is #28. The tree's own instance is `dependency-cruiser` providing `depcruise`, which `arch/cycles` and `arch/coupling` both state outright: "`depcruise` is the command this tool documents but not the name of the package that provides it", and npm carries a dependency-confusion placeholder under the command's name.
- `needs` is per route rather than per tool, which is #31: a tool with two invocation modes is two routes, one tiered and one not.
- `argv_by_manager` enumerates rather than derives. The three runner spellings in `arch/coupling` differ structurally - npm takes `--package X --package Y --`, yarn takes `-p X -p Y`, and pnpm requires its flags before `dlx`, since `pnpm dlx --package=` fails outright - so a spelling reconstructed from a command name is a spelling that has not been run.
- `alone_insufficient` is #58's stop rule. It carries the evidence, not just the flag, because the reason is what makes an agent act on it.

**What the record does not carry.** `completion`, `supplied_by_partition` and `supplied_note` stay in the harness. They hold what a partition needed that the record did not say, which is the verification round's finding; moving them into the record would delete the finding. `record_quote` ceases to exist, having nothing left to anchor.

## The validator

`audit_checks.py` gains `routes:` and keeps `tooling:`/`needs:` for the eight unmigrated domains. Each existing invariant is carried, transformed or dropped, and the reason is recorded on the field:

- **`needs` names only tools the record offers.** Dropped, because it cannot be violated: a route's tier is on the route, so there is no second list to disagree with. This is the invariant that existed only because the names were repeated.
- **One tier per tool.** Transformed, and the transformation stated here was not built. See the correction section below: the rule as written would reject the tree's only instance of the case it was meant to allow.
- **`ungranted_note` required where every tool in a language is tiered.** Transformed into a structural check with no note: where every route in a language carries a tier, the record must also carry an untiered route in that language, or an explicit `answers_ungranted: none`. The sentinel stays explicit for the reason the current one does - an absent field must never read as a claim.
- **A record with no `tooling`** stated what to read instead in prose. Becomes a `kind: procedure` route, so the claim is in the schema rather than in a paragraph a validator cannot check.

**Mixed state is declared, not tolerated.** The validator accepts both schemas while the migration runs, and a test holds the set of records still on `tooling:` - asserted non-empty so the exception cannot become dead, and shrinking, so a domain migrated without updating the set fails. This is the idiom the harness already uses for its `unanchored` and `skipped` sets.

## The oracle, and the half it does not cover

Arch's Python routes have one. The harness's `INVOCATIONS` table was verified through #53 and #55 and reverified by mutation, so a test asserting that the migrated routes agree with it on argv, disposition, `findings_stream` and per-manager spelling catches transcription errors introduced by the migration itself.

**The TypeScript half has no oracle and the pilot does not claim one.** `madge`, `dependency-cruiser` and the three runner spellings are authored from documentation and one smoke run, not from a seeded fixture, which is epic #44's whole thesis. What this pilot proves about the TypeScript routes is that the schema can express them, not that they run.

## Migration order

1. The schema and validator, with the dual-schema acceptance and the legacy set.
2. `arch/cycles` alone, as the shape test: it carries a library, a conditional command with a differing binary name, a superseded form and a procedure route.
3. The remaining ten arch records.
4. The oracle test binding the migrated Python routes to `INVOCATIONS`.

Schema and validator commits stay separate from record commits. A record is a prompt, so each record commit says why the record now reads the way it does, not merely that it changed.

## Acceptance

- The eleven arch records carry `routes:` and no `tooling:`, `needs:` or `ungranted_note:`.
- Every claim the three `ungranted_note`s made is expressible as routes, or the residue is recorded on #59 as something the schema could not express.
- `arch/complexity-gate`'s three subject routes, `arch/cycles`'s superseded `--show-cycles` form, `arch/coupling`'s three runner spellings and forbidden bare `dlx depcruise`, and `arch/layering`'s two conditional commands each round-trip through the schema without prose.
- The oracle test passes over arch's Python routes.
- The validator rejects, with a test each: an `argv` on a non-command kind, a non-default disposition on a non-command kind, a fully tiered language with neither an untiered route nor the sentinel, and a record migrated out of the legacy set while still carrying `tooling:`.
- The suite passes and both integrity gates exit 0.

## What the pilot corrected in this spec

Recorded here rather than silently rewritten, because a spec that quietly repairs itself teaches nothing about how it was wrong.

Two claims above named `import-linter` as providing a binary called `lint-imports`, and made that binary an acceptance criterion. No check record writes `lint-imports` anywhere; the string occurs only in this spec and its plan. `arch/cycles` names `import-linter` and prescribes no command line for it at all, so its `package` equals its `tool` and there is nothing for the field to carry. The genuine package-is-not-binary case in the tree is `dependency-cruiser` providing `depcruise`, and the criterion now names it.

A second claim in "The validator" above asserted a per-tool tier rule keyed on `argv`: that two routes for the same tool in one record may carry different tiers only where their `argv` differs. No such check was built, no test implements it, and the plan did not carry it forward. It is also wrong as written. The tree's only instance of a tool with two invocation modes is `arch/complexity`'s two `eslint` routes, and because that record prescribes no command line for either mode both are `kind: procedure` with the same empty `argv` - so the rule would reject exactly the case #31 exists to permit. `test_a_tool_has_one_tier_across_the_family` continues to run against the projection, which keeps one tier per tool per record, and passes only because the projection collapses the untiered mode out of view. The record says so itself: nothing machine-readable tells its two modes apart. Distinguishing them needs a field the schema does not have, and that is recorded against the epic rather than invented here.

The route this leaves is `kind: procedure` naming the tool: the record hands the agent an instruction rather than a command, and inventing an `argv` to satisfy `kind: command` would manufacture exactly the prescription this schema exists to hold records to.

## Out of scope

The eight remaining domains, the `SKILL.md` runner tables and #42's incorrect `yarn dlx` claim, and deleting the harness's Markdown-parsing helpers - that last needs every domain migrated, because those helpers still hold the records that have not moved.
