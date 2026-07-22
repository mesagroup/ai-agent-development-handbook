# Part 1 — The Development Lifecycle

How a piece of work travels from an idea to merged code: issue → spec → plan → implement → review → merge. The individual practices here (TDD, CI, static analysis, code review, the smoke test) are standard professional engineering; what is distinctive is that we run them as *one guided lifecycle* with the human-in-the-loop decisions chosen up front — because we develop *with* agents, and delegation without a spec, a plan, and a verification step is guessing at scale.

## Why: front-load the judgment

Raising the level of abstraction relocates the hard work upward (see [the stance](README.md)). When an agent can write a module from a good plan, the scarce, human-shaped work is *writing the good plan*, *catching the subtle spec violation in review*, and *deciding when it's actually done*. The lifecycle is built to put weight exactly there: the expensive, irreversible moments (what we're building, and shipping it) always get a human, and the mechanical moments (transcribing code from a complete plan, running tests) get delegated to the cheapest agent that can do them.

Task management runs on **GitHub Issues** (repo `lidia-tech/lidia-agents`). Every piece of work traces to an issue; there is no `TODO.md`. The whole run is embodied in the `issue-to-merge` skill, which inlines the sub-workflows (brainstorming, writing-plans, subagent-driven development, code review, merge) so a single issue goes end-to-end in one guided pass.

## The human-in-the-loop gates, decided up front

Before anything else, the human picks *how involved they want to be* — which optional gates are active for this run. This is a deliberate design choice: the involvement level is a decision made once, explicitly, not negotiated at every step. Optional gates include issue selection, approach sign-off, plan approval, per-task checkpoints, review-triage sign-off, and PR-ready confirmation.

**Two gates are always on and can never be disabled:**

- **Spec review** — after the spec is written, work stops until the human approves it. This is the cheapest possible place to catch "we're building the wrong thing."
- **Merge** — before merging, the human does their own review and gives *explicit* approval. "Prepare for merge" is **not** approval; "merge it" is. We never merge without it, and never bump a major version (1.0+) without asking.

When an optional gate is off, the agent takes the autonomous path and *announces the decision it made on your behalf* (which issue, which approach) rather than silently proceeding.

## The phases

### 1. Select the issue

`gh issue list`, pick by priority, and — critically — **read the issue's comments too**, not just the body: comments carry the current state of a task, which the original description often no longer reflects. Set the status label (`status:exploring`).

### 2. Brainstorm into a spec

Explore the problem with the user; propose 2–3 approaches with trade-offs, leading with a recommendation. **No code in this phase.** Design for isolation: each unit one clear purpose, a well-defined interface, independently testable. Write the spec to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` and commit it, then run a self-review (placeholder scan, internal consistency, scope, ambiguity). **Then stop for spec review** (the always-on gate) and loop until the user approves. After approval, post an issue comment linking the spec.

### 3. Branch from fresh `origin/main`

`git fetch origin main`, then create `<number>-short-description` from *up-to-date* `origin/main` — never a stale local `main`. If you started from a stale base (or a worktree/detached HEAD behind `origin/main`), rebase onto `origin/main` immediately. Never start implementation on `main`.

### 4. Write the plan

Assume the implementer has **zero context** for this codebase. Map the file structure first (which files are created/modified, each file's single responsibility). Right-size tasks: a task is the smallest unit that carries its own test cycle and is worth a fresh reviewer's gate. Every step is bite-sized (2–5 min) and follows TDD. Every code step contains the **complete** code — no placeholders, no "TBD", no "similar to Task N", no references to undefined types. Placeholders are plan failures, because the implementer can't see what you can. Save to `docs/superpowers/plans/YYYY-MM-DD-<feature>.md`, self-review against the spec (every requirement maps to a task), and set `status:in-progress`.

### 5. Implement via subagent-driven development

Execute the plan by dispatching a **fresh implementer subagent per task** — subagents never inherit the session's history, so you construct exactly the context each needs and hand bulk artifacts as files. This is the default execution mode in this repo; it is what we've shipped multiple epics with, and the per-task review is a load-bearing quality gate, not optional.

**Model selection is explicit and frugal:** use the least powerful model that fits each role, and always name it (an omitted model silently inherits the session's expensive one). Transcribing complete plan-code or a single-file mechanical fix → cheapest tier; multi-file integration → standard tier; reviewers → mid-tier floor scaled up for risky diffs; the final whole-branch review → most capable tier.

**After each task, a two-stage review** returns *two* verdicts — **spec compliance** and **code quality** — from a reviewer subagent handed the task brief, the implementer's report, and the diff. Never pre-judge findings for the reviewer; let it raise and adjudicate. Loop (fix subagent → re-review) until both verdicts pass before starting the next task.

> When you launch **any** subagent with Bash access, explicitly instruct it to **never pass bash comment lines (`#…`) to the Bash tool** — they confuse the tool-permission subsystem. For long subagent runs, start a background keep-awake first and kill it when done.

### 6–9. Draft PR → comprehensive review → finish → merge

Push and open a **draft** PR whose body starts with `Closes #N` and carries a Test-plan checklist. Run the comprehensive code review (next section). Finish the branch: verify tests pass, update any affected docs / READMEs / module docstrings, run the smoke test if an agent import path was touched, verify-then-tick the issue's acceptance criteria, and post a release-notes-style comment. Mark ready. Then the always-on **merge** gate: explicit human approval, then merge with `--rebase` (never squash or merge-commit) and delete the branch, locally and remotely.

## TDD

The bite-sized loop, run for every feature and bugfix:

```
write a failing test → run it (see it fail) → minimal implementation → run it (passes) → commit
```

New code ships **with** unit tests, and adding code must not reduce overall coverage. The deterministic, pure logic of anything you add — parsing, scoring, transformation, id-mapping, verdict application, regex behaviour — must be covered *before the change is done*, because a bug in a scorer's math or an adjudicator's id-mapping silently corrupts every result it touches. I/O-bound edges (S3, network, LLM calls) may be mocked or left to integration tests. Analysis scripts under `scripts/` are **not** exempt: they are unit-tested by loading them with `importlib` and exercising their pure helpers.

## CI and static analysis

CI (`.github/workflows/ci.yml`) runs lint + typecheck + unit tests on every push/PR to `main`. Before committing, **always run both**:

```
uv run ruff check .          # lint
uv run ruff format --check .  # formatting
uv run pyright                # type check (eval/ excluded)
uv run pytest tests/          # unit tests (integration excluded by default)
```

`ruff check` catches lint errors; `ruff format --check` catches formatting. They are different checks — running only one is not sufficient, and CI runs both.

## The code-review protocol

The comprehensive whole-branch review is deliberately adversarial and multi-perspective. Five parallel finder agents each look a different way — audit the diff against the relevant `CLAUDE.md` files, shallow-scan for obvious bugs, read git history/blame for context, read prior PRs that touched these files, and check compliance with in-code comments — because a single reviewer is blind to what its one angle doesn't surface. Each finding then gets an independent 0–100 **confidence score** against a fixed rubric.

The posting/fix threshold is **60**: findings ≥ 60 are posted as inline PR comments and fixed before merge. Lower-scored findings that aren't false positives and are easy fixes get fixed too. Two rules keep the review honest and in-scope:

- **Report *all* findings**, not only the fixed ones — a full table of score, description, and disposition (posted/fixed, or not-posted with reason). This makes visible what was considered and why.
- **Scope discipline:** fix what *this PR* made worse. Do **not** dismiss a finding merely as "pre-existing" (fix small ones, discuss big ones), and do **not** fork the new code away from identical shared/sibling code just to satisfy a finding — that trades a cosmetic win for real divergence; note it as a follow-up instead.

The authoritative thresholds and scope rules live in the **Code Review** section of [`CLAUDE.md`](../../CLAUDE.md).

## The smoke test — the *agent* quality gate

Unit tests and typecheck cannot catch a regression in an agent's *reasoning* — a prompt change that makes the retriever cite worse, say. The **Smoke Test** workflow (`smoke-test.yml`, manual dispatch) is that gate: it runs the legal-search agent end-to-end against a quality checklist. Trigger it, with the PR number, before merging any PR that touches an agent's import path — anything under `agents/`, or the shared `core/` / `config/` / `capabilities/` / `services/` / `meta/` that an agent actually imports — and wait for it to pass. Use `web_search=mock` for a cheap gate. Changes confined to a capability no agent consumes (e.g. a document-model or reference-extraction change no current agent imports) don't need it; CI's lint + typecheck + unit tests still gate those.

## Coding-hygiene rules that surface at review

These are the recurring review findings, all codified in the **Coding Rules** of [`CLAUDE.md`](../../CLAUDE.md). Each has a *why*:

- **No swallowed exceptions.** Never `except Exception: pass` or a generic "internal error." Every exception is reported to the consumer with type + message, logged at the right level, or re-raised. The goal is that *the error message alone tells you what went wrong* (auth? timeout? malformed response?) without a debugger. This is the developer-facing half of [observability](observability.md).
- **No backward-compatibility wrappers.** This is an R&D alpha (0.x): when refactoring, remove the old API and update all callers in the *same* PR. No re-export stubs. The codebase is small enough, and dead compatibility edges are exactly what silts up a clean dependency graph ([Part 2](codebase-structure.md)).
- **No env-specific values committed.** No personal absolute paths, AWS profile names, or hostnames in code, docs, or scripts — use placeholders (`<your-aws-profile>`) and say what they resolve to. Fix these retroactively when you touch a file that has them.
- **Describe every settings field.** Pydantic `BaseSettings` fields carry `Field(description=...)`, so config schemas are self-documenting.
- **Keep module docstrings current.** Update the docstring whenever a module's purpose or interface changes.
- **Avoid nullable tool params.** Claude-on-Bedrock via Strands handles `X | None` tool arguments poorly; new agent tools use `Literal` enums or non-null defaults instead.

## Prompt and SOP engineering

An agent's behaviour is defined by its **SOP** (Standard Operating Procedure) — the prompts under each service/agent's `prompts/`. Two rules apply specifically to prompts, because a prompt change is a behavioural change that no type-checker will catch:

- **A commit that modifies an LLM/agentic prompt must explain *why* it changed**, not just what — the reasoning is the part a future reader needs. Prefer to keep prompt changes in their own commit, separate from code.
- **We analyze SOPs for cognitive load.** A prompt that overloads the model with constraints degrades its reasoning; the SOP analyses (e.g. [legal-search SOP analysis](../agents/legal-search/sop-analysis.md) and the [per-component analyses](../agents/legal-search/prompts/)) exist to keep constraint density and redundancy in check, and inform when to decompose a monolithic agent into sub-agents.

## After the merge

Merging isn't the end of the trace. After merging a PR linked to an issue: verify each acceptance-criterion was *actually* implemented before ticking it (never blind-check the boxes), post a release-notes-style comment summarizing what shipped, and set `status:done`. This is the [capture-the-trail](documentation.md) throughline closing the loop.

## See also

- [README / the stance](README.md) · [Part 2 — Codebase structure](codebase-structure.md) · [Part 4 — Observability](observability.md) (no swallowed exceptions) · [Part 5 — Evaluation](evaluation.md) (the smoke test is a quality gate; deeper decisions use the eval loop) · [Part 7 — Documentation](documentation.md) (specs, plans, and the trail)
- [`CLAUDE.md`](../../CLAUDE.md) — the authoritative coding rules, review thresholds, PR/merge checklist, and git workflow
- [The document_model CLI](../architecture/capabilities/document_model/) and [agent configuration](../agents/legal-search/configuration.md) for concrete command examples
