"""A book figure: a committed SVG under `docs/engineering/figures/`, seeded by
running `d2` once through `render_handbook_artifact.run_d2`, then corrected by
hand in an SVG editor (Inkscape) so it sits inside the book's print measure.

Every figure is drawn at one scale, `PT_PER_UNIT` (2/3 pt per SVG user unit),
so a figure's own viewBox is also its footprint on the page: `MAX_VIEWBOX` is
the 3.6 x 6.0 in text block converted into that scale, and `TEXT_PT_RANGE`
bounds what a label may print at once the scale is applied.

This module holds the pure logic three later steps share: stamping and
reading the `data-source-sha256` hash a figure was seeded from, cleaning up
what `run_d2` hands the illustrator before it is committed as a seed, and the
checks a fixer or a CI gate runs over a finished figure (does it fit the
block, is every fill dark enough not to wash out on cream paper, does every
text and stroke colour hold its WCAG contrast bar), and the three steps that
turn a committed figure into the EPUB's copy of it: a light backing panel
(`with_backing_panel`) so dark ink stays legible in a reading system's dark
mode, the subset faces its text uses (`embed_fonts`), since an SVG an `<img>`
references cannot reach the book's other files, and the em width that places
it at the one scale (`epub_width_em`). Nothing here spawns a process or
writes a file; that belongs to the scripts built on top of it.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import io
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

FIGURE_FONT = "Source Sans 3"
# Points per SVG user unit: the book places every figure at one scale, chosen
# so a figure's own viewBox reads directly as its footprint on the page.
PT_PER_UNIT = 2 / 3
# The paperback's text block is 3.6 x 6.0 in; converted through PT_PER_UNIT
# (72 pt/in) that is 388.8 x 648.0 units. A figure wider or taller than this
# would either overflow the block or force pandoc to scale it, shrinking its
# labels with it.
MAX_VIEWBOX = (388.8, 648.0)
# A label has to stay legible in print without also swamping the diagram; 7-9
# pt is the book's body-adjacent caption range.
TEXT_PT_RANGE = (7.0, 9.0)
# The paperback's paper colour, used as the contrast backdrop for every fill
# and stroke a figure paints. Text needs 4.5:1 against it, strokes 3:1 (the
# same bars `render_handbook_artifact.PRINT_PALETTE` was chosen to hold).
PAPER_CREAM = "#f7f0dc"
# A fill whose effective alpha is at most this is a tint: a translucent
# overlay the paper shows through, such as the funnel's accent wash at 0.15,
# which the book allows. Above it, a fill covers more paper than it lets
# through, so it is blended over the paper and judged as the surface it prints.
TINT_MAX_ALPHA = 0.5
# The body's nominal size in the EPUB, in points: `epub_width_em` expresses a
# figure's one-scale width relative to it, so labels keep their ratio to the
# text when a reader changes the font size.
BODY_PT = 10
# The committed faces under `fonts/source-sans-3/`, by the (weight, style)
# each one sets. `embed_fonts` snaps any other weight to the nearest of these.
FACE_FILES = {
    (400, "normal"): "SourceSans3-Regular.ttf",
    (700, "normal"): "SourceSans3-Bold.ttf",
    (400, "italic"): "SourceSans3-It.ttf",
}

# Elements whose whole subtree never contributes a drawn shape: a clip mask,
# shared definitions, editor metadata, or Inkscape's own view-state element.
# Walking into one of these would misread furniture as figure content, most
# visibly a mask's opaque white rect, which would otherwise fail the opaque-
# fill check for a mask that paints nothing.
#
# `image` is a narrower case, judged by `_walk_paint` rather than skipped by
# `_walk`: it paints its embedded bitmap, so `fill`/`stroke` reaching it
# through inheritance describes no pixel it actually draws. `use` is not the
# same case despite looking like it: SVG 1.1 section 5.6 has the referenced
# instance inherit from the `use` element itself, so `<use fill="...">`
# genuinely paints its reference and stays judged, even though the walk never
# resolves what that reference is.
_SKIP_TAGS = frozenset({"mask", "defs", "metadata", "namedview"})

_NAMED_COLORS = {"white": "#ffffff", "black": "#000000"}
_TRANSPARENT_LIKE = frozenset({"none", "transparent", "currentcolor"})

_ROOT_SVG_RE = re.compile(r"<svg\b[^>]*>")
_HASH_ATTR_RE = re.compile(r'data-source-sha256="[0-9a-fA-F]*"')
_VIEWBOX_ATTR_RE = re.compile(r'viewBox="([^"]*)"')

_STYLE_BLOCK_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.DOTALL)
_TEXT_CLASS_RE = re.compile(r'class="(text(?:-[\w]+)?)"')
_SALT_TOKEN_RE = re.compile(r"d2-\d+")
_G_CLASS_RE = re.compile(r'<g class="([^"]+)">')

_TEXT_CLASS_ATTR = {
    "text": 'font-weight="400"',
    "text-bold": 'font-weight="700"',
    "text-italic": 'font-style="italic"',
}


def source_hash(source: str) -> str:
    """The sha256 hex digest of a diagram fence body, stamped onto its seed."""
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _root_tag(svg: str) -> re.Match[str]:
    match = _ROOT_SVG_RE.search(svg)
    if match is None:
        raise ValueError("no root <svg> tag found")
    return match


def stamp_hash(svg: str, digest: str) -> str:
    """Record `digest` as the root `<svg>`'s `data-source-sha256` attribute.

    Replaces an existing hash rather than adding a second one, so re-stamping
    a figure after a fence edit never leaves the old digest readable.
    """
    match = _root_tag(svg)
    tag = match.group(0)
    if "data-source-sha256=" in tag:
        new_tag = _HASH_ATTR_RE.sub(f'data-source-sha256="{digest}"', tag, count=1)
    else:
        new_tag = f'{tag[:-1]} data-source-sha256="{digest}">'
    return svg[: match.start()] + new_tag + svg[match.end() :]


def recorded_hash(svg: str) -> str | None:
    """The digest an earlier `stamp_hash` recorded, or `None` if unstamped."""
    match = _root_tag(svg)
    hash_match = _HASH_ATTR_RE.search(match.group(0))
    if hash_match is None:
        return None
    return hash_match.group(0).split('"')[1]


def _viewbox_box(svg: str) -> tuple[float, float, float, float]:
    """The root `<svg>`'s `viewBox` as its four numbers: x, y, width, height.

    Raises:
        ValueError: there is no root `<svg>` tag, or it has no `viewBox`.
    """
    match = _root_tag(svg)
    vb_match = _VIEWBOX_ATTR_RE.search(match.group(0))
    if vb_match is None:
        raise ValueError("root <svg> element has no viewBox")
    parts = vb_match.group(1).split()
    if len(parts) != 4:
        raise ValueError(f"viewBox {vb_match.group(1)!r} does not have four components")
    x, y, width, height = (float(p) for p in parts)
    return x, y, width, height


def viewbox(svg: str) -> tuple[float, float]:
    """The root `<svg>`'s width and height, read from its `viewBox`.

    Raises:
        ValueError: there is no root `<svg>` tag, or it has no `viewBox`.
    """
    _, _, width, height = _viewbox_box(svg)
    return width, height


def _slugify(decoded: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", decoded.lower()).strip("-")


def _replace_g_class(svg: str, figure_id: str) -> str:
    seen: dict[str, int] = {}

    def repl(match: re.Match[str]) -> str:
        value = match.group(1)
        # d2 writes the base64 group name alone for a plain shape, but
        # `class="<base64> <user class>"` for one carrying a `{class: ...}`
        # (e.g. an icon class from `d2_icon_classes`), so only the first
        # whitespace-separated token is ever the base64 name; the rest, if
        # any, is a real CSS class this figure's own classes block styles.
        parts = value.split(None, 1)
        token = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
        try:
            decoded = base64.b64decode(token, validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError):
            return match.group(0)
        if not decoded.isprintable():
            return match.group(0)
        slug = _slugify(decoded)
        seen[slug] = seen.get(slug, 0) + 1
        if seen[slug] > 1:
            slug = f"{slug}-{seen[slug]}"
        rest = rest.strip()
        if rest:
            return f'<g id="{figure_id}-{slug}" class="{rest}">'
        return f'<g id="{figure_id}-{slug}">'

    return _G_CLASS_RE.sub(repl, svg)


def clean_seed_svg(svg: str, figure_id: str) -> str:
    """Turn a raw `run_d2` render into the seed an illustrator opens.

    Works on the text, by regex, so d2's own layout is never re-serialised:
    drops every embedded `<style>` (fonts and shape CSS the print prelude
    already makes redundant, since colour comes from the fence's own
    attributes), turns each `class="text*"` into the attribute it stands for,
    names the root font, and replaces d2's per-render salt and its base64
    group names with stable ids built from `figure_id`. A funnel SVG, which
    carries none of d2's markup, passes through with only the font family
    added.

    Args:
        svg: Raw `run_d2` output, or an already-drawn funnel SVG.
        figure_id: This figure's stem, e.g. `codebase-structure-0`. Used both
            as the salt's replacement and as the prefix for every group id.

    Raises:
        ValueError: a `class="text-*"` names a style this module has no
            attribute mapping for.
    """
    svg = _STYLE_BLOCK_RE.sub("", svg)

    def text_class_repl(match: re.Match[str]) -> str:
        cls = match.group(1)
        attr = _TEXT_CLASS_ATTR.get(cls)
        if attr is None:
            raise ValueError(f"unrecognized text class {cls!r} in seed SVG")
        return attr

    svg = _TEXT_CLASS_RE.sub(text_class_repl, svg)
    svg = re.sub(r"<svg\b", f'<svg font-family="{FIGURE_FONT}"', svg, count=1)
    svg = _SALT_TOKEN_RE.sub(figure_id, svg)
    svg = _replace_g_class(svg, figure_id)
    return svg


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _walk(el: ET.Element):
    """Yield `el` and every descendant, skipping subtrees in `_SKIP_TAGS`."""
    yield el
    for child in el:
        if not isinstance(child.tag, str):
            continue  # a comment or processing instruction, not an element
        if _local(child.tag) in _SKIP_TAGS:
            continue
        yield from _walk(child)


# SVG's initial values for `fill`/`fill-opacity` and `stroke`/`stroke-opacity`:
# opaque black fill, no stroke at all, in force at the root before anything
# has set any of the four.
_INITIAL_FILL = "black"
_INITIAL_FILL_OPACITY = "1"
_INITIAL_STROKE = "none"
_INITIAL_STROKE_OPACITY = "1"


# Painted only through an embedded bitmap, never through its own
# `fill`/`stroke`; see the note beside `_SKIP_TAGS` for why `use` is not here.
_NO_PAINT_TAGS = frozenset({"image"})


def _walk_paint(
    el: ET.Element,
    fill: str = _INITIAL_FILL,
    fill_opacity: str = _INITIAL_FILL_OPACITY,
    stroke: str = _INITIAL_STROKE,
    stroke_opacity: str = _INITIAL_STROKE_OPACITY,
    group_opacity: float = 1.0,
):
    """Yield `(element, fill, fill_alpha, fill_bad, stroke, stroke_alpha, stroke_bad)`.

    `fill_bad`/`stroke_bad` is `(property, raw) | None`; see below.

    `fill`, `fill-opacity`, `stroke` and `stroke-opacity` are all inherited
    SVG properties (SVG 1.1 section 11.4; SVG 2's painting-properties table
    lists `stroke` alongside `fill`, not apart from it): an element that sets
    none of them takes them from its nearest ancestor, all the way up to the
    root's defaults (opaque black fill, no stroke). This is exactly how an
    Inkscape edit leaves colour on a selected group or layer with the shape
    or text inside left unset, so a check reading only an element's own
    attribute would miss a pale colour set on its parent, for a stroke just
    as much as for a fill. An `image` element is never yielded (it paints an
    embedded bitmap, not `fill`/`stroke`), though its subtree, if any, is
    still walked; `use` is still yielded (see `_NO_PAINT_TAGS`'s comment).

    `opacity` is not inherited but composited: a group's `opacity` fades
    everything inside it, and nested groups multiply. So each alpha yielded
    is the paint's own resolved `fill-opacity`/`stroke-opacity` times the
    product of `opacity` on the element and every ancestor, which is how
    much of the colour reaches the paper. Skips subtrees in `_SKIP_TAGS`, as
    `_walk` does.

    `fill_alpha`/`stroke_alpha` is `None`, with the corresponding
    `fill_bad`/`stroke_bad` carrying `(property, raw)` - the property name and
    the raw string that defeated `_parse_opacity` - wherever a `fill-opacity`,
    `stroke-opacity` or `opacity` in force for this element is not one of its
    recognized forms, so a caller reports it the way it already reports an
    unrecognized colour, rather than the alpha silently reading as fully
    opaque. A bad `opacity` poisons both channels, since it composites into
    each, and is named `opacity` in both rather than misattributed to
    `fill-opacity`/`stroke-opacity`; a bad `fill-opacity`/`stroke-opacity`
    poisons only its own channel, and, inherited unchanged like the colour it
    travels with, is reported again on every descendant that does not
    override it - the same duplication an unrecognized inherited colour
    already produces.
    """
    own_fill = _get_prop(el, "fill")
    effective_fill = own_fill if own_fill is not None else fill
    own_fill_opacity = _get_prop(el, "fill-opacity")
    effective_fill_opacity = (
        own_fill_opacity if own_fill_opacity is not None else fill_opacity
    )
    own_stroke = _get_prop(el, "stroke")
    effective_stroke = own_stroke if own_stroke is not None else stroke
    own_stroke_opacity = _get_prop(el, "stroke-opacity")
    effective_stroke_opacity = (
        own_stroke_opacity if own_stroke_opacity is not None else stroke_opacity
    )
    own_opacity = _get_prop(el, "opacity")
    try:
        own_alpha = _parse_opacity(own_opacity)
        group_bad: tuple[str, str] | None = None
    except ValueError:
        own_alpha = 1.0
        group_bad = ("opacity", own_opacity)
    composite = group_opacity * own_alpha

    def _alpha(raw: str, prop: str) -> tuple[float | None, tuple[str, str] | None]:
        if group_bad is not None:
            return None, group_bad
        try:
            return _parse_opacity(raw) * composite, None
        except ValueError:
            return None, (prop, raw)

    fill_alpha, fill_bad = _alpha(effective_fill_opacity, "fill-opacity")
    stroke_alpha, stroke_bad = _alpha(effective_stroke_opacity, "stroke-opacity")
    if _local(el.tag) not in _NO_PAINT_TAGS:
        yield (
            el,
            effective_fill,
            fill_alpha,
            fill_bad,
            effective_stroke,
            stroke_alpha,
            stroke_bad,
        )
    for child in el:
        if not isinstance(child.tag, str):
            continue  # a comment or processing instruction, not an element
        if _local(child.tag) in _SKIP_TAGS:
            continue
        yield from _walk_paint(
            child,
            effective_fill,
            effective_fill_opacity,
            effective_stroke,
            effective_stroke_opacity,
            composite,
        )


def _style_props(el: ET.Element) -> dict[str, str]:
    style = el.attrib.get("style", "")
    props = {}
    for part in style.split(";"):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        props[key.strip()] = value.strip()
    return props


def _get_prop(el: ET.Element, name: str) -> str | None:
    """A presentation property, preferring `style` over the bare attribute."""
    style_value = _style_props(el).get(name)
    if style_value is not None:
        return style_value
    return el.attrib.get(name)


def _parse_opacity(value: str | None) -> float:
    """Parse an SVG alpha: a bare number (SVG 1.1) or a percentage (SVG 2).

    Clamped to 0..1, since that is the only range that means anything as an
    alpha and an author value outside it should not paint as more or less
    opaque than fully.

    Raises:
        ValueError: `value` is set but neither of those two forms.
    """
    if value is None:
        return 1.0
    v = value.strip()
    number = float(v[:-1]) / 100 if v.endswith("%") else float(v)
    return max(0.0, min(1.0, number))


def _normalize_hex(value: str) -> str:
    """Normalize `#rgb`, `#rrggbb`, `white` or `black` to lowercase `#rrggbb`.

    Raises:
        ValueError: `value` is not one of the recognized forms.
    """
    v = value.strip()
    low = v.lower()
    if low in _NAMED_COLORS:
        return _NAMED_COLORS[low]
    if re.fullmatch(r"#[0-9a-fA-F]{6}", v):
        return low
    if re.fullmatch(r"#[0-9a-fA-F]{3}", v):
        return "#" + "".join(c * 2 for c in v[1:]).lower()
    raise ValueError(f"unrecognized colour {value!r}")


def _resolve_paint(value: str) -> str | None:
    """A fill/stroke value's colour, or `None` if it is never opaque or checked.

    `none`, `transparent`, `currentColor` and `url(...)` paint nothing this
    module can read the colour of, so they are neither opaque nor held to a
    contrast bar.

    Raises:
        ValueError: `value` is set but not a recognized colour and not one of
            the paint-nothing forms above.
    """
    low = value.strip().lower()
    if low in _TRANSPARENT_LIKE or low.startswith("url("):
        return None
    return _normalize_hex(value)


def _channel_linear(c: float) -> float:
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_color: str) -> float:
    r = int(hex_color[1:3], 16) / 255
    g = int(hex_color[3:5], 16) / 255
    b = int(hex_color[5:7], 16) / 255
    r, g, b = _channel_linear(r), _channel_linear(g), _channel_linear(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _blend(hex_color: str, alpha: float, paper: str) -> str:
    """`hex_color` painted at `alpha` over `paper`, as the colour that prints.

    Source-over compositing per channel in sRGB, which is how a renderer
    composites a translucent paint onto what lies beneath it.
    """
    top, under = _normalize_hex(hex_color), _normalize_hex(paper)
    alpha = min(max(alpha, 0.0), 1.0)
    channels = (
        round(alpha * int(top[i : i + 2], 16) + (1 - alpha) * int(under[i : i + 2], 16))
        for i in (1, 3, 5)
    )
    return "#" + "".join(f"{c:02x}" for c in channels)


def contrast_ratio(a: str, b: str) -> float:
    """The WCAG 2 contrast ratio between two `#rgb`/`#rrggbb`/named colours."""
    la, lb = (
        _relative_luminance(_normalize_hex(a)),
        _relative_luminance(_normalize_hex(b)),
    )
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def _fmt(x: float) -> str:
    return f"{x:g}"


def _parse_font_size(value: str) -> float:
    v = value.strip()
    if v.endswith("px"):
        v = v[:-2]
    return float(v)


# A `transform` that only moves its content keeps every label at the one scale;
# anything else (`scale`, `rotate`, `skew`, `matrix`) can change the size a
# label prints at while its `font-size` still reads in range.
_PURE_TRANSLATE_RE = re.compile(
    r"\s*(?:translate\(\s*[-+.\deE]+(?:\s*,?\s*[-+.\deE]+)?\s*\)\s*,?\s*)*"
)
# SVG's initial font-size, 16 px: 10.7 pt at the one scale, outside the range.
_INITIAL_FONT_SIZE_UNITS = 16


def _walk_chain(el: ET.Element, ancestors: tuple[ET.Element, ...] = ()):
    """Yield `(element, chain)`, `chain` running from the root to `element`.

    Skips subtrees in `_SKIP_TAGS`, as `_walk` does.
    """
    chain = (*ancestors, el)
    yield el, chain
    for child in el:
        if not isinstance(child.tag, str):
            continue  # a comment or processing instruction, not an element
        if _local(child.tag) in _SKIP_TAGS:
            continue
        yield from _walk_chain(child, chain)


def _label(el: ET.Element) -> str:
    text = "".join(el.itertext()).strip()
    return f"<{_local(el.tag)}> {text[:20]!r}" if text else f"<{_local(el.tag)}>"


def fit_problems(svg: str) -> list[str]:
    """Where a figure would overflow the book's block, in words.

    Checks the root `viewBox` against `MAX_VIEWBOX`, and every `text` or
    `tspan`'s font-size against `TEXT_PT_RANGE` once scaled by
    `PT_PER_UNIT`. The size is the element's own, or else its nearest
    ancestor's, `style` winning over the bare attribute (unitless or `px`),
    and a text with no font-size anywhere up its ancestry is reported, since
    SVG's 16 px default prints outside the range. Each out-of-range size is
    reported once, on the element that sets it.

    A `transform` on a text or on any ancestor of one is reported unless it
    is only `translate(...)`: a scale, rotation, skew or matrix changes the
    size a label prints at while its `font-size` still reads in range, which
    is how a group shrunk in an editor would otherwise pass. The fix is to
    bake the transform into the drawing, or redraw it, never to shrink it.
    """
    problems: list[str] = []
    width, height = viewbox(svg)
    max_w, max_h = MAX_VIEWBOX
    if width > max_w:
        problems.append(f"{_fmt(width)} units wide, over {_fmt(max_w)}")
    if height > max_h:
        problems.append(f"{_fmt(height)} units tall, over {_fmt(max_h)}")

    root = ET.fromstring(svg)
    lo, hi = TEXT_PT_RANGE
    bad_transforms: set[int] = set()
    judged_sizes: set[int] = set()
    for el, chain in _walk_chain(root):
        if _local(el.tag) not in ("text", "tspan"):
            continue
        for node in chain:
            transform = _get_prop(node, "transform")
            if transform is None or id(node) in bad_transforms:
                continue
            if not _PURE_TRANSLATE_RE.fullmatch(transform):
                bad_transforms.add(id(node))
                problems.append(
                    f"transform {transform!r} on <{_local(node.tag)}> changes the "
                    "size its text prints at; bake the transform into the "
                    "drawing or redraw it"
                )
        setter = next(
            (n for n in reversed(chain) if _get_prop(n, "font-size") is not None),
            None,
        )
        if setter is None:
            if _local(el.tag) == "text":
                pt = _INITIAL_FONT_SIZE_UNITS * PT_PER_UNIT
                problems.append(
                    f"{_label(el)} has no font-size anywhere up its ancestry, so "
                    f"it prints at SVG's {_INITIAL_FONT_SIZE_UNITS} px default, "
                    f"{pt:.1f} pt, outside {_fmt(lo)}-{_fmt(hi)} pt"
                )
            continue
        if id(setter) in judged_sizes:
            continue
        value = _get_prop(setter, "font-size")
        try:
            units = _parse_font_size(value)
        except ValueError:
            judged_sizes.add(id(setter))
            problems.append(f"font-size {value!r} is not a recognized size")
            continue
        pt = units * PT_PER_UNIT
        if pt < lo or pt > hi:
            judged_sizes.add(id(setter))
            problems.append(
                f"font-size {_fmt(units)} units is {pt:.1f} pt, "
                f"outside {_fmt(lo)}-{_fmt(hi)} pt"
            )
    return problems


def opaque_fill_problems(svg: str, paper: str = PAPER_CREAM) -> list[str]:
    """Fills, on anything but text, that would print as a pale surface.

    `fill` is inherited (`_walk_paint`), so a shape left with no fill of its
    own, painted by a colour set on an ancestor group or layer, is checked
    under that inherited colour rather than skipped as unset. Its alpha is
    the resolved `fill-opacity` composited with every `opacity` above it. A
    fill at or below `TINT_MAX_ALPHA` is a tint and passes; any other is
    blended over `paper` at its alpha and reported when the colour that
    prints has a luminance over 0.5, so a pale fill at 0.99 is judged as the
    pale surface it is. An alpha of 0 paints nothing. An unrecognized colour,
    or a `fill-opacity`/`opacity` in none of `_parse_opacity`'s recognized
    forms, is reported rather than silently passed. `text`/`tspan` fills are
    `contrast_problems`'s concern, held to a paper-contrast bar rather than a
    bare luminance cutoff. An `image` element is never judged (`_walk_paint`
    never yields one): it paints an embedded bitmap, not its inherited
    `fill`.
    """
    problems: list[str] = []
    root = ET.fromstring(svg)
    for (
        el,
        fill,
        fill_alpha,
        fill_bad,
        _stroke,
        _stroke_alpha,
        _stroke_bad,
    ) in _walk_paint(root):
        if _local(el.tag) in ("text", "tspan"):
            continue
        if fill_bad is not None:
            prop, raw = fill_bad
            problems.append(
                f"{prop} {raw!r} on <{_local(el.tag)}> is not a recognized opacity"
            )
            continue
        if fill_alpha <= TINT_MAX_ALPHA:
            continue
        try:
            hex_color = _resolve_paint(fill)
        except ValueError:
            problems.append(f"unrecognized fill {fill!r} on <{_local(el.tag)}>")
            continue
        if hex_color is None:
            continue
        printed = _blend(hex_color, fill_alpha, paper)
        if _relative_luminance(printed) > 0.5:
            problems.append(
                f"fill {hex_color} at alpha {_fmt(fill_alpha)} on "
                f"<{_local(el.tag)}> prints as {printed}, luminance over 0.5, "
                "and would wash out on the paper"
            )
    return problems


def _contrast_problem(
    kind: str, paint: str, alpha: float, tag: str, paper: str, bar: float
) -> str | None:
    """A paint's problem against its contrast `bar`, or `None` if it holds.

    Raises:
        ValueError: `paint` is set but not a recognized colour.
    """
    if alpha <= 0:
        return None
    hex_color = _resolve_paint(paint)
    if hex_color is None:
        return None
    printed = _blend(hex_color, alpha, paper)
    ratio = contrast_ratio(printed, paper)
    if ratio >= bar:
        return None
    shown = hex_color if alpha >= 1 else f"{hex_color} at alpha {_fmt(alpha)}"
    return (
        f"{kind} {shown} on <{tag}> contrasts {ratio:.2f}:1 against the "
        f"paper, under {_fmt(bar)}:1"
    )


def contrast_problems(svg: str, paper: str = PAPER_CREAM) -> list[str]:
    """Text and strokes that would not hold their contrast bar against `paper`.

    Every `text`/`tspan` fill is held to 4.5:1, every stroke (on any element)
    to 3:1. Both `fill` and `stroke` are inherited SVG properties (SVG 1.1
    section 11.4; SVG 2's painting-properties table lists them side by side),
    so a `<text>` or a shape left with no colour of its own, painted by its
    ancestor group or layer instead, exactly how an Inkscape edit tends to
    leave it, is checked under that inherited colour via `_walk_paint` rather
    than read from the element alone. A translucent paint is not exempt: its
    colour is blended over `paper` at its alpha (the resolved paint opacity
    composited with every `opacity` above it) and the colour that prints is
    what is held to the bar, so ink under a faded group is judged as the grey
    it becomes. An alpha of 0 paints nothing. An unrecognized colour, or a
    `fill-opacity`/`stroke-opacity`/`opacity` in none of `_parse_opacity`'s
    recognized forms, is reported rather than silently passed. An `image`
    element is never judged (`_walk_paint` never yields one): it paints an
    embedded bitmap, not its inherited `fill`/`stroke`.
    """
    problems: list[str] = []
    root = ET.fromstring(svg)
    for el, fill, fill_alpha, fill_bad, stroke, stroke_alpha, stroke_bad in _walk_paint(
        root
    ):
        tag = _local(el.tag)
        if tag in ("text", "tspan"):
            if fill_bad is not None:
                prop, raw = fill_bad
                problems.append(
                    f"text {prop} {raw!r} on <{tag}> is not a recognized opacity"
                )
            else:
                try:
                    problem = _contrast_problem(
                        "text fill", fill, fill_alpha, tag, paper, 4.5
                    )
                except ValueError:
                    problem = f"unrecognized text fill {fill!r} on <{tag}>"
                if problem is not None:
                    problems.append(problem)
        if stroke_bad is not None:
            prop, raw = stroke_bad
            problems.append(f"{prop} {raw!r} on <{tag}> is not a recognized opacity")
            continue
        try:
            problem = _contrast_problem("stroke", stroke, stroke_alpha, tag, paper, 3.0)
        except ValueError:
            problem = f"unrecognized stroke {stroke!r} on <{tag}>"
        if problem is not None:
            problems.append(problem)
    return problems


def _insert_after_root(svg: str, markup: str) -> str:
    end = _root_tag(svg).end()
    return svg[:end] + markup + svg[end:]


def with_backing_panel(svg: str, colour: str) -> str:
    """The EPUB copy's opaque light panel, drawn behind everything else.

    A book figure is transparent, so on a reading system's dark background its
    dark ink would vanish, and reading systems do not invert images. The panel
    is a `<rect>` covering the root `viewBox`, inserted as the root's first
    child, inside the SVG, where a reading system's stylesheet cannot remove
    it. The committed file stays transparent; only the EPUB copy carries this.

    Raises:
        ValueError: there is no root `<svg>` tag, or it has no `viewBox`.
    """
    x, y, width, height = _viewbox_box(svg)
    panel = (
        f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}"'
        f' fill="{colour}"/>'
    )
    return _insert_after_root(svg, panel)


# CSS's initial font-weight and font-style, in force at the root before any
# element sets either.
_INITIAL_WEIGHT = "400"
_INITIAL_STYLE = "normal"
_WEIGHT_KEYWORDS = {"normal": 400, "bold": 700}
_STYLE_KEYWORDS = {"normal": "normal", "italic": "italic", "oblique": "italic"}


def _walk_font(
    el: ET.Element, weight: str = _INITIAL_WEIGHT, style: str = _INITIAL_STYLE
):
    """Yield `(element, font_weight, font_style)`, inherited as `_walk_paint` does.

    Both are inherited properties: an element that sets neither takes them
    from its nearest ancestor that does, `style` winning over the bare
    attribute (`_get_prop`), up to CSS's initial `400`/`normal` at the root.
    Skips subtrees in `_SKIP_TAGS`.
    """
    own_weight = _get_prop(el, "font-weight")
    effective_weight = own_weight if own_weight is not None else weight
    own_style = _get_prop(el, "font-style")
    effective_style = own_style if own_style is not None else style
    yield el, effective_weight, effective_style
    for child in el:
        if not isinstance(child.tag, str):
            continue  # a comment or processing instruction, not an element
        if _local(child.tag) in _SKIP_TAGS:
            continue
        yield from _walk_font(child, effective_weight, effective_style)


def _face_for(weight: str, style: str) -> tuple[int, str]:
    """The committed face in `FACE_FILES` that sets text of this weight and style.

    `bold` reads as 700 and `normal` as 400; a numeric weight snaps to the
    nearer of 400 and 700, a tie going to 400 as CSS's own font matching
    would for 500 (a funnel's 600-weight labels set in the bold face). Italic
    text of any weight sets in the one italic face, which is 400.

    Raises:
        ValueError: the weight or style is neither a keyword above nor, for
            the weight, a number.
    """
    w = weight.strip().lower()
    if w in _WEIGHT_KEYWORDS:
        numeric = _WEIGHT_KEYWORDS[w]
    else:
        try:
            numeric = int(float(w))
        except ValueError:
            raise ValueError(f"unrecognized font-weight {weight!r}") from None
    font_style = _STYLE_KEYWORDS.get(style.strip().lower())
    if font_style is None:
        raise ValueError(f"unrecognized font-style {style!r}")
    if font_style == "italic":
        return 400, "italic"
    return (400 if abs(numeric - 400) <= abs(numeric - 700) else 700), "normal"


def _set_text_run(
    used: dict[tuple[int, str], set[str]], face: tuple[int, str], run: str | None
) -> None:
    # A whitespace-only run (Inkscape's indentation between tspans) sets no
    # glyph worth a face of its own; the space every subset carries covers it.
    if run and run.strip():
        used.setdefault(face, set()).update(run)


def _collect_text(
    el: ET.Element, weight: str, style: str, used: dict[tuple[int, str], set[str]]
) -> None:
    """Assign each run of text inside `el` to the face that sets it.

    A text-content child (`tspan`, `textPath`) may set its own weight or
    style, inherited by its descendants exactly as `_walk_font` resolves it,
    so its `.text` is set in its own face while its `.tail` - the characters
    after it, still inside its parent - is set in the parent's.
    """
    face = _face_for(weight, style)
    _set_text_run(used, face, el.text)
    for child in el:
        if isinstance(child.tag, str) and _local(child.tag) not in _SKIP_TAGS:
            own_weight = _get_prop(child, "font-weight")
            own_style = _get_prop(child, "font-style")
            _collect_text(
                child,
                own_weight if own_weight is not None else weight,
                own_style if own_style is not None else style,
                used,
            )
        _set_text_run(used, face, child.tail)


def _faces_and_text(svg: str) -> dict[tuple[int, str], set[str]]:
    """Each committed face the figure's text sets, and the characters it sets.

    Resolved per run of text rather than per `<text>` element, so a weight
    or style an editor left on a `<tspan>` reaches the characters inside it.
    """
    used: dict[tuple[int, str], set[str]] = {}
    for el, weight, style in _walk_font(ET.fromstring(svg)):
        if _local(el.tag) == "text":
            _collect_text(el, weight, style, used)
    return used


def used_faces(svg: str) -> set[tuple[int, str]]:
    """The `(weight, style)` of every committed face the figure's text sets."""
    return set(_faces_and_text(svg))


def _subset_woff(font_path: Path, chars: set[str]) -> bytes:
    options = subset.Options()
    options.flavor = "woff"
    # A fresh TTFont per call: `Subsetter.subset` shrinks the font in place.
    font = TTFont(font_path)
    subsetter = subset.Subsetter(options)
    subsetter.populate(text="".join(sorted(chars | {" "})))
    subsetter.subset(font)
    font.flavor = "woff"
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


def embed_fonts(svg: str, font_dir: Path) -> str:
    """Embed, as one `<style>`, each face the figure's text uses, subset to it.

    An SVG an `<img>` references cannot reach the book's other files, and a
    reading system's fallback font sets wider than Source Sans 3 and would
    push labels out of their boxes. So the weight and style of each run of
    text, inside a `<text>` or any `<tspan>` in it, are resolved through its
    ancestors (`_walk_font`, `_collect_text`) and snapped to a committed face
    (`_face_for`); each face in use is subset with fontTools
    to the characters set in it, plus a space, as WOFF, and declared as one
    `@font-face` under `FIGURE_FONT`, the family the figure already names.
    A figure with no text is returned unchanged.

    Known limits: text inside `<defs>` drawn through `<use>` is not seen,
    since `<defs>` is skipped; a weight or style set by a `<style>` class
    rule is not read, only attributes and `style` properties; and 700
    italic sets in the one italic face, which is 400.

    Raises:
        FileNotFoundError: a face the figure uses is missing from `font_dir`.
        ValueError: a `<text>` resolves to an unrecognized weight or style.
    """
    used = _faces_and_text(svg)
    if not used:
        return svg
    rules = []
    for (weight, style), chars in sorted(used.items()):
        font_path = font_dir / FACE_FILES[(weight, style)]
        if not font_path.is_file():
            raise FileNotFoundError(
                f"{font_path.name} not found in {font_dir}; the figure's text "
                f"uses the {weight} {style} face"
            )
        data = base64.b64encode(_subset_woff(font_path, chars)).decode("ascii")
        rules.append(
            f'@font-face {{ font-family: "{FIGURE_FONT}"; font-weight: {weight}; '
            f"font-style: {style}; src: url(data:font/woff;base64,{data}); }}"
        )
    return _insert_after_root(svg, "<style>" + "\n".join(rules) + "</style>")


def epub_width_em(svg: str) -> float:
    """The figure's EPUB width in em, at the one scale.

    The viewBox width times `PT_PER_UNIT` is the figure's printed width in
    points; over the body's nominal `BODY_PT` that is its width relative to
    the body font, which is width / 15 at the book's scale.
    """
    width, _ = viewbox(svg)
    return width * PT_PER_UNIT / BODY_PT
