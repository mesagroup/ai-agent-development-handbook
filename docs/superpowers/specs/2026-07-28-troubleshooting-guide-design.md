# Handbook Troubleshooting Guide — Design

**Issue:** [#536](https://github.com/lidia-tech/lidia-agents/issues/536)
**Date:** 2026-07-28
**Status:** approved in session (placement, depth, and symptom set each confirmed by the user)

## Goal

Add a symptom-indexed troubleshooting guide to the engineering handbook (`docs/engineering/`). The nine parts are organized by discipline, which is the right shape for learning but the wrong entry point for a developer whose agent is misbehaving right now. The guide starts from the observable symptom, gives a short differential diagnosis (how to tell the plausible root causes apart, and what to instrument or inspect first), and routes each root cause to the handbook section that carries the fix. The guide adds diagnosis only; the parts keep the fixes.

## Decisions

- **Placement:** a new unnumbered companion page, `docs/engineering/troubleshooting.md`, outside the Part 1-9 numbering (like the Coda). Rendered in the HTML artifact between Part 9 and the Coda; indexed in the handbook README. Part numbering never churns and the guide can grow entries freely.
- **Entry depth:** short diagnosis plus links. Each entry is the symptom as a heading, 3-6 sentences of differential diagnosis, then one routing line per root cause pointing into the parts. No step-by-step runbooks (they would duplicate and drift against the parts) and no bare routing table (it would drop the tell-the-causes-apart guidance, which is the point).
- **Symptom set:** fifteen entries. The six seeds from the issue, four approved extensions, and five additions proposed and approved in session. Six further candidates are folded into host entries as facets rather than shipped standalone, each marked **Folded facet** in the entry list: dev-vs-prod cost surprise and prefix-cache churn (into token burn), silently empty answers (into hangs), unsupported citations (into hallucination), structured-output validation failures (into tool misuse), and model-swap regression (into eval-numbers-moved).

## Page structure

1. An italic bridge paragraph in the handbook's established voice: the parts teach the disciplines in order; this page is the other entry point, for when you arrive with a problem instead of a curriculum.
2. A short "how to use this page" intro (2-3 sentences): find your symptom, read the differential, follow the route. Plus the standing caveat that one symptom often has several distinct root causes and the first move is almost always to instrument, not to tune.
3. Fifteen entries grouped under four cluster headings (`##` clusters, `###` entries) for scannability.
4. A closing hand-off line to the Coda / README, matching the handbook's italic hand-off convention.

**Entry template:** heading phrased as the developer says it (first person, concrete), body of 3-6 sentences of differential diagnosis with the what-to-check-first move, then a routing list: one line per root cause, each linking to the part (relative `.md` link, no `#anchor` fragments) and naming the target section in prose.

## The fifteen entries

Cluster and entry ordering below is the shipping order. Routing names the actual section headings verified against the parts at design time.

### Cluster 1: Cost and latency

1. **"My (subagent-based) agent eats $5 of tokens per run and I can't see where."** First move: the per-(sub)agent, per-tool usage record. Causes: no per-stage instrumentation at all (Part 6, "Capture per-(sub)agent, per-tool usage"); counting only input/output tokens while cache read/write dominates (Part 6, "Account for the full cost, not the convenient part"); low utilization, most of what is fetched never informs the answer (Part 6, utilization); iterating against live expensive backends instead of mock/cheap ones (Part 5, "Offer cheap and mock backends"). **Folded facets:** costs fine in dev but explode in prod (cache accounting again); prefix-cache churn, where a frequently edited system prompt invalidates the cache every run.
2. **"The app is unbearably slow."** First move: per-stage timing, never a parameter sweep (Part 6, "Instrument before you tune"). Causes: one dominant sequential stage in a multi-agent pipeline (Part 6, where a multi-agent run spends its time); a poorly formed upstream input poisoning every later stage (Part 6, instrument before you tune / look upstream); a slow model or too many retriever cycles (Part 7, cost/quality trade-offs and escalation ladders); unbounded waits inflating the tail (Part 5, "Make bounding the default").

### Cluster 2: Reliability

3. **"It hangs while calling tools."** Causes: no wall-clock/idle/connect/read timeouts, so a dropped socket waits forever (Part 5, "Make bounding the default"); a crash swallowed by an async event handler, so the failure never surfaces and the loop waits on nothing (Part 2, no-swallowed-exceptions under "Coding-hygiene rules that surface at review"; Part 6, "Make errors diagnosable"); a wedged resource teardown (Part 5, time-bound teardown). First move: the persisted production usage record, to tell a hang from a merely long run (Part 6, "Close the loop"). **Folded facet:** tool errors silently yielding empty answers, same swallowed-exception root cause.
4. **"External API calls fail intermittently (429s, throttling, a flaky provider)."** Distinct from the entry above: errors, not silence. Causes: missing bounded retries with backoff (Part 5, "Make bounding the default", hardened HTTP client); no circuit breaker, so one degraded dependency poisons every run (Part 5, "Build the harness, don't inline the plumbing"); retries happening but invisible in cost and latency accounting (Part 6, "Account for the full cost").
5. **"It loops without progress, repeating tool calls and never converging."** First move: the tool-call sequence and loop-cycle counts in the usage record (Part 6). Causes: no cycle/budget bound in the harness (Part 5, "Make bounding the default"); the SOP gives no stop condition or completion criterion (Part 2, "Prompt and SOP engineering"); a tool returning unusable output so the agent retries blindly (the tool-misuse entry below); a model too weak to plan its way out (Part 7).

### Cluster 3: Output quality

6. **"It errors out with out-of-context errors."** Causes: bookkeeping and analysis metadata riding inside the prompt (Part 6, "Keep observability out of the model's context"); unbounded tool outputs with no truncation/summarization strategy (Part 5, "Make bounding the default"); over-fetching that instrumentation would show as unused (Part 6, utilization).
7. **"It hallucinates."** The canonical multi-cause entry; three distinct scenarios behind one symptom. (a) Quotes non-existent facts: ungrounded generation from model weights; check whether claims trace to fetched sources; route to Part 7 ("Measure the behaviors that matter", groundedness as an eval dimension) and Part 2 (grounding rules in the SOP). (b) Quotes documents imprecisely because the ingestion pipeline/OCR introduced the errors: diff the Layer 1 representation against the source document before blaming the model; route to Part 4 (the three-layer model, the engine-agnostic Layer 1 contract) and Part 7 (extraction-quality evaluation, "Build a dataset you can trust"). (c) Quotes documents imprecisely because too much context dilutes attention: reproduce with the passage in isolation, and if the quote comes back clean the problem is dilution, not extraction; route to Part 6 (utilization) and Part 5 (bounding what enters the context). The isolation reproduction is the pivot that separates (b) from (c). **Folded facet:** citations that don't support the claim, a groundedness case of (a).
8. **"It reasons wrongly / draws bad conclusions."** Causes: model too weak for the task (Part 7, "Pick the approach that fits the decision", escalation ladders, and the staged screening funnel); the SOP asking for a leap where it should ask for steps (Part 2, "Prompt and SOP engineering"). The differential against the hallucination entry: the facts are right, the inference is wrong.
9. **"It ignores its SOP."** Causes: constraint overload, too many rules competing for attention (Part 2, "Prompt and SOP engineering"); rules in the SOP that should be deterministic harness guards instead (Part 2 division of labour; Part 5); contradictory instructions that force the model to pick one (Part 2).
10. **"It won't use the tool I gave it, picks the wrong one, or calls it with garbage arguments."** Causes: tool description and schema quality, including nullable/ambiguous parameters (Part 4, "Compose typed tools over one fuzzy lookup"; Part 5); too many overlapping tools (Part 4); the SOP never saying when to reach for it (Part 2). First move: read the actual tool-call transcript (Part 6). **Folded facet:** structured-output validation failures, the same schema-quality root cause.
11. **"Results differ run to run."** Causes: sampling parameters, temperature above zero where determinism was assumed (Part 5, "Expose model parameters as optional, defaulted flags"); an unpinned model version moving underneath (Part 9, pin models and providers); the external world changing between runs, live web or live corpus (Part 7, "Measure honestly", variance and repeated runs); nondeterministic tests/evals mistaken for agent nondeterminism (Part 2, deterministic tests).

### Cluster 4: Measurement and change

12. **"It works in my demo/eval but fails on real user queries."** Causes: benchmark too narrow or contaminated (Part 7, "Build a dataset you can trust"); production inputs distributionally different, malformed, other language, longer documents (Part 7, dataset realism); no production feedback loop returning real sessions to development (Part 6, "Close the loop").
13. **"I changed the prompt and can't tell if it helped, or it broke something else."** Causes: no frozen benchmark to A/B against (Part 7, "Run the loop", "Grow the eval into a gate"); several things changed at once (Part 7, "Measure honestly"); prompt edits buried inside code commits with no rationale (Part 2, prompt changes in their own commit with the why).
14. **"I don't trust my eval numbers."** Causes: the LLM judge disagreeing with human judgment (Part 7, "Use the LLM judge only where it agrees with the human"); a leaderboard that flips between runs, variance and too few samples (Part 7, "Measure honestly"); a rubric measuring the wrong behavior (Part 7, "Measure the behaviors that matter"); the general failure mode all three feed (Part 7, "The enemy is false confidence").
15. **"My eval numbers moved and I changed nothing."** Causes: a silent provider-side model upgrade, the unpinned-dependency case (Part 9, "Depend only on what you can account for", pin models and record which model produced a result); dataset drift or contamination (Part 7, "Build a dataset you can trust"); the live external world changing under a web-touching eval (Part 7, "Measure honestly"). **Folded facet:** a deliberate model swap regressing the agent, which routes to the screening funnel (Part 7).

## Wiring

- **`docs/engineering/README.md`:** add the guide as a companion row in the parts table area (alongside/near the Coda), and add one "in trouble right now, start here" pointer sentence near the top of the page. The story-walk paragraph does not change (the guide is not a station on the route).
- **`scripts/render_handbook_artifact.py`:** add one PARTS row for the `troubleshooting` stem between `p9` (security-supply-chain) and `coda`, so the artifact renders it after Part 9. Verify the LINKMAP mechanism picks up the new stem so links to and from `troubleshooting.md` rewrite to in-page anchors.
- **`docs/README.md`:** extend the handbook blurb (line ~177) to mention the troubleshooting guide.
- **Cross-links from parts:** none by default. The README pointer is the discovery path; the parts do not each grow a backlink. (If a specific part turns out to want one during implementation, at most one, where genuinely natural.)
- **mkdocs:** `docs/engineering/` is excluded from the built docs site (the handbook ships as its own standalone artifact; see the exclude list in `mkdocs.yml`), so the new page needs no nav entry and cannot orphan. `mkdocs build --strict` still runs as a regression gate.

## Constraints

All standing `docs/engineering/` gates, binding:

- Zero em-dashes (the render script counts them; must stay 0).
- No comma splices in new prose.
- One paragraph per source line (no hard-wrap).
- Cross-links are relative `.md` links with no `#anchor` fragments; same-file references use prose ("above"/"below"); target sections in other parts are named in prose next to the part link.
- Handbook register: portable "how to" voice, no institutional "we"; italic bridge and hand-off lines; clipped-imperative body.

**Verification gates (all four must pass):**

1. `uv run scripts/render_handbook_artifact.py --out <scratch>/handbook-check.html` (counters: em-dashes 0, residual .md hrefs 0).
2. `uv run python scripts/check_docs.py`.
3. `uv run mkdocs build --strict`.
4. `uv run python scripts/check_site_links.py site`.

## Out of scope

- No new fix content in the parts. If writing an entry exposes a genuine gap in a part (a root cause with nothing to route to), file it as a separate issue rather than inlining the fix material in the guide.
- The renderer change turned out to need a `render_nav` glyph branch as well as the PARTS row (an unnumbered anchor needs its own `✚` case), and per the project's rule that new code ships with tests, that branch carries a unit test.
- No diagrams: that is #537, and the guide can pick up a diagram there later if one earns its place.
