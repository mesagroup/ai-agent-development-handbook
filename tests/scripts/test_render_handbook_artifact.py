"""Tests for the handbook-artifact renderer's pure HTML transforms."""

from __future__ import annotations

import importlib.util
import re
import shutil
import sys
from itertools import pairwise
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


def test_rewrite_links_preserves_a_fragment_that_names_a_heading():
    """A section citation lands on the section, not on the top of its part.

    Until the page carried heading ids, `evaluation.md#loop` collapsed to
    `#p5` and every section-level citation a report emits opened the part
    rather than the clause. The id is `<stem>-<fragment>`, and it has to be
    in `ids` for the rewrite to trust it.
    """
    html = '<a href="evaluation.md#loop">the loop</a>'
    out, unmapped = rh.rewrite_links(
        html, {"evaluation.md": "#p5"}, ids={"evaluation-loop"}
    )
    assert out == '<a href="#evaluation-loop">the loop</a>'  # text untouched
    assert unmapped == []


def test_rewrite_links_reports_a_fragment_the_page_has_no_heading_for():
    """A dead fragment is unmapped, not quietly collapsed to the part anchor.

    Collapsing is what GitHub does for a fragment naming no heading (it
    scrolls to the top of the file), and it is exactly the silent miss the
    ids exist to end, so the href is left as written and reported, and
    `build` raises on it as it does on any relative link it cannot resolve.
    """
    html = '<a href="evaluation.md#nowhere">x</a> <a href="evaluation.md">y</a>'
    out, unmapped = rh.rewrite_links(
        html, {"evaluation.md": "#p5"}, ids={"evaluation-loop"}
    )
    assert 'href="evaluation.md#nowhere"' in out
    assert 'href="#p5"' in out  # the bare part link still maps
    assert unmapped == ["evaluation.md#nowhere"]


def test_heading_id_is_the_stem_and_the_github_slug_of_the_text():
    r"""Tags and entities in the converter's heading HTML do not reach the slug.

    The matrix side slugifies the markdown source (`Why \`x\` matters &
    more`), the renderer sees the converted HTML; both must name one element.
    """
    assert (
        rh.heading_id("lifecycle", "Why <code>x</code> matters &amp; more")
        == "lifecycle-why-x-matters--more"
    )
    assert rh.heading_id("coda", "Coda") == "coda-coda"


def test_add_heading_ids_marks_every_level_in_order():
    html = "<h1>Part</h1><p>t</p><h2>One</h2><h3>Deep</h3><h2>Two</h2>"
    out, ids = rh.add_heading_ids(html, "p")
    assert ids == ["p-part", "p-one", "p-deep", "p-two"]
    assert '<h1 id="p-part">Part</h1>' in out
    assert '<h3 id="p-deep">Deep</h3>' in out
    assert out.count(' id="') == 4


def test_add_heading_ids_refuses_two_headings_with_one_slug():
    with pytest.raises(ValueError, match="two headings slugify to 'p-same'"):
        rh.add_heading_ids("<h2>Same</h2><h3>Same</h3>", "p")


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


def test_unlink_out_of_tree_keeps_the_text_and_drops_the_anchor():
    # A relative .md target with a path separator is outside the handbook
    # directory, so it is not in this artifact and no anchor can reach it.
    html = '<a href="../engineering-notes.md">Engineering notes</a> matter'
    out, unlinked = rh.unlink_out_of_tree(html)
    assert out == "Engineering notes matter"
    assert unlinked == ["../engineering-notes.md"]


def test_unlink_out_of_tree_leaves_siblings_and_absolute_urls_alone():
    # A bare stem is an in-tree part for rewrite_links to map; an absolute URL
    # is meant to leave the page. Neither is this function's business.
    html = (
        '<a href="evaluation.md#loop">the loop</a> and '
        '<a href="https://example.com/docs/a.md">out</a>'
    )
    out, unlinked = rh.unlink_out_of_tree(html)
    assert out == html
    assert unlinked == []


def test_post_process_unlinks_out_of_tree_before_mapping_in_tree():
    html = (
        '<p><a href="lifecycle.md">Part 1</a> and '
        '<a href="../engineering-notes.md">notes</a></p>'
    )
    out, unmapped, unlinked = rh.post_process(html, {"lifecycle.md": "#p1"})
    assert 'href="#p1"' in out
    assert "notes" in out and "engineering-notes.md" not in out
    # Handled, not skipped: build raises on an unmapped relative link, so an
    # out-of-tree link reported as unmapped would fail the render.
    assert unmapped == []
    assert unlinked == ["../engineering-notes.md"]


def test_build_accepts_a_relative_out_of_tree_link(tmp_path):
    docs = _one_part_docs(tmp_path, "[notes](../engineering-notes.md)\n")
    html = rh.build(docs, [("top", "solo", "Solo")])
    assert "notes" in html
    assert "engineering-notes.md" not in html


def test_post_process_applies_all_transforms():
    html = '<a href="lifecycle.md">L</a><table></table><li>[ ] check</li>'
    out, unmapped, _ = rh.post_process(html, {"lifecycle.md": "#p1"})
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
    assert '<h1 id="README-handbook">Handbook</h1>' in html
    assert 'href="#top"' in html  # self .md link rewritten
    assert '<div class="tablewrap"><table>' in html
    assert '<li class="task">first</li>' in html
    assert '<li class="task done">second</li>' in html
    assert 'href="README.md"' not in html  # no residual .md link


def test_build_resolves_a_fragment_into_another_part(tmp_path: Path):
    """The ids of every part exist before any part's links are rewritten.

    `codebase-structure.md` links into a README section; rewriting links
    part by part, as the renderer once did, would have had no README ids to
    offer when the later part was rendered. The link lands on the heading,
    and the heading carries the id.
    """
    pytest.importorskip("markdown")
    (tmp_path / "later.md").write_text("# Later\n\nSee [rules](README.md#the-rules).\n")
    (tmp_path / "README.md").write_text("# Handbook\n\n## The rules\n\ntext\n")
    html = rh.build(
        tmp_path, parts=[("later", "later", "Later"), ("top", "README", "Overview")]
    )
    assert '<h2 id="README-the-rules">The rules</h2>' in html
    assert 'href="#README-the-rules"' in html
    assert 'href="README.md' not in html


def test_build_raises_on_a_fragment_that_names_no_heading(tmp_path: Path):
    pytest.importorskip("markdown")
    (tmp_path / "README.md").write_text("# Handbook\n\nSee [x](README.md#nowhere).\n")
    with pytest.raises(ValueError, match=re.escape("README.md#nowhere")):
        rh.build(tmp_path, parts=[("top", "README", "Overview")])


def test_heading_ids_are_the_ids_a_built_page_carries(tmp_path: Path):
    """The citation check reads `heading_ids` where no renderer can run.

    So the set it computes has to be the set the page carries: every part
    anchor and every heading id, and nothing the page has that this lacks
    except a diagram caption, which none of these parts draws, and the two
    ids of the page chrome, subtracted below.
    """
    pytest.importorskip("markdown")
    (tmp_path / "README.md").write_text("# Handbook\n\n## One\n\n### Two\n")
    (tmp_path / "coda.md").write_text("# Coda\n\ntext\n")
    parts = [("top", "README", "Overview"), ("coda", "coda", "Coda")]
    html = rh.build(tmp_path, parts=parts)
    in_page = set(re.findall(r' id="([^"]+)"', html)) - {"toc", "themeBtn"}
    assert rh.heading_ids(tmp_path, parts) == in_page
    assert "coda-coda" in in_page


def test_every_matrix_heading_slug_is_a_heading_id_on_the_live_tree():
    """One slug function, proven on the tree rather than assumed.

    `render_handbook_traceability.handbook_headings` slugifies the markdown
    source; the renderer slugifies the converter's HTML. For every `##`
    heading of every part the two must agree, or a matrix row id resolves
    in the matrix and not in the page.
    """
    pytest.importorskip("markdown")
    from render_handbook_traceability import handbook_headings, slugify

    docs = Path(__file__).resolve().parents[2] / "docs" / "engineering"
    ids = rh.heading_ids(docs)
    expected = {
        f"{stem}-{slugify(h)}"
        for stem, heads in handbook_headings(docs).items()
        for h in heads
    }
    assert expected, "no ## heading found; the check would hold vacuously"
    assert expected <= ids, sorted(expected - ids)


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


def test_extract_diagram_blocks_replaces_fence_with_placeholder():
    md = 'intro\n\n```d2 title="The TDD loop"\na -> b\n```\n\noutro\n'
    out, blocks = rh.extract_diagram_blocks(md, "implementation-disciplines")
    assert '<div class="dgph" data-i="0"></div>' in out
    assert "```d2" not in out
    assert len(blocks) == 1
    assert blocks[0].title == "The TDD loop"
    assert blocks[0].source == "a -> b\n"


def test_extract_diagram_blocks_numbers_multiple_fences():
    md = '```d2 title="One"\na\n```\n\ntext\n\n```d2 title="Two"\nb\n```\n'
    out, blocks = rh.extract_diagram_blocks(md, "x")
    assert [b.index for b in blocks] == [0, 1]
    assert [b.title for b in blocks] == ["One", "Two"]
    assert 'data-i="0"' in out
    assert 'data-i="1"' in out


def test_extract_diagram_blocks_requires_a_title():
    with pytest.raises(ValueError, match="title"):
        rh.extract_diagram_blocks("```d2\na -> b\n```\n", "lifecycle")


def test_extract_diagram_blocks_leaves_other_fences_alone():
    md = "```python\nprint(1)\n```\n"
    out, blocks = rh.extract_diagram_blocks(md, "x")
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
    block = rh.DiagramBlock(
        index=0, kind="d2", title="The three layers", source="a -> b\n"
    )
    svg = '<svg viewBox="0 0 10 20"></svg>'
    out = rh.diagram_figure("three-layer-model", block, svg, svg)
    assert out.count("<svg") == 2
    assert 'class="dgvar dg-light"' in out
    assert 'class="dgvar dg-dark"' in out
    assert (
        '<figcaption id="dcap-three-layer-model-0">The three layers</figcaption>' in out
    )


def test_substitute_diagrams_replaces_placeholders_by_index():
    html = (
        '<p>a</p><div class="dgph" data-i="1"></div><div class="dgph" data-i="0"></div>'
    )
    out = rh.substitute_diagrams(
        html, {0: "<figure>zero</figure>", 1: "<figure>one</figure>"}
    )
    assert out == "<p>a</p><figure>one</figure><figure>zero</figure>"


def test_substitute_diagrams_raises_on_a_missing_figure():
    with pytest.raises(ValueError, match="3"):
        rh.substitute_diagrams('<div class="dgph" data-i="3"></div>', {})


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


def test_d2_preludes_shrink_the_label_font_in_both_variants():
    # The label font sets d2's minimum box size, so it drives the whole
    # diagram's footprint. Losing it from one variant would silently make that
    # theme's diagrams larger than the other's.
    for prelude in rh.D2_PRELUDES.values():
        assert "**.style.font-size: 12" in prelude


def test_d2_preludes_size_connection_labels_too():
    # `**` reaches shapes only. Setting it alone left every edge label at d2's
    # 16px default, larger than the boxes it ran between and wide enough to
    # cover the short arrows it sat on.
    for prelude in rh.D2_PRELUDES.values():
        assert "(** -> **)[*].style.font-size: 12" in prelude


def test_d2_rank_gap_is_long_enough_to_show_an_unlabelled_arrow():
    # The gap is the entire length of an edge carrying no label, arrowhead
    # included. Below roughly 20 such an arrow collapses to just its head.
    args = rh._D2_LAYOUT_ARGS
    gap = int(args[args.index("--elk-nodeNodeBetweenLayers") + 1])
    assert 20 <= gap < 70


def test_d2_icon_classes_declares_both_classes_and_writes_the_files():
    block = rh.d2_icon_classes("light")
    assert "step:" in block and "human:" in block
    paths = re.findall(r"icon: (\S+\.svg)", block)
    assert len(paths) == 2
    for path in paths:
        assert Path(path).is_file()


def test_d2_icon_person_follows_the_theme_but_the_blank_does_not():
    # The person is drawn in the palette's accent, so it has to differ per
    # theme; the blank one draws nothing and is deliberately shared.
    light = dict(
        re.findall(r"(\w+): \{ icon: (\S+\.svg) \}", rh.d2_icon_classes("light"))
    )
    dark = dict(
        re.findall(r"(\w+): \{ icon: (\S+\.svg) \}", rh.d2_icon_classes("dark"))
    )
    assert light["step"] == dark["step"]
    assert light["human"] != dark["human"]
    assert rh._D2_ICON_STROKE["light"] in Path(light["human"]).read_text()
    assert rh._D2_ICON_STROKE["dark"] in Path(dark["human"]).read_text()


def test_d2_blank_icon_draws_nothing_but_keeps_the_person_footprint():
    # It exists only to buy a node the same 21px icon gutter d2 forces on any
    # node that has an icon, so marked and unmarked steps end up equal boxes.
    blank, person = rh._D2_ICON_BLANK, rh._D2_ICON_PERSON
    assert 'width="16" height="16"' in blank
    assert 'width="16" height="16"' in person
    assert "<path" not in blank and "<circle" not in blank


def test_d2_layout_pins_elk_with_a_tighter_rank_gap_than_dagre():
    # dagre offers no rank-separation knob, which is why every diagram used to
    # render taller than a laptop viewport. ELK's nodeNodeBetweenLayers is the
    # fix, and it only helps below its own default of 70.
    args = rh._D2_LAYOUT_ARGS
    assert args[args.index("--layout") + 1] == "elk"
    gap = int(args[args.index("--elk-nodeNodeBetweenLayers") + 1])
    assert 0 < gap < 70


_GRID_RE = re.compile(r"\bgrid-(rows|columns):")
_SIZE_RE = re.compile(r"\b(width|height):\s*\d")


def sizes_a_node_inside_a_grid(source: str) -> bool:
    """Does this d2 source set an explicit size on a node under a grid?

    Brace-scoped rather than a flat search, in both directions. A container
    declares its `grid-rows` indented, so an anchored match never fires; and a
    sized node in a *sibling* container is fine, so a whole-block match would
    cry wolf on the tier diagram, which has both and is correct.
    """
    depth = 0
    grid_depths: set[int] = set()
    for line in source.splitlines():
        if _GRID_RE.search(line):
            grid_depths.add(depth)
        if _SIZE_RE.search(line) and any(d <= depth for d in grid_depths):
            return True
        depth += line.count("{") - line.count("}")
        grid_depths = {d for d in grid_depths if d <= depth}
    return False


def test_sizes_a_node_inside_a_grid_sees_through_container_indentation():
    # The idiomatic form: the grid is declared inside a container, so it is
    # indented and an anchored `^grid-` would miss it entirely.
    assert sizes_a_node_inside_a_grid(
        "core: Reusable core {\n  grid-rows: 2\n  a: Alpha { width: 240 }\n}\n"
    )
    assert sizes_a_node_inside_a_grid("grid-rows: 1\na: Alpha { width: 240 }\n")


def test_sizes_a_node_inside_a_grid_leaves_a_sibling_container_alone():
    # A sized node beside a grid, not under it, is exactly what the tier
    # diagram does. Flagging it would make the guard unusable.
    assert not sizes_a_node_inside_a_grid(
        "task: Task layer {\n  width: 240\n  a: Agent A\n}\n"
        "core: Reusable core {\n  grid-rows: 2\n  b: Beta\n}\n"
    )


def test_no_handbook_diagram_sizes_nodes_inside_a_grid():
    # d2's grid layout forces every cell to the row's largest height, silently
    # discarding a per-node `height`. The screening funnel shipped that way for
    # one commit: it asked for six tapering stages, rendered six equal ones, and
    # the overall bbox was identical either way, so nothing downstream noticed.
    # The funnel has since moved off d2 onto its own fence, so it can no longer
    # regress this way; the guard stands for every d2 fence that follows it.
    source_dir = Path(rh.__file__).resolve().parent.parent / "docs" / "engineering"
    offenders = []
    for path in sorted(source_dir.glob("*.md")):
        _, blocks = rh.extract_diagram_blocks(path.read_text(), path.stem)
        for block in blocks:
            if block.kind == "d2" and sizes_a_node_inside_a_grid(block.source):
                offenders.append(f"{path.name}: {block.title}")
    assert not offenders, f"grid layout ignores explicit node sizes in {offenders}"


def test_extract_diagram_blocks_recognises_a_funnel_fence():
    md = '```funnel title="The funnel"\nMany candidates 100\nThe one 1\n```\n'
    out, blocks = rh.extract_diagram_blocks(md, "evaluation")
    assert '<div class="dgph" data-i="0"></div>' in out
    assert [(b.kind, b.title) for b in blocks] == [("funnel", "The funnel")]


def test_extract_diagram_blocks_rejects_an_unrecognised_funnel_fence():
    # Same trap as the d2 fence: left unmatched it would ship as a code block.
    with pytest.raises(ValueError, match="funnel"):
        rh.extract_diagram_blocks('```funnel title="x"\nA 10\n', "evaluation")


def test_parse_funnel_reads_the_count_off_the_end_of_each_line():
    stages = rh.parse_funnel(
        "Many candidates              10_000\nThe one you ship   1\n", "evaluation"
    )
    assert [(s.label, s.count) for s in stages] == [
        ("Many candidates", 10000),
        ("The one you ship", 1),
    ]


def test_parse_funnel_rejects_a_line_with_no_count():
    with pytest.raises(ValueError, match="does not end in a count"):
        rh.parse_funnel("Many candidates\nThe one you ship 1\n", "evaluation")


def test_parse_funnel_rejects_a_funnel_that_widens():
    # A funnel that grows is a typo, and the drawing would assert it as fact.
    with pytest.raises(ValueError, match="admits more items"):
        rh.parse_funnel("First 10\nSecond 50\n", "evaluation")


def test_parse_funnel_rejects_a_single_stage():
    with pytest.raises(ValueError, match="at least two stages"):
        rh.parse_funnel("Only one 10\n", "evaluation")


def test_funnel_bands_shrink_monotonically_and_stay_visible():
    # The log scale exists so the tail stays legible: on a linear scale a stage
    # of 1 against a first stage of 10000 is a sub-pixel sliver.
    stages = rh.parse_funnel("A 10000\nB 2000\nC 400\nD 60\nE 8\nF 1\n", "evaluation")
    svg = rh.funnel_svg(stages, "light")
    heights = [float(h) for h in re.findall(r'<rect[^>]*height="([\d.]+)"', svg)]
    assert len(heights) == 6
    assert heights == sorted(heights, reverse=True)
    assert heights[0] == rh._FUNNEL_BAND_MAX
    assert heights[-1] == rh._FUNNEL_BAND_MIN
    # Every stage stays thick enough to read as a band rather than a rule, which
    # is the property a linear scale loses: there, 1 against 10000 is 0.01px.
    assert min(heights) >= 12


def test_funnel_bands_are_log_spaced_not_linear():
    # Equal ratios between counts must give equal steps in height. That is what
    # "log scale" means here, and it is what a linear fallback would lose.
    stages = rh.parse_funnel("A 10000\nB 1000\nC 100\nD 10\nE 1\n", "evaluation")
    svg = rh.funnel_svg(stages, "light")
    heights = [float(h) for h in re.findall(r'<rect[^>]*height="([\d.]+)"', svg)]
    steps = [a - b for a, b in pairwise(heights)]
    assert max(steps) - min(steps) < 0.5


def test_funnel_lifts_the_count_off_a_band_too_thin_to_hold_it():
    # The tail of a log funnel is thinner than its own digits, so a centred
    # count would straddle the band's edges instead of sitting in it.
    stages = rh.parse_funnel("A 10000\nB 1\n", "evaluation")
    svg = rh.funnel_svg(stages, "light")
    rects = re.findall(r'<rect[^>]*y="([\d.]+)"[^>]*height="([\d.]+)"', svg)
    counts = [float(y) for y in re.findall(r'<text[^>]*y="([\d.]+)"[^>]*700"', svg)]
    thin_y, thin_h = (float(v) for v in rects[-1])
    assert thin_h < rh._FUNNEL_COUNT_INSIDE_MIN
    assert counts[-1] < thin_y  # lifted clear of the band's top edge


def test_funnel_svg_fits_the_prose_measure_and_names_no_size():
    stages = rh.parse_funnel("A 100\nB 1\n", "evaluation")
    svg = rh.funnel_svg(stages, "light")
    width, height = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg).groups()
    assert int(width) == rh._FUNNEL_WIDTH <= 771  # the artifact's measure
    assert int(height) > 0
    # prepare_svg adds width/height; emitting them here would duplicate them.
    assert 'width="' not in svg.split(">")[0]


def test_funnel_svg_draws_each_theme_in_its_own_palette():
    stages = rh.parse_funnel("A 100\nB 1\n", "evaluation")
    light, dark = rh.funnel_svg(stages, "light"), rh.funnel_svg(stages, "dark")
    assert rh.PALETTE["light"]["surface"] in light
    assert rh.PALETTE["light"]["surface"] not in dark
    assert rh.PALETTE["dark"]["surface"] in dark


def test_funnel_svg_emits_pure_ascii():
    # to_ascii_entities never looks inside a rendered SVG, so a literal thin
    # space in a grouped number would reach the browser as mojibake.
    stages = rh.parse_funnel("Many candidates 10000\nThe one 1\n", "evaluation")
    svg = rh.funnel_svg(stages, "light")
    svg.encode("ascii")
    assert "10&#8201;000" in svg


def test_funnel_labels_wrap_to_the_slab_width():
    assert rh.wrap_label("Semantic scoring, LLM judge", 12) == [
        "Semantic",
        "scoring, LLM",
        "judge",
    ]
    assert rh.wrap_label("Short", 12) == ["Short"]


def test_d2_preludes_and_the_funnel_read_from_one_palette():
    # A figure that drifts from the page's own colours reads as a picture from
    # another system, which is the thing the shared palette exists to prevent.
    for variant, colours in rh.PALETTE.items():
        assert colours["surface"] in rh.D2_PRELUDES[variant]
        assert colours["accent"] in rh.D2_PRELUDES[variant]


def test_the_print_prelude_paints_no_surface():
    prelude = rh.D2_PRINT_PRELUDE
    assert "**.style.fill: transparent" in prelude
    assert rh.PALETTE["light"]["surface"] not in prelude
    assert rh.PRINT_PALETTE["line"] in prelude
    assert rh.PRINT_PALETTE["accent"] in prelude


def test_the_page_palettes_are_untouched_by_print():
    assert set(rh.PALETTE) == {"light", "dark"}
    assert set(rh.D2_PRELUDES) == {"light", "dark"}


def test_the_vertical_funnel_label_budget_is_derived_like_the_horizontal_one():
    # Same formula funnel_svg uses for its own wrap budget, over the vertical
    # funnel's own label width; today's geometry puts it at 24, so the
    # committed evaluation-0 figure needs no re-seeding.
    expected = max(8, int(rh._VFUNNEL_LABEL_RIGHT / rh._FUNNEL_CHAR_W))
    assert rh._VFUNNEL_LABEL_BUDGET == expected == 24


def test_print_palette_reads_its_non_line_slots_from_the_light_theme():
    # `line` is print's own darker hairline (see the comment above
    # PRINT_PALETTE); every other slot must be the light theme's value by
    # reference, not a re-typed literal that could drift from it.
    for key in rh.PRINT_PALETTE:
        if key == "line":
            continue
        assert rh.PRINT_PALETTE[key] == rh.PALETTE["light"][key]


def _stages():
    return rh.parse_funnel(
        "Many candidates 10000\nCheap gates 2000\nComposite score 400\n"
        "Semantic scoring 60\nHuman adjudication 8\nThe one you ship 1\n",
        "evaluation",
    )


def test_the_vertical_funnel_fits_the_print_width():
    svg = rh.funnel_svg_vertical(_stages())
    w, h = map(float, re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg).groups())
    assert w <= 388.8 and h <= 648


def test_the_vertical_funnel_draws_one_hollow_band_per_stage():
    svg = rh.funnel_svg_vertical(_stages())
    rects = re.findall(r"<rect [^>]*>", svg)
    assert len(rects) == 6
    assert all('fill="none"' in r for r in rects)


def test_the_vertical_funnel_tints_are_translucent():
    svg = rh.funnel_svg_vertical(_stages())
    paths = re.findall(r"<path [^>]*>", svg)
    assert len(paths) == 5
    assert all(f'fill-opacity="{rh.PRINT_WASH_OPACITY}"' in p for p in paths)


def test_the_vertical_funnel_escapes_labels():
    stages = rh.parse_funnel("A & <b> 10\nC 1\n", "evaluation")
    svg = rh.funnel_svg_vertical(stages)
    assert "A &amp; &lt;b&gt;" in svg


@pytest.mark.skipif(
    shutil.which("d2") is None, reason="needs the d2 CLI; CI gains it with #192"
)
def test_a_print_render_carries_no_surface_fill():
    svg = rh.run_d2("a -> b", "t-print", "print")
    assert rh.PALETTE["light"]["surface"] not in svg
    assert rh.PRINT_PALETTE["line"] in svg


def test_extract_diagram_blocks_rejects_an_unclosed_fence():
    # An unclosed fence used to swallow every following paragraph up to the
    # next stray fence line, so the page lost content with nothing to notice.
    md = '```d2 title="One"\na -> b\n\nSome prose that must not be swallowed.\n'
    with pytest.raises(ValueError, match="unrecognised"):
        rh.extract_diagram_blocks(md, "lifecycle")


def test_extract_diagram_blocks_rejects_an_indented_fence():
    md = '1. A step:\n\n   ```d2 title="One"\n   a -> b\n   ```\n'
    with pytest.raises(ValueError, match="column 0"):
        rh.extract_diagram_blocks(md, "lifecycle")


def test_extract_diagram_blocks_does_not_overrun_a_following_fence():
    md = (
        '```d2 title="One"\na -> b\n```\n\ntext\n\n'
        "```python\nprint(1)\n```\n\nmore text\n"
    )
    out, blocks = rh.extract_diagram_blocks(md, "x")
    assert len(blocks) == 1
    assert blocks[0].source == "a -> b\n"
    assert "```python\nprint(1)\n```" in out  # untouched, not absorbed
    assert "more text" in out


def test_extract_diagram_blocks_rejects_a_title_with_escaped_quotes():
    # Silently truncating to `Foo \` would ship a wrong caption; erroring is
    # what makes the mistake visible.
    with pytest.raises(ValueError, match="title"):
        rh.extract_diagram_blocks('```d2 title="Foo \\"Bar\\""\na\n```\n', "x")


def test_diagram_figure_escapes_the_caption():
    # to_ascii_entities only rewrites non-ASCII, so an unescaped & or < in a
    # title would reach the browser intact and corrupt the markup after it.
    block = rh.DiagramBlock(
        index=0, kind="d2", title="Retrieve & rerank <2s", source="a\n"
    )
    svg = '<svg viewBox="0 0 1 2"></svg>'
    out = rh.diagram_figure("evaluation", block, svg, svg)
    assert "Retrieve &amp; rerank &lt;2s" in out
    assert "<2s" not in out


def test_render_variants_draws_a_funnel_without_reaching_for_the_cli():
    # The dispatch is the only thing standing between a `funnel` fence and the
    # d2 subprocess. Route it wrong and every funnel would be fed to a CLI that
    # cannot parse it, so the branch is worth a test of its own.
    called = []
    block = rh.DiagramBlock(
        index=0, kind="funnel", title="Funnel", source="Many 100\nOne 1\n"
    )
    light, dark = rh.render_variants(block, "evaluation")
    assert not called
    assert 'class="funnel"' in light and 'class="funnel"' in dark
    assert light != dark  # the two palettes


def test_render_variants_sends_a_d2_fence_to_the_cli(monkeypatch):
    calls = []

    def fake_run_d2(source, salt, variant):
        calls.append((source, salt, variant))
        return f"<svg data-v='{variant}'></svg>"

    monkeypatch.setattr(rh, "run_d2", fake_run_d2)
    block = rh.DiagramBlock(index=3, kind="d2", title="Arc", source="a -> b\n")
    light, dark = rh.render_variants(block, "README")
    assert [c[1] for c in calls] == ["README-3-light", "README-3-dark"]
    assert [c[2] for c in calls] == ["light", "dark"]
    assert "light" in light and "dark" in dark


def test_group_digits_separates_thousands_with_an_ascii_entity():
    assert rh.group_digits(1) == "1"
    assert rh.group_digits(999) == "999"
    assert rh.group_digits(1000) == "1&#8201;000"
    assert rh.group_digits(10000) == "10&#8201;000"
    assert rh.group_digits(1234567) == "1&#8201;234&#8201;567"
    assert rh.group_digits(1000).isascii()


def test_parse_funnel_rejects_more_stages_than_fit_the_width():
    # Stages share a fixed width; past the bound the slab is narrower than its
    # own label, and further out the rect width goes negative.
    n = rh._FUNNEL_MAX_STAGES + 1
    body = "".join(f"Stage {i} {n - i}\n" for i in range(n))
    with pytest.raises(ValueError, match="does not fit"):
        rh.parse_funnel(body, "evaluation")


def test_funnel_bands_stay_positive_at_the_maximum_stage_count():
    n = rh._FUNNEL_MAX_STAGES
    stages = rh.parse_funnel("".join(f"Stage {i} {n - i}\n" for i in range(n)), "x")
    svg = rh.funnel_svg(stages, "light")
    widths = [float(w) for w in re.findall(r'<rect\b[^>]*?\swidth="([-\d.]+)"', svg)]
    assert len(widths) == n
    assert all(w >= rh._FUNNEL_MIN_SLAB for w in widths)


def _one_part_docs(tmp_path: Path, body: str) -> Path:
    (tmp_path / "solo.md").write_text(body)
    return tmp_path


def test_build_rejects_a_sibling_link_naming_no_part(tmp_path):
    # The parts are siblings, so a bare stem is a claim that this artifact
    # contains that part. When it does not, the link is dead in the page and
    # resolves on GitHub, and nothing else in the repository reads the
    # handbook's links - so warning alone would be a silent pass. An
    # out-of-tree target (with a path separator) is a different case and is
    # unlinked rather than rejected; see the build test above.
    docs = _one_part_docs(tmp_path, "[gone](nonexistent.md)\n")
    with pytest.raises(ValueError, match=r"relative link\(s\)"):
        rh.build(docs, [("top", "solo", "Solo")])


def test_build_accepts_an_absolute_md_url_and_in_handbook_links(tmp_path):
    # Absolute URLs are unmapped by design: they are meant to leave the page.
    docs = _one_part_docs(
        tmp_path,
        "[notes](https://github.com/o/r/blob/main/docs/engineering-notes.md)\n"
        "and [self](solo.md)\n",
    )
    html = rh.build(docs, [("top", "solo", "Solo")])
    assert "engineering-notes.md" in html
    assert 'href="#top"' in html


def test_parts_lists_every_handbook_file_on_disk():
    # A part file absent from PARTS is silently missing from the artifact: no
    # error, no warning, just a page one section short. The traceability
    # renderer guards its own two constants in `validate_parts`; nothing
    # guarded this one, so a handbook that grew a part could render into the
    # matrix and out of the page at the same time.
    handbook = Path(__file__).resolve().parents[2] / "docs" / "engineering"
    assert {stem for _, stem, _ in rh.PARTS} == {p.stem for p in handbook.glob("*.md")}


def test_assemble_returns_each_part_with_ids_and_rewritten_links(tmp_path: Path):
    pytest.importorskip("markdown")
    (tmp_path / "README.md").write_text("# Handbook\n\nSee [later](later.md).\n")
    (tmp_path / "later.md").write_text("# Later\n\ntext\n")
    parts = [("top", "README", "Overview"), ("p1", "later", "Later")]
    assembled = rh.assemble(tmp_path, parts)
    assert [(a.anchor, a.stem) for a in assembled] == [
        ("top", "README"),
        ("p1", "later"),
    ]
    assert '<h1 id="README-handbook">Handbook</h1>' in assembled[0].html
    assert 'href="#p1"' in assembled[0].html
    assert assembled[0].blocks == []


def test_assemble_honours_a_caller_supplied_linkmap(tmp_path: Path):
    pytest.importorskip("markdown")
    (tmp_path / "README.md").write_text("# Handbook\n\nSee [later](later.md).\n")
    (tmp_path / "later.md").write_text("# Later\n\ntext\n")
    parts = [("top", "README", "Overview"), ("p1", "later", "Later")]
    linkmap = {"README.md": "#README-handbook", "later.md": "#later-later"}
    assembled = rh.assemble(tmp_path, parts, linkmap)
    assert 'href="#later-later"' in assembled[0].html


def test_assemble_raises_on_a_dead_relative_link(tmp_path: Path):
    pytest.importorskip("markdown")
    (tmp_path / "README.md").write_text("# Handbook\n\nSee [x](missing.md).\n")
    with pytest.raises(ValueError, match=re.escape("missing.md")):
        rh.assemble(tmp_path, [("top", "README", "Overview")])


def test_assemble_raises_when_two_parts_heading_ids_collide(tmp_path: Path):
    """`assemble`'s own `ids & set(part_ids)` check, not `add_heading_ids`'s.

    `add_heading_ids` only catches a collision within one part; this is the
    cross-part half, for two parts whose ``<stem>-<slug>`` land on the same
    string by different routes. Stem ``a-b`` heading ``C`` and stem ``a``
    heading ``B C`` both slugify to ``a-b-c``, so the second part rendered
    collides with the id the first already added to the page.
    """
    pytest.importorskip("markdown")
    (tmp_path / "a-b.md").write_text("# Intro\n\n## C\n")
    (tmp_path / "a.md").write_text("# Intro\n\n## B C\n")
    parts = [("p1", "a-b", "AB"), ("p2", "a", "A")]
    with pytest.raises(
        ValueError, match=re.escape("a.md: heading id(s) ['a-b-c'] collide")
    ):
        rh.assemble(tmp_path, parts)
