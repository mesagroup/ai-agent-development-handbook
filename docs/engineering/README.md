# How We Develop at Lidia

A vademecum: the way we build software and AI agents, and — more importantly — *why* we build them this way. It is a handbook for judgment, not a rulebook. The commands and the checklists matter, but they are downstream of a few convictions that recur in every section. Read this page first; it is the lens for the rest.

The practices here are meant to be portable. Some of them are supported by shared infrastructure we maintain (a model catalog, a configuration system, a run harness), but nothing below *depends* on that infrastructure — a project that reuses none of it should still recognize every principle as its own. Where a section describes a capability, treat it as "here is what a good setup provides and why," not "here is our specific tool."

## Two throughlines

Almost everything below is an application of one of two ideas.

### 1. Evidence over intuition — the enemy is false confidence

Every non-trivial change to an agent, a prompt, or an extractor is a *hypothesis*: "this will be better." "Better" only means something against a metric, and a metric is only trustworthy against a dataset the change under test did not get to define.

The failure mode we guard against is not *no* confidence — it is **false** confidence. The naive paths (add patterns until the suite is green, tweak a prompt until the one example you're looking at reads well, pick the model that impressed in a demo) do not leave you uncertain. They leave you confidently wrong, which is worse, because confidence is when you stop looking. So we make the dataset and the metric exist *before* the decision, so the decision is falsifiable and a wrong turn is visible instead of comfortable. This is the subject of [Part 5 — Evaluation](evaluation.md), but its discipline leaks into everything: we calibrate the data before locking a schema, we instrument before we tune, we account for the full cost and not the convenient part.

### 2. Capture the trail — a decision and its evidence should outlive the moment

We work in the open and we write things down. A spec before code; a plan before implementation; a story after a piece of work lands; a recorded result after an experiment. The point is not ceremony. It is that a decision made six months ago, and the evidence that justified it, has to be recoverable by someone who wasn't there — including our future selves. The artifact trail is how the system stays honest as the data, the models, and the team drift. This is the subject of [Part 7 — Documentation & knowledge capture](documentation.md).

## The stance: we develop *with* agents

The systems we build are agents, and increasingly they are also built *by* agents under human direction. Both facts shape how we work.

Raising the level of abstraction — from hand-writing every line to directing an agent that writes it — does not abolish the hard work; it **relocates it upward**. The floor rises and the interesting work moves to knowing what you want, decomposing it, exercising judgment, and *verifying*. A higher layer sheds the accidental complexity of the level below but never the essential complexity of the problem, and it leaks, so the level below still has to be understood when it shows through. Concretely: an agent can write a whole module from a good plan, but writing the good plan, catching the subtle spec violation in review, and designing the eval that proves the module is actually better — that is the work now, and it is not less work.

This is why the lifecycle in [Part 1](lifecycle.md) puts so much weight on the spec, the plan, the review gates, and the human-in-the-loop decisions: those are exactly the places where the hard part now lives. Delegation without a spec, a plan, and a verification step is just guessing at scale.

## The parts

| Part | What it covers |
|---|---|
| **[1 — Development lifecycle](lifecycle.md)** | Issue → spec → plan → implement → review → merge. TDD, the human-in-the-loop gates, subagent-driven development, CI, static analysis, the code-review protocol, when to add an end-to-end agent quality gate, and the coding-hygiene rules that surface at review. |
| **[2 — Codebase structure](codebase-structure.md)** | Layered architecture with strict acyclic dependencies — what it is and why it holds down the integration tax. Agent composition and provider polymorphism. |
| **[3 — The extended agent harness](agent-harness.md)** | The capabilities a good agent setup provides: provider-agnostic model selection, configuration and named profiles, headless CLI execution, cheap/mock backends, and bounded external calls. |
| **[4 — Observability](observability.md)** | Instrument before you tune; keep observability out of the model's context; per-(sub)agent tokens, timing, and cost; full-cost accounting; and the production → development feedback loop. |
| **[5 — Evaluation: how we decide](evaluation.md)** | Build → measure → decide → re-measure. Trustworthy datasets, variance and cost, which method fits which decision, LLM-as-judge vs human-in-the-loop, evaluating a multi-agent system unit by unit, and escalation ladders. |
| **[6 — The three-layer document model](three-layer-model.md)** | Why a generic, domain-independent decomposition (intrinsic structure / domain entities / workflow knowledge) is the right organizing principle for document-AI, and the contracts (engine-agnostic representation, stable IDs, versioned enrichment) that make it pay off. |
| **[7 — Documentation & knowledge capture](documentation.md)** | Keeping docs in sync with code, the architecture-vs-research split, cross-reference sanity, and the decision-trail artifacts. |

## Where the binding rules live

This handbook explains and connects; it teaches the reasoning. The *binding*, project-specific rules — exact coding standards, review thresholds, the merge checklist, the git workflow — belong in your project's rules file (the file your team and your coding agents both read as authoritative). When this handbook and that file disagree, the rules file wins, and the mismatch is a docs bug to fix (see [Part 7](documentation.md)).
