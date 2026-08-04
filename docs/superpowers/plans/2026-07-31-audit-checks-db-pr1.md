# Audit checks database, PR 1: schema, validator, loader and the `arch` pilot

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the `arch-audit` skill's per-check content into ten machine-readable check records under `.agents/skills/audit-core/checks/arch/`, rewire the traceability matrix's 15 `arch-audit` references onto stable check ids, and reduce `arch-audit/SKILL.md` to a domain header.

**Architecture:** A check record is a Markdown file with YAML frontmatter: machine-checkable attributes in the frontmatter, judgment prose in the body. A new library module `scripts/audit_checks.py` loads records and validates each one in isolation. `scripts/render_handbook_traceability.py` gains the cross-reference half - it already holds the matrix and the handbook headings, so it stays the single gate. During PR 1 the matrix's `checks[]` list accepts both forms: a bare string is a check id, a mapping is the legacy `{skill, dimension}` pair the other seven domains still use. PR 3 removes the legacy path.

**Tech Stack:** Python 3.11+, `pyyaml`, `pytest`, `ruff`, `pyright`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-07-31-audit-checks-db-design.md`. Issue: [lidia-tech/lidia-agents#559](https://github.com/lidia-tech/lidia-agents/issues/559).

> **One path changed after this plan ran.** Every `.agents/skills/audit-core/checks/arch/` below is now `.agents/skills/arch-audit/checks/`: the records live in the domain's own skill, so a domain is one portable directory and a record is one hop from the `SKILL.md` naming it rather than two hops through a sibling skill. The check ids and every matrix reference were unaffected. The reasoning is in decision 1 of the spec; the paths below are left as the tasks were actually dispatched.

## Spec deviations recorded before implementation

Four numbers in the spec were estimates. Measuring the real data changed them; the plan follows the measurement, and the PR body must state each deviation.

1. **Ten arch checks, not eleven.** The eight `## 2. Dimensions` bullets, with `Coupling & cohesion` split into `coupling` and `over-decomposition` (the spec's own decision-1 file listing splits them, and `arch-audit` §1 already treats them as two global dimensions), plus the opt-in Martin metrics. The other two opt-in sub-audits are deliverables, not checks, per spec decision 4.
2. **Fifteen matrix references across eight rows**, not seven. The spec's "7" counted the *distinct dimensions* cited. Seven of arch's eight dimensions are cited; `Hidden coupling` is cited by none.
3. **`handbook` is a list, not a scalar.** `arch/layering` is cited by six matrix rows and `arch/over-abstraction` by two. A single field would force an arbitrary primary and under-report the grounding the agent reading the record needs. Empty list plus a required `handbook_note` replaces the spec's literal `none`.
4. **The spec's example anchor `three-layer-model/the-dependency-rule` does not exist.** The dependency rule lives at `codebase-structure/point-every-dependency-toward-the-core-and-never-cycle-a`. Use the real anchors from the table in Task 3.

Two items the spec's Files table assigns to PR 1 that must **not** land here:

- **`audit/SKILL.md` domain detection from the checks tree.** After PR 1 the tree holds one domain and eight skills exist; detecting from the tree would silently drop seven domains from `/audit all`. Moves to PR 2, when the tree is complete.
- **Removing `skill_dimensions()`.** Seven domains still depend on it. That is PR 3, as the spec's own sequencing says.

## Global Constraints

Copied verbatim into every task's dispatch.

- **Work in `<worktree-root>`**, the absolute path of the worktree this plan is executed from. The dispatcher resolves it once with `git rev-parse --show-toplevel` and interpolates it into every task dispatch; each agent confirms its own `--show-toplevel` matches before reading or editing anything. Do not `cd` to the primary checkout.
- **Never pass a line starting with `#` to the Bash tool.**
- **Never `git add -A`, `git add .`, or `git commit -a`.** Run `git status --short`, then `git add` the exact paths you changed.
- **Prose moves verbatim.** When migrating text out of `arch-audit/SKILL.md`, move the sentences unchanged. Do not summarise a judgment paragraph into a bullet, do not shorten, do not "tighten". The only permitted edits are: (a) replacing an em-dash `—` with ` - `, (b) changing a leading bold label when the sentence acquires its own heading, and (c) splitting a sentence at a clause boundary when the source sentence covers several checks and each clause moves to a different file. Everything else is a defect.
- **No em-dash (`—`) in any file this PR writes.** Use ` - `. The single exception is `arch-audit`'s `description:` string in Task 5, which is moved verbatim and whose wording is the skill-discovery surface.
- **Markdown: one paragraph per source line.** Never hard-wrap prose, and never reflow a neighbouring line you did not otherwise change.
- **No environment-specific values** in committed files: no absolute personal paths, AWS/browser profile names, hostnames, emails, bucket names. Use placeholders and say in prose what they resolve to.
- **Docstrings are Google style** (`Args:` / `Returns:` / `Raises:`), no reStructuredText roles or directives, types from the annotations only.
- **Module docstrings stay current.** If you change what a module does, update its docstring in the same commit.
- **Every commit runs `uv run ruff check .` and `uv run ruff format --check .` clean** before it is made. Run `uv run pyright` for any task touching `scripts/` or `tests/`.
- **The domain gate for every task is:** `uv run pytest tests/scripts/ -q` green **and** `uv run python scripts/render_handbook_traceability.py --check` exit 0.
- **Reference the issue in every commit message:** `Refs lidia-tech/lidia-agents#559`. No Claude credits, no co-author trailers naming an assistant.
- **Do not open a PR and do not merge.** The controller handles both.

---

### Task 1: The check-record loader and intra-record validation

**Files:**
- Create: `scripts/audit_checks.py`
- Create: `tests/scripts/test_audit_checks.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces, for Task 2 and the check-authoring tasks:
  - `CHECKS_DIR: Path` - `.agents/skills/audit-core/checks`
  - `LOCALITIES: tuple[str, ...]` - `("local", "global")`
  - `Check` - frozen dataclass with fields `id: str`, `domain: str`, `locality: str`, `title: str`, `handbook: tuple[str, ...]`, `handbook_note: str | None`, `tooling: dict[str, tuple[str, ...]]`, `optin: bool`, `path: Path`
  - `load_checks(checks_dir: Path) -> tuple[dict[str, Check], list[str]]` - id-keyed records plus one message per problem. Never raises on bad input; a file that fails validation is absent from the dict and explained in the list.

- [ ] **Step 1: Write the failing tests**

Create `tests/scripts/test_audit_checks.py`:

```python
"""Tests for scripts/audit_checks.py (lidia-tech/lidia-agents#559)."""

import importlib.util
import sys
from pathlib import Path

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
    _write(tmp_path, "arch/layering.md", GOOD)
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
    _write(tmp_path, "arch/hidden-coupling.md", UNCITED)
    checks, errors = ac.load_checks(tmp_path)
    assert errors == []
    check = checks["arch/hidden-coupling"]
    assert check.handbook == ()
    assert check.handbook_note.startswith("The handbook's decay list")
    assert check.optin is True


def test_missing_frontmatter_is_reported_not_raised(tmp_path):
    _write(tmp_path, "arch/broken.md", "# No frontmatter here\n")
    checks, errors = ac.load_checks(tmp_path)
    assert checks == {}
    assert any("frontmatter" in e for e in errors)


def test_id_must_match_the_file_path(tmp_path):
    _write(tmp_path, "arch/layering.md", GOOD.replace("id: arch/layering", "id: arch/wrong"))
    _, errors = ac.load_checks(tmp_path)
    assert any("does not match its path" in e for e in errors)


def test_domain_must_match_the_directory(tmp_path):
    _write(tmp_path, "deps/layering.md", GOOD)
    _, errors = ac.load_checks(tmp_path)
    assert any("directory" in e for e in errors)


def test_locality_must_be_local_or_global(tmp_path):
    _write(tmp_path, "arch/layering.md", GOOD.replace("locality: local", "locality: sometimes"))
    _, errors = ac.load_checks(tmp_path)
    assert any("locality" in e for e in errors)


def test_empty_handbook_without_a_note_is_rejected(tmp_path):
    text = UNCITED.replace(
        "handbook_note: The handbook's decay list names no equivalent signal.\n", ""
    )
    _write(tmp_path, "arch/hidden-coupling.md", text)
    _, errors = ac.load_checks(tmp_path)
    assert any("handbook_note" in e for e in errors)


def test_a_note_alongside_anchors_is_rejected(tmp_path):
    text = GOOD.replace(
        "tooling:", "handbook_note: why this exceeds the handbook\ntooling:"
    )
    _write(tmp_path, "arch/layering.md", text)
    _, errors = ac.load_checks(tmp_path)
    assert any("handbook_note" in e for e in errors)


def test_unknown_frontmatter_key_is_rejected(tmp_path):
    _write(tmp_path, "arch/layering.md", GOOD.replace("domain: arch", "domain: arch\nsevrity: high"))
    _, errors = ac.load_checks(tmp_path)
    assert any("sevrity" in e for e in errors)


def test_missing_title_is_rejected(tmp_path):
    body_start = GOOD.index("# Layering")
    _write(tmp_path, "arch/layering.md", GOOD[:body_start] + "no heading here\n")
    _, errors = ac.load_checks(tmp_path)
    assert any("title" in e for e in errors)


def test_tooling_must_map_language_to_a_list(tmp_path):
    _write(tmp_path, "arch/layering.md", GOOD.replace("python: [import-linter, tach]", "python: import-linter"))
    _, errors = ac.load_checks(tmp_path)
    assert any("tooling" in e for e in errors)


def test_duplicate_ids_across_files_are_reported(tmp_path):
    _write(tmp_path, "arch/layering.md", GOOD)
    _write(tmp_path, "arch/layering-copy.md", GOOD)
    _, errors = ac.load_checks(tmp_path)
    assert any("duplicate" in e for e in errors)


def test_an_absent_checks_dir_loads_empty_without_error(tmp_path):
    checks, errors = ac.load_checks(tmp_path / "nope")
    assert checks == {}
    assert errors == []


def test_the_real_checks_tree_loads_clean():
    checks, errors = ac.load_checks(ac.CHECKS_DIR)
    assert errors == []
    assert checks == checks  # tautology guard removed in Task 4
```

Delete the final tautological assertion line once Task 4 lands the full tree; Task 4 replaces this test with a real inventory assertion. Keep the test itself - it is the gate that the committed tree parses.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/scripts/test_audit_checks.py -q`
Expected: collection error, `FileNotFoundError` / `ModuleNotFoundError` for `scripts/audit_checks.py`.

- [ ] **Step 3: Write `scripts/audit_checks.py`**

```python
"""Load and validate the audit check records (lidia-tech/lidia-agents#559).

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
        errors.append(f"{where}: id {cid!r} does not match its path (expected {expected_id!r})")

    domain = meta.get("domain")
    expected_domain = rel.parts[0] if len(rel.parts) > 1 else None
    if domain != expected_domain:
        errors.append(
            f"{where}: domain {domain!r} does not match its directory {expected_domain!r}"
        )

    locality = meta.get("locality")
    if locality not in LOCALITIES:
        errors.append(f"{where}: locality must be one of {LOCALITIES}, got {locality!r}")

    handbook = _str_list(meta.get("handbook"))
    if handbook is None:
        errors.append(f"{where}: handbook must be a list of handbook row ids (may be empty)")
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
            errors.append(f"{where}: tooling must be a mapping of language to tool list")
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
        errors.append(f"{where}: body needs an '# ' title - it is the check's display name")
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
    for path in sorted(checks_dir.glob("*/*.md")):
        check, problems = _load_one(path, checks_dir)
        errors.extend(problems)
        if check is None:
            continue
        if check.id in checks:
            errors.append(
                f"{path.relative_to(checks_dir).as_posix()}: duplicate check id {check.id!r} "
                f"(also declared by {checks[check.id].path.name})"
            )
            continue
        checks[check.id] = check
    return checks, errors
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/scripts/test_audit_checks.py -q`
Expected: PASS. `test_the_real_checks_tree_loads_clean` passes trivially against the absent tree.

- [ ] **Step 5: Lint, typecheck, commit**

```bash
uv run ruff check . && uv run ruff format --check . && uv run pyright
git add scripts/audit_checks.py tests/scripts/test_audit_checks.py
git commit -m "feat(lidia-tech/lidia-agents#559): check-record loader and intra-record validation

The audit family's per-check attributes move out of eight SKILL.md files
into one record per check. This is the loader and the half of validation
that a single file can answer on its own; the matrix cross-reference
lands next, in the renderer that already holds the matrix.

Refs lidia-tech/lidia-agents#559"
```

---

### Task 2: Teach the renderer check ids

**Files:**
- Modify: `scripts/render_handbook_traceability.py` (module docstring; `validate` signature and body; `_checks_cell`; `main`)
- Modify: `tests/scripts/test_render_handbook_traceability.py` (add cases; update `validate` call sites)

**Interfaces:**
- Consumes: `audit_checks.load_checks`, `audit_checks.CHECKS_DIR`, `audit_checks.Check` from Task 1.
- Produces, for Tasks 3 and 4: a matrix whose `checks[]` entries may be either a bare string (a check id) or a `{skill, dimension}` mapping, validated and rendered either way.

No real data changes in this task. `docs/audit/handbook-traceability.yaml` and `.md` are untouched; the new code path is exercised by fixtures only.

**Rules this task implements** (numbered for the reviewer):

1. A string entry in `checks[]` is a check id. It must exist in the loaded check tree, else `unknown check id`.
2. A mapping entry is the legacy `{skill, dimension}` pair, validated exactly as today.
3. Every anchor in a check's `handbook` list must resolve to a real `##` handbook heading, reusing `slugify` and `_resolve` so a split-suffixed anchor (`...-a`) resolves to its base heading.
4. Every anchor in a check's `handbook` list must be the id of a matrix row that cites that check. Listing a clause the matrix does not connect is the disagreement the database exists to prevent.
5. A check cited by at least one row must have a non-empty `handbook`; a check no row cites must have an empty one. The list need not be exhaustive - rule 4 makes what it says true, rule 5 makes it non-empty when a grounding exists.

- [ ] **Step 1: Write the failing tests**

Append to `tests/scripts/test_render_handbook_traceability.py`. First add the shared fixture helper near the other helpers:

```python
def _checks_tree(tmp_path, records):
    """Write a checks tree and load it, for validate()'s fourth argument.

    Args:
        tmp_path: pytest tmp dir.
        records: Mapping of `<domain>/<slug>` to a frontmatter dict; the body
            title is derived from the slug.

    Returns:
        The id-keyed `Check` mapping `validate` expects.
    """
    root = tmp_path / "checks"
    for cid, meta in records.items():
        path = root / f"{cid}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        front = yaml.safe_dump({"id": cid, **meta}, sort_keys=False)
        path.write_text(f"---\n{front}---\n\n# {cid.split('/', 1)[1]}\n\nclaim.\n")
    checks, errors = audit_checks.load_checks(root)
    assert errors == []
    return checks
```

and the import beside the existing `rht` bootstrap:

```python
_ac_spec = importlib.util.spec_from_file_location(
    "audit_checks", REPO_ROOT / "scripts" / "audit_checks.py"
)
assert _ac_spec is not None and _ac_spec.loader is not None
audit_checks = importlib.util.module_from_spec(_ac_spec)
sys.modules["audit_checks"] = audit_checks
_ac_spec.loader.exec_module(audit_checks)
```

Then the cases:

```python
_HEADINGS = {"alpha": ["First section"]}


def _row(**over):
    row = {
        "id": "alpha/first-section",
        "section": "First section",
        "class": "static",
        "severity": "minor",
        "checks": ["alpha/one"],
    }
    row.update(over)
    return row


def _one(**over):
    meta = {"domain": "alpha", "locality": "local", "handbook": ["alpha/first-section"]}
    meta.update(over)
    return meta


def test_string_check_entry_resolves_against_the_check_tree(tmp_path):
    checks = _checks_tree(tmp_path, {"alpha/one": _one()})
    assert rht.validate([_row()], _HEADINGS, {}, checks) == []


def test_unknown_check_id_is_reported(tmp_path):
    checks = _checks_tree(tmp_path, {"alpha/one": _one()})
    errors = rht.validate([_row(checks=["alpha/nope"])], _HEADINGS, {}, checks)
    assert any("unknown check id" in e for e in errors)


def test_legacy_skill_dimension_entry_still_validates(tmp_path):
    checks = _checks_tree(tmp_path, {"alpha/one": _one(handbook=[], handbook_note="n/a")})
    rows = [_row(checks=[{"skill": "docs-audit", "dimension": "Coverage"}])]
    assert rht.validate(rows, _HEADINGS, {"docs-audit": ["Coverage"]}, checks) == []
    errors = rht.validate(rows, _HEADINGS, {"docs-audit": ["Other"]}, checks)
    assert any("has no dimension" in e for e in errors)


def test_handbook_anchor_must_resolve_to_a_heading(tmp_path):
    checks = _checks_tree(tmp_path, {"alpha/one": _one(handbook=["alpha/ghost"])})
    errors = rht.validate([_row()], _HEADINGS, {}, checks)
    assert any("does not resolve" in e for e in errors)


def test_handbook_anchor_must_be_a_row_that_cites_the_check(tmp_path):
    # alpha/two is cited, so rule 5 is satisfied; the anchor it names is the
    # base row, which cites alpha/one only, so rule 4 must fire.
    checks = _checks_tree(tmp_path, {"alpha/one": _one(), "alpha/two": _one()})
    rows = [_row(), _row(id="alpha/first-section-b", checks=["alpha/two"])]
    errors = rht.validate(rows, _HEADINGS, {}, checks)
    assert any("no matrix row citing" in e for e in errors)


def test_cited_check_may_not_claim_to_be_ungrounded(tmp_path):
    checks = _checks_tree(tmp_path, {"alpha/one": _one(handbook=[], handbook_note="why")})
    errors = rht.validate([_row()], _HEADINGS, {}, checks)
    assert any("empty handbook" in e for e in errors)


def test_uncited_check_must_not_claim_a_grounding(tmp_path):
    checks = _checks_tree(tmp_path, {"alpha/one": _one(), "alpha/two": _one()})
    errors = rht.validate([_row()], _HEADINGS, {}, checks)
    assert any("alpha/two" in e and "no matrix row" in e for e in errors)


def test_checks_cell_renders_id_and_title(tmp_path):
    checks = _checks_tree(tmp_path, {"alpha/one": _one()})
    cell = rht._checks_cell(_row(), checks)
    assert cell == "`alpha/one` / one"


def test_checks_cell_still_renders_a_legacy_pair(tmp_path):
    cell = rht._checks_cell(
        _row(checks=[{"skill": "docs-audit", "dimension": "Coverage"}]), {}
    )
    assert cell == "`docs-audit` / Coverage"
```

Every existing call to `rht.validate(rows, headings, dims)` in the module gains a fourth argument `{}`. Update them all; a bare three-argument call must not survive.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/scripts/test_render_handbook_traceability.py -q`
Expected: FAIL - `validate() takes 3 positional arguments`, `_checks_cell() takes 1`.

- [ ] **Step 3: Change the renderer**

Add the import beside the existing ones:

```python
from audit_checks import CHECKS_DIR, Check, load_checks
```

Replace `_checks_cell`:

```python
def _checks_cell(row: dict[str, Any], checks: dict[str, Check]) -> str:
    """Render the Mapped-checks cell for one row.

    Handles both entry forms during the migration: a string is a check id,
    resolved to its record's title; a mapping is the legacy
    `{skill, dimension}` pair the not-yet-migrated domains still use.
    """
    entries = row.get("checks") or []
    if not entries:
        return "-"
    cells = []
    for entry in entries:
        if isinstance(entry, str):
            title = checks[entry].title if entry in checks else entry
            cells.append(f"`{entry}` / {_md_escape(title)}")
        else:
            cells.append(f"`{entry['skill']}` / {_md_escape(entry['dimension'])}")
    return "<br>".join(cells)
```

Update its one call site in `render` to `_checks_cell(row, checks)`, and give `render` the `checks` parameter:

```python
def render(rows: list[dict[str, Any]], checks: dict[str, Check]) -> str:
```

with the docstring gaining:

```
        checks: Check records keyed by id, from `load_checks`; used to
            resolve an id reference to its display name.
```

In `validate`, add the parameter and the new rules. The signature becomes:

```python
def validate(
    rows: list[dict[str, Any]],
    headings: dict[str, list[str]],
    dims: dict[str, list[str]],
    checks: dict[str, Check],
) -> list[str]:
```

with the docstring gaining:

```
        checks: Check records keyed by id, from `load_checks`. A `checks[]`
            entry that is a string names one of these; a mapping is the
            legacy `{skill, dimension}` pair, still used by the domains
            that have not migrated.
```

**Rename the row-local list.** `validate` currently binds `checks` twice - once as the row's own entry list, now also as the record mapping parameter. Rename every row-local use to `entries`, in all four places:

```python
        checks_raw = row.get("checks")
        if checks_raw and not isinstance(checks_raw, list):
            errors.append(f"{rid}: checks must be a list")
            entries = []
        else:
            entries = checks_raw or []
```

and, further down, `if cls in ("static", "artifact") and not entries and not gap:` and `if cls in ("process", "informative") and entries:`. A surviving row-local `checks` would silently read the record mapping and pass every row.

Then replace the `for check in checks:` block that follows:

```python
        for entry in entries:
            if isinstance(entry, str):
                if entry not in checks:
                    errors.append(f"{rid}: unknown check id {entry!r}")
                    continue
                cited.setdefault(entry, set()).add(rid)
                continue
            if not isinstance(entry, dict):
                errors.append(f"{rid}: check entries must be a check id or a mapping")
                continue
            skill = entry.get("skill")
            dim = entry.get("dimension")
            if skill not in norm_dims:
                errors.append(f"{rid}: unknown skill {skill!r}")
                continue
            if not isinstance(dim, str):
                errors.append(f"{rid}: check dimension must be a string, got {dim!r}")
                continue
            if " ".join(dim.split()).lower() not in norm_dims[skill]:
                errors.append(f"{rid}: {skill} has no dimension {dim!r}")
```

Declare `cited: dict[str, set[str]] = {}` beside the other accumulators at the top of `validate`, and add this block after the row loop, before the coverage-hole loop:

```python
    # The check records and the matrix are two views of one edge set, so a
    # record may not name a clause the matrix does not connect, nor deny a
    # grounding the matrix gives it. Without this the frontmatter would be
    # unchecked prose again, one field further in.
    for cid, check in sorted(checks.items()):
        rows_citing = cited.get(cid, set())
        if check.handbook and not rows_citing:
            errors.append(
                f"{cid}: cites {len(check.handbook)} handbook anchor(s) but no matrix "
                "row cites this check; add the citation to the matrix or empty the "
                "handbook list and explain why in handbook_note"
            )
        if not check.handbook and rows_citing:
            errors.append(
                f"{cid}: declares an empty handbook, but "
                f"{', '.join(sorted(rows_citing))} cite(s) it; list the grounding "
                "clause and drop handbook_note"
            )
        for anchor in check.handbook:
            part, _, sub = anchor.partition("/")
            part_headings = headings.get(part)
            if part_headings is None:
                errors.append(f"{cid}: handbook anchor names unknown part {part!r}")
                continue
            if _resolve(sub, {slugify(h): h for h in part_headings}) is None:
                errors.append(
                    f"{cid}: handbook anchor {anchor!r} does not resolve to a ## "
                    f"heading in {part}.md"
                )
                continue
            if anchor not in rows_citing:
                errors.append(
                    f"{cid}: handbook anchor {anchor!r} has no matrix row citing this "
                    "check; the record and the matrix disagree"
                )
```

In `main`, load the checks and pass them through:

```python
    checks, errors = load_checks(CHECKS_DIR)
    errors += validate_parts(handbook_part_numbers(HANDBOOK_DIR))
    errors += validate(
        rows, handbook_headings(HANDBOOK_DIR), skill_dimensions(SKILLS_DIR), checks
    )
```

and `rendered = render(rows, checks)`.

Finally update the module docstring: after the paragraph ending "renders the committed Markdown view", add

```
A row's `checks` list carries one entry per check that reaches the clause.
An entry is a check id (`arch/layering`) resolved against the check records
under `.agents/skills/audit-core/checks/` (lidia-tech/lidia-agents#559), or - until the remaining
domains migrate - the legacy `{skill, dimension}` pair parsed out of a
skill's `## N. Dimensions` bullets. The two views of an edge are checked
against each other: a record may not cite a clause no row connects it to,
and a cited record may not declare itself ungrounded.
```

and add the design-doc line to the `Design:` block:

```
        docs/superpowers/specs/2026-07-31-audit-checks-db-design.md (checks database)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run pytest tests/scripts/ -q
uv run python scripts/render_handbook_traceability.py --check
```
Expected: PASS, exit 0. The committed `.md` is unchanged - no real row uses an id yet.

- [ ] **Step 5: Lint, typecheck, commit**

```bash
uv run ruff check . && uv run ruff format --check . && uv run pyright
git add scripts/render_handbook_traceability.py tests/scripts/test_render_handbook_traceability.py
git commit -m "feat(lidia-tech/lidia-agents#559): resolve matrix check references against the check records

A checks[] entry may now be a stable check id as well as the legacy
{skill, dimension} pair, and the two views of an edge are validated
against each other: a record may not cite a clause no row connects it
to, and a cited record may not declare itself ungrounded. No matrix row
uses an id yet; the arch rows migrate next.

Refs lidia-tech/lidia-agents#559"
```

---

### Task 3: The four local `arch` checks, and their nine matrix references

**Files:**
- Create: `.agents/skills/audit-core/checks/arch/layering.md`
- Create: `.agents/skills/audit-core/checks/arch/complexity.md`
- Create: `.agents/skills/audit-core/checks/arch/dead-code.md`
- Create: `.agents/skills/audit-core/checks/arch/size.md`
- Modify: `docs/audit/handbook-traceability.yaml` (9 of the 15 `arch-audit` entries)
- Modify: `docs/audit/handbook-traceability.md` (regenerated, never hand-edited)

**Interfaces:**
- Consumes: the loader and the renderer support from Tasks 1 and 2.
- Produces: the record shape every later domain copies. Four ids: `arch/layering`, `arch/complexity`, `arch/dead-code`, `arch/size`.

**Where each section's prose comes from.** All line references are `.agents/skills/arch-audit/SKILL.md` at this task's base commit. Move the text verbatim under the Global Constraints rule.

| Record | Lead prose | `## Severity` | `## Tooling fallback` | `## Fix` | `## Review lens` |
|---|---|---|---|---|---|
| `layering` | L43 | L73 first sentence; L73's Critical hidden-dependency clause stays with `hidden-coupling` | L57 | L82 | L94 |
| `complexity` | L46 | L74 "a function whose complexity makes it untestable"; L75 "a moderately complex function" | L61 | none in source - omit the section | L98 (No regression) applies family-wide; omit |
| `dead-code` | L47 | L74 "a clearly dead public module"; L75 "a low-confidence dead-code hit" | L62 | L86 | L97 |
| `size` | L48 | L75 "an oversized-but-cohesive file" | L63 | L84 (the split half of the god-module bullet) | L100 (the split half about fragmenting a cohesive unit) |

Two source sentences are compound and split at a clause boundary, which the Global Constraints permit:

- L74 and L75 each enumerate several checks in one sentence. Each check's `## Severity` takes only its own clause, rewritten as a `**Important** - <clause>` line with the clause's words unchanged.
- L84 covers splitting a god-module *and* an oversized file. `size` takes it; `coupling` takes it too in Task 4. Duplicating one sentence across two records is correct - each is read alone.

**Worked example - the exact target shape.** Write `.agents/skills/audit-core/checks/arch/layering.md` as:

```markdown
---
id: arch/layering
domain: arch
locality: local
handbook:
  - codebase-structure/order-the-tiers-by-reuse
  - codebase-structure/point-every-dependency-toward-the-core-and-never-cycle-a
  - codebase-structure/watch-for-structural-decay-beyond-layering
  - codebase-structure/compose-agents-with-typed-hooks-over-a-generic-runner-b
  - codebase-structure/dispatch-on-a-discriminator-not-a-type
  - three-layer-model/hold-the-contracts-that-make-layering-pay-off-a
tooling:
  python: [import-linter, tach, grimp]
  typescript: [dependency-cruiser, madge]
---

# Layering / dependency-rule conformance

Every import that crosses a tier boundary the wrong way (a lower tier importing a higher one), or an edge the documented rules forbid. This is the highest-value axis when the project documents its layers.

## Severity

**Critical** - an import that violates a documented dependency rule (e.g. a lower tier importing a higher one). These break the architecture the team committed to.

## Tooling fallback

**Python** - `import-linter` if a `.importlinter` contract exists, or `tach`. If neither, build the ground-truth edge set yourself - parse each module's `import` / `from ... import` statements (`grimp`, or an AST/`ast`-based walk, or a scoped grep) and check every cross-tier edge against the declared rules. Record the offending `file:line` for each violation.

**TypeScript** - `dependency-cruiser` if the project has a `.dependency-cruiser` config, else read the `tsconfig` path aliases and project references as the declared boundaries, walk each module's import specifiers, and check every cross-boundary edge against them. Record the offending `file:line`.

## Fix

Invert or cut an illegal edge: move the shared type down to a lower tier both sides may import, introduce an interface/protocol the lower tier defines and the higher tier implements, or relocate the misplaced module. Re-run the layering check to green.

## Review lens

Is each flagged edge genuinely a violation of the documented (or confirmed) rules, and does each fix actually remove the edge rather than hide it (e.g. a lazy import that still couples the tiers)?
```

**TypeScript tooling.** Only these, only where the equivalent is real; invent nothing:

| Check | TypeScript |
|---|---|
| `layering` | `dependency-cruiser`; `tsconfig` paths / project references as the declared boundaries |
| `complexity` | ESLint `complexity` and `max-depth` rules; `eslint-plugin-sonarjs` for cognitive complexity |
| `dead-code` | `knip` (unused files, exports and dependencies); `ts-prune` on older setups |
| `size` | line counts per file, same as Python - use `tooling: {any: [cloc, tokei]}` and one paragraph, not two |

**Matrix rewiring, this task.** Replace exactly these nine entries; leave every other `arch-audit` entry alone.

| Row id | `- skill: arch-audit` / `dimension:` | becomes |
|---|---|---|
| `codebase-structure/order-the-tiers-by-reuse` | Layering / dependency-rule conformance | `- arch/layering` |
| `codebase-structure/point-every-dependency-toward-the-core-and-never-cycle-a` | Layering / dependency-rule conformance | `- arch/layering` |
| `codebase-structure/watch-for-structural-decay-beyond-layering` | Layering / dependency-rule conformance | `- arch/layering` |
| `codebase-structure/watch-for-structural-decay-beyond-layering` | Complexity | `- arch/complexity` |
| `codebase-structure/watch-for-structural-decay-beyond-layering` | Dead code | `- arch/dead-code` |
| `codebase-structure/watch-for-structural-decay-beyond-layering` | File / module size | `- arch/size` |
| `codebase-structure/compose-agents-with-typed-hooks-over-a-generic-runner-b` | Layering / dependency-rule conformance | `- arch/layering` |
| `codebase-structure/dispatch-on-a-discriminator-not-a-type` | Layering / dependency-rule conformance | `- arch/layering` |
| `three-layer-model/hold-the-contracts-that-make-layering-pay-off-a` | Layering / dependency-rule conformance | `- arch/layering` |

Each becomes one list item that is a plain string. A row keeps its remaining legacy mappings in the same list:

```yaml
  checks:
  - arch/layering
  - skill: arch-audit
    dimension: Cycles
```

- [ ] **Step 1: Write the four records**

Write `layering.md` exactly as given above. Write `complexity.md`, `dead-code.md` and `size.md` from the source-mapping table, with these frontmatter blocks:

```yaml
id: arch/complexity
domain: arch
locality: local
handbook:
  - codebase-structure/watch-for-structural-decay-beyond-layering
tooling:
  python: [ruff, radon, xenon]
  typescript: [eslint, eslint-plugin-sonarjs]
```

```yaml
id: arch/dead-code
domain: arch
locality: local
handbook:
  - codebase-structure/watch-for-structural-decay-beyond-layering
tooling:
  python: [vulture]
  typescript: [knip, ts-prune]
```

```yaml
id: arch/size
domain: arch
locality: local
handbook:
  - codebase-structure/watch-for-structural-decay-beyond-layering
tooling:
  any: [cloc, tokei]
```

- [ ] **Step 2: Verify the records load before touching the matrix**

Run: `uv run pytest tests/scripts/test_audit_checks.py -q`
Expected: PASS - in particular `test_the_real_checks_tree_loads_clean`, which now loads four real records.

- [ ] **Step 3: Confirm the matrix gate fails for the right reason**

Run: `uv run python scripts/render_handbook_traceability.py --check`
Expected: exit 1, with four messages of the form `arch/layering: cites 6 handbook anchor(s) but no matrix row cites this check`. This is rule 5 firing because the rewiring has not happened yet - it is the failing test for Step 4.

- [ ] **Step 4: Rewire the nine references and regenerate**

Apply the nine replacements from the table, then:

```bash
uv run python scripts/render_handbook_traceability.py
```
Expected: `wrote docs/audit/handbook-traceability.md (125 rows)`, exit 0.

- [ ] **Step 5: Verify the rendered cells and the word-count gate**

```bash
grep -c 'arch/layering' docs/audit/handbook-traceability.md
uv run python scripts/render_handbook_traceability.py --check
uv run pytest tests/scripts/ -q
wc -w .agents/skills/audit-core/checks/arch/*.md
```
Expected: 6 occurrences of `arch/layering` in the rendered md; exit 0; tests pass. Record the word counts - Task 6 diffs them against the source sections.

- [ ] **Step 6: Commit**

```bash
git add .agents/skills/audit-core/checks/arch/layering.md .agents/skills/audit-core/checks/arch/complexity.md .agents/skills/audit-core/checks/arch/dead-code.md .agents/skills/audit-core/checks/arch/size.md docs/audit/handbook-traceability.yaml docs/audit/handbook-traceability.md
git commit -m "feat(lidia-tech/lidia-agents#559): migrate the four local arch checks to check records

Layering, complexity, dead code and file size become records under
audit-core/checks/arch/, and the nine matrix references that cited them
as arch-audit dimensions now cite stable ids. Prose moved verbatim; the
TypeScript half of each tooling fallback is new (#5).

Refs lidia-tech/lidia-agents#559, #7, #5"
```

---

### Task 4: The six global `arch` checks, and their six matrix references

**Files:**
- Create: `.agents/skills/audit-core/checks/arch/cycles.md`
- Create: `.agents/skills/audit-core/checks/arch/coupling.md`
- Create: `.agents/skills/audit-core/checks/arch/over-decomposition.md`
- Create: `.agents/skills/audit-core/checks/arch/over-abstraction.md`
- Create: `.agents/skills/audit-core/checks/arch/hidden-coupling.md`
- Create: `.agents/skills/audit-core/checks/arch/martin-metrics.md`
- Modify: `docs/audit/handbook-traceability.yaml` (the last 6 `arch-audit` entries, plus two `note:` fields)
- Modify: `docs/audit/handbook-traceability.md` (regenerated)
- Modify: `tests/scripts/test_audit_checks.py` (real-tree inventory assertion)

**Interfaces:**
- Consumes: the record shape from Task 3.
- Produces: the complete `arch` inventory - ten ids, no `arch-audit` mapping left anywhere in the matrix.

**Source mapping.** Same rule and same base file as Task 3.

| Record | Lead prose | `## Severity` | `## Tooling fallback` | `## Fix` | `## Review lens` |
|---|---|---|---|---|---|
| `cycles` | L44 | L73 "an import cycle across package boundaries"; L74 "a cycle within a package" | L58 | L83 | L96 (Graph correctness) |
| `coupling` | L45, the "Too **coarse**" half | L74 "a god-module with runaway coupling that blocks safe change"; L75 "a grab-bag `utils` that should be split" | L59 | L84 | L96 and the split half of L100 |
| `over-decomposition` | L45, the "Too **fine**" half | L74 the shotgun-surgery clause; L75 "a handful of over-decomposed pass-through modules that should be merged" | L60 | L85 | the merge half of L100 |
| `over-abstraction` | L49 | L73 the over-abstraction clause (both halves - the contributor-guide exception belongs here); L74 the registry/indirection clause; L75 the single-implementer clause | L64 | L88 | L99 |
| `hidden-coupling` | L50 | L73 the hidden-dependency clause; L74 the shared-mutable-state clause | L65 | L87 | L101 |
| `martin-metrics` | L107 | none in source - omit | L107's formulae | none - omit | none - omit |

`martin-metrics` carries `optin: true` and keeps the whole of L107 as its lead prose plus a `## Tooling fallback` holding the `Ca`/`Ce`/`I`/`A`/`D` definitions.

**Frontmatter.**

```yaml
id: arch/cycles
domain: arch
locality: global
handbook:
  - codebase-structure/order-the-tiers-by-reuse
  - codebase-structure/point-every-dependency-toward-the-core-and-never-cycle-a
  - codebase-structure/watch-for-structural-decay-beyond-layering
tooling:
  python: [import-linter, pydeps, grimp]
  typescript: [madge, dependency-cruiser]
```

```yaml
id: arch/coupling
domain: arch
locality: global
handbook:
  - codebase-structure/watch-for-structural-decay-beyond-layering
tooling:
  python: [grimp, pydeps]
  typescript: [dependency-cruiser, madge]
```

```yaml
id: arch/over-decomposition
domain: arch
locality: global
handbook: []
handbook_note: >-
  The handbook's structural-decay list names hub modules and grab-bag utils - coupling that is too coarse - and no equivalent signal for the opposite fault, so no clause grounds this check. Mapping it to that clause would be a near miss the matrix's own rule forbids: the section would pass a codebase that is fragmented rather than tangled.
tooling:
  python: [grimp]
  typescript: [madge, dependency-cruiser]
```

```yaml
id: arch/over-abstraction
domain: arch
locality: global
handbook:
  - implementation-disciplines/coding-hygiene-rules-that-surface-at-review-b
  - codebase-structure/why-the-rule-matters-a
tooling:
  python: [grimp, ruff]
  typescript: [knip, ts-morph]
```

```yaml
id: arch/hidden-coupling
domain: arch
locality: global
handbook: []
handbook_note: >-
  Deliberately beyond the handbook: the structural-decay section lists five signals an import graph can see, and this check exists for the coupling that never reaches the graph at all. The matrix records the addition in the note on codebase-structure/watch-for-structural-decay-beyond-layering.
tooling:
  python: [grimp]
  typescript: [eslint, knip]
```

```yaml
id: arch/martin-metrics
domain: arch
locality: global
optin: true
handbook: []
handbook_note: >-
  A quantitative restatement of the god-module and over-abstraction axes rather than a clause of its own; the handbook states neither the metric nor a threshold for it.
tooling:
  python: [grimp]
```

`martin-metrics` gets no TypeScript entry: no standard TS tool computes package instability and abstractness, and inventing one would be worse than the gap.

**Matrix rewiring, this task.**

| Row id | dimension | becomes |
|---|---|---|
| `codebase-structure/order-the-tiers-by-reuse` | Cycles | `- arch/cycles` |
| `codebase-structure/point-every-dependency-toward-the-core-and-never-cycle-a` | Cycles | `- arch/cycles` |
| `codebase-structure/watch-for-structural-decay-beyond-layering` | Cycles | `- arch/cycles` |
| `codebase-structure/watch-for-structural-decay-beyond-layering` | Coupling & cohesion | `- arch/coupling` |
| `implementation-disciplines/coding-hygiene-rules-that-surface-at-review-b` | Over-abstraction / speculative generality | `- arch/over-abstraction` |
| `codebase-structure/why-the-rule-matters-a` | Over-abstraction / speculative generality | `- arch/over-abstraction` |

`Coupling & cohesion` maps to `arch/coupling` **only**. The handbook clause names hub modules and grab-bag utils and no ravioli signal, so citing `arch/over-decomposition` there would assert a grounding the section does not give.

**Two `note:` fields name dimensions that no longer exist as such.** Update the prose, changing nothing else in those rows:

- `codebase-structure/watch-for-structural-decay-beyond-layering`, `note:` - "arch-audit declares a dimension for every signal named here, and adds Hidden coupling for the edges an import graph misses" becomes "arch declares a check for every signal named here, and adds `arch/hidden-coupling` for the edges an import graph misses and `arch/over-decomposition` for the opposite fault, neither of which this section names".
- `codebase-structure/compose-agents-with-typed-hooks-over-a-generic-runner-b`, `gap.note:` - "its Coupling & cohesion dimension is the right lens for" becomes "`arch/over-decomposition` is the right lens for", and "the fix is to extend the over-decomposition axis to that second graph" becomes "the fix is to extend that check to the second graph". The two other `note:` fields that mention "Over-abstraction dimension" (`codebase-structure/why-the-rule-matters-a` and `three-layer-model/hold-the-contracts-that-make-layering-pay-off-a`) keep reading correctly with the display name unchanged - leave them.

- [ ] **Step 1: Write the six records**

Follow the source mapping and frontmatter above.

- [ ] **Step 2: Confirm the gate fails for the right reason**

Run: `uv run python scripts/render_handbook_traceability.py --check`
Expected: exit 1, with `arch/cycles`, `arch/coupling` and `arch/over-abstraction` each reporting `cites N handbook anchor(s) but no matrix row cites this check`. The three ungrounded records (`over-decomposition`, `hidden-coupling`, `martin-metrics`) must produce **no** message - if one does, its `handbook_note` or empty list is wrong.

- [ ] **Step 3: Rewire the six references, update the two notes, regenerate**

```bash
grep -c 'skill: arch-audit' docs/audit/handbook-traceability.yaml
uv run python scripts/render_handbook_traceability.py
```
Expected: the grep prints `0` after the edit; the render writes 125 rows and exits 0.

- [ ] **Step 4: Pin the inventory in the test suite**

In `tests/scripts/test_audit_checks.py`, replace `test_the_real_checks_tree_loads_clean` with:

```python
def test_the_real_checks_tree_loads_clean():
    checks, errors = ac.load_checks(ac.CHECKS_DIR)
    assert errors == []
    assert sorted(checks) == [
        "arch/complexity",
        "arch/coupling",
        "arch/cycles",
        "arch/dead-code",
        "arch/hidden-coupling",
        "arch/layering",
        "arch/martin-metrics",
        "arch/over-abstraction",
        "arch/over-decomposition",
        "arch/size",
    ]
    assert {c.locality for c in checks.values()} == {"local", "global"}
    assert [c.id for c in checks.values() if c.optin] == ["arch/martin-metrics"]
```

- [ ] **Step 5: Run the full gate**

```bash
uv run pytest tests/scripts/ -q
uv run python scripts/render_handbook_traceability.py --check
uv run ruff check . && uv run ruff format --check . && uv run pyright
```
Expected: all green, exit 0.

- [ ] **Step 6: Commit**

```bash
git add .agents/skills/audit-core/checks/arch/ docs/audit/handbook-traceability.yaml docs/audit/handbook-traceability.md tests/scripts/test_audit_checks.py
git commit -m "feat(lidia-tech/lidia-agents#559): migrate the six global arch checks; no arch-audit pair left

Completes the arch inventory at ten records. Splitting Coupling &
cohesion into coupling and over-decomposition is what makes the handbook
grounding honest: the decay section names hubs and grab-bag utils and no
ravioli signal, so over-decomposition carries an empty handbook and a
note instead of a citation the clause does not support.

Refs lidia-tech/lidia-agents#559, #7, #5"
```

---

### Task 5: Reduce `arch-audit` to a domain header; teach `audit-core` the record

**Files:**
- Modify: `.agents/skills/arch-audit/SKILL.md` (3,335 words to roughly 250)
- Modify: `.agents/skills/audit-core/SKILL.md` (add a "Check records" section; mark the seven-slot section transitional)

**Interfaces:**
- Consumes: the complete `arch` inventory from Task 4.
- Produces: the header shape the other seven domains copy in PR 2.

**What survives in `arch-audit/SKILL.md`:** the `description` verbatim (it is the discovery surface and nothing about it changed), §1's declared-architecture-first rule and its build-the-graph-once instruction, the status scale, the two opt-in *deliverables*, and the load instruction. Everything else is now in the records.

Write the whole file as:

```markdown
---
name: arch-audit
description: "Audit a Python project's structure: layering / dependency-rule conformance (no illegal cross-tier imports, no cycles), module cohesion and coupling (god-modules and the opposite — over-decomposition / ravioli code), per-module complexity, dead code, oversized files, over-abstraction / speculative generality (single-implementer interfaces, one-caller wrappers, one-case registries, back-compat shims), and hidden coupling that bypasses the import graph (shared global state, service locators, import-time side effects). Use when a codebase has grown organically and the boundaries have blurred, before a refactor, when import cycles or god-modules are suspected, when the structure feels heavier than the problem, or when the user asks to audit architecture / structure / layering. Works on any Python project. Runs on the audit-core engine."
---

# Architecture Audit (structure, layering, coupling)

A domain specialization of **[audit-core](../audit-core/SKILL.md)** - read that first; it owns the loop and the cross-cutting rules. The checks are records under [`audit-core/checks/arch/`](../audit-core/checks/arch/); load the ones your slice needs, not the directory.

**Announce:** "I'm using the arch-audit skill (on the audit-core engine) to audit the project structure."

**Subject:** the package tree (the importable source under `src/`, the top-level package, or wherever the project keeps its code) and its import graph.

**Establish the declared architecture first**, because it is the spec every layering finding is judged against. Read the contributor guide (CLAUDE.md / AGENTS.md / CONTRIBUTING) for a stated tier/layer structure and dependency rules ("A may import B, never the reverse; no cycles"). If it states them, they are the rubric. If no rules are documented, **infer** the intended layers from the directory structure and confirm the inferred rules with the user before flagging violations - don't invent an architecture the team never agreed to.

**Build the graph once, first.** Produce the ground-truth artifact every downstream agent consumes - the import edge set plus per-module symbol/LOC counts - so agents read it rather than each re-parsing the tree and rebuilding a (possibly inconsistent) graph.

**Fan out by each check's `locality`.** One read-only agent per top-level package/tier for the `local` checks, each mapping its slice's outgoing imports and internal shape; one agent per `global` check over the whole graph artifact, because a per-tier agent sees only its slice's edges and *cannot* compute a whole-graph property. Do **not** fan a cheap local check out to its own agent - that over-fans the work and duplicates the graph build.

**Status scale:** ok / warn / violation (for a documented rule: conforms / borderline / violates). Suppressions - an intentionally allowed edge, a framework hook a dead-code tool can't see - must be explicit and recorded with a reason, never silently dropped.

**Fixes touch code**, so the domain gate is "imports resolve, the type checker passes, **and** the test suite passes" - run the normal install + lint/typecheck/test CI, and the code-review gate. The highest-leverage fix in this domain is a layering contract (`import-linter` / `tach`) wired into CI so the violation can't silently recur.

**Opt-in deliverables** (ask the user, or take from an argument; default off): a layering-contract bootstrap that encodes the confirmed rules as an `import-linter` / `tach` config, and a full complexity/coupling metric report over the whole tree with a dependency-graph render. The opt-in *check* - package stability metrics - is `arch/martin-metrics`, loaded like any other.
```

The em-dashes inside the `description` string stay: it is moved verbatim and re-wording the discovery surface is out of scope for this PR.

**`audit-core/SKILL.md`:** replace the "Authoring a new auditing skill" section's opening with the record model, and keep the seven-slot list below it marked as what the unmigrated domains still use.

```markdown
## Authoring a new auditing skill

A `<domain>-audit` skill is thin: it states the lens and defers the loop above to this engine.

**Checks are records, not prose.** Each check the domain runs is one file under `checks/<domain>/`, with its machine-checkable attributes in YAML frontmatter (`id`, `domain`, `locality`, `handbook`, `tooling`, `optin`) and its judgment prose in the body: the claim as lead prose, then `## Severity`, `## Tooling fallback`, `## Fix`, `## Review lens`, omitting any section the check has nothing to say in. An executing agent loads the subset its slice needs - `locality: local` checks per partition, one `global` check per agent - so no agent pays for the rest of the domain. `handbook` lists the handbook clauses grounding the check and is validated against the traceability matrix in both directions; a check that deliberately exceeds the handbook carries an empty list and a `handbook_note` saying why. See `checks/arch/` for the reference set.

**The skill file holds only what does not vary by check:** the subject and how to slice it, the ground-truth artifact to build once, the status scale, whether fixes touch code, and any opt-in *deliverables* (a generated config, a rendered report - things that produce an artifact rather than findings-matrix rows). Target roughly 250 words plus the `description`.

**Domains not yet migrated** (everything but `arch`, until lidia-tech/lidia-agents#559 PR 2) still carry their checks inline as seven numbered slots: 1. Subject & scope, 2. Dimensions, 3. Evidence sources & tooling, 4. Status scale + severity rubric, 5. Fix patterns, 6. Review dimensions, 7. Opt-in sub-audits. Read them as written; do not convert one on the side.
```

- [ ] **Step 1: Rewrite both files**

- [ ] **Step 2: Verify the gate and the word count**

```bash
wc -w .agents/skills/arch-audit/SKILL.md .agents/skills/audit-core/SKILL.md
uv run python scripts/render_handbook_traceability.py --check
uv run pytest tests/scripts/ -q
```
Expected: `arch-audit/SKILL.md` between 200 and 320 words; exit 0; tests pass. `skill_dimensions()` now returns no `arch-audit` key, which is fine because no legacy `arch-audit` pair remains in the matrix. If the render reports `unknown skill 'arch-audit'`, a Task 3 or Task 4 rewiring was missed - find it with `grep -n "skill: arch-audit" docs/audit/handbook-traceability.yaml`.

- [ ] **Step 3: Verify the docs site still builds**

```bash
uv run mkdocs build --strict
uv run python scripts/check_site_links.py site
```
Expected: both clean. `.agents/skills/` is outside the site, so the only site-visible change is the regenerated matrix.

- [ ] **Step 4: Commit**

```bash
git add .agents/skills/arch-audit/SKILL.md .agents/skills/audit-core/SKILL.md
git commit -m "refactor(lidia-tech/lidia-agents#559): reduce arch-audit to a domain header

Prompt change, so the why: every /audit sweep dispatches one subagent per
domain and each reads its whole SKILL.md, so arch-audit's 3,335 words
were a per-agent tax paid before any evidence was gathered - and 71% of
them were per-check attributes scattered across four sections. What
stays is what does not vary by check: the subject, the
declared-architecture-first rule, the build-the-graph-once artifact, the
status scale, and the opt-in deliverables. audit-core gains the record
model and marks the seven-slot shape as what the unmigrated domains
still use.

Refs lidia-tech/lidia-agents#559"
```

---

### Task 6: Pilot verification against the lidia-tech/lidia-agents#508 baseline

**Files:**
- Create: `test-reports/559-arch-pilot/findings.md` (gitignored working artifact, not committed)
- Modify: none

**Interfaces:**
- Consumes: everything above.
- Produces: the evidence the PR body cites, and the word-count table spec decision 5 requires at review.

This is the spec's application test: a schema that survives `arch` survives the other seven domains, and one pilot run costs an eighth of discovering the schema is wrong after 68 records.

**Baseline.** [lidia-tech/lidia-agents#512](https://github.com/lidia-tech/lidia-agents/issues/512) records what `arch-audit` found on this repo on 2026-07-22, verified with `grimp`, `radon`, `vulture` and `ruff C901`:

- 3 illegal cross-tier import edges: `core.references` -> `capabilities.citing.markers`, `core.hooks.url_masking` -> `capabilities.citing.markers`, `eval.convert` -> `agents.legal_search.references_section`
- 2 tier-level import cycles: `capabilities <-> core`, `agents <-> eval`
- 2 F-grade functions: `core.ui.gradio.interactive_chat.chat_stream` (CC 60), `eval.report.charts.make_radar` (CC 50)
- complexity ungated in CI (no `C901` threshold in `pyproject.toml`)
- 9 files over 800 lines; 6 high-confidence `vulture` hits; `document_model.schema` a 29-importer coupling hub
- roll-up: 0 Critical, 7 Important, ~6 Minor

**The gate is not identical output.** The tree has moved since 2026-07-22. Each baseline finding must end in one of two states, and the report must say which: **reproduced** (the check found it again) or **fixed in the tree** (verified absent at the cited `file:line`, with the commit or issue that closed it). A baseline finding that is neither - the tree still has it and the migrated check no longer sees it - is a **migration defect** and blocks the PR.

- [ ] **Step 1: Run the migrated audit, report-only**

Dispatch `arch-audit` in report-only mode on this repo. Pin every subagent to the worktree root from the Global Constraints and require each to confirm its own `git rev-parse --show-toplevel` before reading. Save the findings matrix to `test-reports/559-arch-pilot/findings.md`.

- [ ] **Step 2: Diff against the baseline**

Produce a table with a row per baseline finding: finding, baseline severity, this run's status (reproduced / fixed in tree / **missed**), and the evidence. Any `missed` row names the record that should have caught it.

- [ ] **Step 3: Measure the prose migration**

```bash
wc -w .agents/skills/audit-core/checks/arch/*.md .agents/skills/arch-audit/SKILL.md
```

Compare the total against the source: `arch-audit/SKILL.md` was 3,335 words, of which the spec measured 2,379 as per-check content. Expect the ten records plus the header to land at or above that, since each record adds a TypeScript paragraph. **A record materially shorter than its source sections is the failure spec decision 5 names** - shrinkage needs a justification in the PR body, per finding, or the prose goes back.

- [ ] **Step 4: Record the per-agent budget**

State in the PR body what an executing agent now reads, against the 3,335-word floor:

| agent | before | after |
|---|---|---|
| per-package local agent | 3,335 + audit-core | header + `layering`, `complexity`, `dead-code`, `size` |
| per-global-check agent | 3,335 + audit-core | header + 1 record |

Measure both with `wc -w`; do not estimate.

- [ ] **Step 5: No commit**

Task 6 produces evidence, not code. `test-reports/` is gitignored. If Step 2 finds a `missed` row, stop and report it - that is a BLOCKED status for the controller, not something to paper over in the PR body.

## Self-review notes

Checked against the spec section by section:

- Decisions 1, 2, 3, 5, 6 are implemented by Tasks 3, 4 and 5. Decision 4 (check vs deliverable) decides the ten-record inventory and is recorded in Task 5's opt-in paragraph.
- "What this also fixes": the run-on severity rubric is split in Tasks 3 and 4 (L73-L75 fan out to eight records). Un-citable coverage does not arise for `arch` - all eight dimensions were already parseable - so it lands in PR 2 with `prompt-audit` Tier B and `docs-audit` §7.
- Testing: `audit_checks.py` and the renderer changes ship with unit tests in the same task, via the `importlib.util.spec_from_file_location` pattern and the existing `tests/scripts/conftest.py`. Task 6 is the application test.
- Files table: every PR 1 row is covered except the two moved out with a reason at the top of this plan.
