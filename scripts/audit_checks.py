"""Load and validate the audit check records (#559).

`.agents/skills/audit-core/checks/<domain>/<check>.md` holds one record per
auditable check: the machine-checkable attributes in YAML frontmatter, the
judgment prose in the body. The `*-audit` skills load a subset of these at
run time - a domain's checks, sliced by locality - instead of eight
`SKILL.md` files each carrying the same five per-check attributes inline.

This module owns loading and *intra-record* validation: is this one file
well formed on its own. Cross-referencing a record against the traceability
matrix - does its `handbook` anchor name a row that actually cites it -
lives in `render_handbook_traceability.py`, which already holds the matrix
and the handbook headings. That keeps one gate
(`render_handbook_traceability.py --check`) reporting every problem.

Frontmatter fields:

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Stable `<domain>/<slug>`, and the file's own path |
| `domain` | yes | The owning domain, and the file's own directory |
| `locality` | yes | `local` (decidable from one partition) or `global` |
| `handbook` | yes | Handbook row ids grounding the check; may be empty |
| `handbook_note` | iff `handbook` is empty | Why the check exceeds the handbook |
| `tooling` | no | Language to preferred tools; `any` for language-agnostic |
| `optin` | no | Default `false`; an opt-in sub-audit that produces findings |

`handbook` is a list because a check is commonly grounded in several
clauses. It is not required to be exhaustive - the matrix is the
authoritative edge set - but everything it lists must be true, and a check
some row cites may not claim to be ungrounded.

Usage:
    from audit_checks import CHECKS_DIR, load_checks

    checks, errors = load_checks(CHECKS_DIR)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKS_DIR = REPO_ROOT / ".agents" / "skills" / "audit-core" / "checks"

LOCALITIES = ("local", "global")
FIELDS = frozenset(
    {"id", "domain", "locality", "handbook", "handbook_note", "tooling", "optin"}
)

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)
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
    return meta, m.group(2), None


def _str_list(value: Any) -> tuple[str, ...] | None:
    """Coerce a YAML value to a tuple of strings, or `None` if it is not one."""
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        return None
    return tuple(value)


def _load_one(path: Path, checks_dir: Path) -> tuple[Check | None, list[str]]:
    """Parse and validate a single record in isolation.

    Args:
        path: The record file.
        checks_dir: The root the record's expected id is relative to.

    Returns:
        The record (or `None` if it failed) and one message per problem.
    """
    rel = path.relative_to(checks_dir)
    where = rel.as_posix()
    meta, body, err = _split_frontmatter(path.read_text())
    if meta is None:
        return None, [f"{where}: {err}"]

    errors: list[str] = []
    for key in sorted(set(meta) - FIELDS):
        errors.append(f"{where}: unknown frontmatter key {key!r}")

    expected_id = rel.with_suffix("").as_posix()
    cid = meta.get("id")
    if not isinstance(cid, str):
        errors.append(f"{where}: id must be a string, got {cid!r}")
        cid = expected_id
    elif cid != expected_id:
        errors.append(
            f"{where}: id {cid!r} does not match its path (expected {expected_id!r})"
        )

    domain = meta.get("domain")
    expected_domain = rel.parts[0] if len(rel.parts) > 1 else None
    if domain != expected_domain:
        errors.append(
            f"{where}: domain {domain!r} does not match its directory {expected_domain!r}"
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
        return None, errors
    return (
        Check(
            id=cid,
            domain=str(domain),
            locality=str(locality),
            title=title,
            handbook=handbook,
            handbook_note=note,
            tooling=tooling,
            optin=optin,
            path=path,
        ),
        [],
    )


def _declared_id(path: Path) -> str | None:
    """Best-effort peek at a record's raw declared id, without validating it.

    Used only to detect id collisions across files independently of whether
    each file otherwise passes validation: a file that fails validation for
    an unrelated reason (for instance, its id does not match its own path)
    can still collide with another file's id, and both problems are worth
    reporting. A validated `Check.id` can never collide with another,
    because it is required to equal its own file's path-derived id and
    paths are unique, so duplicate detection has to run on the raw value.

    Args:
        path: The record file.

    Returns:
        The declared id, or `None` if the frontmatter is missing, malformed,
        or the `id` field is absent or not a string.
    """
    meta, _, _ = _split_frontmatter(path.read_text())
    if meta is None:
        return None
    cid = meta.get("id")
    return cid if isinstance(cid, str) else None


def load_checks(checks_dir: Path) -> tuple[dict[str, Check], list[str]]:
    """Load every check record under a checks tree.

    Collects problems rather than raising, so one run reports every
    malformed record instead of stopping at the first. A record that fails
    validation is absent from the returned mapping and explained in the
    error list.

    Args:
        checks_dir: Root of the checks tree, one subdirectory per domain.
            A tree that does not exist yet loads empty and clean.

    Returns:
        Records keyed by id, and one message per problem.
    """
    checks: dict[str, Check] = {}
    errors: list[str] = []
    if not checks_dir.is_dir():
        return checks, errors
    declared_ids: dict[str, Path] = {}
    for path in sorted(checks_dir.glob("*/*.md")):
        check, problems = _load_one(path, checks_dir)
        errors.extend(problems)
        declared = _declared_id(path)
        if declared is not None:
            if declared in declared_ids:
                errors.append(
                    f"{path.relative_to(checks_dir).as_posix()}: duplicate check id "
                    f"{declared!r} (also declared by {declared_ids[declared].name})"
                )
            else:
                declared_ids[declared] = path
        if check is None:
            continue
        checks[check.id] = check
    return checks, errors
