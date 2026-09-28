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
`run_tool`, `build_epub` and `main` spawns no process and writes no file;
`first_heading_ids` and `require_h1_first` read files. All of it is
unit-tested in ``tests/scripts/test_render_handbook_book.py``.
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import tempfile
import uuid
from html import escape as html_escape
from pathlib import Path

from render_handbook_artifact import (
    _DIAGRAM_PLACEHOLDER_RE,
    PARTS,
    AssembledPart,
    DiagramBlock,
    assemble,
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


_FIRST_HEADING_LEVEL_RE = re.compile(r'<h([1-6]) id="')


def require_h1_first(docs_dir: Path, parts: list[tuple[str, str, str]]) -> None:
    """Raise unless every part with a heading starts with an ``<h1>``.

    Pandoc splits chapters on ``<h1>`` (``--split-level=1``). A part whose
    first heading is ``<h2>`` or deeper gives it nothing to split on, so the
    part merges silently into the previous chapter instead of becoming its
    own; this check catches that before pandoc ever runs, rather than after,
    where only a diff of the chapter count would show it.

    Raises:
        ValueError: A part's first heading is not level 1.
    """
    for _, stem, _ in parts:
        html, ids, _ = render_part(docs_dir, stem)
        if not ids:
            continue
        match = _FIRST_HEADING_LEVEL_RE.search(html)
        if match and match.group(1) != "1":
            raise ValueError(
                f"{stem}.md: first heading is <h{match.group(1)}>, not <h1>; "
                "pandoc splits chapters on <h1> (--split-level=1), so this "
                "part would merge silently into the previous chapter instead "
                "of starting its own"
            )


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


_PANDOC_TIMEOUT_S = 120
_PANDOC_HINT = (
    "Install it with `brew install pandoc`, or see https://pandoc.org/installing.html."
)


def run_tool(cmd: list[str], timeout: float, install_hint: str) -> None:
    """Run one external tool, bounded, and turn every failure into a message.

    Raises:
        SystemExit: The tool is absent, did not finish within ``timeout``
            seconds, or exited non-zero; the message names the tool and, for
            a missing one, how to install it.
    """
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=timeout
        )
    except FileNotFoundError as exc:
        raise SystemExit(f"{cmd[0]} not found on PATH. {install_hint}") from exc
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(
            f"{cmd[0]} did not finish within {timeout}s. An unbounded call would "
            "hang the build with no diagnosis."
        ) from exc
    if proc.returncode != 0:
        raise SystemExit(
            f"{cmd[0]} failed (exit {proc.returncode}):\n{proc.stderr.strip()}"
        )


def build_epub(
    docs_dir: Path,
    out: Path,
    date: str,
    parts: list[tuple[str, str, str]] = PARTS,
) -> Path:
    """Write the EPUB for ``docs_dir`` to ``out`` and return ``out``."""
    require_h1_first(docs_dir, parts)
    linkmap = book_linkmap(parts, first_heading_ids(docs_dir, parts))
    html = book_html(assemble(docs_dir, parts, linkmap))
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / "book.html").write_text(html, encoding="utf-8")
        (work / "metadata.yaml").write_text(book_metadata(date), encoding="utf-8")
        (work / "epub.css").write_text(EPUB_CSS, encoding="utf-8")
        cmd = epub_command(
            work / "book.html", work / "metadata.yaml", work / "epub.css", out
        )
        run_tool(cmd, _PANDOC_TIMEOUT_S, _PANDOC_HINT)
    return out


def _build_date() -> str:
    """``SOURCE_DATE_EPOCH`` when set, so a tagged build is reproducible.

    Raises:
        SystemExit: ``SOURCE_DATE_EPOCH`` is set but is not an integer.
    """
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        try:
            moment = datetime.datetime.fromtimestamp(int(epoch), tz=datetime.UTC)
        except ValueError as exc:
            raise SystemExit(
                f"SOURCE_DATE_EPOCH={epoch!r} is not an integer Unix timestamp."
            ) from exc
    else:
        moment = datetime.datetime.now(tz=datetime.UTC)
    return moment.date().isoformat()


def main(argv: list[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--format", choices=["epub"], required=True)
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=repo_root / "docs" / "engineering",
        help="Directory holding the handbook markdown (default: docs/engineering).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path (default: build/handbook.epub, gitignored).",
    )
    args = parser.parse_args(argv)
    out = args.out or repo_root / "build" / "handbook.epub"
    build_epub(args.docs_dir, out, _build_date())
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
