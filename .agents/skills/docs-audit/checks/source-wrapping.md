---
id: docs/source-wrapping
domain: docs
locality: global
evidence: >-
  One row per paragraph that occupies more than one source line, evidenced by
  the file and the line range the paragraph spans, so the fix is a rejoin of
  named lines rather than a reformat of the file. A row also records which
  block kind the paragraph sits in - top level, a list item, a block quote -
  because the rejoin differs: a continuation line inside a list item carries
  the item's indentation and a naive join produces a different document. A
  whole-file verdict is deliberately not the unit; it hides which paragraph to
  fix and reads as an instruction to reformat everything.
handbook:
  - documentation/house-rule-dont-hard-wrap-markdown-source
---

# Source wrapping

Whether each prose paragraph in the documentation source occupies **one line**, leaving the wrapping to the renderer. The finding is a paragraph that spans more than one source line. What this buys is the diff: in a hard-wrapped tree a one-word edit reflows the paragraph around it, so every small change arrives as a multi-line hunk and a reviewer cannot tell a typo fix from a rewrite. It also reads correctly in the editors and review tools that soft-wrap, which a column-wrapped source does not.

Conformance is decidable from the source bytes, with no reading and no judgment - which is what makes this a check rather than a convention the domain merely states.

## What counts as a paragraph, and what does not

**CommonMark's own block structure decides.** A paragraph inside a list item or a block quote is a paragraph, and its continuation lines count exactly as a top-level paragraph's do. Resolve the blocks with a Markdown parser where the project has one available rather than with a line regex: a regex cannot tell a paragraph's second line from a lazy continuation, a setext heading's underline, or a line inside a fence, and each of those misreadings produces a finding on conforming source.

**An explicit hard break is not a finding.** A line ending in two spaces, or in a backslash, is a line break the author asked the renderer to honour. That is the opposite of a paragraph wrapped to a column - the author wants the break to survive rendering - so a paragraph whose internal line endings are all explicit breaks conforms.

**Non-paragraph blocks are out of scope by construction**, because their line structure is content rather than formatting: fenced and indented code, tables, YAML front matter, HTML blocks, link reference definitions, headings and thematic breaks. A table's rows and a code block's lines mean what they are; joining them changes the document.

**Some of those are not CommonMark constructs, so no parser excludes them for you.** The base specification defines neither tables nor front matter. A pipe table is a GFM extension and parses as an ordinary multi-line paragraph without it; a leading `---` block parses as a thematic break followed by a paragraph whose closing `---` turns it into a setext heading. A plain CommonMark parse therefore reports both as findings on conforming source, and the rejoin this record prescribes as the fix would destroy a table and swallow the front matter. Enable the parser's table and front-matter extensions, or, where it has neither, strip the front-matter block and every table by their own syntax before the paragraph scan. Say in the row which of the two you did, because a reader cannot tell a tree with no tables from a scan that never saw them.

**That is one instance of the trap, and enumerating the instances is not the guard.** A construct whose meaning depends on where its lines break, and which the parser does not model, reads as an ordinary wrapped paragraph however many extensions are enabled - and the rejoin then damages the document rather than merely misreporting it, which no other misreading in this record does. A GitHub alert is the instance a table-and-front-matter parse still misses: `> [!NOTE]` and the line beneath it are one paragraph with a soft break inside a block quote, so every alert spans more than one source line even when its body is unwrapped, and joining it folds the label into the text and the alert stops being one. So the guard is per paragraph rather than per construct: before reporting, confirm that no line in the paragraph opens with a marker that loses its meaning anywhere but at the start of a line - a pipe-delimited row, an alert label, a front-matter key, a directive or admonition marker from whatever flavour the docs use. A paragraph this check is not equipped to judge is **`no-evidence (tool-unavailable)`**, naming the flavour and the parser that does not model it - that is the reason a reader can act on, because what answers it next time is a parser that models the flavour. It is not a third value on this domain's `ok` / `warn` / `violation` scale: the scale every domain shares is fixed and does not grow - see `audit-core` - so inventing a status here would collapse the distinction those two exist to draw.

## The finding is never that a line is too long

This check and a line-length rule are opposites wearing the same clothes, and confusing them is the way it goes wrong once someone wires a tool in. `markdownlint`'s `MD013` enforces a maximum line length, so it fails a conforming tree on every paragraph long enough to be worth reading, and a tree that satisfies it is hard-wrapped by construction. **Name the finding by the paragraph, never by the line**, and where a project already runs a Markdown linter, check whether its configuration enables a line-length rule - that is a conflicting convention and belongs in the row rather than being silently overruled.

## Why this is answered once over the whole tree

The subject is the documentation tree, which no code-tier partition slices, so there is no partition to give this check a slice of. It is answered in one pass over the tree. That is a statement about where its subject lives, not a claim that it needs a cross-file property: each file is decidable on its own, which is why fanning it out per agent would duplicate the read for no gain.

## Severity

**Minor** - a paragraph occupying more than one source line. That is the whole of the tier scale here, and deliberately so. The cost this clause names is review legibility and diff noise; nothing about it is a correctness, availability or security question, so there is no evidence on which this check could raise an Important. A tree that is hard-wrapped throughout is many minor rows rather than one severe one, because the fix is per paragraph and so is the evidence.

**A project that has chosen the opposite convention is what Minor is for.** Where a contributor guide or a linter configuration states a column limit, say so in the row: the project has made a decision this clause disagrees with, and reporting it as a defect at any higher tier would be this check overruling a convention rather than recording the distance from the handbook's.

## Tooling fallback

No tool answers this as asked, so read the source. `markdownlint`'s `MD013` is the opposite rule and must not be substituted - see above. Resolve the blocks with whatever CommonMark parser the project already has (a docs site's own renderer, a Markdown library in the test environment), with its table and front-matter extensions enabled for the reason above.

**This section says what to run. It does not say what counts as a finding, and it deliberately does not restate the rule that does.** That rule is `What counts as a paragraph, and what does not` above, and it is one rule rather than a headline with qualifications: the hard-break exception and the per-paragraph marker guard are clauses of it, not footnotes to it. The separation is here because a paraphrase in this section is the form an agent actually runs, so every clause a paraphrase drops becomes a conforming paragraph reported and then joined - and this record lost a different clause that way on each of two consecutive revisions before the paraphrase was removed rather than corrected again.

With no parser available, read the files, which is affordable because the subject is a docs tree rather than a codebase.

Detection needs nothing installed and nothing resolved: the files are in a read-only clone, and this check reads their bytes.

## Fix

**Join each paragraph reported as a violation onto one line**, and change nothing else in the file. A row that is not a violation is not a rejoin instruction - a `no-evidence` row is the check saying it could not judge that paragraph, so joining it destroys exactly the construct the guard above declined to judge. The joined line is the paragraph's text with **each line break that is not an explicit hard break** replaced by a single space. The exception is stated here as well as in the detection rule because the two are separately reachable: an agent handed a row acts on this section, and a row that reached it wrongly is exactly the case where the fix must not compound the error.

**Join the paragraph's text, not its source lines.** A paragraph inside a block quote or a list item carries a prefix on every line it occupies, not only on its first: a block quote repeats `>`, and a list item repeats the continuation indentation. Concatenating the source lines therefore leaves those prefixes inside the sentence, where a stray `>` renders as literal text and the page changes. Strip each line's prefix and join the text. This is the corruption to look for in the diff read the domain gate asks for, and the one this check can cause that leaves no structural trace at all - the result is a single line, so re-running detection reports clean, and nothing has moved for a scan watching tables, alerts and fences to notice.

**Then write each surviving line with the prefix its own position in the block needs, rather than reapplying the opening line's prefix once.** Two shapes make the difference visible. A paragraph nested in more than one block - a list item inside a block quote - has a prefix built from every level it sits under, and an opening prefix that differs from the continuation one. And a mixed hard-break paragraph still occupies several lines after the join, so lines after the first need the continuation prefix rather than nothing at all; reapplying only the opening prefix drops them out of the block, which is a structural change on top of the rendering one.

**A paragraph that mixes column wraps with explicit hard breaks does not join onto one line, and joining it changes what the page shows.** Detection reports such a paragraph, because not all of its line endings are ones the author asked for - but a hard break needs a line break in the source to exist at all, so the conforming form here is one line per hard-break-delimited segment rather than one line overall. Replace only the breaks that are not explicit; keep every two-space and backslash ending exactly where it is, including the whitespace, which a trailing-whitespace stripper will otherwise remove on the way past. This is the one shape where the rule's own instruction, read literally, edits the rendered document.

**Leave every code block and every diagram exactly as authored.** This is the clause's second instruction and it binds the fix rather than the detection, because it is not decidable from a snapshot: a wrapped code line and a code line written that way are the same bytes. So a reformatter pointed at the whole file is the wrong instrument - it cannot tell the two apart either, and it will normalise fences, tables and diagram sources that were correct. Rejoin the paragraphs the rows name and leave the rest of the file untouched.

**Never reflow a paragraph the check did not report.** A conforming paragraph is already one line; touching it turns a fix into a whole-file diff, which is the cost the clause exists to avoid, arriving as its own remedy.

## What this check does not do

**It does not judge the prose.** The finding is "this paragraph is hard-wrapped", never "this paragraph is too long", "badly written" or "in the wrong file". Length, clarity and placement are `docs/coverage`'s and `docs/organization`'s, and answering them here would double count the findings the front door exists to consolidate.

**It does not decide whether the project should adopt the rule.** It reports the distance from the handbook's house rule. Whether a project with a stated column limit changes that limit is a convention decision its maintainers take, and the row's Minor severity and the note about a conflicting configuration are how this check hands that decision over rather than making it.

## Review lens

**Paragraph, not line** - does every row name a paragraph and a line range rather than a long line, and does the report survive the obvious challenge that it is a line-length finding under another name? A row that cites a single line number is the shape this fails as.

**The fix touched only what was reported** - were the reported paragraphs joined and nothing else, with every code block, table and diagram source byte-identical to what it was? A whole-file reformat closes the rows and reintroduces the diff cost the clause is about.

**Convention conflict recorded, not overruled** - where the project's own guide or linter configuration asks for a column limit, does the row say so, rather than reporting the tree as defective against a rule its maintainers declined?
