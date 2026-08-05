---
name: audit
description: "Run a broad, parallel, report-only audit sweep across multiple quality domains (docs, dependencies, architecture, security, CI/CD, tests, evals, prompts/SOPs) and produce ONE consolidated findings report. Use when you want a whole-repo health check / multi-dimensional audit, or when the user says 'audit the repo' / 'run all the audits'. This is the front door to the *-audit family: it fans the domain audits out as parallel subagents and merges their findings. For a deep single-domain audit WITH fixes, invoke that domain's skill directly by its qualified name (e.g. handbook-audit:ci-audit, handbook-audit:deps-audit). Defaults to report-only. Runs on the audit-core engine."
---

# Audit - the multi-domain sweep front door

The front door to the `*-audit` family. It runs several domain audits **at once**, each as a read-only subagent, and consolidates their findings into a single report. It does not add a new lens of its own - it orchestrates the existing ones (`docs-audit`, `deps-audit`, `arch-audit`, `security-audit`, `ci-audit`, `test-audit`, `eval-audit`, `prompt-audit`), all built on **[audit-core](../audit-core/SKILL.md)**.

**Coverage record:** which clauses of the [engineering handbook](https://github.com/mesagroup/ai-agent-development-handbook/blob/main/docs/engineering/README.md) each domain skill actually checks is recorded clause by clause in [handbook-traceability.md](https://github.com/mesagroup/ai-agent-development-handbook/blob/main/docs/audit/handbook-traceability.md), and the gaps in domain coverage - what no skill can see yet, and which issue would fix it - are tracked there. Both links are absolute: this family ships as a Claude Code plugin and runs against other repositories, where a relative path out of the skill directory resolves to nothing.

**Core principle:** a sweep is for *breadth* - surface where the repo hurts across every dimension, cheaply and in parallel, without changing anything. Depth and fixes are a deliberate follow-up, one domain at a time. So this skill defaults to **report-only** and fans out; it never runs fixes in parallel (see "Fixes are delegated").

**Announce:** "I'm using the audit skill to run a multi-domain audit sweep (report-only) and consolidate the findings."

## When to use

- A whole-repo health check: "is this shippable / where are the problems?"
- Before a release, a public/open-source push, or an onboarding, when you want breadth across quality dimensions in one pass.
- The user says "audit the repo", "run all the audits", or names several domains at once.

**Not for:** a deep single-domain audit **with remediation** - invoke that domain's skill directly and by its qualified name (`handbook-audit:ci-audit`, `handbook-audit:deps-audit`, …), which runs the full audit-core loop (plan → subagent-driven fixes → review → PR). This front door is diagnosis-across-domains, not fix-one-domain-deeply.

## How it works

### 0. Scope + mode

- **Scope - argument-first.** `/audit` (no args) or `/audit all` → every available domain. `/audit ci security test` → just those. **Detect which domains are available from this skill's own siblings**, at `../<domain>-audit/checks/` relative to this skill's directory: a domain is available when that directory exists and holds at least one record. Resolve it relative to *this skill*, never to the audited repository, because a path relative to a repository root resolves inside the target: it finds nothing in a repository that has never carried the family, or the target's own copy in one that has, and either way the sweep reports a scope it did not audit. The audited repository's own skills, if it has any, are evidence for the prompt domain and are never the lens. **If the user explicitly names a domain that has no such checks directory, tell them it was skipped (and why) before fanning out** - never drop a requested scope silently. If the invocation is interactive and the scope is genuinely unclear, ask with the ask-the-user tool - but note that tool caps a question at **4 options**, so do **not** try to render every available domain as one checklist; offer a coarse choice instead (e.g. *All (recommended)* / *A subset I'll name* / *Just the security-relevant ones: security + deps + ci*). **Default = all.**
- **Mode - report-only by default.** The sweep produces findings, changes nothing, creates no branches/commits/PRs. Only ask about report+fix if the user explicitly wants fixes in this run - and then still hand each fix to the per-domain skill (see below), do not fan fixes out.
- **Opt-in sub-audits - resolve them here, once, for every selected domain at once.** A record carrying `optin: true` is a deeper pass or an extra deliverable the user chooses rather than a check the sweep owes them, and the fan-out is the wrong place to choose: parallel domain agents have nobody to ask, so an agent left to decide either skips a pass the user wanted or spends the run on one they did not ask for. Take each record's own default from its prose where it states one (`deps/transitive-licenses`, for instance, defaults on for a published library and asks otherwise) and off where it states none, then ask once for whatever that leaves undecided - one coarse question, within the same 4-option cap the scope question is subject to, not one question per domain. Pass each domain the list of its own opt-ins that were granted, and record in the report which were offered and which ran, so a reader can tell a pass nobody asked for from a pass that found nothing. **That list is the answer to the question the domain skill would otherwise ask** - `docs-audit`, for instance, tells a directly-invoked run to ask the user once whether to include the docstring phase - so a dispatched domain agent takes the granted list as given and neither re-asks nor decides for itself. And **opt-in *deliverables* are not in scope for a sweep at all**, however the user answers: an SBOM, a generated layering-contract config or a rendered metric report produces an artifact rather than findings-matrix rows, and a report-only run that emitted one would be writing on the strength of a diagnosis nobody has read yet. Offer it in step 4 as a per-domain follow-up instead.
- **Target and output - resolve all three here, exactly as `audit-core` step 0 defines them**, before anything fans out: `target_root` (`git rev-parse --show-toplevel`, resolved to a real path, never inferred from the working directory), `target_ref` (the `HEAD` short SHA, the branch name, and whether the tree is dirty), and `out_path` (ask for it, and refuse any path resolving under `target_root`; the consolidated report is **always** returned in conversation as well, so a run given no path is never silent, and a non-interactive run therefore **defaults to** conversation only, writing a file only where the invocation itself supplied a path). This sweep substitutes its own steps for the `audit-core` loop rather than running it, so it inherits none of that step implicitly - and every step below names all three, so leaving them unresolved here is what lets a sweep invent an output path or audit whichever tree the shell happened to be in. Which `audit-core` obligations the sweep restates, which it adapts, which it delegates to the domain skill and which it never reaches is enumerated in [sweep-obligations.md](https://github.com/mesagroup/ai-agent-development-handbook/blob/main/docs/audit/sweep-obligations.md), because a promise to restate is not checkable from either file alone: a dropped obligation leaves no trace in the file that dropped it.

### 1. Fan out - one read-only subagent per selected domain, in parallel

**Build the project inventory first, once, and pass it to every domain.** It is `audit-core` step 1's shared ground-truth artifact, and the sweep is where the saving is largest: eight domain agents would otherwise each re-derive the same partition and language map over the same tree, and be free to disagree about it. Building it here also means a domain that needs only one field of it does not pay to discover that field itself.

**Classify each partition's languages by a file census plus declaration files, never from the presence of a manifest.** A partition's language is a set, not a single value, and a package carrying a JavaScript manifest for monorepo wiring while holding only Python is classified as JavaScript by any "has a manifest, therefore" rule - whereupon the wrong toolchain runs against no matching source, finds nothing, and reports a pass. In a sweep that misclassification is not contained: every selected domain consumes the one artifact, so all of them inherit it at once and agree on a clean bill of health for code none of them looked at, which reads as corroboration across lenses rather than as the single error it is. The sweep builds the artifact, so the sweep owes the rule - a domain agent handed the inventory cannot re-derive what it was given.

Dispatch all selected domains **concurrently** (a barrier - collect the matrices before consolidating; a domain that errors does **not** block the others). Give each subagent:
- `target_root`, `target_ref`, and **the requirement to confirm its own `git rev-parse --show-toplevel` matches `target_root` before it reads anything** - passing the path is not enough on its own, because an agent that resolves the tree itself lands in the primary checkout whenever the sweep runs from a worktree, and then reports ground-truth evidence from a tree nobody is auditing with nothing in its matrix to say which tree that was. The sweep dispatches more agents than anything else in the family, so it is where a missing confirmation costs the most.
- The one line: "**Invoke the `handbook-audit:<domain>-audit` skill**, then load the records from its `checks/` directory that your audit needs - all of them for a small domain, or fan out internally by `locality` (the `local` records per partition, one `global` check per sub-agent) for a large one - and execute that audit against `target_root` in REPORT-ONLY mode, through the findings-matrix step only." **Pass no path to the lens.** Invoking the skill by name lets the harness resolve where the family is installed and hand the skill its own base directory, from which its `checks/` resolve; a path relative to a repository root resolves inside the audited repository instead. Qualifying the name with the plugin also stops a same-named project-level skill in the target from shadowing the lens under audit.
- **The project inventory**, which supersedes the per-domain list of grounding this bullet used to enumerate: the partitions and their language sets, the package managers and lockfiles, the test runners, the already-installed tooling, and the CI workflow list. One artifact rather than a list that had to grow with every new domain. Add only grounding the inventory does not carry, such as a declared architecture rule the user states, and pass it as a short pointer rather than a pasted lens.
- The hard constraints: **do NOT edit/create/delete any file, do NOT create branches/commits/PRs, report-only**; "keep raw tool output OUT of your final answer - return the matrix (**capped to the significant rows**), counts, top findings, and a one-line-per-tool ran/fell-back log."
- Instruction to run the domain's detection tooling **without adding a dependency to the target**, which for a tool that has to be fetched at all means the one-shot runner of the partition's package manager as recorded in the inventory: `uv run --with <tool>` for uv, `npx <tool>` for npm, `pnpm dlx <tool>` for pnpm, `yarn dlx <tool>` for yarn. Fetching ephemerally is a means to that constraint rather than the constraint itself, which is why most of what follows is about not fetching. For a package manager not listed, use its documented one-shot form; if it has none, fall back to the record's `## Tooling fallback`. **A `tooling:` entry names one of three kinds of thing, and a one-shot runner reaches only the first, so read the entry before choosing how to run it.** A *registry package* (`depcheck`, `pip-audit`, `@cyclonedx/cdxgen`) is what the runners above are for. A *subcommand of the target's own package manager* (`pnpm audit`, `npm sbom`, `yarn licenses list`) has nothing to fetch: run it directly, and run it only when that package manager is the partition's own, because such a subcommand resolves from the lockfile of the manager that owns it - `npm audit` on a pnpm partition reads a `package-lock.json` that is not there, and no runner can supply a subcommand of a manager the target does not use. A *standalone binary* (`osv-scanner`) belongs to no language registry at all, so it is available when the audit environment already carries it and otherwise unavailable, and no one-shot runner will install it. Fetching one of the latter two as if it were a package fails in the way a missing tool fails, which lands in the report as `no-evidence` for a check the target could in fact have answered - so the distinction is what keeps that status honest. **Always prefer a tool the inventory reports already installed**, which is pinned by the target's own lockfile and already trusted by that project. A one-shot runner is the fallback, and it is not free: it resolves a package at run time and executes it in the audit environment, so a run that promises only to read the target is nonetheless executing third-party code that could write to it - the same reason the no-writes invariant is checked rather than promised. So **record the resolved version of every ephemerally fetched tool in the report**, which makes the run reproducible and a bad version identifiable afterwards; and where policy forbids fetching at all, run only what is already installed and mark the remaining checks `no-evidence`, which is precisely what that status is for. Hardcoding one ecosystem's runner here would make every other ecosystem's tooling unrunnable no matter what the records say, and naming only one ecosystem's runner concretely while gesturing vaguely at the rest achieves genericity by omitting the hard part: an agent that cannot resolve the instruction falls through to the fallback, which is the same failure more quietly. And to **verify each finding against the real artifact** (source→sink, `file:line`, tool output) so scanner artifacts don't become findings. **If every fallback for a check fails (no network, tool won't install), mark that check `no-evidence` - never as a clean result; if the check has no lens in the partition's languages, mark it `not-applicable` - also never as a clean result** - so neither absence of tooling nor absence of a lens is reported as absence of findings.

One subagent per domain; do not split a single domain across subagents here (that's the domain skill's own internal concern).

**Partial results.** If a subagent dies, times out, or returns null/unusable output, do **not** stall the sweep: consolidate the domains that returned, and mark each missing one as `errored / incomplete` (with the reason) in the roll-up. A broken domain degrades the report; it does not block it.

### 2. Consolidate - into the report template

Merge the returned matrices into one report using the **template below**. Rules:
- **Carry each domain's self-verification forward.** Do not upgrade a Minor to a Critical (or invent a finding) during the merge; the domain subagent owns severity. If a domain reports a false positive it caught, keep that note - it is evidence the lens is grounded.
- **Surface cross-domain agreement.** When two domains flag the same root cause (e.g. "checks exist but aren't enforced", a shared shim), call it out as a theme - corroboration across lenses is a strong signal. A theme is corroboration, **not a new finding**: it is not added to the severity totals.
- Compute the severity roll-up by counting **per-domain matrix rows** (not themes); include the total Criticals, and any `errored / incomplete` domains from partial results.

### 3. Output - ask which format(s), then emit

Ask the user with the ask-the-user tool (**multi-select**, 3 options, all can be chosen; recommend Markdown):
- **Markdown file** - write the report to the `out_path` resolved in step 0, which is never under `target_root`, whether or not the audited repository is the one asking. This is the durable, linkable, diff-able record; recommended default.
- **HTML file** - write a **self-contained** `.html` (inline CSS, no external assets) alongside the Markdown, for a shareable local file.
- **claude.ai Artifact** - publish a hosted page: first load the `artifact-design` skill to calibrate the design, write the page file, then publish via the Artifact tool. Use for a polished, shareable dashboard.

Emit every format the user selects (writing an output file in report-only mode is fine **provided it lands outside `target_root`** - it is a report artifact, and inside the audited tree it would instead be an uninvited change to somebody else's branch), **and present the report in conversation whichever formats they selected**: the three options above are files to write, not alternatives to reporting, and step 0 already fixed the consolidated report as always returned in conversation as well. A non-interactive run has nobody to select a format or supply a path, so it follows step 0: write Markdown to `out_path` when one was supplied with the invocation, and otherwise return the report in conversation and write nothing. Never invent a path to satisfy a default - that is how a run with no stated destination writes into the audited tree.

### 4. Next steps

After presenting, offer (do not auto-run):
- **File issues** - turn the Important+ findings into tracked issues (one per domain under an umbrella epic is the proven shape).
- **Fix a domain** - run report+fix on a specific domain via its skill (sequential, its own PR).
- **Produce an opt-in deliverable** - an SBOM, a layering-contract config, a rendered metric report: a per-domain run of the skill that owns it, since it emits an artifact rather than findings and the sweep deliberately emitted none (see step 0).
- **Nothing** - the diagnosis is the deliverable.

## Fixes are delegated (why the sweep is report-only)

Report-only fans out safely because read-only subagents never collide. **Fix-mode does not fan out:** parallel implementers editing shared files collide, and a single sweep-wide fix produces one incoherent mega-PR. So when the user wants remediation, this skill hands the chosen domain to its own skill - **invoked as `handbook-audit:<domain>-audit`**, qualified exactly as in the report-only fan-out - in report+fix mode, which runs the full audit-core loop - one domain, one coherent PR, per-item review - and does the next domain after. Breadth here; depth there. The qualified name matters more here than in the diagnosis path, not less: a bare `<domain>-audit` resolves to a same-named skill in the working tree wherever one exists, so a target carrying its own fork of the family would be diagnosed with the plugin's lens and then **remediated with its own**, and remediation is the half that writes.

## Consolidated report template

```markdown
# Repo audit - <project> (report-only, <YYYY-MM-DD>)

<one-sentence verdict: overall health + the single most important thing to fix>

## Severity roll-up
| Domain | Critical | Important | Minor | Coverage (ran / no-evidence / n-a) | One-line verdict |
|---|---|---|---|---|---|
| <domain> | n | n | n | n / n / n | <pass/warn/fail + gist> |
| ... |
| **Total** | **n** | **n** | **n** | **n / n / n** | |

Coverage is not optional decoration. A domain whose every check returned `no-evidence` shows zero findings at every severity, which is indistinguishable from a clean domain in a severity-only table, and on a foreign repository with none of the expected tooling installed that is the likely case rather than the exotic one. **When coverage is partial, the one-line verdict must lead with coverage**, not with the finding count.

## Criticals (<count>)
1. <finding> (<domain>) - <evidence file:line / tool result>
   ...   (omit this section if zero Criticals)

## Cross-cutting themes
- <theme>: <which domains agree, and the shared root cause>

## Per-domain findings
### <domain>
<the domain's findings matrix: Item | Check | Status | Severity | Evidence | Handbook - capped to the significant rows>
Top findings: <2-3 one-liners>

## How the audit ran
- Target: <repository identity - the remote's `owner/repo` if one is configured, else the repository directory's own name; never a filesystem path> at <short SHA> on <branch><, working tree dirty if it was>
- Lenses: handbook-audit @ <short SHA>
- Scope: <domains run> · Mode: report-only
- Stacks present: <partition: languages, tested yes/no, in CI yes/no> (one line each)
- Per-domain tool log: <ran / fell back / no runner available> (one line each)
- Verification note: <any false positives caught and discarded>
- Target tree unchanged: <yes, or the git status delta observed>

## Next steps
- File issues (Important+) / run report+fix on <domain> / nothing
```

## Cross-cutting rules

- **Project-agnostic.** Detect available domain skills and each domain's tooling; run the subset that applies; never hardcode a fixed set, and detect the domains from this skill's own siblings rather than from the audited repository.
- **Report-only means no writes to the target's working tree or git history.** The only files this skill may write are the report artifacts in step 3, and they land outside `target_root`. Verify it rather than assert it, per `audit-core`'s invariant: `git status --porcelain` at the target before and after.
- **Verify against evidence** is inherited from audit-core and enforced per-domain - the consolidation must not weaken it.
- **No environment-specific values** in any emitted report (placeholders with prose, not machine paths / personal profiles).
