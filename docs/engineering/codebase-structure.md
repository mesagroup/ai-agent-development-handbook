# Part 3. Codebase Structure

*Your change is planned and built; whether it lands cleanly or ripples into places it had no business touching is decided by the structure it meets on arrival. This part gives that structure one organizing idea (the reusable core versus the disposable task layer) and one invariant that holds the idea in place.*

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
| **Agents / applications** | The task-shaped layer, a specific product built from everything below. | Single&#8209;use |

## Point every dependency toward the core, and never cycle

Hold one invariant: **an import may only point at a more-reusable tier than the one it lives in, and the dependency graph has no cycles.** Don't let core infrastructure import an application's types, or an integration import an agent. Reuse across applications by *composition* (expose one agent to another as a tool), never by one application reaching into another's internals.

```d2 title="Tiers, and the direction an import may point"
task: Task layer {
  direction: right
  width: 240
  a: Agent A
  b: Agent B
  a -> b: as_tool {style.stroke-dash: 4}
}
core: Reusable core {
  grid-rows: 2
  ev: Evaluation
  cap: Capabilities
  integ: External integrations
  conf: Configuration
  infra: Core infrastructure
  types: "Shared schemas / types"
}
task -> core: imports point at the core
core -> task: "never, and\nnever in a cycle" {style.stroke-dash: 4}
```

Write the rule down explicitly for your project, which tier may import which, so it is enforceable, ideally by an import-boundary linter in CI rather than by memory ([import-linter](https://import-linter.readthedocs.io/) in Python, [dependency-cruiser](https://github.com/sverweij/dependency-cruiser) in the JavaScript ecosystem).

## Why the rule matters

Read the arrows and the reason is visible: a lower tier never depends on the specifics of a higher, task-shaped one. This is the architectural enforcement of the same rule the document model states for its shared layer, *keep the reusable core sparse and stable; keep the task layer rich and disposable.* Keep a convenience that a single application needs inside that application; don't migrate it down into the core, where it would bake one workflow's assumptions into shared code and couple every other consumer to them.

The acyclic, directional shape buys three concrete things:

- **Each tier is independently testable.** You can exercise an integration without standing up an agent, because it cannot depend on one. The dependency graph *is* the test-isolation boundary.
- **Churn stays local.** Change an application and nothing below it can break, because nothing below it imports it. Change a core utility and the blast radius is explicit, exactly the set of tiers above it, which the type-checker can enumerate.
- **The integration tax is paid once.** New agents reuse the harness, the config machinery, the eval framework, and the integrations as-is (see [Part 5](agent-harness.md)). The marginal agent is mostly its prompt/SOP and its tools, not a fresh copy of the plumbing.

Treat an import that would violate a rule as a **design smell, not a lint nuisance.** If an application-specific concept is pulling toward the core, the concept is in the wrong tier, or it is two concepts that need splitting. The rule is doing its job by making that visible at the import line.

## Watch for structural decay beyond layering

Layering is the highest-value axis, but it is not the only way structure decays, and a clean layer graph can still hide modules that are painful to change. A codebase that has grown organically drifts in ways a dependency rule alone won't catch, so periodically measure the **declared** architecture against the **real** one (what the imports actually do) and watch a few more signals:

- **Cycles**: import cycles defeat the isolation the tiers were meant to give and make the graph un-orderable. Treat a cycle *within* a package as a warning and one *across* package boundaries as a real break.
- **Coupling and cohesion**: a hub module everything imports (or one that reaches into everything) becomes a change-amplifier: touching it ripples everywhere. A grab-bag `utils` whose contents don't belong together is the same problem wearing a different name. Split both along cohesion seams, files that change together belong together.
- **Complexity**: a function whose cyclomatic complexity or nesting depth resists understanding also resists testing; high complexity and low coverage tend to be the same modules.
- **Dead code**: modules, functions, or exports reachable from nothing are cost with no benefit, but verify true unreachability before deleting (a plugin entry point, a dynamic import, or a re-export can look dead and not be).
- **File size**: a file grown past what a reader can hold in one sitting is a cohesion smell; flag the outliers.

Treat these as health signals, not absolutes, an oversized-but-cohesive file or a moderately complex function may be fine. Measure them deliberately rather than discovering them during a refactor that keeps rippling further than expected. And per [Part 1](lifecycle.md), the durable fix for the layering rule specifically is to encode it as an import-linter contract in CI, so a violation can't silently return.

## Count the runtimes, and make each one earn its place

The tier list assumes one language stack. Each additional runtime brings its own dependency graph and lockfile, its own test suite and the gate that runs it, its own vulnerability and licence surface, and its own upgrade cadence that somebody has to schedule. Those costs are fixed and they recur, while the reason a second stack arrives is usually local and momentary - one library that exists only there, one function a platform wants in a different language, one contributor's fluency.

So **carry the fewest runtimes that do the work, and treat each additional one as a decision rather than a consequence.** A second stack earns its place when the work genuinely cannot be done in the primary one and the team can carry both; it does not earn it by being the language whoever wrote that component reached for first. That judgment is yours, because it turns on which libraries exist and who you can staff - but it is a judgment somebody should make on purpose.

**Name every runtime the project carries in its [binding-rules file](README.md#where-the-binding-rules-live)** (see also [Part 8](documentation.md)), marking which one is primary, and for each of the others say what it buys and who maintains it. What this prevents is not a second stack, it is an unowned one: a service or a function in another language, with a dependency file nobody locked, no test command anyone runs, and no CI lane, which stays invisible until it breaks or a vulnerability lands in it. A stack that arrives as several separate footprints, each with its own dependency file and none of them named, is that failure repeated rather than one instance of it.

A declared stack's costs are ordinary and live where the rest of the handbook puts them: its tests and the gate that runs them in [Part 2](implementation-disciplines.md), its lockfile and its vulnerability surface in [Part 9](security-supply-chain.md). What this section governs is the count and the declaration, not those costs.

## Compose agents with typed hooks over a generic runner

Don't fork a base agent; **configure shared machinery**. Give the core tier a generic runner that owns the run lifecycle and exposes a small set of hook methods (create the agent, build the collector, format the query, post-process the result, and so on). Customize each application by overriding those hooks, and narrow the runner's loose metadata into your own typed sub-models, so run records are structured and self-describing rather than a loose bag of keys. This is composition-over-inheritance: the reusable runner, the disposable task layer.

Build multi-agent systems by exposing one agent to another **as a tool**: the only sanctioned cross-application dependency. Let an orchestrator spawn its sub-agents (a retriever, a tool-user, a writer) this way. Design the split so it reflects a genuine data dependency between the sub-agents, not an arbitrary partition; a sub-agent boundary that doesn't correspond to a real hand-off just adds latency.

## Dispatch on a discriminator, not a type

Where a component has interchangeable backends (say, several research or model providers), select them through a **polymorphic configuration** rather than conditionals scattered across call sites. Give a base config a `mode` (or `kind`) discriminator, let each concrete variant live in its own module, and dispatch with a `match`/`switch` on that discriminator literal, **never** a runtime type test (an `isinstance()` chain in Python, `instanceof` in TypeScript), which couples the dispatcher to every concrete class and quietly breaks the tier boundaries. Let a settings library resolve environment variables per variant to keep the wiring declarative. Expose one provider-agnostic entry point that returns a uniform result type, so an application swaps a backend by changing a config value, not its own code.

## Name every configuration worth reusing

A **configuration** here is the full bundle of choices that determine how a run behaves: which model it uses, that model's parameters (temperature, top-p, and so on), which tools and features are switched on, and any budgets or limits. A run is pinned by one specific combination of these, and the same combination tends to be wanted again, by the next experiment, by CI, by a teammate reproducing a result.

So any combination worth reusing gets a name. Bundle it into a machine-readable **named profile**, selectable by name (and discoverable by listing). Then have scripts, eval harnesses, and agents reference a configuration *by name* instead of reconstructing a pile of flags at each call site. That is what makes an experiment reproducible (rerun the exact same profile months later) and a "run the cheap profile" instruction unambiguous (see [Part 5](agent-harness.md)).

## Checklist: placing new code / reviewing an import

- [ ] The new code lives in the **most reusable tier that fully contains its concerns**: no lower.
- [ ] Every import points at a more-reusable tier; none points sideways into another application or up toward a task layer.
- [ ] No new import cycle (within or across packages).
- [ ] A single-application convenience stayed *in* that application, not migrated into shared core.
- [ ] Cross-application reuse is via `as_tool()` composition, not internal reach-in.
- [ ] Backend selection dispatches on a discriminator (`match`/`switch`), not a runtime type test (`isinstance`/`instanceof`).
- [ ] The layering rule is enforced by an import-linter contract in CI, not left to prose and memory.
- [ ] Any runtime this change introduces is named in the binding-rules file, with what it buys and who maintains it.

*Next: the same core-versus-task-layer shape, one level down, inside the documents your agents work on. [Part 4. The three-layer document model](three-layer-model.md).*

## See also

- [Part 5. The extended agent harness](agent-harness.md), the shared machinery agents reuse.
- [Part 4. The three-layer document model](three-layer-model.md), the same reusable-core-vs-task-layer idea, one level down.
