"""The paperback's wraparound cover: `render_handbook_book.py --format cover`."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import book_publication as bp
import kdp_print as kp
import pytest
import render_handbook_book as rb

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / "docs" / "engineering"


def test_cover_inputs_size_the_page_from_the_page_count():
    inputs = rb.cover_inputs(120, bp.PublicationDetails())
    assert float(inputs["width"]) == pytest.approx(0.125 + 5 + 0.3 + 5 + 0.125)
    assert float(inputs["height"]) == pytest.approx(8.25)
    assert float(inputs["spine"]) == pytest.approx(0.3)
    assert float(inputs["bleed"]) == kp.BLEED_IN
    assert float(inputs["trim-width"]) == rb.TRIM_IN[0]
    assert inputs["spine-text"] == "true"
    assert inputs["isbn-set"] == "false"
    assert inputs["back-cover-text"] == bp.PLACEHOLDERS["back_cover_text"]
    assert inputs["cover-art"] == ""


def test_a_thin_book_has_no_spine_text():
    assert rb.cover_inputs(60, bp.PublicationDetails())["spine-text"] == "false"


def test_cover_art_is_named_by_the_file_the_build_copies_beside_the_template():
    details = bp.PublicationDetails(cover_art="docs/book/front.png")
    assert rb.cover_inputs(120, details)["cover-art"] == "front.png"


def test_a_missing_cover_art_file_is_refused(tmp_path):
    details = tmp_path / "publication.toml"
    details.write_text('cover_art = "docs/book/no-such.png"\n', encoding="utf-8")
    with pytest.raises(SystemExit, match=r"no-such\.png"):
        rb.build_cover(DOCS, tmp_path / "c.pdf", details, final=False)


needs_print_tools = pytest.mark.skipif(
    shutil.which("pandoc") is None or shutil.which("typst") is None,
    reason="pandoc and typst CLIs needed; CI gains them with #192",
)


@pytest.fixture(scope="module")
def built_cover(tmp_path_factory) -> tuple[Path, int]:
    pytest.importorskip("markdown")
    if shutil.which("pandoc") is None or shutil.which("typst") is None:
        pytest.skip("pandoc and typst CLIs needed; CI gains them with #192")
    root = tmp_path_factory.mktemp("cover")
    details = root / "publication.toml"
    details.write_text("", encoding="utf-8")
    return rb.build_cover(DOCS, root / "nested" / "cover.pdf", details, final=False)


def _poppler(tool: str, pdf: Path, *args: str) -> str:
    if shutil.which(tool) is None:
        pytest.skip(f"{tool} (poppler) not installed")
    return subprocess.run(
        [tool, *args, str(pdf), *(["-"] if tool == "pdftotext" else [])],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout


@needs_print_tools
def test_the_cover_is_one_page_at_kdps_size_for_the_page_count(built_cover):
    pdf, pages = built_cover
    info = _poppler("pdfinfo", pdf)
    assert re.search(r"^Pages:\s+1$", info, re.M)
    w, h = map(float, re.search(r"Page size:\s+([\d.]+) x ([\d.]+) pts", info).groups())
    want_w, want_h = kp.cover_dimensions(rb.TRIM_IN, pages, rb.PAPER)
    assert w == pytest.approx(want_w * 72, abs=0.5)
    assert h == pytest.approx(want_h * 72, abs=0.5)


@needs_print_tools
def test_the_cover_prints_the_title_and_the_back_cover_placeholder(built_cover):
    text = " ".join(_poppler("pdftotext", built_cover[0]).split())
    assert "AI Agent Development Handbook" in text
    assert bp.PLACEHOLDERS["back_cover_text"] in text
    assert "[Barcode area]" in text


@needs_print_tools
def test_every_cover_font_is_embedded_and_committed(built_cover):
    rows = _poppler("pdffonts", built_cover[0]).splitlines()[2:]
    committed = {p.stem for p in rb.FONTS_ROOT.glob("*/*.ttf")}
    assert rows
    for row in rows:
        name, *_, emb, _sub, _uni, _obj, _gen = row.split()
        assert emb == "yes", row
        assert name.split("+", 1)[-1] in committed, row
