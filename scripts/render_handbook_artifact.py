# /// script
# requires-python = ">=3.11"
# dependencies = ["markdown>=3.5", "pyyaml>=6.0"]
# ///
"""Render the engineering handbook into a single self-contained HTML artifact.

The prose is produced verbatim by a Markdown converter over
``docs/engineering/*.md``, so the HTML text is identical to the repo; only
cross-links (``foo.md`` -> ``#<part anchor>``, ``foo.md#frag`` ->
``#<stem>-<frag>``), heading ids (``<stem>-<slug>`` on every heading, so a
report's citation resolves into the page), table / task-list markup, and
```d2 fences are transformed, and the result is wrapped in a styled,
single-page shell (sidebar nav, light/dark theme toggle, scroll-spy). Re-run after editing
any doc to regenerate the shareable artifact; there is no hand-maintained copy
to drift.

Requires the `d2` CLI on PATH (``brew install d2``): every ```d2 fence is
rendered twice, once per theme palette, and inlined as SVG so the artifact
stays self-contained under a strict CSP.

Usage::

    # standalone (uv fetches `markdown` and `pyyaml` from the inline dependency header)
    uv run scripts/render_handbook_artifact.py
    uv run scripts/render_handbook_artifact.py --out /tmp/handbook.html
    uv run scripts/render_handbook_artifact.py --docs-dir docs/engineering --out build/handbook.html

The output is a fragment (``<title> + <style> + <body> markup + <script>``)
suitable for publishing as a Claude artifact, and it also renders as a complete
page when opened directly in a browser.

Two diagram fences are recognised. A ```d2 fence is laid out by the d2 CLI. A
```funnel fence is drawn here instead, from one `label count` line per stage,
because a staged funnel wants exact label placement and a chosen scale, and no
layout engine offers either. Both render to a light and a dark SVG and are
wrapped in the same ``<figure>``.

NOT a CI test. Everything except ``run_d2`` is unit-tested in
``tests/scripts/``: the pure transforms (``unlink_out_of_tree``,
``heading_id``, ``add_heading_ids``, ``rewrite_links``, ``wrap_tables``,
``heading_ids`` and ``render_part`` through ``build`` and the id-set tests,
``mark_task_items``, ``extract_diagram_blocks``, ``parse_funnel``,
``wrap_label``, ``group_digits``, ``funnel_svg``, ``prepare_svg``,
``diagram_figure``, ``substitute_diagrams``, ``count_em_dashes``), the
per-fence dispatch (``render_variants``), and ``d2_icon_classes``, which
writes files but is deterministic given the theme. ``run_d2`` shells out to
the CLI and is deliberately left to the manual render.
"""

from __future__ import annotations

import argparse
import math
import re
import subprocess
import tempfile
from dataclasses import dataclass
from functools import cache
from html import escape as html_escape
from html import unescape as html_unescape
from itertools import pairwise
from pathlib import Path

from render_handbook_traceability import slugify

# (anchor id, markdown stem, sidebar label). Order defines the page order;
# README is the intro section (#top), the numbered parts follow, then the
# troubleshooting companion and the coda close. Every `*.md` in the handbook
# directory must appear here or it renders out of the page in silence, which
# `test_parts_lists_every_handbook_file_on_disk` catches.
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
    ("p10", "data-protection", "Data protection &amp; privacy"),
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
# from 70 to 22 cuts the tallest diagram roughly in half with no loss of
# legibility, because the boxes were never the problem, the air between the
# ranks was.
#
# 22 rather than tighter because this is also the *whole* length of an edge
# that carries no label, arrowhead included: below about 20 an unlabelled arrow
# collapses to little more than its head. It is the horizontal gap in a
# `direction: right` diagram, so raising it also widens the story arc, which is
# why that one sets a narrower fixed box to stay inside the measure.
_D2_LAYOUT_ARGS = [
    "--layout", "elk",
    "--elk-nodeNodeBetweenLayers", "22",
    "--elk-edgeNodeBetweenLayers", "15",
    "--elk-padding", "[top=20,left=20,bottom=20,right=20]",
]  # fmt: skip

# d2 defaults to 16px labels, which sets the minimum box size and so drives the
# whole diagram's footprint. 12px reads as figure furniture next to the body
# serif instead of competing with it, and shrinks every box in both axes.
#
# Both globs are needed: `**` reaches shapes only, so setting it alone left
# every connection label at the 16px default, visibly larger than the boxes it
# ran between and wide enough to cover the short arrows it sat on.
_D2_FONT_SIZE = "**.style.font-size: 12\n(** -> **)[*].style.font-size: 12\n"

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
#
# d2 scales whatever it is given into a fixed 37px icon box, so the drawing is
# deliberately small and bottom-weighted inside its 24-unit viewBox rather than
# filling it: the empty upper third is what sets the icon back from the label
# above it, and it is the only way to control either size or spacing, since the
# box d2 draws into cannot be changed.
_D2_ICON_PERSON = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"'
    ' viewBox="0 0 24 24" fill="none" stroke="{stroke}" stroke-width="1.9"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="11.8" r="2.6"/>'
    '<path d="M7.5 21.4a4.5 4.5 0 0 1 9 0"/></svg>'
)
_D2_ICON_BLANK = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"'
    ' viewBox="0 0 24 24"></svg>'
)
# One source for the hex values every rendered figure uses. These mirror the
# artifact's CSS custom properties, and the point of naming them once is that a
# figure cannot drift from the page it sits on: d2's preludes, the person icon,
# and the funnel renderer all read from here.
PALETTE: dict[str, dict[str, str]] = {
    "light": {
        "surface": "#f7f6f2", "line": "#c3bfb1", "ink": "#1c2024",
        "ink_soft": "#4b5057", "accent": "#9a6a1c", "accent_ink": "#6f4c12",
        "accent_wash": "#ece2cd",
    },
    "dark": {
        "surface": "#1e2126", "line": "#3a4048", "ink": "#e9e7df",
        "ink_soft": "#adaaa0", "accent": "#d9a441", "accent_ink": "#e7bd6c",
        "accent_wash": "#2a2519",
    },
}  # fmt: skip

# Not the same palette slot in both themes: the icon is a hairline drawing, so
# it takes the darker accent on the light background and the brighter one on the
# dark background, where `accent_ink` would be too close to the panel fill.
_D2_ICON_STROKE = {
    "light": PALETTE["light"]["accent_ink"],
    "dark": PALETTE["dark"]["accent"],
}
# Held for the process lifetime so the files outlive every d2 call; its
# finalizer removes the directory at interpreter exit.
_D2_ICON_TMPDIR: tempfile.TemporaryDirectory[str] | None = None

# The handbook's own palette, prepended to every diagram's source so the
# rendered SVG uses the same hex values as the artifact's CSS variables and the
# diagrams read as page furniture rather than as pictures from another system.
# Two variants rather than d2's own `--dark-theme`, because that follows the
# `prefers-color-scheme` query alone and the page carries a manual theme button.
D2_PRELUDES: dict[str, str] = {
    variant: (
        "style.fill: transparent\n"
        + _D2_FONT_SIZE
        + f'**.style.fill: "{p["surface"]}"\n'
        f'**.style.stroke: "{p["line"]}"\n'
        f'**.style.font-color: "{p["ink"]}"\n'
        "**.style.shadow: false\n"
        f'(** -> **)[*].style.stroke: "{p["accent"]}"\n'
        f'(** -> **)[*].style.font-color: "{p["ink_soft"]}"\n'
    )
    for variant, p in PALETTE.items()
}

# Funnel geometry, in SVG user units, which are CSS pixels here because the
# figure is drawn at its natural size. The width sits inside the 771px prose
# measure so the page never has to scale the figure down, which would shrink its
# labels with it. `CHAR_W` is the measured average advance of the artifact's
# sans at 12px, used only to choose where labels wrap.
_FUNNEL_WIDTH = 700
_FUNNEL_BAND_MAX = 118
_FUNNEL_BAND_MIN = 13
_FUNNEL_GAP = 26
_FUNNEL_PAD = 26
_FUNNEL_PAD_TOP = 10
_FUNNEL_CHAR_W = 6.15
_FUNNEL_LINE_H = 14
# A 13px band cannot hold a 13px digit; below this the count goes above it.
_FUNNEL_COUNT_INSIDE_MIN = 18
# Stages share a fixed width, so past some count the bands are narrower than
# the shortest label that fits in them, and beyond that the arithmetic turns
# negative and emits rects of negative width. Bound it at the point the label
# stops fitting, and derive the bound so it tracks the geometry above.
_FUNNEL_MIN_SLAB = 8 * _FUNNEL_CHAR_W
_FUNNEL_MAX_STAGES = int(
    (_FUNNEL_WIDTH - 2 * _FUNNEL_PAD + _FUNNEL_GAP) / (_FUNNEL_MIN_SLAB + _FUNNEL_GAP)
)

# The two fence kinds a page may carry. `d2` is laid out by the d2 CLI; `funnel`
# is drawn here, coordinate by coordinate, because a staged funnel wants exact
# label placement and a deliberate scale, and no layout engine will give either.
_DIAGRAM_KINDS = ("d2", "funnel")

# The body admits no line of its own that opens with a fence, so an unclosed
# block fails to match instead of swallowing the prose and headings that follow
# it up to the next stray ``` line. `extract_diagram_blocks` then turns that
# non-match into a loud error rather than a page with content silently missing.
_DIAGRAM_FENCE_RE = re.compile(
    rf"^```(?P<kind>{'|'.join(_DIAGRAM_KINDS)})(?P<meta>[^\n]*)\n"
    r"(?P<body>(?:(?!```)[^\n]*\n)*)^```[ \t]*$",
    re.MULTILINE,
)
# Anchored to the whole meta, so `title="Foo \"Bar\""` fails to match and is
# reported as a missing title, rather than being truncated to a wrong caption.
_DIAGRAM_TITLE_RE = re.compile(r'^\s*title="([^"]+)"\s*$')
_DIAGRAM_PLACEHOLDER_RE = re.compile(r'<div class="dgph" data-i="(\d+)"></div>')
# The six d2 diagrams render in well under a second; a bound this loose only
# ever fires on a d2 that has genuinely wedged. (The seventh figure, the
# screening funnel, is a `funnel` fence and never reaches the CLI.)
_D2_TIMEOUT_S = 60
_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:|^//")
_SVG_OPEN_RE = re.compile(r"<svg\b[^>]*>")
_VIEWBOX_RE = re.compile(r'viewBox="[-\d.]+ [-\d.]+ ([\d.]+) ([\d.]+)"')


@dataclass(frozen=True)
class DiagramBlock:
    """One diagram fence lifted out of a handbook page."""

    index: int
    kind: str
    title: str
    source: str


def extract_diagram_blocks(md: str, stem: str) -> tuple[str, list[DiagramBlock]]:
    """Replace every diagram fence with a placeholder and return the blocks.

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
        ValueError: A fence carries no `title="..."`, or a diagram fence was
            left unrecognised (unclosed, indented, or containing a fence of its
            own).
    """
    blocks: list[DiagramBlock] = []

    def repl(match: re.Match[str]) -> str:
        kind = match.group("kind")
        title = _DIAGRAM_TITLE_RE.match(match.group("meta"))
        if title is None:
            raise ValueError(
                f'{stem}.md: a ```{kind} fence has no title="..."; the title '
                "becomes the figure caption and the diagram's accessible name, "
                "so an untitled diagram would ship unlabeled."
            )
        index = len(blocks)
        blocks.append(
            DiagramBlock(
                index=index,
                kind=kind,
                title=title.group(1),
                source=match.group("body"),
            )
        )
        return f'<div class="dgph" data-i="{index}"></div>'

    out = _DIAGRAM_FENCE_RE.sub(repl, md)
    for kind in _DIAGRAM_KINDS:
        if f"```{kind}" in out:
            raise ValueError(
                f"{stem}.md: a ```{kind} fence was left unrecognised. A fence "
                "must begin at column 0, must carry a closing ``` line, and must "
                "contain no ``` line of its own. Left alone it would render as a "
                "literal code block and the diagram would go missing without any "
                "gate noticing."
            )
    return out, blocks


@dataclass(frozen=True)
class FunnelStage:
    """One stage of a `funnel` fence: what it is, and how many reach it."""

    label: str
    count: int


def parse_funnel(body: str, stem: str) -> list[FunnelStage]:
    """Read a `funnel` fence body into stages.

    One stage per line, the count last: `Cheap deterministic gates    2000`.
    Digits may be grouped with `_` or `,` for readability in the source.

    Args:
        body: The fence body.
        stem: The page's filename stem, used in error messages.

    Returns:
        The stages in the order the source lists them.

    Raises:
        ValueError: A line carries no count, the funnel has fewer than two
            stages or more than `_FUNNEL_MAX_STAGES`, a count is below 1, or
            the counts are not monotonically non-increasing.
    """
    stages: list[FunnelStage] = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        label, _, count = line.rpartition(" ")
        digits = count.strip().replace("_", "").replace(",", "")
        if not label.strip() or not digits.isdigit():
            raise ValueError(
                f"{stem}.md: funnel line {raw!r} does not end in a count. Each "
                "line is a label followed by the number of items reaching that "
                "stage."
            )
        value = int(digits)
        if value < 1:
            raise ValueError(
                f"{stem}.md: funnel stage {label.strip()!r} has a count of "
                f"{value}. Stages are placed on a log scale, which has no room "
                "for zero; drop the stage instead."
            )
        stages.append(FunnelStage(label.strip(), value))
    if len(stages) < 2:
        raise ValueError(f"{stem}.md: a funnel needs at least two stages")
    if len(stages) > _FUNNEL_MAX_STAGES:
        raise ValueError(
            f"{stem}.md: a funnel of {len(stages)} stages does not fit "
            f"{_FUNNEL_WIDTH}px; at most {_FUNNEL_MAX_STAGES} stages leave a "
            "band wide enough to label. Group the tail stages instead."
        )
    for earlier, later in pairwise(stages):
        if later.count > earlier.count:
            raise ValueError(
                f"{stem}.md: funnel stage {later.label!r} admits more items "
                f"({later.count}) than {earlier.label!r} ({earlier.count}). A "
                "funnel that widens is a typo in the counts, and the drawing "
                "would state it as fact."
            )
    return stages


def wrap_label(text: str, budget: int) -> list[str]:
    """Greedy-wrap a stage label to at most `budget` characters per line."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > budget:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def group_digits(n: int) -> str:
    """Group thousands with a thin space, as an entity.

    `build` runs `to_ascii_entities` over the assembled page, SVGs included, so
    a literal U+2009 would survive that route. The entity is written here so
    the SVG is self-sufficient: `funnel_svg` is also called on its own, by the
    tests and by anything that embeds one figure without the page around it.
    """
    return f"{n:,}".replace(",", "&#8201;")


def funnel_svg(stages: list[FunnelStage], variant: str) -> str:
    """Draw a staged funnel: a tapering band, each stage carrying its count.

    Every coordinate is computed here rather than by a layout engine, which is
    the whole reason this fence exists: labels sit under the band where nothing
    can collide with them, and the vertical scale is a decision rather than an
    accident.

    The scale is logarithmic. A screening funnel spans orders of magnitude, and
    on a linear scale every stage after the first two collapses into a hairline,
    so the drawing would be honest and unreadable at the same time. Log keeps
    the taper legible; the printed count is what carries the exact magnitude.

    Args:
        stages: The stages, largest first.
        variant: Which palette to draw in, `light` or `dark`.

    Returns:
        An `<svg>` element with a viewBox and no width or height; `prepare_svg`
        adds those along with the accessible name.
    """
    p = PALETTE[variant]
    counts = [s.count for s in stages]
    hi, lo = max(counts), min(counts)
    span = math.log(hi) - math.log(lo)

    def band_height(count: int) -> float:
        if span == 0:
            return _FUNNEL_BAND_MAX
        t = (math.log(count) - math.log(lo)) / span
        return _FUNNEL_BAND_MIN + t * (_FUNNEL_BAND_MAX - _FUNNEL_BAND_MIN)

    n = len(stages)
    slab = (_FUNNEL_WIDTH - 2 * _FUNNEL_PAD - _FUNNEL_GAP * (n - 1)) / n
    budget = max(8, int(slab / _FUNNEL_CHAR_W))
    wrapped = [wrap_label(s.label, budget) for s in stages]

    mid = _FUNNEL_PAD_TOP + _FUNNEL_BAND_MAX / 2
    label_top = _FUNNEL_PAD_TOP + _FUNNEL_BAND_MAX + 18
    total_h = int(label_top + max(map(len, wrapped)) * _FUNNEL_LINE_H + 12)

    parts: list[str] = []
    for i, stage in enumerate(stages):
        x = _FUNNEL_PAD + i * (slab + _FUNNEL_GAP)
        h = band_height(stage.count)
        parts.append(
            f'<rect x="{x:.1f}" y="{mid - h / 2:.1f}" width="{slab:.1f}"'
            f' height="{h:.1f}" fill="{p["surface"]}" stroke="{p["line"]}"'
            ' stroke-width="1.5"/>'
        )
        if i + 1 < n:
            h2 = band_height(stages[i + 1].count)
            edge = x + slab
            far = edge + _FUNNEL_GAP
            parts.append(
                f'<path d="M {edge:.1f} {mid - h / 2:.1f} L {far:.1f}'
                f" {mid - h2 / 2:.1f} L {far:.1f} {mid + h2 / 2:.1f} L {edge:.1f}"
                f' {mid + h / 2:.1f} Z" fill="{p["accent_wash"]}"'
                f' stroke="{p["line"]}" stroke-width="1"/>'
            )
        cx = x + slab / 2
        # The tail stages are thinner than their own digits, so the count sits
        # above the band there rather than straddling its edges.
        inside = h >= _FUNNEL_COUNT_INSIDE_MIN
        count_y = mid + 4 if inside else mid - h / 2 - 6
        parts.append(
            f'<text x="{cx:.1f}" y="{count_y:.1f}" text-anchor="middle"'
            f' fill="{p["accent_ink"]}" font-size="13" font-weight="700"'
            f' font-variant-numeric="tabular-nums">{group_digits(stage.count)}</text>'
        )
        for j, line in enumerate(wrapped[i]):
            parts.append(
                f'<text x="{cx:.1f}" y="{label_top + j * _FUNNEL_LINE_H:.1f}"'
                f' text-anchor="middle" fill="{p["ink"]}" font-size="12"'
                f' font-weight="600">{html_escape(line)}</text>'
            )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" class="funnel"'
        f' viewBox="0 0 {_FUNNEL_WIDTH} {total_h}">' + "".join(parts) + "</svg>"
    )


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
        svg: Raw renderer output.
        caption_id: The `id` of the `<figcaption>` that names this diagram.

    Returns:
        The SVG with `width`, `height`, `role`, and `aria-labelledby` added.

    Raises:
        ValueError: The output has no `<svg>` element, or none with a viewBox.
    """
    opening = _SVG_OPEN_RE.search(svg)
    if opening is None:
        raise ValueError("the renderer produced output with no <svg> element")
    tag = opening.group(0)
    viewbox = _VIEWBOX_RE.search(tag)
    if viewbox is None:
        raise ValueError("the outer <svg> element has no viewBox to size from")
    sized = (
        f'{tag[:-1]} width="{viewbox.group(1)}" height="{viewbox.group(2)}"'
        f' role="img" aria-labelledby="{caption_id}">'
    )
    return svg[: opening.start()] + sized + svg[opening.end() :]


def diagram_figure(stem: str, block: DiagramBlock, light: str, dark: str) -> str:
    """Wrap both rendered variants and their caption in one `<figure>`.

    The title is escaped on the way in: `to_ascii_entities` later rewrites only
    non-ASCII characters, so an unescaped `&` or `<` in a caption would reach
    the browser intact and corrupt the markup after it.
    """
    caption_id = f"dcap-{stem}-{block.index}"
    return (
        '<figure class="diagram">'
        f'<span class="dgvar dg-light">{prepare_svg(light, caption_id)}</span>'
        f'<span class="dgvar dg-dark">{prepare_svg(dark, caption_id)}</span>'
        f'<figcaption id="{caption_id}">{html_escape(block.title)}</figcaption>'
        "</figure>"
    )


def substitute_diagrams(html: str, figures: dict[int, str]) -> str:
    """Replace each diagram placeholder with its rendered figure.

    Raises:
        ValueError: A placeholder has no matching figure.
    """

    def repl(match: re.Match[str]) -> str:
        index = int(match.group(1))
        if index not in figures:
            raise ValueError(f"no rendered figure for diagram placeholder {index}")
        return figures[index]

    return _DIAGRAM_PLACEHOLDER_RE.sub(repl, html)


def count_em_dashes(html: str) -> int:
    """Count em-dashes in both the literal and the numeric-entity form.

    `to_ascii_entities` runs before this counter and has already rewritten the
    literal character to `&#8212;`, so counting only the character reported zero
    whatever the sources held, which made the handbook's em-dash gate vacuous.
    """
    return html.count("—") + html.count("&#8212;")


def unlink_out_of_tree(html: str) -> tuple[str, list[str]]:
    """Unwrap anchors whose relative ``.md`` target lies outside the handbook.

    The parts are all siblings in one directory, so an in-tree link is a bare
    ``<stem>.md`` and any relative ``.md`` href carrying a ``/`` points out of
    the tree. That target is not in this artifact and cannot be, so there is no
    anchor to rewrite it to. Keep the link text and drop the anchor: the
    sentence still reads, and the reader is not handed an href that resolves to
    nothing. On GitHub the same source link resolves normally, which is why it
    is written relatively rather than as an absolute URL that would carry the
    org and repository name into every artifact the page is published as.

    Args:
        html: Converted HTML for one doc.

    Returns:
        The HTML with those anchors unwrapped, and the hrefs that were, so the
        caller can report them rather than let them vanish silently.
    """
    unlinked: list[str] = []

    def repl(m: re.Match[str]) -> str:
        href = m.group(1)
        if _SCHEME_RE.match(href) or "/" not in href.split("#")[0]:
            return m.group(0)
        unlinked.append(href)
        return m.group(2)

    out = re.sub(r'<a href="([^"]+\.md[^"]*)"[^>]*>(.*?)</a>', repl, html, flags=re.S)
    return out, unlinked


_HEADING_RE = re.compile(r"<h([1-6])>(.*?)</h\1>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")


def heading_id(stem: str, heading_html: str) -> str:
    """The id a heading gets in the page: the part's stem, a hyphen, the slug.

    The slug is the GitHub-style one `render_handbook_traceability.slugify`
    computes over the heading's text, so a report citation written as
    ``<stem>.md#<slug>`` and a matrix row id written as ``<stem>/<slug>``
    both name the same element as ``<stem>-<slug>``. The stem is in front
    because a slug is unique within one part and not across the page:
    ten parts end in a ``See also`` heading, and a bare-slug id would have
    left nine of them unreachable.

    Args:
        stem: The part's markdown stem, ``lifecycle`` for ``lifecycle.md``.
        heading_html: The heading's inner HTML as the converter wrote it,
            tags and entities included; both are removed before slugifying,
            so a heading carrying a code span or an ampersand slugs the way
            its markdown source does.
    """
    text = html_unescape(_TAG_RE.sub("", heading_html))
    return f"{stem}-{slugify(text)}"


def add_heading_ids(html: str, stem: str) -> tuple[str, list[str]]:
    """Put an ``id`` on every heading of one part's HTML.

    Every level, not only ``##``: GitHub anchors all of them, the matrix's
    whole-part rows resolve through a part's ``h1`` (``coda/coda``), and a
    link into a ``###`` is a link the page would otherwise drop.

    Returns:
        The HTML with ids added, and the ids in document order.

    Raises:
        ValueError: Two headings of the part slugify to the same id. Such a
            part has two headings a citation cannot tell apart, and a second
            id silently winning would send the reader to the wrong one.
    """
    ids: list[str] = []

    def repl(m: re.Match[str]) -> str:
        hid = heading_id(stem, m.group(2))
        if hid in ids:
            raise ValueError(
                f"{stem}.md: two headings slugify to {hid!r}, so a citation "
                "naming it cannot say which one it means; reword one of them"
            )
        ids.append(hid)
        return f'<h{m.group(1)} id="{hid}">{m.group(2)}</h{m.group(1)}>'

    return _HEADING_RE.sub(repl, html), ids


def rewrite_links(
    html: str, linkmap: dict[str, str], ids: frozenset[str] | set[str] = frozenset()
) -> tuple[str, list[str]]:
    """Rewrite ``*.md`` hrefs to in-page anchors.

    A bare ``<stem>.md`` maps to the part's anchor. ``<stem>.md#<frag>`` maps
    to the heading id ``<stem>-<frag>`` where the page has one, and is
    reported as unmapped where it does not: a fragment naming no heading
    resolved on GitHub only by scrolling to the top of the file, and here it
    would silently do the same, which is the defect the ids exist to close.

    Args:
        html: Converted HTML for one part.
        linkmap: ``<stem>.md`` to ``#<part anchor>``.
        ids: Every heading id the whole page carries, from every part, since
            a link may cross into a part rendered after this one.

    Returns the rewritten HTML and the list of hrefs that could not be mapped
    (external links, docs outside the handbook, or a fragment the page has
    no heading for), so the caller can warn or raise.
    """
    unmapped: list[str] = []

    def repl(m: re.Match[str]) -> str:
        href = m.group(1)
        base, _, fragment = href.partition("#")
        anchor = linkmap.get(base)
        if anchor is None:
            unmapped.append(href)
            return m.group(0)
        if not fragment:
            return f'href="{anchor}"'
        target = f"{base[: -len('.md')]}-{fragment}"
        if target in ids:
            return f'href="#{target}"'
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


def post_process(
    html: str, linkmap: dict[str, str], ids: frozenset[str] | set[str] = frozenset()
) -> tuple[str, list[str], list[str]]:
    """Apply all HTML transforms; return the result, unmapped and unlinked hrefs.

    Out-of-tree links are unwrapped before the in-tree rewrite, so they never
    reach `unmapped` - they were handled rather than skipped, and `assemble`
    raises on an unmapped relative link. Heading ids are not added here: they
    are added per part before any link is rewritten, because `ids` has to
    hold the whole page's for a cross-part fragment to resolve.
    """
    html, unlinked = unlink_out_of_tree(html)
    html, unmapped = rewrite_links(html, linkmap, ids)
    html = wrap_tables(html)
    html = mark_task_items(html)
    return html, unmapped, unlinked


def render_part(docs_dir: Path, stem: str) -> tuple[str, list[str], list[DiagramBlock]]:
    """Convert one part to HTML with heading ids, links and diagrams untouched.

    The first of `assemble`'s two passes: every part goes through this before
    any link is rewritten, so the ids a cross-part fragment needs exist
    before the link that needs them is read. Lazy-imports markdown, so the
    pure helpers stay importable without the dependency.

    Returns:
        The HTML, the heading ids in document order, and the diagram blocks
        lifted out of the source for the caller to render and substitute.
    """
    import markdown  # lazy: keeps the pure helpers importable without the dep

    md = (docs_dir / f"{stem}.md").read_text()
    md, blocks = extract_diagram_blocks(md, stem)
    html = markdown.markdown(md, extensions=["tables", "fenced_code", "sane_lists"])
    html, ids = add_heading_ids(html, stem)
    return html, ids, blocks


def heading_ids(docs_dir: Path, parts: list[tuple[str, str, str]] = PARTS) -> set[str]:
    """Every id the page built from ``docs_dir`` carries, without rendering it.

    The part anchors plus every heading id, computed the way `assemble`
    computes them and without reaching for the d2 CLI, which is what lets the citation
    check run where no renderer can. A rendered page carries exactly this set
    plus the figure captions' ids and the two ids of the page chrome, the
    sidebar and the theme button, and a test holds the two together.
    """
    ids = {anchor for anchor, _, _ in parts}
    for _, stem, _ in parts:
        _, part_ids, _ = render_part(docs_dir, stem)
        ids.update(part_ids)
    return ids


def render_variants(block: DiagramBlock, stem: str) -> tuple[str, str]:
    """Render one block's light and dark SVGs, dispatching on its fence kind."""
    if block.kind == "funnel":
        stages = parse_funnel(block.source, stem)
        return funnel_svg(stages, "light"), funnel_svg(stages, "dark")
    return (
        run_d2(block.source, f"{stem}-{block.index}-light", "light"),
        run_d2(block.source, f"{stem}-{block.index}-dark", "dark"),
    )


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


@dataclass(frozen=True)
class AssembledPart:
    """One part after ids and links, before diagrams and page chrome."""

    anchor: str
    stem: str
    html: str
    blocks: list[DiagramBlock]


def assemble(
    docs_dir: Path,
    parts: list[tuple[str, str, str]] = PARTS,
    linkmap: dict[str, str] | None = None,
) -> list[AssembledPart]:
    """Render every part with heading ids and rewritten links.

    The half of the build the page and the book share. Every part is
    rendered before any link is rewritten, so a fragment into a later part
    finds its id. Diagrams stay as placeholders for the caller, which is what
    lets the page draw two themed variants and the book one print variant.

    Args:
        docs_dir: Directory holding the handbook Markdown.
        parts: ``(anchor, stem, label)`` in page order.
        linkmap: ``<stem>.md`` to the fragment a bare link to that part
            lands on. ``None`` means the page's map, the part anchors.

    Raises:
        ValueError: A heading id collides with another id, or a relative
            link names no part or no heading. See `build` for why each is a
            raise rather than a warning.
    """
    if linkmap is None:
        linkmap = {stem + ".md": "#" + anchor for anchor, stem, _ in parts}
    rendered = {stem: render_part(docs_dir, stem) for _, stem, _ in parts}
    ids = {anchor for anchor, _, _ in parts}
    for stem, (_, part_ids, _) in rendered.items():
        clash = ids & set(part_ids)
        if clash:
            raise ValueError(
                f"{stem}.md: heading id(s) {sorted(clash)} collide with an id the "
                "page already carries, so a link to one of them would land on "
                "the other"
            )
        ids.update(part_ids)
    assembled = []
    for anchor, stem, _ in parts:
        html, _, blocks = rendered[stem]
        html, unmapped, unlinked = post_process(html, linkmap, ids)
        dead = [h for h in unmapped if not _SCHEME_RE.match(h)]
        if dead:
            raise ValueError(
                f"{stem}.md: relative link(s) the artifact cannot resolve: "
                + ", ".join(dead)
                + ". A sibling link must name a part this artifact contains, and "
                "a fragment on it must name a heading of that part; a target "
                "outside the handbook is written relatively and gets unlinked "
                "here."
            )
        for href in unmapped:
            print(f"  WARNING unmapped link in {stem}.md: {href}")
        for href in unlinked:
            print(f"  NOTE unlinked out-of-tree link in {stem}.md: {href}")
        assembled.append(AssembledPart(anchor, stem, html, blocks))
    return assembled


def build(docs_dir: Path, parts: list[tuple[str, str, str]] = PARTS) -> str:
    """Render the full handbook artifact HTML from ``docs_dir``.

    Raises:
        ValueError: If a page carries a relative `.md` link the linkmap
            cannot resolve, or a fragment on one that names no heading of
            its part. Such a link resolves on GitHub and is dead in
            this artifact, and nothing else in this repository looks at the
            handbook's links, so a warning here would be a silent pass.
            This raise is the only check there is. Absolute URLs are
            unmapped by design and pass; the one link out of the handbook
            tree (`engineering-notes.md`, from the README's parts table) is
            relative and is unlinked by `unlink_out_of_tree` before the
            rewrite sees it. Also raised when two headings of one part
            slugify alike (from `add_heading_ids`) or a heading id collides
            with an id the page already carries, because either would send a
            citation to the wrong element.
    """
    sections = []
    for part in assemble(docs_dir, parts):
        cls = "part intro" if part.anchor == "top" else "part"
        html = part.html
        if part.blocks:
            html = substitute_diagrams(
                html,
                {
                    block.index: diagram_figure(
                        part.stem, block, *render_variants(block, part.stem)
                    )
                    for block in part.blocks
                },
            )
        sections.append(
            f'    <section id="{part.anchor}" class="{cls}">\n'
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

  /* Diagrams: two rendered variants, toggled with the page theme.
     Diagrams are authored to fit the prose measure at their natural size, so
     that `max-width: 100%` never has to scale one down: scaling shrinks the
     labels with it, and a diagram whose text has gone small is worse than a
     diagram that is merely narrow. */
  .doc figure.diagram { margin: 22px 0; }
  .doc figure.diagram svg { display: block; margin: 0 auto; max-width: 100%; height: auto; }
  /* d2 embeds its own font; funnels are drawn here and take the page's. */
  .doc figure.diagram svg.funnel text { font-family: var(--sans); }
  .doc figure.diagram figcaption {
    margin-top: 10px; text-align: center; font-family: var(--mono);
    font-size: .7rem; letter-spacing: .07em; text-transform: uppercase; color: var(--ink-faint);
  }
  .dgvar { display: block; }
  .dg-dark { display: none; }
  @media (prefers-color-scheme: dark) { .dg-light { display: none; } .dg-dark { display: block; } }
  :root[data-theme="light"] .dg-light { display: block; }
  :root[data-theme="light"] .dg-dark { display: none; }
  :root[data-theme="dark"] .dg-light { display: none; }
  :root[data-theme="dark"] .dg-dark { display: block; }

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
