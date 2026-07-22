# Part 2. Codebase Structure

Organize the codebase into layered tiers with **acyclic dependencies** between them. This is not bureaucratic tidiness, it is the same conviction as the [three-layer document model](three-layer-model.md), applied one level up: **the reusable core is real, and only the task-shaped layer is use-relative.** Lower tiers are the reusable core; the agents and applications are the task layer. Keep the dependencies directional and acyclic to stop the reusable core from quietly acquiring one application's assumptions, and to pay the "wire this up" integration tax once instead of per agent.

## Order the tiers by reuse

Pick your own tier list; what matters is the *ordering principle*. Sort the code by how much of it carries over to the next agent or task, and let dependencies run only from the task-shaped code toward the reusable core, never the other way, and never in a cycle. A typical layering, from most reusable to most task-specific:

| Tier | Role | Reuse |
|---|---|---|
| **Shared schemas / types** | The typed data contracts other tiers exchange. Standalone. | Universal |
| **Core infrastructure** | Cross-cutting machinery: the run harness, model access, hooks, storage, timeouts, logging. | Universal |
| **Configuration** | How runs are parameterized: settings, named profiles. | Universal |
| **External integrations** | Clients and adapters for third-party services and APIs. | Broad |
| **Capabilities** | Opt-in, cross-agent units of behaviour an application composes. | Broad |
| **Evaluation** | The harness that measures the tiers above. | Broad |
| **Agents / applications** | The task-shaped layer, a specific product built from everything below. | Single-use |

## Point every dependency toward the core, and never cycle

Hold one invariant: **an import may only point at a more-reusable tier than the one it lives in, and the dependency graph has no cycles.** Don't let core infrastructure import an application's types, or an integration import an agent. Reuse across applications by *composition* (expose one agent to another as a tool), never by one application reaching into another's internals.

Write the rule down explicitly for your project, which tier may import which, so it is enforceable, ideally by an import-linter in CI rather than by memory.

## Why the rule matters

Read the arrows and the reason is visible: a lower tier never depends on the specifics of a higher, task-shaped one. This is the architectural enforcement of the same rule the document model states for its shared layer, *keep the reusable core sparse and stable; keep the task layer rich and disposable.* Keep a convenience that a single application needs inside that application; don't migrate it down into the core, where it would bake one workflow's assumptions into shared code and couple every other consumer to them.

The acyclic, directional shape buys three concrete things:

- **Each tier is independently testable.** You can exercise an integration without standing up an agent, because it cannot depend on one. The dependency graph *is* the test-isolation boundary.
- **Churn stays local.** Change an application and nothing below it can break, because nothing below it imports it. Change a core utility and the blast radius is explicit, exactly the set of tiers above it, which the type-checker can enumerate.
- **The integration tax is paid once.** New agents reuse the harness, the config machinery, the eval framework, and the integrations as-is (see [Part 3](agent-harness.md)). The marginal agent is mostly its prompt/SOP and its tools, not a fresh copy of the plumbing.

Treat an import that would violate a rule as a **design smell, not a lint nuisance.** If an application-specific concept is pulling toward the core, the concept is in the wrong tier, or it is two concepts that need splitting. The rule is doing its job by making that visible at the import line.

## Watch for structural decay beyond layering

Layering is the highest-value axis, but it is not the only way structure decays, and a clean layer graph can still hide modules that are painful to change. A codebase that has grown organically drifts in ways a dependency rule alone won't catch, so periodically measure the **declared** architecture against the **real** one (what the imports actually do) and watch a few more signals:

- **Cycles**: import cycles defeat the isolation the tiers were meant to give and make the graph un-orderable. Treat a cycle *within* a package as a warning and one *across* package boundaries as a real break.
- **Coupling and cohesion**: a hub module everything imports (or one that reaches into everything) becomes a change-amplifier: touching it ripples everywhere. A grab-bag `utils` whose contents don't belong together is the same problem wearing a different name. Split both along cohesion seams, files that change together belong together.
- **Complexity**: a function whose cyclomatic complexity or nesting depth resists understanding also resists testing; high complexity and low coverage tend to be the same modules.
- **Dead code**: modules, functions, or exports reachable from nothing are cost with no benefit, but verify true unreachability before deleting (a plugin entry point, a dynamic import, or a re-export can look dead and not be).
- **File size**: a file grown past what a reader can hold in one sitting is a cohesion smell; flag the outliers.

Treat these as health signals, not absolutes, an oversized-but-cohesive file or a moderately complex function may be fine. Measure them deliberately rather than discovering them during a refactor that keeps rippling further than expected. And per [Part 1](lifecycle.md), the durable fix for the layering rule specifically is to encode it as an import-linter contract in CI, so a violation can't silently return.

## Compose agents with typed hooks over a generic runner

Don't fork a base agent; **configure shared machinery**. Give the core tier a generic runner that owns the run lifecycle and exposes a small set of hook methods (create the agent, build the collector, format the query, post-process the result, and so on). Customize each application by overriding those hooks, and narrow the runner's loose metadata into your own typed sub-models, so run records are structured and self-describing rather than a loose bag of keys. This is composition-over-inheritance: the reusable runner, the disposable task layer.

Build multi-agent systems by exposing one agent to another **as a tool**: the only sanctioned cross-application dependency. Let an orchestrator spawn its sub-agents (a retriever, a tool-user, a writer) this way. Design the split so it reflects a genuine data dependency between the sub-agents, not an arbitrary partition; a sub-agent boundary that doesn't correspond to a real hand-off just adds latency.

## Dispatch on a discriminator, not a type

Where a component has interchangeable backends (say, several research or model providers), select them through a **polymorphic configuration** rather than conditionals scattered across call sites. Give a base config a `mode` (or `kind`) discriminator, let each concrete variant live in its own module, and dispatch with a `match` on the discriminator literal, **never** an `isinstance()` chain, which couples the dispatcher to every concrete class and quietly breaks the tier boundaries. Let a settings library resolve environment variables per variant to keep the wiring declarative. Expose one provider-agnostic entry point that returns a uniform result type, so an application swaps a backend by changing a config value, not its own code.

## Name every configuration worth reusing

A configuration worth reusing gets a name. Bundle a model, its parameters, and feature toggles into a machine-readable named profile, selectable by name (and discoverable by listing). Then have scripts, eval harnesses, and agents reference a configuration *by name* instead of reconstructing a pile of flags, which is what makes an experiment reproducible and a "run the cheap profile" instruction unambiguous (see [Part 3](agent-harness.md)).

## Checklist: placing new code / reviewing an import

- [ ] The new code lives in the **most reusable tier that fully contains its concerns**: no lower.
- [ ] Every import points at a more-reusable tier; none points sideways into another application or up toward a task layer.
- [ ] No new import cycle (within or across packages).
- [ ] A single-application convenience stayed *in* that application, not migrated into shared core.
- [ ] Cross-application reuse is via `as_tool()` composition, not internal reach-in.
- [ ] Backend selection dispatches on a discriminator (`match`), not an `isinstance()` chain.
- [ ] The layering rule is (or is now) an import-linter contract in CI, not just prose.

## See also

- [Part 3. The extended agent harness](agent-harness.md), the shared machinery agents reuse.
- [Part 6. The three-layer document model](three-layer-model.md), the same reusable-core-vs-task-layer idea, one level down.
- [Handbook index](README.md).
