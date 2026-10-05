"""The paperback interior: `render_handbook_book.py --format pdf`."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import book_figures as bf
import book_publication as bp
import kdp_print as kp
import pytest
import render_handbook_artifact as rh
import render_handbook_book as rb

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / "docs" / "engineering"
HOLDER = "A*B #1 [x] $y$ \\z"


def test_the_interior_margins_leave_exactly_the_figures_text_block():
    m = rb.INTERIOR_MARGINS_IN
    width = rb.TRIM_IN[0] - m["inside"] - m["outside"]
    height = rb.TRIM_IN[1] - m["top"] - m["bottom"]
    assert (width * 72, height * 72) == pytest.approx(bf.TEXT_BLOCK_PT)


def test_the_template_states_the_builders_margins_and_trim():
    template = rb.INTERIOR_TEMPLATE.read_text(encoding="utf-8")
    m = rb.INTERIOR_MARGINS_IN
    assert (
        f"margin: (inside: {m['inside']}in, outside: {m['outside']}in, "
        f"top: {m['top']}in, bottom: {m['bottom']}in)"
    ) in template
    assert f"width: {rb.TRIM_IN[0]:g}in" in template
    assert f"height: {rb.TRIM_IN[1]:g}in" in template


def test_the_inside_margin_meets_kdps_minimum_for_any_plausible_length():
    assert rb.INTERIOR_MARGINS_IN["inside"] >= kp.gutter_minimum(700)
    assert rb.INTERIOR_MARGINS_IN["outside"] >= kp.OUTSIDE_MARGIN_MIN_IN


def test_the_typst_compile_command_uses_only_the_committed_fonts(tmp_path):
    cmd = rb.typst_compile_command(
        tmp_path / "m.typ", tmp_path / "o.pdf", {"isbn": "[ISBN]"}
    )
    assert cmd[:2] == ["typst", "compile"]
    assert "--ignore-system-fonts" in cmd
    assert cmd[cmd.index("--font-path") + 1] == str(rb.FONTS_ROOT)
    assert cmd[cmd.index("--input") + 1] == "isbn=[ISBN]"
    assert cmd[-2:] == [str(tmp_path / "m.typ"), str(tmp_path / "o.pdf")]


def test_the_page_count_command_evaluates_the_templates_marker(tmp_path):
    cmd = rb.typst_page_count_command(tmp_path / "m.typ", {})
    assert cmd[:2] == ["typst", "eval"]
    assert "query(<page-count>).first().value" in cmd
    assert cmd[cmd.index("--in") + 1] == str(tmp_path / "m.typ")


def test_the_pandoc_typst_command_writes_the_body_only(tmp_path):
    cmd = rb.typst_body_command(tmp_path / "b.html", tmp_path / "b.typ")
    assert "-s" not in cmd and "--standalone" not in cmd
    assert cmd[cmd.index("-t") + 1] == "typst"
    assert cmd[cmd.index("-f") + 1] == "html"


def test_the_main_file_applies_the_template_to_the_body():
    main = rb.interior_main("body.typ")
    assert '#import "book_interior.typ": interior, horizontalrule' in main
    assert main.index("#show: interior") < main.index('#include "body.typ"')


def test_a_final_build_refuses_unset_details_before_running_any_tool(
    tmp_path, monkeypatch
):
    details = tmp_path / "publication.toml"
    details.write_text('isbn = "9780306406157"\n', encoding="utf-8")
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(SystemExit) as exc:
        rb.main(["--format", "pdf", "--final", "--details", str(details)])
    assert "copyright_holder" in str(exc.value)
    assert "isbn," not in str(exc.value)


# The built interior. Needs pandoc and typst, and d2 only while a d2 fence has
# no committed figure.
needs_print_tools = pytest.mark.skipif(
    shutil.which("pandoc") is None or shutil.which("typst") is None,
    reason="pandoc and typst CLIs needed; CI gains them with #192",
)


@pytest.fixture(scope="module")
def built_pdf(tmp_path_factory) -> tuple[Path, int, Path]:
    pytest.importorskip("markdown")
    if shutil.which("pandoc") is None or shutil.which("typst") is None:
        pytest.skip("pandoc and typst CLIs needed; CI gains them with #192")
    root = tmp_path_factory.mktemp("pdf")
    details = root / "publication.toml"
    # A TOML literal string: no escapes, so the value arrives as written.
    details.write_text(f"copyright_holder = '{HOLDER}'\n", encoding="utf-8")
    work = root / "work"
    out, pages = rb.build_pdf(
        DOCS, root / "nested" / "interior.pdf", details, final=False, work_dir=work
    )
    return out, pages, work


def _pdf_text(pdf: Path, first: int | None = None, last: int | None = None) -> str:
    if shutil.which("pdftotext") is None:
        pytest.skip("pdftotext (poppler) not installed")
    cmd = ["pdftotext"]
    if first is not None:
        cmd += ["-f", str(first), "-l", str(last or first)]
    proc = subprocess.run(
        [*cmd, str(pdf), "-"], capture_output=True, text=True, check=True, timeout=60
    )
    return proc.stdout


@needs_print_tools
def test_the_typst_body_carries_every_heading_id_as_a_label(built_pdf):
    _, _, work = built_pdf
    labels = set(re.findall(r"<([A-Za-z0-9_.:-]+)>", (work / "body.typ").read_text()))
    part_anchors = {anchor for anchor, _, _ in rh.PARTS}
    assert rh.heading_ids(DOCS) - part_anchors <= labels


@needs_print_tools
def test_the_typst_body_carries_one_image_per_diagram_fence(built_pdf):
    _, _, work = built_pdf
    blocks = rb.part_blocks(DOCS)
    widths = dict(
        re.findall(
            r'image\("media/([^"]+)\.svg", width: ([\d.]+)pt',
            (work / "body.typ").read_text(),
        )
    )
    assert len(widths) == len(blocks)
    for stem, block in blocks:
        svg, _ = rb.load_figure(DOCS / "figures", stem, block)
        assert float(widths[f"{stem}-{block.index}"]) == pytest.approx(
            bf.print_width_pt(svg), abs=0.01
        )


@needs_print_tools
def test_the_interior_prints_each_detail_or_its_placeholder(built_pdf):
    text = _pdf_text(built_pdf[0], 1, 8)
    assert HOLDER in text
    assert bp.PLACEHOLDERS["isbn"] in text
    assert bp.PLACEHOLDERS["copyright_year"] in text


@needs_print_tools
def test_an_in_book_link_prints_its_page(built_pdf):
    assert re.search(r"Part\s1\s\(p\.\s\d+\)", _pdf_text(built_pdf[0]))


@needs_print_tools
def test_the_page_count_is_the_pdfs(built_pdf):
    pdf, pages, _ = built_pdf
    if shutil.which("pdfinfo") is None:
        pytest.skip("pdfinfo (poppler) not installed")
    info = subprocess.run(
        ["pdfinfo", str(pdf)], capture_output=True, text=True, check=True, timeout=60
    ).stdout
    assert int(re.search(r"^Pages:\s+(\d+)", info, re.M).group(1)) == pages


@needs_print_tools
def test_every_font_is_embedded_and_committed(built_pdf):
    if shutil.which("pdffonts") is None:
        pytest.skip("pdffonts (poppler) not installed")
    listing = subprocess.run(
        ["pdffonts", str(built_pdf[0])],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout.splitlines()[2:]
    committed = {p.stem for p in rb.FONTS_ROOT.glob("*/*.ttf")}
    assert listing, "pdffonts listed no font, so this proves nothing"
    for row in listing:
        name, *_, emb, _sub, _uni, _obj, _gen = row.split()
        assert emb == "yes", row
        assert name.split("+", 1)[-1] in committed, row


@needs_print_tools
def test_each_part_opens_on_a_recto_page(built_pdf):
    pdf, pages, _ = built_pdf
    titles = {
        rb.BOOK_PART_TITLES.get(
            stem, (DOCS / f"{stem}.md").read_text().splitlines()[0].lstrip("# ")
        )[:12]
        for _, stem, _ in rh.PARTS
    }
    openings = {}
    for page in range(1, pages + 1):
        lines = _pdf_text(pdf, page).strip().splitlines()
        if lines and lines[0][:12] in titles:
            openings.setdefault(lines[0][:12], page)
    assert set(openings) == titles, sorted(titles - set(openings))
    assert all(page % 2 == 1 for page in openings.values()), openings


@needs_print_tools
def test_a_checklist_draws_its_box_in_place_of_the_bullet(built_pdf):
    text = _pdf_text(built_pdf[0])
    assert "☐" in text
    assert not re.search(r"•\s*[☐☒]", text)


@needs_print_tools
def test_a_missing_typst_is_named_with_its_install_command(tmp_path, monkeypatch):
    pytest.importorskip("markdown")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "pandoc").symlink_to(shutil.which("pandoc"))
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}/usr/bin{os.pathsep}/bin")
    details = tmp_path / "publication.toml"
    details.write_text("", encoding="utf-8")
    with pytest.raises(SystemExit, match=r"typst.*brew install typst"):
        rb.build_pdf(DOCS, tmp_path / "o.pdf", details, final=False)


@needs_print_tools
def test_the_introduction_is_page_one_on_a_recto(built_pdf):
    pdf, pages, _ = built_pdf
    for page in range(1, pages + 1):
        lines = _pdf_text(pdf, page).strip().splitlines()
        if lines and lines[0] == rb.BOOK_PART_TITLES["README"]:
            assert page % 2 == 1
            assert lines[-1].strip() == "1"
            return
    pytest.fail("no page opens with the Introduction")


@needs_print_tools
def test_the_title_page_never_hyphenates_the_title(built_pdf):
    # Plain pdftotext output rejoins a hyphenated word; its word boxes do not.
    if shutil.which("pdftotext") is None:
        pytest.skip("pdftotext (poppler) not installed")
    boxes = subprocess.run(
        ["pdftotext", "-bbox", "-f", "1", "-l", "4", str(built_pdf[0]), "-"],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout
    words = re.findall(r"<word [^>]*>([^<]*)</word>", boxes)
    assert "Handbook" in words
    # Typst marks a break it made with a soft hyphen (U+00AD).
    assert not [w for w in words if w.endswith(("-", "\u00ad", "\u2010"))]


@needs_print_tools
def test_a_gutter_too_narrow_for_the_page_count_leaves_no_pdf(tmp_path, monkeypatch):
    pytest.importorskip("markdown")
    monkeypatch.setitem(rb.INTERIOR_MARGINS_IN, "inside", 0.1)
    details = tmp_path / "publication.toml"
    details.write_text("", encoding="utf-8")
    out = tmp_path / "interior.pdf"
    with pytest.raises(SystemExit, match="inside margin"):
        rb.build_pdf(DOCS, out, details, final=False)
    assert not out.exists()
