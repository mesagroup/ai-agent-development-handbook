# A TypeScript lens for test-audit and security-audit

Design for #5's remaining half. Status: approved 2026-08-10.

## Goal

Give the `test-audit` and `security-audit` check records a lens on a TypeScript partition, so those two domains stop reporting `not-applicable` for every check on a TypeScript target. `arch-audit` and `deps-audit` already carry `typescript:` tooling entries; these two carry none, which is the whole of what #5 has left.

## What exists, measured

Counted on `main` at the commit this spec lands on: `test-audit` has 7 records, of which 0 carry a `typescript:` key and 1 carries no `tooling:` at all; `security-audit` has 7 records, of which 0 carry a `typescript:` key, 2 already carry `any:` (the secret scanners) and 1 carries no `tooling:` at all. Ten records therefore need a TypeScript lens: `coverage-reach`, `determinism`, `isolation`, `mutation`, `new-code-coverage` and `property-based-gap` in `test-audit`, and `crypto`, `dangerous-calls`, `injection` and `unsafe-io` in `security-audit`.

The two records with no `tooling:` key were read rather than assumed: `test/assertion-strength` prescribes reading tests against the code they cover and judging whether an assertion would fail on a regression, and `security/sensitive-data` prescribes reading logging and exception-handling call sites near secret-bearing variables. Neither names a Python construct, so both already have a lens on any partition and neither changes here.

Why this costs anything: `audit-core` defines `not-applicable` as "the check has no lens in this partition's languages", so the language key on `tooling:` is what decides whether a partition gets looked at, and PR #17 verified the consequence on a real TypeScript repository - five of seven `test-audit` checks came back `not-applicable`.

## The schema does not change

`ungranted_note` is one field per record, required where *any* language the record offers is fully tiered. Every `test-audit` record that becomes fully tiered in TypeScript here is already fully tiered in Python, so no record's requirement bit flips: the notes need their prose extended to cover the TypeScript partition, not the field added or removed. `arch/complexity` is the precedent, and its note already reads across both languages ("answers the metric on any partition with nothing installed, in either language").

That the field is per record while the rule requiring it is per language remains a real strain, and this work is the second body of evidence for it rather than the fix. It stays the follow-up PR #27 flagged. Deciding it here would put a schema change in the middle of a records sweep, and the sweep is what tells us how many records the strain actually reaches.

## Decisions taken

**Verification is documentation-based.** Every tool name, package scope, subcommand, config key and flag is checked against the tool's own documentation before it lands, plus the unit suite, both ruff passes and the integrity gate. No TypeScript target is executed. This matches how `arch-audit`'s and `deps-audit`'s TypeScript entries were authored, and it respects the repository's rule that a successful fetch is not verification. An end-to-end smoke run against a real TypeScript target is filed as a follow-up covering all four TypeScript-capable domains at once, since `arch`'s and `deps`' entries have never been run either.

**The security lens is `semgrep` beside `eslint` and `eslint-plugin-security`.** This mirrors the Python list's shape, a dataflow scanner beside a linter, and it keeps `semgrep` - which needs nothing beyond a read-only clone - in the TypeScript list. The pair is therefore mixed rather than fully tiered, so `ungranted_note` stays rejected as vacuous on all four records, which is the correct outcome and not a gap.

**`test/new-code-coverage` moves `diff-cover` from `python:` to `any:`.** The language key names the partitions a lens serves, and this record's own prose already argues that `diff-cover` needs nothing from the target: it reads a coverage report and a git diff. Its documentation states it accepts "Cobertura, Clover or JaCoCo XML format, or LCov format", and both TypeScript runners emit LCov, so the tool genuinely serves a TypeScript partition unchanged. No new tool is named; the fallback prose gains the TypeScript path to producing the report.

## Frontmatter deltas

### security-audit, four records, identical delta

```yaml
tooling:
  python: [bandit, ruff, semgrep]
  typescript: [semgrep, eslint, eslint-plugin-security]
needs:
  target-execution: [eslint, eslint-plugin-security]
```

These four carry no `needs:` key today, so this is the first tier any of them claims. `eslint` at `target-execution` is the tier `arch/complexity` and `arch/hidden-coupling` already assign it, so `test_a_tool_has_one_tier_across_the_family` agrees rather than reporting a disagreement. `semgrep` stays unclassified, which is the claim that it answers from a read-only clone, and it is the reason no note is required.

### test-audit, six records

| Record | new entry | tier | `ungranted_note` |
| --- | --- | --- | --- |
| `coverage-reach` | `typescript: [vitest, jest, c8]` | all three `target-execution` | extended to name the TypeScript exclusion keys |
| `determinism` | `typescript: [vitest, jest]` | both `target-execution` | extended to name the TypeScript non-determinism greps and the statically readable sequence options |
| `isolation` | `typescript: [vitest, jest]` | both `target-execution` | extended to name the statically readable isolation and timeout options |
| `mutation` | `typescript: ["@stryker-mutator/core"]` | `target-execution` | stays the sentinel `none` |
| `new-code-coverage` | `any: [diff-cover]`, replacing `python:` | unchanged, none | unchanged, none required |
| `property-based-gap` | `typescript: [fast-check]` | unchanged, none | unchanged, none required |

`mutation`'s note stays `none` for the same reason it is `none` now: Stryker's whole method is re-running the target's suite once per injected mutant, so with the grant withheld there is no residual axis, exactly as with `mutmut`.

`property-based-gap` stays unclassified because `fast-check` is a library imported inside existing tests rather than a runner of its own - its README documents integration with ava, jasmine, jest, mocha and tape - which is `hypothesis`'s role, and this check asks where property tests *would* strengthen the suite, a judgment made by reading source.

`property-based-gap` also needs the most rewriting relative to its size: it is a single body line naming `hypothesis` and has no `## Tooling fallback` section at all, so the line becomes language-neutral and the section gets written.

## Verified tool facts

Everything below was checked against the named source before this spec was written. An implementer should not re-derive these, and should not add a name that has not had the same treatment.

| Claim | Source |
| --- | --- |
| Stryker's package is `@stryker-mutator/core`, its CLI is `stryker run` and its documented invocation `npx stryker run`, which resolves the binary a local install put in `node_modules`, and it needs a runner plugin: `@stryker-mutator/vitest-runner`, `@stryker-mutator/jest-runner` or `@stryker-mutator/mocha-runner`, selected by `testRunner` and `plugins` in `stryker.config.json` | StrykerJS docs |
| Vitest exposes `sequence.shuffle` and `sequence.seed` (also as `--sequence.shuffle` / `--sequence.seed=<n>`), `retry`, `repeats`, `coverage.include`, `coverage.exclude`, `coverage.thresholds.branches`, and the `coverage.reporter` key, whose documented values include `lcov` (its config docs show `reporter` taking a list such as `[['lcov', {...}], ['json', {...}], ['text']]`) | Vitest docs, config/coverage |
| Vitest's `isolate` defaults to `true` and `pool` to `forks`, `--no-isolate` disables isolation, `slowTestThreshold` defaults to 300ms, `testTimeout` sets the per-test timeout | Vitest docs and `packages/vitest/src/defaults.ts` |
| Jest exposes `collectCoverageFrom`, `coveragePathIgnorePatterns`, `coverageThreshold.global.branches`, and `coverageReporters` accepting "any istanbul reporter", with `lcov` and `clover` among the documented examples; `testTimeout` defaults to 5000ms; `jest --randomize --seed 1234` shuffles test order within a file and is supported only on the default `jest-circus` runner | Jest 30 docs |
| Vitest enables coverage with the `--coverage` flag, and its coverage guide gives `vitest run --coverage` as the documented `package.json` script. A coverage provider is not bundled: the guide offers to install the matching package and otherwise gives `npm i -D @vitest/coverage-v8` or `npm i -D @vitest/coverage-istanbul` to install one by hand, which is why a record must speak of the provider the partition configured rather than assume one | Vitest docs, guide/coverage and packages/coverage-istanbul |
| Jest's `--coverage` flag is aliased `--collectCoverage` and turns on collecting and reporting coverage; the config equivalent is `collectCoverage`, and Jest's providers are `babel` (default) and `v8` | Jest 30 docs, cli and configuration |
| `diff-cover` accepts "Cobertura, Clover or JaCoCo XML format, or LCov format", defaults to comparing against `origin/main`, takes `--compare-branch`, and accepts several report files at once, counting a line covered if any report covers it | diff-cover README |
| Semgrep's registry carries `p/javascript` and `p/typescript` (alongside `p/nodejs`, `p/expressjs`, `p/eslint` and others), used as `semgrep scan --config p/javascript` | Semgrep docs |
| `eslint-plugin-security` is the exact package name, configured in flat config as `pluginSecurity.configs.recommended`, providing `detect-child-process`, `detect-eval-with-expression`, `detect-non-literal-fs-filename`, `detect-non-literal-require`, `detect-non-literal-regexp`, `detect-object-injection`, `detect-unsafe-regex`, `detect-pseudoRandomBytes`, `detect-possible-timing-attacks`, `detect-disable-mustache-escape`, `detect-buffer-noassert`, `detect-new-buffer`, `detect-no-csrf-before-method-override` and `detect-bidi-characters`; its own README warns it "finds a lot of false positives which need triage by a human", and it requires no type information | eslint-plugin-security README |
| `c8` wraps an arbitrary command (`c8 --check-coverage --lines 100 npm test`) and takes `-r`/`--reporter`, `-n`/`--include`, `-x`/`--exclude`, `--check-coverage` and `--branches` | c8 README |
| `fast-check` is the exact package name, installed as a dev dependency (`npm install fast-check --save-dev`, or the pnpm and yarn equivalents). Its README shows "Integration with other test frameworks: ava, jasmine, jest, mocha and tape", which is what supports calling it a library used inside an existing suite rather than a runner of its own. It does **not** contain the phrase "agnostic to test runners"; that wording came from a catalogue summary rather than the project, and no record may attribute it to fast-check's documentation | fast-check README, packages/fast-check |
| Semgrep's documented install channels are `pipx install semgrep` (which its docs mark recommended), `uv tool install semgrep`, Homebrew (which its docs describe as best-effort and prone to lagging the latest release), and the `semgrep/semgrep` Docker image. None is the JavaScript registry, which is what makes naming the runner load-bearing on a TypeScript partition | Semgrep docs, getting-started/cli |
| ESLint's `--no-config-lookup` disables the search for configuration files, and `-c`/`--config` names an alternate config file instead of searching for one. The two together are the audit-owned-config path | ESLint docs, command-line-interface and configure/configuration-files |
| The npm registry carries a package named `semgrep` that is not Semgrep: its `latest` dist-tag is `0.0.1`, published 2020-04-16, described as "a npm module for semgrep tool", and it declares no `bin`, so a JavaScript one-shot runner fetches it into the audit environment and then has no command to run. The npm registry also carries a package named `diff-cover` that is not the Python `diff-cover`: it is an independent third-party TypeScript port of it, published under the name `diff-cover` and titling itself diff-cover-ts in its own README, `latest` `2.0.5` published 2026-01-27, described as "A Tool to Show Code Coverage for Modified Lines in a Diff", and it *does* declare working `diff-cover` and `diff-quality` binaries - so a JavaScript one-shot runner fetches it and runs a different implementation, whose flags and defaults no row here has verified, to a plausible-looking number. Neither name fails cleanly under `npx`, which is why the records that reach for these two tools must name the registry rather than merely say the tool is absent from npm | npm registry metadata for `semgrep` and for `diff-cover`, read with `npm view` |
| The npm registry also carries an unscoped `stryker`, and unlike the `semgrep` and `diff-cover` cases above it is Stryker's own: the same three maintainers as `@stryker-mutator/core`, 107 published versions, `latest` `0.35.1`, declaring a `stryker` bin exactly as the scoped package does, and carrying npm's deprecation message "Stryker v1 is released, but you're still using a 0.x version. This version is no longer maintained. Please use @stryker-mutator/core". So the bin name and the package name differ, and `npx stryker run` reaches the scoped package only where the target installed it: on a partition with no local install it fetches and runs an unmaintained 0.x rather than failing, which is why `test/mutation` gives the `--package` form on the fetch path | npm registry metadata for `stryker` and for `@stryker-mutator/core` |
| `npx --help` documents the usage `npm exec --package=<pkg>[@<version>] -- <cmd> [args...]` and a repeatable `--package <package-spec>` option, which is the form that pins what a one-shot fetch resolves where the command name and the package name differ | `npx --help`, npm 11.16.0 |
| `uvx` "invokes a tool without installing it", is "exactly equivalent to" `uv tool run` and "is provided as an alias for convenience", and "Tools are installed into temporary, isolated environments when using `uvx`"; pipx's equivalent is its `run` command, which runs "the latest version of a Python application in a temporary environment", beside `pipx install` for a persistent one. So `uvx <tool>` and `pipx run <tool>` are the two one-shot forms a record may name, and bare `pipx` is not one | uv docs, guides/tools; pipx docs, README |
| `diff-cover` is published on PyPI under that exact name and its own README installs it with `pip install diff-cover`, so it reaches the audit environment through the same Python-registry one-shot forms as `semgrep` | diff-cover README, Installation |
| Vitest's config discovery falls through from `vitest.config.*` to `vite.config.*`: "If you are using Vite and have a `vite.config` file, Vitest will read it", a `vitest.config.ts` "will have the higher priority and will **override** the configuration from `vite.config.ts`", and "When an explicit `--config` option is not provided, Vitest looks for `vitest.config.{ts,mts,cts,js,mjs,cjs}` first and `vite.config.{ts,mts,cts,js,mjs,cjs}` second in the project `root`". Either file carries the settings, because "To configure `vitest` itself, add `test` property in your Vite config" - so a record naming only `vitest.config.*` sends an agent past every project that keeps its `test` block in the Vite config | Vitest docs, config |
| Bare `vitest` "Will enter the watch mode in development environment and run mode in CI (or non-interactive terminal) automatically", while `vitest run` is documented as "Perform a single run without watch mode", so any invocation a record gives says `run` | Vitest docs, guide/cli |
| `c8`'s `-r`/`--reporter` defaults to `['text']` and `--check-coverage` ("check whether coverage is within thresholds provided") defaults to `false`, so the plain wrapping form `c8 <command>` (the README's own `c8 node foo.js`) measures and reports while `c8 --check-coverage --lines 100 npm test` is a gate whose "check fails if coverage falls below 100%". The `text` reporter is Istanbul's, whose per-file table header is `File`, `% Stmts`, `% Branch`, `% Funcs`, `% Lines`, `Uncovered Line #s` | c8 README; `istanbul-reports`, `lib/text/index.js` |
| The `lcov` reporter is Istanbul's too, and it is a composite: it constructs `LcovOnlyReport({ file: 'lcov.info', ...opts })` alongside an `HtmlReport({ subdir: 'lcov-report' })`, so an LCov artifact is named `lcov.info` in the coverage output directory unless the project overrode `file`. This is what a record can tell an agent to search a target's published artifacts for, which the Cobertura name `coverage.xml` does not cover | `istanbul-reports`, `lib/lcov/index.js` |

`c8`'s documentation does not confirm a `cobertura` reporter, so no record asserts one. The TypeScript path to a `diff-cover` input is stated as LCov, which is verified on both sides.

This spec originally deferred two facts rather than asserting them. Semgrep's install channels are now read off its own documentation and carry a row above, as do the `uvx` and `pipx run` forms themselves, which is what a record naming either rests on. Of the per-package-manager one-shot runner names the Prose conventions section below uses (`npx`, `pnpm dlx`, `yarn dlx`), the table verifies the two `npx` forms between them: `npx stryker run`, in the Stryker row, which is that project's documented invocation and resolves a local install, and the `--package` form in the `npx --help` row, which is what `test/mutation` gives where the tool has to be fetched instead. `pnpm dlx` and `yarn dlx` are this section's own vocabulary for talking about one-shot runners and the table asserts nothing about them, so a record that wants to name one must add its row first.

## Prose conventions

Where a record's fallback genuinely splits by language it takes `arch/complexity`'s convention, a `**Python** - ` paragraph beside a `**TypeScript** - ` one. Where the guidance is language-neutral the existing topic-keyed paragraph stays as it is. In practice `determinism`'s `**Flakiness:**` and `isolation`'s `**Speed/isolation:**` become per-language paragraphs, the four security records gain a `**TypeScript** - ` paragraph, and `new-code-coverage`'s single `**Diff coverage:**` paragraph stays one paragraph because the tool is one tool for both languages.

Each TypeScript paragraph states which of the three kinds every entry is, because a record that does not distinguish them gets its entry attempted as a package, failing like a missing tool and reporting `no-evidence` for a check that could have been answered:

- `vitest`, `jest` and Stryker are the **target's own runner**. A one-shot fetch of `vitest` cannot run a suite configured for jest, and Stryker drives whichever runner the target uses through a matching plugin. So the precedence is: read the inventory's test-runner field, use that runner, and never assume. Where Stryker itself has to be fetched, what gets fetched is `@stryker-mutator/core` and not the `stryker` its bin is called: the registry carries both names, so the bare bin name reaches the wrong package on exactly the partitions that did not install the right one, and it is a live 0.x of the same project rather than a missing-tool error. This is the `semgrep` and `diff-cover` hazard in a third shape - those two are absent from the JavaScript registry, Stryker is present in it under a name that is not its bin's - and the record answers it the same way, by naming the package the fetch must resolve.
- `c8` is **fetchable from the partition's own registry**, which is what makes it the runner-neutral fallback for coverage where the partition's runner has no coverage integration: the partition's own one-shot runner (`npx`, `pnpm dlx`, `yarn dlx`) obtains it.
- `semgrep` and `diff-cover` are fetchable but **not from the JavaScript registry**, and a record that leaves this implicit invites `npx semgrep` or `npx diff-cover` - neither of which fails cleanly, because the npm registry carries a package under each of those names and neither is this tool. `npx semgrep` fetches a 2020 placeholder with no `bin` and runs nothing; `npx diff-cover` fetches a third-party TypeScript port and runs it, to a plausible-looking number. Both are recorded in the row above, and both are worse than a missing tool: one puts unvetted third-party code in the audit environment for nothing, the other answers the check wrongly with no sign that it did. Both real tools are Python-registry packages, so the one-shot form is `uvx <tool>` or `pipx run <tool>` whatever the partition's language is. Semgrep's other published install channels are not asserted here and must be read off its own installation documentation before a record names one. Naming the runner matters more on a TypeScript partition than on a Python one, because there the audit's own ecosystem and the target's differ, and the obvious runner is the wrong one.
- `eslint` is the target's own runner in the ordinary case, and `eslint-plugin-security` needs no type information, so - unlike `eslint-plugin-sonarjs`, whose type-aware rules need a real TypeScript program - these rules can also run under an audit-owned flat config with `--config` and `--no-config-lookup`, with a TypeScript parser fetched alongside ESLint. What the target's own config buys is the project's own rule selection. This belongs in the fallback prose rather than in an `ungranted_note`, since the pair is mixed and the field is rejected there.

The security records' TypeScript paragraphs also carry the per-record grep patterns, as the Python ones do: `child_process.exec`, `new Function(`, bare `eval(` for `dangerous-calls`; template-interpolated SQL and `path.join` on request-derived input for `injection` and `unsafe-io`; `createHash('md5')`, `Math.random()` used for anything token-shaped, and `rejectUnauthorized: false` for `crypto`. Each record keeps the instruction to read every hit rather than trusting the scanner, which matters more here than in Python given the plugin's own false-positive warning.

## Skill descriptions

Both domain `description:` fields currently state the gap this work closes: `test-audit` says its entries "are currently Python-first, so a partition in another language reports `not-applicable` where no lens exists rather than a clean result", and `security-audit` says the same of everything but its secret scanners. Both sentences become false when the records land, and the description is what a model reads to decide whether to invoke the skill, so both are corrected in the same change. A `grep` for `Python-first` finds these two occurrences and no others.

Each skill's `**Detect**` paragraph gains the TypeScript names beside the Python ones it already gives as examples, because that paragraph is where an executing agent learns what to look for in the project inventory.

## Consequences for the gates

`tests/scripts/test_audit_checks.py::test_the_classification_is_not_vacuous` holds a floor on the number of records that classify any tool. That count is 18 today and becomes 22, because the four security records gain a `needs:` key and no test record gains or loses one. The floor moves to 22 in the same commit as the records, which is what the test's own docstring requires of work that adds a tier.

`test_a_tool_has_one_tier_across_the_family` must keep passing without being weakened: `eslint` matches the `arch` records at `target-execution`, `semgrep` stays unclassified in every record that names it, and `eslint-plugin-security`, `vitest`, `jest`, `c8` and `@stryker-mutator/core` are new names classified once each and consistently.

The `ungranted_note` floor test is unaffected: no note is added or removed, three are extended in place, and `mutation`'s stays the sentinel.

Nothing here changes any record's `handbook:` list, so the traceability matrix needs no edit and the integrity gate should pass untouched. Nothing here edits `audit-core/SKILL.md` or `audit/SKILL.md`, so `docs/audit/sweep-obligations.md` needs no row and no disposition revisited.

## Out of scope

The `ungranted_note` per-record-versus-per-language schema question. An end-to-end run against a real TypeScript target, which becomes its own issue. Any language beyond TypeScript. The four domains whose tooling is already language-agnostic (`ci`, `docs`, `eval`, `prompt`), which are correct as they are. `test/assertion-strength` and `security/sensitive-data`, read and confirmed language-neutral.

## Acceptance

Ten records carry a TypeScript lens, no record's `ungranted_note` requirement flips, the classification floor moves with the count it measures, both domain descriptions stop asserting a Python-first limitation, and every tool name in the diff traces to the entry in the verified-facts table above. `uv run pytest tests/ -q`, `uv run ruff check .`, `uv run ruff format --check .` and `uv run python scripts/render_handbook_traceability.py --check` all pass. Issue #5's second acceptance criterion is ticked, and its first, third and fourth stay ticked.
