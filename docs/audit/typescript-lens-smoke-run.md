# TypeScript lens smoke run

Every `typescript:` and `any:` tooling entry in `arch`, `deps`, `test` and `security` was authored from the tools' own documentation and had never been executed against a real TypeScript repository. This record is what happened when they were, under both grant states. It exists because a docs-only pass cannot catch the defect where a name resolves, a command runs, and the output is unusable or wrong at exit 0.

The subject here is the **skill family**, not the audited codebase: a point-in-time audit report belongs to the codebase it is about, per the rule in [README](README.md). What that report found about the target stays with the target. What appears below is tool behaviour, aggregate counts, and the corrections they forced.

## The run

The target is a real internal Next.js application: 381 TypeScript files, 57,551 lines of code, `npm` with `package-lock.json`, Vitest as the runner, no `.dependency-cruiser` config, a `tsconfig` that declares `paths` and `extends` nothing, and a second partition in C#. It is named, with its package manager, in issue #29; this file does not name it, because a repository name is an environment-specific identifier.

**A second target followed, to close the pnpm half.** It is a **pnpm 9.15.9 workspace** pinned by `packageManager`: 9 manifests under `apps/*` and `packages/*`, 653 `.ts` and 218 `.tsx` tracked, **254 declared dependencies of which 10 sit at the root**, a `pnpm-lock.yaml`, and a solution-style `tsconfig.json` in its frontend app. pnpm came from `corepack`, which honours the target's own pin. It is named in the same issue and not here, for the same reason. Everything below applies to the npm target unless it says pnpm.

Both grant states were run against each target, as two `git clone`s in a scratch directory, never the target itself:

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
| `pnpm audit` (`deps/vulnerabilities`) | **ok** on pnpm 9.15.9 from the lockfile - 106 advisories, against a record that said it fails below pnpm 11 | ok |
| `pnpm outdated` (`deps/freshness`) | unusable as documented, and **root-only on a workspace**: 10 entries against `-r`'s 136 | **ok**, 7 of 7 carrying `current` |
| `pnpm licenses list` (`deps/licenses`) | exit 1 without the tree, as documented | **ok**, 25 licences over 1325 packages, recursive by default |
| `pnpm dlx` co-package form (four `arch` records, `test/mutation`) | **fails**: the flags belong before `dlx`, and on pnpm 11 the co-package never arrives either way | same |
| `yarn licenses list`, `yarn npm audit`, `yarn dlx` | **not executed** - no yarn target (the criterion's remaining half) | same |
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
| `gitleaks`, `trufflehog` (`secrets-in-code`, `secret-history`) | `no-evidence (tool-unavailable)` - both are standalone binaries, and **`uvx trufflehog` resolves a superseded namesake rather than failing** (below) | same |
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

### 6. What only a pnpm target could show

Four claims were wrong, and none of them could have failed on the npm target.

**`deps/vulnerabilities` wrote off a check that answers in full.** The record gated `pnpm audit` on pnpm 11 and sent anything earlier to `osv-scanner` or to `no-evidence`. On **pnpm 9.15.9**, with no `node_modules`, `pnpm audit` returned **106 advisories - 3 critical, 47 high, 59 moderate, 9 low** - from `pnpm-lock.yaml`, covering 5 workspace packages by their advisory paths. Predicting a tool's failure from its version is how a check the clone could answer gets reported as unanswerable. The two sibling claims in the same paragraph held exactly: `npm audit` on a pnpm partition is `ENOLOCK`, and `npm sbom --package-lock-only` is `EUSAGE`, so the npm-only licence route added earlier is correctly scoped.

**`pnpm dlx --package=` is not a thing.** Five records prescribed it. pnpm reads the flag as a package spec (`ERR_PNPM_SPEC_NOT_SUPPORTED_BY_ANY_RESOLVER`), and `--package X` fetches a package literally named `--package`. The flags belong **before** `dlx`: `pnpm --package=typescript@5 --package=dependency-cruiser dlx depcruise` enables `typescript@5.9.3` and cruised 220 modules of one app with 16 in cycles, on a read-only clone. On **pnpm 11** neither ordering delivers the co-package and nothing says so - loud failure on 9, silent on 11.

**`pnpm outdated` audits the root and says nothing about the rest.**

| invocation | entries |
|---|---|
| `pnpm outdated` | **10** (the root manifest) |
| `pnpm outdated -r` | **136** |
| declared across the 9 manifests | **254** |

`pnpm audit` and `pnpm licenses list` are recursive by default on the same tree, so this is per-command rather than per-manager, and the domain header's "global is not a licence to audit one graph" needed the per-command check spelled out rather than the obligation restated.

**A solution-style `tsconfig` makes `--ts-config` a no-op.** The frontend app's `tsconfig.json` is `{"files": [], "references": [...]}` with the compiler options in `tsconfig.app.json` - the Vite default. madge does not follow `references`:

| madge on that app | result |
|---|---|
| `--ts-config .../tsconfig.json` | 45 warnings, **6 cycles** |
| no `--ts-config` at all | 45 warnings, **6 cycles** |
| `--ts-config .../tsconfig.app.json` | 31 warnings, **7 cycles** |

Passing the obvious file is byte-for-byte passing nothing. This is a third route to the same false clean, alongside the missing flag and the `extends`-into-`node_modules` case neither target has exercised.

Confirmed rather than corrected, on the pnpm side: `pnpm licenses list` needs the tree (exit 1 without it) and with it reported 25 distinct licences over 1325 packages, including `Unknown` and `SEE LICENSE IN LICENSE.md`, which is why the record says to flag `UNKNOWN`; `pnpm outdated` without an install reports entries whose `current` is undefined, and with one reports 7 of 7 carrying it; `npm-check-updates --packageManager pnpm` answers on the read-only clone.

### 7. Smaller observations

- **An ESLint exit code is not a verdict under an audit-owned config.** The target's own `eslint-disable` comments name rules the audit config does not load, and ESLint reports each as an **error-severity** `Definition for rule 'X' was not found`. Nineteen of them here, while every real hit was a warning: exit 1, no findings. Read the message list, not the status.
- **The Semgrep registry rulesets are narrow.** `p/javascript` plus `p/typescript` ran **74 rules and returned 0 findings** on a tree where `eslint-plugin-security` produced 557 hits, six of them `detect-non-literal-fs-filename`. On this target Semgrep alone would have reported all four security checks clean. Semgrep also notes that the scan was **limited to files tracked by git**, so an untracked file is skipped silently.
- **`knip` without the tree flags 62 unused files against 27 with it**, at exit 0 with a single stderr line. Its documented quiet degradation, quantified: 35 genuinely-used files falsely flagged.
- **`depcheck` without the tree** falsely reported `typescript`, `tsx`, `@types/react-dom` and `react-dom` unused; all four disappeared after the install. The record's fixture claim, reproduced on a real target.
- **`npm outdated` without the tree** reported all 37 production dependencies with no `current` and **dropped all 14 devDependencies from the output**, exactly as documented; with the tree it reported 36 entries and 12 devDependencies.
- **`diff-cover` has a working npm namesake.** `uvx diff-cover` gives 10.5.0; `npx diff-cover` gives 0.1.0 and runs. The record's warning, confirmed.
- **`tokei` is a standalone binary** and `arch/size` does not say so; `npx tokei` fails with `could not determine executable to run`, because a package of that name exists with no bin.
- **A tool's own output is not pathed at the target.** `npm outdated --json` stamped the scratch clone's directory name into every `dependent` field, which is why the engine requires pointers to be re-expressed relative to the target root.

## Records corrected

Traceable to the observed output above; see the commits on issue #29.

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
| `security/secrets-in-code`, `security/secret-history` | which of the three secret scanners a runner can fetch, and that `uvx trufflehog` runs a superseded namesake rather than failing; `secret-history` had no `## Tooling fallback` at all |
| `deps/vulnerabilities`, `deps/freshness`, `deps-audit/SKILL.md`, and the four `arch` records again | the pnpm round: the `pnpm audit` version gate, the `pnpm dlx --package=` form, `pnpm outdated`'s non-recursion on a workspace, and the solution-style `tsconfig` |
| `test/coverage-reach` and `test/mutation` again, plus `audit-core/SKILL.md`, `audit/SKILL.md` and the ledger row | also found in review rather than by the run: both records told a check to install a missing coverage provider or runner plugin into "the audit's own copy of the target", and the only copy a sweep defines is the one shared tree it builds once and hands all eight domains at the same moment. Installing there mutates the graph the other domains are measuring, and leaves `deps` reading a package the target never declared. The engine now requires a second copy the check owns, and states that a package the audit added is never evidence about the target |
| the four `security` code checks again, and `audit/SKILL.md`'s untiered-tool preference | found in review of the corrections above, not by the run: the prose said the audit-owned ESLint path answers ungranted while `needs:` tiers those tools, and the sweep's preference for an untiered sibling then licensed a grant-withheld run to stop at Semgrep and report the zero findings this run recorded. A tier describes an invocation, not a tool |

## Still open

- **No yarn target was run.** The `yarn licenses list`, `yarn npm audit` and `yarn dlx` entries remain docs-verified only. Given that every pnpm-specific claim tested turned out to need correction, and that the `yarn dlx -p` form is the one nothing has exercised, treat those entries as the least trustworthy in the family. Tracked in issue #44, which closes it with a seeded Yarn Classic and a seeded Yarn Berry fixture rather than by waiting for a real target of each kind. Issue #42 is the neighbouring design question, `dlx` being a Yarn 2+ command that a Yarn 1 partition does not have.
- **`@cyclonedx/cdxgen` against `pnpm-lock.yaml` did not finish.** It ran past 40 minutes on the 1325-package workspace and wrote no SBOM before this record was written, where it took about nine minutes on the npm target's 945. Unresolved rather than disproved: the record's claim that it reads `pnpm-lock.yaml` is untested at this size. A small fixture under issue #44 can establish that it reads the format at all, which is the weaker half of the claim; whether it terminates at workspace scale needs a large tree and stays open either way.
- **Plug'n'Play was never reached, and no record mentions it.** Yarn Berry's default linker materializes no `node_modules` at all, so every tool the check records tier `resolved-tree` or `target-execution` - `knip`, `depcheck`, the ESLint flat-config invocation, the coverage provider, Stryker, and `madge` and `dependency-cruiser` module resolution - rests on a directory such a partition does not have. Both targets here used a linker that produces one, so nothing above bears on it. Whether those tools degrade loudly or return the false clean this record keeps finding is the open question, and it is family-wide rather than a `deps` matter; issue #44 carries it.
- **`gitleaks`, `trufflehog` and `osv-scanner` were absent.** `npx osv-scanner` 404s and `npx gitleaks` reports `could not determine executable to run`, both of which read as a missing tool. **`uvx trufflehog` does not fail at all**: PyPI carries `trufflehog` 2.2.1, the original `dxa4481/truffleHog` Python v2 line superseded by the Go TruffleHog v3, and it runs with a different CLI and weaker detectors - the same substitution hazard as `diff-cover`'s npm namesake, in a domain where the substituted tool answers a Critical check. Neither secret record said which of its tools were binaries; both now do. An audit environment expected to cover Yarn Classic or pnpm 10 partitions needs `osv-scanner` installed in advance.
- **One partition was C#.** No `*-audit` domain offers a lens for it, so it reports `not-applicable` rather than clean, which is the intended behaviour and was not otherwise tested here.
