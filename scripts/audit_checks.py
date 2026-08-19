"""Load and validate the audit check records (lidia-tech/lidia-agents#559).

`.agents/skills/<domain>-audit/checks/<check>.md` holds one record per
auditable check: the machine-checkable attributes in YAML frontmatter, the
judgment prose in the body. The `*-audit` skills load a subset of these at
run time - a domain's checks, sliced by locality - instead of eight
`SKILL.md` files each carrying the same five per-check attributes inline.

A domain's records live inside that domain's own skill, not in a shared
tree under `audit-core`. Each skill then stands alone - a repo adopting
three of the nine domains copies three directories plus the engine - and
a record is one hop from the `SKILL.md` that names it rather than two hops
through a sibling skill, which is the nesting depth Anthropic's skill
guidance warns leads agents to preview a file rather than read it.

This module owns loading and *intra-record* validation: is this one file
well formed on its own. Cross-referencing a record against the traceability
matrix - does its `handbook` anchor name a row that actually cites it -
lives in `render_handbook_traceability.py`, which already holds the matrix
and the handbook headings. That keeps one gate
(`render_handbook_traceability.py --check`) reporting every problem.

Frontmatter fields:

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Stable `<domain>/<slug>`, matching the file's own path |
| `domain` | yes | The owning domain, matching the owning skill's name |
| `locality` | yes | `local` (decidable from one partition) or `global` |
| `handbook` | yes | Handbook row ids grounding the check; may be empty |
| `handbook_note` | iff `handbook` is empty | Why the check exceeds the handbook |
| `tooling` | no | Language to preferred tools; `any` for language-agnostic |
| `needs` | no | Tier to tool names, for tools needing more than a read-only clone |
| `ungranted_note` | iff every tool in a language needs a grant | What the check still answers when that grant is withheld |
| `routes` | no, and non-empty where present | A list of `Route`s: what this check can run, replacing `tooling`/`needs`/`ungranted_note` for a migrated record |
| `answers_ungranted` | iff every answering-kind route in a language needs a grant | The routes-schema counterpart of `ungranted_note`: the sentinel `none`, written where no route in that language answers without a grant |
| `optin` | no | Default `false`; an opt-in sub-audit that produces findings |

`handbook` is a list because a check is commonly grounded in several
clauses. It is not required to be exhaustive - the matrix is the
authoritative edge set - but everything it lists must be true, and a check
some row cites may not claim to be ungrounded.

A `tooling` value is a list of names, not of invocations, and a name may be
a registry package, a subcommand of the target's own package manager, or a
standalone binary in no registry. Nothing here validates which - a name is
only a string to this loader - so a record still carrying `tooling` states
the kind and the precedence between its names in `## Tooling fallback`
prose. A record carrying `routes` instead (below) states both as data:
`kind` is a field on every route, and precedence is the route's
`disposition` and its position in the list, so neither depends on prose
there.

`needs` answers a different question about the same names: not where the
tool comes from, but what must be present in the target before it can
answer. A tool absent from `needs` runs against a read-only clone;
`resolved-tree` needs the dependency graph materialized; `target-execution`
needs that and runs the target's own code. The names are deliberately
repeated from `tooling` rather than folded into it, and the repetition is
what is checked: every name under `needs` must be one the record actually
offers, so a rename that misses one of the two places fails here instead of
quietly describing a tool that is no longer listed.

`ungranted_note` answers a third question, and it is about the check rather
than about any tool: when the tools need a grant this run does not hold,
what can the check still answer? `needs` cannot express this, because it
is per-tool, and the engine's rule - a check whose every tool needs a
grant is `no-evidence` without it - is a check-level conclusion derived
from tool-level facts. That derivation is wrong wherever a check has an
axis needing no tool, which is why the field exists rather than the
records arguing with their own frontmatter in prose. The value is either
what still answers, or the sentinel `none` where nothing does, and it is
rejected on a record that keeps a tool answering from a read-only clone,
because there the withheld-grant situation it describes cannot arise.
It is required on exactly the records this rule would silence, so an absent
key is never a silent claim - which is the hazard `needs` still carries and
this field does not.

A record may declare `routes` instead of `tooling`/`needs`/`ungranted_note`:
one list of `Route`s, each one way of answering the check in one language,
in place of a free-form tool list plus the two side mappings that classify
it. The list must hold at least one route, because an empty one is the
schema declared and then not stated - indistinguishable downstream from a
record that never declared it. The two schemas are mutually exclusive - a record naming both is
rejected, because a route's tier is the only place a tool's requirement is
declared, and repeating it under `needs` too would reopen the drift
`needs`'s own repetition-check exists to close. A migrated record's
`tooling` and `needs` are then derived from its routes by projection (see
`_project_tooling` and `_project_needs`), so the call sites in
`run_python_fixture_lens.py`, `test_python_fixture_harness.py` and
`test_python_fixture_spec.py` that predate `routes` still read the same
shape without change. The shape is all the projection carries: the tools
and their tiers, and no ungranted claim, so whether a withheld grant
silences a language is read from the routes through
`_silenced_languages` and never off the projected pair - `_project_tooling`
keeps a `kind: subject` route's tool under its language, which is how a
language nothing there was answering reads as fully tiered.

`answers_ungranted` is `ungranted_note`'s counterpart under `routes`: where
every answering-kind route (`command`, `library`, `procedure`) a language
offers needs a grant, the record must also carry an untiered route that
answers there, or the sentinel `none`, for the same reason `ungranted_note`
is required rather than left to an absent key reading as a claim. A route
whose `lang` is one of `UNIVERSAL_ROUTE_LANGS` answers in every language
the record answers for, because that is what those two `ROUTE_LANGS`
values mean, so an untiered one rescues a language whose own routes are
all tiered. A
`kind: subject` route is excluded from this rule in both directions - it
never supplies the untiered escape, and it never counts toward a language
having a claim to silence in the first place - because it names what the
check inspects rather than what runs it: `arch/complexity-gate` names
`ruff`, `radon` and `xenon` this way, and counting one as an answer would
silence exactly the records this rule exists to protect. A
`disposition: forbidden` route is excluded from the escape side of the
same rule for a different reason: it is a route the record warns against
running, not one it offers, so an untiered forbidden route must never be
read as what still answers - `arch/coupling`'s bare `dlx depcruise`
invocation (an npm dependency-confusion placeholder that exits 0 having
touched nothing) is exactly the untiered-but-forbidden shape this
exclusion exists for. `alternative` and `superseded` routes are not
excluded; the record does offer those, it simply does not run them by
default. `_routes_answering_ungranted` computes, per language, the routes
actually in scope for this: the answering-kind, non-forbidden routes
carrying no tier, each language's own plus the universal ones. A language absent from its result has offered no such
route at all, so it has made no claim this rule can silence, exactly as a
language absent from `tooling` makes none under the legacy schema.

Usage:
    from audit_checks import SKILLS_DIR, load_checks

    checks, errors = load_checks(SKILLS_DIR)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"

# A domain skill is `<domain>-audit`; its records live in `checks/` beneath it.
SKILL_SUFFIX = "-audit"
CHECKS_SUBDIR = "checks"

LOCALITIES = ("local", "global")
# What a tool needs *present in the target* before it can answer, which is a
# different axis from where the tool comes from: a registry package a runner
# can fetch may still need the tree, and a standalone binary no runner can
# fetch may answer from a lockfile alone. `target-execution` implies
# `resolved-tree`. The common case carries no tier and no key.
NEEDS_TIERS = ("resolved-tree", "target-execution")
# The sentinel a record writes when a withheld grant really does leave it
# nothing to answer. Spelled lowercase because YAML turns `None` and `NONE`
# into ordinary strings, which would read as a fallback claim, and turns
# `null` and an empty value into nothing at all, which reads as an omitted
# key. The loader rejects each of those by name rather than guessing.
UNGRANTED_NONE = "none"
# A route's four vocabularies. `ROUTE_LANGS` includes `none` alongside the
# languages: a procedure route that names no tool (reading source, reading
# CI config) belongs to no language, which `tooling`'s bare language keys
# had no way to say.
ROUTE_KINDS = ("command", "library", "procedure", "subject")
# The `ROUTE_KINDS` that can answer the check at all. `subject` is the one
# absence: it names what the check inspects rather than what runs it -
# `arch/complexity-gate` names `ruff`, `radon` and `xenon` as "the gate's
# subject rather than its instrument", running one answers `arch/complexity`,
# not the gate - so it must never satisfy the ungranted rule below.
ANSWERING_ROUTE_KINDS = ("command", "library", "procedure")
DISPOSITIONS = ("runs", "alternative", "superseded", "forbidden")
ROUTE_LANGS = ("python", "typescript", "any", "none")
# The `ROUTE_LANGS` that name no language of their own. A route carrying
# one applies whatever the partition's language is, which is why
# `_routes_answering_ungranted` reads an untiered one as an answer for
# every language the record answers for rather than only under its own key.
UNIVERSAL_ROUTE_LANGS = ("any", "none")
FINDINGS_STREAMS = ("stdout", "stderr")
ROUTE_FIELDS = frozenset(
    {
        "lang",
        "kind",
        "tool",
        "package",
        "argv",
        "argv_by_manager",
        "disposition",
        "needs",
        "in_env",
        "findings_stream",
        "applies_when",
        "alone_insufficient",
        "note",
    }
)
FIELDS = frozenset(
    {
        "id",
        "domain",
        "locality",
        "handbook",
        "handbook_note",
        "tooling",
        "needs",
        "ungranted_note",
        "routes",
        "answers_ungranted",
        "optin",
    }
)

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---(?:\n(.*))?\Z", re.DOTALL)
_TITLE_RE = re.compile(r"^# (.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Route:
    """One way of answering one check in one language.

    Three axes a record's prose used to write as a single sentence. `kind`
    says what the thing is, `disposition` says whether the harness takes this
    route, and `applies_when` says what the target must carry for the route to
    be available at all. They stay separate fields because one list of tool
    names cannot tell a library apart from a command conditional on a target
    artifact from a tool that is the check's subject rather than its
    instrument - three different reasons a route might prescribe no command,
    each needing its own field to be checked rather than read as prose.
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


@dataclass(frozen=True)
class Check:
    """One audit check: its machine-checkable attributes plus its display name."""

    id: str
    domain: str
    locality: str
    title: str
    handbook: tuple[str, ...]
    handbook_note: str | None
    tooling: dict[str, tuple[str, ...]]
    needs: dict[str, tuple[str, ...]]
    ungranted_note: str | None
    routes: tuple[Route, ...]
    answers_ungranted: str | None
    optin: bool
    path: Path


def _split_frontmatter(text: str) -> tuple[dict[str, Any] | None, str, str | None]:
    """Split a record into its frontmatter mapping and its body.

    Args:
        text: The whole file contents.

    Returns:
        The parsed mapping, the body, and an error message; the mapping is
        `None` exactly when the message is not.
    """
    m = _FRONTMATTER_RE.match(text)
    if m is None:
        return None, "", "missing YAML frontmatter delimited by --- lines"
    try:
        meta = yaml.safe_load(m.group(1))
    except yaml.YAMLError as exc:
        return None, "", f"frontmatter is not valid YAML: {exc}"
    if not isinstance(meta, dict):
        return None, "", "frontmatter must be a mapping"
    return meta, m.group(2) or "", None


def _read_text(path: Path) -> tuple[str | None, str | None]:
    """Read a record file, turning any read failure into a message.

    `load_checks` promises to collect problems rather than raise, and it is
    called from the traceability gate, so an unreadable file must degrade to
    one error line rather than a traceback that hides every other problem in
    the tree. A directory named `*.md`, a non-UTF-8 byte, a broken symlink
    and an unreadable file all arrive here.

    Args:
        path: The record file.

    Returns:
        The contents and an error message; the contents are `None` exactly
        when the message is not.
    """
    try:
        return path.read_text(encoding="utf-8"), None
    except UnicodeDecodeError:
        return None, "not valid UTF-8"
    except OSError as exc:
        return None, f"cannot be read: {type(exc).__name__}: {exc}"


def _str_list(value: Any) -> tuple[str, ...] | None:
    """Coerce a YAML value to a tuple of strings, or `None` if it is not one."""
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        return None
    return tuple(value)


def _fully_tiered_languages(
    tooling: dict[str, tuple[str, ...]], needs: dict[str, tuple[str, ...]]
) -> tuple[str, ...]:
    """Languages whose every offered tool needs a grant.

    These are the (record, language) pairs the engine silences: with no
    grant held, a check has nothing left to run in that language, so it
    reports `no-evidence (not-permitted)` unless the record says otherwise.
    A language offering no tools at all is not one of them - `all()` is
    vacuously true over an empty list, and a record that lists a language
    with no tools has said nothing about grants.

    Args:
        tooling: Language to the tools the record offers.
        needs: Tier to the tools that need it.

    Returns:
        The languages, sorted, so a message naming them is stable.
    """
    tiered = {name for names in needs.values() for name in names}
    return tuple(
        lang
        for lang, names in sorted(tooling.items())
        if names and all(name in tiered for name in names)
    )


def _load_routes(raw: Any, where: str) -> tuple[tuple[Route, ...], list[str]]:
    """Parse and validate a record's `routes` list.

    Collects every problem rather than stopping at the first, matching
    `_load_one`'s contract: a caller that raised on the first bad route in a
    twelve-route record would hide the other eleven. Validates, in order:
    the value is a list of mappings; the list is not empty; every key is a
    string, and one `ROUTE_FIELDS` knows; `lang`, `kind`, `disposition`,
    `findings_stream` and `needs` each name a known value; `tool` is present
    unless `kind` is `procedure`; `package` defaults to `tool` when the key
    is absent and is rejected when the key is written with no value, because
    those two are the same YAML to `get` and different claims to a reader;
    `argv` and `argv_by_manager` are present only where `kind` is `command`,
    and every argv they name - `argv` itself, and each manager's entry
    under `argv_by_manager` - is non-empty there; a `disposition` other than
    `runs` appears only where `kind` is `command`.

    The empty list is rejected rather than tolerated because `routes: []` and
    an absent `routes` key are indistinguishable to everything downstream:
    both project to no tooling and no needs, neither can silence a language,
    and so neither is ever asked for `answers_ungranted`. A record that
    declared the routes schema and then listed nothing would read as one that
    never declared it, which is the schema question answered by default in
    the direction that hides it.

    Args:
        raw: The frontmatter's `routes` value, or `None` if the record does
            not declare one.
        where: The record's path, for error messages.

    Returns:
        The routes, in file order, and one message per problem. Each message
        names the record, the route's index, and the field, so a failure on
        a many-route record says which route and which field are wrong.
    """
    errors: list[str] = []
    if raw is None:
        return (), errors
    if not isinstance(raw, list) or not all(isinstance(entry, dict) for entry in raw):
        errors.append(f"{where}: routes must be a list of mappings")
        return (), errors
    if not raw:
        errors.append(
            f"{where}: routes is empty - a record declaring routes must declare "
            "at least one; an empty list reads downstream exactly as a record "
            "that declares no routes at all"
        )
        return (), errors

    routes: list[Route] = []
    for i, entry in enumerate(raw):
        loc = f"{where}: routes[{i}]"
        # Sorted by a stable string form rather than by the keys
        # themselves: YAML admits a non-string mapping key (`1: extra`
        # parses to an int), and sorting a set holding both raises
        # `TypeError`, which would leave `_load_routes` raising out of
        # `load_checks` and lose every other problem in the tree to one
        # malformed record.
        for key in sorted(set(entry) - ROUTE_FIELDS, key=repr):
            if isinstance(key, str):
                errors.append(f"{loc}: unknown route key {key!r}")
            else:
                errors.append(
                    f"{loc}: route key {key!r} is not a string - every route "
                    "field is named by a string, so a key YAML parsed as "
                    "anything else names none of them whatever it was meant "
                    "to say"
                )

        lang = entry.get("lang", "any")
        if lang not in ROUTE_LANGS:
            errors.append(f"{loc}: lang must be one of {ROUTE_LANGS}, got {lang!r}")
            lang = "any"

        kind = entry.get("kind")
        if kind not in ROUTE_KINDS:
            errors.append(f"{loc}: kind must be one of {ROUTE_KINDS}, got {kind!r}")

        disposition = entry.get("disposition", "runs")
        if disposition not in DISPOSITIONS:
            errors.append(
                f"{loc}: disposition must be one of {DISPOSITIONS}, got {disposition!r}"
            )
            disposition = "runs"
        elif disposition != "runs" and kind != "command":
            errors.append(
                f"{loc}: disposition {disposition!r} needs kind: command - a "
                f"{kind!r} route has nothing for the harness to run instead of"
            )

        findings_stream = entry.get("findings_stream", "stdout")
        if findings_stream not in FINDINGS_STREAMS:
            errors.append(
                f"{loc}: findings_stream must be one of {FINDINGS_STREAMS}, got "
                f"{findings_stream!r}"
            )
            findings_stream = "stdout"

        needs = entry.get("needs")
        if needs is not None and needs not in NEEDS_TIERS:
            errors.append(f"{loc}: needs must be one of {NEEDS_TIERS}, got {needs!r}")
            needs = None

        tool = entry.get("tool")
        if tool is not None and not isinstance(tool, str):
            errors.append(f"{loc}: tool must be a string, got {tool!r}")
            tool = None
        elif tool is None and kind != "procedure":
            errors.append(
                f"{loc}: tool is required - only a kind: procedure route may "
                "name no tool"
            )

        package = entry.get("package", tool)
        if "package" in entry and entry["package"] is None:
            errors.append(
                f"{loc}: package is empty - YAML reads `null`, `~` and a bare "
                "key as nothing, which is not the same as an absent key: an "
                "absent key falls back to tool, while this one takes neither "
                "the fallback nor the string check. Name the package, or drop "
                "the key to take the tool name"
            )
            package = tool
        elif package is not None and not isinstance(package, str):
            errors.append(f"{loc}: package must be a string, got {package!r}")
            package = tool

        raw_argv = entry.get("argv")
        if kind == "command":
            argv = _str_list(raw_argv) or ()
            if not argv:
                errors.append(f"{loc}: a command route must carry a non-empty argv")
        else:
            if raw_argv is not None:
                errors.append(
                    f"{loc}: argv is only valid on a command route, not {kind!r}"
                )
            argv = ()

        raw_argv_by_manager = entry.get("argv_by_manager")
        argv_by_manager: dict[str, tuple[str, ...]] = {}
        if raw_argv_by_manager is not None:
            if kind != "command":
                errors.append(
                    f"{loc}: argv_by_manager is only valid on a command route, "
                    f"not {kind!r}"
                )
            elif not isinstance(raw_argv_by_manager, dict):
                errors.append(
                    f"{loc}: argv_by_manager must be a mapping of manager to argv"
                )
            else:
                for manager, manager_argv in raw_argv_by_manager.items():
                    names = _str_list(manager_argv)
                    if not isinstance(manager, str) or names is None:
                        errors.append(
                            f"{loc}: argv_by_manager[{manager!r}] must be a list "
                            "of argv strings"
                        )
                        continue
                    if not names:
                        errors.append(
                            f"{loc}: argv_by_manager[{manager!r}] is empty - a "
                            "command route carries a command for every manager "
                            "it names, and an empty one declares that manager "
                            "answered by nothing at all, which is the absence "
                            "the non-empty argv rule already rejects"
                        )
                        continue
                    argv_by_manager[manager] = names

        in_env = entry.get("in_env", False)
        if not isinstance(in_env, bool):
            errors.append(f"{loc}: in_env must be a boolean, got {in_env!r}")
            in_env = bool(in_env)

        applies_when = entry.get("applies_when")
        if applies_when is not None and not isinstance(applies_when, str):
            errors.append(f"{loc}: applies_when must be a string, got {applies_when!r}")
            applies_when = None

        alone_insufficient = entry.get("alone_insufficient")
        if alone_insufficient is not None and not isinstance(alone_insufficient, str):
            errors.append(
                f"{loc}: alone_insufficient must be a string, got "
                f"{alone_insufficient!r}"
            )
            alone_insufficient = None

        note = entry.get("note")
        if note is not None and not isinstance(note, str):
            errors.append(f"{loc}: note must be a string, got {note!r}")
            note = None

        routes.append(
            Route(
                lang=lang,
                kind=kind if kind in ROUTE_KINDS else "procedure",
                tool=tool,
                package=package,
                argv=argv,
                argv_by_manager=argv_by_manager,
                disposition=disposition,
                needs=needs,
                in_env=in_env,
                findings_stream=findings_stream,
                applies_when=applies_when,
                alone_insufficient=alone_insufficient,
                note=note,
            )
        )

    return tuple(routes), errors


def _project_tooling(routes: tuple[Route, ...]) -> dict[str, tuple[str, ...]]:
    """Derive a legacy `tooling` mapping from a migrated record's routes.

    This is a view, not a second source - a route is the only place a tool is
    declared. It exists so the call sites in `run_python_fixture_lens.py` and
    its tests that still read `Check.tooling` see the same shape they always
    have, without a migrated record repeating each tool a second time.

    Args:
        routes: The record's parsed routes.

    Returns:
        Language to the tools offered in that language, in route order,
        duplicates collapsed. A `lang: any` route projects under the literal
        `"any"` key, exactly as `tooling: {any: [...]}` did before routes
        existed - every reader of `Check.tooling` already looks a language
        up with `.get(lang, ())`, so an `any` tool stays invisible to a
        `python`/`typescript` lookup precisely as it did before. A
        `disposition: forbidden` route contributes nothing: the record is
        warning against that tool, not offering it, though the same tool
        offered by another route in the record still appears. A route
        naming no tool contributes nothing either.
    """
    per_lang: dict[str, list[str]] = {}
    for route in routes:
        if route.tool is None or route.disposition == "forbidden":
            continue
        tools = per_lang.setdefault(route.lang, [])
        if route.tool not in tools:
            tools.append(route.tool)
    return {lang: tuple(tools) for lang, tools in per_lang.items()}


def _project_needs(routes: tuple[Route, ...]) -> dict[str, tuple[str, ...]]:
    """Derive a legacy `needs` mapping from a migrated record's routes.

    The same view as `_project_tooling`: a route's tier is the only place it
    is declared, and this only reshapes it for the pre-migration readers of
    `Check.needs`. A `disposition: forbidden` route contributes nothing here
    either, for the same reason `_project_tooling` excludes it - the record
    is warning against the tool, not offering it under that tier.

    Args:
        routes: The record's parsed routes.

    Returns:
        Tier to the tools of the routes carrying it, in route order,
        duplicates collapsed.
    """
    per_tier: dict[str, list[str]] = {}
    for route in routes:
        if (
            route.needs is None
            or route.tool is None
            or route.disposition == "forbidden"
        ):
            continue
        tools = per_tier.setdefault(route.needs, [])
        if route.tool not in tools:
            tools.append(route.tool)
    return {tier: tuple(tools) for tier, tools in per_tier.items()}


def _routes_answering_ungranted(
    routes: tuple[Route, ...],
) -> dict[str, tuple[Route, ...]]:
    """Group a record's answering-kind routes by language, keeping only the
    ones that still answer with no grant held.

    Two exclusions apply before grouping, for two different reasons - a
    route dropped for one is not dropped for the other:

    - A `kind: subject` route neither offers a language an untiered escape
      nor gives that language a claim to silence in the first place,
      because it is the record's own admission that running it inspects
      the check's subject rather than answering the check -
      `arch/complexity-gate`'s `ruff`, `radon` and `xenon` are exactly
      this, and counting one as an answer would silence the very records
      this rule exists to protect.
    - A `disposition: forbidden` route is excluded for the opposite
      reason: it is a route the record warns against running at all, not
      one it offers. `arch/coupling` carries a tiered `dependency-cruiser`
      route for TypeScript and a bare `dlx depcruise` invocation that
      resolves to an npm dependency-confusion placeholder exiting 0 having
      touched nothing - a `disposition: forbidden` route that happens to
      need no grant. Counting that untiered forbidden route as the
      language's escape would let the record pass without ever saying
      what actually answers once the grant is withheld, which is the
      exact silence this rule exists to prevent, produced by the rule
      itself. `_project_tooling`/`_project_needs` already exclude a
      forbidden route from what the record offers; this mirrors that.
      An `alternative` or `superseded` route is not excluded - the record
      does offer those, it just does not run them by default.

    An untiered route whose `lang` is one of `UNIVERSAL_ROUTE_LANGS` is
    what still answers for every language, not only for the key it is
    filed under: the schema says such a route applies whatever the
    partition's language is, so a record pairing a tiered `python` route
    with an untiered `any` one has an answer for Python once the grant is
    withheld. Reading it under the literal key alone demanded
    `answers_ungranted: none` from a record that is not silenced, which
    is a false claim forced into frontmatter by the rule meant to prevent
    one. This differs from `_project_tooling`, which files an `any` route
    under the literal `"any"` key on purpose - there the question is which
    invocations a language's lens should run, and here it is whether
    anything at all still answers.

    Args:
        routes: The record's parsed routes.

    Returns:
        Language to the tuple of its untiered answering routes, for every
        language offering at least one answering-kind, non-forbidden
        route (`command`, `library`, `procedure`), each language's own
        untiered routes first and the universal ones after. A language
        offering none at all - no routes, only a `subject` route, or only
        `forbidden` routes - is absent from the mapping: it has made no
        claim about grants for this rule to silence, and a universal route
        does not put it back, because spreading only reaches languages the
        record already answers for.
    """
    by_lang: dict[str, list[Route]] = {}
    for route in routes:
        if route.kind in ANSWERING_ROUTE_KINDS and route.disposition != "forbidden":
            by_lang.setdefault(route.lang, []).append(route)
    universal = [
        route
        for lang_routes in by_lang.values()
        for route in lang_routes
        if route.lang in UNIVERSAL_ROUTE_LANGS and route.needs is None
    ]
    return {
        lang: tuple(
            [route for route in lang_routes if route.needs is None]
            + [route for route in universal if route.lang != lang]
        )
        for lang, lang_routes in by_lang.items()
    }


def _silenced_languages(routes: tuple[Route, ...]) -> tuple[str, ...]:
    """Languages a withheld grant silences under the `routes` schema.

    Mirrors `_fully_tiered_languages` for routes: a language is silenced
    when it offers at least one answering-kind route and every one of them
    needs a grant, i.e. `_routes_answering_ungranted` maps it to an empty
    tuple. A language absent from that mapping altogether - no answering
    route at all - is not one of them, for the same reason `all()` over an
    empty list must not be read as a claim.

    Args:
        routes: The record's parsed routes.

    Returns:
        The languages, sorted, so a message naming them is stable.
    """
    answering = _routes_answering_ungranted(routes)
    return tuple(lang for lang, untiered in sorted(answering.items()) if not untiered)


def _load_one(
    path: Path, skills_dir: Path
) -> tuple[Check | None, list[str], str | None]:
    """Parse and validate a single record in isolation.

    Args:
        path: The record file, at `<domain>-audit/checks/<slug>.md`.
        skills_dir: The skills root the record's expected id is relative to.

    Returns:
        The record (or `None` if it failed), one message per problem, and the
        raw declared `id` if the frontmatter had a string one. The raw id is
        returned even for a record that failed validation, because collision
        detection has to run on the declared value: a validated `Check.id`
        equals its own file's path-derived id, and paths are unique, so two
        of them can never collide.
    """
    rel = path.relative_to(skills_dir)
    where = rel.as_posix()
    expected_domain = rel.parts[0].removesuffix(SKILL_SUFFIX)
    text, read_err = _read_text(path)
    if text is None:
        return None, [f"{where}: {read_err}"], None
    meta, body, err = _split_frontmatter(text)
    if meta is None:
        return None, [f"{where}: {err}"], None

    errors: list[str] = []
    for key in sorted(set(meta) - FIELDS):
        errors.append(f"{where}: unknown frontmatter key {key!r}")

    expected_id = f"{expected_domain}/{path.stem}"
    cid = meta.get("id")
    declared = cid if isinstance(cid, str) else None
    if not isinstance(cid, str):
        errors.append(f"{where}: id must be a string, got {cid!r}")
        cid = expected_id
    elif cid != expected_id:
        errors.append(
            f"{where}: id {cid!r} does not match its path (expected {expected_id!r})"
        )

    domain = meta.get("domain")
    if domain != expected_domain:
        errors.append(
            f"{where}: domain {domain!r} does not match its owning skill "
            f"{rel.parts[0]!r} (expected {expected_domain!r})"
        )

    locality = meta.get("locality")
    if locality not in LOCALITIES:
        errors.append(
            f"{where}: locality must be one of {LOCALITIES}, got {locality!r}"
        )

    handbook = _str_list(meta.get("handbook"))
    if handbook is None:
        errors.append(
            f"{where}: handbook must be a list of handbook row ids (may be empty)"
        )
        handbook = ()
    note = meta.get("handbook_note")
    if note is not None and not isinstance(note, str):
        errors.append(f"{where}: handbook_note must be a string, got {note!r}")
        note = None
    if not handbook and not note:
        errors.append(
            f"{where}: an empty handbook needs a handbook_note saying why the check "
            "deliberately exceeds the handbook"
        )
    if handbook and note:
        errors.append(
            f"{where}: handbook_note explains an empty handbook; this record cites "
            f"{len(handbook)} anchor(s), so the note belongs in the body"
        )

    raw_routes = meta.get("routes")
    routes, route_errors = _load_routes(raw_routes, where)
    errors.extend(route_errors)

    legacy_route_keys = [
        key for key in ("tooling", "needs", "ungranted_note") if key in meta
    ]
    if raw_routes is not None and legacy_route_keys:
        for key in legacy_route_keys:
            errors.append(
                f"{where}: carries both routes and {key} - a record declares "
                "what it runs once, not in two schemas; drop one"
            )

    tooling: dict[str, tuple[str, ...]] = {}
    raw_tooling = meta.get("tooling")
    if raw_tooling is not None:
        if not isinstance(raw_tooling, dict):
            errors.append(
                f"{where}: tooling must be a mapping of language to tool list"
            )
        else:
            for lang, tools in raw_tooling.items():
                names = _str_list(tools)
                if not isinstance(lang, str) or names is None:
                    errors.append(
                        f"{where}: tooling[{lang!r}] must be a list of tool-name strings"
                    )
                    continue
                tooling[lang] = names

    needs: dict[str, tuple[str, ...]] = {}
    raw_needs = meta.get("needs")
    if raw_needs is not None:
        if not isinstance(raw_needs, dict):
            errors.append(f"{where}: needs must be a mapping of tier to tool list")
        elif raw_tooling is None:
            errors.append(
                f"{where}: needs classifies tooling this record does not declare - "
                "add a tooling map, or drop needs"
            )
        else:
            offered = {name for names in tooling.values() for name in names}
            tier_of: dict[str, str] = {}
            for tier, tools in raw_needs.items():
                names = _str_list(tools)
                if tier not in NEEDS_TIERS or names is None:
                    errors.append(
                        f"{where}: needs[{tier!r}] must map one of {NEEDS_TIERS} to "
                        "a list of tool-name strings"
                    )
                    continue
                for name in names:
                    if name not in offered:
                        errors.append(
                            f"{where}: needs[{tier}] names {name!r}, which is not in "
                            "this record's tooling"
                        )
                    if name in tier_of:
                        errors.append(
                            f"{where}: {name!r} is classified both "
                            f"{tier_of[name]} and {tier}"
                        )
                    else:
                        tier_of[name] = tier
                needs[tier] = names

    silenced = _fully_tiered_languages(tooling, needs)
    if silenced and "ungranted_note" not in meta:
        errors.append(
            f"{where}: every tool this record offers for {', '.join(silenced)} "
            "needs a grant, so a withheld grant silences the check - add an "
            "ungranted_note saying what still answers, or "
            f"{UNGRANTED_NONE!r} if nothing does"
        )

    ungranted = meta.get("ungranted_note")
    if "ungranted_note" in meta:
        if ungranted is None:
            errors.append(
                f"{where}: ungranted_note is empty - YAML reads `null`, `~` and a "
                f"bare key as nothing, which is indistinguishable from omitting "
                f"the key. Write {UNGRANTED_NONE!r} if nothing answers without a "
                "grant, or say what does"
            )
        elif not isinstance(ungranted, str):
            errors.append(
                f"{where}: ungranted_note must be prose or {UNGRANTED_NONE!r}, "
                f"got {ungranted!r}"
            )
        elif not ungranted.strip():
            errors.append(
                f"{where}: ungranted_note is blank - write {UNGRANTED_NONE!r} if "
                "nothing answers without a grant, or say what does"
            )
        elif (
            ungranted.strip().lower() == UNGRANTED_NONE
            and ungranted.strip() != UNGRANTED_NONE
        ):
            errors.append(
                f"{where}: write the sentinel as {UNGRANTED_NONE!r}, not "
                f"{ungranted!r} - YAML leaves the capitalised spellings as "
                "ordinary strings, so this would be read as a claim that "
                "something answers"
            )
        else:
            ungranted = ungranted.strip()
    else:
        ungranted = None

    if not silenced and "ungranted_note" in meta:
        errors.append(
            f"{where}: ungranted_note describes a withheld grant leaving this "
            "record with nothing to run, which cannot happen here - no language "
            "it offers is fully tiered, because every one of them either lists "
            "no tools or keeps a tool that answers from a read-only clone. "
            "Remove ungranted_note, "
            "or add a tooling entry that needs a grant if this record is meant "
            "to be silenced"
        )

    # `answers_ungranted` is the routes-schema counterpart of `ungranted_note`
    # above; the two blocks stay separate because a record on the legacy
    # schema keeps using `ungranted_note` unchanged until it migrates.
    raw_answers = meta.get("answers_ungranted")
    has_answers_key = "answers_ungranted" in meta
    if has_answers_key and raw_routes is None:
        errors.append(
            f"{where}: answers_ungranted names an answering route this record "
            "does not declare - it only means something alongside a routes "
            "list, add one, or drop answers_ungranted"
        )

    answers_ungranted: str | None = None
    silenced_langs = _silenced_languages(routes) if raw_routes is not None else ()
    if raw_routes is not None:
        if silenced_langs and not has_answers_key:
            errors.append(
                f"{where}: every route that answers for {', '.join(silenced_langs)} "
                "needs a grant, so a withheld grant silences the check - add an "
                "untiered route that still answers, or answers_ungranted: "
                f"{UNGRANTED_NONE!r} if nothing does"
            )

        if has_answers_key:
            if raw_answers is None:
                errors.append(
                    f"{where}: answers_ungranted is empty - YAML reads `null`, `~` "
                    "and a bare key as nothing, which is indistinguishable from "
                    f"omitting the key. Write {UNGRANTED_NONE!r} if nothing "
                    "answers without a grant, or add an untiered route that does"
                )
            elif not isinstance(raw_answers, str):
                errors.append(
                    f"{where}: answers_ungranted must be the sentinel "
                    f"{UNGRANTED_NONE!r}, got {raw_answers!r}"
                )
            elif not raw_answers.strip():
                errors.append(
                    f"{where}: answers_ungranted is blank - write "
                    f"{UNGRANTED_NONE!r} if nothing answers without a grant, or "
                    "add an untiered route that does"
                )
            elif raw_answers.strip() != UNGRANTED_NONE:
                if raw_answers.strip().lower() == UNGRANTED_NONE:
                    errors.append(
                        f"{where}: write the answers_ungranted sentinel as "
                        f"{UNGRANTED_NONE!r}, not {raw_answers!r} - YAML leaves "
                        "the capitalised spellings as ordinary strings, so this "
                        "would be read as a claim that something answers"
                    )
                else:
                    errors.append(
                        f"{where}: answers_ungranted accepts only the sentinel "
                        f"{UNGRANTED_NONE!r} - a record with something to say "
                        "about what still answers says it with an untiered "
                        "route, not prose here"
                    )
            else:
                answers_ungranted = UNGRANTED_NONE

            if not silenced_langs:
                errors.append(
                    f"{where}: answers_ungranted describes a withheld grant "
                    "leaving this record with nothing to run, which cannot "
                    "happen here - no language it offers an answering route "
                    "for is fully tiered, because every one of them either "
                    "offers no answering route or keeps one that runs from a "
                    "read-only clone. Remove answers_ungranted, or make every "
                    "route that answers for that language need a grant if this "
                    "record is meant to be silenced"
                )

    optin = meta.get("optin", False)
    if not isinstance(optin, bool):
        errors.append(f"{where}: optin must be a boolean, got {optin!r}")
        optin = bool(optin)

    title_match = _TITLE_RE.search(body)
    if title_match is None:
        errors.append(
            f"{where}: body needs an '# ' title - it is the check's display name"
        )
        title = ""
    else:
        title = title_match.group(1)

    if errors:
        return None, errors, declared
    # `tooling`/`needs` are read by sites outside this module that predate
    # `routes`; project them from the routes rather than changing every
    # reader, so a route stays the one place a tool is declared.
    final_tooling = _project_tooling(routes) if raw_routes is not None else tooling
    final_needs = _project_needs(routes) if raw_routes is not None else needs
    return (
        Check(
            id=cid,
            domain=str(domain),
            locality=str(locality),
            title=title,
            handbook=handbook,
            handbook_note=note,
            tooling=final_tooling,
            needs=final_needs,
            ungranted_note=ungranted,
            routes=routes,
            answers_ungranted=answers_ungranted,
            optin=optin,
            path=path,
        ),
        [],
        declared,
    )


def load_checks(skills_dir: Path) -> tuple[dict[str, Check], list[str]]:
    """Load every check record owned by every domain skill.

    Collects problems rather than raising, so one run reports every
    malformed record instead of stopping at the first. A record that fails
    validation is absent from the returned mapping and explained in the
    error list.

    Args:
        skills_dir: The skills root. Each `<domain>-audit/checks/` beneath
            it holds that domain's records; a skill with no such directory
            has not migrated yet and is skipped in silence.

    Returns:
        Records keyed by id, and one message per problem.
    """
    checks: dict[str, Check] = {}
    errors: list[str] = []
    if not skills_dir.is_dir():
        return checks, errors
    declared_ids: dict[str, Path] = {}
    for skill in sorted(skills_dir.glob(f"*{SKILL_SUFFIX}")):
        root = skill / CHECKS_SUBDIR
        if not root.is_dir():
            continue
        # Walk the whole subtree, not just `checks/*.md`: a record at the
        # wrong depth would otherwise be neither loaded nor reported, and a
        # check that silently never runs is the failure this family exists
        # to prevent.
        for path in sorted(root.rglob("*.md")):
            rel = path.relative_to(skills_dir)
            if len(rel.parts) != 3:
                errors.append(
                    f"{rel.as_posix()}: a check record lives at "
                    f"<domain>{SKILL_SUFFIX}/{CHECKS_SUBDIR}/<slug>.md; this one is "
                    f"nested deeper and would never be loaded"
                )
                continue
            check, problems, declared = _load_one(path, skills_dir)
            errors.extend(problems)
            if declared is not None:
                if declared in declared_ids:
                    errors.append(
                        f"{rel.as_posix()}: duplicate check id {declared!r} "
                        f"(also declared by {declared_ids[declared].name})"
                    )
                else:
                    declared_ids[declared] = path
            if check is None:
                continue
            checks[check.id] = check
    return checks, errors
