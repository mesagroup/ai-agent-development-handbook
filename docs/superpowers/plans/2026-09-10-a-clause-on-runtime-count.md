# Plan: a clause on runtime count

Issue #18. Design: [../specs/2026-09-10-a-clause-on-runtime-count-design.md](../specs/2026-09-10-a-clause-on-runtime-count-design.md).

The edge-set rule makes this one commit: a clause and its rows land together or the integrity gate fails.

## 1. The clause, in Part 3 after the decay section

Four paragraphs in the part's own voice: the costs each additional runtime brings, the rule and the judgment it leaves to the reader, the declaration the rule requires and the unowned stack it prevents, and a closing paragraph pointing the individual costs back at the parts that already own them so the clause is not a second home for any of them.

After `## Watch for structural decay beyond layering` rather than after the tier table, so the part's idea-then-invariant run stays contiguous and the two sections that step outside the layering argument sit together.

## 2. Two matrix rows under the section's slug

`-a` `process` / important, the judgment, with a note saying why no snapshot reaches it. `-b` `static` / important, the declaration, with an `extend-skill` gap naming `arch-audit` in the note and #91 in `gap.target`, which is the field the renderer reads and five other `extend-skill` gaps use.

The checklist gains a line for the declaration half, and the checklist's own recap row goes from seven items to eight.

Then re-render, because the Markdown view is generated and the gate compares it against the YAML.

## 3. #91 for the check

Filed rather than written: the record needs two decisions the clause deliberately does not make - how to resolve the binding-rules file, and what separates a runtime from a language one file happens to be written in.

## Gates

The six runnable gates, the artifact renderer excluded because it needs the `d2` CLI. The traceability `--check` is the load-bearing one here: it holds every `##` section against a row, both rows' section text against the heading verbatim, the class and severity vocabularies, and that a `static` row carries either checks or a gap. A stale-prose pass over anything asserting what Part 3 contains or how many rows the matrix has.
