"""Tests for scripts/audit_checks.py (lidia-tech/lidia-agents#559)."""

import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = REPO_ROOT / "scripts" / "audit_checks.py"

_spec = importlib.util.spec_from_file_location("audit_checks", _SCRIPT)
assert _spec is not None and _spec.loader is not None
ac = importlib.util.module_from_spec(_spec)
sys.modules["audit_checks"] = ac
_spec.loader.exec_module(ac)


GOOD = """---
id: arch/layering
domain: arch
locality: local
handbook:
  - codebase-structure/point-every-dependency-toward-the-core-and-never-cycle-a
tooling:
  python: [import-linter, tach]
  typescript: [dependency-cruiser]
---

# Layering / dependency-rule conformance

Every import that crosses a tier boundary the wrong way.

## Severity

**Critical** - an import that violates a documented dependency rule.
"""

UNCITED = """---
id: arch/hidden-coupling
domain: arch
locality: global
handbook: []
handbook_note: The handbook's decay list names no equivalent signal.
optin: true
---

# Hidden coupling / implicit dependencies

Coupling that does not travel through an import.
"""


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_loads_a_well_formed_record(tmp_path):
    _write(tmp_path, "arch-audit/checks/layering.md", GOOD)
    checks, errors = ac.load_checks(tmp_path)
    assert errors == []
    check = checks["arch/layering"]
    assert check.domain == "arch"
    assert check.locality == "local"
    assert check.title == "Layering / dependency-rule conformance"
    assert check.handbook == (
        "codebase-structure/point-every-dependency-toward-the-core-and-never-cycle-a",
    )
    assert check.handbook_note is None
    assert check.tooling == {
        "python": ("import-linter", "tach"),
        "typescript": ("dependency-cruiser",),
    }
    assert check.optin is False


def test_optin_and_empty_handbook_with_note_are_valid(tmp_path):
    _write(tmp_path, "arch-audit/checks/hidden-coupling.md", UNCITED)
    checks, errors = ac.load_checks(tmp_path)
    assert errors == []
    check = checks["arch/hidden-coupling"]
    assert check.handbook == ()
    assert check.handbook_note.startswith("The handbook's decay list")
    assert check.optin is True


NEEDS = """---
id: deps/hygiene
domain: deps
locality: global
handbook:
  - security-supply-chain/depend-only-on-what-you-can-account-for-a
tooling:
  python: [deptry]
  typescript: [depcheck, knip]
needs:
  resolved-tree: [deptry, knip]
ungranted_note: none
---

# Hygiene

Declared-but-unused dependencies.

## Tooling fallback

`depcheck` answers from source alone; `knip` and `deptry` need the tree.
"""


def test_needs_records_the_tier_of_each_tool(tmp_path):
    _write(tmp_path, "deps-audit/checks/hygiene.md", NEEDS)
    checks, errors = ac.load_checks(tmp_path)
    assert errors == []
    assert checks["deps/hygiene"].needs == {"resolved-tree": ("deptry", "knip")}


def test_a_record_without_needs_claims_every_tool_runs_on_a_clone(tmp_path):
    _write(tmp_path, "arch-audit/checks/layering.md", GOOD)
    checks, errors = ac.load_checks(tmp_path)
    assert errors == []
    assert checks["arch/layering"].needs == {}


def test_needs_must_name_a_known_tier(tmp_path):
    _write(
        tmp_path,
        "deps-audit/checks/hygiene.md",
        NEEDS.replace("resolved-tree: [deptry, knip]", "needs-network: [deptry]"),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("needs-network" in e and "must map one of" in e for e in errors)


def test_needs_must_name_a_tool_the_record_offers(tmp_path):
    _write(
        tmp_path,
        "deps-audit/checks/hygiene.md",
        NEEDS.replace("[deptry, knip]", "[deptry, kn1p]"),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("'kn1p'" in e and "not in this record's tooling" in e for e in errors)


def test_a_tool_may_not_sit_in_two_tiers(tmp_path):
    _write(
        tmp_path,
        "deps-audit/checks/hygiene.md",
        NEEDS.replace(
            "  resolved-tree: [deptry, knip]",
            "  resolved-tree: [deptry, knip]\n  target-execution: [knip]",
        ),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any(
        "'knip'" in e and "resolved-tree" in e and "target-execution" in e
        for e in errors
    )


def test_needs_without_tooling_is_an_error(tmp_path):
    _write(
        tmp_path,
        "deps-audit/checks/hygiene.md",
        NEEDS.replace(
            "tooling:\n  python: [deptry]\n  typescript: [depcheck, knip]\n", ""
        ),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("does not declare" in e for e in errors)


def test_needs_must_be_a_mapping(tmp_path):
    _write(
        tmp_path,
        "deps-audit/checks/hygiene.md",
        NEEDS.replace("needs:\n  resolved-tree: [deptry, knip]", "needs: [deptry]"),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("needs must be a mapping" in e for e in errors)


def _record(tooling=None, needs=None, extra=""):
    """Build a minimal well-formed `demo/thing` record for `ungranted_note`
    tests, with `tooling`, `needs` and any extra frontmatter lines the
    caller wants layered in before the closing `---`.
    """
    lines = [
        "---",
        "id: demo/thing",
        "domain: demo",
        "locality: local",
        "handbook: []",
        "handbook_note: Fixture record for ungranted_note tests.",
    ]
    if tooling:
        lines.append("tooling:")
        for lang, tools in tooling.items():
            lines.append(f"  {lang}: [{', '.join(tools)}]")
    if needs:
        lines.append("needs:")
        for tier, tools in needs.items():
            lines.append(f"  {tier}: [{', '.join(tools)}]")
    text = "\n".join(lines) + "\n" + extra + "---\n\n# Thing\n\nFixture body.\n"
    return text


def _load_one(tmp_path, check):
    """Write `check` as the sole record in a fresh tree and load it."""
    _write(tmp_path, "demo-audit/checks/thing.md", check)
    return ac.load_checks(tmp_path)


def test_the_sentinel_is_accepted(tmp_path):
    """A record with nothing to answer writes the lowercase sentinel."""
    check = _record(
        tooling={"python": ["pip-licenses"]},
        needs={"resolved-tree": ["pip-licenses"]},
        extra="ungranted_note: none\n",
    )
    checks, errors = _load_one(tmp_path, check)
    assert errors == []
    assert checks["demo/thing"].ungranted_note == "none"


def test_prose_is_accepted_and_stripped(tmp_path):
    check = _record(
        tooling={"python": ["pip-licenses"]},
        needs={"resolved-tree": ["pip-licenses"]},
        extra="ungranted_note: |\n  Reading the lockfile answers the pinned set.\n",
    )
    checks, errors = _load_one(tmp_path, check)
    assert errors == []
    assert checks["demo/thing"].ungranted_note == (
        "Reading the lockfile answers the pinned set."
    )


@pytest.mark.parametrize("spelling", ["None", "NONE", "nOnE"])
def test_a_miscased_sentinel_is_rejected_by_name(tmp_path, spelling):
    """YAML leaves `None` and `NONE` as ordinary strings, so a miscased
    sentinel would be read as a claim that something answers. Reject it
    with a message naming the spelling to use.
    """
    check = _record(
        tooling={"python": ["pip-licenses"]},
        needs={"resolved-tree": ["pip-licenses"]},
        extra=f"ungranted_note: {spelling}\n",
    )
    _, errors = _load_one(tmp_path, check)
    assert any("write the sentinel as 'none'" in e for e in errors)


@pytest.mark.parametrize("value", ["null", "~", ""])
def test_a_null_note_is_rejected_as_indistinguishable_from_omission(tmp_path, value):
    """YAML turns `null`, `~` and a bare key into nothing, which the loader
    cannot tell from an absent key. Say so rather than silently treating
    the record as unclassified.
    """
    check = _record(
        tooling={"python": ["pip-licenses"]},
        needs={"resolved-tree": ["pip-licenses"]},
        extra=f"ungranted_note: {value}\n",
    )
    _, errors = _load_one(tmp_path, check)
    assert any("ungranted_note is empty" in e for e in errors)


def test_a_blank_note_is_rejected(tmp_path):
    check = _record(
        tooling={"python": ["pip-licenses"]},
        needs={"resolved-tree": ["pip-licenses"]},
        extra='ungranted_note: "   "\n',
    )
    _, errors = _load_one(tmp_path, check)
    assert any("ungranted_note is blank" in e for e in errors)


def test_a_non_string_note_is_rejected(tmp_path):
    check = _record(
        tooling={"python": ["pip-licenses"]},
        needs={"resolved-tree": ["pip-licenses"]},
        extra="ungranted_note: [a, b]\n",
    )
    _, errors = _load_one(tmp_path, check)
    assert any("must be prose or 'none'" in e for e in errors)


def test_a_note_on_a_record_that_keeps_an_untiered_tool_is_vacuous(tmp_path):
    """The field describes a withheld grant leaving the record with nothing
    to run. A record keeping a tool that answers from a read-only clone
    cannot reach that state, so a note there describes nothing and must
    not be mistaken for one that is doing work.
    """
    check = _record(
        tooling={"python": ["pip-licenses", "osv-scanner"]},
        needs={"resolved-tree": ["pip-licenses"]},
        extra="ungranted_note: none\n",
    )
    _, errors = _load_one(tmp_path, check)
    assert any("cannot happen here" in e for e in errors)


def test_a_silenced_record_must_say_what_still_answers(tmp_path):
    """An absent note on a record the engine silences is not a claim, it is
    an omission - and the engine cannot tell the two apart, which is the
    whole reason the field is required here.
    """
    check = _record(
        tooling={"python": ["pip-licenses"]},
        needs={"resolved-tree": ["pip-licenses"]},
    )
    _, errors = _load_one(tmp_path, check)
    assert any("silences the check" in e for e in errors)


def test_the_requirement_names_every_silenced_language(tmp_path):
    check = _record(
        tooling={"python": ["deptry"], "typescript": ["knip"]},
        needs={"resolved-tree": ["deptry"], "target-execution": ["knip"]},
    )
    _, errors = _load_one(tmp_path, check)
    assert any("python, typescript" in e for e in errors)


def test_an_unsilenced_record_needs_no_note(tmp_path):
    check = _record(
        tooling={"python": ["pip-licenses", "osv-scanner"]},
        needs={"resolved-tree": ["pip-licenses"]},
    )
    _, errors = _load_one(tmp_path, check)
    assert errors == [], errors


def test_the_notes_are_not_all_sentinels():
    """The requirement can be satisfied without thought by writing `none`
    everywhere. Nothing can tell a correct `none` from a lazy one, so hold
    the number of records that say something real at a floor: the sweep
    behind #26 produced ten. Be honest about what a floor on a count
    catches and what it does not: it fails only once the count drops below
    the floor, so it says nothing if the count already sits above it - a
    change that trades one record's prose for another's passes silently,
    because the guard counts records rather than naming them, and so does a
    drop back down to just above the floor once a later change has raised
    it. Issue #5 did not add notes, contrary to what this docstring first
    predicted: it gave records already silenced in one language a second
    fully tiered language, which changes what a note must say and not
    whether the record carries one, so the count did not move. Resist
    naming how many records that was - an earlier draft of this sentence
    said three and the number was four, because the three whose prose had
    to be rewritten are not the same set as the records that gained a
    second fully tiered language. The claim the floor rests on needs no
    count of records at all. A later change
    that does add notes raises the count and therefore the slack above
    this floor rather than the floor itself; raise the floor by hand if
    that slack should be closed. Never lower it to make a deletion pass.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    prose = [
        c.id
        for c in checks.values()
        if c.ungranted_note is not None and c.ungranted_note != ac.UNGRANTED_NONE
    ]
    assert len(prose) >= 10, (
        f"only {len(prose)} records answer anything: {sorted(prose)}"
    )


def test_a_language_with_no_tools_is_not_fully_tiered(tmp_path):
    """`all()` is vacuously true over an empty list. A record listing a
    language with no tools has said nothing about grants, so it must not
    read as silenced - which would demand a note it has no basis to write.
    """
    check = _record(
        tooling={"python": ["pip-licenses"], "typescript": []},
        needs={"resolved-tree": ["pip-licenses"]},
        extra="ungranted_note: none\n",
    )
    _, errors = _load_one(tmp_path, check)
    assert errors == [], errors
    assert ac._fully_tiered_languages(
        {"python": ("pip-licenses",), "typescript": ()},
        {"resolved-tree": ("pip-licenses",)},
    ) == ("python",)


def _routes_frontmatter(route_body: str, extra: str = "") -> str:
    """Render a fixture record whose `routes:` carries one route built from
    `route_body`. `route_body`'s own lines are already indented to sit under
    a `- ` list item (the shape every route-body literal below uses), so
    this only prefixes the first line with the marker. `extra` is inserted
    as sibling frontmatter, at column 0, after `routes:` and before the
    closing `---`.
    """
    return f"""---
id: demo/thing
domain: demo
locality: local
handbook: []
handbook_note: Fixture record for route tests.
routes:
  - {route_body}
{extra}---

# Thing

Fixture body.
"""


def _one_route_record(tmp_path, route_body):
    """Write a record whose frontmatter carries one route built from
    `route_body`, assert the load produced no errors, and return the loaded
    Check.
    """
    _write(tmp_path, "demo-audit/checks/thing.md", _routes_frontmatter(route_body))
    checks, errors = ac.load_checks(tmp_path)
    assert errors == [], errors
    return checks["demo/thing"]


def _errors_for_route(tmp_path, route_body):
    """Write a record whose frontmatter carries one route built from
    `route_body`, and return the error list instead of the Check.
    """
    _write(tmp_path, "demo-audit/checks/thing.md", _routes_frontmatter(route_body))
    _, errors = ac.load_checks(tmp_path)
    return errors


def _errors_for_both_schemas(tmp_path):
    """Write a record carrying both `routes:` and `tooling:`, and return the
    error list.
    """
    text = _routes_frontmatter(
        "kind: command\n    tool: t\n    argv: [t]",
        extra="tooling:\n  python: [t]\n",
    )
    _write(tmp_path, "demo-audit/checks/thing.md", text)
    _, errors = ac.load_checks(tmp_path)
    return errors


def test_a_route_carries_its_kind_and_command(tmp_path):
    check = _one_route_record(
        tmp_path, "kind: command\n    tool: pydeps\n    argv: [pydeps, --show-cycles]"
    )
    route = check.routes[0]
    assert (route.kind, route.tool, route.argv) == (
        "command",
        "pydeps",
        ("pydeps", "--show-cycles"),
    )
    assert route.disposition == "runs"
    assert route.needs is None
    assert route.findings_stream == "stdout"


def test_a_package_defaults_to_the_tool_name(tmp_path):
    check = _one_route_record(
        tmp_path, "kind: command\n    tool: pydeps\n    argv: [pydeps]"
    )
    assert check.routes[0].package == "pydeps"


def test_a_package_is_written_only_where_it_differs(tmp_path):
    check = _one_route_record(
        tmp_path,
        "kind: command\n    tool: import-linter\n    package: import-linter\n    argv: [lint-imports]",
    )
    assert (check.routes[0].package, check.routes[0].argv) == (
        "import-linter",
        ("lint-imports",),
    )


@pytest.mark.parametrize("kind", ["library", "procedure", "subject"])
def test_an_argv_on_a_non_command_kind_is_rejected(tmp_path, kind):
    errors = _errors_for_route(
        tmp_path, f"kind: {kind}\n    tool: grimp\n    argv: [grimp]"
    )
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
    [
        ("kind", "gadget"),
        ("lang", "cobol"),
        ("disposition", "maybe"),
        ("findings_stream", "syslog"),
        ("needs", "a-network"),
    ],
)
def test_a_route_field_must_name_a_known_value(tmp_path, field, value):
    errors = _errors_for_route(
        tmp_path, f"kind: command\n    tool: t\n    argv: [t]\n    {field}: {value}"
    )
    assert any(field in e for e in errors), errors


def test_an_unknown_route_key_is_rejected(tmp_path):
    errors = _errors_for_route(
        tmp_path, "kind: command\n    tool: t\n    argv: [t]\n    runner: npx"
    )
    assert any("runner" in e for e in errors), errors


@pytest.mark.parametrize(
    "field,route_body",
    [
        ("tool", "kind: command\n    tool: [t]\n    argv: [t]"),
        (
            "package",
            "kind: command\n    tool: t\n    package: [t]\n    argv: [t]",
        ),
        (
            "argv_by_manager",
            "kind: command\n    tool: t\n    argv: [t]\n    argv_by_manager: [x]",
        ),
        (
            "argv_by_manager",
            "kind: command\n    tool: t\n    argv: [t]\n"
            "    argv_by_manager:\n      pnpm: not-a-list",
        ),
        ("in_env", "kind: command\n    tool: t\n    argv: [t]\n    in_env: maybe"),
        (
            "applies_when",
            "kind: command\n    tool: t\n    argv: [t]\n    applies_when: [oops]",
        ),
        (
            "alone_insufficient",
            "kind: command\n    tool: t\n    argv: [t]\n    alone_insufficient: [oops]",
        ),
        ("note", "kind: command\n    tool: t\n    argv: [t]\n    note: [oops]"),
    ],
)
def test_a_wrong_typed_route_field_is_rejected(tmp_path, field, route_body):
    """The review named eight validation branches in `_load_routes` with no
    test of their own: `tool`, `package`, `argv_by_manager` (both its own
    mapping type and a per-manager entry's list type), `in_env`,
    `applies_when`, `alone_insufficient` and `note` each reject a
    wrong-typed value. Assert only that the field name appears in the
    message, not the message's full text.
    """
    errors = _errors_for_route(tmp_path, route_body)
    assert any(field in e for e in errors), errors


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
        tmp_path,
        "kind: library\n    tool: grimp\n    argv_by_manager:\n      pnpm: [x]",
    )
    assert any("argv_by_manager" in e for e in errors), errors


def test_a_route_defaults_to_the_any_language(tmp_path):
    """No test above names `lang:` on a route, and every one of them must
    still load clean - so the default has to be a value nothing in
    `ROUTE_LANGS` treats as an error. `any` is that value, and it is also
    the one the projection in `_project_tooling` gives special handling.
    """
    check = _one_route_record(tmp_path, "kind: command\n    tool: t\n    argv: [t]")
    assert check.routes[0].lang == "any"


def test_a_record_with_no_routes_key_carries_none(tmp_path):
    _write(tmp_path, "arch-audit/checks/layering.md", GOOD)
    checks, errors = ac.load_checks(tmp_path)
    assert errors == []
    assert checks["arch/layering"].routes == ()


def test_routes_must_be_a_list_of_mappings(tmp_path):
    text = _routes_frontmatter("kind: command\n    tool: t\n    argv: [t]").replace(
        "routes:\n  - kind: command\n    tool: t\n    argv: [t]\n",
        "routes: [not, a, mapping]\n",
    )
    _write(tmp_path, "demo-audit/checks/thing.md", text)
    _, errors = ac.load_checks(tmp_path)
    assert any("routes must be a list of mappings" in e for e in errors)


def test_a_route_error_names_its_index(tmp_path):
    """A record with several routes, one of them broken, must say which."""
    text = """---
id: demo/thing
domain: demo
locality: local
handbook: []
handbook_note: Fixture record for route tests.
routes:
  - kind: command
    tool: pydeps
    argv: [pydeps]
  - kind: command
    tool: grimp
---

# Thing

Fixture body.
"""
    _write(tmp_path, "demo-audit/checks/thing.md", text)
    _, errors = ac.load_checks(tmp_path)
    assert any("routes[1]" in e and "argv" in e for e in errors), errors
    assert not any("routes[0]" in e for e in errors), errors


def test_tooling_and_needs_are_projected_from_routes(tmp_path):
    """A migrated record's `tooling`/`needs` are read by call sites outside
    this module that predate `routes`. Project them so none of those
    readers has to change.
    """
    text = """---
id: demo/thing
domain: demo
locality: local
handbook: []
handbook_note: Fixture record for route tests.
routes:
  - lang: python
    kind: command
    tool: pydeps
    argv: [pydeps, --show-cycles]
    needs: resolved-tree
  - lang: python
    kind: library
    tool: grimp
  - lang: typescript
    kind: command
    tool: dependency-cruiser
    argv: [depcruise]
---

# Thing

Fixture body.
"""
    _write(tmp_path, "demo-audit/checks/thing.md", text)
    checks, errors = ac.load_checks(tmp_path)
    assert errors == [], errors
    check = checks["demo/thing"]
    assert check.tooling == {
        "python": ("pydeps", "grimp"),
        "typescript": ("dependency-cruiser",),
    }
    assert check.needs == {"resolved-tree": ("pydeps",)}


def test_a_lang_any_route_projects_under_the_literal_any_key(tmp_path):
    """`tooling: {any: [...]}` was the legacy shape for a language-agnostic
    tool - every reader looks a language up with `.get(lang, ())`, so an
    `any` tool is deliberately invisible to a `python`/`typescript` lookup.
    A migrated record's `lang: any` route must project the same way: under
    the literal `"any"` key, not fanned out to every language the record
    also names.
    """
    text = """---
id: demo/thing
domain: demo
locality: local
handbook: []
handbook_note: Fixture record for route tests.
routes:
  - lang: any
    kind: library
    tool: semgrep
---

# Thing

Fixture body.
"""
    _write(tmp_path, "demo-audit/checks/thing.md", text)
    checks, errors = ac.load_checks(tmp_path)
    assert errors == [], errors
    assert checks["demo/thing"].tooling == {"any": ("semgrep",)}


def test_an_any_route_does_not_fan_into_a_named_language(tmp_path):
    """A record naming both a `python` route and an `any` route must keep
    the `any` tool out of `tooling["python"]` - fanning it out would hand
    a check like `arch/size` (an `any`-only record today) Python
    invocations it does not have, and would change which records a
    Python lens believes it must cover.
    """
    text = """---
id: demo/thing
domain: demo
locality: local
handbook: []
handbook_note: Fixture record for route tests.
routes:
  - lang: python
    kind: command
    tool: pydeps
    argv: [pydeps]
  - lang: any
    kind: library
    tool: semgrep
---

# Thing

Fixture body.
"""
    _write(tmp_path, "demo-audit/checks/thing.md", text)
    checks, errors = ac.load_checks(tmp_path)
    assert errors == [], errors
    check = checks["demo/thing"]
    assert check.tooling == {"python": ("pydeps",), "any": ("semgrep",)}


def test_a_forbidden_route_is_excluded_from_both_projections(tmp_path):
    """A `disposition: forbidden` route names a command the record warns
    against - the npm `semgrep` placeholder, the bare `dlx depcruise` - so
    projecting it into `tooling`/`needs` would tell the lens to check a
    tool the record forbids. `depcruise` appears only on the forbidden
    route here, so it must not appear in either projection at all; `madge`
    appears on an ordinary route and must appear normally.
    """
    text = """---
id: demo/thing
domain: demo
locality: local
handbook: []
handbook_note: Fixture record for route tests.
routes:
  - lang: typescript
    kind: command
    tool: depcruise
    argv: [dlx, depcruise]
    disposition: forbidden
  - lang: typescript
    kind: command
    tool: madge
    argv: [madge]
    needs: resolved-tree
---

# Thing

Fixture body.
"""
    _write(tmp_path, "demo-audit/checks/thing.md", text)
    checks, errors = ac.load_checks(tmp_path)
    assert errors == [], errors
    check = checks["demo/thing"]
    assert check.tooling == {"typescript": ("madge",)}
    assert check.needs == {"resolved-tree": ("madge",)}


def test_alternative_and_superseded_routes_do_contribute(tmp_path):
    """Unlike `forbidden`, an `alternative` or `superseded` route is a tool
    the record does offer - just not the one it runs by default - so both
    must still appear in the `tooling` projection.
    """
    text = """---
id: demo/thing
domain: demo
locality: local
handbook: []
handbook_note: Fixture record for route tests.
routes:
  - lang: python
    kind: command
    tool: import-linter
    argv: [lint-imports]
  - lang: python
    kind: command
    tool: tach
    argv: [tach, check]
    disposition: alternative
  - lang: python
    kind: command
    tool: pydeps
    argv: [pydeps, --show-cycles]
    disposition: superseded
---

# Thing

Fixture body.
"""
    _write(tmp_path, "demo-audit/checks/thing.md", text)
    checks, errors = ac.load_checks(tmp_path)
    assert errors == [], errors
    assert checks["demo/thing"].tooling == {
        "python": ("import-linter", "tach", "pydeps")
    }


def test_missing_frontmatter_is_reported_not_raised(tmp_path):
    _write(tmp_path, "arch-audit/checks/broken.md", "# No frontmatter here\n")
    checks, errors = ac.load_checks(tmp_path)
    assert checks == {}
    assert any("frontmatter" in e for e in errors)


def test_id_must_match_the_file_path(tmp_path):
    _write(
        tmp_path,
        "arch-audit/checks/layering.md",
        GOOD.replace("id: arch/layering", "id: arch/wrong"),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("does not match its path" in e for e in errors)


def test_domain_must_match_the_owning_skill(tmp_path):
    _write(tmp_path, "deps-audit/checks/layering.md", GOOD)
    _, errors = ac.load_checks(tmp_path)
    assert any("does not match its owning skill 'deps-audit'" in e for e in errors)


def test_a_checks_dir_outside_a_domain_skill_is_ignored(tmp_path):
    _write(tmp_path, "some-helper/checks/layering.md", GOOD)
    checks, errors = ac.load_checks(tmp_path)
    assert (checks, errors) == ({}, [])


def test_locality_must_be_local_or_global(tmp_path):
    _write(
        tmp_path,
        "arch-audit/checks/layering.md",
        GOOD.replace("locality: local", "locality: sometimes"),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("locality" in e for e in errors)


def test_empty_handbook_without_a_note_is_rejected(tmp_path):
    text = UNCITED.replace(
        "handbook_note: The handbook's decay list names no equivalent signal.\n", ""
    )
    _write(tmp_path, "arch-audit/checks/hidden-coupling.md", text)
    _, errors = ac.load_checks(tmp_path)
    assert any("handbook_note" in e for e in errors)


def test_a_note_alongside_anchors_is_rejected(tmp_path):
    text = GOOD.replace(
        "tooling:", "handbook_note: why this exceeds the handbook\ntooling:"
    )
    _write(tmp_path, "arch-audit/checks/layering.md", text)
    _, errors = ac.load_checks(tmp_path)
    assert any("handbook_note" in e for e in errors)


def test_unknown_frontmatter_key_is_rejected(tmp_path):
    _write(
        tmp_path,
        "arch-audit/checks/layering.md",
        GOOD.replace("domain: arch", "domain: arch\nsevrity: high"),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("sevrity" in e for e in errors)


def test_missing_title_is_rejected(tmp_path):
    body_start = GOOD.index("# Layering")
    _write(
        tmp_path,
        "arch-audit/checks/layering.md",
        GOOD[:body_start] + "no heading here\n",
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("title" in e for e in errors)


def test_tooling_must_map_language_to_a_list(tmp_path):
    _write(
        tmp_path,
        "arch-audit/checks/layering.md",
        GOOD.replace("python: [import-linter, tach]", "python: import-linter"),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("tooling" in e for e in errors)


def test_duplicate_ids_across_files_are_reported(tmp_path):
    _write(tmp_path, "arch-audit/checks/layering.md", GOOD)
    _write(tmp_path, "arch-audit/checks/layering-copy.md", GOOD)
    _, errors = ac.load_checks(tmp_path)
    assert any("duplicate" in e for e in errors)


def test_an_absent_checks_dir_loads_empty_without_error(tmp_path):
    checks, errors = ac.load_checks(tmp_path / "nope")
    assert checks == {}
    assert errors == []


def test_a_record_at_the_wrong_depth_is_reported_not_skipped(tmp_path):
    _write(tmp_path, "arch-audit/checks/nested/deep.md", GOOD)
    checks, errors = ac.load_checks(tmp_path)
    assert checks == {}
    assert [e.split(":")[0] for e in errors] == ["arch-audit/checks/nested/deep.md"]
    assert all("would never be loaded" in e for e in errors)


def test_an_unreadable_record_is_reported_not_raised(tmp_path):
    root = tmp_path / "arch-audit" / "checks"
    root.mkdir(parents=True)
    (root / "binary.md").write_bytes(b"---\nid: arch/binary\n---\n\xff\xfe")
    (root / "adir.md").mkdir()
    checks, errors = ac.load_checks(tmp_path)
    assert checks == {}
    assert any(e == "arch-audit/checks/binary.md: not valid UTF-8" for e in errors)
    assert any(
        e.startswith("arch-audit/checks/adir.md: cannot be read:") for e in errors
    )


def test_frontmatter_with_an_empty_body_is_not_reported_as_missing(tmp_path):
    _write(
        tmp_path,
        "arch-audit/checks/layering.md",
        "---\nid: arch/layering\ndomain: arch\n---",
    )
    _, errors = ac.load_checks(tmp_path)
    assert not any("missing YAML frontmatter" in e for e in errors)
    assert any("title" in e for e in errors)


def test_every_audit_skill_has_a_non_empty_checks_directory():
    """Regression net for lidia-tech/lidia-agents#559 PR 2: the `/audit` front door now detects
    which domains are available from `<domain>-audit/checks/` instead of a
    fixed list, so a domain skill with an empty or missing `checks/` would
    silently drop out of `/audit all`. If this fails, go find which
    `*-audit` skill lost its checks - do not weaken the assertion.
    """
    skill_dirs = sorted(
        p for p in ac.SKILLS_DIR.glob(f"*{ac.SKILL_SUFFIX}") if p.is_dir()
    )
    assert skill_dirs, "no *-audit skills found under the real skills directory"
    empty = [p.name for p in skill_dirs if not any((p / ac.CHECKS_SUBDIR).glob("*.md"))]
    assert empty == [], f"these *-audit skills have no checks records: {empty}"


def test_the_real_checks_tree_covers_every_domain():
    """Structural complement to `test_the_real_checks_tree_loads_clean`'s
    exact id list: this asserts the *shape* the front door now depends on -
    zero load errors and full domain coverage - so it stays meaningful as
    individual check ids are added, renamed, or removed.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    domains = {check.domain for check in checks.values()}
    assert domains == {
        "arch",
        "ci",
        "data-protection",
        "deps",
        "docs",
        "eval",
        "prompt",
        "security",
        "test",
    }


def test_the_real_checks_tree_loads_clean():
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    assert sorted(checks) == [
        "arch/complexity",
        "arch/complexity-gate",
        "arch/coupling",
        "arch/cycles",
        "arch/dead-code",
        "arch/hidden-coupling",
        "arch/layering",
        "arch/martin-metrics",
        "arch/over-abstraction",
        "arch/over-decomposition",
        "arch/size",
        "ci/action-supply-chain",
        "ci/branch-protection",
        "ci/deploy-safety",
        "ci/efficiency",
        "ci/gate-enforcement",
        "ci/permissions-secrets",
        "ci/self-hosted-runners",
        "ci/trigger-safety",
        "ci/workflow-correctness",
        "data-protection/boundary-minimization",
        "data-protection/data-flow-map",
        "data-protection/deletion-path",
        "data-protection/processor-register",
        "data-protection/provider-surface",
        "data-protection/residency-pinning",
        "data-protection/retention-limits",
        "data-protection/stored-artifact-pii",
        "deps/freshness",
        "deps/hygiene",
        "deps/inventory",
        "deps/licenses",
        "deps/transitive-licenses",
        "deps/vulnerabilities",
        "docs/coverage",
        "docs/cross-referencing",
        "docs/docstring-coverage",
        "docs/docstring-staleness",
        "docs/docstring-standard",
        "docs/organization",
        "eval/adversarial",
        "eval/contamination",
        "eval/cost-latency",
        "eval/coverage",
        "eval/judge-calibration",
        "eval/methodology",
        "eval/prompt-quality",
        "eval/regression-tracking",
        "eval/reproducibility",
        "eval/smoke-test-gate",
        "eval/verdict-scale",
        "prompt/cognitive-load",
        "prompt/cross-prompt-consistency",
        "prompt/examples-delimiters",
        "prompt/grounding",
        "prompt/instruction-precision",
        "prompt/internal-consistency",
        "prompt/output-contract",
        "prompt/positive-framing",
        "prompt/role-objective",
        "prompt/sop-naming",
        "prompt/sop-rfc2119",
        "prompt/sop-structure",
        "security/crypto",
        "security/dangerous-calls",
        "security/injection",
        "security/secret-history",
        "security/secrets-in-code",
        "security/sensitive-data",
        "security/unsafe-io",
        "test/assertion-strength",
        "test/coverage-reach",
        "test/determinism",
        "test/isolation",
        "test/mutation",
        "test/new-code-coverage",
        "test/property-based-gap",
    ]
    assert {c.locality for c in checks.values()} == {"local", "global"}
    assert [c.id for c in checks.values() if c.optin] == [
        "arch/martin-metrics",
        "ci/branch-protection",
        "ci/self-hosted-runners",
        "deps/inventory",
        "deps/transitive-licenses",
        "docs/docstring-coverage",
        "docs/docstring-staleness",
        "docs/docstring-standard",
        "eval/adversarial",
        "eval/cost-latency",
        "eval/judge-calibration",
        "prompt/cross-prompt-consistency",
        "security/secret-history",
        "test/mutation",
        "test/property-based-gap",
    ]


def test_every_tool_less_check_states_a_reading_procedure():
    """lidia-tech/lidia-agents#567 item 5: a record may omit `tooling:` when its detection is
    reading rather than running something - but it must then say so under
    `## Tooling fallback`, or the executing agent has nothing to run and
    nothing told to read. If this fails, add the section to the named
    record - do not weaken the assertion.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    missing = sorted(
        check_id
        for check_id, check in checks.items()
        if not check.tooling and "\n## Tooling fallback" not in check.path.read_text()
    )
    assert missing == [], (
        f"these checks declare no tooling and state no fallback: {missing}"
    )


def test_every_review_lens_paragraph_carries_a_label():
    """lidia-tech/lidia-agents#567 item 4: a `## Review lens` paragraph opens with a bold label
    naming what it judges, followed by ` - ` and the sentence
    (`**Label** - <sentence>`), so a whole-branch reviewer assembling
    lenses from several records can tell them apart. If this fails,
    label the paragraph in that exact form - do not weaken the
    assertion.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    unlabeled = []
    label_re = re.compile(r"^\*\*[^*]+\*\* - ")
    for check_id, check in sorted(checks.items()):
        section = re.search(
            r"^## Review lens\n(.*?)(?=\n## |\Z)",
            check.path.read_text(),
            re.S | re.M,
        )
        if section is None:
            continue
        for para in section.group(1).strip().split("\n\n"):
            if para.strip() and not label_re.match(para.strip()):
                unlabeled.append(f"{check_id}: {para.strip()[:60]}")
    assert unlabeled == [], f"unlabeled review-lens paragraphs: {unlabeled}"


def test_a_tool_has_one_tier_across_the_family():
    """A tool needs the same thing everywhere, so two records that name it
    must agree. This is the guard that can see *into* a record's
    classification, and it sees only through a tool some other record
    already classified: an absent `needs:` entry is a positive claim that
    the tool runs against a read-only clone, so a record nobody examined is
    indistinguishable from one deliberately left at the default unless the
    same tool is classified elsewhere. The vacuity test below covers the
    other half - that the sweep happened at all - by counting the records
    that classify anything; neither reaches a wrongly-defaulted tool no
    other record names. If this fails, classify the tool the same way in
    both records - do not weaken the assertion.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    tier_of: dict[str, tuple[str, str]] = {}
    disagreements = []
    for check_id, check in sorted(checks.items()):
        classified = {
            name: tier for tier, names in check.needs.items() for name in names
        }
        for name in sorted({n for names in check.tooling.values() for n in names}):
            tier = classified.get(name, "")
            if name not in tier_of:
                tier_of[name] = (tier, check_id)
                continue
            seen_tier, seen_in = tier_of[name]
            if seen_tier != tier:
                disagreements.append(
                    f"{name!r}: {seen_in} says {seen_tier or 'read-only clone'}, "
                    f"{check_id} says {tier or 'read-only clone'}"
                )
    assert disagreements == [], "the same tool is classified two ways: " + "; ".join(
        disagreements
    )


def test_the_classification_is_not_vacuous():
    """`test_a_tool_has_one_tier_across_the_family` passes trivially on a
    tree where nothing is classified, which is the state this change exists
    to leave behind. Assert the sweep actually happened, so deleting every
    `needs:` key fails loudly instead of turning the guard above into a
    no-op. The floor is the number of records the sweep classified, with no
    slack: a floor below that count would let a classification be deleted
    silently, and a deleted tier is not visibly missing - it reads as the
    positive claim that every tool in the record answers from a read-only
    clone. Adding a record that needs a tier therefore raises the floor
    with it. If this fails, a classification was removed - restore it
    rather than lowering the floor.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    classified = sorted(c.id for c in checks.values() if c.needs)
    assert len(classified) >= 22, (
        f"only {len(classified)} record(s) classify any tool: {classified}"
    )
    assert {t for c in checks.values() for t in c.needs} == set(ac.NEEDS_TIERS), (
        "both tiers should be in use across the family"
    )


_NO_TYPESCRIPT_LENS = {
    # arch/martin-metrics and docs/docstring-coverage are the debt this sweep
    # did not clear: #5 scoped its remaining half to test-audit and
    # security-audit. Both are python-only and both are real gaps.
    "arch/martin-metrics",
    "docs/docstring-coverage",
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
    reading pass, which needs no language. What this checks is that a
    `typescript:` or `any:` key is present, not what is under it, so
    `typescript: []` would satisfy it. If this fails, add the lens or
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


def test_a_record_that_classifies_a_tool_states_a_fallback():
    """A `needs:` entry is machine-readable and says nothing about what to
    do instead. `## Tooling fallback` is where an executing agent reads
    that, so a record admitting one of its tools needs a grant must have
    the section - otherwise the agent reaches for the tool, it fails, and
    the check reports `no-evidence` for a reason the record could have
    predicted. If this fails, write the section - do not weaken the
    assertion.

    This deliberately checks that the section exists and not that it names
    each classified tool. `deps/transitive-licenses` defers its whole
    fallback to `deps/licenses` by reference rather than restating the
    tool list, which is the right shape for that record; an
    every-name-must-appear rule would force it to duplicate exactly what
    it was written to avoid. Whether the prose actually explains the
    consequence is a reading pass, not a test.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    silent = sorted(
        check_id
        for check_id, check in checks.items()
        if check.needs
        and not re.search(
            r"^## Tooling fallback\n\s*\S",
            check.path.read_text(),
            re.M,
        )
    )
    assert silent == [], (
        f"these records classify a tool and state no fallback: {silent}"
    )
