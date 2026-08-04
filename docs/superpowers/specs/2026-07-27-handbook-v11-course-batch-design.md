# Handbook v1.1 Course Batch: Design (issue lidia-tech/lidia-agents#533)

**Date:** 2026-07-27
**Issue:** [lidia-tech/lidia-agents#533](https://github.com/lidia-tech/lidia-agents/issues/533)
**Builds on:** lidia-tech/lidia-agents#531 / PR lidia-tech/lidia-agents#532 (narrative restructure, merged)

## Goal

Fold the additive ideas from the "AI Harness Engineering" course (Luca Mezzalira, 2026-07-24) into the AI Agent Development Handbook (`docs/engineering/`). The transcript analysis (recorded on lidia-tech/lidia-agents#533) found roughly two thirds of the course already covered by the handbook, so this is a targeted batch: 8 ranked additions/extensions, one terminology paragraph, and 5 one-line grafts. Not a rewrite.

## Constraints (binding for every addition)

- **Register:** every addition is a directive-with-reasons in the handbook's existing voice: clipped imperative in section bodies, portable "how to" tone, no institutional "we". Narrative tissue (italicized bridges/hand-offs) is not touched.
- **Structure:** the lidia-tech/lidia-agents#531 narrative spine, part order, bridges, and hand-offs are preserved. No part changes its role, so the README throughline matrix and parts table stay as they are.
- **Style gates:** no em-dashes anywhere in `docs/engineering/`; no comma splices in new prose; one paragraph per source line (no hard wrap); Markdown links relative within the handbook.
- **Word budget:** the whole batch stays within **+1.5k prose words** across all files (hard cap; compress drafts that run over).
- **Settled decisions** (from lidia-tech/lidia-agents#533, not renegotiable at implementation time):
  - Harness terminology converges to the industry standard (Agent = Model + Harness); Part 4 keeps its title; Fowler's broader usage gets one acknowledging sentence with the link `https://martinfowler.com/articles/harness-engineering.html`.
  - The spec-review and merge bookend gates stay always-on for every change; only optional gates and involvement depth scale with criticality.
  - Mild Brandolini position: agent-assisted authoring stands even for core-domain code; core code gets intensified oversight and review, not a hand-write-only rule.
  - No dated vendor stats or chart reproductions; cite the *Accelerate* book (Forsgren, Humble, Kim) as the durable source.

## Changes by file

### 1. `lifecycle.md` (Part 1) — 5 items + 2 grafts, ~+700 words

**(a) New H2 "Scale involvement to criticality"**, placed immediately after "Decide the human-in-the-loop gates up front" (it refines that decision). Content requirements:

- The two axes: *how present the human is* (in-the-loop: co-design and approve each step; on-the-loop: monitor and audit, intervene on signal; out-of-the-loop: run behind guardrails, sample after the fact) and *how much the code matters* (core differentiator / supporting / commodity).
- The mapping: core code gets in-the-loop treatment (co-design, double review); supporting code gets on-the-loop; commodity integrations can run out-of-the-loop behind guardrails and gates.
- The mild Brandolini position: even core-domain code is agent-assisted; what scales up is oversight, not who types.
- Explicit non-license sentence: the two always-on bookend gates (spec review, merge) never scale off; criticality scales the *optional* gates and the depth of implementation involvement only.
- Cross-link Part 2's tier map: reuse and criticality are two different axes over the same codebase.
- One new pre-merge checklist item (e.g. "Involvement depth matched the change's criticality; bookend gates were on regardless.").

**(b) New H2 "Keep batches small and the flow fast"**, placed immediately after "Front-load the judgment" (it is an issue-scoping discipline, upstream of the gates). Content requirements:

- The hazard: AI multiplies code volume and resurrects the giant-branch anti-pattern; a huge diff defeats review (ties to the review section's purpose).
- The counter is upstream: scope each request/issue narrowly; a batch-size cap (max diff size) is only a backstop, not the mechanism.
- Measure idea-to-production, not just commit-to-deploy; name the four DORA measures (lead time, deployment frequency, change-failure rate, time to restore) as shared vocabulary.
- Cite *Accelerate* for the evidence base (small batches, loosely coupled architecture, lightweight change approval predict performance). No numbers or charts.

**(c) Extend "The code-review protocol"** with one opening paragraph (before the current first paragraph): review's primary value in the AI era is *shared understanding*, the moment a human is forced to understand what ships (the bus-factor guard when agents write most code). Review what the change *expresses* (intent, design, fit), not how it is written (the how is a linter's job, see CI section). A review that one person silently absorbs has failed its purpose even if it caught bugs.

**(d) Extend step 2 ("Brainstorm into a spec")** of the step-by-step with 2-3 sentences: spec quality is bounded by collaborative context extraction across product, engineering, and domain experts, not by solo authoring skill; name Event Storming, event modeling, or a lightweight architecture canvas as options (without importing enterprise DDD wholesale); live low-fidelity modeling resists the "have the AI write the doc" failure mode because the shared understanding forms in the room, not in the artifact.

**(e) Sharpen the deterministic/agentic division**, one directive sentence in each of two sections:

- In "CI and static analysis": never use an agent for what a linter, formatter, or analyzer can enforce deterministically; an agent is slower, costlier, and non-deterministic at exactly the job a rule does perfectly.
- In "Prompt and SOP engineering": reserve skills/SOPs for heuristic judgment a deterministic tool cannot express; if a rule can be written, write the rule (cross-reference the CI section).

**(f) Two one-line grafts:**

- In step 2 of the step-by-step (or adjacent): use the architecture doc *forward*: render the post-change version of the architecture to estimate impact before implementing.
- In the TDD section: for a like-for-like refactor or port, a throwaway test battery pinning current behaviour is legitimate scaffolding; delete it after the port instead of maintaining it.

### 2. `agent-harness.md` (Part 4) — terminology paragraph, ~+120 words

One new paragraph placed after the current intro paragraph (line 5), before "Build the harness, don't inline the plumbing". Content requirements:

- The industry definition: an agent is a model plus its **harness**, the infrastructure around the model (tool dispatch, memory, sandboxes, safeguards); the agent framework provides the base agentic loop, and this part is the *extended* layer built around it (hence the part's title).
- One sentence acknowledging Fowler's broader "harness engineering" usage (guides/feedforward + sensors/feedback + human steering, linked to `https://martinfowler.com/articles/harness-engineering.html`) and noting this handbook covers that broader envelope across Parts 1, 5, and 6.

### 3. `evaluation.md` (Part 6) — 3 touches, ~+350 words

**(a) New H2 "Grow the eval into a gate"**, placed after "Pick the approach that fits the decision". Content requirements: the maturity ladder: (1) offline eval on a fixed dataset, (2) shadow mode on real traffic, logged but not blocking, (3) only then a merge-blocking CI gate; promoting an eval before it has survived shadow mode gates on noise; production misses become new dataset cases at every rung (ties to "Run the loop").

**(b) Extend the "Report variance" bullet** in "Measure honestly": for pass/fail cases run N times, report per-case reliability bands (k of N passes per case distinguishes a flaky case from a failing one) alongside the strict pass^N aggregate (the probability all N runs pass, the honest number for "will this work every time"); these complement the coefficient-of-variation guidance for scalar metrics. Add one sentence: the acceptable reliability bar is a business decision tied to the change's criticality (cross-link Part 1's new criticality section).

**(c) Name the grader taxonomy** in "Measure the behaviors that matter" (1-2 sentences): match the grader to the behavior: code-graded (deterministic assertions on output), judge-graded (LLM rubric where calibrated), and trajectory-graded (asserting on the run's path, e.g. a forbidden tool was never called), the last being the only kind that can see *how* the agent got there.

### 4. `documentation.md` (Part 7) — ADR + 2 grafts, ~+150 words

**(a) New row in the decision-trail artifact table** (Forward direction): **ADR** (Architecture Decision Record): a terse record of one durable architectural decision, its alternatives, and rationale, socialized with 1-3 readers before implementation. Follow the table with 1-2 sentences distinguishing it from its neighbours: a spec scopes one change, a story looks back; an ADR captures a decision that outlives both. Architectural rationale goes in the ADR; implementation-level rationale stays in the story.

**(b) Two grafts:**

- Near the ADR row: declare the data model as an explicit, versioned context artifact (schemas plus known quirks) that agents are pointed at and must respect; an agent that guesses the data model reinvents it wrong.
- In "Keep the living docs current too" (or the audit section, implementer's choice by flow): constrain LLM-generated diagrams to a metalanguage (Mermaid/PlantUML) and regenerate them from source on merge, so diagrams stay diffable and cannot silently drift from the code.

### 5. `security-supply-chain.md` (Part 8) — 1 item, ~+250 words

**New H2 "Grant the agent the least privilege it needs"**, placed after "First-party code: trace a path from source to sink" (source-to-sink flows into "and don't hand the agent the dangerous sinks in the first place"). Content requirements:

- The gap being closed: the handbook treats model/tool *outputs* as untrusted, but the agent's own granted powers are a security surface too.
- Name the **lethal trifecta**: access to private data + exposure to untrusted content + the ability to act externally (exfiltrate, write, spend). Any two are manageable; never concentrate all three in one agent without a human gate on the acting edge.
- Directives: prefer read-only tool/MCP access for diagnostics and research agents; grant write access per-tool and per-purpose, never wholesale; never grant production or pipeline write access for convenience (mirror of the CI least-privilege rule in "Treat the pipeline as a privileged environment").
- New checklist group **"Agent privileges"** in the sweep checklist (3 items: trifecta audit per agent; read-only default for diagnostics; no convenience write grants to prod/pipeline).

### 6. `README.md` — 1 graft, ~+20 words

In throughline 1 ("Evidence over intuition"), one clause naming **AI sycophancy** as a hazard behind false confidence: the model agrees with the premise it is handed, so its confidence is not evidence.

## Explicitly out of scope

Dated DORA/vendor survey stats and vendor war stories; team-learning rituals; ops runbooks and postmortem tooling; the speculative Q&A ideas (AI-chat-log mining, artifact dependency manager), except the data-model-declaration graft kept above. The reader-feedback items (README opening line, greenfield section) already shipped in PR lidia-tech/lidia-agents#532.

## Verification

- `uv run scripts/render_handbook_artifact.py --out <tmp>/handbook.html` reports **em-dashes: 0, residual .md hrefs: 0**, sections: 10.
- `uv run python scripts/check_docs.py` passes (0 dead links, 0 unindexed).
- `uv run mkdocs build --strict` passes (handbook excluded from site; must not regress).
- `uv run python scripts/check_site_links.py site` passes.
- Manual: total added prose across the six files ≤ ~1.5k words (`git diff --word-diff` based count); every new cross-link resolves; no comma splices in new prose.

## Execution

Single PR on branch `533-handbook-v11-course-batch`, executed via subagent-driven development: 6 tasks, one per file (Part 1 the largest), each task ending with the renderer + docs gates, plus a final whole-branch review. Docs-only change: no smoke-test dispatch required.
