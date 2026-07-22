# Part 4 — Observability

You cannot improve what you cannot see, and you cannot decide ([Part 5](evaluation.md)) without numbers you trust. Observability is how an agent run stops being a black box: what it fetched, how big it was before and after processing, whether it was actually used, how many tokens and seconds and dollars each (sub-)agent and each tool spent. This page is why we instrument, where the instrumentation goes, and how it closes the loop from production back into R&D.

## Why: instrument before you tune

Tuning knobs before you can see their effect is guessing with extra steps. The knobs you worry about are often nearly irrelevant, and the factors that dominate are ones you didn't think to vary — only instrumentation tells them apart. The highest-leverage intervention frequently sits *upstream* of the part you were about to optimize: a poorly formed query returns noisier results that waste every later stage, and no amount of pipeline tuning compensates for a bad input. Averages hide this — a healthy-looking overall number can mask a bimodal split (well-formed inputs doing fine, malformed ones dragging it down), and the win is eliminating the low mode at its source, not nudging the average. So the first move on any performance question is not a parameter sweep; it is adding the per-item metadata that lets you measure what happens instead of arguing about it.

## The rule: keep observability out of the model's context

Analysis metadata travels in a **side channel the model never sees.** Every extra byte in the prompt costs tokens and risks distracting the model's reasoning, so per-item timing, sizes, utilization, and cost ride *alongside* the run and persist in the artifacts — they do not ride inside the prompt. This is the same discipline as the [reference-metadata side-channel](../architecture/reference-metadata-sidecar.md), where citation references reach the hooks but not the model; the general pattern is written up in [tool side-channels](../research/tool-side-channels.md). Observability that changes the thing it observes is not observability.

## What we capture

The runner tier produces a per-run usage record with per-(sub)agent and per-tool granularity — tokens (including cache read/write), wall-clock timing, agent-loop cycles, and per-tool total time and cost. The design is documented in the [runner architecture](../architecture/core/runner.md); it was built as a dedicated piece of work (the runner-observability spec under `docs/superpowers/specs/2026-05-12-runner-observability-design.md`). Each agent defines typed metadata sub-models (a `StatsMeta`, a `ParametersMeta`) so the record is structured, not a loose dict — see [Part 2](codebase-structure.md) on the agent composition pattern.

Two things this makes visible that are otherwise invisible:

- **Utilization** — of everything fetched or retrieved, how much actually informed the answer. A pipeline can look busy and productive while most of what it pulls is never used. The [content-utilization analysis](../stories/2026-05-04-content-utilization-analysis.md) is the worked example of instrumenting this and acting on it.
- **Where a multi-agent run spends its time** — because timing is per-sub-agent, you can attribute a slow turn to the retriever vs the web sub-agent vs the writer, rather than staring at one opaque total. This is exactly what let us diagnose the legal-search latency question: the wall-clock was dominated by the sequential retrieve → web → write stages, not by any single tool.

## Account for the full cost, not the convenient part

A quality number without its full cost is not a decision — most model and pipeline choices are quality/cost trade-offs. Two failure modes recur:

- **Counting only input/output tokens.** On cached-context workloads the cache read and write tokens often dominate the bill and are invisible if you count only the obvious two. Sub-agent calls, latency, and retries all belong in the total.
- **Estimating cost from token counts instead of actual billing.** This can flip a conclusion: a filter that looks cheaper because *its own* model is cheap can be more expensive once it inflates the downstream context. Account for the effect a component has on the whole pipeline, not just its local price.

And efficiency is necessary but not sufficient: two options can tie on utilization, cost, and latency while differing in the quality of the final answer, and the efficiency numbers are silent about it. A change that delivers the same utilization at lower cost can still ship measurably worse answers. Always pair an efficiency metric with an independent quality evaluation ([Part 5](evaluation.md)). When you communicate the trade-off, lead with absolute figures (a few cents per query) over percentages (69% more) — the absolute number is what hits the budget, and a large percentage on a tiny base often doesn't matter.

## The developer-facing half: errors must be diagnosable

Observability is not only metrics; it is also what happens when something breaks. The coding rule ([`CLAUDE.md`](../../CLAUDE.md), and [Part 1](lifecycle.md)) is that we never swallow exceptions. Every exception is reported to the downstream consumer with enough detail to diagnose (type + message at minimum), logged at the right level where it is actually visible during debugging, or re-raised for a better-positioned caller. The goal is concrete: when something fails in production or during an eval run, the error message *alone* should tell you what went wrong — auth? timeout? malformed response? missing resource? — without reproducing the issue or attaching a debugger. A generic "Internal error" string is the opposite of observability.

## Closing the loop: production → R&D

Observability is not just for the dev inner loop; it is how production experience feeds back into R&D. The same per-(sub)agent usage record is persisted per production message, so a real-world conversation can be triaged after the fact — reconstruct where a turn spent its time, whether it hung or merely ran long, which tool errored. That feedback loop is what turned a set of "the agent is slow / hanging" production reports into a specific, fixable root cause: bounded browser teardown, wall-clock and idle timeouts, and a hardened Bedrock socket ([Part 3](agent-harness.md)). The full investigation and cross-repo handoff is in [legal-search prod hangs & slowdowns](../research/2026-07-16-legal-search-prod-hangs-slowdowns.md). The lesson worth generalizing: instrumentation that persists into production artifacts is what lets you debug the run you weren't watching.

## See also

- [Runner architecture](../architecture/core/runner.md) — the usage/metrics record
- [Reference-metadata side-channel](../architecture/reference-metadata-sidecar.md) · [tool side-channels](../research/tool-side-channels.md) — observability out of the model's context
- [Content-utilization analysis](../stories/2026-05-04-content-utilization-analysis.md) — instrumenting utilization
- [Legal-search prod hangs & slowdowns](../research/2026-07-16-legal-search-prod-hangs-slowdowns.md) — the production feedback loop in action
- Handbook: [Part 3 — Agent harness](agent-harness.md) · [Part 5 — Evaluation](evaluation.md)
