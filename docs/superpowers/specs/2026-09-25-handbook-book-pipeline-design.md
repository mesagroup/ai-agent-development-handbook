# The handbook book pipeline (#189, #190, #195)

**Status:** design approved in conversation on 2026-09-25; this written spec awaits the maintainer's review.

## Problem

O8 publishes the handbook as a free EPUB on a public GitHub release and as a print-on-demand paperback on KDP. #188 settled the channels, the licence (CC BY 4.0) and the author. Three issues build the files: #189 the EPUB, #190 its figures, #195 the paperback's interior and wraparound cover. They share everything up to the output stage, so one design covers all three, and each issue lands as its own pull request.

The constraint that shapes the design is the citation contract. Every heading on the rendered page carries `id="<stem>-<slug>"`, and every citation a report emits is written against those ids. O8's reached clause requires the book to carry the same ids, so a reader holding the book can follow a citation exactly as a reader holding the page can.

## Out of scope

- The release workflow (#192). This design gives it one command per format to run.
- The front-cover art and the front-matter wording (#191). This design lays out whatever #191 supplies and uses a typographic placeholder until then.
- The copyright holder and the location of the public release, both deferred in #188. The copyright page carries a placeholder.
- The prose itself (#193).

## Approach: pandoc reads the page renderer's HTML

Three ways to reach pandoc were weighed.

1. **Pandoc reads the HTML the page renderer already produces.** `render_handbook_artifact.py` turns each part into HTML, gives every heading its `<stem>-<slug>` id, rewrites sibling `.md` links to in-page fragments, unlinks the one out-of-tree link, and lifts the diagram fences out. Feeding that HTML to pandoc makes the book's ids and links the page's by construction.
2. **Pandoc reads the Markdown, and a Lua filter re-implements the ids and the link rewrite.** The logic then lives twice, in two languages, and a test has to hold the two together.
3. **Pandoc reads the Markdown and assigns its own ids.** This breaks every citation. Rejected.

The first is chosen. A spike on 2026-09-25 ran every part through `render_part` and `post_process` and gave the result to `pandoc -f html -t epub3 --split-level=1`. It produced 13 chapters, no link left pointing at a `.md` file, the page's heading ids unchanged, and 242 in-book links resolving across the chapter split. By contrast, a direct `pandoc -f gfm` conversion left 183 links pointing at `.md` files and emitted explicit ids on only a few headings.

The spike also found the one adjustment the book needs. The page wraps each part in `<section id="p1">` and links to a part by that anchor. Pandoc splits chapters on the part's `<h1>`, and a wrapper section stops the split. So the book emits no wrapper and maps a part link to that part's first heading id instead.

## Architecture

```
docs/engineering/*.md
        |
   assemble()                       shared with the page renderer
        |  per part: HTML with ids and rewritten links, diagram blocks
        |
   book figures                     one print-safe SVG per diagram
        |
   book HTML (one document)
        |
   +----+------------------+
   |                       |
 pandoc -t epub3      pandoc -t typst -> typst compile
   |                       |
 build/handbook.epub  build/handbook-interior.pdf
                           |  page count
                      cover builder
                           |
                      build/handbook-cover.pdf
```

### 1. Shared assembly (#189)

The first half of `build()` in `render_handbook_artifact.py` becomes `assemble(docs_dir, parts, linkmap)`. It returns one record per part, carrying the anchor, the stem, the HTML with heading ids and rewritten links, and the diagram blocks. The unmapped-link and id-collision raises move with it, so both callers inherit them. `build()` calls `assemble` with the page's link map and keeps its own figure substitution, section wrapping and page chrome.

The refactor must not change the page. A test renders the page before and after with diagram rendering stubbed, and asserts the two outputs are byte-identical.

The book passes its own link map: `<stem>.md` maps to `#<first heading id of that part>` instead of `#<part anchor>`. A fragment link `<stem>.md#<frag>` already maps to `#<stem>-<frag>` and needs no change.

### 2. Book figures (#190)

Each diagram block renders once, in a new `print` variant, rather than twice for the page's light and dark toggle. The variant starts from the light palette and is checked for grayscale contrast: every fill and stroke pair a figure relies on stays distinguishable when the colour is dropped. That serves e-ink screens and paper alike. d2 blocks go through `run_d2` with a `print` prelude, and funnel blocks through `funnel_svg` with the `print` variant.

Each SVG is written to a temporary media directory as `<stem>-<index>.svg` and referenced as:

```html
<figure><img src="media/<stem>-<index>.svg" alt="<title>"><figcaption><title></figcaption></figure>
```

The caption is the fence's `title`, escaped. SVG serves both formats: it is native to EPUB3, and Typst embeds it as vector, so the 300 DPI minimum for raster images never applies. This is the vector output #190's triage note asks the figure step to keep.

Fonts: d2 embeds its own font faces in the SVG. The implementation confirms their licence permits embedding in a distributed book, and replaces them with a font that does if not. The result is recorded in the #190 pull request.

### 3. The book builder (#189, #195)

A new `scripts/render_handbook_book.py`, with one entry point and a `--format` flag:

- **`--format epub`** writes `build/handbook.epub`. It runs `pandoc -f html -t epub3 --split-level=1 --toc --toc-depth=2` with a metadata file, `--css` pointing at a book stylesheet, and `--resource-path` pointing at the media directory. The metadata carries title, creator (Janos Tolgyesi), `lang: en`, rights (CC BY 4.0), date, and an identifier `urn:uuid:<uuid5 of the title>`, so the identifier stays stable across builds. This covers what `epubcheck` requires; #191 adds the cover, the title and copyright pages, and the rest of the metadata.
- **`--format pdf`** writes `build/handbook-interior.pdf`. It runs `pandoc -f html -t typst` with a Typst template, then `typst compile`. The template sets:
  - the trim size, 5 x 8 inches;
  - mirrored margins with a gutter meeting KDP's minimum for the page count;
  - every part starting on a recto page;
  - a table of contents with page numbers;
  - in-book links printed as page references;
  - external links with their URL printed after the link text.
- **`--format cover`** writes `build/handbook-cover.pdf`. It reads the interior's page count, computes the spine width, and lays out back, spine and front with 0.125 inch bleed on every side. Spine text is printed only above KDP's minimum page count for it.

`--out` overrides the output path. `build/` joins `.gitignore`.

### 4. Pure functions the tests hold

- `book_linkmap(parts, first_ids)` builds the book's link map.
- `figure_markup(stem, block)` builds a figure's HTML.
- `book_metadata(...)` builds the metadata document.
- `spine_width(pages, paper)` returns the spine width in inches, from KDP's per-page thickness for the paper type. It raises on a page count outside KDP's supported range.
- `cover_dimensions(trim, pages, paper)` returns the full cover width and height, with bleed.

## Error handling

A missing external tool (`pandoc`, `d2`, `typst`, `epubcheck`) raises `SystemExit` naming the tool and its install command, as `run_d2` already does. Every subprocess call is bounded by a timeout, for the reason `run_d2` gives. A pandoc or Typst failure raises with the tool's stderr. The unmapped-link and id-collision raises come from `assemble`, so the book builds under the same rules as the page. There is no warning-only path for a dead link.

## Testing

- **Unit tests** over every pure function above, in `tests/scripts/`.
- **Id parity.** A test opens the built EPUB, collects every `id` in its XHTML documents, and holds the set of heading ids equal to `heading_ids(docs_dir)` minus the part anchors, which the book deliberately does not emit. For the PDF, parity holds through `assemble`, because the same HTML feeds both formats; the test asserts that the Typst source names every heading id as a label.
- **No `.md` link survives** in any EPUB document.
- **Figure count.** The EPUB carries exactly one image per diagram fence in the source, and the Typst source one figure per fence.
- **Spine width** against KDP's published values at a few page counts.
- **`epubcheck`** runs locally on the built EPUB, and its clean result is recorded in the #189 and #190 pull requests. CI takes it over in #192.
- **KDP's previewer** on the interior and cover PDFs is a manual step, recorded in #195.

Tests that need `pandoc`, `d2` or `typst` skip with a stated reason when the tool is absent, so the existing suite stays runnable where only Python is installed. CI (#192) installs the tools, so the skip does not happen there.

## Delivery

Three pull requests, in dependency order:

1. **#189:** the `assemble` refactor with its byte-identity test, `render_handbook_book.py --format epub`, the book link map, metadata, stylesheet, and `.gitignore`. Diagrams render as listings until #190.
2. **#190:** the `print` variant, figure files and markup, the grayscale check, the font-licence finding, and the figure-count test.
3. **#195:** the Typst template, `--format pdf` and `--format cover`, the spine computation, and the manual previewer step.

Each pull request adds its command to CLAUDE.md's Commands section. Any new module in `scripts/` joins `[tool.deptry] known_first_party`.

## Decisions

- **Pandoc reads the renderer's HTML, not the Markdown,** so the ids and links are the page's by construction. #189's body names `pandoc -f gfm`; this spec supersedes that line, and the #189 pull request records it.
- **Typst over LaTeX for the PDF.** It is a single binary, much lighter than a TeX distribution, embeds SVG natively, and pandoc 3.8 writes it. Install with `brew install typst` locally; #192 pins a version.
- **SVG for every figure** in both formats, so one render serves both and print needs no raster step.
- **Trim size 5 x 8 inches.** Decided by the maintainer on 2026-09-28, for a pocket-manual feel. It is the smallest trim KDP offers for a paperback, so a true pocket size would need another printer. A throwaway typesetting run on 2026-09-28 (pandoc to Typst 0.15.1, 10 pt Libertinus Serif, parts on recto pages, four front-matter pages and the table of contents) came to 115 pages at this size, against 85 at 6 x 9. The #195 pull request records the count of the final build.
- **The narrow text block has costs the template has to meet.** About 3.6 inches of text width forces three things, and the same run showed which of them bite. The 4- and 5-column tables fit at 8 pt, but justified cell text spaces badly, so table cells are set ragged-right. The wide left-to-right diagrams are not legible: the story-of-a-change figure's labels print at about 4 pt, so a wide diagram gets a top-to-bottom layout in the `print` variant. Long inline code needs a line-breaking rule. The #195 pull request settles each and records the choice.
- **Black and white on white paper.** Assumed on 2026-09-25 and not yet confirmed by the maintainer. White paper keeps the spine formula at KDP's white-paper thickness. The paper type is a template parameter, so changing it is a one-line edit.
- **`epubcheck` from Homebrew** locally. #192 chooses how CI obtains it.
