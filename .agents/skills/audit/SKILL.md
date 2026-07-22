---
name: audit
description: "Run a broad, parallel, report-only audit sweep across multiple quality domains (docs, dependencies, architecture, security, CI/CD, tests, evals) and produce ONE consolidated findings report. Use when you want a whole-repo health check / multi-dimensional audit, or when the user says 'audit the repo' / 'run all the audits'. This is the front door to the *-audit family: it fans the domain audits out as parallel subagents and merges their findings. For a deep single-domain audit WITH fixes, invoke that domain's skill directly (e.g. ci-audit, deps-audit). Defaults to report-only. Runs on the audit-core engine."
---

# Audit — the multi-domain sweep front door

The front door to the `*-audit` family. It runs several domain audits **at once**, each as a read-only subagent, and consolidates their findings into a single report. It does not add a new lens of its own — it orchestrates the existing ones (`docs-audit`, `deps-audit`, `arch-audit`, `security-audit`, `ci-audit`, `test-audit`, `eval-audit`), all built on **[audit-core](../audit-core/SKILL.md)**.

**Core principle:** a sweep is for *breadth* — surface where the repo hurts across every dimension, cheaply and in parallel, without changing anything. Depth and fixes are a deliberate follow-up, one domain at a time. So this skill defaults to **report-only** and fans out; it never runs fixes in parallel (see "Fixes are delegated").

**Announce:** "I'm using the audit skill to run a multi-domain audit sweep (report-only) and consolidate the findings."

**Bash rule (you and every subagent you dispatch):** never pass a line starting with `#` to the Bash tool — hash comments confuse the tool-permission subsystem.

## When to use

- A whole-repo health check: "is this shippable / where are the problems?"
- Before a release, a public/open-source push, or an onboarding, when you want breadth across quality dimensions in one pass.
- The user says "audit the repo", "run all the audits", or names several domains at once.

**Not for:** a deep single-domain audit **with remediation** — invoke that domain's skill directly (`ci-audit`, `deps-audit`, …), which runs the full audit-core loop (plan → subagent-driven fixes → review → PR). This front door is diagnosis-across-domains, not fix-one-domain-deeply.

## How it works

### 0. Scope + mode

- **Scope — argument-first.** `/audit` (no args) or `/audit all` → every available domain. `/audit ci security test` → just those. **Detect which `*-audit` skills actually exist** under the skills dir and only run those (project-agnostic; a repo may have a subset). If the invocation is interactive and the scope is genuinely unclear, ask with the ask-the-user tool — but note that tool caps a question at **4 options**, so do **not** try to render all seven domains as one checklist; offer a coarse choice instead (e.g. *All (recommended)* / *A subset I'll name* / *Just the security-relevant ones: security + deps + ci*). **Default = all.**
- **Mode — report-only by default.** The sweep produces findings, changes nothing, creates no branches/commits/PRs. Only ask about report+fix if the user explicitly wants fixes in this run — and then still hand each fix to the per-domain skill (see below), do not fan fixes out.

### 1. Fan out — one read-only subagent per selected domain, in parallel

Dispatch all selected domains **concurrently** (a barrier — you need every matrix to consolidate). Give each subagent:
- The repo root and the one line: "Read `.agents/skills/<domain>-audit/SKILL.md` and `.agents/skills/audit-core/SKILL.md`, then execute that audit on THIS repo in REPORT-ONLY mode, through the findings-matrix step only."
- Any repo-specific grounding the domain needs (declared architecture rules for arch, the eval stack location for eval, the workflow list for ci, etc.) — a short pointer, not a pasted lens.
- The hard constraints: **do NOT edit/create/delete any file, do NOT create branches/commits/PRs, report-only**; the Bash-no-`#` reminder; "keep raw tool output OUT of your final answer — return the matrix, counts, top findings, and a one-line-per-tool ran/fell-back log."
- Instruction to run the domain's detection tooling ephemerally (`uv run --with <tool> …`) with the domain skill's fallbacks, and to **verify each finding against the real artifact** (source→sink, `file:line`, tool output) so scanner artifacts don't become findings.

One subagent per domain; do not split a single domain across subagents here (that's the domain skill's own internal concern).

### 2. Consolidate — into the report template

Merge the returned matrices into one report using the **template below**. Rules:
- **Carry each domain's self-verification forward.** Do not upgrade a Minor to a Critical (or invent a finding) during the merge; the domain subagent owns severity. If a domain reports a false positive it caught, keep that note — it is evidence the lens is grounded.
- **Surface cross-domain agreement.** When two domains flag the same root cause (e.g. "checks exist but aren't enforced", a shared shim), call it out as a theme — corroboration across lenses is a strong signal.
- Compute the severity roll-up (counts per domain, total Criticals).

### 3. Output — ask which format(s), then emit

Ask the user with the ask-the-user tool (**multi-select**, 3 options, all can be chosen; recommend Markdown):
- **Markdown file** — write the report to `docs/audit/<YYYY-MM-DD>-repo-audit.md` (or the project's audit dir). This is the durable, linkable, diff-able record; recommended default.
- **HTML file** — write a **self-contained** `.html` (inline CSS, no external assets) alongside the Markdown, for a shareable local file.
- **claude.ai Artifact** — publish a hosted page: first load the `artifact-design` skill to calibrate the design, write the page file, then publish via the Artifact tool. Use for a polished, shareable dashboard.

Emit every format the user selects (writing an output file in report-only mode is fine — it is a report artifact, not a change to the audited code). If the user is non-interactive, default to Markdown only.

### 4. Next steps

After presenting, offer (do not auto-run):
- **File issues** — turn the Important+ findings into tracked issues (one per domain under an umbrella epic is the proven shape).
- **Fix a domain** — run report+fix on a specific domain via its skill (sequential, its own PR).
- **Nothing** — the diagnosis is the deliverable.

## Fixes are delegated (why the sweep is report-only)

Report-only fans out safely because read-only subagents never collide. **Fix-mode does not fan out:** parallel implementers editing shared files collide, and a single sweep-wide fix produces one incoherent mega-PR. So when the user wants remediation, this skill hands the chosen domain to its own skill (`<domain>-audit` in report+fix mode), which runs the full audit-core loop — one domain, one coherent PR, per-item review — and does the next domain after. Breadth here; depth there.

## Consolidated report template

```markdown
# Repo audit — <project> (report-only, <YYYY-MM-DD>)

<one-sentence verdict: overall health + the single most important thing to fix>

## Severity roll-up
| Domain | Critical | Important | Minor | One-line verdict |
|---|---|---|---|---|
| <domain> | n | n | n | <pass/warn/fail + gist> |
| ... |
| **Total** | **n** | **n** | **n** | |

## Criticals (<count>)
1. <finding> (<domain>) — <evidence file:line / tool result>
   ...   (omit this section if zero Criticals)

## Cross-cutting themes
- <theme>: <which domains agree, and the shared root cause>

## Per-domain findings
### <domain>
<the domain's findings matrix: Item | Dimension | Status | Severity | Evidence — capped to the significant rows>
Top findings: <2-3 one-liners>

## How the audit ran
- Scope: <domains run> · Mode: report-only
- Per-domain tool log: <ran / fell back> (one line each)
- Verification note: <any false positives caught and discarded>

## Next steps
- File issues (Important+) / run report+fix on <domain> / nothing
```

## Cross-cutting rules

- **Project-agnostic.** Detect available domain skills and each domain's tooling; run the subset that applies; never hardcode a fixed seven.
- **Report-only means read-only for the audited code.** The only files this skill may write are the report artifacts in step 3.
- **Verify against evidence** is inherited from audit-core and enforced per-domain — the consolidation must not weaken it.
- **No environment-specific values** in any emitted report (placeholders with prose, not machine paths / personal profiles).
