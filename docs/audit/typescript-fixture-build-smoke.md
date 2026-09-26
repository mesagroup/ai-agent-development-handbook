# TypeScript fixture build smoke

The two seeded TypeScript fixture partitions, `npm` and `pnpm`, were generated and their lockfiles read against the pins in `scripts/python_fixture_spec.py`. This record is what happened on **2026-09-26**. It is the gate on the fixture machinery rather than the verification round: it answers whether the generator produces the trees [the TypeScript expectations record](typescript-fixture-expectations.md) was written against, so that the round which grades the TypeScript command routes starts from a fixture that works.

**No check record is corrected on this evidence, and no expectation is changed by it.** The lockfiles were read directly; no route a check record prescribes was run. The one value this record settles for the family is the vitest shuffle seed, which the expectations record defers to this record because it is measured and cannot be derived.

The subject is the **fixture set**, as in [the Python build smoke](python-fixture-build-smoke.md). Nothing here is a finding about any audited codebase.

## What was built

`uv run python scripts/build_python_fixtures.py npm pnpm` wrote both partitions to `fixtures/typescript/npm` and `fixtures/typescript/pnpm`, printed the tracked file count for each, and exited 0 in about 7 seconds. The generator probes each partition's manager before writing anything and refuses to build when the version differs from the partition's `packageManager` pin; it refuses to return from a tree whose `git status --porcelain` is non-empty, and compares each tree's own `git ls-files` against `committed_files(partition)`, so a build that returns has already asserted all three.

| Partition | Tracked files | Lock artifact | Built by | Manager |
|---|---|---|---|---|
| `npm` | 10 | `package-lock.json`, `lockfileVersion` 3 | `npm install --package-lock-only --ignore-scripts --no-audit --no-fund` | `npm 11.19.0`, from the host, equal to the pin `npm@11.19.0` |
| `pnpm` | 13 | `pnpm-lock.yaml`, `lockfileVersion` `'9.0'` | `corepack pnpm install --lockfile-only --ignore-scripts` | `pnpm 9.15.9`, provisioned by corepack from the pin `pnpm@9.15.9` |

The host toolchain was **node v24.20.0**, **npm 11.19.0**, **corepack 0.35.0** and **git 2.43.0**, with no pnpm on PATH. Both lock steps ran with every `npm_config_*registry` variable removed from the environment and `npm_config_registry` set to `https://registry.npmjs.org/`, and with `COREPACK_ENABLE_DOWNLOAD_PROMPT=0` and `COREPACK_ENABLE_AUTO_PIN=0`.

The probe's placement is not incidental: `corepack pnpm --version` run in a directory with no `packageManager` pin downloaded and reported **pnpm 12.6.0**, and run inside the pinned tree reported 9.15.9. So the version a probe outside the tree reports is not the version the lock step uses, which is why the generator probes in a scratch directory carrying the partition's root `package.json`.

Tracked files per partition:

- `npm`: `FIXTURE.md`, `package.json`, `package-lock.json`, `tsconfig.json`, `src/clamp.ts`, `src/domain/model.ts`, `src/infra/store.ts`, `test/clamp.test.ts`, `test/order.test.ts`, `test/slow.test.ts`.
- `pnpm`: `FIXTURE.md`, `package.json`, `pnpm-workspace.yaml`, `pnpm-lock.yaml`, `apps/api/package.json`, `packages/core/package.json`, and the seven seeded files of the `npm` list under `packages/core/`.

Each tree carries two commits, the seeded source with its manifests and then the lockfile. Neither lock step left anything else behind: no `node_modules`, no `.modules.yaml`, and no `packageManager` field rewritten, since `git status --porcelain` was empty in both trees after the build and `git status --short` at the handbook repository listed only this branch's own changes, `fixtures/` being gitignored.

## What the lockfiles resolved

Every pin resolved exactly, in both lockfiles.

| Package | Pin | `npm` lockfile | `pnpm` lockfile |
|---|---|---|---|
| lodash | 4.17.20 | 4.17.20, runtime, MIT | 4.17.20, importer `apps/api` |
| commander | 2.20.3 | 2.20.3, runtime, MIT | 2.20.3, importer `apps/api` |
| is-odd | 3.0.1 | 3.0.1, runtime, MIT | 3.0.1, importer `.` |
| is-number, through is-odd | none, declared nowhere | 6.0.0, runtime, MIT, depended on by is-odd alone | 6.0.0, the snapshot of `is-odd@3.0.1` depends on `is-number: 6.0.0` |
| tinymce | 7.9.3 | 7.9.3, runtime, GPL-2.0-or-later | 7.9.3, importer `packages/core` |
| vitest | 5.0.2 | 5.0.2, dev, MIT | 5.0.2, importer `.` |
| @vitest/coverage-v8 | 5.0.2 | 5.0.2, dev, MIT | 5.0.2, importer `.` |
| typescript | 5.9.3 | 5.9.3, dev, Apache-2.0 | 5.9.3, importer `.` |

- **The pnpm leaf holds commander and lodash, and nothing else declares them.** The `apps/api` importer lists `@fixture/core` as `link:../../packages/core`, commander 2.20.3 and lodash 4.17.20; the `.` importer lists is-odd and the three dev dependencies; `packages/core` lists tinymce alone. Neither commander nor lodash appears under any other importer, which is the arrangement the leaf-only stale seed and the pnpm half of `deps/vulnerabilities` rest on.
- **vite, vitest's peer, was resolved in both**, at **8.3.1**, against vitest's declared peer range `^6.4.0 || ^7.0.0 || ^8.0.0`. On npm it is `dev` and `peer`; on pnpm the lockfile records `autoInstallPeers: true` and vitest's snapshot key is `vitest@5.0.2(@vitest/coverage-v8@5.0.2)(vite@8.3.1)`.
- **The runtime graph is exactly five packages**: the npm lockfile marks commander, is-number, is-odd, lodash and tinymce as non-dev, and the other 73 of its 78 package entries as dev. The pnpm lockfile's `packages` section carries the same 78 name and version pairs, compared as sets.
- **Every `resolved` URL in the npm lockfile names `registry.npmjs.org`**, 78 of 78. Every npm entry carries a `license` field, so the per-package licence the npm `deps/licenses` expectation reads off the lockfile is there.

## What differed from the expectations' assumptions

No expectation in [the TypeScript expectations record](typescript-fixture-expectations.md) is falsified by either lockfile. Two properties of the pnpm lockfile were not stated there and are recorded so that the round that follows does not discover them as defects:

- **pnpm-lock.yaml records no licence.** It carries no `license` field for any package. The expectations already route the pnpm licence and transitive-licence claims through `pnpm licenses list` in an installed workspace and say no command route answers without the grant, so this is consistent with them; it also means no lockfile-only licence read is possible on this partition.
- **pnpm-lock.yaml records no registry.** Its package entries carry an `integrity` hash and no tarball URL, so the public registry the generator sets decides what pnpm resolved from without appearing in the file. Reproducibility of the pnpm lock rests on the pins and the integrity hashes; the `resolved` URL property holds on the npm lockfile only.

## The measured shuffle seed

The `test/determinism` expectation says the seed that reverses the order-dependent pair in `test/order.test.ts` is measured when the fixture is first built and recorded here.

**Seed 0** is the smallest seed in 0..30 that fails, and **seed 3** is the smallest non-zero one, measured with `npx vitest run test/order.test.ts --sequence.shuffle --sequence.seed=<n>` under **vitest 5.0.2**, **vite 8.3.1** and **node v24.20.0**, in a copy of the `npm` partition made in a scratch directory outside the fixture root and materialized there with `npm ci --ignore-scripts --no-audit --no-fund --registry=https://registry.npmjs.org/`. Nothing was installed inside a fixture tree.

- The failure is the seeded assertion and nothing else: `reads` runs first and fails with `expected [] to deeply equal [ 1 ]`, and `appends` passes.
- Seeds 0 and 3 each failed on five repeated runs, and seed 1 passed on five, so the seed is deterministic under these versions. Seed 0 is named because it was measured, though a reader of `--sequence.seed=0` may reasonably suspect a falsy default; seed 3 does not carry that doubt.
- The whole suite at seed 0 and at seed 3 reports one failed test and three passed, the failure being `test/order.test.ts > reads`; the suite without `--sequence.shuffle` passes, 4 of 4.
- 13 of the 31 seeds in 0..30 reverse the pair: 0, 3, 9, 11, 12, 14, 17, 18, 20, 22, 24, 25 and 28.

The seed was measured on the `npm` partition only. The `pnpm` partition carries the same seeded files under `packages/core/`, and whether the same seed reverses the pair there, where vitest runs from the member rather than from the root, was not measured.

## Still open

- **Only the lockfiles were read.** No route a check record prescribes was run against either partition, under either grant state. That is the round that follows.
- **The seed will need re-measuring when vitest moves.** It is recorded with the versions it was measured under, and nothing fails when it goes stale.
- **The pins are dated.** Every pin was verified against OSV and the registry on the expectations record's verified date; advisories against lodash 4.17.20 only accumulate, and the vitest line ships often enough that its current-release status can move before the run.

## Rebuilt under the lock environment

The build above ran its lock steps and version probe under the generic fixture environment rather than the lock environment the builder computes, because `_run` accepted an `env` argument and did not pass it on, which the automated review of PR #201 found. The host carried no `npm_config_registry` override and corepack already held pnpm 9.15.9, so neither the registry pin nor the corepack flags had anything to change on this host. The trees were rebuilt after the fix, and the npm lockfile resolves the same pins from the same single registry host, with commander still present in the pnpm lockfile. The conclusions above stand.
