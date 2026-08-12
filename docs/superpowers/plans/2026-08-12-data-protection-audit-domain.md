# Data-protection audit domain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `data-protection-audit`, the ninth domain on the `audit-core` engine, with eight check records grounding the eight dimensions of #4 in real handbook Part 10 matrix rows, and the reciprocal half of every matrix edge.

**Architecture:** A domain skill is thin: one `SKILL.md` stating the lens, plus one Markdown record per check under `checks/`, each with YAML frontmatter the loader validates. The matrix row's `checks:` entry and the record's `handbook:` entry are two directions of one edge, so every record lands in the same commit as its row. `scripts/render_handbook_traceability.py --check` is the gate that enforces the edge set; two exact-set tests in `tests/scripts/test_audit_checks.py` enforce the domain list and the check-id list.

**Tech Stack:** Markdown with YAML frontmatter; `scripts/audit_checks.py` (loader and validator); `scripts/render_handbook_traceability.py` (integrity gate and Markdown renderer); pytest; ruff.

## Global Constraints

Copied verbatim into every task. Every task's requirements implicitly include this section.

- **Never edit `docs/audit/handbook-traceability.md`.** It is generated. Edit `docs/audit/handbook-traceability.yaml` and re-render with `uv run python scripts/render_handbook_traceability.py`.
- **A matrix row's `checks:` entry and a record's `handbook:` entry are two directions of one edge.** Change one, change the other, in the same commit, or `--check` fails.
- **Markdown is never hard-wrapped: one paragraph is one source line.** Never reflow a line you did not change.
- **No em-dash (U+2014).** Use ` - `. This plan and the spec are under `docs/superpowers/`, which bans it; `.agents/skills/` does not ban it but the family's existing records all use ` - `, so match them.
- **Links from `.agents/skills/` to files in this repository are absolute GitHub URLs** (`https://github.com/mesagroup/ai-agent-development-handbook/blob/main/...`), because the skills run from a plugin cache where a relative path resolves to nothing. A link to a *sibling skill* stays relative (`../audit-core/SKILL.md`), which is what every existing record and skill file does.
- **Never commit environment-specific values:** absolute personal paths, profile names, tokens, hostnames, emails. Use a `<placeholder>` and say what it resolves to.
- **Never assert a count you did not compute.** Compute it in the same breath, or state no number.
- **Every `## Review lens` paragraph opens with a bold label, then ` - `, then the sentence** - the exact form `**Label** - <sentence>`. `tests/scripts/test_audit_checks.py::test_every_review_lens_paragraph_carries_a_label` enforces it.
- **A record omitting `tooling:` must carry a `## Tooling fallback` section saying what to read instead.** `test_every_tool_less_check_states_a_reading_procedure` enforces it.
- **Record frontmatter keys are exactly `id`, `domain`, `locality`, `handbook`, `handbook_note`, `tooling`, `needs`, `ungranted_note`, `optin`.** Any other key is a load error. `id` must equal `<domain>/<file stem>`; `domain` must equal the owning directory with `-audit` removed. `handbook_note` is rejected when `handbook` is non-empty.
- **Every record body starts with an H1** (`# Title`); the loader reads it as the display name.
- **The domain gate for every task:** `uv run python scripts/render_handbook_traceability.py --check && uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check .` - all four green in the task's own commit.
- **Commit message references the issue:** `Refs #4`. No Claude credits. A commit touching a prompt (which every `.agents/skills/` file is) says WHY, not just what.
- **Stage explicit paths** with `git add <path>`; never `git add -A`, `git add .` or `git commit -a`.

---

## File Structure

**Created:**

- `.agents/skills/data-protection-audit/SKILL.md` - the lens: subject, applicability rule, slicing, status scale, fix conventions, cross-links, the opt-in deliverable.
- `.agents/skills/data-protection-audit/checks/data-flow-map.md`
- `.agents/skills/data-protection-audit/checks/processor-register.md`
- `.agents/skills/data-protection-audit/checks/provider-surface.md`
- `.agents/skills/data-protection-audit/checks/residency-pinning.md`
- `.agents/skills/data-protection-audit/checks/boundary-minimization.md`
- `.agents/skills/data-protection-audit/checks/retention-limits.md`
- `.agents/skills/data-protection-audit/checks/deletion-path.md`
- `.agents/skills/data-protection-audit/checks/stored-artifact-pii.md`

**Modified:**

- `docs/audit/handbook-traceability.yaml` - nine row changes.
- `docs/audit/handbook-traceability.md` - regenerated, never hand-edited.
- `tests/scripts/test_audit_checks.py` - two exact-set assertions.
- `.agents/skills/audit/SKILL.md`, `.agents/skills/audit-core/SKILL.md` - domain lists and arithmetic.
- `README.md`, `CLAUDE.md` - counts.
- `docs/audit/sweep-obligations.md` - only if an engine-file edit disturbed a quoted anchor.

---

## Task 1: The skill file, the first record, and the two exact-set tests

This task establishes the directory, the loader's view of a ninth domain, and the record pattern the remaining tasks follow. It is the highest-value reviewer gate in the plan: a wrong frontmatter shape here gets copied seven times.

**Files:**
- Create: `.agents/skills/data-protection-audit/SKILL.md`
- Create: `.agents/skills/data-protection-audit/checks/data-flow-map.md`
- Modify: `docs/audit/handbook-traceability.yaml` (row `data-protection/know-what-personal-data-you-hold-and-where-it-goes`)
- Modify: `docs/audit/handbook-traceability.md` (regenerated)
- Modify: `tests/scripts/test_audit_checks.py`

**Interfaces:**
- Produces: the directory `.agents/skills/data-protection-audit/checks/`, which every later task adds a record to; the domain string `data-protection`; the record frontmatter shape (`id`, `domain`, `locality`, `handbook`) later records repeat.

- [ ] **Step 1: Read the ground truth before writing anything**

Read these four, in this order. Do not skip the first: the record's prose has to be a check over the clause, and the clause is in the handbook.

```
docs/engineering/data-protection.md            (the section "Know what personal data you hold, and where it goes")
.agents/skills/audit-core/SKILL.md             ("Authoring a new auditing skill", and the loop's step 1 and 2)
.agents/skills/security-audit/SKILL.md         (the reference for a domain skill that establishes a subject first)
.agents/skills/deps-audit/checks/vulnerabilities.md   (the reference for a record with all four body sections)
```

Then read the row this record grounds, including its `gap.note`, which says in reviewed prose exactly what no existing skill can see:

```bash
uv run python -c "
import yaml, pathlib
rows = yaml.safe_load(pathlib.Path('docs/audit/handbook-traceability.yaml').read_text())
row = next(r for r in rows if r['id'] == 'data-protection/know-what-personal-data-you-hold-and-where-it-goes')
print(yaml.safe_dump(row, sort_keys=False, width=200, allow_unicode=True))
"
```

- [ ] **Step 2: Write `SKILL.md`**

Frontmatter is `name` and `description` only, matching every sibling. The `description` is what the harness matches an invocation against, so it names the lens, when to use it, what it is not for, and that it runs on `audit-core`. Model it on `security-audit`'s, which is the closest shape (a domain with a subject that has to be established before any check means anything).

```yaml
---
name: data-protection-audit
description: "..."
---
```

The `description` must state, in one paragraph: that it audits a project's data-protection and privacy posture (data-flow map, processor register and its reconciliation against the code, region pinning, minimization before the trust boundary, retention limits and the deletion path, personal data in stored traces and eval fixtures); when to use it (before a release that touches personal data, when onboarding a processor, when a data subject request has to be answerable, or when the user asks for a GDPR / privacy / data-protection audit); that the evidence is largely a register and a map rather than code, so several checks report what the repository cannot see rather than a pass; that it runs on the audit-core engine; and the handoffs - first-party call-site leaks belong to `security-audit`, third-party package CVEs to `deps-audit`, pipeline credentials to `ci-audit`.

The body covers exactly these, in this order, and nothing that belongs in a record:

1. **The opening line**, in the family's form: a domain specialization of **[audit-core](../audit-core/SKILL.md)**, read that first, it owns the loop and the cross-cutting rules; the checks are records in [`checks/`](checks/), load the ones your slice needs rather than the directory.
2. **Core principle.** State it as the thing this domain gets wrong when it is careless: an audit here has two kinds of answer and mixing them is the failure - what the repository shows, and what no repository can show. Name each unverifiable item with what would settle it and who holds that evidence. A report that lists an unsigned agreement as passing has not audited it, it has failed to look and said so in the vocabulary of success.
3. **Announce:** `"I'm using the data-protection-audit skill (on the audit-core engine) to audit the project's data-protection posture."`
4. **Not for:** first-party call-site leaks of secrets or personal data into logs and error messages (`security-audit`, which this skill cross-links rather than duplicates); third-party package CVEs (`deps-audit`); pipeline credentials and permissions (`ci-audit`); and legal judgment on whether an agreement or a transfer route suffices, which is out of scope entirely - this skill reports what is recorded and what is missing.
5. **Subject.** The personal-data surface, established first because every check is a question asked of one part of it: where personal data **enters** (uploads, form fields, integrations pulling from a customer's system, whatever a user types at an agent); where it **rests** (primary store, object store, vector index, caches, logs, eval datasets, run artifacts, backups); and every **outbound edge** that leaves the trust boundary. Plus the two artifacts that are supposed to describe it - the data-flow map and the processor register - which are evidence and subject at once.
6. **Applicability - the rule, and why it is here rather than in a record.** `audit-core` step 0 asks whether the target processes personal data, alongside mode, grants and opt-ins, because a dispatched agent has nobody to ask. Answered no, the domain is out of scope for the run and the report says so, naming the operator's declaration as the reason - the way the front door reports a domain the user named that has no checks directory. **Do not report `not-applicable` on every row instead:** that status means the check has no lens in this partition's languages, and a second meaning on it would make a polyglot gap and an operator's scoping decision indistinguishable in the one column a reader uses to tell measured from unmeasured. And the declaration is not a pass: it is an assertion about the target from outside it, which is exactly what the core principle says to report separately. Where nobody can be asked - a sweep's dispatched agent, a non-interactive run - the lens runs and **the absence of a documented personal-data surface is itself the finding**, which is `audit/SKILL.md`'s no-inferred-rubric rule applied here. State the constraint that rule puts on the checks, because it is the load-bearing half: no check infers a personal-data surface from field names or file paths and then flags violations against the surface it invented. "You have not written this down" is a diagnosis; "you violate the standard I made up for you" is not.
7. **Slicing.** Six records are `global` and get their own agent each; `data-protection/residency-pinning` and `data-protection/boundary-minimization` are `local` and ride the per-partition agent, because configuration and the outbound call path live in a partition and a monorepo where one service pins its region while another defaults is the finding rather than an average. **Build the outbound-surface derivation once** as `audit-core`'s shared ground-truth artifact: `provider-surface` reconciles it against the register and `data-flow-map` checks the map's outbound edges against it, so two agents deriving it separately would be free to disagree about the one list the domain rests on.
8. **Status scale:** `ok / warn / violation`, plus `audit-core`'s `no-evidence` and `not-applicable`, which are additions rather than replacements. Then the domain's own restatement of what must never collapse: a claim the repository cannot settle is reported as unverifiable-from-here with what would settle it and who holds that evidence, and it is neither `ok` nor `no-evidence` - `no-evidence` says a tool could not run, and this says the evidence is not in a repository at all.
9. **Fixes touch code.** Not a docs-only domain: a required region key with startup validation, a redaction step in the shared outbound call path, a TTL or lifecycle rule, a deletion path and the test that walks it. The domain gate is the target's own test suite plus whatever the region validation needs to keep passing. Two fixes are documents rather than code - the data-flow map and the processor register - and they are the two the audited team must own rather than the audit, so the remediation plan names who. Docs-only outputs: the findings report and the two artifacts above.
10. **The opt-in deliverable:** a **sub-processor inventory**, rendered from `provider-surface`'s derivation rather than from a fresh pass, so the inventory and the finding cannot disagree. Per `audit/SKILL.md` a deliverable is out of scope for a sweep however the user answers, because it is an artifact *of* the audited project rather than findings *about* it; offer it as a per-domain follow-up.
11. **Cross-checks**, each naming the check id it hands to: `security/sensitive-data` for the call-site half of the trail claim (this skill owns the stored artifacts, that one owns the call sites); `deps/inventory` for why the package graph is not the provider list, since a provider reached over HTTP never enters it; `eval-audit` for redaction's quality cost as a dimension; `ci/permissions-secrets` for pipeline credentials, which are not about where a request lands. Note each handoff in the report.

- [ ] **Step 3: Write `checks/data-flow-map.md`**

Frontmatter, verbatim:

```yaml
---
id: data-protection/data-flow-map
domain: data-protection
locality: global
handbook:
  - data-protection/know-what-personal-data-you-hold-and-where-it-goes
---
```

Body:

- H1: `# Data-flow map`
- **Lead prose** (the claim, one or two sentences): whether a data-flow map exists beside the code, answering where personal data enters, every store it rests in and every outbound edge that leaves the trust boundary; and whether it is falsifiable against the code rather than a document produced once for an audit.
- `## Severity` - three graded paragraphs. **Critical**: no map at all, in a project with a personal-data surface the code plainly shows, because every other check in this domain is a question asked of one edge or one store and none of them can be answered against a list that does not exist. **Important**: a map that exists and is demonstrably stale - it omits a store or an outbound edge the code shows. **Minor**: a map that is complete but kept somewhere a reviewer will not see it go stale, so its accuracy is a matter of luck.
- `## Tooling fallback` - required, since there is no `tooling:` key. Say plainly that no tool enumerates a project's personal-data surface and that this check is a reading pass, then say exactly what to read: the shared outbound-surface derivation the skill file says to build once (imports, configured base URLs, MCP and tool endpoints, credential names) for the edges; the deployment and infrastructure configuration for the stores, naming the kinds that get missed because they are an implementation detail of something else - a managed vector index, a cache, an object bucket, a queue, a backup schedule; and the repository's documentation tree for the map itself, including a compliance directory if there is one. State the rule the front door imposes: where no map is documented, report the absence as the finding and do **not** infer a map from field names or paths and then flag the code against it.
- `## Fix` - add the map beside the code, derived from the repository rather than from memory, listing entry points, stores and outbound edges; put it where a reviewer sees it go stale (next to the code or in the contributor guide's path), and say that a regime asks for a superset it calls records of processing (purposes, categories, erasure limits), so the map is the engineering half and not the whole obligation. The audited team owns the content; the audit can derive the edge and store list.
- `## Review lens` - at least two paragraphs, each opening `**Label** - `. **Derivation honesty** - every store and edge the finding claims is missing is cited at a `file:line` in the target, expressed relative to `target_root`, so the audited team can check it. **Inferred-surface guard** - the finding is the absence of the map, never a violation of a map the audit invented; a row that flags the code against a surface no artifact documents is the no-inferred-rubric failure and is withdrawn.

- [ ] **Step 4: Add the reciprocal matrix edge**

In `docs/audit/handbook-traceability.yaml`, on row `data-protection/know-what-personal-data-you-hold-and-where-it-goes`: add `checks: [data-protection/data-flow-map]` and **delete the whole `gap:` block**. The check answers the claim - a map exists, and it is reconciled against the code - so the gap retires rather than shrinking. Keep the row's `claim`, `class` and `severity` untouched.

- [ ] **Step 5: Update the two exact-set tests**

In `tests/scripts/test_audit_checks.py`:

- `test_the_real_checks_tree_covers_every_domain`: add `"data-protection"` to the asserted set, in sorted position (it sorts before `"deps"` and after `"ci"`).
- `test_the_real_checks_tree_loads_clean`: add `"data-protection/data-flow-map"` to the asserted sorted list, in sorted position (after the `ci/` ids, before the `deps/` ids).

Do not weaken either assertion to a subset or a count. Both docstrings say why they assert exact sets.

- [ ] **Step 6: Regenerate and run the gate**

```bash
uv run python scripts/render_handbook_traceability.py
uv run python scripts/render_handbook_traceability.py --check
uv run pytest tests/ -q
uv run ruff check . && uv run ruff format --check .
```

Expected: `--check` **prints nothing and exits 0** - silence is the pass, so do not watch for a success string, and read `$?` rather than the output. Where it does print, it is naming a broken edge: a `handbook:` id with no matching row `id`, or a row citing a check that does not load. Fix the record, not the row, unless the row id is genuinely what you mistyped.

- [ ] **Step 7: Verify the loader sees the new domain**

```bash
uv run python -c "
import sys; sys.path.insert(0, 'scripts')
from audit_checks import SKILLS_DIR, load_checks
checks, errors = load_checks(SKILLS_DIR)
assert errors == [], errors
print('domains:', sorted({c.domain for c in checks.values()}))
print('records:', len(checks))
print('data-protection:', sorted(c.id for c in checks.values() if c.domain == 'data-protection'))
"
```

Expected: nine domains, `data-protection` among them, one `data-protection/` id, no errors.

- [ ] **Step 8: Commit**

```bash
git add .agents/skills/data-protection-audit/SKILL.md .agents/skills/data-protection-audit/checks/data-flow-map.md docs/audit/handbook-traceability.yaml docs/audit/handbook-traceability.md tests/scripts/test_audit_checks.py
git commit -F - <<'EOF'
feat: open the data-protection audit domain on the map check

Part 10 asks for a data-flow map beside the code because every other
directive in the part is a question asked of one edge or one store: a team
that cannot enumerate them is answering about the ones it remembers. So the
domain opens on the map rather than on the register - without it the other
checks have no list to be questions about.

The skill file carries what no record can: the applicability rule, which is
where this domain would otherwise go wrong. A target that holds no personal
data must not collect a stack of Criticals, and the answer is not to infer a
personal-data surface from field names and flag the code against the one the
audit invented. audit-core step 0 asks; where nobody can be asked, absence of
a documented surface is the finding.

Refs #4
EOF
git show --stat HEAD
```

---

## Task 2: The processor pair - the register, and the surface the code actually calls

The two halves Part 10 split on purpose: what the register *contains* rests on evidence outside any repository, while whether it *matches the code* is settled inside one. `provider-surface` is the load-bearing check of the whole domain and the derivation #6 will consume.

**Files:**
- Create: `.agents/skills/data-protection-audit/checks/processor-register.md`
- Create: `.agents/skills/data-protection-audit/checks/provider-surface.md`
- Modify: `docs/audit/handbook-traceability.yaml` (rows `...-register-must-match-the-code-a` and `-b`)
- Modify: `docs/audit/handbook-traceability.md` (regenerated)
- Modify: `tests/scripts/test_audit_checks.py`

**Interfaces:**
- Consumes: the directory and frontmatter shape from Task 1.
- Produces: `data-protection/provider-surface`, whose derivation the skill file names as the shared artifact and which #6 is expected to consume; `data-protection/processor-register`.

- [ ] **Step 1: Read the section and both rows**

Read the Part 10 section "Every processor needs an agreement, and the register must match the code" in `docs/engineering/data-protection.md`, then both rows and their gap notes:

```bash
uv run python -c "
import yaml, pathlib
rows = yaml.safe_load(pathlib.Path('docs/audit/handbook-traceability.yaml').read_text())
for rid in ('data-protection/every-processor-needs-an-agreement-and-the-register-must-match-the-code-a',
            'data-protection/every-processor-needs-an-agreement-and-the-register-must-match-the-code-b'):
    print(yaml.safe_dump(next(r for r in rows if r['id'] == rid), sort_keys=False, width=200, allow_unicode=True))
"
```

Note the terms of art the section fixes and that the records must not undo: a **legal basis** is the controller's and is a separate question from the processor's contract, so this check is about the agreement and never about the basis.

- [ ] **Step 2: Write `checks/processor-register.md`**

```yaml
---
id: data-protection/processor-register
domain: data-protection
locality: global
handbook:
  - data-protection/every-processor-needs-an-agreement-and-the-register-must-match-the-code-a
---
```

- H1: `# Processor register`
- **Lead prose**: whether a register of processors exists and records, per processor, a signed data processing agreement, the provider's position on training and how it was opted out of, and the retention window including any longer abuse-monitoring one - and the date the register was last reconciled against the code.
- `## Severity` - **Critical**: no register, or a register with no DPA field at all, in a project whose code reaches a third party with personal data. **Critical** also for a processor recorded with no retention window, since a provider whose retention you cannot state is a provider you have not accounted for. **Important**: a register complete in its fields but with no recorded reconciliation date, so nobody can say when it last matched the code. **Minor**: a field recorded as free prose where a date or a yes/no would be checkable.
- `## Tooling fallback` - a reading pass; there is no tool that enumerates a project's processors or reads a contract. Say what to read: the register wherever the project keeps it (a compliance directory, a vendor or sub-processor page in the docs tree, an ADR); then, for each processor it lists, whether the three fields are present and dated rather than gestured at. **State the hard boundary explicitly**, because it is the rule this domain most easily breaks: whether an agreement was actually signed, and whether the provider honours the retention window it publishes, is not visible from a repository at all. Report each as unverifiable-from-here, name what would settle it (the executed agreement; the provider's current terms) and who holds it (whoever owns compliance; the provider), and never as `ok`. A register nobody has ever checked and a register that matches the code look identical from outside, which is why the reconciliation date is part of the check.
- `## Fix` - create or complete the register with the three fields per processor plus a reconciliation date; note that the enumeration is most of the work and that the list is longer than the one a team writes from memory - hosting and managed databases underneath everything, and the three forgotten because they receive prompts rather than documents: tracing and observability backends, error trackers, eval platforms. The audited team owns the contract facts; the audit can supply the list of who is called, from `data-protection/provider-surface`.
- `## Review lens` - **Evidence boundary** - every claim the row makes is separated into what the repository showed and what it cannot show, and no unverifiable item is reported as passing. **Term precision** - the row is about the processor's agreement, its training position and its retention window; never the controller's legal basis, which is a different obligation, and never the lawful transfer route, which belongs to `data-protection/residency-pinning` and its own row. (My first draft of this step said "and the transfer route", which Task 2's review caught: a transfer-route claim in this record has no severity band to land in and duplicates the Task 3 check. Task 3 must not be written against the boundary that draft implied.)

- [ ] **Step 3: Write `checks/provider-surface.md`**

```yaml
---
id: data-protection/provider-surface
domain: data-protection
locality: global
handbook:
  - data-protection/every-processor-needs-an-agreement-and-the-register-must-match-the-code-b
---
```

- H1: `# Provider surface against the register`
- **Lead prose**: derive the outbound provider surface from the code - SDK imports, configured base URLs, MCP servers and tool endpoints, the credentials the deployment carries - and reconcile it against the register. A provider reachable from the code and missing from the register is the finding, and it is the half of this question a repository can settle.
- `## Severity` - **Critical**: a provider reachable from the code with personal data crossing to it and absent from the register. **Important**: a provider present in both but reached from a path the register does not describe (a second base URL, a fallback endpoint). **Minor**: a registered provider with no reachable call path, which is a stale register entry rather than an unaccounted transfer, and is worth reporting because it is evidence the register is not maintained.
- `## Tooling fallback` - a reading pass with a stated derivation, and this is the shared artifact the skill file says to build once. Enumerate the four sources concretely, and say why each is needed rather than any one being sufficient: **imports** of provider SDKs catch the ones used through a client library; **configured base URLs and endpoint settings** catch a provider reached over plain HTTP with no SDK, and catch a proxy or gateway standing in front of one; **MCP server declarations and tool endpoint config** catch the ones an agent reaches at run time, which no import mentions; **credential names** in env templates, secret manifests and deployment config catch a provider whose call path is dynamic or lives in infrastructure rather than code. Say why the package graph is not the answer and hand that off: `deps/inventory` enumerates packages, and a provider reached over HTTP never enters it, so a clean dependency inventory is no evidence about this check. Note that `security/sensitive-data` reads outbound URL construction too, but for exposure at the call site rather than to enumerate who is called.
- `## Fix` - add the missing providers to the register with their three fields, and record the reconciliation date; where the surface is large or dynamic, move the outbound calls behind one client layer so the surface is enumerable by construction rather than by search.
- `## Review lens` - **Derivation completeness** - the finding names which of the four sources produced each provider, so a reader can tell an SDK import from a credential name and judge the confidence. **Reachability honesty** - a provider named in code that no configuration reaches is reported as such rather than as an unaccounted transfer, and a dynamic call path the derivation could not resolve is stated as a limit of the pass rather than left implied.
- Add one sentence recording that #6 wants this same surface for pinning, EOL and region questions and should consume this derivation rather than re-deriving it.

- [ ] **Step 4: Add both reciprocal edges**

In `docs/audit/handbook-traceability.yaml`:

- Row `...-register-must-match-the-code-a`: add `checks: [data-protection/processor-register]`, and **rewrite the `gap:` block** rather than deleting it. It becomes `recommendation: report-only`, no `target`, and a note saying the check reads the register and its fields while the evidence that settles the claim - whether the agreement was signed, and whether the provider honours the terms it publishes - is a contract and a vendor's current terms, both outside any repository; the residue is that evidence, held by whoever owns compliance and by the provider. This row now carries a `checks:` entry, so the renderer classifies its gap as `residue` rather than `unchecked` automatically - do not add a kind field.
- Row `...-register-must-match-the-code-b`: add `checks: [data-protection/provider-surface]` and **delete the `gap:` block** - the reconciliation is exactly what the check does.

- [ ] **Step 5: Update the exact-set test**

Add `"data-protection/processor-register"` and `"data-protection/provider-surface"` to `test_the_real_checks_tree_loads_clean`, in sorted position.

- [ ] **Step 6: Regenerate, gate, commit**

```bash
uv run python scripts/render_handbook_traceability.py
uv run python scripts/render_handbook_traceability.py --check
uv run pytest tests/ -q
uv run ruff check . && uv run ruff format --check .
git add .agents/skills/data-protection-audit/checks/processor-register.md .agents/skills/data-protection-audit/checks/provider-surface.md docs/audit/handbook-traceability.yaml docs/audit/handbook-traceability.md tests/scripts/test_audit_checks.py
git commit -F - <<'EOF'
feat: check the processor register and the surface the code calls

Part 10 split this section into two rows because the halves rest on
different evidence, and the checks have to keep them apart for the same
reason. What the register contains is a contract and a vendor's terms, so
processor-register reads the register and reports the signing as
unverifiable-from-here rather than passing it. Whether the register matches
the code is settled inside the repository, so provider-surface derives the
outbound surface and reconciles it, and a provider reachable from the code
and missing from the register is the finding.

The derivation reads four sources rather than one because each catches
providers the others miss: an import catches an SDK client, a base URL
catches plain HTTP behind no SDK, MCP and tool endpoints catch what an agent
reaches at run time and no import mentions, and a credential name catches a
call path that lives in infrastructure. The package graph catches none of
them, which is why deps/inventory is a handoff rather than a substitute.

Refs #4
EOF
git show --stat HEAD
```

---

## Task 3: The two local records - residency pinning and boundary minimization

Both are `local` because configuration and the outbound call path live in a partition. They ride the per-partition agent rather than getting their own.

**Files:**
- Create: `.agents/skills/data-protection-audit/checks/residency-pinning.md`
- Create: `.agents/skills/data-protection-audit/checks/boundary-minimization.md`
- Modify: `docs/audit/handbook-traceability.yaml` (rows `keep-the-data-where-the-law-lets-it-be-a`, `minimize-before-the-boundary`)
- Modify: `docs/audit/handbook-traceability.md` (regenerated)
- Modify: `tests/scripts/test_audit_checks.py`

- [ ] **Step 1: Read the two sections and the two rows**

Read "Keep the data where the law lets it be" and "Minimize before the boundary" in `docs/engineering/data-protection.md`, and the rows:

```bash
uv run python -c "
import yaml, pathlib
rows = yaml.safe_load(pathlib.Path('docs/audit/handbook-traceability.yaml').read_text())
for rid in ('data-protection/keep-the-data-where-the-law-lets-it-be-a',
            'data-protection/keep-the-data-where-the-law-lets-it-be-b',
            'data-protection/minimize-before-the-boundary'):
    print(yaml.safe_dump(next(r for r in rows if r['id'] == rid), sort_keys=False, width=200, allow_unicode=True))
"
```

The `-b` row is `process` and carries **no gap and no check** - read it so you know what this task deliberately leaves alone: provider failover, a store's creation-time region, telemetry's jurisdiction, cross-region backups, and the laptop case are deployment facts, not repository facts.

- [ ] **Step 2: Write `checks/residency-pinning.md`**

```yaml
---
id: data-protection/residency-pinning
domain: data-protection
locality: local
handbook:
  - data-protection/keep-the-data-where-the-law-lets-it-be-a
---
```

- H1: `# Region pinning and startup validation`
- **Lead prose**: whether the region is pinned explicitly in configuration, required rather than defaulted, and validated at startup with the missing key named in the error.
- `## Severity` - **Critical**: no region configuration at all where a provider or store is reached, or a region key that silently falls back to a default in the project's own code. **Critical** also for a default that names a real region, since a forgotten configuration line then resolves to a jurisdiction nobody chose. **Important**: a required key with no startup validation, so a missing value surfaces as a failed request rather than a failed boot. **Minor**: validation that fails without naming which key was missing, which costs a deploy cycle rather than a jurisdiction.
- `## Tooling fallback` - a reading pass; no scanner knows which setting is a region. Say what to read: environment templates and example config, the settings or config module where defaults live, the client construction sites for each provider and store, and the startup or lifespan hook where validation would run. Give the test that separates this from Part 5's opposite advice, because an agent that has read Part 5 will otherwise flag a correct default: a value whose wrong setting produces a visible, reversible result may default (a model parameter), and one whose wrong setting is invisible and irreversible must be required (a region). Do not flag a temperature or a model alias under this check.
- `## Fix` - make the region key required, validate it at startup, and name every missing key at once in the error rather than failing on the first. Where the provider SDK takes a region argument, pass the validated value explicitly rather than relying on the SDK's own environment lookup, which is a default one layer down.
- `## Review lens` - **Default-layer completeness** - a key called required in the application is not required if the SDK or the platform supplies a default beneath it; the finding says which layer was checked. **Scope discipline** - this check is the pinned configuration only; where a destination actually lands under failover, backup or telemetry routing is a deployment fact carried by the report's prose and the adoption roadmap, not a row here.

- [ ] **Step 3: Write `checks/boundary-minimization.md`**

```yaml
---
id: data-protection/boundary-minimization
domain: data-protection
locality: local
handbook:
  - data-protection/minimize-before-the-boundary
---
```

- H1: `# Minimization before the trust boundary`
- **Lead prose**: whether personal data is redacted, pseudonymized or truncated before it crosses the trust boundary, with the step in the one shared outbound call path rather than at each call site - and whether its quality cost is measured rather than assumed in either direction.
- `## Severity` - **Critical**: no minimization anywhere on a path that sends personal data across the boundary. **Important**: minimization present but implemented per call site, so a call site added next month will not have it. **Important** also where redaction is in place and its quality cost is assumed rather than measured, in either direction - a team that assumes it away ships a regression under a privacy justification, and a team that assumes it ruinous stops redacting on a hunch. **Minor**: a shared path that a documented escape hatch bypasses.
- `## Tooling fallback` - a reading pass. Say what to read: the outbound client layer or middleware every request goes through, if there is one, and its absence if there is not; the individual call sites, to see whether the step is shared or repeated; and the eval suite, for a dimension that measures the redacted path against the unredacted one. Hand the second half off explicitly: `eval-audit` owns whether a behaviour is evaluated at all, so a project with no eval suite is that domain's finding rather than this one's, and this check reports the missing dimension rather than the missing suite.
- `## Fix` - move the redaction into the single outbound path; prefer sending a reference over a payload, and an extract over a whole document, where the task allows it; use stable pseudonyms where the agent must refer to the same person across turns. Then make redaction an eval dimension and decide it on the numbers: a redaction the metric survives is free, and one it does not is an evidenced trade-off for whoever owns the risk.
- `## Review lens` - **Path coverage** - the finding names whether every outbound call reaches the shared step, and cites a call site that bypasses it where one does. **Cost evidence** - a claim that redaction is or is not costly cites the eval dimension that measured it, and where none exists the row says the cost is unmeasured rather than asserting a direction.

- [ ] **Step 4: Add both reciprocal edges**

- Row `keep-the-data-where-the-law-lets-it-be-a`: add `checks: [data-protection/residency-pinning]`, and **rewrite the `gap:`** to `recommendation: report-only`, no `target`, with a note that the pinning and its startup validation are read from configuration while the other half of the claim - whether a destination outside the permitted region is covered by a lawful transfer route, adequacy, standard contractual clauses or binding corporate rules among them - is a contract and a legal determination that no repository holds.
- Row `minimize-before-the-boundary`: add `checks: [data-protection/boundary-minimization]` and **delete the `gap:` block**; both halves of the claim, the shared-path placement and the measured cost, are readable from the repository.
- Row `keep-the-data-where-the-law-lets-it-be-b`: **unchanged.** Do not add a check or a gap.

- [ ] **Step 5: Update the exact-set test, regenerate, gate, commit**

Add `"data-protection/boundary-minimization"` and `"data-protection/residency-pinning"` to `test_the_real_checks_tree_loads_clean` in sorted position, then:

```bash
uv run python scripts/render_handbook_traceability.py
uv run python scripts/render_handbook_traceability.py --check
uv run pytest tests/ -q
uv run ruff check . && uv run ruff format --check .
git add .agents/skills/data-protection-audit/checks/residency-pinning.md .agents/skills/data-protection-audit/checks/boundary-minimization.md docs/audit/handbook-traceability.yaml docs/audit/handbook-traceability.md tests/scripts/test_audit_checks.py
git commit -F - <<'EOF'
feat: check region pinning and minimization per partition

Both are local rather than global, and the reason is the finding they would
otherwise lose: configuration and the outbound call path live in a
partition, so a monorepo where one service pins its region while another
defaults is exactly what to report, and a global check would average it
into one row.

residency-pinning has to carry Part 5's opposite advice with it, or an agent
that has read Part 5 flags a correct default. The record states the test the
handbook derives: a value whose wrong setting is visible and reversible may
default, one whose wrong setting is invisible and irreversible must be
required. A region is the second kind and a temperature is the first.

boundary-minimization keeps the quality cost in scope rather than treating
redaction as free. Part 10 states the tension outright because a team that
assumes it away ships a regression under a privacy justification, so an
unmeasured cost is a finding in either direction.

Refs #4
EOF
git show --stat HEAD
```

---

## Task 4: Retention limits and the deletion path

Two records against one row. Splitting them is deliberate: a store with no enforced limit and a deletion that reaches the primary store but not the vector index are different findings with different fixes, and one can be clean while the other is Critical.

**Files:**
- Create: `.agents/skills/data-protection-audit/checks/retention-limits.md`
- Create: `.agents/skills/data-protection-audit/checks/deletion-path.md`
- Modify: `docs/audit/handbook-traceability.yaml` (row `retention-and-deletion-are-design-decisions-not-cleanup`)
- Modify: `docs/audit/handbook-traceability.md` (regenerated)
- Modify: `tests/scripts/test_audit_checks.py`

- [ ] **Step 1: Read the section and the row**

Read "Retention and deletion are design decisions, not cleanup" in `docs/engineering/data-protection.md`, and:

```bash
uv run python -c "
import yaml, pathlib
rows = yaml.safe_load(pathlib.Path('docs/audit/handbook-traceability.yaml').read_text())
print(yaml.safe_dump(next(r for r in rows if r['id'] == 'data-protection/retention-and-deletion-are-design-decisions-not-cleanup'), sort_keys=False, width=200, allow_unicode=True))
"
```

- [ ] **Step 2: Write `checks/retention-limits.md`**

```yaml
---
id: data-protection/retention-limits
domain: data-protection
locality: global
handbook:
  - data-protection/retention-and-deletion-are-design-decisions-not-cleanup
---
```

- H1: `# Retention limits per store`
- **Lead prose**: whether every store that holds personal data has a retention limit chosen on purpose, with something enforcing it: a TTL on the record, a lifecycle rule on the bucket, or a scheduled job with a test.
- `## Severity` - **Critical**: a store holding personal data with no limit anywhere. **Important**: a limit documented but unenforced, which is a policy rather than a retention limit. **Important** also for a scheduled job with no test, since nothing tells you the day it stops running. **Minor**: a limit enforced but not stated anywhere a reader can find it, so nobody can say whether it was chosen.
- `## Tooling fallback` - a reading pass over the store enumeration this domain already has. Say to take the store list from `data-protection/data-flow-map`'s derivation rather than rebuilding it, then read, per store, where a limit would live: a TTL or expiry column in the schema or migrations, a lifecycle or expiration rule in the infrastructure definition, a retention setting in a managed service's configuration, or a scheduled job in the CI or scheduler config plus its test. Name the stores whose limit is most often absent because they are an implementation detail of something else: a cache, a vector index, an object bucket of uploads, the log and trace retention on the observability backend, and the backup schedule. Say that a provider-side retention window is `processor-register`'s field and not this check's, so the two do not double-count.
- `## Fix` - choose the limit when the store is created, which is when you know what is in it and why; then enforce it in the mechanism the store already has, preferring a TTL or lifecycle rule over a job because it cannot silently stop. Where a job is the only option, add the test.
- `## Review lens` - **Enforcement evidence** - a limit is reported as enforced only where the finding cites the mechanism (a TTL definition, a lifecycle rule, a scheduled job and its test), never on the strength of a documented policy. **Store coverage** - the row states which stores were enumerated and where the list came from, so a store nobody looked at is visible as unexamined rather than absent.

- [ ] **Step 3: Write `checks/deletion-path.md`**

```yaml
---
id: data-protection/deletion-path
domain: data-protection
locality: global
handbook:
  - data-protection/retention-and-deletion-are-design-decisions-not-cleanup
---
```

- H1: `# Deletion path over the derived copies`
- **Lead prose**: whether a deletion path exists, walks the data-flow map through the derived copies rather than the primary store alone, and is tested.
- `## Severity` - **Critical**: no deletion path at all. **Critical**: a path that reaches the primary store and misses a derived copy, which is a deletion in name only - name the copies that get missed, because they are the substance of this check: embeddings and the vector index, cached model responses, stored traces and run artifacts, eval datasets and the fixtures extracted from real cases, and backups. **Important**: a complete path with no test, so nobody can know it works before the day it matters. **Minor**: a tested path whose store list is hardcoded rather than taken from the map, so it goes stale when a store is added.
- `## Tooling fallback` - a reading pass. Say what to read: the deletion entry point (an API handler, a management command, a job), and then, against the store list from `data-flow-map`, which stores it touches; the test suite, for a test that asserts the walk rather than one that deletes a row; and the derived copies specifically, since an embedding of a personal document is personal data and deleting the document does not empty the index. Say that some of those copies exist because the handbook asked for them - run records are Part 6 doing its job and a dataset built from real inputs is Part 7 doing its job - which is why they are the last place anyone looks. **State the boundary**: whether a deletion propagated provider-side and into backups is not visible from the repository, so report it as unverifiable-from-here with what would settle it, never as `ok`.
- `## Fix` - build the deletion path as a feature that walks the map, so the store list has one definition; test the walk rather than the row; and where a copy cannot be deleted in place (a backup, a provider's retained copy), record the mechanism and the window instead, which is an answer rather than a silence.
- `## Review lens` - **Derived-copy reach** - the finding enumerates which copies the path reaches and which it misses, and a path reported as complete cites the code that reaches each one. **Test substance** - a test counted as covering the path asserts the walk over the stores, not that one delete call returned; a test that would pass with the vector index untouched is not evidence.

- [ ] **Step 4: Add the reciprocal edge**

On row `retention-and-deletion-are-design-decisions-not-cleanup`: add `checks: [data-protection/retention-limits, data-protection/deletion-path]`, and **rewrite the `gap:`** to `recommendation: report-only`, no `target`, with a note that the limits and the deletion path are read from the repository while what a deletion actually did downstream - whether a provider deleted its retained copy, and whether the backups aged out - is outside it; that residue is held by the provider and by whoever operates the backups.

- [ ] **Step 5: Update the exact-set test, regenerate, gate, commit**

Add `"data-protection/deletion-path"` and `"data-protection/retention-limits"` in sorted position, then:

```bash
uv run python scripts/render_handbook_traceability.py
uv run python scripts/render_handbook_traceability.py --check
uv run pytest tests/ -q
uv run ruff check . && uv run ruff format --check .
git add .agents/skills/data-protection-audit/checks/retention-limits.md .agents/skills/data-protection-audit/checks/deletion-path.md docs/audit/handbook-traceability.yaml docs/audit/handbook-traceability.md tests/scripts/test_audit_checks.py
git commit -F - <<'EOF'
feat: check retention limits and the deletion path separately

Two records against one matrix row, because the statuses cannot be shared: a
store with no enforced limit and a deletion that reaches the primary store
but not the vector index are different findings with different fixes, and
one can be clean while the other is Critical. audit-core splits a check when
a status cannot be shared, not when a handbook section can.

Both take their store list from the data-flow map's derivation rather than
rebuilding it, which is the point of Part 10 putting the map first: a
deletion path whose store list has a second definition goes stale the moment
a store is added, and a retention check that enumerates its own stores
disagrees with the map by construction.

Refs #4
EOF
git show --stat HEAD
```

---

## Task 5: The trail residue, and the standing-check row

The last record, and the two matrix rows that change without one. `stored-artifact-pii` owns only what `security/sensitive-data` does not reach.

**Files:**
- Create: `.agents/skills/data-protection-audit/checks/stored-artifact-pii.md`
- Modify: `docs/audit/handbook-traceability.yaml` (rows `personal-data-does-not-belong-in-the-trail`, `verify-against-the-real-artifacts`)
- Modify: `docs/audit/handbook-traceability.md` (regenerated)
- Modify: `tests/scripts/test_audit_checks.py`

- [ ] **Step 1: Read the section, the existing near-miss mapping, and both rows**

Read "Personal data does not belong in the trail" and "Verify against the real artifacts" in `docs/engineering/data-protection.md`. Read `.agents/skills/security-audit/checks/sensitive-data.md` in full - it is short, and it is what this record must not duplicate. Then:

```bash
uv run python -c "
import yaml, pathlib
rows = yaml.safe_load(pathlib.Path('docs/audit/handbook-traceability.yaml').read_text())
for rid in ('data-protection/personal-data-does-not-belong-in-the-trail',
            'data-protection/verify-against-the-real-artifacts',
            'security-supply-chain/verify-against-the-real-artifacts',
            'lifecycle/make-the-standard-executable-and-audit-periodically-b'):
    print(yaml.safe_dump(next(r for r in rows if r['id'] == rid), sort_keys=False, width=200, allow_unicode=True))
"
```

The last two are the precedent for step 4: both are standing-check rows, both carry `report-only`, and neither cites a check.

- [ ] **Step 2: Write `checks/stored-artifact-pii.md`**

The tooling question the spec opened is **resolved**: this is the one record in the domain that carries a `tooling:` key, and the tool is `pdscan`, under `any:`. Do not re-run the research, and do not add a second tool without verifying it against its own documentation the same way.

Frontmatter, verbatim:

```yaml
---
id: data-protection/stored-artifact-pii
domain: data-protection
locality: global
handbook:
  - data-protection/personal-data-does-not-belong-in-the-trail
tooling:
  any: [pdscan]
---
```

Four things about that frontmatter, each of which a plausible-looking edit would break:

- **`any:` rather than `python:` and `typescript:`.** `pdscan` scans files and knows nothing about the language that wrote them, and `any:` is the lens shape `security/secrets-in-code` already uses for a language-agnostic scanner. It also satisfies `test_every_tooling_record_offers_a_typescript_lens`, which checks for a `typescript:` **or** `any:` key.
- **No `needs:` key.** `pdscan` answers from a read-only clone: no dependency graph, no execution of the target's code. An omitted tier is the positive claim that this is so, which is the correct claim here.
- **Therefore no `ungranted_note`.** The validator *rejects* the field where no tool in any language carries a tier, because a note about a withheld grant that silences nothing is vacuous. Adding one out of caution fails the loader.
- **`pdscan` is a standalone binary in no language registry**, so no one-shot runner can fetch it - the same kind, and the same consequence, as `osv-scanner` in `deps/vulnerabilities`. The fallback prose must say so, or an agent will try `uvx pdscan`, watch it fail like a missing package, and report `no-evidence` for a check the reading pass could have answered.

- H1: `# Personal data in stored artifacts`
- **Lead prose**: whether personal data has reached the artifacts that outlive the call - stored traces and run records, eval datasets, and the fixtures extracted from real cases - and state in the first sentence that the call-site half of this claim belongs to `security/sensitive-data`, so the two do not overlap.
- `## Severity` - **Critical**: personal data found in a stored artifact that is committed to the repository, since it is then in the history and on every clone. **Critical**: an eval dataset or fixture built from a raw copy of production. **Important**: a trace or run-record schema that captures a payload field, where no artifact is committed but the production store will hold them. **Minor**: an artifact carrying an identifier where a reference would do, which is the shape Part 10 asks for rather than a leak.
- `## Tooling fallback` - the tool **and** the reading pass, because neither is sufficient alone. In order:
  - **Detect first**, per `audit-core`: prefer `pdscan` if the inventory reports the audit environment already carries it. It is a standalone binary in no language registry, so no one-shot runner can fetch it - do not attempt `uvx pdscan` or `npx pdscan`, which fails the way a missing package fails and lands as `no-evidence` for a check the reading pass could have answered.
  - **Scope the invocation to the artifact directories** rather than the clone root - `pdscan file://<dir>` over the log, trace, fixture and eval-data directories. It line-scans every file that is not video or bzip2 and descends into zip and gzip, so pointed at the whole tree it reports `.git` objects and binary assets as noise.
  - **Two caveats that decide what its output means**, and both belong in the prose because either one turns a tool that ran into a false clean. Its rules are US-shaped and regex-based - a US social-security number's shape, US street suffixes, a list of common US surnames - with nothing for passports, IBANs or non-US national identifiers, so **empty output discharges this check only on the axes it scans** and the rest falls to the reading pass below. And its flag that prints matched values propagates the very leak the check exists to find, so a finding reports the location and the rule name, and quotes a value only where a false positive has to be demonstrated.
  - **The reading pass, which runs whether or not the tool did**: committed fixture and test-data directories; eval datasets and their generation scripts, which is where "built from real inputs" is visible even when the data is not committed; the trace and run-record schema or emitter, for which fields it captures; and the log and trace configuration for what is shipped to a backend.
  - **What no pass can see**: whether a fixture's source was synthetic, consented, or a real case somebody redacted is provenance, and provenance is not in the file. Report it as unverifiable-from-here with who would know.
  - **Reject the secret-scanner substitution explicitly.** `gitleaks`, `trufflehog` and `detect-secrets` each scope themselves to credentials in their own documentation, and a credential is not a data subject, so `security/secrets-in-code`'s tooling list is not transferable and a clean secret scan is no evidence about this check.
- `## Fix` - replace the payload with the identifier you can join back; rebuild fixtures from synthetic or consented data, or from real data put through the production redaction path; and where a committed artifact already holds personal data, say that removing it from the working tree does not remove it from the history, so the fix is a history rewrite or a rotation of what was exposed, decided with whoever owns the risk.
- `## Review lens` - three paragraphs. **Boundary with the code lens** - a finding here is about a stored artifact; a personal-data leak at a logging or exception call site is `security/sensitive-data`'s row and is not restated in this one. **Provenance honesty** - a fixture is not reported as synthetic because it looks synthetic; where provenance is not recorded, the row says so and names who would know. **Scan-axis honesty** - a row resting on an empty scanner run names the axes that run covered, because the scanner's rules are regionally shaped and a clean result over them is not a clean result over personal data; and no row quotes a matched value it did not have to quote to demonstrate a false positive.

- [ ] **Step 3: Add the trail row's reciprocal edge**

On row `personal-data-does-not-belong-in-the-trail`: **append** `data-protection/stored-artifact-pii` to the existing `checks:` list, which already holds `security/sensitive-data` - do not replace it. Then rewrite the `gap:` note. It stays `recommendation: report-only` with no target, and it narrows: the two checks now cover the call sites and the stored artifacts between them, so the residue is fixture and dataset **provenance** - whether the source was synthetic, consented, or a real case put through redaction - which is a fact about how a file was made and is not in the file.

Also add the reciprocal `handbook:` anchor **nowhere** - `security-audit/checks/sensitive-data.md` already cites this row, from #47.

- [ ] **Step 4: Convert the standing-check row's gap**

On row `data-protection/verify-against-the-real-artifacts`: keep `checks:` absent, and change the `gap:` from `recommendation: new-domain` with `target: '#4'` to `recommendation: report-only` with **no target**. Rewrite the note: the reason it was `new-domain` was that `audit-core` had no lens in this domain to apply its report-only-then-fix cadence through, and this issue supplies the lens; what remains is the audit cadence itself - whether the sweep is run, and whether past reports separated clean from not-visible-from-here - which sits outside every skill's evidence base, exactly as it does on `lifecycle/make-the-standard-executable-and-audit-periodically-b` and `security-supply-chain/verify-against-the-real-artifacts`. Cite both row ids in the note so the disposition is checkable against its precedent.

Leave `data-protection/checklist-a-data-protection-sweep` and `data-protection/see-also` untouched: all seven checklist rows in the matrix carry no checks and no gap, and mapping a recap would double-count every check it recaps.

- [ ] **Step 5: Update the exact-set test, regenerate, gate, commit**

Add `"data-protection/stored-artifact-pii"` in sorted position, then:

```bash
uv run python scripts/render_handbook_traceability.py
uv run python scripts/render_handbook_traceability.py --check
uv run pytest tests/ -q
uv run ruff check . && uv run ruff format --check .
git add .agents/skills/data-protection-audit/checks/stored-artifact-pii.md docs/audit/handbook-traceability.yaml docs/audit/handbook-traceability.md tests/scripts/test_audit_checks.py
git commit -F - <<'EOF'
feat: own the trail residue, and retire the standing-check gap

security/sensitive-data already flags personal data reaching a log or an
error message, so this record takes only what a code lens cannot see: the
artifacts that outlive the call, which are stored traces, run records, eval
datasets and the fixtures somebody extracted from a real case because it
reproduced a bug. Those are the copies that persist longest and get shared
widest, and the near-miss mapping on that row recorded them as residue
precisely so a later check would own them.

verify-against-the-real-artifacts stops being new-domain here, and not
because this issue checks it. Its gap said audit-core had no lens in this
domain to apply its cadence through; supplying the lens removes that reason
and leaves the cadence itself, which no skill can see. That is report-only,
the same disposition its two siblings carry, and the note now cites them.

Refs #4
EOF
git show --stat HEAD
```

---

## Task 6: The count and list sweep

Nine files assert a domain count or a list that a ninth domain falsifies. Only the two tests are caught by a gate, which is why this is its own task with its own reviewer.

**Files:**
- Modify: `.agents/skills/audit/SKILL.md`
- Modify: `.agents/skills/audit-core/SKILL.md`
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `docs/audit/handbook-traceability.yaml` (one gap note)
- Modify: `docs/audit/handbook-traceability.md` (regenerated)
- Read, and modify only if disturbed: `docs/audit/sweep-obligations.md`

- [ ] **Step 1: Find every assertion rather than guessing at the list**

```bash
grep -rniE 'eight (domain|skill|migrated)|eight of the|the other seven|nine domain' README.md CLAUDE.md docs/README.md docs/audit/*.md docs/audit/*.yaml .agents/skills/audit/SKILL.md .agents/skills/audit-core/SKILL.md
grep -rn 'docs-audit, deps-audit\|docs-audit`, `deps-audit\|prompt-audit)' .agents/skills/audit/SKILL.md .agents/skills/audit-core/SKILL.md
```

Read each hit and decide what kind of claim it is before editing. **Not every "eight" becomes "nine".**

- [ ] **Step 2: Edit `audit/SKILL.md`**

**Two bullets in this file already carry the personal-data declaration** - one in the step-0 list, one in the fan-out brief - added when Task 1's review found that the domain skill cited a step-0 question no engine file asks. Do not add a third, and do not reword them into the count sweep's edits; read them first so the domain list you are about to fix stays consistent with what they say.

- The `description` frontmatter: the parenthesised domain list `(docs, dependencies, architecture, security, CI/CD, tests, evals, prompts/SOPs)` gains data protection, and the `*-audit` list in the body's opening paragraph gains `data-protection-audit`.
- "eight domain agents would otherwise each re-derive the same partition and language map" and the second instance in the materialize-the-tree paragraph: these are counts of the agents a sweep fans out, so they become nine.
- "the graph the other seven domains are measuring at the same moment" and "the other seven domains": arithmetic over the family minus the one being discussed, so it becomes eight.
- Anywhere the description or body enumerates the domains to say what the front door orchestrates, add this one. Do not add it to a sentence that is about a specific past measurement.

- [ ] **Step 3: Edit `audit-core/SKILL.md`**

- The `description` frontmatter's parenthesised list of domain skills gains `data-protection-audit`.
- **Leave "Measured across the eight migrated domains" as written.** It records a measurement taken over the eight that were migrated, and re-numbering it would claim a measurement nobody took. If the surrounding sentence reads as a claim about the family's current size rather than about that migration, adjust the surrounding words to make the scope explicit rather than changing the number.

- [ ] **Step 4: Recompute both numbers in `README.md`, never carry them**

The domain count is the number of `*-audit` directories, which is the same glob the front door detects domains with and the same one `test_every_audit_skill_has_a_non_empty_checks_directory` uses. Neither `audit` nor `audit-core` matches it, since neither name carries a `-audit` suffix. Print the per-domain record counts and the two totals together, so the number written into the prose is the one the tree just reported:

```bash
for d in .agents/skills/*-audit/; do n=$(ls "$d/checks" 2>/dev/null | wc -l | tr -d ' '); echo "$(basename $d): $n"; done
echo "domains: $(ls -d .agents/skills/*-audit | wc -l | tr -d ' ')"
echo "records: $(ls .agents/skills/*/checks/*.md | wc -l | tr -d ' ')"
```

Then update `README.md`'s "Eight domains, 69 check records" to the computed values, and `CLAUDE.md`'s "eight `<domain>-audit` skills" to the computed count.

- [ ] **Step 5: De-number the gap note in the YAML**

`docs/audit/handbook-traceability.yaml`, row `observability/capture-per-subagent-per-tool-usage`, whose gap note reads "not one of the eight skills declares a check for run instrumentation". **De-number it** rather than re-numbering: "no skill in the family declares a check for run instrumentation". A count in a gap note goes stale every time a domain is added, and the note's point is that nothing checks it. This is the precedent already set when a "six checks" note became "none of its checks".

- [ ] **Step 6: Check `sweep-obligations.md`**

`CLAUDE.md` requires it after editing `audit-core/SKILL.md` or `audit/SKILL.md`: that file is hand-maintained, one row per `audit-core` obligation, and `tests/test_sweep_obligations.py` fails on an anchor that no longer occurs in `audit-core` exactly once or a quotation that is no longer verbatim.

```bash
uv run pytest tests/test_sweep_obligations.py -q
```

If it fails, the edit disturbed a quoted phrase or an anchor: restore the quotation to verbatim, or update the row to match the new wording, whichever is correct. Also read the rows touching the fan-out brief and the domain list, since a disposition can become untrue without any anchor moving - that is a reading pass the test cannot do.

- [ ] **Step 7: Regenerate, gate, commit**

```bash
uv run python scripts/render_handbook_traceability.py
uv run python scripts/render_handbook_traceability.py --check
uv run pytest tests/ -q
uv run ruff check . && uv run ruff format --check .
git add .agents/skills/audit/SKILL.md .agents/skills/audit-core/SKILL.md README.md CLAUDE.md docs/audit/handbook-traceability.yaml docs/audit/handbook-traceability.md
git commit -F - <<'EOF'
prompt: tell the sweep there is a ninth domain

The front door detects available domains from its own siblings, so
data-protection-audit joins /audit all the moment its checks directory
exists - but the prose an agent reads still enumerated eight, and a list
that disagrees with the detection is how a domain gets dropped from a scope
the code would have included.

Not every eight became nine. The agent counts in the sweep's shared-artifact
arguments are counts of what it fans out, so they moved. "The other seven
domains" is arithmetic over the family minus the one under discussion, so it
became eight. audit-core's "eight migrated domains" is a record of a
measurement taken over those eight and stays: re-numbering it would claim a
measurement nobody took. The gap note asserting no skill checks run
instrumentation is de-numbered rather than re-numbered, because a count
there goes stale on every domain added and the point was that nothing
checks it.

Refs #4
EOF
git show --stat HEAD
```

---

## Task 7: Verification, discovery, and the reading pass no gate can do

**Files:** none created or modified unless a check fails. This task's deliverable is evidence.

- [ ] **Step 1: Run the whole gate on the finished branch**

```bash
uv run python scripts/render_handbook_traceability.py --check
uv run pytest tests/ -q
uv run ruff check . && uv run ruff format --check .
uv run python scripts/render_handbook_artifact.py
```

Record the numbers. The artifact renderer's line should still read `sections: 13 ... em-dashes: 0  residual .md hrefs: 0` - the handbook is unchanged by this issue, so a change there is a regression.

- [ ] **Step 2: Verify the new skill is discoverable, with a check that reads this tree**

`claude plugin validate` passes on a plugin that discovers no skills, so it proves nothing. **And `claude plugin details handbook-audit` does not prove it either on an unmerged branch** - it reads the installed marketplace clone under `~/.claude/plugins/marketplaces/`, which tracks a pushed commit and is typically many commits behind, so it reports the old skill count and the old description no matter what this tree holds. Running it here and reading its count as this branch's would be a verification step measuring the wrong tree.

Two checks that do read this tree:

```bash
uv run python -c "
import sys; sys.path.insert(0, 'scripts')
from audit_checks import SKILLS_DIR, load_checks
checks, errors = load_checks(SKILLS_DIR)
assert errors == [], errors
print('domains:', len({c.domain for c in checks.values()}), 'records:', len(checks))
"
```

That proves the records parse and the domain resolves from this working tree. The second is the running session's own available-skills list, which names a newly written skill within a turn or two of its `SKILL.md` landing - the only live evidence that the frontmatter parses *as a skill* rather than as a file. Note it in the report when it happens, because nothing re-creates it later.

Then re-run `claude plugin details handbook-audit` **after the merge**, where the installed clone has the commit and the count means what it says.

- [ ] **Step 3: Confirm the gap accounting moved the way the spec said**

```bash
uv run python -c "
import yaml, pathlib
rows = yaml.safe_load(pathlib.Path('docs/audit/handbook-traceability.yaml').read_text())
dp = [r for r in rows if r['id'].startswith('data-protection/')]
print('rows:', len(dp))
for r in dp:
    g = r.get('gap') or {}
    kind = 'residue' if (g and r.get('checks')) else ('unchecked' if g else '-')
    print(' ', r['id'].split('/', 1)[1], '| checks=', r.get('checks'), '| gap=', g.get('recommendation'), g.get('target'), '| kind=', kind)
print('still targeting #4:', [r['id'] for r in rows if (r.get('gap') or {}).get('target') == '#4'])
"
```

Expected: no `data-protection/` row still targets `#4`; five rows carry a check and no gap; four carry both, so the renderer classifies them `residue`; the `-b` residency row, the checklist row and the see-also row are unchanged.

- [ ] **Step 4: The reading pass**

Dispatch a subagent that has **not** seen the implementation, pinned to this worktree (pass the absolute root and require it to confirm `git rev-parse --show-toplevel` matches before reading). Give it #4's eight dimensions and the eight records, and ask three questions no gate can answer:

1. Does each record's prose actually check the clause its `handbook:` row claims, or does it check something adjacent?
2. Does any record duplicate `security/sensitive-data` rather than cross-linking it?
3. Does any record infer a personal-data surface and then flag the code against it, which the applicability rule forbids?

Also ask for the stale-prose pass `CLAUDE.md` requires: `grep` for anything the change invalidated **without touching**, scoped by blast radius rather than by the diff.

- [ ] **Step 5: Push and open the PR**

Push the branch, open the PR with `Closes #4`, a **Test plan** checklist with every command above and its recorded result, and a section naming which of the eight dimensions each record covers. Then **read the automation** - `check`, Cursor Bugbot on every push, and Cursor Security Agent once the PR is marked ready - before handing the conversation back. Do not merge.

---

## Self-Review

Run against the spec after the plan is written.

**Spec coverage.** Eight checks: Tasks 1-5. Applicability rule: Task 1 step 2 item 6. Reciprocal matrix half, all nine row changes: Tasks 1 step 4, 2 step 4, 3 step 4, 4 step 4, 5 steps 3-4. Deliverable: Task 1 step 2 item 10. Blast radius: Task 6. Verification: Task 7. Tooling open question: Task 5 step 2, with both branches specified.

**Placeholders.** Every record's frontmatter is given verbatim; every body section is specified by content rather than by "write the section". The one genuinely open value is `stored-artifact-pii`'s `tooling:` key, and both outcomes are written out with the exact consequence for `needs:` and `ungranted_note`.

**Type consistency.** Check ids are spelled identically in the record frontmatter, the matrix `checks:` entries, the test additions and the commit messages: `data-flow-map`, `processor-register`, `provider-surface`, `residency-pinning`, `boundary-minimization`, `retention-limits`, `deletion-path`, `stored-artifact-pii`, each prefixed `data-protection/`. Matrix row ids are quoted from the YAML rather than retyped from the issue comment, which predates the review round that renamed the processor section and split the residency row.
