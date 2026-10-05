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
BACK_TEXT = "Read #me [now] *gently* $x$ \\back"


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


def test_spine_text_is_set_only_where_its_line_fits_between_the_fold_margins():
    # 90 cream pages pass KDP's page minimum, but 0.225 in of spine less two
    # 0.0625 in margins leaves 7.2 pt, too narrow for a legible line.
    assert rb.cover_inputs(90, bp.PublicationDetails())["spine-text"] == "false"
    roomy = rb.cover_inputs(125, bp.PublicationDetails())
    assert roomy["spine-text"] == "true"
    room_pt = (float(roomy["spine"]) - 2 * kp.SPINE_TEXT_MARGIN_IN) * 72
    assert float(roomy["spine-text-size"]) * rb.SPINE_LINE_RATIO <= room_pt


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
    # A TOML literal string: the back cover's text carries Typst syntax.
    details.write_text(f"back_cover_text = '{BACK_TEXT}'\n", encoding="utf-8")
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
    assert BACK_TEXT in text
    assert "[Barcode area]" in text


@needs_print_tools
def test_no_front_cover_text_reaches_into_the_safe_zone(built_cover):
    pdf, pages = built_cover
    width, height = kp.cover_dimensions(rb.TRIM_IN, pages, rb.PAPER)
    fold = (kp.BLEED_IN + rb.TRIM_IN[0] + kp.spine_width(pages, rb.PAPER)) * 72
    edge = (kp.BLEED_IN + kp.COVER_SAFE_IN) * 72
    words = re.findall(
        r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">',
        _poppler("pdftotext", pdf, "-bbox"),
    )
    front = [tuple(map(float, w)) for w in words if float(w[0]) >= fold]
    assert front, "no word on the front cover, so this proves nothing"
    for x_min, y_min, x_max, y_max in front:
        assert x_min >= fold + kp.COVER_SAFE_IN * 72 - 0.5
        assert x_max <= width * 72 - edge + 0.5
        assert y_min >= edge - 0.5
        assert y_max <= height * 72 - edge + 0.5


@needs_print_tools
def test_every_cover_font_is_embedded_and_committed(built_cover):
    rows = _poppler("pdffonts", built_cover[0]).splitlines()[2:]
    committed = {p.stem for p in rb.FONTS_ROOT.glob("*/*.ttf")}
    assert rows
    for row in rows:
        name, *_, emb, _sub, _uni, _obj, _gen = row.split()
        assert emb == "yes", row
        assert name.split("+", 1)[-1] in committed, row
