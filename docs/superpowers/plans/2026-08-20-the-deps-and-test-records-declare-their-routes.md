# The deps and test records declare their routes - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the 13 `deps` and `test` records from `tooling:`/`needs:` to `routes:`, so the Python fixture harness reads all 16 of their rows from the records instead of from a transcription.

**Architecture:** Three mechanism tasks first, each with no record change and a byte-identical row dump as its proof: a field rename, a command route that may prescribe a command for some partitions and none for others, and a round-owned home for a supplied route. Then four record-migration tasks, each deleting the `INVOCATIONS` rows its records replace. Then one sweep task that holds the whole result against the baseline, proves every narrowed property still has a subject, and runs the fixtures.

**Tech Stack:** Python 3, `uv`, pytest, ruff. The records are Markdown with YAML frontmatter under `.agents/skills/<domain>-audit/checks/`.

**Spec:** `docs/superpowers/specs/2026-08-20-the-deps-and-test-records-declare-their-routes-design.md`

## Global Constraints

- **The baseline row dump** is at `<SCRATCH>/rows-baseline.json`, where `<SCRATCH>` is the session scratchpad directory named in the dispatch. It holds all 50 rows (31 hand-written, 19 routed) as they were before this branch, keyed `check|tool`. Every task that can change a row compares against it. Regenerate the comparison, never the baseline.
- **Migration is not correction.** A route prescribes what the prose prescribed, token for token. A command the prose leaves incomplete stays incomplete and the missing tokens stay in `COMPLETIONS`, which is round-owned. Every one of the four `COMPLETIONS` entries on `main` is for an already-migrated `arch` record, which is the precedent.
- **A placeholder never reaches a command.** `argv` on a `disposition: runs` route carries no `<...>` token; the completion supplies the concrete value. A non-`runs` route may carry a placeholder, because nothing runs it.
- **Never write into `fixtures/python/<partition>`.** Those trees are seeded ground truth. Every run happens in a copy.
- **Prompt changes get their own commits.** `CLAUDE.md`, everything under `.agents/skills/` including every check record. The message says WHY, not just what. Never in the same commit as loader, harness or test code.
- **`git commit -F - -- <paths>`**, naming the paths. Never a bare `git commit`, never `git add -A`, `git add .`, `git commit -a`, `git stash`, `git checkout -- .` or `git clean`.
- **Markdown is never hard-wrapped**: one paragraph is one source line, and lines you did not change are never reflowed. This does not apply inside a record's YAML block scalars, which the family already wraps.
- **No em-dash (U+2014)** anywhere in this work. Use ` - `.
- **Never assert a count you did not compute.** Compute it in the same breath or state no number. This includes "every other record does X".
- **Every property this work narrows or widens is proven non-vacuous** - by mutation where it reads a population, by deletion where it reads a guard. A property whose premise a change falsifies is repaired against the new premise, never left green.
- Run Python via `uv run`. Prepend `caffeinate` to any command that waits. Mutation runs against `scripts/run_python_fixture_lens.py` set `PYTHONDONTWRITEBYTECODE=1`.
- Never run `ruff` explicitly against `docs/`; `extend-exclude = ["docs"]` is load-bearing. Never `ruff --fix` repo-wide.

## File Structure

| File | Responsibility in this plan |
|---|---|
| `scripts/audit_checks.py` | The loader. Renames `argv_by_manager`, relaxes the shared-`argv` requirement on a command route that carries per-partition commands. |
| `scripts/run_python_fixture_lens.py` | The harness. Renames the field it reads, derives forms from every command a route prescribes, gains the `SUPPLIED` overlay, loses 16 `INVOCATIONS` rows and gains four `COMPLETIONS` entries. |
| `tests/scripts/test_audit_checks.py` | Loader tests: the rename, the relaxation, the reworded rejections. |
| `tests/scripts/test_python_fixture_harness.py` | Harness properties: forms derivation, the overlay, and the scope every property narrows as records migrate. |
| `.agents/skills/deps-audit/checks/*.md` (6) | Migrated in Tasks 4 and 5. |
| `.agents/skills/test-audit/checks/*.md` (7) | Migrated in Tasks 6 and 7. |
| `.agents/skills/arch-audit/checks/{coupling,cycles,layering,over-decomposition}.md` | One `argv_by_manager` key each, renamed in Task 1. |
| `CLAUDE.md`, `.agents/skills/audit/SKILL.md` | One mention of the field each, renamed in Task 1. |

---

## Task 1: Rename `argv_by_manager` to `argv_by_partition`

**Files:**
- Modify: `scripts/audit_checks.py` (21 occurrences), `scripts/run_python_fixture_lens.py` (4), `tests/scripts/test_audit_checks.py` (20), `tests/scripts/test_python_fixture_harness.py` (9)
- Modify: `.agents/skills/arch-audit/checks/coupling.md`, `cycles.md`, `layering.md`, `over-decomposition.md` (1 each)
- Modify: `CLAUDE.md` (1), `.agents/skills/audit/SKILL.md` (1)

**Interfaces:**
- Produces: `Route.argv_by_partition: dict[str, tuple[str, ...]]`, and the frontmatter key `argv_by_partition`. Every later task reads this name.

**Do not** touch anything under `docs/superpowers/`. The specs and plans of #63 and #66 record decisions as they were taken, and this unit's own spec and plan describe the rename in both spellings on purpose; all of those occurrences stay, which is why the check above excludes the directory rather than counting them.

- [ ] **Step 1: Confirm the occurrence set before changing anything**

```bash
grep -rn "argv_by_manager" --exclude-dir=.git --exclude-dir=superpowers . | wc -l
```

Expected: 60 lines. `--exclude-dir=superpowers` is how the specs and plans are held out, this one included: a `grep -v "^./docs/superpowers/"` filter silently excludes nothing, because `grep -r .` prints paths with no `./` prefix and the pattern's unescaped `.` then matches any character. If the count differs, stop and report - the plan's file list is then wrong, and a rename driven by a stale list leaves a half-renamed field that loads as an unknown key.

- [ ] **Step 2: Write the failing test**

In `tests/scripts/test_audit_checks.py`, beside the other route-field tests:

```python
def test_the_per_partition_argv_key_is_argv_by_partition(tmp_path):
    """The schema's word for the axis a language's targets split along.

    A package manager where one distinguishes the case, a lock standard where
    none does: a python route's keys are `uv`, `pip`, `poetry`, `pipenv` and
    `pylock`, and only four of those name a manager. The old key is rejected as
    an unknown field rather than silently ignored, which is what would leave a
    renamed record prescribing one command for every partition.
    """
    errors = _errors_for_route(
        tmp_path,
        "kind: command\n    tool: t\n    argv: [t]\n"
        "    argv_by_manager:\n      uv: [t, u]",
    )
    assert any("argv_by_manager" in e for e in errors), errors
```

- [ ] **Step 3: Run it to see it fail**

```bash
uv run pytest tests/scripts/test_audit_checks.py::test_the_per_partition_argv_key_is_argv_by_partition -q
```

Expected: FAIL - the key is currently valid, so no error mentions it.

- [ ] **Step 4: Rename in the four Python files**

Rename the field, the local variables, the `ROUTE_FIELDS` entry and every message. Then read each renamed message and docstring and reword the prose around it: `manager` becomes `partition` where it names the key's vocabulary, and the sentences explaining what the two `own_runner` shapes mean must say partition too. `_own_runner_partitions`, `_argv_by_partition` and `Invocation.argv_by_partition` already use the word and stay as they are.

- [ ] **Step 5: Run the suite**

```bash
caffeinate uv run pytest tests/ -q
```

Expected: PASS, including the new test. Any failure naming `argv_by_manager` is a spot the rename missed.

- [ ] **Step 6: Prove the rows did not move**

```bash
uv run python - <<'PY'
import sys, json, dataclasses
sys.path.insert(0, "scripts")
from run_python_fixture_lens import INVOCATIONS, routed_invocations
rows = {}
for src, pop in (("hand", INVOCATIONS), ("routed", routed_invocations())):
    for inv in pop:
        d = dataclasses.asdict(inv); d["_source"] = src
        rows[f"{inv.check}|{inv.tool}"] = d
base = json.load(open("<SCRATCH>/rows-baseline.json"))
same = json.loads(json.dumps(rows, sort_keys=True, default=list)) == base
print("rows identical to baseline:", same, len(rows))
PY
```

Expected: `True 50`. The four `arch` records are renamed in this task, so this is the step that proves a rename of live record keys changed no command.

- [ ] **Step 7: Commit the code**

```bash
git commit -F - -- scripts/audit_checks.py scripts/run_python_fixture_lens.py tests/scripts/test_audit_checks.py tests/scripts/test_python_fixture_harness.py
```

Message: why the field is renamed - a python route's keys are the lens's partition names and only four of the five name a manager, so the old name was wrong on the key #67 has to write, and `Invocation.argv_by_partition` already carried the other name for the same thing.

- [ ] **Step 8: Rename in the records and the two prompt files, and commit them separately**

```bash
git commit -F - -- .agents/skills/arch-audit/checks/coupling.md .agents/skills/arch-audit/checks/cycles.md .agents/skills/arch-audit/checks/layering.md .agents/skills/arch-audit/checks/over-decomposition.md .agents/skills/audit/SKILL.md CLAUDE.md
```

The `CLAUDE.md` sentence enumerating the route fields and the `audit/SKILL.md` line an executing agent reads both name the key; the prose around each must state the vocabulary, not just the new spelling. Message says why, as above.

- [ ] **Step 9: Confirm nothing is half-renamed**

```bash
grep -rn "argv_by_manager" --exclude-dir=.git . | grep -v "^./docs/superpowers/"
```

Expected: no output.

---

## Task 2: A command route may prescribe a command for some partitions and none for others

**Files:**
- Modify: `scripts/audit_checks.py` (the `raw_argv` block in `_load_routes`, and the docstring enumerating what it validates)
- Modify: `scripts/run_python_fixture_lens.py` (`_forms_for`, `_argv_by_partition`)
- Test: `tests/scripts/test_audit_checks.py`, `tests/scripts/test_python_fixture_harness.py`

**Interfaces:**
- Consumes: `Route.argv_by_partition` from Task 1.
- Produces: a `kind: command` route may carry `argv_by_partition` with no `argv`; a partition the map does not name then has no command. `_forms_for(check, tool, route)` returns one form per distinct command the route prescribes.

- [ ] **Step 1: Write the failing loader tests**

```python
def test_a_command_route_may_name_per_partition_commands_and_no_shared_argv(tmp_path):
    """`deps/inventory` prescribes a subcommand per dependency file and none for PEP 751.

    Read as default-plus-overrides, a shared argv makes an unnamed partition
    inherit rather than have none, and there is no command to inherit that
    would be true: `cyclonedx-py requirements` on a tree with no requirements
    file runs and answers about nothing.
    """
    errors = _errors_for_route(
        tmp_path,
        "kind: command\n    tool: t\n"
        "    argv_by_partition:\n      uv: [t, u]\n      pip: [t, p]",
    )
    assert errors == []


def test_a_command_route_carrying_neither_argv_nor_per_partition_commands_is_rejected(
    tmp_path,
):
    """The relaxation is about where the command lives, not about having one."""
    errors = _errors_for_route(tmp_path, "kind: command\n    tool: t")
    assert any("no command at all" in e for e in errors), errors
```

- [ ] **Step 2: Run them to see the first fail**

```bash
uv run pytest tests/scripts/test_audit_checks.py -q -k "per_partition_commands_and_no_shared or carrying_neither"
```

Expected: the first FAILs on `a command route must carry a non-empty argv`; the second passes already, on the old message.

- [ ] **Step 3: Relax the loader**

Replace the `kind == "command"` branch of the `raw_argv` block. The `argv_by_partition` block runs after it, so read the raw value rather than the parsed map:

```python
        raw_argv = entry.get("argv")
        raw_per_partition = entry.get("argv_by_partition")
        if kind == "command":
            argv = _str_list(raw_argv) or ()
            if not argv and not raw_per_partition:
                errors.append(
                    f"{loc}: a command route carries no command at all - name the "
                    "shared argv, or name one per partition where the record "
                    "prescribes a different command for each and none for some"
                )
            elif not argv and raw_argv is not None:
                errors.append(
                    f"{loc}: argv is present and empty - an absent argv beside "
                    "argv_by_partition says the partitions it does not name have "
                    "no command, and an empty one says nothing at all"
                )
```

Then update the `_load_routes` docstring sentence that currently says every command route's `argv` is non-empty: it is non-empty **where written**, and absent only beside `argv_by_partition`, where its absence is what says an unnamed partition has no command.

- [ ] **Step 4: Run the loader tests**

```bash
uv run pytest tests/scripts/test_audit_checks.py -q
```

Expected: PASS. A pre-existing test asserting `a command route must carry a non-empty argv` for a route with neither field needs its expected substring updated to `no command at all` - it is the same rejection, reworded, and it must keep asserting a substring that occurs in exactly one loader message.

- [ ] **Step 5: Write the failing harness test for forms**

```python
def test_a_route_with_no_shared_argv_takes_its_forms_from_the_per_partition_commands():
    """Otherwise the row declares the empty string as a form.

    `Invocation._check_forms` raises on it, so the failure is loud rather than
    silent - which is the only reason this is a design decision and not a
    defect waiting for the first record to carry the shape. Each per-partition
    command is a command the row runs, so each is a form; a form no command
    carries and a command no form declares are the two halves the guards hold
    against each other, and a form derived from the shared argv alone would
    leave every per-partition command in the second category.
    """
    route = _fake_route(
        kind="command",
        tool="t",
        argv=(),
        argv_by_partition={"uv": ("t", "u"), "pip": ("t", "p")},
    )
    assert _forms_for("c/x", "t", route) == (("t u", "runs"), ("t p", "runs"))


def test_two_partitions_prescribing_the_same_command_declare_it_once():
    """`_check_forms` raises on a duplicate form, and one command is one form."""
    route = _fake_route(
        kind="command",
        tool="t",
        argv=(),
        argv_by_partition={"uv": ("t", "s"), "pip": ("t", "s")},
    )
    assert _forms_for("c/x", "t", route) == (("t s", "runs"),)
```

- [ ] **Step 6: Run them to see them fail**

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest tests/scripts/test_python_fixture_harness.py -q -k "no_shared_argv_takes_its_forms or same_command_declare_it_once"
```

Expected: FAIL - `_forms_for` takes one argument today and reads `route.argv` only.

- [ ] **Step 7: Derive the forms from every command**

```python
def _partition_keys(check: str, tool: str, route: object) -> tuple[str, ...]:
    """The route's per-partition keys, checked against this lens's partitions.

    Held for every command route rather than only the `runs` one, because a
    form is derived from every command route: a key outside `PARTITIONS` on a
    `superseded` route would contribute a form no partition could ever run,
    which reads as a record whose prescription the harness ignores.
    """
    unknown = sorted(set(route.argv_by_partition) - set(PARTITIONS))
    if unknown:
        raise ValueError(
            f"{check}/{tool}: argv_by_partition names {unknown}, which is not a "
            f"partition of this lens ({list(PARTITIONS)}); a python route's keys "
            "are partition names, and one that is not would thread into a "
            "command no partition ever runs"
        )
    return tuple(route.argv_by_partition)


def _forms_for(check: str, tool: str, route: object) -> tuple[tuple[str, str], ...]:
    """Every distinct command this route prescribes, as a form.

    Its shared `argv` where it has one, each per-partition command, and its
    `then`. A route with no shared argv would otherwise contribute the empty
    string, which `Invocation._check_forms` raises on. Two partitions
    prescribing the same command contribute one form: `_check_forms` rejects a
    duplicate, and one command is one form whatever number of partitions run
    it.

    The `then` takes the route's disposition because it is that route's second
    half rather than a route of its own, and it is a form because the row runs
    it - left out, it is a command the row runs that no guard sees declared.
    """
    commands: list[tuple[str, ...]] = []
    if route.argv:
        commands.append(tuple(route.argv))
    for partition in _partition_keys(check, tool, route):
        argv = tuple(route.argv_by_partition[partition])
        if argv not in commands:
            commands.append(argv)
    if route.then:
        commands.append(tuple(route.then))
    return tuple((" ".join(argv), route.disposition) for argv in commands)
```

Update the two call sites: `routed_invocations` passes `check_id` and `tool`, and `_argv_by_partition` calls `_partition_keys` instead of carrying its own copy of the raise. Keep `_argv_by_partition`'s `.get(partition, route.argv)`, which with an empty shared argv already yields `()` for an unnamed partition; correct its docstring, which today says a route "cannot yet say that one manager has no command at all".

- [ ] **Step 8: Run the suite**

```bash
caffeinate env PYTHONDONTWRITEBYTECODE=1 uv run pytest tests/ -q
```

Expected: PASS. No record carries per-partition commands on a python route yet, so nothing else moves.

- [ ] **Step 9: Prove the rows still match the baseline**

Re-run Task 1 Step 6. Expected: `True 50`.

- [ ] **Step 10: Prove each new guard fires**

Delete the `not argv and not raw_per_partition` branch, run the loader tests, confirm the named test fails, restore, confirm it passes. Do the same for `_partition_keys`'s raise and for the dedup in `_forms_for`. Compare each restored file byte-for-byte with a copy taken before the mutation.

- [ ] **Step 11: Commit**

```bash
git commit -F - -- scripts/audit_checks.py scripts/run_python_fixture_lens.py tests/scripts/test_audit_checks.py tests/scripts/test_python_fixture_harness.py
```

---

## Task 3: A round-owned home for a supplied route

**Files:**
- Modify: `scripts/run_python_fixture_lens.py` (a `Supplied` dataclass, a `SUPPLIED` mapping, and `routed_invocations`)
- Test: `tests/scripts/test_python_fixture_harness.py`

**Interfaces:**
- Produces: `SUPPLIED: dict[tuple[str, str], Supplied]`, read by `routed_invocations` and populated in Task 5. `Supplied(by_partition: tuple[tuple[str, tuple[tuple[str, ...], ...]], ...], note: str)`.

A supplied route is a command **this round contributed** for a partition the record prescribes none for. It cannot be a route field: a record declaring one would be prescribing it, which is the distinction the field exists to preserve.

- [ ] **Step 1: Write the failing test**

```python
def test_a_migrated_record_reads_its_supplied_route_from_the_overlay(monkeypatch):
    """The round's contribution stays round-owned after a record migrates.

    `Invocation` already refuses a supplied route with no note, a partition
    carrying both a prescribed and a supplied route, and a supplied route
    beside `in_env`, so the overlay needs no validation of its own - what it
    needs is a place to live that is not the record.
    """
    steps = (("uvx", "t", "sub", "pylock.toml"),)
    monkeypatch.setitem(
        SUPPLIED,
        ("x/y", "t"),
        Supplied(
            by_partition=(("pylock", steps),),
            note="the record names no route at all for a PEP 751 file",
        ),
    )
    with _records_replaced_by(monkeypatch, {"x/y": _fake_record(_fake_route())}):
        (row,) = routed_invocations()
    assert row.supplied("pylock") == steps
    assert row.supplied_note
```

`_records_replaced_by` and `_fake_record`/`_fake_route` are the module's existing helpers; the context manager clears `routed_invocations`' cache on both sides, and `monkeypatch.setitem` reverts the overlay. Assert on the row, never on the mapping.

- [ ] **Step 2: Run it to see it fail**

Expected: FAIL - `SUPPLIED` does not exist.

- [ ] **Step 3: Add the dataclass and the mapping**

```python
@dataclass(frozen=True)
class Supplied:
    """A route this round contributed where the record prescribes none.

    Round-owned for the reason `Completion` is: the record naming no route for
    a partition is a hole in the record, and this is the candidate answer this
    round tests against it. Keyed `(check, tool)` beside `COMPLETIONS`, so a
    migrated record's supplied route lives where its completion does rather
    than in the record that, by definition, does not prescribe it.
    """

    by_partition: tuple[tuple[str, tuple[tuple[str, ...], ...]], ...]
    note: str

    def __post_init__(self) -> None:
        if not self.by_partition:
            raise ValueError("a supplied route with no steps is not a route")
        if not self.note:
            raise ValueError(
                "a supplied route needs the reason the record has none; "
                "unexplained, it reads as a command the record prescribed"
            )


SUPPLIED: dict[tuple[str, str], Supplied] = {}
```

In `routed_invocations`, read it beside the completion and pass both fields through:

```python
            contributed = SUPPLIED.get((check_id, tool))
```

with `supplied_by_partition=contributed.by_partition if contributed else ()` and `supplied_note=contributed.note if contributed else ""`. Extend the function's docstring: the row's supplied route comes from the overlay, never from a route, and the two reasons a row's `note` can be round-owned are now a completion and nothing else - a supplied route carries its own note.

- [ ] **Step 4: Run the suite**

```bash
caffeinate env PYTHONDONTWRITEBYTECODE=1 uv run pytest tests/ -q
```

Expected: PASS, and the rows still match the baseline (`True 50`) - the mapping is empty until Task 5.

- [ ] **Step 5: Prove both `Supplied` guards fire**

Two tests, each asserting the message: a `Supplied` with no steps, and one with steps and no note.

- [ ] **Step 6: Commit**

```bash
git commit -F - -- scripts/run_python_fixture_lens.py tests/scripts/test_python_fixture_harness.py
```

---

## Task 4: Migrate the four straightforward `deps` records

**Files:**
- Modify: `.agents/skills/deps-audit/checks/freshness.md`, `hygiene.md`, `licenses.md`, `transitive-licenses.md`
- Modify: `scripts/run_python_fixture_lens.py` (delete five `INVOCATIONS` rows, add two `COMPLETIONS` entries)
- Test: `tests/scripts/test_python_fixture_harness.py` if a property's scope needs repairing

**Interfaces:**
- Consumes: the schema as Tasks 1-3 leave it.
- Produces: five routed rows replacing five transcribed ones, with the exact values in the table below.

Each record: replace `tooling:`/`needs:`/`ungranted_note:` with `routes:`, delete the whole `## Tooling fallback` section, and move every claim it held into the field that carries it. Nothing is dropped. A claim about the check rather than about any one route goes in `evidence:` or in body prose; a claim about one route goes in that route's `note`, `applies_when` or `alone_insufficient`.

**The `ungranted_note` becomes routes.** `answers_ungranted` accepts only the sentinel `none`, so there is no prose slot: each of these records' notes becomes an untiered `kind: procedure` route carrying that prose, which is what un-silences the language. `_silenced_languages` counts a procedure route as answering, so the claim the note made is now a route the harness enumerates.

**Every TypeScript claim moves too**, into `lang: typescript` routes. These records carry long measured TypeScript prose - `npm outdated` dropping missing devDependencies, `pnpm outdated` reporting the root manifest only against a 9-manifest workspace, `depcheck`'s `bin` special silently reporting a CLI-only dependency as unused, `@cyclonedx/cdxgen` needing `FETCH_LICENSE=true`. None of it is this lens's business and all of it is the record's.

**Exact row values after migration.** `<VENV_BIN>` is the module constant, `stdout` unless named:

| row | argv | completion | in_env | stream | needs | derived forms |
|---|---|---|---|---|---|---|
| `deps/freshness` / `uv` | `[uv, pip, list, --outdated, --python]` | `[<VENV_BIN>/python]` | true | | `resolved-tree` | `uv pip list --outdated --python` (runs), `uv pip list --outdated` (superseded) |
| `deps/freshness` / `pip` | `[pip, list, --outdated]` | | true | | `resolved-tree` | `pip list --outdated` (runs) |
| `deps/hygiene` / `deptry` | `[deptry]` | `[.]` | true | `stderr` | `resolved-tree` | `deptry` (runs) |
| `deps/licenses` / `pip-licenses` | `[pip-licenses]` | | true | | `resolved-tree` | `pip-licenses` (runs), `pip-licenses --format json` (alternative) |
| `deps/transitive-licenses` / `pip-licenses` | `[pip-licenses]` | | true | | `resolved-tree` | `pip-licenses` (runs) |

Three of those derived form sets are wider than what the transcription declared, and that is the migration closing a gap rather than changing what runs: `deptry` and `pip-licenses` are commands the harness runs today and declares in no form, because forms were read off the prose and the prose names them inside a sentence rather than as a command line. `deps/freshness`'s `uv` runs form loses its `<path-to-venv-python>` tail, because a form is now derived from the argv and the argv stops where the placeholder starts - the placeholder lives in the completion's note.

- [ ] **Step 1: Write the failing acceptance test**

In `tests/scripts/test_python_fixture_harness.py`:

```python
def test_the_deps_rows_survive_their_records_migration():
    """The five rows these records prescribe, held against what they ran before.

    A migration that changes what runs is not a migration. The values are
    written out rather than read from a baseline file because the point is to
    fail when the record changes, not when a scratch file goes missing.
    """
    expected = {
        ("deps/freshness", "uv"): (("uv", "pip", "list", "--outdated", "--python"), True, "stdout"),
        ("deps/freshness", "pip"): (("pip", "list", "--outdated"), True, "stdout"),
        ("deps/hygiene", "deptry"): (("deptry",), True, "stderr"),
        ("deps/licenses", "pip-licenses"): (("pip-licenses",), True, "stdout"),
        ("deps/transitive-licenses", "pip-licenses"): (("pip-licenses",), True, "stdout"),
    }
    rows = {(i.check, i.tool): i for i in routed_invocations()}
    for key, (argv, in_env, stream) in expected.items():
        row = rows[key]
        assert row.argv == argv, key
        assert row.in_env is in_env, key
        assert row.findings_stream == stream, key
```

- [ ] **Step 2: Run it to see it fail**

Expected: FAIL with `KeyError` - the records declare no routes yet, so no routed row exists for them.

- [ ] **Step 3: Migrate the four records**

One record at a time. After each, run `uv run python -c "import sys; sys.path.insert(0, 'scripts'); from audit_checks import SKILLS_DIR, load_checks; c, e = load_checks(SKILLS_DIR); print(len(c), e)"` and expect `77 []`. A loader error names the record, the route index and the field.

- [ ] **Step 4: Delete the five `INVOCATIONS` rows and add the two `COMPLETIONS` entries**

The completion notes carry what the deleted rows' notes said: the interpreter path resolving inside the copy this run owns, and `deptry`'s missing scan root with the measurement that the answer moves with it.

- [ ] **Step 5: Run the suite**

```bash
caffeinate env PYTHONDONTWRITEBYTECODE=1 uv run pytest tests/ -q
```

Expected: PASS. `PROSE_FALLBACK_CHECKS` shrinks by four and the properties scoped by it stop reading these records, which is the intended narrowing - `test_the_prose_fallback_scope_is_not_empty_and_holds_no_migrated_record` is what holds it to a set that is neither empty nor stale.

- [ ] **Step 6: Compare against the baseline**

```bash
uv run python - <<'PY'
import sys, json, dataclasses
sys.path.insert(0, "scripts")
from run_python_fixture_lens import INVOCATIONS, routed_invocations
base = json.load(open("<SCRATCH>/rows-baseline.json"))
now = {}
for pop in (INVOCATIONS, routed_invocations()):
    for inv in pop:
        now[f"{inv.check}|{inv.tool}"] = json.loads(
            json.dumps(dataclasses.asdict(inv), sort_keys=True, default=list))
for key in sorted(set(base) | set(now)):
    if key not in now:
        print("GONE", key); continue
    if key not in base:
        print("NEW ", key); continue
    b = {k: v for k, v in base[key].items() if k != "_source"}
    for field in sorted(b):
        if b[field] != now[key][field]:
            print(f"{key} {field}:\n    was {b[field]!r}\n    now {now[key][field]!r}")
PY
```

Expected: differences on the five migrated rows only, and on those only in `record_quote` (emptied), `forms` (as the table says) and `note` (the completion's note, or empty). Every `arch` row and every `docs`, `security` and unmigrated `test` row identical. Read every line of output; a difference nobody named is a finding.

- [ ] **Step 7: Commit, records apart from code**

```bash
git commit -F - -- .agents/skills/deps-audit/checks/freshness.md .agents/skills/deps-audit/checks/hygiene.md .agents/skills/deps-audit/checks/licenses.md .agents/skills/deps-audit/checks/transitive-licenses.md
git commit -F - -- scripts/run_python_fixture_lens.py tests/scripts/test_python_fixture_harness.py
```

The record commit's message says why each claim landed in the field it did, naming the ones that moved rather than were quoted.

---

## Task 5: Migrate `deps/inventory` and `deps/vulnerabilities`

**Files:**
- Modify: `.agents/skills/deps-audit/checks/inventory.md`, `vulnerabilities.md`
- Modify: `scripts/run_python_fixture_lens.py` (delete three `INVOCATIONS` rows, populate `SUPPLIED`)
- Test: `tests/scripts/test_python_fixture_harness.py`

**Interfaces:**
- Consumes: the argv-less command route from Task 2, the `SUPPLIED` overlay from Task 3.
- Produces: three routed rows with per-partition commands, one carrying `own_runner`.

**`deps/inventory` / `cyclonedx-py`.** One `disposition: runs` command route with no shared `argv` and `argv_by_partition`:

```yaml
    argv_by_partition:
      uv: [uv, export, "--format=cyclonedx1.5", "--frozen"]
      pip: [cyclonedx-py, requirements]
      poetry: [cyclonedx-py, poetry]
      pipenv: [cyclonedx-py, pipenv]
    own_runner: [uv]
```

`pylock` is named nowhere, which is how the route says the record prescribes nothing for a PEP 751 tree. `own_runner: [uv]` because that command is `uv`'s own export rather than the tool the row is keyed on, so a fetch in front of it would report the fetched package's version as the one that answered. A second command route, `disposition: alternative`, `argv: [cyclonedx-py, environment]`, carries the record's claim that reading the installed environment is more accurate where a tree exists and answers nothing on a read-only clone.

The `SUPPLIED` entry is `("deps/inventory", "cyclonedx-py")`, steps `(("uvx", "cyclonedx-py", "requirements", "pylock.toml"),)`, and the note the transcription already carries: the record's first named hole, a candidate this round tests rather than a correction it has made.

The paragraph stating that no route populates a licence field, and that `deps/licenses` is the only source of licence evidence in the family, is a claim about the check and goes in `evidence:`.

**`deps/vulnerabilities` / `pip-audit`.** One `runs` command route, no shared `argv`:

```yaml
    argv_by_partition:
      pip: [pip-audit, "-r", requirements.txt, "--no-deps", "--disable-pip"]
      pylock: [pip-audit, "--locked", "."]
```

`requirements.txt` stays the literal the transcription resolved: moving it into a completion would need a per-partition completion mechanism nothing else wants and would change the provenance of a command that runs today. A second command route, `disposition: superseded`, `argv: [pip-audit, "-r", "<requirements>"]`, is the un-narrowed form the record names and then narrows; the placeholder is safe there because nothing runs a superseded route. The `SUPPLIED` entry is `("deps/vulnerabilities", "pip-audit")` with the two-step uv export-then-audit route and its note.

**`deps/vulnerabilities` / `safety`** stays an offered route prescribing no command: `kind: procedure`, `needs: resolved-tree`, its note carrying both reasons the record gives - the completeness it claims is only ever claimed about an installed environment, and it requires authentication whatever else is true. **Not `disposition: forbidden`**: `_project_tooling` drops a forbidden route's tool, which would delete this row and fail the exact-set guard. The same holds for `osv-scanner`, a standalone binary the record says a one-shot runner cannot supply.

- [ ] **Step 1: Write the failing acceptance test**

```python
def test_the_per_partition_deps_rows_survive_their_records_migration():
    """All five partitions present, the ones the record prescribes nothing for empty.

    `prescribed()` falls back to the shared `argv` when the row carries no
    per-partition map at all, so a row that lost its map would answer these
    assertions with the shared command rather than with nothing - which is why
    the empty `argv` is asserted beside them.
    """
    rows = {(i.check, i.tool): i for i in routed_invocations()}
    inv = rows[("deps/inventory", "cyclonedx-py")]
    assert inv.argv == ()
    assert inv.argv_by_partition == (
        ("uv", ("uv", "export", "--format=cyclonedx1.5", "--frozen")),
        ("pip", ("cyclonedx-py", "requirements")),
        ("poetry", ("cyclonedx-py", "poetry")),
        ("pipenv", ("cyclonedx-py", "pipenv")),
        ("pylock", ()),
    )
    assert inv.own_runner == ("uv",)
    assert inv.supplied("pylock") == (
        ("uvx", "cyclonedx-py", "requirements", "pylock.toml"),
    )
    vuln = rows[("deps/vulnerabilities", "pip-audit")]
    assert vuln.argv == ()
    assert vuln.prescribed("pip") == (
        "pip-audit", "-r", "requirements.txt", "--no-deps", "--disable-pip",
    )
    assert vuln.prescribed("pylock") == ("pip-audit", "--locked", ".")
    assert [p for p in PARTITIONS if not vuln.prescribed(p)] == ["uv", "poetry", "pipenv"]
    assert vuln.supplied("uv")[0][:3] == ("uv", "export", "--frozen")
    assert rows[("deps/vulnerabilities", "safety")].argv == ()
```

- [ ] **Step 2: Run it to see it fail**

- [ ] **Step 3: Migrate the two records**

- [ ] **Step 4: Delete the three `INVOCATIONS` rows and populate `SUPPLIED`**

- [ ] **Step 5: Run the suite and compare against the baseline**

Expected differences on these three rows: `record_quote` emptied, and `forms` per the derivation - `deps/inventory` gains `cyclonedx-py requirements` and `cyclonedx-py pipenv`, which are commands it runs today and declares nowhere, and `deps/vulnerabilities` trades `pip-audit -r <requirements> --no-deps --disable-pip` for the concrete `requirements.txt` spelling. `argv_by_partition`, `own_runner`, `supplied_by_partition`, `supplied_note`, `in_env` and `findings_stream` identical.

- [ ] **Step 6: Commit, records apart from code**

---

## Task 6: Migrate `test/coverage-reach` and `test/mutation`

**Files:**
- Modify: `.agents/skills/test-audit/checks/coverage-reach.md`, `mutation.md`
- Modify: `scripts/run_python_fixture_lens.py` (delete four `INVOCATIONS` rows, add one `COMPLETIONS` entry)

**Interfaces:**
- Consumes: `then` from #66.
- Produces: four routed rows, one carrying a `then`.

These two carry the longest prose in the family. Every measurement in them is a claim to place, not to summarise:

- **`test/coverage-reach`** - the `c8` false clean (96.35% statements and 69.56% branches over three files against the provider's 8.05% and 5.86% over 339, and 0% of 47,306 statements pointed at the source tree with `--all --src`), the provider-install rule and its own-copy constraint, `--coverage.reportOnFailure` defaulting to false, `--check-coverage --branches <n>` being a gate rather than a measurement. The `c8` route is `disposition: forbidden` **around a Vitest command** and the record also says its plain form remains the measurement for a runner whose tests run in the process it wrapped: that is two routes for one tool, separated by `applies_when`, not one route with a hedged note. `c8` is TypeScript-only, so neither affects the python lens.
- **`test/mutation`** - `mutmut run`'s exit code never being a findings signal, the clean-tests baseline failing on module-level state, `npx stryker` resolving a deprecated unscoped 0.x, `@stryker-mutator/core`'s dynamic `typescript` import defeating a one-shot runner, the three package-naming spellings and why `dlx`'s flag order differs. Its `ungranted_note: none` becomes `answers_ungranted: none`.

**Exact row values:**

| row | argv | then | completion | in_env | needs | derived forms |
|---|---|---|---|---|---|---|
| `test/coverage-reach` / `pytest-cov` | `[pytest, --cov-branch, --cov-report=term-missing]` | | `[--cov=<PACKAGE>]` | true | `target-execution` | `pytest --cov-branch --cov-report=term-missing` (runs) |
| `test/coverage-reach` / `coverage.py` | `[coverage, run, -m, pytest]` | `[coverage, report, --show-missing]` | | true | `target-execution` | `coverage run -m pytest` (runs), `coverage report --show-missing` (runs) |
| `test/mutation` / `mutmut` | `[mutmut, run]` | | | true | `target-execution` | `mutmut run` (runs), `mutmut results` (alternative) |
| `test/mutation` / `cosmic-ray` | none (`kind: procedure`) | | | true | `target-execution` | none |

`pytest-cov`'s runs form loses its `<pkg>` tail for the same reason `deps/freshness`'s did. `in_env: true` on the `cosmic-ray` route matters even though it runs nothing: `probe_versions` calls `launcher` for every tool regardless of `argv`, and without it the probe resolves a bare runner with the plugin never installed, on every partition and grant. Carry that reason into the route's note; it is the record's tool and the harness's consequence, and a reader who deletes the flag as decorative reintroduces it.

- [ ] **Step 1: Write the failing acceptance test**

```python
def test_the_coverage_and_mutation_rows_survive_their_records_migration():
    """The `then`'s order is the record's, and the row that runs nothing keeps in_env."""
    rows = {(i.check, i.tool): i for i in routed_invocations()}
    cov = rows[("test/coverage-reach", "coverage.py")]
    assert cov.argv == ("coverage", "run", "-m", "pytest")
    assert cov.then == ("coverage", "report", "--show-missing")
    pcov = rows[("test/coverage-reach", "pytest-cov")]
    assert pcov.argv == ("pytest", "--cov-branch", "--cov-report=term-missing")
    assert pcov.completion == (f"--cov={PACKAGE}",)
    assert rows[("test/mutation", "mutmut")].argv == ("mutmut", "run")
    cosmic = rows[("test/mutation", "cosmic-ray")]
    assert cosmic.argv == ()
    assert cosmic.in_env is True
    for key in (cov, pcov, rows[("test/mutation", "mutmut")]):
        assert key.in_env is True
```

- [ ] **Step 2: Run it to see it fail.**
- [ ] **Step 3: Migrate the two records.**
- [ ] **Step 4: Delete the four rows, add the `COMPLETIONS` entry for `pytest-cov`.**
- [ ] **Step 5: Run the suite and compare against the baseline.** Expected differences: `record_quote` emptied on all four; `forms` losing the `<pkg>` tail on `pytest-cov` and reordered on `coverage.py` (argv first, `then` second, which is the record's order); `note` from the completion or empty.
- [ ] **Step 6: Commit, records apart from code.**

---

## Task 7: Migrate the remaining five `test` records

**Files:**
- Modify: `.agents/skills/test-audit/checks/assertion-strength.md`, `determinism.md`, `isolation.md`, `new-code-coverage.md`, `property-based-gap.md`
- Modify: `scripts/run_python_fixture_lens.py` (delete four `INVOCATIONS` rows, add one `COMPLETIONS` entry)

**Interfaces:**
- Produces: four routed rows; `test/assertion-strength` and `test/new-code-coverage` produce none, which is what they produce today.

Two of these have no python tool and are the reason the `kind` vocabulary exists:

- **`test/assertion-strength`** declares no `tooling` at all and prescribes a reading pass: "a scanner can't do this - a subagent reading test to code pairs can." That is one `lang: any`, `kind: procedure` route with **no tool**, which the loader permits only for `procedure`. It produces no row in any lens, exactly as today.
- **`test/new-code-coverage`** declares `tooling: {any: [diff-cover]}`, so its route is `lang: any` and projects under the literal `any` key, invisible to a `python` lookup precisely as before. Its prose carries the reason the tool needs no tier - it reads a coverage report and a git diff - and the two artifact names to search for, `coverage.xml` and `lcov.info`, where searching for only the first is how the check reports `no-evidence` on a target that published everything it needed. That belongs in the route's note, and the `npx diff-cover` warning - an independent third-party port that runs and prints a plausible number - belongs beside it.

**Exact row values:**

| row | argv | completion | in_env | needs | derived forms |
|---|---|---|---|---|---|
| `test/determinism` / `pytest-randomly` | `[pytest]` | | true | `target-execution` | `pytest` (runs), `pytest --randomly-seed=<n>` (alternative) |
| `test/determinism` / `pytest-rerunfailures` | none (`kind: procedure`) | | true | `target-execution` | none |
| `test/isolation` / `pytest-timeout` | `[pytest, --durations=25]` | `[--timeout=<ISOLATION_TIMEOUT_SECONDS>]` | true | `target-execution` | `pytest --durations=25` (runs) |
| `test/property-based-gap` / `hypothesis` | none (`kind: library`) | | false | none | none |

`pytest-randomly`'s alternative route carries the `<n>` placeholder and nothing runs it. `test/isolation`'s completion keeps the record's own gap: the record prescribes `--durations=25`, which is core pytest and never exercises `pytest-timeout`, the tool the record names - that observation is the round's and stays in the completion's note. `hypothesis` is `kind: library` because the record says it is imported inside the partition's own tests rather than run, and both records' `ungranted_note` prose becomes untiered procedure routes.

- [ ] **Step 1: Write the failing acceptance test**

```python
def test_the_remaining_test_rows_survive_their_records_migration():
    """Four rows, and the two records that produce none still produce none."""
    routed = routed_invocations()
    rows = {(i.check, i.tool): i for i in routed}
    assert rows[("test/determinism", "pytest-randomly")].argv == ("pytest",)
    rerun = rows[("test/determinism", "pytest-rerunfailures")]
    assert rerun.argv == ()
    assert rerun.in_env is True
    iso = rows[("test/isolation", "pytest-timeout")]
    assert iso.argv == ("pytest", "--durations=25")
    assert iso.completion == (f"--timeout={ISOLATION_TIMEOUT_SECONDS}",)
    assert rows[("test/property-based-gap", "hypothesis")].argv == ()
    assert not {i.check for i in routed} & {
        "test/assertion-strength",
        "test/new-code-coverage",
    }
```

- [ ] **Step 2: Run it to see it fail.**
- [ ] **Step 3: Migrate the five records.**
- [ ] **Step 4: Delete the four rows, add the `COMPLETIONS` entry for `pytest-timeout`.**
- [ ] **Step 5: Run the suite and compare against the baseline.**
- [ ] **Step 6: Commit, records apart from code.**

---

## Task 8: Hold the whole result against the baseline, and run the fixtures

**Files:**
- Modify: `tests/scripts/test_python_fixture_harness.py` (the scope assertions, and any property this migration left without a subject)
- Modify: `CLAUDE.md` if the schema description needs it (prompt commit, on its own)

- [ ] **Step 1: Assert what `INVOCATIONS` now holds**

```python
def test_the_transcription_holds_only_the_domains_that_have_not_migrated():
    """15 rows over 5 checks, all `docs` or `security`.

    Named rather than counted loosely: a row left behind for a migrated record
    is a second prescription for a check whose record already carries one, and
    the enumeration would run both.
    """
    assert {i.check for i in INVOCATIONS} == {
        "docs/docstring-coverage",
        "security/crypto",
        "security/dangerous-calls",
        "security/injection",
        "security/unsafe-io",
    }
    assert len(INVOCATIONS) == 15
```

- [ ] **Step 2: Run the full baseline comparison and read every line**

Every one of the 50 rows accounted for: 19 `arch` and 15 `docs`/`security` identical field for field, 16 differing only in `record_quote`, `forms` and `note` as Tasks 4-7 named. Write the comparison output to the plan's workspace and cite it in the PR.

- [ ] **Step 3: Prove every narrowed property still has a subject**

For each property scoped by `PROSE_FALLBACK_CHECKS` or reading `INVOCATIONS` directly, confirm it iterates something and that a mutation inside its loop fails it. A property that passes over an empty population is the failure this whole epic keeps producing. Where a property's docstring justifies its narrow scope with a premise this migration falsified, repair the premise or widen the property and prove the widening non-vacuous - each one on its own evidence, not as a batch.

- [ ] **Step 4: Check `_fallback_paragraphs`' callers**

It raises for a record with no `## Tooling fallback` section. Confirm every caller reaches it only for a record that still has one, and that the confirmation is a guard rather than a reading.

- [ ] **Step 5: Live fixture run**

```bash
caffeinate uv run python scripts/run_python_fixture_lens.py <partition> --grant target-execution --only-check deps/hygiene
caffeinate uv run python scripts/run_python_fixture_lens.py <partition> --grant target-execution --only-check test/isolation
```

Read the flag names off the script's own `--help` first. Build the fixture trees if they are absent (`uv run python scripts/build_python_fixtures.py --all`); they are gitignored and live in the main checkout. A route that parses is not a route that runs, and this is the only step in the plan that answers that.

- [ ] **Step 6: Re-render and run the gates**

```bash
uv run python scripts/render_handbook_traceability.py --check
uv run python scripts/render_python_fixture_expectations.py --check
caffeinate uv run pytest tests/ -q
uv run ruff check . && uv run ruff format --check .
```

The expectations renderer reads `python_fixture_spec.py` and not the lens, so it should re-render byte-identical; report it as a gate that ran rather than as evidence about the migration.

- [ ] **Step 7: Stale-prose pass**

Dispatch to a subagent that has not seen the implementation, given the worktree's absolute root and required to confirm `git rev-parse --show-toplevel` and `git rev-parse HEAD` before reading. Scope it by blast radius, not by the diff: `argv_by_manager` was renamed, `_forms_for` changed signature and meaning, `SUPPLIED` is new, 16 rows and 13 `## Tooling fallback` sections are gone, and `COMPLETIONS` doubled. Grep for each name and read the prose around every hit, including `CLAUDE.md`, `docs/audit/sweep-obligations.md` and every check record that mentions a sibling's fallback section.

- [ ] **Step 8: Update `CLAUDE.md` and commit it alone**

The route-field enumeration names `argv_by_manager` (Task 1) and describes a command route as always carrying an argv (Task 2). Both need the new statement, and the paragraph must stay one source line.
