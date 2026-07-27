# AI Agent Development Handbook

How to build software and AI agents here, and why. Read each section as a set of **directives backed by their reasons**: it states what to do, then why the practice earns its place. The reasons matter, they are what let you apply a rule to a case it doesn't literally cover, but when you just need to act, the directives and the checklists are the operational surface.

The practices are meant to be portable. Some are supported by shared infrastructure we maintain (a model catalog, a configuration system, a run harness), but nothing below *depends* on it, a project that reuses none of it should still recognize every directive as its own. Where a section describes a capability, read it as "here is what a good setup provides, and what to build or demand if you don't have it," not "here is our specific tool."

## How to use this handbook

- **Follow the imperatives.** Each section is written as instructions. Do what they say; the prose next to each one tells you why, so you can adapt it when your case is off-pattern.
- **Use the checklists as the working surface.** Most parts end with a checklist. Paste it into a PR description, an issue, or a review comment and tick it. Where a part describes a procedure (the lifecycle, an eval run, a security sweep), it also gives a **step-by-step** you can run top to bottom.
- **Treat the reasons as load-bearing, not decoration.** A rule you follow without knowing why is a rule you'll misapply at the first edge case. When a directive and reality collide, the *why* is how you decide.

## Two throughlines

Almost every directive below is an application of one of two ideas. Internalize these and the rest follows.

### 1. Prefer evidence over intuition: the enemy is false confidence

Treat every non-trivial change to an agent, a prompt, or an extractor as a *hypothesis*: "this will be better." "Better" only means something against a metric, and a metric is only trustworthy if the dataset it runs on was fixed independently of the change under test. If the change got to shape the very examples it is judged on (patterns added until they pass, a prompt tuned to the one case you were looking at), the metric measures the tuning, not the improvement.

Guard against **false** confidence, not the mere absence of it. The naive paths, add patterns until the suite is green, tweak a prompt until the one example you're looking at reads well, pick the model that impressed in a demo, do not leave you uncertain. They leave you confidently wrong, which is worse, because confidence is when you stop looking. So make the yardstick exist *before* the decision, the test suite before the code (this is just TDD), the dataset and the metric before the model or prompt change, so the decision is falsifiable and a wrong turn is visible instead of comfortable. This is the subject of [Part 6. Evaluation](evaluation.md), but its discipline leaks into everything: calibrate the data before locking a schema, instrument before you tune, account for the full cost and not the convenient part.

### 2. Capture the trail: a decision and its evidence should outlive the moment

Work in the open and write things down: a spec before code; a plan before implementation; a story after a piece of work lands; a recorded result after an experiment. The point is not ceremony. It is that a decision made six months ago, and the evidence that justified it, has to be recoverable by someone who wasn't there, including your future self. The artifact trail is how the system stays honest as the data, the models, and the team drift. This is the subject of [Part 7. Documentation & knowledge capture](documentation.md).

## The stance: you develop *with* agents

The systems we build are agents, and increasingly they are also built *by* agents under human direction. Both facts shape how to work.

Raising the level of abstraction, from hand-writing every line to directing an agent that writes it, does not abolish the hard work; it **relocates it upward**. The floor rises and the interesting work moves to knowing what you want, decomposing it, exercising judgment, and *verifying*. A higher layer sheds the accidental complexity of the level below but never the essential complexity of the problem, and it leaks, so you still have to understand the level below when it shows through. Concretely: an agent can write a whole module from a good plan, but writing the good plan, catching the subtle spec violation in review, and designing the eval that proves the module is actually better, that is the work now, and it is not less work.

This is why the lifecycle in [Part 1](lifecycle.md) puts so much weight on the spec, the plan, the review gates, and the human-in-the-loop decisions: those are exactly the places where the hard part now lives. Delegating without a spec, a plan, and a verification step is just guessing at scale.

## The parts

| Part | What it covers |
|---|---|
| **[1. Development lifecycle](lifecycle.md)** | Issue → spec → plan → implement → review → merge. TDD, the human-in-the-loop gates, subagent-driven development, CI, static analysis, the code-review protocol, when to add an end-to-end agent quality gate, and the coding-hygiene rules that surface at review. |
| **[2. Codebase structure](codebase-structure.md)** | Layered architecture with strict acyclic dependencies, what it is and why it holds down the integration tax. Agent composition and provider polymorphism. |
| **[3. The three-layer document model](three-layer-model.md)** | Why a generic, domain-independent decomposition (intrinsic structure / domain entities / workflow knowledge) is the right organizing principle for document-AI, and the contracts (engine-agnostic representation, stable IDs, versioned enrichment) that make it pay off. |
| **[4. The extended agent harness](agent-harness.md)** | The capabilities a good agent setup provides: provider-agnostic model selection, configuration and named profiles, headless CLI execution, cheap/mock backends, and bounded external calls. |
| **[5. Observability](observability.md)** | Instrument before you tune; keep observability out of the model's context; per-(sub)agent tokens, timing, and cost; full-cost accounting; and the production → development feedback loop. |
| **[6. Evaluation: how to decide](evaluation.md)** | Build → measure → decide → re-measure. Trustworthy datasets, variance and cost, which method fits which decision, LLM-as-judge vs human-in-the-loop, evaluating a multi-agent system unit by unit, and escalation ladders. |
| **[7. Documentation & knowledge capture](documentation.md)** | Keeping docs in sync with code, the architecture-vs-research split, cross-reference sanity, and the decision-trail artifacts. |
| **[8. Security, dependencies & supply chain](security-supply-chain.md)** | The safety surfaces the other parts don't cover: first-party code (untrusted-source-to-sink), secrets, the dependency graph (licenses, CVEs, pinning), and the pipeline as a privileged environment. |

## Where the binding rules live

This handbook explains and connects; it teaches the reasoning. The *binding*, project-specific rules, exact coding standards, review thresholds, the merge checklist, the git workflow, belong in your project's rules file (the file your team and your coding agents both read as authoritative). When this handbook and that file disagree, the rules file wins, and the mismatch is a docs bug to fix (see [Part 7](documentation.md)).
