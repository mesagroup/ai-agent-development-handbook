# Handbook v1.1 Course Batch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fold the additive "AI Harness Engineering" course ideas into the AI Agent Development Handbook (`docs/engineering/`) as directive-with-reasons prose, per the approved spec.

**Architecture:** Prose-authoring plan, not code. Each task edits one handbook file, inserting pre-drafted prose at exact anchors, then runs the render + docs gates. The prose is drafted in full in each task (implementers place and lightly adapt it for local flow, they do not author from scratch), which is how word-budget and register control are held at plan time. No Python, no tests in the pytest sense; the "test" for every task is the handbook renderer and the docs-link checkers.

**Tech Stack:** Markdown; `scripts/render_handbook_artifact.py`; `scripts/check_docs.py`; `mkdocs build --strict`; `scripts/check_site_links.py`.

## Global Constraints

- No em-dashes anywhere in `docs/engineering/` (the renderer counts them; target is 0). Use commas, colons, or parentheses.
- No comma splices in new prose (join independent clauses with a colon, a semicolon, a conjunction, or split the sentence).
- One paragraph per source line: never hard-wrap prose; never reflow code blocks or tables.
- Cross-links inside the handbook use relative `.md` links (`[Part 2](codebase-structure.md)`); do NOT use `#anchor` links (the custom renderer concatenates parts; use prose directional words "above"/"below" for same-file references).
- Register: clipped imperative in section bodies, portable "how to" tone, no institutional "we". Do not touch the italicized narrative bridges/hand-offs.
- Word budget: the whole batch stays within roughly +1.5k prose words. The drafts below are already sized to this; do not expand them.
- Settled content decisions (do not renegotiate): industry "agent = model + harness" definition for the Part 4 paragraph with a Fowler footnote; bookend gates (spec review, merge) always on, only optional gates + involvement depth scale with criticality; mild Brandolini (agent-assisted core code, scaled oversight, not hand-write-only); cite *Accelerate*, no dated stats or charts.
- Every task ends by running the gates (Verification block) and committing with a `docs(<origin-repo>#533):` message and the trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`. NEVER pass shell comment lines (starting with `#`) to the Bash tool.

**Gate commands (run at the end of every task):**

```
uv run scripts/render_handbook_artifact.py --out /tmp/handbook-533.html
uv run python scripts/check_docs.py
uv run mkdocs build --strict
```

The renderer prints `sections: 10`, `em-dashes: 0`, `residual .md hrefs: 0` when clean. `check_docs.py` must report 0 dead links / 0 unindexed. `mkdocs build --strict` must pass (the handbook is excluded from the site; this only confirms no regression). Run `uv run python scripts/check_site_links.py site` once in the final task.

---

### Task 1: Part 1 (`lifecycle.md`) — criticality, small batches, review purpose, context extraction, deterministic division, TDD graft

**Files:**
- Modify: `docs/engineering/lifecycle.md`

This is the largest task (5 items + 2 grafts). Insert each block at its anchor. Anchors are current heading lines in the file.

- [ ] **Step 1: Insert "Keep batches small and the flow fast" after the "Front-load the judgment" section**

Locate the end of the `## Front-load the judgment` section (the paragraph beginning "Run task management on an issue tracker"), immediately before `## Decide the human-in-the-loop gates up front`. Insert this new section between them:

```markdown
## Keep batches small and the flow fast

Where the human's judgment goes is one lever; the *size* of what you hand off is another, set before any gate fires. An agent multiplies the code you can produce, which quietly revives the oldest anti-pattern there is: the giant branch nobody can review. A change too large to hold in one reading defeats the review protocol below, because a reviewer forced to skim approves what they cannot actually see. Counter it at the source: scope each issue narrowly enough that its diff stays reviewable. A hard cap on diff size is a legitimate backstop, but only a backstop; the mechanism is scoping the work small in the first place.

Then measure the whole distance, not the convenient part. Optimizing commit-to-deploy while idea-to-production stays slow moves a number without moving the outcome. The four DORA measures (deployment frequency, lead time for changes, change-failure rate, and time to restore) are a useful shared vocabulary for that whole-distance view. The durable evidence that small batches, loosely coupled architecture, and lightweight change approval predict delivery performance is in *Accelerate* (Forsgren, Humble, Kim): reach for the book, not a screenshotted chart whose numbers rot.
```

- [ ] **Step 2: Insert "Scale involvement to criticality" after the "Decide the human-in-the-loop gates up front" section**

Locate the end of the `## Decide the human-in-the-loop gates up front` section (the paragraph beginning "When an optional gate is off"), immediately before `## Step-by-step: one issue, end to end`. Insert this new section between them:

```markdown
## Scale involvement to criticality

Not every change deserves the same human attention, and spending it uniformly starves the risky change to over-supervise the trivial one. Scale involvement along two independent axes. The first is *how present the human is*: **in-the-loop** (co-design and approve each step), **on-the-loop** (let the agent run, monitor and audit the result, intervene on a signal), or **out-of-the-loop** (run behind guardrails and sample after the fact). The second is *how much the code matters*: a **core differentiator** (the logic that is the reason the product exists), **supporting** code, or a **commodity** integration any equivalent could replace.

Match one to the other. Core-differentiator code gets in-the-loop treatment, co-design and a second reviewer, because a subtle error there is expensive and the understanding must not live in one head. Supporting code runs on-the-loop; a commodity integration behind a good guardrail can run out-of-the-loop. This does *not* mean hand-writing the core yourself: even core-domain code is agent-assisted here (see [the stance](README.md)); what scales up with criticality is the *oversight and review*, not who types.

Two boundaries keep this from becoming a licence to cut corners. First, the two always-on bookend gates (spec review and the merge gate) never scale off, whatever the criticality: only the *optional* gates and the depth of implementation involvement move. Second, criticality is a different axis from reuse: a commodity utility can sit in the reusable core, and a core differentiator can live in a single agent's task layer ([Part 2](codebase-structure.md)). Classify a change on both, then place your attention accordingly.
```

- [ ] **Step 3: Add the context-extraction and architecture-forward sentences to step 2 of the step-by-step**

Find list item `2.` (`**Brainstorm into a spec.**`) in `## Step-by-step: one issue, end to end`. It currently ends with "After approval, post an issue comment linking the spec." Append these sentences to the same line (keep it one line, do not wrap):

```
Spec quality is bounded less by solo authoring skill than by how well context is extracted across product, engineering, and domain experts, so pull that knowledge out collaboratively: techniques like Event Storming, event modeling, or a lightweight architecture canvas surface it without importing enterprise DDD wholesale. Model live and low-fidelity, because the shared understanding forms in the room; handing the whole job to an agent to "write the doc" produces an artifact without the alignment that was the point. Where the change is architectural, use the architecture doc *forward*: sketch the post-change version and read the blast radius off it before committing to the approach.
```

- [ ] **Step 4: Add the throwaway-battery graft to the TDD section**

In `## TDD`, find the paragraph beginning "Ship new code **with** unit tests" (ends "exercise their pure helpers with unit tests too."). Immediately after it (still inside `## TDD`, before `### Chase caught regressions, not coverage percentage`), insert this paragraph:

```markdown
One exception earns its keep: for a pure like-for-like refactor or port, a throwaway battery that pins the *current* behaviour is legitimate scaffolding. Write it to prove the port changed nothing, then delete it once the old and new paths agree; it was a safety harness for the move, not a permanent test of the design.
```

- [ ] **Step 5: Add the SOP/deterministic-division sentence to "Prompt and SOP engineering"**

At the end of `## Prompt and SOP engineering` (after the second bullet, "Analyze SOPs for cognitive load…"), append this paragraph:

```markdown
And keep the division of labour sharp from the other side: reserve an SOP for judgment a deterministic tool cannot express, the heuristic, context-weighing steps where there is no rule to write. If a constraint *can* be written as a lint rule or a type, write the rule instead (the CI gates below handle it); an SOP is for the genuinely non-deterministic part, not for re-encoding what a checker already guarantees.
```

- [ ] **Step 6: Add the deterministic-first sentence to "CI and static analysis"**

At the very end of `## CI and static analysis` (after the paragraph ending "matches what the workflows actually require."), append this paragraph:

```markdown
Keep the labour on the right side of the line: never spend an agent on what a linter, formatter, or type-checker already enforces deterministically. A deterministic tool is faster, cheaper, and gives the same verdict every time on the job it was built for; an agent pointed at a linter's task is strictly worse at it.
```

- [ ] **Step 7: Add the review-purpose opening paragraph to "The code-review protocol"**

In `## The code-review protocol`, insert this paragraph as the new FIRST paragraph of the section, before the existing "The mechanical gates pass; what they cannot judge, the review does." paragraph:

```markdown
Before the mechanics, the purpose. When agents write most of the code, review is the moment a human is *forced* to understand what ships, which makes it the real guard against a codebase no one on the team actually comprehends. So review what the change *expresses*: its intent, its design, whether it fits the system and solves the right problem. How the code is *written* (formatting, naming, layout) is the CI gates' job, above, not a reviewer's. A review whose understanding one person silently absorbs has failed its primary purpose even when it catches a bug, because the point was to spread the understanding, not merely to filter defects.
```

- [ ] **Step 8: Add the criticality item to the pre-merge checklist**

In `## Pre-merge checklist`, add this item immediately after the existing "Explicit human "merge it" obtained…" line (keep list order otherwise):

```markdown
- [ ] Involvement depth matched the change's criticality; the bookend gates stayed on regardless.
```

- [ ] **Step 9: Run the gates and commit**

Run the three gate commands from Global Constraints against `/tmp/handbook-533.html`. Confirm `em-dashes: 0` and `residual .md hrefs: 0`, `check_docs.py` clean, `mkdocs build --strict` passes. Then:

```
git add docs/engineering/lifecycle.md
git commit -m "docs(<origin-repo>#533): Part 1 additions: criticality scaling, small batches, review purpose

Refs <origin-repo>#533"
```

---

### Task 2: Part 4 (`agent-harness.md`) — terminology paragraph

**Files:**
- Modify: `docs/engineering/agent-harness.md`

- [ ] **Step 1: Insert the terminology paragraph after the intro**

Find the intro paragraph beginning "Don't make a new agent re-solve model selection" (the paragraph ending "the reason reproducibility matters so much is in [Part 6](evaluation.md)."). It sits immediately before `## Build the harness, don't inline the plumbing`. Insert this new paragraph between them:

```markdown
A word on the term. Industry usage has converged on *agent = model + harness*: the model reasons, and the harness is everything built around it (tool dispatch, memory, configuration, sandboxing, the safeguards that keep it bounded). The agent framework gives you the base agentic loop; this part is the *extended* harness layered around that loop, which is what the title means. The word also travels in a broader sense, Fowler's ["harness engineering"](https://martinfowler.com/articles/harness-engineering.html), spanning guides that steer the model forward, sensors that feed results back, and the human steering between them: this handbook covers that wider envelope too, distributed across the lifecycle ([Part 1](lifecycle.md)), observability ([Part 5](observability.md)), and evaluation ([Part 6](evaluation.md)).
```

- [ ] **Step 2: Run the gates and commit**

Run the three gate commands. Confirm clean. Then:

```
git add docs/engineering/agent-harness.md
git commit -m "docs(<origin-repo>#533): Part 4 terminology paragraph (agent = model + harness; Fowler footnote)

Refs <origin-repo>#533"
```

---

### Task 3: Part 6 (`evaluation.md`) — maturity ladder, reliability bands, grader taxonomy

**Files:**
- Modify: `docs/engineering/evaluation.md`

- [ ] **Step 1: Add the grader-taxonomy sentences to "Measure the behaviors that matter"**

`## Measure the behaviors that matter` is a single paragraph ending "the security-surface counterpart is in [Part 8](security-supply-chain.md)." Append these sentences to that same line (keep one line):

```
Match the *grader* to the behavior too: some checks are **code-graded** (a deterministic assertion on the output: exact match, schema validity, a required citation present), some are **judge-graded** (an LLM rubric, but only where it has been calibrated against a human, below), and some are **trajectory-graded** (an assertion on the *path* the run took, for example that a forbidden tool was never called or that retrieval ran before generation). The trajectory grader is the only one that sees *how* the agent reached its answer rather than only whether the answer was right, which is what you need for behaviours the final output does not reveal.
```

- [ ] **Step 2: Extend the "Report variance" bullet in "Measure honestly" with per-case bands and pass^N**

In `## Measure honestly`, find the bullet beginning "**Report variance.**" (ends "reads as an improvement."). Append to that same line:

```
For pass/fail cases rather than scalar scores, report the same honesty a different way: run each case N times and record its reliability band (how many of N passed), because *k of N* separates a case that is flaky from one that is genuinely failing, which a single pass/fail hides. Alongside the per-case bands, report the strict **pass^N** aggregate (the probability that all N runs pass), the honest answer to "will this work every time" that an average of lucky runs flatters. How high that reliability bar must sit is a business decision tied to the change's criticality ([Part 1](lifecycle.md)): a commodity path tolerates a band a core differentiator cannot.
```

- [ ] **Step 2b: Verify the "Report variance" bullet contains no em-dash**

The inserted text uses "pass^N" and parentheses, no em-dash. Confirm visually before running gates.

- [ ] **Step 3: Insert "Grow the eval into a gate" after "Pick the approach that fits the decision"**

Find the end of `## Pick the approach that fits the decision` (the paragraph ending "spend expensive semantic evaluation only on candidates that already cleared the cheap gates."), immediately before `## Use the LLM judge only where it agrees with the human`. Insert this new section between them:

```markdown
## Grow the eval into a gate

An eval does not start life as a merge blocker; it earns that authority in stages. First run it **offline** against a fixed dataset, to answer a question you are asking deliberately. Once it is stable, run it in **shadow mode**: score real production traffic and log the result, but let nothing block on it, so you learn what the metric does on live inputs (and where it is noisy) before it can stop a merge. Only after it has proven trustworthy in shadow does it become a **merge-blocking CI gate**. Promote an eval past a rung it has not earned and you gate on noise, which teaches the team to ignore the gate, which is worse than having none.

At every rung the loop still feeds itself: a miss the eval let through in production becomes a new case in the dataset, so the gate that let it slip cannot let the same class slip twice. That is the same feedback loop this part opened with, now wired into the pipeline.
```

- [ ] **Step 4: Run the gates and commit**

Run the three gate commands. Confirm clean. Then:

```
git add docs/engineering/evaluation.md
git commit -m "docs(<origin-repo>#533): Part 6 additions: eval maturity ladder, k/N + pass^N bands, grader taxonomy

Refs <origin-repo>#533"
```

---

### Task 4: Part 7 (`documentation.md`) — ADR row, data-model artifact, diagrams-as-code

**Files:**
- Modify: `docs/engineering/documentation.md`

- [ ] **Step 1: Add the ADR row to the decision-trail artifact table**

In `## Keep the decision-trail artifacts`, the table has rows Spec, Plan, Story, Experiment, Results log. Insert the ADR row immediately after the **Plan** row (so the two "Forward" rows sit together):

```markdown
| **ADR** | One durable architectural decision, its alternatives, and the rationale for the choice, socialized with 1-3 readers before implementation. | Forward |
```

- [ ] **Step 2: Insert the ADR-boundary and data-model paragraphs after the table**

Immediately after the table (before the paragraph beginning "Don't skip the **story**"), insert these two paragraphs:

```markdown
An ADR is not a spec and not a story: a spec scopes one change and its acceptance, a story looks back at what a piece of work taught, and an ADR records a decision meant to *outlive* both, the kind a future contributor would otherwise reverse without knowing why it was made. Keep the boundary clean: architectural rationale (why this boundary, why this datastore, why not the obvious alternative) goes in the ADR; implementation-level rationale stays in the story.

Treat the data model itself as a first-class artifact in this set: a versioned, explicit description of the schemas the system works over, plus their known quirks and invariants, that both people and agents are pointed at. An agent left to infer the data model from scattered code will reinvent it wrong, and an undocumented quirk is a bug waiting for the next author who does not know it is there.
```

- [ ] **Step 3: Add the diagrams-as-code bullet to "Keep the living docs current too"**

In `## Keep the living docs current too`, the section is a bullet list (Module and symbol docstrings; The project's binding-rules file; Prompt / SOP changes). Add this bullet at the end of that list:

```markdown
- **Diagrams as code, generated from source**: keep any generated diagram in a text metalanguage (Mermaid, PlantUML) rather than a binary image, and regenerate it from the source of truth on merge. A diagram drawn by hand or by a model drifts from the code the moment either changes; one generated from the code cannot, and it stays diffable in review like the rest of the source.
```

- [ ] **Step 4: Run the gates and commit**

Run the three gate commands. Confirm clean. Then:

```
git add docs/engineering/documentation.md
git commit -m "docs(<origin-repo>#533): Part 7 additions: ADR artifact, data-model context artifact, diagrams-as-code

Refs <origin-repo>#533"
```

---

### Task 5: Part 8 (`security-supply-chain.md`) — least privilege for the agent

**Files:**
- Modify: `docs/engineering/security-supply-chain.md`

- [ ] **Step 1: Insert "Grant the agent the least privilege it needs" after the first-party-code section**

Find the end of `## First-party code: trace a path from source to sink` (the bullet ending "URL-host allowlisting against SSRF)."), immediately before `## Secrets: never commit them, and rotate: don't just delete`. Insert this new section between them:

```markdown
## Grant the agent the least privilege it needs

The rule above treats what a model or tool *returns* as untrusted. The other half of the agent's security surface is what it is *allowed to do*: its granted powers are an attack surface in their own right, and the handbook has so far said less about them than about its inputs. Reason about them explicitly.

The danger to avoid is concentrating the **lethal trifecta** in one agent: access to private data, exposure to untrusted content, and the ability to act on the outside world (to write, to spend, or to exfiltrate). Any one alone is ordinary; any two are manageable; all three in one agent mean a prompt injection carried in the untrusted content can read the private data and ship it out, with no further foothold required. Keep the three apart, and put a human gate on the acting edge whenever a task genuinely needs more than one of them at once.

- **Default to read-only.** A diagnostic, research, or analysis agent should get read-only tool and MCP access: it can look at everything and change nothing.
- **Grant write access narrowly.** Widen from read-only per tool and per purpose, never wholesale, and never grant an agent production or pipeline write access for convenience. That is the least-privilege rule the pipeline itself runs on (below), applied to the agent.
```

- [ ] **Step 2: Add the "Agent privileges" checklist group**

In `## Checklist: a security & supply-chain sweep`, the checklist has bold group labels (**First-party code**, **Secrets**, **Dependencies**, **Pipeline**, **Standing**). Insert this new group immediately after the **First-party code** group (after its last item "Dangerous sinks neutralized at the sink; input validated/canonicalized at the boundary.") and before **Secrets**:

```markdown
**Agent privileges**

- [ ] Each agent audited against the **lethal trifecta**: no single agent holds private-data access, untrusted-content exposure, and an external-action power at once without a human gate.
- [ ] Diagnostic / research agents default to **read-only** tool and MCP access.
- [ ] No **convenience write grants** to production or the pipeline; write access is per-tool and per-purpose.
```

- [ ] **Step 3: Run the gates and commit**

Run the three gate commands. Confirm clean. Then:

```
git add docs/engineering/security-supply-chain.md
git commit -m "docs(<origin-repo>#533): Part 8 addition: least privilege for the agent (lethal trifecta)

Refs <origin-repo>#533"
```

---

### Task 6: `README.md` sycophancy graft + final whole-handbook gate

**Files:**
- Modify: `docs/engineering/README.md`

- [ ] **Step 1: Add the sycophancy clause to throughline 1**

In `### 1. Evidence over intuition: the enemy is false confidence`, find the sentence ending "which is worse, because confidence is when you stop looking." Immediately after it (same line, same paragraph), insert this sentence:

```
(AI deepens the trap: a model tends to *agree* with the premise it is handed, so its readiness to confirm your idea is not evidence for it.)
```

- [ ] **Step 2: Run ALL gates including the site-link crawler**

```
uv run scripts/render_handbook_artifact.py --out /tmp/handbook-533.html
uv run python scripts/check_docs.py
uv run mkdocs build --strict
uv run python scripts/check_site_links.py site
```

Confirm the renderer prints `sections: 10`, `em-dashes: 0`, `residual .md hrefs: 0`; `check_docs.py` and `check_site_links.py` clean; `mkdocs build --strict` passes.

- [ ] **Step 3: Word-budget check**

Run `git diff origin/main -- docs/engineering/ | grep -c '^+'` for a rough added-line count, and skim the diff to confirm total added prose is near +1.5k words, not far over. If materially over, trim the least-load-bearing sentences (the plan's drafts are already sized, so this should pass).

- [ ] **Step 4: Commit**

```
git add docs/engineering/README.md
git commit -m "docs(<origin-repo>#533): name AI sycophancy as a false-confidence hazard (throughline 1)

Refs <origin-repo>#533"
```

---

## Notes for the executor

- Tasks are independent per file and can run in any order, but Task 1 is the largest; do it first so the biggest review lands early.
- Every inserted block is drafted to final quality. Adapt only for local sentence flow (a connective word, matching an adjacent list's punctuation style); do not rewrite or expand, the word budget depends on it.
- The single most likely gate failure is an accidental em-dash introduced by an editor's smart-quotes. If the renderer reports `em-dashes: N > 0`, grep the changed file for the character and replace with a comma, colon, or parenthetical.
- If any cross-link (`codebase-structure.md`, `README.md`, `lifecycle.md`, `evaluation.md`, `observability.md`, `security-supply-chain.md`) fails `check_docs.py`, confirm the target file name is spelled exactly as on disk.
