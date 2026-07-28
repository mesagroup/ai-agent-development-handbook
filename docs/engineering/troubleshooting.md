# Troubleshooting: From Symptom to Section

*The nine parts teach the disciplines in the order you would learn them. This page is the other entry point, for the day you arrive with a problem instead of a curriculum: an agent that burns money, stalls, or lies, and no obvious owner among the disciplines. Find your symptom, read the short diagnosis, follow the route.*

Every entry has the same shape: the symptom as a developer says it, a few sentences of differential diagnosis that tell the plausible root causes apart, and one route per cause into the part that carries the fix. Two habits make the page work. Expect several distinct root causes behind one symptom, and read the diagnosis to tell them apart rather than to confirm the first suspicion. And make the first move instrumentation, not tuning: most entries begin by pointing at a record to read before anything gets changed ([Part 6](observability.md)).

## Cost and latency

### My agent burns dollars of tokens per run and I can't see where

The complaint is usually two complaints: a bill you dislike, and a bill you cannot attribute. Before changing anything, pull the usage record for one expensive run and read it per (sub)agent and per tool (the per-(sub)agent, per-tool capture in [Part 6](observability.md)); a total you cannot decompose is a visibility problem before it is a cost problem. Then ask what the total actually counts: on cached-context workloads the cache read and write tokens routinely dominate, and a bill assembled from input and output alone will look mysteriously smaller than the invoice. If the accounting is honest and the number is still ugly, ask how much of what the run fetched ever reached the answer, because a pipeline can look busy while most of its retrieval goes unread. Two familiar variants hide inside this symptom: cheap in development and ruinous in production is usually the same cache blind spot seen from the other end, and a system prompt edited every few days invalidates the prefix cache on every run, so each iteration pays full price for context that was supposed to be nearly free.

- No per-stage instrumentation at all: capture per-(sub)agent, per-tool usage, typed and on a side channel ([Part 6](observability.md)).
- A total that counts only input and output tokens: account for the full cost, not the convenient part ([Part 6](observability.md)).
- Low utilization, where most of what is fetched never informs the answer: the utilization metric that per-(sub)agent, per-tool capture makes visible ([Part 6](observability.md)).
- Iterating against live, expensive backends: offer cheap and mock backends for the inner loop ([Part 5](agent-harness.md)).

### The app is unbearably slow

Slow is a total, and a total says nothing about which stage owns it. Resist the config file: the first move is per-stage timing, not a parameter sweep, because the knobs you suspect are rarely the ones that dominate (instrument before you tune, [Part 6](observability.md)). With the breakdown in hand the answer is usually blunt: a staged multi-agent run is often dominated by one sequential stage, and tuning anywhere else moves nothing. Look upstream of that stage before optimizing it, since a poorly formed query returns noisier results that waste every stage after it. If the breakdown is flat and everything is merely slow, the variable to change is the model or the number of retriever cycles, not the pipeline. And read the tail, not the average: an unbounded wait leaves the median untouched and turns the occasional run into an hour.

- One dominant sequential stage in a multi-agent pipeline: where a multi-agent run spends its time, under per-(sub)agent, per-tool capture ([Part 6](observability.md)).
- A poorly formed upstream input poisoning every later stage: instrument before you tune, and look upstream of what you meant to optimize ([Part 6](observability.md)).
- A slow model, or too many retriever cycles: pick the approach that fits the decision, then build escalation ladders so the expensive path runs only on the residual ([Part 7](evaluation.md)).
- Unbounded waits inflating the tail: make bounding the default ([Part 5](agent-harness.md)).

## Reliability

### It hangs while calling tools

Silence is not one failure; it is three. Before touching code, pull the persisted usage record for the stuck run and see where the clock went (the production feedback loop in [Part 6](observability.md)): a stage that never returned points at a missing timeout; a stage that returned instantly with nothing points at a swallowed error. The classic causes: an outbound call with no connect or read timeout waiting on a dropped socket; an exception raised inside an async event handler that nothing awaits, so the failure evaporates and the loop waits on a result that will never come; a resource teardown (a browser, a session) wedged on close. A tool that silently yields an empty answer instead of hanging is the second cause wearing a different face.

- No timeouts anywhere: make bounding the default, wall-clock, idle, connect, and read ([Part 5](agent-harness.md)).
- Errors that vanish instead of surfacing: the no-swallowed-exceptions rule ([Part 2](implementation-disciplines.md)) and making errors diagnosable ([Part 6](observability.md)).
- A wedged teardown of external resources: time-bound teardown ([Part 5](agent-harness.md)).

### External calls fail intermittently

Unlike the hang above, this failure announces itself: you get errors, sporadically, on calls that succeed the rest of the time. That pattern is the signature of a dependency that is flaky rather than broken, and the harness, not the agent, is where it should be absorbed. Check first whether the outbound path retries at all: a single attempt against a service with a small but real error rate makes every run a coin toss, and bounded retries with backoff turn most of those failures into a slightly slower success. Then check the blast radius, because without a circuit breaker one degraded dependency keeps being called by every run, and a partial outage becomes a fleet-wide slowdown. Finally, make sure the retries are visible: a retry that eventually succeeds still spends tokens, seconds, and money, and a cost or latency figure that omits it will quietly mislead the next comparison you run.

- No bounded retries with backoff on the outbound path: make bounding the default, via the hardened HTTP client ([Part 5](agent-harness.md)).
- No circuit breaker, so one degraded dependency poisons every run: build the harness, don't inline the plumbing ([Part 5](agent-harness.md)).
- Retries that happen but never reach the numbers: account for the full cost, not the convenient part ([Part 6](observability.md)).

### It loops without progress

The run is alive, spending, and getting nowhere: the same tool called with near-identical arguments, the cycle count climbing, the answer no closer. Read the tool-call sequence and the agent-loop cycle counts in the usage record first (the per-(sub)agent, per-tool capture in [Part 6](observability.md)); the shape of the repetition names the cause. A loop that would run forever if you let it is a missing bound, and bounds belong in the harness rather than in the model's good intentions. A loop that does stop, but late, usually means the procedure never said what done looks like, so the agent keeps polishing an answer that was finished several cycles ago. A loop that reissues the same call because the result was unusable is not a looping problem at all; see the tool-misuse entry below. And when the bounds exist, the stop condition is explicit, and the tools return clean output, what remains is a model that cannot plan its way through the task, which is a model-choice question settled by measurement rather than by prompt patches.

- No cycle or budget bound in the harness: make bounding the default ([Part 5](agent-harness.md)).
- An SOP with no stop condition or completion criterion: prompt and SOP engineering ([Part 2](implementation-disciplines.md)).
- A tool returning output the agent cannot use, so it retries blindly: the tool-misuse entry below.
- A model too weak to plan its way through the task: pick the approach that fits the decision, and settle the swap with a staged evaluation funnel ([Part 7](evaluation.md)).

*Whatever brought you here, the durable fix ends the same way every change does: encode the standard as an executable check so the symptom cannot return unannounced ([Part 1](lifecycle.md)). The full story starts at the [beginning](README.md).*
