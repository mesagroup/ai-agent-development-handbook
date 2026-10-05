// The paperback interior: 5 x 8 in, a 3.6 x 6 in text block, black on cream.
//
// `render_handbook_book.py --format pdf` copies this file beside pandoc's
// Typst body and a main file that applies `interior` to it. The publication
// details arrive as `typst compile --input` strings, read with `sys.inputs`
// and printed as text, never evaluated, so a value carrying Typst syntax
// prints as written. A detail not decided yet arrives as its bracketed
// placeholder (`book_publication.PLACEHOLDERS`).

#let detail(key) = sys.inputs.at(key)

#let title = "AI Agent Development Handbook"
#let author = "Janos Tolgyesi"

// Half-title, its blank verso, the title page and the copyright page, then the
// contents on a recto. None of them carries a page number. #191 owns the
// wording of the title and copyright pages; these lines carry what #188
// decided and a placeholder for what it has not.
#let front-matter() = {
  set page(numbering: none, footer: none)
  align(center + horizon, text(font: "Source Sans 3", weight: "bold", 14pt, title))
  pagebreak()
  pagebreak()
  align(center + horizon, {
    text(font: "Source Sans 3", weight: "bold", 20pt, title)
    v(1.5em)
    text(12pt, author)
  })
  pagebreak()
  {
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
  }
  pagebreak(to: "odd")
  outline(title: "Contents", depth: 1)
}

#let interior(body) = {
  set document(title: title, author: author)
  // The margins leave exactly the text block the figures are scaled to
  // (`book_figures.TEXT_BLOCK_PT`); `INTERIOR_MARGINS_IN` in the builder
  // states the same numbers, and a test holds the two together.
  set page(
    width: 5in,
    height: 8in,
    margin: (inside: 0.75in, outside: 0.65in, top: 0.875in, bottom: 1.125in),
  )
  // Source Sans 3 stands in only for the marks Source Serif 4 lacks
  // (● ○ ↔), so no face outside fonts/ is ever used.
  set text(font: ("Source Serif 4", "Source Sans 3"), size: 9.5pt, lang: "en", hyphenate: true)
  set par(justify: true, leading: 0.55em)
  show heading: set text(font: "Source Sans 3", weight: "bold", hyphenate: false)
  show heading: set par(justify: false)
  show heading: set block(sticky: true)
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
  // Table cells are set ragged-right and never hyphenated: the measure is
  // narrow, and justified cell text spaces badly.
  show table.cell: set par(justify: false)
  show table.cell: set text(hyphenate: false)
  show figure: set block(breakable: false)
  show figure.caption: set text(8pt, style: "italic")
  // An in-book link prints its page; an external one prints its URL in a
  // footnote, since a URL inline in a 3.6 in measure breaks lines badly.
  show link: it => {
    if type(it.dest) == label {
      it.body
      [ (p.~#context counter(page).at(it.dest).first())]
    } else if type(it.dest) == str {
      it.body
      footnote(raw(it.dest))
    } else {
      it
    }
  }
  // A checklist arrives as a block labelled `checklist-<n>`
  // (`restore_task_boxes`): it draws its box in place of the bullet, and the
  // box has a fixed width so justification never moves the text after it.
  show block: it => {
    let name = if it.has("label") { str(it.label) } else { "" }
    if name.starts-with("checklist-") {
      set list(marker: none, body-indent: 0pt)
      it
    } else {
      it
    }
  }
  show regex("[☐☒]"): box.with(width: 1.2em)
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
  context [#metadata(here().page()) <page-count>]
}

// pandoc's Typst writer emits `#horizontalrule` for an <hr>.
#let horizontalrule = line(length: 100%, stroke: 0.5pt)
