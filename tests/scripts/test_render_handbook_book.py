from __future__ import annotations

from pathlib import Path

import pytest
import render_handbook_artifact as rh
import render_handbook_book as rb


def test_book_linkmap_points_a_bare_part_link_at_its_first_heading():
    parts = [("top", "README", "Overview"), ("p1", "lifecycle", "Lifecycle")]
    first = {"README": "README-handbook", "lifecycle": "lifecycle-part-1"}
    assert rb.book_linkmap(parts, first) == {
        "README.md": "#README-handbook",
        "lifecycle.md": "#lifecycle-part-1",
    }


def test_book_linkmap_refuses_a_part_with_no_heading():
    parts = [("top", "README", "Overview"), ("p1", "empty", "Empty")]
    with pytest.raises(ValueError, match=r"empty\.md"):
        rb.book_linkmap(parts, {"README": "README-handbook"})


def test_first_heading_ids_reads_each_parts_first_heading(tmp_path: Path):
    pytest.importorskip("markdown")
    (tmp_path / "README.md").write_text("# Handbook\n\n## One\n")
    (tmp_path / "later.md").write_text("# Later\n")
    parts = [("top", "README", "Overview"), ("p1", "later", "Later")]
    assert rb.first_heading_ids(tmp_path, parts) == {
        "README": "README-handbook",
        "later": "later-later",
    }


def test_first_heading_ids_leaves_out_a_part_with_no_heading(tmp_path: Path):
    pytest.importorskip("markdown")
    (tmp_path / "empty.md").write_text("just text\n")
    assert rb.first_heading_ids(tmp_path, [("p1", "empty", "Empty")]) == {}


def test_listing_markup_escapes_the_source_and_keeps_the_title():
    block = rh.DiagramBlock(index=0, kind="d2", title="A & B", source="a -> b: <x>\n")
    html = rb.listing_markup(block)
    assert "<pre><code>a -&gt; b: &lt;x&gt;\n</code></pre>" in html
    assert "<figcaption>A &amp; B</figcaption>" in html


def test_book_html_substitutes_every_placeholder_and_wraps_no_section():
    block = rh.DiagramBlock(index=0, kind="d2", title="T", source="a -> b\n")
    part = rh.AssembledPart(
        anchor="p1",
        stem="lifecycle",
        html='<h1 id="lifecycle-x">X</h1>\n<div class="dgph" data-i="0"></div>',
        blocks=[block],
    )
    html = rb.book_html([part])
    assert 'class="dgph"' not in html
    assert "<section" not in html
    assert '<h1 id="lifecycle-x">X</h1>' in html
    assert html.startswith("<!DOCTYPE html>")
    assert f"<title>{rb.TITLE}</title>" in html


def test_book_identifier_is_a_stable_urn_uuid():
    first = rb.book_identifier(rb.TITLE)
    assert first == rb.book_identifier(rb.TITLE)
    assert first.startswith("urn:uuid:")
    assert first != rb.book_identifier("Another title")


def test_book_metadata_carries_what_epubcheck_requires_and_names_no_holder():
    meta = rb.book_metadata("2026-09-28")
    assert meta.startswith("---\n") and meta.rstrip().endswith("---")
    assert f"title: {rb.TITLE!r}" in meta
    assert f"creator: {rb.CREATOR!r}" in meta
    assert "lang: 'en'" in meta
    assert "date: '2026-09-28'" in meta
    assert f"identifier: {rb.book_identifier(rb.TITLE)!r}" in meta
    assert "CC BY 4.0" in meta
    assert "©" not in meta and "Copyright" not in meta


def test_epub_command_reads_html_with_smart_quotes_and_splits_on_parts(tmp_path: Path):
    cmd = rb.epub_command(
        tmp_path / "book.html",
        tmp_path / "meta.yaml",
        tmp_path / "epub.css",
        tmp_path / "out.epub",
    )
    assert cmd[0] == "pandoc"
    assert cmd[cmd.index("-f") + 1] == "html+smart"
    assert cmd[cmd.index("-t") + 1] == "epub3"
    assert "--split-level=1" in cmd
    assert "--toc" in cmd and "--toc-depth=2" in cmd
    assert cmd[cmd.index("--metadata-file") + 1] == str(tmp_path / "meta.yaml")
    assert cmd[cmd.index("--css") + 1] == str(tmp_path / "epub.css")
    assert cmd[cmd.index("-o") + 1] == str(tmp_path / "out.epub")
    assert cmd[-1] == str(tmp_path / "book.html")
