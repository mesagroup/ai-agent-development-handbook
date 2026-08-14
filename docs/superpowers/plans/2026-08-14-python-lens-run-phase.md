# Python lens run phase implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run every `python:` tooling entry in the audit skill family against the five seeded fixture partitions under both grant states, correct each record against what was observed, and publish the dated verification record.

**Architecture:** The instrument already exists. PR 1 built the definition module, the generator and the harness that holds each record's prescribed invocation verbatim. This phase adds two committed units - version capture in the harness, so the evidence names the tools it came from, and a grader that pairs each written-down expectation with the observation the run produced - then runs, grades, corrects and records. Corrections land one record per commit, each quoting the output that forced it.

**Tech Stack:** Python 3.12, `uv`, pytest, ruff. The tools under test are fetched by `uvx` or run from the materialized environment, per partition.

## Global Constraints

- **PR 2 `Closes #45`**, branched from `main` after PR 1 merged. Not stacked on PR 1's branch.
- **No correction without observed output.** A record change whose justification is reasoning rather than a transcript is the failure this round exists to remove. Quote the output in the commit body.
- **The harness is the instrument.** Do not run a tool by hand and treat the result as evidence. A command that has to change to work is a finding, and it is visible as a diff against the transcribed command - running it by hand is how that finding gets lost.
- **Read-only discipline.** `git status --porcelain` empty at the fixture before and after every run. Materialize in a copy that does not resolve under the fixture root. A package a check needs for itself never goes into the shared materialized tree.
- **Grant states are two:** `none` and `target-execution`. Every entry runs under both.
- **Evidence is gitignored.** `fixtures/python/results/` exists only on the machine that ran it. Anything the verification record relies on must be quoted in the record itself.
- **A commit touching a check record is a prompt change:** it says WHY, and it does not share a commit with code.
- No em-dash (U+2014) in `docs/engineering/`, `docs/superpowers/specs/`, `docs/superpowers/plans/`. Use ` - `.
- Markdown is never hard-wrapped; one paragraph is one source line. Never reflow a line you did not change.
- Never commit an environment-specific value. The results JSON carries an absolute `source` path; the record quotes output, never that field.
- Never assert a count you did not compute.
- New code ships with unit tests. Scripts are loaded in tests with `importlib.util.spec_from_file_location`.
- `safety` is the one planned non-execution, recorded with its authentication reason.

---

## File structure

| File | Responsibility |
|---|---|
| `scripts/run_python_fixture_lens.py` | Modified: records the version of every tool it invokes |
| `scripts/grade_python_fixture_run.py` | New: pairs each expectation with its observation and computes what is mechanical |
| `tests/scripts/test_python_fixture_harness.py` | Modified: guards the version probe table against the invocation table |
| `tests/scripts/test_python_fixture_grader.py` | New: the grader's pure helpers, against synthetic runs |
| `docs/audit/python-lens-smoke-run.md` | New: the dated verification record |
| `docs/audit/README.md` | Modified: a verification-records row for it |
| `.agents/skills/<domain>-audit/checks/*.md` | Modified: the corrections, one record per commit |

---

## Task 1: Record the version of every tool the harness invokes

A dated verification record whose tools are unversioned goes stale in silence, which is the exact failure `docs/audit/README.md`'s standing-versus-verification split exists to make visible. `uvx` resolves the latest release at run time, so nothing in the current results file says what actually ran. This lands before the run, because a version captured afterwards is a version of whatever is current then.

**Files:**
- Modify: `scripts/run_python_fixture_lens.py`
- Test: `tests/scripts/test_python_fixture_harness.py`

**Interfaces:**
- Consumes: `INVOCATIONS`, `launcher`, `_run`, `_fixture_env` from the harness.
- Produces: `VERSION_PROBE: dict[str, tuple[str, ...] | None]`, `probe_versions(partition, grant, work_dir, timeout) -> dict[str, str]`, and a `versions` key in the results JSON.

- [ ] **Step 1: Write the failing guard test**

The table must name every tool the harness can invoke, and no others. This mirrors the existing exact-set guard, so a tool added to a record and forgotten here fails the suite rather than running unversioned.

```python
def test_every_invoked_tool_has_a_version_route_or_a_stated_absence(harness):
    invoked = {inv.tool for inv in harness.INVOCATIONS}
    assert set(harness.VERSION_PROBE) == invoked

def test_a_tool_with_no_version_route_says_so_by_name(harness):
    for tool, argv in harness.VERSION_PROBE.items():
        if argv is None:
            assert tool in harness.NO_VERSION_ROUTE, (
                f"{tool} has no version probe and no stated reason"
            )
            assert harness.NO_VERSION_ROUTE[tool].strip()
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `uv run pytest tests/scripts/test_python_fixture_harness.py -k version -v`
Expected: FAIL with `AttributeError: module has no attribute 'VERSION_PROBE'`

- [ ] **Step 3: Add the table**

`None` is a positive claim that the tool offers no version route, and it is rejected unless `NO_VERSION_ROUTE` explains it - the same shape as `ungranted_note`'s `none` sentinel, and for the same reason: an omitted entry must never read as a silent default.

```python
VERSION_PROBE: dict[str, tuple[str, ...] | None] = {
    # every tool in INVOCATIONS; ("--version",) for the ordinary case
}

NO_VERSION_ROUTE: dict[str, str] = {
    # tool -> why it cannot report a version, for the ones mapped to None
}
```

- [ ] **Step 4: Implement `probe_versions`**

It runs each probe through the same `launcher` the invocation uses, so a `uvx`-fetched tool reports the version `uvx` actually resolved rather than one a differently-fetched copy would.

```python
def probe_versions(
    partition: str, grant: str, work_dir: Path, timeout: int
) -> dict[str, str]:
    """Report the version of every tool this partition will invoke.

    Runs through the same launcher as the invocation, because a `uvx`-fetched
    tool and a tool on `PATH` are different copies and may differ in version.
    A probe that fails is recorded as its failure text rather than dropped: an
    absent version is a fact about the run, and a missing key would read as a
    tool that was never invoked.
    """
```

- [ ] **Step 5: Write it into the results JSON**

Add a top-level `versions` key beside `grant`, `materialization`, `partition`, `results` and `source`.

- [ ] **Step 6: Run the harness tests**

Run: `uv run pytest tests/scripts/test_python_fixture_harness.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git status --short
git commit -m "feat: record the version of every tool the run invokes

Refs #45" -- scripts/run_python_fixture_lens.py tests/scripts/test_python_fixture_harness.py
```

Paths go on the commit, not only on `git add`: a bare commit commits the whole index, and an agent staging in the gap lands in it.

---

## Task 2: The grader

The harness classifies a result into the engine's status vocabulary, which is triage - it says a tool ran and produced something, not that it produced the truth. The grade is whether the observation matches the expectation written down before the run.

**That grade cannot be fully mechanical, and the grader must not pretend otherwise.** `Expectation.claim` is prose written for a reader; `Expectation.seeds` names the planted constructs. So the grader computes every mechanical signal and pairs it with the claim, leaving the judgement explicit rather than inferring a verdict from a substring match and reporting a confidence it does not have. A grader that guessed would manufacture exactly the false clean this round exists to catch.

**Files:**
- Create: `scripts/grade_python_fixture_run.py`
- Test: `tests/scripts/test_python_fixture_grader.py`

**Interfaces:**
- Consumes: `expectations_for`, `SEED_MARKERS`, `ABSENCE_SEEDS`, `PARTITIONS`, `FORMS` from `scripts/python_fixture_spec.py`; the results JSON written by the harness.
- Produces: `load_run(path) -> Run`, `observations_for(run, check) -> list[dict]`, `seed_signals(entry, seeds) -> dict[str, int]`, `grade_row(expectation, run) -> Row`, `render(rows) -> str`, `main(argv) -> int`.

- [ ] **Step 1: Write the failing test for the mechanical signal**

```python
def test_a_seed_marker_absent_from_the_findings_stream_counts_zero(grader):
    entry = {"stdout": "no issues found", "stderr": "", "ran": True}
    assert grader.seed_signals(entry, ("eval(",)) == {"eval(": 0}


def test_a_seed_marker_is_counted_in_the_stream_the_entry_names(grader):
    entry = {"stdout": "", "stderr": "DEP002 markupsafe", "ran": True,
             "findings_stream": "stderr"}
    assert grader.seed_signals(entry, ("markupsafe",)) == {"markupsafe": 1}
```

The second test is the one that matters. deptry writes its entire report to stderr, so a grader reading `stdout` alone scores a tool that found everything as having found nothing.

- [ ] **Step 2: Run it to confirm it fails**

Run: `uv run pytest tests/scripts/test_python_fixture_grader.py -v`
Expected: FAIL with `ModuleNotFoundError` / no such file

- [ ] **Step 3: Implement `seed_signals`**

```python
def seed_signals(entry: dict[str, object], seeds: Sequence[str]) -> dict[str, int]:
    """Count each seed marker in the stream this entry reports findings on.

    The stream matters: a tool that writes its report to stderr scores zero on
    stdout, which is indistinguishable from a tool that ran and found nothing.
    """
    stream = str(entry.get(str(entry.get("findings_stream", "stdout")), ""))
    return {seed: stream.count(seed) for seed in seeds}
```

- [ ] **Step 4: Write the failing test for a row**

A row is one expectation against one run. It carries what is mechanical and states the verdict as unjudged.

```python
def test_a_row_pairs_the_claim_with_the_observation_and_leaves_the_verdict_open(grader, spec):
    run = {"partition": "uv", "grant": "none", "versions": {}, "results": [
        {"check": "security/dangerous-calls", "tool": "bandit", "ran": True,
         "status": "ok", "stdout": "B307 eval(", "stderr": ""}]}
    rows = [r for r in grader.grade_rows(run) if r.check == "security/dangerous-calls"]
    assert rows
    assert rows[0].verdict == "unjudged"
    assert rows[0].signals
```

- [ ] **Step 5: Run it, then implement `grade_rows` and `render`**

Run: `uv run pytest tests/scripts/test_python_fixture_grader.py -v`
Expected: FAIL, then PASS after implementing.

`render` emits a Markdown worksheet, one row per expectation per partition per grant: check, tool, form, claim, status and reason, per-seed counts, and an empty verdict cell. It is a working document, written under the gitignored results directory - not a committed record.

- [ ] **Step 6: Add a CLI**

`main(argv)` takes the results directory and writes the worksheet. `--check` is deliberately absent: this output is evidence about one dated run, not a generated view of the tree, so there is nothing for a gate to compare it against.

- [ ] **Step 7: Full suite and lint**

Run: `uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check .`
Expected: PASS, clean

- [ ] **Step 8: Commit**

```bash
git status --short
git commit -m "feat: grade a fixture run against the expectations written before it

Refs #45" -- scripts/grade_python_fixture_run.py tests/scripts/test_python_fixture_grader.py
```

---

## Task 3: Execute the ten runs

Five partitions, two grant states. This produces evidence, not code.

**Files:** none committed. Output goes to `fixtures/python/results/`, which is gitignored.

- [ ] **Step 1: Start the host-awake guard**

The full matrix is long: mutation runs take minutes each and every entry needs network. An inline `caffeinate` covers only the command it wraps, so a standalone guard covers the gaps between calls.

```bash
caffeinate -i -t 21600 > /dev/null 2>&1 &
```

Record the PID and kill it when the run finishes.

- [ ] **Step 2: Rebuild the fixtures from this branch**

```bash
caffeinate uv run python scripts/build_python_fixtures.py --all
```

The trees on disk were built by PR 1's smoke. Rebuilding makes their provenance this branch's merged main, so the record can say what produced them without qualification.

- [ ] **Step 3: Confirm every fixture is a clean git repository**

```bash
for p in uv pip poetry pipenv pylock; do
  echo "$p: [$(git -C fixtures/python/$p status --porcelain)]"
done
```

Expected: every bracket empty. A dirty fixture before the run means the read-only check cannot say anything afterwards.

- [ ] **Step 4: Run the matrix, one partition and grant at a time**

```bash
caffeinate uv run python scripts/run_python_fixture_lens.py <partition> --grant <none|target-execution>
```

Ten invocations. Run them sequentially rather than in parallel: they share a network and a uv cache, and a partition that fails is easier to read alone.

- [ ] **Step 5: Re-confirm the fixtures are clean**

Same loop as step 3. Any partition that is now dirty is a read-only violation and is a finding in its own right - record what changed before doing anything about it.

- [ ] **Step 6: Record what the run cost and what refused to run**

Note the wall-clock per partition and every entry whose status is `no-evidence`, with its reason. `mutmut` on the uv partition is predicted to fail its baseline, because PR 1 established that the order-dependence seed's module-level state accumulates across the single-process re-run. Record it; do not loop on it.

---

## Task 4: Grade and triage, without correcting anything

Separating the grade from the correction is what stops a surprising observation being written up as whatever the reader expected to see.

- [ ] **Step 1: Produce the worksheet**

```bash
uv run python scripts/grade_python_fixture_run.py fixtures/python/results
```

- [ ] **Step 2: Fill every verdict cell**

One of: `met`, `missed`, `partial`, or `no-evidence` with its reason.

- [ ] **Step 3: Classify every mismatch by what is actually wrong**

Five kinds, and the distinction decides who gets edited:

- **The record is wrong** - it prescribes a command that does not work, or claims an exclusion that does not hold. The record gets corrected.
- **The tool is defective** - it runs, exits zero and reports less than the truth. The record gets a stated limit; the tool is not fixed here.
- **The expectation is wrong** - the fixture does not contain what the module claimed. `scripts/python_fixture_spec.py` gets corrected and re-rendered, and this is a defect in PR 1 that PR 2 fixes.
- **The host is at fault** - it fails here for a reason unrelated to the record. Recorded as a host fact and explicitly not a correction.
- **The instrument is wrong** - the harness, not the record, is what failed: a materialization route naming a binary the generator never assumed exists, a launcher resolving a tool from a directory nothing installed it into, a classifier reading a tool's designed exit code as a failure. The harness gets fixed and every affected run is re-run. **Nothing observed through a broken instrument is evidence**, so no correction may cite it, and a partition whose materialization failed measured nothing at all rather than measuring absence.

- **The check is not command-shaped** - its route is a script, a library call or a prose grep-and-read pass, and it has no CLI form for a command-running harness to invoke. Nothing is broken: not the record, not the tool, not the harness. It is a fact about the check, and the round reports it as a limit on what execution can verify rather than as a defect in anything. Without this kind, every such row files as `instrument-wrong` and the verification record publishes phantom harness defects.

**A step is sound only if `tool_present` is true AND `returncode` is zero.** A `FileNotFoundError` records `returncode: null`, so a filter written as `returncode not in (0, None)` counts a materialization that never ran as clean - which is the same false-clean shape this round exists to catch, turned on the harness's own output.

- [ ] **Step 4: Write the triage table into the scratchpad and check it against the expectations record**

Every one of the 31 expectations appears exactly once. An expectation with no row is one nobody looked at.

---

## Task 5: Correct the records

One record per commit, each quoting the output that forced it. A check record is a prompt, so the commit body says why the old text was wrong, not only what replaced it.

- [ ] **Step 1: For each record needing correction, edit it and its matrix edge together**

A matrix row's `checks:` entry and a record's `handbook:` entry are two directions of one edge. Change one, change the other, or the gate fails.

- [ ] **Step 2: Re-render and gate after each**

```bash
uv run python scripts/render_handbook_traceability.py --check
uv run python scripts/render_python_fixture_expectations.py --check
uv run pytest tests/ -q
```

- [ ] **Step 3: Commit each on its own**

```bash
git status --short
git commit -m "prompt: <what the record now says>

<the observed output, and why the previous text was wrong>

Refs #45" -- .agents/skills/<domain>-audit/checks/<slug>.md docs/audit/handbook-traceability.yaml
```

- [ ] **Step 4: Check the sweep obligations ledger**

Required only if `audit-core/SKILL.md` or `audit/SKILL.md` changed. `docs/audit/sweep-obligations.md` is hand-maintained and its test cannot judge whether a disposition is still true, so this is a reading pass.

---

## Task 6: Settle the three named holes

Each is a candidate the spec stated as a question. Each is answered with output or recorded as still open.

- [ ] **Step 1: `deps/inventory` has no uv route**

Candidate: `uv export --format cyclonedx1.5 --frozen`. The question is not whether it emits something but whether what it emits satisfies what the record asks an SBOM for. PR 1 already found that no route populates licences on any partition, and that `cyclonedx-py requirements` pointed at a `pylock.toml` emits a schema-invalid document rather than refusing - so validate the output against the CycloneDX schema rather than reading it for plausibility.

- [ ] **Step 2: `deps/vulnerabilities` writes off uv targets**

Candidate: `uv export --frozen --format requirements.txt` into `pip-audit -r`.

Two facts are already established and must be carried into the record with their limits rather than flattened:

- **`pip-audit -r` provisions a virtualenv and dies on this host** - `ensurepip` aborts with SIGABRT, under both CPython 3.12 and 3.13, with and without `--no-deps`. That is a host fact, not a record fact, and must not be written up as a `deps/vulnerabilities` finding.
- **`--no-deps --disable-pip` avoids the virtualenv and reports advisories.** Both flags are documented for this use: `--no-deps` "requires all requirements are pinned to an exact version", and `--disable-pip` "can only be used with hashed requirements files or if the `--no-deps` flag has been provided".

**The route's soundness depends on the shape of the file, and the record must say so.** `uv export --frozen` emits the full resolved set - measured at 7 entries on the uv fixture, including the transitives `markupsafe` and `pyparsing` - so skipping resolution loses nothing. The pip partition's committed `requirements.txt` declares 4 directs and no transitives, so the same flags there audit a strict subset and a transitive advisory is invisible. A record that says "use `--no-deps`" without naming which file shape it is sound for converts a complete answer into a silent partial one.

Also confirm how the export's editable `-e .` line is handled: it is the target itself, not a dependency, and `--skip-editable` exists. Whatever is needed goes through the harness's supplied-route provenance, never silently in place of the transcribed command.

- [ ] **Step 3: The pylock partition's own routes**

Establish the generation route and the install route, and read the uv and poetry results against it as the control - it is the one format `--locked` does read.

- [ ] **Step 4: Commit each resolution as its own prompt change**

---

## Task 7: The verification record

**Files:**
- Create: `docs/audit/python-lens-smoke-run.md`
- Modify: `docs/audit/README.md`

- [ ] **Step 1: Write the record, modelled on `docs/audit/typescript-lens-smoke-run.md`**

It carries: the date, every tool with the version the run captured, one row per entry per grant state with what was observed, the corrections it produced and the fixture that produced each, the defects found in tools that ran and produced nothing usable, `safety`'s non-execution with its authentication reason, and every seeded finding no tool reached.

**Quote the evidence.** `fixtures/python/results/` is gitignored and exists on one machine; a record that cites it cites nothing a reader can open. Quote output, never the results file's absolute `source` path.

**It is a client-facing record of current behaviour.** State what each tool does now and its limits. It does not narrate the debugging, and it does not say a record "used to" claim something - the superseded text is in this PR's diff and in the issue, which is where that history belongs.

- [ ] **Step 2: Add the README row**

Under **Verification records**, not standing records: it is a dated finding about tool behaviour that a tool version can invalidate without any gate failing.

- [ ] **Step 3: Commit**

---

## Task 8: Finish the branch

- [ ] **Step 1: Stale-prose pass, scoped by blast radius**

Not scoped to the diff. Every record whose text changed: grep the tool's name across `.agents/skills/` and read every neighbouring claim, because a route corrected in one record is frequently asserted in another. Dispatch it to a reader that has not seen the corrections.

- [ ] **Step 2: Full local gate**

```bash
caffeinate uv run pytest tests/ -q
caffeinate uv run ruff check . && caffeinate uv run ruff format --check .
caffeinate uv run python scripts/render_handbook_traceability.py --check
caffeinate uv run python scripts/render_python_fixture_expectations.py --check
```

- [ ] **Step 3: Kill the caffeinate guard**

- [ ] **Step 4: Open the PR**

`Closes #45`. Body states the corrections made, the holes settled and any left open, and the seeds no tool reached. Mark it ready as soon as the diff is the diff to review - the security reviewer does not run on a draft.

- [ ] **Step 5: Tick the issue's acceptance criteria, only where verified**

- [ ] **Step 6: Read the automation before handing back**

Push, then wait out and read the full cycle: `check`, `Cursor Bugbot`, `Cursor Security Agent: Security Reviewer`. Confirm the check set matches a recently merged PR by name rather than confirming nothing failed.

---

## Self-review

**Spec coverage.** Every criterion in the design's mapping table has a task: execution and both grant states (Task 3), the three holes (Task 6), every seeded finding found or its absence recorded (Tasks 4 and 7), corrections traceable to output naming the fixture (Task 5), README and the conditional ledger check (Tasks 7 and 5). `safety`'s non-execution is carried in Task 7's record contents.

**Where this plan cannot be specified further, and why that is not a placeholder.** Tasks 4 through 6 name the procedure, the classification and the evidence standard, but not the per-record edits. The design says this outright: the per-entry work cannot be written before the observations exist without inventing them. Naming a correction here would be the unverified claim the round exists to eliminate.

**Type consistency.** `seed_signals`, `grade_rows`, `render` and `main` are used in Task 2 under the names its interface block declares. `VERSION_PROBE`, `NO_VERSION_ROUTE` and `probe_versions` likewise in Task 1.

**One known risk carried from PR 1.** `mutmut` cannot reach a green baseline on the uv partition, so `test/mutation-coverage` is expected to return `no-evidence` rather than a grade. It is predicted rather than discovered, and Task 3 says not to loop on it.
