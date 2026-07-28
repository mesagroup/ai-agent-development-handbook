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

## Output quality

### It fails with out-of-context errors

The window did not get smaller, so ask what grew. Before raising any limit, read one failing run's context by origin: the question is which producer put the bytes there, and the answer is rarely the user's query. The first suspect is bookkeeping, timing, sizes, provenance, analysis metadata, riding inside the prompt instead of on a side channel the model never sees. The second is a tool that hands back whatever the upstream service gave it, because nothing in the harness ever decided what a too-large result should become. The third is quieter and more expensive: the run fetches far more than it uses, and the fix is less retrieval rather than a bigger window, which only per-item instrumentation will show you.

- Bookkeeping and analysis metadata riding inside the prompt: keep observability out of the model's context ([Part 6](observability.md)).
- Tool output with no truncation or summarization strategy: make bounding the default, the harness rule that an unbounded thing is a latent failure, applied to size as well as to time ([Part 5](agent-harness.md)).
- Over-fetching that instrumentation would show as unused: the utilization metric that per-(sub)agent, per-tool capture makes visible ([Part 6](observability.md)).

### It hallucinates

One word, three different failures, and the fix for each lives somewhere else entirely. Establish first whether the claim is invented or merely mangled, by checking whether it traces to anything the run actually fetched. If it traces to nothing, this is ungrounded generation out of the model's weights, and the answer is an eval dimension that scores groundedness plus an SOP that binds the answer to its sources rather than a prompt that asks nicely. If it traces to a real document but the wording is wrong, do not blame the model yet: diff the Layer 1 representation against the source page, because an ingestion or OCR error is reproduced faithfully by a model that is behaving perfectly. If Layer 1 is clean, reproduce the same question with that passage alone in the context; a clean quote in isolation means the context was diluted, not that extraction failed. That isolation reproduction is the whole pivot between the two: it separates a pipeline defect you fix upstream from an attention problem you fix by putting less in the window. Citations that point at real sources which do not support the claim are the first case wearing a bibliography, and the same groundedness measurement catches them.

- Claims that trace to no fetched source: measure the behaviors that matter, with groundedness among them ([Part 7](evaluation.md)), and an SOP whose constraints bind the answer to its sources ([Part 2](implementation-disciplines.md)).
- Misquotation introduced upstream by the extraction pipeline: the engine-agnostic Layer 1 contract ([Part 4](three-layer-model.md)), scored on its own against a frozen golden set ([Part 7](evaluation.md), on building a dataset you can trust).
- Misquotation from a context too full to attend to: utilization, which shows how much of what you loaded was ever used ([Part 6](observability.md)), and bounding what enters the context in the first place ([Part 5](agent-harness.md)).

### It reasons wrongly from correct facts

Unlike the entry above, nothing here is invented or mangled: every fact checks out and the conclusion still does not follow. That narrows it to two places, and neither of them is retrieval. Either the model cannot carry the inference the task demands, which is a model-choice question and therefore a measurement question rather than something a sharper prompt will patch; or the procedure asks for a leap where it should ask for steps, handing the model one move to make when the reasoning has three. Tell them apart cheaply: decompose the step in the SOP and re-run the same case, then run the same case unchanged against a stronger model. Whichever intervention moves the answer names the cause, and if it is the model, the swap is settled by measurement rather than by the impression the demo left.

- A model too weak to carry the inference: pick the approach that fits the decision, rank the candidates with a staged evaluation funnel, and build an escalation ladder so the expensive model runs only on the residual ([Part 7](evaluation.md)).
- An SOP that asks for a leap where it should ask for ordered steps: prompt and SOP engineering ([Part 2](implementation-disciplines.md)).

### It ignores its SOP

An agent that ignores a rule is usually not disobeying it; it is failing to weigh it against forty others. Count the constraints before rewriting any of them, because density is the measurement here, and a prompt that overloads the model degrades exactly the reasoning you were asking it for. Then sort the rules by kind. Anything a machine could enforce, a schema on the output, a validator in the tool, a guard in the pipeline, does not belong in the SOP at all, and moving it out buys attention for the rules that genuinely need judgment. What is left may still contradict itself, and a model handed two rules it cannot both satisfy will quietly pick one; the rule it drops then reads as disobedience instead of as the contradiction it actually is.

- Constraint overload, too many rules competing for attention: prompt and SOP engineering, with the periodic analysis of constraint density and redundancy it prescribes ([Part 2](implementation-disciplines.md)).
- Rules that should have been deterministic guards: the division of labour that reserves the SOP for judgment and pushes the rest into the harness ([Part 2](implementation-disciplines.md)), which is where such shared machinery belongs in the first place ([Part 5](agent-harness.md)).
- Instructions that contradict each other, forcing the model to choose: prompt and SOP engineering, where every constraint carries an explicit requirement level ([Part 2](implementation-disciplines.md)).

### It won't use the tool I gave it, or calls it wrong

Before theorizing about the model, read the transcript: the calls it actually made, with their arguments, in order (the per-(sub)agent, per-tool capture in [Part 6](observability.md)). That record decides which of three failures you have. If the tool is never called at all, the procedure probably never says when to reach for it, and a tool the SOP does not situate is one the model has to guess about. If it is called with malformed or wrong arguments, the schema and the description are the suspects: an ambiguous parameter, a nullable field that some model and runtime combinations handle badly, a description that documents the implementation instead of the decision the caller has to make. If the wrong tool keeps winning, there are too many overlapping ones, and the fix is a smaller set of precise, typed operations rather than a better prompt. Structured-output validation failures are the same schema problem one layer over, so read a response that will not parse as a contract specified badly, not as a model that cannot count braces.

- Tool description and schema quality, including ambiguous or nullable parameters: compose typed tools over one fuzzy lookup ([Part 4](three-layer-model.md)), plus the hygiene rule on provider-specific tool-argument quirks ([Part 2](implementation-disciplines.md)).
- Too many overlapping tools for the model to choose between: compose typed tools over one fuzzy lookup, so the job is picking the right operation rather than hoping one lookup suffices ([Part 4](three-layer-model.md)).
- An SOP that never says when to reach for the tool: prompt and SOP engineering ([Part 2](implementation-disciplines.md)).

### Results differ from run to run

Before calling the agent nondeterministic, decide whether the variance is in the system or in how you are looking at it, because the fixes sit in opposite places. Check the boring inputs first: a temperature above zero produces exactly this symptom, and it is easy to assume away when the parameter is a default nobody consciously passed. Then check what moved underneath the run, because an unpinned model version is an unpinned dependency and a silent provider upgrade shifts your numbers without touching your code. Then check the world: a run over live web results or a live corpus is reading different input each time, and no amount of pinning brings yesterday's page back. What remains is genuine model stochasticity, which is not a defect to eliminate but a property to report, so run each candidate several times and give the spread rather than a single flattering number. And if the variance appears only in your tests or eval harness, suspect the harness: a check that depends on wall-clock, unseeded randomness, or ordering is flaky on its own account.

- Sampling parameters left where determinism was assumed: expose model parameters as optional, defaulted flags, so a run's actual settings are visible ([Part 5](agent-harness.md)).
- An unpinned model version moving underneath you: treat the model and the provider as dependencies, pinned and recorded ([Part 9](security-supply-chain.md)).
- A live web or live corpus changing between runs: measure honestly, with repeated runs and a reported variance band ([Part 7](evaluation.md)).
- A nondeterministic test or eval mistaken for a nondeterministic agent: keep tests deterministic by injecting the clock and the seed ([Part 2](implementation-disciplines.md)).

*Whatever brought you here, the durable fix ends the same way every change does: encode the standard as an executable check so the symptom cannot return unannounced ([Part 1](lifecycle.md)). The full story starts at the [beginning](README.md).*
