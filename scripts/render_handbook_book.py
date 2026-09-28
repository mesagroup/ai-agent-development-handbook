"""Build the handbook as a book: an EPUB now, the paperback later (#195).

The page renderer's first pass, `assemble`, produces each part's HTML with
the heading ids and in-page links the rendered page carries. This module
joins those parts into one HTML document and hands it to pandoc, so the
book's ids are the page's by construction and every citation a report
emits lands on the same heading in both. Diagrams render as listings here
until #190 draws them as figures, and a checklist item carries a ☐/☒ glyph
(`restore_task_boxes`) so it reads as a box rather than a plain bullet.
Prose quotes are curled to typographic ones and inline code is left
untouched (`curl_quotes`) before the document ever reaches pandoc.

Usage::

    uv run python scripts/render_handbook_book.py --format epub
    uv run python scripts/render_handbook_book.py --format epub --out /tmp/handbook.epub

Needs the pandoc CLI (``brew install pandoc``). Everything except
`run_tool`, `build_epub` and `main` spawns no process and writes no file.
All of it is unit-tested in ``tests/scripts/test_render_handbook_book.py``.
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
    render_parts,
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
    rendered: dict[str, tuple[str, list[str], list[DiagramBlock]]],
    parts: list[tuple[str, str, str]],
) -> dict[str, str]:
    """Each part's first heading id; a part with no heading is left out.

    Args:
        rendered: Every part's `render_part` output, keyed by stem - what
            `render_parts` produces once for the whole build.
        parts: ``(anchor, stem, label)`` in page order.
    """
    first = {}
    for _, stem, _ in parts:
        _, ids, _ = rendered[stem]
        if ids:
            first[stem] = ids[0]
    return first


_LEADING_HEADING_RE = re.compile(r'^\s*<h([1-6]) id="')


def require_h1_first(
    rendered: dict[str, tuple[str, list[str], list[DiagramBlock]]],
    parts: list[tuple[str, str, str]],
) -> None:
    """Raise unless every part with a heading opens with its own ``<h1>``.

    Pandoc splits chapters on ``<h1>`` (``--split-level=1``). A part whose
    first heading is ``<h2>`` or deeper gives it nothing to split on, and a
    part carrying content - prose, a list, a placeholder - before its
    ``<h1>`` leaves that content with nothing to split on either, since a
    check that only found *some* ``<h1>`` in the part would pass either way;
    either shape merges silently into the previous chapter instead of
    becoming its own. This check catches that before pandoc ever runs,
    rather than after, where only a diff of the chapter count would show it.

    Args:
        rendered: Every part's `render_part` output, keyed by stem - what
            `render_parts` produces once for the whole build.
        parts: ``(anchor, stem, label)`` in page order.

    Raises:
        ValueError: A part's first heading is not level 1, or the part
            carries content before its first heading.
    """
    for _, stem, _ in parts:
        html, ids, _ = rendered[stem]
        if not ids:
            continue
        match = _LEADING_HEADING_RE.match(html)
        if match is None:
            raise ValueError(
                f"{stem}.md: content precedes its first heading; pandoc "
                "splits chapters on <h1> (--split-level=1), so that leading "
                "content would join the previous chapter instead of starting "
                "this part's own"
            )
        if match.group(1) != "1":
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


_TASK_ITEM_RE = re.compile(r'<li class="task( done)?">')


def restore_task_boxes(html: str) -> str:
    """Turn the page's task-list markup into a literal box glyph.

    `render_handbook_artifact.mark_task_items` strips a checklist item's
    ``[ ]``/``[x]`` and marks it ``<li class="task">``/``<li class="task
    done">``; the page's CSS draws the box from that class. Pandoc's HTML
    reader drops the class, so this writes ☐ (U+2610, open) or ☒ (U+2612,
    done) as the item's leading text instead. The glyph is wrapped in a
    ``<span>`` rather than left bare: checked against pandoc 3.8.2, its HTML
    reader turns a bare ☐/☒-prefixed ``<li>`` into an ``<input
    type="checkbox">`` regardless of the ``task_lists`` extension - disabling
    it on both reader and writer left the behaviour unchanged - and an EPUB
    reading system is not required to render a form control at all, nor can
    a reader's tick of it persist. The span defeats that detection, so the
    glyph reaches the EPUB as the literal character it is. Spelling the
    source as a raw ``<input type="checkbox">`` fares worse still: the same
    reader drops the surrounding ``<ul>``/``<li>`` entirely and the item
    survives only as a bare ``<p>``.
    """

    def repl(match: re.Match[str]) -> str:
        glyph = "☒" if match.group(1) else "☐"
        return f'<li><span class="task-box">{glyph}</span> '

    return _TASK_ITEM_RE.sub(repl, html)


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

        bodies.append(restore_task_boxes(_DIAGRAM_PLACEHOLDER_RE.sub(repl, part.html)))
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        f'<meta charset="utf-8">\n<title>{TITLE}</title>\n</head>\n<body>\n'
        + "\n".join(bodies)
        + "\n</body>\n</html>\n"
    )


_QUOTE_TOKEN_RE = re.compile(r"<[^>]*>|[^<]+")
_QUOTE_TAG_NAME_RE = re.compile(r"</?\s*([a-zA-Z][a-zA-Z0-9]*)")
_QUOTE_SKIP_TAGS = frozenset({"code", "pre"})
_QUOTE_OPEN_CONTEXT = frozenset(" \t\n\r([{\u2018\u201c")


def curl_quotes(html: str) -> str:
    """Curl straight quotes to typographic ones in prose, verbatim in code.

    Pandoc's own ``+smart`` reader extension would do this, but it also
    rewrites ``--`` inside an inline ``<code>`` span (``--rebase`` becomes an
    en dash), because pandoc's HTML reader applies smart typography to a
    ``Code`` span's text the same as to prose, unlike its Markdown reader,
    which exempts code spans by design - confirmed against pandoc 3.8.2 with
    ``echo '<p><code>--rebase</code></p>' | pandoc -f html+smart -t html``.
    Doing the curling here instead, and dropping ``+smart`` from
    `epub_command`, sidesteps that reader entirely, at the cost of narrowing
    to what the handbook's own prose needs: every ``docs/engineering/*.md``
    straight quote is either a double quote or a mid-word apostrophe/
    possessive (verified by sweeping the corpus for one-word single-quoted
    phrases and finding none), and the corpus carries no ``--`` or em dash
    outside a fenced or inline code span, so dashes need no handling here.

    Walks `html` as a stream of tag and text tokens, skipping every run of
    text inside ``<code>`` or ``<pre>`` (nested or not) so inline code and
    the book's diagram-source listings reach pandoc, and the EPUB, exactly as
    written. In the text that is curled, a straight double quote opens
    (``\u201c``) when the character before it is missing, whitespace, or an
    opening bracket, and closes (``\u201d``) otherwise; a straight single
    quote is an apostrophe (``\u2019``) when the character before it is a
    letter or digit, an opening quote (``\u2018``) under the same rule as a
    double quote, and otherwise a closing one. An *opening* tag counts as
    whitespace for this rule, since the handbook's own quoted asides
    (```**"We added more patterns"**```) open a quote flush against
    ``<strong>`` with no letter beside it to judge by; a *closing* tag does
    not reset the context, so ``Part 1</a>'s gates`` - a real
    ``docs/engineering/lifecycle.md`` link followed immediately by a
    possessive - still sees the ``1`` before the apostrophe and curls it as
    one, rather than resetting to whitespace and misreading it as an opening
    single quote.
    """
    out: list[str] = []
    skip_depth = 0
    prev = " "
    for token in _QUOTE_TOKEN_RE.findall(html):
        if token.startswith("<"):
            out.append(token)
            name_match = _QUOTE_TAG_NAME_RE.match(token)
            closing = token.startswith("</")
            if name_match and name_match.group(1).lower() in _QUOTE_SKIP_TAGS:
                if closing:
                    skip_depth = max(0, skip_depth - 1)
                elif not token.rstrip().endswith("/>"):
                    skip_depth += 1
            if not closing and not token.rstrip().endswith("/>"):
                prev = " "
            continue
        if skip_depth:
            out.append(token)
            if token:
                prev = token[-1]
            continue
        chars = []
        for ch in token:
            if ch == '"':
                chars.append("\u201c" if prev in _QUOTE_OPEN_CONTEXT else "\u201d")
            elif ch == "'":
                if prev.isalnum():
                    chars.append("\u2019")
                elif prev in _QUOTE_OPEN_CONTEXT:
                    chars.append("\u2018")
                else:
                    chars.append("\u2019")
            else:
                chars.append(ch)
            prev = ch
        out.append("".join(chars))
    return "".join(out)


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
    """The pandoc argv that turns the book document into an EPUB3.

    Reads plain ``html``, not ``html+smart``: `curl_quotes` already curled
    the book document's prose quotes before it reached this command, and
    ``+smart`` would also rewrite ``--`` inside an inline ``<code>`` span
    (see `curl_quotes`), which no step in this pipeline should ever do.
    """
    return [
        "pandoc",
        "-f", "html",
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
    """Write the EPUB for ``docs_dir`` to ``out`` and return ``out``.

    Renders every part once with `render_parts` and shares that one render
    across `require_h1_first`, `first_heading_ids` and `assemble`, rather
    than each converting every part's Markdown on its own.
    """
    rendered = render_parts(docs_dir, parts)
    require_h1_first(rendered, parts)
    linkmap = book_linkmap(parts, first_heading_ids(rendered, parts))
    html = curl_quotes(book_html(assemble(docs_dir, parts, linkmap, rendered=rendered)))
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
