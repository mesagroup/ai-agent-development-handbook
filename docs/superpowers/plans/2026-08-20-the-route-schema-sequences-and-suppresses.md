# The route schema sequences a second command and suppresses a runner - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `Route` a `then` and an `own_runner` field, validated by the loader and threaded through the harness enumeration, so that stage 4 can migrate `test/coverage-reach` and `deps/inventory` in #67.

**Architecture:** Two new route fields, validated where every other route field is validated. The enumeration in `run_python_fixture_lens.py` reads both, and reads `argv_by_manager` for the first time because `own_runner`'s list shape is meaningless without it. No record changes, so every new guard is exercised by a synthetic record.

**Tech Stack:** Python 3.12, `pytest`, `ruff`, `PyYAML`.

**Spec:** `docs/superpowers/specs/2026-08-20-the-route-schema-sequences-and-suppresses-design.md`. **Issue:** #66.

## Global Constraints

- The field names are exactly `then` and `own_runner`, in both files. The route field's name matches the `Invocation` field it threads into, deliberately: one vocabulary across the two modules, and the validator checks the repetition rather than trusting it.
- **No check record changes.** No file under `.agents/skills/<domain>-audit/checks/` is edited by any task, and Tasks 1 to 3 edit nothing under `.agents/skills/` at all. Task 4 Step 6 edits `.agents/skills/audit/SKILL.md`, which is a skill instruction rather than a check record; that step was added by amendment after this constraint was written, and the constraint is scoped to records rather than relaxed.
- `own_runner` on a route is `True` or a tuple of manager names. `False` is rejected rather than accepted as a default spelled out: the field's absence already says the launcher applies.
- Every new loader rejection appends to `errors` and never raises: `load_checks` is called from the traceability gate and promises to collect problems.
- Every new enumeration ambiguity raises `ValueError` naming the check, the tool and what is ambiguous, in the style of the five raises already there.
- Run Python through `uv run`. Run `uv run ruff check .` and `uv run ruff format --check .` before every commit.
- Mutation checks run with `PYTHONDONTWRITEBYTECODE=1`.
- Markdown is never hard-wrapped: one paragraph is one source line. No em-dash (U+2014) in `docs/`; use ` - `.
- Never hand-edit anything under `docs/audit/` that a renderer generates.
- `CLAUDE.md` is an agent prompt: its edit is its own commit, and the message says why.

---

### Task 1: `Route` carries the two fields, and the loader validates them

**Files:**
- Modify: `scripts/audit_checks.py` (`ROUTE_FIELDS` around line 199, `Route` around line 252, `_load_routes` docstring around line 374, the per-entry validation around line 530)
- Test: `tests/scripts/test_audit_checks.py`

**Interfaces:**
- Consumes: `_str_list(value) -> tuple[str, ...] | None`, the existing `errors.append(f"{loc}: ...")` idiom, and the test helpers `_one_route_record(tmp_path, route_body)` and `_errors_for_route(tmp_path, route_body)`.
- Produces: `Route.then: tuple[str, ...]` and `Route.own_runner: bool | tuple[str, ...]`, both required fields on the dataclass, both passed by keyword at the single construction site.

- [ ] **Step 1: Write the failing tests**

Add to `tests/scripts/test_audit_checks.py`, beside the other route tests:

```python
def test_a_route_carries_a_second_command_in_sequence(tmp_path):
    check = _one_route_record(
        tmp_path,
        "kind: command\n    tool: coverage.py\n    argv: [coverage, run, -m, pytest]"
        "\n    then: [coverage, report, --show-missing]",
    )
    assert check.routes[0].then == ("coverage", "report", "--show-missing")


def test_a_route_carries_no_second_command_by_default(tmp_path):
    check = _one_route_record(
        tmp_path, "kind: command\n    tool: t\n    argv: [t]"
    )
    assert check.routes[0].then == ()
    assert check.routes[0].own_runner is False


@pytest.mark.parametrize("kind", ["library", "procedure", "subject"])
def test_a_second_command_on_a_non_command_kind_is_rejected(tmp_path, kind):
    errors = _errors_for_route(
        tmp_path, f"kind: {kind}\n    tool: t\n    then: [t, --report]"
    )
    assert any("then" in e and kind in e for e in errors), errors


@pytest.mark.parametrize("written", ["then: []", "then: t --report"])
def test_a_second_command_that_is_not_a_non_empty_list_is_rejected(tmp_path, written):
    errors = _errors_for_route(
        tmp_path, f"kind: command\n    tool: t\n    argv: [t]\n    {written}"
    )
    assert any("then" in e for e in errors), errors


def test_a_shared_argv_may_say_it_needs_no_runner(tmp_path):
    check = _one_route_record(
        tmp_path,
        "kind: command\n    tool: cloc\n    argv: [npx, cloc]\n    own_runner: true",
    )
    assert check.routes[0].own_runner is True


def test_a_per_manager_argv_names_the_managers_needing_no_runner(tmp_path):
    check = _one_route_record(
        tmp_path,
        "kind: command\n    tool: cyclonedx-py\n    argv: [cyclonedx-py, requirements]"
        "\n    argv_by_manager:\n      uv: [uv, export, --frozen]"
        "\n    own_runner: [uv]",
    )
    assert check.routes[0].own_runner == ("uv",)


def test_own_runner_true_beside_per_manager_argvs_is_rejected(tmp_path):
    errors = _errors_for_route(
        tmp_path,
        "kind: command\n    tool: t\n    argv: [t]"
        "\n    argv_by_manager:\n      uv: [uv, export]\n    own_runner: true",
    )
    assert any("own_runner" in e for e in errors), errors


def test_own_runner_naming_managers_without_per_manager_argvs_is_rejected(tmp_path):
    errors = _errors_for_route(
        tmp_path, "kind: command\n    tool: t\n    argv: [t]\n    own_runner: [uv]"
    )
    assert any("own_runner" in e for e in errors), errors


def test_own_runner_naming_a_manager_the_route_does_not_carry_is_rejected(tmp_path):
    errors = _errors_for_route(
        tmp_path,
        "kind: command\n    tool: t\n    argv: [t]"
        "\n    argv_by_manager:\n      uv: [uv, export]\n    own_runner: [poetry]",
    )
    assert any("poetry" in e for e in errors), errors


@pytest.mark.parametrize("kind", ["library", "procedure", "subject"])
def test_own_runner_on_a_non_command_kind_is_rejected(tmp_path, kind):
    errors = _errors_for_route(
        tmp_path, f"kind: {kind}\n    tool: t\n    own_runner: true"
    )
    assert any("own_runner" in e and kind in e for e in errors), errors


def test_own_runner_beside_in_env_is_rejected(tmp_path):
    """An `in_env` route needs the launcher's prefix to reach the materialized
    environment, so suppressing the prefix there is not a command that runs as
    written - it is one that never arrives. `Invocation` rejects the same pair
    from the other side.
    """
    errors = _errors_for_route(
        tmp_path,
        "kind: command\n    tool: t\n    argv: [t]\n    in_env: true"
        "\n    own_runner: true",
    )
    assert any("own_runner" in e and "in_env" in e for e in errors), errors


def test_own_runner_written_false_is_rejected(tmp_path):
    """The absence of the key already says the launcher applies, so writing the
    field is a claim - and `false` is that claim spelled as its own opposite,
    which reads to the next author as a considered decision rather than as a
    key that should not be there.
    """
    errors = _errors_for_route(
        tmp_path, "kind: command\n    tool: t\n    argv: [t]\n    own_runner: false"
    )
    assert any("own_runner" in e for e in errors), errors


def test_own_runner_that_is_neither_true_nor_a_list_is_rejected(tmp_path):
    errors = _errors_for_route(
        tmp_path, "kind: command\n    tool: t\n    argv: [t]\n    own_runner: 1"
    )
    assert any("own_runner" in e for e in errors), errors
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/scripts/test_audit_checks.py -q -k "second_command or own_runner"`
Expected: FAIL - `unknown route key 'then'` / `'own_runner'`, and `AttributeError` on `Route.then`.

- [ ] **Step 3: Add the two keys and the two fields**

In `ROUTE_FIELDS`, add `"then"` and `"own_runner"` to the set. In `Route`, after `argv_by_manager`:

```python
    then: tuple[str, ...]
    own_runner: bool | tuple[str, ...]
```

and extend the class docstring with what each holds and who its first user is:

```python
    `then` holds a second command the record prescribes in sequence, where it
    does: `coverage run -m pytest` followed by `coverage report
    --show-missing` is one route, not two, and dropping the half that prints
    the report would leave the route looking like a tool that produced
    nothing. `own_runner` says the prescribed command is complete as written,
    so whatever launcher a lens would put in front of it puts nothing: `True`
    where the route's one argv needs no runner, or the managers whose
    `argv_by_manager` command needs none.

    Both fields are unused by any record in this tree. Their first users are
    `test/coverage-reach` (`then`) and `deps/inventory` (`own_runner`), which
    migrate in #67 - they are the two records stage 4 could not migrate at
    all, which is why the schema moved first. Nine `arch` routes are already
    runner-led (`npx --package typescript@^5 ...`, `npx cloc`) and say
    nothing, because no lens runs a `lang: typescript` route today.
```

- [ ] **Step 4: Validate them in `_load_routes`**

Insert after the `in_env` block - `own_runner`'s rejection needs both `argv_by_manager` and `in_env` already parsed:

```python
        raw_then = entry.get("then")
        then: tuple[str, ...] = ()
        if raw_then is not None:
            if kind != "command":
                errors.append(
                    f"{loc}: then is only valid on a command route, not {kind!r} - "
                    "there is no first command for a second to follow"
                )
            else:
                names = _str_list(raw_then)
                if names is None:
                    errors.append(f"{loc}: then must be a list of argv strings")
                elif not names:
                    errors.append(
                        f"{loc}: then is empty - a route prescribing a second "
                        "command carries it, and an empty one is the absence the "
                        "field exists to prevent"
                    )
                else:
                    then = names

        raw_own_runner = entry.get("own_runner")
        own_runner: bool | tuple[str, ...] = False
        if raw_own_runner is not None:
            if kind != "command":
                errors.append(
                    f"{loc}: own_runner is only valid on a command route, not "
                    f"{kind!r} - a route prescribing no command has no launcher "
                    "prefix to suppress"
                )
            elif raw_own_runner is True:
                if argv_by_manager:
                    errors.append(
                        f"{loc}: own_runner is true beside argv_by_manager, which "
                        "says every manager's command is complete while naming "
                        "commands per manager; name the managers whose command "
                        "needs no runner instead"
                    )
                else:
                    own_runner = True
            elif raw_own_runner is False:
                errors.append(
                    f"{loc}: own_runner is false - an absent key already says the "
                    "launcher applies, so writing the field is a claim, and false "
                    "is that claim spelled as its own opposite. Drop the key"
                )
            else:
                names = _str_list(raw_own_runner)
                if names is None:
                    errors.append(
                        f"{loc}: own_runner must be true or a list of manager "
                        f"names, got {raw_own_runner!r}"
                    )
                elif not argv_by_manager:
                    errors.append(
                        f"{loc}: own_runner names {list(names)} and the route "
                        "carries no argv_by_manager, so it names managers this "
                        "route does not distinguish; write true where the one "
                        "argv needs no runner"
                    )
                else:
                    unknown = [n for n in names if n not in argv_by_manager]
                    if unknown:
                        errors.append(
                            f"{loc}: own_runner names {unknown}, which "
                            "argv_by_manager does not carry, so the suppressed "
                            "prefix applies to no command"
                        )
                    else:
                        own_runner = names
            if own_runner and in_env:
                errors.append(
                    f"{loc}: own_runner beside in_env - an in_env route needs the "
                    "launcher's prefix to reach the materialized environment, so "
                    "suppressing it is not a command that runs as written, it is "
                    "one that never arrives"
                )
```

Pass both at the construction site: `then=then,` and `own_runner=own_runner,`.

**Abandoned after Task 4's review, and left here as what was planned.** The `own_runner is True` branch above rejects the field beside `argv_by_manager`. Four of the five routes in the tree that would carry this flag have runner-led per-manager overrides, so that rule refuses the field to its own users and leaves the shared argv - what an unnamed manager runs - unable to say it is complete. `true` became a claim about every command the route prescribes; the spec's own section records the reversal and what refuted it.

- [ ] **Step 5: Extend the `_load_routes` docstring**

The docstring enumerates what the loader checks. Add a sentence naming both new fields and their rejections, in its existing voice; it is prose about the code, so state the structural reason rather than the current count.

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/scripts/test_audit_checks.py -q`
Expected: PASS, including the existing route tests.

Then `uv run pytest tests/ -q` - the whole suite, because `Route` gained required fields and the projection reads it.

- [ ] **Step 7: Commit**

```bash
git add scripts/audit_checks.py tests/scripts/test_audit_checks.py
git commit -F - -- scripts/audit_checks.py tests/scripts/test_audit_checks.py
```

Message: what the two fields hold, that no record carries either yet, and that their first users are the two records stage 4 cannot migrate without them. `Refs #66`.

---

### Task 2: the enumeration threads `then`, and a `then` contributes a form

**Files:**
- Modify: `scripts/run_python_fixture_lens.py` (`routed_invocations` around line 1212, its docstring, and a new module-level helper beside it)
- Test: `tests/scripts/test_python_fixture_harness.py`

**Interfaces:**
- Consumes: `Route.then` from Task 1; `_fake_route(**kw)` and `_records_replaced_by(monkeypatch, records)` in the test module.
- Produces: `_forms_for(route) -> tuple[tuple[str, str], ...]`, and a routed row whose `then` is the `runs` route's.

- [ ] **Step 1: Give `_fake_route` the new fields**

`_fake_route` builds a `SimpleNamespace`, so a field the enumeration reads and the fake lacks is an `AttributeError` rather than a default. Add to its `field` dict:

```python
        "then": (),
        "own_runner": False,
        "argv_by_manager": {},
```

`argv_by_manager` and `own_runner` are unused until Task 3 and land here because this is the one place they can land once: a fake missing a field the enumeration will read in the next task fails as an attribute error, which reads as a broken test rather than as a missing default.

- [ ] **Step 2: Write the failing tests**

```python
def test_a_routed_row_carries_the_records_second_command(monkeypatch):
    with _records_replaced_by(
        monkeypatch,
        {
            "x/y": _fake_record(
                _fake_route(
                    tool="coverage.py",
                    argv=("coverage", "run", "-m", "pytest"),
                    then=("coverage", "report", "--show-missing"),
                )
            )
        },
    ):
        (row,) = routed_invocations()
    assert row.then == ("coverage", "report", "--show-missing")


def test_a_second_command_is_a_form_of_its_own(monkeypatch):
    """A `then` that contributed no form would drop the second command out of
    `forms` while the row still ran it, and every property reading forms would
    pass. It takes the route's disposition because it is that route's second
    half rather than a route of its own.
    """
    with _records_replaced_by(
        monkeypatch,
        {
            "x/y": _fake_record(
                _fake_route(argv=("t", "run"), then=("t", "report")),
                _fake_route(
                    argv=("t", "old"),
                    then=("t", "old-report"),
                    disposition="superseded",
                ),
            )
        },
    ):
        (row,) = routed_invocations()
    assert row.forms == (
        ("t run", "runs"),
        ("t report", "runs"),
        ("t old", "superseded"),
        ("t old-report", "superseded"),
    )
    assert row.then == ("t", "report")
```

- [ ] **Step 3: Run them to verify they fail**

Run: `uv run pytest tests/scripts/test_python_fixture_harness.py -q -k second_command`
Expected: FAIL - the row's `then` is `()` and the superseded route's follow-up is missing from `forms`.

- [ ] **Step 4: Implement**

Add beside `routed_invocations`:

```python
def _forms_for(route: object) -> tuple[tuple[str, str], ...]:
    """The forms one command route contributes: its own, and its `then`'s.

    A `then` contributing no form would leave the second command out of
    `forms` while the row still ran it, and every property reading forms would
    still pass. The follow-up takes the route's disposition because it is that
    route's second half rather than a route of its own.
    """
    forms = ((" ".join(route.argv), route.disposition),)
    if route.then:
        forms += ((" ".join(route.then), route.disposition),)
    return forms
```

In `routed_invocations`, replace the `forms=` argument with `forms=tuple(f for r in commands for f in _forms_for(r))`, and add `then=tuple(runs[0].then) if runs else (),` to the `Invocation(...)` call.

- [ ] **Step 5: Extend the `routed_invocations` docstring**

State that a route's `then` is both executed and a form, and why the second half of that is not optional.

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/ -q`
Expected: PASS. The 19 existing routed rows carry no `then`, so their forms are unchanged - Task 4 measures that rather than assuming it.

- [ ] **Step 7: Commit** with `Refs #66`.

---

### Task 3: the enumeration threads `argv_by_manager` and `own_runner`

**Files:**
- Modify: `scripts/run_python_fixture_lens.py` (`routed_invocations` and two new helpers beside it)
- Test: `tests/scripts/test_python_fixture_harness.py`

**Interfaces:**
- Consumes: `Route.own_runner` and `Route.argv_by_manager`; `PARTITIONS`, already imported in this module.
- Produces: `_argv_by_partition(check, tool, route)` and `_own_runner_partitions(route)`.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_routed_row_expands_a_per_manager_argv(monkeypatch):
    """A route may carry both a shared argv and per-manager ones - the loader
    requires the shared one on every command route - so an unnamed partition
    takes the shared argv. A route cannot yet say that one manager has no
    command at all, which is what #67 needs for `deps/inventory`'s PEP 751
    partition.
    """
    with _records_replaced_by(
        monkeypatch,
        {
            "x/y": _fake_record(
                _fake_route(
                    tool="cyclonedx-py",
                    argv=("cyclonedx-py", "requirements"),
                    argv_by_manager={"uv": ("uv", "export", "--frozen")},
                    own_runner=("uv",),
                )
            )
        },
    ):
        (row,) = routed_invocations()
    assert row.argv == ()
    assert dict(row.argv_by_partition)["uv"] == ("uv", "export", "--frozen")
    assert dict(row.argv_by_partition)["pip"] == ("cyclonedx-py", "requirements")
    assert row.own_runner == ("uv",)


def test_own_runner_true_covers_every_partition(monkeypatch):
    with _records_replaced_by(
        monkeypatch,
        {"x/y": _fake_record(_fake_route(argv=("npx", "cloc"), own_runner=True))},
    ):
        (row,) = routed_invocations()
    assert row.own_runner == PARTITIONS
    assert row.argv == ("npx", "cloc")


def test_a_manager_that_is_not_a_partition_is_refused_by_name(monkeypatch):
    """A python route's `argv_by_manager` keys are this lens's partition names.
    A key that is not one threads into an `argv_by_partition` entry
    `prescribed` never finds, so the command silently never runs.
    """
    with (
        _records_replaced_by(
            monkeypatch,
            {
                "x/y": _fake_record(
                    _fake_route(argv=("t",), argv_by_manager={"pnpm": ("pnpm", "t")})
                )
            },
        ),
        pytest.raises(ValueError, match="not a partition"),
    ):
        routed_invocations()
```

`PARTITIONS` needs importing in the test module if it is not already imported there.

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/scripts/test_python_fixture_harness.py -q -k "per_manager or own_runner or not_a_partition"`
Expected: FAIL - `argv_by_partition` is empty, `own_runner` is empty, and no raise.

- [ ] **Step 3: Implement**

```python
def _argv_by_partition(
    check: str, tool: str, route: object
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """One entry per partition, where the record narrows the command per manager.

    Returns `()` where the route names no manager, which leaves the row's
    shared `argv` as the one command every partition runs.

    A route may carry a shared `argv` and per-manager ones at once - the loader
    requires the shared one on every command route - and `Invocation` admits
    one or the other, so a route carrying both expands here: the override
    where the route names the manager, the shared argv everywhere else. That
    makes an unnamed partition inherit rather than have none, which is a limit
    rather than a choice: a route cannot yet say that one manager has no
    command at all.

    Raises:
        ValueError: If the route names a manager that is not a partition of
            this lens. It would thread into an entry `prescribed` never finds,
            so the command would silently never run.
    """
    if not route.argv_by_manager:
        return ()
    unknown = sorted(set(route.argv_by_manager) - set(PARTITIONS))
    if unknown:
        raise ValueError(
            f"{check}/{tool}: argv_by_manager names {unknown}, which is not a "
            f"partition of this lens ({list(PARTITIONS)}); a python route's "
            "manager keys are partition names, and one that is not would thread "
            "into a command no partition ever runs"
        )
    return tuple(
        (p, tuple(route.argv_by_manager.get(p, route.argv))) for p in PARTITIONS
    )


def _own_runner_partitions(route: object) -> tuple[str, ...]:
    """The partitions whose prescribed command takes no launcher prefix.

    `True` on a route carrying one argv is every partition, because that one
    command is what every partition runs. A list names managers, which for a
    python route are partition names.
    """
    if route.own_runner is True:
        return PARTITIONS
    return tuple(route.own_runner) if route.own_runner else ()
```

In `routed_invocations`, replace the `argv` computation and extend the `Invocation(...)` call:

```python
            per_partition = (
                _argv_by_partition(check_id, tool, runs[0]) if runs else ()
            )
            argv = () if per_partition else (tuple(runs[0].argv) if runs else ())
```

and pass `argv_by_partition=per_partition,` and `own_runner=_own_runner_partitions(runs[0]) if runs else (),`.

The `note` branch reads `argv` to decide whether the command ran as written. A row with per-partition argvs has `argv == ()` and does prescribe commands, so that branch must read "prescribes any command" rather than "has a shared argv": use `if supplied: ... elif argv or per_partition: note = ""` and leave the rest as it stands.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/ -q`
Expected: PASS.

- [ ] **Step 5: Commit** with `Refs #66`.

---

### Task 4: hold "nothing existing changes" to a measurement, then the prompt and the gates

**Files:**
- Modify: `CLAUDE.md` (the route-field enumeration in the "Check records" section) - **its own commit**
- Modify: `docs/superpowers/plans/2026-08-20-the-route-schema-sequences-and-suppresses.md` only if a step here proves a plan step wrong, in which case amend it in its own commit saying what forced it

**Interfaces:**
- Consumes: the enumeration as Tasks 2 and 3 left it.
- Produces: the evidence the PR body cites.

- [ ] **Step 1: Measure the 19 routed rows against `main`**

The claim "the enumeration's output is unchanged" is the one thing in this change that a passing suite does not establish. Dump the rows from both trees and diff them:

```bash
git worktree add --detach ../.route-schema-baseline origin/main
cat > /tmp/dump_rows.py <<'PY'
import importlib.util, json, sys
sys.path.insert(0, "scripts")
spec = importlib.util.spec_from_file_location("lens", "scripts/run_python_fixture_lens.py")
m = importlib.util.module_from_spec(spec)
sys.modules["lens"] = m
spec.loader.exec_module(m)
print(json.dumps([
    {k: (list(v) if isinstance(v, tuple) else v) for k, v in vars(r).items()}
    for r in m.routed_invocations()
], indent=2, sort_keys=True, default=str))
PY
uv run python /tmp/dump_rows.py > /tmp/rows-branch.json
(cd ../.route-schema-baseline && uv run python /tmp/dump_rows.py) > /tmp/rows-main.json
diff /tmp/rows-main.json /tmp/rows-branch.json && echo IDENTICAL
git worktree remove --force ../.route-schema-baseline
```

Expected: `IDENTICAL`, or a diff confined to the two new keys carrying their empty values. Record which of the two it was, verbatim, for the PR body. A diff in any other field is a finding, not a formatting difference: stop and report it.

Use a path outside the repository for the worktree if `../.route-schema-baseline` is inconvenient, and remove it in the same step either way - a worktree left behind inside the repo shows up as untracked files in the next commit's `git status`.

- [ ] **Step 2: Mutate each new guard and confirm the named test fails**

Run each with `PYTHONDONTWRITEBYTECODE=1`, revert between mutations, and record the test that failed:

| mutation | test that must fail |
|---|---|
| `_forms_for` returns only the argv's form | `test_a_second_command_is_a_form_of_its_own` |
| `_own_runner_partitions` returns `()` for `True` | `test_own_runner_true_covers_every_partition` |
| the `unknown` raise in `_argv_by_partition` is dropped | `test_a_manager_that_is_not_a_partition_is_refused_by_name` |
| the `own_runner`/`in_env` rejection is dropped | `test_own_runner_beside_in_env_is_rejected` |
| `own_runner is False` falls through instead of appending an error | `test_own_runner_written_false_is_rejected` |

A mutation that leaves the suite green is a finding about the test, not a mutation to skip.

- [ ] **Step 3: Run the four gates**

```bash
uv run pytest tests/ -q
uv run ruff check . && uv run ruff format --check .
uv run python scripts/render_handbook_traceability.py --check
uv run python scripts/render_python_fixture_expectations.py --check
```

The second renderer is a gate that ran, not evidence about this change: neither it nor `python_fixture_spec.py` imports the lens.

- [ ] **Step 4: Confirm no record changed**

```bash
git diff --name-only origin/main...HEAD -- '.agents/skills/*/checks/'
```

Expected: empty. The check records are what this unit must not touch. The broader `-- .agents/skills/` form returns `audit/SKILL.md` once Step 6 has run, which is that step's deliverable rather than a violation - run the narrow form, and read the broad one as the record of which skill instructions changed.

- [ ] **Step 5: Extend `CLAUDE.md`'s route-field enumeration, in its own commit**

The "Check records" section lists the route fields verbatim ("carrying `lang`, `kind`, `tool`, ... `alone_insufficient` and `note`"). Add `then` and `own_runner` to that list, and one sentence on what each holds and on `own_runner`'s two shapes. Commit alone:

```bash
git commit -F - -- CLAUDE.md
```

The message says **why**: the file is the prompt an agent reads before writing a record, so a field it does not list is a field the next record cannot use.

- [ ] **Step 6: Extend `.agents/skills/audit/SKILL.md`'s route-reading instruction, in its own commit**

This is the step the plan originally missed, and it is the one that matters most to an executing agent. Line 53 of that file tells an agent how to read a route: which `kind` hands it something to run, that a `kind: command` route's `argv` or matching `argv_by_manager` entry is what to run, what each `disposition` means. An agent reading that instruction against a record carrying `then` runs the first command and drops the second - which is precisely the failure `then` exists to prevent, reintroduced one layer up. Same for `own_runner`: an agent that fronts a complete command with a one-shot runner fetches a package the command never calls, and the run reports that package's version as the one that answered.

Add to that instruction, in its existing voice: that a `kind: command` route may carry a `then`, which is the second half of the same route rather than a route of its own, so both commands run in the record's order and a route whose `then` is dropped reports a tool that produced nothing; and that `own_runner` says the prescribed command is complete as written, so the one-shot runner the surrounding instruction otherwise requires goes in front of nothing - `true` for the route's one argv, or the managers named for their `argv_by_manager` entries.

Then check `docs/audit/sweep-obligations.md`, which is hand-maintained and whose rows quote `audit-core` verbatim: `CLAUDE.md` states that editing `audit/SKILL.md` means checking it. `tests/scripts/test_sweep_obligations.py` catches a row whose anchor moved or whose quotation is no longer verbatim; it cannot judge whether a disposition is still true, so read the rows whose subject is route-reading.

Commit alone: `git commit -F - -- .agents/skills/audit/SKILL.md`, and the message says why - the file is the instruction an executing agent follows, so a route field it does not describe is a field the agent ignores at run time even though the loader accepts it and the harness threads it.

- [ ] **Step 7: Stale-prose pass, scoped by blast radius**

Dispatch to a subagent that has seen neither the plan nor the implementation. Give it the worktree's absolute root, require it to confirm `git rev-parse --show-toplevel` and `git rev-parse HEAD` before reading, and scope it by what the change could have invalidated rather than by the diff: every mention of the route field list, of what `Invocation.then`/`own_runner` are populated from, of "no python route carries an `argv_by_manager`", and of `_fake_route`'s fields. `docs/audit/sweep-obligations.md`, the nine `<domain>-audit/SKILL.md` files and `docs/engineering/` are in scope for the reading even though no task edits them, and so is `audit-core/SKILL.md`, whose record-schema paragraph names what each schema carries.
