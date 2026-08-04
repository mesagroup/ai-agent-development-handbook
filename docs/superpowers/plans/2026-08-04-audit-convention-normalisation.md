# Audit Family Convention Normalisation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Normalise the eight audit domain headers, the 68 check records, the two shared skill files and the traceability matrix's judgment prose onto one settled shape, and lock the two mechanically-checkable conventions behind tests.

**Architecture:** Issue #567's eight items, regrouped into seven tasks by *file set* rather than by item, because several items touch the same file and a file must be owned by exactly one task. Nothing here changes behaviour: every edit is prose, with the single exception of Task 7, which adds two structural tests.

**Tech Stack:** Markdown, YAML, Python (pytest) for the convention tests only.

## Global Constraints

Copied verbatim into every task's dispatch.

- **Work in `<worktree-root>`**, the absolute path of the worktree this plan is executed from. The dispatcher resolves it once with `git rev-parse --show-toplevel` and interpolates it into every task dispatch; each agent confirms its own `git rev-parse --show-toplevel` matches before reading or editing anything. Do not `cd` to the primary checkout.
- **Never pass a line starting with `#` to the Bash tool.**
- **Never `git add -A`, `git add .`, or `git commit -a`.** Run `git status --short`, then `git add` the exact paths you changed.
- **This is a normalisation pass, not a rewrite.** The claim a sentence makes must survive the edit unchanged. You are changing *form* - where a sentence sits, what label it carries, which dash it uses, which noun names a check - never *what it asserts*. The one exception is explicitly scoped in Tasks 5 and 6: a sentence whose assertion is now false against the checks tree must be corrected, and every such correction must be listed in your report.
- **No em-dash (`—`) in any file this plan writes.** Use ` - `. The only exception is a skill's `description:` frontmatter string, which is the skill-discovery surface and is never touched by this plan.
- **Markdown: one paragraph per source line.** Never hard-wrap prose, and never reflow a neighbouring line you did not otherwise change. A diff that reflows untouched lines hides the real change and will be rejected.
- **No environment-specific values** in committed files: no absolute personal paths, AWS/browser profile names, hostnames, emails, bucket names.
- **Every commit runs `uv run ruff check .` and `uv run ruff format --check .` clean** before it is made. Run `uv run pyright` for any task touching `scripts/` or `tests/`.
- **The domain gate for every task is:** `uv run pytest tests/scripts/ -q` green **and** `uv run python scripts/render_handbook_traceability.py --check` exit 0.
- **Re-render the Markdown view** with `uv run python scripts/render_handbook_traceability.py` in any task that edits `docs/audit/handbook-traceability.yaml`, and commit both files together.
- **Reference the issue in every commit message:** `Refs #567`. No Claude credits, no co-author trailers naming an assistant.
- **Do not open a PR and do not merge.** The controller handles both.

## Shared reference artifacts

Two files are built once by the controller and handed to Tasks 5 and 6 by path. Do not rebuild them.

- **`<scratchpad>/crosswalk.txt`** - the 37 legacy `{skill, dimension}` pairs PR #566 rewired, each mapped to the check id that replaced it. Derived mechanically by diffing the pre-migration matrix (commit `29499564`) against the current one, so it is evidence, not reconstruction.
- **`<scratchpad>/record-index.txt`** - all 68 records: `<id>  <locality>  [optin]  <title>`. Every record's `# Title` is the display name its dimension carried before the migration, so a prose mention of a dimension name resolves through this file even when the pair was never cited by a matrix row.

## The settled shape

The majority form, measured across the family as it stands on `main` at `7bc4b31b`. These are the targets; the tasks below say which files miss them.

**Header opening** (six of eight already):

1. `A domain specialization of **[audit-core](../audit-core/SKILL.md)** - read that first; it owns the loop (scope → parallel evidence → findings matrix → plan → subagent-driven fixes → review → PR) and the cross-cutting rules.`
2. `The checks are records in [`checks/`](checks/) beside this file; load the ones your slice needs, not the directory.`
3. `This skill supplies the <X> lens.` (plus any cross-domain handoff sentence the header already carries)
4. A `**Core principle:**` paragraph.
5. `**Announce:** "..."`, then `**Not for:** ...`

**Status line:** `Status per row: **ok / warn / violation**` - bold the values, not the label.

**Locality:** every header states which of its checks are `global` and why, by id. This is the one element the `/audit` front door dispatches on.

**Review lens:** every paragraph opens with a bold label naming what it judges, then ` - `, then the existing sentence: `**Label** - <sentence>`.

**Tooling fallback:** a record with no `tooling:` frontmatter carries a `## Tooling fallback` section saying what to read instead. Never in lead prose.

---

### Task 1: Header normalisation (issue items 1, 2, 3)

**Files:**
- Modify: `.agents/skills/arch-audit/SKILL.md`
- Modify: `.agents/skills/deps-audit/SKILL.md`
- Modify: `.agents/skills/ci-audit/SKILL.md`
- Modify: `.agents/skills/docs-audit/SKILL.md`
- Modify: `.agents/skills/security-audit/SKILL.md`

**Interfaces:**
- Produces: nothing later tasks consume. Header bodies stay within the measured 373-1,018 word range `audit-core` records; adding the missing boilerplate moves `arch` and `deps` up by roughly 60-90 words each, which is inside the range.

- [ ] **Step 1: Read the reference headers**

Read `.agents/skills/ci-audit/SKILL.md` and `.agents/skills/test-audit/SKILL.md` in full. These are the majority form. Every element you add below is copied from them and adapted to the target domain - do not invent new phrasing.

- [ ] **Step 2: `arch` - add the three missing boilerplate elements**

In `.agents/skills/arch-audit/SKILL.md`:

- Extend the audit-core sentence with the loop parenthetical so it reads `... it owns the loop (scope → parallel evidence → findings matrix → plan → subagent-driven fixes → review → PR) and the cross-cutting rules.`
- Add `This skill supplies the structural lens.` to the end of that same paragraph, matching where `ci` and `deps` put theirs.
- Add a `**Core principle:**` paragraph directly after it. Write it from what the header *already* asserts - the "Establish the declared architecture first, because it is the spec every layering finding is judged against" idea plus the behavior-preserving-refactor rule are the domain's two load-bearing claims. Do not introduce a claim the header does not already make.

- [ ] **Step 3: `deps` - add the three missing boilerplate elements**

In `.agents/skills/deps-audit/SKILL.md`: add the same loop parenthetical, a `**Core principle:**` paragraph, and a `**Not for:**` line. The Core principle should come from what the header already establishes - that verdicts here are relative to the project's own license and distribution model, and that most of the risk arrives transitively. The `**Not for:**` line should name what the header already hands off: first-party application-code security (`security-audit`) and the pipeline's own supply chain (`ci-audit`).

- [ ] **Step 4: `arch` - name its global checks**

`arch`'s existing "Fan out by each check's `locality`" paragraph states the rule generically but names no check. Every other migrated header names them. Add the enumeration to that paragraph, using these exact ids and this exact split, verified against the records:

- `local`: `arch/complexity`, `arch/dead-code`, `arch/layering`, `arch/size`
- `global`: `arch/complexity-gate`, `arch/coupling`, `arch/cycles`, `arch/hidden-coupling`, `arch/over-abstraction`, `arch/over-decomposition`, and the opt-in `arch/martin-metrics`

Say *why* the global ones are global in one clause - they are whole-graph properties (a cycle, a ratio across the tree, an edge that bypasses the import graph) plus, for `arch/complexity-gate`, a single repo-wide fact that must be reported once. That last one is the locality-split rule `audit-core` records; the header should reflect it.

- [ ] **Step 5: `docs` and `security` - state their locality split**

Neither header says anything about locality. Add one sentence to each, in the same position the other headers use (in or beside the fan-out/slicing paragraph). Verified splits:

- `docs`: `docs/coverage`, `docs/cross-referencing` and `docs/organization` are `global` - each is answered against the whole docs tree at once. The three opt-in docstring checks (`docs/docstring-coverage`, `docs/docstring-staleness`, `docs/docstring-standard`) are `local` to a source slice.
- `security`: every core check is `local` to a code slice; only the opt-in `security/secret-history` is `global`, because git history is one object and no per-slice agent can scan it.

- [ ] **Step 6: Status-line style in `arch`, `deps`, `ci`**

Change `**Status per row:** ok / warn / violation` to `Status per row: **ok / warn / violation**` in those three headers. Leave everything after the values - the parenthetical alternate scale and the suppressions sentence - byte-identical.

- [ ] **Step 7: Verify no regression**

Run, and paste the output into your report:

```bash
grep -c '—' .agents/skills/arch-audit/SKILL.md .agents/skills/deps-audit/SKILL.md .agents/skills/ci-audit/SKILL.md .agents/skills/docs-audit/SKILL.md .agents/skills/security-audit/SKILL.md
```

Expected: `1` for each file whose `description:` frontmatter contains an em-dash (that string is untouched by design), `0` otherwise. Any em-dash outside a `description:` line is a defect you introduced.

Then confirm each of the five headers still opens with the five majority elements, and report each header's new body word count.

- [ ] **Step 8: Gate and commit**

```bash
uv run python scripts/render_handbook_traceability.py --check
uv run pytest tests/scripts/ -q
git status --short
git add .agents/skills/arch-audit/SKILL.md .agents/skills/deps-audit/SKILL.md .agents/skills/ci-audit/SKILL.md .agents/skills/docs-audit/SKILL.md .agents/skills/security-audit/SKILL.md
git commit -m "docs(#567): normalise the eight audit domain headers

Refs #567"
```

---

### Task 2: Review-lens labels (issue item 4)

**Files:**
- Modify: 18 records under `.agents/skills/{arch,deps,security,test}-audit/checks/`

**Interfaces:**
- Produces: the labeled form Task 7 asserts. After this task, every `## Review lens` paragraph in all 68 records starts with `**`.

- [ ] **Step 1: Find the exact set**

Run this and work from its output - do not work from a list in this plan, because it is the ground truth:

```bash
uv run python - <<'PY'
import pathlib, re
for f in sorted(pathlib.Path('.agents/skills').glob('*-audit/checks/*.md')):
    m = re.search(r'^## Review lens\n(.*?)(?=\n## |\Z)', f.read_text(), re.S | re.M)
    if not m:
        continue
    for p in [x.strip() for x in m.group(1).strip().split('\n\n') if x.strip()]:
        if not p.startswith('**'):
            print(f"{f.parent.parent.name}/{f.stem}: {p[:100]}")
PY
```

Expected: 20 paragraphs across 18 records - 10 in `arch`, 4 in `deps`, 2 in `security`, 4 in `test`.

- [ ] **Step 2: Read the labeled majority first**

Read the `## Review lens` sections of `.agents/skills/ci-audit/checks/trigger-safety.md`, `.agents/skills/prompt-audit/checks/output-contract.md` and `.agents/skills/docs-audit/checks/coverage.md`. Note what a label does: it names the *dimension of judgment* the sentence applies - `**Pipeline-security correctness**`, `**No pipeline regression**` - in two to four words, not a restatement of the check's title.

- [ ] **Step 3: Label each of the 20 paragraphs**

For each, rewrite the paragraph as `**<Label>** - <the existing sentence, unchanged>`.

Three rules, in priority order:

1. **The sentence is not edited.** Only its first character's capitalisation may change, and only if the label makes the original leading capital read wrong mid-sentence. Everything else is byte-identical.
2. **The label names what the paragraph judges, not what the check detects.** A paragraph asking "does the fix actually remove the edge rather than hide it" is judging *fix adequacy*, so `**Layering-fix adequacy**` is right and `**Layering**` is not.
3. **Where a sibling record already carries a label for materially the same sentence, reuse that label verbatim.** The known case: `security/secret-history`'s paragraph is the same sentence as `security/secrets-in-code`'s, which carries `**Secret verification**`. Use `**Secret verification**` for it. Check for other sibling pairs before inventing a label - if two records share a sentence and get different labels, that is a defect.

- [ ] **Step 4: Verify**

Re-run the Step 1 script. Expected output: nothing. Then run:

```bash
git diff --stat
git diff -U0 | grep '^[-+]' | grep -v '^[-+][-+]' | head -60
```

Every `-`/`+` pair must differ only by the added `**Label** - ` prefix. Any other difference is a defect. Report the full label list (record id → label) in your report.

- [ ] **Step 5: Gate and commit**

```bash
uv run python scripts/render_handbook_traceability.py --check
uv run pytest tests/scripts/ -q
git status --short
git add <the exact record paths you changed>
git commit -m "docs(#567): label every review-lens paragraph

Refs #567"
```

---

### Task 3: Tooling-fallback placement and the unwrapped note (issue items 5, 8)

**Files:**
- Modify: `.agents/skills/docs-audit/checks/coverage.md`, `organization.md`, `docstring-standard.md`, `docstring-staleness.md`
- Modify: `.agents/skills/security-audit/checks/sensitive-data.md`
- Modify: `.agents/skills/eval-audit/checks/adversarial.md`, `cost-latency.md`, `judge-calibration.md`
- Modify: `.agents/skills/deps-audit/checks/transitive-licenses.md`

**Interfaces:**
- Produces: the invariant Task 7 asserts - every record without `tooling:` frontmatter has a `## Tooling fallback` section.

**Scope note:** issue #567 names five records for item 5. Three more have the same defect in a different form: `eval/adversarial`, `eval/cost-latency` and `eval/judge-calibration` have neither `tooling:` nor a `## Tooling fallback`, so an agent loading them gets nothing to run *and* nothing told to read. They are folded in here so the rule is uniform and testable rather than carrying a three-record exemption list. Say so in your report.

- [ ] **Step 1: Read the reference idiom**

Read the `## Tooling fallback` sections of `.agents/skills/ci-audit/checks/deploy-safety.md` and `.agents/skills/eval-audit/checks/contamination.md`. The idiom is: `Needs reading - <why no tool reaches this>: <what to read, concretely>.` Match it.

- [ ] **Step 2: Move the five lead-prose sentences into a section**

For each of `docs/coverage`, `docs/organization`, `docs/docstring-standard`, `docs/docstring-staleness`, `security/sensitive-data`: the detection sentence currently sits at the end of the lead prose. Cut it from there and place it under a new `## Tooling fallback` heading, in the section order the schema fixes (`## Severity`, `## Tooling fallback`, `## Fix`, `## Review lens`) - so it goes after `## Severity` if present, otherwise directly after the lead prose.

**Move the sentence, do not rewrite it.** The permitted edits are exactly two: (a) if the sentence began with a connective that only made sense trailing the lead prose, drop that connective; (b) if it is now the section's only content and reads as a fragment, promote its first word's capitalisation. `docs/coverage` and `docs/organization` carry the identical sentence ("Detection is the shared source-map pass the skill header builds ... - no separate tool or fallback of its own.") - it stays identical in both.

- [ ] **Step 3: Add a `## Tooling fallback` to the three eval opt-ins**

`eval/adversarial`, `eval/cost-latency` and `eval/judge-calibration` each have a one-sentence body that *is* the procedure. Do not move that sentence - it is the claim. Add a `## Tooling fallback` section stating, in the reference idiom, that no tool in the domain's evidence pass reaches this and what the agent reads or runs instead. Derive it from the record's own claim; introduce no new requirement.

- [ ] **Step 4: Soft-wrap the one unwrapped note**

`.agents/skills/deps-audit/checks/transitive-licenses.md`'s `handbook_note` is a single long line inside a `>-` folded block; every other folded note in the family is soft-wrapped at roughly 78 columns. Re-wrap it to match. **The text is unchanged** - a YAML folded block joins its lines with spaces, so re-wrapping must not alter the parsed string. Verify:

```bash
uv run python -c "
import sys; sys.path.insert(0, 'scripts')
import importlib.util, pathlib
s = importlib.util.spec_from_file_location('ac', 'scripts/audit_checks.py'); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
c, e = m.load_checks(m.SKILLS_DIR)
assert e == [], e
print(repr(c['deps/transitive-licenses'].handbook_note))
"
```

Run it **before** and **after** your edit and paste both outputs into your report. They must be identical.

- [ ] **Step 5: Verify the invariant holds**

```bash
uv run python - <<'PY'
import pathlib, re
bad = []
for f in sorted(pathlib.Path('.agents/skills').glob('*-audit/checks/*.md')):
    t = f.read_text()
    if not re.search(r'^tooling:', t, re.M) and not re.search(r'^## Tooling fallback', t, re.M):
        bad.append(f"{f.parent.parent.name}/{f.stem}")
print("records with neither tooling nor a fallback section:", bad)
PY
```

Expected: `[]`.

- [ ] **Step 6: Gate and commit**

```bash
uv run python scripts/render_handbook_traceability.py --check
uv run pytest tests/scripts/ -q
git status --short
git add <the exact record paths you changed>
git commit -m "docs(#567): give every tool-less check a stated reading procedure

Refs #567"
```

---

### Task 4: `audit-core` and `audit` - dashes and stale vocabulary (issue item 7, and the skill-file half of item 6)

**Files:**
- Modify: `.agents/skills/audit-core/SKILL.md`
- Modify: `.agents/skills/audit/SKILL.md`

**Interfaces:**
- Consumes: nothing. Produces: nothing later tasks read.

**Why these two files are one task:** both items touch both files, and the same sentences. Splitting them would have two agents editing the same lines.

- [ ] **Step 1: Convert em-dashes**

`audit-core/SKILL.md` has 12 em-dashes; `audit/SKILL.md` has 28. Replace each with ` - `, **except** the one inside each file's `description:` frontmatter string, which is the skill-discovery surface and stays verbatim.

Watch the two shapes that are not a simple swap:

- A parenthetical em-dash pair (`text — aside — text`) becomes ` - aside - `, which reads correctly. Keep both.
- A numeric range (`Steps 3–6`) uses an **en-dash**, not an em-dash. Leave en-dashes alone entirely; this item is about `—` (U+2014) only.

Verify with `grep -n '—' <file>` - expected: exactly the one `description:` line per file.

- [ ] **Step 2: Retire "dimension" where it means "check"**

Both files still say "dimension" in live rule text, describing a structure that no longer exists. Fix each occurrence. The known set (re-derive it with `grep -n -i dimension` rather than trusting this list):

In `audit-core/SKILL.md`:
- Step 1's `(per package, per config file, per dimension — whatever partitions cleanly)` - a dimension is not a fan-out slice; a check is.
- The fan-out paragraph's `Match the fan-out axis to each dimension's *locality*`, `slice **local** dimensions` and `give each **global** dimension ... its own agent`. `locality` is a field on a *record*. This is the sentence the `/audit` front door's dispatch behaviour depends on being right, so it matters most.

In `audit/SKILL.md`:
- `If every fallback for a dimension fails ... mark that dimension `no-evidence` — never `pass`` - the unit that gets a `no-evidence` verdict is a check.
- The report template's findings-matrix column header `Item | Dimension | Status | Severity | Evidence`. Rename the column to `Check`.
- `surface where the repo hurts across every dimension` in the Core principle - here "dimension" is used in its ordinary English sense (breadth across concerns), not as the family's structural term. **Leave it.** Judge each occurrence this way: if replacing it with "check" would be a *correction*, replace it; if it would be a *distortion*, leave it.

- [ ] **Step 3: Verify you left the ordinary-English uses alone**

Report every occurrence you found, with your verdict (changed / left, and why) for each. A blanket replace is a defect: the 68 records and the eight headers legitimately use "dimension" in its ordinary sense 11 times, and this task must not start that same mistake in these two files.

- [ ] **Step 4: Gate and commit**

```bash
uv run python scripts/render_handbook_traceability.py --check
uv run pytest tests/scripts/ -q
git status --short
git add .agents/skills/audit-core/SKILL.md .agents/skills/audit/SKILL.md
git commit -m "docs(#567): make the engine and front door name checks, not dimensions

The fan-out rule in audit-core keys on a record's locality field, and the
front door dispatches on it. Both still said dimension, naming a structure
#559 removed - so the one sentence an executing agent reads to decide how
to slice the work described something that no longer exists.

Refs #567"
```

---

### Task 5: Matrix prose sweep, README spine through Part 5 (issue item 6, first half)

**Files:**
- Modify: `docs/audit/handbook-traceability.yaml` (lines 1-647 only: the README spine and Parts 1-5)

**Interfaces:**
- Consumes: `<scratchpad>/crosswalk.txt` and `<scratchpad>/record-index.txt`, handed to you by path.
- Produces: the same treatment Task 6 applies to lines 648-end. Task 6 re-renders the Markdown view for both halves.

**Do not touch `docs/audit/handbook-traceability.md`** - it is generated, and Task 6 regenerates it once at the end.

- [ ] **Step 1: Understand what you are changing**

These are the free-prose `note:` and `gap: note:` fields - the judgment prose explaining why a handbook clause is unmapped, partially mapped, or an exact fit. They describe a `## N. Dimensions` structure in each skill that #559 removed. The structured half of the matrix (the `checks:` lists) was already rewired to check ids in #566; this is the prose that still talks about the old shape.

Read `<scratchpad>/crosswalk.txt` and `<scratchpad>/record-index.txt` first. Between them, every dimension display name that appears in this prose resolves to exactly one check id.

- [ ] **Step 2: Rewrite each occurrence, by category**

Find them with `grep -n -i dimension docs/audit/handbook-traceability.yaml` and work only on hits in lines 1-647. Roughly 33 occurrences. Four categories:

1. **A named dimension → its check id.** `eval-audit's Reproducibility dimension` becomes `` `eval/reproducibility` ``. Resolve through the crosswalk, or through the record index when the name was never cited by a row. Use backticked ids, which is how #566 left the rest of the file.
2. **An unnamed "no dimension ..." → "no check ...".** `no dimension asks whether a change carries a committed spec` becomes `no check asks whether ...`. This is the largest category and is a straight noun swap.
3. **A reference to the section that no longer exists.** `outside its Dimensions section`, `declares no dimensions so no row can cite it`, `sit outside the citable Dimensions section` - these named a markdown heading. Restate against the checks tree: the question is now whether a *record* exists that a row can cite. Keep the argument the note was making; only the mechanism it names changes.
4. **Ordinary English.** `one dimension at a time`, `an eval dimension`, `injection-resistance as an eval dimension` - domain vocabulary, not the family's structural term. **Leave these alone.** Test: would replacing it with "check" be a correction or a distortion?

- [ ] **Step 3: Correct the notes that are now false**

Category 3 hides a second problem. Some notes do not merely *describe* the old structure - they *prescribe declaring a dimension* as the fix, and #566 already performed that fix by creating the record. A note that says the fix is still pending, when the record exists, is false rather than dated.

For each category-3 occurrence, check the checks tree for a record that now covers what the note says is undeclared. If one exists:

- Restate the note against reality: say what the record does and does not reach, which is the argument the record's own `handbook_note` already makes.
- Then ask the harder question: **does the row now have a real citation?** If the record genuinely grounds the row's claim, the row should cite it in `checks:` and the `gap:` should narrow or go. If the record's scope is genuinely adjacent rather than matching, leave the row uncited and say why.
- **The bidirectional rule binds either way.** If you add a row id to a `checks:` list, you must add that row id to the record's `handbook:` frontmatter and remove its `handbook_note`. The renderer's `--check` enforces this in both directions, so getting it wrong fails your gate rather than slipping through.

**Report every such change as its own numbered item, with the row id, the record id, and the evidence.** These are the substantive findings of this task; the vocabulary swaps are not.

- [ ] **Step 4: Verify**

```bash
uv run python scripts/render_handbook_traceability.py --check
git diff -U0 docs/audit/handbook-traceability.yaml | grep -c '^+'
```

Then re-read your own diff and confirm: no `claim:` field changed (those are handbook quotations, not commentary), no `id:`/`class:`/`severity:` changed, and every prose edit kept the note's argument.

- [ ] **Step 5: Commit**

```bash
uv run pytest tests/scripts/ -q
git status --short
git add docs/audit/handbook-traceability.yaml
git commit -m "docs(#567): retire dimension vocabulary from the matrix prose (spine, Parts 1-5)

Refs #567"
```

---

### Task 6: Matrix prose sweep, Parts 6-9 and re-render (issue item 6, second half)

**Files:**
- Modify: `docs/audit/handbook-traceability.yaml` (lines 648-end: Parts 6-9, the troubleshooting guide, the coda)
- Modify: `docs/audit/handbook-traceability.md` (regenerated, both halves)

**Interfaces:**
- Consumes: `<scratchpad>/crosswalk.txt` and `<scratchpad>/record-index.txt`, and Task 5's committed result - read Task 5's diff (`git show`) before starting so your phrasing matches the half already done.

- [ ] **Step 1: Apply Task 5's Steps 1-3 to lines 648-end**

Same four categories, same rules, same reporting requirement. Roughly 24 occurrences. Read Task 5's report and its commit diff first; where Task 5 settled a phrasing for a recurring shape, reuse it rather than inventing a second one.

- [ ] **Step 2: The one known false note**

`security-supply-chain/secrets-never-commit-them-and-rotate-dont-just-delete-b` (around line 1048) is a confirmed instance of Task 5's Step 3 case. Its `gap: note:` says the citeability gap exists because "Secrets in code, the one citable dimension, reads the working tree", and prescribes "The fix is to declare the history-and-rotation coverage as a dimension."

#566 created `security/secret-history`, a citable record whose whole scope is scanning git history for secrets. So the prescribed fix has been performed and the note is false as written.

Resolve it: the row's claim is *"rotate the credential at its provider first, then remove the line, then purge history if it was ever pushed"*. Read `security/secret-history`'s own `handbook_note`, which argues the handbook states no separate history-scan clause - then judge that argument against this row's claim, which does mention purging history. Decide whether the row cites the record, apply the bidirectional rule if it does, and state your reasoning in your report either way. **This is the task's most consequential decision - do not resolve it silently.**

- [ ] **Step 3: Re-render the Markdown view**

```bash
uv run python scripts/render_handbook_traceability.py
uv run python scripts/render_handbook_traceability.py --check
```

- [ ] **Step 4: Verify the whole file**

```bash
grep -n -i 'dimension' docs/audit/handbook-traceability.yaml
```

Every surviving occurrence must be a deliberate ordinary-English use. List each one in your report with a one-line justification. Expect a handful, not zero - `one dimension at a time` in the audit-cadence claim and `an eval dimension` in the evaluation rows are correct English and must survive.

- [ ] **Step 5: Commit**

```bash
uv run pytest tests/scripts/ -q
git status --short
git add docs/audit/handbook-traceability.yaml docs/audit/handbook-traceability.md
git commit -m "docs(#567): retire dimension vocabulary from the matrix prose (Parts 6-9)

Refs #567"
```

---

### Task 7: Lock the two mechanical conventions behind tests

**Files:**
- Modify: `tests/scripts/test_audit_checks.py`

**Interfaces:**
- Consumes: the invariants Tasks 2 and 3 established. **This task must run last** - both tests fail against the tree as it stands before those tasks.

**Why only two:** of #567's eight items, exactly two state a rule that holds for every record with no judgment call - a tool-less record carries a reading procedure, and a review-lens paragraph carries a label. The rest (header boilerplate, locality prose, prose vocabulary) are judgment and stay reviewed by humans. Do not add tests for those; a test that encodes a judgment call becomes a thing to satisfy rather than a net.

- [ ] **Step 1: Write the failing tests**

Add both to `tests/scripts/test_audit_checks.py`, following the file's existing real-tree test style (`test_every_audit_skill_has_a_non_empty_checks_directory` is the model - it asserts a structural invariant over `ac.SKILLS_DIR`, names what to do if it fails, and says not to weaken the assertion).

```python
def test_every_tool_less_check_states_a_reading_procedure():
    """#567 item 5: a record may omit `tooling:` when its detection is
    reading rather than running something - but it must then say so under
    `## Tooling fallback`, or the executing agent has nothing to run and
    nothing told to read. If this fails, add the section to the named
    record - do not weaken the assertion.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    missing = sorted(
        check_id
        for check_id, check in checks.items()
        if not check.tooling and "\n## Tooling fallback" not in check.path.read_text()
    )
    assert missing == [], (
        f"these checks declare no tooling and state no fallback: {missing}"
    )


def test_every_review_lens_paragraph_carries_a_label():
    """#567 item 4: a `## Review lens` paragraph opens with a bold label
    naming what it judges, so a whole-branch reviewer assembling lenses
    from several records can tell them apart. If this fails, label the
    paragraph - do not weaken the assertion.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    unlabeled = []
    for check_id, check in sorted(checks.items()):
        section = re.search(
            r"^## Review lens\n(.*?)(?=\n## |\Z)",
            check.path.read_text(),
            re.S | re.M,
        )
        if section is None:
            continue
        for para in section.group(1).strip().split("\n\n"):
            if para.strip() and not para.strip().startswith("**"):
                unlabeled.append(f"{check_id}: {para.strip()[:60]}")
    assert unlabeled == [], f"unlabeled review-lens paragraphs: {unlabeled}"
```

Add `import re` to the file's imports if it is not already there.

- [ ] **Step 2: Run them and confirm they pass**

```bash
uv run pytest tests/scripts/test_audit_checks.py -q
```

Both must pass. If either fails, **the failure is real** - Task 2 or Task 3 missed a record. Report the failure and fix the record rather than the test.

- [ ] **Step 3: Confirm they would catch a regression**

Temporarily break one record each way (delete a `## Tooling fallback` heading; strip a `**Label** - ` prefix), confirm the matching test fails and names that record, then restore the record with `git checkout -- <path>`. Paste both failure messages into your report. A test that passes on a tree it cannot fail on is not a net.

- [ ] **Step 4: Gate and commit**

```bash
uv run ruff check . && uv run ruff format --check . && uv run pyright
uv run pytest tests/scripts/ -q
git status --short
git add tests/scripts/test_audit_checks.py
git commit -m "test(#567): lock the two mechanical record conventions

Refs #567"
```

---

## Out of scope

Stated so a reviewer does not read these as misses:

- **`docs/audit/2026-07-20-docs-audit.md`** uses "dimension" throughout. It is a dated report of a past audit run, and rewriting it would falsify the record of what that run actually said.
- **`scripts/render_handbook_traceability.py`**'s remaining "dimension" references are all the legacy `skill_dimensions()` path. Deleting that path is PR 3 of #559, tracked on that issue's two open acceptance criteria.
- **The eleven ordinary-English uses of "dimension"** in the headers and records (an eval dimension, a matrix dimension, a quality dimension). They are correct English and correct domain vocabulary.
