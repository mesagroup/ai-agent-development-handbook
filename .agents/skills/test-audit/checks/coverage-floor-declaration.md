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
      executable at all. coverage.py searches `.coveragerc`,
      `.coveragerc.toml`, `setup.cfg`, `tox.ini` and `pyproject.toml` in that
      order, stops at the first that answers and ignores the rest - and what
      counts as answering differs between the two kinds of file, which is
      where this goes wrong. **A dedicated file wins by existing.** An empty
      or comment-only `.coveragerc` or `.coveragerc.toml` ends the search, so
      a `fail_under` anywhere later is never read: verified by running
      coverage.py against a tree holding an empty `.coveragerc` beside a
      `setup.cfg` carrying `fail_under = 90`, where the effective value stays
      at the default. **A shared file has to carry a coverage section.** A
      `setup.cfg` or `tox.ini` with no `[coverage:...]` in it is passed over
      and the search continues. So a floor in a later file is written where
      nothing reads it whenever an earlier *dedicated* file exists at all, or
      an earlier shared file carries a coverage section - a finding here
      rather than a floor, because nothing enforces it. The empty-file trap
      is the same one the pytest half names below, in a second tool. And
      `pyproject.toml` support needs Python 3.11 or the `toml` extra, so read
      the project's own floor against what it runs on. `--cov-fail-under=<n>` is the same decision written as a
      pytest flag, and it counts wherever it is durable, which is
      wider than a config file: pytest's `addopts`, a CI step, a `tox.ini`
      `[testenv]` command, a Nox or Hatch script, a Makefile target, a
      `package.json`-style script entry in whatever the project uses. What
      disqualifies an invocation is a person typing it, not the kind of file it
      sits in. Pytest's own
      config files are a second set with a second set of headings, overlapping
      the coverage ones without sharing their spelling: `pytest.toml` or
      `.pytest.toml` under `[pytest]`, which take precedence over the rest
      **even when empty** - so an empty one silences every floor carried in
      pytest's own configuration, `--cov-fail-under` in `addopts` above all,
      because it wins *pytest's* search and those files are then never read.
      It silences nothing of coverage.py's: that tool runs the separate search
      named above, over `.coveragerc`, `.coveragerc.toml`, `setup.cfg`,
      `tox.ini` and `pyproject.toml`, so a `fail_under` in one of those is
      still read and still fails the run. Report the empty file as a finding
      for the floor it actually hides, and not for one the other search still
      reaches - the two config searches belong to two tools and neither
      shadows the other; `pytest.ini` or
      `.pytest.ini` under `[pytest]`; `pyproject.toml` under
      `[tool.pytest.ini_options]`, or under `[tool.pytest]` **on pytest 9 and
      later only** - pytest 8 ignores that table silently, with no warning and
      no error, so a `--cov-fail-under` living only there is not executable on
      a project pinned below 9 and is this check's finding rather than its
      floor; verified by running both versions against a `[tool.pytest]`
      `addopts` naming an option that does not exist, which pytest 9 rejects
      and pytest 8 runs straight past. The two tables also take different
      value types, so read the pin before reading either: the native table
      takes real TOML and wants `addopts = ["--cov-fail-under=90"]`, while
      `ini_options` keeps the ini spelling, `addopts = "--cov-fail-under=90"`; `tox.ini` under `[pytest]`; and `setup.cfg`
      under `[tool:pytest]` - renamed from the bare `[pytest]` to stop it
      colliding with distutils commands, so the bare name is right in `tox.ini`
      and wrong in `setup.cfg`. Pytest also takes only the first matching file,
      so the precedence trap above has a second instance here. What the floor is measured over is set in
      both sections, and reading only the run one overstates the denominator.
      The run section contributes `source`, `source_pkgs`, `include` and
      `omit`. The report section contributes `exclude_lines` and
      `exclude_also` - the last supplements the default exclusions rather than
      replacing them, so a project using it has exclusions a reader watching
      only `exclude_lines` never sees - **and its own `include` and `omit`**,
      which are separate settings from the run section's and are the ones that
      matter most here: `fail_under` is itself a report setting, computed over
      the files the report covers, so a `[report] omit` dropping load-bearing
      modules lowers the denominator the floor is compared against while the
      run configuration still names them. `.coveragerc.toml` takes the bare `[run]` and
      `[report]` headings, the same as `.coveragerc`, and also accepts the
      `[tool.coverage.*]` form; it is a recent addition, so check the coverage
      version the project pins before reading a floor there as one anything
      enforces.
      **Finding nothing here is not the finding**: the floor may live in a CI
      step instead, which the `lang: any` route reads, so absence is evidence
      only once every home has been read.
    alone_insufficient: >-
      A floor found here is a clean result that does not by itself answer the
      check, and the two things still to read produce different findings.
      **Which file the tool would actually open** decides whether a floor was
      declared at all: a `fail_under` in a file coverage.py never reads,
      because an earlier one in the search order held valid settings, is the
      absence finding however plainly the number is written. **What the number
      is measured over** does not: a denominator that drops load-bearing code
      is the exclusion finding in this record's severity scale, where the
      decision exists and is incomplete, so do not report it as no floor
      having been decided.
  - lang: typescript
    kind: procedure
    note: >-
      Where a TypeScript project's floor lives, all readable from a read-only
      clone. Vitest carries its floor at `test.coverage.thresholds`, under the
      `test` block in **both** `vitest.config.*` and `vite.config.*`: every
      Vitest option lives under `test`, a standalone `vitest.config.*`
      included, so the two files differ in which one is read and never in
      where the key sits. Vitest looks for the former first.
      That cuts both ways, and the rule is the one the Python route states:
      a number in a file the tool will not open is the absence finding rather
      than a floor. A project with no `vitest.config.*` keeps these keys in
      its Vite config, so a search naming only the former reads a project
      that set a floor as one that set none. A project carrying both is the
      opposite trap: Vitest resolves `vitest.config.*` first and its own
      documentation says the Vite config's options are then **ignored**
      entirely, so a threshold left behind in `vite.config.*` is written
      where nothing reads it. **Read the vitest config for a merge before
      raising that one** - `mergeConfig(viteConfig, defineConfig({...}))` is
      the documented way to keep both, and a project using it does have the
      Vite config's thresholds read, so the finding is false there. Jest
      carries `coverageThreshold` in `jest.config.*` or in `package.json`'s
      `jest` key, and it resolves the two by refusing rather than by
      preferring. With exactly one of them present, that one is read. With
      **both** present and no `--config` on the invocation, Jest does not
      pick a winner and does not run: it exits with *"Multiple configurations
      found ... Implicit config resolution does not allow multiple
      configuration files"* and asks for one to be named. So the both-present
      case is not a silent-precedence trap and must not be read as one - the
      threshold is not unread, the test run does not happen. What decides it
      there is the invocation: where the project's own test command passes
      `--config <path>`, that file is the floor's only home and a
      `coverageThreshold` in the other is written where nothing reads it,
      which is this check's finding. Where it does not, the project cannot
      run Jest implicitly at all, and a floor is moot until that is fixed -
      report the configuration collision as the finding and do not score the
      threshold either way. `c8` is the third
      home, and the domain already treats it as one of this language's coverage
      tools: it reads `.c8rc`, `.c8rc.json`, `.nycrc` or `.nycrc.json`, walked
      up from the working directory, or a `c8` key in `package.json`, and its
      config keys are the long-form flags without the dashes - so the floor is
      `check-coverage` set beside `lines`, `branches`, `functions` or
      `statements` - **and `check-coverage` on its own is already a floor**,
      because the metric flags carry defaults, so a config or a
      `c8 --check-coverage` script naming no number still fails a build under
      one. Reading the keys rather than the switch is how a declared floor gets
      reported as none. It can be a command rather than a file too:
      `c8 --check-coverage --lines <n>` in a script, `c8 --100` for the
      all-metrics shorthand, or a separate `c8 check-coverage --lines <n>` step
      re-checking data an earlier step collected. Whether `c8` can measure that
      project truthfully is not this check's question - `test/coverage-reach`
      owns it - and a floor
      declared for a tool that measures the wrong thing is still a floor that
      was decided. What the floor is measured over is `coverage.include` and
      `coverage.exclude` for Vitest, `collectCoverageFrom` and
      `coveragePathIgnorePatterns` for Jest, and `include`, `exclude` and `src`
      for `c8`.
      **Finding nothing here is not the finding**, for the same reason as the
      Python route: the floor may live in a CI step, and absence is evidence
      only once every home has been read.
    alone_insufficient: >-
      A threshold found here is a clean result that does not by itself answer
      the check: a `test.coverage.thresholds` or `coverageThreshold` block
      can carry a number while `test.coverage.include`,
      `test.coverage.exclude`, `collectCoverageFrom` or
      `coveragePathIgnorePatterns` remove the code it
      was meant to cover, and a `c8` config can set `check-coverage` over a
      `src` that is not the source tree. Read the denominator - and record what
      it holds as the exclusion finding, which this record's severity scale
      puts at Minor with the decision made and incomplete, rather than as the
      floor not having been declared.
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
      **Finding nothing here is not the finding** either: the floor may live in
      the partition's own coverage config, which the language routes read.
    alone_insufficient: >-
      A threshold flag found in a workflow or a task runner is a clean result
      that does not by itself answer the check, because the two decisions this
      record keeps apart are spelled the same way here. A `--fail-under` on a
      diff-coverage command is the **changed-lines** floor and says nothing
      about the whole-project one; reading it as either is how one decision
      gets reported as two made or two as one. Read which command the flag
      belongs to before recording what was declared. Whether the step is one
      anything actually runs is deliberately not asked: that is enforcement,
      it is `ci/gate-enforcement`'s, and this check is answered for the
      project rather than for a change, so a path filter has no diff here to
      be judged against.
---

# Coverage floor declaration

Whether the project **decided** a unit-test coverage floor, what that floor is measured over, and whether both are recorded somewhere a machine enforces them. This is a declaration check: it asks whether the decision was taken and written down, never whether the number is high enough.

What it prevents is a verdict the audit invented. This domain's own status scale reads `meets-floor / below-floor / untested`, and its scope step asks what floor the contributor guide or CI enforces - so every other part of the skill assumes a floor exists. A project that never decided one still gets `meets-floor` or `below-floor`, measured against a number the audit supplied on its behalf, and nobody reading the report can tell that from a real verdict.

## What counts as declared, what counts as executable, and what is a finding

**A floor is declared when a bar exists in a place that is durable and machine-read.** Durable means it survives the person who typed it - a file in the repository, or a command in something the project runs the same way every time. Machine-read means a tool actually consults it and fails on it. Those two together are the test, and every home named in the routes below is an instance of it rather than the definition.

**The bar is usually a number and does not have to be one.** A switch that turns a tool's documented defaults into a threshold declares a floor as surely as a percentage does - `c8 --check-coverage` names no figure and still fails a build, because its metric flags carry defaults, which is what the TypeScript route below says in its own words. What the rule asks is that something the project recorded makes a run fail below some level, not that a digit appears in the file. Reading for the digit is how an enforced floor gets reported as never decided, and that is the one direction this check must not be wrong in.

**Treat the routes' lists as the common homes, never as the whole set.** They name where a floor usually lives and the traps in reading those places; they cannot be exhaustive, because a project declares its floor wherever its own toolchain reads one, and a check that concludes from a fixed list reports the absence of the list rather than the absence of a floor. So when nothing on the lists holds a bar, find the command the project's tests actually run under - the CI job, the task runner's entry, the script in the manifest - and read that before concluding anything, because a threshold flag there is a floor by the rule above however unfamiliar the file carrying it. The routes read all of them before the check concludes: a floor found in any one home is a floor.

**A floor recorded only in prose is a finding.** A number in a contributor guide, a README or a code-review checklist, with no `fail_under`, no runner threshold and no CI step carrying it, is the aspirational form the clause rejects outright - and it is the shape most likely to be mistaken for conformance, because the project did decide and can point at the sentence. The finding is the pair: the prose that states the number, and the executable homes that hold none.

**Exclusions are part of the decision.** A floor sitting beside an exclusion list that removes load-bearing deterministic logic from the denominator describes a different codebase than the one shipped, so the number is met by a project that tests less than the number claims. Whether a given exclusion is load-bearing is a judgment rather than a parse, so the finding is raised with the exclusion patterns and the modules they remove named in the row, leaving the reader the evidence to disagree with. An exclusion list that removes tests, generated files or vendored code is ordinary and is not this finding.

**The changed-lines floor is a second decision, and its absence is a second finding.** The clause asks for the whole-project floor to be paired with one on changed lines, so a project with `fail_under` and no diff-coverage threshold has taken half the decision. Report it separately rather than folding it into the first, because the fix is a different line in a different file.

## The three neighbours, and where each line falls

**`test/coverage-reach` measures reach, and reads the threshold as context for its own number.** What a project excluded from measurement and the threshold it set for itself are context for that measured number. Two questions stay there and not here: whether the reported coverage is adequate, and whether the floor measures the right thing. What is here is whether the decision exists at all and whether it has an executable home.

**`ci/gate-enforcement` owns whether an intended gate can actually block** - its own subject is whether the intended quality gates are run and *required*, and a workflow that is skippable, scheduled-only or absent from branch protection is a gate in name only. So a floor written into a job nobody requires is a `ci` finding and a pass here: the decision was taken and recorded executably, and what failed is the mechanism carrying it. Do not read branch protection to answer this check.

**`test/new-code-coverage` measures coverage on the diff.** The changed-lines floor is a declaration question here - was one decided - and a measurement question there. A project that declared a diff floor and does not meet it is that check's finding, not this one's.

## Severity

**Important** - no floor was decided anywhere, or a floor exists only in prose. This is the clause's own failure, and it is the state in which every other coverage verdict in the report is measured against a number nobody chose.

**Minor** - the whole-project floor was decided and the changed-lines one was not, or the floor is executable but its exclusions remove load-bearing deterministic logic from the denominator. The decision exists; it is incomplete, or it is measured over less than the project ships.

There is deliberately **no Critical tier**. The check asks whether a decision was recorded and never what the code's coverage is, so it has no untested scorer and no evaded gate to offer - those belong to `test/coverage-reach` and `ci/gate-enforcement`.

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
