# /// script
# requires-python = ">=3.11"
# dependencies = ["markdown>=3.5"]
# ///
"""Render the engineering handbook into a single self-contained HTML artifact.

The prose is produced verbatim by a Markdown converter over
``docs/engineering/*.md``, so the HTML text is identical to the repo; only
cross-links (``foo.md`` -> ``#anchor``), table / task-list markup, and ```d2
fences are transformed, and the result is wrapped in a styled, single-page
shell (sidebar nav, light/dark theme toggle, scroll-spy). Re-run after editing
any doc to regenerate the shareable artifact; there is no hand-maintained copy
to drift.

Requires the `d2` CLI on PATH (``brew install d2``): every ```d2 fence is
rendered twice, once per theme palette, and inlined as SVG so the artifact
stays self-contained under a strict CSP.

Usage::

    # standalone (uv fetches `markdown` from the inline dependency header)
    uv run scripts/render_handbook_artifact.py
    uv run scripts/render_handbook_artifact.py --out /tmp/handbook.html
    uv run scripts/render_handbook_artifact.py --docs-dir docs/engineering --out build/handbook.html

The output is a fragment (``<title> + <style> + <body> markup + <script>``)
suitable for publishing as a Claude artifact, and it also renders as a complete
page when opened directly in a browser.

NOT a CI test. The pure transforms (``rewrite_links``, ``wrap_tables``,
``mark_task_items``, ``extract_d2_blocks``, ``prepare_svg``, ``diagram_figure``,
``substitute_d2``, ``count_em_dashes``) are unit-tested in ``tests/scripts/``.
``run_d2`` shells out to the CLI and is deliberately left to the manual render.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from dataclasses import dataclass
from functools import cache
from html import escape as html_escape
from pathlib import Path

# (anchor id, markdown stem, sidebar label). Order defines the page order;
# README is the intro section (#top), the nine parts follow, then the
# troubleshooting companion and the coda close.
PARTS: list[tuple[str, str, str]] = [
    ("top", "README", "Overview &amp; the story"),
    ("p1", "lifecycle", "Development lifecycle"),
    ("p2", "implementation-disciplines", "Implementation disciplines"),
    ("p3", "codebase-structure", "Codebase structure"),
    ("p4", "three-layer-model", "Three-layer model"),
    ("p5", "agent-harness", "The agent harness"),
    ("p6", "observability", "Observability"),
    ("p7", "evaluation", "Evaluation"),
    ("p8", "documentation", "Documentation"),
    ("p9", "security-supply-chain", "Security &amp; supply chain"),
    ("troubleshooting", "troubleshooting", "Troubleshooting"),
    ("coda", "coda", "Coda"),
]

# `<stem>.md` -> in-page anchor, used to turn repo cross-links into scroll links.
LINKMAP: dict[str, str] = {stem + ".md": "#" + anchor for anchor, stem, _ in PARTS}

# ELK rather than d2's default dagre, for one reason: dagre exposes no
# rank-separation knob (only `--dagre-nodesep`, which is horizontal), and its
# default vertical gap made every multi-step diagram taller than a laptop
# viewport, forcing the reader to scroll a figure that is meant to be taken in
# at a glance. ELK's `nodeNodeBetweenLayers` is exactly that knob: dropping it
# from 70 to 15 cuts the tallest diagram roughly in half with no loss of
# legibility, because the boxes were never the problem, the air between the
# ranks was.
_D2_LAYOUT_ARGS = [
    "--layout", "elk",
    "--elk-nodeNodeBetweenLayers", "15",
    "--elk-edgeNodeBetweenLayers", "15",
    "--elk-padding", "[top=20,left=20,bottom=20,right=20]",
]  # fmt: skip

# d2 defaults to 16px labels, which sets the minimum box size and so drives the
# whole diagram's footprint. 12px reads as figure furniture next to the body
# serif instead of competing with it, and shrinks every box in both axes.
_D2_FONT_SIZE = "**.style.font-size: 12\n"

# A person outline for marking a step a human owns, plus an empty icon of the
# same footprint. Both are generated rather than committed as assets: the
# stroke has to follow the theme, and d2 inlines the file as a base64 data URI,
# so nothing external survives into the artifact anyway.
#
# The blank one exists because d2 adds a fixed 21px of icon gutter to any node
# carrying an icon, and offers no way to opt out or to compensate (a height set
# on the node or on the class is ignored). Marking two nodes in a row of eight
# therefore leaves those two visibly taller than their neighbours. Giving every
# node an icon, blank for all but the marked ones, puts each of them in the
# same box. Diagrams that never reference these classes are unaffected.
_D2_ICON_PERSON = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"'
    ' viewBox="0 0 24 24" fill="none" stroke="{stroke}" stroke-width="2.2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="7.5" r="3.6"/>'
    '<path d="M5 20a7 7 0 0 1 14 0"/></svg>'
)
_D2_ICON_BLANK = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"'
    ' viewBox="0 0 24 24"></svg>'
)
_D2_ICON_STROKE = {"light": "#6f4c12", "dark": "#d9a441"}
# Held for the process lifetime so the files outlive every d2 call; its
# finalizer removes the directory at interpreter exit.
_D2_ICON_TMPDIR: tempfile.TemporaryDirectory[str] | None = None

# The handbook's own palette, prepended to every diagram's source so the
# rendered SVG uses the same hex values as the artifact's CSS variables and the
# diagrams read as page furniture rather than as pictures from another system.
# Two variants rather than d2's own `--dark-theme`, because that follows the
# `prefers-color-scheme` query alone and the page carries a manual theme button.
D2_PRELUDES: dict[str, str] = {
    "light": (
        "style.fill: transparent\n" + _D2_FONT_SIZE + '**.style.fill: "#f7f6f2"\n'
        '**.style.stroke: "#c3bfb1"\n'
        '**.style.font-color: "#1c2024"\n'
        "**.style.shadow: false\n"
        '(** -> **)[*].style.stroke: "#9a6a1c"\n'
        '(** -> **)[*].style.font-color: "#4b5057"\n'
    ),
    "dark": (
        "style.fill: transparent\n" + _D2_FONT_SIZE + '**.style.fill: "#1e2126"\n'
        '**.style.stroke: "#3a4048"\n'
        '**.style.font-color: "#e9e7df"\n'
        "**.style.shadow: false\n"
        '(** -> **)[*].style.stroke: "#d9a441"\n'
        '(** -> **)[*].style.font-color: "#adaaa0"\n'
    ),
}

# The body admits no line of its own that opens with a fence, so an unclosed
# ```d2 block fails to match instead of swallowing the prose and headings that
# follow it up to the next stray ``` line. `extract_d2_blocks` then turns that
# non-match into a loud error rather than a page with content silently missing.
_D2_FENCE_RE = re.compile(
    r"^```d2(?P<meta>[^\n]*)\n(?P<body>(?:(?!```)[^\n]*\n)*)^```[ \t]*$", re.MULTILINE
)
# Anchored to the whole meta, so `title="Foo \"Bar\""` fails to match and is
# reported as a missing title, rather than being truncated to a wrong caption.
_D2_TITLE_RE = re.compile(r'^\s*title="([^"]+)"\s*$')
_D2_PLACEHOLDER_RE = re.compile(r'<div class="d2ph" data-i="(\d+)"></div>')
# Seven small diagrams render in well under a second; a bound this loose only
# ever fires on a d2 that has genuinely wedged.
_D2_TIMEOUT_S = 60
_SVG_OPEN_RE = re.compile(r"<svg\b[^>]*>")
_VIEWBOX_RE = re.compile(r'viewBox="[-\d.]+ [-\d.]+ ([\d.]+) ([\d.]+)"')


@dataclass(frozen=True)
class D2Block:
    """One ```d2 fence lifted out of a handbook page."""

    index: int
    title: str
    source: str


def extract_d2_blocks(md: str, stem: str) -> tuple[str, list[D2Block]]:
    """Replace every ```d2 fence with a placeholder and return the blocks.

    Fences are lifted out of the Markdown *before* the converter runs, so the
    rendered SVG never has to be recovered from an entity-escaped `<pre><code>`
    block. python-markdown passes a block-level `<div>` through untouched.

    Args:
        md: The page's Markdown source.
        stem: The page's filename stem, used in error messages and ids.

    Returns:
        The Markdown with each fence replaced by its placeholder, and the
        extracted blocks in document order.

    Raises:
        ValueError: A fence carries no `title="..."`, or a `d2` fence was left
            unrecognised (unclosed, indented, or containing a fence of its own).
    """
    blocks: list[D2Block] = []

    def repl(match: re.Match[str]) -> str:
        title = _D2_TITLE_RE.match(match.group("meta"))
        if title is None:
            raise ValueError(
                f'{stem}.md: a ```d2 fence has no title="..."; the title becomes '
                "the figure caption and the diagram's accessible name, so an "
                "untitled diagram would ship unlabeled."
            )
        index = len(blocks)
        blocks.append(
            D2Block(index=index, title=title.group(1), source=match.group("body"))
        )
        return f'<div class="d2ph" data-i="{index}"></div>'

    out = _D2_FENCE_RE.sub(repl, md)
    if "```d2" in out:
        raise ValueError(
            f"{stem}.md: a ```d2 fence was left unrecognised. A fence must begin "
            "at column 0, must carry a closing ``` line, and must contain no ``` "
            "line of its own. Left alone it would render as a literal code block "
            "and the diagram would go missing without any gate noticing."
        )
    return out, blocks


@cache
def d2_icon_classes(variant: str) -> str:
    """Write this theme's icon files and declare the classes that use them.

    Diagrams reference these by name, `{class: human}` for a step a human owns
    and `*.class: step` for the rest, so no diagram source has to carry a
    filesystem path.

    Args:
        variant: Which palette the icon stroke should match, `light` or `dark`.

    Returns:
        A d2 `classes` block declaring `human` and `step`.
    """
    global _D2_ICON_TMPDIR
    if _D2_ICON_TMPDIR is None:
        _D2_ICON_TMPDIR = tempfile.TemporaryDirectory(prefix="handbook-d2-icons-")
    directory = Path(_D2_ICON_TMPDIR.name)
    blank = directory / "blank.svg"
    blank.write_text(_D2_ICON_BLANK)
    person = directory / f"person-{variant}.svg"
    person.write_text(_D2_ICON_PERSON.format(stroke=_D2_ICON_STROKE[variant]))
    return (
        f"classes: {{\n  step: {{ icon: {blank} }}\n  human: {{ icon: {person} }}\n}}\n"
    )


def run_d2(source: str, salt: str, variant: str) -> str:
    """Render one diagram to SVG with the `d2` CLI.

    Args:
        source: The fence body.
        salt: Appended to every generated SVG element id, so two variants of one
            diagram (or two identical diagrams) cannot collide on one page.
        variant: Which palette prelude to prepend, `light` or `dark`.

    Returns:
        The SVG markup, with no XML prolog.

    Raises:
        SystemExit: The `d2` CLI is absent, hung, or rejected the source.
    """
    command = [
        "d2",
        "--stdout-format", "svg",
        "--no-xml-tag",
        "--theme", "0",
        *_D2_LAYOUT_ARGS,
        "--pad", "10",
        "--salt", salt,
        "-", "-",
    ]  # fmt: skip
    try:
        proc = subprocess.run(
            command,
            input=D2_PRELUDES[variant] + d2_icon_classes(variant) + source,
            capture_output=True,
            text=True,
            check=False,
            timeout=_D2_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(
            f"d2 did not finish within {_D2_TIMEOUT_S}s on diagram {salt!r}. "
            "Bounding this call is the same rule Part 5 of the handbook "
            "prescribes for every external call, applied to the handbook's own "
            "build: an unbounded one would hang the render with no diagnosis."
        ) from exc
    except FileNotFoundError as exc:
        raise SystemExit(
            "d2 CLI not found on PATH. The handbook renderer turns ```d2 fences "
            "into inline SVG and cannot produce the artifact without it. Install "
            "it with `brew install d2`, or take a binary from "
            "https://github.com/terrastruct/d2/releases."
        ) from exc
    if proc.returncode != 0:
        raise SystemExit(
            f"d2 failed on diagram {salt!r} (exit {proc.returncode}):\n"
            f"{proc.stderr.strip()}"
        )
    return proc.stdout


def prepare_svg(svg: str, caption_id: str) -> str:
    """Make one d2 SVG embeddable: give it an intrinsic size and a name.

    d2 puts only a `viewBox` on the outer element, but `max-width: 100%;
    height: auto` needs an intrinsic size to scale against, so the viewBox's
    dimensions are copied onto the tag as `width`/`height`.

    Args:
        svg: Raw d2 output.
        caption_id: The `id` of the `<figcaption>` that names this diagram.

    Returns:
        The SVG with `width`, `height`, `role`, and `aria-labelledby` added.

    Raises:
        ValueError: The output has no `<svg>` element, or none with a viewBox.
    """
    opening = _SVG_OPEN_RE.search(svg)
    if opening is None:
        raise ValueError("d2 produced output with no <svg> element")
    tag = opening.group(0)
    viewbox = _VIEWBOX_RE.search(tag)
    if viewbox is None:
        raise ValueError("the outer <svg> element has no viewBox to size from")
    sized = (
        f'{tag[:-1]} width="{viewbox.group(1)}" height="{viewbox.group(2)}"'
        f' role="img" aria-labelledby="{caption_id}">'
    )
    return svg[: opening.start()] + sized + svg[opening.end() :]


def diagram_figure(stem: str, block: D2Block, light: str, dark: str) -> str:
    """Wrap both rendered variants and their caption in one `<figure>`.

    The title is escaped on the way in: `to_ascii_entities` later rewrites only
    non-ASCII characters, so an unescaped `&` or `<` in a caption would reach
    the browser intact and corrupt the markup after it.
    """
    caption_id = f"dcap-{stem}-{block.index}"
    return (
        '<figure class="diagram">'
        f'<span class="d2var d2-light">{prepare_svg(light, caption_id)}</span>'
        f'<span class="d2var d2-dark">{prepare_svg(dark, caption_id)}</span>'
        f'<figcaption id="{caption_id}">{html_escape(block.title)}</figcaption>'
        "</figure>"
    )


def substitute_d2(html: str, figures: dict[int, str]) -> str:
    """Replace each d2 placeholder with its rendered figure.

    Raises:
        ValueError: A placeholder has no matching figure.
    """

    def repl(match: re.Match[str]) -> str:
        index = int(match.group(1))
        if index not in figures:
            raise ValueError(f"no rendered figure for d2 placeholder {index}")
        return figures[index]

    return _D2_PLACEHOLDER_RE.sub(repl, html)


def count_em_dashes(html: str) -> int:
    """Count em-dashes in both the literal and the numeric-entity form.

    `to_ascii_entities` runs before this counter and has already rewritten the
    literal character to `&#8212;`, so counting only the character reported zero
    whatever the sources held, which made the handbook's em-dash gate vacuous.
    """
    return html.count("—") + html.count("&#8212;")


def rewrite_links(html: str, linkmap: dict[str, str]) -> tuple[str, list[str]]:
    """Rewrite ``*.md`` hrefs to in-page anchors.

    Returns the rewritten HTML and the list of hrefs that could not be mapped
    (external links, or docs outside the handbook), so the caller can warn.
    """
    unmapped: list[str] = []

    def repl(m: re.Match[str]) -> str:
        href = m.group(1)
        base = href.split("#")[0]
        anchor = linkmap.get(base)
        if anchor is not None:
            return f'href="{anchor}"'
        unmapped.append(href)
        return m.group(0)

    out = re.sub(r'href="([^"]+\.md[^"]*)"', repl, html)
    return out, unmapped


def wrap_tables(html: str) -> str:
    """Wrap every ``<table>`` in an overflow container so wide tables scroll."""
    return html.replace("<table>", '<div class="tablewrap"><table>').replace(
        "</table>", "</table></div>"
    )


def mark_task_items(html: str) -> str:
    """Turn GitHub-style task-list items into styled checkbox rows.

    ``<li>[ ] text`` -> ``<li class="task">text`` and ``<li>[x] text`` ->
    ``<li class="task done">text``. The item text itself is left untouched.
    """
    html = re.sub(r"<li>\s*\[ \]\s*", '<li class="task">', html)
    html = re.sub(r"<li>\s*\[[xX]\]\s*", '<li class="task done">', html)
    return html


def post_process(html: str, linkmap: dict[str, str]) -> tuple[str, list[str]]:
    """Apply all HTML transforms; return the result and any unmapped hrefs."""
    html, unmapped = rewrite_links(html, linkmap)
    html = wrap_tables(html)
    html = mark_task_items(html)
    return html, unmapped


def render_doc(
    docs_dir: Path, stem: str, linkmap: dict[str, str]
) -> tuple[str, list[str]]:
    """Convert one markdown doc to post-processed HTML (lazy-imports markdown)."""
    import markdown  # lazy: keeps the pure helpers importable without the dep

    md = (docs_dir / f"{stem}.md").read_text()
    md, blocks = extract_d2_blocks(md, stem)
    html = markdown.markdown(md, extensions=["tables", "fenced_code", "sane_lists"])
    html, unmapped = post_process(html, linkmap)
    if blocks:
        html = substitute_d2(
            html,
            {
                block.index: diagram_figure(
                    stem,
                    block,
                    run_d2(block.source, f"{stem}-{block.index}-light", "light"),
                    run_d2(block.source, f"{stem}-{block.index}-dark", "dark"),
                )
                for block in blocks
            },
        )
    return html, unmapped


def render_nav(parts: list[tuple[str, str, str]]) -> str:
    """Build the sidebar table-of-contents markup."""
    rows = []
    for i, (anchor, _, label) in enumerate(parts):
        lead = ' class="lead"' if anchor == "top" else ""
        num = (
            "§"
            if anchor == "top"
            else "∎"
            if anchor == "coda"
            else "✚"
            if anchor == "troubleshooting"
            else f"{i:02d}"
        )
        rows.append(
            f'      <a href="#{anchor}"{lead}><span class="num">{num}</span>'
            f"<span>{label}</span></a>"
        )
    return "\n".join(rows)


def to_ascii_entities(html: str) -> str:
    """Escape every non-ASCII character to a numeric HTML entity.

    The artifact host serves the page from a wrapper whose ``<head>`` we do not
    control, so we cannot declare ``<meta charset="utf-8">``. Raw UTF-8 bytes
    then mojibake under a Latin-1 interpretation (``·`` -> ``Â·``). Numeric
    entities are pure ASCII and render as the same glyph under any charset.
    """
    return html.encode("ascii", "xmlcharrefreplace").decode("ascii")


def build(docs_dir: Path, parts: list[tuple[str, str, str]] = PARTS) -> str:
    """Render the full handbook artifact HTML from ``docs_dir``."""
    linkmap = {stem + ".md": "#" + anchor for anchor, stem, _ in parts}
    sections = []
    for anchor, stem, _ in parts:
        cls = "part intro" if anchor == "top" else "part"
        html, unmapped = render_doc(docs_dir, stem, linkmap)
        for href in unmapped:
            print(f"  WARNING unmapped link in {stem}.md: {href}")
        sections.append(
            f'    <section id="{anchor}" class="{cls}">\n'
            f'      <div class="col doc">\n{html}\n      </div>\n    </section>'
        )
    body = _BODY % {"nav": render_nav(parts), "sections": "\n".join(sections)}
    return to_ascii_entities(_HEAD + body + _SCRIPT)


def main(argv: list[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=repo_root / "docs" / "engineering",
        help="Directory holding the handbook markdown (default: docs/engineering).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=repo_root / "test-reports" / "handbook.html",
        help="Output HTML path (default: test-reports/handbook.html, gitignored).",
    )
    args = parser.parse_args(argv)

    html = build(args.docs_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html)

    residual = len(re.findall(r'href="[^"]+\.md', html))
    tasks = html.count('class="task')
    diagrams = html.count('<figure class="diagram"')
    print(f"wrote {args.out} ({len(html)} bytes)")
    print(
        f"  sections: {html.count('<section id=')}  "
        f"task items: {tasks}  "
        f"diagrams: {diagrams}  "
        f"em-dashes: {count_em_dashes(html)}  "
        f"residual .md hrefs: {residual}"
    )
    return 0


_HEAD = """<title>AI Agent Development Handbook</title>
<style>
  :root {
    --bg: #edece6; --surface: #f7f6f2; --surface-2: #e6e4db;
    --ink: #1c2024; --ink-soft: #4b5057; --ink-faint: #6d7178;
    --line: #d6d3c8; --line-strong: #c3bfb1;
    --accent: #9a6a1c; --accent-ink: #6f4c12; --accent-wash: #ece2cd;
    --shadow: 0 1px 2px rgba(28,32,36,.05), 0 8px 30px rgba(28,32,36,.06);
    --serif: ui-serif, Georgia, "Iowan Old Style", Palatino, "Book Antiqua", serif;
    --sans: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    --mono: ui-monospace, "SF Mono", "Cascadia Code", Menlo, Consolas, monospace;
    --measure: 72ch;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #16181c; --surface: #1e2126; --surface-2: #23272d;
      --ink: #e9e7df; --ink-soft: #adaaa0; --ink-faint: #85837b;
      --line: #2b3037; --line-strong: #3a4048;
      --accent: #d9a441; --accent-ink: #e7bd6c; --accent-wash: #2a2519;
      --shadow: 0 1px 2px rgba(0,0,0,.3), 0 10px 34px rgba(0,0,0,.34);
    }
  }
  :root[data-theme="light"] {
    --bg: #edece6; --surface: #f7f6f2; --surface-2: #e6e4db;
    --ink: #1c2024; --ink-soft: #4b5057; --ink-faint: #6d7178;
    --line: #d6d3c8; --line-strong: #c3bfb1;
    --accent: #9a6a1c; --accent-ink: #6f4c12; --accent-wash: #ece2cd;
    --shadow: 0 1px 2px rgba(28,32,36,.05), 0 8px 30px rgba(28,32,36,.06);
  }
  :root[data-theme="dark"] {
    --bg: #16181c; --surface: #1e2126; --surface-2: #23272d;
    --ink: #e9e7df; --ink-soft: #adaaa0; --ink-faint: #85837b;
    --line: #2b3037; --line-strong: #3a4048;
    --accent: #d9a441; --accent-ink: #e7bd6c; --accent-wash: #2a2519;
    --shadow: 0 1px 2px rgba(0,0,0,.3), 0 10px 34px rgba(0,0,0,.34);
  }

  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  @media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }
  body {
    margin: 0; background: var(--bg); color: var(--ink);
    font-family: var(--sans); font-size: 17px; line-height: 1.62;
    -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility;
  }

  .wrap { display: grid; grid-template-columns: 260px minmax(0,1fr); max-width: 1200px; margin: 0 auto; }

  .rail {
    position: sticky; top: 0; align-self: start; height: 100vh;
    padding: 34px 26px 34px 32px; border-right: 1px solid var(--line);
    display: flex; flex-direction: column; gap: 22px; overflow-y: auto;
  }
  .brand { display: flex; flex-direction: column; gap: 6px; }
  .brand .mark { font-family: var(--mono); font-size: .68rem; letter-spacing: .22em; text-transform: uppercase; color: var(--accent); }
  .brand .name { font-family: var(--serif); font-size: 1.32rem; line-height: 1.12; letter-spacing: -.01em; }
  nav.toc { display: flex; flex-direction: column; gap: 2px; }
  nav.toc a {
    display: grid; grid-template-columns: 22px 1fr; gap: 10px; align-items: baseline;
    padding: 7px 8px; border-radius: 6px; text-decoration: none; color: var(--ink-soft);
    font-size: .875rem; border: 1px solid transparent; transition: background .18s ease, color .18s ease;
  }
  nav.toc a .num { font-family: var(--mono); font-size: .72rem; color: var(--ink-faint); font-variant-numeric: tabular-nums; }
  nav.toc a:hover { background: var(--surface-2); color: var(--ink); }
  nav.toc a.active { background: var(--accent-wash); color: var(--ink); border-color: var(--line-strong); }
  nav.toc a.active .num { color: var(--accent); }
  nav.toc a.lead { color: var(--ink); font-weight: 600; }
  nav.toc a.lead .num { color: var(--accent); }

  .railfoot { margin-top: auto; display: flex; flex-direction: column; gap: 14px; }
  .toggle {
    display: inline-flex; align-items: center; gap: 8px; background: var(--surface); color: var(--ink);
    border: 1px solid var(--line-strong); border-radius: 999px; padding: 7px 13px;
    font-family: var(--mono); font-size: .72rem; letter-spacing: .06em; cursor: pointer; width: max-content;
  }
  .toggle:hover { border-color: var(--accent); color: var(--accent-ink); }
  .toggle:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .railfoot .fine { font-family: var(--mono); font-size: .68rem; color: var(--ink-faint); line-height: 1.5; }

  main { padding: 40px clamp(24px,5vw,76px) 96px; min-width: 0; }
  .col { max-width: var(--measure); }
  section.part { padding-top: 40px; scroll-margin-top: 20px; }
  section.part.intro { padding-top: 16px; }

  /* rendered-markdown content */
  .doc h1 {
    font-family: var(--serif); font-weight: 600; font-size: clamp(1.9rem,3.6vw,2.4rem);
    line-height: 1.08; letter-spacing: -.015em; text-wrap: balance;
    margin: 0 0 6px; padding-bottom: 12px; border-bottom: 2px solid var(--accent); display: inline-block;
  }
  .intro .doc h1 { font-size: clamp(2.4rem,6vw,3.6rem); border-bottom: none; padding-bottom: 0; letter-spacing: -.02em; }
  .doc h2 { font-family: var(--serif); font-weight: 600; font-size: 1.42rem; line-height: 1.15; letter-spacing: -.01em; text-wrap: balance; margin: 36px 0 6px; }
  .doc h3 { font-family: var(--sans); font-weight: 700; font-size: 1.04rem; letter-spacing: .005em; margin: 28px 0 4px; }
  .doc p { margin: 14px 0; }
  .doc b, .doc strong { color: var(--ink); font-weight: 650; }
  .doc em, .doc i { color: inherit; }
  .doc a { color: var(--accent-ink); text-decoration: none; border-bottom: 1px solid var(--line-strong); }
  .doc a:hover { border-color: var(--accent); }
  .doc ul, .doc ol { margin: 14px 0; padding-left: 24px; }
  .doc li { position: relative; margin: 6px 0; }
  .doc li::marker { color: var(--accent); }
  .doc code { font-family: var(--mono); font-size: .84em; background: var(--surface-2); padding: 1px 5px; border-radius: 3px; color: var(--accent-ink); }
  .doc pre { background: var(--surface); border: 1px solid var(--line); border-radius: 4px; padding: 14px 16px; overflow-x: auto; margin: 18px 0; }
  .doc pre code { background: none; padding: 0; color: var(--ink-soft); font-size: .86rem; }
  .doc blockquote { margin: 20px 0; padding: 12px 18px; border-left: 3px solid var(--accent); background: var(--surface); border-radius: 4px; color: var(--ink-soft); }
  .doc blockquote > :first-child { margin-top: 0; }
  .doc blockquote > :last-child { margin-bottom: 0; }

  .tablewrap { overflow-x: auto; margin: 20px 0; border: 1px solid var(--line); border-radius: 4px; }
  table { border-collapse: collapse; width: 100%; font-size: .92rem; background: var(--surface); }
  th, td { text-align: left; padding: 10px 14px; vertical-align: top; border-bottom: 1px solid var(--line); }
  thead th { font-family: var(--mono); font-size: .68rem; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-faint); background: var(--surface-2); font-weight: 600; }
  tbody tr:last-child td { border-bottom: none; }
  td code { white-space: nowrap; }

  /* task-list checklists */
  .doc li.task { list-style: none; padding-left: 4px; }
  .doc li.task::before {
    content: ""; position: absolute; left: -20px; top: .32em; width: 14px; height: 14px;
    border: 1px solid var(--line-strong); border-radius: 3px; background: var(--surface-2);
  }
  .doc li.task.done::before { content: "\\2713"; color: var(--accent); font-size: .7rem; line-height: 13px; text-align: center; }

  /* d2 diagrams: two rendered variants, toggled with the page theme.
     Diagrams are authored to fit the prose measure at their natural size, so
     that `max-width: 100%` never has to scale one down: scaling shrinks the
     labels with it, and a diagram whose text has gone small is worse than a
     diagram that is merely narrow. */
  .doc figure.diagram { margin: 22px 0; }
  .doc figure.diagram svg { display: block; margin: 0 auto; max-width: 100%; height: auto; }
  .doc figure.diagram figcaption {
    margin-top: 10px; text-align: center; font-family: var(--mono);
    font-size: .7rem; letter-spacing: .07em; text-transform: uppercase; color: var(--ink-faint);
  }
  .d2var { display: block; }
  .d2-dark { display: none; }
  @media (prefers-color-scheme: dark) { .d2-light { display: none; } .d2-dark { display: block; } }
  :root[data-theme="light"] .d2-light { display: block; }
  :root[data-theme="light"] .d2-dark { display: none; }
  :root[data-theme="dark"] .d2-light { display: none; }
  :root[data-theme="dark"] .d2-dark { display: block; }

  footer { max-width: var(--measure); margin: 70px 0 0; padding-top: 24px; border-top: 1px solid var(--line); font-size: .82rem; color: var(--ink-faint); }
  footer code { font-family: var(--mono); background: var(--surface-2); padding: 1px 5px; border-radius: 3px; }

  .fade { opacity: 0; transform: translateY(8px); animation: rise .6s ease forwards; }
  @keyframes rise { to { opacity: 1; transform: none; } }
  @media (prefers-reduced-motion: reduce) { .fade { animation: none; opacity: 1; transform: none; } }

  @media (max-width: 860px) {
    .wrap { grid-template-columns: 1fr; }
    .rail { position: static; height: auto; border-right: none; border-bottom: 1px solid var(--line); }
    nav.toc { flex-direction: row; flex-wrap: wrap; gap: 6px; }
    nav.toc a { grid-template-columns: auto auto; }
    .railfoot { margin-top: 6px; }
    main { padding: 28px 22px 64px; }
  }
</style>
"""

_BODY = """
<div class="wrap">
  <aside class="rail">
    <div class="brand">
      <span class="mark">Lidia · Engineering</span>
      <span class="name">AI Agent Development Handbook</span>
    </div>
    <nav class="toc" id="toc">
%(nav)s
    </nav>
    <div class="railfoot">
      <button class="toggle" id="themeBtn" type="button" aria-label="Toggle colour theme">◐ Theme</button>
      <span class="fine">Verbatim render of <br><code>docs/engineering/</code></span>
    </div>
  </aside>

  <main class="fade">
%(sections)s
    <footer class="col">This page is generated verbatim from the handbook in the repository at <code>docs/engineering/</code>; cross-links are rewritten to in-page anchors. When the two disagree, the repo wins.</footer>
  </main>
</div>
"""

_SCRIPT = """
<script>
  (function () {
    var root = document.documentElement;
    var btn = document.getElementById("themeBtn");
    try { var saved = localStorage.getItem("hwd-theme"); if (saved) root.setAttribute("data-theme", saved); } catch (e) {}
    function current() {
      var attr = root.getAttribute("data-theme");
      if (attr) return attr;
      return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    btn.addEventListener("click", function () {
      var next = current() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("hwd-theme", next); } catch (e) {}
    });
    var links = Array.prototype.slice.call(document.querySelectorAll("nav.toc a"));
    var map = {};
    links.forEach(function (a) { map[a.getAttribute("href").slice(1)] = a; });
    var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    // Intercept EVERY in-page #anchor (sidebar nav, the "parts" table, and the
    // "See also" links inside the rendered docs). Letting the fragment trigger a
    // top-level navigation is what the sandboxed artifact frame rejects (403).
    var anchors = Array.prototype.slice.call(document.querySelectorAll('a[href^="#"]'));
    anchors.forEach(function (a) {
      a.addEventListener("click", function (e) {
        var el = document.getElementById(a.getAttribute("href").slice(1));
        if (el) { e.preventDefault(); el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" }); }
      });
    });
    var targets = Object.keys(map).map(function (id) { return document.getElementById(id); }).filter(Boolean);
    if ("IntersectionObserver" in window) {
      var obs = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (en.isIntersecting) {
            links.forEach(function (l) { l.classList.remove("active"); });
            var a = map[en.target.id];
            if (a) a.classList.add("active");
          }
        });
      }, { rootMargin: "-12% 0px -80% 0px", threshold: 0 });
      targets.forEach(function (t) { obs.observe(t); });
    }
  })();
</script>
"""


if __name__ == "__main__":
    raise SystemExit(main())
