# Handbook Traceability Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the handbook-to-audit-skills traceability matrix (#543): a hand-maintained YAML source of truth, a renderer/validator script, its unit tests, and the full clause-by-clause content walk of all 12 handbook parts.

**Architecture:** A flat YAML list at `docs/audit/handbook-traceability.yaml` (one entry per adaptive-section row) is validated and rendered to `docs/audit/handbook-traceability.md` by `scripts/render_handbook_traceability.py`. The script's `--check` mode doubles as the CI staleness gate via a pytest test. Content is added part by part, each addition validated by the renderer.

**Tech Stack:** Python 3.11+, `pyyaml` (already a main dependency), pytest with the `importlib.util.spec_from_file_location` pattern for `scripts/` tests.

**Spec:** `docs/superpowers/specs/2026-07-29-handbook-traceability-matrix-design.md` — the schema, classes, validation rules, and rendered layout are normative there; this plan repeats the exact values where a task needs them.

## Global Constraints

- Gates: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run pytest tests/` must pass at the end of every task.
- Markdown: one paragraph per source line, never hard-wrap prose. Do not edit anything under `docs/engineering/` (read-only input).
- Commit messages reference the issue: `Refs #543` (or `docs(#543): ...` / `feat(#543): ...` style used in this repo).
- The four classes are exactly `static`, `artifact`, `process`, `informative`. Gap recommendations are exactly `extend-skill`, `new-domain`, `report-only`.
- Row IDs are `<part-stem>/<github-style-anchor>` with an optional single-letter `-a`/`-b` suffix for splits. A part with no `##` sections gets one whole-part row with id `<part>/<part>`.
- `checks[].dimension` must match the bolded lead phrase of a bullet under the skill's `## 2. Dimensions (findings-matrix columns)` heading, verbatim (whitespace-normalized, case-insensitive).
- Never pass lines starting with `#` to the Bash tool (repo-wide subagent rule).

## Handbook part order (the README spine — used by the renderer and the content tasks)

`README`, `lifecycle`, `implementation-disciplines`, `codebase-structure`, `three-layer-model`, `agent-harness`, `observability`, `evaluation`, `documentation`, `security-supply-chain`, `troubleshooting`, `coda`.

Section counts (2026-07-29): README 5, lifecycle 9, implementation-disciplines 7, codebase-structure 9, three-layer-model 8, agent-harness 9, observability 8, evaluation 13, documentation 8, security-supply-chain 9, troubleshooting 4, coda 0 (whole-part row). Total 89 `##` sections.

---

### Task 1: Renderer pure helpers (slugify, heading extraction, dimension lookup)

**Files:**
- Create: `scripts/render_handbook_traceability.py`
- Create: `tests/scripts/test_render_handbook_traceability.py`

**Interfaces:**
- Produces: `slugify(heading: str) -> str`, `handbook_headings(handbook_dir: Path) -> dict[str, list[str]]`, `skill_dimensions(skills_dir: Path) -> dict[str, list[str]]`, plus module constants `PART_ORDER`, `CLASSES`, `RECOMMENDATIONS`, and path globals `REPO_ROOT`, `HANDBOOK_DIR`, `SKILLS_DIR`, `YAML_PATH`, `MD_PATH`. Task 2 consumes all of these.

- [ ] **Step 1: Write the failing tests**

Create `tests/scripts/test_render_handbook_traceability.py`. Load the script with the established pattern (register in `sys.modules` before `exec_module`, as `tests/scripts/test_render_handbook_artifact.py` does):

```python
"""Tests for scripts/render_handbook_traceability.py (#543)."""

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = REPO_ROOT / "scripts" / "render_handbook_traceability.py"

_spec = importlib.util.spec_from_file_location("rht", _SCRIPT)
assert _spec is not None and _spec.loader is not None
rht = importlib.util.module_from_spec(_spec)
sys.modules["rht"] = rht
_spec.loader.exec_module(rht)


def test_slugify_matches_github_anchor_rules():
    assert rht.slugify("The staged screening funnel") == "the-staged-screening-funnel"
    assert rht.slugify("Dimensions (findings-matrix columns)") == "dimensions-findings-matrix-columns"
    assert rht.slugify("Aliases, profiles & CLIs") == "aliases-profiles--clis"
    assert rht.slugify("`code` in a heading") == "code-in-a-heading"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_handbook_headings_skips_fences_and_deeper_levels(tmp_path):
    _write(
        tmp_path / "alpha.md",
        "# Alpha\n\n## First section\n\ntext\n\n### Not this one\n\n```\n## not a heading\n```\n\n## Second section\n",
    )
    _write(tmp_path / "coda.md", "# Coda\n\nno sections here\n")
    headings = rht.handbook_headings(tmp_path)
    assert headings == {"alpha": ["First section", "Second section"], "coda": []}


def test_skill_dimensions_reads_bolded_bullets_until_next_heading(tmp_path):
    _write(
        tmp_path / "demo-audit" / "SKILL.md",
        "---\nname: demo-audit\n---\n\n## 1. Subject\n\ntext\n\n## 2. Dimensions (findings-matrix columns)\n\n"
        "- **Injection** — command, SQL.\n- **Secrets & credential handling** — keys in code.\n\n"
        "## 3. Evidence\n\n- **Not a dimension** — different section.\n",
    )
    _write(tmp_path / "helper" / "SKILL.md", "---\nname: helper\n---\n\nNo dimensions heading.\n")
    dims = rht.skill_dimensions(tmp_path)
    assert dims == {"demo-audit": ["Injection", "Secrets & credential handling"]}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/scripts/test_render_handbook_traceability.py -v`
Expected: FAIL (file `scripts/render_handbook_traceability.py` does not exist).

- [ ] **Step 3: Write the module with the helpers**

Create `scripts/render_handbook_traceability.py`:

```python
"""Render and verify the handbook traceability matrix (#543).

``docs/audit/handbook-traceability.yaml`` is the hand-maintained source of
truth mapping every ``##`` section of the engineering handbook
(``docs/engineering/``) onto the ``*-audit`` skill family
(``.agents/skills/``). This script validates that mapping against the real
handbook headings and skill dimensions, and renders the committed Markdown
view ``docs/audit/handbook-traceability.md``.

Usage:
    uv run python scripts/render_handbook_traceability.py          # validate + write the md
    uv run python scripts/render_handbook_traceability.py --check  # validate; fail if the md is stale

Exit code 0 on success; 1 with one message per problem on validation
failure or staleness. The pytest gate in ``tests/scripts/`` runs ``--check``
so CI guards staleness with no workflow change.

Design: docs/superpowers/specs/2026-07-29-handbook-traceability-matrix-design.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
HANDBOOK_DIR = REPO_ROOT / "docs" / "engineering"
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
YAML_PATH = REPO_ROOT / "docs" / "audit" / "handbook-traceability.yaml"
MD_PATH = REPO_ROOT / "docs" / "audit" / "handbook-traceability.md"

PART_ORDER = [
    "README",
    "lifecycle",
    "implementation-disciplines",
    "codebase-structure",
    "three-layer-model",
    "agent-harness",
    "observability",
    "evaluation",
    "documentation",
    "security-supply-chain",
    "troubleshooting",
    "coda",
]
PART_TITLES = {
    "README": "The README spine",
    "lifecycle": "Part 1: Development lifecycle",
    "implementation-disciplines": "Part 2: Implementation disciplines",
    "codebase-structure": "Part 3: Codebase structure",
    "three-layer-model": "Part 4: The three-layer document model",
    "agent-harness": "Part 5: The extended agent harness",
    "observability": "Part 6: Observability",
    "evaluation": "Part 7: Evaluation",
    "documentation": "Part 8: Documentation & knowledge capture",
    "security-supply-chain": "Part 9: Security, dependencies & supply chain",
    "troubleshooting": "Troubleshooting guide",
    "coda": "Coda",
}

CLASSES = ("static", "artifact", "process", "informative")
RECOMMENDATIONS = ("extend-skill", "new-domain", "report-only")

_HEADING_RE = re.compile(r"^## (.+?)\s*$")
_FENCE_RE = re.compile(r"^(```|~~~)")
_DIMENSIONS_HEADING_RE = re.compile(r"^## \d+\. Dimensions\b")
_DIM_BULLET_RE = re.compile(r"^- \*\*(.+?)\*\*")
_SPLIT_SUFFIX_RE = re.compile(r"-([a-z])$")


def slugify(heading: str) -> str:
    """GitHub-style anchor: lowercase, keep ``[a-z0-9 _-]``, spaces to hyphens."""
    text = heading.strip().lower().replace("`", "")
    text = re.sub(r"[^a-z0-9 _-]", "", text)
    return text.replace(" ", "-")


def handbook_headings(handbook_dir: Path) -> dict[str, list[str]]:
    """Map each handbook part stem to its ordered ``##`` heading texts.

    Only level-2 headings count (the row unit per the design spec); fenced
    code blocks are skipped so a ``##`` inside an example is not a section.
    """
    parts: dict[str, list[str]] = {}
    for md in sorted(handbook_dir.glob("*.md")):
        headings: list[str] = []
        in_fence = False
        for line in md.read_text().splitlines():
            if _FENCE_RE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            m = _HEADING_RE.match(line)
            if m:
                headings.append(m.group(1))
        parts[md.stem] = headings
    return parts


def skill_dimensions(skills_dir: Path) -> dict[str, list[str]]:
    """Map each skill directory name to the bolded lead phrases of its Dimensions bullets.

    A skill without a numbered ``## N. Dimensions`` heading (audit-core, the
    audit front door, non-audit skills) is simply absent from the result.
    """
    dims: dict[str, list[str]] = {}
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        names: list[str] = []
        in_section = False
        for line in skill_md.read_text().splitlines():
            if _DIMENSIONS_HEADING_RE.match(line):
                in_section = True
                continue
            if in_section and line.startswith("## "):
                break
            if in_section:
                m = _DIM_BULLET_RE.match(line)
                if m:
                    names.append(m.group(1))
        if names:
            dims[skill_md.parent.name] = names
    return dims
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/scripts/test_render_handbook_traceability.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Run the gates and commit**

Run: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest tests/`
Then:

```bash
git add scripts/render_handbook_traceability.py tests/scripts/test_render_handbook_traceability.py
git commit -m "feat(#543): traceability renderer helpers (slugify, headings, dimensions)"
```

---

### Task 2: Validation, rendering, and the CLI

**Files:**
- Modify: `scripts/render_handbook_traceability.py` (append)
- Modify: `tests/scripts/test_render_handbook_traceability.py` (append)

**Interfaces:**
- Consumes: everything Task 1 produced.
- Produces: `validate(rows, headings, dims) -> list[str]`, `render(rows) -> str`, `main(argv) -> int`. Tasks 3–7 run the CLI; the Task 3 gate test calls `main(["--check"])`.

- [ ] **Step 1: Write the failing tests**

Append to the test file. A tiny valid fixture plus one mutation per validation rule:

```python
def _fixture_dirs(tmp_path):
    _write(
        tmp_path / "handbook" / "alpha.md",
        "# Alpha\n\n## Mapped section\n\ntext\n\n## Split section\n\ntext\n",
    )
    _write(tmp_path / "handbook" / "coda.md", "# Coda\n\nno sections\n")
    _write(
        tmp_path / "skills" / "demo-audit" / "SKILL.md",
        "## 2. Dimensions (findings-matrix columns)\n\n- **Injection** — text.\n",
    )
    return rht.handbook_headings(tmp_path / "handbook"), rht.skill_dimensions(tmp_path / "skills")


def _valid_rows():
    return [
        {"id": "alpha/mapped-section", "section": "Mapped section", "claim": "c1", "class": "static",
         "checks": [{"skill": "demo-audit", "dimension": "Injection"}]},
        {"id": "alpha/split-section-a", "section": "Split section", "claim": "c2a", "class": "artifact",
         "gap": {"recommendation": "new-domain", "target": "#516", "note": "no lens yet"}},
        {"id": "alpha/split-section-b", "section": "Split section", "claim": "c2b", "class": "process"},
        {"id": "coda/coda", "section": "Coda", "claim": "closing words", "class": "informative"},
    ]


def test_validate_accepts_the_valid_fixture(tmp_path):
    headings, dims = _fixture_dirs(tmp_path)
    assert rht.validate(_valid_rows(), headings, dims) == []


def test_validate_catches_each_rule(tmp_path):
    headings, dims = _fixture_dirs(tmp_path)
    cases = [
        (lambda r: r[0].update(id="alpha/mapped-section", section="Wrong text"), "does not match heading"),
        (lambda r: r[0].update(id="nowhere/mapped-section"), "unknown handbook part"),
        (lambda r: r[0].update(id="alpha/no-such-anchor"), "does not resolve"),
        (lambda r: r[0].update(**{"class": "bogus"}), "class must be one of"),
        (lambda r: r[0].pop("checks"), "needs checks or a gap"),
        (lambda r: r[3].update(checks=[{"skill": "demo-audit", "dimension": "Injection"}]), "must not carry checks"),
        (lambda r: r[0]["checks"][0].update(skill="ghost-audit"), "unknown skill"),
        (lambda r: r[0]["checks"][0].update(dimension="Ghost dimension"), "no dimension"),
        (lambda r: r[1]["gap"].update(recommendation="wontfix"), "recommendation must be one of"),
        (lambda r: r.append(dict(r[0])), "duplicate id"),
        (lambda r: r.pop(3), "coda.md has no whole-part row"),
        (lambda r: (r.pop(1), r.pop(1)), "has no matrix row"),
    ]
    for mutate, expected in cases:
        rows = _valid_rows()
        mutate(rows)
        errors = rht.validate(rows, headings, dims)
        assert any(expected in e for e in errors), f"{expected!r} not in {errors}"


def test_render_produces_tables_gap_list_and_summary():
    rows = _valid_rows()
    out = rht.render(rows)
    assert "generated file" in out.lower()
    assert "[Mapped section](../engineering/alpha.md#mapped-section)" in out
    assert "`demo-audit` / Injection" in out
    assert "### new-domain" in out and "#516" in out
    assert "| static | 1 |" in out


def test_main_check_detects_a_stale_md(tmp_path, monkeypatch):
    headings_dir = tmp_path / "handbook"
    _fixture_dirs(tmp_path)
    yaml_path = tmp_path / "handbook-traceability.yaml"
    md_path = tmp_path / "handbook-traceability.md"
    import yaml as _yaml

    yaml_path.write_text(_yaml.safe_dump(_valid_rows(), sort_keys=False, allow_unicode=True))
    monkeypatch.setattr(rht, "HANDBOOK_DIR", headings_dir)
    monkeypatch.setattr(rht, "SKILLS_DIR", tmp_path / "skills")
    monkeypatch.setattr(rht, "YAML_PATH", yaml_path)
    monkeypatch.setattr(rht, "MD_PATH", md_path)
    assert rht.main(["--check"]) == 1  # md missing -> stale
    assert rht.main([]) == 0  # writes the md
    assert rht.main(["--check"]) == 0  # now fresh
    md_path.write_text(md_path.read_text() + "tampered\n")
    assert rht.main(["--check"]) == 1
```

Note for the `PART_ORDER` interaction: the fixture parts `alpha` is not in `PART_ORDER`; `render` must therefore emit parts in `PART_ORDER` order first and any remaining parts in sorted order afterwards (this also keeps the renderer usable on fixtures). `validate` does NOT require membership in `PART_ORDER` — the coverage check against the real handbook directory is what keeps the real matrix complete.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/scripts/test_render_handbook_traceability.py -v`
Expected: new tests FAIL with `AttributeError: module 'rht' has no attribute 'validate'`.

- [ ] **Step 3: Implement validate, render, main**

Append to the script:

```python
def _resolve(anchor: str, by_slug: dict[str, str]) -> str | None:
    """Return the base slug an anchor resolves to (exact, or minus a split suffix)."""
    if anchor in by_slug:
        return anchor
    stripped = _SPLIT_SUFFIX_RE.sub("", anchor)
    return stripped if stripped in by_slug else None


def validate(
    rows: list[dict[str, Any]],
    headings: dict[str, list[str]],
    dims: dict[str, list[str]],
) -> list[str]:
    """Check every schema rule from the design spec; return one message per violation."""
    errors: list[str] = []
    seen_ids: set[str] = set()
    covered: set[tuple[str, str]] = set()
    covered_parts: set[str] = set()
    norm_dims = {skill: {" ".join(d.split()).lower() for d in names} for skill, names in dims.items()}

    for i, row in enumerate(rows):
        rid = row.get("id")
        if not isinstance(rid, str) or "/" not in rid:
            errors.append(f"row {i}: missing or malformed id (expected <part>/<anchor>)")
            continue
        if rid in seen_ids:
            errors.append(f"{rid}: duplicate id")
        seen_ids.add(rid)
        part, anchor = rid.split("/", 1)
        part_headings = headings.get(part)
        if part_headings is None:
            errors.append(f"{rid}: unknown handbook part {part!r}")
            continue
        by_slug = {slugify(h): h for h in part_headings}
        base = _resolve(anchor, by_slug)
        if base is not None:
            covered.add((part, base))
            if row.get("section") != by_slug[base]:
                errors.append(
                    f"{rid}: section {row.get('section')!r} does not match heading {by_slug[base]!r}"
                )
        elif not part_headings and anchor == part:
            covered_parts.add(part)
        else:
            errors.append(f"{rid}: anchor does not resolve to a ## heading in {part}.md")

        cls = row.get("class")
        if cls not in CLASSES:
            errors.append(f"{rid}: class must be one of {CLASSES}, got {cls!r}")
        checks = row.get("checks") or []
        gap = row.get("gap")
        if cls in ("static", "artifact") and not checks and not gap:
            errors.append(f"{rid}: auditable row needs checks or a gap entry")
        if cls in ("process", "informative") and checks:
            errors.append(f"{rid}: {cls} row must not carry checks")
        for check in checks:
            skill = check.get("skill")
            dim = check.get("dimension", "")
            if skill not in norm_dims:
                errors.append(f"{rid}: unknown skill {skill!r}")
                continue
            if " ".join(dim.split()).lower() not in norm_dims[skill]:
                errors.append(f"{rid}: {skill} has no dimension {dim!r}")
        if gap and gap.get("recommendation") not in RECOMMENDATIONS:
            errors.append(
                f"{rid}: gap.recommendation must be one of {RECOMMENDATIONS}, got {gap.get('recommendation')!r}"
            )

    for part, part_headings in headings.items():
        for h in part_headings:
            if (part, slugify(h)) not in covered:
                errors.append(f"coverage hole: {part}.md section {h!r} has no matrix row")
        if not part_headings and part not in covered_parts:
            errors.append(f"coverage hole: {part}.md has no whole-part row")
    return errors


_HEADER = """<!-- GENERATED FILE - do not edit. Source: handbook-traceability.yaml; run scripts/render_handbook_traceability.py after editing. -->

# Handbook traceability matrix

Maps every ``##`` section of the [engineering handbook](../engineering/README.md) onto the ``*-audit`` skill family. Source of truth: [`handbook-traceability.yaml`](handbook-traceability.yaml). Issue: #543.

| Class | Meaning |
|---|---|
| `static` | Statically auditable from a repo snapshot; mapped to a skill check or carries a gap entry. |
| `artifact` | Auditable only via artifacts (eval runs, CI history, issue/PR trail). Absence of the artifact is itself a finding - never a pass. |
| `process` | Process/culture; not verifiable from the repo. Audit-report prose and adoption recommendations, never fake-automated. |
| `informative` | Non-normative (spine, coda, symptom index); accounted for, maps to nothing. |
"""


def _md_escape(text: str) -> str:
    return text.replace("|", "\\|")


def _checks_cell(row: dict[str, Any]) -> str:
    checks = row.get("checks") or []
    if not checks:
        return "-"
    return "<br>".join(f"`{c['skill']}` / {_md_escape(c['dimension'])}" for c in checks)


def _gap_cell(row: dict[str, Any]) -> str:
    gap = row.get("gap")
    if not gap:
        return "-"
    parts = [f"**{gap['recommendation']}**"]
    if gap.get("target"):
        parts.append(gap["target"])
    if gap.get("note"):
        parts.append(_md_escape(gap["note"]))
    return " - ".join(parts)


def _section_cell(row: dict[str, Any]) -> str:
    part, anchor = row["id"].split("/", 1)
    label = _md_escape(row.get("section", anchor))
    if anchor == part:
        return f"[{label}](../engineering/{part}.md)"
    if slugify(row.get("section", "")) == anchor:
        return f"[{label}](../engineering/{part}.md#{anchor})"
    m = _SPLIT_SUFFIX_RE.search(anchor)
    base = _SPLIT_SUFFIX_RE.sub("", anchor) if m else anchor
    marker = f" ({m.group(1)})" if m else ""
    return f"[{label}](../engineering/{part}.md#{base}){marker}"


def render(rows: list[dict[str, Any]]) -> str:
    by_part: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_part.setdefault(row["id"].split("/", 1)[0], []).append(row)
    ordered_parts = [p for p in PART_ORDER if p in by_part]
    ordered_parts += sorted(p for p in by_part if p not in PART_ORDER)

    out = [_HEADER]
    for part in ordered_parts:
        title = PART_TITLES.get(part, part)
        out.append(f"\n## {title}\n")
        out.append("| Section | Class | Mapped checks | Gap |")
        out.append("|---|---|---|---|")
        for row in by_part[part]:
            out.append(
                f"| {_section_cell(row)} | {row['class']} | {_checks_cell(row)} | {_gap_cell(row)} |"
            )

    gaps = [r for r in rows if r.get("gap")]
    out.append("\n## Gap list\n")
    if not gaps:
        out.append("No gaps: every auditable row is mapped.")
    for rec in RECOMMENDATIONS:
        group = [r for r in gaps if r["gap"]["recommendation"] == rec]
        if not group:
            continue
        out.append(f"\n### {rec}\n")
        for r in group:
            target = f" ({r['gap']['target']})" if r["gap"].get("target") else ""
            note = f" - {r['gap']['note']}" if r["gap"].get("note") else ""
            out.append(f"- `{r['id']}`{target}{note}")

    counts = {cls: sum(1 for r in rows if r["class"] == cls) for cls in CLASSES}
    auditable = [r for r in rows if r["class"] in ("static", "artifact")]
    mapped = [r for r in auditable if r.get("checks")]
    pct = round(100 * len(mapped) / len(auditable)) if auditable else 0
    out.append("\n## Coverage summary\n")
    out.append("| Class | Rows |")
    out.append("|---|---|")
    for cls in CLASSES:
        out.append(f"| {cls} | {counts[cls]} |")
    out.append("")
    out.append(
        f"{len(rows)} rows total; {len(mapped)}/{len(auditable)} auditable rows mapped ({pct}%); {len(gaps)} gap rows; {counts['process']} process-only rows."
    )
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render/verify the handbook traceability matrix.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate and fail if the committed md is stale, without writing",
    )
    parser.add_argument(
        "--allow-pending-parts",
        action="store_true",
        help="staged content walk: coverage holes in parts with no rows yet warn instead of failing",
    )
    args = parser.parse_args(argv)

    rows = yaml.safe_load(YAML_PATH.read_text())
    if not isinstance(rows, list):
        print(f"{YAML_PATH.name}: top level must be a list of rows", file=sys.stderr)
        return 1
    errors = validate(rows, handbook_headings(HANDBOOK_DIR), skill_dimensions(SKILLS_DIR))
    if args.allow_pending_parts:
        walked = {r["id"].split("/", 1)[0] for r in rows if isinstance(r.get("id"), str) and "/" in r["id"]}
        pending = [
            e
            for e in errors
            if e.startswith("coverage hole: ") and e.split(" ")[2].removesuffix(".md") not in walked
        ]
        errors = [e for e in errors if e not in pending]
        for w in pending:
            print(f"pending: {w}", file=sys.stderr)
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    rendered = render(rows)
    if args.check:
        if not MD_PATH.exists() or MD_PATH.read_text() != rendered:
            print(
                f"{MD_PATH.name} is stale; run: uv run python scripts/render_handbook_traceability.py",
                file=sys.stderr,
            )
            return 1
        return 0
    MD_PATH.write_text(rendered)
    print(f"wrote {MD_PATH.relative_to(REPO_ROOT)} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Implementation note on `_section_cell`: the split marker logic must render a split row (`...-a`) as a link to the base anchor plus a ` (a)` marker, and a non-split row whose slug happens to end in `-a` (its own heading resolves exactly) with no marker. The `slugify(section) == anchor` short-circuit handles the latter: equal means the anchor IS the heading's own slug (no split).

Also append the test for the staged-walk flag:

```python
def test_allow_pending_parts_tolerates_unwalked_parts_only(tmp_path, monkeypatch):
    import yaml as _yaml

    _fixture_dirs(tmp_path)
    _write(tmp_path / "handbook" / "beta.md", "# Beta\n\n## Unwalked section\n\ntext\n")
    yaml_path = tmp_path / "handbook-traceability.yaml"
    md_path = tmp_path / "handbook-traceability.md"
    yaml_path.write_text(_yaml.safe_dump(_valid_rows(), sort_keys=False, allow_unicode=True))
    monkeypatch.setattr(rht, "HANDBOOK_DIR", tmp_path / "handbook")
    monkeypatch.setattr(rht, "SKILLS_DIR", tmp_path / "skills")
    monkeypatch.setattr(rht, "YAML_PATH", yaml_path)
    monkeypatch.setattr(rht, "MD_PATH", md_path)
    assert rht.main([]) == 1  # beta.md uncovered -> strict fails
    assert rht.main(["--allow-pending-parts"]) == 0
    assert md_path.exists()
    rows = _valid_rows()
    del rows[0]  # alpha stays walked but now misses a section -> fails even with the flag
    yaml_path.write_text(_yaml.safe_dump(rows, sort_keys=False, allow_unicode=True))
    assert rht.main(["--allow-pending-parts"]) == 1
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/scripts/test_render_handbook_traceability.py -v`
Expected: PASS (9 tests).

- [ ] **Step 5: Run the gates and commit**

Run: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest tests/`

```bash
git add scripts/render_handbook_traceability.py tests/scripts/test_render_handbook_traceability.py
git commit -m "feat(#543): traceability matrix validation, rendering, and CLI"
```

---

### Task 3: Seed the matrix — informative parts + Part 7 (evaluation) — and the real-repo gate

**Files:**
- Create: `docs/audit/handbook-traceability.yaml`
- Create: `docs/audit/handbook-traceability.md` (generated)
- Modify: `tests/scripts/test_render_handbook_traceability.py` (append the gate test)

**Interfaces:**
- Consumes: the Task 2 CLI.
- Produces: the YAML file Tasks 4–6 append to; the always-on staleness gate.

- [ ] **Step 1: Write the informative rows**

Create `docs/audit/handbook-traceability.yaml` with one row per `##` section of `README.md` (5) and `troubleshooting.md` (4), plus the whole-part row `coda/coda`. Read each file; classify: README and troubleshooting sections are `informative` UNLESS a section carries a normative claim in its own right (judge while reading — e.g. a README section that mandates behavior rather than summarizing parts gets its real class). `claim` is a one-line paraphrase. Follow the schema from the Global Constraints exactly.

- [ ] **Step 2: Walk Part 7 (evaluation.md, 13 sections) — the first real mapping**

Read `docs/engineering/evaluation.md` section by section, and read the `## 2. Dimensions` sections of ALL eight skills (`docs-audit`, `deps-audit`, `arch-audit`, `security-audit`, `ci-audit`, `test-audit`, `eval-audit`, `prompt-audit`) so dimension names are quoted verbatim. For each section: identify the normative claims, classify (`static`/`artifact`/`process`), split into `-a`/`-b` rows only where claims diverge in class or skill, map to dimensions (expect mostly `eval-audit`), and write `gap` entries where auditable claims have no dimension (e.g. variance reporting → `#517` exists for that: `recommendation: extend-skill, target: "#517"`).

- [ ] **Step 3: Render and self-validate**

Run: `uv run python scripts/render_handbook_traceability.py --allow-pending-parts`
Expected: exits 0 and writes the md, printing `pending:` warnings for Parts 1–6, 8, 9 (no rows yet — that is the staged-walk state, resolved by Tasks 4–6). Any non-pending error is a defect in the rows just written; fix before committing.

The gate test added now must tolerate the same staged state (Task 6 Step 4 flips it to the strict `main(["--check"]) == 0` form):

```python
def test_real_matrix_has_no_errors_beyond_pending_parts():
    """Staleness + schema gate on the real repo files.

    Until the content walk completes (plan Tasks 4-6), parts not yet walked
    produce 'coverage hole' errors; anything else is a real defect. Task 6
    replaces this test with the strict main(["--check"]) == 0 form.
    """
    import yaml as _yaml

    rows = _yaml.safe_load(rht.YAML_PATH.read_text())
    errors = rht.validate(rows, rht.handbook_headings(rht.HANDBOOK_DIR), rht.skill_dimensions(rht.SKILLS_DIR))
    real = [e for e in errors if "coverage hole" not in e]
    assert real == []
    assert rht.MD_PATH.read_text() == rht.render(rows)
```

- [ ] **Step 4: Run the gates and commit**

Run: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest tests/`

```bash
git add docs/audit/handbook-traceability.yaml docs/audit/handbook-traceability.md tests/scripts/test_render_handbook_traceability.py
git commit -m "docs(#543): seed traceability matrix (informative parts + Part 7 evaluation)"
```

---

### Task 4: Content walk — Part 1 (lifecycle) + Part 2 (implementation-disciplines)

**Files:**
- Modify: `docs/audit/handbook-traceability.yaml` (append 16+ rows)
- Modify: `docs/audit/handbook-traceability.md` (regenerate)

- [ ] **Step 1: Walk lifecycle.md (9 sections)**

Same method as Task 3 Step 2. Expect: heavily `process` (spec gates, review discipline, human moments) with `artifact` rows where the trail is checkable (issue/spec/plan artifacts exist → `docs-audit` dimensions; CI gates enforced → `ci-audit` dimensions).

- [ ] **Step 2: Walk implementation-disciplines.md (7 sections)**

Expect a mix: TDD/test hygiene → `test-audit` dimensions; prompt/SOP engineering → `prompt-audit` dimensions; mechanical gates → `ci-audit`; behavioural gates → `eval-audit`. Split sections where craft (process) and gate (artifact/static) claims co-exist.

- [ ] **Step 3: Regenerate, gates, commit**

Run: `uv run python scripts/render_handbook_traceability.py --allow-pending-parts`
Run the four gates.

```bash
git add docs/audit/handbook-traceability.yaml docs/audit/handbook-traceability.md
git commit -m "docs(#543): traceability walk of Parts 1-2 (lifecycle, implementation disciplines)"
```

---

### Task 5: Content walk — Parts 3, 4, 5 (codebase-structure, three-layer-model, agent-harness)

**Files:**
- Modify: `docs/audit/handbook-traceability.yaml` (append 26+ rows)
- Modify: `docs/audit/handbook-traceability.md` (regenerate)

- [ ] **Step 1: Walk codebase-structure.md (9 sections)**

Expect mostly `static` → `arch-audit` dimensions (layering, acyclic deps, composition).

- [ ] **Step 2: Walk three-layer-model.md (8 sections)**

Expect the hardest classification of the plan: the three-layer *document* model is a domain-design prescription. Claims about code shape (layer boundaries in the codebase) → `static`/`arch-audit`; claims about how document knowledge is organized → likely `process` or gaps (`report-only` recommendation when no skill could reasonably check it).

- [ ] **Step 3: Walk agent-harness.md (9 sections)**

Expect `static` claims (model aliases not hard-coded IDs, named profiles, headless CLI exists, mock backends, bounded external calls) that today have NO owning dimension — candidate gap rows. Decide per row: `extend-skill` (name the closest skill, e.g. `arch-audit` or `eval-audit`) vs `new-domain`. These gap rows are a key #543 deliverable — do not force-map to a vaguely related dimension just to avoid a gap entry.

- [ ] **Step 4: Regenerate, gates, commit**

Run: `uv run python scripts/render_handbook_traceability.py --allow-pending-parts`
Run the four gates.

```bash
git add docs/audit/handbook-traceability.yaml docs/audit/handbook-traceability.md
git commit -m "docs(#543): traceability walk of Parts 3-5 (structure, document model, harness)"
```

---

### Task 6: Content walk — Parts 6, 8, 9 (observability, documentation, security-supply-chain) — strict gate flips on

**Files:**
- Modify: `docs/audit/handbook-traceability.yaml` (append 25+ rows)
- Modify: `docs/audit/handbook-traceability.md` (regenerate, now strict)
- Modify: `tests/scripts/test_render_handbook_traceability.py` (flip the gate test to strict)

- [ ] **Step 1: Walk observability.md (8 sections)**

Expect predominantly `artifact` gap rows → `recommendation: new-domain, target: "#516"` (the observability domain does not exist yet). Where an existing dimension genuinely covers a claim (e.g. eval-audit's cost tracking), map it.

- [ ] **Step 2: Walk documentation.md (8 sections)**

Expect `docs-audit` dimensions for most auditable claims; `process` for knowledge-capture culture (stories, recorded results) unless docs-audit has a matching dimension — check, do not assume.

- [ ] **Step 3: Walk security-supply-chain.md (9 sections)**

Expect `security-audit`, `deps-audit`, `ci-audit` dimensions; data-protection claims with no dimension → `gap: {recommendation: new-domain, target: "#518"}`.

- [ ] **Step 4: Flip the gate to strict**

All 12 parts now have rows. Replace `test_real_matrix_has_no_errors_beyond_pending_parts` with:

```python
def test_real_matrix_passes_the_strict_check():
    assert rht.main(["--check"]) == 0
```

Regenerate WITHOUT the flag: `uv run python scripts/render_handbook_traceability.py`
Expected: exits 0, coverage complete.

- [ ] **Step 5: Gates and commit**

Run the four gates.

```bash
git add docs/audit/handbook-traceability.yaml docs/audit/handbook-traceability.md tests/scripts/test_render_handbook_traceability.py
git commit -m "docs(#543): traceability walk of Parts 6, 8, 9; strict coverage gate on"
```

---

### Task 7: Consolidation — gap-list review, front-door link, docs index

**Files:**
- Modify: `docs/audit/handbook-traceability.yaml` (consistency edits only, if the review finds any)
- Modify: `.agents/skills/audit/SKILL.md` (one pointer line)
- Modify: `docs/README.md` (index entry for docs/audit/)

- [ ] **Step 1: Review the gap list as a whole**

Read the rendered Gap list end to end and check: (a) every `new-domain` gap carries the right target among #516/#518 or explicitly none; (b) `extend-skill` gaps name a plausible skill in the note; (c) related sections got consistent classifications across parts (e.g. CI-gate claims in Part 1 and Part 2 map to the same `ci-audit` dimensions). Fix inconsistencies in the YAML, regenerate.

- [ ] **Step 2: Link from the audit front door**

Add one line to `.agents/skills/audit/SKILL.md` (in the "How it works" intro, after the opening paragraph): a pointer that the handbook↔skills coverage record lives at `docs/audit/handbook-traceability.md`, and that gaps in domain coverage are tracked there. One sentence — the #544 citation-binding work is explicitly NOT this task.

- [ ] **Step 3: Update the docs index**

Add `docs/audit/` (the traceability matrix) to the index in `docs/README.md`, following its existing entry style.

- [ ] **Step 4: Final verification**

Run: `uv run python scripts/render_handbook_traceability.py --check` → exit 0.
Run the four gates. Verify each #543 acceptance criterion against the artifacts (do not tick issue boxes yet — that happens at merge time).

```bash
git add docs/audit/handbook-traceability.yaml docs/audit/handbook-traceability.md .agents/skills/audit/SKILL.md docs/README.md
git commit -m "docs(#543): gap-list consolidation, front-door pointer, docs index"
```
