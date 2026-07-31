---
name: eval-audit
description: "Audit an AI/agent project's evaluation setup: whether the behaviors that matter are actually evaluated, the soundness of the eval methodology (metrics, judges, ground truth, reproducibility, contamination), prompt/SOP quality and injection-resistance, and the smoke-test gate that guards merges. Use before trusting eval numbers or a leaderboard, after changing a prompt or model, when a regression slipped through green evals, or when the user asks to audit evals / prompts / smoke tests. For projects with LLM/agent behavior. Runs on the audit-core engine. Deterministic code-level tests belong to test-audit; static prompt/SOP authoring quality (structure, spec-conformance, constraint hygiene, cognitive load) belongs to prompt-audit; this skill owns behavioral, model-level quality."
---

# Eval Audit (evals, prompts, smoke tests)

A domain specialization of **[audit-core](../audit-core/SKILL.md)** - read that first; it owns the loop (scope → parallel evidence → findings matrix → plan → subagent-driven fixes → review → PR) and the cross-cutting rules. The checks are records in [`checks/`](checks/) beside this file; load the ones your slice needs, not the directory. This skill supplies the behavioral, model-level quality lens. Deterministic, code-level testing (unit coverage, assertion strength, flakiness) belongs to **`test-audit`**, and static prompt/SOP *authoring* quality (spec-conformance, constraint hygiene, clarity, cognitive load) belongs to **`prompt-audit`** - both siblings in the audit-skills program; this skill cross-links them rather than covering them.

**Core principle:** an eval is a measuring instrument, and an instrument you haven't calibrated can read anything. The audit asks two things: *are the behaviors that actually matter being measured at all?* (an unevaluated capability is an unmonitored one) and *do the numbers mean what everyone assumes they mean?* (a metric that doesn't track quality, a judge that rubber-stamps, a contaminated dataset, or an unreproducible run produces confident nonsense). A green leaderboard built on a broken instrument is worse than no leaderboard, because decisions get made on it.

**Announce:** "I'm using the eval-audit skill (on the audit-core engine) to audit the evals, prompts, and smoke tests."

**Not for:** deterministic unit-test coverage and quality (use `test-audit`); a one-off "how good is this output" spot check (just run it). Prompt-*injection as an application-security* concern overlaps `security-audit`; here the lens is behavioral robustness, and the two cross-link.

**Subject:** the project's evaluation assets and the behaviors they are meant to measure. Establish first:

- **What behaviors matter** - the agent/model capabilities, quality dimensions, and failure modes the product depends on (accuracy, grounding/citation, refusal handling, format adherence, latency/cost). This is the yardstick for "is it evaluated."
- **The eval assets** - datasets / ground truth, metrics and scorers, any LLM-as-judge, the runner, leaderboards / eval history, and the smoke-test workflow. Detect the framework (a bespoke `eval/` package, or `promptfoo` / `deepeval` / `ragas` / `langsmith` / OpenAI Evals).
- **The prompts / SOPs** - where system prompts, tool descriptions, and agent SOPs live, and whether the project has a prompt-change discipline (versioning, changelog, "explain why a prompt changed").

Slice the parallel evidence pass **by capability or by asset type** - one read-only agent per agent/capability, or one per concern (datasets, metrics, prompts, smoke test) - whichever partitions cleanly.

**Detect** the project's eval stack (a `eval/` package with its own runner/report, or `promptfoo` / `deepeval` / `ragas` / `langsmith` / OpenAI Evals) and how evals are invoked, plus where prompts live and any prompt-analysis skill the project ships. Prefer the project's own harness; don't impose a framework it doesn't use. Record the eval config / dataset / prompt `file:line` (or the metric value and how it was produced) as the evidence pointer for every row.

Status per row: **ok / warn / violation** (coverage: measured / partial / unmeasured). Suppressions (a behavior intentionally out of eval scope, a known non-deterministic metric reported with a stated confidence interval) must be explicit and recorded with a reason - never silently dropped. Some issues are *reminders about interpretation*, not code fixes (e.g. "don't penalize a model for a sub-agent refusal") - record those as policy in the report.

Fixes here range from **eval/prompt code** (a new dataset, a fixed scorer, a prompt edit) to **interpretation policy** (how to read a number). The domain gate depends on the fix: code-touching fixes run the normal lint/typecheck/test CI plus a smoke/eval run where feasible; prompt edits should be re-evaluated behaviorally before trust. State which applies. **Highest-leverage fix:** wire a cheap, reproducible eval/smoke gate into CI. Docs-only outputs: the findings report, an eval methodology note, and leaderboard/eval-history updates.
