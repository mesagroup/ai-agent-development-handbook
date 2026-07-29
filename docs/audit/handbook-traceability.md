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
- `evaluation/measure-the-behaviors-that-matter-b` - Methodology soundness reaches the wrong-grader case as "a metric that is a gameable proxy", but it never asks which grader *type* the behavior needs, and trajectory grading - asserting on the path a run took rather than on its answer - is unrepresented anywhere in the family.
- `evaluation/measure-honestly-a` (#517) - no eval-audit dimension requires repeated runs or a reported variance band; the target issue exists to add exactly this one.
- `evaluation/measure-honestly-b` (#516) - extend eval-audit - its Regression tracking & cost dimension is about the cost of running evals, not about pricing a candidate comparison honestly; the target issue is the cost domain whose accounting rules the new eval-audit check should reuse, not itself the thing being extended.
- `evaluation/pick-the-approach-that-fits-the-decision` - no dimension asks whether the eval approach fits the decision it settles, nor whether expensive semantic scoring is staged behind cheap deterministic gates.
- `evaluation/grow-the-eval-into-a-gate` - the middle rung - "run it in shadow mode on production traffic, blocking nothing, before it can block a merge" - has no dimension anywhere; eval-audit is the owner, and its Smoke-test gate covers only the promoted, merge-blocking end of the ladder.
- `evaluation/build-escalation-ladders-spend-measurement-where-it-pays` - no dimension asks whether a fast-path/escalation threshold was justified by an independent recall probe at the crossover rather than set by feel.

## Coverage summary

| Class | Rows |
|---|---|
| static | 8 |
| artifact | 6 |
| process | 5 |
| informative | 8 |

27 rows total; 9/14 auditable rows mapped (64%); 7 gap rows; 5 process-only rows.
