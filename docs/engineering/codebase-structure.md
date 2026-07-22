# Part 2 — Codebase Structure

We organize the codebase into layered tiers with **acyclic dependencies** between them. This is not bureaucratic tidiness — it is the same conviction as the [three-layer document model](three-layer-model.md), applied one level up: **the reusable core is real, and only the task-shaped layer is use-relative.** Lower tiers are the reusable core; the agents and applications are the task layer. Keeping the dependencies directional and acyclic is what stops the reusable core from quietly acquiring one application's assumptions, and it is what lets us pay the "wire this up" integration tax once instead of per agent.

## The shape: tiers ordered by reuse

The exact tier list is a project's own choice; what matters is the *ordering principle*. Sort the code by how much of it carries over to the next agent or task, and let dependencies run only from the task-shaped code toward the reusable core — never the other way, and never in a cycle. A typical layering, from most reusable to most task-specific:

| Tier | Role | Reuse |
|---|---|---|
| **Shared schemas / types** | The typed data contracts other tiers exchange. Standalone. | Universal |
| **Core infrastructure** | Cross-cutting machinery: the run harness, model access, hooks, storage, timeouts, logging. | Universal |
| **Configuration** | How runs are parameterized: settings, named profiles. | Universal |
| **External integrations** | Clients and adapters for third-party services and APIs. | Broad |
| **Capabilities** | Opt-in, cross-agent units of behaviour an application composes. | Broad |
| **Evaluation** | The harness that measures the tiers above. | Broad |
| **Agents / applications** | The task-shaped layer — a specific product built from everything below. | Single-use |

## The rule: dependencies point toward the core, and never cycle

The one invariant: **an import may only point at a more-reusable tier than the one it lives in, and the dependency graph has no cycles.** Core infrastructure cannot import an application's types; an integration cannot import an agent. Cross-application reuse happens by *composition* (one agent exposed to another as a tool), never by one application reaching into another's internals.

Write the rule down explicitly for your project — which tier may import which — so it is enforceable, ideally by an import-linter in CI rather than by memory.

## Why the rules matter

Read the arrows and the reason is visible: a lower tier never depends on the specifics of a higher, task-shaped one. This is the architectural enforcement of the same rule the document model states for its shared layer — *keep the reusable core sparse and stable; keep the task layer rich and disposable.* A convenience that a single application needs must live in that application, not migrate down into the core where it would bake one workflow's assumptions into shared code and couple every other consumer to them.

The acyclic, directional shape buys three concrete things:

- **Each tier is independently testable.** An integration can be exercised without standing up an agent, because it cannot depend on one. The dependency graph *is* the test-isolation boundary.
- **Churn stays local.** Change an application and nothing below it can break, because nothing below it imports it. Change a core utility and the blast radius is explicit — it is exactly the set of tiers above it, which the type-checker can enumerate.
- **The integration tax is paid once.** New agents reuse the harness, the config machinery, the eval framework, and the integrations as-is (see [Part 3](agent-harness.md)). The marginal agent is mostly its prompt/SOP and its tools, not a fresh copy of the plumbing.

An import that would violate a rule is therefore a **design smell, not a lint nuisance.** If an application-specific concept is pulling toward the core, the concept is in the wrong tier, or it is two concepts that need splitting. The rule is doing its job by making that visible at the import line.

## Agent composition: typed hooks over a generic runner

Agents are not forks of a base agent; they are **configurations of shared machinery**. A generic runner in the core tier owns the run lifecycle and exposes a small set of hook methods (create the agent, build the collector, format the query, post-process the result, and so on). Each application customizes behaviour by overriding those hooks, and narrows the runner's loose metadata into its own typed sub-models, so its run records are structured and self-describing rather than a loose bag of keys. This is composition-over-inheritance: the reusable runner, the disposable task layer.

Multi-agent systems are built by exposing one agent to another **as a tool** — the only sanctioned cross-application dependency. An orchestrator spawns its sub-agents (a retriever, a tool-user, a writer) this way. Design the split so it reflects a genuine data dependency between the sub-agents, not an arbitrary partition; a sub-agent boundary that doesn't correspond to a real hand-off just adds latency.

## Provider polymorphism: dispatch on a discriminator, not a type

Where a component has interchangeable backends (say, several research or model providers), select them through a **polymorphic configuration** rather than conditionals scattered across call sites. Give a base config a `mode` (or `kind`) discriminator, let each concrete variant live in its own module, and dispatch with a `match` on the discriminator literal — **never** an `isinstance()` chain, which couples the dispatcher to every concrete class and quietly breaks the tier boundaries. A settings library that resolves environment variables per variant keeps the wiring declarative. Expose one provider-agnostic entry point that returns a uniform result type, so an application swaps a backend by changing a config value, not its own code.

## Named profiles: configuration as a first-class, named thing

A configuration worth reusing gets a name. Bundle a model, its parameters, and feature toggles into a machine-readable named profile, selectable by name (and discoverable by listing). Scripts, eval harnesses, and agents then reference a configuration *by name* instead of reconstructing a pile of flags — which is what makes an experiment reproducible and a "run the cheap profile" instruction unambiguous (see [Part 3](agent-harness.md)).

## See also

- [Part 3 — The extended agent harness](agent-harness.md) — the shared machinery agents reuse.
- [Part 6 — The three-layer document model](three-layer-model.md) — the same reusable-core-vs-task-layer idea, one level down.
- [Handbook index](README.md).
