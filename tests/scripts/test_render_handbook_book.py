from __future__ import annotations

import datetime
import re
import shutil
import zipfile
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


def test_listing_markup_escapes_the_source_and_keeps_the_title():
    block = rh.DiagramBlock(index=0, kind="d2", title="A & B", source="a -> b: <x>\n")
    html = rb.listing_markup(block)
    assert "<pre><code>a -&gt; b: &lt;x&gt;\n</code></pre>" in html
    assert "<figcaption>A &amp; B</figcaption>" in html


def test_restore_task_boxes_marks_open_and_done_items():
    html = (
        '<li class="task">open item</li>'
        '<li class="task done">done item</li>'
        "<li>plain item</li>"
    )
    result = rb.restore_task_boxes(html)
    assert result == (
        '<li><span class="task-box">☐</span> open item</li>'
        '<li><span class="task-box">☒</span> done item</li>'
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
    assert '<li><span class="task-box">☐</span> open item</li>' in result
    assert '<li><span class="task-box">☒</span> done item</li>' in result


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
    )
    assert cmd[0] == "pandoc"
    assert cmd[cmd.index("-f") + 1] == "html"
    assert cmd[cmd.index("-t") + 1] == "epub3"
    assert "--split-level=1" in cmd
    assert "--toc" in cmd and "--toc-depth=2" in cmd
    assert cmd[cmd.index("--metadata-file") + 1] == str(tmp_path / "meta.yaml")
    assert cmd[cmd.index("--css") + 1] == str(tmp_path / "epub.css")
    assert cmd[cmd.index("-o") + 1] == str(tmp_path / "out.epub")
    assert cmd[-1] == str(tmp_path / "book.html")


def test_book_html_raises_on_a_placeholder_with_no_matching_diagram_block():
    part = rh.AssembledPart(
        anchor="p1",
        stem="lifecycle",
        html='<h1 id="lifecycle-x">X</h1>\n<div class="dgph" data-i="0"></div>',
        blocks=[],
    )
    with pytest.raises(ValueError, match=r"lifecycle\.md.*placeholder 0"):
        rb.book_html([part])


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
    """Every `` `span` `` in the handbook's Markdown, fenced blocks excluded."""
    spans: set[str] = set()
    for path in sorted(DOCS.glob("*.md")):
        prose = _FENCED_BLOCK_RE.sub("", path.read_text())
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
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "handbook.epub"
    assert rb.main(["--format", "epub", "--out", str(out)]) == 0
    assert out.exists()
