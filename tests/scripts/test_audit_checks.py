"""Tests for scripts/audit_checks.py (<origin-repo>#559)."""

import importlib.util
import re
import sys
from pathlib import Path

import pytest
import yaml

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
    assert check.routes == ()
    assert check.optin is False


def test_optin_and_empty_handbook_with_note_are_valid(tmp_path):
    _write(tmp_path, "arch-audit/checks/hidden-coupling.md", UNCITED)
    checks, errors = ac.load_checks(tmp_path)
    assert errors == []
    check = checks["arch/hidden-coupling"]
    assert check.handbook == ()
    assert check.handbook_note.startswith("The handbook's decay list")
    assert check.optin is True


def _record(tooling=None, needs=None, extra=""):
    """Build a minimal `demo/thing` record, with any extra frontmatter lines
    the caller wants layered in before the closing `---`.

    `tooling` and `needs` write the record-level keys the loader refuses, for
    the tests that hold the refusal; a record built without either declares no
    routes.
    """
    lines = [
        "---",
        "id: demo/thing",
        "domain: demo",
        "locality: local",
        "handbook: []",
        "handbook_note: Fixture record for loader tests.",
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


def test_evidence_is_absent_rather_than_blank_when_the_routes_carry_it(tmp_path):
    """A record with nothing check-level to say about measurement omits it.

    Unlike a route's `needs`, whose absence is the positive claim that the
    route needs no grant, an absent `evidence` claims nothing at all: what to measure is in
    the routes, which is where a per-tool measurement belongs.
    """
    checks, errors = _load_one(tmp_path, _record())
    assert errors == []
    assert checks["demo/thing"].evidence is None


def test_evidence_carries_the_check_level_measurement(tmp_path):
    check = _record(
        extra="evidence: Line counts per file; flag outliers.\n",
    )
    checks, errors = _load_one(tmp_path, check)
    assert errors == []
    assert checks["demo/thing"].evidence == "Line counts per file; flag outliers."


def test_evidence_is_stored_stripped(tmp_path):
    """The same normalisation `answers_ungranted` does, for the same reason.

    Every record that will carry this field writes it as a YAML folded scalar,
    which leaves the value's surrounding whitespace up to how the block was
    indented rather than up to what the author meant. Storing it raw would put
    that accident into the value a reader compares.
    """
    check = _record(
        extra="evidence: >-\n  Line counts per file.\n",
    )
    checks, errors = _load_one(tmp_path, check)
    assert errors == []
    assert checks["demo/thing"].evidence == "Line counts per file."


@pytest.mark.parametrize(
    ("extra", "fragment"),
    [
        ("evidence:\n", "evidence is empty"),
        ("evidence: ''\n", "evidence is blank"),
        ("evidence: '   '\n", "evidence is blank"),
    ],
)
def test_an_empty_evidence_key_is_rejected_rather_than_read_as_absent(
    tmp_path, extra, fragment
):
    """The key present and saying nothing is the one state that must not pass.

    YAML turns a bare `evidence:` into `None`, which is indistinguishable from
    omitting the key by the time it reaches the dataclass - and the two mean
    opposite things, so the difference has to be caught where it is still
    visible. Asserted on the message rather than on the word `evidence`
    appearing somewhere in the error list, because the unknown-key rule already
    produces an error naming `evidence` and these would pass against it.
    """
    _, errors = _load_one(tmp_path, _record(extra=extra))
    assert any(fragment in e for e in errors), errors


def test_evidence_must_be_prose_not_a_list(tmp_path):
    check = _record(extra="evidence: [a, b]\n")
    _, errors = _load_one(tmp_path, check)
    assert any("evidence must be a string" in e for e in errors), errors


def _languages_rescued_by_an_untiered_route(check: ac.Check) -> list[str]:
    """The languages a record would be silenced in but for an untiered
    answering route.

    A language qualifies when it offers at least one answering route that
    needs a grant *and* at least one that answers it needing none: delete
    the untiered ones and `_silenced_languages` would name it, so the record
    would owe `answers_ungranted`. The untiered side is taken from the
    loader's own `_routes_answering_ungranted` rather than recomputed, so
    neither the two exclusions that grouping applies - a `kind: subject`
    route is not an answer, a `disposition: forbidden` route is not an offer
    - nor the universal spread it applies, whereby an untiered `lang: any`
    or `lang: none` route answers for every language the record answers for,
    can drift away from the rule this is counted against.

    Args:
        check: A loaded record. One carrying no routes yields no languages,
            because it offers nothing a grant could silence.

    Returns:
        The qualifying languages, sorted.
    """
    untiered = ac._routes_answering_ungranted(check.routes)
    tiered: dict[str, list[ac.Route]] = {}
    for route in check.routes:
        if (
            route.kind in ac.ANSWERING_ROUTE_KINDS
            and route.disposition != "forbidden"
            and route.needs is not None
        ):
            tiered.setdefault(route.lang, []).append(route)
    return sorted(
        lang for lang, routes in untiered.items() if routes and lang in tiered
    )


def test_the_notes_are_not_all_sentinels():
    """The requirement can be satisfied without thought by writing the
    sentinel everywhere. Nothing can tell a correct `answers_ungranted: none`
    from a lazy one, so hold the number of records that say something real at
    a floor, ratcheted to the population measured at the time rather than
    left with slack under it. That is the convention its neighbour
    `test_the_classification_is_not_vacuous` follows, for the same reason: a
    floor sitting below the count is a floor a deletion passes under in
    silence, and a deleted claim is not visibly missing - the record simply
    stops demonstrating anything.

    "Something real" has no prose field to live in: a record says it
    structurally, by carrying a language whose answering routes would all
    need a grant except for an untiered one that still answers.
    `arch/complexity` is the shape - silenced in TypeScript but for an ESLint
    invocation under an audit-owned config that needs no install. A record
    that writes `answers_ungranted: none` instead is the sentinel and does not
    count.

    A `kind: subject` route is not something a language can be rescued from:
    `arch/complexity-gate` names `ruff`, `radon` and `xenon` as the gate's
    subject rather than its instrument and is not in the population, because
    it was never silenced. Counting a tiered subject route here would recover
    a number by contradicting the independence of `needs` and `kind`, which a
    test below pins.

    Be honest about what a floor on a count catches and what it does not: it
    fails only once the count drops below the floor, so a change that trades
    one record's claim for another's passes silently, because the guard counts
    records rather than naming them. It also cannot see whether an untiered
    route genuinely answers, which is the judgment `answers_ungranted` exists
    to force and no count can make.

    A **drop** means some record that used to demonstrate an ungranted answer
    no longer does, which is a real defect. A **rise** is a record gaining a
    rescuing route, and the floor is raised onto it in the same commit, so no
    slack is left for a later deletion to hide in. Never lower the floor to
    make a deletion pass, and never narrow or widen what it counts to recover
    a number. The number written here is the population at the last ratchet,
    and the only way to know the current one is to measure it.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    claims = sorted(
        c.id for c in checks.values() if _languages_rescued_by_an_untiered_route(c)
    )
    assert len(claims) >= 23, f"only {len(claims)} records answer anything: {claims}"


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


def test_a_record_level_tooling_is_refused(tmp_path):
    """`routes:` is the schema, not one of two (#69): `tooling:` alone is refused.

    A record declares what it runs as routes, so a record-level tool list is
    refused by name, with a message saying what replaces it.
    """
    _write(
        tmp_path,
        "demo-audit/checks/thing.md",
        _record(tooling={"python": ["t"]}),
    )
    checks, errors = ac.load_checks(tmp_path)
    assert checks == {}
    assert any("record-level tooling" in e for e in errors), errors
    assert not any("record-level needs" in e for e in errors), errors


def test_a_record_level_needs_is_refused(tmp_path):
    """The record-level tier mapping goes with the list it classified."""
    _write(
        tmp_path,
        "demo-audit/checks/thing.md",
        _record(
            tooling={"python": ["t", "u"]},
            needs={"resolved-tree": ["t"]},
        ),
    )
    checks, errors = ac.load_checks(tmp_path)
    assert checks == {}
    assert any("record-level needs" in e for e in errors), errors
    assert any("record-level tooling" in e for e in errors), errors


def test_a_refused_record_gets_only_the_refusal(tmp_path):
    """A refused key is reported once, by name, and read for nothing else.

    The keys are not parsed, so their shape cannot add a second error, and the
    message names what replaces each, so it is the whole of what the author
    needs. The same holds beside `routes:`.
    """
    _write(
        tmp_path,
        "demo-audit/checks/thing.md",
        _record(tooling={"python": ["t"]}, needs={"bogus-tier": ["t", "u"]}),
    )
    _, errors = ac.load_checks(tmp_path)
    assert len(errors) == 2, errors
    assert all("is not a field" in e for e in errors), errors
    _write(
        tmp_path,
        "demo-audit/checks/thing.md",
        _routes_frontmatter(
            "lang: any\n    kind: procedure\n    note: Read it.",
            extra="tooling:\n  python: [t]\nneeds:\n  resolved-tree: [t]\n"
            "ungranted_note: none\n",
        ),
    )
    _, errors = ac.load_checks(tmp_path)
    assert len(errors) == 3, errors
    assert all("is not a field" in e for e in errors), errors
    assert any("answers_ungranted" in e for e in errors), errors


def test_a_route_s_own_needs_is_untouched_by_the_refusal(tmp_path):
    """The refusal reads the record's keys, never a route's `needs` field."""
    _write(
        tmp_path,
        "demo-audit/checks/thing.md",
        _routes_frontmatter(
            "lang: python\n    kind: command\n    tool: t\n    argv: [t]\n"
            "    needs: resolved-tree",
            extra="answers_ungranted: none\n",
        ),
    )
    checks, errors = ac.load_checks(tmp_path)
    assert errors == [], errors
    check = checks["demo/thing"]
    assert check.routes[0].needs == "resolved-tree"


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
        tmp_path,
        "kind: command\n    tool: pydeps\n    registry: pypi\n    argv: [pydeps, --show-cycles]",
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
        tmp_path,
        "kind: command\n    tool: pydeps\n    registry: pypi\n    argv: [pydeps]",
    )
    assert check.routes[0].package == "pydeps"


def test_a_package_written_with_no_value_is_rejected(tmp_path):
    """`package:` with nothing after it and `package: null` both parse to
    `None`, which `get` cannot tell from an absent key - so the fallback to
    the tool name never fires and the string check is skipped, and a record
    that meant to name a package ends up naming none while loading clean.
    This is the shape `answers_ungranted` and `evidence` already reject by
    name, for the same reason: an empty value is a claim the
    reader cannot distinguish from an omission.
    """
    errors = _errors_for_route(
        tmp_path, "kind: command\n    tool: t\n    argv: [t]\n    package:"
    )
    assert any("package" in e for e in errors), errors
    assert errors == _errors_for_route(
        tmp_path, "kind: command\n    tool: t\n    argv: [t]\n    package: null"
    )


def test_a_package_is_written_only_where_it_differs(tmp_path):
    check = _one_route_record(
        tmp_path,
        "kind: command\n    tool: import-linter\n    package: import-linter"
        "\n    registry: pypi\n    argv: [lint-imports]",
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
    assert any("no command at all" in e for e in errors), errors


def test_a_command_route_may_name_per_partition_commands_and_no_shared_argv(tmp_path):
    """`deps/inventory` prescribes a subcommand per dependency file and none for PEP 751.

    Read as default-plus-overrides, a shared argv makes an unnamed partition
    inherit rather than have none, and there is no command to inherit that
    would be true: `cyclonedx-py requirements` on a tree with no requirements
    file runs and answers about nothing.
    """
    errors = _errors_for_route(
        tmp_path,
        "kind: command\n    tool: t\n    registry: pypi\n"
        "    argv_by_partition:\n      uv: [t, u]\n      pip: [t, p]",
    )
    assert errors == []


def test_a_command_route_carrying_neither_argv_nor_per_partition_commands_is_rejected(
    tmp_path,
):
    """The relaxation is about where the command lives, not about having one."""
    errors = _errors_for_route(tmp_path, "kind: command\n    tool: t")
    assert any("no command at all" in e for e in errors), errors


def test_an_argv_that_is_not_a_list_of_strings_is_rejected(tmp_path):
    """`_str_list` returns `None` for a value that is not a list of strings,
    the same as for an absent key, so a bare string written beside
    `argv_by_partition` would otherwise pass as an absent shared argv rather
    than as the mistake it is.
    """
    errors = _errors_for_route(
        tmp_path,
        "kind: command\n    tool: t\n    argv: deptry\n"
        "    argv_by_partition:\n      uv: [t, u]",
    )
    assert any("argv must be a list of argv strings" in e for e in errors), errors


def test_an_empty_argv_beside_per_partition_commands_is_rejected(tmp_path):
    """`_str_list([]) or ()` and `_str_list(None) or ()` both evaluate to
    `()`, but only the absent key is the deliberate omission that lets a
    partition the map does not name have no command; a written empty list
    says nothing and is rejected on its own terms.
    """
    errors = _errors_for_route(
        tmp_path,
        "kind: command\n    tool: t\n    argv: []\n"
        "    argv_by_partition:\n      uv: [t, u]",
    )
    assert any("argv is present and empty" in e for e in errors), errors


@pytest.mark.parametrize("key", ["argv_by_partition", "then", "own_runner"])
def test_the_other_get_read_keys_reject_a_value_left_off_too(tmp_path, key):
    """The same rule on the three siblings, held so the guard cannot narrow.

    None of these three inverts a claim the way `argv` does, which is why the
    sibling below is the one with the long reason. They are here because the
    guard is written as a loop over four keys, and a loop is exactly the shape
    that quietly loses a member: dropping one from the tuple would leave a key
    reading a bare value as an absent one with nothing going red. Held on a
    route that is otherwise valid, so the only thing failing is the key under
    test.
    """
    errors = _errors_for_route(
        tmp_path, f"kind: command\n    tool: t\n    argv: [t]\n    {key}:"
    )
    assert any(f"{key} is empty" in e for e in errors), errors


@pytest.mark.parametrize("spelling", ["argv:", "argv: ~", "argv: null"])
def test_an_argv_written_with_no_value_is_not_the_absent_key(tmp_path, spelling):
    """The three YAML spellings of nothing, which are not the absent key.

    The sibling above rejects `argv: []` because a written empty list says
    nothing. These three say nothing in exactly the same way and `entry.get`
    cannot tell them from a key that was never written - and on a command
    route the absent key is the one shape here that carries a claim, that the
    partitions `argv_by_partition` does not name have no command at all. So
    an author who meant to write a command and left the value off would have
    had that read as the opposite claim, silently.

    Parametrized over the three rather than tested once, because they reach
    the loader as the same `None` by three different routes through the YAML
    parser and a rule keyed on any one of them is a rule the other two walk
    past. `package` has carried this guard since before routes existed and
    its message names the same three; this closes the gap for `argv`, which
    opened when the shared argv became optional beside a per-partition map.

    Held on a command route because that is where the confusion inverts a
    claim, and asserted only on the message so the same rule covers the
    other kinds, where the key is rejected whatever it holds.
    """
    errors = _errors_for_route(
        tmp_path,
        f"kind: command\n    tool: t\n    {spelling}\n"
        "    argv_by_partition:\n      uv: [t, u]",
    )
    assert any("argv is empty" in e for e in errors), errors


@pytest.mark.parametrize("disposition", ["alternative", "superseded", "forbidden"])
def test_a_non_running_disposition_needs_a_command(tmp_path, disposition):
    errors = _errors_for_route(
        tmp_path, f"kind: library\n    tool: grimp\n    disposition: {disposition}"
    )
    assert any("disposition" in e for e in errors), errors


@pytest.mark.parametrize("disposition", ["alternative", "superseded"])
def test_an_offered_disposition_on_a_procedure_route_is_rejected(tmp_path, disposition):
    """`alternative` and `superseded` offer something to run instead of the
    default, and a procedure route hands the harness nothing to run, so the
    rule stays command-only for those two even though `forbidden` no longer is.
    """
    errors = _errors_for_route(
        tmp_path,
        f"kind: procedure\n    tool: grimp\n    disposition: {disposition}\n"
        "    note: read the graph",
    )
    assert any("needs kind: command" in e for e in errors), errors


def test_a_forbidden_procedure_route_names_a_tool_and_a_note(tmp_path):
    """The prohibition-with-no-invocation shape: a record warns against a
    tool it prescribes no command line for - `markdownlint` on
    `docs/source-wrapping`, `c8` around Vitest on `test/coverage-reach`. On a
    command route the argv is what is forbidden; here the tool is, and the
    note is what says why, so both are required and the route loads.
    """
    check = _one_route_record(
        tmp_path,
        "kind: procedure\n    tool: markdownlint\n    disposition: forbidden\n"
        "    note: MD013 is the opposite rule and must not be substituted",
    )
    route = check.routes[0]
    assert (route.kind, route.tool, route.disposition) == (
        "procedure",
        "markdownlint",
        "forbidden",
    )


def test_a_forbidden_procedure_route_without_a_tool_is_rejected(tmp_path):
    """A route forbidding neither a command nor a tool forbids nothing. One
    mistake, one message: the missing tool is named and the note rule, which
    would otherwise also fire on a tool-less procedure route, is not.
    """
    errors = _errors_for_route(
        tmp_path, "kind: procedure\n    disposition: forbidden\n    note: never run it"
    )
    assert any("tool is required on a disposition: forbidden" in e for e in errors), (
        errors
    )
    assert not any("needs a note" in e for e in errors), errors


def test_a_forbidden_procedure_route_without_a_note_is_rejected(tmp_path):
    """With no argv to forbid, the note is the whole of the warning."""
    errors = _errors_for_route(
        tmp_path, "kind: procedure\n    tool: c8\n    disposition: forbidden"
    )
    assert any("forbidden procedure route needs a note" in e for e in errors), errors
    errors = _errors_for_route(
        tmp_path,
        "kind: procedure\n    tool: c8\n    disposition: forbidden\n    note: ''",
    )
    assert any("forbidden procedure route needs a note" in e for e in errors), errors


def test_an_untiered_forbidden_procedure_route_does_not_satisfy_the_escape(tmp_path):
    """The `arch/coupling` shape with the forbidden route as a procedure: a
    tiered instrument beside a warned-against tool needing no grant is still a
    silenced language, and the sentinel is still required.
    """
    errors = _errors_for_routes(
        tmp_path,
        [
            {
                "lang": "typescript",
                "kind": "command",
                "tool": "vitest",
                "argv": ["vitest", "run", "--coverage"],
                "needs": "target-execution",
            },
            {
                "lang": "typescript",
                "kind": "procedure",
                "tool": "c8",
                "disposition": "forbidden",
                "note": "never around a Vitest command",
            },
        ],
    )
    assert any("answers_ungranted" in e and "typescript" in e for e in errors), errors


def test_a_forbidden_procedure_route_is_outside_the_answers_scope(tmp_path):
    """A forbidden route answers no axis, so an axised language may carry one
    without the field and is not half-axised by it; the route may not carry
    the field itself.
    """
    check, errors = _two_route_record(
        tmp_path,
        "lang: typescript\n    kind: command\n    tool: a\n    argv: [a]\n    answers: measurement",
        "lang: typescript\n    kind: procedure\n    answers: configuration\n    note: read the config",
        "lang: typescript\n    kind: procedure\n    tool: c8\n    disposition: forbidden\n"
        "    note: never around a Vitest command",
    )
    assert errors == [], errors
    assert [r.answers for r in check.routes] == ["measurement", "configuration", None]
    _, errors = _two_route_record(
        tmp_path,
        "lang: typescript\n    kind: command\n    tool: a\n    argv: [a]\n    answers: measurement",
        "lang: typescript\n    kind: procedure\n    answers: configuration\n    note: read the config",
        "lang: typescript\n    kind: procedure\n    tool: c8\n    disposition: forbidden\n"
        "    answers: measurement\n    note: never around a Vitest command",
    )
    assert any("forbidden" in e and "answers" in e for e in errors), errors


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


def test_a_non_string_route_key_is_reported_rather_than_raised(tmp_path):
    """YAML admits a mapping key that is not a string - `1: extra` parses to
    an int - and the unknown-key sweep sorts the keys a route carries that
    the schema does not know. Sorting a set holding an int beside a string
    raises `TypeError`, and `_load_routes` is reached from `load_checks`,
    which promises to collect problems rather than raise: the traceability
    gate would then stop on one malformed record with a traceback in place
    of the other records' messages. A key of any other type names no route
    field either, so it is reported in its own right rather than passed
    over.
    """
    errors = _errors_for_route(
        tmp_path, "kind: command\n    tool: t\n    argv: [t]\n    1: extra"
    )
    assert any("not a string" in e for e in errors), errors


def test_a_non_string_route_key_beside_a_string_one_reports_both(tmp_path):
    """The mixed set is the shape that raises - a set of ints alone sorts
    fine - so the two kinds of key have to arrive together for the guard to
    be exercised at all, and both must be named: reporting one and dropping
    the other would fix the crash by hiding half the record's problems.
    """
    errors = _errors_for_route(
        tmp_path,
        "kind: command\n    tool: t\n    argv: [t]\n    1: extra\n    weird: whatever",
    )
    assert any("not a string" in e for e in errors), errors
    assert any("weird" in e for e in errors), errors


@pytest.mark.parametrize(
    "field,route_body",
    [
        ("tool", "kind: command\n    tool: [t]\n    argv: [t]"),
        (
            "package",
            "kind: command\n    tool: t\n    package: [t]\n    argv: [t]",
        ),
        (
            "argv_by_partition",
            "kind: command\n    tool: t\n    argv: [t]\n    argv_by_partition: [x]",
        ),
        (
            "argv_by_partition",
            "kind: command\n    tool: t\n    argv: [t]\n"
            "    argv_by_partition:\n      pnpm: not-a-list",
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
        (
            "registry",
            "kind: command\n    tool: t\n    argv: [t]\n    registry: [oops]",
        ),
    ],
)
def test_a_wrong_typed_route_field_is_rejected(tmp_path, field, route_body):
    """Every `_load_routes` branch that rejects a wrong-typed value has a row.

    Written after a review found eight of them untested, and kept as a row per
    branch rather than a count, because the population grows with the schema:
    `registry` arrived with #77 and its type check would otherwise have been
    the ninth branch nobody exercised. A field added here without a row is the
    same silence as before - the loader has the check and nothing proves it
    fires. Assert only that the field name appears in the message, not the
    message's full text.
    """
    errors = _errors_for_route(tmp_path, route_body)
    assert any(field in e for e in errors), errors


def test_a_record_may_not_carry_both_schemas(tmp_path):
    errors = _errors_for_both_schemas(tmp_path)
    assert any("routes" in e and "tooling" in e for e in errors), errors


def test_argv_by_partition_maps_a_partition_to_a_command(tmp_path):
    check = _one_route_record(
        tmp_path,
        "kind: command\n    tool: dependency-cruiser\n    registry: npm\n    argv: [depcruise]\n"
        "    argv_by_partition:\n      pnpm: [pnpm, dlx, depcruise]",
    )
    assert check.routes[0].argv_by_partition == {"pnpm": ("pnpm", "dlx", "depcruise")}


def test_argv_by_partition_needs_a_command_kind(tmp_path):
    errors = _errors_for_route(
        tmp_path,
        "kind: library\n    tool: grimp\n    argv_by_partition:\n      pnpm: [x]",
    )
    assert any("argv_by_partition" in e for e in errors), errors


def test_an_argv_by_partition_entry_must_be_non_empty(tmp_path):
    """`argv` on a command route is required to be non-empty, and a
    per-partition argv is the command that replaces it on a target using
    that partition. An empty list there declares a partition the route
    names and supplies nothing to run for it, which is the same absence the
    rule on `argv` exists to reject - and `_str_list` returns an empty tuple
    rather than `None` for it, so the mapping's own type check passes it
    through.
    """
    errors = _errors_for_route(
        tmp_path,
        "kind: command\n    tool: t\n    argv: [t]\n"
        "    argv_by_partition:\n      pnpm: []",
    )
    assert any("argv_by_partition" in e and "pnpm" in e for e in errors), errors


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
    assert any("argv_by_manager" in e and "unknown route key" in e for e in errors), (
        errors
    )


def test_a_route_carries_a_second_command_in_sequence(tmp_path):
    check = _one_route_record(
        tmp_path,
        "kind: command\n    tool: coverage.py\n    registry: pypi\n    argv: [coverage, run, -m, pytest]"
        "\n    then: [coverage, report, --show-missing]",
    )
    assert check.routes[0].then == ("coverage", "report", "--show-missing")


def test_a_route_carries_no_second_command_by_default(tmp_path):
    check = _one_route_record(
        tmp_path, "kind: command\n    tool: t\n    registry: pypi\n    argv: [t]"
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


def test_a_registry_names_where_the_tool_is_fetched_from(tmp_path):
    check = _one_route_record(
        tmp_path,
        "lang: any\n    kind: command\n    tool: diff-cover"
        "\n    registry: pypi\n    argv: [diff-cover]",
    )
    assert check.routes[0].registry == "pypi"


@pytest.mark.parametrize("kind", ["library", "procedure", "subject"])
def test_a_registry_on_a_non_command_kind_is_rejected(tmp_path, kind):
    """Only a command route prescribes something a runner goes in front of."""
    errors = _errors_for_route(
        tmp_path, f"kind: {kind}\n    tool: t\n    registry: pypi"
    )
    assert any("registry" in e and kind in e for e in errors), errors


def test_a_bare_registry_key_is_rejected(tmp_path):
    """Written-but-empty is its own mistake, and it bypassed two rules.

    YAML reads a bare key as `null`, so `registry:` with no value reached the
    kind and `own_runner` checks as `None` and passed both - a
    `kind: procedure` route could declare the field and load clean. The two
    commits before this branch fixed the same class for `argv` and its three
    neighbours; the new field was added without joining them.
    """
    errors = _errors_for_route(tmp_path, "kind: procedure\n    tool: t\n    registry:")
    assert any("registry is empty" in e for e in errors), errors


def test_a_bare_registry_still_fails_the_kind_rule(tmp_path):
    """The bypass, stated as the shape it let through rather than as the key.

    The empty-value error alone would be satisfied by rejecting the key and
    stopping, so this holds the thing that mattered: a procedure route
    declaring a registry is rejected whether or not it named one.
    """
    named = _errors_for_route(
        tmp_path, "kind: procedure\n    tool: t\n    registry: pypi"
    )
    assert any("registry" in e and "procedure" in e for e in named), named


def test_a_rejected_registry_is_not_also_reported_as_a_missing_one(tmp_path):
    """A typo must not produce a second error naming a fix already applied.

    The vocabulary check resets the value to `None`, and the required rule
    reads `None`, so `registry: pypy` on a universal command route used to
    report both "not one of" and "needs a registry" - the second false about
    the record, and pointing the author at the field they had just written.
    """
    errors = _errors_for_route(
        tmp_path,
        "lang: any\n    kind: command\n    tool: t\n    registry: pypy\n    argv: [t]",
    )
    assert any("not one of" in e for e in errors), errors
    assert not any("needs a registry" in e for e in errors), errors


def test_a_wrong_typed_registry_is_rejected_as_a_type_and_not_as_a_vocabulary_miss(
    tmp_path,
):
    """The parametrized row above cannot tell these two branches apart.

    It asserts only that the field name appears, and a non-string value fails
    the vocabulary check too - no list is a member of `REGISTRIES` - so
    deleting the type check entirely leaves that row green. Checked by doing
    it. This one pins the type message, which is the only assertion that
    distinguishes "you wrote the wrong shape" from "you wrote a registry
    nobody supports", and those want different fixes from a record author.
    """
    errors = _errors_for_route(
        tmp_path,
        "lang: any\n    kind: command\n    tool: t\n    registry: [oops]"
        "\n    argv: [t]",
    )
    assert any("registry must be a string" in e for e in errors), errors


def test_a_registry_outside_the_vocabulary_is_rejected(tmp_path):
    """An unrecognised registry reads to a consumer as no registry at all.

    Which is the failure the field exists to prevent, so a typo or a registry
    nobody has decided to support has to be an error rather than a value that
    silently falls back to the partition's runner.
    """
    errors = _errors_for_route(
        tmp_path,
        "lang: any\n    kind: command\n    tool: t\n    registry: crates"
        "\n    argv: [t]",
    )
    assert any("registry" in e and "crates" in e for e in errors), errors


def test_a_registry_beside_own_runner_true_is_rejected(tmp_path):
    """`own_runner: true` says nothing is fetched, so a registry names nowhere.

    The mirror of the loader's existing refusal of `own_runner` beside
    `in_env`: there the suppressed prefix never arrives, here the named
    registry is never reached.
    """
    errors = _errors_for_route(
        tmp_path,
        "lang: any\n    kind: command\n    tool: wc\n    registry: npm"
        "\n    argv: [wc, -l]\n    own_runner: true",
    )
    assert any("registry" in e and "own_runner" in e for e in errors), errors


def test_a_registry_contradicting_its_lang_is_rejected(tmp_path):
    """A `lang: python` route on npm is a wrong `lang` or a typo, never both true.

    Accepting the disagreement would let the field mean whichever of the two a
    consumer happened to read first, which is worse than not having it: a
    record can then declare a registry and still be fetched from the other one.
    """
    errors = _errors_for_route(
        tmp_path,
        "lang: python\n    kind: command\n    tool: t\n    registry: npm"
        "\n    argv: [t]",
    )
    assert any("registry" in e and "lang" in e for e in errors), errors


def test_a_universal_command_route_without_a_registry_is_rejected(tmp_path):
    """Neither `any` nor `none` implies one, so nothing else in the record says."""
    errors = _errors_for_route(
        tmp_path, "lang: any\n    kind: command\n    tool: t\n    argv: [t]"
    )
    assert any("registry" in e and "any" in e for e in errors), errors


def test_the_requirement_does_not_exempt_a_defaulted_lang(tmp_path):
    """`lang` defaults to `any`, and a consumer cannot tell that from a declared one.

    So the rule reads the value rather than whether it was written. This is the
    one ergonomic cost of the field: a command route that omits `lang` has to
    name a registry, where before it loaded clean on the default alone.
    """
    errors = _errors_for_route(tmp_path, "kind: command\n    tool: t\n    argv: [t]")
    assert any("registry" in e for e in errors), errors


def test_a_language_specific_route_needs_no_registry(tmp_path):
    """The requirement is scoped to where the registry is underivable."""
    check = _one_route_record(
        tmp_path, "lang: python\n    kind: command\n    tool: t\n    argv: [t]"
    )
    assert check.routes[0].registry is None
    assert ac.registry_for(check.routes[0]) == "pypi"


def test_registry_for_reads_the_route_then_the_lang_then_nothing(tmp_path):
    """The three outcomes, because a caller must not conflate the last two.

    `None` means put no runner in front; a derived value means put this one
    there. A caller treating `None` as "use the default" fetches a package
    named after a coreutils binary, which is exactly the `wc` route.
    """
    declared = _one_route_record(
        tmp_path,
        "lang: any\n    kind: command\n    tool: cloc\n    registry: npm"
        "\n    argv: [cloc]",
    )
    assert ac.registry_for(declared.routes[0]) == "npm"

    complete = _one_route_record(
        tmp_path,
        "lang: any\n    kind: command\n    tool: wc\n    argv: [wc, -l]"
        "\n    own_runner: true",
    )
    assert ac.registry_for(complete.routes[0]) is None

    nothing_to_run = _one_route_record(
        tmp_path, "lang: python\n    kind: procedure\n    tool: t"
    )
    assert ac.registry_for(nothing_to_run.routes[0]) is None


# The first word of a command that leaves nothing for a one-shot runner to go in
# front of: a package manager whose subcommand is run directly, or a runner the
# argv already spells. Both are `registry_for`'s two reasons for answering a
# route that needs no fetch, which is the trap its docstring warns about.
_RUNS_ITSELF = frozenset(
    {
        "npm",
        "pnpm",
        "yarn",
        "pip",
        "poetry",
        "pipenv",
        "uv",
        "npx",
        "dlx",
        "uvx",
        "pipx",
    }
)


def test_the_registry_requirement_is_not_vacuous():
    """The rule fires on routes that exist, and the count is the guard.

    A rule whose population leaves the tree stops being tested by the record
    set, and this one is easy to empty by accident: give both universal
    command routes an `own_runner` and the requirement never fires again,
    while every test above still passes on its synthetic records.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == [], errors
    required = [
        (check.id, index)
        for check in checks.values()
        for index, route in enumerate(check.routes or ())
        if route.kind == "command"
        and route.lang in ac.UNIVERSAL_ROUTE_LANGS
        and route.own_runner is not True
    ]
    assert len(required) == 11, (
        f"the registry requirement fires on {sorted(required)}; the tree carried "
        "two such routes when the rule was written - `arch/size`'s `cloc` and "
        "`test/new-code-coverage`'s `diff-cover` - five more arrived with the "
        "security migration, each a Python-registry scanner a TypeScript partition "
        "fetches with a Python runner: `semgrep` on the four code checks and "
        "`detect-secrets` on `security/secrets-in-code`, and four with the ci "
        "migration, `zizmor` on each record that names it, a PyPI package a "
        "workflow partition of any language fetches with `uvx`. A change here means "
        "a universal command route arrived or left, and either way the rule and "
        "this floor want re-reading rather than the number being edited to match"
    )
    assert all(
        route.registry is not None
        for check in checks.values()
        for route in (check.routes or ())
        if route.kind == "command"
        and route.lang in ac.UNIVERSAL_ROUTE_LANGS
        and route.own_runner is not True
    )


def test_a_per_partition_argv_names_the_partitions_needing_no_runner(tmp_path):
    check = _one_route_record(
        tmp_path,
        "kind: command\n    tool: cyclonedx-py\n    registry: pypi\n    argv: [cyclonedx-py, requirements]"
        "\n    argv_by_partition:\n      uv: [uv, export, --frozen]"
        "\n    own_runner: [uv]",
    )
    assert check.routes[0].own_runner == ("uv",)


def test_own_runner_true_covers_a_routes_per_partition_commands_too(tmp_path):
    """`true` is a claim about every command the route prescribes.

    It was briefly rejected beside `argv_by_partition`, on the reading that
    naming commands per partition makes a blanket claim ambiguous. The
    record set says otherwise: the four `dependency-cruiser` routes carry a
    runner-led shared `argv` and runner-led `pnpm` and `yarn` overrides, so
    every command in them is complete as written, and a rule refusing `true`
    there leaves the shared form - the one an unnamed partition runs - with
    no way to say so at all. The list form stays for the partial case, so
    the two shapes divide as all-of-them against these-named-ones.
    """
    check = _one_route_record(
        tmp_path,
        "kind: command\n    tool: t\n    argv: [t]"
        "\n    argv_by_partition:\n      uv: [uv, export]\n    own_runner: true",
    )
    assert check.routes[0].own_runner is True


def test_own_runner_as_an_empty_list_is_rejected(tmp_path):
    """An empty list loads to exactly what an absent key loads to.

    So it claims nothing while reading as a considered claim - the shape
    `own_runner: false` is rejected for, and the one a later edit produces by
    deleting the last partition name from a list that had one.
    """
    errors = _errors_for_route(
        tmp_path,
        "kind: command\n    tool: t\n    argv: [t]"
        "\n    argv_by_partition:\n      uv: [uv, export]\n    own_runner: []",
    )
    assert any("claims nothing" in e for e in errors), errors


@pytest.mark.parametrize(
    "written",
    [
        "argv: [t, run]\n    then: [t, run]",
        "argv: [t, run]\n    argv_by_partition:\n      uv: [t, alt]\n"
        "    then: [t, alt]",
    ],
)
def test_a_then_repeating_a_command_the_route_prescribes_is_rejected(tmp_path, written):
    """Two halves of one sequence cannot be the same command.

    A consumer building the route's declared forms takes one from the argv and
    one from the `then`, so a repeat declares the same form twice - and a form
    declared twice is the ambiguity a form list cannot carry. Rejected here
    rather than left to the consumer, because there the whole enumeration
    raises and every routed row goes with it.
    """
    errors = _errors_for_route(tmp_path, f"kind: command\n    tool: t\n    {written}")
    assert any("written twice" in e for e in errors), errors


def test_own_runner_naming_partitions_without_per_partition_argvs_is_rejected(
    tmp_path,
):
    errors = _errors_for_route(
        tmp_path, "kind: command\n    tool: t\n    argv: [t]\n    own_runner: [uv]"
    )
    assert any("own_runner" in e and "does not distinguish" in e for e in errors), (
        errors
    )


def test_own_runner_naming_a_partition_the_route_does_not_carry_is_rejected(tmp_path):
    errors = _errors_for_route(
        tmp_path,
        "kind: command\n    tool: t\n    argv: [t]"
        "\n    argv_by_partition:\n      uv: [uv, export]\n    own_runner: [poetry]",
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
    assert any("own_runner" in e and "its own opposite" in e for e in errors), errors


def test_own_runner_that_is_neither_true_nor_a_list_is_rejected(tmp_path):
    errors = _errors_for_route(
        tmp_path, "kind: command\n    tool: t\n    argv: [t]\n    own_runner: 1"
    )
    assert any("own_runner" in e for e in errors), errors


def test_a_route_defaults_to_the_any_language(tmp_path):
    """No test above names `lang:` on a route, and every one of them must
    still load clean - so the default has to be a value nothing in
    `ROUTE_LANGS` treats as an error. `any` is that value, and it is also
    the one `_routes_answering_ungranted` spreads over every language.
    """
    check = _one_route_record(
        tmp_path, "kind: command\n    tool: t\n    registry: pypi\n    argv: [t]"
    )
    assert check.routes[0].lang == "any"


def test_an_unrecognized_lang_earns_one_error_and_not_the_registry_s_too(tmp_path):
    """One authoring mistake, one message.

    An unrecognized `lang` is recovered as `any` so the rest of the route
    still reports its own problems. `any` is also what the registry
    requirement fires on, so the recovery used to earn a second error
    demanding a registry - a field that stops being required the moment
    `lang` is corrected, demanded under a language the record never wrote.
    An author reading that adds `registry: pypi` to a route that wanted
    `lang: python`, which loads clean and is wrong.

    The recovery still happens, and every other rule still sees `any`; only
    the requirement that exists *because* `any` implies no registry is
    skipped, since a recovered `any` is not the author's claim.
    """
    errors = _errors_for_route(
        tmp_path,
        "lang: pyhton\n    kind: command\n    tool: ruff\n    argv: [ruff, check]",
    )
    assert len(errors) == 1, errors
    assert "lang must be one of" in errors[0], errors
    assert "needs a registry" not in errors[0], errors


def test_a_genuinely_universal_route_still_needs_its_registry(tmp_path):
    """The complement of the test above, so the suppression cannot go wide.

    Skipping the requirement on a recovered `lang` is right; skipping it on a
    written one would remove the rule this branch exists to add, and nothing
    else in the suite reads the two cases against each other.
    """
    errors = _errors_for_route(
        tmp_path,
        "lang: any\n    kind: command\n    tool: ruff\n    argv: [ruff, check]",
    )
    assert any("needs a registry" in e for e in errors), errors


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


def test_an_empty_routes_list_is_rejected(tmp_path):
    """`routes: []` is the schema declared and then not stated, and nothing
    downstream can tell it from a record that never declared it: it projects
    to no tooling and no needs, it silences no language, and so it is never
    asked for `answers_ungranted`. Left accepted, a migration that emptied a
    record's routes would read as a record declaring no routes rather
    than as the mistake it is. The record must be named in the message,
    because the loader collects rather than raises and a bare complaint about
    an empty list points at no file.
    """
    text = _routes_frontmatter("kind: command\n    tool: t\n    argv: [t]").replace(
        "routes:\n  - kind: command\n    tool: t\n    argv: [t]\n",
        "routes: []\n",
    )
    _write(tmp_path, "demo-audit/checks/thing.md", text)
    checks, errors = ac.load_checks(tmp_path)
    assert any("routes is empty" in e for e in errors), errors
    assert all("demo-audit/checks/thing.md" in e for e in errors), errors
    assert "demo/thing" not in checks


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
    registry: pypi
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


_UNSET = object()


def _frontmatter_from_route_dicts(routes, answers_ungranted=_UNSET):
    """Render a fixture record whose `routes:` list is built from route
    dicts as plain data, for the tests below that assemble several routes
    at once instead of one literal route body at a time (`_routes_frontmatter`
    above serves the latter).

    `answers_ungranted`, when given, is written as a raw frontmatter line
    rather than round-tripped through `yaml.safe_dump`: PyYAML quotes a
    Python string like `"null"` or `""` so it re-parses as an ordinary
    string, not as YAML's own null - which would silently divert the
    miscased-sentinel tests below away from the branch they exist to
    exercise. `_UNSET` is what tells "no answers_ungranted key at all" apart
    from "the key with an empty value", which those tests need to keep
    separate too.
    """
    routes_yaml = yaml.safe_dump({"routes": routes}, sort_keys=False)
    text = (
        "---\n"
        "id: demo/thing\n"
        "domain: demo\n"
        "locality: local\n"
        "handbook: []\n"
        "handbook_note: Fixture record for the ungranted rule.\n"
        f"{routes_yaml}"
    )
    if answers_ungranted is not _UNSET:
        text += f"answers_ungranted: {answers_ungranted}\n"
    return text + "---\n\n# Thing\n\nFixture body.\n"


def _routes_record(tmp_path, routes, answers_ungranted=_UNSET):
    """Write a record whose `routes:` list is built from route dicts,
    assert the load produced no errors, and return the loaded Check.
    """
    text = _frontmatter_from_route_dicts(routes, answers_ungranted)
    _write(tmp_path, "demo-audit/checks/thing.md", text)
    checks, errors = ac.load_checks(tmp_path)
    assert errors == [], errors
    return checks["demo/thing"]


def _errors_for_routes(tmp_path, routes, answers_ungranted=_UNSET):
    """Write a record whose `routes:` list is built from route dicts, and
    return the error list instead of the Check.
    """
    text = _frontmatter_from_route_dicts(routes, answers_ungranted)
    _write(tmp_path, "demo-audit/checks/thing.md", text)
    _, errors = ac.load_checks(tmp_path)
    return errors


def test_a_language_whose_every_route_is_tiered_must_say_what_answers(tmp_path):
    errors = _errors_for_routes(
        tmp_path,
        [
            {
                "lang": "python",
                "kind": "command",
                "tool": "t",
                "argv": ["t"],
                "needs": "resolved-tree",
            }
        ],
    )
    assert any("answers_ungranted" in e and "python" in e for e in errors), errors


def test_an_untiered_route_in_the_same_language_answers_it(tmp_path):
    check = _routes_record(
        tmp_path,
        [
            {
                "lang": "python",
                "kind": "command",
                "tool": "t",
                "argv": ["t"],
                "needs": "resolved-tree",
            },
            {"lang": "python", "kind": "procedure", "note": "read the config"},
        ],
    )
    assert check.answers_ungranted is None


@pytest.mark.parametrize("lang", ["any", "none"])
def test_an_untiered_universal_route_answers_a_tiered_language(tmp_path, lang):
    """`lang: any` and `lang: none` both mean the route applies whatever the
    partition's language is - that is the whole difference between them and
    a named language, and `audit-core/SKILL.md` states it as the rule an
    executing agent follows. So an untiered universal route is what still
    answers for Python once the grant is withheld, and grouping the routes
    under their literal `lang` alone would demand `answers_ungranted: none`
    from a record that plainly has something left to run - a false claim
    forced into frontmatter by the rule that exists to keep false claims out
    of it.
    """
    check = _routes_record(
        tmp_path,
        [
            {
                "lang": "python",
                "kind": "command",
                "tool": "t",
                "argv": ["t"],
                "needs": "target-execution",
            },
            {"lang": lang, "kind": "procedure", "note": "walk the AST by hand"},
        ],
    )
    assert check.answers_ungranted is None
    assert ac._silenced_languages(check.routes) == ()


@pytest.mark.parametrize(
    "rescue",
    [
        {"lang": "any", "kind": "subject", "tool": "ruff"},
        {
            "lang": "any",
            "kind": "command",
            "tool": "depcruise",
            "argv": ["depcruise"],
            "disposition": "forbidden",
        },
    ],
)
def test_a_universal_route_rescues_only_where_it_answers(tmp_path, rescue):
    """Applying to every language does not make a route an answer. The two
    exclusions the grouping already applies hold across languages exactly as
    they hold within one: a `kind: subject` route names what the check
    inspects rather than what runs it, and a `disposition: forbidden` route
    is one the record warns against running rather than one it offers.
    Either read as a universal escape would silence a record without it ever
    saying what answers, which is the silence this rule exists to prevent,
    produced by the rule itself.
    """
    errors = _errors_for_routes(
        tmp_path,
        [
            {
                "lang": "python",
                "kind": "command",
                "tool": "t",
                "argv": ["t"],
                "needs": "target-execution",
            },
            rescue,
        ],
    )
    assert any("answers_ungranted" in e and "python" in e for e in errors), errors


def test_a_subject_route_does_not_answer_the_check(tmp_path):
    errors = _errors_for_routes(
        tmp_path,
        [
            {
                "lang": "python",
                "kind": "command",
                "tool": "t",
                "argv": ["t"],
                "needs": "target-execution",
            },
            {"lang": "python", "kind": "subject", "tool": "ruff"},
        ],
    )
    assert any("answers_ungranted" in e for e in errors), errors


def test_the_sentinel_satisfies_the_rule(tmp_path):
    check = _routes_record(
        tmp_path,
        [
            {
                "lang": "python",
                "kind": "command",
                "tool": "t",
                "argv": ["t"],
                "needs": "resolved-tree",
            }
        ],
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
        [
            {
                "lang": "python",
                "kind": "command",
                "tool": "t",
                "argv": ["t"],
                "needs": "resolved-tree",
            }
        ],
        answers_ungranted=spelling,
    )
    assert any("answers_ungranted" in e for e in errors), errors


def test_no_routes_at_all_is_not_silenced():
    """`all()` is vacuously true over an empty list. A route tuple carrying
    nothing has offered no answering route for any language, so if
    `_silenced_languages` ever stopped treating that as no claim at all,
    every record declaring no routes would acquire an unmet demand for
    `answers_ungranted`.

    Asserted against the function rather than through a loaded record,
    because a record whose frontmatter says `routes: []` does not load: it is
    rejected as the schema declared and then not stated. A record omitting the
    key reaches the function with the same empty tuple.
    """
    assert ac._routes_answering_ungranted(()) == {}
    assert ac._silenced_languages(()) == ()


def test_answers_ungranted_without_routes_is_rejected(tmp_path):
    """`answers_ungranted` only means something alongside a `routes:` list:
    it says no route answers without a grant, and a record with no routes has
    none to say that of.
    """
    check = _record(extra="answers_ungranted: none\n")
    _, errors = _load_one(tmp_path, check)
    assert any("answers_ungranted" in e and "routes" in e for e in errors), errors


def test_a_non_string_sentinel_is_rejected(tmp_path):
    errors = _errors_for_routes(
        tmp_path,
        [
            {
                "lang": "python",
                "kind": "command",
                "tool": "t",
                "argv": ["t"],
                "needs": "resolved-tree",
            }
        ],
        answers_ungranted="[a, b]",
    )
    assert any(
        "answers_ungranted" in e and "must be the sentinel" in e for e in errors
    ), errors


def test_a_blank_sentinel_is_rejected(tmp_path):
    errors = _errors_for_routes(
        tmp_path,
        [
            {
                "lang": "python",
                "kind": "command",
                "tool": "t",
                "argv": ["t"],
                "needs": "resolved-tree",
            }
        ],
        answers_ungranted='"   "',
    )
    assert any("answers_ungranted" in e and "blank" in e for e in errors), errors


def test_prose_is_rejected_the_dissolution_says_it_with_a_route(tmp_path):
    """`answers_ungranted` is not a free-form note: a record that has something
    to say about what still answers says it with an untiered route, which is
    the entire point of the field accepting only the sentinel. Prose here is rejected even though it is not the
    miscased sentinel.
    """
    errors = _errors_for_routes(
        tmp_path,
        [
            {
                "lang": "python",
                "kind": "command",
                "tool": "t",
                "argv": ["t"],
                "needs": "resolved-tree",
            }
        ],
        answers_ungranted="reading the ast answers this",
    )
    assert any(
        "answers_ungranted" in e and "accepts only the sentinel" in e for e in errors
    ), errors


def test_routes_answering_ungranted_excludes_subject_routes():
    """Direct unit test of `_routes_answering_ungranted`: a `kind: subject`
    route must never appear in the untiered set this function hands to the
    silencing rule, in either direction - it does not supply the escape,
    and its language still counts as having only tiered answering routes.
    """
    routes, errors = ac._load_routes(
        [
            {
                "lang": "python",
                "kind": "command",
                "tool": "t",
                "argv": ["t"],
                "needs": "resolved-tree",
            },
            {"lang": "python", "kind": "subject", "tool": "ruff"},
        ],
        "demo-audit/checks/thing.md",
    )
    assert errors == []
    assert ac._routes_answering_ungranted(routes) == {"python": ()}


def test_routes_answering_ungranted_spreads_a_universal_route():
    """Direct unit test of the universal spread: an untiered `lang: any` or
    `lang: none` route is filed under every language the record answers
    for, because that is what those two values mean - the route applies
    whatever the partition's language is. Asserted on the mapping rather
    than only through `_silenced_languages`, so the spread is pinned where
    it happens: the counting helper this module uses for the ungranted
    floor reads this mapping too, and a spread applied only in the
    silencing wrapper would leave the two disagreeing.
    """
    routes, errors = ac._load_routes(
        [
            {
                "lang": "python",
                "kind": "command",
                "tool": "t",
                "argv": ["t"],
                "needs": "target-execution",
            },
            {"lang": "any", "kind": "procedure", "note": "walk the AST by hand"},
        ],
        "demo-audit/checks/thing.md",
    )
    assert errors == []
    answering = ac._routes_answering_ungranted(routes)
    assert sorted(answering) == ["any", "python"]
    assert [route.lang for route in answering["python"]] == ["any"]
    assert [route.lang for route in answering["any"]] == ["any"]


def test_a_universal_route_does_not_create_a_language(tmp_path):
    """The spread reaches only languages the record already answers for. A
    language with no answering route of its own has made no claim about
    grants, so it must stay absent from the mapping rather than arrive
    carrying a universal route - the same vacuity rule that keeps an empty
    tuple from reading as a claim.
    """
    routes, errors = ac._load_routes(
        [
            {"lang": "python", "kind": "subject", "tool": "ruff"},
            {"lang": "any", "kind": "procedure", "note": "read the config"},
        ],
        "demo-audit/checks/thing.md",
    )
    assert errors == []
    assert sorted(ac._routes_answering_ungranted(routes)) == ["any"]


def test_routes_answering_ungranted_keeps_an_untiered_procedure():
    routes, errors = ac._load_routes(
        [{"lang": "python", "kind": "procedure", "note": "read it"}],
        "demo-audit/checks/thing.md",
    )
    assert errors == []
    answering = ac._routes_answering_ungranted(routes)
    assert [route.kind for route in answering["python"]] == ["procedure"]


def test_routes_answering_ungranted_omits_a_subject_only_language():
    routes, errors = ac._load_routes(
        [{"lang": "python", "kind": "subject", "tool": "ruff"}],
        "demo-audit/checks/thing.md",
    )
    assert errors == []
    assert ac._routes_answering_ungranted(routes) == {}


def test_routes_answering_ungranted_excludes_forbidden_routes():
    """Direct unit test: an untiered `disposition: forbidden` route must
    not appear in the untiered set this function hands to the silencing
    rule. This is the `arch/coupling` shape - a tiered `dependency-cruiser`
    route plus a bare `dlx depcruise` invocation that resolves to an npm
    dependency-confusion placeholder exiting 0 having touched nothing, so
    it needs no grant only because it does not run the real tool.
    """
    routes, errors = ac._load_routes(
        [
            {
                "lang": "typescript",
                "kind": "command",
                "tool": "dependency-cruiser",
                "argv": ["depcruise"],
                "needs": "resolved-tree",
            },
            {
                "lang": "typescript",
                "kind": "command",
                "tool": "depcruise",
                "argv": ["dlx", "depcruise"],
                "disposition": "forbidden",
            },
        ],
        "demo-audit/checks/thing.md",
    )
    assert errors == []
    assert ac._routes_answering_ungranted(routes) == {"typescript": ()}


def test_routes_answering_ungranted_keeps_an_untiered_alternative_route():
    """Direct unit test: unlike `forbidden`, an `alternative` route is a
    route the record does offer - just not the one it runs by default - so
    it must still appear in the untiered set.
    """
    routes, errors = ac._load_routes(
        [
            {
                "lang": "python",
                "kind": "command",
                "tool": "import-linter",
                "argv": ["lint-imports"],
                "needs": "resolved-tree",
            },
            {
                "lang": "python",
                "kind": "command",
                "tool": "tach",
                "argv": ["tach", "check"],
                "disposition": "alternative",
            },
        ],
        "demo-audit/checks/thing.md",
    )
    assert errors == []
    answering = ac._routes_answering_ungranted(routes)
    assert [route.tool for route in answering["python"]] == ["tach"]


def test_an_untiered_forbidden_route_does_not_satisfy_the_escape(tmp_path):
    """Record-level test for the `arch/coupling` shape named above: a
    forbidden route needing no grant must not let the record skip
    `answers_ungranted` - the language is genuinely silenced, because the
    record's only real instrument for it needs a grant and the untiered
    route is one it warns against running. If this regresses, a forbidden
    placeholder invocation would silently satisfy the ungranted rule for a
    real record.
    """
    errors = _errors_for_routes(
        tmp_path,
        [
            {
                "lang": "typescript",
                "kind": "command",
                "tool": "dependency-cruiser",
                "argv": ["depcruise"],
                "needs": "resolved-tree",
            },
            {
                "lang": "typescript",
                "kind": "command",
                "tool": "depcruise",
                "argv": ["dlx", "depcruise"],
                "disposition": "forbidden",
            },
        ],
    )
    assert any("answers_ungranted" in e and "typescript" in e for e in errors), errors


def test_an_untiered_alternative_route_still_answers_the_check(tmp_path):
    """Record-level complement: an `alternative` route is offered, not
    forbidden, so an untiered one satisfies the escape and the record
    needs no sentinel. If this regresses, a record naming a real
    not-run-by-default alternative would be wrongly forced to add
    `answers_ungranted: none`.
    """
    check = _routes_record(
        tmp_path,
        [
            {
                "lang": "python",
                "kind": "command",
                "tool": "import-linter",
                "argv": ["lint-imports"],
                "needs": "resolved-tree",
            },
            {
                "lang": "python",
                "kind": "command",
                "tool": "tach",
                "argv": ["tach", "check"],
                "disposition": "alternative",
            },
        ],
    )
    assert check.answers_ungranted is None


def test_a_rescued_language_needs_a_tiered_route_to_be_rescued_from(tmp_path):
    """The floor counts a record that *would* be silenced and is not - never
    one that was never at risk. The record here is the first:
    `knip` needs the tree, `ts-prune` does not, so deleting the untiered
    route would silence TypeScript.
    """
    check = _routes_record(
        tmp_path,
        [
            {
                "lang": "typescript",
                "kind": "procedure",
                "tool": "knip",
                "needs": "target-execution",
            },
            {"lang": "typescript", "kind": "procedure", "tool": "ts-prune"},
        ],
    )
    assert _languages_rescued_by_an_untiered_route(check) == ["typescript"]


def test_a_language_needing_no_grant_at_all_is_not_a_rescued_one(tmp_path):
    """The other side of the same line, and the one that keeps the floor
    from inflating: a language whose every route already answers from a
    read-only clone made no claim about grants, so it is not the
    counterpart of anything and must not be counted as one.
    """
    check = _routes_record(
        tmp_path,
        [
            {
                "lang": "python",
                "kind": "command",
                "tool": "vulture",
                "argv": ["vulture"],
            },
            {"lang": "python", "kind": "library", "tool": "grimp"},
        ],
    )
    assert _languages_rescued_by_an_untiered_route(check) == []


def test_a_subject_route_is_not_the_tier_a_language_is_rescued_from(tmp_path):
    """`kind: subject` is excluded from both sides of the ungranted rule, so
    a tiered subject route cannot be what an untiered route rescues a
    language from - the language was never silenced, because a subject route
    is not an answer. Pinned here because `arch/complexity-gate` is exactly
    this shape and the floor must not read it as a claim it does not make.
    """
    check = _routes_record(
        tmp_path,
        [
            {
                "lang": "typescript",
                "kind": "subject",
                "tool": "eslint",
                "needs": "target-execution",
            },
            {"lang": "typescript", "kind": "procedure", "tool": "ts-prune"},
        ],
    )
    assert _languages_rescued_by_an_untiered_route(check) == []


def test_a_sentinel_language_is_not_a_rescued_one(tmp_path):
    """A language answered only by tiered routes, whose withheld-grant claim
    is spelled `answers_ungranted: none` rather than answered by an untiered
    route, must not count as rescued either - the sentinel says nothing else
    answers, and reading it as a routed claim anyway would let the floor
    count the same withheld grant twice: once for needing the sentinel at
    all, once for treating the sentinel as if an untiered route had rescued
    the language it was written for.
    """
    check = _routes_record(
        tmp_path,
        [
            {
                "lang": "python",
                "kind": "command",
                "tool": "t",
                "argv": ["t"],
                "needs": "resolved-tree",
            },
        ],
        answers_ungranted="none",
    )
    assert _languages_rescued_by_an_untiered_route(check) == []


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
        "\n---\n\n# ", "\nhandbook_note: why this exceeds the handbook\n---\n\n# "
    )
    _write(tmp_path, "arch-audit/checks/layering.md", text)
    _, errors = ac.load_checks(tmp_path)
    assert any("handbook_note" in e for e in errors)


def test_a_non_string_frontmatter_key_is_reported_not_raised(tmp_path):
    """`load_checks` collects problems; a malformed record must not silence
    the rest of the tree.

    YAML admits a non-string mapping key, and sorting a set holding both a
    string and an int raises. Reached through `load_checks` rather than the
    helper, because what matters is that one bad record leaves the others
    reportable rather than that a function returns a list: the integrity gate
    runs over every record at once, and a raise there loses the whole sweep
    to whichever file happened to be malformed.
    """
    _write(
        tmp_path,
        "demo-audit/checks/thing.md",
        "---\nid: demo/thing\ndomain: demo\nlocality: local\nhandbook: []\n"
        "handbook_note: Fixture record.\n1: oops\nweird: whatever\n---\n\n# Thing\n\nBody.\n",
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("is not a string" in e for e in errors), errors
    assert any("'weird'" in e for e in errors), errors


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
    """Regression net for <origin-repo>#559 PR 2: the `/audit` front door now detects
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
        "arch/harness-bounding",
        "arch/hidden-coupling",
        "arch/import-rule-declaration",
        "arch/layering",
        "arch/martin-metrics",
        "arch/over-abstraction",
        "arch/over-decomposition",
        "arch/runtime-declaration",
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
        "deps/model-catalog-indirection",
        "deps/model-pinning-and-eol",
        "deps/transitive-licenses",
        "deps/vulnerabilities",
        "docs/coverage",
        "docs/cross-referencing",
        "docs/docstring-coverage",
        "docs/docstring-staleness",
        "docs/docstring-standard",
        "docs/organization",
        "docs/source-wrapping",
        "eval/adversarial",
        "eval/contamination",
        "eval/cost-latency",
        "eval/coverage",
        "eval/judge-calibration",
        "eval/merge-coverage-assertion",
        "eval/methodology",
        "eval/prompt-quality",
        "eval/regression-tracking",
        "eval/reproducibility",
        "eval/run-variance",
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
        "security/agent-privilege-surface",
        "security/crypto",
        "security/dangerous-calls",
        "security/injection",
        "security/secret-history",
        "security/secrets-in-code",
        "security/sensitive-data",
        "security/unsafe-io",
        "test/assertion-strength",
        "test/coverage-floor-declaration",
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


# Empty: every record declares routes. Kept as a named set rather than deleted, so a record written without `routes:` fails
# here by name instead of reading as nothing having changed.
RECORDS_DECLARING_NO_ROUTES: frozenset[str] = frozenset()


def test_the_records_declaring_no_routes_are_the_ones_named():
    """A record gaining or losing `routes:` fails until this set is updated.

    The set is every record the loader accepts without a `routes:` block: a
    record with nothing to run, whose body says what to read instead. The
    loader accepts one, so the set is empty by what the tree holds rather than
    by what the loader refuses, and a new record of that kind fails here by
    name.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert not errors, errors
    routeless = {cid for cid, check in checks.items() if not check.routes}
    assert routeless == RECORDS_DECLARING_NO_ROUTES


def test_every_tool_less_check_states_a_reading_procedure():
    """<origin-repo>#567 item 5: a check with nothing to run must say what to read
    instead, or the executing agent has nothing to run and nothing told to
    read. If this fails, write the prose or the note the named record is
    missing - do not weaken either assertion.

    Two shapes, each saying it in the one place it has. A record declaring no
    routes says it in `## Tooling fallback`. A record declaring `routes:` may
    not carry that section at all - the loader rejects one beside routes - and
    says it per route instead, in the `note` of a route naming no tool, which
    is the shape a route takes when there is nothing for the harness to run.
    Each axis of a check is its own route, so each one can be silent on its
    own, which is why the routed half reads every route naming no tool.

    **The loader now owns the routed half**, rejecting a tool-less route that
    carries no note, so `assert errors == []` below fires before `silent` can
    name anything and the routed message is unreachable on a tree that loads.
    The assertion is kept rather than deleted because the two guard different
    things - the loader rejects the record, this names which route of which
    record went silent - but a reader should not maintain the message below as
    the live guard: a failure here arrives as the loader's error list.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    prose_scope = [check_id for check_id, check in checks.items() if not check.routes]
    routed_scope = [
        check_id
        for check_id, check in checks.items()
        if any(route.tool is None for route in check.routes)
    ]
    # The prose half is a record declaring no routes, which the loader accepts
    # and which must then say what to read in that section; none exists today,
    # and the half is what guards the next one.
    assert routed_scope, sorted(routed_scope)
    missing = sorted(
        check_id
        for check_id in prose_scope
        if "\n## Tooling fallback" not in checks[check_id].path.read_text()
    )
    assert missing == [], (
        f"these checks declare no routes and state no fallback: {missing}"
    )
    silent = sorted(
        f"{check_id}: routes[{i}]"
        for check_id, check in checks.items()
        for i, route in enumerate(check.routes)
        if route.tool is None and not (route.note or "").strip()
    )
    assert silent == [], (
        f"these routes name no tool and no reading pass either: {silent}"
    )


def test_every_review_lens_paragraph_carries_a_label():
    """<origin-repo>#567 item 4: a `## Review lens` paragraph opens with a bold label
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


def _tiers_a_record_gives(check: ac.Check) -> dict[str, frozenset[str]]:
    """Each tool a record offers, mapped to the tiers its routes give it.

    Over the non-forbidden routes naming a tool, so a route the record warns
    against says nothing about what the tool needs. A tool none of whose
    routes is tiered maps to the empty set, which is the claim that every way
    the record runs it answers from a read-only clone.
    """
    tiers: dict[str, set[str]] = {}
    for route in check.routes:
        if route.tool is None or route.disposition == "forbidden":
            continue
        held = tiers.setdefault(route.tool, set())
        if route.needs is not None:
            held.add(route.needs)
    return {tool: frozenset(held) for tool, held in tiers.items()}


def test_a_tool_has_one_tier_across_the_family():
    """A tool needs the same thing everywhere, so two records that name it
    must agree on the tiers they give it. This is the guard that can see
    *into* a record's classification, and it sees only through a tool some
    other record already classified: an absent `needs` on a route is a
    positive claim that the route runs against a read-only clone, so a record
    nobody examined is indistinguishable from one deliberately left at the
    default unless the same tool is classified elsewhere. The vacuity test
    below covers the other half - that the sweep happened at all - by
    counting the records that classify anything; neither reaches a
    wrongly-defaulted tool no other record names. If this fails, classify the
    tool the same way in both records - do not weaken the assertion.

    What is compared is the set of tiers a record's routes give a tool, not
    one tier per route, because a tier belongs to how a route runs its tool:
    ESLint under a config the audit supplies needs nothing, under the
    target's own config it needs `target-execution`, and several records
    carry both routes. So this catches a record that tiers none of a tool's
    routes where the others tier one, or tiers it differently; it does not
    catch two routes running a tool the same way under different tiers, which
    only a reading keyed on the route's command could see.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    tiers_of: dict[str, tuple[frozenset[str], str]] = {}
    disagreements = []
    for check_id, check in sorted(checks.items()):
        for name, tiers in sorted(_tiers_a_record_gives(check).items()):
            if name not in tiers_of:
                tiers_of[name] = (tiers, check_id)
                continue
            seen_tiers, seen_in = tiers_of[name]
            if seen_tiers != tiers:
                disagreements.append(
                    f"{name!r}: {seen_in} says "
                    f"{sorted(seen_tiers) or 'read-only clone'}, "
                    f"{check_id} says {sorted(tiers) or 'read-only clone'}"
                )
    assert disagreements == [], "the same tool is classified two ways: " + "; ".join(
        disagreements
    )


def test_the_classification_is_not_vacuous():
    """`test_a_tool_has_one_tier_across_the_family` passes trivially on a
    tree where nothing is classified. Assert the sweep actually happened, so
    deleting every route's `needs` field fails loudly instead of turning the
    guard above into a no-op. The floor is the number of records classifying
    a tool, with no slack: a floor below that count would let a
    classification be deleted silently, and a deleted tier is not visibly
    missing - it reads as the positive claim that the route answers from a
    read-only clone. Adding a record that needs a tier therefore raises the
    floor with it. If this fails, a classification was removed - restore it
    rather than lowering the floor.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    tiered = {
        c.id: set().union(*_tiers_a_record_gives(c).values()) for c in checks.values()
    }
    classified = sorted(cid for cid, tiers in tiered.items() if tiers)
    assert len(classified) >= 23, (
        f"only {len(classified)} record(s) classify any tool: {classified}"
    )
    assert set().union(*tiered.values()) == set(ac.NEEDS_TIERS), (
        "both tiers should be in use across the family"
    )


_NO_TYPESCRIPT_LENS = {
    # Python docstring tooling with nothing on the other side; the record's
    # sweep is `lang: python` because TypeScript has no docstring node.
    "docs/docstring-coverage",
    # arch/martin-metrics and docs/docstring-coverage are the debt this sweep
    # did not clear: #5 scoped its remaining half to test-audit and
    # security-audit. Both are python-only and both are real gaps.
    "arch/martin-metrics",
}


def test_every_tooling_record_offers_a_typescript_lens():
    """`audit-core` reports `not-applicable` where a check "has no lens in
    this partition's languages", so a record offering only `python:` tools
    is how a TypeScript partition earns a clean bill of health for code
    nobody looked at. Assert the exception set rather than a count, and
    assert it by equality: a new python-only record fails because it is not
    in the set, and a record whose lens was added fails until it is removed
    from the set, so the set cannot quietly outlive the debt it names. If
    this fails, add the lens or add the record to the set with a reason; do
    not delete the assertion.

    The requirement is at least one answering-kind (`command`, `library`,
    `procedure`), non-`forbidden` route whose `lang` is `typescript`, `any` or
    `none`. A `kind: subject` route does not count: it names what the check
    inspects rather than what answers it, so a record whose every TypeScript
    route is a subject would otherwise earn the clean bill this guard exists
    to refuse. `any` and `none` both apply whatever the partition's language
    is, and `none` is how a single repo-wide fact read off configuration
    answers for every partition at once, so a record whose only untyped route
    is one of those has a TypeScript lens. A record declaring no routes is out
    of scope - it prescribes a reading pass, which needs no language.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    gaps = set()
    for check_id, check in checks.items():
        if check.routes and not any(
            route.lang in {"typescript", "any", "none"}
            and route.kind in ac.ANSWERING_ROUTE_KINDS
            and route.disposition != "forbidden"
            for route in check.routes
        ):
            gaps.add(check_id)
    assert gaps == _NO_TYPESCRIPT_LENS, (
        f"missing a TypeScript lens: {sorted(gaps - _NO_TYPESCRIPT_LENS)}; "
        f"lens added but still listed: {sorted(_NO_TYPESCRIPT_LENS - gaps)}"
    )


def test_a_routes_record_may_not_carry_a_fallback_section(tmp_path):
    """A section beside the routes is a second copy of the prescription.

    No property reads it and nothing holds it against the routes, so the
    loader refuses it, which keeps a record to one copy of what it prescribes.
    """
    text = _routes_frontmatter("kind: command\n    tool: t\n    argv: [t]")
    _write(
        tmp_path,
        "demo-audit/checks/thing.md",
        text + "\n## Tooling fallback\n\nRun `t` over the package.\n",
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("Tooling fallback" in e for e in errors), errors


@pytest.mark.parametrize("fence", ["```bash", "```", "~~~bash", "   ```"])
def test_a_record_may_not_write_a_prescription_in_a_fenced_block(tmp_path, fence):
    """The shape that hides a command from every reader of one.

    The form extractor reads inline backtick spans out of a record's body, so
    a command in a fence is invisible to it and the suite stays green over a
    prescription nothing holds against what ran. A fence is also
    the most idiomatic Markdown way to write a command, which is why the
    convention needs enforcing rather than assuming - no record uses one today,
    and nothing but this stops the next one.

    Both spellings, because a rule catching only ``` leaves the same hole open
    under three different characters, and up to three spaces of indentation,
    because that is a fence in CommonMark and four spaces is not. Every
    parameter's *closing* fence carries the opener's own indentation: written
    flush left it would be caught whatever the opener looked like, and the
    indented parameter would then pass for a reason that has nothing to do with
    what it is testing.
    """
    _write(
        tmp_path,
        "demo-audit/checks/thing.md",
        _routes_frontmatter("lang: any\n    kind: procedure\n    note: Read it.")
        + f"\n## Fix\n\n{fence}\npydeps --show-cycles\n{fence}\n",
    )
    checks, errors = ac.load_checks(tmp_path)
    # The fence is the only defect, so an empty mapping is this rule's doing.
    assert errors and all("fenced code block" in e for e in errors), errors
    # The record is absent from the mapping, which is the severity this rule
    # carries on purpose: a prescription no property can read is the
    # absent-check-reads-as-clean failure, and an integrity gate makes it a red
    # suite rather than a check that quietly stops running.
    assert checks == {}


@pytest.mark.parametrize(
    "block",
    [
        "    t: 3 blocks over the threshold",
        "    ```\n    t: 3 blocks over the threshold\n    ```",
    ],
)
def test_a_four_space_indented_block_is_not_a_fence(tmp_path, block):
    """The convention's escape, which the rule above must leave open.

    No record body carries an indented block today - computed, zero of 87 - so
    this is not protecting a use the tree makes. It is the place a record could
    show a tool's observed output, and the second parameter is why the allowance
    has to survive the fence rule rather than being incidental to it: a docs or
    prompt lens quoting a Markdown tool's output would be quoting fences, and a
    rule matching a fence at any indentation would reject the record for showing
    one.

    `arch/complexity` is the nearest thing the tree has, and it is not this: it
    shows `xenon`'s output in a route `note`, in frontmatter, as inline spans -
    which `_FENCE_RE` never sees, since it reads the body alone.
    """
    _write(
        tmp_path,
        "demo-audit/checks/thing.md",
        _record() + f"\n## Tooling fallback\n\nRead `t`'s report:\n\n{block}\n",
    )
    checks, errors = ac.load_checks(tmp_path)
    assert errors == [], errors
    assert set(checks) == {"demo/thing"}


def test_no_record_in_the_tree_carries_a_fence():
    """The rule states a convention the tree keeps, not a migration it needs.

    Read off the records rather than from the loader's own verdict, because
    `load_checks` reporting no errors would also be satisfied by a rule that
    never fires - and off the body alone, because that is what the loader reads
    and a route note in frontmatter is a different question.

    `rglob`, matching `load_checks`, so a record at the wrong depth is read here
    too. Such a record is already its own error, but a glob narrower than the
    loader's would report "no record carries a fence" about a set of records the
    loader is larger than.
    """
    fenced = []
    for path in sorted(ac.SKILLS_DIR.rglob("*.md")):
        if path.parent.name != ac.CHECKS_SUBDIR:
            continue
        _, body, _ = ac._split_frontmatter(path.read_text())
        if ac._FENCE_RE.search(body):
            fenced.append(path.relative_to(ac.SKILLS_DIR).as_posix())
    assert fenced == [], fenced


def test_a_tool_less_route_with_no_note_is_refused_by_name(tmp_path):
    """The note is the prescription where there is no tool and no argv.

    A `kind: procedure` route naming no tool is what a record writes when what
    answers the check is a reading rather than a command. Strip its note and
    the route says nothing at all, while still reading through every set guard
    over the family exactly like a route that works. It is also the one route kind where nothing downstream
    stands in: a `kind: command` route missing a note still has its argv.
    """
    errors = _errors_for_routes(tmp_path, [{"lang": "none", "kind": "procedure"}])
    assert any("naming no tool needs a note" in e for e in errors), errors


def test_a_tool_less_route_whose_note_is_blank_is_refused_too(tmp_path):
    """A whitespace-only note is the same silence as a missing one.

    Validating the type alone accepts it, and it satisfies any rule phrased as
    the key being present - which is why the check is on the stripped value.
    """
    errors = _errors_for_routes(
        tmp_path, [{"lang": "none", "kind": "procedure", "note": "   \n  "}]
    )
    assert any("naming no tool needs a note" in e for e in errors), errors


def test_a_tool_less_route_with_a_note_is_accepted(tmp_path):
    """The shape every tool-less route in the tree actually has."""
    check = _routes_record(
        tmp_path,
        [
            {
                "lang": "none",
                "kind": "procedure",
                "note": "Walk the layering edge set depth-first and record every back edge.",
            }
        ],
    )
    assert [r.tool for r in check.routes] == [None]
    assert check.routes[0].note.startswith("Walk the layering edge set")


def test_a_tool_less_command_route_earns_one_message_not_two(tmp_path):
    """`kind: command` with no tool is already named by the tool rule.

    Reporting the missing note beside it would put two errors on one mistake,
    and the note is not the fix there - the argv is.
    """
    errors = _errors_for_routes(tmp_path, [{"lang": "python", "kind": "command"}])
    assert any("only a kind: procedure route may" in e for e in errors), errors
    assert not any("naming no tool needs a note" in e for e in errors), errors


def test_the_tool_less_route_population_is_held():
    """The rule above cannot go vacuous by the shape leaving the tree.

    A length floor was the alternative considered and rejected - the shortest
    live note is comfortably long, and a floor invites padding without
    addressing this failure at all. If this fails because the count fell, a
    reading was replaced by a command or dropped; check that was intended
    rather than lowering the floor. It was once, and the floor followed: the
    `lang: any` dataflow route PR #151 removed from `security/injection`, for
    #147, answered nothing on its own, so the population fell from 57 to 56 on
    purpose; it rose to 62 when `arch/harness-bounding` arrived with six
    reading routes, one per tell; it rose to 70 when the `data-protection`
    records migrated to routes, each carrying one reading route; it rose to
    71 when `ci/trigger-safety` gained a reading for where `zizmor` cannot be
    obtained; it rose to 86 when the `eval` records migrated, eleven with
    one tool-less route and two with two; and it rose to 98 when the `prompt`
    records migrated, each carrying one reading route.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    tool_less = [(c.id, r) for c in checks.values() for r in c.routes if r.tool is None]
    assert len(tool_less) >= 98, f"only {len(tool_less)} tool-less route(s)"
    assert all(r.kind == "procedure" for _, r in tool_less)
    assert all(r.note.strip() for _, r in tool_less)


def test_a_tool_with_one_tiered_route_and_one_untiered_still_answers(tmp_path):
    """The case a per-tool reading cannot express, stated as the two readings
    disagreeing.

    `deps/inventory` is this shape: one `cyclonedx-py` route carrying the
    file-parsing subcommands untiered, and `cyclonedx-py environment` under
    `target-execution` because it starts the installed environment's
    interpreter. Read per tool, the record's Python side reads as fully tiered and the grant
    looks decisive; read per route, an untiered route still runs a tool and
    the grant changes nothing about what the check answers.
    """
    check = _routes_record(
        tmp_path,
        [
            {"lang": "python", "kind": "command", "tool": "t", "argv": ["t", "file"]},
            {
                "lang": "python",
                "kind": "command",
                "tool": "t",
                "argv": ["t", "environment"],
                "disposition": "alternative",
                "needs": "resolved-tree",
            },
        ],
    )
    # Read per tool - a tool tiered wherever any of its routes is - it is tiered.
    tiered_tools = {r.tool for r in check.routes if r.needs}
    assert {r.tool for r in check.routes} <= tiered_tools
    # Read per route, it does not - and that is the reading the round uses.
    assert ac._languages_whose_tools_all_need_a_grant(check.routes) == ()
    # Nothing is silenced either way, so no sentinel is demanded.
    assert ac._silenced_languages(check.routes) == ()


def test_a_language_whose_tools_are_all_tiered_is_named_even_when_a_reading_answers(
    tmp_path,
):
    """`deps/freshness`'s shape, and the reason the two halves differ.

    Every route naming a tool is tiered and the escape names none - a registry
    comparison a human performs. So the tools all need a grant, something
    still answers, and the expectation has to say what survives. Asking
    instead whether every *answering* route is tiered would be the complement
    of that second half and would drop this claim.
    """
    check = _routes_record(
        tmp_path,
        [
            {
                "lang": "python",
                "kind": "command",
                "tool": "t",
                "argv": ["t"],
                "needs": "resolved-tree",
            },
            {
                "lang": "python",
                "kind": "procedure",
                "note": "Compare each pinned version against the registry by hand.",
            },
        ],
    )
    assert ac._languages_whose_tools_all_need_a_grant(check.routes) == ("python",)
    assert ac._silenced_languages(check.routes) == ()


def test_a_subject_routes_untiered_tool_is_not_a_tool_that_answers(tmp_path):
    """`arch/complexity-gate` names `ruff`, `radon` and `xenon` this way.

    They are the gate's subject rather than its instrument, so counting one as
    an untiered tool would read that record as unaffected by a grant it never
    claimed to need - the same exclusion `_routes_answering_ungranted` makes,
    in the same direction.
    """
    check = _routes_record(
        tmp_path,
        [
            {
                "lang": "python",
                "kind": "command",
                "tool": "t",
                "argv": ["t"],
                "needs": "resolved-tree",
            },
            {"lang": "python", "kind": "subject", "tool": "ruff"},
            {
                "lang": "python",
                "kind": "procedure",
                "note": "Read the project's own configured gate and say whether it exists.",
            },
        ],
    )
    assert ac._languages_whose_tools_all_need_a_grant(check.routes) == ("python",)


def test_a_forbidden_routes_untiered_tool_is_not_a_tool_that_answers(tmp_path):
    """A route the record warns against is not one it offers.

    `arch/coupling`'s bare `dlx depcruise` is untiered and resolves to an npm
    placeholder that exits 0 having touched nothing. Reading it as a tool that
    still answers would say the grant is not decisive on the strength of a
    command the record forbids.
    """
    check = _routes_record(
        tmp_path,
        [
            {
                "lang": "python",
                "kind": "command",
                "tool": "t",
                "argv": ["t"],
                "needs": "resolved-tree",
            },
            {
                "lang": "python",
                "kind": "command",
                "tool": "placeholder",
                "argv": ["dlx", "placeholder"],
                "disposition": "forbidden",
            },
            {
                "lang": "python",
                "kind": "procedure",
                "note": "Read the import graph by hand and record every back edge.",
            },
        ],
    )
    assert ac._languages_whose_tools_all_need_a_grant(check.routes) == ("python",)


def test_an_untiered_universal_route_naming_a_tool_answers_for_every_language(
    tmp_path,
):
    """A `lang: any` route applies whatever the partition speaks.

    So its tool belongs to every language the record answers for, not only to
    the `any` key. A tiered `python` route beside an untiered `any` one naming
    a tool means Python still has a tool once the grant is withheld.
    """
    check = _routes_record(
        tmp_path,
        [
            {
                "lang": "python",
                "kind": "command",
                "tool": "t",
                "argv": ["t"],
                "needs": "resolved-tree",
            },
            {
                "lang": "any",
                "kind": "command",
                "tool": "u",
                "registry": "pypi",
                "argv": ["u"],
            },
        ],
    )
    assert ac._languages_whose_tools_all_need_a_grant(check.routes) == ()


def test_a_language_naming_no_tool_at_all_makes_no_claim_about_grants(tmp_path):
    """`all()` over an empty list is not a claim.

    A language answering only by a reading has said nothing a grant can
    change, so it is absent rather than vacuously named.
    """
    check = _routes_record(
        tmp_path,
        [
            {
                "lang": "python",
                "kind": "procedure",
                "note": "Read the docstrings and count the public symbols missing one.",
            }
        ],
    )
    assert ac._languages_whose_tools_all_need_a_grant(check.routes) == ()
    assert ac._silenced_languages(check.routes) == ()


# A partition key names a package manager, not a version of one. `yarn` is the
# only key in the tree whose manager may not provide `dlx` at all: it is a
# Yarn 2+ command, absent from Yarn classic's CLI index. `pnpm dlx` exists on
# every pnpm, so a pnpm-keyed entry needs no fallback and must not be what
# keeps the guard below non-vacuous.
_KEYS_WHOSE_MANAGER_MAY_LACK_DLX = ("yarn",)


def test_a_dlx_form_for_yarn_always_has_a_runnable_shared_argv_beside_it():
    """`audit/SKILL.md`'s route for Yarn classic depends on this being true.

    `dlx` is a Yarn 2+ command and Yarn classic's CLI index documents no
    general-purpose one-shot runner in its place, so both places the skill
    states the rule - the runner paragraph and the argv-selection bullet - say
    that a `yarn`-keyed `dlx` entry is Yarn Modern's form and what a classic
    partition runs instead is the route's shared `argv`.

    Two properties make that true and this holds both, because presence alone
    is not enough. The shared `argv` must exist, and it must not itself be
    `dlx`-led: a fallback spelled `pnpm ... dlx` or a bare `dlx` is no
    fallback, and restyling a shared argv to match the override's spelling is
    the plausible way that happens. Nothing else in the tree holds either
    property - the loader validates a keyed entry's shape, not whether the
    manager it names owns the command it spells - so a record losing one would
    silently reinstate `no-evidence (tool-unavailable)` for a tool obtainable
    the whole time, which is the failure #42 removed.

    Scoped to the partition keys whose manager may lack `dlx`, which is
    `yarn` alone. A *shared* argv leading with `dlx` is separately excluded
    and must not be caught: the graph records' `disposition: forbidden`
    routes carry a bare `dlx depcruise`, and `deps/inventory` a bare
    `dlx cyclonedx-npm`, each named in order never to be run.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    covered, missing, unrunnable = [], [], []
    for check in checks.values():
        for position, route in enumerate(check.routes):
            if route.disposition == "forbidden":
                continue
            keyed = dict(route.argv_by_partition or {})
            at_risk = sorted(
                partition
                for partition in _KEYS_WHOSE_MANAGER_MAY_LACK_DLX
                if "dlx" in keyed.get(partition, ())
            )
            if not at_risk:
                continue
            covered.append((check.id, route.tool, tuple(at_risk)))
            where = (check.id, route.tool, position, tuple(at_risk))
            if not route.argv:
                missing.append(where)
            elif "dlx" in route.argv:
                unrunnable.append(where)
    assert missing == [], (
        "these routes prescribe a dlx form for a partition whose manager may "
        f"not have dlx, and no shared argv to run instead: {missing}"
    )
    assert unrunnable == [], (
        "these routes' shared argv is itself dlx-led, so it is not a fallback "
        f"for a manager without dlx: {unrunnable}"
    )
    assert covered, (
        "no route carries a dlx form under a key in "
        f"{_KEYS_WHOSE_MANAGER_MAY_LACK_DLX}, so this guard has no subject - "
        "if those forms were removed deliberately, remove this too rather "
        "than leaving it passing over nothing"
    )


def test_the_docstring_s_no_fetch_count_is_the_tree_s():
    """`registry_for`'s warning cites a number, so the number is checked here.

    The docstring's whole point is that a non-`None` answer is not a verdict
    that a fetch applies, and its evidence is how many routes get an answer
    and need no fetch. A number in prose is the kind of claim CLAUDE.md says
    to compute rather than assert, and the two places that carry it - this
    docstring and CLAUDE.md's `## Check records` - are read by agents that
    cannot recompute it. So compute it, and read the docstring's own figures
    back rather than restating them, which is what makes an edit to either
    number fail instead of quietly disagreeing with the tree.

    The predicate is the docstring's own two reasons: a package-manager
    subcommand run directly, and an argv that already leads with a runner.
    Both leave nothing for a caller to put in front, and both derive a
    registry anyway, which is the trap.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == [], errors

    answered = [
        route
        for check in checks.values()
        for route in check.routes or ()
        if route.kind == "command" and ac.registry_for(route) is not None
    ]

    def leads_with_a_manager_or_a_runner(route: ac.Route) -> bool:
        commands = [route.argv] if route.argv else []
        commands += list((route.argv_by_partition or {}).values())
        return bool(commands) and all(
            command and command[0] in _RUNS_ITSELF for command in commands
        )

    no_fetch = [route for route in answered if leads_with_a_manager_or_a_runner(route)]

    stated = re.search(
        r"(\d+) of the (\d+) command routes that get an answer here\s+need no fetch",
        ac.registry_for.__doc__,
    )
    assert stated, (
        "`registry_for`'s docstring no longer states the two counts this guard "
        "reads back. If the sentence was reworded, point the pattern at the new "
        "wording rather than deleting the check - the numbers are what go stale"
    )
    assert (len(no_fetch), len(answered)) == (int(stated[1]), int(stated[2])), (
        f"the tree has {len(no_fetch)} of {len(answered)} command routes getting an "
        f"answer while needing no fetch; the docstring says {stated[1]} of "
        f"{stated[2]}. CLAUDE.md's `## Check records` carries the same pair, so "
        "both want updating together - and a large move here means the taxonomy "
        "shifted rather than the count drifting"
    )


# --- the `answers` route field (#89) -------------------------------------------


def _two_route_record(tmp_path, first: str, second: str, third: str | None = None):
    """Write a record whose frontmatter carries two or three routes, each built
    from a route body already indented to sit under a `- ` list item, and
    return the error list.
    """
    routes = [first, second] + ([third] if third else [])
    body = "\n  - ".join(routes)
    _write(tmp_path, "demo-audit/checks/thing.md", _routes_frontmatter(body))
    checks, errors = ac.load_checks(tmp_path)
    return checks.get("demo/thing"), errors


def test_two_axes_in_one_language_load_and_are_carried_on_the_routes(tmp_path):
    """The shape the field exists for: two routes answering different halves.

    `deps/model-pinning-and-eol` is the live instance, one route reading the
    pin from the project's configuration and one comparing identifiers
    against the provider's schedule; a run that does the first and cannot do
    the second has answered half the check, and the field is what lets the
    engine say which half.
    """
    check, errors = _two_route_record(
        tmp_path,
        "lang: any\n    kind: procedure\n    answers: pin\n    note: read the pin",
        "lang: any\n    kind: procedure\n    answers: lifetime\n    note: read the schedule",
    )
    assert errors == [], errors
    assert [r.answers for r in check.routes] == ["pin", "lifetime"]


def test_a_record_with_no_answers_anywhere_carries_none(tmp_path):
    """Absence is the ordinary case and means every route answers the whole check."""
    check = _one_route_record(
        tmp_path, "lang: python\n    kind: command\n    tool: t\n    argv: [t]"
    )
    assert check.routes[0].answers is None


def test_a_lone_answers_value_in_a_language_is_rejected(tmp_path):
    """One value declares nothing the field's absence does not already say.

    A schema that accepts a behavioural no-op is a field a future author fills
    without thinking, and a single-axis marker is exactly the read-and-judged
    stamp the design session weighed and dropped.
    """
    _, errors = _two_route_record(
        tmp_path,
        "lang: python\n    kind: command\n    tool: a\n    argv: [a]\n    answers: pin",
        "lang: python\n    kind: command\n    tool: b\n    argv: [b]\n    answers: pin",
    )
    assert any("lone value" in e and "python" in e for e in errors), errors


def test_a_half_axised_language_is_rejected(tmp_path):
    """All or none per language: a route with no axis beside axised ones has a
    result the engine cannot place on either axis.
    """
    _, errors = _two_route_record(
        tmp_path,
        "lang: python\n    kind: command\n    tool: a\n    argv: [a]\n    answers: pin",
        "lang: python\n    kind: command\n    tool: b\n    argv: [b]\n    answers: lifetime",
        "lang: python\n    kind: command\n    tool: c\n    argv: [c]",
    )
    assert any(
        "all or none" in e and "python" in e and "python/c" in e for e in errors
    ), errors


def test_a_universal_route_is_in_every_languages_scope(tmp_path):
    """A `lang: any` route applies to a Python partition at run time, so an
    axised Python pair beside an unaxised `any` route is the half-axised
    record the rule forbids, filed under two keys. The language grouping is the
    one `_routes_answering_ungranted` already uses, without its tier filter.
    """
    _, errors = _two_route_record(
        tmp_path,
        "lang: python\n    kind: command\n    tool: a\n    argv: [a]\n    answers: pin",
        "lang: python\n    kind: command\n    tool: b\n    argv: [b]\n    answers: lifetime",
        "lang: any\n    kind: procedure\n    note: read the source",
    )
    assert any("all or none" in e and "lang: python" in e for e in errors), errors
    assert not any("lang: any" in e and "all or none" in e for e in errors), errors


def test_a_forbidden_or_subject_route_may_not_carry_answers(tmp_path):
    """Neither answers anything, so neither has an axis to name."""
    _, errors = _two_route_record(
        tmp_path,
        "lang: python\n    kind: command\n    tool: a\n    argv: [a]\n    answers: pin",
        "lang: python\n    kind: command\n    tool: b\n    argv: [b]\n    answers: lifetime",
        "lang: python\n    kind: command\n    tool: c\n    argv: [c]\n"
        "    disposition: forbidden\n    answers: pin",
    )
    assert any("forbidden" in e and "answers" in e for e in errors), errors
    errors = _errors_for_route(
        tmp_path, "lang: python\n    kind: subject\n    tool: t\n    answers: pin"
    )
    assert any("subject" in e and "answers" in e for e in errors), errors


@pytest.mark.parametrize(
    ("value", "fragment"),
    [
        ("answers: none", "sentinel"),
        ("answers: Pin Axis", "slug"),
        ("answers: ''", "non-empty"),
        ("answers:", "non-empty"),
        ("answers: [pin]", "non-empty"),
    ],
)
def test_a_malformed_answers_value_is_rejected_by_name(tmp_path, value, fragment):
    """`none` is the neighbouring field's sentinel, a spaced or cased value is
    two spellings of one axis waiting to happen, and an empty or non-string
    value names nothing.
    """
    _, errors = _two_route_record(
        tmp_path,
        f"lang: python\n    kind: command\n    tool: a\n    argv: [a]\n    {value}",
        "lang: python\n    kind: command\n    tool: b\n    argv: [b]\n    answers: lifetime",
    )
    assert any("answers" in e and fragment in e for e in errors), errors


def test_alternatives_for_one_axis_share_its_value(tmp_path):
    """Two routes with one value beside a third with another: the first two are
    alternatives for their axis, with `disposition` stating the precedence,
    and the pair is a complement of the third. No separate declaration.
    """
    check, errors = _two_route_record(
        tmp_path,
        "lang: python\n    kind: command\n    tool: a\n    argv: [a]\n    answers: pin",
        "lang: python\n    kind: command\n    tool: b\n    argv: [b]\n"
        "    disposition: alternative\n    answers: pin",
        "lang: python\n    kind: command\n    tool: c\n    argv: [c]\n    answers: lifetime",
    )
    assert errors == [], errors
    assert sorted({r.answers for r in check.routes}) == ["lifetime", "pin"]


def test_a_universal_route_carrying_one_axis_beside_concrete_languages_is_accepted(
    tmp_path,
):
    """`test/isolation`'s shape: per-runner timing routes and one `lang: any`
    grep for real I/O. The `any` route is judged inside the Python scope,
    where it is one of two axes; judging it again under its own key would
    demand a second axis of a route that carries exactly the one the
    concrete languages leave to it.
    """
    check, errors = _two_route_record(
        tmp_path,
        "lang: python\n    kind: command\n    tool: a\n    argv: [a]\n    answers: timing",
        "lang: any\n    kind: procedure\n    answers: io\n    note: read the tests",
    )
    assert errors == [], errors
    assert [r.answers for r in check.routes] == ["timing", "io"]


def test_a_record_with_only_universal_routes_is_held_to_the_rules_as_a_language(
    tmp_path,
):
    """`deps/model-pinning-and-eol` is two `lang: any` routes and nothing else,
    so the universal key is the record's whole scope and a lone value there
    is refused like anywhere else.
    """
    _, errors = _two_route_record(
        tmp_path,
        "lang: any\n    kind: procedure\n    answers: pin\n    note: read the pin",
        "lang: any\n    kind: procedure\n    answers: pin\n    note: read it again",
    )
    assert any("lone value" in e and "lang: any" in e for e in errors), errors


def test_the_answers_pass_is_not_vacuous():
    """The reading pass over the multi-route records happened, and its result holds.

    The loader enforces all-or-none and two-distinct-values, so nothing here
    can be satisfied by stamping; what the loader cannot see is a record
    quietly losing the field, which reads as the positive claim that every
    route answers the whole check. The floor is the number of records the
    pass marked as complements, with no slack, the way the `needs` floor
    above holds its sweep: adding a complement record raises it, and a
    failure here means a record dropped its axes rather than a number to
    lower. Computed at the `answers` pass: 5, over the 28 records that on
    `main` at `ae41836` had a language with more than one answering
    non-`forbidden` route. Recomputed at the ci migration: 7, over 32 such
    records, `ci/workflow-correctness` (`well-formedness` and `injection`,
    the instance #89 named) and `ci/gate-enforcement` (`workflows` and
    `protection`, read under the same rule) having joined; 8, over 33 such records, when
    `arch/harness-bounding` arrived with one axis per tell it reads; and 9,
    over 37 such records, when the `eval` migration gave `eval/cost-latency` a `profile` axis that
    runs the target's evals and a `cheap-mode` axis read without a grant.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    axised = sorted(c.id for c in checks.values() if any(r.answers for r in c.routes))
    assert len(axised) >= 9, f"only {len(axised)} record(s) carry answers: {axised}"
    assert all(
        len({r.answers for r in checks[cid].routes if r.answers}) >= 2 for cid in axised
    )


#: A sentence stating how many rows a check reports - "one row per ...",
#: "a row for ...". `audit-core`'s findings-matrix step makes one instance the
#: row by default and lets a record state another unit only in one form, so a
#: unit sentence anywhere else is either the default restated in a second
#: place or an override nothing but a reader will find.
_ROW_UNIT_SENTENCE = re.compile(
    r"\b(?:one|a|each|single)\s+rows?\s+(?:per|for|at)\b|\bper-\w+\s+rows?\b", re.I
)
#: The permitted sentence ends at a full stop followed by whitespace and a
#: capital, or at the end of the field, so a unit naming `pyproject.toml` or
#: written with "e.g." is one sentence rather than a truncated one.
_FIRST_SENTENCE = re.compile(r"^(.+?\.)(?=\s+[A-Z]|\s*$)", re.S)

#: Records whose unit sentence is left as written, each with the reason. The
#: one entry disagrees with itself about its unit - its `evidence` says "A row
#: records the detected runtimes", its body "one row per detected runtime" -
#: and that disagreement is a decision #20's attended run takes, not one the
#: row rule's migration may settle by picking a side.
ROW_UNIT_LEFT_AS_WRITTEN = {"arch/runtime-declaration": "#20 decides its unit"}


def _strings_in(value: object) -> list[str]:
    """Every string a parsed frontmatter value holds, at any depth."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings_in(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings_in(v)]
    return []


def _row_unit_problems(check_id: str, text: str, evidence: str | None) -> list[str]:
    """What is wrong with how one record states its row unit, if anything."""
    problems = []
    if evidence and evidence.lower().startswith("row unit"):
        match = _FIRST_SENTENCE.match(evidence)
        first = match.group(1) if match else evidence
        if not first.startswith("Row unit: ") or ", because " not in first:
            problems.append(
                f"{check_id}: `evidence` opens with a unit that is not in the form "
                "`Row unit: <unit>, because <why>.`"
            )
        text = text.replace(first, "", 1)
    stray = [
        " ".join(text[max(0, m.start() - 40) : m.end() + 40].split())
        for m in _ROW_UNIT_SENTENCE.finditer(text)
    ]
    if stray:
        problems.append(
            f"{check_id}: states a row unit outside the `Row unit:` sentence: {stray}"
        )
    return problems


def test_a_record_states_its_row_unit_only_in_the_rules_form():
    """A row unit is stated once, where `audit-core` says, or not at all.

    The engine's default is one row per instance; a record overriding it
    opens its `evidence` with `Row unit: <unit>, because <why>.` Any other
    sentence about how many rows the check reports is the grain a domain
    agent used to decide for itself, which is how one run's 12 rows became
    another's 48 over the same defects. The folded YAML is read as the loader
    reads it, so a sentence split across source lines is still one sentence,
    and every string the frontmatter holds is read, route notes included.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    problems = []
    for check in checks.values():
        if check.id in ROW_UNIT_LEFT_AS_WRITTEN:
            continue
        frontmatter, body, _ = ac._split_frontmatter(check.path.read_text())
        text = " ".join([*_strings_in(frontmatter), body])
        evidence = " ".join(check.evidence.split()) if check.evidence else None
        problems += _row_unit_problems(check.id, " ".join(text.split()), evidence)
    assert problems == []
    stated = sorted(
        c.id for c in checks.values() if (c.evidence or "").startswith("Row unit: ")
    )
    assert len(stated) >= 5, stated
    assert set(ROW_UNIT_LEFT_AS_WRITTEN) <= set(checks)


def test_the_row_unit_guard_catches_a_unit_in_the_wrong_place():
    assert _row_unit_problems("x/y", "The check reports one row per module.", None)
    assert _row_unit_problems("x/y", "text", "Row unit - the project.")
    assert _row_unit_problems("x/y", "text", "row unit: the project, because so.")
    assert _row_unit_problems("x/y", "A per-module row each.", None)
    assert not _row_unit_problems(
        "x/y",
        "Row unit: each `pyproject.toml`, because e.g. it declares one. More.",
        "Row unit: each `pyproject.toml`, because e.g. it declares one. More.",
    )
    assert not _row_unit_problems(
        "x/y",
        "Row unit: the project, because the decision is the project's. More.",
        "Row unit: the project, because the decision is the project's. More.",
    )
    assert _row_unit_problems(
        "x/y",
        "Row unit: the project, because it is one. Also a row for each module.",
        "Row unit: the project, because it is one. Also a row for each module.",
    )
