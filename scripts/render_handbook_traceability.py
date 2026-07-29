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

import re
from pathlib import Path

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
