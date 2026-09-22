---
id: arch/harness-bounding
domain: arch
locality: global
evidence: >-
  The check reports once for the repository, one row per harness home read,
  naming the home and how it was resolved. For each of the six bounds the row
  records its state: set in the harness, with the `file:line` of the site that
  constructs the thing it bounds; present only as per-agent copies, with every
  copy's `file:line`; or absent, with what was searched. A retry the row
  reports also records what it wraps and whether that operation carries an
  idempotency key. On a project with no harness separate from its one agent,
  the row is that agent's tier and records whether each bound is set there or
  absent.
handbook:
  - agent-harness/make-bounding-the-default
routes:
  - lang: any
    kind: procedure
    answers: timeouts
    note: >-
      **Wall-clock and idle timeouts on agent turns and streaming loops.** Read
      where the harness runs a turn and consumes a stream: a wall-clock limit on
      the whole turn and an idle limit between chunks, so a stalled or slowly
      dribbling response ends as an error. In Python, for example,
      `asyncio.timeout()` or `asyncio.wait_for` around the turn and a deadline
      per chunk in the stream loop; in TypeScript, an `AbortSignal` from
      `AbortSignal.timeout()` passed to the call, or a timer that aborts when no
      chunk arrives. These are examples, not the set: what counts is a deadline
      the harness applies to every turn. A client read timeout belongs to the
      `http-client` tell and does not answer this one, because it bounds one
      socket read and not a turn that keeps receiving slowly.
  - lang: any
    kind: procedure
    answers: http-client
    note: >-
      **A hardened outbound HTTP client whose retries wrap only what is safe to
      repeat.** Read where the harness constructs the client its agents and
      tools share: explicit connect and read timeouts, a bounded retry count,
      keep-alive, and retries limited to operations safe to repeat or carrying
      an idempotency key. In Python, for example, an `httpx.Client` or
      `httpx.AsyncClient` built with a `timeout`, or a `requests` session behind
      a wrapper that supplies one, since `requests` sets no timeout by default;
      in TypeScript, a `fetch` wrapper that passes a `signal`, or an `undici`
      `Agent` built with connect and body timeouts. Then read every retry for
      what it wraps, as `Retry safety is part of the client tell` below says.
      In Python, bandit's `B113` and ruff's `S113` report a `requests` or
      `httpx` call that sets no timeout, which can find candidate call sites;
      neither says whether a call goes through the harness, which is what this
      tell asks, so the record prescribes neither as a route of its own.
  - lang: any
    kind: procedure
    answers: circuit-breaker
    note: >-
      **A circuit breaker on a dependency that keeps failing.** Read where the
      harness calls each external dependency: after a threshold of failures it
      stops calling for a cooldown and fails fast. A breaker library, for
      example `pybreaker` in Python or `opossum` in TypeScript, and a hand-rolled
      failure counter with a cooldown both count; what counts is that a
      dependency already down is not called again by every run in flight.
  - lang: any
    kind: procedure
    answers: loop-budget
    note: >-
      **A cycle and token budget cap on the agent loop.** Read the loop the
      harness runs: a maximum number of cycles and a token or cost budget
      checked before each model call, ending the run as a diagnosable budget
      error when either is spent. An SDK option that caps turns counts where
      the harness sets it; a cap each agent passes in for itself is a per-agent
      copy. The model deciding when to stop is not a cap: the handbook places
      the cap in the harness because that judgment is what has failed.
  - lang: any
    kind: procedure
    answers: payload-size
    note: >-
      **A size strategy for oversized tool results.** Read the path every tool
      result takes before it reaches the model: one decision, made in the
      harness, of what an oversized result becomes, whether truncated,
      summarized or written to an artifact the model can fetch on demand. A
      limit each tool applies to its own output is the per-agent copy, applied
      per tool; a tool that returns whatever its upstream handed it, with
      nothing on the path, is the absent case.
  - lang: any
    kind: procedure
    answers: teardown
    note: >-
      **Time-bounded teardown of external resources.** Read where the harness
      closes what it opened - browsers, sessions, worker threads, subprocesses:
      each close runs under a time limit, so a wedged close cannot hang the run
      or leak a billed resource. In Python, for example, the close or `aclose`
      awaited under `asyncio.timeout()`, or a thread joined with a timeout; in
      TypeScript, a close raced against a timer. A context manager or a
      `finally` that closes with no time limit is the absent case for this
      tell.
---

# Harness bounding

Whether the project's harness sets six reliability bounds by default, so that no agent author has to remember them: wall-clock and idle timeouts on turns and streaming loops, a hardened outbound HTTP client whose retries wrap only what is safe to repeat, a circuit breaker on a dependency that keeps failing, a cycle and token budget cap on the agent loop, a size strategy for oversized tool results, and time-bounded teardown of external resources. An unbounded call, an unbounded cycle count and an unbounded payload are each a production failure waiting for its trigger, differing only in which resource they exhaust. The finding this check exists for is a bound that is absent, or present only as a copy in each agent, because a bound every agent author must remember is one the next agent forgets.

## What the harness is here

**The harness is resolved by role, not by path.** It is the shared layer the handbook's `Build the harness, don't inline the plumbing` asks for: the module or package that constructs the model client, the outbound HTTP client, the agent loop, the path tool results take back to the model and the lifecycle of external resources, for more than one agent. Take it from the declared architecture this domain establishes before measuring anything, and say in the row which home was read and why, because a reader cannot check the finding without knowing what was read. A repository can hold more than one such home, for example one per deployable, and each is a row of its own.

## How each tell is read

**Each bound is in one of three states, and the row records which.** It is **in the harness** where it is set at the site that constructs the thing it bounds, as a default every agent that goes through the harness inherits; record that site's `file:line` and the path by which agents reach it. It is **present only as per-agent copies** where two or more agents each set their own bound with no harness default beneath them; that is the finding the handbook names even when every copy is correct, because the next agent is the one that forgets, and every copy is recorded. It is **absent** where no bound exists anywhere on the path; that is the finding, and the row records what was searched.

**An agent overriding a harness default is not a copy.** It inherited the default and chose a different value, which is the harness working; record the tell as in the harness and name the override.

**Each tell is its own axis.** The routes carry one `answers` value per tell, so a run that read four of the six has not answered the check and says which two it did not read.

## Retry safety is part of the client tell

**A retry that wraps a non-idempotent operation is a finding even when the retry lives in the harness.** A retried call that creates something - a payment, a job submission, a write with no deduplication - can land twice, so the handbook asks for an idempotency key or a deduplicated write before the operation is put behind a retry. Read each retry the harness applies for the operations it wraps, and record for each whether it is safe to repeat as it stands, carries an idempotency key, or is neither.

## A project with no harness tier

**A single-agent application has no harness separate from its agent, and the check still runs.** A bound set in the one tier that exists is the domain's clean value for that tell, with the construction site recorded as evidence. A bound absent everywhere is the finding. The per-agent-copy finding needs two or more agents, so it cannot arise here. The clean value is not `not-applicable`, which `audit-core` reserves for a check with no lens in a partition's languages: this check reads source in every language, so it has a lens everywhere.

## Severity

**Critical** - on a path every run takes, a model or tool call with no timeout, or an agent loop with no cycle or token cap. These are the unbounded call and the unbounded cycle the handbook names: nothing stops a run that hangs or keeps spending.

**Important** - a retry wrapping a non-idempotent operation with no idempotency key or deduplicated write; a retry with no bound on its count; a bound present only as per-agent copies; no circuit breaker in front of an external dependency the harness calls; no size strategy for tool results; teardown of an external resource with no time limit.

**Minor** - a hardened client with no keep-alive, the one default the handbook lists whose absence degrades a run rather than hanging it.

## Fix

**Set each bound where the harness constructs the thing it bounds, and delete the per-agent copies** rather than adding a harness default beside them. Give a retried non-idempotent operation an idempotency key or a deduplicated write before it goes behind a retry. Put a breaker in front of a dependency that can fail repeatedly, route every tool result through one size strategy, and run each close under a time limit.

**Unlike most fixes in this domain, adding a bound changes behaviour.** A run that used to hang now ends with a timeout or budget error, so choose each value from the project's observed latencies and spend rather than a round number, and run the project's own tests and smoke path against the change rather than treating it as a refactor.

## What this check does not do

**It does not judge a bound's value.** Whether a timeout is long enough or a budget large enough needs the run history, which a snapshot does not hold. Measuring how long runs take, what they spend and how often a dependency fails is a performance and observability question; this check reads whether each bound exists and where it lives.

**It reads the bounding half of the harness claim only.** Whether the model client, configuration and entry points live in the harness rather than in each agent is the other half of `Build the harness, don't inline the plumbing`, and it is not read here.

## Review lens

**Bound placement** - is each bound now set where the harness constructs the thing it bounds, with every per-agent copy removed rather than a harness default added beside them?

**Retry safety** - does every retry that wraps a non-idempotent operation carry an idempotency key or a deduplicated write, and was the key added rather than the retry removed to close the finding?
