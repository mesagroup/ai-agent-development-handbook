# The routes schema and the arch pilot - implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A check record declares what it runs as structured data in frontmatter, validated by the loader, proven against the eleven `arch` records.

**Architecture:** `audit_checks.py` gains a `Route` dataclass and a `routes:` frontmatter field that replaces `tooling:`, `needs:` and `ungranted_note:` on a migrated record. Both schemas are accepted while the migration runs. A migrated record derives `tooling` and `needs` from its routes, so the nine existing consumer sites in the lens and the two fixture test modules keep working untouched.

**Tech Stack:** Python 3, `dataclasses`, `pyyaml`, pytest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-18-routes-schema-arch-pilot-design.md`. It governs; where this plan and the spec disagree, stop and ask.
- `ROUTE_KINDS = ("command", "library", "procedure", "subject")`.
- `DISPOSITIONS = ("runs", "alternative", "superseded", "forbidden")`.
- `ROUTE_LANGS = ("python", "typescript", "any", "none")`.
- `FINDINGS_STREAMS = ("stdout", "stderr")`.
- Grant tiers reuse the existing `NEEDS_TIERS = ("resolved-tree", "target-execution")`.
- The ungranted sentinel reuses the existing `UNGRANTED_NONE = "none"`, under the new key `answers_ungranted`.
- No bare `except Exception: pass`. Every exception is reported to the caller with type and message, logged, or re-raised.
- `load_checks` collects problems into the error list rather than raising. Every new validation follows that.
- Never assert a count you did not compute, in code comments, docstrings or commit messages.
- Markdown is never hard-wrapped: one paragraph is one source line. Never reflow a line you did not change.
- No em-dash (U+2014) anywhere under `docs/`. Use ` - `.
- Record files are prompts. A commit touching one says WHY it now reads the way it does, and record commits stay separate from code commits.
- Never write into `fixtures/python/<partition>`.
- Run `uv run ruff check .` and `uv run ruff format --check .` before every commit. Never pass `docs/` to ruff explicitly - `extend-exclude` is load-bearing.
- Commit with an explicit pathspec: `git commit -F - -- <paths>`. Never `git add -A`, `git add .`, `git commit -a`, `git stash`, `git checkout -- .`, `git clean`.
- `Refs #59` in every commit message.

## File Structure

- `scripts/audit_checks.py` - the loader. Gains `Route`, the route constants, `_load_routes`, the derived-projection helpers, and the routes branch of `_load_one`. This is the only production file the pilot changes.
- `tests/scripts/test_audit_checks.py` - one test per validation rule, plus the legacy-set guard.
- `tests/scripts/test_python_fixture_harness.py` - gains the oracle test binding arch's migrated Python routes to `INVOCATIONS`.
- `.agents/skills/arch-audit/checks/*.md` - the eleven records, migrated. Frontmatter only; prose is not rewritten in this pilot except where it duplicates a route.
- `CLAUDE.md`, `scripts/audit_checks.py`'s module docstring, `.agents/skills/audit-core/SKILL.md` - the prose describing the old schema.

---

### Task 1: The Route dataclass and its field validation

**Files:**
- Modify: `scripts/audit_checks.py`
- Test: `tests/scripts/test_audit_checks.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `Route`, `ROUTE_KINDS`, `DISPOSITIONS`, `ROUTE_LANGS`, `FINDINGS_STREAMS`, `ROUTE_FIELDS`, and `_load_routes(raw, where) -> tuple[tuple[Route, ...], list[str]]`. Task 2 consumes `Route.needs`, `Route.kind` and `Route.lang`. Task 6 consumes `Route.argv`, `Route.argv_by_manager`, `Route.disposition` and `Route.findings_stream`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/scripts/test_audit_checks.py`. `_write` is the existing helper that writes a record into `tmp_path`; follow the file's existing calling convention for it.

```python
def test_a_route_carries_its_kind_and_command(tmp_path):
    check = _one_route_record(tmp_path, "kind: command\n    tool: pydeps\n    argv: [pydeps, --show-cycles]")
    route = check.routes[0]
    assert (route.kind, route.tool, route.argv) == ("command", "pydeps", ("pydeps", "--show-cycles"))
    assert route.disposition == "runs"
    assert route.needs is None
    assert route.findings_stream == "stdout"


def test_a_package_defaults_to_the_tool_name(tmp_path):
    check = _one_route_record(tmp_path, "kind: command\n    tool: pydeps\n    argv: [pydeps]")
    assert check.routes[0].package == "pydeps"


def test_a_package_is_written_only_where_it_differs(tmp_path):
    check = _one_route_record(
        tmp_path,
        "kind: command\n    tool: import-linter\n    package: import-linter\n    argv: [lint-imports]",
    )
    assert (check.routes[0].package, check.routes[0].argv) == ("import-linter", ("lint-imports",))


@pytest.mark.parametrize("kind", ["library", "procedure", "subject"])
def test_an_argv_on_a_non_command_kind_is_rejected(tmp_path, kind):
    errors = _errors_for_route(tmp_path, f"kind: {kind}\n    tool: grimp\n    argv: [grimp]")
    assert any("argv" in e and kind in e for e in errors), errors


def test_a_command_route_must_carry_an_argv(tmp_path):
    errors = _errors_for_route(tmp_path, "kind: command\n    tool: pydeps")
    assert any("argv" in e for e in errors), errors


@pytest.mark.parametrize("disposition", ["alternative", "superseded", "forbidden"])
def test_a_non_running_disposition_needs_a_command(tmp_path, disposition):
    errors = _errors_for_route(
        tmp_path, f"kind: library\n    tool: grimp\n    disposition: {disposition}"
    )
    assert any("disposition" in e for e in errors), errors


def test_a_procedure_route_may_name_no_tool(tmp_path):
    check = _one_route_record(tmp_path, "kind: procedure\n    note: walk the edge set")
    assert check.routes[0].tool is None


@pytest.mark.parametrize("kind", ["command", "library", "subject"])
def test_every_other_kind_must_name_its_tool(tmp_path, kind):
    body = f"kind: {kind}" + ("\n    argv: [x]" if kind == "command" else "")
    errors = _errors_for_route(tmp_path, body)
    assert any("tool" in e for e in errors), errors


@pytest.mark.parametrize(
    "field,value",
    [("kind", "gadget"), ("lang", "cobol"), ("disposition", "maybe"),
     ("findings_stream", "syslog"), ("needs", "a-network")],
)
def test_a_route_field_must_name_a_known_value(tmp_path, field, value):
    errors = _errors_for_route(
        tmp_path, f"kind: command\n    tool: t\n    argv: [t]\n    {field}: {value}"
    )
    assert any(field in e for e in errors), errors


def test_an_unknown_route_key_is_rejected(tmp_path):
    errors = _errors_for_route(tmp_path, "kind: command\n    tool: t\n    argv: [t]\n    runner: npx")
    assert any("runner" in e for e in errors), errors


def test_a_record_may_not_carry_both_schemas(tmp_path):
    errors = _errors_for_both_schemas(tmp_path)
    assert any("routes" in e and "tooling" in e for e in errors), errors


def test_argv_by_manager_maps_a_manager_to_a_command(tmp_path):
    check = _one_route_record(
        tmp_path,
        "kind: command\n    tool: dependency-cruiser\n    argv: [depcruise]\n"
        "    argv_by_manager:\n      pnpm: [pnpm, dlx, depcruise]",
    )
    assert check.routes[0].argv_by_manager == {"pnpm": ("pnpm", "dlx", "depcruise")}


def test_argv_by_manager_needs_a_command_kind(tmp_path):
    errors = _errors_for_route(
        tmp_path, "kind: library\n    tool: grimp\n    argv_by_manager:\n      pnpm: [x]"
    )
    assert any("argv_by_manager" in e for e in errors), errors
```

Add the three helpers beside them, following the file's existing `_write`-based idiom: `_one_route_record(tmp_path, route_body)` writes a record whose frontmatter carries one route built from `route_body` and returns the loaded `Check`, asserting the load produced no errors; `_errors_for_route(tmp_path, route_body)` does the same and returns the error list instead; `_errors_for_both_schemas(tmp_path)` writes a record carrying both `routes:` and `tooling:`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONDONTWRITEBYTECODE=1 caffeinate uv run pytest tests/scripts/test_audit_checks.py -q`
Expected: FAIL - `Check` has no attribute `routes`.

- [ ] **Step 3: Add the constants and the dataclass**

In `scripts/audit_checks.py`, beside the existing `NEEDS_TIERS` and `LOCALITIES`:

```python
ROUTE_KINDS = ("command", "library", "procedure", "subject")
DISPOSITIONS = ("runs", "alternative", "superseded", "forbidden")
ROUTE_LANGS = ("python", "typescript", "any", "none")
FINDINGS_STREAMS = ("stdout", "stderr")
ROUTE_FIELDS = frozenset(
    {
        "lang", "kind", "tool", "package", "argv", "argv_by_manager",
        "disposition", "needs", "in_env", "findings_stream",
        "applies_when", "alone_insufficient", "note",
    }
)
```

Add `"routes"` and `"answers_ungranted"` to the existing `FIELDS` frozenset.

```python
@dataclass(frozen=True)
class Route:
    """One way of answering one check in one language.

    Three axes the record's prose used to write as a single sentence. `kind`
    says what the thing is, `disposition` says whether the harness takes this
    route, and `applies_when` says what the target must carry for the route to
    be available at all. Reading the eleven arch records is what separated
    them: fourteen of its nineteen invocations prescribe no command, for four
    different reasons that one list of tool names cannot tell apart.
    """

    lang: str
    kind: str
    tool: str | None
    package: str | None
    argv: tuple[str, ...]
    argv_by_manager: dict[str, tuple[str, ...]]
    disposition: str
    needs: str | None
    in_env: bool
    findings_stream: str
    applies_when: str | None
    alone_insufficient: str | None
    note: str | None
```

- [ ] **Step 4: Write `_load_routes`**

One function returning `(routes, errors)`, collecting every problem rather than stopping at the first, matching `_load_one`'s existing contract. It validates, in this order: the value is a list of mappings; every key is in `ROUTE_FIELDS`; `lang`, `kind`, `disposition`, `findings_stream` and `needs` each name a known value; `tool` is present unless `kind` is `procedure`; `package` defaults to `tool`; `argv` and `argv_by_manager` are present only where `kind` is `command`, and `argv` is required there and non-empty; a `disposition` other than `runs` appears only where `kind` is `command`.

Each message names the record, the route's index, and the field, so a failure on a twelve-route record says which route.

- [ ] **Step 5: Wire it into `_load_one`**

Accept `routes:` as an alternative to `tooling:`/`needs:`/`ungranted_note:`. A record carrying both is an error naming both keys - two spellings of one fact is the defect this schema removes, so it is rejected rather than merged. Add `routes: tuple[Route, ...]` to `Check`, defaulting to `()` for a legacy record.

- [ ] **Step 6: Derive `tooling` and `needs` for a migrated record**

The nine sites in `run_python_fixture_lens.py`, `test_python_fixture_harness.py` and `test_python_fixture_spec.py` read `check.tooling` and `check.needs`. A migrated record populates both by projection from its routes, so none of them changes in this pilot:

- `tooling[lang]` is the tools of that language's routes, in route order, duplicates collapsed, skipping routes that name no tool. A `lang: any` route contributes to every language the record otherwise names, matching what `tooling: {any: [...]}` meant.
- `needs[tier]` is the tools of the routes carrying that tier.

Write the projection as one function with a docstring saying it is a view rather than a second source, and that a route is the only place a tool is declared.

- [ ] **Step 7: Run the tests**

Run: `PYTHONDONTWRITEBYTECODE=1 caffeinate uv run pytest tests/scripts/test_audit_checks.py -q`
Expected: PASS.

- [ ] **Step 8: Run the full suite and the gates**

Run: `PYTHONDONTWRITEBYTECODE=1 caffeinate uv run pytest tests/ -q && caffeinate uv run ruff check . && caffeinate uv run ruff format --check . && caffeinate uv run python scripts/render_handbook_traceability.py --check && caffeinate uv run python scripts/render_python_fixture_expectations.py --check`
Expected: all pass, both gates exit 0. No record has been migrated yet, so every existing test still exercises the legacy branch.

- [ ] **Step 9: Commit**

```bash
git add scripts/audit_checks.py tests/scripts/test_audit_checks.py
git commit -F - -- scripts/audit_checks.py tests/scripts/test_audit_checks.py
```

Message body says why the three axes are separate fields and why a record carrying both schemas is rejected rather than merged. `Refs #59`.

---

### Task 2: The ungranted rule, rebuilt on routes

**Files:**
- Modify: `scripts/audit_checks.py`
- Test: `tests/scripts/test_audit_checks.py`

**Interfaces:**
- Consumes: `Route`, `ROUTE_KINDS`, `UNGRANTED_NONE` from Task 1.
- Produces: `_routes_answering_ungranted(routes) -> dict[str, tuple[Route, ...]]` and the `answers_ungranted` validation. Nothing later consumes them.

`ungranted_note` prose becomes a structural check. Where every route in a language carries a `needs` tier, the record must also carry a route in that language that answers without one, or the explicit sentinel.

**A `kind: subject` route does not answer.** `arch/complexity-gate` names `ruff`, `radon` and `xenon` as "the gate's subject rather than its instrument" - running one answers `arch/complexity`, not the gate. Counting a subject route as an answer would silence exactly the records the rule exists for.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_language_whose_every_route_is_tiered_must_say_what_answers(tmp_path):
    errors = _errors_for_routes(
        tmp_path,
        [{"lang": "python", "kind": "command", "tool": "t", "argv": ["t"], "needs": "resolved-tree"}],
    )
    assert any("answers_ungranted" in e and "python" in e for e in errors), errors


def test_an_untiered_route_in_the_same_language_answers_it(tmp_path):
    check = _routes_record(
        tmp_path,
        [
            {"lang": "python", "kind": "command", "tool": "t", "argv": ["t"], "needs": "resolved-tree"},
            {"lang": "python", "kind": "procedure", "note": "read the config"},
        ],
    )
    assert check.answers_ungranted is None


def test_a_subject_route_does_not_answer_the_check(tmp_path):
    errors = _errors_for_routes(
        tmp_path,
        [
            {"lang": "python", "kind": "command", "tool": "t", "argv": ["t"], "needs": "target-execution"},
            {"lang": "python", "kind": "subject", "tool": "ruff"},
        ],
    )
    assert any("answers_ungranted" in e for e in errors), errors


def test_the_sentinel_satisfies_the_rule(tmp_path):
    check = _routes_record(
        tmp_path,
        [{"lang": "python", "kind": "command", "tool": "t", "argv": ["t"], "needs": "resolved-tree"}],
        answers_ungranted="none",
    )
    assert check.answers_ungranted == "none"


def test_the_sentinel_is_vacuous_where_an_untiered_route_exists(tmp_path):
    errors = _errors_for_routes(
        tmp_path,
        [{"lang": "python", "kind": "command", "tool": "t", "argv": ["t"]}],
        answers_ungranted="none",
    )
    assert any("answers_ungranted" in e for e in errors), errors


@pytest.mark.parametrize("spelling", ["None", "NONE", "null", ""])
def test_a_miscased_route_sentinel_is_rejected_by_name(tmp_path, spelling):
    errors = _errors_for_routes(
        tmp_path,
        [{"lang": "python", "kind": "command", "tool": "t", "argv": ["t"], "needs": "resolved-tree"}],
        answers_ungranted=spelling,
    )
    assert any("answers_ungranted" in e for e in errors), errors


def test_a_language_with_no_routes_is_not_silenced(tmp_path):
    check = _routes_record(
        tmp_path, [{"lang": "python", "kind": "procedure", "note": "read it"}]
    )
    assert check.answers_ungranted is None
```

The last one mirrors the existing `test_a_language_with_no_tools_is_not_fully_tiered`: a language the record says nothing about has made no claim about grants, and `all()` over an empty list must not silence it.

- [ ] **Step 2: Run to verify they fail**

Run: `PYTHONDONTWRITEBYTECODE=1 caffeinate uv run pytest tests/scripts/test_audit_checks.py -q -k ungranted`
Expected: FAIL.

- [ ] **Step 3: Implement**

Add `answers_ungranted: str | None` to `Check`. Reuse the existing sentinel rejection for `None`/`NONE`/`null`/blank by name, with the same reasoning the current one carries - YAML turns the first two into ordinary strings that read as a fallback claim and the last two into nothing at all.

A language is silenced when it has at least one route, every route carrying a `needs` tier, and no route of a kind that answers. Kinds that answer are `command`, `library` and `procedure`; `subject` does not.

- [ ] **Step 4: Run the tests, then the full suite and both gates**

Same commands as Task 1 Step 8. Expected: PASS.

- [ ] **Step 5: Commit**

Message says that `ungranted_note` prose has become a structural claim, that a subject route does not answer, and why the sentinel stays explicit. `Refs #59`.

---

### Task 3: The legacy set, asserted and shrinking

**Files:**
- Test: `tests/scripts/test_audit_checks.py`

**Interfaces:**
- Consumes: `Check.routes` from Task 1.
- Produces: `LEGACY_TOOLING_RECORDS`, consumed by nothing; Task 5 empties its arch entries.

- [ ] **Step 1: Write the test**

```python
LEGACY_TOOLING_RECORDS = frozenset()  # filled in Step 2 from the tree


def test_the_records_still_on_the_old_schema_are_the_ones_named():
    """A record migrated without updating this set fails, and so does the reverse.

    The migration runs domain by domain, so both schemas load for as long as it
    takes. That is a decision rather than a tolerance: an unmigrated record has
    to be named somewhere, or the loader accepting it reads exactly like the
    loader having nothing left to accept.
    """
    checks, errors = load_checks(SKILLS_DIR)
    assert not errors, errors
    legacy = {cid for cid, check in checks.items() if not check.routes}
    assert legacy == LEGACY_TOOLING_RECORDS
    assert legacy, (
        "no record is on the old schema, so this set is dead - delete it and "
        "the dual-schema branch of the loader with it"
    )
```

- [ ] **Step 2: Fill the set**

Compute it, do not type it by hand:

```bash
caffeinate uv run python -c "
import sys; sys.path.insert(0, 'scripts')
from audit_checks import SKILLS_DIR, load_checks
c, e = load_checks(SKILLS_DIR); assert not e, e
print(sorted(c))
"
```

At this point no record is migrated, so the set is every record in the tree.

- [ ] **Step 3: Run it**

Run: `PYTHONDONTWRITEBYTECODE=1 caffeinate uv run pytest tests/scripts/test_audit_checks.py -q -k legacy`
Expected: PASS.

- [ ] **Step 4: Commit** - `Refs #59`.

---

### Task 4: Migrate `arch/cycles`, the shape test

**Files:**
- Modify: `.agents/skills/arch-audit/checks/cycles.md`
- Modify: `tests/scripts/test_audit_checks.py` (remove its id from the legacy set)

**Interfaces:**
- Consumes: the schema from Tasks 1-3.
- Produces: the first migrated record. Task 5 follows its shape; Task 6's oracle covers its Python routes.

`arch/cycles` goes first because it carries four of the hard cases at once: a library (`grimp`), a command conditional on a target artifact whose binary is not its package name (`import-linter` providing `lint-imports`, applying only where a `.importlinter` contract exists), a superseded form (`pydeps --show-cycles`, which the record says has no textual output channel at all), and a `resolved-tree` tier on one Python tool where the others carry none.

- [ ] **Step 1: Read the record end to end**

Read `.agents/skills/arch-audit/checks/cycles.md` in full, and the three `arch/cycles` entries in `INVOCATIONS` in `scripts/run_python_fixture_lens.py`. The frontmatter's new `routes:` must say what the prose says. Where they disagree, the prose is the source and the disagreement is a finding to report, not to smooth over.

- [ ] **Step 2: Write the frontmatter**

```yaml
routes:
  - lang: python
    kind: command
    tool: pydeps
    argv: [pydeps, --show-cycles, --show-dot]
    needs: resolved-tree
    note: >-
      Reads import opcodes from compiled bytecode rather than executing the target, so it sees only modules the import machinery can find: an uninstalled dependency drops out of the graph and a cycle running through it goes unreported rather than erroring.
  - lang: python
    kind: command
    tool: pydeps
    argv: [pydeps, --show-cycles]
    disposition: superseded
    needs: resolved-tree
    note: >-
      Superseded by the route above: `--show-cycles` alone has no textual output channel at all.
  - lang: python
    kind: command
    tool: import-linter
    argv: [lint-imports]
    applies_when: >-
      The partition carries a `.importlinter` contract. The contract is the input, so writing one to make the tool run would manufacture the configuration whose absence is itself the finding.
  - lang: python
    kind: library
    tool: grimp
    note: >-
      Cycle detection runs over a graph a scripted pass builds, rather than through a command.
```

Then the TypeScript routes for `madge` and `dependency-cruiser`, read from that record's own TypeScript paragraph. Do not copy `arch/coupling`'s runner spellings into this record unless this record's prose carries them.

Delete `tooling:` and `needs:` from the record. Leave the prose below untouched in this task.

- [ ] **Step 3: Verify the projection reproduces the old values**

```bash
caffeinate uv run python -c "
import sys; sys.path.insert(0, 'scripts')
from audit_checks import SKILLS_DIR, load_checks
c, e = load_checks(SKILLS_DIR); assert not e, e
r = c['arch/cycles']
print(r.tooling); print(r.needs)
"
```

Expected: `tooling` reproduces `{'python': ('import-linter', 'pydeps', 'grimp'), 'typescript': ('madge', 'dependency-cruiser')}` as a set per language, and `needs` reproduces `{'resolved-tree': (...)}` containing `pydeps` and `dependency-cruiser`. Tool order within a language may differ from the old list; if any existing test depends on that order, that is a finding to report before changing the test.

- [ ] **Step 4: Remove `arch/cycles` from `LEGACY_TOOLING_RECORDS`, run the full suite and both gates**

Expected: PASS. A failure here is the pilot's first real signal - report what the schema could not express rather than working around it.

- [ ] **Step 5: Commit the record and the test separately**

Two commits. The record commit explains why the record now declares its routes: what each of the four shapes is, and that the harness previously carried this knowledge as hand-written notes. `Refs #59`.

---

### Task 5: Migrate the remaining ten arch records

**Files:**
- Modify: the other ten records under `.agents/skills/arch-audit/checks/`
- Modify: `tests/scripts/test_audit_checks.py`

**Interfaces:**
- Consumes: the shape Task 4 established.
- Produces: an all-migrated `arch`; Task 6's oracle covers every arch Python route.

- [ ] **Step 1: Migrate them one at a time, in this order**

`complexity`, `complexity-gate`, `coupling`, `dead-code`, `hidden-coupling`, `layering`, `martin-metrics`, `over-abstraction`, `over-decomposition`, `size`.

Four carry a shape Task 4 did not:

- **`complexity-gate`** - `ruff`, `radon` and `xenon` are `kind: subject`. Its `ungranted_note` becomes a `kind: procedure` route for reading the linter configuration and the CI workflow files. Its `needs: target-execution` on `eslint` goes: a subject is not tiered.
- **`complexity`** - its `ungranted_note` becomes two routes: a `kind: procedure` branch-point count, and a second `eslint` route under an audit-owned config carrying no tier, beside the tiered one that loads the target's own config. That second route is #31 in the flesh; if the schema cannot hold both, stop and report.
- **`coupling`** - three `argv_by_manager` spellings for `dependency-cruiser`, and a `disposition: forbidden` route for the bare `dlx depcruise` that resolves to an npm dependency-confusion placeholder exiting 0 having done nothing. `pydeps` is `disposition: alternative`: the record offers it as a visual and says the counts are the evidence. `madge` carries `alone_insufficient` for the `tsconfig` `extends` case the record measures.
- **`size`** - declares no Python tooling today, so it has no oracle. Migrate it from its prose alone and say so in the commit.

- [ ] **Step 2: After each record, run the suite and remove that id from the legacy set**

Run: `PYTHONDONTWRITEBYTECODE=1 caffeinate uv run pytest tests/ -q`

- [ ] **Step 3: Run both gates and the linters**

- [ ] **Step 4: Commit each record separately**

Each message says what that record's routes now declare that its prose alone used to carry. `Refs #59`.

---

### Task 6: The oracle - migrated routes agree with the verified table

**Files:**
- Modify: `tests/scripts/test_python_fixture_harness.py`

**Interfaces:**
- Consumes: `Check.routes` and every migrated arch record.
- Produces: nothing.

`INVOCATIONS` was verified through #53 and #55 and re-verified by mutation, so it is the only ground truth available for the migration itself. This test catches a transcription error introduced while migrating.

- [ ] **Step 1: Write the test**

```python
def test_a_migrated_records_routes_agree_with_the_verified_table():
    """The migration's only oracle, and it covers one language.

    `INVOCATIONS` transcribes what each record prescribes and was held against
    the records themselves through #53 and #55, so a route that disagrees with
    it is a migration error rather than a disagreement between two opinions.

    Python only. The TypeScript routes are authored from documentation and one
    smoke run, so nothing here holds them - which is the claim epic #44 exists
    to make good, and is why this test's name says `verified table` rather than
    `the records`.

    Compared per (check, tool, argv) rather than per tool: a record may declare
    the same tool twice with different commands, which is what a superseded
    form is, and a comparison keyed on the tool alone would silently hold only
    one of them.
    """
    checks, errors = load_checks(SKILLS_DIR)
    assert not errors, errors
    migrated = {cid: c for cid, c in checks.items() if c.routes and cid.startswith("arch/")}
    assert migrated, "no arch record is migrated, so this test holds nothing"
    table = {
        (inv.check, inv.tool, inv.argv): inv
        for inv in INVOCATIONS
        if inv.check in migrated and inv.argv
    }
    for cid, check in sorted(migrated.items()):
        for route in check.routes:
            if route.lang != "python" or route.kind != "command":
                continue
            inv = table.get((cid, route.tool, route.argv))
            assert inv is not None, (
                f"{cid}: route {route.tool} {' '.join(route.argv)} is in no verified "
                "entry - either the migration invented it or the table is stale"
            )
            assert route.findings_stream == inv.findings_stream, (cid, route.tool)
    for (cid, tool, argv) in sorted(table):
        assert any(
            r.lang == "python" and r.kind == "command" and r.tool == tool and r.argv == argv
            for r in migrated[cid].routes
        ), f"{cid}: the table prescribes {tool} {' '.join(argv)} and no route declares it"
```

- [ ] **Step 2: Run it**

Run: `PYTHONDONTWRITEBYTECODE=1 caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q -k migrated`
Expected: PASS. A failure names the exact route or table entry that disagrees; fix the record, not the test, unless the table itself is wrong - in which case stop and report, because the table is the verified side.

- [ ] **Step 3: Full suite, both gates, commit** - `Refs #59`.

---

### Task 7: The prose the schema invalidated

**Files:**
- Modify: `CLAUDE.md`, `scripts/audit_checks.py` (module docstring), `.agents/skills/audit-core/SKILL.md`
- Check: `docs/audit/sweep-obligations.md`, `tests/test_sweep_obligations.py`

**Interfaces:**
- Consumes: everything above.
- Produces: nothing.

- [ ] **Step 1: Sweep by blast radius, not by the diff**

Three passages document the old schema as current and are load-bearing for anyone writing a record:

- `scripts/audit_checks.py`'s module docstring - the frontmatter field table, and the paragraph beginning "A `tooling` value is a list of names, not of invocations", which states the decision this pilot reverses. It says the record's `## Tooling fallback` is where the kind and the precedence are stated; `kind` is now a field.
- `CLAUDE.md`'s "Check records" section - the field list, the `needs` second-axis paragraph, the `ungranted_note` third-claim paragraph, and the `tooling`-list three-kinds paragraph.
- `.agents/skills/audit-core/SKILL.md` - whatever it tells an agent about reading `tooling:` and `needs:`.

Then grep for `ungranted_note`, `tooling:` and `needs:` across the repository and read every hit, including test docstrings.

- [ ] **Step 2: Editing `audit-core/SKILL.md` means checking `docs/audit/sweep-obligations.md`**

That file is hand-maintained, one row per `audit-core` obligation. `tests/test_sweep_obligations.py` catches a row whose anchor no longer occurs exactly once and a quotation no longer verbatim, but cannot judge whether a disposition is still true. If an edit moves an anchor, update the row and read the surrounding obligation.

- [ ] **Step 3: Say what is true now, and keep the limits**

Describe the schema as it is. Do not write "previously", "this used to" or "we changed" into `CLAUDE.md` or the skill - the reason belongs in the commit message and on #59. The reversal of the names-not-invocations decision belongs in the commit body, not in the docstring that now describes routes.

- [ ] **Step 4: Full suite, both gates, linters**

- [ ] **Step 5: Commit**

Prose about the code, separate from the skill prompt. Two commits if `audit-core/SKILL.md` moves, since a skill is a prompt and its commit says why. `Refs #59`.

---

## What execution corrected in this plan

Recorded rather than edited away. A plan is the decision as it was taken, and five of its instructions turned out to be wrong in ways worth keeping visible - four of them were caught by an implementer refusing to transcribe them, which is the behaviour this repository wants and would lose if the record were tidied.

- **Task 1 Step 6, the `lang: any` projection.** The plan said an `any` route contributes to every language the record otherwise names. It must project under the literal `"any"` key instead. Twelve records carry `tooling: {any: [...]}`, `arch/size` among them, and every consumer reads `tooling.get("python")`, so fanning out would hand records python invocations they do not have.
- **Task 4 Step 2, the `import-linter` sketch.** It showed `argv: [lint-imports]`. The record prescribes no command line for that tool, and `lint-imports` appears in no check record at all. Writing it would have invented a prescription and then declared it verified.
- **Task 5's two-commit split.** Committing a record and its legacy-set line separately leaves the first commit failing its own suite. One commit per record, including that line.
- **Task 5, dropping `arch/complexity-gate`'s tier.** The plan said a subject route is not tiered. `eslint` is `target-execution` on seven records, so dropping it on one makes that record claim eslint answers from a read-only clone; and exactly the number of records the classification floor requires carry `needs`, so dropping one fails that guard too. `needs` and `kind` are independent axes.
- **Task 6's oracle comparison.** Keying on `inv.argv` alone misses every non-`runs` route, because the table carries those in `forms` as `(form, disposition)` pairs. The plan's test would have raised on a correct migration, and the tempting fix - deleting the superseded route - is the migration losing content to satisfy its own guard.

One statement of the silencing rule in Task 2 is also imprecise as written: a language is silenced when it has at least one answering-kind, non-`forbidden` route and none of them untiered. Taken literally, the plan's wording makes a subject-only language silenced, which is the opposite of what was built and of what `arch/complexity-gate` needs.

## Final verification

- [ ] `PYTHONDONTWRITEBYTECODE=1 caffeinate uv run pytest tests/ -q`
- [ ] `caffeinate uv run ruff check . && caffeinate uv run ruff format --check .`
- [ ] `caffeinate uv run python scripts/render_handbook_traceability.py --check`
- [ ] `caffeinate uv run python scripts/render_python_fixture_expectations.py --check`
- [ ] `caffeinate uv run python -c "import sys; sys.path.insert(0, 'scripts'); from audit_checks import SKILLS_DIR, load_checks; c, e = load_checks(SKILLS_DIR); print(len(c), e)"` - 77 records, no errors
- [ ] `git status --short` empty
- [ ] Report on #59 what the pilot forced the schema to change, and anything it could not express
