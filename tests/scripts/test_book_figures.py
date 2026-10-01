from __future__ import annotations

import hashlib
import re
from pathlib import Path

import book_figures as bf
import pytest

# The label size, in user units, that prints at 8 pt at the one scale: the
# middle of the 7-9 pt range, derived so the fixtures follow `PT_PER_UNIT`.
L = f"{8 / bf.PT_PER_UNIT:.4g}"
# A label size that prints at 12 pt, above the range at any scale this suite runs at.
BIG = f"{12 / bf.PT_PER_UNIT:.4g}"

# A trimmed, hand-shaped stand-in for what `render_handbook_artifact.run_d2`
# produces in "print" variant: an outer sized `<svg>`, d2's own salted inner
# `<svg>`, a transparent background rect, two `<style>` blocks (one carrying
# an `@font-face` with a base64 font payload shortened to a stand-in, one
# carrying d2's `.shape` CSS), one drawn node (`task.a`, base64
# `dGFzay5h`) as a `<g>` wrapping a rect and a bold label, and the clip mask
# d2 always emits. Its label is set at `L`, the size that prints at 8 pt at the
# one scale, where d2's own seeds set 12 and so print smaller (see `fit_problems`
# on a seed). `PRINT_PALETTE["line"]` is `#8a867a`, `PRINT_PALETTE["ink"]`
# is `#1c2024` (see `render_handbook_artifact.PRINT_PALETTE`).
D2_LIKE = (
    '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"'
    ' data-d2-version="0.7.1" preserveAspectRatio="xMinYMin meet"'
    ' viewBox="0 0 287 587">'
    '<svg class="d2-1314600225 d2-svg" width="287" height="587"'
    ' viewBox="1 1 287 587">'
    '<rect x="1.000000" y="1.000000" width="287.000000" height="587.000000"'
    ' rx="0.000000" fill="transparent" stroke-width="0" />'
    '<style type="text/css"><![CDATA['
    ".d2-1314600225 .text-bold {\n"
    '\tfont-family: "d2-1314600225-font-bold";\n'
    "}\n"
    "@font-face {\n"
    "\tfont-family: d2-1314600225-font-bold;\n"
    '\tsrc: url("data:application/font-woff;base64,AAAA");\n'
    "}]]></style>"
    '<style type="text/css"><![CDATA[.shape {\n'
    "  shape-rendering: geometricPrecision;\n"
    "  stroke-linejoin: round;\n"
    "}]]></style>"
    '<g class="dGFzay5h">'
    '<rect fill="transparent" stroke="#8a867a" style="stroke-width:2;"/>'
    '<text class="text-bold" fill="#1c2024"'
    f' style="text-anchor:middle;font-size:{L}px">Agent A</text>'
    "</g>"
    '<mask id="d2-1314600225" maskUnits="userSpaceOnUse" x="1" y="1"'
    ' width="287" height="587">'
    '<rect x="1" y="1" width="287" height="587" fill="white"></rect>'
    "</mask>"
    "</svg></svg>"
)

# The same drawing after an illustrator opens the seed in Inkscape and saves
# it: Inkscape's own namespaces, a `<sodipodi:namedview>` view-state element,
# an RDF `<metadata>` block, and the label re-expressed with plain style
# properties (`font-weight:bold` in place of d2's `class="text-bold"`), the
# way `clean_seed_svg` + a manual save would leave it.
INKSCAPE_LIKE = (
    '<svg xmlns="http://www.w3.org/2000/svg"'
    ' xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"'
    ' xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.0.dtd"'
    ' width="287" height="587" viewBox="0 0 287 587" version="1.1"'
    f' font-family="{bf.FIGURE_FONT}">'
    '<sodipodi:namedview pagecolor="#ffffff" bordercolor="#666666"'
    ' inkscape:zoom="1" fill="#f7f6f2"/>'
    "<metadata>"
    '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
    "<rdf:Description/></rdf:RDF>"
    "</metadata>"
    '<g inkscape:label="Layer 1" inkscape:groupmode="layer" id="codebase-structure-0-task-a">'
    '<rect x="32" y="38" width="87" height="61" fill="none" stroke="#8a867a"'
    ' style="stroke-width:2;"/>'
    '<text x="75.5" y="72.5"'
    f' style="text-anchor:middle;font-size:{L}px;font-weight:bold;fill:#1c2024">'
    "Agent A</text>"
    "</g>"
    "</svg>"
)


def test_source_hash_is_sha256_of_the_body():
    assert bf.source_hash("a -> b\n") == hashlib.sha256(b"a -> b\n").hexdigest()


def test_stamp_then_read_the_hash():
    stamped = bf.stamp_hash('<svg viewBox="0 0 1 1"></svg>', "ab" * 32)
    assert bf.recorded_hash(stamped) == "ab" * 32


def test_stamping_replaces_an_old_hash():
    once = bf.stamp_hash('<svg viewBox="0 0 1 1"></svg>', "a" * 64)
    twice = bf.stamp_hash(once, "b" * 64)
    assert bf.recorded_hash(twice) == "b" * 64
    assert twice.count("data-source-sha256") == 1


def test_an_unstamped_figure_records_no_hash():
    assert bf.recorded_hash('<svg viewBox="0 0 1 1"></svg>') is None


def test_clean_seed_drops_embedded_fonts_and_styles():
    out = bf.clean_seed_svg(D2_LIKE, "codebase-structure-0")
    assert "@font-face" not in out and "font-woff" not in out and "<style" not in out
    assert f'font-family="{bf.FIGURE_FONT}"' in out


def test_clean_seed_turns_text_classes_into_attributes():
    out = bf.clean_seed_svg(D2_LIKE, "codebase-structure-0")
    assert 'class="text-bold"' not in out
    assert 'font-weight="700"' in out


def test_clean_seed_replaces_the_salt_and_the_base64_names():
    out = bf.clean_seed_svg(D2_LIKE, "codebase-structure-0")
    assert "1314600225" not in out
    assert 'id="codebase-structure-0-task-a"' in out
    assert "dGFzay5h" not in out


def test_clean_seed_keeps_a_user_class_beside_the_base64_group_name():
    # d2 writes `class="<base64> <user class>"` for a node carrying a
    # `{class: ...}` (as README-0's `s`/`h` classes and `d2_icon_classes`'
    # `step`/`human` do), unlike the base64-alone form `D2_LIKE` covers.
    # `aWRlYQ==` is `idea`'s base64.
    svg = '<svg viewBox="0 0 1 1"><g class="aWRlYQ== s"></g></svg>'
    out = bf.clean_seed_svg(svg, "x-0")
    assert '<g id="x-0-idea" class="s">' in out


def test_clean_seed_refuses_an_unknown_text_class():
    with pytest.raises(ValueError, match="text-mono"):
        bf.clean_seed_svg(D2_LIKE.replace("text-bold", "text-mono"), "x-0")


def test_a_figure_inside_the_block_at_8pt_fits():
    assert bf.fit_problems(bf.clean_seed_svg(D2_LIKE, "x-0")) == []


def test_a_figure_wider_than_the_block_does_not_fit():
    wide_w = bf.MAX_VIEWBOX[0] + 1
    wide = D2_LIKE.replace('viewBox="0 0 287 587"', f'viewBox="0 0 {wide_w} 361"', 1)
    assert any("wide" in p for p in bf.fit_problems(wide))


def test_a_label_outside_7_to_9pt_is_reported():
    big = D2_LIKE.replace(f"font-size:{L}px", f"font-size:{BIG}px")
    assert any(BIG in p for p in bf.fit_problems(big))


def test_a_figure_with_no_text_size_is_reported():
    bare = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><text>x</text></svg>'
    assert bf.fit_problems(bare)


def test_a_halved_nested_viewport_width_is_reported():
    shrunk = D2_LIKE.replace(
        '<svg class="d2-1314600225 d2-svg" width="287" height="587"',
        '<svg class="d2-1314600225 d2-svg" width="143.5" height="587"',
    )
    problems = bf.fit_problems(bf.clean_seed_svg(shrunk, "x-0"))
    assert any("nested <svg>" in p and "0.5" in p for p in problems)


def test_a_nested_svg_with_no_width_or_height_is_not_a_scale():
    svg = _sized(f'<svg viewBox="0 0 50 50"><text font-size="{L}">a</text></svg>')
    assert bf.fit_problems(svg) == []


def test_a_nested_svg_with_no_viewbox_is_not_a_scale():
    svg = _sized(f'<svg width="25" height="25"><text font-size="{L}">a</text></svg>')
    assert bf.fit_problems(svg) == []


def test_a_nested_svg_with_unrecognized_dimensions_is_reported():
    svg = _sized(
        '<svg width="50%" height="50%" viewBox="0 0 50 50">'
        f'<text font-size="{L}">a</text></svg>'
    )
    problems = bf.fit_problems(svg)
    assert any("not a recognized size" in p for p in problems)


def test_a_nested_svg_with_unequal_x_and_y_scale_is_reported():
    svg = _sized(
        '<svg width="50" height="25" viewBox="0 0 50 50">'
        f'<text font-size="{L}">a</text></svg>'
    )
    problems = bf.fit_problems(svg)
    assert any("nested <svg>" in p for p in problems)


def test_an_opaque_light_fill_is_reported_and_a_mask_is_not():
    painted = D2_LIKE.replace(
        'fill="transparent" stroke="#8a867a"', 'fill="#f7f6f2" stroke="#8a867a"'
    )
    assert bf.opaque_fill_problems(D2_LIKE) == []
    assert bf.opaque_fill_problems(painted)


def test_a_translucent_tint_is_not_opaque():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 9 9"><path d="M0 0" fill="#ece2cd" fill-opacity="0.15"/></svg>'
    assert bf.opaque_fill_problems(svg) == []


def test_pale_text_fails_contrast_and_ink_passes():
    assert bf.contrast_problems(D2_LIKE) == []
    assert bf.contrast_problems(D2_LIKE.replace('fill="#1c2024"', 'fill="#c3bfb1"'))


def test_the_page_hairline_fails_the_print_stroke_bar():
    assert bf.contrast_ratio("#c3bfb1", bf.PAPER_CREAM) < 3.0
    assert bf.contrast_ratio("#8a867a", bf.PAPER_CREAM) >= 3.0


def test_every_print_palette_colour_holds_its_bar():
    from render_handbook_artifact import PRINT_PALETTE

    for name in ("ink", "ink_soft", "accent_ink"):
        assert bf.contrast_ratio(PRINT_PALETTE[name], bf.PAPER_CREAM) >= 4.5
    for name in ("accent", "line"):
        assert bf.contrast_ratio(PRINT_PALETTE[name], bf.PAPER_CREAM) >= 3.0


def test_an_inkscape_saved_figure_passes_every_check():
    assert bf.fit_problems(INKSCAPE_LIKE) == []
    assert bf.opaque_fill_problems(INKSCAPE_LIKE) == []
    assert bf.contrast_problems(INKSCAPE_LIKE) == []


def test_pale_text_inside_a_filled_group_is_reported():
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><g fill="#c3bfb1"><text>x</text></g></svg>'
    assert bf.contrast_problems(svg) != []


def test_pale_text_under_a_filled_root_is_reported():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" fill="#c3bfb1"><text>x</text></svg>'
    assert bf.contrast_problems(svg) != []


def test_ink_text_with_its_own_fill_overrides_a_pale_group():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg"><g fill="#c3bfb1">'
        '<text fill="#1c2024">x</text></g></svg>'
    )
    assert bf.contrast_problems(svg) == []


def test_a_shape_inheriting_a_light_fill_from_a_translucent_group_is_reported():
    # The group's own fill-opacity makes the group itself pass (it is
    # translucent), but the rect re-asserts full opacity for itself while
    # still inheriting the group's pale colour, so the rect alone should be
    # reported; a check that only reads an element's own `fill` misses this
    # because the rect never sets `fill` at all.
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<g fill="#f7f6f2" fill-opacity="0.1">'
        '<rect fill-opacity="1" width="1" height="1"/></g></svg>'
    )
    assert bf.opaque_fill_problems(svg) != []


def test_an_image_does_not_paint_its_inherited_fill_but_a_rect_does():
    # An <image> paints its bitmap, not `fill`/`stroke`, so a pale fill it
    # inherits is furniture the check should not judge; the same fill
    # inherited onto a <rect> in an identical tree, mirroring the group
    # shape above, is a real problem and must still be reported. The
    # group's own low fill-opacity makes the group itself pass, isolating
    # the leaf's own re-asserted full opacity as the only thing in play.
    def tree(tag: str) -> str:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<g fill="#f7f6f2" fill-opacity="0.1">'
            f'<{tag} fill-opacity="1" width="1" height="1"/></g></svg>'
        )

    assert bf.opaque_fill_problems(tree("image")) == []
    assert bf.opaque_fill_problems(tree("rect")) != []


def test_a_shape_inheriting_a_pale_stroke_from_a_translucent_group_is_reported():
    # Mirrors the fill case above: the group's own stroke-opacity makes the
    # group itself pass, but the rect re-asserts full opacity for itself
    # while still inheriting the group's under-contrast stroke colour and no
    # stroke of its own.
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<g stroke="#c3bfb1" stroke-opacity="0.1">'
        '<rect stroke-opacity="1" stroke-width="1" fill="none" width="1" height="1"/>'
        "</g></svg>"
    )
    assert bf.contrast_problems(svg) != []


def test_text_inheriting_a_pale_stroke_is_reported_once_not_skipped():
    # A <text> can carry a stroke like any other shape, so an inherited pale
    # stroke on it must be judged by the same rule, not silently skipped
    # because it is text: exactly one problem names the <text>'s own inherited
    # stroke (the enclosing <g>, which declares that stroke itself, is a
    # separate, correctly reported element, not a duplicate of the text's).
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg"><g stroke="#c3bfb1">'
        '<text fill="#1c2024">x</text></g></svg>'
    )
    problems = bf.contrast_problems(svg)
    text_stroke_problems = [p for p in problems if "stroke" in p and "<text>" in p]
    assert len(text_stroke_problems) == 1


FONTS = Path(__file__).resolve().parents[2] / "fonts" / "source-sans-3"


def test_embed_fonts_carries_only_the_faces_used():
    out = bf.embed_fonts(bf.clean_seed_svg(D2_LIKE, "x-0"), FONTS)
    assert out.count("@font-face") == 1
    assert "font-weight:700" in out.replace(" ", "")


def test_embed_fonts_reads_an_inkscape_style_weight():
    out = bf.embed_fonts(INKSCAPE_LIKE, FONTS)
    assert "font-weight:700" in out.replace(" ", "")


def test_the_embedded_face_is_a_small_subset():
    out = bf.embed_fonts(bf.clean_seed_svg(D2_LIKE, "x-0"), FONTS)
    assert len(out) < 40_000


def test_embed_fonts_resolves_weight_and_style_through_ancestors():
    # A funnel's 600-weight labels snap to the bold face, and an italic set
    # on a group reaches the text inside it, as Inkscape leaves it.
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
        '<text font-weight="600">a</text>'
        '<g style="font-style:italic"><text>b</text></g>'
        "</svg>"
    )
    faces = sorted(
        re.findall(
            r"font-weight:\s*(\d+);\s*font-style:\s*(\w+)", bf.embed_fonts(svg, FONTS)
        )
    )
    assert faces == [("400", "italic"), ("700", "normal")]


def test_embed_fonts_leaves_a_textless_figure_alone():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><rect/></svg>'
    assert bf.embed_fonts(svg, FONTS) == svg


def test_embed_fonts_names_the_font_directory_when_a_face_is_missing(tmp_path):
    with pytest.raises(FileNotFoundError, match=re.escape(str(tmp_path))):
        bf.embed_fonts(INKSCAPE_LIKE, tmp_path)


def test_the_epub_width_keeps_the_one_scale():
    # A figure as wide as the block is the block's width in body ems.
    full = f'<svg viewBox="0 0 {bf.MAX_VIEWBOX[0]} 100"></svg>'
    assert bf.epub_width_em(full) == pytest.approx(bf.TEXT_BLOCK_PT[0] / bf.BODY_PT)


def _text_svg(body: str) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">{body}</svg>'


def test_a_bold_tspan_sets_its_own_characters_in_the_bold_face():
    # Inkscape's habit: the weight sits on the tspan, not on the <text>, and
    # the tspan's tail belongs to the <text>'s own face.
    svg = _text_svg(
        f'<text style="font-size:{L}px"><tspan style="font-weight:bold">Qz</tspan>'
        " ab</text>"
    )
    assert bf._faces_and_text(svg) == {
        (700, "normal"): {"Q", "z"},
        (400, "normal"): {" ", "a", "b"},
    }


def test_a_nested_tspan_can_reset_to_the_normal_weight():
    svg = _text_svg(
        '<text font-weight="700">A<tspan>B<tspan style="font-weight:normal">c'
        "</tspan>D</tspan>E</text>"
    )
    assert bf._faces_and_text(svg) == {
        (700, "normal"): {"A", "B", "D", "E"},
        (400, "normal"): {"c"},
    }


def test_an_italic_tspan_sets_in_the_italic_face():
    svg = _text_svg('<text>x<tspan font-style="italic">yi</tspan></text>')
    assert bf._faces_and_text(svg) == {
        (400, "normal"): {"x"},
        (400, "italic"): {"y", "i"},
    }


def test_a_tspan_face_is_embedded():
    svg = _text_svg(
        f'<text style="font-size:{L}px"><tspan style="font-weight:bold">Qz</tspan>'
        " ab</text>"
    )
    out = bf.embed_fonts(svg, FONTS).replace(" ", "")
    assert out.count("@font-face") == 2
    assert "font-weight:700;font-style:normal" in out
    assert "font-weight:400;font-style:normal" in out


def _sized(body: str) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">{body}</svg>'


def test_a_scale_on_a_group_holding_text_is_reported():
    # L units prints at 8 pt only at the one scale; scale(2) prints it at 16.
    svg = _sized(f'<g transform="scale(2)"><text font-size="{L}">a</text></g>')
    assert any("scale(2)" in p for p in bf.fit_problems(svg))


def test_a_matrix_on_the_text_itself_is_reported():
    svg = _sized(f'<text transform="matrix(1 0 0 1 5 5)" font-size="{L}">a</text>')
    assert any("matrix" in p for p in bf.fit_problems(svg))


def test_a_pure_translate_passes():
    svg = _sized(
        '<g transform="translate(10, 20)"><text transform="translate(3)"'
        f' font-size="{L}">a</text></g>'
    )
    assert bf.fit_problems(svg) == []


def test_a_transform_on_a_textless_shape_is_not_a_fit_problem():
    svg = _sized(
        '<rect transform="rotate(45)" width="1" height="1"/>'
        f'<text font-size="{L}">a</text>'
    )
    assert bf.fit_problems(svg) == []


def test_a_text_inherits_its_font_size_from_its_group():
    svg = _sized(f'<g style="font-size:{L}px"><text>a</text></g>')
    assert bf.fit_problems(svg) == []


def test_an_inherited_out_of_range_size_is_reported():
    svg = _sized(f'<g font-size="{BIG}"><text>a</text></g>')
    assert any(BIG in p for p in bf.fit_problems(svg))


def test_a_bare_text_beside_a_sized_one_is_reported():
    svg = _sized(f'<text font-size="{L}">a</text><text>b</text>')
    problems = bf.fit_problems(svg)
    assert len(problems) == 1 and "no font-size" in problems[0]


def test_a_near_opaque_pale_text_is_reported():
    svg = _sized(f'<text font-size="{L}" fill="#eeeeee" fill-opacity="0.99">a</text>')
    assert bf.contrast_problems(svg) != []


def test_the_funnels_accent_wash_passes():
    from render_handbook_artifact import PRINT_PALETTE, PRINT_WASH_OPACITY

    svg = _sized(
        f'<path d="M0 0" fill="{PRINT_PALETTE["accent"]}"'
        f' fill-opacity="{PRINT_WASH_OPACITY}"/>'
    )
    assert bf.opaque_fill_problems(svg) == []


def test_a_near_opaque_pale_fill_is_reported():
    svg = _sized('<rect width="1" height="1" fill="#eeeeee" fill-opacity="0.99"/>')
    assert bf.opaque_fill_problems(svg) != []


def test_an_svg2_percentage_opacity_reads_as_its_fraction():
    # "20%" is SVG 2's own spelling of 0.2 (SVG 1.1 only allows a bare
    # number), and 0.2 sits at TINT_MAX_ALPHA, the pass/fail boundary, so a
    # fill that reads "20%" as 1.0 (the old silent default) would fail here
    # while the correct 0.2 reading passes.
    svg = _sized('<rect width="1" height="1" fill="#eeeeee" fill-opacity="20%"/>')
    assert bf.opaque_fill_problems(svg) == []


def test_an_unparseable_fill_opacity_is_reported_naming_element_and_value():
    svg = _sized('<rect width="1" height="1" fill="#eeeeee" fill-opacity="abc"/>')
    problems = bf.opaque_fill_problems(svg)
    assert len(problems) == 1
    assert "abc" in problems[0] and "<rect>" in problems[0]


def test_an_unparseable_opacity_is_reported_by_contrast_problems_too():
    svg = _sized(
        '<rect width="1" height="1" stroke="#c3bfb1" stroke-width="1" '
        'fill="none" stroke-opacity="abc"/>'
    )
    problems = bf.contrast_problems(svg)
    assert len(problems) == 1
    assert "abc" in problems[0] and "<rect>" in problems[0]


def test_an_unparseable_group_opacity_is_named_opacity_not_fill_opacity():
    # The group `opacity` attribute, not `fill-opacity`, is what failed to
    # parse here, so the report must name it as such rather than blaming an
    # attribute the element never carries; and it should surface once per
    # channel, not once per (poisoned) alpha computation.
    svg = _sized('<rect width="1" height="1" fill="#eeeeee" opacity="abc"/>')
    problems = bf.opaque_fill_problems(svg)
    assert len(problems) == 1
    assert "opacity" in problems[0] and "<rect>" in problems[0]
    assert "fill-opacity" not in problems[0]


def test_ink_text_under_a_faded_group_is_blended_and_judged():
    # Ink passes on its own; under a 0.3 group opacity it prints as a pale grey.
    ink = f'<text font-size="{L}" fill="#1c2024">a</text>'
    assert bf.contrast_problems(_sized(ink)) == []
    assert bf.contrast_problems(_sized(f'<g opacity="0.3">{ink}</g>')) != []


def test_group_opacity_multiplies_down_the_tree():
    # Two nested 0.8 groups composite to 0.64, which still holds ink at 4.7:1;
    # a third 0.5 group takes it to 0.32, under the bar, only if all three
    # multiply rather than the nearest one standing alone.
    ink = f'<text font-size="{L}" fill="#1c2024">a</text>'
    two = f'<g opacity="0.8"><g opacity="0.8">{ink}</g></g>'
    three = f'<g opacity="0.5">{two}</g>'
    assert bf.contrast_problems(_sized(two)) == []
    assert bf.contrast_problems(_sized(three)) != []


def test_a_fully_transparent_stroke_paints_nothing():
    svg = _sized('<rect stroke="#eeeeee" stroke-opacity="0" fill="none"/>')
    assert bf.contrast_problems(svg) == []


def test_a_pale_style_fill_wins_over_an_ink_fill_attribute():
    svg = _sized(f'<text font-size="{L}" fill="#1c2024" style="fill:#c3bfb1">a</text>')
    assert bf.contrast_problems(svg) != []


def test_an_ink_style_fill_wins_over_a_pale_fill_attribute():
    svg = _sized(f'<text font-size="{L}" fill="#c3bfb1" style="fill:#1c2024">a</text>')
    assert bf.contrast_problems(svg) == []


def test_a_bad_transform_and_a_bad_size_on_one_group_are_both_reported():
    svg = _sized(f'<g transform="scale(2)" font-size="{BIG}"><text>a</text></g>')
    problems = bf.fit_problems(svg)
    assert any("scale(2)" in p for p in problems)
    assert any(f"font-size {BIG}" in p for p in problems)


def test_an_rgb_function_colour_is_read_as_its_hex():
    ink = _sized('<path d="M0 0" fill="none" stroke="rgb(28, 32, 36)"/>')
    pale = _sized('<path d="M0 0" fill="none" stroke="rgb(195, 191, 177)"/>')
    assert bf.contrast_problems(ink) == []
    assert bf.contrast_problems(pale) != []


def test_an_rgba_alpha_folds_into_the_tint_rule():
    # White at an rgba() alpha of 0.15 is a tint; at 0.9 it prints as a surface.
    tint = _sized('<rect width="1" height="1" fill="rgba(255,255,255,0.15)"/>')
    surface = _sized('<rect width="1" height="1" fill="rgba(255,255,255,0.9)"/>')
    assert bf.opaque_fill_problems(tint) == []
    assert bf.opaque_fill_problems(surface) != []


def test_an_rgba_alpha_folds_into_the_contrast_rule():
    # Ink that passes opaque fails once an rgba() alpha greys it out.
    faded = _sized(f'<text font-size="{L}" fill="rgba(28,32,36,0.3)">a</text>')
    assert bf.contrast_problems(faded) != []


def test_an_unreadable_rgba_alpha_is_reported():
    svg = _sized('<path d="M0 0" fill="none" stroke="rgba(0,0,0,lots)"/>')
    assert bf.contrast_problems(svg) != []


def test_a_faint_texture_stroke_is_not_judged_and_a_faded_line_is():
    # A hand-drawn figure's shading: rgba alpha 0.14 under opacity 0.4.
    texture = _sized(
        '<path d="M0 0" fill="none" stroke="rgba(0,0,0,0.14)" opacity="0.4"/>'
    )
    # Above TEXTURE_MAX_ALPHA, a pale line is a line and is held to 3:1.
    faded = _sized('<path d="M0 0" fill="none" stroke="#c3bfb1" opacity="0.3"/>')
    assert bf.contrast_problems(texture) == []
    assert bf.contrast_problems(faded) != []


def test_a_white_panel_at_half_opacity_is_reported():
    # White at 0.5 over cream prints as #fbf8ee, a visible pale panel.
    svg = _sized('<rect width="1" height="1" fill="#ffffff" fill-opacity="0.5"/>')
    assert bf.opaque_fill_problems(svg) != []
