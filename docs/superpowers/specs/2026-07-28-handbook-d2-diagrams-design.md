# Handbook D2 Diagrams — Design

**Issue:** [#537](https://github.com/lidia-tech/lidia-agents/issues/537)
**Date:** 2026-07-28
**Status:** approved in session (style, diagram set, and lifecycle placement each confirmed by the user)

## Goal

The engineering handbook is prose-only; its single "diagram" is an ASCII TDD loop in a plain code fence. Author seven diagrams in **D2**, as ```` ```d2 ```` fences in the Markdown sources, and extend `scripts/render_handbook_artifact.py` to render each fence to inline, theme-aware SVG in the single-file HTML artifact. The diagram *code* is the source of truth, which is the handbook practicing Part 8's own diagrams-as-code rule.

## Which diagrams earn their place

The test applied to each candidate: **does the diagram assert something the prose cannot?** A loop that closes, an arrow that is forbidden, two lanes that never touch. A diagram that merely re-lists what a table already lists fails the test.

| # | Part | Diagram | What it asserts that the prose cannot |
|---|---|---|---|
| 1 | README | The story of a change | The stations of one change, with the two always-on human gates on the edges, closing back to the start. The closing claim ("do not expect the loop to terminate") becomes visible rather than stated. |
| 2 | Part 2 | The TDD loop | That the loop *closes*. The ASCII it replaces draws a chain of arrows that stops at "commit". |
| 3 | Part 3 | Tiers and the direction of imports | The permitted arrow and the **forbidden** one in the same picture, plus `as_tool` as the single sanctioned sideways edge. The tier table can rank tiers but cannot draw a direction. |
| 4 | Part 4 | The three layers, and the shortcut | The dashed bypass from raw document straight to Layer 3 **is** the "never skip a layer" rule. The strongest diagram in the set. |
| 5 | Part 6 | The observability side channel | Two lanes out of one tool call, and a dashed "never" edge from the side channel back into the model's context. The rule is a topology claim, so a topology shows it. |
| 6 | Part 7 | The staged screening funnel | Cost rising and population falling across the same stages, which the decision table lists but does not relate. |
| 7 | Part 9 | Source to sink | That a finding is a **path**, and that the two defenses (validate at the boundary, neutralize at the sink) sit at two distinct points on it. |

**Excluded, with reasons.** *Part 1's operational route*: the README arc already carries the lifecycle, and Part 1's numbered nine-step list is a list, not a graph; two lifecycle diagrams on adjacent ground would read as repetition. *Part 5's harness*: an inventory of capabilities, not a topology; a box per capability would be the table of contents with rounded corners. *Part 9's lethal trifecta*: the idea is a Venn, and D2 is a graph-layout tool with no facility for overlapping circles, so the honest choice is prose plus the source-to-sink diagram that D2 does render well.

## Decisions

- **Style: the handbook's own palette, injected as a D2 style prelude.** The renderer prepends a per-theme prelude (`**.style.fill`, `**.style.stroke`, `**.style.font-color`, and the connection equivalents) carrying the exact hex values from the artifact's CSS variables: paper/ink/ochre in light, slate/gold in dark. Diagrams then read as page furniture rather than as embedded pictures from another system. Stock d2 themes were rejected as visibly foreign against the warm paper; sketch mode was rejected on cost (80KB per variant against 19KB) and because D2 emits its sketch CSS globally, so every diagram would need its streak rules scoped to its own root class.
- **Theme handling: dual render, toggled by CSS.** Each fence is rendered twice, once per palette, and both SVGs ship wrapped in spans that the page's existing theme mechanism toggles. The artifact has a manual theme *button*, not only a `prefers-color-scheme` query, so d2's built-in `--dark-theme` (which keys off the media query alone) cannot follow the toggle. Cost is roughly 40KB per diagram against a current artifact of 178KB.
- **Layout: ELK with a tightened rank gap, and shape chosen per diagram.** *(Revised after PR review: the original decision was "prefer `direction: down`" on dagre, which shipped diagrams up to 1313px tall. They did not fit a laptop viewport, which is what the review caught.)* Two constraints pull against each other: a diagram must fit the viewport vertically, and it must fit the 72ch measure horizontally at its natural size, because `max-width: 100%` scales the labels down along with the boxes. The decisive lever is rank separation. Dagre exposes none (`--dagre-nodesep` is horizontal); ELK exposes `nodeNodeBetweenLayers`, and dropping it from 70 to 15, with a 12px label font, roughly halves every diagram at no cost to legibility. Direction is then chosen per diagram rather than by default: long chains go horizontal (the story arc, 1313px tall down to 182px), wide sets go to a grid (the tier stack, 1232px down to 633px), and short flows stay vertical. Verified in a browser at a 900px viewport: the tallest figure is 635px, and every diagram renders at its natural size, so no label is ever scaled down.
- **Encode a property as a shape before spelling it out in a box.** A label is the most expensive way to mark a node, because in d2 the label *is* the minimum box size, and in a horizontal chain every widened box pushes the whole diagram past the measure. Writing "human approves" into the two gated nodes of the story arc cost 101px of width and forced the entire figure to 0.91 scale. `shape: person` says the same thing, moves the label outside the shape, and is 101px *narrower* than a plain rectangle, which is what brings the arc to natural size. Alternatives were measured and rejected: a separate person node per gate (875px wide and 303px tall, the silhouettes dominating the chain), bold gate edges (807px, and chunky arrowheads that read as noise), and an accent stroke on the gated nodes (807px, and indistinguishable without a legend). The caption carries the legend, so the encoding is never shape-only.
- **Diagram labels stay terse.** Enumerations (the list of untrusted sources, the list of dangerous sinks) live in the prose next to the diagram, not inside its boxes. This is what keeps the diagrams inside the measure, and it is better practice regardless.
- **A `title=` on every fence is mandatory.** The renderer raises when one is missing. The title becomes the visible `<figcaption>` and the accessible name, so making it required is what stops an unlabeled diagram shipping.

## Renderer design

`scripts/render_handbook_artifact.py` grows a D2 stage. The pure helpers stay unit-testable and separate from the subprocess call, matching how the existing transforms are structured.

**Pipeline order.** Fences are extracted from the *Markdown source*, before the Markdown converter runs, and each is replaced by a block-level HTML placeholder (`<div class="d2ph" data-i="N"></div>`) that python-markdown passes through untouched. The rendered figures are substituted back into the HTML afterwards. Extracting first avoids having to unescape HTML entities out of a `<pre><code>` block, which is the failure mode of the post-process approach.

**New functions.**

- `extract_d2_blocks(md) -> tuple[str, list[D2Block]]`: replaces each ```` ```d2 title="..." ```` fence with its placeholder; returns the rewritten Markdown and the blocks (index, title, source). Raises `ValueError` naming the document when a fence carries no `title=`.
- `run_d2(source, salt, theme_prelude) -> str`: composes prelude plus source, pipes it to `d2 --stdout-format svg --no-xml-tag --theme 0 --layout elk --elk-nodeNodeBetweenLayers 15 --elk-edgeNodeBetweenLayers 15 --elk-padding [top=20,left=20,bottom=20,right=20] --pad 10 --salt <salt> - -`, returns the SVG.
- `size_svg(svg) -> str`: copies `width`/`height` onto the outer `<svg>` from its `viewBox`, since D2 emits only a `viewBox` there and `max-width: 100%; height: auto` needs an intrinsic size to scale against.
- `diagram_figure(light, dark, title, uid) -> str`: the `<figure>` markup, both variants plus the caption.
- `substitute_d2(html, figures) -> str`: replaces each placeholder with its figure.
- `count_em_dashes(html) -> int`: counts the literal character **and** the `&#8212;` entity.

**Salt.** `f"{stem}-{index}-{variant}"`, unique per document, per diagram, per theme variant, so two variants of one diagram (or two identical diagrams on the page) never collide on SVG element ids.

**Accessibility.** Each figure is `<figure class="diagram">` holding two `<span>` variants and a `<figcaption id="dcap-{uid}">`. Each `<svg>` carries `role="img"` and `aria-labelledby="dcap-{uid}"`. The hidden variant is `display: none`, so it leaves the accessibility tree and the caption is not announced twice.

**CSS.** The variant toggle mirrors the mechanism the page already uses for its colour variables: a default, a `prefers-color-scheme: dark` override, and `:root[data-theme="..."]` rules that outrank the media query in both directions so the manual button wins.

**Failure mode when `d2` is missing.** `FileNotFoundError` from the subprocess becomes a `SystemExit` naming the tool, why it is needed, and how to install it (`brew install d2`, or the release binaries). A non-zero exit from `d2` becomes a `SystemExit` carrying the document, the diagram title, and d2's stderr verbatim, so a broken fence is diagnosable without re-running by hand. There is no silent-skip and no degraded mode: an artifact missing its diagrams while claiming success is worse than one that refuses to build.

## Fixing the em-dash gate

The gate the handbook's own acceptance criteria lean on is **vacuous**. `main()` counts `chr(8212)` in the string returned by `build()`, but `build()` ends with `to_ascii_entities()`, which has already turned every em-dash into `&#8212;`. The counter therefore reports 0 regardless of content, and has since it was written.

The sources are in fact clean (zero em-dashes across `docs/engineering/*.md`; one en-dash in a numeric range, which the rule does not cover), so this is a gate repair with no cleanup fallout. `count_em_dashes` counts both forms, and it is unit-tested. This is in scope because it is the check this issue must pass, and shipping seven diagrams behind a check that cannot fail would be the wrong kind of green.

## Insertion points

| Diagram | File | Position |
|---|---|---|
| The story of a change | `README.md` | After the closing "Do not expect the loop to terminate" paragraph, before "The parts, at a glance". |
| The TDD loop | `implementation-disciplines.md` | Replaces the ASCII fence under "TDD". |
| Tiers and imports | `codebase-structure.md` | Under "Point every dependency toward the core, and never cycle", after the invariant paragraph. |
| The three layers | `three-layer-model.md` | Under "Never skip a layer", after the paragraph that names the shortcut. |
| The side channel | `observability.md` | Under "Keep observability out of the model's context", after the rule paragraph. |
| The screening funnel | `evaluation.md` | Under "Pick the approach that fits the decision", after the sentence that closes the table. |
| Source to sink | `security-supply-chain.md` | Under "First-party code: trace a path from source to sink", after the sources/sinks/neutralize bullets. |

No diagram gets an introductory sentence of its own: each sits directly after the prose that states the rule it draws, and its caption names it. Adding "the diagram below shows..." would be the caption twice.

## Part 8 cross-reference

Part 8's diagrams-as-code bullet gains a short clause pointing at the handbook's own pipeline as the worked example, closing the loop between the rule and its practice.

## Constraints

All standing `docs/engineering/` gates, binding:

- Zero em-dashes, in prose **and** in diagram labels (the repaired counter now sees both).
- No comma splices in new prose.
- One paragraph per source line. The no-hard-wrap rule covers prose; **diagram source is exempt and must never be reflowed**, the same exemption code fences already have.
- Cross-links are relative `.md` links with no `#anchor` fragments.
- Handbook register: portable "how to" voice, no institutional "we".
- New code ships with unit tests; the pure helpers above are all tested, the subprocess edge is mocked.

**Verification gates (all five must pass):**

1. `uv run scripts/render_handbook_artifact.py` (counters: em-dashes 0, residual .md hrefs 0, diagrams 7).
2. `uv run python scripts/check_docs.py`.
3. `uv run mkdocs build --strict`.
4. `uv run python scripts/check_site_links.py site`.
5. `uv run pytest tests/scripts/ && uv run ruff check . && uv run ruff format --check . && uv run pyright`.

## Out of scope

- **No MkDocs work.** `mkdocs.yml` excludes `engineering/` from the built site, so the d2 fences never reach it. The issue assumed otherwise; nothing is needed beyond confirming `mkdocs build --strict` still passes. No plugin, no degradation strategy.
- **No CI dependency on `d2`.** The render script is explicitly not a CI test, and nothing in CI invokes it. Its pure helpers are covered by unit tests that never shell out.
- **No render cache.** Seven diagrams render in well under a second; a cache keyed on source hash and d2 version would be machinery guarding nothing.
- **No sketch-mode support**, and therefore none of the scoped-overlay CSS handling that sketch would require.
- **No diagram in the troubleshooting guide.** It routes; the parts carry the content, diagrams included.
