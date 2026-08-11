# TypeScript lens smoke run

Every `typescript:` and `any:` tooling entry in `arch`, `deps`, `test` and `security` was authored from the tools' own documentation and had never been executed against a real TypeScript repository. This record is what happened when they were, under both grant states. It exists because a docs-only pass cannot catch the defect where a name resolves, a command runs, and the output is unusable or wrong at exit 0.

The subject here is the **skill family**, not the audited codebase: a point-in-time audit report belongs to the codebase it is about, per the rule in [README](README.md). What that report found about the target stays with the target. What appears below is tool behaviour, aggregate counts, and the corrections they forced.

## The run

The target is a real internal Next.js application: 381 TypeScript files, 57,551 lines of code, `npm` with `package-lock.json`, Vitest as the runner, no `.dependency-cruiser` config, a `tsconfig` that declares `paths` and `extends` nothing, and a second partition in C#. It is named, with its package manager, in [issue #29](https://github.com/mesagroup/ai-agent-development-handbook/issues/29); this file does not name it, because a repository name is an environment-specific identifier.

Both grant states were run, against two `git clone`s of the target in a scratch directory, never the target itself:

- **no grant** - a read-only clone with no `node_modules`, which is what every `ungranted_note` makes a claim about.
- **`target-execution`** (which implies `resolved-tree`) - the same clone with `npm ci --ignore-scripts`, which resolved 810 packages cleanly, so no escalation to install hooks was needed.

`git status --porcelain` at the target was **empty before and after**. Where a tool needed something the target did not have (a coverage provider, ESLint, Stryker), it was installed into the audit's own copy or an audit-owned directory, never into the target.

## Result per entry

`ok` means the entry produced the evidence its `## Severity` section asks for. `no-evidence` and `not-applicable` carry the reason the engine requires.

| Entry | No grant | `target-execution` |
|---|---|---|
| `madge` (cycles, coupling, layering, over-decomposition) | **ok** with `--ts-config`; false clean without it | ok, unchanged |
| `dependency-cruiser` (same four) | **ok only** with a pinned compiler and an audit-owned config; three silent-failure routes otherwise | ok |
| `eslint` core rules (`arch/complexity`) | **ok** from an audit-owned install; the prescribed one-shot form fails | ok |
| `eslint` (`arch/complexity-gate`) | **ok** - the gate question is read from config, and the target configures no threshold | ok, and confirms it |
| `eslint-plugin-sonarjs` (`arch/complexity`) | not run - `target-execution` tier | **ok**, 82 cognitive-complexity hits |
| `eslint` + `knip` (`arch/hidden-coupling`) | **ok** on the source-reading axis; `knip` axis missing | ok |
| `knip` (`arch/dead-code`, `arch/over-abstraction`, `deps/hygiene`) | wrong-at-exit-0 (see below) | ok |
| `ts-prune` (`arch/dead-code`) | **ok**, over-reporting as documented | ok |
| `ts-morph` (`arch/over-abstraction`) | **ok** from an audit-owned install; one-shot form fails | ok |
| `cloc` (`arch/size`) | **ok** via `npx` | ok |
| `tokei` (`arch/size`) | `no-evidence (tool-unavailable)` - standalone binary, absent, and `npx tokei` resolves a package with no bin | same |
| `npm-check-updates` (`deps/freshness`) | **ok**, 33 upgradable | ok |
| `npm outdated` (`deps/freshness`) | unusable as documented: no `current`, devDependencies dropped | **ok** |
| `pnpm outdated`, `pnpm licenses list`, `yarn licenses list`, `yarn npm audit` | **not executed** - no pnpm or yarn target (open criterion) | same |
| `depcheck` (`deps/hygiene`) | partial as documented, four false unused | **ok** |
| `npm audit` (`deps/vulnerabilities`) | **ok** from the lockfile alone, 24 advisories | ok |
| `osv-scanner` (`deps/vulnerabilities`) | `no-evidence (tool-unavailable)` - not fetchable by any one-shot runner | same |
| `npm sbom --package-lock-only` (`deps/inventory`) | **ok**, 945 components | ok |
| `@cyclonedx/cdxgen` with `FETCH_LICENSE=true` (`deps/licenses`, `transitive-licenses`, `inventory`) | **ok**, about nine minutes, licences resolved for every component | ok |
| `vitest run` (`test/isolation`) | not run - `target-execution` tier | **ok**, per-test durations |
| `vitest run --coverage` (`test/coverage-reach`) | exclusion-config read: **ok** (nothing excluded, no floor) | **`no-evidence (tool-failed)`** as prescribed; ok only via the audit copy |
| `c8` (`test/coverage-reach` fallback) | n/a | **false clean** (see below) |
| `vitest --sequence.shuffle` (`test/determinism`) | grep axis **ok** | **ok**, no order dependence at the seed |
| `jest` (all `test` entries) | **not executed** - the target runs Vitest, and the records say to use the partition's own runner | same |
| `diff-cover` (`test/new-code-coverage`) | `no-evidence (not-permitted)` - no coverage artifact published by CI | **ok**, 58% diff coverage over 91 changed lines |
| `@stryker-mutator/core` (`test/mutation`, opt-in) | `no-evidence (not-permitted)` | one-shot form **fails**; **ok** from the audit copy - 52.34% mutation score on one scoped module in 68s |
| `fast-check` (`test/property-based-gap`, opt-in) | **ok** - a reading pass, no execution applies | same |
| `semgrep` (crypto, dangerous-calls, injection, unsafe-io) | **ok** via `uvx`, and see the coverage caveat below | ok |
| `eslint-plugin-security` (same four) | **ok** from an audit-owned install | ok |
| `detect-secrets` (`security/secrets-in-code`) | **ok** via `uvx`, 20 candidates triaged | ok |
| `gitleaks`, `trufflehog` (`secrets-in-code`, `secret-history`) | `no-evidence (tool-unavailable)` - neither is an npm or PyPI package | same |
| `arch/martin-metrics` | nothing to execute - `tooling` is Python-only | same |

## What the run found

### 1. The one-shot-runner prescription fails wherever the co-package must be *imported*

Five records prescribe `npx --package A --package B -- <bin>`. Three distinct outcomes were observed, and only one of them is the documented one.

`npx --package typescript --package dependency-cruiser` installs an **unpinned** `typescript`, which now resolves to **7.x**. dependency-cruiser 18.2.0 declares support for `>=2.0.0 <7.0.0`, so `depcruise --info` reports the transpiler unavailable and enables only `.js .cjs .mjs .jsx`. Pinning it - `--package 'typescript@^5'` - lights up `typescript@5.9.3`, `.ts` and `.tsx`, and the tool then answers correctly from a plain directory argument. So the co-package instruction is right and **incomplete in a way that silently breaks it**: unversioned, it produces exactly the empty result the records warn about.

An audit-owned **flat config** cannot resolve a parser from that sandbox at all: `ERR_MODULE_NOT_FOUND: Cannot find package '@typescript-eslint/parser' imported from <the audit config>`. Same for a script importing `ts-morph`. Node resolves a config's or script's imports from where *it* lives, not from the sandbox. What works is an audit-owned `npm install` with the config beside it, which needs network rather than the target's tree, so the ungranted claim survives in substance while the mechanism named does not.

For `@stryker-mutator/core` the co-package was **not installed at all**: the sandbox's `package.json` recorded three requested packages under `_npx.packages` and two under `dependencies`, with no `typescript` present, and Stryker died on its own dynamic `import('typescript')`. Pinning did not change it. Installed into the audit copy instead, Stryker ran: **52.34% mutation score** on one scoped module, 56 mutants killed, 37 survived, in 68 seconds - which is also the record's own reason for scoping the run to one module rather than the tree.

The bare-name hazard `test/mutation` documents is real and lands differently than predicted: `npx stryker` does resolve and execute the unscoped pre-1.0 package, and on node 24 it **crashes** rather than reporting a wrong mutation score. The record's reasoning about which failure is harder to notice is sound; the failure observed today is the loud one.

### 2. `dependency-cruiser` has three silent-failure routes, and the records name none of them

On a target with no `.dependency-cruiser` config - the ordinary case - the prescribed invocation **exits 1** with `Can't open a config file`, rather than the "zero modules cruised at exit 0" the records describe. Taking depcruise's own suggested remedy, `--no-config`, then **disables `paths` resolution**: 281 unresolvable first-party specifiers and **0 cycles reported**, against 7 modules in cycles once a config is supplied. And a **directory** argument under an unpinned compiler cruises `totalCruised: 0` at exit 0, because `.ts` is not in the extension set it scans a directory with.

The bare-name hazard the records document is real: `npx depcruise` prints `🔒 It does not contain any usable code.` and exits 0.

### 3. `madge`'s `--ts-config` claim is confirmed, on both halves

The four records say the claim is reasoned from documented behaviour and "not reproduced on a fixture here". It is now reproduced, on a partition whose `tsconfig` extends nothing:

| | cycles reported | nodes | edges | edge/node | top hub, afferent |
|---|---|---|---|---|---|
| `madge --circular --ts-config <tsconfig>` | **2** | 340 | 1090 | 3.21 | 92 |
| without the flag | **0**, at exit 0 | 340 | 122 | 0.36 | 13 |

Both halves hold: a missing flag yields a false cycle-free verdict, and the hub counts come back **wrong**, not merely thin - 89% of the edges gone and the ranking reshuffled. dependency-cruiser's 7 modules-in-cycles corroborate madge's 2 chains.

### 4. The coverage fallback returns a false clean

This is the most consequential finding, and it is the exact class the exercise was for.

| step | result |
|---|---|
| `vitest run --coverage` | `MISSING DEPENDENCY Cannot find dependency '@vitest/coverage-v8'` - the target declares no provider, and installing one into the target is barred |
| `c8 <the partition's test command>` | exit 0, Istanbul's table, **All files 96.35% Stmts / 69.56% Branch** - measured over three files: two configs and one script. **Not one line of the source tree** |
| `c8 --all --src src --include 'src/**/*.ts'` | **0% of 47,306 statements** - honest, and still measuring nothing |
| provider installed into the audit copy, `--coverage` | **no report at all** - `coverage.reportOnFailure` defaults to false and the suite has one failing test |
| the same plus `--coverage.reportOnFailure` | **8.05% Stmts / 5.86% Branch**, 339 files, `lcov.info` written |

`c8` cannot see coverage produced inside Vitest's worker processes, and Vitest transforms TypeScript in memory, so `c8` sees the few files Node loaded directly and reports a number over those. **96.35% where the real number is 8.05%.** A false clean is worse than `no-evidence`, and this one arrives at exit 0 in the format the record says to read.

The record did not strictly prescribe `c8` for this partition - its `c8` clause is conditional on a runner with no coverage integration, and Vitest has one. What the run establishes is that the decision tree **dead-ends** where the integration exists but the provider is absent, and that the nearest fallback is unsafe rather than merely inapplicable.

### 5. `npm sbom` already answers the licence question on an npm partition

`package-lock.json` carries a `license` per package. `npm sbom --package-lock-only --sbom-format cyclonedx` therefore returns a CycloneDX document with licence fields populated for **944 of 945** components, with no tree and no network, including every copyleft entry a reviewer would want to see. `deps/licenses` is right that npm has no `licenses` subcommand, and sends an npm partition to `cdxgen` over the network on the strength of it, while its `ungranted_note` describes only the PyPI path. `cdxgen` with `FETCH_LICENSE=true` does work, takes about nine minutes here, and buys exactly one thing: the single component the lockfile leaves unresolved.

### 6. Smaller observations

- **An ESLint exit code is not a verdict under an audit-owned config.** The target's own `eslint-disable` comments name rules the audit config does not load, and ESLint reports each as an **error-severity** `Definition for rule 'X' was not found`. Nineteen of them here, while every real hit was a warning: exit 1, no findings. Read the message list, not the status.
- **The Semgrep registry rulesets are narrow.** `p/javascript` plus `p/typescript` ran **74 rules and returned 0 findings** on a tree where `eslint-plugin-security` produced 557 hits, six of them `detect-non-literal-fs-filename`. On this target Semgrep alone would have reported all four security checks clean. Semgrep also notes that the scan was **limited to files tracked by git**, so an untracked file is skipped silently.
- **`knip` without the tree flags 62 unused files against 27 with it**, at exit 0 with a single stderr line. Its documented quiet degradation, quantified: 35 genuinely-used files falsely flagged.
- **`depcheck` without the tree** falsely reported `typescript`, `tsx`, `@types/react-dom` and `react-dom` unused; all four disappeared after the install. The record's fixture claim, reproduced on a real target.
- **`npm outdated` without the tree** reported all 37 production dependencies with no `current` and **dropped all 14 devDependencies from the output**, exactly as documented; with the tree it reported 36 entries and 12 devDependencies.
- **`diff-cover` has a working npm namesake.** `uvx diff-cover` gives 10.5.0; `npx diff-cover` gives 0.1.0 and runs. The record's warning, confirmed.
- **`tokei` is a standalone binary** and `arch/size` does not say so; `npx tokei` fails with `could not determine executable to run`, because a package of that name exists with no bin.
- **A tool's own output is not pathed at the target.** `npm outdated --json` stamped the scratch clone's directory name into every `dependent` field, which is why the engine requires pointers to be re-expressed relative to the target root.

## Records corrected

Traceable to the observed output above; see the commits on [issue #29](https://github.com/mesagroup/ai-agent-development-handbook/issues/29).

| Record | Correction |
|---|---|
| `arch/cycles`, `arch/coupling`, `arch/layering`, `arch/over-decomposition` | pin the compiler; name the config-less exit 1, the `--no-config` paths loss, and the directory-argument zero; the `madge` claims are no longer unreproduced |
| `arch/complexity`, `security/crypto`, `security/dangerous-calls`, `security/injection`, `security/unsafe-io` | the audit-owned ESLint path is an audit-owned *install*, not a one-shot fetch; ESLint's exit code is not the verdict |
| `arch/over-abstraction` | the same, for `ts-morph` as a library |
| `arch/size` | `tokei` is a standalone binary; `cloc` is the fetchable one |
| `deps/licenses`, `deps/transitive-licenses` | `npm sbom --package-lock-only` answers an npm partition with no tree and no network |
| `test/coverage-reach` | `c8` must not wrap Vitest; the provider goes into the audit copy, with `reportOnFailure` |
| `test/mutation` | the one-shot form does not reliably supply `typescript`; install into the audit copy |
| the four `security` code checks | what the Semgrep registry rulesets do and do not cover |
| `deps/licenses`, `deps/transitive-licenses` (frontmatter) | `npm sbom` added to `tooling:`, since a run picks tools from there and prose alone leaves the prescribed command unpickable |
| `test-audit/SKILL.md` | the domain header no longer offers `c8` for a Vitest partition without the condition that decides it |
| `audit/SKILL.md`, and the [sweep obligations ledger](sweep-obligations.md) row describing it | the three-kinds taxonomy treated every registry package as one-shot-fetchable, which is the gap that let five records prescribe an import a runner cannot supply |

## Still open

- **No pnpm or yarn target was run.** Every `pnpm`/`yarn` entry in `deps` remains docs-verified only, and those are the entries most likely to be wrong, since they differ from npm's. The acceptance criterion asking for one stays unticked.
- **`gitleaks`, `trufflehog` and `osv-scanner` were absent** and cannot be fetched by any one-shot runner. Their entries are correct in saying so, and remain unexercised. An audit environment expected to cover Yarn Classic or pnpm 10 partitions needs `osv-scanner` installed in advance.
- **One partition was C#.** No `*-audit` domain offers a lens for it, so it reports `not-applicable` rather than clean, which is the intended behaviour and was not otherwise tested here.
