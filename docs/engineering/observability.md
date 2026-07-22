# Part 4 — Observability

You cannot improve what you cannot see, and you cannot decide ([Part 5](evaluation.md)) without numbers you trust. Use observability to stop an agent run being a black box: capture what it fetched, how big it was before and after processing, whether it was actually used, how many tokens and seconds and dollars each (sub-)agent and each tool spent. This page is why to instrument, where the instrumentation goes, and how it closes the loop from production back into development.

## Instrument before you tune

Don't tune knobs before you can see their effect — that is guessing with extra steps. The knobs you worry about are often nearly irrelevant, and the factors that dominate are ones you didn't think to vary; only instrumentation tells them apart. Look *upstream* of the part you were about to optimize, because the highest-leverage intervention frequently sits there: a poorly formed query returns noisier results that waste every later stage, and no amount of pipeline tuning compensates for a bad input. Don't trust averages to show this — a healthy-looking overall number can mask a bimodal split (well-formed inputs doing fine, malformed ones dragging it down), and the win is eliminating the low mode at its source, not nudging the average. So make your first move on any performance question adding the per-item metadata that lets you measure what happens — not a parameter sweep.

## Keep observability out of the model's context

Send analysis metadata through a **side channel the model never sees.** Every extra byte in the prompt costs tokens and risks distracting the model's reasoning, so persist per-item timing, sizes, utilization, and cost *alongside* the run in the artifacts — don't ride them inside the prompt. Apply the same discipline to any bookkeeping a tool must carry but the model shouldn't read: attach it to a metadata envelope the downstream code consumes, not to the tool output the model sees. Observability that changes the thing it observes is not observability.

## Capture per-(sub)agent, per-tool usage

Have the run harness produce a per-(sub)agent and per-tool usage record — tokens (including cache read and write, which are easy to forget), wall-clock timing, agent-loop cycles, and per-tool total time and cost. Give it a *typed* shape (structured metadata sub-models per agent, not a loose dict) so the record is analyzable rather than a bag of stringly-typed keys.

Two things this makes visible that are otherwise invisible:

- **Utilization** — of everything fetched or retrieved, how much actually informed the answer. A pipeline can look busy and productive while most of what it pulls is never used, and only per-item instrumentation surfaces the waste.
- **Where a multi-agent run spends its time** — because timing is per-sub-agent, attribute a slow turn to one stage (the retriever vs a tool-using sub-agent vs the writer) rather than staring at one opaque total. A staged pipeline's wall-clock is often dominated by a single sequential stage, and you cannot know which without the breakdown.

## Account for the full cost, not the convenient part

A quality number without its full cost is not a decision — most model and pipeline choices are quality/cost trade-offs. Avoid two recurring failure modes:

- **Counting only input/output tokens.** On cached-context workloads the cache read and write tokens often dominate the bill and are invisible if you count only the obvious two. Put sub-agent calls, latency, and retries in the total too.
- **Estimating cost from token counts instead of actual billing.** This can flip a conclusion: a filter that looks cheaper because *its own* model is cheap can be more expensive once it inflates the downstream context. Account for the effect a component has on the whole pipeline, not just its local price.

And remember efficiency is necessary but not sufficient: two options can tie on utilization, cost, and latency while differing in the quality of the final answer, and the efficiency numbers are silent about it. A change that delivers the same utilization at lower cost can still ship measurably worse answers. So always pair an efficiency metric with an independent quality evaluation ([Part 5](evaluation.md)). When you communicate the trade-off, lead with absolute figures (a few cents per query) over percentages (69% more) — the absolute number is what hits the budget, and a large percentage on a tiny base often doesn't matter.

## Make errors diagnosable

Observability is not only metrics; it is also what happens when something breaks. Never swallow exceptions (see [Part 1](lifecycle.md)). Report every exception to the downstream consumer with enough detail to diagnose (type + message at minimum), log it at the right level where it is actually visible during debugging, or re-raise it for a better-positioned caller. Aim for a concrete goal: when something fails in production or during an eval run, the error message *alone* should tell you what went wrong — auth? timeout? malformed response? missing resource? — without reproducing the issue or attaching a debugger. A generic "internal error" string is the opposite of observability.

## Close the loop: production → development

Don't confine observability to the dev inner loop; use it to feed production experience back into development. Persist the same per-(sub)agent usage record with each production interaction, so you can triage a real-world session after the fact — reconstruct where a turn spent its time, whether it hung or merely ran long, which tool errored. That feedback loop is what turns a vague "the agent is slow / hanging" report into a specific, fixable root cause: a stage with no timeout, an unbounded resource teardown, a socket with no keep-alive (the reliability defaults in [Part 3](agent-harness.md) are the fixes such investigations produce). Generalize the lesson: **instrumentation that persists into production artifacts is what lets you debug the run you weren't watching.**

## Checklist: instrumenting a run

- [ ] Per-(sub)agent and per-tool usage recorded: tokens (**including cache read/write**), timing, loop cycles, per-tool cost.
- [ ] The usage record is **typed**, not a loose dict.
- [ ] Analysis metadata rides a **side channel**, never inside the prompt or the model-visible tool output.
- [ ] **Utilization** captured (fetched-vs-used), so unused retrieval is visible.
- [ ] Cost taken from **actual billing**, whole-pipeline effect included — not estimated from local token counts.
- [ ] Every efficiency number paired with an independent **quality** number.
- [ ] Exceptions reported/logged/re-raised so the message alone diagnoses the failure — none swallowed.
- [ ] The same usage record persists into **production** artifacts, not just dev runs.

## See also

- [Part 1 — Lifecycle](lifecycle.md) — no swallowed exceptions, as a review rule.
- [Part 3 — Agent harness](agent-harness.md) — bounded external calls, the reliability half of the loop.
- [Part 5 — Evaluation](evaluation.md) — pairing efficiency with an independent quality metric.
- [Handbook index](README.md).
