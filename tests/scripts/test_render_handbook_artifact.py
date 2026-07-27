"""Tests for the handbook-artifact renderer's pure HTML transforms."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "render_handbook_artifact",
    Path(__file__).resolve().parents[2] / "scripts" / "render_handbook_artifact.py",
)
assert _spec is not None and _spec.loader is not None
rh = importlib.util.module_from_spec(_spec)
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
