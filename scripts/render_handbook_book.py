"""Build the handbook as a book: an EPUB now, the paperback later (#195).

The page renderer's first pass, `assemble`, produces each part's HTML with
the heading ids and in-page links the rendered page carries. This module
joins those parts into one HTML document and hands it to pandoc, so the
book's ids are the page's by construction and every citation a report
emits lands on the same heading in both. Each diagram is a captioned figure
(`figure_markup`): its committed SVG under ``docs/engineering/figures/``, or,
where none is committed yet, its seed, with a NOTE on stderr naming the
fence (`load_figure`, `write_figures`). The EPUB's copy of each stays
transparent, carries the subset faces its text uses, and is placed at the
one scale through an em width (`book_figures`). A checklist item carries a ☐/☒ glyph
(`restore_task_boxes`) so it reads as a box rather than a plain bullet.
A list item marked `BOOK_OMIT_MARKER` in the source is left out of the
book (`omit_from_book`). Prose quotes are curled to typographic ones and inline code is left
untouched (`curl_quotes`) before the document ever reaches pandoc, and
"Part" is kept on the line of its number (`glue_part_numbers`).
The text is set in the committed faces `EPUB_FACES` names, which pandoc
embeds and `font_face_css` declares.

Usage::

    uv run python scripts/render_handbook_book.py --format epub
    uv run python scripts/render_handbook_book.py --format epub --out /tmp/handbook.epub
    uv run python scripts/render_handbook_book.py --seed-figures

Needs the pandoc CLI (``brew install pandoc``) for ``--format epub``, and
the d2 CLI for ``--seed-figures`` and for ``--format epub`` whenever a d2
diagram has no committed figure, since the build then draws its seed. Only
`run_tool` and `seed_svg` (through `run_d2`) spawn a process themselves,
which `load_figure`, `seed_figures` and `write_figures` reach through
`seed_svg` where a d2 fence has no committed figure, and which `build_epub`
also reaches directly, calling `run_tool` itself to run pandoc; only
`seed_figures`, `write_figures` and `build_epub` write a file, and `main`
calls `seed_figures` or `build_epub`, whichever the CLI selected, `build_epub`
calling `write_figures`. Every other function spawns no process and writes
no file. All of it is unit-tested in
``tests/scripts/test_render_handbook_book.py``.
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import sys
import tempfile
import uuid
from html import escape as html_escape
from pathlib import Path

from book_figures import (
    clean_seed_svg,
    embed_fonts,
    epub_width_em,
    source_hash,
    stamp_hash,
)
from render_handbook_artifact import (
    _DIAGRAM_PLACEHOLDER_RE,
    PARTS,
    AssembledPart,
    DiagramBlock,
    assemble,
    extract_diagram_blocks,
    funnel_svg_vertical,
    parse_funnel,
    render_parts,
    run_d2,
)

TITLE = "AI Agent Development Handbook"
CREATOR = "Janos Tolgyesi"
# No holder is named: #188 has not settled who holds the copyright.
RIGHTS = (
    "Licensed under the Creative Commons Attribution 4.0 International "
    "License (CC BY 4.0), https://creativecommons.org/licenses/by/4.0/"
)
# A part whose heading suits the page but not a book chapter, by stem. The
# README's heading is the handbook's own title, which the book already carries
# as its title, so its chapter is named for what it is. Only the text changes:
# the heading keeps its id, so every citation still lands on it.
BOOK_PART_TITLES = {"README": "Introduction"}
_H1_RE = re.compile(r"(<h1\b[^>]*>).*?(</h1>)", re.S)

# The faces the book is set in, each a committed, unmodified file under
# `FONTS_ROOT` that pandoc embeds (`epub_command`) and `font_face_css` declares:
# (family, weight, style, path under `FONTS_ROOT`). A face the text uses and
# this table leaves out is synthesised by the reading system, or substituted.
FONTS_ROOT = Path(__file__).resolve().parents[1] / "fonts"
# The committed Source Sans 3 faces `embed_fonts` subsets into each figure.
FONT_DIR = FONTS_ROOT / "source-sans-3"
EPUB_FACES = (
    ("Source Serif 4", "normal", "normal", "source-serif-4/SourceSerif4-Regular.ttf"),
    ("Source Serif 4", "normal", "italic", "source-serif-4/SourceSerif4-It.ttf"),
    ("Source Serif 4", "bold", "normal", "source-serif-4/SourceSerif4-Bold.ttf"),
    ("Source Serif 4", "bold", "italic", "source-serif-4/SourceSerif4-BoldIt.ttf"),
    ("Source Sans 3", "bold", "normal", "source-sans-3/SourceSans3-Bold.ttf"),
    ("Source Code Pro", "normal", "normal", "source-code-pro/SourceCodePro-Regular.ttf"),
)  # fmt: skip


def font_face_css(faces=EPUB_FACES) -> str:
    """One ``@font-face`` rule per face, pointing where pandoc puts the file.

    Pandoc copies each ``--epub-embed-font`` file to the EPUB's ``fonts/``
    under its own basename, and the stylesheet sits in the sibling
    ``styles/``, hence ``../fonts/``.
    """
    return "".join(
        f'@font-face {{ font-family: "{family}"; font-weight: {weight}; '
        f'font-style: {style}; src: url("../fonts/{Path(path).name}"); }}\n'
        for family, weight, style, path in faces
    )


# A part opens on a right-hand page where the reading system honours the
# request (a two-page spread can then show its title where every other part's
# is, with its top margin).
#
# A heading asks not to be split across pages or to end one: `break-after:
# avoid` on it and `orphans: 2` on the paragraph after it ask for at least two
# lines of text with it. Each property is spelled three ways because reading
# systems paginate with CSS columns or paged media and honour different
# spellings. These are requests: Apple Books keeps a heading whole but still
# lets one end a page, and an empty block reserving two lines under each
# heading did not change that there either.
#
# A table asks to move whole to the next page rather than split. One too tall
# for any page still splits, between rows and never through one, and repeats
# its header row on each page it continues onto.
# Its rules are horizontal only, so a split leaves no box open at the page edge
# and reads as the gap between two rows.
# A cell is never hyphenated: pandoc sets no column widths, so the reader
# sizes each column from its narrowest unbreakable run, and Apple Books, which
# hyphenates by default, would otherwise squeeze a short column to a syllable.
#
# A figure asks not to split, so its caption stays on the page of its image.
EPUB_CSS = (
    font_face_css()
    + """\
body { font-family: "Source Serif 4", serif; line-height: 1.45; }
h1, h2, h3, h4 { font-family: "Source Sans 3", sans-serif; line-height: 1.2; }
h1 { break-before: right; page-break-before: right; }
h1, h2, h3, h4, h5, h6 { break-inside: avoid; break-after: avoid; page-break-inside: avoid; page-break-after: avoid; -webkit-column-break-inside: avoid; -webkit-column-break-after: avoid; }
p, li { text-align: justify; -webkit-hyphens: auto; hyphens: auto; orphans: 2; widows: 2; }
code, pre { font-family: "Source Code Pro", monospace; font-size: 0.85em; }
pre { white-space: pre-wrap; }
table { border-collapse: collapse; font-size: 0.85em; border-top: 1.5px solid; border-bottom: 1.5px solid; }
table, tr { break-inside: avoid; page-break-inside: avoid; -webkit-column-break-inside: avoid; }
thead { display: table-header-group; }
th, td { border: none; padding: 0.25em 0.4em; text-align: left; vertical-align: top; -webkit-hyphens: manual; hyphens: manual; }
th { border-bottom: 1px solid; }
td { border-top: 1px solid #bbb; }
figure { margin: 1em 0; text-align: center; break-inside: avoid; page-break-inside: avoid; -webkit-column-break-inside: avoid; }
figure img { display: block; margin: 0 auto; }
figcaption { font-size: 0.85em; font-style: italic; text-align: center; }
div.checklist ul { list-style-type: none; }
div.checklist li { padding-left: 1.4em; text-indent: -1.4em; }
.task-box { display: inline-block; width: 1.4em; text-indent: 0; }
a { color: inherit; text-decoration: underline; }
nav#toc ol { list-style-type: none; padding-left: 0; }
nav#toc a { color: inherit; text-decoration: none; }
"""
)


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


def figure_markup(stem: str, block: DiagramBlock, width_em: float) -> str:
    """A diagram as a captioned ``<img>`` of its media SVG, ``width_em`` wide.

    The title is the image's ``alt`` and its caption, escaped both times: a
    title such as ``A & <b>`` would otherwise reach pandoc as markup. The
    width is in em so the figure keeps the one scale relative to the body
    text when a reader changes the font size, and ``max-width: 100%`` stops
    it overflowing a screen narrower than that.
    """
    alt = html_escape(block.title, quote=True)
    caption = html_escape(block.title, quote=False)
    return (
        "<figure>"
        f'<img src="media/{stem}-{block.index}.svg" alt="{alt}"'
        f' style="width: {width_em:.2f}em; max-width: 100%">'
        f"<figcaption>{caption}</figcaption>"
        "</figure>"
    )


def load_figure(figures_dir: Path, stem: str, block: DiagramBlock) -> tuple[str, bool]:
    """A diagram's committed figure, or its seed standing in for one.

    Returns:
        The SVG, and whether it is a seed standing in because no figure is
        committed at `figure_path` - in which case this runs `seed_svg`, and
        with it the d2 CLI for a d2 block.
    """
    path = figure_path(figures_dir, stem, block.index)
    if path.exists():
        return path.read_text(encoding="utf-8"), False
    return seed_svg(stem, block), True


_TASK_ITEM_RE = re.compile(r'<li class="task( done)?">')
# An innermost list: one that contains no other list.
_INNER_UL_RE = re.compile(r"<ul>(?:(?!</?ul\b).)*?</ul>", re.S)
_LI_RE = re.compile(r"<li\b[^>]*>")


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

    A list whose every item is a checklist item is wrapped in ``<div
    class="checklist">``, the one way to mark it that survives pandoc, which
    drops a ``<ul>``'s class as it drops an ``<li>``'s: the stylesheet then
    draws it with the box in place of the bullet. No space follows the box,
    because justification would stretch it differently on every line; the
    stylesheet gives the box a fixed width instead.
    """

    def wrap(match: re.Match[str]) -> str:
        items = _LI_RE.findall(match.group(0))
        if items and all(_TASK_ITEM_RE.fullmatch(item) for item in items):
            return f'<div class="checklist">{match.group(0)}</div>'
        return match.group(0)

    def repl(match: re.Match[str]) -> str:
        glyph = "☒" if match.group(1) else "☐"
        return f'<li><span class="task-box">{glyph}</span>'

    return _TASK_ITEM_RE.sub(repl, _INNER_UL_RE.sub(wrap, html))


BOOK_OMIT_MARKER = "<!-- book: omit -->"
# A list item holding the marker, and no other list item.
_OMITTED_LI_RE = re.compile(
    r"<li\b[^>]*>(?:(?!</?li\b).)*?"
    + re.escape(BOOK_OMIT_MARKER)
    + r"(?:(?!</?li\b).)*?</li>\s*",
    re.S,
)


def omit_from_book(html: str) -> str:
    """Drop each list item that carries `BOOK_OMIT_MARKER`.

    The marker is an HTML comment in the Markdown source, so GitHub and the
    rendered page show the item and only the book leaves it out: an entry
    pointing at something the book does not contain, such as a file outside
    the handbook tree.

    Raises:
        ValueError: The marker stands anywhere but inside a list item that
            holds no other one, where this cannot drop exactly what it marks.
    """
    kept = _OMITTED_LI_RE.sub("", html)
    if BOOK_OMIT_MARKER in kept:
        raise ValueError(f"{BOOK_OMIT_MARKER} outside a list item it can omit")
    return kept


def retitle_part(html: str, title: str) -> str:
    """Replace the text of ``html``'s first ``<h1>`` with ``title``, keeping its id.

    Raises:
        ValueError: ``html`` has no ``<h1>``.
    """
    retitled, count = _H1_RE.subn(
        lambda m: m.group(1) + html_escape(title) + m.group(2), html, count=1
    )
    if not count:
        raise ValueError(f"no <h1> to retitle as {title!r}")
    return retitled


def book_html(
    assembled: list[AssembledPart], figures: dict[str, dict[int, str]]
) -> str:
    """Join the parts into one document, with each diagram as its figure.

    A part named in `BOOK_PART_TITLES` gets its chapter title from there.

    Args:
        assembled: The parts, as `assemble` returns them.
        figures: Each diagram's figure markup, by part stem and block index.

    Raises:
        ValueError: A placeholder has no figure in `figures`.
    """
    bodies = []
    for part in assembled:
        markup = figures.get(part.stem, {})

        def repl(match, markup=markup, stem=part.stem):
            index = int(match.group(1))
            if index not in markup:
                raise ValueError(f"{stem}.md: no diagram block for placeholder {index}")
            return markup[index]

        html = _DIAGRAM_PLACEHOLDER_RE.sub(repl, part.html)
        if part.stem in BOOK_PART_TITLES:
            html = retitle_part(html, BOOK_PART_TITLES[part.stem])
        bodies.append(restore_task_boxes(omit_from_book(html)))
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
    code blocks reach pandoc, and the EPUB, exactly as written. In the text
    that is curled, a straight double quote opens (``\u201c``) when the
    character before it is missing, whitespace, or an
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


_PART_NUMBER_RE = re.compile(r"\b(Parts?) (?=\d)")


def glue_part_numbers(html: str) -> str:
    """Join "Part" and its number with a no-break space, outside code.

    Running text names a part as ``Part 4`` or ``Parts 2, 3 and 6``, and a
    justified line may otherwise break between the word and the number. Only
    text is rewritten, never a tag, so heading ids and link targets are the
    page's as before; text inside ``<code>`` or ``<pre>`` is left as written.
    """
    out: list[str] = []
    skip_depth = 0
    for token in _QUOTE_TOKEN_RE.findall(html):
        if token.startswith("<"):
            name_match = _QUOTE_TAG_NAME_RE.match(token)
            if name_match and name_match.group(1).lower() in _QUOTE_SKIP_TAGS:
                if token.startswith("</"):
                    skip_depth = max(0, skip_depth - 1)
                elif not token.rstrip().endswith("/>"):
                    skip_depth += 1
            out.append(token)
        elif skip_depth:
            out.append(token)
        else:
            out.append(_PART_NUMBER_RE.sub("\\1\u00a0", token))
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
        # Pandoc otherwise heads the contents page with the book's title.
        "toc-title": "Contents",
    }
    lines = [f"{key}: {value!r}" for key, value in fields.items()]
    return "---\n" + "\n".join(lines) + "\n---\n"


def epub_command(
    html_path: Path,
    metadata_path: Path,
    css_path: Path,
    out: Path,
    resource_path: Path,
    fonts: tuple[Path, ...] = (),
) -> list[str]:
    """The pandoc argv that turns the book document into an EPUB3.

    Reads plain ``html``, not ``html+smart``: `curl_quotes` already curled
    the book document's prose quotes before it reached this command, and
    ``+smart`` would also rewrite ``--`` inside an inline ``<code>`` span
    (see `curl_quotes`), which no step in this pipeline should ever do.
    ``--resource-path`` is where pandoc resolves each figure's
    ``media/<stem>-<index>.svg`` from. Each of ``fonts`` is embedded with
    ``--epub-embed-font``, which `build_epub` fills from `EPUB_FACES`.
    """
    embed = [arg for font in fonts for arg in ("--epub-embed-font", str(font))]
    return [
        "pandoc",
        "-f", "html",
        "-t", "epub3",
        "--split-level=1",
        "--toc",
        "--toc-depth=1",
        "--metadata-file", str(metadata_path),
        "--css", str(css_path),
        "--resource-path", str(resource_path),
        *embed,
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


def figure_path(figures_dir: Path, stem: str, index: int) -> Path:
    """Where a diagram's seed or hand-corrected figure lives on disk."""
    return figures_dir / f"{stem}-{index}.svg"


def seed_svg(stem: str, block: DiagramBlock) -> str:
    """Render one diagram block into the SVG an illustrator opens next.

    A d2 block goes through the d2 CLI at the print variant, transparent and
    salted so its ids are stable; a funnel is drawn directly, top to bottom,
    for the same print measure. Either way the raw render is cleaned
    (`clean_seed_svg`) and stamped with the fence body's hash
    (`stamp_hash`/`source_hash`), so a later run can tell a hand-corrected
    figure from one still matching its source.

    Raises:
        ValueError: `block.kind` is neither `d2` nor `funnel`.
    """
    figure_id = f"{stem}-{block.index}"
    if block.kind == "d2":
        raw = run_d2(block.source, figure_id, "print")
    elif block.kind == "funnel":
        raw = funnel_svg_vertical(parse_funnel(block.source, stem))
    else:
        raise ValueError(f"{stem}.md: unrecognized diagram kind {block.kind!r}")
    return stamp_hash(clean_seed_svg(raw, figure_id), source_hash(block.source))


def part_blocks(
    docs_dir: Path, parts: list[tuple[str, str, str]] = PARTS
) -> list[tuple[str, DiagramBlock]]:
    """Every diagram block in `parts`, paired with its part's stem.

    Reads each part's Markdown and calls `extract_diagram_blocks` directly,
    so seeding needs no Markdown-to-HTML conversion and no `markdown`
    dependency.
    """
    pairs: list[tuple[str, DiagramBlock]] = []
    for _, stem, _ in parts:
        md = (docs_dir / f"{stem}.md").read_text()
        _, blocks = extract_diagram_blocks(md, stem)
        pairs.extend((stem, block) for block in blocks)
    return pairs


def seed_figures(
    docs_dir: Path, figures_dir: Path, parts: list[tuple[str, str, str]] = PARTS
) -> list[Path]:
    """Write a starting SVG for every diagram in `parts` that has none yet.

    Creates `figures_dir` if it does not exist. A figure already on disk is
    left untouched, hand-corrected or not, so this is safe to re-run after a
    maintainer has edited a seed.

    Returns:
        The paths written, in part order.
    """
    figures_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for stem, block in part_blocks(docs_dir, parts):
        path = figure_path(figures_dir, stem, block.index)
        if path.exists():
            continue
        path.write_text(seed_svg(stem, block), encoding="utf-8")
        written.append(path)
    return written


def write_figures(
    assembled: list[AssembledPart], figures_dir: Path, media: Path
) -> tuple[dict[str, dict[int, str]], list[str]]:
    """Write each diagram's EPUB copy into `media` and build its figure markup.

    Each figure comes from `load_figure`; its copy, transparent like the
    committed file and carrying the faces its text uses (`embed_fonts`), is
    written as ``media/<stem>-<index>.svg``. For every fence with no
    committed figure, one line goes to stderr, exactly
    ``NOTE: <stem>-<index> has no committed figure; the book uses its seed``,
    which the release workflow (#192) turns into a failure.

    Returns:
        Each diagram's `figure_markup`, by part stem and block index, and the
        ``<stem>-<index>`` of every fence that used its seed, in part order.
    """
    figures: dict[str, dict[int, str]] = {}
    seeded_ids: list[str] = []
    for part in assembled:
        for block in part.blocks:
            figure_id = f"{part.stem}-{block.index}"
            svg, seeded = load_figure(figures_dir, part.stem, block)
            if seeded:
                seeded_ids.append(figure_id)
                print(
                    f"NOTE: {figure_id} has no committed figure; "
                    "the book uses its seed",
                    file=sys.stderr,
                )
            (media / f"{figure_id}.svg").write_text(
                embed_fonts(svg, FONT_DIR),
                encoding="utf-8",
            )
            figures.setdefault(part.stem, {})[block.index] = figure_markup(
                part.stem, block, epub_width_em(svg)
            )
    return figures, seeded_ids


def build_epub(
    docs_dir: Path,
    out: Path,
    date: str,
    parts: list[tuple[str, str, str]] = PARTS,
    figures_dir: Path | None = None,
) -> Path:
    """Write the EPUB for ``docs_dir`` to ``out`` and return ``out``.

    Renders every part once with `render_parts` and shares that one render
    across `require_h1_first`, `first_heading_ids` and `assemble`, rather
    than each converting every part's Markdown on its own.

    Each diagram's figure is read from `figures_dir` (default
    ``docs_dir / "figures"``) by `write_figures`, which falls back to its
    seed with a NOTE on stderr and writes its EPUB copy, transparent and
    carrying the faces its text uses, to the work directory's
    ``media/``, where pandoc resolves it from.
    """
    if figures_dir is None:
        figures_dir = docs_dir / "figures"
    rendered = render_parts(docs_dir, parts)
    require_h1_first(rendered, parts)
    linkmap = book_linkmap(parts, first_heading_ids(rendered, parts))
    assembled = assemble(docs_dir, parts, linkmap, rendered=rendered)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        media = work / "media"
        media.mkdir()
        figures, _ = write_figures(assembled, figures_dir, media)
        html = glue_part_numbers(curl_quotes(book_html(assembled, figures)))
        (work / "book.html").write_text(html, encoding="utf-8")
        (work / "metadata.yaml").write_text(book_metadata(date), encoding="utf-8")
        (work / "epub.css").write_text(EPUB_CSS, encoding="utf-8")
        cmd = epub_command(
            work / "book.html",
            work / "metadata.yaml",
            work / "epub.css",
            out,
            work,
            fonts=tuple(FONTS_ROOT / path for *_, path in EPUB_FACES),
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
    parser.add_argument("--format", choices=["epub"])
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
    parser.add_argument(
        "--seed-figures",
        action="store_true",
        help="Write a starting SVG for every diagram that has none yet, "
        "under --figures-dir, and exit.",
    )
    parser.add_argument(
        "--figures-dir",
        type=Path,
        default=None,
        help="Directory holding each diagram's figure: --seed-figures writes "
        "missing ones there and --format epub reads them from there "
        "(default: <docs-dir>/figures).",
    )
    args = parser.parse_args(argv)
    if bool(args.format) == bool(args.seed_figures):
        parser.error("exactly one of --format and --seed-figures is required")
    figures_dir = args.figures_dir or args.docs_dir / "figures"
    if args.seed_figures:
        written = seed_figures(args.docs_dir, figures_dir)
        if written:
            for path in written:
                print(f"wrote {path}")
        else:
            print("every diagram already has a figure")
        return 0
    out = args.out or repo_root / "build" / "handbook.epub"
    build_epub(args.docs_dir, out, _build_date(), figures_dir=figures_dir)
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
