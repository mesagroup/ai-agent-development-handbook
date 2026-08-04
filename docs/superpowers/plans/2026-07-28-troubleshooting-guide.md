# Handbook Troubleshooting Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the symptom-indexed troubleshooting companion page to the engineering handbook (issue lidia-tech/lidia-agents#536) per the approved spec `docs/superpowers/specs/2026-07-28-troubleshooting-guide-design.md`.

**Architecture:** One new unnumbered companion page `docs/engineering/troubleshooting.md` (15 entries in 4 clusters), wired into the handbook artifact renderer (`scripts/render_handbook_artifact.py`, one PARTS row plus an unnumbered-glyph case in `render_nav`), the handbook README (companion table row + a "start here" pointer), and the `docs/README.md` blurb. Task 1 lands the skeleton page and all wiring so every verification gate runs green from the first commit; Tasks 2-4 author the clusters into the already-wired page.

**Tech Stack:** Markdown (handbook prose), Python 3.11 (render script), pytest (render-script unit tests).

## Global Constraints

Binding for everything under `docs/engineering/` (from the spec; the renderer counts some of these):

- **Zero em-dashes** (the character `—`) anywhere in handbook files. The render gate prints the count; it must stay 0. Use commas, colons, parentheses, or semicolons instead.
- **No comma splices** in new prose (two independent clauses joined by a bare comma). Use a semicolon, a colon, or two sentences.
- **One paragraph per source line.** Never hard-wrap prose to a column.
- **Cross-links** are relative `.md` links (e.g. `[Part 6](observability.md)`) with **no `#anchor` fragments**. Name the target section in prose next to the link. Same-file references use prose ("above", "below"), never links.
- **Register:** handbook voice. Italic bridge line at the top and italic hand-off at the bottom (single `*...*` paragraphs); clipped-imperative body; portable "how to" phrasing; no institutional "we"; no project-specific values (no "$5", no vendor names unless the parts themselves name them).
- **Entry shape** (spec): `###` heading phrased as the developer says the symptom, 3-6 sentences of differential diagnosis including the what-to-check-first move, then a bulleted routing list, one line per root cause, each linking to the part and naming the target section in prose. Folded facets appear as a sentence inside their host entry's diagnosis (never as a literal "Folded facet:" label in the shipped page).
- **Verification gates** (run in every task; all must pass):
  1. `uv run scripts/render_handbook_artifact.py` — output counters must show `em-dashes: 0` and `residual .md hrefs: 0`, and no `WARNING unmapped link` lines. From Task 1 on, `sections: 12`.
  2. `uv run python scripts/check_docs.py` — exit 0.
  3. `uv run mkdocs build --strict` — exit 0 (regression only: `docs/engineering/` is excluded from the site, see `mkdocs.yml`).
  4. `uv run python scripts/check_site_links.py site` — exit 0.
- **Commits:** message style `docs(lidia-tech/lidia-agents#536): <what>`, body explains what/why, ends with `Refs lidia-tech/lidia-agents#536` and the trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`. Stage explicit paths only (never `git add -A`).

---

### Task 1: Skeleton page, renderer wiring, and index wiring

**Files:**
- Create: `docs/engineering/troubleshooting.md` (skeleton: title, bridge, how-to-use, closing hand-off; no entries yet)
- Modify: `scripts/render_handbook_artifact.py:37-49` (PARTS) and `:113-123` (`render_nav`)
- Modify: `docs/engineering/README.md` (parts table + pointer paragraph)
- Modify: `docs/README.md` (handbook blurb, the paragraph starting `**How we work**`)
- Modify: `docs/superpowers/specs/2026-07-28-troubleshooting-guide-design.md` (one factual correction)
- Test: `tests/scripts/test_render_handbook_artifact.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: the skeleton page whose last line is the italic hand-off paragraph quoted in Step 5. Tasks 2-4 insert cluster sections **immediately before that hand-off line**. Also produces the PARTS row `("troubleshooting", "troubleshooting", "Troubleshooting")` so every later gate run renders the page.

- [ ] **Step 1: Write the failing test**

Append to `tests/scripts/test_render_handbook_artifact.py`, next to `test_render_nav_marks_coda_with_glyph_not_number` (import of `render_nav` already exists in the file):

```python
def test_render_nav_marks_troubleshooting_with_glyph_not_number():
    nav = render_nav(
        [
            ("p9", "security-supply-chain", "Security"),
            ("troubleshooting", "troubleshooting", "Troubleshooting"),
            ("coda", "coda", "Coda"),
        ]
    )
    assert 'href="#troubleshooting"' in nav
    assert "✚" in nav  # unnumbered companion glyph, like the coda's ∎
    row = nav.split("#troubleshooting")[1].split("#coda")[0]
    assert "01" not in row  # the companion row carries no part number
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/scripts/test_render_handbook_artifact.py -v -k troubleshooting`
Expected: FAIL (`✚` not found; `render_nav` currently numbers every non-top, non-coda row).

- [ ] **Step 3: Implement the renderer change**

In `scripts/render_handbook_artifact.py`, PARTS gains one row between `p9` and `coda`:

```python
    ("p9", "security-supply-chain", "Security &amp; supply chain"),
    ("troubleshooting", "troubleshooting", "Troubleshooting"),
    ("coda", "coda", "Coda"),
```

Update the comment above PARTS from `README is the intro section (#top), the nine parts follow, the coda closes.` to `README is the intro section (#top), the nine parts follow, then the troubleshooting companion and the coda close.`

In `render_nav`, replace the `num` assignment line with:

```python
        num = (
            "§"
            if anchor == "top"
            else "∎"
            if anchor == "coda"
            else "✚"
            if anchor == "troubleshooting"
            else f"{i:02d}"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/scripts/test_render_handbook_artifact.py -v`
Expected: all tests in the file PASS (the pre-existing ones must not regress).

- [ ] **Step 5: Create the skeleton page**

Create `docs/engineering/troubleshooting.md` with exactly this content (four source lines of prose, one blank line between each):

```markdown
# Troubleshooting: From Symptom to Section

*The nine parts teach the disciplines in the order you would learn them. This page is the other entry point, for the day you arrive with a problem instead of a curriculum: an agent that burns money, stalls, or lies, and no obvious owner among the disciplines. Find your symptom, read the short diagnosis, follow the route.*

Every entry has the same shape: the symptom as a developer says it, a few sentences of differential diagnosis that tell the plausible root causes apart, and one route per cause into the part that carries the fix. Two habits make the page work. Expect several distinct root causes behind one symptom, and read the diagnosis to tell them apart rather than to confirm the first suspicion. And make the first move instrumentation, not tuning: most entries begin by pointing at a record to read before anything gets changed ([Part 6](observability.md)).

*Whatever brought you here, the durable fix ends the same way every change does: encode the standard as an executable check so the symptom cannot return unannounced ([Part 1](lifecycle.md)). The full story starts at the [beginning](README.md).*
```

- [ ] **Step 6: Wire the handbook README**

In `docs/engineering/README.md`:

(a) Insert this row into the "parts, at a glance" table, between the Part 9 row and the Coda row:

```markdown
| **[Troubleshooting](troubleshooting.md)** | The other entry point: from a symptom (it burns money, it hangs, it hallucinates) to the sections that fix it. |
```

(b) Insert this paragraph after the second intro paragraph (the one ending `not "here is a specific tool."`), before the `## The story of a change` heading:

```markdown
Arriving with a problem rather than a curriculum? The [troubleshooting guide](troubleshooting.md) starts from the symptom and routes you to the parts that fix it.
```

- [ ] **Step 7: Wire the docs index blurb**

In `docs/README.md`, in the `**How we work**` paragraph (currently line 177), replace `security, dependencies & supply chain. Browse the source under` with `security, dependencies & supply chain; plus a symptom-indexed troubleshooting guide that routes from observable problems (cost blowups, hangs, hallucinations) into the parts. Browse the source under`.

- [ ] **Step 8: Correct the spec's mkdocs bullet**

In `docs/superpowers/specs/2026-07-28-troubleshooting-guide-design.md`, replace the wiring bullet beginning `- **mkdocs:**` with:

```markdown
- **mkdocs:** `docs/engineering/` is excluded from the built docs site (the handbook ships as its own standalone artifact; see the exclude list in `mkdocs.yml`), so the new page needs no nav entry and cannot orphan. `mkdocs build --strict` still runs as a regression gate.
```

- [ ] **Step 9: Run all four verification gates**

Run each command from the Global Constraints gate list. Expected: renderer prints `sections: 12  task items: <unchanged>  em-dashes: 0  residual .md hrefs: 0` with no `WARNING unmapped link` lines; the other three exit 0.

- [ ] **Step 10: Commit**

```bash
git add docs/engineering/troubleshooting.md scripts/render_handbook_artifact.py tests/scripts/test_render_handbook_artifact.py docs/engineering/README.md docs/README.md docs/superpowers/specs/2026-07-28-troubleshooting-guide-design.md
git commit -m "docs(lidia-tech/lidia-agents#536): add troubleshooting companion skeleton and wire it into the handbook"
```

(Include the standard body: what/why, `Refs lidia-tech/lidia-agents#536`, the co-author trailer from Global Constraints.)

---

### Task 2: Author clusters 1 and 2 (Cost and latency; Reliability — entries 1-5)

**Files:**
- Modify: `docs/engineering/troubleshooting.md`

**Interfaces:**
- Consumes: the skeleton from Task 1. Insert both cluster sections immediately **before** the closing italic hand-off line (`*Whatever brought you here, ...*`).
- Produces: `## Cost and latency` (entries 1-2) and `## Reliability` (entries 3-5) in shipping order. Entry 5's diagnosis references the tool-misuse entry with the prose phrase "the tool-misuse entry below" (that entry lands in Task 3; the forward reference is intentional).

- [ ] **Step 1: Write the two cluster sections**

Each entry is a `###` heading + one diagnosis paragraph (3-6 sentences, one source line) + a routing bullet list. Headings verbatim:

```markdown
## Cost and latency

### My agent burns dollars of tokens per run and I can't see where

### The app is unbearably slow

## Reliability

### It hangs while calling tools

### External calls fail intermittently

### It loops without progress
```

Entry 3 ("It hangs while calling tools") is the voice model for the whole page; include it verbatim:

```markdown
### It hangs while calling tools

Silence is not one failure; it is three. Before touching code, pull the persisted usage record for the stuck run and see where the clock went (the production feedback loop in [Part 6](observability.md)): a stage that never returned points at a missing timeout; a stage that returned instantly with nothing points at a swallowed error. The classic causes: an outbound call with no connect or read timeout waiting on a dropped socket; an exception raised inside an async event handler that nothing awaits, so the failure evaporates and the loop waits on a result that will never come; a resource teardown (a browser, a session) wedged on close. A tool that silently yields an empty answer instead of hanging is the second cause wearing a different face.

- No timeouts anywhere: make bounding the default, wall-clock, idle, connect, and read ([Part 5](agent-harness.md)).
- Errors that vanish instead of surfacing: the no-swallowed-exceptions rule ([Part 2](implementation-disciplines.md)) and making errors diagnosable ([Part 6](observability.md)).
- A wedged teardown of external resources: time-bound teardown ([Part 5](agent-harness.md)).
```

Author entries 1, 2, 4, 5 in the same shape from these requirements (copied from the spec; each "cause: route" pair becomes one routing bullet, each "first move" and each folded facet becomes diagnosis prose):

- **Entry 1 (token burn).** First move: the per-(sub)agent, per-tool usage record. Causes: no per-stage instrumentation at all (Part 6, "Capture per-(sub)agent, per-tool usage"); counting only input/output tokens while cache read/write dominates (Part 6, "Account for the full cost, not the convenient part"); low utilization, most of what is fetched never informs the answer (Part 6, utilization); iterating against live expensive backends instead of mock/cheap ones (Part 5, "Offer cheap and mock backends"). Folded facets: costs fine in dev but exploding in production (cache accounting again); prefix-cache churn, where a frequently edited system prompt invalidates the cache every run.
- **Entry 2 (slow).** First move: per-stage timing, never a parameter sweep (Part 6, "Instrument before you tune"). Causes: one dominant sequential stage in a multi-agent pipeline (Part 6, where a multi-agent run spends its time); a poorly formed upstream input poisoning every later stage (Part 6, look upstream); a slow model or too many retriever cycles (Part 7, cost/quality trade-offs and escalation ladders); unbounded waits inflating the tail (Part 5, "Make bounding the default").
- **Entry 4 (intermittent failures).** Open by distinguishing from the entry above: errors, not silence. Causes: missing bounded retries with backoff (Part 5, "Make bounding the default", the hardened HTTP client); no circuit breaker, so one degraded dependency poisons every run (Part 5, "Build the harness, don't inline the plumbing"); retries happening but invisible in cost and latency accounting (Part 6, "Account for the full cost").
- **Entry 5 (loops without progress).** First move: the tool-call sequence and loop-cycle counts in the usage record (Part 6). Causes: no cycle or budget bound in the harness (Part 5, "Make bounding the default"); the SOP gives no stop condition or completion criterion (Part 2, "Prompt and SOP engineering"); a tool returning unusable output so the agent retries blindly (the tool-misuse entry below); a model too weak to plan its way out (Part 7).

- [ ] **Step 2: Style pass on the new prose**

Check, on the diff only: no `—` character (`grep -c '—' docs/engineering/troubleshooting.md` must print `0`); no comma splices; every paragraph one source line; every link relative `.md` with no `#`; every routed section named in prose.

- [ ] **Step 3: Run all four verification gates**

Same commands and expectations as Task 1 Step 9 (`sections: 12`, `em-dashes: 0`, `residual .md hrefs: 0`, no unmapped-link warnings, others exit 0).

- [ ] **Step 4: Commit**

```bash
git add docs/engineering/troubleshooting.md
git commit -m "docs(lidia-tech/lidia-agents#536): author troubleshooting clusters 1-2 (cost and latency; reliability)"
```

(Standard body, `Refs lidia-tech/lidia-agents#536`, co-author trailer.)

---

### Task 3: Author cluster 3 (Output quality — entries 6-11)

**Files:**
- Modify: `docs/engineering/troubleshooting.md`

**Interfaces:**
- Consumes: Task 2's clusters. Insert `## Output quality` after the `## Reliability` section, before the closing hand-off line. Read entry 3 ("It hangs while calling tools") first and match its voice and shape exactly. Entry 10 is the target of Task 2's "the tool-misuse entry below" forward reference.
- Produces: entries 6-11 under `## Output quality`.

- [ ] **Step 1: Write the cluster**

Headings verbatim:

```markdown
## Output quality

### It fails with out-of-context errors

### It hallucinates

### It reasons wrongly from correct facts

### It ignores its SOP

### It won't use the tool I gave it, or calls it wrong

### Results differ from run to run
```

Author each entry (3-6 sentences of diagnosis + routing bullets) from these requirements:

- **Entry 6 (out-of-context).** Causes: bookkeeping and analysis metadata riding inside the prompt (Part 6, "Keep observability out of the model's context"); unbounded tool outputs with no truncation or summarization strategy (Part 5, "Make bounding the default"); over-fetching that instrumentation would show as unused (Part 6, utilization).
- **Entry 7 (hallucinates).** The canonical multi-cause entry; up to 7 sentences allowed here. Three scenarios behind one symptom: (a) quotes non-existent facts, ungrounded generation from model weights; check whether claims trace to fetched sources; route to Part 7 ("Measure the behaviors that matter", groundedness as an eval dimension) and Part 2 (grounding rules in the SOP). (b) Quotes documents imprecisely because the ingestion pipeline or OCR introduced the errors; diff the Layer 1 representation against the source document before blaming the model; route to Part 4 (the engine-agnostic Layer 1 contract) and Part 7 (extraction-quality evaluation, "Build a dataset you can trust"). (c) Quotes documents imprecisely because too much context dilutes attention; reproduce with the passage in isolation, and a clean quote means dilution, not extraction; route to Part 6 (utilization) and Part 5 (bounding what enters the context). The isolation reproduction is the pivot separating (b) from (c); say so explicitly. Folded facet: citations that do not support the claim, a groundedness case of (a).
- **Entry 8 (wrong reasoning).** Open with the differential against the entry above: the facts are right, the inference is wrong. Causes: model too weak for the task (Part 7, "Pick the approach that fits the decision", escalation ladders, the staged screening funnel); the SOP asking for a leap where it should ask for steps (Part 2, "Prompt and SOP engineering").
- **Entry 9 (ignores SOP).** Causes: constraint overload, too many rules competing for attention (Part 2, "Prompt and SOP engineering"); rules in the SOP that should be deterministic harness guards instead (Part 2 division of labour; Part 5); contradictory instructions that force the model to pick one (Part 2).
- **Entry 10 (tool misuse).** First move: read the actual tool-call transcript (Part 6). Causes: tool description and schema quality, including nullable or ambiguous parameters (Part 4, "Compose typed tools over one fuzzy lookup"; Part 5); too many overlapping tools (Part 4); the SOP never saying when to reach for the tool (Part 2). Folded facet: structured-output validation failures, the same schema-quality root cause.
- **Entry 11 (nondeterminism).** Causes: sampling parameters, temperature above zero where determinism was assumed (Part 5, "Expose model parameters as optional, defaulted flags"); an unpinned model version moving underneath (Part 9, pin models and providers); the external world changing between runs, live web or live corpus (Part 7, "Measure honestly", variance and repeated runs); nondeterministic tests or evals mistaken for agent nondeterminism (Part 2, deterministic tests).

- [ ] **Step 2: Style pass on the new prose**

Same checks as Task 2 Step 2.

- [ ] **Step 3: Run all four verification gates**

Same commands and expectations as Task 1 Step 9.

- [ ] **Step 4: Commit**

```bash
git add docs/engineering/troubleshooting.md
git commit -m "docs(lidia-tech/lidia-agents#536): author troubleshooting cluster 3 (output quality)"
```

(Standard body, `Refs lidia-tech/lidia-agents#536`, co-author trailer.)

---

### Task 4: Author cluster 4 (Measurement and change — entries 12-15) and final consistency pass

**Files:**
- Modify: `docs/engineering/troubleshooting.md`

**Interfaces:**
- Consumes: Tasks 2-3's clusters. Insert `## Measurement and change` after `## Output quality`, before the closing hand-off line. Read the whole page first and match the established voice.
- Produces: the complete 15-entry page.

- [ ] **Step 1: Write the cluster**

Headings verbatim:

```markdown
## Measurement and change

### It works in the demo but fails on real queries

### I changed the prompt and can't tell if it helped

### I don't trust my eval numbers

### My eval numbers moved and I changed nothing
```

Author each entry from these requirements:

- **Entry 12 (demo vs prod).** Causes: benchmark too narrow or contaminated (Part 7, "Build a dataset you can trust"); production inputs distributionally different, malformed, another language, longer documents (Part 7, dataset realism); no production feedback loop returning real sessions to development (Part 6, "Close the loop").
- **Entry 13 (prompt change flying blind).** Causes: no frozen benchmark to compare against (Part 7, "Run the loop" and "Grow the eval into a gate"); several things changed at once (Part 7, "Measure honestly"); prompt edits buried inside code commits with no rationale (Part 2, prompt changes in their own commit with the why).
- **Entry 14 (don't trust my eval).** Causes: the LLM judge disagreeing with human judgment (Part 7, "Use the LLM judge only where it agrees with the human"); a leaderboard that flips between runs, variance and too few samples (Part 7, "Measure honestly"); a rubric measuring the wrong behavior (Part 7, "Measure the behaviors that matter"). Close by naming the failure mode all three feed: false confidence (Part 7, "The enemy is false confidence").
- **Entry 15 (eval moved, nothing changed).** Causes: a silent provider-side model upgrade, the unpinned-dependency case (Part 9, "Depend only on what you can account for": pin model versions and record which model produced a result); dataset drift or contamination (Part 7, "Build a dataset you can trust"); the live external world changing under a web-touching eval (Part 7, "Measure honestly"). Folded facet: a deliberate model swap regressing the agent, which routes to the staged screening funnel (Part 7).

- [ ] **Step 2: Full-page consistency read**

Read `docs/engineering/troubleshooting.md` top to bottom and fix in place: voice drift between clusters (entry 3 is the model); the forward reference in entry 5 ("the tool-misuse entry below") now points at a real entry; every entry has heading + one diagnosis paragraph + routing bullets; no entry exceeds 6 sentences of diagnosis (7 for entry 7); the bridge, how-to-use, and hand-off from Task 1 still read correctly against the finished body.

- [ ] **Step 3: Style pass on the new prose**

Same checks as Task 2 Step 2, applied to the whole file.

- [ ] **Step 4: Run all four verification gates**

Same commands and expectations as Task 1 Step 9.

- [ ] **Step 5: Commit**

```bash
git add docs/engineering/troubleshooting.md
git commit -m "docs(lidia-tech/lidia-agents#536): author troubleshooting cluster 4 (measurement and change), complete the page"
```

(Standard body, `Refs lidia-tech/lidia-agents#536`, co-author trailer.)
