# Part 3. The Extended Agent Harness

Don't make a new agent re-solve model selection, configuration, headless execution, or reliability. Those are the same problem every time, so solve them once, in the shared core and configuration tiers, and let each agent author spend their attention on the task-shaped logic that is actually new. Aim for a harness that makes agents **cheap to build, cheap to swap models under, cheap to run headless, and reproducible**. This page lists the capabilities such a harness provides and why each earns its place; the tier boundaries they live in are in [Part 2](codebase-structure.md), and the reason reproducibility matters so much is in [Part 5](evaluation.md).

## Build the harness, don't inline the plumbing

The temptation with a new agent is to wire a model client, a config object, and an entry point directly into the agent module, it feels faster. It is faster once. The second agent pays the tax again, the third diverges subtly from the first two, and now "swap the model" or "run this headless for an eval" means editing three places that drift apart. So instrument and configure once, reuse across every agent, and let the marginal agent be mostly its prompt and its tools.

Put the production-reliability decisions in the harness too, so no agent has to remember them. An unbounded call to a model or an external tool is a production hang waiting to happen; make *bounding* the default, not an afterthought each author reinvents.

## Resolve models through aliases, never hard-coded IDs

Never name a concrete provider model inline. Take a short **alias** and resolve it through a central catalog. Encode the provider in the alias's prefix (a `bedrock-…` alias, an `openrouter-…` alias, and so on), so the same call site works across providers and switching the model a run uses is a one-token change, not a code change.

This indirection is what makes model screening (see [Part 5](evaluation.md)) practical: point the same agent at a dozen candidate models by varying a flag, never touching the agent. Keep the catalog the single place that knows real model IDs, regions, and credentials, so provider churn is contained to one file.

## Expose model parameters as optional, defaulted flags

Make generation parameters (temperature, top-p, penalties) optional flags with provider defaults when omitted, so the common case stays terse and the tuning case stays possible. For models that support it, expose reasoning/extended-thinking as a budget flag. Decide whether any such parameter change is actually an improvement the same way as everything else: treat it as a hypothesis, measure it against a frozen benchmark, one variable at a time (see [Part 5](evaluation.md)).

## Bundle configuration into named profiles

A bare pile of flags is not reproducible, the next person has to know which twelve you passed. Have the config tier bundle a model, its parameters, and feature toggles into a **named profile** selectable by name and discoverable by listing. Keep profiles machine-readable, so scripts and eval harnesses reference a configuration by name rather than reconstructing it, and "run the cheap profile" becomes a shared, unambiguous instruction. The polymorphic configuration machinery underneath profiles is covered in [Part 2](codebase-structure.md).

## Ship every agent with a headless CLI

Give every agent a headless command-line entry point that takes a query and writes its artifacts to an output directory, with no UI in the loop:

```
agent-run --query "<question>" --output-dir runs/2026-05-05-<agent>-<model>-q0/
```

This is not a convenience, it is the load-bearing design decision that makes evaluation possible. **Make the entry point a human uses the same one an eval harness drives as a subprocess.** Because the CLI is headless and artifact-producing, an A/B runner or a screening funnel can spawn agent runs by the dozen, capture every output, and score them, without any special "eval mode" that might diverge from what production does. Keep no separate code path to hold honest.

Keep a machine's worth of runs navigable months later with two conventions: land artifacts in a **dated subfolder** (never at a directory root), and encode what produced the run in the folder name (date, agent, model, query). When you want an interactive streaming UI, build it as the human-facing *peer* of this CLI (the same agent underneath, a different surface) rather than as a separate implementation.

## Offer cheap and mock backends: a fast inner loop is a discipline

Iterating against a frozen benchmark means running the agent many times, and the expensive part of a run is usually a live external API (search, retrieval, a large model). So offer cheaper backends, selected by flag, that keep the loop fast without changing the agent, for example a **mock backend** (a small model over a fixed knowledge base) that stands in for the live service at a fraction of the cost, or a lighter real backend for the same capability.

Treat a cheap inner loop as a first-class capability, not just a cost saving: it is what lets you re-measure against the same benchmark ten times in an afternoon instead of once a day, the difference between a decision backed by a variance band and one backed by an anecdote (see [Part 5](evaluation.md)). Account for the *full* cost when you compare backends, though, a stand-in that inflates the downstream context is not as cheap as its own token count suggests (see [Part 4](observability.md)).

## Make bounding the default

Bake the production-reliability defaults into the harness so no agent author has to rediscover them under an incident:

- **Set wall-clock and idle timeouts** on agent turns and streaming loops, so a stalled or slowly-dribbling response can no longer hang a run past a usable window with nothing to rescue it.
- **Harden the outbound HTTP client**: explicit connect and read timeouts, bounded retries, TCP keep-alive, so a dropped socket surfaces as an error instead of an indefinite wait.
- **Time-bound teardown** of external resources (browsers, sessions, worker threads), so a wedged close cannot hang the run or leak a billed resource.

Carry this principle into any new external integration: an unbounded external call is a latent production hang. Bound it at the harness level, and the failure becomes a clean, diagnosable error instead of a silent stall, which is also what makes the production feedback loop in [Part 4](observability.md) possible.

## Checklist: standing up a new agent

- [ ] Agent takes a model **alias**, resolved through the central catalog, no inline model IDs.
- [ ] Generation parameters are optional flags with provider defaults.
- [ ] A named **profile** captures the intended model + params + toggles, discoverable by listing.
- [ ] A **headless CLI** entry point exists; it is the same path the eval harness drives.
- [ ] Artifacts land in a **dated, self-describing subfolder**, never at a root.
- [ ] A **cheap/mock backend** is selectable by flag for the inner loop.
- [ ] External calls are **bounded** (turn/idle timeouts, hardened HTTP client, time-bounded teardown) via the harness, not per-agent.

## See also

- [Part 2. Codebase structure](codebase-structure.md), the tier boundaries the harness lives in, and the configuration polymorphism under named profiles.
- [Part 4. Observability](observability.md), the per-(sub)agent metrics the harness emits, and full-cost accounting.
- [Part 5. Evaluation](evaluation.md), why headless, reproducible, cheap-to-run agents are the precondition for deciding with evidence.
- [Handbook index](README.md).
