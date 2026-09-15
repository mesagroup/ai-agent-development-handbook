# Handbook Narrative Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the AI Agent Development Handbook (`docs/engineering/`) around a narrative spine (the life of one change), with four named throughlines, a throughline x part matrix, per-part bridges, and a single part reorder (three-layer model 6 -> 3), per the approved spec `docs/superpowers/specs/2026-07-27-handbook-narrative-restructure-design.md` (issue `<origin-repo>#531`).

**Architecture:** Pure documentation work plus one mechanical script edit. Six tasks: (1) renumber and reorder the parts everywhere, (2) rewrite the README, (3) add bridges and hand-offs to all eight parts, (4) rework Part 1 internally, (5) rework the observability part internally, (6) final verification sweep. All prose that a task inserts is given verbatim in this plan; the implementer transcribes it.

**Tech Stack:** Markdown, Python (one list literal in `scripts/render_handbook_artifact.py`), pytest, uv.

## Global Constraints

- **No em-dashes anywhere in `docs/engineering/` or in any text this plan inserts.** The render script counts them; its report must show `em-dashes: 0`.
- **No comma splices in new or retouched prose.** Use a colon, a semicolon, parentheses, or a restructured sentence instead.
- **Markdown source is not hard-wrapped**: one paragraph is one source line.
- **Bridge convention:** each part's bridge is a single *italicized paragraph* (whole paragraph wrapped in `*...*`), inserted immediately after the H1 line (with a blank line between), before the first body paragraph. Not a blockquote.
- **Hand-off convention:** a single italicized paragraph beginning `*Next:` (or `*And the loop begins again:` for Part 8), inserted immediately before the `## See also` heading (with blank lines around it).
- **Part bodies are untouched** except: the renumbering edits in Task 1, the scoped Task 4 edits (lifecycle), and the scoped Task 5 edits (observability). Do not "improve" other prose in passing.
- **Insert all plan-provided text verbatim.** If an old_string given here does not match the file, stop and report; do not improvise a similar edit.
- **Renumbering map (old -> new):** harness 3 -> 4, observability 4 -> 5, evaluation 5 -> 6, three-layer 6 -> 3. Parts 1, 2, 7, 8 keep their numbers.
- **Commit message prefix:** `docs(<origin-repo>#531): ...`, one commit per task, with the trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- **Verification gates** (used repeatedly): `uv run scripts/render_handbook_artifact.py --out /tmp/handbook.html` must report `sections: 9`, `em-dashes: 0`, `residual .md hrefs: 0`; `uv run python scripts/check_docs.py` must pass; `uv run pytest tests/scripts/test_render_handbook_artifact.py -q` must pass.

---

### Task 1: Renumber and reorder the parts everywhere

**Files:**
- Modify: `docs/engineering/three-layer-model.md`
- Modify: `docs/engineering/agent-harness.md`
- Modify: `docs/engineering/observability.md`
- Modify: `docs/engineering/evaluation.md`
- Modify: `docs/engineering/codebase-structure.md`
- Modify: `docs/engineering/lifecycle.md`
- Modify: `docs/engineering/documentation.md`
- Modify: `docs/engineering/security-supply-chain.md`
- Modify: `docs/engineering/README.md` (minimal renumber patch only; full rewrite is Task 2)
- Modify: `scripts/render_handbook_artifact.py` (the `PARTS` list)
- Test: existing `tests/scripts/test_render_handbook_artifact.py` (no test changes; must stay green)

**Interfaces:**
- Consumes: nothing (first task).
- Produces: a handbook whose H1s read Part 1 lifecycle, Part 2 codebase-structure, Part 3 three-layer-model, Part 4 agent-harness, Part 5 observability, Part 6 evaluation, Part 7 documentation, Part 8 security-supply-chain, with every cross-reference consistent. Later tasks assume this numbering.

Apply each edit below with an exact-match replacement. Do NOT use a global sed for `Part N` (sequential number swaps collide: 3 -> 4 then 4 -> 5 would double-bump). Each edit is anchored by enough surrounding text to be unique.

- [ ] **Step 1: `three-layer-model.md` (part 6 -> 3)**

| old_string | new_string |
|---|---|
| `# Part 6. The Three-Layer Document Model` | `# Part 3. The Three-Layer Document Model` |
| `far less noisy than one ill-defined end-to-end number ([Part 5](evaluation.md))` | `far less noisy than one ill-defined end-to-end number ([Part 6](evaluation.md))` |
| `- [Part 5. Evaluation](evaluation.md), why separable layers are separately evaluable.` | `- [Part 6. Evaluation](evaluation.md), why separable layers are separately evaluable.` |

- [ ] **Step 2: `agent-harness.md` (part 3 -> 4)**

| old_string | new_string |
|---|---|
| `# Part 3. The Extended Agent Harness` | `# Part 4. The Extended Agent Harness` |
| `the reason reproducibility matters so much is in [Part 5](evaluation.md)` | `the reason reproducibility matters so much is in [Part 6](evaluation.md)` |
| `This indirection is what makes model screening (see [Part 5](evaluation.md)) practical` | `This indirection is what makes model screening (see [Part 6](evaluation.md)) practical` |
| `measure it against a frozen benchmark, one variable at a time (see [Part 5](evaluation.md))` | `measure it against a frozen benchmark, one variable at a time (see [Part 6](evaluation.md))` |
| `one backed by an anecdote (see [Part 5](evaluation.md))` | `one backed by an anecdote (see [Part 6](evaluation.md))` |
| `not as cheap as its own token count suggests (see [Part 4](observability.md))` | `not as cheap as its own token count suggests (see [Part 5](observability.md))` |
| `the production feedback loop in [Part 4](observability.md) possible` | `the production feedback loop in [Part 5](observability.md) possible` |
| `- [Part 4. Observability](observability.md), the per-(sub)agent metrics` | `- [Part 5. Observability](observability.md), the per-(sub)agent metrics` |
| `- [Part 5. Evaluation](evaluation.md), why headless, reproducible` | `- [Part 6. Evaluation](evaluation.md), why headless, reproducible` |

- [ ] **Step 3: `observability.md` (part 4 -> 5)**

| old_string | new_string |
|---|---|
| `# Part 4. Observability` | `# Part 5. Observability` |
| `you cannot decide ([Part 5](evaluation.md)) without numbers you trust` | `you cannot decide ([Part 6](evaluation.md)) without numbers you trust` |
| `an independent quality evaluation ([Part 5](evaluation.md))` | `an independent quality evaluation ([Part 6](evaluation.md))` |
| `the reliability defaults in [Part 3](agent-harness.md) are the fixes` | `the reliability defaults in [Part 4](agent-harness.md) are the fixes` |
| `- [Part 3. Agent harness](agent-harness.md), bounded external calls` | `- [Part 4. Agent harness](agent-harness.md), bounded external calls` |
| `- [Part 5. Evaluation](evaluation.md), pairing efficiency` | `- [Part 6. Evaluation](evaluation.md), pairing efficiency` |

- [ ] **Step 4: `evaluation.md` (part 5 -> 6)**

| old_string | new_string |
|---|---|
| `# Part 5. Evaluation: How to Decide` | `# Part 6. Evaluation: How to Decide` |
| `(see [Part 4. Observability](observability.md) on full-cost accounting)` | `(see [Part 5. Observability](observability.md) on full-cost accounting)` |
| `Drive the frozen headless CLI ([Part 3](agent-harness.md))` | `Drive the frozen headless CLI ([Part 4](agent-harness.md))` |
| `- [Part 4. Observability](observability.md), instrument before you tune` | `- [Part 5. Observability](observability.md), instrument before you tune` |
| `- [Part 6. Three-layer model](three-layer-model.md), separately-evaluable layers.` | `- [Part 3. Three-layer model](three-layer-model.md), separately-evaluable layers.` |

- [ ] **Step 5: `codebase-structure.md` (references only; stays Part 2)**

| old_string | new_string |
|---|---|
| `the eval framework, and the integrations as-is (see [Part 3](agent-harness.md))` | `the eval framework, and the integrations as-is (see [Part 4](agent-harness.md))` |
| `a "run the cheap profile" instruction unambiguous (see [Part 3](agent-harness.md))` | `a "run the cheap profile" instruction unambiguous (see [Part 4](agent-harness.md))` |
| `- [Part 3. The extended agent harness](agent-harness.md), the shared machinery agents reuse.` | `- [Part 4. The extended agent harness](agent-harness.md), the shared machinery agents reuse.` |
| `- [Part 6. The three-layer document model](three-layer-model.md), the same reusable-core-vs-task-layer idea, one level down.` | `- [Part 3. The three-layer document model](three-layer-model.md), the same reusable-core-vs-task-layer idea, one level down.` |

- [ ] **Step 6: `lifecycle.md` (references only; stays Part 1)**

| old_string | new_string |
|---|---|
| `an LLM-as-judge rubric, see [Part 5](evaluation.md)). Run it on the branch, before merge, with a **cheap** configuration (a mock or lighter backend, see [Part 3](agent-harness.md))` | `an LLM-as-judge rubric, see [Part 6](evaluation.md)). Run it on the branch, before merge, with a **cheap** configuration (a mock or lighter backend, see [Part 4](agent-harness.md))` |
| `the same discipline that makes an eval trustworthy ([Part 5](evaluation.md))` | `the same discipline that makes an eval trustworthy ([Part 6](evaluation.md))` |
| `[Part 4. Observability](observability.md) (no swallowed exceptions) · [Part 5. Evaluation](evaluation.md) (the quality gate uses a checklist; deeper decisions use the eval loop)` | `[Part 5. Observability](observability.md) (no swallowed exceptions) · [Part 6. Evaluation](evaluation.md) (the quality gate uses a checklist; deeper decisions use the eval loop)` |

- [ ] **Step 7: `documentation.md` (references only; stays Part 7)**

| old_string | new_string |
|---|---|
| `the evidence half of "evidence over intuition" ([Part 5](evaluation.md))` | `the evidence half of "evidence over intuition" ([Part 6](evaluation.md))` |
| `- [Part 5. Evaluation](evaluation.md), the loop that the results log and stories feed.` | `- [Part 6. Evaluation](evaluation.md), the loop that the results log and stories feed.` |

- [ ] **Step 8: `security-supply-chain.md` (references only; stays Part 8)**

| old_string | new_string |
|---|---|
| `- [Part 4. Observability](observability.md), errors that don't leak secrets/PII` | `- [Part 5. Observability](observability.md), errors that don't leak secrets/PII` |
| `- [Part 5. Evaluation](evaluation.md), behavioral injection-resistance as an eval dimension.` | `- [Part 6. Evaluation](evaluation.md), behavioral injection-resistance as an eval dimension.` |

- [ ] **Step 9: `README.md` minimal renumber patch** (keeps the repo consistent until Task 2 rewrites this file)

| old_string | new_string |
|---|---|
| `This is the subject of [Part 5. Evaluation](evaluation.md), but its discipline leaks into everything` | `This is the subject of [Part 6. Evaluation](evaluation.md), but its discipline leaks into everything` |

Then reorder and renumber the parts table rows. Replace this block (rows 3 through 6 of the table in the `## The parts` section):

```markdown
| **[3. The extended agent harness](agent-harness.md)** | The capabilities a good agent setup provides: provider-agnostic model selection, configuration and named profiles, headless CLI execution, cheap/mock backends, and bounded external calls. |
| **[4. Observability](observability.md)** | Instrument before you tune; keep observability out of the model's context; per-(sub)agent tokens, timing, and cost; full-cost accounting; and the production → development feedback loop. |
| **[5. Evaluation: how to decide](evaluation.md)** | Build → measure → decide → re-measure. Trustworthy datasets, variance and cost, which method fits which decision, LLM-as-judge vs human-in-the-loop, evaluating a multi-agent system unit by unit, and escalation ladders. |
| **[6. The three-layer document model](three-layer-model.md)** | Why a generic, domain-independent decomposition (intrinsic structure / domain entities / workflow knowledge) is the right organizing principle for document-AI, and the contracts (engine-agnostic representation, stable IDs, versioned enrichment) that make it pay off. |
```

with:

```markdown
| **[3. The three-layer document model](three-layer-model.md)** | Why a generic, domain-independent decomposition (intrinsic structure / domain entities / workflow knowledge) is the right organizing principle for document-AI, and the contracts (engine-agnostic representation, stable IDs, versioned enrichment) that make it pay off. |
| **[4. The extended agent harness](agent-harness.md)** | The capabilities a good agent setup provides: provider-agnostic model selection, configuration and named profiles, headless CLI execution, cheap/mock backends, and bounded external calls. |
| **[5. Observability](observability.md)** | Instrument before you tune; keep observability out of the model's context; per-(sub)agent tokens, timing, and cost; full-cost accounting; and the production → development feedback loop. |
| **[6. Evaluation: how to decide](evaluation.md)** | Build → measure → decide → re-measure. Trustworthy datasets, variance and cost, which method fits which decision, LLM-as-judge vs human-in-the-loop, evaluating a multi-agent system unit by unit, and escalation ladders. |
```

- [ ] **Step 10: reorder `PARTS` in `scripts/render_handbook_artifact.py`**

Replace:

```python
PARTS: list[tuple[str, str, str]] = [
    ("top", "README", "Overview &amp; stance"),
    ("p1", "lifecycle", "Development lifecycle"),
    ("p2", "codebase-structure", "Codebase structure"),
    ("p3", "agent-harness", "The agent harness"),
    ("p4", "observability", "Observability"),
    ("p5", "evaluation", "Evaluation"),
    ("p6", "three-layer-model", "Three-layer model"),
    ("p7", "documentation", "Documentation"),
    ("p8", "security-supply-chain", "Security &amp; supply chain"),
]
```

with:

```python
PARTS: list[tuple[str, str, str]] = [
    ("top", "README", "Overview &amp; stance"),
    ("p1", "lifecycle", "Development lifecycle"),
    ("p2", "codebase-structure", "Codebase structure"),
    ("p3", "three-layer-model", "Three-layer model"),
    ("p4", "agent-harness", "The agent harness"),
    ("p5", "observability", "Observability"),
    ("p6", "evaluation", "Evaluation"),
    ("p7", "documentation", "Documentation"),
    ("p8", "security-supply-chain", "Security &amp; supply chain"),
]
```

(The `"Overview &amp; stance"` label is updated in Task 2, when the README's stance section is folded into the story.)

- [ ] **Step 11: verify**

Run each of the following and confirm the expected output:

```bash
grep -h "^# Part" docs/engineering/*.md | sort
```
Expected exactly (sorted):
```
# Part 1. The Development Lifecycle
# Part 2. Codebase Structure
# Part 3. The Three-Layer Document Model
# Part 4. The Extended Agent Harness
# Part 5. Observability
# Part 6. Evaluation: How to Decide
# Part 7. Documentation & Knowledge Capture
# Part 8. Security, Dependencies & Supply Chain
```

```bash
grep -nE "Part 3\]\(agent-harness|Part 4\]\(observability|Part 5\]\(evaluation|Part 6\]\(three-layer|Part 3\. The extended|Part 4\. Observability|Part 5\. Evaluation|Part 6\. (The )?[Tt]hree-layer" docs/engineering/*.md
```
Expected: no output (all stale pairings gone; exit code 1).

```bash
uv run scripts/render_handbook_artifact.py --out /tmp/handbook.html
uv run python scripts/check_docs.py
uv run pytest tests/scripts/test_render_handbook_artifact.py -q
uv run ruff check scripts/render_handbook_artifact.py && uv run ruff format --check scripts/render_handbook_artifact.py
```
Expected: render reports `sections: 9` and `residual .md hrefs: 0` and `em-dashes: 0`; docs check passes; tests pass; ruff clean.

- [ ] **Step 12: commit**

```bash
git add docs/engineering/ scripts/render_handbook_artifact.py
git commit -m "docs(<origin-repo>#531): renumber handbook parts; three-layer model moves 6 -> 3

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Rewrite the README (story, four throughlines, matrix)

**Files:**
- Modify: `docs/engineering/README.md` (full rewrite via Write)
- Modify: `scripts/render_handbook_artifact.py` (one label string)
- Modify: `docs/README.md` (the "How we work" blurb in the repo-only section)

**Interfaces:**
- Consumes: Task 1's numbering (the story and the tables below use it).
- Produces: the four throughline names later tasks reference in bridges: *evidence over intuition*, *capture the trail*, *the reusable core vs. the disposable task layer*, *make the standard executable*.

- [ ] **Step 1: replace the full content of `docs/engineering/README.md`** with exactly:

````markdown
# AI Agent Development Handbook

How to build software and AI agents here, and why. Read each section as a set of **directives backed by their reasons**: it states what to do, then why the practice earns its place. The reasons matter (they are what let you apply a rule to a case it doesn't literally cover), but when you just need to act, the directives and the checklists are the operational surface.

The practices are meant to be portable. Some are supported by shared infrastructure we maintain (a model catalog, a configuration system, a run harness), but nothing below *depends* on it: a project that reuses none of it should still recognize every directive as its own. Where a section describes a capability, read it as "here is what a good setup provides, and what to build or demand if you don't have it", not "here is our specific tool."

## The story of a change

Every part of this handbook attaches to one story: the life of a single change. Follow it once, end to end, and the eight parts stop being a list of best practices; they become the stations where the change (and you) will need them.

It starts with an idea. A bug report comes in, an eval number dips, a user asks for a feature. The idea becomes an **issue**, because work that is not traceable to an issue evaporates: nobody can find its reasoning later, and nobody notices when it silently dies. Before any code exists, the issue becomes a **spec**: what exactly are we building, and how will we know it is right? We stop here, deliberately, for a human to approve it. This is the cheapest moment in the whole story to discover we are building the wrong thing; every later stage multiplies the cost of that discovery. Then the spec becomes a **plan**: the work decomposed into tasks so complete that an implementer with zero context can execute them, and today that implementer is increasingly an agent. You are not hand-writing every line anymore; you direct agents that write most of them. Raising the level of abstraction does not abolish the hard work: it relocates it upward, into the spec, the plan, the review, and the judgment calls between them. [Part 1](lifecycle.md) is this path in operational detail: the gates, the reviews, and the disciplines that keep delegation from becoming guessing at scale.

The change needs a home, and the home has a shape. It lands in a codebase layered by reuse: a reusable core below, task-shaped applications above, dependencies pointing only toward the core, never sideways and never in a cycle ([Part 2](codebase-structure.md)). That shape decides the change's blast radius, and whether the next agent costs a prompt and its tools or a fresh copy of all the plumbing. If the change touches documents (a contract, a judgment, an invoice), it meets the same shape again inside the data: intrinsic structure that fully generalizes, a sparse vocabulary of domain entities, and a disposable task layer on top ([Part 3](three-layer-model.md)). And when it runs, it runs on machinery no change should ever rebuild: model aliases instead of hard-coded IDs, named configuration profiles, a headless CLI, cheap mock backends, external calls that are bounded by default ([Part 4](agent-harness.md)).

Implemented, tested, reviewed, merged. That is half the story, and the easy half. Now the change ships and starts doing things no unit test can see: fetching, spending, taking seconds and dollars in places you did not predict. The run records tell you what it actually did (what it fetched, what it used, what it cost, where its time went), because we instrument before we tune and keep the instruments out of the model's context ([Part 5](observability.md)). And then comes the question the whole handbook exists to answer honestly: **is the product actually better?** Not "do the tests pass": a change can be green on every unit test and still make an agent measurably worse. Better means measured, against a dataset the change did not get to define, with variance reported and the full cost on the table ([Part 6](evaluation.md)).

Here the loop closes. What the measurement teaches (a new failure form, a surprising cost, an assumption that did not survive contact with production) becomes the next issue. What the change leaves behind (the spec, the plan, a story of what surprised us, a recorded result) is the trail that lets someone who was not there, including a future you and the next agent, recover the decision and its evidence ([Part 7](documentation.md)). And over every change, not just this one, stands the obligation that no test and no eval will enforce: keeping the machine safe, from your own code's trust boundaries to your dependency graph to the pipeline that builds you ([Part 8](security-supply-chain.md)).

Do not expect the loop to terminate. That the story ends where it began is not a defect; it is how the system stays honest as the data, the models, and the team drift.

### The parts, at a glance

| Part | Role in the story |
|---|---|
| **[1. Development lifecycle](lifecycle.md)** | The spine: issue to spec to plan to implementation to review to merge, with the human gates placed where they pay. |
| **[2. Codebase structure](codebase-structure.md)** | The change needs a home: layered tiers, acyclic dependencies, composition over forking. |
| **[3. The three-layer document model](three-layer-model.md)** | The same shape inside the domain: intrinsic structure, domain entities, workflow knowledge. |
| **[4. The extended agent harness](agent-harness.md)** | The machinery the change runs on: aliases, profiles, headless CLIs, mocks, bounded calls. |
| **[5. Observability](observability.md)** | The change ships: instrument before you tune, account for the full cost. |
| **[6. Evaluation: how to decide](evaluation.md)** | The loop closes: was it actually better, measured against a dataset you trust? |
| **[7. Documentation & knowledge capture](documentation.md)** | What the change leaves behind: the trail that outlives the moment. |
| **[8. Security, dependencies & supply chain](security-supply-chain.md)** | The standing obligation: safe code, accounted dependencies, a trustworthy pipeline. |

## The four throughlines

Almost every directive in the parts is an application of one of four ideas. Internalize these and the rest follows; when a directive and reality collide, the throughline is how you decide.

### 1. Evidence over intuition: the enemy is false confidence

Treat every non-trivial change to an agent, a prompt, or an extractor as a *hypothesis*: "this will be better." "Better" only means something against a metric, and a metric is only trustworthy if the dataset it runs on was fixed independently of the change under test. Guard against **false** confidence, not the mere absence of it: the naive paths (add patterns until the suite is green, tune a prompt to the one example in front of you, ship the model that impressed in a demo) do not leave you uncertain; they leave you confidently wrong, which is worse, because confidence is when you stop looking. So make the yardstick exist *before* the decision: the test suite before the code, the dataset and the metric before the model or prompt change. [Part 6](evaluation.md) is this idea as a method; [Part 5](observability.md) is its precondition (instrument before you tune); and its discipline leaks into everything else.

### 2. Capture the trail: a decision and its evidence should outlive the moment

Work in the open and write things down: a spec before code, a plan before implementation, a story after a piece of work lands, a recorded result after an experiment. The point is not ceremony. It is that a decision made six months ago, and the evidence that justified it, must be recoverable by someone who was not there, including your future self and the next agent dispatched with zero history. [Part 7](documentation.md) is this idea made concrete; [Part 1](lifecycle.md)'s gates are where the artifacts get produced.

### 3. The reusable core vs. the disposable task layer

Sort everything you build by how much of it carries over to the next task: keep the reusable core sparse and stable, keep the task layer rich and disposable, and let dependencies point only toward the core. The alternative is one workflow's assumptions quietly baked into shared code, where they couple every other consumer and tax every new agent with plumbing it should have inherited. [Part 2](codebase-structure.md) applies this to the module graph, [Part 3](three-layer-model.md) to document knowledge, and [Part 4](agent-harness.md) to the machinery agents share.

### 4. Make the standard executable

Whenever you fix a class of problem, ask what stops it coming back, and prefer the answer that is a gate: encode the standard as an executable check wired into CI and pre-commit, rather than leaving it to memory and review diligence. A rule a human has to remember eventually lapses; a rule the pipeline enforces does not. [Part 1](lifecycle.md) builds the gates into the lifecycle, [Part 7](documentation.md) turns docs hygiene into checkers, and [Part 8](security-supply-chain.md) turns every security fix into one. The periodic audit is the counterpart, catching what no gate was written for.

### Where each throughline lives

The map of throughlines to parts (● a primary home, ○ drawn on):

| Part | Evidence over intuition | Capture the trail | Core vs. task layer | Executable standards |
|---|:-:|:-:|:-:|:-:|
| 1 Lifecycle | ○ | ● | | ● |
| 2 Codebase structure | | | ● | ○ |
| 3 Three-layer model | ○ | | ● | |
| 4 Agent harness | ○ | | ● | |
| 5 Observability | ● | ○ | | |
| 6 Evaluation | ● | ○ | | |
| 7 Documentation | | ● | | ○ |
| 8 Security | ○ | | | ● |

## How to use this handbook

- **Follow the imperatives.** Each part is written as instructions. Do what they say; the prose next to each one tells you why, so you can adapt it when your case is off-pattern.
- **Use the checklists as the working surface.** Most parts end with a checklist. Paste it into a PR description, an issue, or a review comment and tick it. Where a part describes a procedure (the lifecycle, an eval run, a security sweep), it also gives a step-by-step you can run top to bottom.
- **Treat the reasons as load-bearing, not decoration.** A rule you follow without knowing why is a rule you will misapply at the first edge case. When a directive and reality collide, the *why* is how you decide.
- **Enter anywhere.** The story above is the recommended first read, but every part opens by locating itself in the story and stands alone; you can land on any part cold, mid-task, and use it.

## Where the binding rules live

This handbook explains and connects; it teaches the reasoning. The *binding*, project-specific rules (exact coding standards, review thresholds, the merge checklist, the git workflow) belong in your project's rules file: the file your team and your coding agents both read as authoritative. When this handbook and that file disagree, the rules file wins, and the mismatch is a docs bug to fix (see [Part 7](documentation.md)).
````

- [ ] **Step 2: update the sidebar label in `scripts/render_handbook_artifact.py`**

| old_string | new_string |
|---|---|
| `("top", "README", "Overview &amp; stance"),` | `("top", "README", "Overview &amp; the story"),` |

- [ ] **Step 3: update the handbook blurb in `docs/README.md`**

| old_string | new_string |
|---|---|
| `**How we work** — a principled, project-agnostic vademecum of how we build software and AI agents, and why (the two throughlines: evidence over intuition; capture the trail). Maintained under `engineering/` and shipped as a **standalone self-contained HTML artifact** rendered by `scripts/render_handbook_artifact.py`, so it is deliberately not duplicated in the built docs site. Parts: development lifecycle; codebase structure; the extended agent harness; observability; evaluation (how to decide); the three-layer document model; documentation & knowledge capture; security, dependencies & supply chain. Browse the source under `engineering/`.` | `**How we work** — a principled, project-agnostic vademecum of how we build software and AI agents, and why, told along the life of one change and organized by four throughlines (evidence over intuition; capture the trail; reusable core vs. disposable task layer; make the standard executable). Maintained under `engineering/` and shipped as a **standalone self-contained HTML artifact** rendered by `scripts/render_handbook_artifact.py`, so it is deliberately not duplicated in the built docs site. Parts: development lifecycle; codebase structure; the three-layer document model; the extended agent harness; observability; evaluation (how to decide); documentation & knowledge capture; security, dependencies & supply chain. Browse the source under `engineering/`.` |

(Note: the em-dash after `**How we work**` is pre-existing style in `docs/README.md`, which is outside the handbook's no-em-dash rule. Keep it.)

- [ ] **Step 4: verify**

```bash
uv run scripts/render_handbook_artifact.py --out /tmp/handbook.html
uv run python scripts/check_docs.py
uv run pytest tests/scripts/test_render_handbook_artifact.py -q
grep -c "—" docs/engineering/README.md
```
Expected: render reports `sections: 9`, `em-dashes: 0`, `residual .md hrefs: 0`; docs check passes; tests pass; the grep reports `0` (exit code 1 with count 0 is fine).

- [ ] **Step 5: commit**

```bash
git add docs/engineering/README.md scripts/render_handbook_artifact.py docs/README.md
git commit -m "docs(<origin-repo>#531): rewrite handbook README: the story of a change, four throughlines, matrix

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Add bridges and hand-offs to all eight parts

**Files:**
- Modify: all eight `docs/engineering/*.md` part files (not README.md)

**Interfaces:**
- Consumes: Task 1 numbering; Task 2 throughline names.
- Produces: the bridge/hand-off convention Tasks 4 and 5 must preserve when editing lifecycle.md and observability.md.

For each part: insert the **bridge** as a new paragraph immediately after the H1 line (blank line between H1 and bridge, blank line after bridge, existing first paragraph unchanged below it). Insert the **hand-off** as a new paragraph immediately before the `## See also` heading (blank lines around it). Insert the text exactly as given; every bridge and hand-off is one italicized paragraph.

- [ ] **Step 1: `lifecycle.md`**

Bridge (after `# Part 1. The Development Lifecycle`):

```markdown
*Here the story begins: an idea on its way to becoming a merged, verified change. This part is the handbook's spine, the one path every piece of work travels, with the human judgment placed at the moments where it pays most. Two throughlines run through it end to end: the trail you capture at every step, and the standards you make executable so that the path holds without heroics.*
```

Hand-off (before `## See also`):

```markdown
*Next: the change needs a home, and the shape of that home decides how cheap every future change will be. [Part 2. Codebase structure](codebase-structure.md).*
```

- [ ] **Step 2: `codebase-structure.md`**

Bridge (after `# Part 2. Codebase Structure`):

```markdown
*Your change is specced and planned; now it needs a home. Whether it lands cleanly or ripples into places it had no business touching is decided by the structure it meets on arrival. This part gives that structure one organizing idea (the reusable core versus the disposable task layer) and one invariant that holds the idea in place.*
```

Hand-off (before `## See also`):

```markdown
*Next: the same core-versus-task-layer shape, one level down, inside the documents your agents work on. [Part 3. The three-layer document model](three-layer-model.md).*
```

- [ ] **Step 3: `three-layer-model.md`**

Bridge (after `# Part 3. The Three-Layer Document Model`):

```markdown
*If your change touches documents, the codebase's shape repeats inside the data. This part draws the same core-versus-task-layer boundary through document knowledge itself: what generalizes to every document, what generalizes across a domain, and what belongs to a single workflow. Hold the boundary and a failure stays localizable to a layer; collapse it and the system just fails, nowhere in particular.*
```

Hand-off (before `## See also`):

```markdown
*Next: the machinery every change runs on and none should rebuild. [Part 4. The extended agent harness](agent-harness.md).*
```

- [ ] **Step 4: `agent-harness.md`**

Bridge (after `# Part 4. The Extended Agent Harness`):

```markdown
*Your change is about to run: as an agent, or through one. Between it and the model sits machinery that is the same for every agent (model selection, configuration, entry points, reliability), which is exactly why it should belong to none of them. This part is the shared harness: the core-versus-task-layer throughline applied to the plumbing, and, through the headless CLI and the cheap backends, the precondition for every measurement in [Part 6](evaluation.md).*
```

Hand-off (before `## See also`):

```markdown
*Next: the change ships, and starts doing things no unit test can see. [Part 5. Observability](observability.md).*
```

- [ ] **Step 5: `observability.md`**

Bridge (after `# Part 5. Observability`):

```markdown
*The change is merged and running, and it is now doing things no test asserted: fetching, spending, taking time in places nobody predicted. Before anyone asks whether it made the product better, you need to see what it actually does. This part is the evidence throughline's first half: instrument before you tune, and keep the instruments from disturbing the thing they observe.*
```

Hand-off (before `## See also`):

```markdown
*Next: the numbers are in hand; now the question they exist for: is it actually better? [Part 6. Evaluation](evaluation.md).*
```

- [ ] **Step 6: `evaluation.md`**

Bridge (after `# Part 6. Evaluation: How to Decide`):

```markdown
*Everything so far was preparation for one question: did the change actually make the product better? Green tests cannot answer it, and neither can a demo that went well. This part answers it with evidence: a dataset fixed before the decision, a metric you can trust, and the honesty disciplines that keep both. The story's loop closes here, because what the measurement teaches becomes the next issue.*
```

Hand-off (before `## See also`):

```markdown
*Next: the loop has closed; what remains is what the change leaves behind. [Part 7. Documentation & knowledge capture](documentation.md).*
```

- [ ] **Step 7: `documentation.md`**

Bridge (after `# Part 7. Documentation & Knowledge Capture`):

```markdown
*The change shipped and the verdict is in. What survives of it now (for a teammate, a future you, or an agent dispatched with zero conversation history) is only what was written down. This part is about the artifacts that make a decision and its evidence recoverable, and about keeping every written claim true against the code it describes.*
```

Hand-off (before `## See also`):

```markdown
*Next: the one obligation that stands over every change rather than following any single one. [Part 8. Security, dependencies & supply chain](security-supply-chain.md).*
```

- [ ] **Step 8: `security-supply-chain.md`**

Bridge (after `# Part 8. Security, Dependencies & Supply Chain`):

```markdown
*One obligation follows no single change but stands over all of them: keeping the machine safe. Nothing in the story so far would catch a leaked credential, a dependency you may not legally ship, or a pipeline that hands its own keys to a malicious pull request. This part covers those surfaces, and it applies the make-the-standard-executable throughline at its most literal: turn every fix into a gate.*
```

Hand-off (before `## See also`):

```markdown
*And the loop begins again: the next idea becomes the next issue. [Part 1. The development lifecycle](lifecycle.md).*
```

- [ ] **Step 9: verify**

```bash
grep -c "^\*.*\*$" docs/engineering/lifecycle.md docs/engineering/codebase-structure.md docs/engineering/three-layer-model.md docs/engineering/agent-harness.md docs/engineering/observability.md docs/engineering/evaluation.md docs/engineering/documentation.md docs/engineering/security-supply-chain.md
```
Expected: every listed file reports at least `2` (its bridge and its hand-off; some part bodies contain no other full-line italic paragraphs, so most report exactly 2).

```bash
uv run scripts/render_handbook_artifact.py --out /tmp/handbook.html
uv run python scripts/check_docs.py
```
Expected: `sections: 9`, `em-dashes: 0`, `residual .md hrefs: 0`; docs check passes.

- [ ] **Step 10: commit**

```bash
git add docs/engineering/
git commit -m "docs(<origin-repo>#531): add you-are-here bridges and hand-offs to all handbook parts

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Rework Part 1 (lifecycle) internally

**Files:**
- Modify: `docs/engineering/lifecycle.md`

**Interfaces:**
- Consumes: Task 1 numbering (all old_strings below reflect post-Task-1 text); Task 3's bridge and hand-off in this file (must be preserved untouched).
- Produces: the final section order of Part 1 (listed below), which Task 6 verifies.

**Step A. Reorder sections.** Move whole sections (heading plus body, up to the next `##` heading) so the file's `##` sections run in this order:

1. `## Front-load the judgment`
2. `## Decide the human-in-the-loop gates up front`
3. `## Step-by-step: one issue, end to end`
4. `## TDD` (with its `### Chase caught regressions, not coverage percentage` subsection)
5. `## Prompt and SOP engineering` (moved up from after "Coding-hygiene rules")
6. `## CI and static analysis`
7. `## The code-review protocol`
8. `## Coding-hygiene rules that surface at review` (moved up from after "Make the standard executable")
9. `## When to add an end-to-end agent quality gate`
10. `## After the merge` (moved up from after "Prompt and SOP engineering")
11. `## Make the standard executable, and audit periodically` (moved down; closes the part)
12. `## Pre-merge checklist`
13. `## See also`

Move sections verbatim (including their intra-section links); only their position changes.

- [ ] **Step 1: perform the section reorder above.** Mechanically: cut the full `## Prompt and SOP engineering` section and paste it directly after the end of the `### Chase caught regressions, not coverage percentage` subsection (before `## CI and static analysis`); cut the full `## Coding-hygiene rules that surface at review` section and paste it directly after the `## The code-review protocol` section; cut the full `## Make the standard executable, and audit periodically` section and paste it directly after the `## After the merge` section (before `## Pre-merge checklist`).

- [ ] **Step 2: add connector sentences.** Four insertions:

(a) Append a new paragraph at the end of the `## Step-by-step: one issue, end to end` section, after the blockquote about subagents with shell access (before `## TDD`):

```markdown
That is the route. The rest of this part equips its stations, in the order the change meets them: how the code gets written (TDD), how an agent's behaviour gets written (prompts and SOPs), the mechanical gates (CI and static analysis), the human-shaped gate (the review protocol and the hygiene findings it keeps surfacing), the behavioural gate (the end-to-end quality run), what happens after the merge, and the meta-practice that keeps all of it enforced.
```

(b) In `## Prompt and SOP engineering`, prepend a sentence to the section's first paragraph. old_string -> new_string:

| old_string | new_string |
|---|---|
| `An agent's behaviour is defined by its **SOP** (Standard Operating Procedure)` | `For an agent, part of the implementation is not code but prompt, and it deserves the same discipline as code. An agent's behaviour is defined by its **SOP** (Standard Operating Procedure)` |

(c) In `## CI and static analysis`, prepend to the first paragraph:

| old_string | new_string |
|---|---|
| `Run the same static-quality checks on every push and pull request` | `With the change written, the first gates it meets are mechanical. Run the same static-quality checks on every push and pull request` |

(d) In `## The code-review protocol`, prepend to the first paragraph:

| old_string | new_string |
|---|---|
| `Run the comprehensive whole-branch review as a deliberately adversarial, multi-perspective pass.` | `The mechanical gates pass; what they cannot judge, the review does. Run the comprehensive whole-branch review as a deliberately adversarial, multi-perspective pass.` |

(e) In `## Make the standard executable, and audit periodically`, prepend to the first paragraph:

| old_string | new_string |
|---|---|
| `Whenever you fix a class of problem, ask the follow-up: *what stops it coming back?*` | `One meta-practice closes the lifecycle, because it decides whether every gate above keeps existing. Whenever you fix a class of problem, ask the follow-up: *what stops it coming back?*` |

- [ ] **Step 3: fix comma splices.** Exact replacements (each old_string appears once):

| old_string | new_string |
|---|---|
| `(which issue, which approach), don't silently proceed` | `(which issue, which approach); don't silently proceed` |
| `not just the body, comments carry the current state` | `not just the body: comments carry the current state` |
| `put the **complete** code in every code step, no placeholders` | `put the **complete** code in every code step: no placeholders` |
| `Keep the per-task review (below), it is a load-bearing quality gate, not optional.` | `Keep the per-task review (below): it is a load-bearing quality gate, not optional.` |
| `require *two* verdicts, **spec compliance** and **code quality**` | `require *two* verdicts: **spec compliance** and **code quality**` |
| `Cover the deterministic, pure logic of anything you add, parsing, scoring, transformation, id-mapping, verdict application, regex behaviour, *before the change is done*` | `Cover the deterministic, pure logic of anything you add (parsing, scoring, transformation, id-mapping, verdict application, regex behaviour) *before the change is done*` |
| `is a *false* safety net, worse than an honest low number, because people trust it` | `is a *false* safety net: worse than an honest low number, because people trust it` |
| `passes the checker by having nothing to check, a false pass in the same family` | `passes the checker by having nothing to check: a false pass in the same family` |
| `Give each reviewer pass a different angle, audit the diff against the project's binding rules, shallow-scan for obvious bugs, read git history/blame for context, read prior PRs that touched these files, check compliance with in-code comments, because a single reviewer is blind` | `Give each reviewer pass a different angle (audit the diff against the project's binding rules; shallow-scan for obvious bugs; read git history and blame for context; read prior PRs that touched these files; check compliance with in-code comments), because a single reviewer is blind` |
| `not only the fixed ones, a full table of score, description, and disposition` | `not only the fixed ones: a full table of score, description, and disposition` |
| `just to satisfy a finding, that trades a cosmetic win for real divergence` | `just to satisfy a finding: that trades a cosmetic win for real divergence` |
| `Run the counterpart to standing gates too: the **periodic audit**: a deliberate` | `Run the counterpart to standing gates too, the **periodic audit**: a deliberate` |
| `not just what, the reasoning is the part a future reader needs` | `not just what: the reasoning is the part a future reader needs` |

- [ ] **Step 4: verify**

```bash
grep -n "^## " docs/engineering/lifecycle.md
```
Expected: the 13 headings in the Step-A order above.

```bash
uv run scripts/render_handbook_artifact.py --out /tmp/handbook.html
uv run python scripts/check_docs.py
```
Expected: `sections: 9`, `em-dashes: 0`, `residual .md hrefs: 0`; docs check passes.

- [ ] **Step 5: commit**

```bash
git add docs/engineering/lifecycle.md
git commit -m "docs(<origin-repo>#531): order Part 1 sections along the spine; add connectors; fix comma splices

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Rework Part 5 (observability) internally

**Files:**
- Modify: `docs/engineering/observability.md`

**Interfaces:**
- Consumes: Task 1 numbering; Task 3's bridge and hand-off in this file (preserve untouched).
- Produces: nothing later tasks depend on.

Section order is already the argument chain (see -> attribute -> cost -> diagnose -> feed back); no reorder. Two connector insertions and seven splice fixes.

- [ ] **Step 1: add connector sentences.**

(a) In `## Keep observability out of the model's context`, prepend to the first paragraph:

| old_string | new_string |
|---|---|
| `Send analysis metadata through a **side channel the model never sees.**` | `Before deciding what to capture, decide where it rides. Send analysis metadata through a **side channel the model never sees.**` |

(b) In `## Capture per-(sub)agent, per-tool usage`, prepend to the first paragraph:

| old_string | new_string |
|---|---|
| `Have the run harness produce a per-(sub)agent and per-tool usage record` | `With the side channel in place, this is what to put on it. Have the run harness produce a per-(sub)agent and per-tool usage record` |

- [ ] **Step 2: fix comma splices.** Exact replacements (each old_string appears once):

| old_string | new_string |
|---|---|
| `Don't tune knobs before you can see their effect, that is guessing with extra steps.` | `Don't tune knobs before you can see their effect: that is guessing with extra steps.` |
| `Don't trust averages to show this, a healthy-looking overall number can mask` | `Don't trust averages to show this: a healthy-looking overall number can mask` |
| `*alongside* the run in the artifacts, don't ride them inside the prompt` | `*alongside* the run in the artifacts; don't ride them inside the prompt` |
| `per-tool usage record, tokens (including cache read and write, which are easy to forget), wall-clock timing` | `per-tool usage record: tokens (including cache read and write, which are easy to forget), wall-clock timing` |
| `A quality number without its full cost is not a decision, most model and pipeline choices are quality/cost trade-offs.` | `A quality number without its full cost is not a decision: most model and pipeline choices are quality/cost trade-offs.` |
| `over percentages (69% more), the absolute number is what hits the budget` | `over percentages (69% more): the absolute number is what hits the budget` |
| `triage a real-world session after the fact, reconstruct where a turn spent its time` | `triage a real-world session after the fact: reconstruct where a turn spent its time` |

- [ ] **Step 3: verify**

```bash
uv run scripts/render_handbook_artifact.py --out /tmp/handbook.html
uv run python scripts/check_docs.py
```
Expected: `sections: 9`, `em-dashes: 0`, `residual .md hrefs: 0`; docs check passes.

- [ ] **Step 4: commit**

```bash
git add docs/engineering/observability.md
git commit -m "docs(<origin-repo>#531): connect Part 5 sections into one argument; fix comma splices

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Final verification sweep and artifact regeneration

**Files:**
- Modify: none expected (fix-ups only if a check fails)

**Interfaces:**
- Consumes: everything above.
- Produces: the verified final state.

- [ ] **Step 1: run the full gate battery**

```bash
uv run scripts/render_handbook_artifact.py --out /tmp/handbook.html
uv run python scripts/check_docs.py
uv run pytest tests/scripts/ -q
uv run ruff check . && uv run ruff format --check .
```
Expected: render reports `sections: 9`, `em-dashes: 0`, `residual .md hrefs: 0`; docs check passes; all tests pass; ruff clean.

- [ ] **Step 2: renumbering consistency check**

```bash
grep -h "^# Part" docs/engineering/*.md | sort
grep -nE "Part 3\]\(agent-harness|Part 4\]\(observability|Part 5\]\(evaluation|Part 6\]\(three-layer|Part 3\. The extended|Part 4\. Observability|Part 5\. Evaluation|Part 6\. (The )?[Tt]hree-layer" docs/engineering/*.md
grep -rn "—" docs/engineering/ || true
```
Expected: the eight H1s in the Task 1 Step 11 order; no stale-pairing matches; no em-dash matches.

- [ ] **Step 3: matrix-vs-bridges consistency check (manual read)**

Open `docs/engineering/README.md`'s matrix and each part's bridge. For every ● in the matrix, the corresponding bridge (or the part's opening paragraph) names that throughline. Confirm: Part 1 bridge names the trail and executable standards; Part 2 bridge names core-versus-task-layer; Part 3 bridge names core-versus-task-layer; Part 4 bridge names core-versus-task-layer; Part 5 bridge names the evidence throughline; Part 6 bridge names evidence ("answers it with evidence"); Part 7 bridge speaks of the trail ("what was written down"); Part 8 bridge names make-the-standard-executable. If a ● has no matching mention, report it; do not silently edit the matrix.

- [ ] **Step 4: standalone-consultability check (manual read)**

Read each part's bridge in isolation and confirm it states the part's problem in its own words, understandable without having read the README story. All eight bridges in Task 3 were written to this standard; confirm no later edit broke it.

- [ ] **Step 5: commit any fix-ups**

Only if Steps 1 to 4 surfaced problems:

```bash
git add docs/engineering/ scripts/render_handbook_artifact.py
git commit -m "docs(<origin-repo>#531): fix-ups from the final verification sweep

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Plan self-review notes

- **Spec coverage:** story + throughlines + matrix (Task 2); bridges/hand-offs with the italicized-paragraph convention (Task 3); reorder 6 -> 3 and renumbering sweep incl. `docs/README.md` blurb and PARTS list (Tasks 1, 2); Parts 1 and old-4 internal rework with splice fixes (Tasks 4, 5); verification gates and the matrix-vs-bridge check (Task 6); voice split honored (bridges and story use we/you narrative register; bodies untouched).
- **Numbering convention in this plan:** "Part 5 (observability)" and all old_strings use the *post-Task-1* numbering; the spec's section 5 referred to observability by its old number (Part 4).
- **Known trade-off:** Task 1 Step 9 patches the old README table, which Task 2 then rewrites wholesale. The duplication is deliberate: it keeps the repo self-consistent after every task boundary.
