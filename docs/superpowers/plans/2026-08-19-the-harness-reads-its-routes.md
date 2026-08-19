# The Python fixture harness reads its routes from the records - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A migrated check's prescription is read from its `routes`, so it is written once in the tree rather than transcribed into a Python table beside the record.

**Architecture:** `invocations_for(partition)` stays the single enumeration point every consumer reads. Its result becomes the union of two sources: the hand-written `INVOCATIONS`, cut down to the 31 entries for checks whose fallback still lives in prose, and `routed_invocations()`, which builds the same `Invocation` row type from a migrated record's `lang: python` routes. `Invocation` stays the runtime row so no consumer downstream of the enumeration changes. A four-entry `COMPLETIONS` overlay carries what the round supplied and the record could not say.

**Tech Stack:** Python 3.12, `uv`, pytest, ruff. `scripts/audit_checks.py` for the record loader, `scripts/run_python_fixture_lens.py` for the harness, `tests/scripts/test_python_fixture_harness.py` for its properties.

**Spec:** `docs/superpowers/specs/2026-08-19-the-harness-reads-its-routes-design.md`. Issue #63. Stage 3 of epic #58.

## Global Constraints

- Route selection is `lang: python` only. Nothing selects `lang: any` or `lang: none`. Widening it is #44's territory and changes the set of checks the round runs.
- What the harness runs must not move. Only where it reads it from. The transitional equality in Task 1 is the evidence, and it is deleted in Task 2 rather than kept, because frozen into the suite it would be the second copy this stage removes.
- `completion`, `supplied_by_partition` and `supplied_note` are round-owned and never move into a record.
- `NONZERO_EXIT_MEANING`, `VERSION_PROBE` and `TOOL_PACKAGES` stay engine-owned and keyed by tool.
- `record_quote` goes for migrated checks and stays for the 31 prose entries, because it is still the only thing holding those transcriptions to their records.
- No bare `except Exception: pass`. Every exception reaches the caller with type and message.
- Never assert a count in prose or a docstring that the same change does not compute.
- `PYTHONDONTWRITEBYTECODE=1` on any mutate-run-revert cycle against `scripts/run_python_fixture_lens.py`.
- Markdown is never hard-wrapped: one paragraph is one source line. Never reflow a line you did not change.
- No em-dash in `docs/superpowers/plans/` or `docs/superpowers/specs/`. Use ` - `.

---

## File Structure

- Modify `scripts/run_python_fixture_lens.py`: add `Completion`, `COMPLETIONS` and `routed_invocations()`; give `record_quote` a default; cut lines 641 to 887, the arch block of `INVOCATIONS`; union the two sources in `invocations_for`.
- Modify `tests/scripts/test_python_fixture_harness.py`: add the enumeration's own properties; restate the three-way check-set property as a union; add the no-entry-for-a-migrated-check property; delete the two oracle tests and the transitional equality; re-derive the engine-table properties from the routes; delete any prose helper nothing reaches.
- No change to `scripts/audit_checks.py`, `scripts/python_fixture_spec.py`, any check record, or any generated document. A diff touching a check record in this plan is a mistake: the records are the source and this plan only changes who reads them.

---

### Task 1: The enumeration, and the quote becomes the prose population's field

**Files:**
- Modify: `scripts/run_python_fixture_lens.py`
- Test: `tests/scripts/test_python_fixture_harness.py`

**Interfaces:**
- Consumes: `Check.routes` from `scripts/audit_checks.py`, where each route carries `lang`, `kind`, `tool`, `argv`, `disposition`, `findings_stream`, `in_env`.
- Produces: `Completion`, `COMPLETIONS`, `routed_invocations() -> tuple[Invocation, ...]`, and `Invocation.record_quote` defaulting to `""`. Task 2 unions the result into `invocations_for`.

The quote's default belongs in this task and not a later one: `routed_invocations` cannot construct a row without it, and a task that ends with a red suite is not an independently reviewable deliverable.

- [ ] **Step 1: Write the failing test for the grouping rule**

Add to `tests/scripts/test_python_fixture_harness.py`, importing `routed_invocations` and `COMPLETIONS` from the lens alongside the existing imports:

```python
def test_a_routed_row_is_one_per_check_and_tool_rather_than_one_per_route():
    """`arch/cycles` declares four python routes and has three rows.

    Its `superseded` `pydeps --show-cycles` is a second form of the same tool,
    not a second row. A rule keyed on routes would run a form the record
    narrows against as though it prescribed it.
    """
    rows = {(r.check, r.tool) for r in routed_invocations()}
    cycles = sorted(t for c, t in rows if c == "arch/cycles")
    assert cycles == ["grimp", "import-linter", "pydeps"]
    pydeps = next(
        r for r in routed_invocations()
        if r.check == "arch/cycles" and r.tool == "pydeps"
    )
    assert pydeps.argv == ("pydeps", "--show-cycles", "--show-dot")
    assert set(pydeps.forms) == {
        ("pydeps --show-cycles --show-dot", "runs"),
        ("pydeps --show-cycles", "superseded"),
    }


def test_a_route_that_is_not_a_command_still_produces_a_row():
    """`arch/complexity-gate`'s three `subject` routes are three rows.

    The engine grades a row prescribing no command as exactly that, so
    dropping these would shrink the round's evidence rather than simplify it.
    """
    rows = [r for r in routed_invocations() if r.check == "arch/complexity-gate"]
    assert sorted(r.tool for r in rows) == ["radon", "ruff", "xenon"]
    assert all(r.argv == () and r.forms == () for r in rows)


def test_a_route_naming_no_tool_produces_no_row():
    """A `procedure` route with no tool is a reading pass, not a row.

    `arch/martin-metrics` declares two python routes and has one row.
    """
    rows = [r for r in routed_invocations() if r.check == "arch/martin-metrics"]
    assert [r.tool for r in rows] == ["grimp"]


def test_a_record_with_no_python_route_produces_no_row():
    """`arch/size` declares `lang: any` routes only, and selection is python.

    Widening selection is #44's territory: it changes the set of checks the
    round runs, and `arch/size` is in neither the expectations' declared scope
    nor the three-way equality that holds the harness to them.
    """
    assert not [r for r in routed_invocations() if r.check == "arch/size"]


def test_a_routed_row_carries_the_rounds_completion_and_its_reason():
    """The completion is round-owned and travels with why it was needed."""
    row = next(
        r for r in routed_invocations()
        if r.check == "arch/dead-code" and r.tool == "vulture"
    )
    assert row.completion == ("src", "tests")
    assert "the record names none" in row.note


def test_a_quote_belongs_to_a_transcription_and_only_to_one():
    """The field is the prose population's, and the split is asserted.

    Every hand-written entry carries the sentence it was transcribed from;
    every routed row carries none, because there is no second copy for a quote
    to drift from. Read together these two say which population a row belongs
    to without a flag naming it, which is why they are one property and not
    two.
    """
    assert all(i.record_quote for i in INVOCATIONS), sorted(
        (i.check, i.tool) for i in INVOCATIONS if not i.record_quote
    )
    assert all(not r.record_quote for r in routed_invocations())
```

- [ ] **Step 2: Run them to verify they fail**

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q -k routed_row or routed_invocations`
Expected: FAIL with `ImportError: cannot import name 'routed_invocations'`.

- [ ] **Step 3: Add the overlay and the enumeration**

In `scripts/run_python_fixture_lens.py`, directly above `INVOCATIONS`, add the overlay. The four notes are the current entries' notes verbatim: they are the round's finding about what the record failed to say, and rewording one would edit a finding.

```python
@dataclass(frozen=True)
class Completion:
    """What a partition needed that the record did not say, and why.

    Round-owned, which is the whole reason it is here and not in the record:
    a record whose command needs completing is a record to correct, and the
    completion is this round's report of that. `tokens` never reaches the
    prescribed command, so what the record said stays distinguishable from
    what the audit added.
    """

    tokens: tuple[str, ...]
    note: str

    def __post_init__(self) -> None:
        if not self.tokens:
            raise ValueError("a completion with no tokens is not a completion")
        if not self.note:
            raise ValueError(
                "a completion needs the reason it was needed; unexplained, it "
                "reports a repaired command as a clean run"
            )


# Keyed `(check, tool)` to match a row rather than a record: a tool answering
# two checks may need completing for one and not the other.
COMPLETIONS: dict[tuple[str, str], Completion] = {
    ("arch/complexity", "radon"): Completion(
        tokens=("src",),
        note=(
            "`radon cc` takes a path and the record names none; ruff defaults "
            "to the working directory and radon does not, so the same sentence "
            "is runnable for one tool and not the other"
        ),
    ),
    ("arch/complexity", "xenon"): Completion(
        tokens=("--max-absolute", "B", "src"),
        note=(
            "the record names the tool and no arguments; xenon needs both a "
            "threshold and a path, and the expectation is written against "
            "`--max-absolute B`"
        ),
    ),
    ("arch/cycles", "pydeps"): Completion(
        tokens=("src/fixture_app",),
        note="pydeps takes the package to graph and the record names none",
    ),
    ("arch/dead-code", "vulture"): Completion(
        tokens=("src", "tests"),
        note=(
            "vulture takes the paths to scan and the record names none; both "
            "trees are passed because a symbol referenced only by a test is "
            "not dead, and scanning src alone would report the suite's own "
            "callees as unused"
        ),
    ),
}
```

Then, below `invocations_for`, add the enumeration. Keep it beside the other record derivations (`grant_tier`, `tools_named_in_records`) rather than beside the table, because that is what it is.

```python
@cache
def routed_invocations() -> tuple[Invocation, ...]:
    """Every row a migrated record prescribes, read from the record.

    One row per `(check, tool)` rather than per route: a record may narrow the
    same tool's command twice, once `runs` and once `superseded`, and those are
    two forms of one row. A route naming no tool is a reading pass and produces
    no row. A route whose `kind` is not `command` produces a row prescribing no
    command, which is what the record says and what the engine grades.

    `lang: python` only. A `lang: any` route is applicable to a python
    partition by its own note, and selecting it would still be wrong here: it
    adds a check the expectations do not grade, so the three-way equality that
    holds the harness to them would fail rather than the round quietly growing
    a row nothing checks.

    Raises:
        ValueError: If a group carries more than one `runs` command route, two
            different `findings_stream` values, two different `in_env` values,
            or a disposition outside `DISPOSITIONS`. Each would otherwise
            resolve silently to whichever route happened to come first.
    """
    rows: list[Invocation] = []
    for check_id, record in sorted(_records().items()):
        if not record.routes:
            continue
        groups: dict[str, list] = {}
        for route in record.routes:
            if route.lang != "python" or not route.tool:
                continue
            groups.setdefault(route.tool, []).append(route)
        for tool, routes in sorted(groups.items()):
            commands = [r for r in routes if r.kind == "command"]
            for route in commands:
                if route.disposition not in DISPOSITIONS:
                    raise ValueError(
                        f"{check_id}/{tool}: route disposition "
                        f"{route.disposition!r} is outside {DISPOSITIONS}, which "
                        "is the vocabulary the form guards read; a form carrying "
                        "an unknown one would be compared against nothing"
                    )
            runs = [r for r in commands if r.disposition == "runs"]
            if len(runs) > 1:
                raise ValueError(
                    f"{check_id}/{tool}: {len(runs)} command routes declare "
                    "`runs`, so which one the round ran would depend on their "
                    "order in the record"
                )
            streams = {r.findings_stream for r in routes}
            if len(streams) > 1:
                raise ValueError(
                    f"{check_id}/{tool}: routes disagree on findings_stream "
                    f"({sorted(streams)}); classify reads one stream, and "
                    "picking either would grade every run of this tool"
                )
            in_env = {bool(r.in_env) for r in routes}
            if len(in_env) > 1:
                raise ValueError(
                    f"{check_id}/{tool}: routes disagree on in_env, so whether "
                    "the tool launches through the partition's environment "
                    "would depend on their order in the record"
                )
            supplied = COMPLETIONS.get((check_id, tool))
            rows.append(
                Invocation(
                    check=check_id,
                    tool=tool,
                    argv=tuple(runs[0].argv) if runs else (),
                    forms=tuple(
                        (" ".join(r.argv), r.disposition) for r in commands
                    ),
                    findings_stream=streams.pop(),
                    in_env=in_env.pop(),
                    completion=supplied.tokens if supplied else (),
                    note=supplied.note if supplied else "",
                )
            )
    return tuple(rows)
```

`from functools import cache` goes with the existing imports if it is not already there.

- [ ] **Step 3b: Give `record_quote` a default, because a routed row has no transcription to quote**

`routed_invocations` passes no quote, so this is a prerequisite for step 3 constructing at all rather than a separate concern. In `Invocation`:

```python
    record_quote: str = ""
```

Append one sentence to that argument's existing docstring paragraph rather than rewriting it:

```
            Empty on a row built from a record's `routes`, where there is no
            transcription to anchor: the prescription is read from the record
            each run rather than copied here, so there is nothing for a quote
            to hold it against. The property above is what keeps the empty
            value from spreading to a hand-written entry.
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q -k "routed"`
Expected: PASS.

- [ ] **Step 5: Write the transitional equality, which Task 2 deletes**

This is the evidence that the enumeration is a derivation of the table rather than a re-authoring of it. It exists only while both copies do.

```python
def test_the_enumeration_reproduces_the_table_it_replaces():
    """Transitional. Deleted in the commit that cuts the arch entries.

    Held while both copies exist, because that is the only moment the claim
    "nothing about what runs moves" is checkable. Kept afterwards it would be
    a second copy of the prescription, which is the defect this stage removes,
    so its output goes in the PR and the test goes with the entries.

    Compares forms as sets: the table's are in the order somebody typed them
    and the enumeration's follow the record, and neither order is a claim.
    """
    migrated = {cid for cid, c in load_checks(SKILLS_DIR)[0].items() if c.routes}
    table = {
        (i.check, i.tool): i for i in INVOCATIONS if i.check in migrated
    }
    derived = {(r.check, r.tool): r for r in routed_invocations()}
    assert set(derived) == set(table), (
        sorted(set(derived) ^ set(table))
    )
    for key, row in sorted(derived.items()):
        entry = table[key]
        assert row.argv == entry.argv, key
        assert row.findings_stream == entry.findings_stream, key
        assert row.in_env == entry.in_env, key
        assert row.completion == entry.completion, key
        assert row.note == entry.note, key
        expected = set(entry.forms) or (
            {(" ".join(entry.argv), "runs")} if entry.argv else set()
        )
        assert set(row.forms) == expected, key
```

- [ ] **Step 6: Run it and record its output**

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q -k enumeration_reproduces -v`
Expected: PASS, 19 pairs compared. Paste the result into the task report - it is the evidence Task 2 removes the test on.

- [ ] **Step 7: Commit**

```bash
git add scripts/run_python_fixture_lens.py tests/scripts/test_python_fixture_harness.py
git commit -F - -- scripts/run_python_fixture_lens.py tests/scripts/test_python_fixture_harness.py
```

Message: `harness: build a migrated record's rows from its routes`, saying in the body that the transitional equality proves the derivation against the table and is deleted with the entries in the next commit. `Refs #63`.

---

### Task 2: Cut the entries, union the sources, restate the bridge

**Files:**
- Modify: `scripts/run_python_fixture_lens.py:641-887` (delete), and `invocations_for`
- Test: `tests/scripts/test_python_fixture_harness.py`

**Interfaces:**
- Consumes: `routed_invocations()` from Task 1.
- Produces: `invocations_for(partition)` returning rows from both sources. Every downstream consumer is unchanged.

- [ ] **Step 1: Write the failing tests**

```python
def test_no_migrated_check_has_a_hand_written_entry():
    """Two enumeration paths, and a row belongs to exactly one.

    A stale entry is the silent failure this change opens: it keeps a check
    running after its record stops being the source, so editing the record
    has no effect on the run and nothing goes red. Held on the schema the
    record declares rather than on a list of check ids, so a record migrating
    in stage 4 fails here until its entry goes.
    """
    checks, errors = load_checks(SKILLS_DIR)
    assert not errors, errors
    migrated = {cid for cid, c in checks.items() if c.routes}
    stale = sorted({i.check for i in INVOCATIONS} & migrated)
    assert not stale, (
        f"{stale} declare routes and still have a hand-written entry, so the "
        "record is no longer what the run reads"
    )


def test_the_harness_runs_exactly_the_checks_the_expectations_declare():
    """Three views of one set, held equal, over both enumeration paths.

    The records carrying a `python:` entry are what the round exists to
    exercise; the expectations are what each one is graded against; the
    harness is what runs them. A check present in any one of the three and
    missing from another is either a check nobody grades or a claim nobody
    tests, and both look like a complete run.

    The harness's view is now a union: hand-written entries for the checks
    whose fallback lives in prose, routed rows for the records that declare
    their routes. A check dropped by the enumeration, invented by it, or
    claimed by both paths fails here.
    """
    checks, errors = load_checks(SKILLS_DIR)
    assert not errors, errors
    with_python = {c.id for c in checks.values() if c.tooling.get("python")}
    from_table = {i.check for i in INVOCATIONS}
    from_records = {r.check for r in routed_invocations()}
    assert from_table | from_records == with_python, sorted(
        (from_table | from_records) ^ with_python
    )
    assert not from_table & from_records
    assert {e.check for e in EXPECTATIONS} == with_python
```

The second replaces the existing test of the same name rather than sitting beside it.

- [ ] **Step 2: Run them to verify they fail**

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q -k "no_migrated_check or exactly_the_checks"`
Expected: FAIL - 10 migrated checks still have hand-written entries, and the union double-counts them.

- [ ] **Step 3: Delete the arch block**

Delete `scripts/run_python_fixture_lens.py` lines 641 to 887 inclusive: the `# --- arch ---` banner and the 19 entries under it, up to but not including the `# --- deps ---` banner. Nothing else in the tuple moves.

- [ ] **Step 4: Union the two sources in `invocations_for`**

```python
    carried = {e.check for e in expectations_for(partition)}
    everything = INVOCATIONS + routed_invocations()
    scoped = tuple(i for i in everything if i.check in carried)
```

Extend that function's docstring with one sentence rather than rewriting it: the scope is still the expectations, and what changed is that the rows come from two places, the records for those that declare their routes and this file for those whose fallback is still prose.

- [ ] **Step 5: Delete the transitional equality**

Remove `test_the_enumeration_reproduces_the_table_it_replaces` added in Task 1. Its subject is gone: with the entries deleted there is no second copy to compare against, and leaving a frozen expected set in its place would be the copy this stage removes. Paste its final passing output into the commit body.

- [ ] **Step 6: Run the full suite**

Run: `caffeinate uv run pytest tests/ -q`
Expected: PASS. A failure here is the interesting outcome and belongs in the task report with its name: it means a property read the table where it should read the enumeration.

- [ ] **Step 7: Commit**

Message: `harness: the record is the only place a migrated row's command is written`, with the transitional equality's output in the body and the reason it is deleted rather than kept. `Refs #63`.

---

### Task 3: The oracle dissolves, with its reason recorded

**Files:**
- Test: `tests/scripts/test_python_fixture_harness.py`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing. This task only removes, and records why.

- [ ] **Step 1: Delete the two oracle tests**

Remove `test_a_migrated_records_routes_agree_with_the_verified_table` and `test_every_migrated_record_is_in_the_domain_the_oracle_covers`, together with `_ORACLE_DOMAINS` if nothing else reads it. Both exist to catch two copies of one prescription disagreeing, and with one copy neither has a subject.

- [ ] **Step 2: Record the reason where the next reader will look**

Add a module-level comment where they were, not a commit message alone:

```python
# The routes oracle stood here. It held a migrated record's routes against this
# module's transcription of them, which was the only check on the migration
# while both copies existed. `routed_invocations` is now the single source, so
# the oracle had nothing left to compare and was deleted rather than weakened -
# a derivation cannot disagree with itself. Its companion held one of its three
# reach dimensions and went with it.
#
# What it never held, and what still nothing holds, is whether a route is true.
# `arch/size`'s `cloc` argv and `arch/coupling`'s `typescript@^5` pin can each
# be edited to contradict their own notes with this suite green, before this
# change and after it. That is answered by running a route against a seeded
# fixture, which is epic #44, and reading this deletion as having closed it
# would be exactly backwards.
```

- [ ] **Step 3: Run the suite**

Run: `caffeinate uv run pytest tests/ -q`
Expected: PASS, with two fewer tests than Task 2's run. Report both counts.

- [ ] **Step 4: Commit**

Message: `harness: the routes oracle has no subject once there is one copy`. `Refs #63`.

---

### Task 4: Engine-owned properties read the routes, and unreached helpers go

**Files:**
- Test: `tests/scripts/test_python_fixture_harness.py`
- Possibly modify: `scripts/run_python_fixture_lens.py` (only if a property proves a table is now incomplete)

**Interfaces:**
- Consumes: `routed_invocations()`.
- Produces: nothing new. This task re-points existing properties and deletes dead helpers.

- [ ] **Step 1: Find every property that reads `INVOCATIONS` where it means "every row"**

Run: `caffeinate grep -n 'INVOCATIONS' tests/scripts/test_python_fixture_harness.py`

For each, decide which of two things it means, and say which in its docstring if it is not already obvious: rows the table hand-writes, or rows the harness runs. The second must read `INVOCATIONS + routed_invocations()`. `_tools_that_can_run_a_command` and the properties over `NONZERO_EXIT_MEANING` and `VERSION_PROBE` are the ones the spec names: a tool a routed row runs and no engine table grades must fail.

- [ ] **Step 2: Write the failing test for the engine-table coverage**

```python
def test_every_tool_the_harness_runs_carries_an_engine_grading_rule():
    """Engine-owned tables cover both enumeration paths, not just the table.

    The record says what to run; this module says how to read a nonzero exit
    from it. A routed row whose tool no rule grades would be classified by a
    default nobody chose, so it fails here instead.
    """
    for inv in INVOCATIONS + routed_invocations():
        if not inv.argv and not inv.argv_by_partition:
            continue
        assert nonzero_exit_meaning(inv.tool) in NONZERO_EXIT_KINDS, inv.tool
```

- [ ] **Step 3: Run it**

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q -k engine_grading`
Expected: PASS if the tables already cover the five routed command tools, and that is the likely outcome - `ruff`, `radon`, `xenon`, `pydeps` and `vulture` are all in `NONZERO_EXIT_MEANING` today. A failure names a tool to add, and adding it is in scope for this task.

- [ ] **Step 4: Audit the prose helpers for reachability**

For each private helper defined before the first test in `tests/scripts/test_python_fixture_harness.py`, establish whether any surviving property still calls it, directly or through another helper:

```bash
caffeinate uv run python - <<'PY'
import ast, pathlib
src = pathlib.Path("tests/scripts/test_python_fixture_harness.py").read_text()
tree = ast.parse(src)
defs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
helpers = {n for n in defs if n.startswith("_")}
called: dict[str, set] = {n: set() for n in defs}
for name, node in defs.items():
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
            if sub.func.id in defs:
                called[name].add(sub.func.id)
reached, frontier = set(), [n for n in defs if n.startswith("test_")]
while frontier:
    n = frontier.pop()
    for m in called[n] - reached:
        reached.add(m); frontier.append(m)
print("helpers no test reaches:", sorted(helpers - reached))
PY
```

Delete every helper the script names. A helper with no caller is indistinguishable from a helper whose caller was deleted by mistake, and the record set is in git if stage 4 wants it back. Report the list in the task report rather than asserting a count in prose.

- [ ] **Step 5: Confirm the parser still covers the population it is for**

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q -k "prose_fallback_scope"`
Expected: PASS. `PROSE_FALLBACK_CHECKS` must still be non-empty and hold no migrated record, which is the assertion that the 16 live transcriptions are still guarded.

- [ ] **Step 6: Commit**

Message: `harness: the engine's tables cover every row, from either source`, naming the deleted helpers in the body. `Refs #63`.

---

### Task 5: Verify against the fixtures, not only against the suite

**Files:**
- No source change expected. Any change this task forces is a finding and belongs in its own commit with the reason.

**Interfaces:**
- Consumes: the seeded fixture trees under `fixtures/python/`, which are gitignored and live in the main checkout.

- [ ] **Step 1: Run the whole suite and the four gates**

```bash
caffeinate uv run pytest tests/ -q
caffeinate uv run ruff check . && caffeinate uv run ruff format --check .
caffeinate uv run python scripts/render_handbook_traceability.py --check
caffeinate uv run python scripts/render_python_fixture_expectations.py --check
```

Expected: all green. The last one passes whatever this change does, because neither it nor `python_fixture_spec.py` imports the lens; report it as a gate that ran, never as evidence about this change.

- [ ] **Step 2: Run one migrated check against a real fixture**

This is the only step that proves the enumeration reaches a running command rather than only a passing assertion.

```bash
caffeinate uv run python scripts/run_python_fixture_lens.py --partition uv --check arch/complexity --grant none
```

Expected: three rows, `ruff`, `radon` and `xenon`, each with the command the record prescribes plus its completion where it has one, and `xenon` classified off stderr. Paste the rows into the task report. A row reporting `no-evidence (not-permitted)` for all three is the grant doing its job, not a failure; re-run with the grant the row needs if the output is unreadable without it.

- [ ] **Step 3: Re-run the mutation table**

The harness's own mutation table lists the edits that must fail. Re-run it with bytecode writing off, because a mutate-run-revert inside one second can otherwise leave the next run honouring the mutant's cached bytecode:

```bash
PYTHONDONTWRITEBYTECODE=1 caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q
```

For each mutation the table names against `scripts/run_python_fixture_lens.py`, apply it, confirm the suite fails, revert it. A mutation this change makes unreachable - one against a deleted entry - is recorded as such in the table with the reason, not deleted from it.

- [ ] **Step 4: Add the mutation this change invites**

The new silent failure is a routed row and a hand-written entry claiming the same `(check, tool)`. Verify it fails: add back one deleted entry, for instance `arch/dead-code`'s `vulture`, run the suite, confirm `test_no_migrated_check_has_a_hand_written_entry` fails by name, revert. Record the result in the task report and add the mutation to the table.

- [ ] **Step 5: Stale-prose pass**

Not scoped to the diff. `grep` for the names of everything removed - `record_quote` in prose, the oracle test names, `_ORACLE_DOMAINS`, any deleted helper - across `docs/`, `CLAUDE.md` and both modules' comments, and read the whole of any file that describes the harness's shape rather than only the changed hunks. `CLAUDE.md`'s "Check records" and "Tests" sections both describe this machinery and neither is in the diff.

- [ ] **Step 6: Commit**

Message: `harness: record what the fixtures and the mutation table say about the change`, with the filtered run's rows and the mutation results in the body. `Refs #63`.
