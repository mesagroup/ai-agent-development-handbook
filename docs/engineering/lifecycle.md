# Part 1. The Development Lifecycle

Take every piece of work from idea to merged code along one path: issue → spec → plan → implement → review → merge. The individual practices here (TDD, CI, static analysis, code review, an end-to-end quality gate) are standard professional engineering; what is distinctive is running them as *one guided lifecycle* with the human-in-the-loop decisions chosen up front, because you develop *with* agents, and delegating without a spec, a plan, and a verification step is guessing at scale.

## Front-load the judgment

Raising the level of abstraction relocates the hard work upward (see [the stance](README.md)). When an agent can write a module from a good plan, the scarce, human-shaped work is *writing the good plan*, *catching the subtle spec violation in review*, and *deciding when it's actually done*. Put your weight exactly there: give the expensive, irreversible moments (what you're building, and shipping it) a human every time, and delegate the mechanical moments (transcribing code from a complete plan, running tests) to the cheapest agent that can do them.

Run task management on an issue tracker, and **trace every piece of work to an issue**: keep no scratch `TODO` list. Encode the whole run as a single reusable workflow that inlines the sub-steps (brainstorming, plan-writing, subagent-driven implementation, code review, merge) so one issue goes end-to-end in a single guided pass.

## Decide the human-in-the-loop gates up front

Before anything else, pick *how involved the human wants to be*, which optional gates are active for this run. Decide this once, explicitly; don't renegotiate it at every step. Optional gates include issue selection, approach sign-off, plan approval, per-task checkpoints, review-triage sign-off, and confirming the PR is ready.

**Two gates are always on. Never disable them:**

- **Spec review**: after the spec is written, stop until the human approves it. This is the cheapest possible place to catch "we're building the wrong thing."
- **Merge**: before merging, the human does their own review and gives *explicit* approval. "Prepare for merge" is **not** approval; "merge it" is. Never merge without it, and never bump a major version without asking.

When an optional gate is off, take the autonomous path but *announce the decision you made on the human's behalf* (which issue, which approach), don't silently proceed.

## Step-by-step: one issue, end to end

1. **Select the issue.** Pick by priority, and **read the issue's comments too**, not just the body, comments carry the current state, which the original description often no longer reflects. Reflect the state back on the issue (a status label).
2. **Brainstorm into a spec.** Explore the problem with the user; propose 2–3 approaches with trade-offs, leading with a recommendation. **Write no code in this phase.** Design for isolation: each unit one clear purpose, a well-defined interface, independently testable. Write the spec to a dated file in the docs tree, commit it, then self-review it (placeholder scan, internal consistency, scope, ambiguity). **Then stop for spec review** (always-on) and loop until the user approves. After approval, post an issue comment linking the spec.
3. **Branch from fresh main.** Fetch first, then create a descriptively-named branch from *up-to-date* `main`, never a stale local copy. If you started from a stale base, rebase onto the latest `main` immediately. Never implement on `main`.
4. **Write the plan.** Assume the implementer has **zero context** for this codebase. Map the file structure first (which files are created/modified, each file's single responsibility). Right-size tasks: a task is the smallest unit that carries its own test cycle and is worth a fresh reviewer's gate. Make every step bite-sized and TDD-shaped, and put the **complete** code in every code step, no placeholders, no "TBD", no "similar to Task N", no references to undefined types. A placeholder is a plan failure, because the implementer can't see what you can. Save the plan to the docs tree, self-review it against the spec (every requirement maps to a task), and update the issue status.
5. **Implement via subagent-driven development.** Dispatch a **fresh implementer subagent per task**: subagents never inherit the session's history, so construct exactly the context each needs and hand bulk artifacts as files. Keep the per-task review (below), it is a load-bearing quality gate, not optional.
6. **Draft PR.** Push and open a **draft** PR whose body starts with the issue it closes and carries a Test-plan checklist.
7. **Comprehensive review.** Run the whole-branch review protocol (below).
8. **Finish the branch.** Verify tests pass; update any affected docs / READMEs / module docstrings; run the end-to-end quality gate if agent behaviour was touched (below); verify-then-tick the issue's acceptance criteria; post a release-notes-style comment. Mark the PR ready.
9. **Merge.** The always-on merge gate: get explicit human approval, then merge with a rebase (never squash or merge-commit) and delete the branch, locally and remotely.

**Select the model per role, explicitly and frugally.** Use the least powerful model that fits each role, and always name it (an omitted model silently inherits the session's expensive one). Transcribing complete plan-code or a single-file mechanical fix → cheapest tier; multi-file integration → standard tier; reviewers → a mid-tier floor scaled up for risky diffs; the final whole-branch review → the most capable tier.

**After each task, run a two-stage review.** Hand a reviewer subagent the task brief, the implementer's report, and the diff, and require *two* verdicts, **spec compliance** and **code quality**. Never pre-judge findings for the reviewer; let it raise and adjudicate. Loop (fix subagent → re-review) until both verdicts pass before starting the next task.

> When you launch **any** subagent with shell access, explicitly instruct it to **never pass comment lines (`#…`) to the shell tool**: they can confuse a tool-permission subsystem. For long subagent runs, start a background keep-awake first and kill it when done. And scope each subagent to its brief: a worker that inherits too much context tends to overreach and act on the whole plan instead of its one task.

## TDD

Run this bite-sized loop for every feature and bugfix:

```
write a failing test → run it (see it fail) → minimal implementation → run it (passes) → commit
```

Ship new code **with** unit tests, and don't let adding code reduce overall coverage. Cover the deterministic, pure logic of anything you add, parsing, scoring, transformation, id-mapping, verdict application, regex behaviour, *before the change is done*, because a bug in a scorer's math or an adjudicator's id-mapping silently corrupts every result it touches. You may mock or defer I/O-bound edges (network, storage, model calls) to integration tests. Don't exempt analysis and tooling scripts: exercise their pure helpers with unit tests too.

### Chase caught regressions, not coverage percentage

Judge a test suite by whether it **fails when the code breaks**, not by its coverage number. A high number produced by tests that assert nothing, only check "no exception was raised," assert against a value the test computed the same way (a tautology), or mock away the very unit under test is a *false* safety net, worse than an honest low number, because people trust it. So build two habits: write the assertion that would actually fail on a plausible regression (not the one that merely executes the line), and mock only true I/O edges, never the logic you're testing.

Measure the right things: track **branch** coverage, not just line coverage (an untested error path is an uncovered branch that reads as covered), and measure coverage **on the diff**, because "don't lower overall coverage" can hide new code that shipped untested behind a large well-covered base. Keep tests **deterministic**: a test that depends on wall-clock, unseeded randomness, ordering, or the network is a flake that erodes trust in the whole suite; inject the clock and the seed rather than reaching for the real ones.

## CI and static analysis

Run the same static-quality checks on every push and pull request, and locally before committing, so CI is a formality because the checks already passed. Treat these as **four distinct, complementary gates**, not one blurry "lint" step, because each catches a class the others miss:

- **Format.** Run the formatter, not just the linter: a linter catches rule violations, a formatter catches layout drift, and they are different checks. Normalized layout is also what keeps diffs meaningful and ends whitespace arguments.
- **Lint.** Flag rule violations, likely bugs, and smells the formatter won't see; add domain-specific linters where they pay (an import-linter for the layering rule, see [Part 2](codebase-structure.md)).
- **Type-check, and annotate.** Keep type-checking in the gate, not optional. But remember a type-checker only helps code that is annotated: annotate public interfaces, prefer typed models over loose dicts, and run the checker strict enough to actually fail on an untyped or mistyped path. An un-annotated codebase passes the checker by having nothing to check, a false pass in the same family as a test that asserts nothing.
- **Docstrings.** Treat them as a checked surface too: every public module and symbol carries one, audited for coverage and staleness (see [Part 7](documentation.md)).

These are language-agnostic disciplines; only the toolchain changes. Pick the equivalent for your stack and wire each in the same way (illustrative, not prescriptive):

| Check | Python | TypeScript |
|---|---|---|
| Format | `ruff format` / `black` | `prettier` |
| Lint | `ruff` / `flake8` | `eslint` |
| Type-check | `pyright` / `mypy` | `tsc` (with `strict`) |
| Docstrings | docstring-coverage + staleness audit | JSDoc/TSDoc comments; `eslint-plugin-jsdoc` for coverage; `typedoc` to generate |

A gate only counts if it is actually enforced. **A gate that never runs, or runs but isn't required to pass, is worse than no gate, because people trust it.** A check that is skippable by a path filter, marked continue-on-error, only fires on a schedule, or is green but not in branch protection does not block a bad merge. So confirm the gate against the branch-protection rules, not the badge, and make sure "what the contributor guide says CI enforces" matches what the workflows actually require.

## The code-review protocol

Run the comprehensive whole-branch review as a deliberately adversarial, multi-perspective pass. Give each reviewer pass a different angle, audit the diff against the project's binding rules, shallow-scan for obvious bugs, read git history/blame for context, read prior PRs that touched these files, check compliance with in-code comments, because a single reviewer is blind to what its one angle doesn't surface. Then score each finding independently against a fixed rubric.

Set a single, agreed **confidence threshold** that decides what must be acted on: post findings at or above it as inline PR comments and fix them before merge; fix easy, non-false-positive findings below it too. Keep two rules that hold the review honest and in-scope:

- **Report *all* findings**, not only the fixed ones, a full table of score, description, and disposition. This makes visible what was considered and why.
- **Hold scope discipline:** fix what *this PR* made worse. Do **not** dismiss a finding merely as "pre-existing" (fix small ones, discuss big ones), and do **not** fork the new code away from identical shared/sibling code just to satisfy a finding, that trades a cosmetic win for real divergence; note it as a follow-up instead.

**Reviewer checklist** (one pass per line, most surface different findings):

- [ ] Diff audited against the project's binding rules.
- [ ] Shallow bug scan (off-by-one, nullability, error paths, resource leaks).
- [ ] Git history / blame read for context on why the code is as it was.
- [ ] Prior PRs touching these files read.
- [ ] In-code comments and docstrings still match the code.
- [ ] Every finding scored against the fixed rubric; all findings reported with disposition.

## When to add an end-to-end agent quality gate

Unit tests and type-checking verify code; they cannot catch a regression in an agent's *reasoning*, a prompt tweak that makes a retriever cite worse, or a routing change that quietly degrades answers. Those failures live above the level any assertion in the test suite reaches, so give an agent a second kind of gate.

- **Why.** An agent's output quality is an emergent property of prompts, tools, model, and context working together. A change can be green on every unit test and still make the agent measurably worse. The gate exists to make that class of regression visible before merge.
- **When.** Add the gate for any change that can alter an agent's behaviour, its prompts/SOPs, its tools, its model or parameters, or the shared code on its import path (the harness, config, or capabilities it actually uses). A change confined to code no agent consumes does **not** need it; ordinary CI still gates that. Deciding this requires knowing which shared modules each agent imports, so make that dependency explicit.
- **How.** Run the agent end-to-end against a small, fixed battery of representative queries and score the output against a quality checklist (deterministic checks, or an LLM-as-judge rubric, see [Part 5](evaluation.md)). Run it on the branch, before merge, with a **cheap** configuration (a mock or lighter backend, see [Part 3](agent-harness.md)) so the gate is affordable enough to run every time. Set a pass bar (a minimum number of checks) and treat a drop as a blocking regression, the same as a failing test. Keep the battery frozen so a run is comparable to the last one.

The general principle: **test each thing at the level where its failures actually appear.** Gate deterministic code with unit tests; gate emergent agent behaviour with an end-to-end run against a frozen battery.

## Make the standard executable, and audit periodically

Whenever you fix a class of problem, ask the follow-up: *what stops it coming back?* A one-time cleanup regresses the moment the next change reintroduces it, because nothing was watching. So take the highest-leverage version of almost every fix in this handbook: **encode the standard as an executable check and wire it into CI (and pre-commit)** rather than leaving it to memory and review diligence. The pattern recurs at every layer: an import-linter contract makes a layering rule ([Part 2](codebase-structure.md)) un-violable; a coverage-plus-diff-coverage gate makes "new code ships with tests" mechanical; a SAST and secret scan, a CVE-and-license gate, and a workflow linter make the safety rules ([Part 8](security-supply-chain.md)) self-enforcing; a cheap eval/smoke gate makes a behavioural bar hold. A rule a human has to remember is a rule that eventually lapses; a rule the pipeline enforces is one that doesn't.

Run the counterpart to standing gates too: the **periodic audit**: a deliberate, evidence-based sweep across the quality dimensions (structure, tests, evals, docs, dependencies, security, CI) to find what has drifted below the standard, because gates catch only the regressions you already thought to encode. Hold an audit to the same discipline that makes an eval trustworthy ([Part 5](evaluation.md)): cite the artifact or tool output each finding rests on, mark tooling that can't run as *no-evidence* rather than *pass* (absence of a scanner is not absence of a problem), and produce a report-only diagnosis first, with fixes following one dimension at a time in their own reviewed changes.

## Coding-hygiene rules that surface at review

These are the recurring review findings. Each has a *why*, and each belongs, with your project's exact wording, in the binding rules file the review audits against:

- **Swallow no exceptions.** Never catch-and-ignore or collapse an error into a generic "internal error." Report every exception to the consumer with type + message, log it at the right level, or re-raise it. Aim for *the error message alone tells you what went wrong* (auth? timeout? malformed response?) without a debugger. This is the developer-facing half of [observability](observability.md).
- **Leave no backward-compatibility wrappers in a pre-1.0 codebase.** When refactoring, remove the old API and update all callers in the *same* PR, no re-export stubs. Dead compatibility edges are exactly what silts up a clean dependency graph ([Part 2](codebase-structure.md)).
- **Commit no environment-specific values.** No personal absolute paths, account/profile names, or hostnames in code, docs, or scripts, use placeholders and say what they resolve to. Fix these retroactively when you touch a file that has them.
- **Describe every settings field.** Give configuration fields a description, so config schemas are self-documenting.
- **Keep module docstrings current.** Update the docstring whenever a module's purpose or interface changes.
- **Mind provider-specific tool-argument quirks.** Some model/runtime combinations handle nullable or loosely-typed tool arguments poorly; prefer explicit enums or non-null defaults for agent tool parameters.

## Prompt and SOP engineering

An agent's behaviour is defined by its **SOP** (Standard Operating Procedure): a structured, reusable prompt that specifies how the agent performs a task, so a complex workflow runs the same way every time instead of being re-improvised per run. Give an SOP a fixed shape (keep it in a `.sop.md` file): an **Overview** of what it does and when to use it, its **Parameters** (the `snake_case` inputs, each marked required or optional), and ordered **Steps**, each carrying explicit **Constraints**, with optional **Examples** and **Troubleshooting**. Write the constraints with RFC 2119 keywords (**MUST** / **SHOULD** / **MAY** and their negatives) so the requirement level is unambiguous, and give every negative constraint (**MUST NOT**, **SHOULD NOT**) its *reason* inline, because "don't do X because Y" is what stops the model quietly reintroducing X. That is the same capture-the-why discipline the rest of the handbook runs on, applied to the prompt. (The format is the open [`agent-sop`](https://github.com/strands-agents/agent-sop) specification.)

Apply two rules specifically to prompts, because a prompt change is a behavioural change that no type-checker will catch:

- **Explain *why* a prompt changed in its commit**, not just what, the reasoning is the part a future reader needs. Keep prompt changes in their own commit, separate from code, where you can.
- **Analyze SOPs for cognitive load.** A prompt that overloads the model with constraints degrades its reasoning; run a periodic analysis of constraint density and redundancy to keep prompts lean, and let it inform when to decompose a monolithic agent into sub-agents.

## After the merge

Don't treat merging as the end of the trace. After merging a PR linked to an issue: verify each acceptance-criterion was *actually* implemented before ticking it (never blind-check the boxes), post a release-notes-style comment summarizing what shipped, and set the issue's final status. This is the [capture-the-trail](documentation.md) throughline closing the loop.

## Pre-merge checklist

- [ ] Work traces to an issue; issue comments read and status reflected.
- [ ] Spec written, committed, self-reviewed, and **approved** at the always-on gate.
- [ ] Branch cut from up-to-date `main` (rebased if the base was stale).
- [ ] Plan written with complete, placeholder-free code; every spec requirement maps to a task.
- [ ] Each task implemented by a fresh subagent and passed both review verdicts (spec + quality).
- [ ] New code ships with tests; branch + diff coverage not lowered; tests deterministic.
- [ ] Format, lint, type-check (with annotations), and docstring checks pass locally; CI green and actually required in branch protection.
- [ ] Comprehensive review run; all findings reported with disposition; ≥-threshold findings fixed.
- [ ] End-to-end agent quality gate run if any agent's import path was touched.
- [ ] Docs / READMEs / module docstrings updated in the same PR.
- [ ] Prompt changes carry a *why* in their commit message.
- [ ] Explicit human "merge it" obtained; merged with `--rebase`; branch deleted local + remote.
- [ ] Acceptance criteria verified-then-ticked; release-notes comment posted; issue status set.

## See also

- [README / the stance](README.md) · [Part 2. Codebase structure](codebase-structure.md) · [Part 4. Observability](observability.md) (no swallowed exceptions) · [Part 5. Evaluation](evaluation.md) (the quality gate uses a checklist; deeper decisions use the eval loop) · [Part 7. Documentation](documentation.md) (specs, plans, and the trail) · [Part 8. Security & supply chain](security-supply-chain.md) (the safety gates)
