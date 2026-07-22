# How We Develop at Lidia

A vademecum: the way we build software and agents in this repository, and — more importantly — *why* we build them this way. It is a handbook for judgment, not a rulebook. The commands and the checklists matter, but they are downstream of a few convictions that recur in every section. Read this page first; it is the lens for the rest.

## Two throughlines

Almost everything below is an application of one of two ideas.

### 1. Evidence over intuition — the enemy is false confidence

Every non-trivial change to an agent, a prompt, or an extractor is a *hypothesis*: "this will be better." "Better" only means something against a metric, and a metric is only trustworthy against a dataset the change under test did not get to define.

The failure mode we guard against is not *no* confidence — it is **false** confidence. The naive paths (add regex patterns until the suite is green, tweak a prompt until the one example you're looking at reads well, pick the model that impressed in a demo) do not leave you uncertain. They leave you confidently wrong, which is worse, because confidence is when you stop looking. So we make the dataset and the metric exist *before* the decision, so the decision stays falsifiable and a wrong turn is visible instead of comfortable. This is the subject of [Part 5 — Evaluation](evaluation.md), but its discipline leaks into everything: we calibrate the corpus before locking a schema, we instrument before we tune, we account for the full cost and not the convenient part.

### 2. Capture the trail — a decision and its evidence should outlive the moment

We work in the open and we write things down. A spec before code; a plan before implementation; a story after a piece of work lands; a leaderboard entry and an evaluation-history line after an experiment. The point is not ceremony. It is that a decision made six months ago, and the evidence that justified it, has to be recoverable by someone who wasn't there — including our future selves. The artifact trail is how the system stays honest as the corpus, the models, and the team drift. This is the subject of [Part 7 — Documentation & knowledge capture](documentation.md).

## The stance: we develop *with* agents

This codebase is built largely *by* agents, under human direction, and it also *is* a collection of agents. Both facts shape how we work.

Raising the level of abstraction — from hand-writing every line to directing an agent that writes it — does not abolish the hard work; it **relocates it upward**. The floor rises and the interesting work moves to knowing what you want, decomposing it, exercising judgment, and *verifying*. A higher layer sheds the accidental complexity of the level below but never the essential complexity of the problem, and it leaks, so the level below still has to be understood when it shows through. Concretely: an agent can write a whole module from a good plan, but writing the good plan, catching the subtle spec violation in review, and designing the eval that proves the module is actually better — that is the work now, and it is not less work.

This is why the lifecycle in [Part 1](lifecycle.md) puts so much weight on the spec, the plan, the review gates, and the human-in-the-loop decisions: those are exactly the places where the hard part now lives. Delegation without a spec, a plan, and a verification step is just guessing at scale.

## The parts

| Part | What it covers |
|---|---|
| **[1 — Development lifecycle](lifecycle.md)** | Issue → spec → plan → implement → review → merge. TDD, the human-in-the-loop gates, subagent-driven development, CI, static analysis, the code-review protocol, the smoke-test quality gate, and the coding-hygiene rules that surface at review. |
| **[2 — Codebase structure](codebase-structure.md)** | The seven-tier architecture and the strict acyclic import rules — what they are and why they hold down the integration tax. Agent composition and provider polymorphism. |
| **[3 — The extended agent harness](agent-harness.md)** | Model catalog, configuration infrastructure and named profiles, CLI-first headless execution, cheap/mock backends, and the timeout/hardening lessons. |
| **[4 — Observability](observability.md)** | Instrument before you tune; keep observability out of the model's context; per-(sub)agent tokens, timing, and cost; full-cost accounting; and the production → R&D feedback loop. |
| **[5 — Evaluation: how we decide](evaluation.md)** | Build → measure → decide → re-measure. Trustworthy datasets, variance and cost, which method fits which decision, LLM-as-judge vs human-in-the-loop, evaluating a multi-agent system unit by unit, and escalation ladders. |
| **[6 — The three-layer document model](three-layer-model.md)** | Why a generic, domain-independent decomposition (intrinsic structure / domain entities / workflow knowledge) is the right organizing principle, and the contracts (engine-agnostic IR, stable IDs, versioned enrichment) that make it pay off. |
| **[7 — Documentation & knowledge capture](documentation.md)** | Keeping docs in sync with code, the architecture-vs-research split, cross-reference sanity, and the decision-trail artifacts. |

## Where the rules actually live

This handbook explains and connects; it does not replace the authoritative sources. The binding rules are in [`CLAUDE.md`](../../CLAUDE.md) (coding rules, review thresholds, git workflow, task management). The decision *philosophy* has its own entry point in [Data-Driven Development](../eval/data-driven-development.md). When this handbook and those disagree, they win — and that is a docs bug to fix (see [Part 7](documentation.md)).
