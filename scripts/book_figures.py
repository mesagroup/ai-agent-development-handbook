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
text and stroke colour hold its WCAG contrast bar). Nothing here spawns a
process or writes a file; that belongs to the scripts built on top of it.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import re
import xml.etree.ElementTree as ET

FIGURE_FONT = "Source Sans 3"
# SVG user units per point: the book places every figure at one scale, chosen
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

# Elements whose whole subtree never contributes a drawn shape: a clip mask,
# shared definitions, editor metadata, or Inkscape's own view-state element.
# Walking into one of these would misread furniture as figure content, most
# visibly a mask's opaque white rect, which would otherwise fail the opaque-
# fill check for a mask that paints nothing.
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


def viewbox(svg: str) -> tuple[float, float]:
    """The root `<svg>`'s width and height, read from its `viewBox`.

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
    return float(parts[2]), float(parts[3])


def _slugify(decoded: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", decoded.lower()).strip("-")


def _replace_g_class(svg: str, figure_id: str) -> str:
    seen: dict[str, int] = {}

    def repl(match: re.Match[str]) -> str:
        token = match.group(1)
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


# SVG's initial values for `fill`/`fill-opacity`: opaque black, in force at
# the root before anything has set either.
_INITIAL_FILL = "black"
_INITIAL_FILL_OPACITY = "1"


def _walk_fill(
    el: ET.Element, fill: str = _INITIAL_FILL, fill_opacity: str = _INITIAL_FILL_OPACITY
):
    """Yield `(element, effective_fill, effective_fill_opacity)`, inherited.

    `fill` and `fill-opacity` are inherited SVG properties: an element that
    sets neither takes them from its nearest ancestor, all the way up to the
    root's default of opaque black. This is exactly how an Inkscape edit
    leaves colour on a selected group or layer with the text inside left
    unset, so a check reading only an element's own attribute would miss a
    pale colour set on its parent. Skips subtrees in `_SKIP_TAGS`, as `_walk`
    does.
    """
    own_fill = _get_prop(el, "fill")
    effective_fill = own_fill if own_fill is not None else fill
    own_fill_opacity = _get_prop(el, "fill-opacity")
    effective_fill_opacity = (
        own_fill_opacity if own_fill_opacity is not None else fill_opacity
    )
    yield el, effective_fill, effective_fill_opacity
    for child in el:
        if not isinstance(child.tag, str):
            continue  # a comment or processing instruction, not an element
        if _local(child.tag) in _SKIP_TAGS:
            continue
        yield from _walk_fill(child, effective_fill, effective_fill_opacity)


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
    if value is None:
        return 1.0
    try:
        return float(value)
    except ValueError:
        return 1.0


def _prop_opacity(el: ET.Element, name: str) -> float:
    return _parse_opacity(_get_prop(el, name))


def _is_translucent(el: ET.Element, kind: str) -> bool:
    return _prop_opacity(el, "opacity") < 1 or _prop_opacity(el, f"{kind}-opacity") < 1


def _fill_translucent(el: ET.Element, fill_opacity: str) -> bool:
    """Like `_is_translucent(el, "fill")`, but `fill_opacity` is the value
    `_walk_fill` already resolved (own or inherited), not `el`'s own alone.

    The element's own `opacity` (group opacity, never inherited as a colour
    property) is still read directly from `el`.
    """
    return _prop_opacity(el, "opacity") < 1 or _parse_opacity(fill_opacity) < 1


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


def fit_problems(svg: str) -> list[str]:
    """Where a figure would overflow the book's block, in words.

    Checks the root `viewBox` against `MAX_VIEWBOX` and every `font-size`
    (attribute or style, unitless or `px`) against `TEXT_PT_RANGE` once scaled
    by `PT_PER_UNIT`. A figure carrying no `font-size` at all is also a
    problem: nothing here can tell whether its text prints at the right size.
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
    found = False
    for el in _walk(root):
        value = _get_prop(el, "font-size")
        if value is None:
            continue
        found = True
        try:
            units = _parse_font_size(value)
        except ValueError:
            problems.append(f"font-size {value!r} is not a recognized size")
            continue
        pt = units * PT_PER_UNIT
        if pt < lo or pt > hi:
            problems.append(
                f"font-size {_fmt(units)} units is {pt:.1f} pt, "
                f"outside {_fmt(lo)}-{_fmt(hi)} pt"
            )
    if not found:
        problems.append("no font-size found anywhere in the figure")
    return problems


def opaque_fill_problems(svg: str) -> list[str]:
    """Opaque fills, on anything but text, that would wash out on cream paper.

    `fill` is inherited (`_walk_fill`), so a shape left with no fill of its
    own, painted by a colour set on an ancestor group or layer, is checked
    under that inherited colour rather than skipped as unset. A fill counts
    once it is opaque (no `fill-opacity`/`opacity` below 1) and recognized as
    a colour; an unrecognized colour is reported rather than silently passed.
    `text`/`tspan` fills are `contrast_problems`'s concern, held to a
    paper-contrast bar rather than a bare luminance cutoff.
    """
    problems: list[str] = []
    root = ET.fromstring(svg)
    for el, fill, fill_opacity in _walk_fill(root):
        if _local(el.tag) in ("text", "tspan"):
            continue
        if _fill_translucent(el, fill_opacity):
            continue
        try:
            hex_color = _resolve_paint(fill)
        except ValueError:
            problems.append(f"unrecognized fill {fill!r} on <{_local(el.tag)}>")
            continue
        if hex_color is None:
            continue
        if _relative_luminance(hex_color) > 0.5:
            problems.append(
                f"opaque fill {hex_color} on <{_local(el.tag)}> has luminance "
                "over 0.5 and would wash out on the paper"
            )
    return problems


def contrast_problems(svg: str, paper: str = PAPER_CREAM) -> list[str]:
    """Text and strokes that would not hold their contrast bar against `paper`.

    Every opaque `text`/`tspan` fill is held to 4.5:1, every opaque stroke
    (on any element) to 3:1. `fill` is inherited (`_walk_fill`): a `<text>`
    left with no fill of its own, coloured by its ancestor group or layer
    instead, exactly how an Inkscape edit tends to leave it, is checked under
    that inherited colour. `stroke` is not inherited here, since only a
    drawn shape's own stroke paints a line. An unrecognized colour is
    reported rather than silently passed.
    """
    problems: list[str] = []
    root = ET.fromstring(svg)
    for el, fill, fill_opacity in _walk_fill(root):
        tag = _local(el.tag)
        if tag in ("text", "tspan") and not _fill_translucent(el, fill_opacity):
            try:
                hex_color = _resolve_paint(fill)
            except ValueError:
                problems.append(f"unrecognized text fill {fill!r} on <{tag}>")
            else:
                if hex_color is not None:
                    ratio = contrast_ratio(hex_color, paper)
                    if ratio < 4.5:
                        problems.append(
                            f"text fill {hex_color} on <{tag}> contrasts "
                            f"{ratio:.2f}:1 against the paper, under 4.5:1"
                        )
        stroke = _get_prop(el, "stroke")
        if stroke is not None and not _is_translucent(el, "stroke"):
            try:
                hex_color = _resolve_paint(stroke)
            except ValueError:
                problems.append(f"unrecognized stroke {stroke!r} on <{tag}>")
            else:
                if hex_color is not None:
                    ratio = contrast_ratio(hex_color, paper)
                    if ratio < 3.0:
                        problems.append(
                            f"stroke {hex_color} on <{tag}> contrasts "
                            f"{ratio:.2f}:1 against the paper, under 3:1"
                        )
    return problems
