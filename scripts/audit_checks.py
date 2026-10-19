"""Load and validate the audit check records (<origin-repo>#559).

`.agents/skills/<domain>-audit/checks/<check>.md` holds one record per
auditable check: the machine-checkable attributes in YAML frontmatter, the
judgment prose in the body. The `*-audit` skills load a subset of these at
run time - a domain's checks, sliced by locality - instead of one
`SKILL.md` per domain carrying every per-check attribute inline.

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
| `evidence` | no, and non-empty where present | What this check measures and what a row records as its evidence, where that belongs to the check rather than to any one route |
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
needs that and runs code from the target's graph, the target's own or an
installed package's, a `.pth` startup hook included. The names are deliberately
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

`evidence` is the one field that is about neither the tools nor the grant:
what does this check measure, and what does a row record as the evidence
behind it? A record whose every route measures the same thing says it once
here rather than once per route, which is the case that has no other home -
a route's own `note` is the right place for a measurement only that route
takes. It is optional on either schema and carries no derived meaning, so
an absent key claims nothing at all; that is the difference from `needs`,
whose absence is the positive claim that no tool here needs a grant. What
it must not be is present and empty, because YAML reads a bare key as
nothing and the dataclass cannot tell that from an omitted one.

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
shape without change - `test_python_fixture_spec.py` now reads it on the
legacy branch only, and `run_python_fixture_lens.py`'s `grant_tier` reads
the prescribed route instead. The shape is all the projection carries: the
tools and their tiers, and no ungranted claim, so the questions about
grants are read from the routes and never off the projected pair. Whether a
withheld grant silences a language goes through `_silenced_languages`;
whether any *tool* still answers there goes through
`_languages_whose_tools_all_need_a_grant`. The pair over-reports tiering in
two structurally different ways, which is why neither is derived from it:
`_project_tooling` keeps a `kind: subject` route's tool under its language,
which is how a language nothing there was answering reads as fully tiered;
and `_project_needs` collapses a record's routes onto their tools, so a
tool carrying one tiered route and one untiered route reads as simply
tiered - `deps/inventory`'s `cyclonedx-py` is that shape, and reading the
pair for it withheld a whole row over one tiered `alternative` route. A record
declaring `routes` may not also carry a `## Tooling fallback` section: on
this schema the routes are the fallback, and a section beside them would be
a second copy nothing holds against the first, unread by the properties
that read it on a record still declaring `tooling`.

The body is validated too, which the split above understates: it must carry
an `# ` title, being the check's display name, and it may not carry a fenced
code block in either spelling. Every command a record prescribes appears in
an inline backtick span, because that is the only place the form extractor
reads: it sweeps every record's spans for the glued-placeholder rule, over the
records on `routes:` and the ones still on `tooling:` alike, so a command in a
fence is invisible to it. A four-space indented block is
legal - its content is literal text, so a record may show a tool's output
there even where that output prints a fence.

A route may carry `answers`, the axis of the check it answers, where a
record's routes in one language answer different halves of it. Two routes
with the same value are alternatives for that axis and their `disposition`
states the precedence; two with different values are complements, and the
check is answered in that language only when every distinct value has a
route that ran, a missing axis reporting `no-evidence` with the reason on
that axis's routes rather than `ok`. `_load_routes` holds the field to all
or none per language, over the language grouping `_routes_answering_ungranted`
uses without its tier filter, a universal key judged alone only where the
record has no concrete language, and to at least two distinct values where
it appears; a record whose every route answers the whole check carries it
nowhere.

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
carrying no tier, each language's own plus the universal ones. A
language absent from its result has offered no such route at all, so it
has made no claim this rule can silence, exactly as a language absent
from `tooling` makes none under the legacy schema.

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
# The registries any route in the tree fetches from, and the language each one
# is implied by. Two members rather than a plausible list of package indexes: a
# value no record uses is a value nothing exercises, and the same reasoning
# keeps `REGISTRY_BY_LANG` to the languages that actually imply a registry -
# `lang: any` and `lang: none` imply none, which is exactly why a command route
# declaring one of those has to say the registry itself.
REGISTRIES = ("pypi", "npm")
REGISTRY_BY_LANG = {"python": "pypi", "typescript": "npm"}
ROUTE_FIELDS = frozenset(
    {
        "lang",
        "kind",
        "tool",
        "package",
        "registry",
        "argv",
        "argv_by_partition",
        "disposition",
        "needs",
        "in_env",
        "findings_stream",
        "applies_when",
        "alone_insufficient",
        "note",
        "then",
        "own_runner",
        "answers",
    }
)
# `answers` values are slugs: lowercase words joined by hyphens. The shape is
# held so that two routes meaning one axis cannot differ by case or
# whitespace and read as two axes.
_ANSWERS_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
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
        "evidence",
        "optin",
    }
)

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---(?:\n(.*))?\Z", re.DOTALL)
_TITLE_RE = re.compile(r"^# (.+?)\s*$", re.MULTILINE)
_FALLBACK_SECTION_RE = re.compile(r"^## Tooling fallback\s*$", re.M)
#: A fenced code block opening at the start of a line, in either spelling. Only
#: the fence is matched, not the block: one occurrence is the whole finding, and
#: a record with an unclosed fence is as much of a problem as one with a closed
#: one. Up to three spaces of indentation, which is CommonMark's own rule - at
#: four the line is an indented code block, so its content is literal text and a
#: fence inside it is a fence being *shown* rather than opened. No record body
#: carries an indented block today (computed: zero of 87), so that allowance
#: keeps an escape open rather than protecting a use the tree makes: a record
#: quoting the observed output of a tool that prints fences, which a docs or
#: prompt lens plausibly would.
_FENCE_RE = re.compile(r"^ {0,3}(?:```|~~~)", re.M)


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

    `then` holds a second command the record prescribes in sequence, where it
    does: `coverage run -m pytest` followed by `coverage report
    --show-missing` is one route, not two, and dropping the half that prints
    the report would leave the route looking like a tool that produced
    nothing. `own_runner` says the prescribed command is complete as written,
    so whatever launcher a lens would put in front of it puts nothing: `True`
    where every command the route prescribes needs no runner, shared argv and
    per-partition overrides alike, or the partitions whose override needs none
    where the rest of the route's commands do.

    Each of the two is a record's own declaration rather than anything derived,
    so which records carry either moves as the migration runs and `grep
    own_runner` and `grep "then:"` over the check tree is the way to ask.
    `deps/inventory` and `test/coverage-reach` are the records the two fields
    were written for - the schema moved ahead of them because neither could be
    migrated without it - and each now declares its own: `own_runner: [uv]` on
    the first, `then` on the second.

    A runner-led shared argv is the shape that wants the flag, and the test is
    the argv's own first token: a fetcher there - `npx` or a `dlx` - means the
    command already carries whatever a lens would put in front of it. Not
    "where the fetched name is not the route's tool", which sounds like the same
    rule and selects a different set: `--package dependency-cruiser` and
    `--package @stryker-mutator/core` each name the route's own tool, and
    `pytest --cov-branch` and every `npm`/`pnpm`/`yarn` subcommand lead with a
    word that is not their tool while needing a runner like anything else. Ask
    what leads the command, not what it fetches.

    Which routes have that shape moves with the migration and `grep` is the way
    to ask, for the reason the paragraph above gives. The one thing worth
    stating structurally is the split: a fetcher-led shared argv sits either on
    a route some lens may run, which wants the flag, or on a
    `disposition: forbidden` one, which no lens runs and so needs nothing - the
    `dlx depcruise` the four `dependency-cruiser` records warn against and
    `deps/inventory`'s `dlx cyclonedx-npm` are the second kind. Nothing enforces
    that split; a `forbidden` route is simply never a candidate, and the fixture
    lens drops it before it groups a record's routes. The candidates are
    `lang: typescript` routes, and on the ones it runs - a record's
    `disposition: runs` command route - the fixture lens's TypeScript half reads
    the flag: a fetcher-led route missing it would be fronted by a second fetch
    for a package named after the tool. `arch/size`'s `cloc` was the one
    exception until it stopped leading with a fetcher: its argv names the
    command and `registry: npm` names what fetches it, which is the shape the
    flag was never for.

    The residual shape neither form expresses: a route whose shared argv needs
    no runner while one partition's override does. `True` over-claims it and a
    partition list cannot name the shared command. No route in the tree is
    that shape, so it stays unexpressed rather than given a third spelling.

    `answers` names the axis of the check this route answers, where a
    record's routes in one language answer different halves of it. Two
    routes in one language with the same value are alternatives for that
    axis and their `disposition` states the precedence, as it does today;
    two with different values are complements, and the check is answered in
    that language only when every distinct value has a route that ran. A
    record whose every route answers the whole check carries the field
    nowhere, and nothing changes for it. `_load_routes` holds the field to
    all-or-none per language and to at least two distinct values where it
    appears, because a language half-axised or single-axised has declared
    nothing the field's absence does not already say.

    Neither form is verifiable here, which is worth knowing before writing
    either. Whether a command needs a runner in front of it is a fact about
    the command, so the loader checks only that a named partition exists. `True`
    on a route whose overrides are runner-led while its shared argv is not
    claims the fallback is complete as well, and every partition running the
    fallback then goes unfetched with no error raised. Write the list form
    there. `deps/inventory` takes the list form for a different reason worth
    knowing beside that one: it carries no shared argv at all, and exactly one
    of its per-partition commands - the uv partition's `uv export`, a command
    of another tool entirely - is complete as written, while the rest are
    `cyclonedx-py` subcommands a runner has to fetch. `True` would claim those
    three need no fetching either.
    """

    lang: str
    kind: str
    tool: str | None
    package: str | None
    registry: str | None
    argv: tuple[str, ...]
    argv_by_partition: dict[str, tuple[str, ...]]
    disposition: str
    needs: str | None
    in_env: bool
    findings_stream: str
    applies_when: str | None
    alone_insufficient: str | None
    note: str | None
    then: tuple[str, ...]
    own_runner: bool | tuple[str, ...]
    answers: str | None


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
    evidence: str | None
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
    is absent and is rejected when the key is written with no value; `registry`
    is a string from `REGISTRIES`, is present only where `kind` is `command`,
    and never contradicts the registry its `lang` implies, because
    those two are the same YAML to `get` and different claims to a reader;
    `argv` and `argv_by_partition` are present only where `kind` is `command`,
    and every argv they name - `argv` itself, and each partition's entry
    under `argv_by_partition` - is non-empty wherever it is written; a
    command route carries at least one of the two, but not necessarily
    `argv` itself - it is absent exactly where a per-partition map says a
    partition the map does not name has no command, rather than inheriting
    one from a shared argv that does not exist; a `disposition` names what
    it applies to, so `alternative` and `superseded` appear only where `kind`
    is `command`, there being nothing to run instead of on any other kind,
    while `forbidden` appears on a `command` route, whose argv is what is
    forbidden, or on a `procedure` route naming a `tool`, that tool being
    what is forbidden - the shape a record takes to warn against a tool it
    prescribes no invocation for, where a `library` or `subject` route
    could name neither; `then`, a second command in
    sequence, is present only where `kind` is `command` and, where present, is
    a non-empty list of argv strings, because a route with no first command
    has none for a second to follow and an empty second command is the
    absence the field exists to prevent; `own_runner`, which says a command
    needs no launcher prefix in front of it, is present only where `kind` is
    `command`, is never written `false` or as an empty list since an absent
    key already carries what both of those would mean, is `true` where every
    command the route prescribes needs no prefix - its shared `argv` and each
    partition's entry alike, or, on a route carrying no shared `argv`, the
    entries its map names, those being every command it prescribes - and is
    otherwise a list of partition names, rejected unless `argv_by_partition`
    carries every name listed. Whichever
    form it takes, it is never written beside `in_env`, whose materialized
    environment the suppressed prefix would otherwise never reach; and `true`
    is never written beside `registry`, which names where a fetch that never
    happens would have come from - while a universal command route that is
    *not* `true` must carry one, since neither `any` nor `none` implies a
    registry and nothing else in the record would say. Last,
    a route naming no tool carries a non-empty `note`: with neither a tool
    nor an argv the note is the whole prescription, and it is the one route
    kind where nothing downstream stands in for it - a `kind: command`
    route missing a note still has its argv to say what to do. Checked only
    where `kind` is `procedure`, since a tool-less route of any other kind
    is already rejected above and one mistake earns one message. A
    `forbidden` procedure route carries a non-empty `note` for the mirror
    reason: with no argv to forbid, the note is what says what not to run
    and why, and without it the route names a tool and warns of nothing.
    `answers`,
    where written, is a slug (lowercase words joined by hyphens), never the
    word `none`, which is `answers_ungranted`'s sentinel one line away and
    would read as it, and never on a `kind: subject` or a
    `disposition: forbidden` route, since neither answers anything. Then,
    over the whole list, all-or-none per language: the routes in scope for a
    language are its own answering-kind, non-forbidden routes plus the
    universal ones (`lang: any`, `lang: none`), which apply to every
    language at run time - the same scoping `_routes_answering_ungranted`
    uses, a universal key being scoped on its own only where the record has
    no concrete language - and where any route in that scope carries
    `answers`, every route in it must, and the values must be at least two distinct ones, because
    a lone value says nothing the field's absence does not already say and
    a schema that accepts a behavioural no-op is a field a future author
    fills without thinking.

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
        # An unrecognized `lang` is recovered as `any` so the rest of the route
        # still loads and reports its own problems, but the recovery is not a
        # claim the author made. The registry requirement below fires on `any`,
        # so without this flag a typo'd language earns a second error demanding
        # a field that stops being required the moment `lang` is corrected -
        # and demanding it under a language the record never wrote.
        lang_recovered = lang not in ROUTE_LANGS
        if lang_recovered:
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
        elif disposition in ("alternative", "superseded") and kind != "command":
            errors.append(
                f"{loc}: disposition {disposition!r} needs kind: command - a "
                f"{kind!r} route has nothing for the harness to run instead of"
            )
        elif disposition == "forbidden" and kind not in ("command", "procedure"):
            errors.append(
                f"{loc}: disposition 'forbidden' needs kind: command or kind: "
                f"procedure - a forbidden route names what it forbids, the argv "
                f"of a command route or the tool of a procedure route, and a "
                f"{kind!r} route names neither as a thing to warn against"
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
        elif tool is None and disposition == "forbidden":
            errors.append(
                f"{loc}: tool is required on a disposition: forbidden procedure "
                "route - with no argv, the tool is the thing the route warns "
                "against, and a route forbidding neither a command nor a tool "
                "forbids nothing"
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

        # Written-but-empty is its own mistake, and `registry` needs the same
        # guard `package` has for the same reason: YAML reads a bare key as
        # nothing, so without this the two rules below never fire and an
        # illegal shape loads clean. Tracked separately from the value because
        # the required rule must not then tell an author to add a field they
        # did write - it would name a fix already applied.
        registry_declared = "registry" in entry
        registry = entry.get("registry")
        if registry_declared and registry is None:
            errors.append(
                f"{loc}: registry is empty - YAML reads `null`, `~` and a bare "
                "key as nothing, which is not the same as an absent key: an "
                "absent key means the registry is whatever `lang` implies, "
                "while this one declares a field and says nothing with it, so "
                "the kind and own_runner rules below would pass over it. Name "
                "the registry, or drop the key"
            )
        if registry is not None and not isinstance(registry, str):
            errors.append(f"{loc}: registry must be a string, got {registry!r}")
            registry = None
        elif registry is not None and registry not in REGISTRIES:
            errors.append(
                f"{loc}: registry {registry!r} is not one of {list(REGISTRIES)} - "
                "the vocabulary holds the registries this family actually fetches "
                "from, so a new one is a decision to record rather than a value "
                "to spell, and an unrecognised one would be read by a consumer "
                "choosing a runner as no registry at all"
            )
            registry = None
        if registry is not None:
            if kind != "command":
                errors.append(
                    f"{loc}: registry on a kind: {kind} route - only a command "
                    "route prescribes something a one-shot runner goes in front "
                    "of, so a registry here names where a fetch that never "
                    "happens would have come from"
                )
            implied = REGISTRY_BY_LANG.get(lang)
            if implied is not None and implied != registry:
                errors.append(
                    f"{loc}: registry {registry!r} contradicts lang {lang!r}, "
                    f"which implies {implied!r}. A route whose tool really comes "
                    "from another language's registry is a lang: any route with "
                    "a note saying so; accepting the disagreement here would let "
                    "the field mean whichever of the two a consumer read first"
                )

        raw_argv = entry.get("argv")
        raw_per_partition = entry.get("argv_by_partition")
        for empty_key in ("argv", "argv_by_partition", "then", "own_runner"):
            if empty_key in entry and entry[empty_key] is None:
                errors.append(
                    f"{loc}: {empty_key} is empty - YAML reads `null`, `~` and "
                    "a bare key as nothing, so the key declares nothing and is "
                    "not the absent key either. Every one of these four is read "
                    "with a `get`, so a value left off arrives as an absent key "
                    "and takes whatever an absent key means - which for `argv` "
                    "beside `argv_by_partition` is the claim that the "
                    "partitions the map does not name have no command at all, "
                    "and for `own_runner` is that the launcher applies. Write "
                    "the value, or drop the key to make its absence the claim "
                    "on purpose"
                )
        if kind == "command":
            parsed_argv = _str_list(raw_argv)
            if raw_argv is not None and parsed_argv is None:
                errors.append(
                    f"{loc}: argv must be a list of argv strings, got {raw_argv!r}"
                )
                argv = ()
            elif parsed_argv == ():
                errors.append(
                    f"{loc}: argv is present and empty - an absent argv beside "
                    "argv_by_partition says the partitions it does not name "
                    "have no command, and an empty one says nothing at all"
                )
                argv = ()
            elif parsed_argv is None and not raw_per_partition:
                errors.append(
                    f"{loc}: a command route carries no command at all - name "
                    "the shared argv, or name one per partition where the "
                    "record prescribes a different command for each and none "
                    "for some"
                )
                argv = ()
            else:
                argv = parsed_argv or ()
        else:
            if raw_argv is not None:
                errors.append(
                    f"{loc}: argv is only valid on a command route, not {kind!r}"
                )
            argv = ()

        raw_argv_by_partition = entry.get("argv_by_partition")
        argv_by_partition: dict[str, tuple[str, ...]] = {}
        if raw_argv_by_partition is not None:
            if kind != "command":
                errors.append(
                    f"{loc}: argv_by_partition is only valid on a command route, "
                    f"not {kind!r}"
                )
            elif not isinstance(raw_argv_by_partition, dict):
                errors.append(
                    f"{loc}: argv_by_partition must be a mapping of partition to argv"
                )
            else:
                for partition, partition_argv in raw_argv_by_partition.items():
                    names = _str_list(partition_argv)
                    if not isinstance(partition, str) or names is None:
                        errors.append(
                            f"{loc}: argv_by_partition[{partition!r}] must be a "
                            "list of argv strings"
                        )
                        continue
                    if not names:
                        errors.append(
                            f"{loc}: argv_by_partition[{partition!r}] is empty - a "
                            "command route carries a command for every partition "
                            "it names, and an empty one declares that partition "
                            "answered by nothing at all, which is the same "
                            "absence a written-but-empty shared argv is rejected "
                            "for"
                        )
                        continue
                    argv_by_partition[partition] = names

        in_env = entry.get("in_env", False)
        if not isinstance(in_env, bool):
            errors.append(f"{loc}: in_env must be a boolean, got {in_env!r}")
            in_env = bool(in_env)

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
                elif names == argv or names in argv_by_partition.values():
                    errors.append(
                        f"{loc}: then repeats a command this route already "
                        "prescribes, so the two halves of the sequence are one "
                        "command written twice. A consumer building the route's "
                        "declared forms gets the same string from both halves, "
                        "and a form declared twice is the ambiguity a form list "
                        "cannot carry"
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
                        f"{loc}: own_runner must be true or a list of partition "
                        f"names, got {raw_own_runner!r}"
                    )
                elif not names:
                    errors.append(
                        f"{loc}: own_runner is an empty list, which loads to "
                        "exactly what an absent key loads to and so claims "
                        "nothing; write true where every command this route "
                        "prescribes is complete, name the partitions whose "
                        "command is, or drop the key"
                    )
                elif not argv_by_partition:
                    errors.append(
                        f"{loc}: own_runner names {list(names)} and the route "
                        "carries no argv_by_partition, so it names partitions "
                        "this route does not distinguish; write true where the "
                        "one argv needs no runner"
                    )
                else:
                    unknown = [n for n in names if n not in argv_by_partition]
                    if unknown:
                        errors.append(
                            f"{loc}: own_runner names {unknown}, which "
                            "argv_by_partition does not carry, so the suppressed "
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
            if own_runner is True and registry is not None:
                errors.append(
                    f"{loc}: registry beside own_runner: true - that says the "
                    "prescribed command is complete as written, so nothing is "
                    "fetched and the registry names where a fetch that never "
                    "happens would have gone. Drop one: a standalone binary in "
                    "no registry says own_runner, and a tool a runner fetches "
                    "says registry"
                )
        if (
            kind == "command"
            and lang in UNIVERSAL_ROUTE_LANGS
            and not lang_recovered
            and own_runner is not True
            and registry is None
            and not registry_declared
        ):
            errors.append(
                f"{loc}: a kind: command route with lang: {lang} needs a registry "
                f"- one of {list(REGISTRIES)}, or own_runner: true where the "
                "command is complete as written. Neither `any` nor `none` implies "
                "a registry, so nothing else in the record says which one a runner "
                "should reach, and a consumer left to infer it from the partition "
                "runs whatever package that registry happens to carry under the "
                "same name"
            )

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

        answers: str | None = None
        if "answers" in entry:
            raw_answers = entry.get("answers")
            if not isinstance(raw_answers, str) or not raw_answers.strip():
                errors.append(
                    f"{loc}: answers must be a non-empty slug naming the axis this "
                    f"route answers, got {raw_answers!r}"
                )
            elif raw_answers == UNGRANTED_NONE:
                errors.append(
                    f"{loc}: answers: none reads as answers_ungranted's sentinel and "
                    "names no axis; a route that answers nothing does not carry "
                    "answers at all"
                )
            elif not _ANSWERS_RE.match(raw_answers):
                errors.append(
                    f"{loc}: answers must be a slug of lowercase words joined by "
                    f"hyphens, got {raw_answers!r}, so that two spellings of one "
                    "axis cannot read as two axes"
                )
            elif kind == "subject":
                errors.append(
                    f"{loc}: answers on a kind: subject route - such a route names "
                    "what the check inspects rather than what answers it, so it "
                    "answers no axis"
                )
            elif disposition == "forbidden":
                errors.append(
                    f"{loc}: answers on a disposition: forbidden route - a route "
                    "the record warns against running answers no axis"
                )
            else:
                answers = raw_answers

        note = entry.get("note")
        if note is not None and not isinstance(note, str):
            errors.append(f"{loc}: note must be a string, got {note!r}")
            note = None
        elif tool is None and kind == "procedure" and not (note or "").strip():
            errors.append(
                f"{loc}: a route naming no tool needs a note - it is the "
                "prescription. With no tool and no argv, the note is the whole "
                "of what this route says to do, so without one the record "
                "offers a way of answering the check that carries nothing an "
                "agent or a consumer can act on, and reads through the "
                "projected tooling/needs pair exactly like a route that works"
            )
        elif (
            tool is not None
            and kind == "procedure"
            and disposition == "forbidden"
            and not (note or "").strip()
        ):
            errors.append(
                f"{loc}: a forbidden procedure route needs a note - with no argv "
                "to forbid, the note is what says what not to run and why, and "
                "without it the route names a tool and warns of nothing an agent "
                "can act on"
            )

        routes.append(
            Route(
                lang=lang,
                kind=kind if kind in ROUTE_KINDS else "procedure",
                tool=tool,
                package=package,
                registry=registry,
                argv=argv,
                argv_by_partition=argv_by_partition,
                disposition=disposition,
                needs=needs,
                in_env=in_env,
                findings_stream=findings_stream,
                applies_when=applies_when,
                alone_insufficient=alone_insufficient,
                note=note,
                then=then,
                own_runner=own_runner,
                answers=answers,
            )
        )

    errors.extend(_answers_errors(tuple(routes), where))
    return tuple(routes), errors


def _answers_scopes(routes: tuple[Route, ...]) -> dict[str, tuple[Route, ...]]:
    """Group a record's answering routes by the language they answer for.

    The scope of a language is its own answering-kind, non-forbidden routes
    plus the universal ones (`lang: any`, `lang: none`), because a universal
    route applies whatever the partition's language is: a `lang: python`
    route carrying `answers: pin` beside an unaxised `lang: any` route is a
    Python partition running an axised route and an unaxised one together,
    which is the half-axised record the rule forbids. The same scoping
    `_routes_answering_ungranted` uses, without its tier filter, because
    which axis a route answers does not depend on what it needs.

    A universal key is scoped only where the record has no concrete
    language at all, as `deps/model-pinning-and-eol` has two `lang: any`
    routes and nothing else: there the universal routes are the whole
    record and are held to the rules as a language. Where a concrete
    language exists, every universal route is already inside that
    language's scope and judged there, and judging it again under its own
    key would demand two axes of a single `any` route that carries the one
    axis the concrete languages leave to it - `test/isolation`'s grep for
    real I/O beside its per-runner timing routes.
    """
    by_lang: dict[str, list[Route]] = {}
    for route in routes:
        if route.kind in ANSWERING_ROUTE_KINDS and route.disposition != "forbidden":
            by_lang.setdefault(route.lang, []).append(route)
    universal = [
        route
        for lang, lang_routes in by_lang.items()
        if lang in UNIVERSAL_ROUTE_LANGS
        for route in lang_routes
    ]
    concrete = {lang for lang in by_lang if lang not in UNIVERSAL_ROUTE_LANGS}
    return {
        lang: tuple(lang_routes + [r for r in universal if r.lang != lang])
        for lang, lang_routes in by_lang.items()
        if not concrete or lang in concrete
    }


def _answers_errors(routes: tuple[Route, ...], where: str) -> list[str]:
    """The per-language rules on `answers`: all or none, and two distinct values.

    Returns one message per language that breaks either rule, naming the
    routes with and without the field or the lone value, so a many-route
    record says which language and which routes.
    """
    errors: list[str] = []
    for lang, scope in sorted(_answers_scopes(routes).items()):
        with_field = [r for r in scope if r.answers is not None]
        if not with_field:
            continue
        without = [r for r in scope if r.answers is None]
        if without:
            errors.append(
                f"{where}: answers is written on {len(with_field)} of the "
                f"{len(scope)} answering routes in scope for lang: {lang} "
                f"(missing on {sorted({f'{r.lang}/{r.tool or r.kind}' for r in without})}) "
                "- the field is all or none per language, because a route with no "
                "axis beside axised ones is a route whose result the engine cannot "
                "place"
            )
        values = sorted({r.answers for r in with_field if r.answers is not None})
        if len(values) == 1:
            errors.append(
                f"{where}: every answering route in scope for lang: {lang} carries "
                f"answers: {values[0]} - a lone value declares nothing the field's "
                "absence does not already say; name at least two axes or drop the "
                "field"
            )
    return errors


def registry_for(route: Route) -> str | None:
    """Which registry a fetch would have to reach, if this route needs a fetch.

    The route's own `registry` where it declares one, and the registry its
    `lang` implies otherwise. `None` only where the route settles the question
    itself: it prescribes no command, or its command is complete as written.

    **It does not answer whether a fetch applies at all, and a caller must not
    read it that way.** 21 of the 76 command routes that get an answer here
    need no fetch: a subcommand of the target's own package manager - `npm
    audit`, `pip list --outdated` - is run directly, and a route whose argv
    already leads with a runner has its fetch spelled out. Both are
    `kind: command` with a language, so both derive a registry, and a caller
    that treats a non-`None` answer as "put this runner in front" produces
    `npx npm audit`. Deciding that is the three-kinds question, which no field
    answers yet; this one only says where to look once something else has
    decided a package must be obtained.

    One implementation because the derivation is the whole point of the field:
    a consumer working it out for itself is a second copy of the rule, and the
    failure the field exists to prevent is exactly a consumer inferring a
    registry from something that does not name one.

    Args:
        route: The route to read.

    Returns:
        A member of `REGISTRIES`, or `None` where the route settles the
        question itself - it prescribes no command, or its command is complete
        as written. Not a verdict on whether a fetch applies, per above.
    """
    if route.kind != "command" or route.own_runner is True:
        return None
    if route.registry is not None:
        return route.registry
    return REGISTRY_BY_LANG.get(route.lang)


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


def _languages_whose_tools_all_need_a_grant(
    routes: tuple[Route, ...],
) -> tuple[str, ...]:
    """Languages where every route that names a tool needs a grant.

    The counterpart of `_fully_tiered_languages` for routes, and the one
    that reads per route rather than per tool. That difference is the
    whole point of it: `_project_needs` collapses a record's routes onto
    their tools, so a tool with a tiered route and an untiered one reads
    through the projected pair as simply tiered, and a record cannot then
    tier one invocation mode without its whole language reading as tiered.
    `deps/inventory` is that shape - `cyclonedx-py` carries the
    per-partition file-parsing subcommands untiered and `environment`
    under `target-execution`, because it starts the installed environment's
    interpreter - and reading it off the projection says the
    grant changes what the check answers when the route it prescribes by
    default is untiered and answers the same either way.

    Distinct from `_silenced_languages`, which the two bracket rather than
    duplicate. That one asks whether *anything* still answers; this asks
    whether any *tool* still answers, and the pair gives three states
    rather than two: a language with an untiered route naming a tool is
    absent here, so the grant changes nothing; a language present here but
    absent from `_silenced_languages` has lost its tools and kept an
    untiered reading, so what it answers ungranted is different and has to
    be stated; a language in both has nothing left at all and says so with
    `answers_ungranted`. Nothing in validation reads this - it is not a
    rule a record can break - and it lives here rather than in the fixture
    round that asks it because it is a fact about routes, and a route is
    declared here.

    The three exclusions are the ones `_routes_answering_ungranted`
    applies, for the same reasons. A `kind: subject` route names what the
    check inspects rather than what runs it, so counting
    `arch/complexity-gate`'s untiered `ruff`, `radon` and `xenon` as tools
    that answer would read that record as unaffected by a grant it never
    claimed to need. A `disposition: forbidden` route is one the record
    warns against. And a route under one of `UNIVERSAL_ROUTE_LANGS`
    applies whatever the partition's language is, so its tool belongs to
    every language the record answers for, not only to the key it is filed
    under - tiered or not, since here the question is which tools the
    language has rather than which of them survive.

    Args:
        routes: The record's parsed routes.

    Returns:
        The languages, sorted. A language naming no tool at all is absent,
        mirroring `_fully_tiered_languages`' own rule that a language
        offering no tools has said nothing about grants: `all()` over an
        empty list is not a claim. So is a language with no answering-kind,
        non-forbidden route to begin with.
    """
    by_lang: dict[str, list[Route]] = {}
    for route in routes:
        if route.kind in ANSWERING_ROUTE_KINDS and route.disposition != "forbidden":
            by_lang.setdefault(route.lang, []).append(route)
    universal = [
        route
        for lang_routes in by_lang.values()
        for route in lang_routes
        if route.lang in UNIVERSAL_ROUTE_LANGS
    ]
    fully_tiered = []
    for lang, lang_routes in sorted(by_lang.items()):
        in_scope = lang_routes + [r for r in universal if r.lang != lang]
        tooled = [route for route in in_scope if route.tool is not None]
        if tooled and all(route.needs is not None for route in tooled):
            fully_tiered.append(lang)
    return tuple(fully_tiered)


def _silenced_languages(routes: tuple[Route, ...]) -> tuple[str, ...]:
    """Languages a withheld grant silences under the `routes` schema.

    Mirrors `_fully_tiered_languages` for routes: a language is silenced
    when it offers at least one answering-kind route and every one of them
    needs a grant, i.e. `_routes_answering_ungranted` maps it to an empty
    tuple. A language absent from that mapping altogether - no answering
    route at all - is not one of them, for the same reason `all()` over an
    empty list must not be read as a claim.

    `_languages_whose_tools_all_need_a_grant` asks the neighbouring
    question - whether any *tool* still answers, rather than whether
    anything does - and its docstring gives the three states the two
    describe between them. A language silenced here is in that result too,
    because a language with nothing answering has no untiered tool
    answering either; the converse does not hold, and that gap is exactly
    the record whose tools are gone and whose untiered reading is not.

    Args:
        routes: The record's parsed routes.

    Returns:
        The languages, sorted, so a message naming them is stable.
    """
    answering = _routes_answering_ungranted(routes)
    return tuple(lang for lang, untiered in sorted(answering.items()) if not untiered)


def _load_one(
    path: Path, skills_dir: Path, *, legacy_schema: bool = False
) -> tuple[Check | None, list[str], str | None]:
    """Parse and validate a single record in isolation.

    Args:
        path: The record file, at `<domain>-audit/checks/<slug>.md`.
        skills_dir: The skills root the record's expected id is relative to.
        legacy_schema: Accept a record-level `tooling:`/`needs:` instead of
            refusing it, as `load_checks` documents.

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
    # Sorted by a stable string form for the same reason the route keys are:
    # YAML admits a non-string mapping key, and sorting a set holding both a
    # string and an int raises `TypeError`, which would leave `_load_one`
    # raising out of `load_checks` and lose every other problem in the tree to
    # one malformed record. This path serves every record rather than only a
    # migrated one, so it reaches further than the route-level check does.
    for key in sorted(set(meta) - FIELDS, key=repr):
        if isinstance(key, str):
            errors.append(f"{where}: unknown frontmatter key {key!r}")
        else:
            errors.append(
                f"{where}: frontmatter key {key!r} is not a string - every "
                "field is named by a string, so a key YAML parsed as anything "
                "else names none of them whatever it was meant to say"
            )

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

    evidence = meta.get("evidence")
    if "evidence" in meta:
        if evidence is None:
            errors.append(
                f"{where}: evidence is empty - YAML reads a bare key as `None`, "
                "which is indistinguishable from omitting it once it reaches the "
                "dataclass, and the two say opposite things. Write what the check "
                "measures, or drop the key"
            )
        elif not isinstance(evidence, str):
            errors.append(
                f"{where}: evidence must be a string, got {evidence!r} - it is one "
                "statement about the check, not a list of them"
            )
            evidence = None
        elif not evidence.strip():
            errors.append(
                f"{where}: evidence is blank - write what the check measures, or "
                "drop the key"
            )
        else:
            evidence = evidence.strip()

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
    # `routes:` is the schema, not one of two: every record was migrated onto
    # it, so a record-level `tooling:` or `needs:` is refused outright rather
    # than read as the legacy schema. A route's own `needs` field is a key of
    # the route, not of the record, and is untouched. The readers below still
    # parse the two keys, because retiring them is its own change; on a tree
    # that loads they now read nothing.
    elif raw_routes is None and not legacy_schema:
        for key in ("tooling", "needs"):
            if key in meta:
                errors.append(
                    f"{where}: declares a record-level {key}, the legacy schema "
                    "every record has migrated off - declare `routes:` instead, "
                    "one route per way of answering the check, with each "
                    "route's own `needs` field carrying its tier"
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

    if _FENCE_RE.search(body):
        errors.append(
            f"{where}: body carries a fenced code block. Every command a record "
            "prescribes appears in an inline backtick span, because that is the "
            "only place the form extractor reads, for the glued-placeholder "
            "sweep over every record on either schema: a command in a fence is "
            "invisible to it, and the suite stays green over it. Write the "
            "command in a span in its own paragraph. A four-space indented "
            "block is not this: its content is literal text, so a record may "
            "show a tool's output there even where that output prints a fence"
        )

    if raw_routes is not None and _FALLBACK_SECTION_RE.search(body):
        errors.append(
            f"{where}: declares routes: and carries a `## Tooling fallback` "
            "section. On this schema the routes are the fallback - a route's "
            "note says what to run, its alone_insufficient says what running it "
            "is not enough for on its own, and its needs says what must be "
            "present first. A section beside them is a second copy nothing "
            "holds against the first, and the properties that would have read "
            "it do not read a migrated record"
        )

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
            evidence=evidence,
            optin=optin,
            path=path,
        ),
        [],
        declared,
    )


def load_checks(
    skills_dir: Path, *, legacy_schema: bool = False
) -> tuple[dict[str, Check], list[str]]:
    """Load every check record owned by every domain skill.

    Collects problems rather than raising, so one run reports every
    malformed record instead of stopping at the first. A record that fails
    validation is absent from the returned mapping and explained in the
    error list.

    Args:
        skills_dir: The skills root. Each `<domain>-audit/checks/` beneath
            it holds that domain's records; a skill with no such directory
            has not migrated yet and is skipped in silence.
        legacy_schema: Accept a record declaring the legacy record-level
            `tooling:`/`needs:` pair instead of refusing it. Every record
            declares `routes:`, so a tree is always loaded without it; it
            exists so the legacy readers, which are retired in their own
            change rather than in the one that started refusing the schema,
            can still be exercised by their tests until then, and it goes
            with them.

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
            check, problems, declared = _load_one(
                path, skills_dir, legacy_schema=legacy_schema
            )
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


def fallback_lives_in_prose(check: Check) -> bool:
    """Whether this record's `## Tooling fallback` prose is its source of truth.

    A record declaring `tooling:` states what to run instead in that section and
    nowhere else. A record declaring `routes:` states the same thing per route -
    the `note`, the `alone_insufficient` and the `needs` - and carries no such
    section at all. The record suite scopes two properties by this: a legacy
    record naming no tool must say in its body what to read instead, and a
    legacy record classifying a tool under `needs` must state a fallback; on a
    routed record both questions are answered by the routes and the loader.

    Keyed on the declared schema rather than on whether the section is present.
    Presence is what those properties check, and a scope keyed on it would
    switch each one off on exactly the record it was written to catch.
    """
    return not check.routes
