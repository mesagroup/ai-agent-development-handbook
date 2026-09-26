<!-- GENERATED FILE - do not edit. Source: scripts/python_fixture_spec.py; run scripts/render_python_fixture_expectations.py after editing. -->

# TypeScript fixture expectations

What each `lang: typescript` command route in the audit skill family must observe when it runs against the seeded npm and pnpm fixture partitions, written down before the run. Generated from `scripts/python_fixture_spec.py` by `scripts/render_python_fixture_expectations.py`, the same module and renderer as the Python record beside it: edit the module and re-render, never this file. The `--check` flag of that renderer holds both records to the module, and CI runs it.

A fixture whose expected output is not recorded first is just a smaller real target. Against a real repository an audit can only ask whether a command ran and returned something plausible; here the right answer is known before the tool speaks, so a route that runs cleanly and reports half the truth fails instead of passing.

Every pin below was checked against OSV and the npm registry on **2026-09-25**. A pin is frozen, but the advisories against it only accumulate and its latest release moves, so re-verifying one means querying both sources again and moving the date with it.

The fixture trees are generated and never committed to this repository.

## The shared dependency set

Both partitions declare the same set at exact pins. The npm partition is one package and declares all of it in one `package.json`; the pnpm partition is a workspace, and the `Member` column says which of its manifests declares each entry - the root, `packages/core` (the seeded source) or `apps/api` (the leaf, which also depends on the core package through `workspace:*`). The member is what decides whether a root-only read reaches a pin.

| Package | Pin | Latest | Dev | Member | Seeds | Evidence |
|---|---|---|---|---|---|---|
| `lodash` | `4.17.20` | `4.18.1` | no | `apps/api` | vulnerable | OSV: 5 advisories, GHSA-29mw-wpgm-hmr9, GHSA-35jh-r3h4-6jhm, GHSA-f23m-r3pf-42rh, GHSA-r5fr-rjxr-66jc and GHSA-xxjr-mmjv-4gpg, two pairs of which alias each other, over CVE-2020-28500, CVE-2021-23337, CVE-2026-4800, CVE-2025-13465 and CVE-2026-2950. npm view: MIT, no dependencies. Latest is 4.18.1, so it is outdated too |
| `commander` | `2.20.3` | `15.0.0` | no | `apps/api` | stale, leaf-only | OSV: no advisories. npm view: MIT, no dependencies. Latest is 15.0.0, thirteen majors ahead. Declared in the pnpm leaf only, so a root-only freshness read cannot reach it |
| `is-odd` | `3.0.1` | `3.0.1` | no | root | transitive-root | OSV: no advisories. npm view: MIT, the latest release, which makes it the freshness control. Depends on is-number ^6.0.0, which resolves to is-number 6.0.0 (MIT, no OSV advisories, not declared anywhere in the fixture): the transitive component the licence and inventory checks have to reach |
| `tinymce` | `7.9.3` | `8.9.2` | no | `packages/core` | copyleft | npm view: GPL-2.0-or-later, no dependencies. OSV: no advisories. Pinned at 7.9.3 rather than the planned 7.9.1, which carries three XSS advisories (GHSA-q742-qvgc-gc2f, GHSA-v98h-vmpc-fpqv, GHSA-vg35-5wq7-3x7w) fixed in 7.9.3 and would have made lodash not the only vulnerable seed. The 8.x line is unusable for the seed: 8.9.2 declares `SEE LICENSE IN license.md`, which is not an SPDX id. Latest is 8.9.2, so it is outdated too |
| `vitest` | `5.0.2` | `5.0.2` | yes | root | - | npm view: MIT, the latest release. Declares a non-optional peer dependency on vite and engines node ^22.12.0 \|\| ^24.0.0 \|\| >=26.0.0. Its option documentation gives slowTestThreshold a default of 300 and testTimeout a default of 5000, and says `sequence.shuffle` runs files and tests in random order |
| `@vitest/coverage-v8` | `5.0.2` | `5.0.2` | yes | root | - | npm view: MIT, the latest release, peer dependency vitest 5.0.2 exactly |
| `typescript` | `5.9.3` | `7.0.2` | yes | root | - | npm view: Apache-2.0. Pinned at 5.9.3, the newest 5.x release, rather than the latest 7.0.2: 7.x ships as per-platform native binaries, madge 8.0.0 declares a typescript peer of ^5.4.4 and the dependency-cruiser routes record a declared range below 7.0.0, so a 7.x in the tree would be an unplanted confound on every resolved-tree arch route. Outdated by construction |

## What each partition runs

Both partitions carry every check in the expectation table, because each TypeScript command route there is either the partition's own package manager's subcommand or a tool that runs the same way on both, so each partition asks it a different question. The `packageManager` pin is on the root manifest, which is where corepack reads it.

| Partition | Manager pin | Expectations | Checks |
|---|---|---|---|
| `npm` | `npm@11.19.0` | 11 | every check in the expectation table |
| `pnpm` | `pnpm@9.15.9` | 11 | every check in the expectation table |

## Expected result per check

15 entries over 11 checks. A check whose answer differs by partition is written as one entry per scope, the scopes disjoint. The `Form` column takes one of `exact`, `floor`, `absence`, with the meanings the Python record gives them: `exact` is fully determined, `floor` states a location and a minimum where an exact number would go stale on its own, and `absence` states that any hit is a false positive. An entry with no seed states what a correct tool reports on a fixture that plants nothing for it.

| Check | Partitions | Form | Seeds | Expected |
|---|---|---|---|---|
| `deps/vulnerabilities` | all | floor | vulnerable | at least 5 distinct CVEs against lodash 4.17.20: CVE-2020-28500, CVE-2021-23337, CVE-2025-13465, CVE-2026-2950, CVE-2026-4800. The record's routes are `npm audit` on npm and `pnpm audit` on pnpm, both untiered and both reading the lockfile, and on pnpm lodash is declared in apps/api rather than at the root, so an audit that reads only the root importer misses it. A floor because advisories against a frozen pin only accumulate and tools count advisories rather than CVEs; the run records which unit it counted in. The other seeded runtime dependencies, is-number included, had no OSV advisory on the verified date, so an advisory against one of them is a false positive; the devDependency tree was not queried package by package, so advisories there are recorded rather than graded |
| `deps/freshness` | `npm` | exact | stale | `npm outdated` in the installed tree reports exactly lodash 4.17.20 (latest 4.18.1), commander 2.20.3 (latest 15.0.0), tinymce 7.9.3 (latest 8.9.2), typescript 5.9.3 (latest 7.0.2). is-odd 3.0.1 has had no release since its pin and is the control: a route reporting it outdated is producing a false positive. vitest 5.0.2, @vitest/coverage-v8 5.0.2 were the latest releases on the verified date, and a line that ships patches as often as vitest's can move before the run, so they are re-checked against the registry then rather than graded as controls. Named rather than counted, because the count moves with the dependency set while which entry is the control does not |
| `deps/freshness` | `pnpm` | exact | stale, leaf-only | across the workspace, lodash 4.17.20 (latest 4.18.1), commander 2.20.3 (latest 15.0.0), tinymce 7.9.3 (latest 8.9.2), typescript 5.9.3 (latest 7.0.2) are outdated. is-odd 3.0.1 is the control, and vitest 5.0.2, @vitest/coverage-v8 5.0.2 were current on the verified date and are re-checked before the run, as on npm. The record's argv is bare `pnpm outdated`, which its own note says reads the root manifest only: run as written from the root it can report typescript 5.9.3 and nothing declared in packages/core or apps/api, so commander, the stale pin declared only in apps/api, is missing from a run that looks complete. That is the half-truth #44 names, and it is graded as less than the truth rather than as a clean run; the note's workspace form, `pnpm outdated -r`, is the one that reaches both members |
| `deps/licenses` | `npm` | exact | copyleft | `npm sbom --package-lock-only --sbom-format cyclonedx` reports tinymce 7.9.3 under GPL-2.0-or-later, read off the lockfile's per-package `license` with no tree and no network. The one copyleft entry the check must surface, rather than a count |
| `deps/licenses` | `pnpm` | exact | copyleft | `pnpm licenses list` in the installed workspace reports tinymce 7.9.3 under GPL-2.0-or-later, declared in packages/core |
| `deps/transitive-licenses` | `npm` | floor | transitive-root | at least is-number 6.0.0 appears as a component with MIT, since it is never declared and arrives through is-odd; `npm sbom --package-lock-only` reads it from the lockfile's pinned transitive graph |
| `deps/transitive-licenses` | `pnpm` | floor | transitive-root | at least is-number 6.0.0 appears with MIT in `pnpm licenses list`, which reports across the whole workspace, arriving through is-odd at the root |
| `deps/inventory` | `npm` | floor | - | `npm sbom --package-lock-only --sbom-format cyclonedx` emits a CycloneDX document whose components include lodash 4.17.20, commander 2.20.3, is-odd 3.0.1, tinymce 7.9.3, vitest 5.0.2, @vitest/coverage-v8 5.0.2, typescript 5.9.3 at their pins, plus is-number 6.0.0 through is-odd. A floor rather than an exact count, because the devDependency tree vitest resolves is in the lockfile too and its size moves with the resolution |
| `deps/inventory` | `pnpm` | exact | - | none of this record's TypeScript command routes reads pnpm-lock.yaml: `npm sbom`, the only one, is built on package-lock.json, which this partition does not carry by construction. So no SBOM comes from a command route here, and the record's remaining route for the partition is the `@cyclonedx/cdxgen` procedure, which this round does not execute. A family finding if the run confirms it; the error text the command prints is recorded at the run rather than predicted |
| `arch/cycles` | all | exact | cycle | one cycle, between src/domain/model.ts and src/infra/store.ts, from `madge --circular --ts-config` given the seeded package's own tsconfig.json. That tsconfig extends nothing, so the route's applies_when holds by construction, and madge needs no grant, so the claim holds in both states. Paths are relative to the seeded package, which is the tree root on npm and packages/core/ on pnpm |
| `arch/coupling` | all | floor | cycle | the two modules in the cycle are each other's dependents, so neither is a leaf, from the dependency map the tiered `dependency-cruiser` route builds |
| `arch/over-decomposition` | all | exact | pass-through | two forwarding functions, one per module in the cycle: load in src/domain/model.ts forwards to read in src/infra/store.ts, and loadViaDomain in src/infra/store.ts forwards to load. Minor on the record's band, and neither becomes a finding without the read the record requires, so the expected observation is the pair, not a verdict on it. Paths are relative to the seeded package, which is the tree root on npm and packages/core/ on pnpm |
| `test/coverage-reach` | all | exact | uncovered-branch | `vitest run --coverage` with @vitest/coverage-v8 installed reports src/clamp.ts with its two guard branches uncovered. The fixture sets no coverage.include, and vitest's documented default includes only files covered by tests, so model.ts and store.ts, which no test imports, are absent from the report rather than at zero: an absence the default produces, not a miss. The suite is green in file order, so the report is written without `--coverage.reportOnFailure`. Paths are relative to the seeded package, which is the tree root on npm and packages/core/ on pnpm |
| `test/determinism` | all | exact | order-dependence | test/order.test.ts fails under `vitest run --sequence.shuffle --sequence.seed=<n>` for a seed that reverses its pair, and passes in file order. Both tests are in one file, and `--sequence.shuffle` as a boolean shuffles tests within a file as well as the files, which is what reaches the pair. The seed is measured when the fixture is first built and recorded in the build smoke record, never guessed |
| `test/isolation` | all | exact | slow-test | the test in test/slow.test.ts sleeps 2000ms: over vitest's default slowTestThreshold of 300ms, so `vitest run` reports its duration and marks it slow, and under the default testTimeout of 5000ms, so it passes. All three numbers are interpolated from the module constants the seeded file is written from |

## Without the grant

Every entry is run under two grant states, and the table above is the answer with the grant. Where withholding it changes what the check answers on that partition, the second answer is written out below - 9 of the 15 entries. It is judged per partition rather than per language, because an untiered TypeScript route can be one partition's own package manager: `npm sbom` needs no grant, but it reads `package-lock.json`, so it answers nothing on the pnpm partition. An entry not listed here answers its claim in both states.

| Check | Partitions | Without the grant |
|---|---|---|
| `deps/freshness` | `npm` | the same claim, from the record's registry-comparison route: every pin is exact and in package.json, so comparing it with the registry's latest release needs no tree. That route is a procedure rather than a command, so the harness's ungranted run of the tiered `npm outdated` records no-evidence (not-permitted) and the claim is what the procedure answers |
| `deps/freshness` | `pnpm` | the same claim, from the record's registry-comparison route over all three manifests. The harness's ungranted run of the tiered `pnpm outdated` records no-evidence (not-permitted), and the claim is what the procedure answers |
| `deps/licenses` | `pnpm` | no command route answers. `pnpm licenses list` needs the tree, and `npm sbom`, the record's untiered command, reads package-lock.json, which this partition does not carry; what remains is the `@cyclonedx/cdxgen` procedure, which this round does not execute. So the harness records no-evidence (not-permitted), and a clean licence list from this partition without the grant is a false clean |
| `deps/transitive-licenses` | `pnpm` | the same as deps/licenses on this partition: `pnpm licenses list` needs the tree and `npm sbom` has no package-lock.json to read, so the harness records no-evidence (not-permitted) and only the cdxgen procedure would answer |
| `arch/coupling` | all | the tiered command route does not run, so the harness records no-evidence (not-permitted); the same claim is what the record's untiered madge procedure answers from a read-only clone, which this round does not execute |
| `arch/over-decomposition` | all | the tiered `dependency-cruiser` route does not run, so the harness records no-evidence (not-permitted); the record's untiered madge procedure answers the same pair from a read-only clone, which this round does not execute |
| `test/coverage-reach` | all | the measurement does not survive the withheld grant while the configuration axis does: the fixture carries no vitest config at all, so no coverage include, exclude or threshold is readable in the clone and the axis answers clean. The expected ungranted answer is a half-answered check, no-evidence (not-permitted) in status and in the coverage count, its evidence naming the configuration axis as answered clean and the measurement axis as unmeasured |
| `test/determinism` | all | the inputs axis answers without the tree, and finds nothing: the seeded suite reads no clock, calls no Math.random and touches no network. Order-dependence goes unmeasured, so the expected ungranted answer is a half-answered check, no-evidence (not-permitted) in status and in the coverage count, its evidence naming the inputs axis as answered clean and the order axis as unmeasured |
| `test/isolation` | all | the I/O axis answers without the tree and finds nothing: the seeded suite makes no network, filesystem or database call and configures no timeout. The duration is what the grant buys, so the expected ungranted answer is a half-answered check, no-evidence (not-permitted) in status and in the coverage count, its evidence naming the I/O axis as answered clean and the timing axis as unmeasured |

## What a result still owes

An entry whose check has a TypeScript route naming a tool that carries `alone_insufficient` states what is still owed, 5 of the 15 entries. Where the record uses the field for an invocation requirement - a command not complete as written - the entry says what the invocation needs. The row's status is the engine's and does not move for either.

| Check | Partitions | Still owed |
|---|---|---|
| `deps/freshness` | `npm` | the unpinned and deprecated-release halves: an outdated list answers only whether a release is behind. The fixture pins every declaration exactly, so the unpinned half should read clean, and whether a pinned release is deprecated is the registry read the record's procedure route carries |
| `deps/freshness` | `pnpm` | the unpinned and deprecated-release halves, as on npm: the fixture pins every declaration exactly in all three manifests, and the `workspace:*` link to the core package is a workspace protocol rather than an unpinned registry dependency |
| `arch/cycles` | all | nothing a read of the result adds: the record's field on `dependency-cruiser` states an invocation requirement, that the spelling is a prefix and answers only once given `--config` with an audit-owned config (the record prefers one setting `options.tsConfig`) or `--no-config`, and a run with neither exits 1 with `Can't open a config file`, which is no-evidence (tool-failed) rather than an empty graph |
| `arch/coupling` | all | nothing a read of the result adds: the record's field on `dependency-cruiser` states an invocation requirement, that the spelling is a prefix and answers only once given `--config` with an audit-owned config (the record prefers one setting `options.tsConfig`) or `--no-config`, and a run with neither exits 1 with `Can't open a config file`, which is no-evidence (tool-failed) rather than an empty graph |
| `arch/over-decomposition` | all | a read confirming each forwarding module is genuinely trivial and that merging it raises cohesion, as the record requires once the graph is complete; and the `dependency-cruiser` invocation requirement, an audit-owned `--config` or `--no-config`, without which the prefix exits 1 |

## Checks with no expectation

Every check with a `lang: typescript` route either has an expectation above or is listed here with its reason - 15 checks. The suite holds the two sets to a partition of the family's TypeScript-route checks, read from the check records, so a new TypeScript route cannot drop out of the round unclassified.

| Check | Why no expectation |
|---|---|
| `arch/complexity` | no TypeScript command route: its routes are ESLint procedures (the core complexity rule and eslint-plugin-sonarjs), which prescribe a configuration to write rather than a command to run |
| `arch/complexity-gate` | no TypeScript command route: its ESLint routes are `kind: subject`, the configuration the check inspects rather than a way of answering it |
| `arch/dead-code` | no TypeScript command route: knip and ts-prune are procedures |
| `arch/hidden-coupling` | no TypeScript command route: its ESLint, knip and tool-less routes are procedures |
| `arch/import-rule-declaration` | no TypeScript command route: its one route is a tool-less reading procedure |
| `arch/layering` | its one TypeScript command route, `dependency-cruiser`, applies only where the project carries its own `.dependency-cruiser` config, and planting one would have the fixture declare the boundary the check tests; the fallback it names is a reading of tsconfig paths and references, which this fixture does not declare |
| `arch/over-abstraction` | no TypeScript command route: knip is a procedure and ts-morph a library |
| `deps/hygiene` | no TypeScript command route: depcheck and knip are procedures |
| `security/crypto` | no TypeScript command route: its ESLint and tool-less routes are procedures |
| `security/dangerous-calls` | no TypeScript command route: its ESLint and tool-less routes are procedures |
| `security/injection` | no TypeScript command route: its ESLint and tool-less routes are procedures |
| `security/unsafe-io` | no TypeScript command route: its ESLint and tool-less routes are procedures |
| `test/coverage-floor-declaration` | no TypeScript command route: its one route is a tool-less reading procedure |
| `test/mutation` | its one TypeScript command route is `disposition: alternative` to the record's procedure route, and its argv carries a `<runner>` placeholder the record leaves the inventory to fill; nothing is planted for it beyond the untested clamp guards, and the plan for this round seeds no mutation survivor |
| `test/property-based-gap` | no TypeScript command route: fast-check is a library |

## A seed nothing expects

A seeded finding no expectation names would be planted and never looked for, so the planted and expected seeds are held equal in both directions by the suite.

None: all 10 seeds the source files and the dependency set plant are named by some expectation.
