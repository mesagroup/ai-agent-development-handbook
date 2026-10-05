# Paperback Interior and Cover Implementation Plan (#195)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `render_handbook_book.py --format pdf` writes the KDP paperback interior and `--format cover` writes its wraparound cover. Every detail the maintainer has not decided yet (copyright holder, ISBN, cover art, back-cover text) prints as a visible placeholder and is kept in one committed file, so filling it in is the whole of the work later.

**Architecture:** The print build shares the EPUB's assembly: the same `render_parts`, `assemble`, figure loading and HTML passes produce one book document. A `print` target differs only in its figure markup (a width in points at the one scale) and its checklist wrapper. Pandoc writes that document as a body-only Typst file. The build then writes a small main file that imports a committed Typst template (`scripts/book_interior.typ`), passes the publication details as `typst compile --input` values, and includes the body. KDP's numbers live in a pure module (`scripts/kdp_print.py`), and the deferred details live in `docs/book/publication.toml`, read by `scripts/book_publication.py`. The cover is a second committed template (`scripts/book_cover.typ`), sized from the interior's page count, which the build reads back with `typst query`.

**Tech Stack:** Python 3.12 via `uv run`, pandoc 3.8 CLI (`-t typst`), Typst 0.15 CLI, `tomllib` (stdlib), pytest, ruff. Local checks use poppler's `pdfinfo` and `pdffonts` when installed.

**Spec:** `docs/superpowers/specs/2026-09-25-handbook-book-pipeline-design.md`. This plan implements its delivery item 3 (#195): the Typst template, `--format pdf` and `--format cover`, the spine computation and the manual previewer step.

## Global Constraints

- Run Python through `uv run`. Run `uv run ruff check . && uv run ruff format --check .` before every commit.
- No em dash (U+2014) in `docs/superpowers/plans/` or `docs/superpowers/specs/`. Use ` - `.
- Markdown is never hard-wrapped. One paragraph is one source line.
- No bare `except Exception: pass`. Every exception is reported with type and message, or re-raised.
- Every subprocess call goes through `run_tool` (or a sibling that captures stdout) with a timeout.
- The EPUB's output must not change: the document the EPUB build hands pandoc is byte-identical before and after the refactor in Task 3.
- Commit with explicit paths: `git commit -F - -- <paths>`. A new file is `git add`-ed first. Never `git add -A`, `git add .` or `git commit -a`.
- Commit messages end with `Refs #195` and carry no AI attribution trailer (the `commit-msg` hook refuses one).
- No environment-specific values in committed files: no absolute personal paths, emails or hostnames.
- A new module in `scripts/` joins `[tool.deptry] known_first_party` in `pyproject.toml`; `tests/test_deptry_gate.py` holds that list against the directory.
- KDP's numbers are copied from KDP's help pages, never recalled. Each constant carries the page it came from:
  - Interior: https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6 ("Set Trim Size, Bleed, and Margins"). Inside margin by page count: 24-150 pages 0.375 in; 151-300 0.5 in; 301-500 0.625 in; 501-700 0.75 in; 701-828 0.875 in. Outside margin without bleed at least 0.25 in. 5 x 8 in, black ink on cream paper: 24 to 828 pages.
  - Cover: https://kdp.amazon.com/en_US/help/topic/G201953020 ("Create a Paperback Cover"). Spine width = pages x 0.002252 in (white paper) or pages x 0.0025 in (cream). Bleed 0.125 in on top, bottom and outside edges. Cover width = bleed + back + spine + front + bleed; cover height = bleed + trim height + bleed. Spine text only at 79 pages or more, with at least 0.0625 in between the text and each spine edge. Cover text at least 0.125 in inside the trim.
  - Barcode: https://kdp.amazon.com/en_US/help/topic/G201857950 ("Paperback Submission Guidelines"). Barcode area 2 x 1.2 in, at least 0.25 in from the spine and from the trim.
- Decided values (spec and #195): trim 5 x 8 in; black ink on cream paper; text block 3.6 x 6 in (`book_figures.TEXT_BLOCK_PT`); faces Source Serif 4 (body), Source Sans 3 (headings), Source Code Pro (code), all from `fonts/`; publisher line "Independently published"; licence CC BY 4.0; author Janos Tolgyesi.
- Undecided values are never guessed. Each one prints as a bracketed placeholder, for example `[Copyright holder]`, until `docs/book/publication.toml` gives it.

## Review Focus

1. **A placeholder reaching a release.** A build with any detail still unset must be refusable: `--final` exits non-zero naming every unset field at once. Test in Task 2 (pure) and Task 4 (CLI).
2. **A malformed ISBN.** KDP's ISBN is typed in by hand. A value that is not a valid ISBN-13 (wrong length, wrong check digit, stray characters other than hyphens) must be rejected when the file is loaded, not printed. Test in Task 2.
3. **A page count outside KDP's range.** `spine_width` and `gutter_minimum` must raise on fewer than 24 or more than 828 pages, rather than extrapolate. Test in Task 1.
4. **Typst absent, or pandoc absent.** The build stops with a message naming the tool and its install command, as the EPUB build does. Tests that need either tool skip with a stated reason. Test in Task 4.
5. **A detail value with Typst syntax in it** (`#`, `[`, `]`, `*`, `$`, `\`). Details reach Typst as `--input` strings and the template prints them as plain text with `sys.inputs.at(...)`, never through `eval`, so a holder named `A*B #1` prints as written. Test in Task 4.

---

### Task 1: KDP's print numbers as pure functions

**Files:**
- Create: `scripts/kdp_print.py`
- Create: `tests/scripts/test_kdp_print.py`
- Modify: `pyproject.toml` (`known_first_party` gains `"kdp_print"`, alphabetically)

**Interfaces:**
- Produces: `Paper` (a `Literal["white", "cream"]`), `MIN_PAGES = 24`, `MAX_PAGES = 828`, `BLEED_IN = 0.125`, `SPINE_TEXT_MIN_PAGES = 79`, `SPINE_TEXT_MARGIN_IN = 0.0625`, `COVER_SAFE_IN = 0.125`, `BARCODE_IN = (2.0, 1.2)`, `BARCODE_MARGIN_IN = 0.25`, `gutter_minimum(pages: int) -> float`, `spine_width(pages: int, paper: Paper) -> float`, `spine_text_allowed(pages: int) -> bool`, `cover_dimensions(trim: tuple[float, float], pages: int, paper: Paper) -> tuple[float, float]`. All lengths in inches.

- [ ] **Step 1: Write the failing tests**

```python
"""KDP's paperback numbers, against the values KDP publishes.

Sources: https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6 (margins)
and https://kdp.amazon.com/en_US/help/topic/G201953020 (cover and spine).
"""

import pytest

import kdp_print as kp


@pytest.mark.parametrize(
    ("pages", "inches"),
    [(24, 0.375), (150, 0.375), (151, 0.5), (300, 0.5), (301, 0.625),
     (500, 0.625), (501, 0.75), (700, 0.75), (701, 0.875), (828, 0.875)],
)  # fmt: skip
def test_gutter_minimum_follows_kdps_bands(pages, inches):
    assert kp.gutter_minimum(pages) == inches


@pytest.mark.parametrize("pages", [0, 23, 829])
def test_a_page_count_outside_kdps_range_raises(pages):
    with pytest.raises(ValueError, match=str(pages)):
        kp.gutter_minimum(pages)
    with pytest.raises(ValueError, match=str(pages)):
        kp.spine_width(pages, "cream")


def test_spine_width_is_pages_times_the_papers_thickness():
    assert kp.spine_width(100, "cream") == pytest.approx(0.25)
    assert kp.spine_width(100, "white") == pytest.approx(0.2252)
    assert kp.spine_width(120, "cream") == pytest.approx(0.3)


def test_an_unknown_paper_raises():
    with pytest.raises(ValueError, match="glossy"):
        kp.spine_width(100, "glossy")


def test_spine_text_needs_79_pages():
    assert not kp.spine_text_allowed(78)
    assert kp.spine_text_allowed(79)


def test_cover_dimensions_add_bleed_on_the_outside_edges_and_the_spine_between():
    width, height = kp.cover_dimensions((5.0, 8.0), 120, "cream")
    assert width == pytest.approx(0.125 + 5.0 + 0.3 + 5.0 + 0.125)
    assert height == pytest.approx(0.125 + 8.0 + 0.125)
```

- [ ] **Step 2: Run them and see them fail**

Run: `uv run pytest tests/scripts/test_kdp_print.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'kdp_print'`.

- [ ] **Step 3: Write the module**

```python
"""KDP's paperback numbers: margins, spine, cover size and barcode area.

Every value is copied from KDP's help pages, named beside it, so a change
on KDP's side is a change to one constant here. All lengths are inches.
"""

from __future__ import annotations

from typing import Literal

Paper = Literal["white", "cream"]

# https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6
# ("Set Trim Size, Bleed, and Margins"): 5 x 8 in, black ink, cream paper.
MIN_PAGES = 24
MAX_PAGES = 828
# Inside (gutter) margin minimum by the highest page count it covers.
_GUTTER_BANDS = ((150, 0.375), (300, 0.5), (500, 0.625), (700, 0.75), (828, 0.875))
OUTSIDE_MARGIN_MIN_IN = 0.25

# https://kdp.amazon.com/en_US/help/topic/G201953020 ("Create a Paperback Cover").
_THICKNESS_IN = {"white": 0.002252, "cream": 0.0025}
BLEED_IN = 0.125
SPINE_TEXT_MIN_PAGES = 79
SPINE_TEXT_MARGIN_IN = 0.0625
COVER_SAFE_IN = 0.125

# https://kdp.amazon.com/en_US/help/topic/G201857950 ("Paperback Submission
# Guidelines"): KDP prints the barcode for its own ISBN in this area.
BARCODE_IN = (2.0, 1.2)
BARCODE_MARGIN_IN = 0.25


def _check_pages(pages: int) -> None:
    if not MIN_PAGES <= pages <= MAX_PAGES:
        raise ValueError(
            f"{pages} pages is outside KDP's paperback range, "
            f"{MIN_PAGES} to {MAX_PAGES}"
        )


def gutter_minimum(pages: int) -> float:
    """KDP's minimum inside margin for a book of ``pages`` pages.

    Raises:
        ValueError: ``pages`` is outside KDP's range.
    """
    _check_pages(pages)
    return next(inches for top, inches in _GUTTER_BANDS if pages <= top)


def spine_width(pages: int, paper: Paper) -> float:
    """The spine width KDP's formula gives for ``pages`` pages on ``paper``.

    Raises:
        ValueError: ``pages`` is outside KDP's range, or ``paper`` is not
            one KDP lists for black ink.
    """
    _check_pages(pages)
    if paper not in _THICKNESS_IN:
        raise ValueError(f"unknown paper {paper!r}; KDP lists {sorted(_THICKNESS_IN)}")
    return pages * _THICKNESS_IN[paper]


def spine_text_allowed(pages: int) -> bool:
    """Whether KDP allows text on the spine of a ``pages``-page book."""
    return pages >= SPINE_TEXT_MIN_PAGES


def cover_dimensions(
    trim: tuple[float, float], pages: int, paper: Paper
) -> tuple[float, float]:
    """The full wraparound cover's width and height, bleed included."""
    trim_w, trim_h = trim
    width = BLEED_IN + trim_w + spine_width(pages, paper) + trim_w + BLEED_IN
    return width, BLEED_IN + trim_h + BLEED_IN
```

Add `"kdp_print"` to `known_first_party` in `pyproject.toml`.

- [ ] **Step 4: Run the tests and the deptry gate**

Run: `uv run pytest tests/scripts/test_kdp_print.py tests/test_deptry_gate.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/kdp_print.py tests/scripts/test_kdp_print.py
git commit -F - -- scripts/kdp_print.py tests/scripts/test_kdp_print.py pyproject.toml <<'EOF'
Hold KDP's paperback margins, spine and cover size as pure functions

The print interior and the cover both size themselves from these, so
each number is copied once from KDP's help pages and named beside them.

Refs #195
EOF
```

---

### Task 2: The details still to decide, in one committed file

**Files:**
- Create: `docs/book/publication.toml`
- Create: `scripts/book_publication.py`
- Create: `tests/scripts/test_book_publication.py`
- Modify: `pyproject.toml` (`known_first_party` gains `"book_publication"`)

**Interfaces:**
- Produces: `PublicationDetails` (frozen dataclass: `copyright_holder: str | None`, `copyright_year: str | None`, `isbn: str | None`, `cover_art: str | None` (a path relative to the repository root), `back_cover_text: str | None`), `PLACEHOLDERS: dict[str, str]` (field name to the bracketed text printed in its place), `load_details(path: Path) -> PublicationDetails`, `unresolved(details) -> list[str]` (field names still unset, in field order), `require_resolved(details) -> None` (raises `SystemExit` naming every unset field), `typst_inputs(details) -> dict[str, str]` (every field, its value or its placeholder, plus `isbn-set` as `"true"`/`"false"`), `valid_isbn13(value: str) -> bool`.

`docs/book/publication.toml` is the one place the maintainer folds a decision in. It is committed with every field present and commented out, so the file names what is still open:

```toml
# The paperback's details that are not decided yet. Uncomment a line and fill
# it in when it is; the print build prints a bracketed placeholder in place of
# every field left out, and `render_handbook_book.py --final` refuses to build
# while any is. Which issue settles each one is noted beside it.

# Who holds the copyright: the owning organisation or the author (#188).
# copyright_holder = ""

# The year on the copyright line, normally the year of first publication.
# copyright_year = ""

# KDP's free ISBN, issued when the paperback title is created on KDP (#194).
# Hyphens are allowed; the check digit is verified.
# isbn = ""

# The front cover's art, a path from the repository root (#191). Without it
# the front cover is typographic.
# cover_art = ""

# The back cover's text (#191).
# back_cover_text = ""
```

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path

import pytest

import book_publication as bp

FIELDS = ("copyright_holder", "copyright_year", "isbn", "cover_art", "back_cover_text")


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "publication.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_an_empty_file_leaves_every_detail_unresolved(tmp_path):
    details = bp.load_details(_write(tmp_path, ""))
    assert bp.unresolved(details) == list(FIELDS)


def test_the_committed_file_parses_and_names_every_field():
    path = Path(__file__).resolve().parents[2] / "docs" / "book" / "publication.toml"
    bp.load_details(path)
    text = path.read_text()
    for field in FIELDS:
        assert f"# {field} = " in text or f"{field} = " in text, field


def test_a_set_detail_is_resolved(tmp_path):
    details = bp.load_details(_write(tmp_path, 'copyright_holder = "A B"\n'))
    assert details.copyright_holder == "A B"
    assert "copyright_holder" not in bp.unresolved(details)


def test_an_unknown_key_is_refused(tmp_path):
    with pytest.raises(SystemExit, match="copyright_holdr"):
        bp.load_details(_write(tmp_path, 'copyright_holdr = "x"\n'))


def test_an_empty_string_counts_as_unset(tmp_path):
    details = bp.load_details(_write(tmp_path, 'isbn = ""\n'))
    assert "isbn" in bp.unresolved(details)


@pytest.mark.parametrize("isbn", ["978-0-306-40615-7", "9780306406157"])
def test_a_valid_isbn13_loads(tmp_path, isbn):
    assert bp.load_details(_write(tmp_path, f'isbn = "{isbn}"\n')).isbn == isbn


@pytest.mark.parametrize("isbn", ["978-0-306-40615-8", "97803064061", "978030640615X", "978 0306406157"])
def test_an_invalid_isbn_is_refused_at_load(tmp_path, isbn):
    with pytest.raises(SystemExit, match="ISBN"):
        bp.load_details(_write(tmp_path, f'isbn = "{isbn}"\n'))


def test_require_resolved_names_every_unset_field_at_once(tmp_path):
    details = bp.load_details(_write(tmp_path, 'isbn = "9780306406157"\n'))
    with pytest.raises(SystemExit) as exc:
        bp.require_resolved(details)
    message = str(exc.value)
    for field in FIELDS:
        assert (field in message) == (field != "isbn"), field


def test_typst_inputs_print_a_placeholder_for_each_unset_field(tmp_path):
    details = bp.load_details(_write(tmp_path, 'copyright_holder = "A*B #1"\n'))
    inputs = bp.typst_inputs(details)
    assert inputs["copyright-holder"] == "A*B #1"
    assert inputs["isbn"] == bp.PLACEHOLDERS["isbn"]
    assert inputs["isbn-set"] == "false"
    assert all(p.startswith("[") and p.endswith("]") for p in bp.PLACEHOLDERS.values())
```

- [ ] **Step 2: Run them and see them fail**

Run: `uv run pytest tests/scripts/test_book_publication.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'book_publication'`.

- [ ] **Step 3: Write the module and the TOML file**

`scripts/book_publication.py`:

```python
"""The paperback's undecided details, read from `docs/book/publication.toml`.

A detail left out of the file, or set to an empty string, is unresolved: the
print build prints its bracketed placeholder (`PLACEHOLDERS`) in its place,
and `require_resolved` refuses a release build while any remains.
"""

from __future__ import annotations

import dataclasses
import re
import tomllib
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class PublicationDetails:
    copyright_holder: str | None = None
    copyright_year: str | None = None
    isbn: str | None = None
    cover_art: str | None = None
    back_cover_text: str | None = None


PLACEHOLDERS = {
    "copyright_holder": "[Copyright holder]",
    "copyright_year": "[Year]",
    "isbn": "[ISBN]",
    "cover_art": "[Cover art]",
    "back_cover_text": "[Back cover text]",
}
_FIELDS = tuple(f.name for f in dataclasses.fields(PublicationDetails))
_ISBN_CHARS_RE = re.compile(r"^[0-9]+(?:-[0-9]+)*$")


def valid_isbn13(value: str) -> bool:
    """Whether ``value`` is an ISBN-13: 13 digits, optional hyphens, a valid check digit."""
    if not _ISBN_CHARS_RE.match(value):
        return False
    digits = [int(c) for c in value if c.isdigit()]
    if len(digits) != 13:
        return False
    total = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:12]))
    return (10 - total % 10) % 10 == digits[12]


def load_details(path: Path) -> PublicationDetails:
    """Read ``path``; an empty string counts as unset.

    Raises:
        SystemExit: The file names a key that is not a detail, a value is not
            a string, or the ISBN is not a valid ISBN-13.
    """
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    unknown = sorted(set(data) - set(_FIELDS))
    if unknown:
        raise SystemExit(f"{path}: unknown key(s) {unknown}; the details are {list(_FIELDS)}")
    values: dict[str, str | None] = {}
    for key, value in data.items():
        if not isinstance(value, str):
            raise SystemExit(f"{path}: {key} must be a string, not {type(value).__name__}")
        values[key] = value or None
    isbn = values.get("isbn")
    if isbn is not None and not valid_isbn13(isbn):
        raise SystemExit(f"{path}: isbn {isbn!r} is not a valid ISBN-13")
    return PublicationDetails(**values)


def unresolved(details: PublicationDetails) -> list[str]:
    """The details still unset, in field order."""
    return [name for name in _FIELDS if getattr(details, name) is None]


def require_resolved(details: PublicationDetails) -> None:
    """Raise unless every detail is set, naming every unset one at once.

    Raises:
        SystemExit: Any detail is unset.
    """
    missing = unresolved(details)
    if missing:
        raise SystemExit(
            "a release build needs every publication detail; unset in "
            f"docs/book/publication.toml: {', '.join(missing)}"
        )


def typst_inputs(details: PublicationDetails) -> dict[str, str]:
    """Each detail as a ``typst compile --input`` value, or its placeholder.

    Keys are the field names with ``-`` for ``_``, and ``isbn-set`` says
    whether the ISBN is real, since the copyright page and the cover leave
    KDP's barcode area clear only for a real one.
    """
    inputs = {
        name.replace("_", "-"): getattr(details, name) or PLACEHOLDERS[name]
        for name in _FIELDS
    }
    inputs["isbn-set"] = "true" if details.isbn else "false"
    return inputs
```

Write `docs/book/publication.toml` exactly as shown above the steps. Add `"book_publication"` to `known_first_party`.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/scripts/test_book_publication.py tests/test_deptry_gate.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/book/publication.toml scripts/book_publication.py tests/scripts/test_book_publication.py
git commit -F - -- docs/book/publication.toml scripts/book_publication.py tests/scripts/test_book_publication.py pyproject.toml <<'EOF'
Keep the paperback's undecided details in one file, as placeholders

The copyright holder, the year, KDP's ISBN, the cover art and the back
cover's text are not decided yet. Each prints as a bracketed
placeholder until docs/book/publication.toml gives it, and a release
build can refuse while any is unset.

Refs #195
EOF
```

---

### Task 3: One book document for both formats

**Files:**
- Modify: `scripts/book_figures.py` (add `print_width_pt`, next to `epub_width_em`)
- Modify: `scripts/render_handbook_book.py` (`figure_markup` gains a size argument, `write_figures` gains a target, a new `book_document`, `build_epub` calls it)
- Modify: `tests/scripts/test_render_handbook_book.py`, `tests/scripts/test_book_figures.py`

**Interfaces:**
- Consumes: `assemble`, `render_parts`, `require_h1_first`, `book_linkmap`, `first_heading_ids`, `load_figure`, `embed_fonts`, `book_html`, `curl_quotes`, `glue_part_numbers` (all existing).
- Produces:
  - `print_width_pt(svg: str) -> float`: viewBox width times `PT_PER_UNIT`.
  - `Target = Literal["epub", "print"]`.
  - `figure_markup(stem, block, size: str) -> str`: `size` is the CSS-free sizing the target needs. For `epub` the build passes `style="width: <em>em; max-width: 100%"` exactly as today; for `print` it passes `width="<pt>pt"`, which pandoc's Typst writer carries as `image(..., width: <pt>pt)` (confirmed against pandoc 3.8.2).
  - `write_figures(assembled, figures_dir, media, target: Target = "epub")`: for `print` the copy is the committed figure as is, without `embed_fonts` (Typst does not read fonts embedded in an SVG, and the committed figures' lettering is outlined).
  - `book_document(docs_dir, parts, figures_dir, media, target: Target) -> str`: renders, checks, assembles, writes figures and returns `glue_part_numbers(curl_quotes(book_html(assembled, figures, target)))`.
  - `book_html(assembled, figures, target: Target = "epub")`: for `print`, the checklist wrapper `<div class="checklist">` also carries `id="checklist-<n>"` numbered from 1 in document order, because pandoc's Typst writer drops a div's class but keeps its id as a label, which is how the template finds a checklist (Task 4). The EPUB's output is unchanged.

- [ ] **Step 1: Write the failing tests**

```python
# tests/scripts/test_book_figures.py
def test_print_width_pt_places_the_widest_figure_at_the_text_width():
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {bf.FULL_WIDTH_UNITS} 100"/>'
    assert bf.print_width_pt(svg) == pytest.approx(bf.TEXT_BLOCK_PT[0])
```

```python
# tests/scripts/test_render_handbook_book.py
def test_a_print_figure_is_sized_in_points_for_pandocs_typst_writer():
    block = rh.DiagramBlock(index=0, kind="d2", title="T", source="a -> b")
    html = rb.figure_markup("p", block, 'width="200.00pt"')
    assert '<img src="media/p-0.svg" alt="T" width="200.00pt">' in html


def test_a_print_checklist_carries_a_numbered_id():
    html = '<ul><li class="task">a</li></ul><ul><li class="task done">b</li></ul>'
    out = rb.restore_task_boxes(html, numbered=True)
    assert '<div class="checklist" id="checklist-1">' in out
    assert '<div class="checklist" id="checklist-2">' in out
    assert 'id="checklist' not in rb.restore_task_boxes(html)


@needs_pandoc
def test_the_epub_document_is_unchanged_by_the_shared_assembly(tmp_path):
    _skip_unless_the_build_can_draw_its_seeds()
    media_a, media_b = tmp_path / "a", tmp_path / "b"
    media_a.mkdir()
    media_b.mkdir()
    rendered = rh.render_parts(DOCS, rh.PARTS)
    linkmap = rb.book_linkmap(rh.PARTS, rb.first_heading_ids(rendered, rh.PARTS))
    assembled = rh.assemble(DOCS, rh.PARTS, linkmap, rendered=rendered)
    figures, _ = rb.write_figures(assembled, DOCS / "figures", media_a)
    before = rb.glue_part_numbers(rb.curl_quotes(rb.book_html(assembled, figures)))
    assert rb.book_document(DOCS, rh.PARTS, DOCS / "figures", media_b, "epub") == before
```

(The last test needs no pandoc in itself; mark it with the same `pytest.importorskip("markdown")` the `built_epub` fixture uses instead of `needs_pandoc` if markdown is the only requirement. Check `rh.DiagramBlock`'s real field names before writing the first test and use them.)

- [ ] **Step 2: Run them and see them fail**

Run: `uv run pytest tests/scripts/test_book_figures.py tests/scripts/test_render_handbook_book.py -q -k "print or checklist or unchanged"`
Expected: FAIL on the missing names and the changed `figure_markup` signature.

- [ ] **Step 3: Implement**

- `print_width_pt` in `book_figures.py`, docstring parallel to `epub_width_em`'s.
- `figure_markup(stem, block, size)`: the `<img>` becomes `f'<img src="media/{stem}-{block.index}.svg" alt="{alt}" {size}>'`. `write_figures` builds `size` per target: `f'style="width: {epub_width_em(svg):.2f}em; max-width: 100%"'` for `epub`, `f'width="{print_width_pt(svg):.2f}pt"'` for `print`. Update `figure_markup`'s docstring and its existing tests to the new argument.
- `restore_task_boxes(html, numbered=False)`: when `numbered`, the wrapper is `f'<div class="checklist" id="checklist-{n}">'` with `n` counting from 1. `book_html(..., target="epub")` passes `numbered=(target == "print")`.
- `book_document`: the first half of today's `build_epub` up to and including the HTML passes. `build_epub` calls it with `target="epub"`.

- [ ] **Step 4: Run the whole suite and rebuild the EPUB**

Run: `uv run pytest tests/ -q` then `uv run python scripts/render_handbook_book.py --format epub` and `epubcheck build/handbook.epub`.
Expected: all pass; epubcheck reports 0 errors and 0 warnings.

- [ ] **Step 5: Commit**

```bash
git commit -F - -- scripts/book_figures.py scripts/render_handbook_book.py tests/scripts/test_book_figures.py tests/scripts/test_render_handbook_book.py <<'EOF'
Build one book document for the EPUB and the paperback

The print build shares the EPUB's assembly instead of running its own.
A print document differs in two places: each figure is sized in points
at the one scale, and each checklist carries an id, the one mark
pandoc's Typst writer keeps on a div. The EPUB's document is unchanged.

Refs #195
EOF
```

---

### Task 4: The print interior, `--format pdf`

**Files:**
- Create: `scripts/book_interior.typ`
- Modify: `scripts/render_handbook_book.py` (`typst_body_command`, `typst_compile_command`, `interior_main`, `typst_page_count`, `build_pdf`, CLI)
- Modify: `tests/scripts/test_render_handbook_book.py`

**Interfaces:**
- Consumes: `book_document(..., "print")`, `kdp_print.gutter_minimum`, `book_publication.load_details`, `typst_inputs`, `require_resolved`.
- Produces:
  - `INTERIOR_MARGINS_IN = {"inside": 0.75, "outside": 0.65, "top": 0.875, "bottom": 1.125}`: trim minus margins is exactly the 3.6 x 6 in text block (`TEXT_BLOCK_PT`), and a test holds that.
  - `TRIM_IN = (5.0, 8.0)`, `PAPER: Paper = "cream"`.
  - `typst_body_command(html_path, out) -> list[str]`: `pandoc -f html -t typst -o <out> <html>`. No `-s`, so pandoc writes only the body and none of its own template.
  - `interior_main(body_name: str) -> str`: the main file, `#import "book_interior.typ": interior` then `#show: interior` then `#include "<body_name>"`. The template is copied into the work directory beside it.
  - `typst_compile_command(main, out, inputs: dict[str, str]) -> list[str]`: `typst compile --font-path <FONTS_ROOT> --ignore-system-fonts`, one `--input key=value` per input, then `<main> <out>`. `--ignore-system-fonts` makes a missing face fail loudly instead of resolving from the machine that built it.
  - `typst_page_count(main, inputs) -> int`: `typst query <main> "<page-count>" --field value --one`, through a `run_tool` sibling that returns stdout. The template places `#metadata(...) <page-count>` with the final page count.
  - `build_pdf(docs_dir, out, details_path, final: bool, figures_dir=None) -> tuple[Path, int]`: writes the interior, returns it and its page count, and raises `SystemExit` if `INTERIOR_MARGINS_IN["inside"] < gutter_minimum(pages)` or if `final` and any detail is unset.
  - CLI: `--format` gains `pdf` and `cover`; new `--final` and `--details` (default `docs/book/publication.toml`). Default outputs `build/handbook-interior.pdf` and `build/handbook-cover.pdf`.

The template, `scripts/book_interior.typ`, was tried on 2026-10-05 against the current handbook (pandoc 3.8.2, Typst 0.15.1) and came to 107 pages before front matter, with parts opening on odd pages and in-book links printing their page. Start from this and keep each rule's comment:

```typst
// The paperback interior: 5 x 8 in, a 3.6 x 6 in text block, black on cream.
// The build passes the publication details as `--input` strings, read with
// `sys.inputs` and printed as text, never evaluated.
#let detail(key) = sys.inputs.at(key)

#let front-matter() = {
  set page(numbering: none, footer: none)
  // Half-title, recto.
  align(center + horizon, text(font: "Source Sans 3", weight: "bold", 14pt)[AI Agent Development Handbook])
  pagebreak()
  // Its verso stays blank.
  pagebreak()
  // Title page, recto.
  align(center + horizon, {
    text(font: "Source Sans 3", weight: "bold", 20pt)[AI Agent Development Handbook]
    v(1.5em)
    text(12pt)[Janos Tolgyesi]
  })
  pagebreak()
  // Copyright page, verso. #191 owns this wording; these lines carry what
  // #188 decided and a placeholder for what it has not.
  set text(8pt)
  set par(justify: false)
  align(bottom)[
    Copyright © #detail("copyright-year") #detail("copyright-holder").

    This work is licensed under the Creative Commons Attribution 4.0
    International License (CC BY 4.0). To view a copy of this licence,
    visit #raw("https://creativecommons.org/licenses/by/4.0/").

    ISBN #detail("isbn")

    Independently published.
  ]
  pagebreak(to: "odd")
  outline(title: "Contents", depth: 1)
}

#let interior(body) = {
  set document(title: "AI Agent Development Handbook", author: "Janos Tolgyesi")
  set page(
    width: 5in, height: 8in,
    margin: (inside: 0.75in, outside: 0.65in, top: 0.875in, bottom: 1.125in),
  )
  // Source Sans 3 stands in only for the three marks Source Serif 4 lacks
  // (● ○ ↔), so no face outside fonts/ is ever used.
  set text(font: ("Source Serif 4", "Source Sans 3"), size: 9.5pt, lang: "en", hyphenate: true)
  set par(justify: true, leading: 0.55em)
  show heading: set text(font: "Source Sans 3", weight: "bold", hyphenate: false)
  show heading: set par(justify: false)
  // A part opens on a recto page.
  show heading.where(level: 1): it => {
    pagebreak(to: "odd", weak: true)
    v(1in)
    text(16pt, it)
    v(0.3in)
  }
  show raw: set text(font: "Source Code Pro", size: 8pt)
  // Long inline code may break after a path or identifier separator.
  show raw.where(block: false): it => {
    show regex("[/_.=-]"): c => c + sym.zws
    it
  }
  set table(stroke: none, inset: (x: 3pt, y: 2.5pt))
  show table: set text(8pt)
  // Table cells are set ragged-right and never hyphenated (spec, narrow trim).
  show table.cell: set par(justify: false)
  show table.cell: set text(hyphenate: false)
  show figure: set block(breakable: false)
  show figure.caption: set text(8pt, style: "italic")
  // An in-book link prints its page; an external one prints its URL in a footnote.
  show link: it => {
    if type(it.dest) == label {
      it.body
      [ (p.~#context counter(page).at(it.dest).first())]
    } else if type(it.dest) == str {
      it.body
      footnote(raw(it.dest))
    } else { it }
  }
  // A checklist (`checklist-<n>`) draws its box in place of the bullet.
  // Implement as a show rule on the labelled block that sets
  // `list(marker: none)`, and give the ☐/☒ glyph a fixed-width box.
  front-matter()
  set page(
    numbering: "1",
    footer: context {
      set align(if calc.even(here().page()) { left } else { right })
      set text(8pt)
      counter(page).display()
    },
  )
  counter(page).update(1)
  body
  context [#metadata(counter(page).final().first()) <page-count>]
}

// pandoc's Typst writer emits `#horizontalrule` for an <hr>.
#let horizontalrule = line(length: 100%, stroke: 0.5pt)
```

Notes for the implementer, each found on the 2026-10-05 trial:

- The checklist rule is the one part not tried. A show rule per label cannot be written generically, so either emit the rule from Python into the main file (one `#show <checklist-n>: set list(marker: none)` per checklist, counted from the document), or match by label in a single rule if Typst 0.15 allows it. Choose one, and test it from the compiled text: no bullet precedes a ☐ or ☒.
- `#horizontalrule` must be defined where the body is included. If the import does not make it visible to the included file, define it in `interior_main` instead.
- `typst query` counts pages from the final layout; a count read before the body has run is wrong. Test that the queried count equals `pdfinfo`'s `Pages:` where `pdfinfo` is installed.

- [ ] **Step 1: Write the failing tests**

Pure (no tools):

```python
def test_the_interior_margins_leave_exactly_the_figures_text_block():
    m = rb.INTERIOR_MARGINS_IN
    width = rb.TRIM_IN[0] - m["inside"] - m["outside"]
    height = rb.TRIM_IN[1] - m["top"] - m["bottom"]
    assert (width * 72, height * 72) == pytest.approx(bf.TEXT_BLOCK_PT)


def test_the_inside_margin_meets_kdps_minimum_for_any_plausible_length():
    assert rb.INTERIOR_MARGINS_IN["inside"] >= kp.gutter_minimum(700)
    assert rb.INTERIOR_MARGINS_IN["outside"] >= kp.OUTSIDE_MARGIN_MIN_IN


def test_the_typst_compile_command_uses_only_the_committed_fonts(tmp_path):
    cmd = rb.typst_compile_command(tmp_path / "m.typ", tmp_path / "o.pdf", {"isbn": "[ISBN]"})
    assert cmd[:2] == ["typst", "compile"]
    assert "--ignore-system-fonts" in cmd
    assert cmd[cmd.index("--font-path") + 1] == str(rb.FONTS_ROOT)
    assert cmd[cmd.index("--input") + 1] == "isbn=[ISBN]"


def test_the_pandoc_typst_command_writes_the_body_only(tmp_path):
    cmd = rb.typst_body_command(tmp_path / "b.html", tmp_path / "b.typ")
    assert "-s" not in cmd and "--standalone" not in cmd
    assert cmd[cmd.index("-t") + 1] == "typst"
```

Built (module-scoped fixture `built_pdf` that skips without pandoc or typst, as `built_epub` does, and builds with a details file whose holder is `A*B #1` and everything else unset; it also keeps the work directory's `body.typ` for the label test):

- every heading id from `rh.heading_ids(DOCS)` minus the part anchors appears in `body.typ` as `<id>`;
- `body.typ` carries exactly one `image(` per diagram fence;
- the PDF's text (`pdftotext`, skip if absent) contains `A*B #1`, `[ISBN]`, `[Year]`, and `(p.` after `Part 1`;
- every font `pdffonts` lists is embedded and is one of Source Serif 4, Source Sans 3 or Source Code Pro (skip if `pdffonts` is absent);
- `typst_page_count` equals `pdfinfo`'s page count;
- each part's heading text starts an odd page (via `pdftotext -f n -l n`);
- no line of the PDF's text starts with `•` followed by `☐` or `☒`;
- `main(["--format", "pdf", "--final", "--details", <that file>])` exits non-zero naming `isbn`;
- with `typst` hidden from `PATH` (monkeypatch `PATH` to a temp dir holding only `pandoc`), `build_pdf` raises `SystemExit` naming `typst` and `brew install typst`.

- [ ] **Step 2: Run them and see them fail**

Run: `uv run pytest tests/scripts/test_render_handbook_book.py -q -k "interior or typst or pdf"`
Expected: FAIL on the missing names.

- [ ] **Step 3: Implement** the template, the four functions, `build_pdf` and the CLI, keeping `build_epub`'s shape: a temporary work directory, `media/` inside it, the template copied in, every tool call through `run_tool`. `_TYPST_TIMEOUT_S = 300` and `_TYPST_HINT = "Install it with \`brew install typst\`, or see https://typst.app/open-source/."` beside the pandoc ones. `--final` is checked before any tool runs.

- [ ] **Step 4: Run the suite and build the interior**

Run: `uv run pytest tests/ -q` then `uv run python scripts/render_handbook_book.py --format pdf`.
Expected: all pass; the build prints the path and page count. Open the PDF as a two-page spread with the first page alone and look at a part opening, a table, a figure, a checklist and a page with a footnoted URL.

- [ ] **Step 5: Commit**

```bash
git add scripts/book_interior.typ
git commit -F - -- scripts/book_interior.typ scripts/render_handbook_book.py tests/scripts/test_render_handbook_book.py <<'EOF'
Build the paperback interior with Typst

--format pdf writes a 5 x 8 in interior: the shared book document
through pandoc's Typst writer into a committed template, set in the
committed faces only, with parts on recto pages, a contents list with
page numbers, in-book links printed as page references and external
links as footnoted URLs. The undecided details print as placeholders,
and --final refuses to build while any is unset.

Refs #195
EOF
```

---

### Task 5: The wraparound cover, `--format cover`

**Files:**
- Create: `scripts/book_cover.typ`
- Modify: `scripts/render_handbook_book.py` (`cover_inputs`, `build_cover`, CLI)
- Modify: `tests/scripts/test_render_handbook_book.py`

**Interfaces:**
- Consumes: `build_pdf` (for the page count), `kdp_print.cover_dimensions`, `spine_width`, `spine_text_allowed` and the cover constants, `book_publication.typst_inputs`.
- Produces:
  - `cover_inputs(pages: int, details) -> dict[str, str]`: the details' inputs plus `width`, `height`, `spine` (inches, as decimal strings), `bleed`, `trim-width`, `trim-height`, `safe`, `spine-margin`, `barcode-width`, `barcode-height`, `barcode-margin`, `spine-text` (`"true"`/`"false"`), and `cover-art` (the absolute path when set, else empty).
  - `build_cover(docs_dir, out, details_path, final: bool, figures_dir=None) -> tuple[Path, int]`: builds the interior in a temporary directory to read its page count, so a cover is never sized from a stale interior, then compiles the cover.

`scripts/book_cover.typ` reads every length from `sys.inputs` and draws, on one page of `width` x `height` with no margin:

- **Back** (left panel): the back-cover text in a block inset `safe` from the trim, and, when `isbn-set` is `true`, a white rectangle `barcode-width` x `barcode-height` placed `barcode-margin` from the spine fold and from the bottom trim, left empty for KDP's barcode. With no ISBN yet, the same rectangle is drawn as a thin outline labelled `[Barcode area]`, so the proof shows where it will go.
- **Spine** (middle, `spine` wide): when `spine-text` is `true`, the title and author rotated 90 degrees clockwise, kept `spine-margin` from each fold. Otherwise nothing.
- **Front** (right panel): `cover-art` filling the panel to the bleed when given; otherwise a typographic cover, the title in Source Sans 3 bold and the author below it, inside the safe area.
- The background is white. Cover colour and art belong to #191.

- [ ] **Step 1: Write the failing tests**

Pure:

```python
def test_cover_inputs_size_the_page_from_the_page_count():
    inputs = rb.cover_inputs(120, bp.PublicationDetails())
    assert float(inputs["width"]) == pytest.approx(0.125 + 5 + 0.3 + 5 + 0.125)
    assert float(inputs["height"]) == pytest.approx(8.25)
    assert float(inputs["spine"]) == pytest.approx(0.3)
    assert inputs["spine-text"] == "true"
    assert inputs["isbn-set"] == "false"


def test_a_thin_book_has_no_spine_text():
    assert rb.cover_inputs(60, bp.PublicationDetails())["spine-text"] == "false"
```

Built (skips without pandoc or typst): `pdfinfo`'s `Page size` equals `cover_dimensions(TRIM_IN, pages, PAPER)` in points to within 0.5 pt; the PDF has one page; its text contains the title and `[Back cover text]`; every font is embedded and from `fonts/`.

- [ ] **Step 2: Run them and see them fail.**

- [ ] **Step 3: Implement** the template and the two functions.

- [ ] **Step 4: Run the suite and build the cover**

Run: `uv run pytest tests/ -q` then `uv run python scripts/render_handbook_book.py --format cover`. Open it and check the spine sits in the middle, the barcode outline at the back's bottom right, and nothing within 0.125 in of the trim.

- [ ] **Step 5: Commit**

```bash
git add scripts/book_cover.typ
git commit -F - -- scripts/book_cover.typ scripts/render_handbook_book.py tests/scripts/test_render_handbook_book.py <<'EOF'
Build the paperback's wraparound cover, sized from the interior

--format cover counts the interior's pages, sizes back, spine and front
with KDP's formula for cream paper and its bleed, prints the spine text
only at 79 pages or more, and keeps KDP's barcode area clear. The front
is typographic until #191 supplies the art.

Refs #195
EOF
```

---

### Task 6: Documentation and the record

**Files:**
- Modify: `CLAUDE.md` (Commands: the two new commands; layout: `docs/book/publication.toml`)
- Modify: `docs/superpowers/specs/2026-09-25-handbook-book-pipeline-design.md` (an amendment line in its Status and a Decisions bullet per decision this plan took that the spec left open)
- Modify: `scripts/render_handbook_book.py` (module docstring and Usage)

- [ ] **Step 1:** CLAUDE.md Commands gains, after the EPUB line:

```
uv run python scripts/render_handbook_book.py --format pdf       # needs pandoc and typst; writes build/handbook-interior.pdf, with placeholders for what docs/book/publication.toml leaves unset
uv run python scripts/render_handbook_book.py --format cover     # builds the interior to count its pages; writes build/handbook-cover.pdf
```

and the layout list gains a `docs/book/publication.toml` bullet: the paperback's undecided details, each printed as a placeholder until set, `--final` refusing a build while any is unset.

- [ ] **Step 2:** The spec's Decisions gain, one bullet each: external links print their URL in a footnote rather than inline, because a URL inline in a 3.6 in measure breaks lines badly; the publication details live in `docs/book/publication.toml` and reach Typst as `--input` strings; the cover reads the interior's page count by building it, never from a file on disk; the margins are inside 0.75, outside 0.65, top 0.875, bottom 1.125 in, which is the figures' text block and above KDP's gutter minimum up to 700 pages; figures with translucent shading are placed as they are, and KDP's previewer decides whether they need flattening.

- [ ] **Step 3:** Run the full gate: `uv run ruff check . && uv run ruff format --check .`, `uv run pytest tests/ -q`, `uv run python scripts/render_handbook_traceability.py --check`, `uv run python scripts/check_handbook_citations.py`, `uv run deptry .`, and all three builds.

- [ ] **Step 4: Commit**

```bash
git commit -F - -- CLAUDE.md docs/superpowers/specs/2026-09-25-handbook-book-pipeline-design.md scripts/render_handbook_book.py <<'EOF'
Document the paperback build and record its decisions

Refs #195
EOF
```

## Left for later, by design

- **KDP's previewer** on both files, and the proof copy: manual, after this lands (#195, #194).
- **The release workflow** building both files from a tag with pinned pandoc and Typst: #192, which does not exist yet. Until it does, CI skips every test that needs pandoc or Typst, as it already does for the EPUB.
- **Front-matter wording and cover design:** #191. The template's copyright page and typographic cover are the slots it fills.
- **Translucent shading in four figures** (opacity 0.4 and rgba 0.14). KDP's guidelines ask for flattened transparency. If the previewer flags it, the print copy of those figures gets its overlays composited to opaque grey in `write_figures`' print branch.
