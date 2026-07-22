# Part 1 — The Development Lifecycle

How a piece of work travels from an idea to merged code: issue → spec → plan → implement → review → merge. The individual practices here (TDD, CI, static analysis, code review, an end-to-end quality gate) are standard professional engineering; what is distinctive is that we run them as *one guided lifecycle* with the human-in-the-loop decisions chosen up front — because we develop *with* agents, and delegation without a spec, a plan, and a verification step is guessing at scale.

## Why: front-load the judgment

Raising the level of abstraction relocates the hard work upward (see [the stance](README.md)). When an agent can write a module from a good plan, the scarce, human-shaped work is *writing the good plan*, *catching the subtle spec violation in review*, and *deciding when it's actually done*. The lifecycle is built to put weight exactly there: the expensive, irreversible moments (what we're building, and shipping it) always get a human, and the mechanical moments (transcribing code from a complete plan, running tests) get delegated to the cheapest agent that can do them.

Task management runs on an issue tracker, and **every piece of work traces to an issue** — there is no scratch `TODO` list. The whole run can be encoded as a single reusable workflow that inlines the sub-steps (brainstorming, plan-writing, subagent-driven implementation, code review, merge) so one issue goes end-to-end in a single guided pass.

## The human-in-the-loop gates, decided up front

Before anything else, the human picks *how involved they want to be* — which optional gates are active for this run. This is a deliberate design choice: the involvement level is decided once, explicitly, not renegotiated at every step. Optional gates include issue selection, approach sign-off, plan approval, per-task checkpoints, review-triage sign-off, and confirming the PR is ready.

**Two gates are always on and can never be disabled:**

- **Spec review** — after the spec is written, work stops until the human approves it. This is the cheapest possible place to catch "we're building the wrong thing."
- **Merge** — before merging, the human does their own review and gives *explicit* approval. "Prepare for merge" is **not** approval; "merge it" is. We never merge without it, and never bump a major version without asking.

When an optional gate is off, the agent takes the autonomous path and *announces the decision it made on your behalf* (which issue, which approach) rather than silently proceeding.

## The phases

### 1. Select the issue

Pick by priority, and — critically — **read the issue's comments too**, not just the body: comments carry the current state of a task, which the original description often no longer reflects. Reflect the state on the issue itself (a status label).

### 2. Brainstorm into a spec

Explore the problem with the user; propose 2–3 approaches with trade-offs, leading with a recommendation. **No code in this phase.** Design for isolation: each unit one clear purpose, a well-defined interface, independently testable. Write the spec to a dated file in the docs tree and commit it, then run a self-review (placeholder scan, internal consistency, scope, ambiguity). **Then stop for spec review** (the always-on gate) and loop until the user approves. After approval, post an issue comment linking the spec.

### 3. Branch from fresh main

Fetch first, then create a descriptively-named branch from *up-to-date* `main` — never a stale local copy. If you started from a stale base, rebase onto the latest `main` immediately. Never start implementation on `main`.

### 4. Write the plan

Assume the implementer has **zero context** for this codebase. Map the file structure first (which files are created/modified, each file's single responsibility). Right-size tasks: a task is the smallest unit that carries its own test cycle and is worth a fresh reviewer's gate. Every step is bite-sized and follows TDD. Every code step contains the **complete** code — no placeholders, no "TBD", no "similar to Task N", no references to undefined types. Placeholders are plan failures, because the implementer can't see what you can. Save the plan to the docs tree, self-review it against the spec (every requirement maps to a task), and update the issue status.

### 5. Implement via subagent-driven development

Execute the plan by dispatching a **fresh implementer subagent per task** — subagents never inherit the session's history, so you construct exactly the context each needs and hand bulk artifacts as files. The per-task review is a load-bearing quality gate, not optional.

**Model selection is explicit and frugal:** use the least powerful model that fits each role, and always name it (an omitted model silently inherits the session's expensive one). Transcribing complete plan-code or a single-file mechanical fix → cheapest tier; multi-file integration → standard tier; reviewers → a mid-tier floor scaled up for risky diffs; the final whole-branch review → the most capable tier.

**After each task, a two-stage review** returns *two* verdicts — **spec compliance** and **code quality** — from a reviewer subagent handed the task brief, the implementer's report, and the diff. Never pre-judge findings for the reviewer; let it raise and adjudicate. Loop (fix subagent → re-review) until both verdicts pass before starting the next task.

> When you launch **any** subagent with shell access, explicitly instruct it to **never pass comment lines (`#…`) to the shell tool** — they can confuse a tool-permission subsystem. For long subagent runs, start a background keep-awake first and kill it when done. And scope a subagent to its brief: a worker that inherits too much context tends to overreach and act on the whole plan instead of its one task.

### 6–9. Draft PR → comprehensive review → finish → merge

Push and open a **draft** PR whose body starts with the issue it closes and carries a Test-plan checklist. Run the comprehensive code review (next section). Finish the branch: verify tests pass, update any affected docs / READMEs / module docstrings, run the end-to-end quality gate if agent behaviour was touched (see below), verify-then-tick the issue's acceptance criteria, and post a release-notes-style comment. Mark ready. Then the always-on **merge** gate: explicit human approval, then merge with a rebase (never squash or merge-commit) and delete the branch, locally and remotely.

## TDD

The bite-sized loop, run for every feature and bugfix:

```
write a failing test → run it (see it fail) → minimal implementation → run it (passes) → commit
```

New code ships **with** unit tests, and adding code must not reduce overall coverage. The deterministic, pure logic of anything you add — parsing, scoring, transformation, id-mapping, verdict application, regex behaviour — must be covered *before the change is done*, because a bug in a scorer's math or an adjudicator's id-mapping silently corrupts every result it touches. I/O-bound edges (network, storage, model calls) may be mocked or left to integration tests. Analysis and tooling scripts are **not** exempt: exercise their pure helpers with unit tests too.

### Coverage is not the value; catching a regression is

A test suite's worth is not its coverage percentage — it is whether it **fails when the code breaks.** A high number produced by tests that assert nothing, only check "no exception was raised," assert against a value the test computed the same way (a tautology), or mock away the very unit under test is a *false* safety net, and a false safety net is worse than an honest low number because people trust it. So two habits matter as much as reach: write the assertion that would actually fail on a plausible regression (not the one that merely executes the line), and mock only true I/O edges, never the logic you are testing.

Measure the right things, too: **branch** coverage, not just line coverage, is the signal (an untested error path is an uncovered branch that reads as covered); and measure coverage **on the diff**, because "don't lower overall coverage" can hide new code that shipped untested behind a large well-covered base. And keep tests **deterministic** — a test that depends on wall-clock, unseeded randomness, ordering, or the network is a flake that erodes trust in the whole suite; inject the clock and the seed rather than reaching for the real ones.

## CI and static analysis

CI runs lint + typecheck + unit tests on every push and pull request. Before committing, run the same checks locally — and run **both** the linter and the formatter, not just one: a linter catches rule violations while a formatter catches layout drift, and they are different checks. Type-checking is part of the gate, not optional. The goal is that CI is a formality because the checks already passed locally.

A gate only counts if it is actually enforced. **A gate that never runs — or runs but isn't required to pass — is worse than no gate, because people trust it.** A check that is skippable by a path filter, marked continue-on-error, only fires on a schedule, or is green but not in branch protection does not block a bad merge. So confirm the gate against the branch-protection rules, not the badge, and make sure "what the contributor guide says CI enforces" matches what the workflows actually require.

## The code-review protocol

The comprehensive whole-branch review is deliberately adversarial and multi-perspective. Several reviewer passes each look a different way — audit the diff against the project's binding rules, shallow-scan for obvious bugs, read git history/blame for context, read prior PRs that touched these files, and check compliance with in-code comments — because a single reviewer is blind to what its one angle doesn't surface. Each finding then gets an independent confidence score against a fixed rubric.

A single, agreed **confidence threshold** decides what must be acted on: findings at or above it are posted as inline PR comments and fixed before merge; easy, non-false-positive findings below it get fixed too. Two rules keep the review honest and in-scope:

- **Report *all* findings**, not only the fixed ones — a full table of score, description, and disposition. This makes visible what was considered and why.
- **Scope discipline:** fix what *this PR* made worse. Do **not** dismiss a finding merely as "pre-existing" (fix small ones, discuss big ones), and do **not** fork the new code away from identical shared/sibling code just to satisfy a finding — that trades a cosmetic win for real divergence; note it as a follow-up instead.

## When to add an end-to-end agent quality gate

Unit tests and type-checking verify code; they cannot catch a regression in an agent's *reasoning* — a prompt tweak that makes a retriever cite worse, or a routing change that quietly degrades answers. Those failures live above the level any assertion in the test suite reaches. So an agent needs a second kind of gate.

- **Why.** An agent's output quality is an emergent property of prompts, tools, model, and context working together. A change can be green on every unit test and still make the agent measurably worse. The gate exists to make that class of regression visible before merge.
- **When.** Add the gate for any change that can alter an agent's behaviour — its prompts/SOPs, its tools, its model or parameters, or the shared code on its import path (the harness, config, or capabilities it actually uses). A change confined to code no agent consumes does **not** need it; ordinary CI still gates that. Deciding this requires knowing which shared modules each agent imports, so make that dependency explicit.
- **How.** Run the agent end-to-end against a small, fixed battery of representative queries and score the output against a quality checklist (deterministic checks, or an LLM-as-judge rubric — see [Part 5](evaluation.md)). Run it on the branch, before merge, with a **cheap** configuration (a mock or lighter backend, see [Part 3](agent-harness.md)) so the gate is affordable enough to run every time. Set a pass bar (a minimum number of checks) and treat a drop as a blocking regression, the same as a failing test. Keep the battery frozen so a run is comparable to the last one.

The general principle: **test each thing at the level where its failures actually appear.** Deterministic code is gated by unit tests; emergent agent behaviour is gated by an end-to-end run against a frozen battery.

## Make the standard executable, and audit periodically

Whenever you fix a class of problem, ask the follow-up question: *what stops it coming back?* A one-time cleanup regresses the moment the next change reintroduces it, because nothing was watching. So the highest-leverage version of almost every fix in this handbook is to **encode the standard as an executable check and wire it into CI (and pre-commit)** rather than leaving it to memory and review diligence. The pattern recurs at every layer: an import-linter contract makes a layering rule ([Part 2](codebase-structure.md)) un-violable; a coverage-plus-diff-coverage gate makes "new code ships with tests" mechanical; a SAST and secret scan, a CVE-and-license gate, and a workflow linter make the safety rules ([Part 8](security-supply-chain.md)) self-enforcing; a cheap eval/smoke gate makes a behavioural bar hold. A rule a human has to remember is a rule that eventually lapses; a rule the pipeline enforces is one that doesn't.

The counterpart to standing gates is the **periodic audit** — a deliberate, evidence-based sweep across the quality dimensions (structure, tests, evals, docs, dependencies, security, CI) to find what has drifted below the standard, because gates catch only the regressions you already thought to encode. The discipline that makes an audit trustworthy is the same one that makes an eval trustworthy ([Part 5](evaluation.md)): every finding cites the artifact or tool output it rests on, tooling that can't run is marked *no-evidence* rather than *pass* (absence of a scanner is not absence of a problem), and a report-only diagnosis comes first, with fixes following one dimension at a time in their own reviewed changes.

## Coding-hygiene rules that surface at review

These are the recurring review findings. Each has a *why*, and each belongs — with your project's exact wording — in the binding rules file the review audits against:

- **No swallowed exceptions.** Never catch-and-ignore or collapse an error into a generic "internal error." Every exception is reported to the consumer with type + message, logged at the right level, or re-raised. The goal is that *the error message alone tells you what went wrong* (auth? timeout? malformed response?) without a debugger. This is the developer-facing half of [observability](observability.md).
- **No backward-compatibility wrappers in a pre-1.0 codebase.** When refactoring, remove the old API and update all callers in the *same* PR — no re-export stubs. Dead compatibility edges are exactly what silts up a clean dependency graph ([Part 2](codebase-structure.md)).
- **No environment-specific values committed.** No personal absolute paths, account/profile names, or hostnames in code, docs, or scripts — use placeholders and say what they resolve to. Fix these retroactively when you touch a file that has them.
- **Describe every settings field.** Configuration fields carry a description, so config schemas are self-documenting.
- **Keep module docstrings current.** Update the docstring whenever a module's purpose or interface changes.
- **Mind provider-specific tool-argument quirks.** Some model/runtime combinations handle nullable or loosely-typed tool arguments poorly; prefer explicit enums or non-null defaults for agent tool parameters.

## Prompt and SOP engineering

An agent's behaviour is defined by its **SOP** (Standard Operating Procedure) — its prompts. Two rules apply specifically to prompts, because a prompt change is a behavioural change that no type-checker will catch:

- **A commit that modifies a prompt must explain *why* it changed**, not just what — the reasoning is the part a future reader needs. Prefer to keep prompt changes in their own commit, separate from code.
- **Analyze SOPs for cognitive load.** A prompt that overloads the model with constraints degrades its reasoning; a periodic analysis of constraint density and redundancy keeps prompts lean, and informs when to decompose a monolithic agent into sub-agents.

## After the merge

Merging isn't the end of the trace. After merging a PR linked to an issue: verify each acceptance-criterion was *actually* implemented before ticking it (never blind-check the boxes), post a release-notes-style comment summarizing what shipped, and set the issue's final status. This is the [capture-the-trail](documentation.md) throughline closing the loop.

## See also

- [README / the stance](README.md) · [Part 2 — Codebase structure](codebase-structure.md) · [Part 4 — Observability](observability.md) (no swallowed exceptions) · [Part 5 — Evaluation](evaluation.md) (the quality gate uses a checklist; deeper decisions use the eval loop) · [Part 7 — Documentation](documentation.md) (specs, plans, and the trail) · [Part 8 — Security & supply chain](security-supply-chain.md) (the safety gates)
