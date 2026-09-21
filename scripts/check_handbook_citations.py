"""Hold every handbook citation a report can emit against the rendered page's anchors (#139).

A report cites the handbook two ways, and a recipient holding the rendered
page has to be able to follow both into it. The skills spell absolute URLs of
the form ``.../docs/engineering/<stem>.md#<fragment>``, whose fragment is the
GitHub-style slug of a heading; the emitter lists matrix row ids of the form
``<stem>/<slug>[-letter]``, whose ``section:`` title slugifies to the same
heading. The first shape is read as every ``docs/engineering/<stem>.md`` path
under the skills tree, absolute or relative and with or without a fragment,
because a record's ``handbook_note`` is rendered into the matrix where its
``handbook:`` list is empty, so a path written there as authoring provenance
reaches a report as text too; the count therefore covers what a report can
carry rather than only what a skill spells as a link. The page gives every heading the id ``<stem>-<slug>``, so a URL
fragment resolves to ``<stem>-<fragment>`` and a row to
``<stem>-<slugify(section)>``, and this script computes both mappings over
the whole tree and reports what does and does not resolve.

Two sources of ids. By default the ids are computed from the markdown the way
the renderer computes them, without the d2 CLI, so this runs anywhere the
suite runs. ``--page`` reads them off a rendered page instead, which is the
check to run against the artifact that actually ships.

Usage::

    uv run python scripts/check_handbook_citations.py
    uv run python scripts/check_handbook_citations.py --page test-reports/handbook.html

Exits 1 when any citation resolves to nothing. The counts it prints are what
#139's second criterion asks to record, and a later handbook edit that
orphans a citation shows up here as one unresolved entry naming its source.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from render_handbook_artifact import PARTS, heading_ids
from render_handbook_traceability import slugify

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs" / "engineering"
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
MATRIX = REPO_ROOT / "docs" / "audit" / "handbook-traceability.yaml"

# A citation of a handbook part in any prose the family emits: the absolute
# GitHub URL the skills write, or a relative path. The fragment is optional,
# because a link to a whole part is a citation too, and it resolves to the
# part's anchor rather than to a heading.
_CITATION_RE = re.compile(r"docs/engineering/([A-Za-z0-9-]+)\.md(?:#([A-Za-z0-9_-]+))?")
_ID_ATTR_RE = re.compile(r' id="([^"]+)"')
_PART_ANCHORS = {stem: anchor for anchor, stem, _ in PARTS}


@dataclass(frozen=True)
class Citation:
    """One place a report can point into the handbook, and where it lands.

    Args:
        kind: ``url`` for a fragment or whole-part link found in the skills,
            ``row`` for a matrix row id the emitter lists.
        source: Where it was found: a path for a URL, the row id for a row.
        target: The page id it has to resolve to.
    """

    kind: str
    source: str
    target: str


def skill_citations(root: Path = SKILLS_DIR) -> list[Citation]:
    """Every handbook citation written under the skills tree, deduplicated.

    Read from every Markdown file under ``root``, records included, because a
    check record's prose can cite a clause the way a skill does. A stem naming
    no part resolves to nothing and is kept so that it reports.
    """
    found: set[Citation] = set()
    for path in sorted(root.rglob("*.md")):
        for stem, fragment in _CITATION_RE.findall(path.read_text()):
            if fragment:
                target = f"{stem}-{fragment}"
            else:
                target = _PART_ANCHORS.get(stem, f"<no part {stem!r}>")
            found.add(Citation("url", str(path.relative_to(root)), target))
    return sorted(found, key=lambda c: (c.source, c.target))


def row_target(row_id: str, section: str) -> str:
    """The page id a matrix row's citation lands on.

    The stem is the part before the slash; the slug after it may carry a split
    suffix (``-a``, ``-b``) that names the row rather than the heading, so the
    heading is taken from the row's own ``section:`` title, which the matrix
    validator already holds against the part's ``##`` headings.
    """
    stem = row_id.split("/", 1)[0]
    return f"{stem}-{slugify(section)}"


def row_citations(matrix: Path = MATRIX) -> list[Citation]:
    """One citation per matrix row: the id the emitter lists, and its heading."""
    rows = yaml.safe_load(matrix.read_text())
    return [
        Citation("row", row["id"], row_target(row["id"], row["section"]))
        for row in rows
    ]


def page_ids(html: str) -> set[str]:
    """Every ``id`` attribute a rendered page carries."""
    return set(_ID_ATTR_RE.findall(html))


def resolve(
    citations: list[Citation], ids: set[str]
) -> tuple[list[Citation], list[Citation]]:
    """Split citations into the ones whose target is an id and the ones that are not."""
    resolved = [c for c in citations if c.target in ids]
    unresolved = [c for c in citations if c.target not in ids]
    return resolved, unresolved


def report(
    ids: set[str], skills: list[Citation], rows: list[Citation]
) -> tuple[str, bool]:
    """Render the counts and the unresolved list; the flag says whether all resolved."""
    lines = []
    ok = True
    for label, citations in (("skill citations", skills), ("matrix rows", rows)):
        resolved, unresolved = resolve(citations, ids)
        lines.append(f"{label}: {len(citations)} found, {len(resolved)} resolved")
        for c in unresolved:
            ok = False
            lines.append(f"  UNRESOLVED {c.kind} {c.source} -> {c.target}")
    lines.append(f"page ids: {len(ids)}")
    return "\n".join(lines), ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--page",
        type=Path,
        default=None,
        help="A rendered handbook page to read ids from (default: compute them from the markdown).",
    )
    parser.add_argument("--docs-dir", type=Path, default=DOCS_DIR)
    parser.add_argument("--skills-dir", type=Path, default=SKILLS_DIR)
    parser.add_argument("--matrix", type=Path, default=MATRIX)
    args = parser.parse_args(argv)
    ids = page_ids(args.page.read_text()) if args.page else heading_ids(args.docs_dir)
    text, ok = report(ids, skill_citations(args.skills_dir), row_citations(args.matrix))
    print(text)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
