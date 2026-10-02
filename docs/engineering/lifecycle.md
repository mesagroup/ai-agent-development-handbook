# Part 1. The Development Lifecycle

*Here the story begins: an idea on its way to becoming a merged, verified change. This part is the handbook's spine, the path work travels by default, with the human judgment placed at the moments where it pays most. Two throughlines run through it end to end: the trail you capture at every step, and the standards you make executable so that the path holds without heroics.*

Take every piece of work from idea to merged code along one path: issue → spec → plan → implement → review → merge. The individual practices it runs on (TDD, CI, static analysis, code review, an end-to-end quality gate, each detailed in [Part 2](implementation-disciplines.md)) are standard professional engineering; what is distinctive is running them as *one guided lifecycle* with the human-in-the-loop decisions chosen up front, because you develop *with* agents, and delegating without a spec, a plan, and a verification step is guessing at scale.

## Front-load the judgment

Raising the level of abstraction relocates the hard work upward (see [the stance](README.md)). When an agent can write a module from a good plan, the scarce, human-shaped work is *writing the good plan*, *catching the subtle spec violation in review*, and *deciding when it's actually done*. Put your weight exactly there: give the expensive, irreversible moments (what you're building, and shipping it) a human every time, and delegate the mechanical moments (transcribing code from a complete plan, running tests) to the cheapest agent that can do them.

Run task management on an issue tracker, and **trace every piece of work to an issue**: keep no scratch `TODO` list. Encode the whole run as a single reusable workflow that inlines the sub-steps (brainstorming, plan-writing, subagent-driven implementation, code review, merge) so one issue goes end-to-end in a single guided pass.

## Keep batches small and the flow fast

Where the human's judgment goes is one lever; the *size* of what you hand off is another, set before any gate fires. An agent multiplies the code you can produce, which quietly revives the oldest anti-pattern there is: the giant branch nobody can review. A change too large to hold in one reading defeats the review protocol ([Part 2](implementation-disciplines.md)), because a reviewer forced to skim approves what they cannot actually see. Counter it at the source: scope each issue narrowly enough that its diff stays reviewable. A hard cap on diff size is a legitimate backstop, but only a backstop; the mechanism is scoping the work small in the first place.

Then measure the whole distance, not the convenient part. Optimizing commit-to-deploy while idea-to-production stays slow moves a number without moving the outcome. The [four DORA measures](https://dora.dev/guides/dora-metrics/) (deployment frequency, lead time for changes, change-failure rate, and time to restore) are a useful shared vocabulary for that whole-distance view. The durable evidence that small batches, loosely coupled architecture, and lightweight change approval predict delivery performance is in [*Accelerate*](https://itrevolution.com/product/accelerate/) (Forsgren, Humble, Kim): reach for the book, not a screenshotted chart whose numbers rot.

## Decide the human-in-the-loop gates up front

Before anything else, pick *how involved the human wants to be*, which optional gates are active for this run. Decide this once, explicitly; don't renegotiate it at every step. Optional gates include issue selection, approach sign-off, plan approval, per-task checkpoints, review-triage sign-off, and confirming the PR is ready.

**Two gates are always on. Never disable them:**

- **Spec review**: after the spec is written, stop until the human approves it. This is the cheapest possible place to catch "we're building the wrong thing."
- **Merge**: before merging, the human does their own review and gives *explicit* approval. "Prepare for merge" is **not** approval; "merge it" is. Never merge without it, and never bump a major version without asking.

When an optional gate is off, take the autonomous path but *announce the decision you made on the human's behalf* (which issue, which approach); don't silently proceed.

## Scale involvement to criticality

Not every change deserves the same human attention, and spending it uniformly starves the risky change to over-supervise the trivial one. Scale involvement along two independent axes. The first is *how present the human is*: **in-the-loop** (co-design and approve each step), **on-the-loop** (let the agent run, monitor and audit the result, intervene on a signal), or **out-of-the-loop** (run behind guardrails and sample after the fact). The second is *how much the code matters*: a **core differentiator** (the logic that is the reason the product exists), **supporting** code, or a **commodity** integration any equivalent could replace.

Match one to the other. Core-differentiator code gets in-the-loop treatment, co-design and a second reviewer, because a subtle error there is expensive and the understanding must not live in one head. Supporting code runs on-the-loop; a commodity integration behind a good guardrail can run out-of-the-loop. This does *not* mean hand-writing the core yourself: even core-domain code is agent-assisted here (see [the stance](README.md)); what scales up with criticality is the *oversight and review*, not who types.

Two boundaries keep this from becoming a licence to cut corners. First, the two always-on bookend gates (spec review and the merge gate) never scale off, whatever the criticality: only the *optional* gates and the depth of implementation involvement move. Second, criticality is a different axis from reuse: a commodity utility can sit in the reusable core, and a core differentiator can live in a single agent's task layer ([Part 3](codebase-structure.md)). Classify a change on both; then place your attention accordingly.

## Step-by-step: one issue, end to end

1. **Select the issue.** Pick by priority, and **read the issue's comments too**, not just the body: comments carry the current state, which the original description often no longer reflects. Reflect the state back on the issue (a status label).
2. **Brainstorm into a spec.** Explore the problem with the user; propose 2–3 approaches with trade-offs, leading with a recommendation. **Write no code in this phase.** Design for isolation: each unit one clear purpose, a well-defined interface, independently testable. Write the spec to a dated file in the docs tree, commit it, then self-review it (placeholder scan, internal consistency, scope, ambiguity). **Then stop for spec review** (always-on) and loop until the user approves. After approval, post an issue comment linking the spec. Spec quality is bounded less by solo authoring skill than by how well context is extracted across product, engineering, and domain experts, so pull that knowledge out collaboratively: techniques like [Event Storming](https://www.eventstorming.com/), [event modeling](https://eventmodeling.org/), or a lightweight architecture canvas surface it without importing enterprise DDD wholesale. Model live and low-fidelity, because the shared understanding forms in the room; handing the whole job to an agent to "write the doc" produces an artifact without the alignment that was the point. Where the change is architectural, use the architecture doc *forward*: sketch the post-change version and read the blast radius off it before committing to the approach.
3. **Branch from fresh main.** Fetch first, then create a descriptively-named branch from *up-to-date* `main`, never a stale local copy. If you started from a stale base, rebase onto the latest `main` immediately. Never implement on `main`.
4. **Write the plan.** Assume the implementer has **zero context** for this codebase. Map the file structure first (which files are created/modified, each file's single responsibility). Right-size tasks: a task is the smallest unit that carries its own test cycle and is worth a fresh reviewer's gate. Make every step bite-sized and TDD-shaped, and put the **complete** code in every code step: no placeholders, no "TBD", no "similar to Task N", no references to undefined types. A placeholder is a plan failure, because the implementer can't see what you can. Save the plan to the docs tree, self-review it against the spec (every requirement maps to a task), and update the issue status.
5. **Implement via subagent-driven development.** Dispatch a **fresh implementer subagent per task**: subagents never inherit the session's history, so construct exactly the context each needs and hand bulk artifacts as files. Keep the per-task review (below): it is a load-bearing quality gate, not optional.
6. **Draft PR.** Push and open a **draft** PR whose body starts with the issue it closes and carries a Test-plan checklist.
7. **Comprehensive review.** Run the whole-branch review protocol ([Part 2](implementation-disciplines.md)).
8. **Finish the branch.** Verify tests pass; update any affected docs / READMEs / module docstrings; run the end-to-end quality gate if agent behaviour was touched ([Part 2](implementation-disciplines.md)); verify-then-tick the issue's acceptance criteria; post a release-notes-style comment. Mark the PR ready.
9. **Merge.** The always-on merge gate: get explicit human approval, then merge with a rebase (never squash or merge-commit) and delete the branch, locally and remotely.

**Select the model per role, explicitly and frugally.** Use the least powerful model that fits each role, and always name it (an omitted model silently inherits the session's expensive one). Transcribing complete plan-code or a single-file mechanical fix → cheapest tier; multi-file integration → standard tier; reviewers → a mid-tier floor scaled up for risky diffs; the final whole-branch review → the most capable tier.

**After each task, run a two-stage review.** Hand a reviewer subagent the task brief, the implementer's report, and the diff, and require *two* verdicts: **spec compliance** and **code quality**. Never pre-judge findings for the reviewer; let it raise and adjudicate. Loop (fix subagent → re-review) until both verdicts pass before starting the next task.

> Scope each subagent to its brief: a worker that inherits too much context tends to overreach and act on the whole plan instead of its one task. Any standing instruction of this kind belongs in the dispatching prompt, since a subagent inherits none of the conventions you are working under.

That is the route. The craft each station demands (how the code and the agent's behaviour get written, and the mechanical, human-shaped, and behavioural gates that catch what the writing missed) is the subject of [Part 2](implementation-disciplines.md). What remains here is the shape work takes when it does not fit that route at all, and then the rest of the trace: what to do after the merge, and the one meta-practice that keeps every gate from quietly lapsing.

## Fan work out to parallel agents, and merge it honestly

The route above is sequential: one implementer at a time, one review after each. Some work is not shaped like that - a corpus to judge, a matrix to sweep, a set of documents to classify - and there the unit is a slice rather than a step, with one agent per slice running at once. The pattern is worth having, because it turns a long serial pass into a short parallel one and each agent gets a context holding only its own slice. What it costs is that the failures it introduces merge cleanly and look like success, which is what the four rules below are for. (What redundancy across agents does *not* buy you is [Part 7](evaluation.md)'s subject: agreement among readers of one input is not corroboration.)

- **Reads fan out; writes do not.** Parallelise agents that read and judge; serialise anything that mutates shared state. Parallel writers collide on the same files and the loser's work disappears with no error to notice, so a fan-out whose slices each write is not a faster pipeline, it is a race with a plausible-looking result. This is the rule that decides whether a fan-out is the right tool at all: where the unit of work is a write, it is not.
- **A merged multi-agent artifact needs a mechanical coverage assertion before anything reads it.** Exactly one verdict per unit: the distinct count matches the expected count, nothing is missing, nothing was judged twice, and conflicts and gaps go to a single cleanup pass rather than being settled slice by slice. The assertion is cheap and reusable, and it is the only guard against the failure nobody can see by reading - a merged artifact that looks complete. Every number computed over it inherits whatever it got wrong, which is why the assertion runs before the first consumer rather than after a result looks odd.
- **A per-slice agent cannot decide a whole-subject property, and will decide anyway.** Totals, cycles, ratios, "report this once", "is this the only one" - each needs an agent that sees the whole subject, and an agent holding one slice answers from the slice with no sign in its output that it did. Partition the *questions* along that line before partitioning the work: per-slice questions to the slices, whole-subject questions to one agent holding the whole thing.
- **A rubric a sweep applies is an artifact that grows during the sweep.** Rulings get made mid-run - what counts as a member, how to treat the case nobody anticipated - and answering one to the batch that raised it leaves every earlier slice judged under a thinner rulebook. Keep one rubric file, lift every ruling into it as it is made, and plan the final whole-corpus pass from the start, rather than deciding at the end whether the early slices need re-reading.

## After the merge

Don't treat merging as the end of the trace. After merging a PR linked to an issue: verify each acceptance-criterion was *actually* implemented before ticking it (never blind-check the boxes), post a release-notes-style comment summarizing what shipped, and set the issue's final status. This is the [capture-the-trail](documentation.md) throughline closing the loop.

## Make the standard executable, and audit periodically

One meta-practice closes the lifecycle, because it decides whether every gate above keeps existing. Whenever you fix a class of problem, ask the follow-up: *what stops it coming back?* A one-time cleanup regresses the moment the next change reintroduces it, because nothing was watching. So take the highest-leverage version of almost every fix in this handbook: **encode the standard as an executable check and wire it into CI (and pre-commit)** rather than leaving it to memory and review diligence. The pattern recurs at every layer: an import-linter contract makes a layering rule ([Part 3](codebase-structure.md)) un-violable; a coverage-plus-diff-coverage gate makes "new code ships with tests" mechanical; a SAST and secret scan, a CVE-and-license gate, and a workflow linter make the safety rules ([Part 9](security-supply-chain.md)) self-enforcing; a cheap eval/smoke gate makes a behavioural bar hold. A rule a human has to remember is a rule that eventually lapses; a rule the pipeline enforces is one that doesn't.

Run the counterpart to standing gates too, the **periodic audit**: a deliberate, evidence-based sweep across the quality dimensions (structure, tests, evals, docs, dependencies, security, CI) to find what has drifted below the standard, because gates catch only the regressions you already thought to encode. Hold an audit to the same discipline that makes an eval trustworthy ([Part 7](evaluation.md)): cite the artifact or tool output each finding rests on, mark tooling that can't run as *no-evidence* rather than *pass* (absence of a scanner is not absence of a problem), and produce a report-only diagnosis first, with fixes following one dimension at a time in their own reviewed changes.

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
- [ ] Involvement depth matched the change's criticality; the bookend gates stayed on regardless.
- [ ] Acceptance criteria verified-then-ticked; release-notes comment posted; issue status set.

*Next: the route is laid; now the craft each station on it demands. [Part 2. Implementation disciplines](implementation-disciplines.md).*

## See also

- [Part 2. Implementation disciplines](implementation-disciplines.md).
- [Part 3. Codebase structure](codebase-structure.md).
- [Part 6. Observability](observability.md), no swallowed exceptions.
- [Part 7. Evaluation](evaluation.md), the quality gate uses a checklist; deeper decisions use the eval loop.
- [Part 8. Documentation](documentation.md), specs, plans, and the trail.
- [Part 9. Security & supply chain](security-supply-chain.md), the safety gates.
