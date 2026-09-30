"""Every committed book figure matches its fence and holds the print checks."""

from __future__ import annotations

from pathlib import Path

import book_figures as bf
import pytest
import render_handbook_book as rb
from render_handbook_artifact import PARTS

DOCS = Path(__file__).resolve().parents[2] / "docs" / "engineering"
FIGURES = DOCS / "figures"
BLOCKS = {f"{stem}-{b.index}": b for stem, b in rb.part_blocks(DOCS, PARTS)}
COMMITTED = sorted(FIGURES.glob("*.svg"))


def test_every_committed_figure_names_a_fence():
    assert [p.name for p in COMMITTED if p.stem not in BLOCKS] == []


@pytest.mark.parametrize("path", COMMITTED, ids=lambda p: p.stem)
def test_a_committed_figure_was_drawn_from_its_fence_as_it_stands(path):
    block = BLOCKS[path.stem]
    expected = bf.source_hash(block.source)
    assert bf.recorded_hash(path.read_text()) == expected, (
        f"{path.name} was drawn from an older version of the fence titled "
        f"{block.title!r}; redraw it, or confirm it still holds and re-stamp "
        f'its root <svg> with data-source-sha256="{expected}"'
    )


@pytest.mark.parametrize("path", COMMITTED, ids=lambda p: p.stem)
def test_a_committed_figure_holds_the_print_checks(path):
    svg = path.read_text()
    assert (
        bf.fit_problems(svg) + bf.opaque_fill_problems(svg) + bf.contrast_problems(svg)
        == []
    )
    # The build's EPUB copy of this file, made here without pandoc so a hand
    # edit that `embed_fonts` cannot read fails on any machine, not only
    # where the full build runs. A figure whose lettering is outlined has no
    # text and gets no face; one with live text gets every face it uses.
    embedded = bf.embed_fonts(svg, rb.FONT_DIR)
    assert ("@font-face" in embedded) == bool(bf.used_faces(svg))


def test_a_figure_stale_against_its_fence_fails_the_hash_check(tmp_path):
    """Injects the failure `test_a_committed_figure_was_drawn_from_its_fence_as_it_stands`
    exists to catch, so that test's pass is never vacuous: a figure stamped
    with a hash that no longer matches its fence must fail that test's own
    assertion, called directly here rather than re-derived, so a later
    weakening of the guard shows up here too.
    """
    original = COMMITTED[0]
    stale = bf.stamp_hash(original.read_text(), bf.source_hash("changed"))
    path = tmp_path / original.name
    path.write_text(stale)
    expected = bf.source_hash(BLOCKS[original.stem].source)
    with pytest.raises(AssertionError, match="older version of the fence") as info:
        test_a_committed_figure_was_drawn_from_its_fence_as_it_stands(path)
    assert f'data-source-sha256="{expected}"' in str(info.value)
