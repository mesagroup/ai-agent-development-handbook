# Handbook book figures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The EPUB shows every handbook diagram as a captioned figure drawn from a committed, hand-correctable SVG, placed at one print scale, legible on cream paper, e-ink and a reading system's dark mode.

**Architecture:** A new `scripts/book_figures.py` holds the pure figure logic: the fence hash, the seed clean-up, the scale, transparency and contrast checks, the EPUB's light panel and font embedding. The page renderer gains a `print` d2 prelude and a vertical funnel layout. `render_handbook_book.py` gains `--seed-figures`, which writes a starting SVG per fence into `docs/engineering/figures/`, and its EPUB build reads those committed files (falling back to a seed with a note), prepares an EPUB copy of each and hands them to pandoc as media.

**Tech Stack:** Python 3.12, d2 0.7.1 (ELK), pandoc 3.8.2, fontTools, epubcheck 5.4.0, pytest.

**Spec:** `docs/superpowers/specs/2026-09-25-handbook-book-pipeline-design.md`, section "2. Book figures (#190)", as amended on 2026-09-28.

## Global Constraints

- No em dash (U+2014) in `docs/engineering/`, `docs/superpowers/specs/`, `docs/superpowers/plans/`. Use ` - `.
- Markdown is never hard-wrapped; never reflow lines you did not change.
- Never commit environment-specific values: absolute personal paths, profile names, tokens, hostnames, emails.
- Every new module in `scripts/` joins `[tool.deptry] known_first_party` in `pyproject.toml`; every third-party import is declared in `[project] dependencies`.
- New code ships with unit tests over its pure logic. Tests that need `d2` or `pandoc` skip with `pytest.mark.skipif(shutil.which("<tool>") is None, reason="needs the <tool> CLI; CI gains it with #192")`.
- No bare `except Exception: pass`.
- Commit with explicit pathspecs (`git commit -m ... -- <paths>`), no AI attribution trailer (a commit-msg hook refuses one), `Refs #190` in every message.
- Run `uv run ruff check . && uv run ruff format --check .` and `uv run pytest tests/ -q` before each commit.
- One scale: `PT_PER_UNIT = 2 / 3`; text block 3.6 x 6.0 in, so the viewBox bound is 388.8 x 648 units; every text size between 7 and 9 pt at that scale (10.5 to 13.5 units).
- Figure file: `docs/engineering/figures/<stem>-<index>.svg`, index = `DiagramBlock.index`. Root `<svg>` carries `data-source-sha256="<sha256 hex of the fence body>"`.
- Font family name written into figures: `Source Sans 3`. Font files: `fonts/source-sans-3/` (regular, bold, italic TTF plus `OFL.txt`), from Adobe's `adobe-fonts/source-sans` release `3.052R`.
- Paper reference colour for contrast: `PAPER_CREAM = "#f7f0dc"`. Text needs 4.5:1 against it, strokes 3:1.
- EPUB panel colour: `PALETTE["light"]["surface"]` (`#f7f6f2`).
- The page's `PALETTE` and `D2_PRELUDES` keep exactly their `light` and `dark` keys; the print palette lives beside them.

## Review Focus

1. **A figure saved by Inkscape** (namespaced attributes, `style="font-size:12px;font-weight:bold"`, extra `<defs>`/`<metadata>`) is read by every check and by `embed_fonts` as a d2 seed is. Tests in Task 2 and Task 4 use an Inkscape-shaped fixture.
2. **A fence edited after its figure was drawn** fails the tree test, naming the figure file and the fence. Test in Task 5.
3. **A fence with no committed figure** still builds: the EPUB uses its seed and the build prints a `NOTE` naming it. Test in Task 4.
4. **A reading system in dark mode** shows every figure on its light panel: every EPUB media SVG carries the panel as its first drawn element. Test in Task 4.
5. **A fence title carrying `&`, `<` or `"`** reaches the caption and the `alt` escaped. Test in Task 4.

---

### Task 1: The print prelude and the vertical funnel

**Files:**
- Modify: `scripts/render_handbook_artifact.py` (palette block near `PALETTE`, `_D2_ICON_STROKE`, `run_d2`, a new `funnel_svg_vertical` beside `funnel_svg`, the `_D2_TIMEOUT_S` comment)
- Test: `tests/scripts/test_render_handbook_artifact.py`

**Interfaces:**
- Produces: `PRINT_PALETTE: dict[str, str]`, `PRINT_WASH_OPACITY: float`, `D2_PRINT_PRELUDE: str`, `run_d2(source, salt, "print")`, `funnel_svg_vertical(stages: list[FunnelStage]) -> str`.

- [ ] **Step 1: Write the failing tests**

```python
def test_the_print_prelude_paints_no_surface():
    prelude = rh.D2_PRINT_PRELUDE
    assert "**.style.fill: transparent" in prelude
    assert rh.PALETTE["light"]["surface"] not in prelude
    assert rh.PRINT_PALETTE["line"] in prelude
    assert rh.PRINT_PALETTE["accent"] in prelude


def test_the_page_palettes_are_untouched_by_print():
    assert set(rh.PALETTE) == {"light", "dark"}
    assert set(rh.D2_PRELUDES) == {"light", "dark"}


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


@pytest.mark.skipif(shutil.which("d2") is None, reason="needs the d2 CLI; CI gains it with #192")
def test_a_print_render_carries_no_surface_fill():
    svg = rh.run_d2("a -> b", "t-print", "print")
    assert rh.PALETTE["light"]["surface"] not in svg
    assert rh.PRINT_PALETTE["line"] in svg
```

`parse_funnel` takes the label and count per line as the fence does; check its signature in the module and match the fixture to it if it differs.

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/scripts/test_render_handbook_artifact.py -q -k "print or vertical_funnel or untouched"`
Expected: FAIL with `AttributeError: ... has no attribute 'D2_PRINT_PRELUDE'`.

- [ ] **Step 3: Implement**

Beside `PALETTE`, after `_D2_ICON_STROKE`:

```python
# The paperback's palette, and the EPUB's through the same figures. Not a
# third entry in `PALETTE`: the page reads that dict as its two themes, and a
# print figure paints no surface at all, so it has no `surface` slot to fill.
# `line` is darker than the page's, because the page's hairline measures 1.6:1
# against cream paper and a box border has to hold 3:1 once colour is dropped.
# The wash is the accent at low opacity rather than a pale opaque colour, so
# paper of any shade shows through it.
PRINT_PALETTE: dict[str, str] = {
    "ink": "#1c2024", "ink_soft": "#4b5057", "accent": "#9a6a1c",
    "accent_ink": "#6f4c12", "line": "#8a867a",
}  # fmt: skip
PRINT_WASH_OPACITY = 0.15
```

Add `"print": PRINT_PALETTE["accent_ink"]` to `_D2_ICON_STROKE`.

After `D2_PRELUDES`:

```python
# Everything transparent, so cream paper, e-ink and the EPUB's own light panel
# all show through the same drawing.
D2_PRINT_PRELUDE = (
    "style.fill: transparent\n"
    + _D2_FONT_SIZE
    + "**.style.fill: transparent\n"
    f'**.style.stroke: "{PRINT_PALETTE["line"]}"\n'
    f'**.style.font-color: "{PRINT_PALETTE["ink"]}"\n'
    "**.style.shadow: false\n"
    f'(** -> **)[*].style.stroke: "{PRINT_PALETTE["accent"]}"\n'
    f'(** -> **)[*].style.font-color: "{PRINT_PALETTE["ink_soft"]}"\n'
)
```

In `run_d2`, replace `D2_PRELUDES[variant]` with `(D2_PRINT_PRELUDE if variant == "print" else D2_PRELUDES[variant])` and document `print` in the `variant` arg.

Beside `funnel_svg`:

```python
# The vertical funnel's geometry, in SVG user units. The book places every
# figure at one scale (2/3 pt per unit), so the width has to stay inside the
# 388.8-unit text block rather than being scaled into it.
_VFUNNEL_WIDTH = 340
_VFUNNEL_LABEL_RIGHT = 150
_VFUNNEL_BAND_MAX = 170
_VFUNNEL_BAND_MIN = 14
_VFUNNEL_ROW = 30
_VFUNNEL_GAP = 16
_VFUNNEL_PAD = 10
_VFUNNEL_LABEL_BUDGET = 24
# Below this a band cannot hold its count, which then sits to its right.
_VFUNNEL_COUNT_INSIDE_MIN = 44


def funnel_svg_vertical(stages: list[FunnelStage]) -> str:
    """Draw the funnel top to bottom for print: labels left, bands narrowing.

    The horizontal `funnel_svg` spreads the stages across 700 units, which
    prints its labels at about 4 pt in the book's text block. Stacking them
    keeps every label at the book's one scale. The scale of the band widths
    is logarithmic for the reason `funnel_svg` gives.

    Returns:
        An `<svg>` with a viewBox, in `PRINT_PALETTE`, painting no opaque
        surface.
    """
    p = PRINT_PALETTE
    counts = [s.count for s in stages]
    hi, lo = max(counts), min(counts)
    span = math.log(hi) - math.log(lo)

    def band_width(count: int) -> float:
        if span == 0:
            return _VFUNNEL_BAND_MAX
        t = (math.log(count) - math.log(lo)) / span
        return _VFUNNEL_BAND_MIN + t * (_VFUNNEL_BAND_MAX - _VFUNNEL_BAND_MIN)

    cx = _VFUNNEL_LABEL_RIGHT + 14 + _VFUNNEL_BAND_MAX / 2
    parts: list[str] = []
    for i, stage in enumerate(stages):
        y = _VFUNNEL_PAD + i * (_VFUNNEL_ROW + _VFUNNEL_GAP)
        w = band_width(stage.count)
        parts.append(
            f'<rect x="{cx - w / 2:.1f}" y="{y}" width="{w:.1f}"'
            f' height="{_VFUNNEL_ROW}" fill="none" stroke="{p["line"]}"'
            ' stroke-width="1.5"/>'
        )
        if i + 1 < len(stages):
            w2 = band_width(stages[i + 1].count)
            y2 = y + _VFUNNEL_ROW + _VFUNNEL_GAP
            parts.append(
                f'<path d="M {cx - w / 2:.1f} {y + _VFUNNEL_ROW} L {cx + w / 2:.1f}'
                f" {y + _VFUNNEL_ROW} L {cx + w2 / 2:.1f} {y2} L {cx - w2 / 2:.1f}"
                f' {y2} Z" fill="{p["accent"]}" fill-opacity="{PRINT_WASH_OPACITY}"'
                f' stroke="{p["line"]}" stroke-width="1"/>'
            )
        inside = w >= _VFUNNEL_COUNT_INSIDE_MIN
        tx = cx if inside else cx + w / 2 + 6
        anchor = "middle" if inside else "start"
        parts.append(
            f'<text x="{tx:.1f}" y="{y + _VFUNNEL_ROW / 2 + 4.5:.1f}"'
            f' text-anchor="{anchor}" fill="{p["accent_ink"]}" font-size="13"'
            f' font-weight="700">{group_digits(stage.count)}</text>'
        )
        lines = wrap_label(stage.label, _VFUNNEL_LABEL_BUDGET)
        for j, line in enumerate(lines):
            ly = y + _VFUNNEL_ROW / 2 + 4 + (j - (len(lines) - 1) / 2) * _FUNNEL_LINE_H
            parts.append(
                f'<text x="{_VFUNNEL_LABEL_RIGHT}" y="{ly:.1f}" text-anchor="end"'
                f' fill="{p["ink"]}" font-size="12" font-weight="600">'
                f"{html_escape(line)}</text>"
            )
    height = (
        2 * _VFUNNEL_PAD
        + len(stages) * _VFUNNEL_ROW
        + (len(stages) - 1) * _VFUNNEL_GAP
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" class="funnel"'
        f' viewBox="0 0 {_VFUNNEL_WIDTH} {height}">' + "".join(parts) + "</svg>"
    )
```

`parse_funnel` bounds the stage count against the horizontal geometry; the vertical height grows linearly with stages, and Task 5's tree test holds the real figure to the 648-unit bound, so no second bound is added here.

Fix the stale comment above `_D2_TIMEOUT_S` so it asserts no count: "The d2 diagrams render in well under a second; a bound this loose only ever fires on a d2 that has genuinely wedged. (The screening funnel is a `funnel` fence and never reaches the CLI.)"

- [ ] **Step 4: Run the tests**

Run: `caffeinate uv run pytest tests/scripts/test_render_handbook_artifact.py -q`
Expected: PASS.

- [ ] **Step 5: Confirm the page is unchanged**

Run: `caffeinate uv run python scripts/render_handbook_artifact.py` before and after the change (stash-free: build once on the task's BASE in a temporary worktree, once on the working tree) and `cmp` the two outputs.
Expected: identical. Record the result in the task report.

- [ ] **Step 6: Commit**

```bash
git commit -m "The page renderer draws a print variant: transparent d2 prelude and a vertical funnel

Refs #190" -- scripts/render_handbook_artifact.py tests/scripts/test_render_handbook_artifact.py
```

---

### Task 2: `book_figures`: hash, seed clean-up and the checks

**Files:**
- Create: `scripts/book_figures.py`
- Create: `tests/scripts/test_book_figures.py`
- Modify: `pyproject.toml` (`known_first_party` gains `book_figures`)

**Interfaces:**
- Produces:
  - `FIGURE_FONT = "Source Sans 3"`, `PT_PER_UNIT = 2 / 3`, `MAX_VIEWBOX = (388.8, 648.0)`, `TEXT_PT_RANGE = (7.0, 9.0)`, `PAPER_CREAM = "#f7f0dc"`
  - `source_hash(source: str) -> str`
  - `recorded_hash(svg: str) -> str | None`
  - `stamp_hash(svg: str, digest: str) -> str`
  - `viewbox(svg: str) -> tuple[float, float]`
  - `clean_seed_svg(svg: str, figure_id: str) -> str`
  - `fit_problems(svg: str) -> list[str]`
  - `opaque_fill_problems(svg: str) -> list[str]`
  - `contrast_problems(svg: str, paper: str = PAPER_CREAM) -> list[str]`
  - `contrast_ratio(a: str, b: str) -> float`

The three `*_problems` functions return human-readable strings, empty when the figure passes, so a test can assert `== []` and print every problem at once.

- [ ] **Step 1: Write the failing tests**

Fixtures in the test module: `D2_LIKE`, a trimmed d2 output (outer `<svg ... viewBox="0 0 287 587">`, inner `<svg class="d2-1314600225 d2-svg">`, a background `<rect ... fill="transparent">`, a `<style>` with an `@font-face` carrying `data:application/font-woff;base64,AAAA`, a second `<style>` with `.shape{...}`, a `<g class="dGFzay5h">` (base64 of `task.a`) with `<rect fill="transparent" stroke="#8a867a">` and `<text class="text-bold" fill="#1c2024" style="text-anchor:middle;font-size:12px">Agent A</text>`, and a `<mask id="d2-1314600225">` containing `<rect fill="white"/>`); and `INKSCAPE_LIKE`, the same drawing as Inkscape saves it (`xmlns:inkscape`/`xmlns:sodipodi` declared, a `<sodipodi:namedview>`, a `<metadata>`, and `<text style="font-size:12px;font-weight:bold;fill:#1c2024">`).

```python
def test_source_hash_is_sha256_of_the_body():
    assert bf.source_hash("a -> b\n") == hashlib.sha256(b"a -> b\n").hexdigest()


def test_stamp_then_read_the_hash():
    stamped = bf.stamp_hash('<svg viewBox="0 0 1 1"></svg>', "ab" * 32)
    assert bf.recorded_hash(stamped) == "ab" * 32


def test_stamping_replaces_an_old_hash():
    once = bf.stamp_hash('<svg viewBox="0 0 1 1"></svg>', "a" * 64)
    twice = bf.stamp_hash(once, "b" * 64)
    assert bf.recorded_hash(twice) == "b" * 64
    assert twice.count("data-source-sha256") == 1


def test_an_unstamped_figure_records_no_hash():
    assert bf.recorded_hash('<svg viewBox="0 0 1 1"></svg>') is None


def test_clean_seed_drops_embedded_fonts_and_styles():
    out = bf.clean_seed_svg(D2_LIKE, "codebase-structure-0")
    assert "@font-face" not in out and "font-woff" not in out and "<style" not in out
    assert f'font-family="{bf.FIGURE_FONT}"' in out


def test_clean_seed_turns_text_classes_into_attributes():
    out = bf.clean_seed_svg(D2_LIKE, "codebase-structure-0")
    assert 'class="text-bold"' not in out
    assert 'font-weight="700"' in out


def test_clean_seed_replaces_the_salt_and_the_base64_names():
    out = bf.clean_seed_svg(D2_LIKE, "codebase-structure-0")
    assert "1314600225" not in out
    assert 'id="codebase-structure-0-task-a"' in out
    assert "dGFzay5h" not in out


def test_clean_seed_refuses_an_unknown_text_class():
    with pytest.raises(ValueError, match="text-mono"):
        bf.clean_seed_svg(D2_LIKE.replace("text-bold", "text-mono"), "x-0")


def test_a_figure_inside_the_block_at_8pt_fits():
    assert bf.fit_problems(bf.clean_seed_svg(D2_LIKE, "x-0")) == []


def test_a_figure_wider_than_the_block_does_not_fit():
    wide = D2_LIKE.replace('viewBox="0 0 287 587"', 'viewBox="0 0 424 361"', 1)
    assert any("wide" in p for p in bf.fit_problems(wide))


def test_a_label_outside_7_to_9pt_is_reported():
    big = D2_LIKE.replace("font-size:12px", "font-size:16px")
    assert any("16" in p for p in bf.fit_problems(big))


def test_a_figure_with_no_text_size_is_reported():
    bare = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><text>x</text></svg>'
    assert bf.fit_problems(bare)


def test_an_opaque_light_fill_is_reported_and_a_mask_is_not():
    painted = D2_LIKE.replace('fill="transparent" stroke="#8a867a"', 'fill="#f7f6f2" stroke="#8a867a"')
    assert bf.opaque_fill_problems(D2_LIKE) == []
    assert bf.opaque_fill_problems(painted)


def test_a_translucent_tint_is_not_opaque():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 9 9"><path d="M0 0" fill="#ece2cd" fill-opacity="0.15"/></svg>'
    assert bf.opaque_fill_problems(svg) == []


def test_pale_text_fails_contrast_and_ink_passes():
    assert bf.contrast_problems(D2_LIKE) == []
    assert bf.contrast_problems(D2_LIKE.replace('fill="#1c2024"', 'fill="#c3bfb1"'))


def test_the_page_hairline_fails_the_print_stroke_bar():
    assert bf.contrast_ratio("#c3bfb1", bf.PAPER_CREAM) < 3.0
    assert bf.contrast_ratio("#8a867a", bf.PAPER_CREAM) >= 3.0


def test_every_print_palette_colour_holds_its_bar():
    from render_handbook_artifact import PRINT_PALETTE
    for name in ("ink", "ink_soft", "accent_ink"):
        assert bf.contrast_ratio(PRINT_PALETTE[name], bf.PAPER_CREAM) >= 4.5
    for name in ("accent", "line"):
        assert bf.contrast_ratio(PRINT_PALETTE[name], bf.PAPER_CREAM) >= 3.0


def test_an_inkscape_saved_figure_passes_every_check():
    assert bf.fit_problems(INKSCAPE_LIKE) == []
    assert bf.opaque_fill_problems(INKSCAPE_LIKE) == []
    assert bf.contrast_problems(INKSCAPE_LIKE) == []
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/scripts/test_book_figures.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'book_figures'`.

- [ ] **Step 3: Implement `scripts/book_figures.py`**

Module docstring: what a book figure is (a committed SVG corrected by hand, seeded from d2), the one scale, and that nothing here spawns a process or writes a file.

Required behaviour, beyond what the tests pin:

- Parse with `xml.etree.ElementTree` for the checks. Strip namespaces from tag names (`tag.rsplit("}", 1)[-1]`) so an Inkscape file reads as a d2 one. Skip every subtree rooted at `mask`, `defs`, `metadata` or `namedview`.
- A colour is read from the `fill`/`stroke` attribute or the same property in `style`; `style` wins, as in SVG. Accept `#rgb`, `#rrggbb`, `white`, `black`; `none`, `transparent`, `currentColor` and `url(...)` are never opaque and never checked for contrast. An unrecognised colour is a problem string, not a silent pass.
- Opacity: an element with `opacity`, `fill-opacity` (for fills) or `stroke-opacity` (for strokes) below 1, in attribute or style, is translucent: not opaque, and not held to contrast.
- `opaque_fill_problems`: an opaque fill whose WCAG relative luminance is above 0.5, on any element but `text`/`tspan`. The root background `<rect fill="transparent">` passes by the rule above.
- `contrast_problems`: every opaque `text`/`tspan` fill at 4.5:1 against `paper`, every opaque stroke at 3:1.
- `fit_problems`: the root `viewBox` within `MAX_VIEWBOX` ("<w> units wide, over 388.8" / "... tall ..."), every `font-size` (attribute or style, unitless or `px`) times `PT_PER_UNIT` within `TEXT_PT_RANGE`, and a problem if no `font-size` occurs at all.
- `clean_seed_svg` works on the text, by regex, so d2's layout is not re-serialised: drop every `<style ...>...</style>`; map `class="text"` to `font-weight="400"`, `class="text-bold"` to `font-weight="700"`, `class="text-italic"` to `font-style="italic"`, and raise `ValueError` naming any other `text-*` class; add `font-family="Source Sans 3"` to the root `<svg>`; replace every `d2-<digits>` token with `figure_id`; replace each `<g class="<token>">` whose token base64-decodes to printable UTF-8 with `<g id="<figure_id>-<slug>">`, the slug being the decoded d2 key lower-cased with runs of non-alphanumerics collapsed to `-`, and a `-2`, `-3` suffix on a repeat. A funnel SVG passes through with only the font family added.
- `stamp_hash` and `recorded_hash` touch only the root `<svg>` tag.
- `contrast_ratio` is the WCAG 2 formula.

- [ ] **Step 4: Add `book_figures` to `known_first_party`** in alphabetical order.

- [ ] **Step 5: Run the tests and the gates**

Run: `uv run pytest tests/scripts/test_book_figures.py tests/test_deptry_gate.py -q && uv run deptry .`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git commit -m "book_figures holds a figure's hash, its seed clean-up, and the print checks

Refs #190" -- scripts/book_figures.py tests/scripts/test_book_figures.py pyproject.toml
```

---

### Task 3: `--seed-figures`

**Files:**
- Modify: `scripts/render_handbook_book.py`
- Test: `tests/scripts/test_render_handbook_book.py`

**Interfaces:**
- Consumes: `clean_seed_svg`, `stamp_hash`, `source_hash` (Task 2); `run_d2(..., "print")`, `funnel_svg_vertical`, `parse_funnel`, `extract_diagram_blocks` (Task 1 and the renderer).
- Produces: `figure_path(figures_dir: Path, stem: str, index: int) -> Path`, `seed_svg(stem: str, block: DiagramBlock) -> str`, `part_blocks(docs_dir: Path, parts) -> list[tuple[str, DiagramBlock]]`, `seed_figures(docs_dir: Path, figures_dir: Path, parts=PARTS) -> list[Path]`, CLI `--seed-figures` and `--figures-dir`.

- [ ] **Step 1: Write the failing tests**

```python
def test_figure_path_names_stem_and_index(tmp_path):
    assert rb.figure_path(tmp_path, "README", 0) == tmp_path / "README-0.svg"


def test_a_funnel_seed_is_stamped_and_vertical():
    block = DiagramBlock(index=0, kind="funnel", title="F", source="A 10\nB 1\n")
    svg = rb.seed_svg("evaluation", block)
    assert bf.recorded_hash(svg) == bf.source_hash(block.source)
    assert 'font-family="Source Sans 3"' in svg
    assert bf.fit_problems(svg) == []


def test_seeding_writes_missing_figures_only(tmp_path, monkeypatch):
    docs = tmp_path / "docs"; docs.mkdir()
    (docs / "a.md").write_text('# A\n\n```funnel title="F"\nA 10\nB 1\n```\n')
    figures = tmp_path / "figures"
    parts = [("p1", "a", "A")]
    assert rb.seed_figures(docs, figures, parts) == [figures / "a-0.svg"]
    (figures / "a-0.svg").write_text("hand-corrected")
    assert rb.seed_figures(docs, figures, parts) == []
    assert (figures / "a-0.svg").read_text() == "hand-corrected"


@pytest.mark.skipif(shutil.which("d2") is None, reason="needs the d2 CLI; CI gains it with #192")
def test_a_d2_seed_is_clean_and_transparent():
    block = DiagramBlock(index=0, kind="d2", title="T", source="a -> b\n")
    svg = rb.seed_svg("x", block)
    assert "@font-face" not in svg
    assert bf.opaque_fill_problems(svg) == []
```

Match the funnel fixture's body to `parse_funnel`'s real line format.

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/scripts/test_render_handbook_book.py -q -k "seed or figure_path"`
Expected: FAIL with `AttributeError`.

- [ ] **Step 3: Implement**

`part_blocks` reads each part's Markdown and calls `extract_diagram_blocks(md, stem)`, so seeding needs no Markdown conversion. `seed_svg` renders a d2 block with `run_d2(block.source, f"{stem}-{block.index}", "print")` and a funnel with `funnel_svg_vertical(parse_funnel(block.source, stem))`, then `stamp_hash(clean_seed_svg(raw, f"{stem}-{block.index}"), source_hash(block.source))`. `seed_figures` creates `figures_dir` if absent, writes each missing file as UTF-8, and returns the paths it wrote, in part order.

CLI: `--format` stops being `required`; add `--seed-figures` (store_true) and `--figures-dir` (default `docs_dir / "figures"`, resolved after parsing). Exactly one of `--format` and `--seed-figures` is required: `parser.error(...)` otherwise. `--seed-figures` prints one `wrote <path>` line per file, or `every diagram already has a figure`.

Update the module docstring's Usage block with the new command.

- [ ] **Step 4: Run the tests**

Run: `caffeinate uv run pytest tests/scripts/test_render_handbook_book.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git commit -m "render_handbook_book seeds a starting figure for every diagram that has none

Refs #190" -- scripts/render_handbook_book.py tests/scripts/test_render_handbook_book.py
```

---

### Task 4: The EPUB draws the figures

**Files:**
- Create: `fonts/source-sans-3/SourceSans3-Regular.ttf`, `fonts/source-sans-3/SourceSans3-Bold.ttf`, `fonts/source-sans-3/SourceSans3-It.ttf`, `fonts/source-sans-3/OFL.txt`
- Modify: `scripts/book_figures.py`, `scripts/render_handbook_book.py`, `pyproject.toml` (`fonttools` in `[project] dependencies`, with a comment saying the book build subsets fonts into the EPUB's figures), `uv.lock`
- Test: `tests/scripts/test_book_figures.py`, `tests/scripts/test_render_handbook_book.py`

**Interfaces:**
- Consumes: Tasks 2 and 3.
- Produces: `book_figures.with_backing_panel(svg: str, colour: str) -> str`, `book_figures.embed_fonts(svg: str, font_dir: Path) -> str`, `book_figures.epub_width_em(svg: str) -> float`, `render_handbook_book.figure_markup(stem: str, block: DiagramBlock, width_em: float) -> str`, `render_handbook_book.load_figure(figures_dir: Path, stem: str, block: DiagramBlock) -> tuple[str, bool]` (the SVG, and whether it is a seed standing in), `book_html(assembled, figures: dict[str, dict[int, str]]) -> str`, `epub_command(..., resource_path: Path)`.

- [ ] **Step 1: Fetch the fonts**

```bash
caffeinate gh release download 3.052R --repo adobe-fonts/source-sans --pattern 'TTF-source-sans-3.052R.zip' --dir "$SCRATCH"
unzip -o "$SCRATCH/TTF-source-sans-3.052R.zip" -d "$SCRATCH/ss3"
```

`$SCRATCH` is the SDD workspace directory the controller names. Copy the unmodified `SourceSans3-Regular.ttf`, `SourceSans3-Bold.ttf` and `SourceSans3-It.ttf` into `fonts/source-sans-3/`, and the release's licence file as `OFL.txt`. If the zip's file names differ, keep Adobe's names and report them. Verify with fontTools that each face's name table reads `Source Sans 3` and that `OS/2.fsType` is 0; record both in the report. Run `uv add fonttools`.

- [ ] **Step 2: Write the failing tests**

In `test_book_figures.py`:

```python
FONTS = Path(__file__).resolve().parents[2] / "fonts" / "source-sans-3"


def test_the_panel_is_the_first_drawn_element():
    out = bf.with_backing_panel(bf.clean_seed_svg(D2_LIKE, "x-0"), "#f7f6f2")
    first = re.search(r"<svg[^>]*>\s*<(\w+)[^>]*>", out)
    assert first.group(1) == "rect" and 'fill="#f7f6f2"' in first.group(0)


def test_the_panel_covers_the_viewbox():
    out = bf.with_backing_panel('<svg xmlns="http://www.w3.org/2000/svg" viewBox="3 4 50 60"></svg>', "#fff")
    assert 'x="3" y="4" width="50" height="60"' in out


def test_embed_fonts_carries_only_the_faces_used():
    out = bf.embed_fonts(bf.clean_seed_svg(D2_LIKE, "x-0"), FONTS)
    assert out.count("@font-face") == 1
    assert "font-weight:700" in out.replace(" ", "")


def test_embed_fonts_reads_an_inkscape_style_weight():
    out = bf.embed_fonts(INKSCAPE_LIKE, FONTS)
    assert "font-weight:700" in out.replace(" ", "")


def test_the_embedded_face_is_a_small_subset():
    out = bf.embed_fonts(bf.clean_seed_svg(D2_LIKE, "x-0"), FONTS)
    assert len(out) < 40_000


def test_the_epub_width_keeps_the_one_scale():
    assert bf.epub_width_em('<svg viewBox="0 0 300 100"></svg>') == pytest.approx(20.0)
```

In `test_render_handbook_book.py`:

```python
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


def test_book_html_places_figures_not_listings():
    part = AssembledPart(anchor="p1", stem="a", html='<h1 id="a-x">X</h1><div class="dgph" data-i="0"></div>', blocks=[DiagramBlock(0, "d2", "T", "a -> b")])
    html = rb.book_html([part], {"a": {0: "<figure>F</figure>"}})
    assert "<figure>F</figure>" in html and "<pre>" not in html


@needs_pandoc_and_d2
def test_the_epub_carries_one_image_per_fence(built_epub):
    ...  # count <img> across chapter XHTML == len(rb.part_blocks(DOCS, PARTS)); every src resolves to a media SVG in the archive


@needs_pandoc_and_d2
def test_every_epub_figure_has_its_panel_and_fonts(built_epub):
    ...  # each media SVG: first drawn element is the panel rect, and every face its text uses has an @font-face


@needs_pandoc_and_d2
def test_no_fence_survives_as_a_listing(built_epub):
    ...  # no fence body line appears inside any <pre> in the chapters


@needs_pandoc_and_d2
def test_the_epub_image_keeps_its_em_width(built_epub):
    ...  # every <img> carries a style width in em
```

Build `built_epub` once as a module-scoped fixture, as the existing pandoc-gated tests do; reuse that fixture if one exists. `needs_pandoc_and_d2` skips with the Global Constraints wording when either CLI is absent. Write the elided bodies in the file; the comment on each says what it asserts.

`AssembledPart`'s constructor must match `render_handbook_artifact.AssembledPart` exactly; read it before writing the fixture.

- [ ] **Step 3: Run them to verify they fail**

Run: `uv run pytest tests/scripts/test_book_figures.py tests/scripts/test_render_handbook_book.py -q`
Expected: FAIL on the new names.

- [ ] **Step 4: Implement**

`book_figures`:
- `with_backing_panel`: insert `<rect x=".." y=".." width=".." height=".." fill="<colour>"/>` from the root viewBox's four numbers immediately after the root `<svg ...>` tag, formatting each number with `:g`.
- `embed_fonts`: collect, per `(weight, style)` of each `text` element (attribute, else style property, else its nearest ancestor's, else `400`/`normal`; `bold` reads as 700, `normal` as 400), the characters of its text (`"".join(el.itertext())`). Map `(400, normal)`, `(700, normal)`, `(400, italic)` to the three committed files; any other weight maps to the nearest of 400 and 700 (the funnel's labels are 600). Subset each used face with `fontTools.subset` (`Options(flavor="woff")`, glyphs = the collected characters plus space), and insert one `<style>` holding one `@font-face { font-family: "Source Sans 3"; font-weight: N; font-style: S; src: url(data:font/woff;base64,...) }` per face after the root tag. Raise `FileNotFoundError` with the font directory in the message if a face file is missing.
- `epub_width_em`: viewBox width times `PT_PER_UNIT` divided by 10 (the body's nominal 10 pt), which is width / 15.

`render_handbook_book`:
- `figure_markup` per the spec's markup, with `style="width: <w:.2f>em; max-width: 100%"` on the `<img>`, `alt` escaped with `quote=True`, the caption with `quote=False` as `listing_markup` did.
- `load_figure` reads the committed file if present, else returns `(seed_svg(stem, block), True)`.
- `book_html(assembled, figures)` substitutes `figures[part.stem][index]` for each placeholder, raising as it does now when one is missing; delete `listing_markup` and its tests.
- `build_epub(docs_dir, out, date, parts=PARTS, figures_dir=None)`: `figures_dir` defaults to `docs_dir / "figures"`. For every block, `load_figure`, print `NOTE: <stem>-<index> has no committed figure; the book uses its seed` to stderr when seeded, write `embed_fonts(with_backing_panel(svg, PALETTE["light"]["surface"]), FONT_DIR)` to `work / "media" / f"{stem}-{index}.svg"`, and build the markup with `epub_width_em(svg)`. `FONT_DIR` is `Path(__file__).resolve().parents[1] / "fonts" / "source-sans-3"`.
- `epub_command` gains `resource_path` and passes `--resource-path <work>`; images are referenced as `media/...` relative to it.
- `EPUB_CSS` gains `figure img { display: block; margin: 0 auto; }`.
- Update the module docstring (diagrams are figures; needs the pandoc and d2 CLIs), `curl_quotes`' docstring where it says the book's diagram-source listings reach pandoc, and the `main` help text.

- [ ] **Step 5: Run the tests, build, and epubcheck**

```bash
caffeinate uv run pytest tests/ -q
caffeinate uv run python scripts/render_handbook_book.py --format epub
caffeinate epubcheck build/handbook.epub
```

Expected: tests PASS; the build prints one `NOTE` per fence (no figure is committed yet); epubcheck reports 0 fatals, 0 errors, 0 warnings. If epubcheck rejects the embedded `@font-face` or the `style` width, report the exact message rather than working around it.

- [ ] **Step 6: Commit**

```bash
git add fonts/source-sans-3
git commit -m "The EPUB draws its diagrams as figures, on a light panel, with their fonts

Refs #190" -- fonts/source-sans-3 scripts/book_figures.py scripts/render_handbook_book.py tests/scripts/test_book_figures.py tests/scripts/test_render_handbook_book.py pyproject.toml uv.lock
```

---

### Task 5: The starting figures, their tree test, and the docs

**Files:**
- Create: `docs/engineering/figures/<stem>-<index>.svg`, one per diagram fence
- Create: `tests/scripts/test_book_figures_tree.py`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Write the tree test**

```python
"""Every committed book figure matches its fence and holds the print checks."""

DOCS = Path(__file__).resolve().parents[2] / "docs" / "engineering"
FIGURES = DOCS / "figures"
BLOCKS = {f"{stem}-{b.index}": b for stem, b in rb.part_blocks(DOCS, PARTS)}
COMMITTED = sorted(FIGURES.glob("*.svg"))


def test_every_committed_figure_names_a_fence():
    assert [p.name for p in COMMITTED if p.stem not in BLOCKS] == []


@pytest.mark.parametrize("path", COMMITTED, ids=lambda p: p.stem)
def test_a_committed_figure_was_drawn_from_its_fence_as_it_stands(path):
    block = BLOCKS[path.stem]
    assert bf.recorded_hash(path.read_text()) == bf.source_hash(block.source), (
        f"{path.name} was drawn from an older version of the fence titled "
        f"{block.title!r}; redraw it, or confirm it still holds and re-stamp it"
    )


@pytest.mark.parametrize("path", COMMITTED, ids=lambda p: p.stem)
def test_a_committed_figure_holds_the_print_checks(path):
    svg = path.read_text()
    assert bf.fit_problems(svg) + bf.opaque_fill_problems(svg) + bf.contrast_problems(svg) == []
```

Add a test that injects the failure the hash test exists for: copy one committed figure into `tmp_path`, stamp it with `source_hash("changed")`, and assert the comparison against its fence fails. That keeps the guard non-vacuous.

- [ ] **Step 2: Seed the starting figures**

The maintainer reviewed narrower starting layouts than the fences' own on 2026-09-28. Write a throwaway script in the SDD workspace (never committed) that, for each fence below, renders the given d2 source through `run_d2(src, figure_id, "print")` (or the funnel through `funnel_svg_vertical`), cleans it with `clean_seed_svg`, stamps it with `source_hash(<the real fence body>)`, and writes `docs/engineering/figures/<stem>-<index>.svg`. Fences not listed seed from their own body via `seed_svg`. `PERSON` and `BLANK` are the icon paths `d2_icon_classes("print")` declares for `human` and `step`; read them from its return value.

`README-0` (the story of a change):

```d2
direction: down
classes: {
  s: { width: 150; height: 34; icon: BLANK; icon.near: center-left; label.near: center-center }
  h: { width: 150; height: 34; icon: PERSON; icon.near: center-left; label.near: center-center }
}
idea: An idea {class: s}
issue: Issue {class: s}
spec: Spec {class: h}
plan: Plan {class: s}
build: Build {class: s}
merge: Merge {class: h}
run: Observe {class: s}
decide: Evaluate {class: s}
idea -> issue -> spec -> plan -> build -> merge -> run -> decide
decide -> idea: the next issue
```

`codebase-structure-0`:

```d2
task: Task layer {
  width: 260
  a: Agent A
  b: Agent B
  a -> b: as_tool {style.stroke-dash: 4}
}
core: Reusable core {
  grid-columns: 2
  grid-gap: 8
  ev: Evaluation
  cap: Capabilities
  integ: "External\nintegrations"
  conf: Configuration
  infra: "Core\ninfrastructure"
  types: "Shared schemas\n/ types"
}
task -> core: "imports point\nat the core"
core -> task: "never, and\nnever in a cycle" {style.stroke-dash: 4}
```

`data-protection-0`:

```d2
u: Data subject {width: 190}
app: Your system {width: 190}
b: Minimize at the boundary {shape: hexagon; width: 190}
p: Third-party processor {width: 190}
s: Your stores {shape: cylinder}
u -> app
app -> b
b -> p: "model, search,\nOCR, tracing"
app -> s: "at rest, under\na retention limit"
```

`security-supply-chain-0`:

```d2
src: Untrusted source
b: "Validate and canonicalize\nat the boundary" {shape: hexagon}
app: Your code
n: "Neutralize\nat the sink" {shape: hexagon}
sink: Dangerous sink
src -> b -> app -> n -> sink
```

`observability-0`:

```d2
tool: A tool runs
ctx: Model context
side: Side channel
art: "Run artifacts, persisted\ninto production"
tool -> ctx: "the result\nthe model reads"
tool -> side: "the metadata\nenvelope"
side -> art: "timing, tokens,\ncost, utilization"
side -> ctx: never {style.stroke-dash: 4}
```

Confirm each `<stem>-<index>` against `part_blocks`; if an index differs, the fence's position is the truth.

- [ ] **Step 3: Run the tree test and fix what the seeds fail**

Run: `caffeinate uv run pytest tests/scripts/test_book_figures_tree.py -q`
Expected: PASS. A seed that fails a check is a finding about the seed, not the check: report it with the problem strings, and change only the throwaway source (never a check's bound) to bring it inside.

- [ ] **Step 4: Rebuild and epubcheck**

```bash
caffeinate uv run python scripts/render_handbook_book.py --format epub
caffeinate epubcheck build/handbook.epub
```

Expected: no `NOTE` lines; epubcheck 0 fatals, 0 errors, 0 warnings.

- [ ] **Step 5: Update CLAUDE.md**

- Commands: the book line becomes `uv run python scripts/render_handbook_book.py --format epub      # needs the pandoc and d2 CLIs; writes build/handbook.epub`, and a new line `uv run python scripts/render_handbook_book.py --seed-figures     # write a starting SVG for every diagram without a committed book figure`.
- Repository layout: `docs/engineering/figures/` holds the book's figures, one SVG per diagram fence, corrected by hand from a seed and stamped with the hash of the fence body it was drawn from; editing a fence fails `tests/scripts/test_book_figures_tree.py` until the figure is redrawn or re-stamped. `fonts/source-sans-3/` holds the figures' font, unmodified, under its OFL licence.

- [ ] **Step 6: Commit**

```bash
git add docs/engineering/figures tests/scripts/test_book_figures_tree.py
git commit -m "Seed the book's figures, and hold every committed one to its fence and the print checks

Refs #190" -- docs/engineering/figures tests/scripts/test_book_figures_tree.py CLAUDE.md
```

---

## After the plan: the maintainer's hand pass

The pull request opens with these seeds. The maintainer corrects the figures by hand before merge (decided 2026-09-28): the hexagon entry on `data-protection-0`, the column alignment on `README-0`, vertical compression wherever a gap carries nothing. Each corrected file keeps its `data-source-sha256`, and the tree test and epubcheck run again on the corrected tree before merge.
