"""Render and verify the handbook traceability matrix (#543).

`docs/audit/handbook-traceability.yaml` is the hand-maintained source of
truth mapping every `##` section of the engineering handbook
(`docs/engineering/`) onto the `*-audit` skill family
(`.agents/skills/`). This script validates that mapping against the real
handbook headings and skill dimensions, and renders the committed Markdown
view `docs/audit/handbook-traceability.md`.

Each row carries two orthogonal axes. `class` (`static` | `artifact` |
`process` | `informative`) says whether the clause can be checked at all;
`severity` (`critical` | `important` | `minor`) says what violating it
costs, reusing audit-core's scale. Validation requires `severity` on
`static`/`artifact`/`process` rows and forbids it on `informative` ones,
which also may not carry a `gap` - together that is what keeps the three
severity groups of the rendered gap list exhaustive, so no gap row can
drop off the page unnoticed.

Within a severity group, a gap entry is one of three kinds: `unchecked` (an
auditable row nothing checks), `residue` (the part of a claim a mapped
check does not reach), and `process` (a claim no snapshot can settle).
They are different work downstream, so each entry carries its kind as a
tag rather than relying on its position in the list, and each band states
its own split. A band's unchecked count is by construction the same number
as its Unmapped column in the severity x coverage cross-tab.

Handbook links are rendered as absolute GitHub URLs: `docs/engineering/` is
excluded from the built docs site (the handbook ships as a standalone HTML
artifact), so a relative link into it resolves on GitHub but 404s on the
site and fails `scripts/check_site_links.py`.

Usage:
    uv run python scripts/render_handbook_traceability.py          # validate + write the md
    uv run python scripts/render_handbook_traceability.py --check  # validate; fail if the md is stale

Exit code 0 on success; 1 with one message per problem on validation
failure or staleness. The pytest gate in `tests/scripts/` runs `--check`
so CI guards staleness with no workflow change.

Design: docs/superpowers/specs/2026-07-29-handbook-traceability-matrix-design.md
        docs/superpowers/plans/2026-07-30-matrix-severity-axis.md (severity axis)
        docs/superpowers/specs/2026-07-30-gap-entry-kinds-design.md (gap-entry kinds)
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

# The handbook is excluded from the built site, so links into it must be
# absolute to resolve both on GitHub and on the site.
HANDBOOK_URL = "https://github.com/lidia-tech/lidia-agents/blob/main/docs/engineering"

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
SEVERITIES = ("critical", "important", "minor")
SEVERITY_LABELS = {"critical": "Critical", "important": "Important", "minor": "Minor"}
# Classes that make a normative claim, so a violation carries a risk worth rating.
ASSESSABLE = ("static", "artifact", "process")

KINDS = ("unchecked", "residue", "process")
# Singular and plural for the per-band count line; "unchecked" is invariant.
KIND_LABELS = {
    "unchecked": ("unchecked", "unchecked"),
    "residue": ("residue", "residues"),
    "process": ("process row", "process rows"),
}

_HEADING_RE = re.compile(r"^## (.+?)\s*$")
_FENCE_RE = re.compile(r"^(```|~~~)")
_DIMENSIONS_HEADING_RE = re.compile(r"^## \d+\. Dimensions\b")
_DIM_BULLET_RE = re.compile(r"^- \*\*(.+?)\*\*")
_SPLIT_SUFFIX_RE = re.compile(r"-([a-z])$")
_PART_NUMBER_RE = re.compile(r"^# Part (\d+)\.")
_TITLE_NUMBER_RE = re.compile(r"^Part (\d+):")


def slugify(heading: str) -> str:
    """GitHub-style anchor: lowercase, keep `[a-z0-9 _-]`, spaces to hyphens."""
    text = heading.strip().lower().replace("`", "")
    text = re.sub(r"[^a-z0-9 _-]", "", text)
    return text.replace(" ", "-")


def handbook_headings(handbook_dir: Path) -> dict[str, list[str]]:
    """Map each handbook part stem to its ordered `##` heading texts.

    Only level-2 headings count (the row unit per the design spec); fenced
    code blocks are skipped so a `##` inside an example is not a section.

    A fence left open swallows every heading after it, and a swallowed
    heading is invisible to the coverage check below — no row is demanded
    for a section nobody can see. So an unclosed fence raises here rather
    than quietly shrinking the matrix, the same contract
    `render_handbook_artifact.py` settled on in 722f5eda. A fence closed
    with the other marker (``` opened, ~~~ closed) never closes, and so
    surfaces as the same error.

    Args:
        handbook_dir: Directory holding the handbook's `*.md` parts.

    Returns:
        Part stem mapped to its `##` heading texts, in document order.

    Raises:
        ValueError: A part leaves a fence unclosed at end of file.
    """
    parts: dict[str, list[str]] = {}
    for md in sorted(handbook_dir.glob("*.md")):
        headings: list[str] = []
        fence_marker: str | None = None
        fence_line = 0
        for lineno, line in enumerate(md.read_text().splitlines(), 1):
            m_fence = _FENCE_RE.match(line)
            if m_fence:
                marker = m_fence.group(1)[0]
                if fence_marker is None:
                    fence_marker, fence_line = marker, lineno
                elif marker == fence_marker:
                    fence_marker = None
                continue
            if fence_marker is not None:
                continue
            m = _HEADING_RE.match(line)
            if m:
                headings.append(m.group(1))
        if fence_marker is not None:
            raise ValueError(
                f"{md.name}: the {fence_marker * 3} fence opened at line "
                f"{fence_line} is never closed, so every '##' heading after "
                "it would drop out of the matrix unnoticed. Close it, or "
                "match the marker it was opened with."
            )
        parts[md.stem] = headings
    return parts


def handbook_part_numbers(handbook_dir: Path) -> dict[str, int | None]:
    """Map each handbook part stem to the number in its `# Part N.` H1.

    The stems the matrix orders and titles are hardcoded, but the handbook
    renumbers (becac52a, 262f16f7 — twice in one week, the second of which
    had to hand-fix the sibling renderer's equivalent list). Reading the
    real number back lets `validate` catch the desync.

    Args:
        handbook_dir: Directory holding the handbook's `*.md` parts.

    Returns:
        Part stem mapped to its part number, or `None` for the unnumbered
        parts (README, troubleshooting, coda).
    """
    numbers: dict[str, int | None] = {}
    for md in sorted(handbook_dir.glob("*.md")):
        numbers[md.stem] = None
        for line in md.read_text().splitlines():
            if line.startswith("# "):
                m = _PART_NUMBER_RE.match(line)
                numbers[md.stem] = int(m.group(1)) if m else None
                break
    return numbers


def skill_dimensions(skills_dir: Path) -> dict[str, list[str]]:
    """Map each skill directory name to the bolded lead phrases of its Dimensions bullets.

    A skill without a numbered `## N. Dimensions` heading (audit-core, the
    audit front door, non-audit skills) is simply absent from the result.
    That absence is legitimate; a skill that *has* the heading but whose
    bullets no longer parse is not, and would otherwise be indistinguishable
    from it — every check citing that skill would fail as "unknown skill",
    pointing at the matrix instead of at the reformatted bullet. So an
    empty Dimensions section raises.

    Args:
        skills_dir: Directory holding one subdirectory per skill.

    Returns:
        Skill directory name mapped to its dimensions' bolded lead phrases.

    Raises:
        ValueError: A skill declares a Dimensions section with no bullet
            the `- **Name** — …` parser recognises.
    """
    dims: dict[str, list[str]] = {}
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        names: list[str] = []
        in_section = False
        found_section = False
        for line in skill_md.read_text().splitlines():
            if _DIMENSIONS_HEADING_RE.match(line):
                in_section = found_section = True
                continue
            if in_section and line.startswith("## "):
                in_section = False
                continue
            if in_section:
                m = _DIM_BULLET_RE.match(line)
                if m:
                    names.append(m.group(1))
        if found_section and not names:
            raise ValueError(
                f"{skill_md.parent.name}: has a '## N. Dimensions' section but no "
                "bullet matching '- **Name**'. Every check citing this skill would "
                "fail as an unknown skill and blame the matrix for a formatting "
                "change in the skill."
            )
        if names:
            dims[skill_md.parent.name] = names
    return dims


def validate_parts(part_numbers: dict[str, int | None]) -> list[str]:
    """Check the hardcoded part order and titles against the handbook on disk.

    `validate` guarantees every section of every *known* part has a row. It
    cannot see a part the constants forgot, nor notice that Part 5 became
    Part 6 upstream, because `render` falls back to the raw file stem for an
    unknown part rather than failing.

    Args:
        part_numbers: Part stem mapped to its `# Part N.` number, or `None`
            where the part carries no number.

    Returns:
        One message per mismatch; empty when the constants are in sync.
    """
    errors: list[str] = []
    on_disk = set(part_numbers)
    known = set(PART_ORDER)

    for stem in sorted(on_disk - known):
        errors.append(f"{stem}: handbook part is missing from PART_ORDER")
    for stem in sorted(known - on_disk):
        errors.append(f"{stem}: PART_ORDER names a part with no file on disk")
    for stem in sorted(known - set(PART_TITLES)):
        errors.append(f"{stem}: PART_ORDER entry has no PART_TITLES title")
    for stem in sorted(set(PART_TITLES) - known):
        errors.append(f"{stem}: PART_TITLES entry is not in PART_ORDER")

    for stem in sorted(on_disk & known & set(PART_TITLES)):
        m = _TITLE_NUMBER_RE.match(PART_TITLES[stem])
        titled = int(m.group(1)) if m else None
        actual = part_numbers[stem]
        if titled != actual:
            errors.append(
                f"{stem}: PART_TITLES says part {titled}, the handbook H1 says "
                f"{actual}. The handbook renumbered; update PART_ORDER and "
                "PART_TITLES to match."
            )
    return errors


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
    """Check every schema rule from the design spec.

    Args:
        rows: The raw matrix rows as loaded from YAML, unvalidated.
        headings: Part stem mapped to its `##` heading texts, from
            `handbook_headings`.
        dims: Skill name mapped to its dimension names, from
            `skill_dimensions`.

    Returns:
        One message per violation, so a single run reports every problem;
        empty when the matrix is sound.
    """
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
        sev = row.get("severity")
        if cls in ASSESSABLE and sev not in SEVERITIES:
            errors.append(
                f"{rid}: {cls} row needs severity one of {SEVERITIES}, got {sev!r}"
            )
        if cls == "informative" and sev is not None:
            errors.append(
                f"{rid}: informative rows carry no severity (got {sev!r}); "
                "severity is the risk of violating a normative claim, and an "
                "informative row makes none"
            )
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
        if cls == "informative" and gap:
            errors.append(
                f"{rid}: informative row must not carry a gap; the rendered gap "
                "list groups by severity, which an informative row has none of"
            )

        if cls in ("static", "artifact") and not checks and not gap:
            errors.append(f"{rid}: auditable row needs checks or a gap entry")
        if cls in ("process", "informative") and checks:
            errors.append(f"{rid}: {cls} row must not carry checks")
        for check in checks:
            if not isinstance(check, dict):
                errors.append(f"{rid}: check entries must be mappings")
                continue
            skill = check.get("skill")
            dim = check.get("dimension")
            if skill not in norm_dims:
                errors.append(f"{rid}: unknown skill {skill!r}")
                continue
            if not isinstance(dim, str):
                errors.append(f"{rid}: check dimension must be a string, got {dim!r}")
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

Maps every `##` section of the [engineering handbook](https://github.com/lidia-tech/lidia-agents/blob/main/docs/engineering/README.md) onto the `*-audit` skill family. Source of truth: [`handbook-traceability.yaml`](handbook-traceability.yaml). Issue: #543.

Section links are absolute GitHub URLs because the handbook is excluded from the built docs site (it ships as a standalone HTML artifact).

| Class | Meaning |
|---|---|
| `static` | Statically auditable from a repo snapshot; mapped to a skill check or carries a gap entry. |
| `artifact` | Auditable only via artifacts (eval runs, CI history, issue/PR trail). Absence of the artifact is itself a finding - never a pass. |
| `process` | Process/culture; not verifiable from the repo. Audit-report prose and adoption recommendations, never fake-automated. |
| `informative` | Non-normative (spine, coda, symptom index); accounted for, maps to nothing. |

| Severity | Violating the clause means | Test |
|---|---|---|
| `critical` | Exposure that is hard to undo or reaches beyond the team: credentials or personal data leaked, licence or legal exposure, data loss, wrong output shipped to users unnoticed. | Could this appear in an incident report or a legal review? |
| `important` | You can still ship, but you can no longer tell whether what you shipped is right: silent incorrectness, unreproducible results, undiagnosable production failure, unbounded cost. | Does ignoring it destroy your ability to know the system works? |
| `minor` | Comfort, tidiness, or local velocity, with no effect on correctness, safety, or measurability. | Is the worst case "mildly annoying" or "harder to read"? |

Severity is orthogonal to class: class is *can we check it*, severity is *how bad if it is violated*. The scale is audit-core's own Critical / Important / Minor, so a matrix row and an audit finding speak the same language. Six notes govern how to read the column - the first two are interpretation rules, the rest explain splits a reader would otherwise take for errors:

**Baseline, not verdict.** A row records the severity a violation *inherently* carries, independent of any repo's current state. An auditor may raise or lower it for a specific instance with a stated reason - a load-bearing production prompt and a throwaway eval prompt violate the same clause at different cost.

**`process` rows carry a severity too.** "Spec before code" cannot be checked from a snapshot but is not thereby harmless, and an adoption roadmap needs to know what to sequence first. Only `informative` rows have none.

**Band counts per part do not rank the parts.** A part's distribution reflects how its clauses are cut into rows as much as what it is about: where a section bundles a consequential clause with hygiene, the row takes the higher band and the hygiene becomes invisible, so a part whose sections cut single-clause rows shows Minors that an otherwise similar part does not. Read the severity column per row, not per part.

**Documentation-currency clauses sit in different bands on purpose.** A currency clause is `important` when the stale claim is the reader's only access to the truth, and `minor` when the truth sits beside the claim: the prose tree exists to be read *instead of* the source, so a false claim in it is unfalsifiable where it is read, while a docstring or a commit-message rationale is read *beside* the artifact it describes and its staleness surfaces at the call site.

**Gate-shaped clauses land in more than one band.** A gate is rated on the harm it is the sole detector for, not on the subject it guards: encoding a class of security fix as a CI gate is `important` because the fixes themselves are the Critical part and the gate is one step removed, while a link-and-index checker guards a `minor` property and stays there.

**A checklist recap inherits its band.** A recap row takes the maximum severity of everything it recaps, so it adds no risk surface of its own. Where one lands in the Critical band, it points at rows already in the list rather than widening it, so a triager should read past it to the rows it recaps.

Each row's first cell links to the handbook section and restates the claim the row covers; where one section's claims fall into different classes or map to different skills, the row is split and the split is marked `(a)`, `(b)`, ... The **Notes** column carries the row's rationale - why a class was chosen, what a mapping reaches, what it deliberately leaves to the gap.

## Maintenance rules

Two rules keep the walk reproducible. Apply them when adding or revising a row.

**Gap taxonomy.** `extend-skill` when an existing skill is the natural owner and the fix is one new dimension inside it - or a declaration of coverage it already has outside its `## Dimensions` section. `new-domain` when no existing skill is a natural owner and the capability itself is missing; a note that says the claim "belongs to the domain the target issue creates" is `new-domain`, never `extend-skill`. `report-only` when the claim is auditable but belongs in report prose against the handbook's own checklist rather than in any skill's matrix. Every `extend-skill` gap names its owning skill in the note; every `new-domain` gap carries the issue that would create the domain, or says explicitly that none exists yet.

**Near-miss mappings.** Map a dimension that only partly reaches a claim when it would *flag* the handbook's violation, and record the residue as a gap on the same row. Refuse it - and gap the whole claim - when it would *pass* the violation. Worked example: an inline hard-coded model ID is more pinned than an alias, so `eval-audit` / Reproducibility is satisfied by exactly what Part 5 forbids; that row maps nothing and gaps everything.
"""


def _md_escape(text: str) -> str:
    return text.replace("|", "\\|")


def _oneline(value: Any) -> str:
    """Collapse a YAML scalar to one line, leaving Markdown punctuation alone."""
    return " ".join(str(value).split())


def _flat(value: Any) -> str:
    """Collapse a YAML scalar to one table-safe line.

    A newline ends a GFM table row and a bare pipe opens a column, so any
    hand-written field reaching a cell has to lose both. `--check` is no
    safety net here: it compares a fresh render against the committed one,
    and both would carry the same broken table.
    """
    return _md_escape(_oneline(value))


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
        parts.append(_flat(gap["target"]))
    if gap.get("note"):
        parts.append(_flat(gap["note"]))
    return " - ".join(parts)


def _gap_kind(row: dict[str, Any]) -> str:
    """Which of the three gap-entry kinds a gap-carrying row is.

    The three are not interchangeable downstream: an unchecked clause needs
    new capability, a residue widens something that already runs, and a
    process claim closes in report prose rather than in any skill's matrix.
    They also land in different cross-tab columns, so a two-way split would
    file a process gap under Unmapped and break the band arithmetic.

    Args:
        row: A gap-carrying matrix row, already through `validate`.

    Returns:
        One of `"unchecked"`, `"residue"`, `"process"`.
    """
    if row["class"] == "process":
        return "process"
    return "residue" if row.get("checks") else "unchecked"


def _kind_split_line(group: list[dict[str, Any]]) -> str:
    """The band's own split across the three kinds, zero terms omitted.

    Printing the split is what makes the band's unchecked figure readable
    rather than a counting exercise: it is the same number as the band's
    Unmapped column in the cross-tab.

    Args:
        group: The gap-carrying rows of one severity band.

    Returns:
        A sentence such as `"30 unchecked, 17 residues."`.
    """
    parts = []
    for kind in KINDS:
        n = sum(1 for r in group if _gap_kind(r) == kind)
        if not n:
            continue
        singular, plural = KIND_LABELS[kind]
        parts.append(f"{n} {singular if n == 1 else plural}")
    return ", ".join(parts) + "."


def _severity_cell(row: dict[str, Any]) -> str:
    """Title-cased severity, or `-` for a row carrying none of the three.

    On validated rows that fallback means `informative`. An out-of-enum
    value renders the same way, so the cell is only truthful for rows that
    have been through `validate`.
    """
    return SEVERITY_LABELS.get(row.get("severity", ""), "-")


def _note_cell(row: dict[str, Any]) -> str:
    """Row-level rationale, whitespace-normalized so it fits one table cell."""
    note = row.get("note")
    if not note:
        return "-"
    return _flat(note)


def handbook_link(row: dict[str, Any]) -> tuple[str, str]:
    """Absolute GitHub URL for the row's handbook section, plus its split marker.

    The marker is `" (a)"`-style for a row that covers one slice of a split
    section, and empty otherwise.

    Args:
        row: A matrix row; its `id` and `section` locate the heading.

    Returns:
        A `(url, marker)` pair.
    """
    part, anchor = row["id"].split("/", 1)
    if anchor == part:  # whole-part row (a part with no ## headings)
        return f"{HANDBOOK_URL}/{part}.md", ""
    if slugify(row.get("section", "")) == anchor:
        return f"{HANDBOOK_URL}/{part}.md#{anchor}", ""
    m = _SPLIT_SUFFIX_RE.search(anchor)
    base = _SPLIT_SUFFIX_RE.sub("", anchor) if m else anchor
    return f"{HANDBOOK_URL}/{part}.md#{base}", f" ({m.group(1)})" if m else ""


def _section_cell(row: dict[str, Any]) -> str:
    """Linked section heading with its split marker, over the row's claim."""
    url, marker = handbook_link(row)
    label = _flat(row.get("section", row["id"].split("/", 1)[1]))
    claim = _flat(row.get("claim", "")) if row.get("claim") else ""
    return f"[{label}]({url}){marker}" + (f"<br>{claim}" if claim else "")


def render(rows: list[dict[str, Any]]) -> str:
    """Render the whole matrix document from the validated rows.

    Emits the generated-file header and legend, one table per handbook part
    in the handbook's own reading order, the gap list grouped by severity
    and then by gap-entry kind, and the coverage summary with its severity x
    coverage cross-tab and the sentence reconciling the gap total against
    those components.

    Every severity band is emitted whenever the matrix has any gap at all,
    including one that carries none, so a band that clears its gaps says so
    rather than disappearing from the page.

    Args:
        rows: Matrix rows, already through `validate`.

    Returns:
        The complete Markdown document, newline-terminated.
    """
    by_part: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_part.setdefault(row["id"].split("/", 1)[0], []).append(row)
    ordered_parts = [p for p in PART_ORDER if p in by_part]
    ordered_parts += sorted(p for p in by_part if p not in PART_ORDER)

    out = [_HEADER]
    for part in ordered_parts:
        title = PART_TITLES.get(part, part)
        out.append(f"\n## {title}\n")
        out.append(
            "| Section / claim | Class | Severity | Mapped checks | Gap | Notes |"
        )
        out.append("|---|---|---|---|---|---|")
        for row in by_part[part]:
            out.append(
                f"| {_section_cell(row)} | {row['class']} | {_severity_cell(row)} "
                f"| {_checks_cell(row)} | {_gap_cell(row)} | {_note_cell(row)} |"
            )

    gaps = [r for r in rows if r.get("gap")]
    out.append("\n## Gap list\n")
    if not gaps:
        out.append("No gaps: every auditable row is mapped.")
    else:
        out.append(
            "Ordered by severity - the risk a violation carries - then by kind, "
            "then by handbook order. Each entry names its kind, its "
            "recommendation (`extend-skill` / `new-domain` / `report-only`) and, "
            "where one exists, the issue that would close it. Three kinds "
            "appear, and they are different work: `(unchecked)` is a clause "
            "nothing checks, so closing it means new capability; `(residue)` is "
            "the part of a claim a mapped check does not reach, so closing it "
            "widens something that already runs; `(process)` is a claim no "
            "snapshot can settle, which closes in report prose and an adoption "
            "roadmap rather than in any skill's matrix. Each band opens with its "
            "own split, and a band's unchecked count is the same number as its "
            "[cross-tab](#severity-x-coverage) Unmapped column."
        )
    for sev in SEVERITIES:
        if not gaps:
            break
        group = [r for r in gaps if r.get("severity") == sev]
        out.append(f"\n### {SEVERITY_LABELS[sev]}\n")
        if not group:
            # State the clear band rather than omitting it. A band that drops
            # off the page is indistinguishable from a rendering fault, and
            # the good news is exactly what a triager is looking for.
            out.append(f"No {SEVERITY_LABELS[sev]} clause carries a gap.")
            continue
        out.append(_kind_split_line(group))
        out.append("")
        for kind in KINDS:
            for r in (g for g in group if _gap_kind(g) == kind):
                url, marker = handbook_link(r)
                gap = r["gap"]
                # Bullets, not cells: a pipe is harmless here, a newline is not.
                bits = [f"**{gap['recommendation']}**"]
                if gap.get("target"):
                    bits.append(_oneline(gap["target"]))
                if gap.get("note"):
                    bits.append(_oneline(gap["note"]))
                out.append(
                    f"- [`{r['id']}`]({url}){marker} ({kind}) - " + " - ".join(bits)
                )

    counts = {cls: sum(1 for r in rows if r["class"] == cls) for cls in CLASSES}
    auditable = [r for r in rows if r["class"] in ("static", "artifact")]
    full = [r for r in auditable if r.get("checks") and not r.get("gap")]
    partial = [r for r in auditable if r.get("checks") and r.get("gap")]
    unmapped = [r for r in auditable if not r.get("checks")]
    process_gaps = [r for r in gaps if _gap_kind(r) == "process"]
    pct = round(100 * len(full) / len(auditable)) if auditable else 0
    out.append("\n## Coverage summary\n")
    out.append("| Class | Rows |")
    out.append("|---|---|")
    for cls in CLASSES:
        out.append(f"| {cls} | {counts[cls]} |")
    out.append("\n### Severity x coverage\n")
    out.append(
        "The actionable question: which high-risk clauses does nothing check? "
        "The Unmapped column is the answer, and the rows behind each count are "
        "listed by name, tagged `(unchecked)`, under the matching heading in the "
        "[gap list](#gap-list) "
        "above. Read a Critical unmapped count as the head of the queue. "
        "The four data columns before the Process one count auditable rows only; "
        "the Process column counts rows that carry a severity but can never be "
        "checked from a snapshot, and so belong in report prose and an adoption "
        "roadmap rather than in any skill's matrix."
    )
    out.append("")
    out.append(
        "| Severity | Fully mapped | Partial | Unmapped | Auditable total | Process |"
    )
    out.append("|---|---|---|---|---|---|")
    for sev in SEVERITIES:
        aud = [r for r in auditable if r.get("severity") == sev]
        n_full = sum(1 for r in aud if r.get("checks") and not r.get("gap"))
        n_partial = sum(1 for r in aud if r.get("checks") and r.get("gap"))
        n_proc = sum(
            1 for r in rows if r["class"] == "process" and r.get("severity") == sev
        )
        out.append(
            f"| {SEVERITY_LABELS[sev]} | {n_full} | {n_partial} "
            f"| {len(aud) - n_full - n_partial} | {len(aud)} | {n_proc} |"
        )
    out.append("")
    if process_gaps:
        n = len(process_gaps)
        reconciliation = (
            f"{len(gaps) - n} of the {len(gaps)} gap entries sit on auditable "
            f"rows (all {len(unmapped)} unmapped, plus the {len(partial)} "
            f"partial); the other {n} "
            + ("sits on a process row" if n == 1 else "sit on process rows")
            + ", whose claim is auditable in principle but belongs in report "
            "prose rather than in any skill's matrix. "
        )
    else:
        reconciliation = (
            f"All {len(gaps)} gap entries sit on auditable rows: the "
            f"{len(unmapped)} unmapped "
            + ("one" if len(unmapped) == 1 else "ones")
            + f" plus the {len(partial)} partial. "
        )
    out.append(
        f"{len(rows)} rows total. Of the {len(auditable)} auditable rows "
        f"({counts['static']} static + {counts['artifact']} artifact): "
        f"**{len(full)} fully mapped** ({pct}%), **{len(partial)} partially mapped** "
        f"(a check that reaches part of the claim, with the residue recorded as a gap), "
        f"and **{len(unmapped)} unmapped** (no check reaches the claim; every one of "
        f"them still carries a gap entry saying so and why, which the schema requires). "
        + reconciliation
        + f"The remaining {counts['process']} process and {counts['informative']} informative "
        f"rows are not auditable by design - the honest record of what a snapshot cannot settle."
    )
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Validate the matrix and either write the Markdown or check it is current.

    Args:
        argv: Command-line arguments; `None` reads `sys.argv`.

    Returns:
        `0` on success, `1` on any validation error or, under `--check`, a
        stale committed Markdown file.
    """
    parser = argparse.ArgumentParser(
        description="Render/verify the handbook traceability matrix."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate and fail if the committed md is stale, without writing",
    )
    args = parser.parse_args(argv)

    rows = yaml.safe_load(YAML_PATH.read_text())
    if not isinstance(rows, list):
        print(f"{YAML_PATH.name}: top level must be a list of rows", file=sys.stderr)
        return 1
    errors = validate_parts(handbook_part_numbers(HANDBOOK_DIR))
    errors += validate(
        rows, handbook_headings(HANDBOOK_DIR), skill_dimensions(SKILLS_DIR)
    )
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
