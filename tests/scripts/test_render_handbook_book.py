from __future__ import annotations

import datetime
import re
import shutil
import zipfile
from pathlib import Path

import book_figures as bf
import pytest
import render_handbook_artifact as rh
import render_handbook_book as rb
from render_handbook_artifact import AssembledPart, DiagramBlock


def test_figure_path_names_stem_and_index(tmp_path):
    assert rb.figure_path(tmp_path, "README", 0) == tmp_path / "README-0.svg"


def test_a_funnel_seed_is_stamped_and_vertical():
    block = DiagramBlock(index=0, kind="funnel", title="F", source="A 10\nB 1\n")
    svg = rb.seed_svg("evaluation", block)
    assert bf.recorded_hash(svg) == bf.source_hash(block.source)
    assert 'font-family="Source Sans 3"' in svg
    # A seed is drawn at the funnel's own size, not at the book's one scale,
    # so it is not held to `fit_problems`: it is a starting drawing, and the
    # committed figure drawn from it is what the tree test holds.


def test_seeding_writes_missing_figures_only(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text('# A\n\n```funnel title="F"\nA 10\nB 1\n```\n')
    figures = tmp_path / "figures"
    parts = [("p1", "a", "A")]
    assert rb.seed_figures(docs, figures, parts) == [figures / "a-0.svg"]
    (figures / "a-0.svg").write_text("hand-corrected")
    assert rb.seed_figures(docs, figures, parts) == []
    assert (figures / "a-0.svg").read_text() == "hand-corrected"


@pytest.mark.skipif(
    shutil.which("d2") is None, reason="needs the d2 CLI; CI gains it with #192"
)
def test_a_d2_seed_is_clean_and_transparent():
    block = DiagramBlock(index=0, kind="d2", title="T", source="a -> b\n")
    svg = rb.seed_svg("x", block)
    assert "@font-face" not in svg
    assert bf.opaque_fill_problems(svg) == []


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
    rendered = rh.render_parts(tmp_path, parts)
    assert rb.first_heading_ids(rendered, parts) == {
        "README": "README-handbook",
        "later": "later-later",
    }


def test_first_heading_ids_leaves_out_a_part_with_no_heading(tmp_path: Path):
    pytest.importorskip("markdown")
    (tmp_path / "empty.md").write_text("just text\n")
    parts = [("p1", "empty", "Empty")]
    rendered = rh.render_parts(tmp_path, parts)
    assert rb.first_heading_ids(rendered, parts) == {}


def test_require_h1_first_raises_when_a_parts_first_heading_is_not_h1(tmp_path: Path):
    pytest.importorskip("markdown")
    (tmp_path / "one.md").write_text("# One\n\ntext\n")
    (tmp_path / "two.md").write_text("## Two\n\ntext\n")
    parts = [("p1", "one", "One"), ("p2", "two", "Two")]
    rendered = rh.render_parts(tmp_path, parts)
    with pytest.raises(ValueError, match=r"two\.md: first heading is <h2>, not <h1>"):
        rb.require_h1_first(rendered, parts)


def test_require_h1_first_raises_when_content_precedes_the_h1(tmp_path: Path):
    """A part must open with its <h1>, not merely contain one first.

    A part with prose before its <h1> and no other heading tag before it has
    nothing else for a "first heading tag" search to find, so a check that
    only asked whether that first-found heading was level 1 would pass here
    too - and the leading prose has nothing to split a chapter on, so it
    would silently join the previous one.
    """
    pytest.importorskip("markdown")
    (tmp_path / "one.md").write_text("Leading prose.\n\n# One\n\ntext\n")
    parts = [("p1", "one", "One")]
    rendered = rh.render_parts(tmp_path, parts)
    with pytest.raises(
        ValueError, match=r"one\.md: content precedes its first heading"
    ):
        rb.require_h1_first(rendered, parts)


def test_require_h1_first_passes_a_part_whose_first_heading_is_h1(tmp_path: Path):
    pytest.importorskip("markdown")
    (tmp_path / "one.md").write_text("# One\n\n## Sub\n")
    parts = [("p1", "one", "One")]
    rb.require_h1_first(rh.render_parts(tmp_path, parts), parts)


def test_require_h1_first_leaves_a_headingless_part_alone(tmp_path: Path):
    pytest.importorskip("markdown")
    (tmp_path / "empty.md").write_text("just text\n")
    parts = [("p1", "empty", "Empty")]
    rb.require_h1_first(rh.render_parts(tmp_path, parts), parts)


def test_figure_markup_escapes_the_title():
    block = DiagramBlock(index=2, kind="d2", title='A & <b> "c"', source="")
    html = rb.figure_markup("s", block, 12.5)
    assert 'src="media/s-2.svg"' in html
    assert 'alt="A &amp; &lt;b&gt; &quot;c&quot;"' in html
    assert '<figcaption>A &amp; &lt;b&gt; "c"</figcaption>' in html
    assert "width: 12.50em" in html


def test_a_committed_figure_is_used(tmp_path):
    block = DiagramBlock(index=0, kind="funnel", title="F", source="A 10\nB 1\n")
    (tmp_path / "e-0.svg").write_text("<svg/>")
    assert rb.load_figure(tmp_path, "e", block) == ("<svg/>", False)


def test_a_missing_figure_falls_back_to_its_seed(tmp_path):
    block = DiagramBlock(index=0, kind="funnel", title="F", source="A 10\nB 1\n")
    svg, seeded = rb.load_figure(tmp_path, "e", block)
    assert seeded and bf.recorded_hash(svg) == bf.source_hash(block.source)


def _funnel_part(stem: str, count: int) -> AssembledPart:
    blocks = [DiagramBlock(i, "funnel", f"F{i}", "A 10\nB 1\n") for i in range(count)]
    return AssembledPart(anchor="p1", stem=stem, html="", blocks=blocks)


def test_write_figures_names_each_seeded_fence_on_stderr(tmp_path, capsys):
    # The release workflow (#192) turns this exact line into a failure, so its
    # shape is a contract: one line per fence with no committed figure.
    figures, media = tmp_path / "figures", tmp_path / "media"
    figures.mkdir()
    media.mkdir()
    committed = rb.seed_svg("a", _funnel_part("a", 1).blocks[0])
    (figures / "a-0.svg").write_text(committed, encoding="utf-8")
    parts = [_funnel_part("a", 2), _funnel_part("b", 1)]
    markup, seeded = rb.write_figures(parts, figures, media)
    assert seeded == ["a-1", "b-0"]
    assert capsys.readouterr().err.splitlines() == [
        "NOTE: a-1 has no committed figure; the book uses its seed",
        "NOTE: b-0 has no committed figure; the book uses its seed",
    ]
    assert sorted(p.name for p in media.iterdir()) == ["a-0.svg", "a-1.svg", "b-0.svg"]
    assert set(markup) == {"a", "b"} and set(markup["a"]) == {0, 1}
    assert 'src="media/a-1.svg"' in markup["a"][1]


def test_write_figures_writes_a_transparent_font_embedded_copy(tmp_path):
    figures, media = tmp_path / "figures", tmp_path / "media"
    figures.mkdir()
    media.mkdir()
    _, seeded = rb.write_figures([_funnel_part("a", 1)], figures, media)
    assert seeded == ["a-0"]
    copy = (media / "a-0.svg").read_text(encoding="utf-8")
    # No backing fill: the copy is as transparent as the committed file, so
    # a reading system's page colour shows through it.
    assert bf.opaque_fill_problems(copy) == []
    # ...and that check would see one: a page-coloured panel behind the
    # drawing is reported.
    panelled = re.sub(
        r"(<svg[^>]*>)",
        r'\1<rect width="10" height="10" fill="#f7f6f2"/>',
        copy,
        count=1,
    )
    assert bf.opaque_fill_problems(panelled) != []
    assert "@font-face" in copy
    assert not list(figures.iterdir()), "the build never writes a committed figure"


def test_book_html_places_figures_not_listings():
    part = AssembledPart(
        anchor="p1",
        stem="a",
        html='<h1 id="a-x">X</h1><div class="dgph" data-i="0"></div>',
        blocks=[DiagramBlock(0, "d2", "T", "a -> b")],
    )
    html = rb.book_html([part], {"a": {0: "<figure>F</figure>"}})
    assert "<figure>F</figure>" in html and "<pre>" not in html


def test_restore_task_boxes_marks_open_and_done_items():
    html = (
        '<li class="task">open item</li>'
        '<li class="task done">done item</li>'
        "<li>plain item</li>"
    )
    result = rb.restore_task_boxes(html)
    assert result == (
        '<li><span class="task-box">☐</span>open item</li>'
        '<li><span class="task-box">☒</span>done item</li>'
        "<li>plain item</li>"
    )


def test_restore_task_boxes_reads_mark_task_items_own_output():
    """The two functions share markup that no test held until now.

    `mark_task_items` (in `render_handbook_artifact`) is what actually
    produces `restore_task_boxes`'s input on a real build; the test above
    hand-writes that markup instead, so a change to either function's side of
    the ``<li class="task...">`` contract could drift silently. Feeding one's
    real output to the other is what a pandoc-free CI run can still check.
    """
    html = rh.mark_task_items("<li>[ ] open item</li><li>[x] done item</li>")
    result = rb.restore_task_boxes(html)
    assert '<li><span class="task-box">☐</span>open item</li>' in result
    assert '<li><span class="task-box">☒</span>done item</li>' in result


def test_restore_task_boxes_marks_a_list_of_checklist_items_only():
    checklist = '<ul>\n<li class="task">a</li>\n<li class="task done">b</li>\n</ul>'
    mixed = '<ul>\n<li class="task">a</li>\n<li>b</li>\n</ul>'
    plain = "<ul>\n<li>a</li>\n</ul>"
    nested = '<ul>\n<li>x<ul>\n<li class="task">a</li>\n</ul></li>\n</ul>'
    result = rb.restore_task_boxes(checklist + mixed + plain + nested)
    assert result.count('<div class="checklist">') == 2
    assert result.startswith('<div class="checklist"><ul>\n<li><span')
    assert (
        '<div class="checklist"><ul>\n<li><span class="task-box">☐</span>a</li>\n</ul></div></li>'
        in result
    )
    assert '<ul>\n<li><span class="task-box">☐</span>a</li>\n<li>b</li>' in result


def test_a_checklist_draws_its_box_in_place_of_a_bullet():
    rules = dict(re.findall(r"^([^@{][^{]*?)\s*\{([^}]*)\}", rb.EPUB_CSS, re.M))
    assert "list-style-type: none;" in rules["div.checklist ul"]
    indent = re.search(r"padding-left: ([\d.]+em);", rules["div.checklist li"]).group(1)
    assert f"text-indent: -{indent};" in rules["div.checklist li"]
    assert f"width: {indent};" in rules[".task-box"]
    assert "display: inline-block;" in rules[".task-box"]


def test_a_figure_and_its_caption_are_centred():
    rules = dict(re.findall(r"^([^@{][^{]*?)\s*\{([^}]*)\}", rb.EPUB_CSS, re.M))
    assert "margin: 0 auto;" in rules["figure img"]
    assert "text-align: center;" in rules["figure"]
    assert "text-align: center;" in rules["figcaption"]


def test_a_figure_keeps_its_caption_on_the_page_of_its_image():
    rules = dict(re.findall(r"^([^@{][^{]*?)\s*\{([^}]*)\}", rb.EPUB_CSS, re.M))
    for prop in ("break-inside", "page-break-inside", "-webkit-column-break-inside"):
        assert re.search(rf"(?:^|[ ;]){prop}: avoid;", rules["figure"]), prop


def test_omit_from_book_drops_only_the_marked_item():
    html = (
        "<ul>\n<li>keep</li>\n<li><strong>gone.</strong> text <!-- book: omit --></li>\n"
        "<li>also kept</li>\n</ul>"
    )
    assert rb.omit_from_book(html) == "<ul>\n<li>keep</li>\n<li>also kept</li>\n</ul>"


def test_omit_from_book_refuses_a_marker_it_cannot_place():
    with pytest.raises(ValueError, match="outside a list item"):
        rb.omit_from_book("<p>prose <!-- book: omit --></p>")
    nested = "<ul><li>outer <!-- book: omit --><ul><li>inner</li></ul></li></ul>"
    with pytest.raises(ValueError, match="outside a list item"):
        rb.omit_from_book(nested)


def test_book_html_substitutes_every_placeholder_and_wraps_no_section():
    block = rh.DiagramBlock(index=0, kind="d2", title="T", source="a -> b\n")
    part = rh.AssembledPart(
        anchor="p1",
        stem="lifecycle",
        html='<h1 id="lifecycle-x">X</h1>\n<div class="dgph" data-i="0"></div>',
        blocks=[block],
    )
    html = rb.book_html([part], {"lifecycle": {0: "<figure>F</figure>"}})
    assert 'class="dgph"' not in html
    assert "<section" not in html
    assert '<h1 id="lifecycle-x">X</h1>' in html
    assert html.startswith("<!DOCTYPE html>")
    assert f"<title>{rb.TITLE}</title>" in html


def test_retitle_part_replaces_the_text_and_keeps_the_id():
    html = '<h1 id="README-x">Old <em>t</em></h1>\n<h1 id="b">B</h1>'
    out = rb.retitle_part(html, "A & B")
    assert out == '<h1 id="README-x">A &amp; B</h1>\n<h1 id="b">B</h1>'


def test_retitle_part_refuses_a_part_with_no_h1():
    with pytest.raises(ValueError, match="no <h1>"):
        rb.retitle_part("<h2>x</h2>", "Introduction")


def test_book_html_retitles_the_readme_chapter():
    part = rh.AssembledPart(
        anchor="p0",
        stem="README",
        html='<h1 id="README-ai-agent-development-handbook">AI Agent Development Handbook</h1>',
        blocks=[],
    )
    html = rb.book_html([part], {})
    assert '<h1 id="README-ai-agent-development-handbook">Introduction</h1>' in html


def test_the_contents_page_reads_as_plain_text():
    assert "nav#toc ol { list-style-type: none;" in rb.EPUB_CSS
    assert "nav#toc a { color: inherit; text-decoration: none; }" in rb.EPUB_CSS


def test_a_link_is_set_in_the_text_colour_and_underlined():
    rules = dict(re.findall(r"^([^@{][^{]*?)\s*\{([^}]*)\}", rb.EPUB_CSS, re.M))
    assert "color: inherit;" in rules["a"]
    assert "text-decoration: underline;" in rules["a"]
    # The contents page keeps its own, more specific rule: no underline there.
    assert "text-decoration: none;" in rules["nav#toc a"]


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
    assert "toc-title: 'Contents'" in meta
    assert "©" not in meta and "Copyright" not in meta


def test_glue_part_numbers_joins_part_and_its_number_in_prose():
    out = rb.glue_part_numbers("<p>See Part 4 and Parts 2, 3 and 6.</p>")
    assert out == "<p>See Part\u00a04 and Parts\u00a02, 3 and 6.</p>"


def test_glue_part_numbers_leaves_tags_and_code_as_written():
    html = '<h2 id="p-part-1">Part 1</h2><a href="#Part 2">x</a><code>Part 3</code>'
    out = rb.glue_part_numbers(html)
    assert (
        out
        == '<h2 id="p-part-1">Part\u00a01</h2><a href="#Part 2">x</a><code>Part 3</code>'
    )


def test_curl_quotes_curls_double_quotes_in_prose():
    assert rb.curl_quotes('<p>He said "hi" today.</p>') == "<p>He said “hi” today.</p>"


def test_curl_quotes_treats_a_mid_word_apostrophe_as_a_closing_mark():
    assert rb.curl_quotes("<p>it's done</p>") == "<p>it\u2019s done</p>"


def test_curl_quotes_opens_a_quote_flush_against_a_tag_boundary():
    # The handbook's own pattern: **"We added more patterns"** opens a quote
    # with no letter beside it, only a <strong> tag; the closing quote is
    # judged by the "s" in "patterns", same as any other prose quote.
    out = rb.curl_quotes('<strong>"We added more patterns"</strong>')
    assert out == "<strong>“We added more patterns”</strong>"


def test_curl_quotes_leaves_inline_code_byte_identical():
    out = rb.curl_quotes("<p>merged with <code>--rebase</code>.</p>")
    assert "<code>--rebase</code>" in out


def test_curl_quotes_leaves_a_pre_code_block_byte_identical():
    src = '<pre><code>label: "x"\na -&gt; b: &lt;y&gt;\n</code></pre>'
    assert rb.curl_quotes(src) == src


def test_curl_quotes_curls_prose_around_untouched_code():
    out = rb.curl_quotes('<p>Run <code>--rebase</code>; say "done".</p>')
    assert out == "<p>Run <code>--rebase</code>; say “done”.</p>"


def test_curl_quotes_does_not_touch_attribute_values():
    out = rb.curl_quotes('<a href="x.html" title="a &quot;b&quot;">"y"</a>')
    assert 'href="x.html"' in out
    assert 'title="a &quot;b&quot;"' in out
    assert "“y”" in out


def test_curl_quotes_closes_a_quote_that_wraps_an_inline_tag():
    # A closing tag must not reset the context the way an opening one does:
    # the quote right after </em> is a close, judged by the "x" before the
    # tag, not by the tag itself.
    out = rb.curl_quotes('<p>"<em>x</em>"</p>')
    assert out == "<p>“<em>x</em>”</p>"


def test_curl_quotes_reads_a_possessive_right_after_a_closing_link():
    # docs/engineering/lifecycle.md's own shape: `Part 1</a>'s gates` - a
    # closing tag used to reset the context to whitespace, misreading this
    # apostrophe as an opening single quote instead of a possessive.
    out = rb.curl_quotes('<p><a href="#p1">Part 1</a>\'s gates</p>')
    assert out == '<p><a href="#p1">Part 1</a>\u2019s gates</p>'


def test_curl_quotes_carries_the_last_code_character_past_its_closing_tag():
    # The skip branch must also feed `prev` forward: otherwise a quote right
    # after </code> always reads as if a tag had just reset the context.
    out = rb.curl_quotes("<code>x</code>'s")
    assert out == "<code>x</code>\u2019s"


def test_epub_command_reads_plain_html_and_splits_on_parts(tmp_path: Path):
    """No ``+smart``: `curl_quotes` curls the book's prose before pandoc sees it.

    ``+smart`` also rewrites ``--`` inside an inline ``<code>`` span (see
    `curl_quotes`'s docstring), so this command must never carry it.
    """
    cmd = rb.epub_command(
        tmp_path / "book.html",
        tmp_path / "meta.yaml",
        tmp_path / "epub.css",
        tmp_path / "out.epub",
        tmp_path / "work",
    )
    assert cmd[0] == "pandoc"
    assert cmd[cmd.index("-f") + 1] == "html"
    assert cmd[cmd.index("-t") + 1] == "epub3"
    assert "--split-level=1" in cmd
    # The contents list the parts only; each part's own headings are not in it.
    assert "--toc" in cmd and "--toc-depth=1" in cmd
    assert cmd[cmd.index("--metadata-file") + 1] == str(tmp_path / "meta.yaml")
    assert cmd[cmd.index("--css") + 1] == str(tmp_path / "epub.css")
    assert cmd[cmd.index("-o") + 1] == str(tmp_path / "out.epub")
    assert cmd[cmd.index("--resource-path") + 1] == str(tmp_path / "work")
    assert cmd[-1] == str(tmp_path / "book.html")


def test_epub_command_embeds_each_font_it_is_given(tmp_path: Path):
    fonts = (tmp_path / "a.ttf", tmp_path / "b.ttf")
    cmd = rb.epub_command(
        tmp_path / "book.html",
        tmp_path / "meta.yaml",
        tmp_path / "epub.css",
        tmp_path / "out.epub",
        tmp_path / "work",
        fonts=fonts,
    )
    embedded = [cmd[i + 1] for i, arg in enumerate(cmd) if arg == "--epub-embed-font"]
    assert embedded == [str(f) for f in fonts]


def test_font_face_css_points_each_face_at_its_embedded_basename():
    css = rb.font_face_css((("Fam", "bold", "italic", "dir/Fam-BoldIt.ttf"),))
    assert css == (
        '@font-face { font-family: "Fam"; font-weight: bold; '
        'font-style: italic; src: url("../fonts/Fam-BoldIt.ttf"); }\n'
    )


def test_every_epub_face_is_committed_with_its_licence():
    paths = [rb.FONTS_ROOT / path for *_, path in rb.EPUB_FACES]
    for path in paths:
        assert path.is_file(), path
        assert (path.parent / "OFL.txt").is_file(), path.parent
    # pandoc flattens the files into one fonts/ directory by basename.
    assert len({p.name for p in paths}) == len(paths)
    assert len({face[:3] for face in rb.EPUB_FACES}) == len(rb.EPUB_FACES)


_CSS_FAMILY_RE = re.compile(r'font-family:\s*"([^"]+)"')


def test_every_family_the_stylesheet_names_has_a_face():
    named = set(_CSS_FAMILY_RE.findall(rb.EPUB_CSS))
    assert named == {family for family, *_ in rb.EPUB_FACES}
    # Each rule keeps a generic fallback for a reader that ignores the face.
    for rule in re.findall(r"font-family:[^;]+;", rb.EPUB_CSS.split("}\nbody", 1)[1]):
        assert re.search(r",\s*(serif|sans-serif|monospace);", rule), rule


def test_a_part_opens_on_a_right_hand_page():
    rules = dict(re.findall(r"^([^@{][^{]*?)\s*\{([^}]*)\}", rb.EPUB_CSS, re.M))
    assert "break-before: right;" in rules["h1"]
    assert "page-break-before: right;" in rules["h1"]


def test_a_heading_stays_whole_and_with_two_lines_of_its_text():
    rules = dict(re.findall(r"^([^@{][^{]*?)\s*\{([^}]*)\}", rb.EPUB_CSS, re.M))
    heading = rules["h1, h2, h3, h4, h5, h6"]
    for prop in (
        "break-inside",
        "break-after",
        "page-break-inside",
        "page-break-after",
        "-webkit-column-break-inside",
        "-webkit-column-break-after",
    ):
        assert re.search(rf"(?:^|[ ;]){prop}: avoid;", heading), prop
    assert "orphans: 2;" in rules["p, li"] and "widows: 2;" in rules["p, li"]


def test_a_table_stays_whole_or_splits_between_rows_under_its_header():
    rules = dict(re.findall(r"^([^@{][^{]*?)\s*\{([^}]*)\}", rb.EPUB_CSS, re.M))
    for prop in ("break-inside", "page-break-inside", "-webkit-column-break-inside"):
        assert re.search(rf"(?:^|[ ;]){prop}: avoid;", rules["table, tr"]), prop
    assert "display: table-header-group;" in rules["thead"]


def test_a_table_is_ruled_horizontally_only():
    rules = dict(re.findall(r"^([^@{][^{]*?)\s*\{([^}]*)\}", rb.EPUB_CSS, re.M))
    for sel, body in rules.items():
        if re.search(r"\b(table|th|td|tr)\b", sel):
            values = re.findall(r"border(?:-left|-right)?:\s*([^;]+);", body)
            assert all(v == "none" for v in values), sel
    assert "border-top:" in rules["table"] and "border-bottom:" in rules["table"]
    assert "border-bottom:" in rules["th"]
    assert "border-top:" in rules["td"]


def test_a_table_cell_is_never_hyphenated():
    rules = dict(re.findall(r"^([^@{][^{]*?)\s*\{([^}]*)\}", rb.EPUB_CSS, re.M))
    assert re.search(r"(?:^|[ ;])hyphens: manual;", rules["th, td"])
    assert "-webkit-hyphens: manual;" in rules["th, td"]


def test_prose_is_justified_and_hyphenated_and_nothing_else_is():
    rules = dict(re.findall(r"^([^@{][^{]*?)\s*\{([^}]*)\}", rb.EPUB_CSS, re.M))
    justified = {sel for sel, body in rules.items() if "justify" in body}
    assert justified == {"p, li"}
    # Justified text with no hyphenation opens wide gaps in a narrow column.
    assert "hyphens: auto" in rules["p, li"]


def test_book_html_raises_on_a_placeholder_with_no_matching_diagram_block():
    part = rh.AssembledPart(
        anchor="p1",
        stem="lifecycle",
        html='<h1 id="lifecycle-x">X</h1>\n<div class="dgph" data-i="0"></div>',
        blocks=[],
    )
    with pytest.raises(ValueError, match=r"lifecycle\.md.*placeholder 0"):
        rb.book_html([part], {})


def test_build_date_uses_source_date_epoch_when_set(monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    assert rb._build_date() == "1970-01-01"


def test_build_date_uses_today_when_source_date_epoch_is_unset(monkeypatch):
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    expected = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
    assert rb._build_date() == expected


def test_build_date_refuses_a_malformed_source_date_epoch(monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "not-a-number")
    with pytest.raises(SystemExit, match=r"SOURCE_DATE_EPOCH.*not-a-number"):
        rb._build_date()


REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / "docs" / "engineering"
needs_pandoc = pytest.mark.skipif(
    shutil.which("pandoc") is None,
    reason="pandoc CLI not installed; CI gains it with #192",
)
# A full build draws a seed through the d2 CLI only for a d2 fence with no
# committed figure, so a build needs d2 exactly while one exists. Computed
# rather than assumed, so the gate stays right the day a fence lands before
# its figure.
BUILD_NEEDS_D2 = any(
    block.kind == "d2"
    and not rb.figure_path(DOCS / "figures", stem, block.index).exists()
    for stem, block in rb.part_blocks(DOCS, rh.PARTS)
)


def _skip_unless_the_build_can_draw_its_seeds() -> None:
    if BUILD_NEEDS_D2 and shutil.which("d2") is None:
        pytest.skip("a d2 fence has no committed figure, so the build needs d2")


def test_run_tool_names_a_missing_tool_and_how_to_install_it():
    with pytest.raises(SystemExit, match=r"no-such-tool-189.*brew install x"):
        rb.run_tool(["no-such-tool-189"], timeout=5, install_hint="brew install x")


def test_run_tool_stops_a_hung_tool():
    with pytest.raises(SystemExit, match="did not finish within"):
        rb.run_tool(["sleep", "5"], timeout=0.2, install_hint="n/a")


def test_run_tool_reports_a_failing_tools_stderr():
    with pytest.raises(SystemExit, match=r"(?s)exit 3.*boom"):
        rb.run_tool(
            ["sh", "-c", "echo boom >&2; exit 3"], timeout=5, install_hint="n/a"
        )


def _epub_documents(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n).decode() for n in z.namelist() if n.endswith(".xhtml")}


_SECTION_OR_HEADING_ID_RE = re.compile(r'<(?:section|h[1-6])\b[^>]*\bid="([^"]+)"')


def _chapter_ids(path: Path) -> set[str]:
    """Every id on a ``<section>`` or ``<h1>``-``<h6>`` element in a chapter file.

    Pandoc moves each heading id onto its enclosing ``<section class="levelN">``
    rather than leaving it on the heading tag, so a plain ``id="..."`` scan over
    every element (including the nav and the title page, which carry ids of
    their own) is not the right comparison; this narrows to the chapter files
    (``ch\\d+.xhtml``, so ``nav.xhtml``'s ``toc-title`` is excluded) and to the
    two element kinds that can carry a heading's id.
    """
    ids = set()
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if not re.search(r"ch\d+\.xhtml$", name):
                continue
            ids.update(_SECTION_OR_HEADING_ID_RE.findall(z.read(name).decode()))
    return ids


@pytest.fixture(scope="module")
def built_epub(tmp_path_factory) -> Path:
    pytest.importorskip("markdown")
    if shutil.which("pandoc") is None:
        pytest.skip("pandoc CLI not installed; CI gains it with #192")
    _skip_unless_the_build_can_draw_its_seeds()
    out = tmp_path_factory.mktemp("epub") / "nested" / "handbook.epub"
    return rb.build_epub(DOCS, out, date="2026-09-28")


@needs_pandoc
def test_the_epub_carries_exactly_the_heading_ids_the_page_carries(built_epub: Path):
    part_anchors = {anchor for anchor, _, _ in rh.PARTS}
    assert _chapter_ids(built_epub) == rh.heading_ids(DOCS) - part_anchors


@needs_pandoc
def test_no_link_in_the_epub_points_at_a_markdown_file(built_epub: Path):
    for name, text in _epub_documents(built_epub).items():
        assert not re.search(r'href="[^"#]*\.md', text), name


_INLINE_CODE_SPAN_RE = re.compile(r"`([^`\n]+)`")
_FENCED_BLOCK_RE = re.compile(r"```.*?```", re.S)
_CODE_TAG_TEXT_RE = re.compile(r"<code>(.*?)</code>", re.S)


def _inline_code_spans_in_sources() -> set[str]:
    """Every `` `span` `` in the handbook's Markdown, fenced blocks excluded.

    A line carrying `rb.BOOK_OMIT_MARKER` is left out too: a list item is one
    source line, and the book omits it.
    """
    spans: set[str] = set()
    for path in sorted(DOCS.glob("*.md")):
        prose = _FENCED_BLOCK_RE.sub("", path.read_text())
        prose = "\n".join(
            line for line in prose.splitlines() if rb.BOOK_OMIT_MARKER not in line
        )
        spans.update(_INLINE_CODE_SPAN_RE.findall(prose))
    return spans


@needs_pandoc
def test_the_epub_carries_every_inline_code_span_verbatim(built_epub: Path):
    """`--rebase` (docs/engineering/lifecycle.md) is the reported case, not the only one.

    `curl_quotes` exists because pandoc's ``+smart`` HTML reader rewrites
    ``--`` inside an inline ``<code>`` span into an en dash; this checks the
    fix on the real build rather than on one hand-picked example, over every
    inline code span the handbook's Markdown carries.
    """
    import html as html_mod

    spans = _inline_code_spans_in_sources()
    assert "--rebase" in spans, "the reported case is gone from the source"
    chapters, docs = _chapters(built_epub)
    code_texts = {
        html_mod.unescape(text)
        for name in chapters
        for text in _CODE_TAG_TEXT_RE.findall(docs[name])
    }
    missing = spans - code_texts
    assert not missing, f"inline code spans absent from the EPUB verbatim: {missing}"


_PRE_OR_CODE_ELEMENT_RE = re.compile(r"<(pre|code)\b[^>]*>.*?</\1>", re.S)
_ANY_TAG_RE = re.compile(r"<[^>]+>")


@needs_pandoc
def test_the_epub_carries_typographic_quotes_in_prose(built_epub: Path):
    """No straight ``"``/``'`` survives in prose text; code and tags are excluded.

    A tag's own markup (``class="..."``, ``href="..."``) carries straight
    quotes too, so this strips every ``<pre>``/``<code>`` element (content
    and tag alike) and then every remaining tag, leaving only the visible
    prose text `curl_quotes` was meant to curl, before counting.
    """
    chapters, docs = _chapters(built_epub)
    straight_quotes = 0
    curly_found = False
    opens = closes = 0
    for name in chapters:
        no_code = _PRE_OR_CODE_ELEMENT_RE.sub("", docs[name])
        prose = _ANY_TAG_RE.sub("", no_code)
        straight_quotes += prose.count('"') + prose.count("'")
        if any(c in prose for c in "“”\u2018\u2019"):
            curly_found = True
        opens += prose.count("“")
        closes += prose.count("”")
    assert straight_quotes == 0
    assert curly_found
    # Not just present, but pointing the right way: `curl_quotes` resetting
    # its "boundary" context on a closing tag as well as an opening one
    # (Part 1</a>'s, "<em>x</em>") can flip a close into an open without
    # ever producing a straight quote, which the counts above would miss -
    # see curl_quotes's own tests for the reproduction. Every opening
    # double quote in the handbook's prose is closed.
    assert opens == closes, (opens, closes)


def _chapters(epub_path: Path) -> tuple[list[str], dict[str, str]]:
    """The book's chapter files, in name order, and every xhtml document by name."""
    docs = _epub_documents(epub_path)
    chapters = sorted(n for n in docs if re.search(r"ch\d+\.xhtml$", n))
    return chapters, docs


@needs_pandoc
def test_every_part_is_a_chapter_in_page_order(built_epub: Path):
    chapters, docs = _chapters(built_epub)
    firsts = rb.first_heading_ids(rh.render_parts(DOCS, rh.PARTS), rh.PARTS)
    order = [firsts[stem] for _, stem, _ in rh.PARTS]
    assert len(chapters) == len(rh.PARTS)
    for i, heading_id in enumerate(order):
        assert f'id="{heading_id}"' in docs[chapters[i]]


def test_build_epub_refuses_a_part_whose_first_heading_is_not_h1(tmp_path: Path):
    """`require_h1_first` guards `build_epub` before pandoc ever runs.

    Without the guard, this part would merge silently into the previous
    chapter instead of raising - the failure mode `require_h1_first` exists to
    catch. Reaching pandoc is no longer part of this test: the guard runs
    first, so this needs only the `markdown` dependency, not pandoc.
    """
    pytest.importorskip("markdown")
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "one.md").write_text("# One\n\ntext\n")
    (docs_dir / "two.md").write_text("## Two\n\ntext\n")
    parts = [("p1", "one", "One"), ("p2", "two", "Two")]
    with pytest.raises(ValueError, match=r"two\.md: first heading is <h2>, not <h1>"):
        rb.build_epub(
            docs_dir, tmp_path / "out" / "book.epub", date="2026-09-28", parts=parts
        )


def test_build_epub_refuses_a_part_with_content_before_its_h1(tmp_path: Path):
    """The same guard, for content ahead of the <h1> rather than a wrong level.

    Leading prose has no heading tag of its own for the old "first heading
    tag found" check to see, so it used to pass this guard and merge into
    the previous chapter; `require_h1_first` now demands the part open with
    its <h1>, nothing but whitespace before it.
    """
    pytest.importorskip("markdown")
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "one.md").write_text("# One\n\ntext\n")
    (docs_dir / "two.md").write_text("Leading prose.\n\n# Two\n\ntext\n")
    parts = [("p1", "one", "One"), ("p2", "two", "Two")]
    with pytest.raises(
        ValueError, match=r"two\.md: content precedes its first heading"
    ):
        rb.build_epub(
            docs_dir, tmp_path / "out" / "book.epub", date="2026-09-28", parts=parts
        )


_CHECKLIST_LINE_RE = re.compile(r"^\s*-\s*\[[ xX]\]\s", re.MULTILINE)
_TASK_BOX_GLYPH_RE = re.compile(r'<li><span class="task-box">[☐☒]</span>')


@needs_pandoc
def test_the_epub_carries_a_literal_glyph_for_every_source_checklist_item(
    built_epub: Path,
):
    """`restore_task_boxes` spans the ☐/☒ glyph so it survives as text.

    A bare ☐/☒-prefixed ``<li>`` is rewritten by pandoc's HTML reader into a
    real ``<input type="checkbox">`` (observed under pandoc 3.8.2,
    independent of the ``task_lists`` extension - see
    `render_handbook_book.restore_task_boxes`), but an EPUB reading system
    need not render a form control, and a tick in one cannot persist. The
    ``<span>`` defeats that detection, so the marker to count in the built
    book is the literal glyph, and no chapter file should carry an
    ``<input`` at all.
    """
    source_count = sum(
        len(_CHECKLIST_LINE_RE.findall(path.read_text()))
        for path in sorted(DOCS.glob("*.md"))
    )
    chapters, docs = _chapters(built_epub)
    epub_count = sum(len(_TASK_BOX_GLYPH_RE.findall(docs[name])) for name in chapters)
    assert source_count > 0
    assert epub_count == source_count
    assert not any("<input" in docs[name] for name in chapters)


@needs_pandoc
def test_build_epub_creates_a_missing_output_directory(built_epub: Path):
    assert built_epub.exists() and built_epub.parent.name == "nested"


@needs_pandoc
def test_main_resolves_the_docs_from_the_repository_not_the_cwd(
    tmp_path: Path, monkeypatch
):
    pytest.importorskip("markdown")
    _skip_unless_the_build_can_draw_its_seeds()
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "handbook.epub"
    assert rb.main(["--format", "epub", "--out", str(out)]) == 0
    assert out.exists()


_IMG_SRC_RE = re.compile(r'<img\b[^>]*\bsrc="([^"]+)"')
_IMG_TAG_RE = re.compile(r"<img\b[^>]*>")


def _epub_media_svgs(epub_path: Path) -> dict[str, str]:
    """Every SVG under the archive's media directory, by archive path."""
    with zipfile.ZipFile(epub_path) as z:
        return {
            n: z.read(n).decode()
            for n in z.namelist()
            if "/media/" in n and n.endswith(".svg")
        }


def _resolve_in_archive(chapter: str, src: str) -> str:
    """`src` as written in `chapter`, resolved to an archive path."""
    parts = chapter.split("/")[:-1]
    for piece in src.split("/"):
        if piece == "..":
            parts.pop()
        elif piece != ".":
            parts.append(piece)
    return "/".join(parts)


@needs_pandoc
def test_the_epub_carries_one_image_per_fence(built_epub: Path):
    # Pandoc renames each media file (``media/file0.svg``, ...), so the check
    # resolves every src against its chapter rather than looking for the
    # ``<stem>-<index>.svg`` name the build wrote.
    chapters, docs = _chapters(built_epub)
    media = _epub_media_svgs(built_epub)
    srcs = [(name, src) for name in chapters for src in _IMG_SRC_RE.findall(docs[name])]
    assert len(srcs) == len(rb.part_blocks(DOCS, rh.PARTS))
    for name, src in srcs:
        assert _resolve_in_archive(name, src) in media, (name, src)


_WEIGHT_STYLE_RE = re.compile(r"font-weight:\s*(\d+);\s*font-style:\s*(\w+)")


@needs_pandoc
def test_every_epub_figure_is_transparent_and_has_its_fonts(built_epub: Path):
    media = _epub_media_svgs(built_epub)
    assert media
    literal_checks = 0
    for name, svg in media.items():
        # The print check that refuses a light opaque fill on a committed
        # figure refuses a backing panel the build might add, too.
        assert bf.opaque_fill_problems(svg) == [], name
        declared = {(int(w), s) for w, s in _WEIGHT_STYLE_RE.findall(svg)}
        # `used_faces` is pinned literally by the unit tests in
        # test_book_figures.py (tspan runs included), so it is the oracle for
        # the exact set; the two checks below hold the build to the seeds'
        # own attributes without going through that walk at all.
        assert declared == bf.used_faces(svg), name
        if re.search(r'font-weight="(?:700|bold)"', svg):
            assert (700, "normal") in declared, name
            literal_checks += 1
        if 'font-style="italic"' in svg:
            assert (400, "italic") in declared, name
            literal_checks += 1
    # A figure whose lettering is outlined carries no text and so nothing to
    # check here; the font path is then held by the unit tests alone.
    has_text = any("<text" in svg for svg in media.values())
    assert literal_checks or not has_text, (
        "no figure carried a literal weight or style to check"
    )


@needs_pandoc
def test_no_fence_survives_as_a_listing(built_epub: Path):
    import html as html_mod

    chapters, docs = _chapters(built_epub)
    pre_texts = html_mod.unescape(
        "\n".join(
            m.group(0)
            for name in chapters
            for m in re.finditer(r"<pre\b.*?</pre>", docs[name], re.S)
        )
    )
    for stem, block in rb.part_blocks(DOCS, rh.PARTS):
        for line in block.source.splitlines():
            if line.strip():
                assert line not in pre_texts, (stem, block.index, line)


@needs_pandoc
def test_the_epub_image_keeps_its_em_width(built_epub: Path):
    chapters, docs = _chapters(built_epub)
    imgs = [tag for name in chapters for tag in _IMG_TAG_RE.findall(docs[name])]
    assert imgs
    for tag in imgs:
        assert re.search(r'style="width: \d+\.\d{2}em; max-width: 100%"', tag), tag


@needs_pandoc
def test_the_epub_ships_exactly_the_fonts_its_stylesheet_declares(built_epub: Path):
    with zipfile.ZipFile(built_epub) as z:
        names = z.namelist()
        css = "".join(z.read(n).decode() for n in names if n.endswith(".css"))
    shipped = {n.rsplit("/", 1)[1] for n in names if n.startswith("EPUB/fonts/")}
    declared = set(re.findall(r'src: url\("\.\./fonts/([^"]+)"\)', css))
    assert shipped and shipped == declared


@needs_pandoc
def test_the_contents_list_the_parts_and_nothing_below_them(built_epub: Path):
    with zipfile.ZipFile(built_epub) as z:
        nav = z.read("EPUB/nav.xhtml").decode()
    toc = re.search(r'<nav epub:type="toc".*?</nav>', nav, re.S).group(0)
    assert '<h1 id="toc-title">Contents</h1>' in toc
    entries = re.findall(r"<a [^>]*>([^<]*)</a>", toc)
    assert len(entries) == len(rh.PARTS)
    assert entries[0] == rb.BOOK_PART_TITLES["README"]
    assert toc.count("<ol") == 1


def test_the_book_leaves_out_what_its_source_marks_for_omission(built_epub: Path):
    marked = [
        line
        for md in sorted(DOCS.glob("*.md"))
        for line in md.read_text(encoding="utf-8").splitlines()
        if rb.BOOK_OMIT_MARKER in line
    ]
    assert marked, "no source line carries the marker, so this proves nothing"
    with zipfile.ZipFile(built_epub) as z:
        text = "".join(z.read(n).decode() for n in z.namelist() if n.endswith(".xhtml"))
    assert "Not part of the handbook" not in text
    assert "book: omit" not in text
