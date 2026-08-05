# Auditing a foreign repository ([#8](https://github.com/mesagroup/ai-agent-development-handbook/issues/8), with the residue of [#5](https://github.com/mesagroup/ai-agent-development-handbook/issues/5) and [#7](https://github.com/mesagroup/ai-agent-development-handbook/issues/7))

**Status:** draft 2026-08-05. Delivers what wave 1 of [#1](https://github.com/mesagroup/ai-agent-development-handbook/issues/1) left behind. The checks database shipped the *data* those three issues needed and none of the *behaviour*, so each is half done in a way its acceptance criteria no longer describe. One PR covers all three.

## Problem

Wave 1 restructured the family onto a checks database: 68 check records across eight domains, each carrying a `handbook:` citation list validated against the traceability matrix in both directions, and 37 of them carrying a `tooling:` map keyed by language. The three issues wave 1 was supposed to deliver were left open as acceptance tests. Measuring them against the tree shows the data landed and the behaviour did not.

| Issue | Delivered by wave 1 | Not delivered |
|---|---|---|
| #5 TypeScript | per-language `tooling:` entries in the architecture records (9 of 11) and the dependency records (6 of 6) | nothing detects a partition's language, so the entries are never selected between; five descriptions assert the skill audits a Python project, four headers name only Python tools in their detect and gate prose, and the front door hardcodes a Python-only mechanism for running a tool ephemerally. **The test and security records carry no TypeScript tooling at all, 0 of 7 each**, so #5's criterion naming architecture, test, security and dependencies end to end is met for two of those four domains and not the other two. This pass does not close that; it makes the shortfall visible instead of silent, because a check with no lens in the partition's language now reports `not-applicable` where it would previously have reported a clean result. |
| #7 citations | the `handbook:` lists and their bidirectional validation | the findings matrix has no citation column, and the front door's report template carries none |
| #8 foreign repos | nothing | the front door tells every subagent to audit "THIS repo" and hands it a path relative to a repo root |

The last row is the load-bearing one, and it is worse than an absent feature. The front door's subagent brief says to read `.agents/skills/<domain>-audit/SKILL.md` and load records from `.agents/skills/<domain>-audit/checks/`. Those paths are relative to a repo root, and they work today only because the lenses and the audited code are the same tree. Against a foreign target they resolve inside the target: to nothing in a repository that has never carried the family, or to that repository's own copy in one that has. `lidia-tech/lidia-agents` is the second case. It still carries a complete copy of all eight domains with the same per-domain record counts, because the extraction copied rather than moved. So the dry run in [#10](https://github.com/mesagroup/ai-agent-development-handbook/issues/10) would audit using that repository's fork of the lenses while reporting success, and its stated value as a regression check on the skills would be vacuous.

There is a second instance of the same defect, found while planning, and it is the more damaging one. Step 0 decides which domains are available by testing whether `.agents/skills/<domain>-audit/checks/` exists, which is again a path relative to a repo root. Against the single-package target that directory is absent entirely; against the monorepo target it exists and holds that project's own skills, with no `*-audit` directory among them. Either way step 0 resolves **zero** available domains, and its own parenthetical, "project-agnostic; a repo may have a subset", reads that empty result as a legitimate subset rather than as a failure. So the sweep is not merely Python-flavoured on a foreign target: it cannot run at all, and it says so in language that sounds like a successful scope resolution.

## Decisions

### 1. The audit runs inside the target; the lenses come from the plugin

The working directory is the audited repository, with the `handbook-audit` plugin installed. This matches how the family is distributed and means there is no skills root to thread anywhere.

### 2. Subagents are dispatched to invoke a skill, never to read a path

The front door dispatches each domain subagent with an instruction to invoke `handbook-audit:<domain>-audit`. It passes no path to the lens at all.

This is the standard mechanism rather than a new one. `superpowers:writing-skills` is explicit that a skill references its own supporting files by a path relative to its own directory, that it references *other* skills by name and never by path, and the harness supplies each loaded skill its own base directory. `audit-core` already uses the standard form when it points at `../arch-audit/checks/`. The front door's brief was the single non-standard reference in the family, and replacing the path with a skill invocation deletes the class of bug rather than parameterising it.

Qualifying the name with the plugin also fixes the collision precisely. In a target that carries its own project-level `arch-audit`, `handbook-audit:arch-audit` names the plugin's copy, so a fork cannot shadow the lens under audit.

Domain discovery moves the same way, to `../<domain>-audit/checks/` relative to the front door's own skill directory. The audited repository's own skills, where it has any, are evidence for the prompt domain and are never the lens.

### 3. Step 0 resolves the target root, the target ref and the output path

`audit-core` step 0 fixes the subject and the mode. It gains three more resolutions, each recorded:

- `target_root`: `git rev-parse --show-toplevel`, resolved to a real path. Every tool invocation and every glob is pathed at it. In this posture it happens to equal the working directory, and nothing may *assume* that, because an assumption is what silently audits the wrong tree.
- `target_ref`: `HEAD` short SHA, branch name, and whether the tree is dirty.
- `out_path`: asked at scope time, and refused if it resolves under `target_root`. The consolidated report is always returned in conversation as well, so a run without an output path is never silent. A non-interactive run defaults to conversation only and writes nothing.

`target_ref` is not bookkeeping. Both Mesa target repositories were last committed 2026-07-23 and both are checked out on a branch that is not their default. A report that does not say so neither reproduces nor maps onto what those teams see on their own default branch.

### 4. The invariant is no writes to the target's working tree or git history

Stated that way rather than as "do not touch the target repository", because the emitter in [#9](https://github.com/mesagroup/ai-agent-development-handbook/issues/9) will open issues in the audited project's tracker. Creating an issue leaves the working tree untouched, so the narrow wording is the one that survives the family growing, and the broad wording would have to be broken within weeks of being written.

The invariant is checked rather than promised: capture `git status --porcelain` at the target at scope time and again after consolidation, and report any delta as a defect of the audit run. This has teeth immediately, because package managers write caches and lockfiles into a tree they were asked only to read.

### 5. The project inventory is the shared ground-truth artifact

Step 1 already requires building any shared ground-truth artifact once and letting agents consume it, rather than each rebuilding a possibly inconsistent copy. The project inventory is the canonical instance of that rule, and naming it adds no stage and no branch to the loop. This is why #5's constraint that `audit-core` stay one loop is satisfied in substance: the shape does not change, an artifact that was implicit becomes specified.

The front door builds it once **before** the fan-out and passes it to every domain subagent, replacing the ad hoc list of per-domain grounding that otherwise has to grow whenever a domain is added. A single-domain invocation builds the same artifact itself in step 1. One artifact, two entry points.

Once per repository it records the target root, the target ref, the dirty flag, the monorepo tool and its workspace globs, and the CI workflow list. Once per partition it records the path, the language set, the package manager and lockfile, the test runner, and which audit-relevant tools the partition already has.

That last field is what finally gives `audit-core`'s "detect before it prescribes" rule an input. Nothing computes what the target already runs today, so the rule has nothing to read. `<polyglot-monorepo-target>` is the case it was written for: `dependency-cruiser` is in its dependencies and already runs in CI through `turbo run arch`.

### 6. A partition's language is a set, and a manifest is not a language detector

Detection is a file census plus declaration files, and it yields a set rather than one value. `<polyglot-monorepo-target>` establishes both halves. `<js-manifest-package>` carries a `package.json` for monorepo wiring and contains zero `.ts` or `.tsx` files, three `.py` files and a `requirements.txt`. Any detector shaped like "has a `package.json`, therefore TypeScript" classifies it as TypeScript, runs TypeScript tooling against no TypeScript, finds nothing, and reports a pass. `<mixed-language-package>` is mixed within one partition: 322 `.ts` or `.tsx` files alongside a Python function with its own nested `requirements.txt`.

Tooling selection then reads: the partition's language set, to the union of the check's `tooling:` entries for those languages and its `any` entries, preferring any entry the inventory found already installed, and otherwise the record's `## Tooling fallback`.

Running the selected tool is ecosystem bound too, and the front door hardcodes one ecosystem in the engine rather than in a lens: it instructs every subagent to run detection tooling ephemerally with `uv run --with <tool>`, which no TypeScript audit can follow. That instruction becomes: run the tool ephemerally by the idiom of the partition's package manager, which the inventory already records, and fall back to the record's `## Tooling fallback` when no ephemeral runner is available.

Language stays out of the record schema. A check such as import-graph cycles is neither a Python nor a TypeScript check; only its tooling is language bound, and the `tooling:` map already models exactly that. Adding a `language:` field to records would make language a property of the check, which is the wrong direction.

### 7. `not-applicable` joins `pass` and `no-evidence`

Three statuses that must never collapse into each other:

- `pass`: the check ran against this partition and found nothing.
- `no-evidence`: the check applies here and no tooling or fallback could run.
- `not-applicable`: the check has no lens in this partition's languages.

The front door already forbids reporting `pass` when every fallback fails. The inventory forces the third case, and collapsing it into `pass` is how a polyglot repository earns a clean bill of health for code nobody looked at. It also surfaces a quieter gap: dependency auditing on `<polyglot-monorepo-target>` has three declaration sites across two ecosystems, and nothing tells it to look for the second ecosystem at all.

### 8. The findings matrix carries a handbook citation

The step 2 matrix gains a `handbook` column populated from the check record's frontmatter, so no new source of truth appears. A record with an empty `handbook` list renders its `handbook_note` marked as deliberately beyond the handbook, which satisfies #7's allowance for a finding with no applicable clause structurally rather than as a special case. Citations are stable identifiers, matrix row ids and headings, never line numbers, which `audit-core` already requires of `handbook_note`.

### 9. The report header carries provenance, and the roll-up carries coverage

The header records the target's repository identity and ref, the lens provenance as `handbook-audit @ <short SHA>`, the tools that ran versus fell back per domain, and a stacks-present summary drawn from the inventory: the partitions, their languages, and whether each is tested and exercised in CI. It records repository identity and never a local filesystem path, because the report is a handover artifact and an absolute personal path does not belong in one.

The lens SHA is what lets #10 assert it audited with the plugin's copy rather than the fork that still lives in the audited repository.

The front door's roll-up table counts findings by severity, so a domain in which every check returned `no-evidence` reports zero of each severity and reads exactly like a domain that passed. On a foreign repository with none of the expected tooling installed that is the likely case rather than the exotic one. The table therefore gains a coverage column, checks run against `no-evidence` against `not-applicable`, and a verdict line that must lead with coverage whenever coverage is partial.

### 10. The domain headers stop assuming Python, and only the five that assume it are touched

Five descriptions assert that the skill audits a Python project: architecture, dependency, documentation, security and test. Four headers carry Python-specific `**Detect**` or domain-gate prose: architecture, dependency, security and test. The two sets overlap without coinciding, since the documentation header claims Python in its description alone while the other four carry both. That prose is generalised to read the inventory rather than name one ecosystem's tools, and the per-language tool names stay where they already live, in the records.

The CI, evaluation and prompt headers carry no ecosystem assumption and need no edit. This was verified rather than assumed, and the same search found no lidia-specific grounding anywhere in the family: no repository name, no product vocabulary, no named eval stack, no named workflow. #8's first criterion, a sweep of every domain skill for repo-specific assumptions, is therefore already largely met by the checks-database restructure. What remains of #8 is the path-based dispatch, the Python-only invocation mechanism, and the target root and ref.

## Testing

`superpowers:writing-skills` applies the Iron Law to edits, not only to new skills, and this pass edits seven skill files. It also supplies the calibration that makes that affordable: micro-test wording against a no-guidance control before running full scenarios, reserve pressure scenarios for genuine discipline failures, and stop if the control does not exhibit the failure. For most changes here the no-guidance control is the current skill, so the baseline is free.

| Change | Failure type | Test |
|---|---|---|
| the front door's path-based brief | factual defect | dispatch against the single-package target and watch it fail to find a lens or improvise from a neighbouring skills directory |
| `not-applicable` against `pass` | wrong-shaped output | a required status slot in the template, not a prohibition; fixture is a Python-only partition carrying a `package.json`, judged by a TypeScript-only check |
| the roll-up coverage column | omitted element | a required slot in the template |
| the eight header rewrites | reference retrieval | given a partition, is the right toolchain selected |
| the `out_path` refusal | discipline | a pressure scenario, the only change here that earns a prohibition and a rationalization table |

The last row is expected to fail hardest at baseline, because `audit-core` currently instructs the agent to save the report under the repository being audited. It is a rule the skill has to argue against its own earlier text, which is what makes it a discipline problem rather than a wording problem.

The three verification repositories play deliberately different roles, which is what makes a single PR defensible:

- `<single-package-target>` is the plumbing fixture: one partition, one language, and none of the expected TypeScript audit tooling installed, so every fallback path is exercised.
- `<polyglot-monorepo-target>` is the partition fixture: nine packages, mixed language sets, and tooling already present, so detect-before-prescribe and `not-applicable` are exercised together.
- `lidia-tech/lidia-agents` is the collision fixture: it confirms the qualified plugin name beats a project-level fork, which de-risks #10 before that issue starts.

Because this lands as one PR, `audit-core`'s per-item review runs per skill file as it changes and is verified against these fixtures, rather than once over the finished diff.

## Rejected

**An `arch/guest-stack` check flagging a minority language.** The polyglot signal is real, and every concrete cost it would report already has an owner: untested guest code belongs to the test domain's coverage checks, a stack CI never exercises to the CI domain's gate enforcement, an unlocked declaration file and an unscanned second vulnerability surface to the dependency domain. Restating those under an architecture heading double counts findings that the front door exists to consolidate. The judgment the check would exist to make, whether the host stack could replace the guest, depends on library availability and team capability and is not decidable from a repository snapshot. And it would carry no handbook citation, which is a warning rather than a convenience: the empty-`handbook` escape hatch is for checks that exceed the handbook on technical grounds, not for taste, and adding an uncited judgment check inside the PR that wires up citations argues against that PR. The aggregate observation is kept as the stacks-present summary in the report header, where it costs nothing and asserts nothing.

**A `skills_root` resolved and threaded through every dispatch.** Superseded by decision 2. Invoking the skill by its qualified name lets the harness resolve the location, so there is nothing to thread.

**A `language:` field on check records.** See decision 6. Language belongs to the code, not to the check.

**Per-domain language detection in each header.** Eight copies of one detector, re-derived per domain against the same tree and free to disagree, which is the failure the build-once rule exists to prevent. It would also re-scatter into the domain skills the mechanics the checks database just pulled out of them.

**Quoted clause text alongside each citation in the matrix.** Argued for on the grounds that a private repository's links do not resolve for an outside reader. Dropped: readers are expected to have repository access, and quoted prose inside a table row costs more in width than it returns.

## Follow-up to file separately

The handbook has no clause on runtime or stack count. A search of `docs/engineering/` for polyglot, multi-language and language-choice wording returns nothing, so a guest-stack finding has nothing to cite. That gap belongs in an issue against the handbook, not in this PR, which touches no handbook prose. If a clause lands and proves auditable from a snapshot, the check rejected above becomes reconsiderable, in that order.

## Files

- `.agents/skills/audit-core/SKILL.md`: step 0 resolutions, the inventory as the named ground-truth artifact, the three statuses, the citation column, the no-writes invariant and its check.
- `.agents/skills/audit/SKILL.md`: skill-invocation dispatch instead of a path, the ephemeral-runner instruction, the inventory built before the fan-out, the report header provenance and stacks summary, the roll-up coverage column.
- `.agents/skills/{arch,deps,security,test}-audit/SKILL.md`: the description, plus the Python-specific detect and gate prose.
- `.agents/skills/docs-audit/SKILL.md`: the description only.
- No change expected in the CI, evaluation and prompt headers, per decision 10.

## Issue reconciliation

#5, #7 and #8 stay open and are rewritten to their residue rather than closed and refiled, keeping the parent links wave 1 established. Two corrections go in with that rewrite: #5's criterion that each skill detect "the project language" becomes a per-partition language set, and #8 gains the requirement to capture and report the target ref.
