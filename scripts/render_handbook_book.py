"""Build the handbook as a book: an EPUB now, the paperback later (#195).

The page renderer's first pass, `assemble`, produces each part's HTML with
the heading ids and in-page links the rendered page carries. This module
joins those parts into one HTML document and hands it to pandoc, so the
book's ids are the page's by construction and every citation a report
emits lands on the same heading in both. Diagrams render as listings here
until #190 draws them as figures.

Usage::

    uv run python scripts/render_handbook_book.py --format epub
    uv run python scripts/render_handbook_book.py --format epub --out /tmp/handbook.epub

Needs the pandoc CLI (``brew install pandoc``). Everything except
`run_tool`, `build_epub` and `main` is pure and unit-tested in
``tests/scripts/test_render_handbook_book.py``.
"""

from __future__ import annotations

import uuid
from html import escape as html_escape
from pathlib import Path

from render_handbook_artifact import (
    _DIAGRAM_PLACEHOLDER_RE,
    AssembledPart,
    DiagramBlock,
    render_part,
)

TITLE = "AI Agent Development Handbook"
CREATOR = "Janos Tolgyesi"
# No holder is named: #188 has not settled who holds the copyright.
RIGHTS = (
    "Licensed under the Creative Commons Attribution 4.0 International "
    "License (CC BY 4.0), https://creativecommons.org/licenses/by/4.0/"
)

EPUB_CSS = """\
body { font-family: serif; line-height: 1.45; }
h1, h2, h3, h4 { font-family: sans-serif; line-height: 1.2; }
code, pre { font-family: monospace; font-size: 0.85em; }
pre { white-space: pre-wrap; }
table { border-collapse: collapse; font-size: 0.85em; }
th, td { border: 1px solid #888; padding: 0.25em 0.4em; text-align: left; vertical-align: top; }
figure { margin: 1em 0; }
figcaption { font-size: 0.85em; font-style: italic; }
"""


def book_linkmap(
    parts: list[tuple[str, str, str]], first_ids: dict[str, str]
) -> dict[str, str]:
    """Map each ``<stem>.md`` to its part's first heading id.

    The page links a part by its section anchor (``#p1``). The book emits no
    section wrapper, because a wrapper stops pandoc splitting chapters on the
    part's ``<h1>``, so a bare part link lands on that heading instead.

    Raises:
        ValueError: A part has no heading, so a link to it has nowhere to land.
    """
    linkmap = {}
    for _, stem, _ in parts:
        if stem not in first_ids:
            raise ValueError(
                f"{stem}.md has no heading, so a book link to it would land nowhere"
            )
        linkmap[stem + ".md"] = "#" + first_ids[stem]
    return linkmap


def first_heading_ids(
    docs_dir: Path, parts: list[tuple[str, str, str]]
) -> dict[str, str]:
    """Each part's first heading id; a part with no heading is left out."""
    first = {}
    for _, stem, _ in parts:
        _, ids, _ = render_part(docs_dir, stem)
        if ids:
            first[stem] = ids[0]
    return first


def listing_markup(block: DiagramBlock) -> str:
    """Stand a diagram in as its escaped source under its caption.

    Until #190 draws figures, the book shows each diagram's source. The source
    is escaped: d2 syntax such as ``a -> b: <x>`` would otherwise reach pandoc
    as markup and be dropped without a word.
    """
    return (
        "<figure>"
        f"<pre><code>{html_escape(block.source, quote=False)}</code></pre>"
        f"<figcaption>{html_escape(block.title, quote=False)}</figcaption>"
        "</figure>"
    )


def book_html(assembled: list[AssembledPart]) -> str:
    """Join the parts into one document, with each diagram as a listing."""
    bodies = []
    for part in assembled:
        listings = {block.index: listing_markup(block) for block in part.blocks}

        def repl(match, listings=listings, stem=part.stem):
            index = int(match.group(1))
            if index not in listings:
                raise ValueError(f"{stem}.md: no diagram block for placeholder {index}")
            return listings[index]

        bodies.append(_DIAGRAM_PLACEHOLDER_RE.sub(repl, part.html))
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        f'<meta charset="utf-8">\n<title>{TITLE}</title>\n</head>\n<body>\n'
        + "\n".join(bodies)
        + "\n</body>\n</html>\n"
    )


def book_identifier(title: str) -> str:
    """A ``urn:uuid`` derived from the title, so every build carries the same one."""
    return f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, title)}"


def book_metadata(date: str) -> str:
    """The pandoc metadata document: what epubcheck requires, and the rights.

    Values are written as single-quoted YAML scalars via `repr`, which is
    exact for these ASCII strings with no quote in them.
    """
    fields = {
        "title": TITLE,
        "creator": CREATOR,
        "lang": "en",
        "date": date,
        "identifier": book_identifier(TITLE),
        "rights": RIGHTS,
    }
    lines = [f"{key}: {value!r}" for key, value in fields.items()]
    return "---\n" + "\n".join(lines) + "\n---\n"


def epub_command(
    html_path: Path, metadata_path: Path, css_path: Path, out: Path
) -> list[str]:
    """The pandoc argv that turns the book document into an EPUB3."""
    return [
        "pandoc",
        "-f", "html+smart",
        "-t", "epub3",
        "--split-level=1",
        "--toc",
        "--toc-depth=2",
        "--metadata-file", str(metadata_path),
        "--css", str(css_path),
        "-o", str(out),
        str(html_path),
    ]  # fmt: skip
