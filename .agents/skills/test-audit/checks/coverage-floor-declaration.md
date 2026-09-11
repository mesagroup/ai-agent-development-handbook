---
id: test/coverage-floor-declaration
domain: test
locality: global
evidence: >-
  One row for the project, not one per module, because the decision is the
  project's. The row records every home that was read and what each held, in
  the absent case as much as the present one - a reader cannot check "no floor
  was decided" without knowing which files were looked in, and an empty answer
  from a config a project does not use says nothing. Where a floor is present,
  the row cites it at `file:line` and records what it is measured over: the
  source scope and the exclusion list that produce its denominator. Where a
  floor exists only in prose, the row cites both the prose and the executable
  homes that were checked and found to hold none, because that pair is the
  finding rather than either half. The changed-lines floor is recorded the same
  way and separately, since a project can decide one and not the other.
handbook:
  - implementation-disciplines/tdd-c
routes:
  - lang: python
    kind: procedure
    note: >-
      Where a Python project's floor lives, all readable from a read-only
      clone. `fail_under` is the declaration in its executable form, and the
      section it sits under is spelled differently per file: coverage.py reads
      `[tool.coverage.report]` in `pyproject.toml`, `[report]` in `.coveragerc`
      - and, in `setup.cfg` or `tox.ini`, only a section prefixed `coverage:`,
      so the heading there is `[coverage:report]` and a search for the bare
      `[report]` reads a project that set a floor as one that set none. Two
      more facts about those files decide whether a floor found in one is
      executable at all. coverage.py takes the **first** file that holds valid
      settings, searching `.coveragerc`, `.coveragerc.toml`, `setup.cfg`,
      `tox.ini` and `pyproject.toml` in that order and ignoring the rest, so a
      `fail_under` in a later file of a project that also configures an earlier
      one is written where the tool will never read it - which is a finding
      here rather than a floor, because nothing enforces it. And
      `pyproject.toml` support needs Python 3.11 or the `toml` extra, so read
      the project's own floor against what it runs on. `--cov-fail-under=<n>` is the same decision written as a
      pytest flag, and it counts wherever it is durable - in a CI step, or in
      pytest's `addopts` - and not when a person types it by hand. Pytest's own
      config files are a second set with a second set of headings, overlapping
      the coverage ones without sharing their spelling: `pytest.toml` or
      `.pytest.toml`, which take precedence over the rest; `pytest.ini` or
      `.pytest.ini` under `[pytest]`; `pyproject.toml` under `[tool.pytest]` or
      `[tool.pytest.ini_options]`; `tox.ini` under `[pytest]`; and `setup.cfg`
      under `[tool:pytest]` - renamed from the bare `[pytest]` to stop it
      colliding with distutils commands, so the bare name is right in `tox.ini`
      and wrong in `setup.cfg`. Pytest also takes only the first matching file,
      so the precedence trap above has a second instance here. What the floor is measured over
      is `[tool.coverage.run]`'s `source` and `omit` plus
      `[tool.coverage.report]`'s `exclude_lines`, which together name the code
      the number will never account for.
    alone_insufficient: >-
      Finding nothing here is not the finding. A project may keep its floor in
      a CI step instead, which the `lang: any` route reads, so absence is only
      evidence once every home has been read.
  - lang: typescript
    kind: procedure
    note: >-
      Where a TypeScript project's floor lives, all readable from a read-only
      clone. Vitest carries `coverage.thresholds` in `vitest.config.*` or in
      the `test` block of `vite.config.*` - and it looks for the former first,
      so a project with no `vitest.config.*` keeps these keys in its Vite
      config and a search naming only the former reads a project that set a
      floor as one that set none. Jest carries `coverageThreshold`, in
      `jest.config.*` or in `package.json`'s `jest` key. `c8` is the third
      home, and the domain already treats it as one of this language's coverage
      tools: it reads `.c8rc`, `.c8rc.json`, `.nycrc` or `.nycrc.json`, walked
      up from the working directory, or a `c8` key in `package.json`, and its
      config keys are the long-form flags without the dashes - so the floor is
      `check-coverage` set beside `lines`, `branches`, `functions` or
      `statements`. It can be a command rather than a file too:
      `c8 --check-coverage --lines <n>` in a script, `c8 --100` for the
      all-metrics shorthand, or a separate `c8 check-coverage --lines <n>` step
      re-checking data an earlier step collected. Whether `c8` can measure that
      project truthfully is not this check's question - `test/coverage-reach`
      owns it, and forbids `c8` around a Vitest command outright - and a floor
      declared for a tool that measures the wrong thing is still a floor that
      was decided. What the floor is measured over is `coverage.include` and
      `coverage.exclude` for Vitest, `collectCoverageFrom` and
      `coveragePathIgnorePatterns` for Jest, and `include`, `exclude` and `src`
      for `c8`.
    alone_insufficient: >-
      Finding nothing here is not the finding, for the same reason as the
      Python route: the floor may live in a CI step, and absence is evidence
      only once every home has been read.
  - lang: any
    kind: procedure
    note: >-
      The homes that belong to no language. A workflow step that runs the
      coverage command with a threshold flag is an executable home, and so is a
      job that fails on the number, whatever the partition speaks. The
      changed-lines half of the decision lives here too: a `diff-cover` step
      carrying `--fail-under <n>`, or the equivalent threshold on whatever
      diff-coverage tool the project runs, is the declaration of a floor on
      changed lines. Read the workflow files directly rather than asking the
      API what is required - whether the job can block is
      `ci/gate-enforcement`'s question and not this one, and a floor written
      into a job nobody requires is still a floor that was decided.
    alone_insufficient: >-
      Finding nothing here is not the finding either. The floor may live in the
      partition's own coverage config, which the language routes read.
---

# Coverage floor declaration

Whether the project **decided** a unit-test coverage floor, what that floor is measured over, and whether both are recorded somewhere a machine enforces them. This is a declaration check in the shape of `arch/runtime-declaration`: it asks whether the decision was taken and written down, never whether the number is high enough.

What it prevents is a verdict the audit invented. This domain's own status scale reads `meets-floor / below-floor / untested`, and its scope step asks what floor the contributor guide or CI enforces - so every other part of the skill assumes a floor exists. A project that never decided one still gets `meets-floor` or `below-floor`, measured against a number the audit supplied on its behalf, and nobody reading the report can tell that from a real verdict.

## What counts as declared, what counts as executable, and what is a finding

**A floor is declared when a number exists and something reads it.** The homes are in the routes above, one per language plus the CI-side ones. The check reports on the project, so it reads all of them before concluding anything: a floor found in any one home is a floor.

**A floor recorded only in prose is a finding.** A number in a contributor guide, a README or a code-review checklist, with no `fail_under`, no runner threshold and no CI step carrying it, is the aspirational form the clause rejects outright - and it is the shape most likely to be mistaken for conformance, because the project did decide and can point at the sentence. The finding is the pair: the prose that states the number, and the executable homes that hold none.

**Exclusions are part of the decision.** A floor sitting beside an exclusion list that removes load-bearing deterministic logic from the denominator describes a different codebase than the one shipped, so the number is met by a project that tests less than the number claims. Whether a given exclusion is load-bearing is a judgment rather than a parse, so the finding is raised with the exclusion patterns and the modules they remove named in the row, leaving the reader the evidence to disagree with. An exclusion list that removes tests, generated files or vendored code is ordinary and is not this finding.

**The changed-lines floor is a second decision, and its absence is a second finding.** The clause asks for the whole-project floor to be paired with one on changed lines, so a project with `fail_under` and no diff-coverage threshold has taken half the decision. Report it separately rather than folding it into the first, because the fix is a different line in a different file.

## The three neighbours, and where each line falls

**`test/coverage-reach` measures reach, and reads the threshold as context for its own number.** That record's `evidence` says what a project excluded from measurement and the threshold it set for itself are part of what it asks - and they are, as the thing its measured number is read against. Two questions stay there and not here: whether the reported coverage is adequate, and whether the floor measures the right thing, which is that record's `fail_under`-without-`branch = true` finding. What is here is whether the decision exists at all and whether it has an executable home. A project with no floor is silent in that record and a finding in this one.

**`ci/gate-enforcement` owns whether an intended gate can actually block** - its own subject is whether the intended quality gates are run and *required*, and a workflow that is skippable, scheduled-only or absent from branch protection is a gate in name only. So a floor written into a job nobody requires is a `ci` finding and a pass here: the decision was taken and recorded executably, and what failed is the mechanism carrying it. Do not read branch protection to answer this check.

**`test/new-code-coverage` measures coverage on the diff.** The changed-lines floor is a declaration question here - was one decided - and a measurement question there. A project that declared a diff floor and does not meet it is that check's finding, not this one's.

## Severity

**Important** - no floor was decided anywhere, or a floor exists only in prose. This is the clause's own failure, and it is the state in which every other coverage verdict in the report is measured against a number nobody chose.

**Minor** - the whole-project floor was decided and the changed-lines one was not, or the floor is executable but its exclusions remove load-bearing deterministic logic from the denominator. The decision exists; it is incomplete, or it is measured over less than the project ships.

There is deliberately **no Critical tier**. The check asks whether a decision was recorded and never what the code's coverage is, so it has no untested scorer and no evaded gate to offer - those belong to `test/coverage-reach` and `ci/gate-enforcement`, which have them.

## Fix

Write the floor where a machine reads it: `fail_under` in the coverage config, a threshold in the runner's config, or a CI step that fails below the number. Move a prose floor into one of those and leave the prose as the explanation rather than as the record.

Decide the denominator with it - the source scope and the exclusion list - and write a justification beside a deliberately low floor, which the clause asks for and which is what separates a considered low number from an unconsidered one.

Add the changed-lines floor as its own threshold, since the whole-project number moves too slowly to catch a single weakly-tested change.

**The wrong close is lowering the floor until the tree meets it.** That satisfies every mechanical reading of this check - a number exists, something reads it, the suite passes - and it is the opposite of what the clause asks, which is that the project decide a bar and then meet it. A floor set beneath the coverage the tree already has is not a decision; it is a way of not making one.

## What this check does not do

**It does not rate the number.** The finding is never "the floor is too low". A project that decided 40% and wrote down why conforms; one that decided 95% without recording it executably does not.

**It does not measure coverage**, and it does not need the suite to run. Every route reads configuration and workflow files from a read-only clone, which is why none of them carries a grant tier: the decision is on disk whether or not the tests are.

## Review lens

**Declaration, not level** - does every row say whether a decision was recorded, and not whether the resulting number is good? A row whose evidence is a coverage percentage is this check answering `test/coverage-reach`'s question.

**Every home read** - does the row name the files that were checked and found to hold no floor, and not only the one that did? An absence reported without the search behind it cannot be checked, and is indistinguishable from a home nobody looked in.

**The floor was added, not lowered to fit** - was the number written to state a bar the project intends to meet, and does a low one carry the justification the clause asks for? A `fail_under` set just beneath current coverage closes the finding and decides nothing.
