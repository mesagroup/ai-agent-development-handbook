---
id: arch/harness-bounding
domain: arch
locality: global
evidence: >-
  The check reports once for the repository, one row per harness home read,
  naming the home and what it was resolved from, or one row for the
  repository where two or more agents share no layer at all or where it runs
  no agent. For each of the
  six bounds, and for each part of a bound that has parts, the row records one
  of four states, with the sites behind it: set in the
  harness, with the `file:line` of the site that constructs the thing it
  bounds; not set there, with each agent or tool that reaches the construct
  and whether it sets its own bound, at its `file:line`, or none; nothing to
  bound, with the search that found no such construct; and, on a project
  with no harness separate from its one agent, set or not set in that one
  tier. A retry the row reports also records what it wraps, who applies it,
  and whether the operation is safe to repeat or carries an idempotency key.
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
      chunk arrives. These are examples, not the set: what counts is a
      wall-clock deadline on every turn and, wherever a turn streams, an idle
      deadline on the stream. A client read timeout belongs to the
      `http-client` tell and does not answer this one, because it bounds one
      socket read and not a turn that keeps receiving slowly. A project with no
      streaming loop has nothing for the idle part to bound, and the search
      that shows so is recorded; the wall-clock part applies to every turn
      there is, streamed or not.
  - lang: any
    kind: procedure
    answers: http-client
    note: >-
      **A hardened outbound HTTP client whose retries wrap only what is safe to
      repeat.** Read where the harness constructs the client its agents and
      tools share: connect and read timeouts set explicitly, a bounded retry
      count, TCP keep-alive so a dropped socket surfaces as an error rather
      than an indefinite wait, and retries limited to operations safe to
      repeat or carrying an idempotency key. In Python, for example, an
      `httpx.Client` or `httpx.AsyncClient` built with a `timeout`, or a
      `requests` session behind a wrapper that supplies one, since `requests`
      sets no timeout by default; in TypeScript, a `fetch` wrapper that passes
      a `signal`, or an `undici` `Agent` with its connect, headers and body
      timeouts set rather than left at their defaults. The tell's parts are the
      explicit timeouts, the retry bound, keep-alive and retry safety. A client
      that leaves its timeouts at a library's default is read by what that
      default is: a finite one, as `httpx` has, bounds the call but is not set
      for the explicit-timeout part, and the row records its value; no default
      at all, as with `requests`, leaves the call with no timeout, which is
      the unbounded case. Read the default from the library's own
      documentation for the version the project locks, since a default is a
      fact about a release and not about the language. Then read every retry on the path
      for what it wraps, as `Retry safety is part of the client tell` below
      says. In Python, bandit's `B113` and ruff's `S113` flag a module-level
      `requests` call with no timeout and an `httpx` call whose timeout is set
      to `None`; they miss every call made on a session or client object and
      do not say whether a call goes through the harness, so they find some
      candidate call sites but cannot answer the tell even with a confirmation
      beside them, and the record prescribes neither as a route.
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
      harness runs: a maximum number of cycles and a token budget the loop
      checks, ending the run as a diagnosable budget error when either is
      spent. Both halves are the tell, so a loop capping one and not the other
      is not bounded on the other. An SDK option that caps turns counts where
      the harness sets it; a cap each agent passes in for itself is that
      agent's own bound. The model deciding when to stop is not a cap: the
      handbook places the cap in the harness because that judgment is what has
      failed.
  - lang: any
    kind: procedure
    answers: payload-size
    note: >-
      **A size strategy for oversized tool results.** Read the path every tool
      result takes before it reaches the model: one decision, made in the
      harness, of what an oversized result becomes, whether truncated,
      summarized or written to an artifact the model can fetch on demand. For
      this tell the parties that can repeat the bound are the tools rather than
      the agents, so a limit each tool applies to its own output is the
      repeated case, and a tool that returns whatever its upstream handed it,
      with nothing on the path, is the unbounded one. A tool whose result is
      bounded by construction - a count, a flag, a fixed-shape record - has
      nothing for this tell to bound, and neither has a project whose agents
      call no tools.
  - lang: any
    kind: procedure
    answers: teardown
    note: >-
      **Time-bounded teardown of external resources.** Read where the harness
      closes what it opened - browsers, sessions, worker threads, an HTTP
      client's connection pool among the sessions: each close
      runs under a time limit, so a wedged close cannot hang the run or leak a
      billed resource. In Python, for example, the close or `aclose` awaited
      under `asyncio.timeout()`; in TypeScript, a close raced against a timer.
      A context manager or a `finally` that closes with no time limit is not
      bounded for this tell. A project that opens no such resource has nothing
      for this tell to bound.
---

# Harness bounding

Whether the project's harness sets six reliability bounds by default, so that no agent author has to remember them: wall-clock and idle timeouts on turns and streaming loops, a hardened outbound HTTP client whose retries wrap only what is safe to repeat, a circuit breaker on a dependency that keeps failing, a cycle and token budget cap on the agent loop, a size strategy for oversized tool results, and time-bounded teardown of external resources. An unbounded call, an unbounded cycle count and an unbounded payload are each a production failure waiting for its trigger, differing only in which resource they exhaust. The finding this check exists for is a bound that is missing, or set separately by each agent that needs it, because a bound every agent author must remember is one the next agent forgets.

## What the harness is here

**The harness is resolved by role, not by path.** It is the shared layer the handbook's `Build the harness, don't inline the plumbing` asks for: the module or package that constructs the model client, the outbound HTTP client, the agent loop, the path tool results take back to the model and the lifecycle of external resources, for more than one agent. Find it from the tiers the binding-rules file states or, where it states none, the tier map this domain inferred before measuring anything, and confirm it by reading which modules construct the model client and run the loop. Say in the row which home was read and what it was resolved from, because a reader cannot check the finding without knowing what was read. A repository can hold more than one such home, for example one per deployable, and each is a row of its own. **Two or more agents sharing no layer at all have no harness home, and that is not a reason for silence:** the row is then the repository, every tell is read over the agents as the next section says, and a bound each agent sets for itself is the repeated-bound finding this check exists for, not a clean result.

## How each tell is read

**The tell's state is read over every party that reaches the construct it bounds, and over every such construct a party has.** For most tells those parties are the agents; for the size strategy they are the tools, as that route says. A party with two HTTP clients or two loops is read for each, and an uncovered one is uncovered whatever the other does. A tell is **set in the harness** when a harness default covers every party and every construct that reaches it: record the constructing site's `file:line`. It is **not set there** when some party is not covered by a harness default: the row then names each party and whether it sets its own bound or none, and that is the finding - where every party sets its own, because the next one is the one that forgets, and where any party sets none, because that party is unbounded. A tell, or a part of one, has **nothing to bound** exactly when the construct it bounds does not exist in the project - no stream for the idle part of the turn timeouts, no tools for the size strategy, no external resource to close, and no agent at all for every tell: record the search that showed it, which answers that tell or part, and it is not a finding. The examples are not the set; the rule is the construct's absence. A repository that runs no agent therefore has nothing to bound on any tell and gets the domain's clean value with the search recorded.

**A party overriding a harness default with another bound is not a repeated bound.** It inherited the default and chose a different value, which is the harness working; record the tell as set in the harness and name the override. An override that removes the bound - no timeout, no cap, an unlimited budget - leaves that party unbounded, and the tell is not set there.

**A tell with parts records each part, and takes the least bounded of them.** The turn timeouts have a wall-clock and an idle part, the loop budget a cycle and a token part, and the client its explicit timeouts, retry bound, keep-alive and retry safety. The row names each part's state, and the tell's state is the least bounded one among them, a part with nothing to bound not counting against it.

**Each tell is its own axis.** The routes carry one `answers` value per tell, so a run that read four of the six has not answered the check and says which two it did not read. A tell with nothing to bound has been read.

## Retry safety is part of the client tell

**A retry that wraps a non-idempotent operation is a finding wherever it is applied.** A retried call that creates something - a payment, a job submission, a write with no deduplication - can land twice, so the handbook asks for an idempotency key or a deduplicated write before the operation is put behind a retry. Read every retry on the path, whether the harness applies it, an agent adds it, or a model or HTTP SDK applies it by default, and record what it wraps and whether that operation is safe to repeat as it stands, carries an idempotency key, or is neither.

## A project with no harness tier

**A single-agent application has no harness separate from its agent, and the check still runs.** A bound that covers every construct of that kind in the one tier that exists is the domain's clean value for that tell, with the construction sites recorded as evidence; a construct it leaves uncovered is the finding; a tell with nothing to bound is read as above. The finding for a bound repeated across agents needs two or more agents, so it cannot arise here, and a limit each tool sets for itself in the one agent is read as that tier's bound for those tools. A project with two or more agents and no shared layer is not this case; the section above says how it is read. The clean value is not `not-applicable`, which `audit-core` reserves for a check with no lens in a partition's languages: this check reads source in every language, so it has a lens everywhere.

## Severity

**Critical** - a call, a cycle count or a payload left unbounded for any party that reaches it: a turn with no wall-clock limit, a stream with no idle limit, an outbound call with no connect or read timeout, a loop with no cycle cap or no token budget, or tool results with no size strategy on their path. These are the three unbounded failures the handbook names, and it ranks them alike.

**Important** - a bound set separately by each party rather than in the harness; a retry wrapping a non-idempotent operation with no idempotency key or deduplicated write; a retry with no bound on its count; a client relying on a library's finite default timeout rather than an explicit one; a client with no TCP keep-alive; no circuit breaker in front of an external dependency a run calls; teardown of an external resource with no time limit.

There is no **Minor** tier: every default the handbook lists guards a run against hanging, running away or leaking, and none of those is cosmetic.

## Fix

**Set each bound where the harness constructs the thing it bounds, and delete the per-party copies** rather than adding a harness default beside them. Give a retried non-idempotent operation an idempotency key or a deduplicated write before it goes behind a retry. Put a breaker in front of a dependency that can fail repeatedly, route every tool result through one size strategy, and run each close under a time limit.

**Unlike most fixes in this domain, adding a bound changes behaviour.** A run that used to hang now ends with a timeout or budget error, so choose each value from the project's observed latencies and spend rather than a round number, and run the project's own tests and smoke path against the change rather than treating it as a refactor.

## What this check does not do

**It does not judge a bound's value.** Whether a timeout is long enough or a budget large enough needs the run history, which a snapshot does not hold. Measuring how long runs take, what they spend and how often a dependency fails is a performance and observability question; this check reads whether each bound exists and where it lives.

**It reads the bounding half of the harness claim only.** Whether the model client, configuration and entry points live in the harness rather than in each agent is the other half of `Build the harness, don't inline the plumbing`, and it is not read here.

**It does not decide whether a harness's shared state is hidden coupling.** A breaker's failure counter or a loop's budget is state the harness keeps on purpose; whether any shared state couples modules the import graph does not show is `arch/hidden-coupling`'s question.

## Review lens

**Bound placement** - is each bound now set where the harness constructs the thing it bounds, covering every party that reaches it, with every per-party copy removed rather than a harness default added beside them?

**Retry safety** - does every retry that wraps a non-idempotent operation carry an idempotency key or a deduplicated write, and was the key added rather than the retry removed to close the finding?
