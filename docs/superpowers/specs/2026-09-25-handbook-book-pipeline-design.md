# The handbook book pipeline (#189, #190, #195)

**Status:** design approved in conversation on 2026-09-25. The book figures section was amended on 2026-09-28, after print previews of the diagrams: figures are committed files corrected by hand, placed at one scale. It was amended again on 2026-09-30, when the figures were redrawn in a design tool: every figure is transparent, and the one scale is set by the widest figure, 557 units, filling the text width.

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
   book figures                     one committed, hand-corrected SVG per diagram
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

The page keeps its diagrams as code. The book does not, because d2 and its ELK layout cannot place a figure well enough for print. Previews at the 5 x 8 trim on 2026-09-28 found three placements that none of the d2 settings tried could fix: an icon on a box costs the box its height even when the icon sits outside it; an edge returning to the top of a column pushes the nodes it joins off that column; and two edges leaving one shape split along its lower side, so neither enters the next shape at its centre. So each book figure is a committed SVG that a maintainer draws by hand, in an SVG editor or a design tool, starting from a seed the pipeline renders.

**Files.** Each diagram fence has one book figure at `docs/engineering/figures/<stem>-<index>.svg`, the index being the fence's position in its part. The EPUB and the paperback both use it. Where a fence has no committed figure, the build renders its seed in the figure's place and prints a note naming the fence, so a new diagram builds before its figure is drawn. The release workflow (#192) turns that note into a failure.

**Seed.** `render_handbook_book.py --seed-figures` writes the seed of every fence that has no committed figure, and never overwrites one. A d2 fence renders through `run_d2` with the `print` prelude and ELK, with the page's layout settings. The funnel fence draws through a vertical layout of `funnel_svg`: stages top to bottom, each label left of its band and each count inside it, because the horizontal layout prints its labels at about 4 pt. A seed is a starting point, not reproducible output, drawn at d2's own label size of 12 units rather than at the book's one scale, so it prints small until it is redrawn and a seed committed as it stands fails the size check. The seed step also prepares the file for editing:

- d2 embeds Source Sans Pro as WOFF data that neither SVG editors nor Typst read, which is why the previews fell back to a serif. The seed removes the embedded faces and names Source Sans 3, the family's current name, in plain `font-family` attributes, which an editor resolves from an installed font.
- d2's salted ids and generated class names are replaced with readable ones, so the file opens cleanly and a hand edit reads as a small diff.

**Drift.** Each committed figure carries the SHA-256 of the fence body it was drawn from, as `data-source-sha256` on its root `<svg>`. A test fails when a fence body no longer matches its figure's hash, so a fence edited after its figure was drawn cannot ship a stale figure. Redrawing the figure, or confirming it still holds, updates the hash.

**One scale.** Every figure is placed at one scale: 1 SVG user unit to about 0.465 pt, or 0.0065 inch (`PT_PER_UNIT`), so lettering drawn at one size prints at one size in every figure. The scale is set so the widest figure, 557 units (`FULL_WIDTH_UNITS`), fills the text block's width, and every other figure is scaled by the same factor rather than fitted to the width on its own. A figure is never stretched to the text width. Fitting each figure to the width, as the previews did, printed a small figure's labels larger than a large one's. At that scale a figure must fit the text block, 3.6 x 6 inches (`TEXT_BLOCK_PT`), which bounds its viewBox at 557 x about 928 units (`MAX_VIEWBOX`). Each figure's viewBox is its drawing's full extent, cropped by the maintainer, and is placed as it stands. A figure that does not fit is redrawn narrower, never shrunk. A label in live text is held to 7 to 9 pt, which is about 15 to 19.3 units. In the EPUB the same scale is expressed relative to the body font, as a width of `<viewBox width> x PT_PER_UNIT / 10` em with `max-width: 100%`, so labels keep their ratio to the text when a reader changes the font size. The stylesheet also caps a figure image a little below the page's height, so a figure taller than a reader's page shrinks to leave its caption room on that page rather than pushing it to the next. Vertical space belongs to the hand pass: the maintainer compresses a figure wherever its gaps carry nothing.

**Palette.** A book figure paints no opaque surface. The page palette fills every d2 shape with its `surface` colour and draws each funnel stage on a `surface` rectangle, and on cream paper those print as pale rectangles on a warm page. So shape fills and the background are transparent, and any tint a figure needs is a translucent overlay at an effective opacity of 0.2 or less: the funnel's wash is the accent at 0.15 opacity. Ink and accent come from the light palette; `line` is darkened for print to `#8a867a`, which holds 3.2:1 on the cream paper where the page's hairline does not. The figure stays legible when the colour is dropped, which serves e-ink screens and paper alike, because every text fill holds 4.5:1 and every stroke 3:1 in luminance contrast against the paper, each paint blended over the paper at its effective opacity first, an `rgba()` colour's own alpha included. A stroke at an effective opacity of 0.2 or less is texture, such as a hand-drawn figure's faint shading, and is not held to the bar. That contrast is the whole grayscale check: nothing compares one fill or stroke against another.

**Dark mode.** Every copy of a figure is transparent: the committed file, the EPUB's copy and the paperback's. On paper and in a reading system's light and sepia themes the page colour shows through, as the cream paper does in print. In a reading system's night theme the figure's dark ink meets a dark page and is hard to read, because reading systems do not invert images; that cost is accepted rather than paid for with a panel that would print as a pale rectangle wherever the same drawing is reused.

**Markup.** Each figure is written to a temporary media directory as `<stem>-<index>.svg` and referenced as:

```html
<figure><img src="media/<stem>-<index>.svg" alt="<title>"><figcaption><title></figcaption></figure>
```

The caption is the fence's `title`, escaped. SVG serves both formats: it is native to EPUB3, and Typst embeds it as vector, so the 300 DPI minimum for raster images never applies.

**Fonts.** d2 embeds Source Sans Pro, licensed under the SIL Open Font License 1.1 with an `fsType` of 0, read with fontTools from the embedded faces on 2026-09-28. Embedding it in a distributed book is permitted, so no replacement is needed. The regular, bold and italic faces of Source Sans 3 are committed unmodified under `fonts/source-sans-3/` with the licence, from Adobe's release, so every build uses the same files. A figure whose lettering is converted to outlines, as a design tool's export does, uses no font and embeds none, and the size check has no text to read in it. A figure in live text names the font in its committed file and does not carry it. The EPUB copy does carry it, because an SVG an `<img>` references cannot reach the book's other files, and a reading system's fallback font sets wider and would push labels out of their boxes: the build embeds each face the figure uses, subset with fontTools to the glyphs it uses, as d2 does. The paperback build passes the committed files to Typst with `--font-path`. The book's text is set in the same family's companions, decided by the maintainer on 2026-09-30 (#210): Source Serif 4 for body text, Source Sans 3 for headings, Source Code Pro for code, each committed unmodified under `fonts/` with its licence and embedded whole in the EPUB, with the stylesheet naming each ahead of a generic fallback for a reading system that ignores publisher fonts.

### 3. The book builder (#189, #195)

A new `scripts/render_handbook_book.py`, with one entry point, a `--format` flag, and a `--seed-figures` flag (section 2 describes it):

- **`--format epub`** writes `build/handbook.epub`. It runs `pandoc -f html -t epub3 --split-level=1 --toc --toc-depth=1` with a metadata file, `--css` pointing at a book stylesheet, and `--resource-path` pointing at the media directory. The metadata carries title, creator (Janos Tolgyesi), `lang: en`, rights (CC BY 4.0), date, and an identifier `urn:uuid:<uuid5 of the title>`, so the identifier stays stable across builds. This covers what `epubcheck` requires; #191 adds the cover, the title and copyright pages, and the rest of the metadata.
- **`--format pdf`** writes `build/handbook-interior.pdf`. It runs `pandoc -f html -t typst` with a Typst template, then `typst compile`. The quotes arrive already curled by `curl_quotes`, which #189 added because pandoc's `+smart` also rewrites inline code; without curled quotes pandoc escapes `"` for Typst and the book prints straight quotes, which the preview showed. The template sets:
  - the trim size, 5 x 8 inches;
  - mirrored margins with a gutter meeting KDP's minimum for the page count;
  - every part starting on a recto page;
  - a table of contents with page numbers;
  - in-book links printed as page references;
  - external links with their URL printed after the link text;
  - table cells set ragged-right rather than justified;
  - a line-breaking rule for long inline code.
- **`--format cover`** writes `build/handbook-cover.pdf`. It reads the interior's page count, computes the spine width, and lays out back, spine and front with 0.125 inch bleed on every side. Spine text is printed only above KDP's minimum page count for it.

`--out` overrides the output path. `build/` joins `.gitignore`.

### 4. Pure functions the tests hold

- `book_linkmap(parts, first_ids)` builds the book's link map.
- `figure_markup(stem, block, width_em)` builds a figure's HTML.
- `source_hash(source)` returns the SHA-256 a committed figure records.
- `fit_problems(svg)` holds a figure's viewBox and text sizes to the one scale.
- `opaque_fill_problems(svg, paper)` reports a fill that would print as a pale surface.
- `contrast_problems(svg, paper)` holds every text fill and stroke to its contrast bar against the paper.
- `embed_fonts(svg, font_dir)` embeds each face the figure's text uses, subset to it.
- `book_metadata(...)` builds the metadata document.
- `spine_width(pages, paper)` returns the spine width in inches, from KDP's per-page thickness for the paper type. It raises on a page count outside KDP's supported range.
- `cover_dimensions(trim, pages, paper)` returns the full cover width and height, with bleed.

## Error handling

A missing external tool (`pandoc`, `d2`, `typst`, `epubcheck`) raises `SystemExit` naming the tool and its install command, as `run_d2` already does. Every subprocess call is bounded by a timeout, for the reason `run_d2` gives. A pandoc or Typst failure raises with the tool's stderr. The unmapped-link and id-collision raises come from `assemble`, so the book builds under the same rules as the page. There is no warning-only path for a dead link.

## Testing

- **Unit tests** over every pure function above, in `tests/scripts/`.
- **Id parity.** A test opens the built EPUB, collects every `id` in its XHTML documents, and holds the set of heading ids equal to `heading_ids(docs_dir)` minus the part anchors, which the book deliberately does not emit. For the PDF, parity holds through `assemble`, because the same HTML feeds both formats; the test asserts that the Typst source names every heading id as a label.
- **No `.md` link survives** in any EPUB document.
- **Figure count.** The EPUB carries exactly one image per diagram fence in the source, and so does the Typst source. The count is of images, not figures, because pandoc wraps tables in Typst figures too. No diagram fence survives as a code listing.
- **Committed figures.** Every committed figure names a fence that exists, carries the hash of that fence's body, fits the text block at the one scale with every text size between 7 and 9 pt, and paints no opaque fill on a shape or background. Every EPUB copy stays transparent, holding the same opaque-fill check, and embeds the faces its text uses.
- **Spine width** against KDP's published values at a few page counts.
- **`epubcheck`** runs locally on the built EPUB, and its clean result is recorded in the #189 and #190 pull requests. CI takes it over in #192.
- **KDP's previewer** on the interior and cover PDFs is a manual step, recorded in #195.

Tests that need `pandoc`, `d2` or `typst` skip with a stated reason when the tool is absent, so the existing suite stays runnable where only Python is installed. CI (#192) installs the tools, so the skip does not happen there.

## Delivery

Three pull requests, in dependency order:

1. **#189:** the `assemble` refactor with its byte-identity test, `render_handbook_book.py --format epub`, the book link map, metadata, stylesheet, and `.gitignore`. Diagrams render as listings until #190.
2. **#190:** the `print` prelude, the vertical funnel, `--seed-figures`, the committed figures drawn by hand, the committed font files, the figure markup, the EPUB's embedded fonts, the contrast check against the paper, the font-licence finding, and the drift, scale, transparency and figure-count tests.
3. **#195:** the Typst template, `--format pdf` and `--format cover`, the spine computation, and the manual previewer step.

Each pull request adds its command to CLAUDE.md's Commands section. Any new module in `scripts/` joins `[tool.deptry] known_first_party`.

## Decisions

- **Pandoc reads the renderer's HTML, not the Markdown,** so the ids and links are the page's by construction. #189's body names `pandoc -f gfm`; this spec supersedes that line, and the #189 pull request records it.
- **Typst over LaTeX for the PDF.** It is a single binary, much lighter than a TeX distribution, embeds SVG natively, and pandoc 3.8 writes it. Install with `brew install typst` locally; #192 pins a version.
- **SVG for every figure** in both formats, so one file serves both and print needs no raster step.
- **Book figures are committed and corrected by hand**, decided by the maintainer on 2026-09-28 after the print previews: the d2 and ELK placements above are not acceptable in print, and none of the d2 settings tried fixed them. d2 only seeds a figure; the page keeps rendering its diagrams from code. A per-diagram layout engine, dagre for the data-protection figure, was tried the same day and rejected: it centred one edge and loosened every gap, and the hand pass fixes the edge without either cost.
- **One scale for every figure**, 8 pt labels at 2/3 pt per user unit, decided by the maintainer on 2026-09-28, because fitting each figure to the text width printed labels from about 7 to 10 pt across figures.
- **The figures are drawn in a design tool, and the one scale follows them**, decided by the maintainer on 2026-09-30, who found the SVG editor hand pass too slow and redrew every figure in Claude Design, in a hand-drawn style with outlined lettering, then cropped each export to its drawing, the widest at 557 units. The maintainer chose one scale for every figure, set so that 557 units fills the 3.6 inch text width, over fitting each figure to the width on its own, which would vary the lettering between figures. At that scale, measured from each label style's tallest outline, box labels print at about 9 pt and edge labels at about 8 pt, both above the 7 pt floor. A first export, up to 680 units wide, was placed at 0.38 pt per unit for one commit, which put the edge labels under that floor.
- **Every figure is transparent, the EPUB's included.** Decided by the maintainer on 2026-09-30. An opaque light panel behind the EPUB copy had kept dark ink legible in a reading system's night theme; the maintainer chose one transparent drawing for every format instead, accepting that figures read poorly in a night theme.
- **Trim size 5 x 8 inches.** Decided by the maintainer on 2026-09-28, for a pocket-manual feel. It is the smallest trim KDP offers for a paperback, so a true pocket size would need another printer. A throwaway typesetting run on 2026-09-28 (pandoc to Typst 0.15.1, 10 pt Libertinus Serif, parts on recto pages, four front-matter pages and the table of contents) came to 115 pages at this size, against 85 at 6 x 9. The #195 pull request records the count of the final build.
- **The narrow text block has costs the template has to meet.** About 3.6 inches of text width forces three things, and the same run showed which of them bite. The 4- and 5-column tables fit at 8 pt, but justified cell text spaces badly, so table cells are set ragged-right. The wide left-to-right diagrams are not legible: the story-of-a-change figure's labels print at about 4 pt, so its book figure is drawn top to bottom. Long inline code needs a line-breaking rule. The diagrams belong to #190; the tables and inline code to #195, each pull request recording its choice.
- **Black and white on cream paper.** Decided by the maintainer on 2026-09-28, after comparing a white and a simulated cream preview. Cream is warmer and has less glare for a book read cover to cover. It costs two things the design absorbs: the figures carry transparent fills, and the spine uses KDP's cream-paper thickness, which is greater than white's. The paper type is a template parameter, so `spine_width` takes it as an argument rather than assuming one.
- **`epubcheck` from Homebrew** locally. #192 chooses how CI obtains it.
