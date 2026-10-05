// The paperback's wraparound cover: back, spine and front on one page, with
// bleed on every outside edge.
//
// `render_handbook_book.py --format cover` passes every length as a
// `typst compile --input` string in inches (`cover_inputs`), sized from the
// interior's page count with KDP's formula (`kdp_print`), and the details as
// text or their placeholders. A value is printed, never evaluated.

#let input(key) = sys.inputs.at(key)
#let inches(key) = float(input(key)) * 1in

#let title = "AI Agent Development Handbook"
#let author = "Janos Tolgyesi"

#let width = inches("width")
#let height = inches("height")
#let bleed = inches("bleed")
#let trim-w = inches("trim-width")
#let spine = inches("spine")
#let safe = inches("safe")

// The panels' left edges, measured from the page's, bleed included.
#let back-x = bleed
#let spine-x = bleed + trim-w
#let front-x = bleed + trim-w + spine

#set page(width: width, height: height, margin: 0pt, fill: white)
#set text(font: "Source Serif 4", size: 10pt, lang: "en")

// Front: the art to the bleed where #191 supplies it, else typographic.
#if input("cover-art") != "" {
  place(top + left, dx: front-x, image(input("cover-art"), width: width - front-x, height: height, fit: "cover"))
} else {
  place(top + left, dx: front-x + safe, dy: bleed + safe,
    block(width: trim-w - 2 * safe, height: height - 2 * (bleed + safe), {
      v(1.4in)
      set par(justify: false)
      text(font: "Source Sans 3", weight: "bold", 24pt, title)
      v(1fr)
      // Measured to the descenders, so they stay inside the safe area too.
      text(13pt, bottom-edge: "descender", author)
    }))
}

// Spine: the title and author, reading top to bottom, only where KDP allows
// spine text and the line fits between the fold margins, at the size
// `cover_inputs` chose for it.
#if input("spine-text") == "true" {
  let margin = inches("spine-margin")
  place(top + left, dx: spine-x + margin, dy: bleed + safe,
    block(width: spine - 2 * margin, height: height - 2 * (bleed + safe),
      align(center + horizon, rotate(90deg, reflow: true,
        text(font: "Source Sans 3", weight: "bold", float(input("spine-text-size")) * 1pt)[#title #h(1.5em) #text(weight: "regular", author)]))))
}

// Back: the back-cover text inside the safe area.
#place(top + left, dx: back-x + safe, dy: bleed + safe,
  block(width: trim-w - 2 * safe, {
    v(0.6in)
    set par(justify: false, leading: 0.6em)
    text(11pt, input("back-cover-text"))
  }))

// KDP prints the barcode for its own ISBN in this area at the back's bottom
// right; it stays clear. Until the ISBN is set, the proof outlines it.
#let barcode-w = inches("barcode-width")
#let barcode-h = inches("barcode-height")
#let barcode-margin = inches("barcode-margin")
#place(top + left,
  dx: spine-x - barcode-margin - barcode-w,
  dy: height - bleed - barcode-margin - barcode-h,
  if input("isbn-set") == "true" {
    rect(width: barcode-w, height: barcode-h, fill: white, stroke: none)
  } else {
    rect(width: barcode-w, height: barcode-h, stroke: 0.5pt + gray,
      align(center + horizon, text(font: "Source Sans 3", 8pt, fill: gray)[\[Barcode area\]]))
  })
