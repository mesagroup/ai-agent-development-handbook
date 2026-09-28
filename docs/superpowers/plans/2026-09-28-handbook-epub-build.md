# Handbook EPUB Build Implementation Plan (#189)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One command builds an EPUB3 of the handbook from `docs/engineering/*.md`, carrying the rendered page's heading ids and in-book links, with diagrams shown as listings until #190.

**Architecture:** The first half of `build()` in `scripts/render_handbook_artifact.py` becomes a shared `assemble()` that returns each part's HTML with heading ids and rewritten links. A new `scripts/render_handbook_book.py` calls it with a book link map, writes one HTML document, and runs `pandoc -f html+smart -t epub3 --split-level=1` over it.

**Tech Stack:** Python 3.12 via `uv run`, python-markdown (already declared), pandoc 3.8 CLI, pytest, ruff, epubcheck (manual verification only).

**Spec:** `docs/superpowers/specs/2026-09-25-handbook-book-pipeline-design.md`. This plan implements its delivery item 1 (#189). Items 2 (#190) and 3 (#195) get their own plans.

## Global Constraints

- Run Python through `uv run`. Run `uv run ruff check . && uv run ruff format --check .` before every commit.
- No em-dash (U+2014) in `docs/superpowers/plans/` or `docs/superpowers/specs/`. Use ` - `.
- Markdown is never hard-wrapped.
- No bare `except Exception: pass`. Every exception is reported with type and message or re-raised.
- Every subprocess call has a timeout.
- The rendered page's output must not change: `build()` after the refactor returns byte-identical HTML to `build()` before it.
- Commit with explicit paths: `git commit -m "..." -- <paths>`. A new file is `git add`-ed first. Never `git add -A`, `git add .` or `git commit -a`.
- Commit messages end with `Refs #189` and carry no AI attribution trailer (the `commit-msg` hook refuses one).
- No environment-specific values in committed files: no absolute personal paths, emails or hostnames.
- New module in `scripts/` joins `[tool.deptry] known_first_party` in `pyproject.toml`, and `tests/test_deptry_gate.py` holds that list against the directory.
- EPUB metadata: title `AI Agent Development Handbook`, creator `Janos Tolgyesi`, `lang: en`, rights stating CC BY 4.0 without naming a copyright holder (#188 has not settled it).

## Review Focus

1. **A part with no heading.** `book_linkmap` needs each part's first heading id. A part with none must raise, naming the part, rather than produce a link to `#`. Test in Task 2.
2. **Diagram source containing `<` or `&`.** The listing that stands in for a diagram until #190 must escape its source, or pandoc reads d2 syntax as markup and silently drops it. Test in Task 2.
3. **pandoc absent or hung.** The build must stop with a message naming the tool and how to install it, not a traceback, and must not hang. Tests in Task 3.
4. **An output path whose directory does not exist.** `--out build/x/handbook.epub` must create the directory. Test in Task 3.
5. **Running from another working directory.** The builder must resolve its inputs from the repository, not the cwd. The CLI default paths are absolute, derived from `__file__`. Test in Task 3.

---

### Task 1: Extract `assemble()` from `build()`

**Files:**
- Modify: `scripts/render_handbook_artifact.py` (the `build` function and a new `AssembledPart` dataclass and `assemble` function placed directly above `build`)
- Test: `tests/scripts/test_render_handbook_artifact.py`

**Interfaces:**
- Consumes: `render_part`, `post_process`, `_SCHEME_RE`, `DiagramBlock`, `PARTS` (all existing).
- Produces:
  - `AssembledPart` frozen dataclass: `anchor: str`, `stem: str`, `html: str`, `blocks: list[DiagramBlock]`.
  - `assemble(docs_dir: Path, parts: list[tuple[str, str, str]] = PARTS, linkmap: dict[str, str] | None = None) -> list[AssembledPart]`. `linkmap=None` means the page's map, `{stem + ".md": "#" + anchor}`. It raises `ValueError` exactly where `build` raises today (id collision, dead relative link) and prints the same WARNING and NOTE lines.

- [ ] **Step 1: Capture the page before the refactor**

Render the live page with diagram rendering stubbed, so the comparison needs no d2 CLI and is deterministic. Save it outside the tree.

Run:
```bash
mkdir -p "$TMPDIR/handbook-189" && uv run python -c "
import sys; sys.path.insert(0, 'scripts')
from pathlib import Path
import render_handbook_artifact as r
r.render_variants = lambda block, stem: ('<svg viewBox=\"0 0 1 1\"></svg>', '<svg viewBox=\"0 0 1 1\"></svg>')
Path(sys.argv[1]).write_text(r.build(Path('docs/engineering')))
" "$TMPDIR/handbook-189/before.html"
```
Expected: the file exists and is non-empty.

- [ ] **Step 2: Write the failing tests**

Add to `tests/scripts/test_render_handbook_artifact.py`:

```python
def test_assemble_returns_each_part_with_ids_and_rewritten_links(tmp_path: Path):
    pytest.importorskip("markdown")
    (tmp_path / "README.md").write_text("# Handbook\n\nSee [later](later.md).\n")
    (tmp_path / "later.md").write_text("# Later\n\ntext\n")
    parts = [("top", "README", "Overview"), ("p1", "later", "Later")]
    assembled = rh.assemble(tmp_path, parts)
    assert [(a.anchor, a.stem) for a in assembled] == [("top", "README"), ("p1", "later")]
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


def test_assemble_raises_on_a_dead_relative_link_before_any_diagram_renders(
    tmp_path: Path, monkeypatch
):
    pytest.importorskip("markdown")
    (tmp_path / "README.md").write_text("# Handbook\n\nSee [x](missing.md).\n")

    def fail(*args, **kwargs):
        raise AssertionError("a diagram was rendered before the link check")

    monkeypatch.setattr(rh, "render_variants", fail)
    with pytest.raises(ValueError, match="missing.md"):
        rh.assemble(tmp_path, [("top", "README", "Overview")])
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/scripts/test_render_handbook_artifact.py -k assemble -v`
Expected: FAIL with `AttributeError: module 'render_handbook_artifact' has no attribute 'assemble'`.

- [ ] **Step 4: Implement `AssembledPart` and `assemble`, and make `build` call it**

Insert directly above `def build(`:

```python
@dataclass(frozen=True)
class AssembledPart:
    """One part after ids and links, before diagrams and page chrome."""

    anchor: str
    stem: str
    html: str
    blocks: list[DiagramBlock]


def assemble(
    docs_dir: Path,
    parts: list[tuple[str, str, str]] = PARTS,
    linkmap: dict[str, str] | None = None,
) -> list[AssembledPart]:
    """Render every part with heading ids and rewritten links.

    The half of the build the page and the book share. Every part is
    rendered before any link is rewritten, so a fragment into a later part
    finds its id. Diagrams stay as placeholders for the caller, which is what
    lets the page draw two themed variants and the book one print variant.

    Args:
        docs_dir: Directory holding the handbook Markdown.
        parts: ``(anchor, stem, label)`` in page order.
        linkmap: ``<stem>.md`` to the fragment a bare link to that part
            lands on. ``None`` means the page's map, the part anchors.

    Raises:
        ValueError: A heading id collides with another id, or a relative
            link names no part or no heading. See `build` for why each is a
            raise rather than a warning.
    """
    if linkmap is None:
        linkmap = {stem + ".md": "#" + anchor for anchor, stem, _ in parts}
    rendered = {stem: render_part(docs_dir, stem) for _, stem, _ in parts}
    ids = {anchor for anchor, _, _ in parts}
    for stem, (_, part_ids, _) in rendered.items():
        clash = ids & set(part_ids)
        if clash:
            raise ValueError(
                f"{stem}.md: heading id(s) {sorted(clash)} collide with an id the "
                "page already carries, so a link to one of them would land on "
                "the other"
            )
        ids.update(part_ids)
    assembled = []
    for anchor, stem, _ in parts:
        html, _, blocks = rendered[stem]
        html, unmapped, unlinked = post_process(html, linkmap, ids)
        dead = [h for h in unmapped if not _SCHEME_RE.match(h)]
        if dead:
            raise ValueError(
                f"{stem}.md: relative link(s) the artifact cannot resolve: "
                + ", ".join(dead)
                + ". A sibling link must name a part this artifact contains, and "
                "a fragment on it must name a heading of that part; a target "
                "outside the handbook is written relatively and gets unlinked "
                "here."
            )
        for href in unmapped:
            print(f"  WARNING unmapped link in {stem}.md: {href}")
        for href in unlinked:
            print(f"  NOTE unlinked out-of-tree link in {stem}.md: {href}")
        assembled.append(AssembledPart(anchor, stem, html, blocks))
    return assembled
```

Replace the body of `build` (keep its docstring unchanged) with:

```python
    sections = []
    for part in assemble(docs_dir, parts):
        cls = "part intro" if part.anchor == "top" else "part"
        html = part.html
        if part.blocks:
            html = substitute_diagrams(
                html,
                {
                    block.index: diagram_figure(
                        part.stem, block, *render_variants(block, part.stem)
                    )
                    for block in part.blocks
                },
            )
        sections.append(
            f'    <section id="{part.anchor}" class="{cls}">\n'
            f'      <div class="col doc">\n{html}\n      </div>\n    </section>'
        )
    body = _BODY % {"nav": render_nav(parts), "sections": "\n".join(sections)}
    return to_ascii_entities(_HEAD + body + _SCRIPT)
```

- [ ] **Step 5: Run the whole renderer test file**

Run: `uv run pytest tests/scripts/test_render_handbook_artifact.py -q`
Expected: all pass, including the three new tests and every existing `build` test.

- [ ] **Step 6: Verify the page is byte-identical**

Run:
```bash
uv run python -c "
import sys; sys.path.insert(0, 'scripts')
from pathlib import Path
import render_handbook_artifact as r
r.render_variants = lambda block, stem: ('<svg viewBox=\"0 0 1 1\"></svg>', '<svg viewBox=\"0 0 1 1\"></svg>')
Path(sys.argv[1]).write_text(r.build(Path('docs/engineering')))
" "$TMPDIR/handbook-189/after.html" && cmp "$TMPDIR/handbook-189/before.html" "$TMPDIR/handbook-189/after.html" && echo IDENTICAL
```
Expected: `IDENTICAL`. Record this result for the PR body. The spec asked for a committed test here. A committed test cannot run the pre-refactor code, so the check is this recorded comparison, and the PR body says so.

- [ ] **Step 7: Lint, full suite, commit**

Run: `uv run ruff check . && uv run ruff format --check . && uv run pytest tests/ -q`
Expected: clean, all pass.

```bash
git commit -m "The page renderer's ids-and-links half becomes a shared assemble()

The EPUB and the paperback need each part's HTML with the page's heading
ids and rewritten links, and nothing after that. build() now calls
assemble() and keeps only its diagrams and page chrome. The rendered page
is byte-identical before and after, checked with diagrams stubbed.

Refs #189" -- scripts/render_handbook_artifact.py tests/scripts/test_render_handbook_artifact.py
```

---

### Task 2: The book's pure assembly functions

**Files:**
- Create: `scripts/render_handbook_book.py`
- Create: `tests/scripts/test_render_handbook_book.py`
- Modify: `pyproject.toml` (`[tool.deptry] known_first_party` gains `"render_handbook_book"`, alphabetically after `"render_handbook_artifact"`)

**Interfaces:**
- Consumes: `render_handbook_artifact.assemble`, `AssembledPart`, `DiagramBlock`, `render_part`, `PARTS`, `_DIAGRAM_PLACEHOLDER_RE`.
- Produces (used by Task 3):
  - `TITLE = "AI Agent Development Handbook"`, `CREATOR = "Janos Tolgyesi"`, `RIGHTS: str`, `EPUB_CSS: str`
  - `book_linkmap(parts: list[tuple[str, str, str]], first_ids: dict[str, str]) -> dict[str, str]`
  - `first_heading_ids(docs_dir: Path, parts: list[tuple[str, str, str]]) -> dict[str, str]`
  - `listing_markup(block: DiagramBlock) -> str`
  - `book_html(assembled: list[AssembledPart]) -> str`
  - `book_identifier(title: str) -> str`
  - `book_metadata(date: str) -> str` (a YAML document)
  - `epub_command(html_path: Path, metadata_path: Path, css_path: Path, out: Path) -> list[str]`

- [ ] **Step 1: Write the failing tests**

Create `tests/scripts/test_render_handbook_book.py`:

```python
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
    with pytest.raises(ValueError, match="empty.md"):
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
        tmp_path / "book.html", tmp_path / "meta.yaml", tmp_path / "epub.css", tmp_path / "out.epub"
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/scripts/test_render_handbook_book.py -v`
Expected: FAIL at collection with `ModuleNotFoundError: No module named 'render_handbook_book'`.

- [ ] **Step 3: Implement the pure functions**

Create `scripts/render_handbook_book.py`:

```python
"""Build the handbook as a book: an EPUB now, the paperback later (#195).

The page renderer's first pass, `assemble`, produces each part's HTML with
the heading ids and in-page links the rendered page carries. This module
joins those parts into one HTML document and hands it to pandoc, so the
book's ids are the page's by construction and every citation a report
emits lands on the same heading in both. Diagrams render as listings here
until #190 draws them as figures.

Usage::

    uv run python scripts/render_handbook_book.py --format epub
    uv run python scripts/render_handbook_book.py --format epub --out /tmp/handbook.epub

Needs the pandoc CLI (``brew install pandoc``). Everything except
`run_tool`, `build_epub` and `main` is pure and unit-tested in
``tests/scripts/test_render_handbook_book.py``.
"""

from __future__ import annotations

import uuid
from html import escape as html_escape
from pathlib import Path

from render_handbook_artifact import (
    _DIAGRAM_PLACEHOLDER_RE,
    PARTS,
    AssembledPart,
    DiagramBlock,
    render_part,
)

TITLE = "AI Agent Development Handbook"
CREATOR = "Janos Tolgyesi"
# No holder is named: #188 has not settled who holds the copyright.
RIGHTS = (
    "Licensed under the Creative Commons Attribution 4.0 International "
    "License (CC BY 4.0), https://creativecommons.org/licenses/by/4.0/"
)

EPUB_CSS = """\
body { font-family: serif; line-height: 1.45; }
h1, h2, h3, h4 { font-family: sans-serif; line-height: 1.2; }
code, pre { font-family: monospace; font-size: 0.85em; }
pre { white-space: pre-wrap; }
table { border-collapse: collapse; font-size: 0.85em; }
th, td { border: 1px solid #888; padding: 0.25em 0.4em; text-align: left; vertical-align: top; }
figure { margin: 1em 0; }
figcaption { font-size: 0.85em; font-style: italic; }
"""


def book_linkmap(
    parts: list[tuple[str, str, str]], first_ids: dict[str, str]
) -> dict[str, str]:
    """Map each ``<stem>.md`` to its part's first heading id.

    The page links a part by its section anchor (``#p1``). The book emits no
    section wrapper, because a wrapper stops pandoc splitting chapters on the
    part's ``<h1>``, so a bare part link lands on that heading instead.

    Raises:
        ValueError: A part has no heading, so a link to it has nowhere to land.
    """
    linkmap = {}
    for _, stem, _ in parts:
        if stem not in first_ids:
            raise ValueError(
                f"{stem}.md has no heading, so a book link to it would land nowhere"
            )
        linkmap[stem + ".md"] = "#" + first_ids[stem]
    return linkmap


def first_heading_ids(
    docs_dir: Path, parts: list[tuple[str, str, str]]
) -> dict[str, str]:
    """Each part's first heading id; a part with no heading is left out."""
    first = {}
    for _, stem, _ in parts:
        _, ids, _ = render_part(docs_dir, stem)
        if ids:
            first[stem] = ids[0]
    return first


def listing_markup(block: DiagramBlock) -> str:
    """Stand a diagram in as its escaped source under its caption.

    Until #190 draws figures, the book shows each diagram's source. The source
    is escaped: d2 syntax such as ``a -> b: <x>`` would otherwise reach pandoc
    as markup and be dropped without a word.
    """
    return (
        "<figure>"
        f"<pre><code>{html_escape(block.source, quote=False)}</code></pre>"
        f"<figcaption>{html_escape(block.title, quote=False)}</figcaption>"
        "</figure>"
    )


def book_html(assembled: list[AssembledPart]) -> str:
    """Join the parts into one document, with each diagram as a listing."""
    bodies = []
    for part in assembled:
        listings = {block.index: listing_markup(block) for block in part.blocks}

        def repl(match, listings=listings, stem=part.stem):
            index = int(match.group(1))
            if index not in listings:
                raise ValueError(f"{stem}.md: no diagram block for placeholder {index}")
            return listings[index]

        bodies.append(_DIAGRAM_PLACEHOLDER_RE.sub(repl, part.html))
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        f"<meta charset=\"utf-8\">\n<title>{TITLE}</title>\n</head>\n<body>\n"
        + "\n".join(bodies)
        + "\n</body>\n</html>\n"
    )


def book_identifier(title: str) -> str:
    """A ``urn:uuid`` derived from the title, so every build carries the same one."""
    return f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, title)}"


def book_metadata(date: str) -> str:
    """The pandoc metadata document: what epubcheck requires, and the rights.

    Values are written as single-quoted YAML scalars via `repr`, which is
    exact for these ASCII strings with no quote in them.
    """
    fields = {
        "title": TITLE,
        "creator": CREATOR,
        "lang": "en",
        "date": date,
        "identifier": book_identifier(TITLE),
        "rights": RIGHTS,
    }
    lines = [f"{key}: {value!r}" for key, value in fields.items()]
    return "---\n" + "\n".join(lines) + "\n---\n"


def epub_command(
    html_path: Path, metadata_path: Path, css_path: Path, out: Path
) -> list[str]:
    """The pandoc argv that turns the book document into an EPUB3."""
    return [
        "pandoc",
        "-f", "html+smart",
        "-t", "epub3",
        "--split-level=1",
        "--toc",
        "--toc-depth=2",
        "--metadata-file", str(metadata_path),
        "--css", str(css_path),
        "-o", str(out),
        str(html_path),
    ]  # fmt: skip
```

Add `"render_handbook_book",` to `known_first_party` in `pyproject.toml`, directly after `"render_handbook_artifact",`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/scripts/test_render_handbook_book.py tests/test_deptry_gate.py -v`
Expected: all pass.

- [ ] **Step 5: Lint and commit**

Run: `uv run ruff check . && uv run ruff format --check . && uv run deptry .`
Expected: clean. If either check reports the new files, run `uv run ruff check --fix scripts/render_handbook_book.py tests/scripts/test_render_handbook_book.py` (import order) and `uv run ruff format` on the same two files, then re-check.

```bash
git add scripts/render_handbook_book.py tests/scripts/test_render_handbook_book.py
git commit -m "The book's assembly: one document, the book link map, metadata

A bare part link lands on the part's first heading, because the book
emits no section wrapper for pandoc to split around. Diagrams stand in as
escaped listings until #190. The metadata carries what epubcheck needs
and names no copyright holder, which #188 has not settled.

Refs #189" -- scripts/render_handbook_book.py tests/scripts/test_render_handbook_book.py pyproject.toml
```

---

### Task 3: Build the EPUB from the CLI

**Files:**
- Modify: `scripts/render_handbook_book.py` (add `run_tool`, `build_epub`, `main`)
- Modify: `tests/scripts/test_render_handbook_book.py`
- Modify: `.gitignore` (add `build/`)
- Modify: `CLAUDE.md` (Commands section gains the EPUB command)

**Interfaces:**
- Consumes: everything Task 2 produces, and `render_handbook_artifact.assemble`, `heading_ids`, `PARTS`.
- Produces:
  - `run_tool(cmd: list[str], timeout: float, install_hint: str) -> None`, raising `SystemExit`.
  - `build_epub(docs_dir: Path, out: Path, date: str, parts: list[tuple[str, str, str]] = PARTS) -> Path`
  - `main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: Write the failing tests**

Add `import re`, `import shutil` and `import zipfile` to the import block at the top of `tests/scripts/test_render_handbook_book.py` (ruff's E402 applies to `tests/`, so an import appended mid-file fails lint), then append:

```python
REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / "docs" / "engineering"
needs_pandoc = pytest.mark.skipif(
    shutil.which("pandoc") is None,
    reason="pandoc CLI not installed; CI installs it (#192)",
)


def test_run_tool_names_a_missing_tool_and_how_to_install_it():
    with pytest.raises(SystemExit, match="no-such-tool-189.*brew install x"):
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


@pytest.fixture(scope="module")
def built_epub(tmp_path_factory) -> Path:
    pytest.importorskip("markdown")
    if shutil.which("pandoc") is None:
        pytest.skip("pandoc CLI not installed; CI installs it (#192)")
    out = tmp_path_factory.mktemp("epub") / "nested" / "handbook.epub"
    return rb.build_epub(DOCS, out, date="2026-09-28")


@needs_pandoc
def test_the_epub_carries_every_heading_id_the_page_carries(built_epub: Path):
    docs = _epub_documents(built_epub)
    in_book = set()
    for text in docs.values():
        in_book.update(re.findall(r' id="([^"]+)"', text))
    part_anchors = {anchor for anchor, _, _ in rh.PARTS}
    assert rh.heading_ids(DOCS) - part_anchors <= in_book


@needs_pandoc
def test_no_link_in_the_epub_points_at_a_markdown_file(built_epub: Path):
    for name, text in _epub_documents(built_epub).items():
        assert not re.search(r'href="[^"#]*\.md', text), name


@needs_pandoc
def test_every_part_is_a_chapter_in_page_order(built_epub: Path):
    docs = _epub_documents(built_epub)
    chapters = sorted(n for n in docs if re.search(r"ch\d+\.xhtml$", n))
    firsts = rb.first_heading_ids(DOCS, rh.PARTS)
    order = [firsts[stem] for _, stem, _ in rh.PARTS]
    found = []
    for name in chapters:
        for heading_id in order:
            if f'id="{heading_id}"' in docs[name]:
                found.append(heading_id)
    assert found == order


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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/scripts/test_render_handbook_book.py -v`
Expected: the new tests FAIL with `AttributeError: module 'render_handbook_book' has no attribute 'run_tool'` (or `build_epub` / `main`); the Task 2 tests still pass.

- [ ] **Step 3: Implement `run_tool`, `build_epub` and `main`**

Add to the imports of `scripts/render_handbook_book.py`:

```python
import argparse
import datetime
import os
import subprocess
import tempfile
```

and extend the `render_handbook_artifact` import with `assemble`. Then append:

```python
_PANDOC_TIMEOUT_S = 120
_PANDOC_HINT = "Install it with `brew install pandoc`, or see https://pandoc.org/installing.html."


def run_tool(cmd: list[str], timeout: float, install_hint: str) -> None:
    """Run one external tool, bounded, and turn every failure into a message.

    Raises:
        SystemExit: The tool is absent, did not finish within ``timeout``
            seconds, or exited non-zero; the message names the tool and, for
            a missing one, how to install it.
    """
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=timeout
        )
    except FileNotFoundError as exc:
        raise SystemExit(f"{cmd[0]} not found on PATH. {install_hint}") from exc
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(
            f"{cmd[0]} did not finish within {timeout}s. An unbounded call would "
            "hang the build with no diagnosis."
        ) from exc
    if proc.returncode != 0:
        raise SystemExit(
            f"{cmd[0]} failed (exit {proc.returncode}):\n{proc.stderr.strip()}"
        )


def build_epub(
    docs_dir: Path,
    out: Path,
    date: str,
    parts: list[tuple[str, str, str]] = PARTS,
) -> Path:
    """Write the EPUB for ``docs_dir`` to ``out`` and return ``out``."""
    linkmap = book_linkmap(parts, first_heading_ids(docs_dir, parts))
    html = book_html(assemble(docs_dir, parts, linkmap))
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / "book.html").write_text(html)
        (work / "metadata.yaml").write_text(book_metadata(date))
        (work / "epub.css").write_text(EPUB_CSS)
        cmd = epub_command(
            work / "book.html", work / "metadata.yaml", work / "epub.css", out
        )
        run_tool(cmd, _PANDOC_TIMEOUT_S, _PANDOC_HINT)
    return out


def _build_date() -> str:
    """``SOURCE_DATE_EPOCH`` when set, so a tagged build is reproducible."""
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        moment = datetime.datetime.fromtimestamp(int(epoch), tz=datetime.UTC)
    else:
        moment = datetime.datetime.now(tz=datetime.UTC)
    return moment.date().isoformat()


def main(argv: list[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--format", choices=["epub"], required=True)
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=repo_root / "docs" / "engineering",
        help="Directory holding the handbook markdown (default: docs/engineering).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path (default: build/handbook.epub, gitignored).",
    )
    args = parser.parse_args(argv)
    out = args.out or repo_root / "build" / "handbook.epub"
    build_epub(args.docs_dir, out, _build_date())
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Add to `.gitignore`, after the `test-reports/` block:

```
# Default output dir of scripts/render_handbook_book.py
build/
```

Add to CLAUDE.md's Commands block, directly after the `render_handbook_artifact.py` line:

```
uv run python scripts/render_handbook_book.py --format epub      # needs the pandoc CLI; writes build/handbook.epub
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/scripts/test_render_handbook_book.py -v`
Expected: all pass (the pandoc tests run, since pandoc is installed locally).

- [ ] **Step 5: Build the real EPUB and validate it**

Run:
```bash
uv run python scripts/render_handbook_book.py --format epub && (command -v epubcheck || brew install epubcheck) && epubcheck build/handbook.epub
```
Expected: `wrote .../build/handbook.epub`, then epubcheck reporting `No errors or warnings detected`. If epubcheck reports errors, fix their cause in `book_html`, `book_metadata` or `epub_command` with a test for each, and re-run. Record epubcheck's version and its final line for the PR body.

- [ ] **Step 6: Lint, full suite, commit**

Run: `uv run ruff check . && uv run ruff format --check . && uv run deptry . && uv run pytest tests/ -q`
Expected: clean, all pass.

```bash
git commit -m "render_handbook_book.py --format epub builds the handbook EPUB

pandoc reads the assembled HTML with smart quotes and splits a chapter
per part. Every external call is bounded and a missing tool names its
install command. Tests hold the EPUB to the page's heading ids, to no
link left at a .md file, and to one chapter per part in page order.

Refs #189" -- scripts/render_handbook_book.py tests/scripts/test_render_handbook_book.py .gitignore CLAUDE.md
```
