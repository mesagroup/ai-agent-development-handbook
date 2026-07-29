<!-- GENERATED FILE - do not edit. Source: handbook-traceability.yaml; run scripts/render_handbook_traceability.py after editing. -->

# Handbook traceability matrix

Maps every ``##`` section of the [engineering handbook](../engineering/README.md) onto the ``*-audit`` skill family. Source of truth: [`handbook-traceability.yaml`](handbook-traceability.yaml). Issue: #543.

| Class | Meaning |
|---|---|
| `static` | Statically auditable from a repo snapshot; mapped to a skill check or carries a gap entry. |
| `artifact` | Auditable only via artifacts (eval runs, CI history, issue/PR trail). Absence of the artifact is itself a finding - never a pass. |
| `process` | Process/culture; not verifiable from the repo. Audit-report prose and adoption recommendations, never fake-automated. |
| `informative` | Non-normative (spine, coda, symptom index); accounted for, maps to nothing. |


## The README spine

| Section | Class | Mapped checks | Gap |
|---|---|---|---|
| [The story of a change](../engineering/README.md#the-story-of-a-change) | informative | - | - |
| [Starting from zero](../engineering/README.md#starting-from-zero) | process | - | - |
| [The four throughlines](../engineering/README.md#the-four-throughlines) | process | - | - |
| [How to use this handbook](../engineering/README.md#how-to-use-this-handbook) | informative | - | - |
| [Where the binding rules live](../engineering/README.md#where-the-binding-rules-live) | static | - | **extend-skill** - docs-audit has no dimension for an authoritative rules file or for doc-vs-doc contradiction; ci-audit's Gate enforcement checks that mismatch only for what CI claims to enforce. |

## Part 1: Development lifecycle

| Section | Class | Mapped checks | Gap |
|---|---|---|---|
| [Front-load the judgment](../engineering/lifecycle.md#front-load-the-judgment) (a) | process | - | - |
| [Front-load the judgment](../engineering/lifecycle.md#front-load-the-judgment) (b) | static | - | **extend-skill** - prompt-audit is the nearest owner - a lifecycle workflow is a prompt artifact - but its dimensions judge how a prompt is written, never whether the lifecycle is encoded as one at all, and nothing looks for a scratch TODO file. |
| [Front-load the judgment](../engineering/lifecycle.md#front-load-the-judgment) (c) | artifact | - | **new-domain** - no skill reads the issue tracker, so whether work traces to an issue sits outside the family's evidence base entirely. |
| [Keep batches small and the flow fast](../engineering/lifecycle.md#keep-batches-small-and-the-flow-fast) | artifact | - | **new-domain** - batch size and the DORA four measures are delivery-history evidence; ci-audit reads workflow definitions rather than delivery outcomes, and no skill reads pull-request or deployment history. |
| [Decide the human-in-the-loop gates up front](../engineering/lifecycle.md#decide-the-human-in-the-loop-gates-up-front) | process | - | - |
| [Scale involvement to criticality](../engineering/lifecycle.md#scale-involvement-to-criticality) | process | - | - |
| [Step-by-step: one issue, end to end](../engineering/lifecycle.md#step-by-step-one-issue-end-to-end) (a) | process | - | - |
| [Step-by-step: one issue, end to end](../engineering/lifecycle.md#step-by-step-one-issue-end-to-end) (b) | artifact | - | **extend-skill** - docs-audit is the owner because specs and plans are docs-tree artifacts, but no dimension asks whether a change carries a committed spec and plan, nor scans a plan for placeholders. |
| [Step-by-step: one issue, end to end](../engineering/lifecycle.md#step-by-step-one-issue-end-to-end) (c) | artifact | - | **new-domain** - branch, pull-request and merge mechanics live in git and tracker history, which no skill in the family reads. |
| [Step-by-step: one issue, end to end](../engineering/lifecycle.md#step-by-step-one-issue-end-to-end) (d) | static | - | **extend-skill** - no dimension inspects an agent or subagent definition for an explicit, right-sized model; the nearest is eval-audit's Reproducibility, which wants a pinned model version recorded for an eval run rather than a right-sized one chosen per role. |
| [Step-by-step: one issue, end to end](../engineering/lifecycle.md#step-by-step-one-issue-end-to-end) (e) | static | - | **extend-skill** - prompt-audit is the owner because these are requirements on the text of a dispatching prompt, but no dimension checks a prompt for the operational instructions the project mandates - Tier A judges only the quality of what is already there. |
| [After the merge](../engineering/lifecycle.md#after-the-merge) | artifact | - | **new-domain** - the post-merge trail is entirely tracker-side, so nothing in the family can see whether criteria were verified, ticked, or blind-checked. |
| [Make the standard executable, and audit periodically](../engineering/lifecycle.md#make-the-standard-executable-and-audit-periodically) (a) | static | `ci-audit` / Gate enforcement<br>`eval-audit` / Smoke-test gate | **extend-skill** - Gate enforcement audits the gates that already exist; no dimension walks the project's binding rules to find the ones with no mechanical enforcer, and the local pre-commit half of the claim is unrepresented anywhere. |
| [Make the standard executable, and audit periodically](../engineering/lifecycle.md#make-the-standard-executable-and-audit-periodically) (b) | artifact | - | **report-only** - this is audit-core's own charter, but audit-core declares no dimensions so no row can cite it; audit cadence and past audit reports are outside every skill's evidence base. |
| [Pre-merge checklist](../engineering/lifecycle.md#pre-merge-checklist) | process | - | - |
| [See also](../engineering/lifecycle.md#see-also) | informative | - | - |

## Part 2: Implementation disciplines

| Section | Class | Mapped checks | Gap |
|---|---|---|---|
| [TDD](../engineering/implementation-disciplines.md#tdd) (a) | process | - | - |
| [TDD](../engineering/implementation-disciplines.md#tdd) (b) | static | `test-audit` / TDD adherence / new-code coverage<br>`test-audit` / Coverage reach<br>`test-audit` / Assertion strength<br>`test-audit` / Determinism / flakiness<br>`test-audit` / Isolation & speed<br>`test-audit` / Effectiveness (optional) | - |
| [Prompt and SOP engineering](../engineering/implementation-disciplines.md#prompt-and-sop-engineering) (a) | static | `prompt-audit` / Instruction precision<br>`prompt-audit` / Positive framing, prohibitions with reasons<br>`prompt-audit` / Role, objective & task framing<br>`prompt-audit` / Grounding & handling the unknown<br>`prompt-audit` / Cognitive load & focus | **extend-skill** - prompt-audit's Tier B does audit the SOP structural spec in full, but Tier B declares no bolded dimension bullets so no matrix row can cite it - the fix is to the skill's Dimensions section, not to its coverage. |
| [Prompt and SOP engineering](../engineering/implementation-disciplines.md#prompt-and-sop-engineering) (b) | artifact | - | **extend-skill** - co-owned - prompt-audit's remediation section already states this rule verbatim as a convention it follows, and eval-audit's Prompt / SOP quality dimension owns prompt-change hygiene through its missing-versioning-or-changelog clause, but neither turns it into a check and nothing reads commit messages. |
| [Prompt and SOP engineering](../engineering/implementation-disciplines.md#prompt-and-sop-engineering) (c) | static | - | **extend-skill** - prompt-audit is the owner but no dimension asks whether a constraint stated in the prompt could be enforced deterministically in code; its counterpart claim sits on ci-and-static-analysis-d. |
| [CI and static analysis](../engineering/implementation-disciplines.md#ci-and-static-analysis) (a) | static | `ci-audit` / Gate enforcement | **extend-skill** - Gate enforcement asks whether the type-check runs and is required, never whether it can fail - no dimension measures annotation coverage or checker strictness, the type-checking analogue of test-audit's Assertion strength. |
| [CI and static analysis](../engineering/implementation-disciplines.md#ci-and-static-analysis) (b) | static | - | **extend-skill** - docs-audit does audit docstrings, but only as an opt-in sub-audit whose own coverage and staleness dimensions sit outside the citable Dimensions section; its Coverage dimension is prose docs per code component, not docstrings, and no dimension asks whether the check is wired into the gate. |
| [CI and static analysis](../engineering/implementation-disciplines.md#ci-and-static-analysis) (c) | static | - | **extend-skill** - #519 - ci-audit, prompt-audit and eval-audit are already language-neutral, so a TypeScript project still gets its pipeline, prompt and behavioural audits; what it loses is tooling - arch, deps, docs, security and test all declare Python, leaving the lint, format, type-check, docstring, dependency, structure and test dimensions with no TS equivalent. |
| [CI and static analysis](../engineering/implementation-disciplines.md#ci-and-static-analysis) (d) | static | - | **extend-skill** - no dimension flags a review or audit agent pointed at work a deterministic tool already does; prompt-audit is the nearest owner, as on prompt-and-sop-engineering-c. |
| [The code-review protocol](../engineering/implementation-disciplines.md#the-code-review-protocol) (a) | process | - | - |
| [The code-review protocol](../engineering/implementation-disciplines.md#the-code-review-protocol) (b) | artifact | - | **new-domain** - the review trail - inline pull-request comments and the findings table with its dispositions - is tracker-side evidence no skill reads, and no domain audits review discipline. |
| [Coding-hygiene rules that surface at review](../engineering/implementation-disciplines.md#coding-hygiene-rules-that-surface-at-review) (a) | static | `security-audit` / Sensitive-data handling | **extend-skill** - #516 - security-audit reaches only the security-relevant subset (broad handlers that hide security failures); the developer-facing half - an error collapsed into a generic internal error with no type or message - belongs to the observability domain the target issue creates. |
| [Coding-hygiene rules that surface at review](../engineering/implementation-disciplines.md#coding-hygiene-rules-that-surface-at-review) (b) | static | `arch-audit` / Over-abstraction / speculative generality | - |
| [Coding-hygiene rules that surface at review](../engineering/implementation-disciplines.md#coding-hygiene-rules-that-surface-at-review) (c) | static | - | **extend-skill** - security-audit's Secrets in code is the nearest dimension but is scoped to credentials, and a personal path or profile name is a portability leak rather than a secret, so nothing scans for one. |
| [Coding-hygiene rules that surface at review](../engineering/implementation-disciplines.md#coding-hygiene-rules-that-surface-at-review) (d) | static | - | **extend-skill** - docstring currency is a staleness question, and docs-audit reaches it only through its opt-in docstring sub-audit, outside the citable Dimensions section; self-documenting settings fields and provider-safe tool-argument types have no dimension anywhere. |
| [When to add an end-to-end agent quality gate](../engineering/implementation-disciplines.md#when-to-add-an-end-to-end-agent-quality-gate) | static | `eval-audit` / Smoke-test gate<br>`eval-audit` / Reproducibility<br>`eval-audit` / Regression tracking & cost<br>`ci-audit` / Gate enforcement | - |
| [See also](../engineering/implementation-disciplines.md#see-also) | informative | - | - |

## Part 7: Evaluation

| Section | Class | Mapped checks | Gap |
|---|---|---|---|
| [The enemy is false confidence](../engineering/evaluation.md#the-enemy-is-false-confidence) | process | - | - |
| [Run the loop](../engineering/evaluation.md#run-the-loop) (a) | process | - | - |
| [Run the loop](../engineering/evaluation.md#run-the-loop) (b) | artifact | `eval-audit` / Regression tracking & cost | - |
| [Measure the behaviors that matter](../engineering/evaluation.md#measure-the-behaviors-that-matter) (a) | static | `eval-audit` / Eval coverage<br>`eval-audit` / Prompt / SOP quality | - |
| [Measure the behaviors that matter](../engineering/evaluation.md#measure-the-behaviors-that-matter) (b) | static | `eval-audit` / Methodology soundness | **extend-skill** - Methodology soundness reaches the wrong-grader case as "a metric that is a gameable proxy", but it never asks which grader *type* the behavior needs, and trajectory grading - asserting on the path a run took rather than on its answer - is unrepresented anywhere in the family. |
| [Build a dataset you can trust](../engineering/evaluation.md#build-a-dataset-you-can-trust) | static | `eval-audit` / Contamination / leakage<br>`eval-audit` / Methodology soundness<br>`eval-audit` / Reproducibility | - |
| [Measure honestly](../engineering/evaluation.md#measure-honestly) (a) | artifact | - | **extend-skill** - #517 - no eval-audit dimension requires repeated runs or a reported variance band; the target issue exists to add exactly this one. |
| [Measure honestly](../engineering/evaluation.md#measure-honestly) (b) | artifact | - | **extend-skill** - #516 - extend eval-audit - its Regression tracking & cost dimension is about the cost of running evals, not about pricing a candidate comparison honestly; the target issue is the cost domain whose accounting rules the new eval-audit check should reuse, not itself the thing being extended. |
| [Measure honestly](../engineering/evaluation.md#measure-honestly) (c) | artifact | `eval-audit` / Methodology soundness<br>`eval-audit` / Reproducibility | - |
| [Pick the approach that fits the decision](../engineering/evaluation.md#pick-the-approach-that-fits-the-decision) | static | - | **extend-skill** - no dimension asks whether the eval approach fits the decision it settles, nor whether expensive semantic scoring is staged behind cheap deterministic gates. |
| [Grow the eval into a gate](../engineering/evaluation.md#grow-the-eval-into-a-gate) | static | `eval-audit` / Smoke-test gate<br>`ci-audit` / Gate enforcement | **extend-skill** - the middle rung - "run it in shadow mode on production traffic, blocking nothing, before it can block a merge" - has no dimension anywhere; eval-audit is the owner, and its Smoke-test gate covers only the promoted, merge-blocking end of the ladder. |
| [Use the LLM judge only where it agrees with the human](../engineering/evaluation.md#use-the-llm-judge-only-where-it-agrees-with-the-human) | artifact | `eval-audit` / Methodology soundness | - |
| [Evaluate a multi-agent system unit by unit](../engineering/evaluation.md#evaluate-a-multi-agent-system-unit-by-unit) | static | `eval-audit` / Eval coverage | - |
| [Build escalation ladders: spend measurement where it pays](../engineering/evaluation.md#build-escalation-ladders-spend-measurement-where-it-pays) | static | - | **extend-skill** - no dimension asks whether a fast-path/escalation threshold was justified by an independent recall probe at the crossover rather than set by feel. |
| [Step-by-step: running an evaluation](../engineering/evaluation.md#step-by-step-running-an-evaluation) | process | - | - |
| [Name the anti-patterns out loud](../engineering/evaluation.md#name-the-anti-patterns-out-loud) | artifact | `eval-audit` / Contamination / leakage<br>`eval-audit` / Eval coverage<br>`eval-audit` / Methodology soundness<br>`eval-audit` / Reproducibility | - |
| [See also](../engineering/evaluation.md#see-also) | informative | - | - |

## Troubleshooting guide

| Section | Class | Mapped checks | Gap |
|---|---|---|---|
| [Cost and latency](../engineering/troubleshooting.md#cost-and-latency) | informative | - | - |
| [Reliability](../engineering/troubleshooting.md#reliability) | informative | - | - |
| [Output quality](../engineering/troubleshooting.md#output-quality) | informative | - | - |
| [Measurement and change](../engineering/troubleshooting.md#measurement-and-change) | informative | - | - |

## Coda

| Section | Class | Mapped checks | Gap |
|---|---|---|---|
| [Coda](../engineering/coda.md) | informative | - | - |

## Gap list


### extend-skill

- `README/where-the-binding-rules-live` - docs-audit has no dimension for an authoritative rules file or for doc-vs-doc contradiction; ci-audit's Gate enforcement checks that mismatch only for what CI claims to enforce.
- `lifecycle/front-load-the-judgment-b` - prompt-audit is the nearest owner - a lifecycle workflow is a prompt artifact - but its dimensions judge how a prompt is written, never whether the lifecycle is encoded as one at all, and nothing looks for a scratch TODO file.
- `lifecycle/step-by-step-one-issue-end-to-end-b` - docs-audit is the owner because specs and plans are docs-tree artifacts, but no dimension asks whether a change carries a committed spec and plan, nor scans a plan for placeholders.
- `lifecycle/step-by-step-one-issue-end-to-end-d` - no dimension inspects an agent or subagent definition for an explicit, right-sized model; the nearest is eval-audit's Reproducibility, which wants a pinned model version recorded for an eval run rather than a right-sized one chosen per role.
- `lifecycle/step-by-step-one-issue-end-to-end-e` - prompt-audit is the owner because these are requirements on the text of a dispatching prompt, but no dimension checks a prompt for the operational instructions the project mandates - Tier A judges only the quality of what is already there.
- `lifecycle/make-the-standard-executable-and-audit-periodically-a` - Gate enforcement audits the gates that already exist; no dimension walks the project's binding rules to find the ones with no mechanical enforcer, and the local pre-commit half of the claim is unrepresented anywhere.
- `implementation-disciplines/prompt-and-sop-engineering-a` - prompt-audit's Tier B does audit the SOP structural spec in full, but Tier B declares no bolded dimension bullets so no matrix row can cite it - the fix is to the skill's Dimensions section, not to its coverage.
- `implementation-disciplines/prompt-and-sop-engineering-b` - co-owned - prompt-audit's remediation section already states this rule verbatim as a convention it follows, and eval-audit's Prompt / SOP quality dimension owns prompt-change hygiene through its missing-versioning-or-changelog clause, but neither turns it into a check and nothing reads commit messages.
- `implementation-disciplines/prompt-and-sop-engineering-c` - prompt-audit is the owner but no dimension asks whether a constraint stated in the prompt could be enforced deterministically in code; its counterpart claim sits on ci-and-static-analysis-d.
- `implementation-disciplines/ci-and-static-analysis-a` - Gate enforcement asks whether the type-check runs and is required, never whether it can fail - no dimension measures annotation coverage or checker strictness, the type-checking analogue of test-audit's Assertion strength.
- `implementation-disciplines/ci-and-static-analysis-b` - docs-audit does audit docstrings, but only as an opt-in sub-audit whose own coverage and staleness dimensions sit outside the citable Dimensions section; its Coverage dimension is prose docs per code component, not docstrings, and no dimension asks whether the check is wired into the gate.
- `implementation-disciplines/ci-and-static-analysis-c` (#519) - ci-audit, prompt-audit and eval-audit are already language-neutral, so a TypeScript project still gets its pipeline, prompt and behavioural audits; what it loses is tooling - arch, deps, docs, security and test all declare Python, leaving the lint, format, type-check, docstring, dependency, structure and test dimensions with no TS equivalent.
- `implementation-disciplines/ci-and-static-analysis-d` - no dimension flags a review or audit agent pointed at work a deterministic tool already does; prompt-audit is the nearest owner, as on prompt-and-sop-engineering-c.
- `implementation-disciplines/coding-hygiene-rules-that-surface-at-review-a` (#516) - security-audit reaches only the security-relevant subset (broad handlers that hide security failures); the developer-facing half - an error collapsed into a generic internal error with no type or message - belongs to the observability domain the target issue creates.
- `implementation-disciplines/coding-hygiene-rules-that-surface-at-review-c` - security-audit's Secrets in code is the nearest dimension but is scoped to credentials, and a personal path or profile name is a portability leak rather than a secret, so nothing scans for one.
- `implementation-disciplines/coding-hygiene-rules-that-surface-at-review-d` - docstring currency is a staleness question, and docs-audit reaches it only through its opt-in docstring sub-audit, outside the citable Dimensions section; self-documenting settings fields and provider-safe tool-argument types have no dimension anywhere.
- `evaluation/measure-the-behaviors-that-matter-b` - Methodology soundness reaches the wrong-grader case as "a metric that is a gameable proxy", but it never asks which grader *type* the behavior needs, and trajectory grading - asserting on the path a run took rather than on its answer - is unrepresented anywhere in the family.
- `evaluation/measure-honestly-a` (#517) - no eval-audit dimension requires repeated runs or a reported variance band; the target issue exists to add exactly this one.
- `evaluation/measure-honestly-b` (#516) - extend eval-audit - its Regression tracking & cost dimension is about the cost of running evals, not about pricing a candidate comparison honestly; the target issue is the cost domain whose accounting rules the new eval-audit check should reuse, not itself the thing being extended.
- `evaluation/pick-the-approach-that-fits-the-decision` - no dimension asks whether the eval approach fits the decision it settles, nor whether expensive semantic scoring is staged behind cheap deterministic gates.
- `evaluation/grow-the-eval-into-a-gate` - the middle rung - "run it in shadow mode on production traffic, blocking nothing, before it can block a merge" - has no dimension anywhere; eval-audit is the owner, and its Smoke-test gate covers only the promoted, merge-blocking end of the ladder.
- `evaluation/build-escalation-ladders-spend-measurement-where-it-pays` - no dimension asks whether a fast-path/escalation threshold was justified by an independent recall probe at the crossover rather than set by feel.

### new-domain

- `lifecycle/front-load-the-judgment-c` - no skill reads the issue tracker, so whether work traces to an issue sits outside the family's evidence base entirely.
- `lifecycle/keep-batches-small-and-the-flow-fast` - batch size and the DORA four measures are delivery-history evidence; ci-audit reads workflow definitions rather than delivery outcomes, and no skill reads pull-request or deployment history.
- `lifecycle/step-by-step-one-issue-end-to-end-c` - branch, pull-request and merge mechanics live in git and tracker history, which no skill in the family reads.
- `lifecycle/after-the-merge` - the post-merge trail is entirely tracker-side, so nothing in the family can see whether criteria were verified, ticked, or blind-checked.
- `implementation-disciplines/the-code-review-protocol-b` - the review trail - inline pull-request comments and the findings table with its dispositions - is tracker-side evidence no skill reads, and no domain audits review discipline.

### report-only

- `lifecycle/make-the-standard-executable-and-audit-periodically-b` - this is audit-core's own charter, but audit-core declares no dimensions so no row can cite it; audit cadence and past audit reports are outside every skill's evidence base.

## Coverage summary

| Class | Rows |
|---|---|
| static | 24 |
| artifact | 14 |
| process | 12 |
| informative | 10 |

60 rows total; 16/38 auditable rows mapped (42%); 28 gap rows; 12 process-only rows.
