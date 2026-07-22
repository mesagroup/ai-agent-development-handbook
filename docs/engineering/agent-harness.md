# Part 3 — The Extended Agent Harness

A new agent should not have to re-solve model selection, configuration, headless execution, or reproducibility. Those are the same problem every time, so we solve them once — in the `core/` and `config/` tiers — and let each agent author spend their attention on the task-shaped logic that is actually new. The result is a harness that makes agents **cheap to build, cheap to swap models under, cheap to run headless, and reproducible**. This page is the tour of that harness; the tier boundaries it lives in are in [Part 2](codebase-structure.md), and the reason reproducibility matters so much is in [Part 5](evaluation.md).

## Why a harness at all

The temptation with a new agent is to wire a model client, a config object, and an entry point directly into the agent module — it feels faster. It is faster once. The second agent pays the tax again, the third diverges subtly from the first two, and now "swap the model" or "run this headless for an eval" means editing three places that drift apart. Instrument and configure once, reuse across every agent, and the marginal agent becomes mostly its SOP and its tools.

The harness is also where production-reliability decisions live, so that no agent has to remember them. An unbounded call to a model or a browser is a production hang waiting to happen; the harness makes *bounding* the default, not an afterthought each author reinvents.

## Model catalog: aliases over hard-coded model IDs

Agents never name a concrete provider model. They take a short **alias** and resolve it through the model catalog (`lidia_agents/core/models/`). The alias's prefix encodes the provider:

| Prefix | Provider |
|---|---|
| `br-` | Bedrock |
| `mt-` | Mantle |
| `or-` | OpenRouter |
| `fw-` | Fastweb |
| `ds-` | DashScope (Alibaba Cloud Qwen, OpenAI-compatible) |

So `-m br-sonnet46` and `-m or-minimax-m27` are interchangeable at the call site: switching the model a screening run uses, or the model a sub-agent uses, is a flag change, not a code change. This is what makes the model-screening funnel (see [Part 5](evaluation.md)) practical — you can point the same agent at a dozen candidate models without touching the agent. The catalog is documented in [`docs/architecture/core/models.md`](../architecture/core/models.md).

## Model parameters and extended thinking

Generation parameters are optional flags with provider defaults when omitted, so the common case stays terse and the tuning case stays possible:

```bash
uv run python -m lidia_agents.agents.legal_search.cli --query 0 --temperature 0.3 --top-p 0.9
uv run python -m lidia_agents.agents.legal_search.cli --query 0 --frequency-penalty 0.3 --presence-penalty 0.6
```

For models that support it, reasoning mode is a budget flag:

```bash
uv run python -m lidia_agents.agents.legal_search.cli --query 0 -m br-sonnet46 --thinking-budget 10000
```

Extended thinking — which models support it, the CLI usage, and the mechanism — is documented in [`docs/claude-code/extended-thinking.md`](../claude-code/extended-thinking.md). The discipline that governs *whether* a parameter change is actually an improvement is the same as everywhere else: it is a hypothesis, measured against a frozen benchmark, one variable at a time (see [Part 5](evaluation.md)).

## Configuration and named profiles

A bare pile of flags is not reproducible — the next person has to know which twelve you passed. The config tier bundles a model, its parameters, and feature toggles into a **named profile** that can be selected by name:

```bash
uv run python -m lidia_agents.agents.web_research.cli --query 0 --profile web-research-cheap
uv run python -m lidia_agents.agents.web_research.cli --list-profiles
```

Profiles are declared in [`lidia_agents/config/agent-configurations.yaml`](../../lidia_agents/config/agent-configurations.yaml) and are machine-readable, so scripts and eval harnesses can reference a configuration by name rather than reconstructing it. "Run the cheap profile" is now a shared, unambiguous instruction. The polymorphic configuration machinery underneath profiles — the `ResearchProviderConfig` hierarchy, discriminator-based dispatch, and `pydantic-settings` env resolution — is covered in [Part 2](codebase-structure.md) and [`docs/architecture/config.md`](../architecture/config.md).

## CLI-first: every agent runs headless

Every agent ships a headless CLI that takes a query and writes its artifacts to an output directory, with no UI in the loop:

```bash
uv run python -m lidia_agents.agents.legal_search.cli --query 0 --output-dir cli-output/20260505-legal-search-br-sonnet46-q0
uv run python -m lidia_agents.agents.web_research.cli  --query 0 --output-dir cli-output/20260505-web-research-or-minimax-m27-q0
```

This is not a convenience — it is the load-bearing design decision that makes evaluation possible. **The entry point a human uses is the same one an eval harness drives as a subprocess.** Because the CLI is headless and artifact-producing, the A/B runner and the screening funnel can spawn agent runs by the dozen, capture every output, and score them, without any special "eval mode" that might diverge from what production does. There is no separate code path to keep honest.

Artifacts land in a **dated subfolder**, never at a directory root, by convention:

- Ad-hoc CLI runs: `cli-output/YYYYMMDD-{agent}-{model}-q{N}/`
- Eval runs: `test-reports/YYYYMMDD-{type}-q{N}/`

Both directories are gitignored. The dated-subfolder rule is what keeps a machine's worth of runs navigable months later.

For interactive use, the Gradio app (`uv run python -m lidia_agents.agents.legal_search.gradio_app`) is the real-time-streaming peer of the CLI — the same agent, a human-facing surface instead of a headless one. Configuration flags are documented per agent, e.g. [`docs/agents/legal-search/configuration.md`](../agents/legal-search/configuration.md).

## Cheap and mock backends: a fast inner loop is a discipline

Iterating against a frozen benchmark means running the agent many times, and the expensive part of a legal-search or web-research run is the live research API. So the harness offers cheaper backends, selected by flag, that keep the loop fast without changing the agent:

- `--web-search mock` — a Haiku + knowledge-base mock (~99% cheaper than the live API), documented in [`docs/services/mock-research.md`](../services/mock-research.md). This is the default for eval scripts and the smoke test.
- `--web-search builtin` — Serper + trafilatura extraction, no Perplexity API needed.
- `--web-search off` — LegisRatio only.

Treating a cheap inner loop as a first-class capability is a development discipline, not just a cost saving: it is what lets you re-measure against the same benchmark ten times in an afternoon instead of once a day, which is the difference between a decision backed by a variance band and one backed by an anecdote (see [Part 5](evaluation.md)). Account for the *full* cost when you compare backends, though — a mock that inflates downstream context is not as cheap as its own token count suggests (see [Part 4](observability.md)).

## Timeouts and socket hardening: bounding is the default

The harness bakes in the production-reliability lessons from the browser-teardown hang investigation (#475), so no agent author has to rediscover them:

- **Wall-clock and idle timeouts** on agent turns and stream loops, via `run_with_timeout()` in `lidia_agents/core/timeouts.py`, resolved per call from `LIDIA_AGENT_IDLE_TIMEOUT` and `LIDIA_AGENT_WALL_CLOCK_TIMEOUT`. A stalled or slowly-dribbling stream can no longer hang a run past a usable window with nothing to rescue it.
- **A hardened Bedrock client** — read and connect timeouts, bounded retries, and `tcp_keepalive` — so a dropped socket surfaces as an error instead of an indefinite wait.
- **Time-bounded browser / AgentCore teardown**, so a wedged close cannot hang the run or leak a billed browser session.

The mechanism is documented in [`docs/architecture/core/timeouts.md`](../architecture/core/timeouts.md); the full root-cause and cross-repo fix story is in [`docs/research/2026-07-16-legal-search-prod-hangs-slowdowns.md`](../research/2026-07-16-legal-search-prod-hangs-slowdowns.md). The principle to carry into any new external integration: an unbounded external call is a latent production hang. Bound it at the harness level, and the failure becomes a clean, diagnosable error instead of a silent stall.

## See also

- [Part 2 — Codebase structure](codebase-structure.md) — the tier boundaries the harness lives in, and the configuration polymorphism under named profiles.
- [Part 4 — Observability](observability.md) — the per-(sub)agent metrics the harness emits, and full-cost accounting.
- [Part 5 — Evaluation](evaluation.md) — why headless, reproducible, cheap-to-run agents are the precondition for deciding with evidence.
- [`docs/architecture/core/models.md`](../architecture/core/models.md), [`docs/architecture/config.md`](../architecture/config.md), [`docs/architecture/core/timeouts.md`](../architecture/core/timeouts.md) — the underlying references.
- [Handbook index](README.md).
