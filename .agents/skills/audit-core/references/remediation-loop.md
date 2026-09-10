# The loop, steps 3-6: remediation

Read this when the mode is fix, and not otherwise. `SKILL.md`'s loop runs steps 0 to 2 - scope and mode, evidence, the findings matrix - and stops there when the mode is report-only. These are the four steps after that stop: plan the remediation, apply the fixes, review the whole branch, finish.

The step numbers continue `SKILL.md`'s, so step 3 below follows step 2 there. A report-only run reaches none of it, which is why it is not in the file every run loads.

3. **Plan remediation.** Turn the fail/violation rows into a work list. Write a plan file under the project's plans location (fall back to `docs/plans/`).
   - **One task per coherent fix** (or tightly-coupled group), each independently verifiable.
   - **Global-constraints block** copied verbatim into every task: the domain's fix conventions, the gate that must stay green (link-checker / test suite / linter - whichever the domain uses), style/commit conventions, and **no environment-specific values** (no absolute machine paths, personal profiles, hostnames - use placeholders).
   - **Forward-safe ordering + per-item gate:** order tasks so none depends on a later task's output, and have each task leave the domain gate green in its own commit, so a regression is attributable to the task that caused it.
   - Ground each task in the Phase-1 evidence (exact `file:line` / tool findings) so the implementer verifies rather than guesses.

4. **Apply fixes - subagent-driven with per-item review.** Work one task at a time, tracking progress in a durable ledger (so the run survives interruption):
   1. Dispatch a **fresh implementer subagent** with: where the fix fits, the task brief + evidence, the global constraints and the report-file path. It makes the change, re-runs the domain gate to green, commits, and self-reviews.
   2. **Review against evidence:** a reviewer subagent (or inline if subagents are unstable) verifies the fix actually resolves the finding *against the real artifact/tool output* - not just that it looks plausible. Spec compliance + quality.
   3. **Resolve findings:** fix Critical/Important before advancing; apply easy correct Minor fixes; resolve any "can't verify from the diff" item yourself against the evidence.
   4. Record the task complete in the ledger. **One implementer at a time** (parallel implementers collide on shared files).

5. **Whole-branch review - a multi-reviewer, confidence-scored pass.** After all fixes, review the whole branch with **several specialized reviewer subagents running in parallel**, each taking one lens (the lenses are assembled from the `## Review lens` sections of the records whose fixes were applied; always include a "verify claims against the real artifact/tool output" reviewer). Collect their findings, then **rate each finding on a described three-point confidence scale** for whether it is real rather than a false positive - `confirmed` (a reviewer checked the claim against the artifact or tool output and the mechanism holds), `likely` (the mechanism is sound on reading but nothing was checked against the artifact), `speculative` (it reads as plausible and no mechanism was established) - and **act at a named point on that scale**: fix `confirmed` and `likely` (and easy, correct minor ones), and report the full findings list with a disposition for each (fixed / not-a-real-issue-with-reason / deferred-with-reason). Resolve anything a reviewer "couldn't verify from the diff" yourself against the evidence. Fix everything real in one follow-up pass; use the most capable model available for this gate.

6. **Finish.** Open a PR. State the CI implications up front - a docs/config-only audit usually stays off the heavy code gates; a code-changing audit needs the normal lint/typecheck/test (and any review) gates. Update the tracking issue and tick only acceptance criteria you verified. **Do not merge without explicit user approval.**
