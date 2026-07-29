---
name: eval-audit
description: "Audit an AI/agent project's evaluation setup: whether the behaviors that matter are actually evaluated, the soundness of the eval methodology (metrics, judges, ground truth, reproducibility, contamination), prompt/SOP quality and injection-resistance, and the smoke-test gate that guards merges. Use before trusting eval numbers or a leaderboard, after changing a prompt or model, when a regression slipped through green evals, or when the user asks to audit evals / prompts / smoke tests. For projects with LLM/agent behavior. Runs on the audit-core engine. Deterministic code-level tests belong to test-audit; static prompt/SOP authoring quality (structure, spec-conformance, constraint hygiene, cognitive load) belongs to prompt-audit; this skill owns behavioral, model-level quality."
---

# Eval Audit (evals, prompts, smoke tests)

A domain specialization of **[audit-core](../audit-core/SKILL.md)** — read that first; it owns the loop (scope → parallel evidence → findings matrix → plan → subagent-driven fixes → review → PR) and the cross-cutting rules. This skill supplies the behavioral, model-level quality lens. Deterministic, code-level testing (unit coverage, assertion strength, flakiness) belongs to **`test-audit`**, and static prompt/SOP *authoring* quality (spec-conformance, constraint hygiene, clarity, cognitive load) belongs to **`prompt-audit`** — both siblings in the audit-skills program; this skill cross-links them rather than covering them.

**Core principle:** an eval is a measuring instrument, and an instrument you haven't calibrated can read anything. The audit asks two things: *are the behaviors that actually matter being measured at all?* (an unevaluated capability is an unmonitored one) and *do the numbers mean what everyone assumes they mean?* (a metric that doesn't track quality, a judge that rubber-stamps, a contaminated dataset, or an unreproducible run produces confident nonsense). A green leaderboard built on a broken instrument is worse than no leaderboard, because decisions get made on it.

**Announce:** "I'm using the eval-audit skill (on the audit-core engine) to audit the evals, prompts, and smoke tests."

## When to use

- Before trusting an eval score or a leaderboard to make a model/prompt decision.
- After changing a prompt/SOP or swapping a model, to confirm the change is actually measured and didn't silently regress behavior.
- When a behavioral regression reached production despite green evals (a sign the eval doesn't cover it or the metric is hollow).
- When the user asks to audit evals, prompt quality, or the smoke-test gate.

**Not for:** deterministic unit-test coverage and quality (use `test-audit`); a one-off "how good is this output" spot check (just run it). Prompt-*injection as an application-security* concern overlaps `security-audit`; here the lens is behavioral robustness, and the two cross-link.

## 1. Subject & scope

The project's evaluation assets and the behaviors they are meant to measure. Establish first:

- **What behaviors matter** — the agent/model capabilities, quality dimensions, and failure modes the product depends on (accuracy, grounding/citation, refusal handling, format adherence, latency/cost). This is the yardstick for "is it evaluated."
- **The eval assets** — datasets / ground truth, metrics and scorers, any LLM-as-judge, the runner, leaderboards / eval history, and the smoke-test workflow. Detect the framework (a bespoke `eval/` package, or `promptfoo` / `deepeval` / `ragas` / `langsmith` / OpenAI Evals).
- **The prompts / SOPs** — where system prompts, tool descriptions, and agent SOPs live, and whether the project has a prompt-change discipline (versioning, changelog, "explain why a prompt changed").

Slice the parallel evidence pass **by capability or by asset type** — one read-only agent per agent/capability, or one per concern (datasets, metrics, prompts, smoke test) — whichever partitions cleanly.

## 2. Dimensions (findings-matrix columns)

- **Eval coverage** — for each behavior-that-matters, is there an eval that exercises it? Uncovered capabilities, failure modes with no test case, dimensions asserted in docs but never measured.
- **Methodology soundness** — do metrics actually track quality (vs. a proxy that can be gamed)? Is the sample size adequate; are ground-truth labels correct; is an LLM-judge validated against human labels and run with a stable rubric; are refusals/API errors separated from genuine quality failures (so a sub-agent refusal doesn't penalize a model)?
- **Reproducibility** — frozen datasets/queries, pinned model versions, fixed seeds/temperature where feasible, recorded config; can a reported number be regenerated? Non-determinism that isn't acknowledged.
- **Contamination / leakage** — test items that leaked into prompts/few-shots, ground truth derived from the model under test, or an eval the prompt was tuned against being reported as held-out.
- **Prompt / SOP quality** — the *behavioral* facets: drift between prompt and the current code/tools, missing versioning/changelog, and **injection-resistance** (does the prompt hold under adversarial/tool-returned input). The *static* authoring facets (spec-conformance, RFC 2119 constraint hygiene, contradictions/dead instructions, cognitive load, redundancy) are **`prompt-audit`**'s — run it alongside this one for a prompt change and defer those rows there.
- **Smoke-test gate** — is there a cheap behavioral pre-merge check, does it run on the paths that can regress behavior, and does it actually fail on a real regression (vs. a threshold set so low nothing trips it)?
- **Regression tracking & cost** — are results tracked over time (leaderboard/history) so drift is visible; is there a cheap/mock eval mode so cost doesn't suppress running evals.

## 3. Evidence sources & tooling

**Detect** the project's eval stack (a `eval/` package with its own runner/report, or `promptfoo` / `deepeval` / `ragas` / `langsmith` / OpenAI Evals) and how evals are invoked, plus where prompts live and any prompt-analysis skill the project ships. Prefer the project's own harness; don't impose a framework it doesn't use.

Gather in the parallel evidence pass:
- **Coverage map (the load-bearing step):** list the behaviors-that-matter from §1, then map each to the eval(s) that exercise it by reading the eval configs/datasets — not by trusting a summary. The unmapped behaviors are the gap rows. A capability with a leaderboard entry but no test case for its key failure mode is still a gap.
- **Methodology inspection:** read the metric/scorer/judge implementation and the ground-truth data. Check sample size, judge rubric stability, whether a judge was correlated against human evals, and whether errors/refusals are excluded from quality scores. Re-run a small eval slice if feasible and confirm the number reproduces.
- **Prompt audit:** read each system prompt / SOP / tool description; check against the current code/tools for **drift** (references to tools/steps that changed or vanished) and for injection-resistance (how untrusted/tool-returned content enters the prompt). For the *static* authoring quality (spec-conformance, constraint hygiene, contradictions, cognitive load, redundancy), hand off to **`prompt-audit`**, which drives the `/prompt-analyzer` scan and the SOP-spec checks; don't duplicate them here.
- **Smoke-test inspection:** read the smoke-test workflow and its pass threshold; confirm it runs on the right triggers/paths and that its threshold would actually catch a real regression (cross-check with `ci-audit` for the gate-enforcement mechanics).

Record the eval config / dataset / prompt `file:line` (or the metric value and how it was produced) as the evidence pointer for every row.

## 4. Status scale + severity rubric

Status per row: **ok / warn / violation** (coverage: measured / partial / unmeasured).

- **Critical** — a product-critical behavior with **no** eval; a metric or judge that does not track real quality (so the leaderboard is misleading); dataset contamination / leakage that invalidates reported numbers; a smoke-test gate whose threshold cannot fail on a genuine regression.
- **Important** — an under-powered eval (too few samples to distinguish models); an unvalidated LLM-judge used for decisions; refusals/errors polluting quality scores; a prompt that contradicts the code or has drifted; an unreproducible headline number.
- **Minor** — a missing cheap/mock mode, a stale leaderboard entry, a prompt style inconsistency, a nice-to-have dimension not yet measured.

Suppressions (a behavior intentionally out of eval scope, a known non-deterministic metric reported with a stated confidence interval) must be explicit and recorded with a reason — never silently dropped. Note that some issues are *reminders about interpretation*, not code fixes (e.g. "don't penalize a model for a sub-agent refusal") — record those as policy in the report.

## 5. Fix patterns (and CI implications)

Fixes here range from **eval/prompt code** (a new dataset, a fixed scorer, a prompt edit) to **interpretation policy** (how to read a number). The domain gate depends on the fix: code-touching fixes run the normal lint/typecheck/test CI plus a smoke/eval run where feasible; prompt edits should be re-evaluated behaviorally before trust. State which applies.
- **Close a coverage gap:** add a dataset / test case exercising the behavior (especially the failure mode), with a metric that tracks the quality dimension, not a gameable proxy.
- **Fix the instrument:** correct a scorer's math or an id-mapping; validate the LLM-judge against human labels and stabilize its rubric; separate refusals/errors from quality; increase sample size to a power that distinguishes candidates.
- **De-contaminate:** hold out the eval set from prompt-tuning/few-shots; source ground truth independently of the model under test; label leaked items and re-baseline.
- **Prompt fixes:** remove contradictions/dead instructions, reconcile the prompt with the current tools/code, add versioning + a changelog entry explaining *why* the prompt changed (keep prompt changes in their own commit if the project's convention says so), and harden injection-resistance.
- **Smoke-test fixes:** set a threshold that trips on a real regression, run it on the paths that can change behavior (coordinate with `ci-audit` on making it a required gate).
- **Highest-leverage fix:** wire a cheap, reproducible eval/smoke gate into CI and track results over time (leaderboard/history) so behavioral drift is visible rather than discovered in production.
- Docs-only outputs: the findings report, an eval methodology note, and leaderboard/eval-history updates.

## 6. Review dimensions (Phase-5 specialized reviewers)

- **Metric validity** — does each metric/judge actually measure the quality dimension it claims, and does the fix improve the instrument rather than the number? (Highest-value catch: a change that raises the score without improving behavior.)
- **Coverage honesty** — is each "now evaluated" claim backed by a dataset that exercises the real behavior/failure mode, not a trivial happy-path case?
- **Reproducibility** — can the reported numbers be regenerated from the recorded config; no hidden non-determinism.
- **Contamination** — the eval set is genuinely held out from tuning; ground truth is independent of the model under test.
- **Prompt correctness** — prompt edits preserve intended behavior (re-evaluated), match the current tools/code, and don't introduce new contradictions or injection weaknesses.

## 7. Opt-in sub-audits

- **Adversarial / red-team eval** — probe prompt-injection and jailbreak resistance as a behavioral suite (coordinate the security framing with `security-audit`) — enable via argument or ask the user.
- **LLM-judge calibration study** — correlate the automated judge against a human-labeled sample and report agreement, before the judge is trusted for decisions — ask the user; recommend on when a judge gates model selection.
- **Cost/latency profile** — measure per-eval cost and latency and identify a mock/cheap mode — ask the user; useful when eval cost is suppressing how often evals run.
