# Troubleshooting: From Symptom to Section

*The nine parts teach the disciplines in the order you would learn them. This page is the other entry point, for the day you arrive with a problem instead of a curriculum: an agent that burns money, stalls, lies, or resists measurement, and no obvious owner among the disciplines. Find your symptom, read the short diagnosis, follow the route.*

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

The run is alive, spending, and getting nowhere: the same tool called with near-identical arguments, the cycle count climbing, the answer no closer. Read the agent-loop cycle counts and the per-tool record first (the per-(sub)agent, per-tool capture in [Part 6](observability.md)), then the repeated calls themselves in the artifacts the run persisted; the shape of the repetition names the cause. A loop that would run forever if you let it is a missing bound, and bounds belong in the harness rather than in the model's good intentions. A loop that does stop, but late, usually means the procedure never said what done looks like, so the agent keeps polishing an answer that was finished several cycles ago. A loop that reissues the same call because the result was unusable is not a looping problem at all; see the tool-misuse entry below. And when the bounds exist, the stop condition is explicit, and the tools return clean output, what remains is a model that cannot plan its way through the task, which is a model-choice question settled by measurement rather than by prompt patches.

- No cycle or budget bound in the harness: make bounding the default ([Part 5](agent-harness.md)).
- An SOP with no stop condition or completion criterion: prompt and SOP engineering ([Part 2](implementation-disciplines.md)).
- A tool returning output the agent cannot use, so it retries blindly: the tool-misuse entry below.
- A model too weak to plan its way through the task: pick the approach that fits the decision, and settle the swap with a staged evaluation funnel ([Part 7](evaluation.md)).

## Output quality

### It fails with out-of-context errors

The window did not get smaller, so ask what grew. Before raising any limit, read one failing run's context by origin: the question is which producer put the bytes there, and the answer is rarely the user's query. The first suspect is bookkeeping (timing, sizes, provenance, analysis metadata) riding inside the prompt instead of on a side channel the model never sees. The second is a tool that hands back whatever the upstream service gave it, because nothing in the harness ever decided what a too-large result should become. The third is quieter and more expensive: the run fetches far more than it uses, and only per-item instrumentation will show you that, so the fix is less retrieval rather than a bigger window.

- Bookkeeping and analysis metadata riding inside the prompt: keep observability out of the model's context ([Part 6](observability.md)).
- Tool output with no truncation or summarization strategy: make bounding the default, extending its rule that an unbounded external call is a latent hang to size as well as time ([Part 5](agent-harness.md)).
- Over-fetching that instrumentation would show as unused: the utilization metric that per-(sub)agent, per-tool capture makes visible ([Part 6](observability.md)).

### It hallucinates

One word, three different failures, and the fix for each lives somewhere else entirely. Establish first whether the claim is invented or merely mangled, by checking whether it traces to anything the run actually fetched. If it traces to nothing, this is ungrounded generation out of the model's weights, and the answer is an eval dimension that scores groundedness plus an SOP that binds the answer to its sources rather than a prompt that asks nicely. If it traces to a real document but the wording is wrong, do not blame the model yet: a model behaving perfectly will reproduce an extraction error faithfully, and the mangled quote it hands back looks identical on the page to the other cause. Reproduce the same question with that passage alone in the context: a clean quote in isolation means the context was diluted, while a quote that comes back wrong again means the error was already in what you fed the model, so diff the Layer 1 representation against the source page to see whether ingestion or OCR introduced it. That isolation reproduction is the whole pivot between the two: it separates a pipeline defect you fix upstream from an attention problem you fix by putting less in the window. Citations that point at real sources which do not support the claim are the first case wearing a bibliography, and the same groundedness measurement catches them.

- Claims that trace to no fetched source: measure the behaviors that matter, with groundedness among them ([Part 7](evaluation.md)), and an SOP whose constraints bind the answer to its sources ([Part 2](implementation-disciplines.md)).
- Misquotation introduced upstream by the extraction pipeline: the engine-agnostic Layer 1 contract ([Part 4](three-layer-model.md)), scored on its own against a frozen golden set ([Part 7](evaluation.md)).
- Misquotation from a context too full to attend to: utilization, which shows how much of what you loaded was ever used ([Part 6](observability.md)), and bounding what enters the context in the first place ([Part 5](agent-harness.md)).

### It reasons wrongly from correct facts

Unlike the entry above, nothing here is invented or mangled: every fact checks out and the conclusion still does not follow. That narrows it to two places, and neither of them is retrieval. Either the model cannot carry the inference the task demands, which is a model-choice question and therefore a measurement question rather than something a sharper prompt will patch; or the procedure asks for a leap where it should ask for steps, handing the model one move to make when the reasoning has three. Tell them apart cheaply: decompose the step in the SOP and re-run the same case, then run the same case unchanged against a stronger model. Whichever intervention moves the answer names the cause, and if it is the model, the swap is settled by measurement rather than by the impression the demo left.

- A model too weak to carry the inference: rank the candidates with a staged evaluation funnel, then build an escalation ladder so the expensive model runs only on the residual ([Part 7](evaluation.md)).
- An SOP that asks for a leap where it should ask for ordered steps: prompt and SOP engineering ([Part 2](implementation-disciplines.md)).

### It ignores its SOP

An agent that ignores a rule is usually not disobeying it; it is failing to weigh it against forty others. Count the constraints before rewriting any of them, because density is the measurement here, and a prompt that overloads the model degrades exactly the reasoning you were asking it for. Then sort the rules by kind. Anything a machine could enforce (a schema on the output, a validator in the tool, a guard in the pipeline) does not belong in the SOP at all, and moving it out buys attention for the rules that genuinely need judgment. What is left may still contradict itself, and a model handed two rules it cannot both satisfy will quietly pick one; the rule it drops then reads as disobedience instead of as the contradiction it actually is.

- Constraint overload, too many rules competing for attention: prompt and SOP engineering, with the periodic analysis of constraint density and redundancy it prescribes ([Part 2](implementation-disciplines.md)).
- Rules that should have been deterministic guards: the division of labour that keeps the SOP for judgment and pushes the rest into the harness ([Part 2](implementation-disciplines.md)), where shared machinery belongs ([Part 5](agent-harness.md)).
- Instructions that contradict each other, forcing the model to choose: prompt and SOP engineering, where every constraint carries an explicit requirement level ([Part 2](implementation-disciplines.md)).

### It won't use the tool I gave it, or calls it wrong

Before theorizing about the model, read what the run actually did: which tools it called and in what order, from the per-(sub)agent, per-tool capture ([Part 6](observability.md)), and what it passed them, from the artifacts persisted alongside that capture. That record decides which of three failures you have. If the tool is never called at all, the procedure probably never says when to reach for it, and a tool the SOP does not situate is one the model has to guess about. If it is called with malformed or wrong arguments, the schema and the description are the suspects: an ambiguous parameter, a nullable field that some model and runtime combinations handle badly, a description that documents the implementation instead of the decision the caller has to make. If the wrong tool keeps winning, there are too many overlapping ones, and the fix is a smaller set of precise, typed operations rather than a better prompt. Structured-output validation failures are the same schema problem one layer over, so read a response that will not parse as a contract specified badly, not as a model that cannot count braces.

- A description or schema that misleads, including nullable parameters: compose typed tools over one fuzzy lookup ([Part 4](three-layer-model.md)), plus the hygiene rule on provider-specific tool-argument quirks ([Part 2](implementation-disciplines.md)).
- Too many overlapping tools for the model to choose between: compose typed tools over one fuzzy lookup, so the job is picking an operation rather than hoping one lookup suffices ([Part 4](three-layer-model.md)).
- An SOP that never says when to reach for the tool: prompt and SOP engineering ([Part 2](implementation-disciplines.md)).

### Results differ from run to run

Before calling the agent nondeterministic, decide whether the variance is in the system or in how you are looking at it, because the fixes sit in opposite places. Check the boring inputs first: a temperature above zero produces exactly this symptom, and it is easy to assume away when the parameter is a default nobody consciously passed. Then check what moved underneath the run, because an unpinned model version is an unpinned dependency and a silent provider upgrade shifts your numbers without touching your code. Then check the world: a run over live web results or a live corpus is reading different input each time, and no amount of pinning brings yesterday's page back. What remains is genuine model stochasticity, which is not a defect to eliminate but a property to report, so run each candidate several times and give the spread rather than a single flattering number. And if the variance appears only in your tests or eval harness, suspect the harness: a check that depends on wall-clock, unseeded randomness, or ordering is flaky on its own account.

- A sampling parameter left at a default nobody passed: expose model parameters as optional, defaulted flags, bundled into a named profile so a run's settings are recoverable ([Part 5](agent-harness.md)).
- An unpinned model version moving underneath you: treat the model and the provider as dependencies, pinned and recorded ([Part 9](security-supply-chain.md)).
- A live web or live corpus changing between runs: build a dataset you can trust, frozen for the comparison rather than fetched live ([Part 7](evaluation.md)).
- Genuine model stochasticity read as a defect: measure honestly, with repeated runs and a reported variance band ([Part 7](evaluation.md)).
- A nondeterministic test or eval mistaken for a nondeterministic agent: keep tests deterministic by injecting the clock and the seed ([Part 2](implementation-disciplines.md)).

## Measurement and change

### It works in the demo but fails on real queries

A demo is not a small production; it is a different distribution, and the gap between the two is a property of your dataset before it is a property of your agent. Ask first where the examples came from, because a set curated by the same people who tuned the system, or assembled from its own successful outputs, reports near-perfect quality by construction and stays silent about everything it never contained. Then compare the shapes rather than the scores: real inputs arrive malformed, in another language, far longer than anything you rehearsed, and truncated in places no curated example ever is. If the benchmark is honest and broad and production still disagrees with it, what is missing is the return path, because without real sessions flowing back into development the only failures you can fix are the ones you thought to imagine. Hold on to the blunt version: an example is not a dataset, and a demo that went well is not evidence.

- A benchmark too narrow, or drawn from the system's own output: build a dataset you can trust, from a source independent of the system under test ([Part 7](evaluation.md)).
- Production inputs that do not look like the rehearsed ones: build a dataset you can trust, shaped by the prevalence and the malformations the real corpus has ([Part 7](evaluation.md)).
- No return path from production into development: close the loop, persisting the same usage record with each production interaction ([Part 6](observability.md)).

### I changed the prompt and can't tell if it helped

Not being able to tell is itself the finding, and it is a finding about your instruments rather than about the prompt. An edit is a hypothesis that this will be better, and better is only meaningful against a metric measured on a dataset that existed before the edit did. So if no frozen benchmark exists, stop tuning and build the smallest one that exercises the behaviour you meant to improve, then run the loop: measure, decide, ship, re-measure, and let the eval earn its way up to a merge gate once it has proven stable. If a benchmark does exist and the numbers still refuse to separate, count what actually moved between the two runs, because a change that touched the wording, the model, and the retrieval depth at once measures none of the three. And if you cannot reconstruct what the prompt used to say or why it changed, the failure happened at commit time: an edit buried in a code commit with no rationale hands the next reader, usually you, a behavioural change with no hypothesis attached.

- No frozen benchmark to compare against: run the loop against a dataset fixed before the decision, and grow the eval into a gate once it is stable ([Part 7](evaluation.md)).
- Several variables moved between the two runs: measure honestly, changing one variable at a time so the comparison stays like-for-like ([Part 7](evaluation.md)).
- Prompt edits buried inside code commits: keep a prompt change in its own commit and explain why it changed ([Part 2](implementation-disciplines.md)).

### I don't trust my eval numbers

Distrust is the right instinct; the work is localizing it, because an eval has three joints and they come loose in different ways. Ask what the judge is worth first, since an LLM judge earns trust only on the dimensions where it has been shown to track a human on a sample, and an uncalibrated rubric score is a confident number about nothing in particular. Then ask what the ranking is worth, because a leaderboard whose order changes between runs is reporting noise rather than a difference, and the answer is more runs with the spread published, not a rerun until the order looks right. Then ask what the rubric is aimed at, since an instrument can be perfectly calibrated and pointed at the wrong thing, and a capability with no case for its key failure mode stays a gap however good the score looks. All three end in the same place, which is worse than uncertainty: the enemy is false confidence ([Part 7](evaluation.md)), a number that is wrong and believed, since confidence is where you stop looking.

- A judge never checked against a human: use the LLM judge only where it agrees with the human, and spend the human's time where it does not ([Part 7](evaluation.md)).
- A ranking that flips between runs: measure honestly, reporting the spread across repeated runs instead of a single point estimate ([Part 7](evaluation.md)).
- A rubric aimed at the wrong behaviour: measure the behaviors that matter, mapping each behaviour the product depends on to an eval that exercises it ([Part 7](evaluation.md)).

### My eval numbers moved and I changed nothing

Something did change; it was simply not yours. Unlike the run-to-run scatter above, this is a step between two points in time, so rule out the null case first: a gap that sits inside the spread is not a movement, and two point estimates will happily manufacture one. Then look at the model, since a provider that upgrades a version behind a stable-looking name is an unpinned dependency that moves your numbers without touching a line of your code, and a run that never recorded which model produced its result cannot tell you either way. Then look at the dataset, because a gold that was extended, relabelled, or re-thresholded between the runs still renders a clean comparison that no longer means what it says, and a benchmark is only comparable to itself. Then look outward, at whether the eval reads the live world, since a case that searches the web or scores a moving corpus gets different input every run and no amount of pinning brings yesterday's page back. One neighbouring case is not drift at all: if you swapped the model deliberately and the agent got worse, that is a selection question, settled by putting the candidates through a staged evaluation funnel ([Part 7](evaluation.md)) rather than by reverting on a hunch.

- A silent provider-side model upgrade: treat the model and the provider as dependencies, pinned where the provider allows it and recorded with every result ([Part 9](security-supply-chain.md)).
- A gold, a query set, or a threshold that moved between runs: build a dataset you can trust, and freeze it for the duration of a comparison ([Part 7](evaluation.md)).
- An eval that reads the live web or a moving corpus: measure honestly, keeping the run reproducible and bucketing environmental failures apart from quality ones ([Part 7](evaluation.md)).

*Whatever brought you here, the durable fix ends the same way every change does: encode the standard as an executable check so the symptom cannot return unannounced ([Part 1](lifecycle.md)). The full story starts at the [beginning](README.md).*
