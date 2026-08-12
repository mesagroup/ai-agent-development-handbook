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
| `optin` | no | Default `false`; an opt-in sub-audit that produces findings |

`handbook` is a list because a check is commonly grounded in several
clauses. It is not required to be exhaustive - the matrix is the
authoritative edge set - but everything it lists must be true, and a check
some row cites may not claim to be ungrounded.

A `tooling` value is a list of names, not of invocations, and a name may be
a registry package, a subcommand of the target's own package manager, or a
standalone binary in no registry. Nothing here validates which - a name is
only a string to this loader - so the record's `## Tooling fallback` is where
the kind and the precedence between them are stated.

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
        "optin",
    }
)

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---(?:\n(.*))?\Z", re.DOTALL)
_TITLE_RE = re.compile(r"^# (.+?)\s*$", re.MULTILINE)


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
    return (
        Check(
            id=cid,
            domain=str(domain),
            locality=str(locality),
            title=title,
            handbook=handbook,
            handbook_note=note,
            tooling=tooling,
            needs=needs,
            ungranted_note=ungranted,
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
