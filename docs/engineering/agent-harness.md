# Part 3 — The Extended Agent Harness

A new agent should not have to re-solve model selection, configuration, headless execution, or reliability. Those are the same problem every time, so we solve them once — in the shared core and configuration tiers — and let each agent author spend their attention on the task-shaped logic that is actually new. The result is a harness that makes agents **cheap to build, cheap to swap models under, cheap to run headless, and reproducible**. This page describes the capabilities such a harness provides and why each one earns its place; the tier boundaries they live in are in [Part 2](codebase-structure.md), and the reason reproducibility matters so much is in [Part 5](evaluation.md).

## Why a harness at all

The temptation with a new agent is to wire a model client, a config object, and an entry point directly into the agent module — it feels faster. It is faster once. The second agent pays the tax again, the third diverges subtly from the first two, and now "swap the model" or "run this headless for an eval" means editing three places that drift apart. Instrument and configure once, reuse across every agent, and the marginal agent becomes mostly its prompt and its tools.

The harness is also where production-reliability decisions live, so that no agent has to remember them. An unbounded call to a model or an external tool is a production hang waiting to happen; the harness makes *bounding* the default, not an afterthought each author reinvents.

## Model access: aliases over hard-coded IDs

Agents should never name a concrete provider model inline. They take a short **alias** and resolve it through a central catalog. The alias's prefix encodes the provider (a `bedrock-…` alias, an `openrouter-…` alias, and so on), so the same call site works across providers and switching the model a run uses is a one-token change, not a code change.

This indirection is what makes model screening (see [Part 5](evaluation.md)) practical: you can point the same agent at a dozen candidate models by varying a flag, never touching the agent. Keep the catalog the single place that knows real model IDs, regions, and credentials, so provider churn is contained to one file.

## Model parameters and reasoning mode

Generation parameters (temperature, top-p, penalties) are optional flags with provider defaults when omitted, so the common case stays terse and the tuning case stays possible. For models that support it, reasoning/extended-thinking is exposed as a budget flag. Whether any such parameter change is actually an improvement is decided the same way as everything else: it is a hypothesis, measured against a frozen benchmark, one variable at a time (see [Part 5](evaluation.md)).

## Configuration and named profiles

A bare pile of flags is not reproducible — the next person has to know which twelve you passed. The config tier bundles a model, its parameters, and feature toggles into a **named profile** selectable by name and discoverable by listing. Profiles are machine-readable, so scripts and eval harnesses reference a configuration by name rather than reconstructing it, and "run the cheap profile" becomes a shared, unambiguous instruction. The polymorphic configuration machinery underneath profiles is covered in [Part 2](codebase-structure.md).

## CLI-first: every agent runs headless

Every agent ships a headless command-line entry point that takes a query and writes its artifacts to an output directory, with no UI in the loop:

```
agent-run --query "<question>" --output-dir runs/2026-05-05-<agent>-<model>-q0/
```

This is not a convenience — it is the load-bearing design decision that makes evaluation possible. **The entry point a human uses is the same one an eval harness drives as a subprocess.** Because the CLI is headless and artifact-producing, an A/B runner or a screening funnel can spawn agent runs by the dozen, capture every output, and score them, without any special "eval mode" that might diverge from what production does. There is no separate code path to keep honest.

Two conventions keep a machine's worth of runs navigable months later: artifacts land in a **dated subfolder** (never at a directory root), and the folder name encodes what produced it (date, agent, model, query). An interactive streaming UI, when you want one, is best built as the human-facing *peer* of this CLI — the same agent underneath, a different surface — rather than as a separate implementation.

## Cheap and mock backends: a fast inner loop is a discipline

Iterating against a frozen benchmark means running the agent many times, and the expensive part of a run is usually a live external API (search, retrieval, a large model). So the harness offers cheaper backends, selected by flag, that keep the loop fast without changing the agent — for example a **mock backend** (a small model over a fixed knowledge base) that stands in for the live service at a fraction of the cost, or a lighter real backend for the same capability.

Treating a cheap inner loop as a first-class capability is a development discipline, not just a cost saving: it is what lets you re-measure against the same benchmark ten times in an afternoon instead of once a day, which is the difference between a decision backed by a variance band and one backed by an anecdote (see [Part 5](evaluation.md)). Account for the *full* cost when you compare backends, though — a stand-in that inflates the downstream context is not as cheap as its own token count suggests (see [Part 4](observability.md)).

## Bounding is the default

The harness bakes in production-reliability defaults so no agent author has to rediscover them under an incident:

- **Wall-clock and idle timeouts** on agent turns and streaming loops, so a stalled or slowly-dribbling response can no longer hang a run past a usable window with nothing to rescue it.
- **A hardened outbound HTTP client** — explicit connect and read timeouts, bounded retries, TCP keep-alive — so a dropped socket surfaces as an error instead of an indefinite wait.
- **Time-bounded teardown** of external resources (browsers, sessions, worker threads), so a wedged close cannot hang the run or leak a billed resource.

The principle to carry into any new external integration: an unbounded external call is a latent production hang. Bound it at the harness level, and the failure becomes a clean, diagnosable error instead of a silent stall — which is also what makes the production feedback loop in [Part 4](observability.md) possible.

## See also

- [Part 2 — Codebase structure](codebase-structure.md) — the tier boundaries the harness lives in, and the configuration polymorphism under named profiles.
- [Part 4 — Observability](observability.md) — the per-(sub)agent metrics the harness emits, and full-cost accounting.
- [Part 5 — Evaluation](evaluation.md) — why headless, reproducible, cheap-to-run agents are the precondition for deciding with evidence.
- [Handbook index](README.md).
