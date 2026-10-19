# TypeScript fixture run

Every TypeScript command route the [TypeScript fixture expectations](typescript-fixture-expectations.md) grade was run against the two seeded TypeScript partitions, `npm` and `pnpm`, under both grant states, on **2026-09-26**, and each observation was set beside the expectation written before the run. This record is what came back. It exists for the reason the expectations record gives: against a real repository a route that runs cleanly and reports half the truth passes, and against a seeded fixture it does not.

The subject is the **skill family**, as in [the Python lens smoke run](python-lens-smoke-run.md): the routes the check records prescribe, how the fixture lens ran them, and where an observation fell short of the planted truth. [The build smoke record](typescript-fixture-build-smoke.md) is the sibling for the fixture machinery. Nothing here is a finding about any audited codebase.

**Two check records and one harness table were corrected on this evidence, and the four runs below were made after those corrections**; `## Records corrected` says what each was and what the earlier observation was. No planted truth in the expectations was changed. Where an observation still contradicts an expectation, or a route still reports less than the truth, it is recorded here and listed under `## Found, not fixed`.

## The run

The fixtures were rebuilt from this branch with `uv run python scripts/build_python_fixtures.py npm pnpm`, which wrote 10 tracked files to the `npm` tree and 13 to the `pnpm` tree. Each partition was then run twice:

- `uv run python scripts/run_python_fixture_lens.py <partition> --grant none --timeout 300 --work-dir <scratch-dir>`
- `uv run python scripts/run_python_fixture_lens.py <partition> --grant target-execution --timeout 300 --work-dir <scratch-dir>`

`<scratch-dir>` is a directory outside the repository, one per run. `none` is a read-only copy with nothing installed. `target-execution` implies `resolved-tree`, and materializes the copy first: `npm ci --ignore-scripts` on `npm`, and `pnpm install --frozen-lockfile --ignore-scripts` through a corepack shim on `pnpm`. Both materializations exited 0. The results were written to `fixtures/typescript/results/`, which is gitignored, and graded with `uv run python scripts/grade_python_fixture_run.py fixtures/typescript/results`, which wrote 44 rows from the 4 runs: 11 expectations per partition per grant, and no orphan row.

| Run | Commands run |
|---|---|
| `npm`, `none` | 5 |
| `npm`, `target-execution` | 12 |
| `pnpm`, `none` | 2 |
| `pnpm`, `target-execution` | 11 |

No command reached the 300-second timeout. `git status --porcelain` was empty in both fixture trees after all four runs: every install and every tool ran in the copy the lens makes.

### Versions

| Tool | Version | Source |
|---|---|---|
| node | v24.20.0 | host |
| npm | 11.19.0 | host, equal to the `npm` pin |
| corepack | 0.35.0 | host |
| pnpm | 9.15.9 | corepack, from the `pnpm` pin |
| vitest | 5.0.2 | the partition's own install, probed with `npx --no -- vitest --version` on `npm` and `pnpm exec vitest --version` on `pnpm` |
| @vitest/coverage-v8 | 5.0.2 | the partition's own install |
| madge | 8.0.0 | fetched per run by `npx --yes` or `pnpm dlx` |
| dependency-cruiser | 18.4.0 | fetched per run, beside `typescript@^5` |

## Result per check

A cell reads **matched** where the observation is the expectation, **less than the truth** where a route ran and reported part of the planted answer, **tool-failed** where it ran and produced no answer, and **not run** where the lens recorded no command, each with its reason. The `Signals` column of the worksheet is zero on every row, because every TypeScript seed marker is a source construct no tool echoes, so every verdict below is by reading the stored stdout and stderr.

### deps

| Check | Partition | `none` | `target-execution` |
|---|---|---|---|
| `deps/vulnerabilities` | `npm` | **matched**: `npm audit` exits 1 and reports 5 advisories against lodash 4.17.20 and no other package | **matched**, the same 5 |
| `deps/vulnerabilities` | `pnpm` | **matched**: `pnpm audit` exits 1 with `5 vulnerabilities found`, all against lodash, read from the lockfile with its `Paths` column empty | **matched**, the same 5, each with the path `apps/api > lodash@4.17.20`, so the leaf importer was reached |
| `deps/freshness` | `npm` | **matched** the ungranted claim: `npm outdated` is tiered, so no-evidence (not-permitted); the registry-comparison procedure was not executed | **matched**: `npm outdated` exits 1 listing exactly commander 2.20.3 (latest 15.0.0), lodash 4.17.20 (4.18.1), tinymce 7.9.3 (8.9.2) and typescript 5.9.3 (7.0.2). is-odd, the control, is absent, and so are vitest and @vitest/coverage-v8, which were still current |
| `deps/freshness` | `pnpm` | **matched** the ungranted claim: no-evidence (not-permitted) | **matched**: `pnpm outdated -r` exits 1 listing lodash 4.17.20 and commander 2.20.3 (dependent `@fixture/api`), tinymce 7.9.3 (`@fixture/core`) and typescript 5.9.3 (the workspace root). is-odd, vitest and @vitest/coverage-v8 are absent |
| `deps/licenses` | `npm` | **matched**: `npm sbom --package-lock-only --sbom-format cyclonedx` gives tinymce 7.9.3 under GPL-2.0-or-later, the only copyleft component | **matched**, the same document apart from its serial number and timestamp |
| `deps/licenses` | `pnpm` | **matched** the ungranted claim: `pnpm licenses list` is tiered, so no-evidence (not-permitted), and `npm sbom` is recorded not run as npm's own subcommand | **matched**: `pnpm licenses list` lists tinymce under GPL-2.0-or-later, its only GPL row |
| `deps/transitive-licenses` | `npm` | **matched**: is-number 6.0.0 is a component with MIT | **matched** |
| `deps/transitive-licenses` | `pnpm` | **matched** the ungranted claim: no-evidence (not-permitted) | **matched**: is-number is listed with MIT |
| `deps/inventory` | `npm` | **matched**: a CycloneDX 1.5 document of 78 components carrying all seven declared pins and is-number 6.0.0 | **matched**, the same document |
| `deps/inventory` | `pnpm` | **matched**: not run, as expected; `npm sbom` is npm's subcommand and no other command route exists | **matched**, not run for the same reason |

### arch

| Check | Partition | `none` | `target-execution` |
|---|---|---|---|
| `arch/cycles` | `npm` | **matched**: `madge --circular --extensions ts,tsx --ts-config tsconfig.json src` exits 1 with `Processed 3 files` and `Found 1 circular dependency!`, `domain/model.ts > infra/store.ts`. dependency-cruiser is tiered: no-evidence (not-permitted) | **matched** from madge, the same cycle. dependency-cruiser exits 1 with `Can't open a config file`: **tool-failed**, as the expectation's owed field predicts |
| `arch/cycles` | `pnpm` | **matched**: the same madge command pointed at `packages/core` processes 3 files and reports the same cycle | **matched** from madge, and dependency-cruiser **tool-failed** as on `npm` |
| `arch/coupling` | both | **matched** the ungranted claim: dependency-cruiser no-evidence (not-permitted); the madge procedure was not executed | **tool-failed**: dependency-cruiser exits 1 with `Can't open a config file`, as the owed field predicts, so the claim is not reached |
| `arch/over-decomposition` | both | **matched** the ungranted claim: no-evidence (not-permitted) | **tool-failed**, for the same reason as `arch/coupling` |

madge answers here only because its route carries `--extensions ts,tsx`: given a directory, madge collects the extensions in its `fileExtensions` option, whose default in its own source is `['js']`. See `## Records corrected`.

### test

| Check | Partition | `none` | `target-execution` |
|---|---|---|---|
| `test/coverage-reach` | both | **matched** in status: vitest is tiered, so no-evidence (not-permitted). The configuration axis is a reading the lens does not perform | **matched**: `vitest run --coverage` reports `clamp.ts` as the only file, 50% of branches (2 of 4), with lines 4 and 7, the two guard returns, uncovered |
| `test/determinism` | both | **matched** in status: no-evidence (not-permitted) | **matched**: `vitest run --sequence.shuffle --sequence.seed=3` exits 1 with `order.test.ts > reads` failing on `expected [] to deeply equal [ 1 ]`, 1 failed and 3 passed. On `pnpm` the run starts from the workspace root and reaches `packages/core/test/order.test.ts`, so seed 3 reverses the pair there too |
| `test/isolation` | both | **matched** in status: no-evidence (not-permitted) | **less than the truth**: `vitest run` exits 0 and prints only the file and test totals and the suite duration. The 2000 ms test is neither named nor timed, and nothing marks it slow |

The isolation result was measured further in the scratch copy. Run on a pseudo-terminal rather than captured, `vitest run` prints the same totals and no per-test line, so the default reporter hides the test in both forms. `vitest run --reporter=verbose` prints `test/slow.test.ts > slow but passing 2003ms`, so the duration becomes readable. Even then nothing in the text marks the test slow: with colour forced, the duration is printed in yellow, and without colour, which is how the lens captures it, there is no marker at all. The expectation's words "reports its duration and marks it slow" therefore hold for the duration only under a non-default reporter, and for the mark only as a colour.

## The half-truth

**Yes: the root-only `pnpm outdated` missed commander.** Run bare from the workspace root of the `pnpm` partition, it listed typescript 5.9.3 alone and exited 1, and the lens classified the row `ok`. commander 2.20.3, the stale pin declared only in `apps/api`, was absent, and so were lodash 4.17.20, also declared only in `apps/api`, and tinymce 7.9.3, declared only in `packages/core`: of the four outdated pins, the bare form reported the one declared at the root. That is the half-truth #44 names, caught by the seeded fixture as the expectation predicted. The record's argv now carries `-r`, the workspace form its note named, and the run above shows that form reaching all four.

## Contradictions with the expectations

- **`test/isolation`, contradicted.** The expectation says `vitest run` reports the slow test's duration and marks it slow. On both partitions it does neither: the default reporter prints only totals, `--reporter=verbose` prints the duration, and no reporter form puts a slow mark in text; see the test section. The expectation is left as written, for the maintainer to decide.

No other observation contradicts its expectation. Every ungranted cell recorded the not-permitted status its ungranted claim names, and the procedures those claims defer to were not executed, as the expectations say.

## Found, not fixed

- **vitest's default reporter names no slow test.** What: `test/isolation`'s `vitest run` route prints only file and test totals and the suite duration, captured and on a pseudo-terminal alike, so the 2000 ms test is neither named nor timed on either partition. `vitest run --reporter=verbose` prints `test/slow.test.ts > slow but passing 2003ms`, and even then the only slow mark is the yellow colour of the duration, which captured output does not carry. Where: the vitest route in `.agents/skills/test-audit/checks/isolation.md`, argv `[vitest, run]`, and the `test/isolation` expectation, which says the run marks the test slow. Why not fixed here: a verbose reporter would surface the duration but not the mark, so the route and the expectation's wording are one decision, left to the maintainer.
- **The madge procedures in three other records name no extensions.** What: `arch/coupling`, `arch/layering` and `arch/over-decomposition` carry madge as a `kind: procedure` route whose note tells the reader to give madge the partition's tsconfig and spells no command, so none of them says `--extensions`, and a reader who runs madge as those notes describe, on a TypeScript-only tree and without the flag, gets the 0-file clean result `arch/cycles` produced before its route carried it. Where: the madge routes in those three records. Why not fixed here: they prescribe no argv to extend, and adding the flag to their prose is a wording change to three notes that no run here exercises.
- **dependency-cruiser's prefix fails without a config.** What: every dependency-cruiser row under `target-execution` exits 1 with `Can't open a config file`, so `arch/cycles`, `arch/coupling` and `arch/over-decomposition` get no graph from it on either partition, six cells in all. Where: the dependency-cruiser routes in those three records. Why not fixed here: each record says the prefix answers only with an audit-owned `--config` or with `--no-config` and that neither is free, so choosing one is a decision about what the audit writes, not a one-line fix.
- **No command route answers `deps/inventory` on pnpm.** What: `npm sbom` is the record's only TypeScript command route and reads `package-lock.json`, so the `pnpm` partition records no command in either grant state. Where: `.agents/skills/deps-audit/checks/inventory.md`. Why not fixed here: the expectation already names it as the family finding, and closing it means executing the `@cyclonedx/cdxgen` procedure or adding a pnpm route, which is new scope.

## Records corrected

- **`arch/cycles`, both madge routes.** The `runs` route's argv is now `madge --circular --extensions ts,tsx --ts-config`, and the superseded bare route's `madge --circular --extensions ts,tsx`, so the one thing the superseded form lacks is still the tsconfig. Before the change the route processed 0 files and reported `No circular dependency found!` at exit 0 in all four cells, over the planted cycle. `tsx` is in the list because a TypeScript target's modules are often `.tsx`; the fixture has none, so the run evidences the flag, not that entry. The expectation's description of the command was updated to the new argv; its claim, one cycle between the two seeded modules, is unchanged.
- **`deps/freshness`, the pnpm route.** The argv is now `pnpm outdated -r`, and the note says why and records the fixture measurement. Before the change the bare form listed 1 of the 4 outdated pins, as `## The half-truth` describes. The expectation's description of the record's argv was updated; its claim, four outdated pins across the workspace with is-odd as the control, is unchanged.
- **The fixture lens's npx prefix.** The in-environment prefix on npm is now `npx --no --`. Without the `--`, npx read the version probe's trailing `--version` as its own flag, and the version map recorded npm's `11.19.0` for vitest and jest. The rows' own commands now carry the same `--`, and their output is unchanged.

## Harness, still open

- **`npx --no` reports a tool the tree does not carry.** The granted `npm` run records jest `30.5.2`, though the fixture declares no jest and its `node_modules/.bin` holds none: the earlier `none` probe fetched jest through `npx --yes` into npx's own cache, and `npx --no` resolves from that cache as well as from the tree. No row is affected, because every jest row is not run by its `applies_when`, but a version in the map is not proof that the tree carries the tool.
- **The seed marker signals cannot grade a TypeScript row.** Every marker names a construct in the seeded source, and no route's output quotes the source, so the signals column is zero on all 44 rows and every verdict above is a reading of the stored output.

## 2026-10-19: `deps/inventory` on pnpm

`deps/inventory`'s TypeScript `cdxgen` route was a procedure naming no command, so the pnpm cell above recorded no command in either state. It is now a command route, `cdxgen -t js --no-install-deps -o - .`, fetched as the package `@cdxgen/cdxgen`, and this section records the run that put it there. The rest of the round above was not re-graded here.

### Choosing the tool

- **pnpm's own form does not exist on the fixture's pnpm.** pnpm's documentation gives `pnpm sbom --sbom-format cyclonedx --lockfile-only` as added in v11.0.0. The pnpm partition pins `pnpm@9.15.9`, pnpm switches itself to the pin, and the command answers `Command "sbom" not found` there, so a pnpm-native route would answer only on a partition pinned to 11 or later.
- **The package name is `@cdxgen/cdxgen`.** cdxgen's README and its v13 migration guide say the npm package was renamed at v13: v13 and later are `@cdxgen/cdxgen`, and `@cyclonedx/cdxgen`, the name the records carried, is the v12 line, still patched on a release branch and receiving no v13 features. Both packages point at the same source repository, and neither is a placeholder. The command, `cdxgen`, is unchanged, and is the bin rather than the package name, so the runner names the package. The two sibling procedure routes in `deps/licenses` and `deps/transitive-licenses` were renamed with it, so the family names one package for one tool.
- **The flags come from `cdxgen --help`.** `-o` defaults to `bom.json`, written into the working directory, and `-o -` writes the document to stdout. `--install-deps` defaults to true, so `--no-install-deps` is what keeps cdxgen from installing into the tree it reads. Recursion, which reaches a workspace's members, is the default. cdxgen's `--dry-run` report over a scratch copy of the pnpm tree listed `ldd --version` and `pnpm root -g` as the only commands it would execute and stdout as its only write. `--dry-run` blocks that write, so it is not in the argv.

### The run

The fixtures were rebuilt from this branch with `uv run python scripts/build_python_fixtures.py --output-dir <fixture-dir> npm pnpm`, which wrote 10 tracked files to the `npm` tree and 13 to the `pnpm` tree. Each partition was run under both grant states, as above, with `--fixture-root <fixture-dir> --timeout 300 --work-dir <scratch-dir>`, and graded with `uv run python scripts/grade_python_fixture_run.py <fixture-dir>/results`, which wrote 44 rows from the 4 runs and no orphan row. `<fixture-dir>` and `<scratch-dir>` are directories outside the repository.

| Run | Commands run |
|---|---|
| `npm`, `none` | 6 |
| `npm`, `target-execution` | 13 |
| `pnpm`, `none` | 3 |
| `pnpm`, `target-execution` | 12 |

Each count is one more than the round above: the cdxgen row, which runs on both partitions because it reads either lockfile. `git status --porcelain --ignored` was empty in both fixture trees after all four runs.

The probe recorded **cdxgen 13.4.0** in all four runs, fetched by `npx --yes --package=@cdxgen/cdxgen --` on `npm` and by `pnpm --package=@cdxgen/cdxgen dlx` on `pnpm`, under node v24.20.0 and the pinned pnpm 9.15.9. The route pins no version, so a later run can resolve a later one.

### Result

| Check | Partition | `none` | `target-execution` |
|---|---|---|---|
| `deps/inventory` | `npm` | **matched**: `npm sbom` as above, and cdxgen exits 0 with a CycloneDX 1.7 document of 78 components carrying all seven declared pins and is-number 6.0.0, every component with a licence read from `package-lock.json` | **matched**: cdxgen's components are the same 78, and its document differs from the ungranted one only in its serial number, its timestamps and the path of the copy it scanned |
| `deps/inventory` | `pnpm` | **matched**: cdxgen exits 0 with a CycloneDX 1.7 document of 78 components carrying all seven declared pins - lodash 4.17.20 and commander 2.20.3, declared only in `apps/api`, and tinymce 7.9.3, declared only in `packages/core`, included - and is-number 6.0.0 through is-odd, with `@fixture/api` and `@fixture/core` under the root component. No component carries a licence, because `pnpm-lock.yaml` records none | **matched**: the same 78 components and both members. 53 of them now carry a licence, read from the installed `node_modules`, tinymce's GPL-2.0-or-later among them. Of the 25 without, 23 are platform-specific optional binaries the install skipped, and the other two are `@vitest/mocker` and `fdir` |

`npm sbom` was recorded not run on `pnpm`, as before, as npm's own subcommand. The licence difference between the two pnpm cells is why the record's `evidence` keeps licence findings with `deps/licenses` and `deps/transitive-licenses`: the same command's licence fields depend on whether a tree is installed.

This answers the weaker half of the question [the TypeScript smoke run](typescript-lens-smoke-run.md) left open, that cdxgen reads `pnpm-lock.yaml` at all: it does, the members included, and cdxgen reported generating the 78-component document in under half a second. Whether it finishes at workspace scale stays open. The run that did not finish there was the v12 package with `FETCH_LICENSE=true`, which this command does not set, so it neither confirms nor contradicts this one.

### Found, not fixed

- **cdxgen writes the scanned path into the SBOM.** What: the document's `metadata` summary and each component's evidence name the lockfile by the absolute path of the directory cdxgen scanned, here the lens's scratch copy. Where: any SBOM the `@cdxgen/cdxgen` route produces, which an audit report might quote or attach. Why not fixed here: it is the tool's output rather than the record's, and whether a report strips it is a question for the report's format, which this round does not settle.
- **The cdxgen version probe records a banner rather than a version.** What: `cdxgen --version` prints `CycloneDX Generator 13.4.0` in bold, then a `Runtime:` line, and the version map stores both lines with their escape codes. Where: the `@cdxgen/cdxgen` entry in `TS_VERSION_PROBE` in `scripts/run_python_fixture_lens.py`. Why not fixed here: the version is readable, and stripping a tool's own output is a harness-wide decision about what a version entry holds, not one tool's.
