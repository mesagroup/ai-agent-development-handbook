---
name: audit-core
description: "The shared engine behind the *-audit skills (docs-audit, deps-audit, test-audit, eval-audit, arch-audit, ci-audit, security-audit, prompt-audit). Encodes the reusable audit loop — scope, evidence gathering, findings matrix, remediation plan, subagent-driven fixes, review — that each domain skill specializes. Read this when authoring or running any of those skills; it is not usually invoked directly on its own."
---

# Audit Core — the shared audit engine

Every `*-audit` skill is the **same loop** applied through a different lens. This skill owns that loop so the domain skills stay thin and behave consistently. A domain skill provides the lens (its dimensions, evidence sources, tooling, severity rubric, and fix patterns) and defers the mechanics to here.

**Core principle:** an audit is only as good as the evidence under it. Gather evidence from the actual artifacts (source, config, lockfiles, workflow files, test runs) — never from a summary, a stale doc, or an assumption. A confident finding built on a guess is worse than no finding.

**Announce (from the domain skill):** "I'm using the `<domain>-audit` skill (on the audit-core engine) to audit `<subject>`."

**Pin every subagent to the working tree you are in.** When the audit runs from a git worktree, a dispatched agent given a bare or main-repo-rooted path can silently operate on the *primary* checkout instead, often many commits stale. Both directions fail quietly. A read-only evidence agent then reports ground truth from a tree nobody is auditing, which is the stale-source failure the core principle above forbids. An implementer's edit lands where `git status` in your worktree will never show it, so the fix drops out of the commit and reads afterwards as though the agent simply missed it. Resolve `git rev-parse --show-toplevel` once, pass that absolute root in every dispatch, and require each agent to confirm its own `--show-toplevel` matches before it reads or edits.

## The loop

Runs in order; each step feeds the next.

0. **Scope + mode.** Fix the subject (which package/tree/config) and the depth. **Always ask the user the mode:** *report-only* (produce the findings matrix + report and stop) or *report + fix* (continue through remediation). For a large subject in fix mode, deliver in **increments** (one coherent slice per PR) rather than one giant change. Resolve any opt-in sub-audits here too (ask once if an argument didn't specify).

1. **Gather evidence — fan out read-only subagents in parallel.** This is the load-bearing step. Dispatch one read-only agent per slice of the subject (per package, per config file, per dimension — whatever partitions cleanly) to collect *ground-truth* evidence: run the domain's tools, read the relevant files, and report a structured result. Run the domain's detection/measurement tooling here (see the domain skill for which). Also gather the project's existing conventions (contributor guide, prior audits, existing config) so remediation matches house style.

   **Match the fan-out axis to each dimension's *locality*, don't hardcode one axis.** Build any shared ground-truth artifact (a parsed graph, a resolved dependency tree, a coverage map) **once** and let agents consume it, rather than each rebuilding a possibly-inconsistent copy. Then slice **local** dimensions (decidable from one partition) per-partition, and give each **global** dimension (one that needs the whole subject — a cycle, a whole-graph ratio, a cross-file flow) its own agent over the whole artifact, because a per-partition agent cannot compute a whole-subject property from its slice. Do **not** fan a cheap local check out to its own agent — that duplicates the shared build for no gain.

2. **Build the findings matrix.** Consolidate the evidence into a table: **item × dimension × status × severity**, plus a one-line evidence pointer (`file:line`, tool output, or metric) for every row. Status is a small fixed scale the domain defines (e.g. pass / partial / fail, or ok / warn / violation). Severity is Critical / Important / Minor. Summarize counts. Save the findings report under the repo (e.g. `docs/audit/<date>-<domain>-audit.md`) so it is itself linkable, and record any policy decisions so they are not re-litigated.

**If the mode is report-only, stop here** — present the findings matrix + report (with a short recommended-remediation sketch), modify no files, and ask the user whether to proceed to fixes. Steps 3–6 run only in report + fix mode.

3. **Plan remediation.** Turn the fail/violation rows into a work list. Write a plan file under the project's plans location (fall back to `docs/plans/`).
   - **One task per coherent fix** (or tightly-coupled group), each independently verifiable.
   - **Global-constraints block** copied verbatim into every task: the domain's fix conventions, the gate that must stay green (link-checker / test suite / linter — whichever the domain uses), style/commit conventions, and **no environment-specific values** (no absolute machine paths, personal profiles, hostnames — use placeholders).
   - **Forward-safe ordering + per-item gate:** order tasks so none depends on a later task's output, and have each task leave the domain gate green in its own commit, so a regression is attributable to the task that caused it.
   - Ground each task in the Phase-1 evidence (exact `file:line` / tool findings) so the implementer verifies rather than guesses.

4. **Apply fixes — subagent-driven with per-item review.** Work one task at a time, tracking progress in a durable ledger (so the run survives interruption):
   1. Dispatch a **fresh implementer subagent** with: where the fix fits, the task brief + evidence, the global constraints and the report-file path. It makes the change, re-runs the domain gate to green, commits, and self-reviews.
   2. **Review against evidence:** a reviewer subagent (or inline if subagents are unstable) verifies the fix actually resolves the finding *against the real artifact/tool output* — not just that it looks plausible. Spec compliance + quality.
   3. **Resolve findings:** fix Critical/Important before advancing; apply easy correct Minor fixes; resolve any "can't verify from the diff" item yourself against the evidence.
   4. Record the task complete in the ledger. **One implementer at a time** (parallel implementers collide on shared files).

5. **Whole-branch review — a multi-reviewer, confidence-scored pass.** After all fixes, review the whole branch with **several specialized reviewer subagents running in parallel**, each taking one lens (the lenses are assembled from the `## Review lens` sections of the records whose fixes were applied; always include a "verify claims against the real artifact/tool output" reviewer). Collect their findings, then **score each finding 0–100 for confidence** that it is real (vs. a false positive), and **act by threshold**: fix the confident ones (and easy, correct minor ones), and report the full findings list with a disposition for each (fixed / not-a-real-issue-with-reason / deferred-with-reason). Resolve anything a reviewer "couldn't verify from the diff" yourself against the evidence. Fix everything real in one follow-up pass; use the most capable model available for this gate.

6. **Finish.** Open a PR. State the CI implications up front — a docs/config-only audit usually stays off the heavy code gates; a code-changing audit needs the normal lint/typecheck/test (and any review) gates. Update the tracking issue and tick only acceptance criteria you verified. **Do not merge without explicit user approval.**

## Authoring a new auditing skill

A `<domain>-audit` skill is thin: it states the lens and defers the loop above to this engine.

**Checks are records, not prose.** Each check the domain runs is one file under that domain's own skill, at `<domain>-audit/checks/<slug>.md`, with its machine-checkable attributes in YAML frontmatter (`id`, `domain`, `locality`, `handbook`, `tooling`, `optin`) and its judgment prose in the body: the claim as lead prose, then `## Severity`, `## Tooling fallback`, `## Fix`, `## Review lens`, omitting any section the check has nothing to say in. An executing agent loads the subset its slice needs - `locality: local` checks per partition, one `global` check per agent - so no agent pays for the rest of the domain. A check that is decidable per-partition except for one repo-global fact splits into a `local` check and a `global` one, because "report this once" is not something N parallel agents can honour. `handbook` lists the handbook clauses grounding the check and is validated against the traceability matrix in both directions; a check that deliberately exceeds the handbook carries an empty list and a `handbook_note` saying why. Every `## Tooling fallback` **detects before it prescribes** - prefer a tool the target project already runs, and give a fallback that works when none is installed, because a check that only works with its favourite tool present reports absence of tooling as absence of findings. A `handbook_note` cites a stable identifier - a matrix row `id`, a check id, a heading - and never a line number: a `grep` command may stay in the note as the reproduction step, but the citation itself must survive an edit to the file it points at, since a line number a later edit shifts silently stops pointing at the clause it was written to ground. See `../arch-audit/checks/` for the reference set.

A domain's records live with the domain, not in a shared tree here: this engine owns the record *schema*, each skill owns its *instances*. That keeps a domain portable - a repo adopting three of the eight copies three skill directories plus this engine - and keeps a record one hop from the `SKILL.md` naming it rather than two hops through a sibling skill, which is the nesting depth Anthropic's skill guidance warns leads an agent to preview a file instead of reading it.

**The skill file holds only what does not vary by check:** the subject and how to slice it, the ground-truth artifact to build once, the status scale, whether fixes touch code, and any opt-in *deliverables* (a generated config, a rendered report - things that produce an artifact rather than findings-matrix rows). Measured across the eight migrated domains, the header body ranges from about 370 words (`deps`) to about 1020 words (`prompt`) - measure your own domain rather than copying either number forward as a target. Check count does not predict the size: `arch` carries 11 checks in the low 500s and `test` needs about 590 for 7. What actually drives it is (a) how many of the domain's checks are `global`-locality *and* need a stated, non-generic reason why no per-partition agent can decide them - a domain where every check shares one uniform reason (`deps`) states it once cheaply, while one with several case-by-case exceptions (`ci`, `eval`) must justify each - and (b) whether the domain carries a cross-cutting classification or fix pattern that applies across many checks at once and has no single check to record it in. `prompt`'s tier split (which checks apply to a formal SOP versus a general prompt) is exactly the second case, and it is why `prompt`, despite having only one `global` check, is the densest header in the family.

## Cross-cutting rules (all domains)

- **Verify against evidence, always.** Every finding and every fix cites the artifact/tool output it rests on. Reviews exist to catch confident-but-wrong claims.
- **Cross-link, don't duplicate.** If another skill/doc already owns a topic (e.g. `security-audit` and `deps-audit` both touch CVEs), one owns it and the other links.
- **Attribution / provenance honesty.** Never fabricate a source, URL, license, or CVE id; "unverified, tracked in issue #N" is an acceptable honest outcome.
- **Fix pre-existing issues you touch** if small and real; discuss larger ones before expanding scope.
- **Keep the domain gate green per task**, so regressions are attributable.
- **No environment-specific values** in committed artifacts — placeholders with prose explaining what they resolve to.
- **Project-agnostic.** Discover packages/layout/tooling/conventions from the target repo (`pyproject.toml`, contributor guide, existing config); impose a standard only if none exists, and confirm it with the user.
