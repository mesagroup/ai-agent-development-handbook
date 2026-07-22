---
name: audit-core
description: "The shared engine behind the *-audit skills (docs-audit, deps-audit, test-audit, eval-audit, arch-audit, ci-audit, security-audit). Encodes the reusable audit loop — scope, evidence gathering, findings matrix, remediation plan, subagent-driven fixes, review — that each domain skill specializes. Read this when authoring or running any of those skills; it is not usually invoked directly on its own."
---

# Audit Core — the shared audit engine

Every `*-audit` skill is the **same loop** applied through a different lens. This skill owns that loop so the domain skills stay thin and behave consistently. A domain skill provides the lens (its dimensions, evidence sources, tooling, severity rubric, and fix patterns) and defers the mechanics to here.

**Core principle:** an audit is only as good as the evidence under it. Gather evidence from the actual artifacts (source, config, lockfiles, workflow files, test runs) — never from a summary, a stale doc, or an assumption. A confident finding built on a guess is worse than no finding.

**Announce (from the domain skill):** "I'm using the `<domain>-audit` skill (on the audit-core engine) to audit `<subject>`."

**Bash rule (you and every subagent you dispatch):** never pass a line starting with `#` to the Bash tool — hash comments confuse the tool-permission subsystem. Put commit messages in heredoc files or use `-m`.

## The loop

Runs in order; each step feeds the next.

0. **Scope + mode.** Fix the subject (which package/tree/config) and the depth. **Always ask the user the mode:** *report-only* (produce the findings matrix + report and stop) or *report + fix* (continue through remediation). For a large subject in fix mode, deliver in **increments** (one coherent slice per PR) rather than one giant change. Resolve any opt-in sub-audits here too (ask once if an argument didn't specify).

1. **Gather evidence — fan out read-only subagents in parallel.** This is the load-bearing step. Dispatch one read-only agent per slice of the subject (per package, per config file, per dimension — whatever partitions cleanly) to collect *ground-truth* evidence: run the domain's tools, read the relevant files, and report a structured result. Run the domain's detection/measurement tooling here (see the domain skill for which). Also gather the project's existing conventions (contributor guide, prior audits, existing config) so remediation matches house style.

2. **Build the findings matrix.** Consolidate the evidence into a table: **item × dimension × status × severity**, plus a one-line evidence pointer (`file:line`, tool output, or metric) for every row. Status is a small fixed scale the domain defines (e.g. pass / partial / fail, or ok / warn / violation). Severity is Critical / Important / Minor. Summarize counts. Save the findings report under the repo (e.g. `docs/audit/<date>-<domain>-audit.md`) so it is itself linkable, and record any policy decisions so they are not re-litigated.

**If the mode is report-only, stop here** — present the findings matrix + report (with a short recommended-remediation sketch), modify no files, and ask the user whether to proceed to fixes. Steps 3–6 run only in report + fix mode.

3. **Plan remediation.** Turn the fail/violation rows into a work list. Write a plan file under the project's plans location (fall back to `docs/plans/`).
   - **One task per coherent fix** (or tightly-coupled group), each independently verifiable.
   - **Global-constraints block** copied verbatim into every task: the domain's fix conventions, the gate that must stay green (link-checker / test suite / linter — whichever the domain uses), style/commit conventions, and **no environment-specific values** (no absolute machine paths, personal profiles, hostnames — use placeholders).
   - **Forward-safe ordering + per-item gate:** order tasks so none depends on a later task's output, and have each task leave the domain gate green in its own commit, so a regression is attributable to the task that caused it.
   - Ground each task in the Phase-1 evidence (exact `file:line` / tool findings) so the implementer verifies rather than guesses.

4. **Apply fixes — subagent-driven with per-item review.** Work one task at a time, tracking progress in a durable ledger (so the run survives interruption):
   1. Dispatch a **fresh implementer subagent** with: where the fix fits, the task brief + evidence, the global constraints, the report-file path, and the Bash-no-`#` reminder. It makes the change, re-runs the domain gate to green, commits, and self-reviews.
   2. **Review against evidence:** a reviewer subagent (or inline if subagents are unstable) verifies the fix actually resolves the finding *against the real artifact/tool output* — not just that it looks plausible. Spec compliance + quality.
   3. **Resolve findings:** fix Critical/Important before advancing; apply easy correct Minor fixes; resolve any "can't verify from the diff" item yourself against the evidence.
   4. Record the task complete in the ledger. **One implementer at a time** (parallel implementers collide on shared files).

5. **Whole-branch review — a multi-reviewer, confidence-scored pass.** After all fixes, review the whole branch with **several specialized reviewer subagents running in parallel**, each taking one lens (the domain supplies the lenses in its Review-dimensions slot; always include a "verify claims against the real artifact/tool output" reviewer). Collect their findings, then **score each finding 0–100 for confidence** that it is real (vs. a false positive), and **act by threshold**: fix the confident ones (and easy, correct minor ones), and report the full findings list with a disposition for each (fixed / not-a-real-issue-with-reason / deferred-with-reason). Resolve anything a reviewer "couldn't verify from the diff" yourself against the evidence. Fix everything real in one follow-up pass; use the most capable model available for this gate.

6. **Finish.** Open a PR. State the CI implications up front — a docs/config-only audit usually stays off the heavy code gates; a code-changing audit needs the normal lint/typecheck/test (and any review) gates. Update the tracking issue and tick only acceptance criteria you verified. **Do not merge without explicit user approval.**

## Authoring a new auditing skill

A `<domain>-audit` skill is thin: it states the lens and defers the loop above to this engine. It must define these seven slots:

1. **Subject & scope** — what is audited, and how to slice it for the parallel evidence pass.
2. **Dimensions** — the axes/checks (the columns of the findings matrix).
3. **Evidence sources & tooling** — which files to read and which tools to run to get ground truth; **detect** the project's tools, with sensible fallbacks if absent.
4. **Status scale + severity rubric** — the fixed status values and what makes a finding Critical / Important / Minor in this domain.
5. **Fix patterns** — how remediation is done, and whether fixes touch **code** (needs the normal code CI + maybe code-review) or only **docs/config** (lighter gate).
6. **Review dimensions** — the specialized reviewer lenses for step 5.
7. **Opt-in sub-audits** (if any) — extra phases controlled by an argument or an ask-the-user fallback.

## Cross-cutting rules (all domains)

- **Verify against evidence, always.** Every finding and every fix cites the artifact/tool output it rests on. Reviews exist to catch confident-but-wrong claims.
- **Cross-link, don't duplicate.** If another skill/doc already owns a topic (e.g. `security-audit` and `deps-audit` both touch CVEs), one owns it and the other links.
- **Attribution / provenance honesty.** Never fabricate a source, URL, license, or CVE id; "unverified, tracked in issue #N" is an acceptable honest outcome.
- **Fix pre-existing issues you touch** if small and real; discuss larger ones before expanding scope.
- **Keep the domain gate green per task**, so regressions are attributable.
- **No environment-specific values** in committed artifacts — placeholders with prose explaining what they resolve to.
- **Project-agnostic.** Discover packages/layout/tooling/conventions from the target repo (`pyproject.toml`, contributor guide, existing config); impose a standard only if none exists, and confirm it with the user.
