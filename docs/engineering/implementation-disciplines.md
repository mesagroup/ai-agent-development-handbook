# Part 2. Implementation Disciplines

*The route in [Part 1](lifecycle.md) named the stations; this part is the craft each one demands. Here is how the code gets written, how an agent's behaviour gets written, and the three gates that catch what the writing missed: the mechanical one, the human-shaped one, and the behavioural one. Two throughlines carry it: evidence over intuition (a test or an eval that actually fails when the work is wrong), and standards made executable (a check that enforces the rule so nobody has to remember it).*

The lifecycle placed the human judgment; this part equips the stations a change passes through between a plan and a merge. Each is standard professional engineering, sharpened for developing *with* agents: the discipline is not new, but the failure modes are, because an agent will write a test that asserts nothing or a prompt that quietly drifts unless the craft here holds it to account.

## TDD

Run this bite-sized loop for every feature and bugfix:

```d2 title="The TDD loop"
t: Write a failing test
f: Run it, see it fail
i: Write the minimal code
p: Run it, see it pass
c: Commit
t -> f -> i -> p -> c
c -> t: the next behaviour {style.stroke-dash: 4}
```

Ship new code **with** unit tests, and don't let adding code reduce overall coverage. Cover the deterministic, pure logic of anything you add (parsing, scoring, transformation, id-mapping, verdict application, regex behaviour) *before the change is done*, because a bug in a scorer's math or an adjudicator's id-mapping silently corrupts every result it touches. You may mock or defer I/O-bound edges (network, storage, model calls) to integration tests. Don't exempt analysis and tooling scripts: exercise their pure helpers with unit tests too.

One exception earns its keep: for a pure like-for-like refactor or port, a throwaway battery that pins the *current* behaviour is legitimate scaffolding. Write it to prove the port changed nothing, and delete it once the old and new paths agree; it was a safety harness for the move, not a permanent test of the design.

### Chase caught regressions, not coverage percentage

Judge a test suite by whether it **fails when the code breaks**, not by its coverage number. A high number produced by tests that assert nothing, only check "no exception was raised," assert against a value the test computed the same way (a tautology), or mock away the very unit under test is a *false* safety net: worse than an honest low number, because people trust it. So build two habits: write the assertion that would actually fail on a plausible regression (not the one that merely executes the line), and mock only true I/O edges, never the logic you're testing.

Measure the right things: track **branch** coverage, not just line coverage (an untested error path is an uncovered branch that reads as covered), and measure coverage **on the diff**, because "don't lower overall coverage" can hide new code that shipped untested behind a large well-covered base. Keep tests **deterministic**: a test that depends on wall-clock, unseeded randomness, ordering, or the network is a flake that erodes trust in the whole suite; inject the clock and the seed rather than reaching for the real ones.

### Decide the unit-test coverage floor upfront, and record it where it runs

Unit-test coverage, the proportion of your code that the test suite actually executes, is the number everyone asks for and no handbook can supply: 90% on a thin CRUD service and 90% on a parser mean different things. So this handbook names no percentage, and requires the *decision* instead. State a required floor, state what that floor is measured over, and put both somewhere that executes, the coverage config or the CI gate rather than a wiki page. An unstated floor is not a lenient one, it is an unfalsifiable one: it turns "is 62% good?" into a question nobody can answer, and leaves every later argument about coverage to whoever cares most that day.

The denominator is part of the decision, because a floor without one says nothing: 80% measured over a source tree that quietly excludes the parsers is not 80%. Exclusions are a stated choice, and load-bearing deterministic logic is never a legitimate one. Justify a deliberately low floor rather than leaving it unexplained; a nice-to-have target above the floor is optional, as long as the floor is what CI enforces.

A whole-project floor is the minimum, not the strong form. Pair it with a floor on the changed lines, which the whole-project number cannot substitute for: against a large well-covered base, an entire feature can ship untested before the aggregate number moves.

## Prompt and SOP engineering

For an agent, part of the implementation is not code but prompt, and it deserves the same discipline as code. An agent's behaviour is defined by its **SOP** (Standard Operating Procedure): a structured, reusable prompt that specifies how the agent performs a task, so a complex workflow runs the same way every time instead of being re-improvised per run. Give an SOP a fixed shape (keep it in a `.sop.md` file): an **Overview** of what it does and when to use it, its **Parameters** (the `snake_case` inputs, each marked required or optional), and ordered **Steps**, each carrying explicit **Constraints**, with optional **Examples** and **Troubleshooting**. Write the constraints with [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) keywords (**MUST** / **SHOULD** / **MAY** and their negatives) so the requirement level is unambiguous, and give every negative constraint (**MUST NOT**, **SHOULD NOT**) its *reason* inline, because "don't do X because Y" is what stops the model quietly reintroducing X. That is the same capture-the-why discipline the rest of the handbook runs on, applied to the prompt. (The format is the open [`agent-sop`](https://github.com/strands-agents/agent-sop) specification.)

Say what *done* looks like, too. An SOP that specifies every step but never its **completion criterion** leaves the agent to decide when the work is finished, and an agent with no stop condition keeps polishing, re-checking, and re-searching an answer that was complete several cycles ago. Name the observable state that ends the procedure (the question answered with its sources cited, the required fields all populated), and name the **early exits** as well, the conditions under which the agent should stop and say so rather than keep trying: no result found, a required input missing, a dependency unavailable. A procedure whose failure exit is as explicit as its success exit is one the agent can actually leave. The deterministic backstop still belongs in the harness (a cycle or budget cap, see [Part 5](agent-harness.md)); the criterion here is what lets a well-behaved run stop on its own, long before the cap has to.

Apply two rules specifically to prompts, because a prompt change is a behavioural change that no type-checker will catch:

- **Explain *why* a prompt changed in its commit**, not just what: the reasoning is the part a future reader needs. Keep prompt changes in their own commit, separate from code, where you can.
- **Analyze SOPs for cognitive load.** A prompt that overloads the model with constraints degrades its reasoning; run a periodic analysis of constraint density and redundancy to keep prompts lean, and let it inform when to decompose a monolithic agent into sub-agents.

And keep the division of labour sharp from the other side: reserve an SOP for judgment the model must exercise, the heuristic, context-weighing steps where there is no rule to write. If a constraint on the agent's behaviour *can* be enforced deterministically, enforce it in the harness instead: a schema on the output, a validator in the tool, a guard in the pipeline (see [Part 5](agent-harness.md)); the SOP is for the genuinely non-deterministic part, not for re-encoding what code already guarantees. (The CI section below applies the same division to your own workflow: never spend an agent where a linter suffices.)

## CI and static analysis

With the change written, the first gates it meets are mechanical. Run the same static-quality checks on every push and pull request, and locally before committing, so CI is a formality because the checks already passed. Treat these as **four distinct, complementary gates**, not one blurry "lint" step, because each catches a class the others miss:

- **Format.** Run the formatter, not just the linter: a linter catches rule violations, a formatter catches layout drift, and they are different checks. Normalized layout is also what keeps diffs meaningful and ends whitespace arguments.
- **Lint.** Flag rule violations, likely bugs, and smells the formatter won't see; add domain-specific linters where they pay (an import-linter for the layering rule, see [Part 3](codebase-structure.md)).
- **Type-check, and annotate.** Keep type-checking in the gate, not optional. But remember a type-checker only helps code that is annotated: annotate public interfaces, prefer typed models over loose dicts, and run the checker strict enough to actually fail on an untyped or mistyped path. An un-annotated codebase passes the checker by having nothing to check: a false pass in the same family as a test that asserts nothing.
- **Docstrings.** Treat them as a checked surface too: every public module and symbol carries one, audited for coverage and staleness (see [Part 8](documentation.md)).

These are language-agnostic disciplines; only the toolchain changes. Pick the equivalent for your stack and wire each in the same way (illustrative, not prescriptive):

| Check | Python | TypeScript |
|---|---|---|
| Format | `ruff format` / `black` | `prettier` |
| Lint | `ruff` / `flake8` | `eslint` |
| Type-check | `pyright` / `mypy` | `tsc` (with `strict`) |
| Docstrings | docstring-coverage + staleness audit | JSDoc/TSDoc comments; `eslint-plugin-jsdoc` for coverage; `typedoc` to generate |

A gate only counts if it is actually enforced. **A gate that never runs, or runs but isn't required to pass, is worse than no gate, because people trust it.** A check that is skippable by a path filter, marked continue-on-error, only fires on a schedule, or is green but not in branch protection does not block a bad merge. So confirm the gate against the branch-protection rules, not the badge, and make sure "what the contributor guide says CI enforces" matches what the workflows actually require.

Keep the labour on the right side of the line: never spend an agent on what a linter, formatter, or type-checker already enforces deterministically. A deterministic tool is faster, cheaper, and gives the same verdict every time on the job it was built for; an agent pointed at a linter's task is strictly worse at it.

## The code-review protocol

Before the mechanics, the purpose. When agents write most of the code, review is the moment a human is *forced* to understand what ships, which makes it the real guard against a codebase no one on the team actually comprehends. So review what the change *expresses*: its intent, its design, whether it fits the system and solves the right problem. How the code is *written* (formatting, naming, layout) is the CI gates' job, above, not a reviewer's. A review whose understanding one person silently absorbs has failed its primary purpose even when it catches a bug, because the point was to spread the understanding, not merely to filter defects.

The mechanical gates pass; what they cannot judge, the review does. Run the comprehensive whole-branch review as a deliberately adversarial, multi-perspective pass. Give each reviewer pass a different angle (audit the diff against the project's binding rules; shallow-scan for obvious bugs; read git history and blame for context; read prior PRs that touched these files; check compliance with in-code comments), because a single reviewer is blind to what its one angle doesn't surface. Then score each finding independently against a fixed rubric whose points are named and described rather than left as a bare number ([Part 7](evaluation.md)).

Set a single, agreed **confidence threshold** that decides what must be acted on, naming one of the rubric's own points rather than a value between two of them, so the cut inherits the trigger its label already describes: post findings at or above it as inline PR comments and fix them before merge; fix easy, non-false-positive findings below it too. Keep two rules that hold the review honest and in-scope:

- **Report *all* findings**, not only the fixed ones: a full table of score, description, and disposition. This makes visible what was considered and why.
- **Hold scope discipline:** fix what *this PR* made worse. Do **not** dismiss a finding merely as "pre-existing" (fix small ones, discuss big ones), and do **not** fork the new code away from identical shared/sibling code just to satisfy a finding: that trades a cosmetic win for real divergence; note it as a follow-up instead.

**Reviewer checklist** (one pass per line, most surface different findings):

- [ ] Diff audited against the project's binding rules.
- [ ] Shallow bug scan (off-by-one, nullability, error paths, resource leaks).
- [ ] Git history / blame read for context on why the code is as it was.
- [ ] Prior PRs touching these files read.
- [ ] In-code comments and docstrings still match the code.
- [ ] Every finding scored against the fixed rubric; all findings reported with disposition.

## Coding-hygiene rules that surface at review

These are the recurring review findings. Each has a *why*, and each belongs, with your project's exact wording, in the binding rules file the review audits against:

- **Swallow no exceptions.** Never catch-and-ignore or collapse an error into a generic "internal error." Report every exception to the consumer with type + message, log it at the right level, or re-raise it. Aim for *the error message alone tells you what went wrong* (auth? timeout? malformed response?) without a debugger. This is the developer-facing half of [observability](observability.md).
- **Leave no backward-compatibility wrappers in a pre-1.0 codebase.** When refactoring, remove the old API and update all callers in the *same* PR, no re-export stubs. Dead compatibility edges are exactly what silts up a clean dependency graph ([Part 3](codebase-structure.md)).
- **Commit no environment-specific values.** No personal absolute paths, account/profile names, or hostnames in code, docs, or scripts, use placeholders and say what they resolve to. Fix these retroactively when you touch a file that has them.
- **Describe every settings field.** Give configuration fields a description, so config schemas are self-documenting.
- **Keep module docstrings current.** Update the docstring whenever a module's purpose or interface changes.
- **Mind provider-specific tool-argument quirks.** Some model/runtime combinations handle nullable or loosely-typed tool arguments poorly; prefer explicit enums or non-null defaults for agent tool parameters.

## When to add an end-to-end agent quality gate

Unit tests and type-checking verify code; they cannot catch a regression in an agent's *reasoning*, a prompt tweak that makes a retriever cite worse, or a routing change that quietly degrades answers. Those failures live above the level any assertion in the test suite reaches, so give an agent a second kind of gate.

- **Why.** An agent's output quality is an emergent property of prompts, tools, model, and context working together. A change can be green on every unit test and still make the agent measurably worse. The gate exists to make that class of regression visible before merge.
- **When.** Add the gate for any change that can alter an agent's behaviour, its prompts/SOPs, its tools, its model or parameters, or the shared code on its import path (the harness, config, or capabilities it actually uses). A change confined to code no agent consumes does **not** need it; ordinary CI still gates that. Deciding this requires knowing which shared modules each agent imports, so make that dependency explicit.
- **How.** Run the agent end-to-end against a small, fixed battery of representative queries and score the output against a quality checklist (deterministic checks, or an LLM-as-judge rubric, see [Part 7](evaluation.md)). Run it on the branch, before merge, with a **cheap** configuration (a mock or lighter backend, see [Part 5](agent-harness.md)) so the gate is affordable enough to run every time. Set a pass bar (a minimum number of checks) and treat a drop as a blocking regression, the same as a failing test. Keep the battery frozen so a run is comparable to the last one.

The general principle: **test each thing at the level where its failures actually appear.** Gate deterministic code with unit tests; gate emergent agent behaviour with an end-to-end run against a frozen battery.

*Next: every discipline here assumes a codebase shaped to absorb the change cleanly. That shape, and the single invariant that holds it in place, is [Part 3. Codebase structure](codebase-structure.md).*

## See also

- [Part 1. Development lifecycle](lifecycle.md), the route these disciplines equip.
- [Part 7. Evaluation](evaluation.md), the eval loop the end-to-end quality gate draws on.
- [Part 6. Observability](observability.md), the developer-facing half of "no swallowed exceptions".
