# Auditing a foreign repository - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the `*-audit` family able to audit a repository that is not this one, and make its findings cite the handbook, delivering [#8](https://github.com/mesagroup/ai-agent-development-handbook/issues/8) with the residue of [#5](https://github.com/mesagroup/ai-agent-development-handbook/issues/5) and [#7](https://github.com/mesagroup/ai-agent-development-handbook/issues/7).

**Architecture:** The audit runs with the audited repository as the working directory and the lenses supplied by the installed `handbook-audit` plugin. Nothing threads a skills path anywhere: subagents are dispatched to *invoke* `handbook-audit:<domain>-audit` by name, and the front door discovers its sibling domains through paths relative to its own skill directory. A project inventory, built once before the fan-out, carries per-partition language sets and already-installed tooling, which is what lets a check select a toolchain and lets a report distinguish "clean" from "we could not look".

**Tech Stack:** Markdown skill files under `.agents/skills/`, validated by `scripts/audit_checks.py` and `scripts/render_handbook_traceability.py`; pytest for the script tests; the `handbook-audit` Claude Code plugin for distribution.

## Global Constraints

Every task's requirements implicitly include this section.

- Spec: `docs/superpowers/specs/2026-08-05-audit-foreign-target-design.md`. Read it before starting any task.
- No em-dash (U+2014) anywhere under `docs/superpowers/`. Use ` - `.
- Markdown is never hard-wrapped: one paragraph is one source line. Never reflow a line you did not change.
- No environment-specific values in any committed file: no absolute local paths, personal profile names, hostnames or emails. Refer to the verification repositories by repository name only.
- The gate must stay green in every commit: `uv run python scripts/render_handbook_traceability.py --check` exits 0, and `uv run pytest tests/ -q` passes.
- Run `uv run ruff check . && uv run ruff format --check .` before committing any task that touched a `.py` file. No task in this plan is expected to touch one.
- Bare `#NNN` is an issue in this repository. An issue in the source repository is written `lidia-tech/lidia-agents#NNN`.
- Reference the issue in every commit message: `Refs #8`.
- Never assert a count you did not compute in the same breath.
- Do not merge anything. The PR is the deliverable.

## Baseline recorded before any change

Confirmed on branch `8-foreign-repo-audit-target` at the spec commit:

- `uv run pytest tests/ -q`: 129 passed.
- `uv run python scripts/render_handbook_traceability.py --check`: exit 0, no output.
- `scripts/audit_checks.py` parses only `checks/*.md` records. It never parses a `SKILL.md`. **Therefore no automated gate in this repository can detect a regression in the work this plan does.** The fixture scenarios in Task 7 are the only real verification, and skipping them means shipping unverified.

## File structure

| File | Responsibility after this plan |
|---|---|
| `.agents/skills/audit-core/SKILL.md` | the loop, and the contract every domain inherits: what step 0 resolves, the inventory as the named build-once artifact, the three statuses, the citation column, the no-writes invariant |
| `.agents/skills/audit/SKILL.md` | the sweep front door: sibling-relative domain discovery, dispatch by skill name, inventory built before the fan-out, the report template carrying provenance, coverage and citations |
| `.agents/skills/{arch,deps,security,test}-audit/SKILL.md` | each domain's lens, with its description and its detect/gate prose reading the inventory instead of naming one ecosystem |
| `.agents/skills/docs-audit/SKILL.md` | as above, description only |
| `CLAUDE.md` | records the task-management workflow this repository uses |

No file is created. No file is split. The two engine skills carry the contract; the domain headers carry only what varies by domain, which is the split the checks-database restructure already established.

---

### Task 1: Step 0 resolves the target, and the no-writes invariant becomes checkable

**Files:**
- Modify: `.agents/skills/audit-core/SKILL.md:20` (step 0), `:26` (step 2's save-the-report sentence), `:56-64` (cross-cutting rules)

**Interfaces:**
- Produces, for every later task and every domain skill: the names `target_root`, `target_ref` and `out_path`, the phrase "no writes to the target's working tree or git history", and the `git status --porcelain` before-and-after check. Later tasks and the front door refer to these names verbatim.

- [ ] **Step 1: Read the spec's decisions 3 and 4**

Read `docs/superpowers/specs/2026-08-05-audit-foreign-target-design.md`, sections "3. Step 0 resolves the target root, the target ref and the output path" and "4. The invariant is no writes to the target's working tree or git history". The wording below must not contradict them.

- [ ] **Step 2: Extend step 0 in `audit-core/SKILL.md`**

Step 0 currently begins `0. **Scope + mode.** Fix the subject (which package/tree/config) and the depth.` Keep that sentence and everything after it, and append these three bullets as a sub-list under step 0:

```markdown
   **Resolve the target, once, and record it.** An audit of another repository is the normal case, not the exception, so nothing may infer the subject from the working directory.
   - `target_root`: `git rev-parse --show-toplevel`, resolved to a real path. Every tool invocation and every glob is pathed at it. It often equals the working directory and nothing may *assume* that, because the assumption is what silently audits the wrong tree.
   - `target_ref`: the `HEAD` short SHA, the branch name, and whether the tree is dirty. A target checked out on a non-default branch is common, and a report that omits the ref neither reproduces nor maps onto what the audited team sees on their own default branch.
   - `out_path`: where the report file goes. **Ask for it, and refuse any path that resolves under `target_root`.** The consolidated report is always returned in conversation as well, so a run given no path is never silent. A non-interactive run defaults to conversation only and writes nothing.
```

- [ ] **Step 3: Fix the save-the-report sentence in step 2**

In step 2, this sentence tells the agent to write into the audited repository:

> Save the findings report under the repo (e.g. `docs/audit/<date>-<domain>-audit.md`) so it is itself linkable, and record any policy decisions so they are not re-litigated.

Replace it with:

> Write the findings report to the `out_path` resolved in step 0, never under `target_root`, and record any policy decisions so they are not re-litigated. When the target is this repository the two coincide and `docs/audit/<date>-<domain>-audit.md` is the conventional choice; when it is not, a report written into the audited tree turns a read-only audit into an uninvited commit on somebody else's branch.

- [ ] **Step 4: Add the invariant to the cross-cutting rules**

The `## Cross-cutting rules (all domains)` list currently ends with the `**Project-agnostic.**` bullet. Insert this bullet immediately before it:

```markdown
- **No writes to the target's working tree or git history.** Not "do not touch the target": the emitter may later create issues in the audited project's tracker, which leaves the working tree untouched, and a rule worded too broadly would have to be broken instead of kept. Check it rather than promise it: capture `git status --porcelain` at `target_root` when scope is fixed and again after the matrix is built, and report any delta as a defect of the audit run. This catches the accidental case, because a package manager asked only to read will write a cache or a lockfile into the tree given the chance.
```

- [ ] **Step 5: Verify the gate and the rules**

Run: `uv run python scripts/render_handbook_traceability.py --check && uv run pytest tests/ -q`
Expected: exit 0, 129 passed.

Run: `grep -cP '\x{2014}' .agents/skills/audit-core/SKILL.md`
Expected: `1`. The description on line 3 already contains em-dashes and is pre-existing; the rule covers `docs/`, not the skills tree, so do not reflow or "fix" it. Confirm your added prose contributed none by checking that the count did not rise.

- [ ] **Step 6: Commit**

```bash
git add .agents/skills/audit-core/SKILL.md
git commit -m "feat(audit-core): resolve the audit target in step 0 and check the no-writes invariant

An audit of another repository could not state which repository it audited,
at which ref, and had nowhere to put its report except inside the tree it
promised not to modify. Step 0 now resolves target_root, target_ref and
out_path, and the no-writes rule is checked with git status rather than
promised in prose.

Worded as no writes to the working tree or git history, not as do not touch
the target, so the issue emitter in #9 extends the family without breaking a
rule stated here.

Refs #8"
```

---

### Task 2: The project inventory, the three statuses, and the citation column

**Files:**
- Modify: `.agents/skills/audit-core/SKILL.md:22-24` (step 1), `:26` (step 2), `:64` (the project-agnostic bullet)

**Interfaces:**
- Consumes from Task 1: `target_root`, `target_ref`.
- Produces, for Tasks 3 to 6: the term **project inventory** and its fields (per partition: path, language set, package manager and lockfile, test runner, already-installed audit tooling; per repository: target root, target ref, dirty flag, monorepo tool and workspace globs, CI workflow list); the status names `pass`, `no-evidence` and `not-applicable`; the `handbook` matrix column.

- [ ] **Step 1: Name the inventory in step 1's build-once rule**

Step 1's second paragraph currently reads, in part:

> Build any shared ground-truth artifact (a parsed graph, a resolved dependency tree, a coverage map) **once** and let agents consume it, rather than each rebuilding a possibly-inconsistent copy.

Immediately after that sentence, insert:

```markdown
**The first such artifact is always the project inventory**, and it is the one every domain needs: per repository the `target_root`, the `target_ref`, the dirty flag, the monorepo tool and its workspace globs, and the CI workflow list; per partition the path, the **language set**, the package manager and lockfile, the test runner, and which audit-relevant tools the partition already has. A partition's language is a set and never a single value, and a manifest is not a language detector: a package that carries a JavaScript manifest for monorepo wiring while containing only Python is classified as JavaScript by any "has a manifest, therefore" rule, whereupon the wrong toolchain runs against no matching source, finds nothing, and reports a pass. Detect by a file census plus declaration files. The already-installed field is what gives every record's "detect before it prescribes" an input, because nothing else computes what the target already runs.
```

- [ ] **Step 2: Add the two non-pass statuses to step 2**

Step 2 currently says:

> Status is a small fixed scale the domain defines (e.g. pass / partial / fail, or ok / warn / violation).

Append to that sentence, in the same paragraph:

```markdown
Whatever scale the domain picks, three outcomes are distinct and must never collapse into one another: **`pass`** means the check ran against this partition and found nothing, **`no-evidence`** means the check applies here and no tooling or fallback could run, and **`not-applicable`** means the check has no lens in this partition's languages. Reporting `no-evidence` as `pass` reports absence of tooling as absence of findings; reporting `not-applicable` as `pass` is how a polyglot repository earns a clean bill of health for code nobody looked at.
```

- [ ] **Step 3: Add the citation column to the findings matrix**

Step 2 opens:

> 2. **Build the findings matrix.** Consolidate the evidence into a table: **item × check × status × severity**, plus a one-line evidence pointer (`file:line`, tool output, or metric) for every row.

Change `**item × check × status × severity**` to `**item × check × status × severity × handbook**`, and after the evidence-pointer clause add:

```markdown
The `handbook` cell is read from the check record's `handbook:` frontmatter, so the matrix introduces no new source of truth; a record carrying an empty list renders its `handbook_note` instead, marked as deliberately beyond the handbook. Cite a stable identifier, a matrix row `id` or a heading, never a line number, for the reason the record schema already gives.
```

- [ ] **Step 4: Generalise the project-agnostic bullet**

The last cross-cutting bullet names one ecosystem's manifest:

> - **Project-agnostic.** Discover packages/layout/tooling/conventions from the target repo (`pyproject.toml`, contributor guide, existing config); impose a standard only if none exists, and confirm it with the user.

Replace the parenthetical so it does not privilege one ecosystem:

> - **Project-agnostic.** Discover packages/layout/tooling/conventions from the target repo via the project inventory (its manifests and lockfiles, whatever they are, plus the contributor guide and existing config); impose a standard only if none exists, and confirm it with the user.

- [ ] **Step 5: Verify**

Run: `uv run python scripts/render_handbook_traceability.py --check && uv run pytest tests/ -q`
Expected: exit 0, 129 passed.

Run: `grep -n 'not-applicable' .agents/skills/audit-core/SKILL.md`
Expected: at least one hit, in step 2.

- [ ] **Step 6: Commit**

```bash
git add .agents/skills/audit-core/SKILL.md
git commit -m "feat(audit-core): name the project inventory, split pass from not-applicable, cite the handbook

Step 1 already required building a shared ground-truth artifact once. The
project inventory is the canonical instance, so naming it adds no stage to
the loop and gives per-partition language and already-installed tooling a
single home. That is what a per-language tooling map needs in order to be
selected between, and what detect-before-prescribe needs as an input.

not-applicable is separated from pass because a polyglot repository would
otherwise pass every check whose lens does not exist in one of its
languages. The findings matrix gains a handbook column read from record
frontmatter, so a finding cites the standard it violates.

Refs #8"
```

---

### Task 3: The front door stops resolving lens paths inside the audited repository

**Files:**
- Modify: `.agents/skills/audit/SKILL.md:28` (scope detection), `:34` (the subagent brief)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: the dispatch form `handbook-audit:<domain>-audit` and the sibling-relative discovery path `../<domain>-audit/checks/`, both relied on by Task 4.

- [ ] **Step 1: Reproduce the defect (RED), and record what you saw**

Both defects are on paths relative to a repository root, which resolve inside the *audited* repository. Confirm the ground truth first, from this repository, without editing anything:

```bash
git -C <target-clone> rev-parse --show-toplevel
ls -d <target-clone>/.agents/skills 2>/dev/null || echo "absent"
ls -d <target-clone>/.agents/skills/*-audit 2>/dev/null || echo "no audit domains"
```

Run it against both verification clones. Expected, and already observed at plan time: the single-package Next.js target has no `.agents/skills` at all, and the pnpm monorepo target has one holding that project's own skills and no `*-audit` directory. So step 0's rule "a domain is available when `.agents/skills/<domain>-audit/checks/` exists" yields **zero** available domains against either target, and step 0's parenthetical "project-agnostic; a repo may have a subset" reads that empty result as legitimate rather than as a failure. Neither target can be swept at all, and both fail silently. Write the observed output into the PR description later; it is the RED evidence for this task.

- [ ] **Step 2: Fix domain discovery to read the family, not the target**

In step 0's scope bullet, replace:

> **Detect which domains are available from the checks tree**: a domain is available when `.agents/skills/<domain>-audit/checks/` exists and holds at least one record (project-agnostic; a repo may have a subset).

with:

> **Detect which domains are available from this skill's own siblings**, at `../<domain>-audit/checks/` relative to this skill's directory: a domain is available when that directory exists and holds at least one record. Resolve it relative to *this skill*, never to the audited repository, because a path relative to a repository root resolves inside the target: it finds nothing in a repository that has never carried the family, or the target's own copy in one that has, and either way the sweep reports a scope it did not audit. The audited repository's own skills, if it has any, are evidence for the prompt domain and are never the lens.

- [ ] **Step 3: Fix the subagent brief to invoke the skill rather than read a path**

Replace the whole first bullet of step 1, which currently reads:

> - The repo root and the one line: "Read the `.agents/skills/<domain>-audit/SKILL.md` header and `.agents/skills/audit-core/SKILL.md`, then load the records from `.agents/skills/<domain>-audit/checks/` that your audit needs - all of them for a small domain, or fan out internally by `locality` (the `local` records per partition, one `global` check per sub-agent) for a large one - and execute that audit on THIS repo in REPORT-ONLY mode, through the findings-matrix step only."

with:

> - `target_root`, `target_ref`, and the one line: "**Invoke the `handbook-audit:<domain>-audit` skill**, then load the records from its `checks/` directory that your audit needs - all of them for a small domain, or fan out internally by `locality` (the `local` records per partition, one `global` check per sub-agent) for a large one - and execute that audit against `target_root` in REPORT-ONLY mode, through the findings-matrix step only." **Pass no path to the lens.** Invoking the skill by name lets the harness resolve where the family is installed and hand the skill its own base directory, from which its `checks/` resolve; a path relative to a repository root resolves inside the audited repository instead. Qualifying the name with the plugin also stops a same-named project-level skill in the target from shadowing the lens under audit.

- [ ] **Step 4: Verify no repo-root-relative lens path survives**

Run: `grep -n '\.agents/skills' .agents/skills/audit/SKILL.md`
Expected: no hit that instructs an agent to read a lens. A hit inside prose *explaining* why such a path is wrong is correct and expected.

Run: `uv run python scripts/render_handbook_traceability.py --check && uv run pytest tests/ -q`
Expected: exit 0, 129 passed.

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/audit/SKILL.md
git commit -m "fix(audit): stop resolving lens paths inside the audited repository

Two paths in the front door were relative to a repository root, which works
only while the lenses and the audited code are the same tree. Against a
foreign target both resolve inside the target.

Domain discovery found no *-audit directory in either verification clone, so
step 0 reported zero available domains and swept nothing, and its own
parenthetical read that empty result as a legitimate subset rather than a
failure. The dispatch brief would have found nothing, or in a repository that
still carries a copy of the family would have loaded that fork.

Both now resolve relative to this skill: discovery reads ../<domain>-audit/
checks/, and subagents are told to invoke handbook-audit:<domain>-audit by
name so the harness resolves the install location. Qualifying with the plugin
name also stops a same-named project skill in the target shadowing the lens.

Refs #8"
```

---

### Task 4: The inventory reaches the domains, and tools run by the target's idiom

**Files:**
- Modify: `.agents/skills/audit/SKILL.md:33` (the dispatch preamble), `:35` (per-domain grounding), `:37` (ephemeral tooling and the no-evidence rule)

**Interfaces:**
- Consumes: the project inventory and the three statuses from Task 2; the dispatch form from Task 3.
- Produces: the guarantee that every domain subagent receives the inventory rather than building its own.

- [ ] **Step 1: Build the inventory before the fan-out**

Step 1's preamble currently reads:

> Dispatch all selected domains **concurrently** (a barrier - collect the matrices before consolidating; a domain that errors does **not** block the others). Give each subagent:

Insert before it:

```markdown
**Build the project inventory first, once, and pass it to every domain.** It is `audit-core` step 1's shared ground-truth artifact, and the sweep is where the saving is largest: eight domain agents would otherwise each re-derive the same partition and language map over the same tree, and be free to disagree about it. Building it here also means a domain that needs only one field of it does not pay to discover that field itself.
```

- [ ] **Step 2: Replace the ad hoc grounding bullet with the inventory**

Replace:

> - Any repo-specific grounding the domain needs (declared architecture rules for arch, the eval stack location for eval, the workflow list for ci, etc.) - a short pointer, not a pasted lens.

with:

> - **The project inventory**, which supersedes the per-domain list of grounding this bullet used to enumerate: the partitions and their language sets, the package managers and lockfiles, the test runners, the already-installed tooling, and the CI workflow list. One artifact rather than a list that had to grow with every new domain. Add only grounding the inventory does not carry, such as a declared architecture rule the user states, and pass it as a short pointer rather than a pasted lens.

- [ ] **Step 3: Generalise the ephemeral runner and add `not-applicable`**

The tooling bullet currently hardcodes one ecosystem's runner and knows only one non-pass status:

> - Instruction to run the domain's detection tooling ephemerally (`uv run --with <tool> …`) with the domain skill's fallbacks, and to **verify each finding against the real artifact** (source→sink, `file:line`, tool output) so scanner artifacts don't become findings. **If every fallback for a check fails (no network, tool won't install), mark that check `no-evidence` - never `pass`** - so absence of tooling is not reported as absence of findings.

Replace it with:

> - Instruction to run the domain's detection tooling **ephemerally, by the idiom of the partition's package manager as recorded in the inventory** (for example `uv run --with <tool>` for a Python partition, or the equivalent one-shot runner for a JavaScript one), preferring any tool the inventory reports already installed, and falling back to the record's `## Tooling fallback` when no ephemeral runner is available. Hardcoding one ecosystem's runner here would make every other ecosystem's tooling unrunnable no matter what the records say. And to **verify each finding against the real artifact** (source→sink, `file:line`, tool output) so scanner artifacts don't become findings. **If every fallback for a check fails (no network, tool won't install), mark that check `no-evidence` - never `pass`; if the check has no lens in the partition's languages, mark it `not-applicable` - also never `pass`** - so neither absence of tooling nor absence of a lens is reported as absence of findings.

- [ ] **Step 4: Verify**

Run: `grep -c 'uv run --with' .agents/skills/audit/SKILL.md`
Expected: `1`, and it must now sit inside the "for example" clause rather than being the prescribed mechanism. Read the line to confirm.

Run: `uv run python scripts/render_handbook_traceability.py --check && uv run pytest tests/ -q`
Expected: exit 0, 129 passed.

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/audit/SKILL.md
git commit -m "feat(audit): pass one inventory to every domain and run tools by the target's idiom

The front door enumerated per-domain grounding in a list that had to grow
with every new domain, and told every subagent to run tooling with a
Python-only ephemeral runner. The second is why per-language tooling in the
records was unreachable: no amount of TypeScript entries is runnable through
uv run --with.

The inventory is now built once before the fan-out and passed to all eight
domains, so they cannot disagree about the partition and language map, and
the runner is chosen from the partition's package manager. not-applicable
joins no-evidence as a status the sweep must not report as pass.

Refs #8"
```

---

### Task 5: The report says which repository it audited, with which lenses, and how much it saw

**Files:**
- Modify: `.agents/skills/audit/SKILL.md:53` (the Markdown output path), `:57` (the report-artifact justification), `:78-82` (roll-up table), `:93` (per-domain matrix header), `:96-99` (how the audit ran), `:107-110` (cross-cutting rules)

**Interfaces:**
- Consumes: `target_root`, `target_ref`, `out_path` from Task 1; the inventory and the three statuses from Task 2.
- Produces: the final report shape. No later task depends on it.

- [ ] **Step 1: Point the Markdown output at `out_path`**

Replace:

> - **Markdown file** - write the report to `docs/audit/<YYYY-MM-DD>-repo-audit.md` (or the project's audit dir). This is the durable, linkable, diff-able record; recommended default.

with:

> - **Markdown file** - write the report to the `out_path` resolved in scope, which is never under `target_root`. This is the durable, linkable, diff-able record; recommended default. When the audit target is this repository, `docs/audit/<YYYY-MM-DD>-repo-audit.md` is the conventional choice.

- [ ] **Step 2: Correct the justification that contradicts the invariant**

This clause is now wrong, because the audited repository is usually not ours:

> Emit every format the user selects (writing an output file in report-only mode is fine - it is a report artifact, not a change to the audited code).

Replace the parenthetical:

> Emit every format the user selects (writing an output file in report-only mode is fine **provided it lands outside `target_root`** - it is a report artifact, and inside the audited tree it would instead be an uninvited change to somebody else's branch).

- [ ] **Step 3: Add a coverage column to the roll-up**

The template's roll-up counts findings only, so a domain that could not run anything reports zero of each severity and reads exactly like a domain that passed. Replace:

```markdown
## Severity roll-up
| Domain | Critical | Important | Minor | One-line verdict |
|---|---|---|---|---|
| <domain> | n | n | n | <pass/warn/fail + gist> |
| ... |
| **Total** | **n** | **n** | **n** | |
```

with:

```markdown
## Severity roll-up
| Domain | Critical | Important | Minor | Coverage (ran / no-evidence / n-a) | One-line verdict |
|---|---|---|---|---|---|
| <domain> | n | n | n | n / n / n | <pass/warn/fail + gist> |
| ... |
| **Total** | **n** | **n** | **n** | **n / n / n** | |
```

And immediately under the table, add:

```markdown
Coverage is not optional decoration. A domain whose every check returned `no-evidence` shows zero findings at every severity, which is indistinguishable from a clean domain in a severity-only table, and on a foreign repository with none of the expected tooling installed that is the likely case rather than the exotic one. **When coverage is partial, the one-line verdict must lead with coverage**, not with the finding count.
```

- [ ] **Step 4: Carry the citation into the per-domain matrix**

Replace:

> <the domain's findings matrix: Item | Check | Status | Severity | Evidence - capped to the significant rows>

with:

> <the domain's findings matrix: Item | Check | Status | Severity | Evidence | Handbook - capped to the significant rows>

- [ ] **Step 5: Add provenance and the stacks summary to "How the audit ran"**

Replace the whole block:

```markdown
## How the audit ran
- Scope: <domains run> · Mode: report-only
- Per-domain tool log: <ran / fell back> (one line each)
- Verification note: <any false positives caught and discarded>
```

with:

```markdown
## How the audit ran
- Target: <repository identity> at <short SHA> on <branch><, working tree dirty if it was>
- Lenses: handbook-audit @ <short SHA>
- Scope: <domains run> · Mode: report-only
- Stacks present: <partition: languages, tested yes/no, in CI yes/no> (one line each)
- Per-domain tool log: <ran / fell back / no runner available> (one line each)
- Verification note: <any false positives caught and discarded>
- Target tree unchanged: <yes, or the git status delta observed>
```

Record repository identity and never a local filesystem path: the report is a handover artifact, and an absolute personal path does not belong in one. The lens SHA is what lets a re-run prove which copy of the family produced the findings, which matters in a target that carries its own copy.

- [ ] **Step 6: Correct the two cross-cutting rules that assume our own repository**

Replace:

> - **Report-only means read-only for the audited code.** The only files this skill may write are the report artifacts in step 3.

with:

> - **Report-only means no writes to the target's working tree or git history.** The only files this skill may write are the report artifacts in step 3, and they land outside `target_root`. Verify it rather than assert it, per `audit-core`'s invariant: `git status --porcelain` at the target before and after.

And in the project-agnostic bullet, replace `never hardcode a fixed seven` with `never hardcode a fixed set, and detect the domains from this skill's own siblings rather than from the audited repository`.

- [ ] **Step 7: Verify**

Run: `uv run python scripts/render_handbook_traceability.py --check && uv run pytest tests/ -q`
Expected: exit 0, 129 passed.

Run: `grep -n 'Coverage (ran' .agents/skills/audit/SKILL.md && grep -n 'Handbook' .agents/skills/audit/SKILL.md`
Expected: one hit each.

- [ ] **Step 8: Commit**

```bash
git add .agents/skills/audit/SKILL.md
git commit -m "feat(audit): report which repository was audited, with which lenses, and how much was seen

The roll-up counted findings by severity only, so a domain whose every check
returned no-evidence reported zero of everything and read exactly like a
domain that passed. On a foreign repository with none of the expected tooling
installed that is the likely case, so the table now carries coverage and a
partial-coverage verdict must lead with it.

The header now names the target repository and ref and the lens SHA, which is
what distinguishes a run against a repository that carries its own copy of
the family from a run against the installed plugin. Report output moves to
out_path, and the clause justifying a write into the audited tree is
corrected: that reasoning held only while the audited repository was ours.

Refs #8"
```

---

### Task 6: The domain headers stop asserting one ecosystem

**Files:**
- Modify: `.agents/skills/arch-audit/SKILL.md:3,28,30`; `.agents/skills/deps-audit/SKILL.md:3,18,21,27`; `.agents/skills/security-audit/SKILL.md:3,23`; `.agents/skills/test-audit/SKILL.md:3,20,26`; `.agents/skills/docs-audit/SKILL.md:3`

**Interfaces:**
- Consumes: the project inventory from Task 2, which these headers now tell the agent to read instead of naming one ecosystem's tools.
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Confirm the edit set rather than trusting this plan**

Run:

```bash
for f in .agents/skills/*-audit/SKILL.md; do sed -n '3p' "$f" | grep -q Python && echo "description: $f"; done
grep -ln 'bandit\|pip-audit\|pytest\|vulture\|import-linter\|deptry\|pyproject' .agents/skills/*-audit/SKILL.md
```

Expected, and observed at plan time: five descriptions (architecture, dependency, documentation, security, test) and four files carrying ecosystem-specific detect or gate prose (architecture, dependency, security, test). The two sets overlap without coinciding: the documentation header claims Python in its description alone. If what you observe differs, the tree has moved since this plan was written; follow what you observe and say so in the PR.

- [ ] **Step 2: Correct the five descriptions**

In each of the five, remove the claim that the subject must be a Python project, keeping every other clause intact. Apply these exact substitutions:

- architecture: `Audit a Python project's structure:` becomes `Audit a project's structure:`, and `Works on any Python project.` becomes `Works on any codebase; per-language tooling comes from the check records.`
- dependency: `Audit a Python project's third-party dependency surface:` becomes `Audit a project's third-party dependency surface:`
- documentation: `Works on any Python project.` becomes `Works on any codebase.`
- security: `Audit a Python project's first-party code` becomes `Audit a project's first-party code`, and `Works on any Python project.` becomes `Works on any codebase; per-language tooling comes from the check records.`
- test: `Audit a Python project's automated tests:` becomes `Audit a project's automated tests:`, and `Works on any Python project.` becomes `Works on any codebase; per-language tooling comes from the check records.`

Keep each description under the 1024-character frontmatter limit and do not restructure it: a description that summarises the workflow causes an agent to follow the summary instead of reading the skill.

- [ ] **Step 3: Point the detect prose at the inventory**

In each of the four files carrying it, the `**Detect**` sentence enumerates one ecosystem's tools. Rewrite each so the ecosystem-specific list is an example read from the inventory rather than the definition. The pattern, applied to the dependency header's `**Detect** the project's package manager (`uv` / `pip` / `poetry` - check for `uv.lock`, `poetry.lock`, `requirements*.txt`) and use its resolved graph as ground truth`:

> **Detect** the package manager and lockfile from the project inventory, which already records both per partition, and use its resolved graph as ground truth (transitive deps matter - most CVEs and copyleft licenses arrive transitively). A partition may declare dependencies in an ecosystem the rest of the repository does not use, and each declaration site is its own graph: a repository with a JavaScript lockfile and two Python requirements files has three, and auditing only the first reports the other two as clean.

Apply the same move to the architecture, security and test headers: keep the domain's judgment, replace "check `pyproject.toml`" style instructions with "read the inventory", and keep concrete tool names only as examples. The per-language tool lists stay in the records, which is where they already live.

- [ ] **Step 4: Generalise the domain-gate prose**

Where a gate names one ecosystem's commands, state the gate's *property* and let the inventory supply the command. For the architecture header's `the domain gate is "imports resolve, the type checker passes, **and** the test suite passes" - run the normal install + lint/typecheck/test CI`, keep the sentence and append: `Take the actual commands from the inventory's package manager and test runner rather than assuming one ecosystem's.` Leave the opt-in deliverables naming `import-linter` / `tach` as they are, but add ` (or the detected language's equivalent layering-contract tool)` so the deliverable is not defined as Python-only.

- [ ] **Step 5: Verify**

Run: `for f in .agents/skills/*-audit/SKILL.md; do sed -n '3p' "$f" | grep -q Python && echo "STILL CLAIMS PYTHON: $f"; done; echo done`
Expected: only `done`.

Run: `uv run python scripts/render_handbook_traceability.py --check && uv run pytest tests/ -q`
Expected: exit 0, 129 passed.

- [ ] **Step 6: Commit**

```bash
git add .agents/skills/arch-audit/SKILL.md .agents/skills/deps-audit/SKILL.md .agents/skills/security-audit/SKILL.md .agents/skills/test-audit/SKILL.md .agents/skills/docs-audit/SKILL.md
git commit -m "feat: stop the domain headers asserting the subject is a Python project

Five descriptions claimed a Python project and four headers named one
ecosystem's tools in their detect and gate prose. The sets overlap without
coinciding, so both were checked against the tree rather than assumed.

The prose now reads the project inventory for the package manager, lockfile
and test runner, and keeps concrete tool names only as examples. Per-language
tool lists stay in the check records, where the checks database already put
them. The dependency header additionally states that each declaration site is
its own graph, because a repository with one JavaScript lockfile and two
Python requirements files has three and auditing one reports two as clean.

The CI, evaluation and prompt headers carry no ecosystem assumption and are
untouched.

Refs #8, #5"
```

---

### Task 7: Verify against the three fixtures

**Files:**
- Modify: none. This task produces evidence, and any fix it forces belongs in the task that introduced the defect.

**Interfaces:**
- Consumes: every preceding task.
- Produces: the RED-then-GREEN evidence that goes in the PR description.

- [ ] **Step 1: Make the edited lenses the installed lenses**

The plugin cache holds copies pinned by commit SHA, so the working tree's edits are **not** what an audit would load. Push the branch, then point the plugin at it and confirm discovery:

```bash
git push -u origin 8-foreign-repo-audit-target
claude plugin details handbook-audit
```

Read the reported skill count. `claude plugin validate` checks only the manifest and passes on a plugin that discovers no skills, so the count is the check that matters. If the installed copy is still an older SHA, reinstall or update the plugin to this branch before continuing; verifying against a stale cache proves nothing about this branch and is the same class of mistake as the path defect this PR fixes.

- [ ] **Step 2: The plumbing fixture, on the single-package target**

With the single-package Next.js clone as the working directory, run the sweep report-only, giving an output path outside that repository. Confirm, and capture for the PR:

- domains are discovered (the RED baseline discovered zero)
- the report header names the target repository, its short SHA and its branch, which is not that repository's default branch
- checks with no TypeScript lens report `not-applicable` and never `pass`
- checks whose tooling could not install report `no-evidence` and never `pass`, and the roll-up's coverage column shows them
- `git -C <target> status --porcelain` is byte-identical before and after

- [ ] **Step 3: The polyglot fixture, on the monorepo target**

Repeat against the pnpm monorepo clone. This one exercises what the single-package target cannot. Confirm:

- partitions are enumerated, and the Python-only package that carries a JavaScript manifest is classified by its language set rather than by the manifest, so TypeScript tooling is not run against it and it does not report `pass`
- the package holding both a large TypeScript surface and a nested Python function is reported as both languages
- the architecture domain prefers the layering tool the target already has installed over installing its own, per detect-before-prescribe
- the dependency domain finds all three declaration sites across two ecosystems, not just the JavaScript lockfile
- the stacks-present summary in the header lists each partition with its languages and whether it is tested and in CI
- `git status --porcelain` unchanged

- [ ] **Step 4: The collision fixture**

With the clone that still carries its own copy of the audit family as the working directory, run one domain and confirm from the report header's lens SHA that the **plugin's** copy ran, not the repository's. This is the check that makes the dry run in #10 meaningful; if the local copy wins, the qualified name is not doing its job and Task 3 needs revisiting.

- [ ] **Step 5: The one discipline scenario**

`audit-core` used to instruct the agent to save the report under the audited repository, so an agent told "write me a report" with no path given is under real pressure to write inside the target. Run that scenario against a fixture and confirm the run refuses the in-target path and either asks or returns the report in conversation. If it writes into the target, the wording in Task 1 lost to the pressure and needs the prohibition-plus-rationalization treatment `superpowers:writing-skills` prescribes for a discipline failure.

- [ ] **Step 6: Record the evidence**

Write what each fixture showed into the PR description, including the RED baseline from Task 3 step 1. A verification claim with no captured output is the failure `audit-core`'s own core principle forbids.

- [ ] **Step 7: Commit any fixes the fixtures forced**

If a fixture forced a change, commit it against the task that owned the defect, one commit per fix, with the fixture output quoted in the message. If nothing needed fixing, there is nothing to commit here.

---

### Task 8: Reconcile the issues and record the workflow

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: the outcome of Task 7, because acceptance criteria may only be ticked once verified.
- Produces: nothing.

- [ ] **Step 1: Record the task-management workflow in `CLAUDE.md`**

`CLAUDE.md` documents the issue-reference convention but not the workflow, so a fresh session has to ask. Add a short `## Task management` section stating that this repository uses the `github-issues-workflow` skill: an issue per unit of work, a branch named `<number>-short-description`, `status:*` labels tracking progress, `Refs #<number>` in commits, and no merge without explicit approval. Keep it to a few lines and do not restate the skill.

- [ ] **Step 2: Rewrite #5 to its residue**

Edit the body of #5 so its acceptance criteria describe what is left rather than what wave 1 already did. It must state that per-language `tooling:` entries already exist in the check records, that what was missing is anything selecting between them, and it must correct the criterion "each domain skill detects the project language" to a **per-partition language set**, since one repository can be polyglot and one partition can be two languages. Keep the issue open and keep its labels.

- [ ] **Step 3: Rewrite #7 to its residue**

Edit the body of #7 to state that the `handbook:` lists and their bidirectional validation already exist, and that what was missing is the matrix column and the front door carrying it into the consolidated report. Keep its criterion allowing a finding with no applicable clause, noting it is satisfied structurally by the empty-list plus `handbook_note` form.

- [ ] **Step 4: Rewrite #8 to its residue**

Edit the body of #8 to record that the sweep for repository-specific assumptions is already largely met, because no lidia-specific grounding remains anywhere in the family, and that what remains is the two repo-root-relative paths, the Python-only ephemeral runner, and the target root and ref. Add a criterion for capturing and reporting the target ref, which the issue does not currently ask for.

- [ ] **Step 5: File the handbook gap**

Open a new issue against the handbook: it has no clause on runtime or stack count, so a finding about a casually-wired second stack has nothing to cite. State that a search of `docs/engineering/` for polyglot, multi-language and language-choice wording returns nothing. Note that the `arch/guest-stack` check was considered and rejected in this PR's spec, and that it becomes reconsiderable only if a clause lands **and** proves auditable from a repository snapshot. Label it `enhancement` and `normal`.

- [ ] **Step 6: Tick only what was verified**

In each of #5, #7 and #8, tick only the acceptance criteria Task 7 actually verified, and leave the rest. Post a release-notes-style comment on #8 summarising what shipped.

- [ ] **Step 7: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: record the task-management workflow this repository uses

CLAUDE.md documented the issue-reference convention but not the workflow, so
every fresh session had to ask which one to follow before it could start.

Refs #8"
```

---

## Self-review

**Spec coverage.** Decision 1 (posture) needs no edit and is realised by Task 3's dispatch form. Decision 2 (invoke, do not path) is Task 3. Decision 3 (step 0 resolutions) is Task 1. Decision 4 (invariant) is Task 1 step 4 and Task 5 step 6. Decision 5 (inventory) is Task 2 step 1 and Task 4 steps 1 to 2. Decision 6 (language is a set; ephemeral runner) is Task 2 step 1 and Task 4 step 3. Decision 7 (three statuses) is Task 2 step 2 and Task 4 step 3. Decision 8 (citation column) is Task 2 step 3 and Task 5 step 4. Decision 9 (provenance, coverage) is Task 5 steps 3 and 5. Decision 10 (headers) is Task 6. The spec's Testing section is Task 7. The spec's issue-reconciliation section is Task 8.

**One thing the spec did not have.** The front door's step 0 domain-discovery path is a second instance of the same defect and is not in the spec, which named only the dispatch brief. It is the more damaging of the two, because it makes the sweep a silent no-op that its own prose rationalises as a legitimate subset. It is fixed in Task 3 step 2, and the spec should be amended to record it.

**Ordering.** No task consumes a later task's output. Task 1 establishes the vocabulary Tasks 2 and 5 use; Task 2 establishes the inventory Tasks 4 and 6 consume; Task 3 is independent of both and could run first, but is placed after the engine contract so a reviewer reads the contract before its first consumer. Task 7 verifies everything and therefore runs last but for the bookkeeping.

**Gate honesty.** Every task's verification runs the test suite and the traceability gate, and neither can fail from these edits, because the validator never parses a `SKILL.md`. They are regression insurance, not proof. Task 7 is the proof, and a reviewer should treat a PR that skipped it as unverified regardless of a green CI badge.
