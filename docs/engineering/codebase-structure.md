# Part 2 — Codebase Structure

The codebase is organized into strict tiers with acyclic dependencies between them. This is not bureaucratic tidiness — it is the same conviction as the [three-layer document model](three-layer-model.md), applied one level up: **the reusable core is real, and only the task-shaped layer is use-relative.** Lower tiers are the reusable core; agents are the task layer. Keeping the dependencies directional and acyclic is what stops the reusable core from quietly acquiring one agent's assumptions, and it is what lets us pay the "wire this up" integration tax once instead of per agent. This page is the map and the reasoning behind it; the file-by-file index is [`docs/claude-code/key-files.md`](../claude-code/key-files.md), and the binding rules are in [`CLAUDE.md`](../../CLAUDE.md).

## The seven tiers

| Tier | Purpose |
|---|---|
| **`/meta`** | Shared typed schemas (the MCP `_meta` envelope models — `ToolMeta`, `UrlRef`, `ArticleRef`, usage types). Standalone: no internal imports. |
| **`/config`** | Shared configuration: the `ResearchProviderConfig` base, named-profile loading, `agent-configurations.yaml`. |
| **`/core`** | Shared infrastructure: hooks (circuit breaker, URL masking, human input), model catalog, templates, storage, runner, UI/streaming, LLM completion, timeouts. |
| **`/capabilities`** | Cross-agent, opt-in capabilities: `citing/`, `reference_extraction/`, `document_model/`. Consumed by agents that want them. |
| **`/services`** | External-service integrations: `legisratio/`, `winfried/`, `search/`, `extraction/`, `web_research/`, `mock_research/`, `semantic_grep/`, and more. Each with a `client.py` / `mcp.py` / `types.py` / `prompts/` shape. |
| **`/eval`** | The evaluation framework: parsers, analyzers, metrics collection, A/B flow, report generation. |
| **`/agents`** | Agent implementations: `legal_search/`, `web_research/`. The task-shaped layer. |

## The dependency rules (strict, no cycles)

The arrows only ever point toward the reusable core. Verbatim from [`CLAUDE.md`](../../CLAUDE.md):

- **`agents/`** → `capabilities/`, `config/`, `core/`, `services/`, `eval/`, `meta/`, and other `agents/` (sub-agent composition via `as_tool()` only).
- **`capabilities/`** → `services/`, `config/`, `core/`, `meta/`, and lower-layer `capabilities/` (a higher-layer capability may consume a lower one's *schema* as a data contract — e.g. `reference_extraction` → `document_model`).
- **`config/`** → `core/`, `meta/`.
- **`eval/`** → `core/`, `capabilities/`, `meta/`.
- **`services/`** → sibling `services/` (no cycles), `config/` (base classes only), `core/` (shared utilities only), `meta/`.
- **`core/`** → `meta/`, `utils.py` only. Standalone.

No cycles anywhere.

## Why the rules matter

Read the arrows and the reason is visible: a lower tier never depends on the specifics of a higher, task-shaped one. `core/` cannot import from `agents/`; `services/` cannot import an agent's types. This is the architectural enforcement of the same rule the document model states for Layer 2 — *keep the reusable core sparse and stable; keep the task layer rich and disposable.* A convenience that a single agent needs must live in that agent, not migrate down into `core/` or a `service/` where it would bake one workflow's assumptions into shared code and couple every other consumer to them.

The acyclic, directional shape buys three concrete things:

- **Each tier is independently testable.** A `service/` can be exercised without standing up an agent, because it cannot depend on one. The dependency graph *is* the test-isolation boundary.
- **Churn stays local.** Change an agent and nothing below it can break, because nothing below it imports it. Change a `core/` utility and the blast radius is explicit — it is exactly the set of tiers above it, and the compiler/type-checker can enumerate them.
- **The integration tax is paid once.** New agents reuse the harness, the config machinery, the eval framework, and the services as-is (see [Part 3](agent-harness.md)). The marginal agent is mostly its SOP and its tools, not a fresh copy of the plumbing.

An import that would violate a rule is therefore a **design smell, not a lint nuisance.** If an agent-specific concept is pulling toward `core/`, the concept is in the wrong tier, or it is two concepts that need splitting. The rule is doing its job by making that visible at the import line.

## Agent composition: typed hooks over a generic runner

Agents are not forks of a base agent; they are configurations of shared machinery. `core/runner` defines a *generic* `RunMetadata` with loose `parameters: dict` and `stats: dict`. Each agent narrows that into domain-specific typed sub-models — e.g. `ParametersMeta` and `StatsMeta` in `agents/legal_search/types.py` — so its run records are structured and self-describing rather than a loose bag of keys.

Behaviour is customized by subclassing `AgentRunner` and overriding a small set of hook methods in a dedicated `runner.py`: `create_agent`, `create_collector`, `create_run_context`, `format_query`, `post_process`, `result_class`. The runner owns the lifecycle; the agent owns only what is genuinely task-shaped. This is the composition-over-inheritance form of "reusable core, disposable task layer."

Multi-agent systems are built by exposing one agent to another **as a tool**, via `as_tool()` — the only sanctioned cross-agent dependency. The legal-search orchestrator spawns its retriever, web-research, and writer sub-agents this way. The design rationale (and why the pipeline is a genuine sequential data-dependency, not an arbitrary split) is in [multi-agent decomposition](../architecture/multi-agent-decomposition.md).

## Provider polymorphism: dispatch on a discriminator, not a type

Research backends (builtin, mock, deprecated Perplexity) are selected through a polymorphic configuration hierarchy rather than conditionals scattered across call sites. `ResearchProviderConfig` (`config/research.py`) is the base, carrying a `mode: str` discriminator; concrete variants live in their respective service or agent modules. Dispatch is a `match config.mode` on the discriminator literal — **never** an `isinstance()` chain, which would couple the dispatcher to every concrete class and break the tier boundaries. `pydantic-settings` resolves the relevant environment variables automatically per variant.

The provider-agnostic entry point is `capabilities/research.py`'s `run_research()`: any agent calls it and gets back a uniform `ResearchResult` regardless of which backend is active. Swapping `--web-search mock` for `builtin` changes the config variant, not the agent. The full pattern is documented in [research-provider configuration](../architecture/research-provider-config.md) and the config tier in [config architecture](../architecture/config.md).

## Named profiles: configuration as a first-class, named thing

A configuration worth reusing gets a name. [`lidia_agents/config/agent-configurations.yaml`](../../lidia_agents/config/agent-configurations.yaml) holds machine-readable named profiles that bundle a model, its parameters, and feature toggles, selectable with `--profile <name>` (and discoverable with `--list-profiles`). Scripts, eval harnesses, and agents reference a configuration by name instead of reconstructing a pile of flags — which is what makes an experiment reproducible and a "run the cheap profile" instruction unambiguous (see [Part 3](agent-harness.md)).

## See also

- [Part 3 — The extended agent harness](agent-harness.md) — the shared machinery agents reuse.
- [Part 6 — The three-layer document model](three-layer-model.md) — the same reusable-core-vs-task-layer idea, one level down.
- [`docs/architecture/config.md`](../architecture/config.md) · [`docs/architecture/research-provider-config.md`](../architecture/research-provider-config.md) · [`docs/architecture/multi-agent-decomposition.md`](../architecture/multi-agent-decomposition.md)
- [`docs/claude-code/key-files.md`](../claude-code/key-files.md) — the file-by-file map · [`docs/architecture/`](../architecture/) — cross-cutting patterns as implemented.
- [Handbook index](README.md).
