# TypeScript lens for test-audit and security-audit - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Executed, and five of its instructions were wrong. Do not re-run this plan verbatim.** The prose below is left exactly as written, because a plan is a record of what was instructed at the time and correcting it in place would destroy the evidence that these mistakes were made and caught. But its checkboxes are unticked and the text reads as live instruction, so what execution disproved is listed here rather than left for a future reader to rediscover. In each case the shipped file is right and this plan is wrong: Task 1 Step 5 and Task 4 Step 6 say `semgrep` and `diff-cover` "are not npm packages" and that a JavaScript one-shot runner "will not find" them, when npm carries a bin-less placeholder named `semgrep` and a working third-party TypeScript port published as `diff-cover`, so `npx` fetches unvetted code or runs the wrong tool rather than failing cleanly; both steps also say bare `pipx`, which installs rather than runs. Task 2 Step 5 gives `c8 --check-coverage --branches <n>` as the coverage measurement, when that is a threshold gate whose nonzero exit reads as `tool-failed`. Task 3 Step 5 gives bare `vitest`, which enters watch mode on an interactive terminal. Task 4 Step 7 attributes "agnostic to test runners" to fast-check's documentation, a phrase its README does not contain. The design spec's **Verified tool facts** table carries the corrected facts and is the authority; where this plan and that table disagree, the table wins.

**Goal:** Give ten check records a TypeScript lens so `test-audit` and `security-audit` stop reporting `not-applicable` for every check on a TypeScript partition.

**Architecture:** Each change is one check record's YAML frontmatter plus its `## Tooling fallback` prose. A new test in `tests/scripts/test_audit_checks.py` asserts that every record carrying a `tooling:` key offers a lens for TypeScript, with a shrinking allowlist of records that do not; each task removes its own records from that allowlist, so every task has a failing test before it starts and a green suite when it commits.

**Tech Stack:** Markdown records with YAML frontmatter under `.agents/skills/<domain>-audit/checks/`, validated by `scripts/audit_checks.py`, tested with pytest, formatted and linted by ruff.

**Spec:** `docs/superpowers/specs/2026-08-10-typescript-test-security-lens-design.md`. Its **Verified tool facts** table is the authority for every tool name below.

## Global Constraints

- **Every tool name, subcommand, config key and flag in a record must trace to the spec's Verified tool facts table.** Do not add a name that is not in it. If a task seems to need one, stop and ask - the two facts the spec deliberately leaves unasserted (semgrep's install channels beyond the Python registry, and per-package-manager one-shot runner names) must be read off their own documentation before any record names them.
- **Markdown is never hard-wrapped: one paragraph is one source line.** Never reflow a line you did not otherwise change.
- Use ` - ` where prose needs a dash. No em-dash (U+2014) anywhere in this change.
- A `needs:` entry repeats a name from `tooling:` **exactly**; the validator checks the repetition, so a typo fails the gate rather than being ignored.
- `ungranted_note` is one field per record, required where any language it offers is fully tiered and rejected as vacuous elsewhere. **No record in this change gains or loses the field.** Three have their prose extended; `test/mutation` keeps the sentinel `none`.
- Never assert a count you did not compute in the same breath.
- Commit messages reference the issue as `Refs #5`. These records are agentic prompts, so **every commit message states why the change was made, not only what changed.**
- Before every commit: `uv run pytest tests/ -q`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run python scripts/render_handbook_traceability.py --check`. All four must pass. Where a task edits Python, run `uv run ruff format .` first and keep whatever it produces - `extend-exclude = ["docs"]` means it will not touch the specs or this plan, but it does own the formatting of the test file.
- No record's `handbook:` list changes, so the traceability matrix and `docs/audit/sweep-obligations.md` are not edited by any task. If a task finds itself wanting to, stop and ask.

## File Structure

| File | Responsibility in this change |
| --- | --- |
| `.agents/skills/security-audit/checks/{crypto,dangerous-calls,injection,unsafe-io}.md` | Gain a `typescript:` list, their first `needs:` key, and a `**TypeScript** - ` fallback paragraph |
| `.agents/skills/test-audit/checks/coverage-reach.md` | Gains `typescript:`, three tiered names, per-language fallback paragraphs, and a two-language `ungranted_note` |
| `.agents/skills/test-audit/checks/{determinism,isolation}.md` | Same shape as `coverage-reach`, two names each |
| `.agents/skills/test-audit/checks/mutation.md` | Gains `typescript:` and a tiered name; note stays the sentinel |
| `.agents/skills/test-audit/checks/new-code-coverage.md` | `tooling.python` becomes `tooling.any`; fallback gains the TypeScript producer path |
| `.agents/skills/test-audit/checks/property-based-gap.md` | Gains `typescript:`, a language-neutral claim line, and a `## Tooling fallback` section it does not currently have |
| `.agents/skills/{test,security}-audit/SKILL.md` | `description:` stops asserting a Python-first limitation; `**Detect**` gains the TypeScript names |
| `tests/scripts/test_audit_checks.py` | New TypeScript-lens invariant with a shrinking allowlist; classification floor 18 to 22; one stale docstring prediction about this issue corrected |

---

### Task 1: security-audit gains a TypeScript lens

**Files:**
- Modify: `.agents/skills/security-audit/checks/crypto.md`
- Modify: `.agents/skills/security-audit/checks/dangerous-calls.md`
- Modify: `.agents/skills/security-audit/checks/injection.md`
- Modify: `.agents/skills/security-audit/checks/unsafe-io.md`
- Test: `tests/scripts/test_audit_checks.py`

**Interfaces:**
- Produces: the constant `_NO_TYPESCRIPT_LENS` in `tests/scripts/test_audit_checks.py`, a `frozenset` of check ids that carry a `tooling:` key but offer neither `typescript:` nor `any:`. Tasks 2, 3 and 4 remove ids from it. Its end state after Task 4 is exactly `{"arch/martin-metrics", "docs/docstring-coverage"}`.

- [ ] **Step 1: Write the failing test**

Add to `tests/scripts/test_audit_checks.py`, after `test_the_classification_is_not_vacuous`. The allowlist is the current twelve minus the four this task fixes, so the test fails until the records are authored:

```python
_NO_TYPESCRIPT_LENS = {
    # arch/martin-metrics and docs/docstring-coverage are the debt this sweep
    # did not clear: #5 scoped its remaining half to test-audit and
    # security-audit. Both are python-only and both are real gaps.
    "arch/martin-metrics",
    "docs/docstring-coverage",
    "test/coverage-reach",
    "test/determinism",
    "test/isolation",
    "test/mutation",
    "test/new-code-coverage",
    "test/property-based-gap",
}


def test_every_tooling_record_offers_a_typescript_lens():
    """`audit-core` reports `not-applicable` where a check "has no lens in
    this partition's languages", so a record offering only `python:` tools
    is how a TypeScript partition earns a clean bill of health for code
    nobody looked at. Assert the exception set rather than a count, and
    assert it by equality: a new python-only record fails because it is not
    in the set, and a record whose lens was added fails until it is removed
    from the set, so the set cannot quietly outlive the debt it names. A
    record with no `tooling:` key at all is not in scope - it prescribes a
    reading pass, which needs no language. If this fails, add the lens or
    add the record to the set with a reason; do not delete the assertion.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    gaps = {
        check_id
        for check_id, check in checks.items()
        if check.tooling and not ({"typescript", "any"} & set(check.tooling))
    }
    assert gaps == _NO_TYPESCRIPT_LENS, (
        f"missing a TypeScript lens: {sorted(gaps - _NO_TYPESCRIPT_LENS)}; "
        f"lens added but still listed: {sorted(_NO_TYPESCRIPT_LENS - gaps)}"
    )
```

Also change the classification floor in `test_the_classification_is_not_vacuous` from `18` to `22`, since the four records below gain their first `needs:` key and that test's docstring requires the floor to move with the count:

```python
    assert len(classified) >= 22, (
        f"only {len(classified)} record(s) classify any tool: {classified}"
    )
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/scripts/test_audit_checks.py -q`

Expected: two failures. `test_every_tooling_record_offers_a_typescript_lens` reports `missing a TypeScript lens: ['security/crypto', 'security/dangerous-calls', 'security/injection', 'security/unsafe-io']`, and `test_the_classification_is_not_vacuous` reports `only 18 record(s) classify any tool`.

- [ ] **Step 3: Add the frontmatter to all four records**

In each of `crypto.md`, `dangerous-calls.md`, `injection.md` and `unsafe-io.md`, replace the `tooling:` block:

```yaml
tooling:
  python: [bandit, ruff, semgrep]
```

with:

```yaml
tooling:
  python: [bandit, ruff, semgrep]
  typescript: [semgrep, eslint, eslint-plugin-security]
needs:
  target-execution: [eslint, eslint-plugin-security]
```

`semgrep` is deliberately absent from `needs:`, which is the positive claim that it answers from a read-only clone. That is what keeps each TypeScript pair mixed rather than fully tiered, and therefore what keeps `ungranted_note` correctly rejected on these records. Do not add the field; the loader will reject it as vacuous.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/scripts/test_audit_checks.py -q`

Expected: PASS. In particular `test_a_tool_has_one_tier_across_the_family` must pass without modification, because `eslint` at `target-execution` is the tier `arch/complexity` and `arch/hidden-coupling` already give it. If that test fails, do not weaken it - the tier is wrong.

- [ ] **Step 5: Add the shared TypeScript fallback paragraph to all four records**

In each of the four records, insert this paragraph immediately after the existing `**Python** - ` paragraph in `## Tooling fallback`, as a single source line:

```
**TypeScript** - `semgrep scan --config p/javascript` (add `--config p/typescript` for the TypeScript-specific rules; both are Semgrep Registry rulesets), or ESLint with `eslint-plugin-security`, whose `recommended` flat config turns on the `detect-*` rules. Record rule id + `file:line` per hit. Semgrep is not an npm package, so fetch it with `uvx` or `pipx`; the partition's own one-shot runner will not find it, and an attempt that fails that way is indistinguishable from a missing tool. ESLint is normally the target's own dependency and runs under the target's flat config; because `eslint-plugin-security`'s rules need no type information, it can also run under an audit-owned flat config with `--config` and `--no-config-lookup` and a parser fetched alongside ESLint, which is what makes it answerable without the target's `node_modules`. What the target's own config buys is the project's own rule selection. Triage every hit by reading it: the plugin's own documentation warns it "finds a lot of false positives which need triage by a human", so an untriaged hit list is not a finding list.
```

- [ ] **Step 6: Add the per-record rule and grep pointers**

Each record names the plugin rules and grep targets for its own subject. Append one paragraph per record, immediately after the shared TypeScript paragraph, as a single source line.

`crypto.md`:

```
**TypeScript rules and greps for this check** - `detect-pseudoRandomBytes` and `detect-possible-timing-attacks` are the plugin rules that bear on crypto and randomness. Grep for `createHash('md5')`, `createHash('sha1')`, `Math.random()` wherever the value is token-shaped, and `rejectUnauthorized: false`, and read each hit: `Math.random()` picking a UI jitter is not a weak token.
```

`dangerous-calls.md`:

```
**TypeScript rules and greps for this check** - `detect-child-process`, `detect-eval-with-expression`, `detect-non-literal-require`, `detect-new-buffer` and `detect-buffer-noassert`. Grep for `eval(`, `new Function(`, `child_process.exec(`, `execSync(`, `vm.runInNewContext` and `require(` on anything that is not a literal, and read each hit.
```

`injection.md`:

```
**TypeScript rules and greps for this check** - `detect-object-injection`, `detect-disable-mustache-escape`, `detect-non-literal-regexp` and `detect-unsafe-regex`. Grep for template-interpolated SQL, `innerHTML =` and `dangerouslySetInnerHTML`, and read each hit. `detect-object-injection` in particular fires on ordinary dynamic property access, so it is the rule most likely to produce volume without findings.
```

`unsafe-io.md`:

```
**TypeScript rules and greps for this check** - `detect-non-literal-fs-filename`. Grep for `path.join(` and the `fs` read and write calls where any component derives from a request, and for `..` traversal, and read each hit.
```

`injection.md` already carries a `**Dataflow verification (the load-bearing step):**` paragraph that applies to both languages. Leave it where it is and do not duplicate it.

- [ ] **Step 7: Run the full gates**

Run each of:

```bash
uv run pytest tests/ -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/render_handbook_traceability.py --check
```

Expected: all pass. The traceability gate is unaffected because no `handbook:` list changed.

- [ ] **Step 8: Commit**

```bash
git add .agents/skills/security-audit/checks/crypto.md .agents/skills/security-audit/checks/dangerous-calls.md .agents/skills/security-audit/checks/injection.md .agents/skills/security-audit/checks/unsafe-io.md tests/scripts/test_audit_checks.py
git commit -m "feat: give the security records a TypeScript lens

These four records offered only Python tools, and audit-core reads that
as no lens in the partition's languages - so every one of them reported
not-applicable on a TypeScript partition, which is how a polyglot
repository earns a clean bill of health for code nobody looked at.

semgrep is listed without a needs: tier on purpose. It answers from a
read-only clone, so each TypeScript pair stays mixed rather than fully
tiered, and ungranted_note stays correctly rejected here rather than
four records having to invent one. The prose says what eslint needs
instead, including the audit-owned-config path its plugin allows by
needing no type information.

The new test asserts the lens exists by equality against a named
exception set rather than by a count, so a python-only record cannot be
added silently and a cleared gap cannot stay listed.

Refs #5"
```

---

### Task 2: test/coverage-reach gains a TypeScript lens

**Files:**
- Modify: `.agents/skills/test-audit/checks/coverage-reach.md`
- Test: `tests/scripts/test_audit_checks.py`

**Interfaces:**
- Consumes: `_NO_TYPESCRIPT_LENS` from Task 1.

- [ ] **Step 1: Shrink the allowlist so the test fails**

In `tests/scripts/test_audit_checks.py`, delete the `"test/coverage-reach",` line from `_NO_TYPESCRIPT_LENS`.

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/scripts/test_audit_checks.py::test_every_tooling_record_offers_a_typescript_lens -q`

Expected: FAIL with `missing a TypeScript lens: ['test/coverage-reach']`.

- [ ] **Step 3: Add the frontmatter**

Replace:

```yaml
tooling:
  python: [pytest-cov, coverage.py]
needs:
  target-execution: [pytest-cov, coverage.py]
```

with:

```yaml
tooling:
  python: [pytest-cov, coverage.py]
  typescript: [vitest, jest, c8]
needs:
  target-execution: [pytest-cov, coverage.py, vitest, jest, c8]
```

All three TypeScript names run the target's own suite to produce a coverage report, so all three are `target-execution`. That makes the TypeScript pair fully tiered, which it already was in Python, so the record's `ungranted_note` requirement does not change - only its prose, in the next step.

- [ ] **Step 4: Extend the ungranted_note to cover the TypeScript partition**

Replace the whole `ungranted_note:` block with this one. It keeps every claim the existing note makes and adds the TypeScript reading, in the shape `arch/complexity` uses:

```yaml
ungranted_note: >-
  What is excluded from measurement is readable with nothing installed, in either
  language. In Python, `[tool.coverage.run]`'s `source` and `omit`, and
  `[tool.coverage.report]`'s `exclude_lines`, in `pyproject.toml` (`[run]` and
  `[report]` respectively in `.coveragerc`), name the code no coverage number will
  ever account for. In TypeScript the same reading is `coverage.include` and
  `coverage.exclude` in `vitest.config.*`, or `collectCoverageFrom` and
  `coveragePathIgnorePatterns` in `jest.config.*` or `package.json`'s `jest` key; a
  branch threshold the project set for itself is readable in the same place
  (`coverage.thresholds.branches`, `coverageThreshold.global.branches`) and says what
  it asked of itself. That is part of what this check asks. The reach measurement
  itself runs the suite and does not survive a withheld grant, in either language.
  Whether a coverage threshold is *enforced* is a different check's question -
  `ci/gate-enforcement` owns whether an intended gate is actually required - so do not
  answer it here.
```

- [ ] **Step 5: Restructure the fallback into per-language paragraphs**

Replace the single `**Coverage (with branches):**` paragraph in `## Tooling fallback` with these three source lines:

```
**Python** - `pytest --cov=<pkg> --cov-branch --cov-report=term-missing` (or `coverage run -m pytest` + `coverage report --show-missing`). Branch coverage is the signal; capture the missing line/branch ranges per module as the evidence pointer.

**TypeScript** - use the runner the project inventory says the partition has, because neither runner can run the other's suite: `vitest run --coverage`, whose coverage needs the coverage provider the partition has configured to be installed, or `jest --coverage`. Both report branch coverage. Where the partition's runner has no coverage integration, `c8` wraps an arbitrary command - `c8 --check-coverage --branches <n> <the partition's test command>` - and is fetchable from the partition's own registry, so its own one-shot runner obtains it. Capture the missing line/branch ranges per module, as in Python.

**Both** - every command above runs the target's own suite to produce that report, which is the `target-execution` grant; without it the reach measurement itself is `no-evidence (not-permitted)`, and what remains is the exclusion-config reading described in this record's `ungranted_note`.
```

- [ ] **Step 6: Run the gates**

Run each of:

```bash
uv run pytest tests/ -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/render_handbook_traceability.py --check
```

Expected: all pass. `test_the_classification_is_not_vacuous` still passes because this record already had a `needs:` key, so the count did not move; the floor is already 22 from Task 1.

- [ ] **Step 7: Commit**

```bash
git add .agents/skills/test-audit/checks/coverage-reach.md tests/scripts/test_audit_checks.py
git commit -m "feat: let coverage-reach measure a TypeScript partition

The record named only Python coverage tools, so the check reported
not-applicable on a TypeScript partition rather than measuring anything.

The ungranted_note grows rather than the schema. The record was already
fully tiered in Python, so it already carried the field; adding a second
fully-tiered language changes what the note has to say, not whether it
is required. It now names the TypeScript exclusion keys, because what a
project excludes from measurement is readable with nothing installed and
is part of what this check asks - the same argument the Python half
already made.

Refs #5"
```

---

### Task 3: test/determinism and test/isolation gain a TypeScript lens

**Files:**
- Modify: `.agents/skills/test-audit/checks/determinism.md`
- Modify: `.agents/skills/test-audit/checks/isolation.md`
- Test: `tests/scripts/test_audit_checks.py`

**Interfaces:**
- Consumes: `_NO_TYPESCRIPT_LENS` from Task 1.

- [ ] **Step 1: Shrink the allowlist so the test fails**

Delete the `"test/determinism",` and `"test/isolation",` lines from `_NO_TYPESCRIPT_LENS`.

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/scripts/test_audit_checks.py::test_every_tooling_record_offers_a_typescript_lens -q`

Expected: FAIL with `missing a TypeScript lens: ['test/determinism', 'test/isolation']`.

- [ ] **Step 3: Add determinism's frontmatter**

In `determinism.md`, replace:

```yaml
tooling:
  python: [pytest-randomly, pytest-rerunfailures]
needs:
  target-execution: [pytest-randomly, pytest-rerunfailures]
```

with:

```yaml
tooling:
  python: [pytest-randomly, pytest-rerunfailures]
  typescript: [vitest, jest]
needs:
  target-execution: [pytest-randomly, pytest-rerunfailures, vitest, jest]
```

- [ ] **Step 4: Extend determinism's ungranted_note**

Replace the whole `ungranted_note:` block with this. The Ruff caveat is kept verbatim and stays Python-specific: **do not invent a TypeScript analogue of it**, because nothing in the spec's verified facts supports naming one.

```yaml
ungranted_note: >-
  Grepping tests for non-deterministic inputs answers that axis with nothing
  installed, in either language: `time.time()`, `datetime.now()`, `random.` without a
  seed and live network calls in Python; `Date.now()`, a `new Date()` with no fixed
  argument, `Math.random()` with no seeded generator, and live `fetch` or HTTP-client
  calls in TypeScript. What the project already asked for is readable too: a `retry` or
  `repeats` setting, or a `sequence.shuffle` already enabled in `vitest.config.*`, says
  the project knows its own suite is order- or timing-sensitive. The randomized-order
  and repeat-run passes run the target's own suite and do not survive a withheld grant,
  so order-dependence specifically goes unmeasured in either language. Ruff is not a
  substitute for the Python grep, though it looks like one: `DTZ005` asks whether a
  `datetime.now()` is timezone-aware rather than whether it is deterministic, so it
  stays silent on `datetime.now(tz=...)`, which is exactly as non-deterministic; and
  `S311` flags `random.` as cryptographically weak whether or not a seed was set on the
  line above, so it fires on the deterministic case.
```

- [ ] **Step 5: Restructure determinism's fallback**

Replace the single `**Flakiness:**` paragraph with these three source lines:

```
**Python** - run the suite in randomized order (`pytest-randomly` randomizes automatically once installed; use `--randomly-seed=<n>` to reproduce a failing order) and, for suspected flakies, repeat runs; flag order-dependence and non-determinism.

**TypeScript** - use the partition's own runner. `vitest --sequence.shuffle --sequence.seed=<n>` randomizes order reproducibly, and `retry` or `repeats` re-runs tests to expose flakiness. `jest --randomize --seed <n>` shuffles order within a file, and is supported only on the default `jest-circus` runner, so a project on a custom runner has no randomize flag at all and the grep below carries this check on its own.

**Both** - grep the tests for the non-deterministic constructs named in this record's `ungranted_note` and read each hit; a seeded generator is not a flake, and neither is a timestamp the test pins.
```

- [ ] **Step 6: Add isolation's frontmatter**

In `isolation.md`, replace:

```yaml
tooling:
  python: [pytest-timeout]
needs:
  target-execution: [pytest-timeout]
```

with:

```yaml
tooling:
  python: [pytest-timeout]
  typescript: [vitest, jest]
needs:
  target-execution: [pytest-timeout, vitest, jest]
```

- [ ] **Step 7: Extend isolation's ungranted_note**

Replace the whole `ungranted_note:` block with:

```yaml
ungranted_note: >-
  Reading test source for calls that hit the network, the filesystem or a database
  answers the real-I/O axis with nothing installed, in either language. What the
  project configured is readable in the same way: a `testTimeout` raised well above its
  default (5000ms in jest), `isolate: false` or a non-default `pool` in
  `vitest.config.*`, and a `slowTestThreshold` above its 300ms default each say the
  suite has tests needing more than an isolated unit test should. The timing pass runs
  the target's own suite, so without the grant the duration evidence is missing and this
  check is answered on the I/O axis rather than `no-evidence` as a whole, in either
  language.
```

- [ ] **Step 8: Restructure isolation's fallback**

Replace the single `**Speed/isolation:**` paragraph with these two source lines:

```
**Python** - `pytest --durations=25` for the slowest tests; check unit tests for real I/O.

**TypeScript** - the partition's own runner reports a duration per test; vitest additionally marks anything past `slowTestThreshold`, which defaults to 300ms, and an `isolate: false` or non-default `pool` in its config tells you the suite has been opted out of per-file isolation deliberately rather than by accident. Check unit tests for real I/O the same way.
```

- [ ] **Step 9: Run the gates**

Run each of:

```bash
uv run pytest tests/ -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/render_handbook_traceability.py --check
```

Expected: all pass.

- [ ] **Step 10: Commit**

```bash
git add .agents/skills/test-audit/checks/determinism.md .agents/skills/test-audit/checks/isolation.md tests/scripts/test_audit_checks.py
git commit -m "feat: let determinism and isolation read a TypeScript suite

Both records named only pytest plugins, so both reported
not-applicable on a TypeScript partition instead of looking.

Each note now names what a TypeScript partition still answers with the
grant withheld, which is more than the tier alone implies: the
non-determinism greps and the isolation settings are source and config
reads, and a project that already set retry, sequence.shuffle, a raised
testTimeout or isolate: false has told you something about its own suite
before any tool runs.

determinism's Ruff caveat stays Python-only deliberately. It exists
because two specific ruff rules look like determinism checks and are
not; no verified TypeScript equivalent was found, and inventing a
symmetric warning would assert something unchecked.

Refs #5"
```

---

### Task 4: mutation, new-code-coverage and property-based-gap

**Files:**
- Modify: `.agents/skills/test-audit/checks/mutation.md`
- Modify: `.agents/skills/test-audit/checks/new-code-coverage.md`
- Modify: `.agents/skills/test-audit/checks/property-based-gap.md`
- Test: `tests/scripts/test_audit_checks.py`

**Interfaces:**
- Consumes: `_NO_TYPESCRIPT_LENS` from Task 1. After this task it contains exactly `{"arch/martin-metrics", "docs/docstring-coverage"}`.

- [ ] **Step 1: Shrink the allowlist so the test fails**

Delete the `"test/mutation",`, `"test/new-code-coverage",` and `"test/property-based-gap",` lines from `_NO_TYPESCRIPT_LENS`, leaving only the two `arch`/`docs` entries and the comment above them.

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/scripts/test_audit_checks.py::test_every_tooling_record_offers_a_typescript_lens -q`

Expected: FAIL with `missing a TypeScript lens: ['test/mutation', 'test/new-code-coverage', 'test/property-based-gap']`.

- [ ] **Step 3: Add mutation's frontmatter**

In `mutation.md`, replace:

```yaml
tooling:
  python: [mutmut, cosmic-ray]
needs:
  target-execution: [mutmut, cosmic-ray]
```

with:

```yaml
tooling:
  python: [mutmut, cosmic-ray]
  typescript: ["@stryker-mutator/core"]
needs:
  target-execution: [mutmut, cosmic-ray, "@stryker-mutator/core"]
```

The quotes are required: an unquoted YAML scalar cannot begin with `@`. `ungranted_note: none` stays exactly as it is - Stryker's whole method is re-running the target's suite once per injected mutant, so a withheld grant leaves no residual axis in TypeScript any more than in Python.

- [ ] **Step 4: Restructure mutation's fallback**

Replace the single `**Mutation score:**` paragraph with these three source lines:

```
**Python** - `mutmut run` or `cosmic-ray`.

**TypeScript** - `npx stryker run`, from `@stryker-mutator/core`, which drives the partition's own runner through a matching plugin (`@stryker-mutator/vitest-runner`, `@stryker-mutator/jest-runner` or `@stryker-mutator/mocha-runner`, selected by `testRunner` and `plugins` in `stryker.config.json`). Core on its own runs nothing, so a partition whose runner has no plugin has no mutation lens and this check is `not-applicable` there rather than clean.

**Both** - every one of these re-runs the target's own suite once per injected mutant, so this check needs the `target-execution` grant, and it is the most expensive tool in this family to run - many suite executions rather than one. Without the grant it is `no-evidence (not-permitted)`. Where the grant exists, scope the run to the highest-risk module rather than the whole suite; a full-suite mutation run multiplies an already-slow tool by every module in the tree.
```

- [ ] **Step 5: Change new-code-coverage's tooling key**

In `new-code-coverage.md`, replace:

```yaml
tooling:
  python: [diff-cover]
```

with:

```yaml
tooling:
  any: [diff-cover]
```

Do not add a `needs:` key. The record's existing prose argues at length that the tool needs nothing from the target, and that argument is unchanged by the key.

- [ ] **Step 6: Add new-code-coverage's TypeScript producer path**

The `**Diff coverage:**` paragraph stays one paragraph, because the tool is one tool for both languages. Append these two sentences to the end of that paragraph's source line, after `...never a clean result.`:

```
Both TypeScript runners can produce an input it accepts: `diff-cover`'s own documentation takes "Cobertura, Clover or JaCoCo XML format, or LCov format", and `lcov` is a documented reporter for `vitest` (`coverage.reporter`) and for `jest` (`coverageReporters`, which accepts any istanbul reporter). `diff-cover` is itself a Python-registry package, so run it with `uvx` or `pipx` whatever the partition's language is - the partition's own one-shot runner will not find it, and that failure looks exactly like a missing tool.
```

- [ ] **Step 7: Rewrite property-based-gap**

Its claim line names one language's library. Replace:

```
Identify pure functions that would benefit from `hypothesis` property tests over example-based ones - ask the user.
```

with:

```
Identify pure functions that would benefit from property-based tests over example-based ones - ask the user.
```

Add the `typescript:` entry to its frontmatter, replacing:

```yaml
tooling:
  python: [hypothesis]
```

with:

```yaml
tooling:
  python: [hypothesis]
  typescript: [fast-check]
```

Do not add a `needs:` key: neither library needs the suite run to answer this check.

Then append a `## Tooling fallback` section, which this record does not currently have, after the claim line:

```
## Tooling fallback

**Python** - `hypothesis`. **TypeScript** - `fast-check`. Both are libraries imported inside the partition's existing tests rather than runners of their own - fast-check's own documentation describes it as "agnostic to test runners" - so neither needs the suite run to answer this check: the gap is found by reading the pure functions and the tests covering them, and judging where a property would say more than a handful of examples. Prefer whichever the partition already depends on. Where neither is present the absence is itself the finding, so name the functions that would benefit rather than prescribing a library.
```

- [ ] **Step 8: Run the gates**

Run each of:

```bash
uv run pytest tests/ -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/render_handbook_traceability.py --check
```

Expected: all pass, and `test_every_tooling_record_offers_a_typescript_lens` now passes with the two-entry allowlist.

- [ ] **Step 9: Commit**

```bash
git add .agents/skills/test-audit/checks/mutation.md .agents/skills/test-audit/checks/new-code-coverage.md .agents/skills/test-audit/checks/property-based-gap.md tests/scripts/test_audit_checks.py
git commit -m "feat: complete the test-audit TypeScript lens

Three records left. Each needed a different answer, and only one of them
needed a new tool named.

new-code-coverage names no new tool at all: diff-cover moves from
python: to any:, because the language key says which partitions a lens
serves and this tool reads a coverage report and a git diff. Its docs
accept LCov, which both TypeScript runners emit, so the lens already
served a TypeScript partition and the python: key was simply wrong about
its own reach. What needs the grant is producing the report, which the
record already separated from answering the check.

mutation keeps its sentinel note. Stryker re-runs the suite per mutant,
so a withheld grant leaves nothing behind in TypeScript either - and
because core drives the target's own runner through a plugin, a
partition with no matching plugin is not-applicable rather than clean.

property-based-gap stops naming one language's library in a claim that
was never about a library, and gains the fallback section it never had.
Neither hypothesis nor fast-check is tiered: this check is answered by
reading pure functions, not by running them.

Refs #5"
```

---

### Task 5: correct the prose the change invalidated

**Files:**
- Modify: `.agents/skills/test-audit/SKILL.md`
- Modify: `.agents/skills/security-audit/SKILL.md`
- Modify: `tests/scripts/test_audit_checks.py`

**Interfaces:**
- Consumes: nothing. This task depends only on Tasks 1 to 4 having landed.

- [ ] **Step 1: Confirm what the change invalidated**

Run: `grep -rn "Python-first" .agents/ docs/ tests/ scripts/`

Expected: exactly two hits, both in the `description:` line of `.agents/skills/test-audit/SKILL.md` and `.agents/skills/security-audit/SKILL.md`. If there are more, the extra ones are in scope for this task too.

- [ ] **Step 2: Correct test-audit's description**

In `.agents/skills/test-audit/SKILL.md`, in the `description:` value, replace:

```
whose entries are currently Python-first, so a partition in another language reports `not-applicable` where no lens exists rather than a clean result.
```

with:

```
whose entries cover Python and TypeScript, so a partition in a third language reports `not-applicable` where no lens exists rather than a clean result.
```

- [ ] **Step 3: Correct security-audit's description**

In `.agents/skills/security-audit/SKILL.md`, in the `description:` value, replace:

```
whose entries are language-agnostic for the secret scanners and Python-first otherwise, so a partition in another language reports `not-applicable` where no lens exists rather than a clean result.
```

with:

```
whose entries are language-agnostic for the secret scanners and cover Python and TypeScript otherwise, so a partition in a third language reports `not-applicable` where no lens exists rather than a clean result.
```

- [ ] **Step 4: Give test-audit's Detect paragraph the TypeScript names**

In `.agents/skills/test-audit/SKILL.md`, in the `**Detect**` paragraph, replace:

```
e.g., for a Python partition, `pytest-cov` / `coverage.py`, `diff-cover`, `pytest-randomly` / `pytest-rerunfailures`, `pytest-timeout`, `hypothesis`, and `mutmut` / `cosmic-ray` respectively, or another language's equivalents.
```

with:

```
e.g., for a Python partition, `pytest-cov` / `coverage.py`, `diff-cover`, `pytest-randomly` / `pytest-rerunfailures`, `pytest-timeout`, `hypothesis`, and `mutmut` / `cosmic-ray` respectively; for a TypeScript partition, the partition's own runner's coverage or `c8`, `diff-cover` over an LCov report, `vitest`'s `sequence.shuffle` or `jest --randomize`, `testTimeout` / `slowTestThreshold`, `fast-check`, and `@stryker-mutator/core`; or another language's equivalents.
```

In the same file's test-layout bullet, replace:

```
(from the project inventory's test-runner field, e.g. `pytest` / `unittest` for a Python partition, or the detected language's equivalent)
```

with:

```
(from the project inventory's test-runner field, e.g. `pytest` / `unittest` for a Python partition, `vitest` / `jest` for a TypeScript one, or the detected language's equivalent)
```

- [ ] **Step 5: Give security-audit's Detect paragraph the TypeScript names**

In `.agents/skills/security-audit/SKILL.md`, in the `**Detect**` paragraph, replace:

```
a SAST scanner (e.g. `bandit`, or `ruff` with the `S` = flake8-bandit ruleset for a Python partition, or a language-appropriate equivalent such as `semgrep`)
```

with:

```
a SAST scanner (e.g. `bandit`, or `ruff` with the `S` = flake8-bandit ruleset for a Python partition, `eslint` with `eslint-plugin-security` for a TypeScript one, or the language-agnostic `semgrep`)
```

- [ ] **Step 6: Correct the stale prediction about this issue in the note-floor docstring**

The docstring of `test_the_notes_are_not_all_sentinels` predicts what this issue would do to the note count, and predicts it wrongly: it expected #5 to add notes. Confirm you are in the right place with `grep -n "produced ten" tests/scripts/test_audit_checks.py` - the phrase wraps across source lines, so do not grep for a longer span of it.

Replace exactly this passage, keeping its four-space docstring indentation:

```
    Issue #5 is expected to add notes, which raises the count and
    therefore the slack above this floor rather than raising the floor
    itself; raise the floor by hand if that slack should be closed. Never
    lower it to make a deletion pass.
```

with:

```
    Issue #5 did not add notes, contrary to what this docstring first
    predicted: it gave three already-silenced records a second fully
    tiered language, which changes what a note must say and not whether
    the record carries one, so the count did not move. A later change
    that does add notes raises the count and therefore the slack above
    this floor rather than the floor itself; raise the floor by hand if
    that slack should be closed. Never lower it to make a deletion pass.
```

The final sentence is load-bearing and must survive the edit: it is the instruction not to lower the floor to make a deletion pass.

- [ ] **Step 7: Verify the note count really did not move**

Run:

```bash
uv run python -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('ac', 'scripts/audit_checks.py')
ac = importlib.util.module_from_spec(spec); sys.modules['ac'] = ac; spec.loader.exec_module(ac)
checks, errors = ac.load_checks(ac.SKILLS_DIR)
assert not errors, errors
prose = [c.id for c in checks.values() if c.ungranted_note not in (None, ac.UNGRANTED_NONE)]
print('prose notes:', len(prose))
print('classified:', len([c.id for c in checks.values() if c.needs]))
"
```

Expected: `prose notes: 10` and `classified: 22`. If the note count is not 10, a task added or removed a note it should not have - stop and report it rather than editing the floor.

- [ ] **Step 8: Verify the skills still discover**

Run: `claude plugin details handbook-audit`

Expected: the skill count is unchanged from before this branch. `claude plugin validate` does not enumerate skills, so it passes on a plugin that discovers none and is not the check that matters here.

- [ ] **Step 9: Run the gates**

Run each of:

```bash
uv run pytest tests/ -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/render_handbook_traceability.py --check
```

Expected: all pass.

- [ ] **Step 10: Commit**

```bash
git add .agents/skills/test-audit/SKILL.md .agents/skills/security-audit/SKILL.md tests/scripts/test_audit_checks.py
git commit -m "fix: stop two skill descriptions asserting a limit that is gone

Both descriptions told a reader the records were Python-first and that
another language would report not-applicable. That was true when it was
written and is false now, and the description is what a model reads to
decide whether to invoke the skill at all - so a stale one costs an
invocation, not just accuracy. Each now says which two languages the
entries cover and keeps the not-applicable warning for the third.

Each Detect paragraph gains the TypeScript names beside the Python ones
it already gave as examples, because that paragraph is where an
executing agent learns what to look for in the project inventory, and
naming only one ecosystem's tools is how the inventory gets read for the
wrong things.

The note-floor docstring predicted that this issue would add notes and
raise the count. It did not: giving an already-silenced record a second
fully tiered language changes the prose the note must carry, not whether
the record carries one. Record what happened, so the next reader does
not trust the prediction.

Refs #5"
```

---

## Self-Review

**Spec coverage.** Every section of the spec maps to a task. The frontmatter deltas table: security's four in Task 1, `coverage-reach` in Task 2, `determinism` and `isolation` in Task 3, `mutation`, `new-code-coverage` and `property-based-gap` in Task 4. Prose conventions: applied in the fallback steps of Tasks 1 to 4, including the three-kinds statement for every entry and the `uvx`/`pipx` correction for `semgrep` and `diff-cover`. Skill descriptions: Task 5. Consequences for the gates: the floor moves in Task 1, the note count is verified in Task 5 step 7, and the tier-agreement expectation is stated in Task 1 step 4. Out of scope items appear in no task, which is correct; the two records the spec says are already language-neutral are named in Task 1's allowlist comment as out of scope rather than silently omitted.

**One thing the spec did not anticipate and this plan adds:** the TypeScript-lens invariant test. The spec's acceptance section stated the criterion in prose; the repository's own rule is to move a consistency property into the validator where it can go, and this one can. It also supplies the failing test each otherwise prose-only task needs. The two records outside #5's scope are named in the allowlist with the reason, so the debt is recorded in the suite rather than only in an issue.

**Placeholder scan.** No TBD, TODO, "similar to Task N", or step that describes without showing. Every prose insertion is given in full, including the four near-identical security paragraphs, which are repeated rather than cross-referenced because an implementer may read tasks out of order.

**Consistency.** `_NO_TYPESCRIPT_LENS` is spelled identically in Tasks 1 to 4 and shrinks monotonically: 8 entries after Task 1, 7 after Task 2, 5 after Task 3, 2 after Task 4. The `needs:` lists always repeat names present in the same record's `tooling:`. `ungranted_note` is added to no record and removed from none. Tool names used in tasks appear in the spec's verified-facts table: `vitest`, `jest`, `c8`, `@stryker-mutator/core` with its three runner plugins, `fast-check`, `diff-cover`, `semgrep` with `p/javascript` and `p/typescript`, `eslint`, `eslint-plugin-security` with the rule names quoted per record.
