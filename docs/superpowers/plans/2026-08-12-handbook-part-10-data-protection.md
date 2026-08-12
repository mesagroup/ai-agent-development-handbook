# Handbook Part 10: Data Protection & Privacy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Do not fan these tasks out to parallel subagents.** Seven of the nine tasks author prose in one distinctive voice, and this repository has already recorded what parallel authoring does to that: `docs/stories/2026-08-04-making-a-foreign-key-real.md` describes seven parallel tasks each passing its own review, after which the whole-branch pass found four fresh instances of the exact defect class the branch existed to remove. Voice drift lives between tasks, so only a reader of the whole thing can see it. Run the tasks sequentially in one session, then take the whole-branch review at the end seriously.

**Goal:** Add `docs/engineering/data-protection.md` as Part 10 of the handbook, the normative account of data protection that #4's `data-protection-audit` domain skill will be grounded in, per the approved spec `docs/superpowers/specs/2026-08-12-handbook-part-10-data-protection-design.md`.

**Architecture:** One new numbered part standing beside Part 9 as the second standing obligation, wired into both renderers (`scripts/render_handbook_artifact.py`'s `PARTS`, `scripts/render_handbook_traceability.py`'s `PART_ORDER` and `PART_TITLES`), the README spine, and the traceability matrix. Task 1 lands the file skeleton with both renderers wired and a whole-part matrix row, so every gate is green from the first commit; Tasks 2 to 5 author the sections into the already-wired page, each commit adding its sections *and* their matrix rows together; Task 6 shrinks Part 9 to a cross-link; Task 7 sweeps every part-count and hand-off assertion in the repo; Tasks 8 and 9 verify.

**Tech Stack:** Markdown (handbook prose), YAML (the traceability matrix), Python 3.11 (both render scripts), pytest, ruff, the `d2` CLI (diagrams).

## Global Constraints

Copied verbatim into every task; all of these are binding for every commit on this branch.

- **Zero em-dashes** (the character `—`, U+2014) anywhere under `docs/engineering/`, `docs/superpowers/specs/` or `docs/superpowers/plans/`. Use ` - `. The artifact renderer prints the count and it must stay `0`.
- **One paragraph per source line.** Markdown is never hard-wrapped. Never reflow a line you did not change.
- **Cross-links inside `docs/engineering/` are relative** (`[Part 6](observability.md)`), matching every existing part. Links that a *skill* would read are absolute GitHub URLs; nothing in this plan writes one into a skill.
- **Voice:** the handbook's own. Directives backed by their reasons, clipped imperative, portable phrasing ("here is what a good setup provides"), no institutional "we", no vendor names beyond what the parts already name, no project-specific values. Each part opens by locating itself in the story and stands alone for a reader landing on it cold.
- **Never assert a count you did not compute**, and prefer a structural reason to a snapshot. This applies to the prose you write *and* to the prose you edit.
- **No environment-specific values** in any committed file: no absolute personal paths, profile names, tokens, hostnames or emails.
- **Cite primary sources.** Where the part names a legal regime or mechanism, link the primary source as Part 9 does for [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj). Never fabricate a citation or a URL.
- **Matrix and records are one edge set.** A matrix row's `checks:` entry and a check record's `handbook:` entry are two directions of one edge; add both in the same commit or the gate fails.
- **Verification gates, run at the end of every task, all must pass:**
  1. `caffeinate uv run python scripts/render_handbook_traceability.py` then `caffeinate uv run python scripts/render_handbook_traceability.py --check` (the second confirms the rendered Markdown was committed current).
  2. `caffeinate uv run python scripts/render_handbook_artifact.py` - the counter line must show `em-dashes: 0`, and `residual .md hrefs: 1` with exactly one `WARNING unmapped link` for `engineering-notes.md`, which is pre-existing and expected.
  3. `caffeinate uv run pytest tests/ -q`
  4. `caffeinate uv run ruff check . && caffeinate uv run ruff format --check .`
- **Commits:** stage explicit paths, never `git add -A`. Body says what and why, ends with `Refs #47` and the `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` trailer. No Claude credits beyond that trailer.

**Baseline counters, measured on `main` before this branch:** `sections: 12  task items: 83  diagrams: 7  em-dashes: 0  residual .md hrefs: 1`. After Task 1 `sections` is `13`; `task items` grows by the size of Part 10's checklist in Task 5; `diagrams` becomes `8` in Task 2.

---

### Task 1: The skeleton part, both renderers, and a whole-part row

The part file lands with an H1, its bridge paragraph, its opening paragraph and **no `##` sections at all**. That is deliberate and it is what keeps the gate green: `validate` demands a row per `##` section, and for a part with no sections it instead demands one whole-part row whose anchor equals the part stem (`render_handbook_traceability.py:312`). So this task's matrix cost is exactly one row, and Tasks 2 to 5 replace it.

**Files:**
- Create: `docs/engineering/data-protection.md`
- Modify: `scripts/render_handbook_artifact.py` (the `PARTS` list and the comment above it)
- Modify: `scripts/render_handbook_traceability.py` (`PART_ORDER`, `PART_TITLES`)
- Modify: `docs/audit/handbook-traceability.yaml` (one whole-part row)
- Modify: `docs/audit/handbook-traceability.md` (generated; re-render, never hand-edit)
- Test: `tests/scripts/test_render_handbook_traceability.py`

**Interfaces:**
- Produces: the file `docs/engineering/data-protection.md` whose H1 is exactly `# Part 10. Data protection & privacy`. Both renderers key off the stem `data-protection`. Tasks 2 to 5 append `##` sections to this file, in order, above nothing (the file ends with its last section until Task 5 adds the hand-off and See also).
- Produces: the matrix row id prefix `data-protection/`, which every later row uses.

- [ ] **Step 1: Write the failing test**

`validate_parts` is what catches a part file the constants forgot. Its existing test monkeypatches a fake handbook, so it proves the mechanism, not that Part 10 is wired. Add the direct assertion to `tests/scripts/test_render_handbook_traceability.py`:

```python
def test_part_order_covers_every_handbook_part_on_disk():
    """The real handbook, not a fixture: a new part file must reach both constants."""
    errors = rht.validate_parts(rht.handbook_part_numbers(rht.HANDBOOK_DIR))
    assert errors == []
    assert "data-protection" in rht.PART_ORDER
    assert rht.PART_TITLES["data-protection"] == "Part 10: Data protection & privacy"
```

- [ ] **Step 2: Run it and watch it fail**

Run: `caffeinate uv run pytest tests/scripts/test_render_handbook_traceability.py -v -k part_order_covers`
Expected: FAIL with `KeyError: 'data-protection'` (the file does not exist yet, so `validate_parts` returns no error either; the `PART_TITLES` lookup is what fails).

- [ ] **Step 3: Create the part file**

Create `docs/engineering/data-protection.md` with exactly this content. Note the H1 uses `Part 10.` with a **period** while `PART_TITLES` uses `Part 10:` with a **colon**; `_PART_NUMBER_RE` reads the first and `_TITLE_NUMBER_RE` the second, and they are compared for equality, so getting either punctuation wrong fails the gate with a confusing message.

```markdown
# Part 10. Data protection & privacy

*The previous part keeps the machine safe from whoever attacks it. This one keeps the data lawful for the people it belongs to, which is a different obligation with a different subject: the risk here is the system working exactly as designed, shipping personal data somewhere it may not be. It stands over every change alongside Part 9, and it reaches back into the trail and the datasets the earlier parts asked you to keep.*

Part 9 asks what an attacker could do to your system. This part asks what your system does to the people whose data passes through it, and the two questions have almost disjoint answers. An agentic product makes the question sharper than most: the trust boundary is crossed on every model call, so personal data leaves your control as a matter of routine rather than by accident, and the artifacts the rest of this handbook asks you to keep - the run trail ([Part 6](observability.md)), the eval dataset built from real inputs ([Part 7](evaluation.md)), the decision trail ([Part 8](documentation.md)) - are themselves stores of personal data that nobody set out to create. Where you operate under a data-protection regime ([GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj) and the like), that posture has to be demonstrable rather than merely intended.

This part is engineering, not legal advice: it states what to build and maintain in the repository so that the legal question has an answer, and it says plainly which half of each answer no repository can settle. Bring the other half to whoever owns compliance where you work.
```

- [ ] **Step 4: Wire the traceability renderer**

In `scripts/render_handbook_traceability.py`, `PART_ORDER` gains `"data-protection"` between `"security-supply-chain"` and `"troubleshooting"`, and `PART_TITLES` gains `"data-protection": "Part 10: Data protection & privacy",` in the same position.

- [ ] **Step 5: Wire the artifact renderer**

In `scripts/render_handbook_artifact.py`, `PARTS` gains `("p10", "data-protection", "Data protection &amp; privacy"),` between the `p9` row and the `troubleshooting` row. The sidebar label is HTML, hence `&amp;` (the `p9` row uses the same escaping). Update the comment above `PARTS` where it says "the nine parts follow" to say ten.

- [ ] **Step 6: Add the whole-part row**

In `docs/audit/handbook-traceability.yaml`, after the Part 9 block and before the `# --- Troubleshooting guide` comment, add a part banner comment and the single row:

```yaml
# --- Part 10: Data protection & privacy -------------------------------------

- id: data-protection/data-protection
  section: "Part 10. Data protection & privacy"
  claim: Locates the part as the second standing obligation beside Part 9 - the data subject rather than the attacker as the subject, the model call as a routine crossing of the trust boundary, and the handbook's own trail and eval artifacts as unintended stores of personal data.
  class: informative
  note: Part-opening prose while the part carries no sections; Tasks 2 to 5 of the implementation plan replace this row with one per section.
```

- [ ] **Step 7: Re-render and run every gate**

```bash
caffeinate uv run python scripts/render_handbook_traceability.py
caffeinate uv run python scripts/render_handbook_traceability.py --check
caffeinate uv run python scripts/render_handbook_artifact.py
caffeinate uv run pytest tests/ -q
caffeinate uv run ruff check . && caffeinate uv run ruff format --check .
```
Expected: the traceability gate prints a row count one higher than before and then passes `--check`; the artifact renderer prints `sections: 13`, `em-dashes: 0`, `residual .md hrefs: 1`; pytest and ruff green.

- [ ] **Step 8: Commit**

```bash
git add docs/engineering/data-protection.md scripts/render_handbook_artifact.py scripts/render_handbook_traceability.py docs/audit/handbook-traceability.yaml docs/audit/handbook-traceability.md tests/scripts/test_render_handbook_traceability.py
git commit
```
Message: `docs: open Part 10, the second standing obligation` - body explains that Part 9 protects the system from an attacker and Part 10 protects a data subject from the system working as designed, that both renderers hardcode the part list so a new part file is invisible to one and fails the gate in the other, and that the whole-part row is the shape `validate` demands of a sectionless part. `Refs #47`.

---

### Task 2: The map and the register (sections 1, 2a, 2b)

The three sections that establish what there is to protect and who is allowed to see it. Section 2 splits into two matrix rows because it makes two claims with different evidence bases: the register's *contents* rest on evidence outside the repository, while the register's *agreement with the code* is settled inside it.

**Files:**
- Modify: `docs/engineering/data-protection.md` (append three `##` sections)
- Modify: `docs/audit/handbook-traceability.yaml` (replace the whole-part row with three section rows)
- Modify: `docs/audit/handbook-traceability.md` (generated)

**Interfaces:**
- Consumes: the file and the row prefix from Task 1.
- Produces: heading texts whose slugs the rows depend on. Write them **exactly** as given; `slugify` lowercases, drops every character outside `[a-z0-9 _-]`, and turns spaces into hyphens, so a changed comma or colon changes the row id.

- [ ] **Step 1: Write section 1**

Heading, exactly: `## Know what personal data you hold, and where it goes`

The directive: keep a data-flow map next to the code and maintain it with the code. It enumerates three things - where personal data **enters** (uploads, forms, integrations, and the inputs a user types at an agent), where it **rests** (primary store, object store, vector index, caches, logs, eval datasets, backups), and every **outbound edge** that leaves your trust boundary. A data-protection regime knows this artifact as records of processing; name that, so a reader can connect the engineering artifact to the compliance one, and say that the two are the same list kept in two registers only when nobody maintains the first.

The reason, which is what earns the section its place before every other: every later directive in this part is a question asked of one edge or one store, and a team that cannot enumerate them is answering only about the ones it happens to remember. The map is what turns "do we redact before sending?" from an opinion into a question with a finite number of answers.

Include the d2 diagram here (the artifact renderer renders ` ```d2 ` fences, and the counter must go from 7 to 8):

````
```d2 title="Personal data crosses the trust boundary on every model call"
direction: right
u: Data subject
app: Your system
b: Minimize at the boundary {shape: hexagon}
p: Third-party processor
s: Your stores {shape: cylinder}
u -> app
app -> s: at rest, with a retention limit
app -> b -> p: model, search, OCR, tracing
```
````

- [ ] **Step 2: Write section 2a and 2b under one heading**

Heading, exactly: `## Every processor needs a legal basis, and the register must match the code`

First claim (row `-a`): every third party that sees personal data on your behalf is a processor, and each one needs a legal basis you can produce. Enumerate what the list actually contains, because the enumeration is the useful part: the model and LLM APIs, and also search providers, OCR and extraction services, hosting, and the three teams routinely forget - tracing and observability SaaS, error trackers, and eval platforms, every one of which receives prompts, and a prompt carries whatever personal data the task put in it. For each processor record three things: a signed data processing agreement, whether the provider trains on your data (and that you have opted out where the default is that it does), and the retention window. State the rule that makes the record useful: a provider whose retention window you cannot state is a provider you have not accounted for, which is the same test [Part 9](security-supply-chain.md) applies to a dependency.

Second claim (row `-b`): the register is checked against what the code actually calls. Derive the provider list from the code - SDK imports, configured base URLs, MCP servers and tool endpoints, the credentials the deployment carries - and reconcile it with the register. A provider reachable from the code and absent from the register is the finding, and it is the half of this question a repository can settle on its own; whether the agreement was signed is not. Say that explicitly, because it is what stops a report claiming compliance it cannot see.

- [ ] **Step 3: Replace the whole-part row with three section rows**

In `docs/audit/handbook-traceability.yaml`, delete the `data-protection/data-protection` row added in Task 1 and put these in its place:

```yaml
- id: data-protection/know-what-personal-data-you-hold-and-where-it-goes
  section: "Know what personal data you hold, and where it goes"
  claim: Keep a data-flow map beside the code, maintained with it, enumerating where personal data enters, every store it rests in (primary store, object store, vector index, caches, logs, eval datasets, backups) and every outbound edge that leaves the trust boundary; it is the same list a data-protection regime calls records of processing.
  class: artifact
  severity: important
  gap:
    recommendation: new-domain
    target: "#4"
    note: no skill reads for a data-flow map or reconstructs one from the code, and absence of the map is the finding rather than a pass; this is the data-protection domain the target issue creates.

- id: data-protection/every-processor-needs-a-legal-basis-and-the-register-must-match-the-code-a
  section: "Every processor needs a legal basis, and the register must match the code"
  claim: Treat every third party that sees personal data on your behalf as a processor - model APIs, search, OCR and extraction, hosting, and the ones routinely forgotten because they receive prompts rather than documents (tracing and observability SaaS, error trackers, eval platforms) - and record for each a signed DPA, whether the provider trains on your data, and the retention window.
  class: artifact
  severity: critical
  gap:
    recommendation: new-domain
    target: "#4"
    note: the evidence is a signed agreement and a provider's published terms, both outside the repository entirely; nothing in the family reads either, and this row carries the claim that used to sit on the Part 9 dependency row.

- id: data-protection/every-processor-needs-a-legal-basis-and-the-register-must-match-the-code-b
  section: "Every processor needs a legal basis, and the register must match the code"
  claim: Reconcile the register against what the code actually calls - SDK imports, configured base URLs, MCP servers and tool endpoints, the credentials the deployment carries - because a provider reachable from the code and absent from the register is the half of the question a repository can settle on its own.
  class: static
  severity: critical
  gap:
    recommendation: new-domain
    target: "#4"
    note: deps-audit's inventory is the package graph, so a provider reached over HTTP never enters it, and no skill derives an outbound-provider list from imports, base URLs or tool endpoints.
```

- [ ] **Step 4: Re-render and run every gate**

The five commands from the Global Constraints. Expected: `sections: 13`, `diagrams: 8`, `em-dashes: 0`, `residual .md hrefs: 1`.

- [ ] **Step 5: Commit**

Message: `docs: Part 10's map and its processor register` - the body says why the register rather than the contract is the engineering artifact, and why the section splits into two rows (the contents rest on evidence outside the repository; the agreement with the code does not). `Refs #47`.

---

### Task 3: Residency and minimization (sections 3, 4)

**Files:**
- Modify: `docs/engineering/data-protection.md` (append two `##` sections)
- Modify: `docs/audit/handbook-traceability.yaml`, `docs/audit/handbook-traceability.md`

**Interfaces:**
- Consumes: the file from Tasks 1 and 2. Append below section 2, above nothing.

- [ ] **Step 1: Write section 3**

Heading, exactly: `## Keep the data where the law lets it be`

The directive: personal data stays in the region the law permits, or reaches a destination covered by an adequacy decision or by standard contractual clauses. In engineering terms that is one rule with teeth: **pin the region explicitly in configuration, and fail startup when it is unset**, rather than accepting whatever a provider SDK defaults to. Name the second-order cases, because they are where residency is actually lost: a model provider that silently fails over to another region, a managed vector store whose region is chosen at creation and never revisited, a tracing backend in a different jurisdiction from the application it traces, and a support or debugging workflow that copies a payload to a laptop.

The reason: this is the handbook's own required-never-defaulted argument applied to a border. A default value silently points a forgotten configuration line at the wrong environment, and here the wrong environment is a jurisdiction. A defaulted region is how personal data crosses one with nobody deciding to.

Cite the mechanisms rather than gesturing at them: [adequacy decisions](https://commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection/adequacy-decisions_en) and [standard contractual clauses](https://commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection/standard-contractual-clauses-scc_en). Verify each URL resolves before committing; never fabricate one.

- [ ] **Step 2: Write section 4**

Heading, exactly: `## Minimize before the boundary`

The directive: the cheapest personal data to protect is the personal data you never sent. Redact, pseudonymize or truncate before the trust boundary, and prefer sending a reference over a payload wherever the task allows it. Give the concrete moves, since "minimize" alone is unactionable: strip direct identifiers the task does not need, replace them with stable pseudonyms where the agent has to refer to a person across turns, send the extract rather than the document where the extract answers the question, and put the redaction in the code path every call goes through rather than in each call site.

The tension the section must state rather than hide: redaction can make an agent measurably worse, and a team that assumes otherwise ships a quality regression under a privacy justification. The handbook's own answer is that this is measurable. Make redaction an eval dimension ([Part 7](evaluation.md)) and decide it against numbers, in either direction: keep the redaction if the metric holds, and if it does not, that is an argument to be had with evidence rather than a reason to quietly stop redacting.

- [ ] **Step 3: Add the two rows**

Append after the section 2 rows in `docs/audit/handbook-traceability.yaml`:

```yaml
- id: data-protection/keep-the-data-where-the-law-lets-it-be
  section: "Keep the data where the law lets it be"
  claim: Keep personal data in a permitted region or a destination covered by an adequacy decision or standard contractual clauses, and enforce it the way the handbook enforces any environment-selecting value - pin the region explicitly in configuration and fail startup when it is unset, rather than accepting a provider SDK's default, because a defaulted region is how data crosses a border with nobody deciding to.
  class: static
  severity: critical
  gap:
    recommendation: new-domain
    target: "#4"
    note: a region string and its absence are both readable from configuration, and no skill reads for one; ci-audit's `ci/permissions-secrets` is the nearest thing in the family and scopes to pipeline credentials rather than to where a request lands.

- id: data-protection/minimize-before-the-boundary
  section: "Minimize before the boundary"
  claim: Redact, pseudonymize or truncate personal data before it crosses the trust boundary and prefer a reference over a payload, putting the redaction in the shared call path rather than at each call site; and settle the quality cost as an eval dimension rather than assuming it in either direction.
  class: static
  severity: important
  gap:
    recommendation: new-domain
    target: "#4"
    note: eval-audit owns whether a behaviour is evaluated but has no dimension for redaction, and no skill reads the outbound call path for a minimization step; the whole claim needs the domain the target issue creates.
```

- [ ] **Step 4: Re-render and run every gate**

The five commands. Expected counters unchanged from Task 2.

- [ ] **Step 5: Commit**

Message: `docs: Part 10 on residency and minimizing before the boundary` - the body says that pinning the region is the required-never-defaulted rule applied to a jurisdiction, and that the redaction-versus-quality tension is stated because a team that assumes it away ships a regression under a privacy justification. `Refs #47`.

---

### Task 4: Retention, deletion, and the trail (sections 5, 6)

Section 6 is the one row in this part that maps an existing check. `security/sensitive-data`'s stated subject is "Secrets/PII written to logs or error messages", which reaches section 6's log clause and nothing else in it. The near-miss rule in the matrix header governs: map a check that only partly reaches a claim when it would *flag* the violation, refuse it when it would *pass* the violation. A personal-data leak into a log is flagged by that check, so the mapping stands and the residue is recorded as a gap on the same row. **The reciprocal edge lands in the same commit**: the record gains the anchor in its `handbook:` list, or the gate fails in both directions at once.

**Files:**
- Modify: `docs/engineering/data-protection.md` (append two `##` sections)
- Modify: `.agents/skills/security-audit/checks/sensitive-data.md` (one `handbook:` anchor)
- Modify: `docs/audit/handbook-traceability.yaml`, `docs/audit/handbook-traceability.md`

- [ ] **Step 1: Write section 5**

Heading, exactly: `## Retention and deletion are design decisions, not cleanup`

The directive: every store holding personal data gets a retention limit chosen deliberately and enforced by something (a TTL, a lifecycle rule, a scheduled job), and the deletion path is built as a feature before somebody asks for it. Then the part of the section that earns it: **deletion has to reach the derived copies**, and an agentic system generates more of them than any other kind. An embedding of a personal document is personal data. So is a cached model response, a run artifact, a stored trace, an eval dataset built from real user documents, a fixture somebody extracted from a real case, and a backup. A deletion that reaches the primary store and none of those is a deletion in name.

The reason: retention and deletion are the two obligations that cannot be retrofitted cheaply, because by the time they are asked for, the copies exist and nobody knows where. Deciding the limit when you create the store costs a line of configuration; discovering it afterwards costs an audit of every store you have.

Cross-link [Part 6](observability.md) for the run records and [Part 7](evaluation.md) for the datasets, naming the sections in prose rather than linking to an anchor, as every other part does.

- [ ] **Step 2: Write section 6**

Heading, exactly: `## Personal data does not belong in the trail`

The directive: logs, traces, error messages, run artifacts and eval fixtures are stores of personal data whenever the payload lands in them, and the payload does not need to be there. Log the identifier you can join back to the record, not the record. Keep the payload out of exception messages, which travel further than logs and end up in trackers a wider group can read. Build eval fixtures from synthetic or consented data, or from real data that has been through the same redaction the production path uses, and never from a copy of production nobody minimized.

The reason, and the section's real point: this is where the handbook's own "capture the trail" throughline collides with data protection, and the resolution is not to capture less. Capture the trail and redact the payload. A trail that identifies the run, the inputs' shapes, the tools called, the timings and the costs is the trail [Part 6](observability.md) asks for, and none of it needs the personal data in it.

Cross-link [Part 9](security-supply-chain.md), whose first-party-code lens already covers secrets and personal data reaching logs and error messages, and say what this section adds rather than restating it: the stored artifacts - traces, run records, eval fixtures - that a first-party-code lens does not read.

- [ ] **Step 3: Add the two rows, with section 6 mapping the existing check**

```yaml
- id: data-protection/retention-and-deletion-are-design-decisions-not-cleanup
  section: "Retention and deletion are design decisions, not cleanup"
  claim: Give every store holding personal data a deliberately chosen retention limit enforced by a TTL, a lifecycle rule or a scheduled job, and build the deletion path as a feature that reaches the derived copies an agentic system generates - embeddings, cached model responses, run artifacts, stored traces, eval datasets and fixtures built from real documents, and backups - because a deletion reaching only the primary store is a deletion in name.
  class: static
  severity: critical
  gap:
    recommendation: new-domain
    target: "#4"
    note: nothing in the family enumerates a project's stores or reads for a retention limit on one, and the derived-copy half needs the data-flow map the first row of this part asks for; this is the domain the target issue creates.

- id: data-protection/personal-data-does-not-belong-in-the-trail
  section: "Personal data does not belong in the trail"
  claim: Keep personal data out of logs, traces, error messages, run artifacts and eval fixtures - log the identifier you can join back rather than the record, keep payloads out of exception messages, and build fixtures from synthetic, consented or already-redacted data - because capture-the-trail and data protection are reconciled by redacting the payload, not by capturing less.
  class: static
  severity: critical
  checks:
    - security/sensitive-data
  gap:
    recommendation: new-domain
    target: "#4"
    note: "partial - `security/sensitive-data` reads logging and exception-handling call sites near PII-bearing variables, so it flags the log and error-message half of this claim rather than passing it, which is what the near-miss rule requires of a mapping. The residue is everything that is a stored artifact rather than a call site: traces and run records, eval datasets and the fixtures extracted from real documents. A first-party-code lens does not read them, so their status needs the domain the target issue creates."
```

- [ ] **Step 4: Add the reciprocal anchor to the check record**

In `.agents/skills/security-audit/checks/sensitive-data.md`, the `handbook:` list gains a third entry:

```yaml
handbook:
  - implementation-disciplines/coding-hygiene-rules-that-surface-at-review-a
  - observability/make-errors-diagnosable
  - data-protection/personal-data-does-not-belong-in-the-trail
```

Leave the body alone: the record's lead prose already names "Secrets/PII written to logs or error messages", which is exactly what the new anchor grounds, and its `## Tooling fallback` is unaffected.

- [ ] **Step 5: Re-render and run every gate**

The five commands. If the two edges were not added together, `render_handbook_traceability.py --check` fails with either `security/sensitive-data: handbook anchor ... has no matrix row citing this check` or `unknown check id`. Both mean the same thing: one direction of the edge is missing.

- [ ] **Step 6: Commit**

Message: `docs: Part 10 on retention, deletion, and keeping the trail clean` - the body says why deletion is judged on whether it reaches the derived copies, and why section 6 maps `security/sensitive-data` under the near-miss rule with the stored artifacts recorded as residue. `Refs #47`.

---

### Task 5: The standing check, the checklist, and the close (sections 7, 8, 9)

**Files:**
- Modify: `docs/engineering/data-protection.md` (append three `##` sections and the hand-off line)
- Modify: `docs/audit/handbook-traceability.yaml`, `docs/audit/handbook-traceability.md`

- [ ] **Step 1: Write section 7**

Heading, exactly: `## Verify against the real artifacts`

Part 9 has a section of the same name and this is its twin; write it so it says what *this* part's standing check reads, not a paraphrase of the other. It reads: the register against the outbound calls the code makes, the pinned regions against the providers configured, the retention limits against the stores that exist, and a scan of logs, fixtures and run artifacts for personal data. Run it report-only first, then fix one surface at a time in its own reviewed change, exactly as [Part 9](security-supply-chain.md) and [Part 1](lifecycle.md) ask of any audit.

The claim that distinguishes it: state which half no repository snapshot can settle - whether an agreement was signed, whether a provider honoured a deletion request, whether the retention window a provider publishes is the one it keeps - so a report separates "unverifiable from here" from "clean". Absence of evidence read as a pass is the specific failure this section exists to forbid, and it is the same rule the audit family applies to a check whose tooling could not run.

- [ ] **Step 2: Write the checklist**

Heading, exactly: `## Checklist: a data-protection sweep`

Group the items the way Part 9's checklist groups its own, one bolded group label per section of this part, with `- [ ]` items under each. Every item must be a thing a reader can tick against the repository, and every item must trace to a directive above it - the checklist is a recap, so it introduces nothing new. Keep it to roughly a dozen items, in the band Part 9's fifteen and Part 8's eight sit in.

End the section with the italic hand-off paragraph, which is what Part 9's closing line currently does and now hands to here:

```markdown
*And the loop begins again: the next idea becomes the next issue. First, a few [closing words](coda.md).*
```

- [ ] **Step 3: Write the See also**

Heading, exactly: `## See also`

Bulleted cross-links matching every other part's footer: [Part 6](observability.md) for the run records that are stores of personal data, [Part 7](evaluation.md) for datasets built from real inputs and for redaction as an eval dimension, [Part 9](security-supply-chain.md) for the first-party-code lens on secrets and PII in logs and for the provider-as-dependency rule this part's register extends, and the handbook index.

- [ ] **Step 4: Add the three rows**

```yaml
- id: data-protection/verify-against-the-real-artifacts
  section: "Verify against the real artifacts"
  claim: Run the verification counterpart of this part as a standing check - the register against the outbound calls the code makes, the pinned regions against the providers configured, the retention limits against the stores that exist, and a scan of logs, fixtures and run artifacts for personal data - report-only first, then one surface at a time, and separate what no repository snapshot can settle (whether an agreement was signed, whether a provider honoured a deletion) from a clean result.
  class: artifact
  severity: important
  gap:
    recommendation: new-domain
    target: "#4"
    note: the standing check this row describes is exactly the skill the target issue creates; audit-core already carries the report-only-then-fix cadence and the rule that absence of evidence is never a pass, and has no lens here to apply them through.

- id: data-protection/checklist-a-data-protection-sweep
  section: "Checklist: a data-protection sweep"
  claim: Recap of the part in one group per section - the data-flow map, the processor register and its agreement with the code, pinned regions, minimization before the boundary, retention limits and a deletion path reaching the derived copies, personal data out of the trail, and the standing check.
  class: process
  severity: critical
  note: A recap, so what it adds is the act of working the list during a sweep. It takes the maximum severity of what it recaps, per the legend's rule for a checklist row, which is the critical band four of this part's rows sit in; each item is owned by a row above.

- id: data-protection/see-also
  section: "See also"
  claim: Cross-links to Parts 6, 7 and 9 and the handbook index.
  class: informative
```

- [ ] **Step 5: Re-render and run every gate**

The five commands. Expected: `sections: 13`, `diagrams: 8`, `em-dashes: 0`, `residual .md hrefs: 1`, and `task items` risen from 83 by the number of checklist items written in Step 2. Read the part end to end once here, as one document, before committing: this is the first point at which it exists whole.

- [ ] **Step 6: Commit**

Message: `docs: close Part 10 with its standing check and checklist` - the body says the standing check separates unverifiable-from-here from clean, because absence of evidence read as a pass is the failure the section exists to forbid. `Refs #47`.

---

### Task 6: Part 9 gives up exactly what Part 10 took

Cross-link, don't duplicate. Part 9 keeps every claim that holds with no personal data anywhere, and points at Part 10 for the rest.

**Files:**
- Modify: `docs/engineering/security-supply-chain.md` (the GDPR clause, the checklist line, the closing hand-off, See also)
- Modify: `docs/audit/handbook-traceability.yaml` (retire one row, update two claims), `docs/audit/handbook-traceability.md`

- [ ] **Step 1: Shrink the GDPR clause**

In `docs/engineering/security-supply-chain.md`, the paragraph beginning `**Pin for reproducibility.**` ends with a sentence starting "Where you operate under a data-protection regime". Replace that sentence with a pointer at Part 10, keeping the retention-terms clause earlier in the paragraph intact - retention is a supply-chain fact about a provider and holds whether or not personal data is involved. The pointer should read as a hand-off, not as a summary: the whole legal-basis claim now lives in Part 10, and a reader who needs it should go there rather than get a compressed version here. Do not reflow the rest of the paragraph; it is one source line, and only the final sentence changes.

- [ ] **Step 2: Shrink the checklist line**

Line 88 of the same file reads:

```markdown
- [ ] Models/providers pinned and recorded; retention terms and (where applicable) **DPA/GDPR basis** confirmed.
```

Keep the pinning-and-retention half and replace the DPA half with a pointer at Part 10's checklist. Part 9's checklist stays a security and supply-chain sweep; the data-protection sweep is its own list now.

- [ ] **Step 3: Repoint the closing hand-off**

The italic line at the end of Part 9's checklist section currently reads:

```markdown
*And the loop begins again: the next idea becomes the next issue. First, a few [closing words](coda.md).*
```

Part 10 now carries that line (Task 5, Step 2). Part 9's becomes a hand-off to Part 10, naming it as the second standing obligation rather than as a next step in the story, since neither part is a station the change passes through.

- [ ] **Step 4: Add the See-also entry**

Part 9's See also gains a line for [Part 10. Data protection & privacy](data-protection.md), saying what it owns: the legal basis for every processor, residency, minimization, retention and deletion.

- [ ] **Step 5: Retire the matrix row**

Delete row `security-supply-chain/depend-only-on-what-you-can-account-for-c` from `docs/audit/handbook-traceability.yaml` entirely. Its claim moved to `data-protection/every-processor-needs-a-legal-basis-and-the-register-must-match-the-code-a` in Task 2, which carries its `target: "#4"`. This is safe without touching any check record: the row carries no `checks:` entry, and the edge-set validation only fires on a record naming a row that does not name it back. Rows `-a` and `-b` still cover the section, so no coverage hole opens.

- [ ] **Step 6: Update the two claims the prose edits falsify**

- `security-supply-chain/depend-only-on-what-you-can-account-for-b`: unchanged unless Step 1's rewrite moved wording out of the model-and-provider sentence. Read it against the edited paragraph and correct it if it drifted.
- `security-supply-chain/checklist-a-security--supply-chain-sweep`: its `claim` restates all fifteen checklist items, including "models and providers pinned and recorded with retention and DPA basis confirmed" in the dependencies group. Update that phrase to match the line as edited in Step 2.

- [ ] **Step 7: Re-render and run every gate**

The five commands. The row count drops by one relative to Task 5.

- [ ] **Step 8: Commit**

Message: `docs: Part 9 hands the legal-basis clause to Part 10` - the body says cross-link rather than duplicate, that Part 9 keeps the retention and pinning claims because they hold with no personal data anywhere, and that the retiring row's `target: "#4"` moved rather than disappeared. `Refs #47`.

---

### Task 7: Every part-count and hand-off assertion in the repo

Nine files assert either "nine parts", the part list, or a claim this change falsified. None of them is caught by any gate: nothing validates a matrix row's `claim` text against the prose it paraphrases, and nothing validates a hand-off sentence against the parts it leads into.

**Files:**
- Modify: `docs/engineering/README.md`, `docs/engineering/documentation.md`, `docs/engineering/troubleshooting.md`, `docs/engineering/observability.md`, `docs/engineering/evaluation.md`
- Modify: `CLAUDE.md`, `README.md` (repo root)
- Modify: `docs/audit/handbook-traceability.yaml`, `docs/audit/handbook-traceability.md`

- [ ] **Step 1: The README spine**

Four edits in `docs/engineering/README.md`:

1. "The story of a change", first paragraph: "the nine parts stop being a list of best practices" becomes ten.
2. The story's closing paragraph, which currently ends "keeping the machine safe, from your own code's trust boundaries to your dependency graph to the pipeline that builds you ([Part 9](security-supply-chain.md))". Extend it with the second standing obligation, in the same register: the data that passes through the system stays lawful for the people it belongs to ([Part 10](data-protection.md)). One sentence; the paragraph is one source line and only its end changes.
3. "The parts, at a glance" table: a row between the Part 9 row and the Troubleshooting row - `| **[10. Data protection & privacy](data-protection.md)** | The other standing obligation: what the system owes the people whose data passes through it. |`
4. "Where each throughline lives" table: a row `| 10 Data protection | | ● | | ○ |`. Capture-the-trail is the primary home, because the map and the register are exactly a decision and its evidence outliving the moment; executable standards is drawn on, via the standing check. Verify the column count against the header row as you write it.

Consider whether "Starting from zero" needs Part 10 in its list of what ships with the first commit. It does if the project will ever touch personal data, and the sentence naming the rules file, CI gates and security sweep is where it belongs. If you add it, check `README/starting-from-zero`'s matrix claim still matches.

- [ ] **Step 2: `README/the-story-of-a-change`'s matrix claim**

Its claim says "Narrates the life of a single change through the nine parts and marks its human gates." Update to ten. Check every other README row's claim against the prose you edited in Step 1 while you are there.

- [ ] **Step 3: Part 8's hand-off**

`docs/engineering/documentation.md`, the italic line after the checklist:

```markdown
*Next: the one obligation that stands over every change rather than following any single one. [Part 9. Security, dependencies & supply chain](security-supply-chain.md).*
```

"the one obligation" is now false. Rewrite it to hand off to the two standing obligations, naming both parts. Then read `documentation/checklist-shipping-documentation`'s claim: it recaps eight checklist items and does not quote the hand-off, so it should need no change - confirm rather than assume.

- [ ] **Step 4: The troubleshooting opening**

`docs/engineering/troubleshooting.md`, the opening italic: "The nine parts teach the disciplines in the order you would learn them." Update to ten. This line sits above the first `##`, so it belongs to no matrix row and nothing else needs to move.

- [ ] **Step 5: Two See-also footers**

`docs/engineering/observability.md` and `docs/engineering/evaluation.md` each gain a Part 10 line in their See also, saying what Part 10 wants from them: from Part 6, that the run records are a store of personal data and the payload does not belong in them; from Part 7, that a dataset built from real inputs is a store of personal data and that redaction's quality cost is an eval dimension. Check whether either part's `see-also` matrix row claim enumerates the parts it links to - Part 8's and Part 9's do - and update the claim if so.

- [ ] **Step 6: The two repo-level files**

- `CLAUDE.md`: "`docs/engineering/` — the handbook. Normative prose, nine parts." becomes ten. Note this file uses em-dashes and is outside the three trees that ban them; do not "fix" them.
- `README.md` (repo root): "normative directives covering the life of a change through nine parts" becomes ten.

- [ ] **Step 7: Re-render and run every gate**

The five commands, plus one grep that should now return nothing but false positives you can name:

```bash
grep -rn "nine parts\|nine-part" --include='*.md' --include='*.py' --include='*.yaml' . | grep -v '\.venv'
```

- [ ] **Step 8: Commit**

Message: `docs: the part count and the hand-offs that Part 10 falsified` - the body lists what was stale and says that no gate catches any of it, since nothing validates claim text against the prose it paraphrases. `Refs #47`.

---

### Task 8: Stale-prose sweep by an agent that has not seen the part

The repository's rule is to scope this pass by blast radius rather than by the diff, and to dispatch it to a subagent that has not seen the implementation. This is the task that catches what Task 7 enumerated from a list rather than from the tree.

**Files:** none directly; this task produces findings and then fixes them.

- [ ] **Step 1: Dispatch the sweep**

Dispatch one read-only agent. Resolve `git rev-parse --show-toplevel` in this session first and interpolate it as an absolute path; require the agent to confirm its own `--show-toplevel` matches before it reads anything. Brief it with: the repository has gained a tenth handbook part at `docs/engineering/data-protection.md`, Part 9 has given up its data-protection clause and its closing hand-off, and one matrix row has retired. Ask it to find prose anywhere in the repository that those three facts falsify **without touching**, searching for the part count, for enumerations of the handbook's parts, for hand-off and "see also" sentences naming Part 9 or the coda, for prose describing the retired row, and for anything describing what the audit family does or does not cover in this area. Ask for `file:line` and the falsifying reason on every finding, and tell it explicitly not to edit.

- [ ] **Step 2: Fix what it found**

Verify each finding against the file before acting on it - a stale-prose agent reports plausible-sounding claims like any other. Fix the real ones; for anything you decline, note the reason in the task's commit body.

- [ ] **Step 3: Run every gate and commit**

The five commands. Commit only if Step 2 changed anything; message `docs: fix the prose the tenth part left stale`, body naming what was found and what was declined. `Refs #47`.

---

### Task 9: Whole-branch verification

- [ ] **Step 1: Read Part 10 end to end, as a reader landing on it cold**

The question is whether it stands alone: does it locate itself in the story, does every directive say what to *do to the repository*, and does every reason earn its sentence. Check the voice against Part 9 read immediately before it - that comparison is what surfaces drift the individual tasks could not see.

- [ ] **Step 2: Check the part against #4's eight dimensions**

Provider DPAs, GDPR compliance, data residency, no-training and retention terms, sub-processor inventory, PII minimization at the boundary, retention and deletion, PII in logs and errors and traces and eval artifacts, and records of processing / a data-flow map. Name the section that grounds each. Anything left over is either a deliberate non-goal to state in the PR, or a gap to fix now.

- [ ] **Step 3: Run every gate one final time, from a clean tree**

```bash
git status --short
caffeinate uv run python scripts/render_handbook_traceability.py --check
caffeinate uv run python scripts/render_handbook_artifact.py
caffeinate uv run pytest tests/ -q
caffeinate uv run ruff check . && caffeinate uv run ruff format --check .
```

- [ ] **Step 4: Confirm the plugin still discovers every skill**

`claude plugin validate` passes on a plugin that discovers no skills, so it proves nothing on its own. Run `claude plugin details handbook-audit` and read the skill count: this branch edits one check record, and the count must be unchanged.

- [ ] **Step 5: Open the PR**

Draft PR with `Closes #47`, a Test plan checklist covering the gates above, and a note that the change is docs and matrix only apart from two hardcoded part lists in the render scripts. State that #4 is unblocked by it.

---

## Self-review

**Spec coverage.** Sections 1 to 8 of the spec's section list map to Tasks 2 to 5; "What Part 9 gives up" to Task 6; "The matrix rows" to the row blocks inside Tasks 2 to 5 and the retirement in Task 6; "Blast radius" row by row to Tasks 1, 6 and 7, with `coda.md` read in Task 8's sweep rather than assumed unchanged; "Voice and constraints" to the Global Constraints; "Verification" to Tasks 8 and 9.

**No placeholders.** Every matrix row is written out in full YAML. Every prose section carries its exact heading, the claims it must make, the reasons that earn them, and the cross-links it owes. The prose itself is written in the task rather than pasted from the plan, deliberately: drafting 1600 words twice invites the second copy to drift from the first, and the constraint that actually governs handbook prose is the voice, which a brief can specify and a draft cannot enforce.

**Consistency.** Every row id in Tasks 2 to 5 is the `slugify` of the heading given in the same step (lowercase, non-`[a-z0-9 _-]` dropped, spaces to hyphens); the two split rows carry the `-a`/`-b` suffix `_SPLIT_SUFFIX_RE` strips. The H1 uses `Part 10.` and `PART_TITLES` uses `Part 10:`, which is the existing convention and is compared numerically by `validate_parts`.
