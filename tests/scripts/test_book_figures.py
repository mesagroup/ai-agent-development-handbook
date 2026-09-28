from __future__ import annotations

import hashlib

import book_figures as bf
import pytest

# A trimmed, hand-shaped stand-in for what `render_handbook_artifact.run_d2`
# produces in "print" variant: an outer sized `<svg>`, d2's own salted inner
# `<svg>`, a transparent background rect, two `<style>` blocks (one carrying
# an `@font-face` with a base64 font payload shortened to a stand-in, one
# carrying d2's `.shape` CSS), one drawn node (`task.a`, base64
# `dGFzay5h`) as a `<g>` wrapping a rect and a bold label, and the clip mask
# d2 always emits. `PRINT_PALETTE["line"]` is `#8a867a`, `PRINT_PALETTE["ink"]`
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
    ' style="text-anchor:middle;font-size:12px">Agent A</text>'
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
    ' style="text-anchor:middle;font-size:12px;font-weight:bold;fill:#1c2024">'
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


def test_clean_seed_refuses_an_unknown_text_class():
    with pytest.raises(ValueError, match="text-mono"):
        bf.clean_seed_svg(D2_LIKE.replace("text-bold", "text-mono"), "x-0")


def test_a_figure_inside_the_block_at_8pt_fits():
    assert bf.fit_problems(bf.clean_seed_svg(D2_LIKE, "x-0")) == []


def test_a_figure_wider_than_the_block_does_not_fit():
    wide = D2_LIKE.replace('viewBox="0 0 287 587"', 'viewBox="0 0 424 361"', 1)
    assert any("wide" in p for p in bf.fit_problems(wide))


def test_a_label_outside_7_to_9pt_is_reported():
    big = D2_LIKE.replace("font-size:12px", "font-size:16px")
    assert any("16" in p for p in bf.fit_problems(big))


def test_a_figure_with_no_text_size_is_reported():
    bare = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><text>x</text></svg>'
    assert bf.fit_problems(bare)


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
