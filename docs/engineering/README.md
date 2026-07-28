# AI Agent Development Handbook

How to build software and AI agents: the practices, and the reasons behind them. The premise is doubly agentic: what you build is AI agents, and you build it with coding agents that write most of the code under your direction. Read each section as a set of **directives backed by their reasons**: it states what to do, then why the practice earns its place. The reasons matter (they are what let you apply a rule to a case it doesn't literally cover), but when you just need to act, the directives and the checklists are the operational surface.

The practices are meant to be portable. Some lean on shared infrastructure (a model catalog, a configuration system, a run harness), but nothing below *depends* on any particular implementation of it: a project that has none of it should still recognize every directive as its own. Where a section describes a capability, read it as "here is what a good setup provides, and what to build or demand if you don't have it", not "here is a specific tool."

Arriving with a problem rather than a curriculum? The [troubleshooting guide](troubleshooting.md) starts from the symptom and routes you to the parts that fix it.

## The story of a change

Every part of this handbook attaches to one story: the life of a single change. Follow it once, end to end, and the nine parts stop being a list of best practices; they become the stations where the change (and you) will need them.

It starts with an idea. A bug report comes in, an eval number dips, a user asks for a feature. The idea becomes an **issue**, because work that is not traceable to an issue evaporates: nobody can find its reasoning later, and nobody notices when it silently dies. From here on, though, you will rarely be the one writing the code. You direct agents that write most of it, and that single fact shapes the whole path ahead, because delegation on that scale only works if the human moments are chosen deliberately. The first one comes before any code exists: the issue becomes a **spec** (what exactly are we building, and how will we know it is right?), and the story stops until a human approves it. This is the cheapest moment in the whole story to discover we are building the wrong thing; every later stage multiplies the cost of that discovery. Then the spec becomes a **plan**: the work decomposed into tasks so complete that an implementer with zero context can execute them, and today that implementer is increasingly an agent. Raising the level of abstraction does not abolish the hard work: it relocates it upward, into the spec, the plan, the review, and the judgment calls between them. [Part 1](lifecycle.md) is this path in operational detail: the gates, the reviews, and the judgment calls that keep delegation from becoming guessing at scale. The craft each station on that path demands (how the code and the agent's behaviour get written, and the mechanical, human, and behavioural gates that catch what the writing missed) is [Part 2](implementation-disciplines.md).

The change needs a home, and the home has a shape. It lands in a codebase layered by reuse: a reusable core below, task-shaped applications above, dependencies pointing only toward the core, never sideways and never in a cycle ([Part 3](codebase-structure.md)). That shape decides the change's blast radius, and whether the next agent costs a prompt and its tools or a fresh copy of all the plumbing. If the change touches documents (a contract, a judgment, an invoice), it meets the same shape again inside the data: intrinsic structure that fully generalizes, a sparse vocabulary of domain entities, and a disposable task layer on top ([Part 4](three-layer-model.md)). And when it runs, it runs on machinery no change should ever rebuild: model aliases instead of hard-coded IDs, named configuration profiles, a headless CLI, cheap mock backends, external calls that are bounded by default ([Part 5](agent-harness.md)).

Implemented, tested, reviewed, merged. That is half the story, and the easy half. Now the change ships and starts doing things no unit test can see: fetching, spending, taking seconds and dollars in places you did not predict. The run records tell you what it actually did (what it fetched, what it used, what it cost, where its time went), because we instrument before we tune and keep the instruments out of the model's context ([Part 6](observability.md)). And then comes the question the whole handbook exists to answer honestly: **is the product actually better?** Not "do the tests pass": a change can be green on every unit test and still make an agent measurably worse. Better means measured, against a dataset the change did not get to define, with variance reported and the full cost on the table ([Part 7](evaluation.md)).

Here the loop closes. What the measurement teaches (a new failure form, a surprising cost, an assumption that did not survive contact with production) becomes the next issue. What the change leaves behind (the spec, the plan, a story of what surprised us, a recorded result) is the trail that lets someone who was not there, including a future you and the next agent, recover the decision and its evidence ([Part 8](documentation.md)). And over every change, not just this one, stands the obligation that no test and no eval will enforce: keeping the machine safe, from your own code's trust boundaries to your dependency graph to the pipeline that builds you ([Part 9](security-supply-chain.md)).

Do not expect the loop to terminate. That the story ends where it began is not a defect; it is how the system stays honest as the data, the models, and the team drift.

```d2 title="The story of a change; the marked steps are its human gates"
direction: right
*.class: step
**.width: 74
**.height: 56
idea: An idea
issue: Issue
spec: Spec {class: human}
plan: Plan
build: Build
merge: Merge {class: human}
run: Observe
decide: Evaluate
idea -> issue -> spec -> plan -> build -> merge -> run -> decide
decide -> idea: the next issue
```

### The parts, at a glance

| Part | Role in the story |
|---|---|
| **[1. Development lifecycle](lifecycle.md)** | The spine: issue to spec to plan to implementation to review to merge, with the human gates placed where they pay. |
| **[2. Implementation disciplines](implementation-disciplines.md)** | The craft of the stations: TDD, prompt and SOP engineering, and the mechanical, human, and behavioural gates. |
| **[3. Codebase structure](codebase-structure.md)** | The change needs a home: layered tiers, acyclic dependencies, composition over forking. |
| **[4. The three-layer document model](three-layer-model.md)** | The same shape inside the domain: intrinsic structure, domain entities, workflow knowledge. |
| **[5. The extended agent harness](agent-harness.md)** | The machinery the change runs on: aliases, profiles, headless CLIs, mocks, bounded calls. |
| **[6. Observability](observability.md)** | The change ships: instrument before you tune, account for the full cost. |
| **[7. Evaluation: how to decide](evaluation.md)** | The loop closes: was it actually better, measured against a dataset you trust? |
| **[8. Documentation & knowledge capture](documentation.md)** | What the change leaves behind: the trail that outlives the moment. |
| **[9. Security, dependencies & supply chain](security-supply-chain.md)** | The standing obligation: safe code, accounted dependencies, a trustworthy pipeline. |
| **[Troubleshooting](troubleshooting.md)** | The other entry point: from a symptom (it burns money, it hangs, it hallucinates) to the sections that fix it. |
| **[Coda](coda.md)** | Closing words: the loop, and what stays. |

## Starting from zero

The story above assumes a system for the change to land in. Building an agent, or a whole agentic application, from scratch does not get a different handbook: greenfield is the story of the *first* change. The loop is identical. What changes is that every station has to be built the first time you arrive at it, which turns the parts into a build order.

Begin where every change begins, with an issue and a spec, scoped to a thin end-to-end slice a user could exercise rather than to the whole application ([Part 1](lifecycle.md)). The narrow first slice forces the "how will we know it is right?" question while answering it is still cheap, and it gives every later station something real to attach to. Lay the tier skeleton before writing the first agent ([Part 3](codebase-structure.md)): that first agent will be almost entirely task layer, and that is correct. Resist building the reusable core speculatively; respect the boundaries from day one and let the core condense out of what the second and third agents turn out to need.

Stand up the minimal harness before the second agent exists ([Part 5](agent-harness.md)): model aliases, one named profile, a headless CLI, a mock backend. This looks premature exactly once. It is the precondition for every measurement you will ever make, and retrofitting it under a grown agent costs more than building it under a new one. Create the eval dataset and the metric while writing the spec, before there is anything to tune ([Part 7](evaluation.md)), and instrument from the first run ([Part 6](observability.md)): the first slice's numbers are the baseline every later change is judged against. Give the project its rules file, its CI gates, and its security sweep with the first commit, not as a retrofit ([Part 8](documentation.md), [Part 9](security-supply-chain.md)); a gate added later must fight every habit that grew in its absence.

### Checklist: standing up a project from zero

- [ ] First deliverable specced as a **thin end-to-end slice**, with "how will we know it is right?" answered.
- [ ] **Tier skeleton** laid down; the first agent lives in the task layer, no speculative core.
- [ ] Minimal **harness** up: model aliases, a named profile, a headless CLI, a mock backend.
- [ ] **Eval dataset and metric** exist before tuning starts; the first run is instrumented and becomes the baseline.
- [ ] **Rules file, CI gates, and the security sweep** present from the first commit.

## The four throughlines

Almost every directive in the parts is an application of one of four ideas. Internalize these and the rest follows; when a directive and reality collide, the throughline is how you decide.

### 1. Evidence over intuition: the enemy is false confidence

Treat every non-trivial change to an agent, a prompt, or an extractor as a *hypothesis*: "this will be better." "Better" only means something against a metric, and a metric is only trustworthy if the dataset it runs on was fixed independently of the change under test. Guard against **false** confidence, not the mere absence of it: the naive paths (add patterns until the suite is green, tune a prompt to the one example in front of you, ship the model that impressed in a demo) do not leave you uncertain; they leave you confidently wrong, which is worse, because confidence is when you stop looking. (AI deepens the trap: a model tends to [*agree*](https://arxiv.org/abs/2310.13548) with the premise it is handed, so its readiness to confirm your idea is not evidence for it.) So make the yardstick exist *before* the decision: the test suite before the code, the dataset and the metric before the model or prompt change. [Part 7](evaluation.md) is this idea as a method; [Part 6](observability.md) is its precondition (instrument before you tune); and its discipline leaks into everything else.

### 2. Capture the trail: a decision and its evidence should outlive the moment

Work in the open and write things down: a spec before code, a plan before implementation, a story after a piece of work lands, a recorded result after an experiment. The point is not ceremony. It is that a decision made six months ago, and the evidence that justified it, must be recoverable by someone who was not there, including your future self and the next agent dispatched with zero history. [Part 8](documentation.md) is this idea made concrete; [Part 1](lifecycle.md)'s gates are where the artifacts get produced.

### 3. The reusable core vs. the disposable task layer

Sort everything you build by how much of it carries over to the next task: keep the reusable core sparse and stable, keep the task layer rich and disposable, and let dependencies point only toward the core. The alternative is one workflow's assumptions quietly baked into shared code, where they couple every other consumer and tax every new agent with plumbing it should have inherited. [Part 3](codebase-structure.md) applies this to the module graph, [Part 4](three-layer-model.md) to document knowledge, and [Part 5](agent-harness.md) to the machinery agents share.

### 4. Make the standard executable

Whenever you fix a class of problem, ask what stops it coming back, and prefer the answer that is a gate: encode the standard as an executable check wired into CI and pre-commit, rather than leaving it to memory and review diligence. A rule a human has to remember eventually lapses; a rule the pipeline enforces does not. [Part 1](lifecycle.md) builds the gates into the lifecycle, [Part 8](documentation.md) turns docs hygiene into checkers, and [Part 9](security-supply-chain.md) turns every security fix into one. The periodic audit is the counterpart, catching what no gate was written for.

### Where each throughline lives

The map of throughlines to parts (● a primary home, ○ drawn on):

| Part | Evidence over intuition | Capture the trail | Core vs. task layer | Executable standards |
|---|:-:|:-:|:-:|:-:|
| 1 Lifecycle | ○ | ● | | ● |
| 2 Implementation disciplines | ● | ○ | | ● |
| 3 Codebase structure | | | ● | ○ |
| 4 Three-layer model | ○ | | ● | |
| 5 Agent harness | ○ | | ● | |
| 6 Observability | ● | ○ | | |
| 7 Evaluation | ● | ○ | | |
| 8 Documentation | | ● | | ○ |
| 9 Security | ○ | | | ● |

## How to use this handbook

- **Follow the imperatives.** Each part is written as instructions. Do what they say; the prose next to each one tells you why, so you can adapt it when your case is off-pattern.
- **Use the checklists as the working surface.** Most parts end with a checklist. Paste it into a PR description, an issue, or a review comment and tick it. Where a part describes a procedure (the lifecycle, an eval run, a security sweep), it also gives a step-by-step you can run top to bottom.
- **Treat the reasons as load-bearing, not decoration.** A rule you follow without knowing why is a rule you will misapply at the first edge case. When a directive and reality collide, the *why* is how you decide.
- **Enter anywhere.** The story above is the recommended first read, but every part opens by locating itself in the story and stands alone; you can land on any part cold, mid-task, and use it.
- **Building from scratch?** Greenfield is the story of the *first* change: the "Starting from zero" section above walks the same parts as a build order.

## Where the binding rules live

This handbook explains and connects; it teaches the reasoning. The *binding*, project-specific rules (exact coding standards, review thresholds, the merge checklist, the git workflow) belong in your project's rules file: the file your team and your coding agents both read as authoritative. When this handbook and that file disagree, the rules file wins, and the mismatch is a docs bug to fix (see [Part 8](documentation.md)).
