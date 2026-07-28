"""Tests for the handbook-artifact renderer's pure HTML transforms."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "render_handbook_artifact",
    Path(__file__).resolve().parents[2] / "scripts" / "render_handbook_artifact.py",
)
assert _spec is not None and _spec.loader is not None
rh = importlib.util.module_from_spec(_spec)
# Registering the module before exec is required once the module defines a
# dataclass: with `from __future__ import annotations`, dataclasses resolves
# field types via `sys.modules[cls.__module__]`, which is None (and raises)
# for a module that was never registered under its own name.
sys.modules[_spec.name] = rh
_spec.loader.exec_module(rh)


def test_rewrite_links_maps_known_targets():
    html = '<a href="lifecycle.md">Part 1</a> and <a href="evaluation.md">Part 5</a>'
    out, unmapped = rh.rewrite_links(
        html, {"lifecycle.md": "#p1", "evaluation.md": "#p5"}
    )
    assert 'href="#p1"' in out
    assert 'href="#p5"' in out
    assert unmapped == []


def test_rewrite_links_preserves_link_text_and_handles_fragment():
    html = '<a href="evaluation.md#loop">the loop</a>'
    out, unmapped = rh.rewrite_links(html, {"evaluation.md": "#p5"})
    assert out == '<a href="#p5">the loop</a>'  # anchor collapsed, text untouched
    assert unmapped == []


def test_rewrite_links_flags_unmapped_md_and_ignores_external():
    html = '<a href="orphan.md">x</a> <a href="https://example.com">y</a>'
    out, unmapped = rh.rewrite_links(html, {"lifecycle.md": "#p1"})
    assert 'href="orphan.md"' in out  # unknown .md left as-is
    assert 'href="https://example.com"' in out  # non-.md untouched
    assert unmapped == ["orphan.md"]


def test_wrap_tables_adds_overflow_container():
    out = rh.wrap_tables("<table><tr><td>a</td></tr></table>")
    assert out == '<div class="tablewrap"><table><tr><td>a</td></tr></table></div>'


def test_mark_task_items_unchecked_and_checked():
    assert rh.mark_task_items("<li>[ ] do it</li>") == '<li class="task">do it</li>'
    assert rh.mark_task_items("<li>[x] done</li>") == '<li class="task done">done</li>'
    assert rh.mark_task_items("<li>[X] done</li>") == '<li class="task done">done</li>'


def test_mark_task_items_leaves_plain_items():
    assert rh.mark_task_items("<li>ordinary bullet</li>") == "<li>ordinary bullet</li>"


def test_post_process_applies_all_transforms():
    html = '<a href="lifecycle.md">L</a><table></table><li>[ ] check</li>'
    out, unmapped = rh.post_process(html, {"lifecycle.md": "#p1"})
    assert 'href="#p1"' in out
    assert '<div class="tablewrap"><table>' in out
    assert '<li class="task">check</li>' in out
    assert unmapped == []


def test_render_nav_marks_intro_and_numbers_parts():
    nav = rh.render_nav(
        [("top", "README", "Overview"), ("p1", "lifecycle", "Lifecycle")]
    )
    assert 'href="#top"' in nav and 'class="lead"' in nav
    assert "§" in nav  # intro glyph
    assert 'href="#p1"' in nav and "01" in nav  # first part is 01


def test_render_nav_marks_coda_with_glyph_not_number():
    nav = rh.render_nav(
        [("p8", "security-supply-chain", "Security"), ("coda", "coda", "Coda")]
    )
    assert 'href="#coda"' in nav
    assert "∎" in nav  # coda glyph, not a part number
    assert "01" not in nav.split("#coda")[1]  # the coda row carries no number


def test_render_nav_marks_troubleshooting_with_glyph_not_number():
    nav = rh.render_nav(
        [
            ("p9", "security-supply-chain", "Security"),
            ("troubleshooting", "troubleshooting", "Troubleshooting"),
            ("coda", "coda", "Coda"),
        ]
    )
    assert 'href="#troubleshooting"' in nav
    assert "✚" in nav  # unnumbered companion glyph, like the coda's ∎
    row = nav.split("#troubleshooting")[1].split("#coda")[0]
    assert "01" not in row  # the companion row carries no part number


def test_build_renders_verbatim_section(tmp_path: Path):
    pytest.importorskip("markdown")
    (tmp_path / "README.md").write_text(
        "# Handbook\n\n"
        "See [self](README.md).\n\n"
        "| A | B |\n|---|---|\n| 1 | 2 |\n\n"
        "- [ ] first\n- [x] second\n"
    )
    html = rh.build(tmp_path, parts=[("top", "README", "Overview")])
    assert '<section id="top" class="part intro">' in html
    assert "<h1>Handbook</h1>" in html
    assert 'href="#top"' in html  # self .md link rewritten
    assert '<div class="tablewrap"><table>' in html
    assert '<li class="task">first</li>' in html
    assert '<li class="task done">second</li>' in html
    assert 'href="README.md"' not in html  # no residual .md link


def test_to_ascii_entities_escapes_non_ascii():
    assert (
        rh.to_ascii_entities("A · § ◐ → ≥") == "A &#183; &#167; &#9680; &#8594; &#8805;"
    )
    assert rh.to_ascii_entities("plain ascii") == "plain ascii"


def test_build_output_is_pure_ascii(tmp_path: Path):
    pytest.importorskip("markdown")
    (tmp_path / "README.md").write_text("# Heading\n\n- [ ] a\n")
    html = rh.build(tmp_path, parts=[("top", "README", "Overview")])
    html.encode("ascii")  # must not raise: output carries no raw non-ASCII
    assert "&#183;" in html  # the brand middle dot rendered as an entity


def test_extract_d2_blocks_replaces_fence_with_placeholder():
    md = 'intro\n\n```d2 title="The TDD loop"\na -> b\n```\n\noutro\n'
    out, blocks = rh.extract_d2_blocks(md, "implementation-disciplines")
    assert '<div class="d2ph" data-i="0"></div>' in out
    assert "```d2" not in out
    assert len(blocks) == 1
    assert blocks[0].title == "The TDD loop"
    assert blocks[0].source == "a -> b\n"


def test_extract_d2_blocks_numbers_multiple_fences():
    md = '```d2 title="One"\na\n```\n\ntext\n\n```d2 title="Two"\nb\n```\n'
    out, blocks = rh.extract_d2_blocks(md, "x")
    assert [b.index for b in blocks] == [0, 1]
    assert [b.title for b in blocks] == ["One", "Two"]
    assert 'data-i="0"' in out
    assert 'data-i="1"' in out


def test_extract_d2_blocks_requires_a_title():
    with pytest.raises(ValueError, match="title"):
        rh.extract_d2_blocks("```d2\na -> b\n```\n", "lifecycle")


def test_extract_d2_blocks_leaves_other_fences_alone():
    md = "```python\nprint(1)\n```\n"
    out, blocks = rh.extract_d2_blocks(md, "x")
    assert out == md
    assert blocks == []


def test_prepare_svg_sizes_from_viewbox_and_names_the_figure():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 342 815"><g/></svg>'
    out = rh.prepare_svg(svg, "dcap-three-layer-model-0")
    assert 'width="342"' in out
    assert 'height="815"' in out
    assert 'role="img"' in out
    assert 'aria-labelledby="dcap-three-layer-model-0"' in out
    assert out.endswith("<g/></svg>")


def test_prepare_svg_rejects_output_without_a_viewbox():
    with pytest.raises(ValueError, match="viewBox"):
        rh.prepare_svg("<svg><g/></svg>", "dcap-x-0")


def test_diagram_figure_carries_both_variants_and_one_caption():
    block = rh.D2Block(index=0, title="The three layers", source="a -> b\n")
    svg = '<svg viewBox="0 0 10 20"></svg>'
    out = rh.diagram_figure("three-layer-model", block, svg, svg)
    assert out.count("<svg") == 2
    assert 'class="d2var d2-light"' in out
    assert 'class="d2var d2-dark"' in out
    assert (
        '<figcaption id="dcap-three-layer-model-0">The three layers</figcaption>' in out
    )


def test_substitute_d2_replaces_placeholders_by_index():
    html = (
        '<p>a</p><div class="d2ph" data-i="1"></div><div class="d2ph" data-i="0"></div>'
    )
    out = rh.substitute_d2(
        html, {0: "<figure>zero</figure>", 1: "<figure>one</figure>"}
    )
    assert out == "<p>a</p><figure>one</figure><figure>zero</figure>"


def test_substitute_d2_raises_on_a_missing_figure():
    with pytest.raises(ValueError, match="3"):
        rh.substitute_d2('<div class="d2ph" data-i="3"></div>', {})


def test_count_em_dashes_sees_the_entity_form():
    # to_ascii_entities runs before the counter, so by then the literal
    # character is already gone; counting only chr(8212) is what made the
    # handbook's em-dash gate vacuous.
    assert rh.count_em_dashes("a — b") == 1
    assert rh.count_em_dashes(rh.to_ascii_entities("a — b")) == 1
    assert rh.count_em_dashes("a, b") == 0


def test_d2_preludes_cover_both_variants_and_clear_the_canvas():
    assert set(rh.D2_PRELUDES) == {"light", "dark"}
    for prelude in rh.D2_PRELUDES.values():
        assert prelude.startswith("style.fill: transparent")
