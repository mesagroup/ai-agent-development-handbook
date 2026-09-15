# Handbook D2 Diagrams Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render ```` ```d2 ```` fences in the engineering handbook to inline, theme-aware SVG in the HTML artifact, and author the seven diagrams the design selected.

**Architecture:** `scripts/render_handbook_artifact.py` grows a D2 stage that extracts fences from the Markdown source *before* the Markdown converter runs, replaces each with a block-level HTML placeholder, shells out to the `d2` CLI once per theme variant, and substitutes the resulting `<figure>` back into the converted HTML. Task 1 lands the whole mechanism plus one diagram, so every verification gate runs green from the first commit; Tasks 2 and 3 author the remaining six into the already-working pipeline.

**Tech Stack:** Python 3.11+, the `d2` CLI (v0.7.1, `brew install d2`), python-markdown, pytest.

**Spec:** [`docs/superpowers/specs/2026-07-28-handbook-d2-diagrams-design.md`](../specs/2026-07-28-handbook-d2-diagrams-design.md)

## Global Constraints

- **Zero em-dashes** (`—`, U+2014) anywhere in `docs/engineering/`, in prose *and* in diagram labels. Use commas, parentheses, or colons.
- **No comma splices** in new handbook prose.
- **One paragraph per source line** in Markdown. Never hard-wrap prose. **Never reflow a d2 fence body**; diagram source is exempt from the wrapping rule exactly as code fences are.
- Handbook cross-links are **relative `.md` links with no `#anchor` fragment**; name the target section in prose next to the link.
- Handbook register: portable "how to" voice, no institutional "we", clipped imperative body, every rule carries its *why* inline.
- Every ```` ```d2 ```` fence **must** carry `title="..."` on its opening line.
- Diagram node and edge labels stay terse; enumerations belong in the prose beside the diagram, not inside its boxes. This is what keeps every diagram inside the 72ch measure at natural size.
- New code ships with unit tests. The pure helpers are tested; the `d2` subprocess call is not exercised in tests.

**Verification gates.** Every task ends with all five green:

1. `uv run pytest tests/scripts/ -q`
2. `uv run scripts/render_handbook_artifact.py` — counters must read `em-dashes: 0`, `residual .md hrefs: 0`, and the `diagrams:` count stated in the task. No `WARNING unmapped link` lines.
3. `uv run ruff check . && uv run ruff format --check .`
4. `uv run pyright`
5. `uv run mkdocs build --strict && uv run python scripts/check_docs.py && uv run python scripts/check_site_links.py site`

---

### Task 1: The D2 render stage, plus the Part 2 TDD loop

**Files:**
- Modify: `scripts/render_handbook_artifact.py`
- Modify: `docs/engineering/implementation-disciplines.md:9-19`
- Test: `tests/scripts/test_render_handbook_artifact.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: the ```` ```d2 title="..." ```` fence contract that Tasks 2 and 3 write against. A fence is replaced by `<figure class="diagram">` holding two `<span>` variants (`d2var d2-light`, `d2var d2-dark`) and a `<figcaption id="dcap-{stem}-{index}">`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/scripts/test_render_handbook_artifact.py` (the module is already loaded as `rh`, and `pytest` is already imported):

```python
def test_extract_d2_blocks_replaces_fence_with_placeholder():
    md = 'intro\n\n```d2 title="The TDD loop"\na -> b\n```\n\noutro\n'
    out, blocks = rh.extract_d2_blocks(md, "implementation-disciplines")
    assert '<div class="d2ph" data-i="0"></div>' in out
    assert "```d2" not in out
    assert len(blocks) == 1
    assert blocks[0].title == "The TDD loop"
    assert blocks[0].source == "a -> b\n"


def test_extract_d2_blocks_numbers_multiple_fences():
    md = '```d2 title="One"\na\n```\n\ntext\n\n```d2 title="Two"\nb\n```\n'
    out, blocks = rh.extract_d2_blocks(md, "x")
    assert [b.index for b in blocks] == [0, 1]
    assert [b.title for b in blocks] == ["One", "Two"]
    assert 'data-i="0"' in out
    assert 'data-i="1"' in out


def test_extract_d2_blocks_requires_a_title():
    with pytest.raises(ValueError, match="title"):
        rh.extract_d2_blocks('```d2\na -> b\n```\n', "lifecycle")


def test_extract_d2_blocks_leaves_other_fences_alone():
    md = "```python\nprint(1)\n```\n"
    out, blocks = rh.extract_d2_blocks(md, "x")
    assert out == md
    assert blocks == []


def test_prepare_svg_sizes_from_viewbox_and_names_the_figure():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 342 815"><g/></svg>'
    out = rh.prepare_svg(svg, "dcap-three-layer-model-0")
    assert 'width="342"' in out
    assert 'height="815"' in out
    assert 'role="img"' in out
    assert 'aria-labelledby="dcap-three-layer-model-0"' in out
    assert out.endswith("<g/></svg>")


def test_prepare_svg_rejects_output_without_a_viewbox():
    with pytest.raises(ValueError, match="viewBox"):
        rh.prepare_svg("<svg><g/></svg>", "dcap-x-0")


def test_diagram_figure_carries_both_variants_and_one_caption():
    block = rh.D2Block(index=0, title="The three layers", source="a -> b\n")
    svg = '<svg viewBox="0 0 10 20"></svg>'
    out = rh.diagram_figure("three-layer-model", block, svg, svg)
    assert out.count("<svg") == 2
    assert 'class="d2var d2-light"' in out
    assert 'class="d2var d2-dark"' in out
    assert (
        '<figcaption id="dcap-three-layer-model-0">The three layers</figcaption>' in out
    )


def test_substitute_d2_replaces_placeholders_by_index():
    html = '<p>a</p><div class="d2ph" data-i="1"></div><div class="d2ph" data-i="0"></div>'
    out = rh.substitute_d2(html, {0: "<figure>zero</figure>", 1: "<figure>one</figure>"})
    assert out == "<p>a</p><figure>one</figure><figure>zero</figure>"


def test_substitute_d2_raises_on_a_missing_figure():
    with pytest.raises(ValueError, match="3"):
        rh.substitute_d2('<div class="d2ph" data-i="3"></div>', {})


def test_count_em_dashes_sees_the_entity_form():
    # to_ascii_entities runs before the counter, so by then the literal
    # character is already gone; counting only chr(8212) is what made the
    # handbook's em-dash gate vacuous.
    assert rh.count_em_dashes("a — b") == 1
    assert rh.count_em_dashes(rh.to_ascii_entities("a — b")) == 1
    assert rh.count_em_dashes("a, b") == 0


def test_d2_preludes_cover_both_variants_and_clear_the_canvas():
    assert set(rh.D2_PRELUDES) == {"light", "dark"}
    for prelude in rh.D2_PRELUDES.values():
        assert prelude.startswith("style.fill: transparent")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/scripts/test_render_handbook_artifact.py -q`
Expected: FAIL, `AttributeError: module 'render_handbook_artifact' has no attribute 'extract_d2_blocks'`.

- [ ] **Step 3: Add the D2 stage to the renderer**

In `scripts/render_handbook_artifact.py`, extend the import block at the top (currently `import argparse`, `import re`, `from pathlib import Path`) so it reads:

```python
import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
```

Immediately after the `LINKMAP` definition, insert:

```python
# The handbook's own palette, prepended to every diagram's source so the
# rendered SVG uses the same hex values as the artifact's CSS variables and the
# diagrams read as page furniture rather than as pictures from another system.
# Two variants rather than d2's own `--dark-theme`, because that follows the
# `prefers-color-scheme` query alone and the page carries a manual theme button.
D2_PRELUDES: dict[str, str] = {
    "light": (
        "style.fill: transparent\n"
        '**.style.fill: "#f7f6f2"\n'
        '**.style.stroke: "#c3bfb1"\n'
        '**.style.font-color: "#1c2024"\n'
        "**.style.shadow: false\n"
        '(** -> **)[*].style.stroke: "#9a6a1c"\n'
        '(** -> **)[*].style.font-color: "#4b5057"\n'
    ),
    "dark": (
        "style.fill: transparent\n"
        '**.style.fill: "#1e2126"\n'
        '**.style.stroke: "#3a4048"\n'
        '**.style.font-color: "#e9e7df"\n'
        "**.style.shadow: false\n"
        '(** -> **)[*].style.stroke: "#d9a441"\n'
        '(** -> **)[*].style.font-color: "#adaaa0"\n'
    ),
}

_D2_FENCE_RE = re.compile(
    r"^```d2(?P<meta>[^\n]*)\n(?P<body>.*?)^```[ \t]*$", re.DOTALL | re.MULTILINE
)
_D2_TITLE_RE = re.compile(r'title="([^"]+)"')
_D2_PLACEHOLDER_RE = re.compile(r'<div class="d2ph" data-i="(\d+)"></div>')
_SVG_OPEN_RE = re.compile(r"<svg\b[^>]*>")
_VIEWBOX_RE = re.compile(r'viewBox="[-\d.]+ [-\d.]+ ([\d.]+) ([\d.]+)"')


@dataclass(frozen=True)
class D2Block:
    """One ```d2 fence lifted out of a handbook page."""

    index: int
    title: str
    source: str


def extract_d2_blocks(md: str, stem: str) -> tuple[str, list[D2Block]]:
    """Replace every ```d2 fence with a placeholder and return the blocks.

    Fences are lifted out of the Markdown *before* the converter runs, so the
    rendered SVG never has to be recovered from an entity-escaped `<pre><code>`
    block. python-markdown passes a block-level `<div>` through untouched.

    Args:
        md: The page's Markdown source.
        stem: The page's filename stem, used in error messages and ids.

    Returns:
        The Markdown with each fence replaced by its placeholder, and the
        extracted blocks in document order.

    Raises:
        ValueError: A fence carries no `title="..."`.
    """
    blocks: list[D2Block] = []

    def repl(match: re.Match[str]) -> str:
        title = _D2_TITLE_RE.search(match.group("meta"))
        if title is None:
            raise ValueError(
                f'{stem}.md: a ```d2 fence has no title="..."; the title becomes '
                "the figure caption and the diagram's accessible name, so an "
                "untitled diagram would ship unlabeled."
            )
        index = len(blocks)
        blocks.append(
            D2Block(index=index, title=title.group(1), source=match.group("body"))
        )
        return f'<div class="d2ph" data-i="{index}"></div>'

    return _D2_FENCE_RE.sub(repl, md), blocks


def run_d2(source: str, salt: str, variant: str) -> str:
    """Render one diagram to SVG with the `d2` CLI.

    Args:
        source: The fence body.
        salt: Appended to every generated SVG element id, so two variants of one
            diagram (or two identical diagrams) cannot collide on one page.
        variant: Which palette prelude to prepend, `light` or `dark`.

    Returns:
        The SVG markup, with no XML prolog.

    Raises:
        SystemExit: The `d2` CLI is absent, or it rejected the source.
    """
    command = [
        "d2",
        "--stdout-format", "svg",
        "--no-xml-tag",
        "--theme", "0",
        "--layout", "dagre",
        "--pad", "10",
        "--salt", salt,
        "-", "-",
    ]  # fmt: skip
    try:
        proc = subprocess.run(
            command,
            input=D2_PRELUDES[variant] + source,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise SystemExit(
            "d2 CLI not found on PATH. The handbook renderer turns ```d2 fences "
            "into inline SVG and cannot produce the artifact without it. Install "
            "it with `brew install d2`, or take a binary from "
            "https://github.com/terrastruct/d2/releases."
        ) from exc
    if proc.returncode != 0:
        raise SystemExit(
            f"d2 failed on diagram {salt!r} (exit {proc.returncode}):\n"
            f"{proc.stderr.strip()}"
        )
    return proc.stdout


def prepare_svg(svg: str, caption_id: str) -> str:
    """Make one d2 SVG embeddable: give it an intrinsic size and a name.

    d2 puts only a `viewBox` on the outer element, but `max-width: 100%;
    height: auto` needs an intrinsic size to scale against, so the viewBox's
    dimensions are copied onto the tag as `width`/`height`.

    Args:
        svg: Raw d2 output.
        caption_id: The `id` of the `<figcaption>` that names this diagram.

    Returns:
        The SVG with `width`, `height`, `role`, and `aria-labelledby` added.

    Raises:
        ValueError: The output has no `<svg>` element, or none with a viewBox.
    """
    opening = _SVG_OPEN_RE.search(svg)
    if opening is None:
        raise ValueError("d2 produced output with no <svg> element")
    tag = opening.group(0)
    viewbox = _VIEWBOX_RE.search(tag)
    if viewbox is None:
        raise ValueError("the outer <svg> element has no viewBox to size from")
    sized = (
        f'{tag[:-1]} width="{viewbox.group(1)}" height="{viewbox.group(2)}"'
        f' role="img" aria-labelledby="{caption_id}">'
    )
    return svg[: opening.start()] + sized + svg[opening.end() :]


def diagram_figure(stem: str, block: D2Block, light: str, dark: str) -> str:
    """Wrap both rendered variants and their caption in one `<figure>`."""
    caption_id = f"dcap-{stem}-{block.index}"
    return (
        '<figure class="diagram">'
        f'<span class="d2var d2-light">{prepare_svg(light, caption_id)}</span>'
        f'<span class="d2var d2-dark">{prepare_svg(dark, caption_id)}</span>'
        f'<figcaption id="{caption_id}">{block.title}</figcaption>'
        "</figure>"
    )


def substitute_d2(html: str, figures: dict[int, str]) -> str:
    """Replace each d2 placeholder with its rendered figure.

    Raises:
        ValueError: A placeholder has no matching figure.
    """

    def repl(match: re.Match[str]) -> str:
        index = int(match.group(1))
        if index not in figures:
            raise ValueError(f"no rendered figure for d2 placeholder {index}")
        return figures[index]

    return _D2_PLACEHOLDER_RE.sub(repl, html)


def count_em_dashes(html: str) -> int:
    """Count em-dashes in both the literal and the numeric-entity form.

    `to_ascii_entities` runs before this counter and has already rewritten the
    literal character to `&#8212;`, so counting only the character reported zero
    whatever the sources held, which made the handbook's em-dash gate vacuous.
    """
    return html.count("—") + html.count("&#8212;")
```

Then replace the body of `render_doc` with:

```python
def render_doc(
    docs_dir: Path, stem: str, linkmap: dict[str, str]
) -> tuple[str, list[str]]:
    """Convert one markdown doc to post-processed HTML (lazy-imports markdown)."""
    import markdown  # lazy: keeps the pure helpers importable without the dep

    md = (docs_dir / f"{stem}.md").read_text()
    md, blocks = extract_d2_blocks(md, stem)
    html = markdown.markdown(md, extensions=["tables", "fenced_code", "sane_lists"])
    html, unmapped = post_process(html, linkmap)
    if blocks:
        html = substitute_d2(
            html,
            {
                block.index: diagram_figure(
                    stem,
                    block,
                    run_d2(block.source, f"{stem}-{block.index}-light", "light"),
                    run_d2(block.source, f"{stem}-{block.index}-dark", "dark"),
                )
                for block in blocks
            },
        )
    return html, unmapped
```

In `main`, replace the `residual = ...` line and the two `print` calls at the end (lines 187-194) with:

```python
    residual = len(re.findall(r'href="[^"]+\.md', html))
    tasks = html.count('class="task')
    diagrams = html.count('<figure class="diagram"')
    print(f"wrote {args.out} ({len(html)} bytes)")
    print(
        f"  sections: {html.count('<section id=')}  "
        f"task items: {tasks}  "
        f"diagrams: {diagrams}  "
        f"em-dashes: {count_em_dashes(html)}  "
        f"residual .md hrefs: {residual}"
    )
```

The two counts are lifted into locals deliberately, not for readability. The line being replaced embeds a double-quoted string inside a double-quoted f-string expression, which is [PEP 701](https://peps.python.org/pep-0701/) syntax that only parses on Python 3.12 and later, while this script's inline header declares `requires-python = ">=3.11"`. Keeping the pattern would add a second instance of a latent break for a 3.11 user; hoisting the expression out removes it.

- [ ] **Step 4: Add the diagram CSS**

In `_HEAD`, immediately after the task-list block (the rule ending `.doc li.task.done::before { ... }`) and before the `footer { ... }` rule, insert:

```css
  /* d2 diagrams: two rendered variants, toggled with the page theme */
  .doc figure.diagram { margin: 22px 0; }
  .doc figure.diagram svg { display: block; margin: 0 auto; max-width: 100%; height: auto; }
  .doc figure.diagram figcaption {
    margin-top: 10px; text-align: center; font-family: var(--mono);
    font-size: .7rem; letter-spacing: .07em; text-transform: uppercase; color: var(--ink-faint);
  }
  .d2var { display: block; }
  .d2-dark { display: none; }
  @media (prefers-color-scheme: dark) { .d2-light { display: none; } .d2-dark { display: block; } }
  :root[data-theme="light"] .d2-light { display: block; }
  :root[data-theme="light"] .d2-dark { display: none; }
  :root[data-theme="dark"] .d2-light { display: none; }
  :root[data-theme="dark"] .d2-dark { display: block; }
```

- [ ] **Step 5: Update the module docstring**

In the module docstring of `scripts/render_handbook_artifact.py`, replace the sentence beginning "The prose is produced verbatim..." with:

```
The prose is produced verbatim by a Markdown converter over
``docs/engineering/*.md``, so the HTML text is identical to the repo; only
cross-links (``foo.md`` -> ``#anchor``), table / task-list markup, and ```d2
fences are transformed, and the result is wrapped in a styled, single-page
shell (sidebar nav, light/dark theme toggle, scroll-spy). Re-run after editing
any doc to regenerate the shareable artifact; there is no hand-maintained copy
to drift.

Requires the `d2` CLI on PATH (``brew install d2``): every ```d2 fence is
rendered twice, once per theme palette, and inlined as SVG so the artifact
stays self-contained under a strict CSP.
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/scripts/test_render_handbook_artifact.py -q`
Expected: PASS, all tests.

- [ ] **Step 7: Replace the ASCII TDD loop with a d2 fence**

In `docs/engineering/implementation-disciplines.md`, replace the fence at lines 11-17 (the one starting `write a failing test`) with, exactly:

````
```d2 title="The TDD loop"
t: Write a failing test
f: Run it, see it fail
i: Write the minimal code
p: Run it, see it pass
c: Commit
t -> f -> i -> p -> c
c -> t: the next behaviour {style.stroke-dash: 4}
```
````

Leave the sentence above it ("Run this bite-sized loop for every feature and bugfix:") and the paragraph below it unchanged.

- [ ] **Step 8: Run the verification gates**

Run: `uv run scripts/render_handbook_artifact.py`
Expected: `sections: 12  task items: 83  diagrams: 1  em-dashes: 0  residual .md hrefs: 0`, no WARNING lines.

Run: `uv run ruff check . && uv run ruff format --check . && uv run pyright`
Expected: all clean.

Run: `uv run mkdocs build --strict && uv run python scripts/check_docs.py && uv run python scripts/check_site_links.py site`
Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add scripts/render_handbook_artifact.py tests/scripts/test_render_handbook_artifact.py docs/engineering/implementation-disciplines.md
git commit -m "feat(<origin-repo>#537): render d2 fences to inline theme-aware SVG in the handbook artifact"
```

---

### Task 2: The README arc, and the diagrams for Parts 3 and 4

**Files:**
- Modify: `docs/engineering/README.md:21-22`
- Modify: `docs/engineering/codebase-structure.md:23-24`
- Modify: `docs/engineering/three-layer-model.md:27-28`

**Interfaces:**
- Consumes: the ```` ```d2 title="..." ```` fence contract from Task 1.
- Produces: nothing later tasks depend on.

Each fence goes on its own lines, separated from the surrounding paragraphs by one blank line, exactly as a code fence would be. **Do not reflow the diagram source.** No introductory sentence is added for any diagram: each sits directly after the prose that states the rule it draws, and the caption names it.

- [ ] **Step 1: Add the story-arc diagram to the README**

In `docs/engineering/README.md`, after the paragraph "Do not expect the loop to terminate. ..." (line 21) and before the `### The parts, at a glance` heading, insert a blank line and then:

````
```d2 title="The story of a change"
idea: An idea
issue: Issue
spec: Spec
plan: Plan
build: Implement, task by task
merge: Merge
run: Observe in production
decide: "Evaluate: is it actually better?"
idea -> issue
issue -> spec
spec -> plan: human approves the spec
plan -> build
build -> merge: human approves the merge
merge -> run
run -> decide
decide -> idea: what the measurement teaches becomes the next issue
```
````

- [ ] **Step 2: Add the tier diagram to Part 3**

In `docs/engineering/codebase-structure.md`, after the paragraph beginning "Hold one invariant:" (line 23) and before the paragraph beginning "Write the rule down explicitly", insert:

````
```d2 title="Tiers, and the direction an import may point"
task: Task layer {
  direction: right
  a: Agent A
  b: Agent B
  a -> b: as_tool {style.stroke-dash: 4}
}
core: Reusable core {
  grid-columns: 1
  ev: Evaluation
  cap: Capabilities
  integ: External integrations
  conf: Configuration
  infra: Core infrastructure
  types: Shared schemas and types
}
task -> core: imports point at the core
core -> task: never, and never in a cycle {style.stroke-dash: 4}
```
````

- [ ] **Step 3: Add the layer diagram to Part 4**

In `docs/engineering/three-layer-model.md`, after the paragraph beginning "The cost is not just the error;" (line 27) and before the `## Hold the contracts that make layering pay off` heading, insert:

````
```d2 title="The three layers, and the shortcut that skips them"
doc: The document
l1: "Layer 1: intrinsic structure"
l2: "Layer 2: domain entities"
l3: "Layer 3: workflow knowledge"
ans: The answer
doc -> l1: perception
l1 -> l2: grounding
l2 -> l3: inference
l3 -> ans
doc -> l3: the shortcut that makes a failure undiagnosable {style.stroke-dash: 4}
```
````

- [ ] **Step 4: Run the verification gates**

Run: `uv run scripts/render_handbook_artifact.py`
Expected: `diagrams: 4`, `em-dashes: 0`, `residual .md hrefs: 0`, no WARNING lines.

Run: `uv run pytest tests/scripts/ -q && uv run ruff check . && uv run ruff format --check . && uv run pyright`
Expected: all clean.

Run: `uv run mkdocs build --strict && uv run python scripts/check_docs.py && uv run python scripts/check_site_links.py site`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add docs/engineering/README.md docs/engineering/codebase-structure.md docs/engineering/three-layer-model.md
git commit -m "docs(<origin-repo>#537): diagram the story arc, the tier directions, and the three layers"
```

---

### Task 3: The diagrams for Parts 6, 7 and 9, and the Part 8 cross-reference

**Files:**
- Modify: `docs/engineering/observability.md:13-14`
- Modify: `docs/engineering/evaluation.md:62-63`
- Modify: `docs/engineering/security-supply-chain.md:13-14`
- Modify: `docs/engineering/documentation.md:60`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: the fence contract from Task 1.
- Produces: nothing.

- [ ] **Step 1: Add the side-channel diagram to Part 6**

In `docs/engineering/observability.md`, after the paragraph ending "Observability that changes the thing it observes is not observability." (line 13) and before the `## Capture per-(sub)agent, per-tool usage` heading, insert:

````
```d2 title="The observability side channel"
tool: A tool runs
ctx: Model context
side: Side channel
art: Run artifacts, persisted into production
tool -> ctx: the result the model reads
tool -> side: the metadata envelope
side -> art: timing, tokens, cost, utilization
side -> ctx: never {style.stroke-dash: 4}
```
````

- [ ] **Step 2: Add the funnel diagram to Part 7**

In `docs/engineering/evaluation.md`, after the sentence "The funnel exists precisely so you spend expensive semantic evaluation only on candidates that already cleared the cheap gates." (line 62) and before the `## Grow the eval into a gate` heading, insert:

````
```d2 title="The staged screening funnel"
c: Many candidates
g1: Cheap deterministic gates
g2: Composite score
g3: Semantic scoring, LLM judge
h: Human adjudication
ship: The one you ship
c -> g1: everything
g1 -> g2: the clearly bad eliminated
g2 -> g3: survivors only
g3 -> h: the residual only
h -> ship
```
````

- [ ] **Step 3: Add the source-to-sink diagram to Part 9**

In `docs/engineering/security-supply-chain.md`, after the bullet beginning "**Neutralize at the sink**" (line 13) and before the `## Grant the agent the least privilege it needs` heading, insert:

````
```d2 title="A finding is a path from a source to a sink"
src: Untrusted source
b: Validate and canonicalize at the boundary {shape: hexagon}
app: Your code
n: Neutralize at the sink {shape: hexagon}
sink: Dangerous sink
src -> b -> app -> n -> sink
```
````

- [ ] **Step 4: Cross-reference the handbook's own pipeline from Part 8**

In `docs/engineering/documentation.md`, line 60, replace the final sentence of the diagrams-as-code bullet so the whole bullet reads:

```
- **Diagrams as code, generated from source**: keep any generated diagram in a text metalanguage ([Mermaid](https://mermaid.js.org/), [PlantUML](https://plantuml.com/), [D2](https://d2lang.com/)) rather than a binary image, and regenerate it from the source of truth on merge. A diagram drawn by hand or by a model drifts from the code the moment either changes; one generated from the code cannot, and it stays diffable in review like the rest of the source. This handbook is its own worked example: every diagram in it is a D2 fence in the Markdown source, rendered to inline SVG when the artifact is built.
```

- [ ] **Step 5: Document the d2 prerequisite**

In `CLAUDE.md`, in the Utilities block under "Development Commands", replace the `render_handbook_artifact.py` line with:

```
uv run scripts/render_handbook_artifact.py [--out PATH]                  # Render docs/engineering/ handbook to a single self-contained HTML artifact (needs the d2 CLI: brew install d2)
```

- [ ] **Step 6: Run the verification gates**

Run: `uv run scripts/render_handbook_artifact.py`
Expected: `diagrams: 7`, `em-dashes: 0`, `residual .md hrefs: 0`, no WARNING lines.

Run: `uv run pytest tests/scripts/ -q && uv run ruff check . && uv run ruff format --check . && uv run pyright`
Expected: all clean.

Run: `uv run mkdocs build --strict && uv run python scripts/check_docs.py && uv run python scripts/check_site_links.py site`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add docs/engineering/observability.md docs/engineering/evaluation.md docs/engineering/security-supply-chain.md docs/engineering/documentation.md CLAUDE.md
git commit -m "docs(<origin-repo>#537): diagram the side channel, the funnel, and the source-to-sink path"
```
