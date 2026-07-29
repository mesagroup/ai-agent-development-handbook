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
    norm_dims = {
        skill: {" ".join(d.split()).lower() for d in names}
        for skill, names in dims.items()
    }

    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"row {i}: not a mapping")
            continue

        rid = row.get("id")
        if not isinstance(rid, str) or "/" not in rid:
            errors.append(
                f"row {i}: missing or malformed id (expected <part>/<anchor>)"
            )
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
            errors.append(
                f"{rid}: anchor does not resolve to a ## heading in {part}.md"
            )

        cls = row.get("class")
        if cls not in CLASSES:
            errors.append(f"{rid}: class must be one of {CLASSES}, got {cls!r}")
        checks_raw = row.get("checks")
        if checks_raw and not isinstance(checks_raw, list):
            errors.append(f"{rid}: checks must be a list")
            checks = []
        else:
            checks = checks_raw or []
        gap = row.get("gap")
        if gap is not None and not isinstance(gap, dict):
            errors.append(f"{rid}: gap must be a mapping")
            gap = None

        if cls in ("static", "artifact") and not checks and not gap:
            errors.append(f"{rid}: auditable row needs checks or a gap entry")
        if cls in ("process", "informative") and checks:
            errors.append(f"{rid}: {cls} row must not carry checks")
        for check in checks:
            if not isinstance(check, dict):
                errors.append(f"{rid}: check entries must be mappings")
                continue
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
                errors.append(
                    f"coverage hole: {part}.md section {h!r} has no matrix row"
                )
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
    parser = argparse.ArgumentParser(
        description="Render/verify the handbook traceability matrix."
    )
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
    errors = validate(
        rows, handbook_headings(HANDBOOK_DIR), skill_dimensions(SKILLS_DIR)
    )
    if args.allow_pending_parts:
        walked = {
            r["id"].split("/", 1)[0]
            for r in rows
            if isinstance(r.get("id"), str) and "/" in r["id"]
        }
        pending = [
            e
            for e in errors
            if e.startswith("coverage hole: ")
            and e.split(" ")[2].removesuffix(".md") not in walked
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
