# Traceability matrix severity axis — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `severity` axis to the handbook traceability matrix, assign it to all 108 assessable rows, render the severity × coverage cross-tab that turns the gap list into a risk-ordered work queue, and delete the one confirmed Minor-and-contingent handbook clause into a new advisory sidecar.

**Architecture:** `severity` is a new scalar field on the YAML row, orthogonal to the existing `class`. `class` answers *can we check it*; `severity` answers *how bad if it is violated*. The sweep lands first, in five per-part batches, and only then does the renderer learn about the field — see Task ordering below for why that keeps every commit green. The renderer gains a Severity column, a gap list grouped by severity instead of by recommendation, and a severity × mapped-status cross-tab. Validation makes the field required on `static`/`artifact`/`process` rows and forbidden on `informative` ones.

**Tech Stack:** Python 3.11+, PyYAML, pytest, ruff, pyright. No new dependencies.

## Task ordering — why the sweep comes before the schema

`validate()` ignores unknown keys and `render()` emits only the fields it knows, so adding `severity:` to YAML rows is invisible to both until the renderer changes. That means the five sweep tasks can land one at a time with `pytest`, `--check` and every docs gate staying green, and the schema change in Task 6 arrives when all 108 rows already satisfy it.

The reverse order would need the field to be optional-then-required, or would redden CI on every intermediate commit. #549's review removed exactly that kind of staged scaffolding (`--allow-pending-parts`) under the repo's no-stubs rule; this ordering avoids needing it at all.

## Global Constraints

These bind every task. Copied from #552 and the repo's conventions.

**The scale is audit-core's, not a new one.** `critical` | `important` | `minor`, lowercase in YAML. audit-core's loop already hard-codes those three (step 4.3: "fix Critical/Important before advancing; apply easy correct Minor fixes"), so any other vocabulary needs a translation layer at every seam where a clause becomes a finding.

**Severity is the risk carried by violating the clause:**

| Severity | Violating it means | Test |
|---|---|---|
| `critical` | Exposure that is hard to undo or reaches beyond the team: credentials or personal data leaked, licence/legal exposure, data loss, wrong output shipped to users unnoticed | Could this appear in an incident report or a legal review? |
| `important` | You can still ship, but you can no longer tell whether what you shipped is right: silent incorrectness, unreproducible results, undiagnosable production failure, unbounded cost | Does ignoring it destroy your ability to know the system works? |
| `minor` | Comfort, tidiness, or local velocity, with no effect on correctness, safety, or measurability | Is the worst case "mildly annoying" or "harder to read"? |

**Severity is a baseline, not a verdict.** Record the severity a violation *inherently* carries, independent of this repo's current state. An auditor may raise or lower it for a specific instance with a stated reason. Do not lower a clause's severity because this repo already complies with it.

**Severity is orthogonal to `class`.** Do not let "we cannot check it from a snapshot" pull a severity down. `process` rows carry a severity precisely because the adoption roadmap in an external audit (#542) needs to know what to sequence first.

**Only `informative` rows carry no severity.** Every `static`, `artifact` and `process` row carries exactly one.

**Never change any other field.** The sweep tasks add one line per row. Do not reword a `claim`, retitle a `section`, edit a `note`, or touch `checks`/`gap`. If a row looks wrong, say so in the report; do not fix it.

**Field placement.** `severity:` goes on the line immediately after `class:`, at the same indentation, so the two axes read together.

**Calibration anchors.** These nine rows are pre-assigned and must not be changed. Calibrate every judgment against them; a row you would rate above `security-supply-chain/turn-every-fix-into-a-gate` had better be genuinely worse than an unenforced security gate.

| Row id | Severity | Why |
|---|---|---|
| `security-supply-chain/secrets-never-commit-them-and-rotate-dont-just-delete-a` | `critical` | A committed credential is the archetype: outside exposure, hard to undo. |
| `security-supply-chain/grant-the-agent-the-least-privilege-it-needs` | `critical` | The lethal trifecta in one agent is an exfiltration path, not a tidiness issue. |
| `security-supply-chain/depend-only-on-what-you-can-account-for-c` | `critical` | Personal data at a provider with no legal basis is a regulatory exposure. |
| `security-supply-chain/turn-every-fix-into-a-gate` | `important` | The fixes themselves are Critical; not encoding them as gates means the class recurs — serious, but one step removed from the exposure. |
| `observability/make-errors-diagnosable` | `important` | A swallowed exception destroys your ability to know what the system did. |
| `security-supply-chain/depend-only-on-what-you-can-account-for-b` | `important` | An unpinned model moves eval numbers out from under you: measurability, not exposure. |
| `implementation-disciplines/coding-hygiene-rules-that-surface-at-review-d` | `minor` | Field descriptions and current module docstrings are readability. |
| `implementation-disciplines/ci-and-static-analysis-d` | `minor` | Spending an agent on what a linter enforces wastes money and time; nothing ships wrong. |
| `implementation-disciplines/prompt-and-sop-engineering-b` | `minor` | A commit message that omits *why* a prompt changed costs a future reader some archaeology. |

**Rating a row whose claim bundles several clauses: max over owned clauses.** Rate a row at the highest severity among the clauses the row is the matrix's citation unit for, and name that clause in the report. Never average, never take the modal clause, and never discount a severe clause because the row also bundles hygiene. Two qualifiers:

1. *A clause another row owns does not raise this row; it raises that one.* A cross-reference ("the bookend gates never scale off") scopes this row's own rule and is not ownership.
2. *A pure recap row owns nothing of its own and takes the max of everything it recaps* — because violating "work the list" is violating every item on it. Checklist rows are the case this covers.
3. *A second imperative statement of the same rule is ownership, not a cross-reference.* Where the handbook states one rule in two sections and the matrix records both as citation units, both rows own it and both take the same severity. Qualifier 1 covers a mention that scopes this row's own rule; it does not cover the handbook asserting the same imperative twice. (The docstring rule is stated three times, the reach-in rule twice.)

Max rather than mean because severity is a baseline an auditor may lower with a stated reason, which makes the two errors asymmetric: over-rating surfaces a row in a band where a reader sees it and can lower it, while under-rating buries a high-risk clause where the severity × coverage cross-tab will never surface it. When the deliverable is a risk-ordered work queue, the safe direction is up. The ownership qualifier is what stops bare max from filling the Critical bucket with rows that add no new risk surface, which would destroy the discriminating power the axis exists to provide. (Settled in the Task 1 review; batch A is the worked precedent.)

**"Unbounded cost" in the Important band means one run or process that can run away with no ceiling** — an agent with no completion criterion, an unmetered budget, a retry loop with no cap. It does not mean an engineering tax that recurs. Bounded, visible, billable waste is `minor`; cost you cannot see the end of inside a single execution is `important`. (Settled in the Task 1 review, reaffirmed in Task 2's.)

**Structural clauses.** Rate a clause `minor` when its violation only makes future change more expensive — coupling, cycles, tier drift, duplicated plumbing, a blast radius that is harder to enumerate, a test that needs more scaffolding to run — however much that expense compounds. The Minor band's qualifier is not "small", it is "no effect on correctness, safety, or measurability", and erosion clears that bar: the code runs identically, the suite still bites, no number moves. A structural clause rises to `important` only when the violation makes a **behavioural change invisible to a party that depends on it**. Three shapes qualify:

1. a convenience migrated into shared code, so a second consumer is silently bound to the first workflow's assumptions;
2. one application reaching into another's internals, so a change inside B moves A with nothing in B's diff showing it;
3. a live path removed because the static signal lied — the case the handbook guards with "verify true unreachability before deleting".

Note that a coupled test is not a false-passing test: a test that transitively drags in a higher tier still fails when the code breaks, and the Important band's false-pass family is defined by the check being *incapable* of failing. (Settled in the Task 2 review; Part 4's layer boundaries and Part 5's harness composition are the same shape of clause.)

**Gates and sole detectors.** A gate clause is `critical` only when the harm it is the sole detector for is *itself* Critical — external, irreversible. When a gate is the sole detector for an Important-grade harm, the gate is `important`, and "other barriers still stand between the change and users" is not available as a reason, because by definition none do. Rate on the harm's own band instead. (Settled in the Task 2 review; Part 7 is full of this shape.)

**The knowability test, before writing `important`.** Name the specific thing you can no longer tell after the violation. If the only honest answer is "it costs more, takes longer, or reads worse", it is `minor`. `important` is the largest band and the easiest default; this is the check that keeps it from becoming one.

**Two calibration traps.**

- *Do not inherit severity from the part's subject.* Part 9 is the security part, but not every clause in it is Critical — `verify-against-the-real-artifacts` is about running the sweep, which is Important. Part 2 is the disciplines part, but `tdd-b` (ship tests, do not lower coverage) is Important, not Minor: without it you cannot tell whether the code works.
- *Do not inherit severity from effort.* A clause that is expensive to comply with is not thereby Critical, and a one-line clause is not thereby Minor.

**Deletion candidates.** A clause that is **`minor` *and* contingent on one execution environment** is a deletion candidate — it does not belong in a handbook whose value is that everything in it is normative and universal. Contingent means: a different but legitimate setup (a cloud harness, a different OS, another agent runtime) makes the clause meaningless rather than merely differently-implemented. Record candidates; never delete anything during a sweep task.

**Repo conventions.** Markdown source is never hard-wrapped — one paragraph is one line. No em-dashes anywhere under `docs/engineering/`. Never commit environment-specific values (personal paths, profile names, hostnames). New code ships with tests. Run `uv run ruff check .`, `uv run ruff format --check .` and `uv run pyright` before every commit. Reference the issue as `Refs #552` in commit messages.

## File structure

| File | Change |
|---|---|
| `docs/audit/handbook-traceability.yaml` | One `severity:` line added to each of 108 rows; header comment documents the field |
| `scripts/render_handbook_traceability.py` | `SEVERITIES` constant, three validation rules, Severity column, severity-grouped gap list, cross-tab, legend |
| `tests/scripts/test_render_handbook_traceability.py` | Tests for the three validation rules and the three rendering changes |
| `docs/audit/handbook-traceability.md` | Regenerated (never hand-edited) |
| `docs/engineering/lifecycle.md` | Keep-awake sentence removed from the Part 1 blockquote |
| `docs/engineering-notes.md` | New: the advisory sidecar |
| `docs/engineering/README.md` | Link to the sidecar |
| `docs/README.md` | Index entry for the sidecar |

---

### Task 1: Sweep batch A — README spine and Part 1 (lifecycle)

21 rows: 5 `README/*`, 16 `lifecycle/*`.

**Files:**
- Modify: `docs/audit/handbook-traceability.yaml` (rows with ids starting `README/` and `lifecycle/`)

**Interfaces:**
- Consumes: nothing.
- Produces: the field placement and reasoning style every later batch follows.

- [ ] **Step 1: Read the ground truth**

Read `docs/engineering/README.md` and `docs/engineering/lifecycle.md` in full, then the `README/*` and `lifecycle/*` rows of `docs/audit/handbook-traceability.yaml`. Judge each clause from what the handbook actually says, not from the row's one-line `claim` paraphrase alone.

- [ ] **Step 2: Assign a severity to every non-informative row in the batch**

For each row whose `class` is `static`, `artifact` or `process`, insert one line immediately after `class:`:

```yaml
  class: static
  severity: important
```

Leave every `informative` row untouched — no `severity` key at all.

Apply the scale, the two calibration traps and the nine anchors from Global Constraints. Work row by row; do not batch-guess by part.

- [ ] **Step 3: Verify nothing but severity changed**

```bash
git diff --unified=0 docs/audit/handbook-traceability.yaml | grep '^[-+]' | grep -v '^[-+][-+]' | sort | uniq -c
```

Expected: every changed line is an addition (`+`) and every one of them matches `+  severity: (critical|important|minor)`. Any `-` line means a field was disturbed — revert it.

- [ ] **Step 4: Verify the matrix still validates and renders unchanged**

```bash
uv run python scripts/render_handbook_traceability.py --check
```

Expected: exit 0. The renderer does not know about `severity` yet, so the committed Markdown must be byte-identical. A failure here means something other than severity moved.

- [ ] **Step 5: Report the batch**

In the report file, under a heading `## Severity assignments`, list every row as `id — severity — one clause of justification`. Under `## Deletion candidates`, list any row that is `minor` *and* contingent on one execution environment, with the environment named and why a different setup makes it meaningless. Write "none" if there are none. Under `## Doubts`, list any row where two severities were genuinely arguable, with the reasoning, so the reviewer can check calibration rather than re-derive it.

- [ ] **Step 6: Commit**

```bash
git add docs/audit/handbook-traceability.yaml
git commit -m "docs(#552): assign severity to the README spine and Part 1 rows

Refs #552"
```

---

### Task 2: Sweep batch B — Parts 2 and 3

29 rows: 17 `implementation-disciplines/*`, 12 `codebase-structure/*`.

**Files:**
- Modify: `docs/audit/handbook-traceability.yaml` (rows with ids starting `implementation-disciplines/` and `codebase-structure/`)

**Interfaces:**
- Consumes: the field placement from Task 1.
- Produces: nothing later tasks depend on structurally.

Three of the nine calibration anchors live in this batch (`implementation-disciplines/coding-hygiene-rules-that-surface-at-review-d`, `implementation-disciplines/ci-and-static-analysis-d`, `implementation-disciplines/prompt-and-sop-engineering-b`). Use the severities Global Constraints already fixes for them; do not re-derive them.

- [ ] **Step 1: Read the ground truth**

Read `docs/engineering/implementation-disciplines.md` and `docs/engineering/codebase-structure.md` in full, then the matching rows.

- [ ] **Step 2: Assign a severity to every non-informative row in the batch**

Same format and rules as Task 1 Step 2.

Note for this batch: `implementation-disciplines/tdd-b` is `important` — shipping untested code does not leak anything, but it destroys your ability to know the code works. Layering and dependency-direction clauses in Part 3 are about long-run maintainability rather than correctness or exposure; weigh whether a violation makes the system *wrong* or merely *harder*, and rate accordingly.

- [ ] **Step 3: Verify nothing but severity changed**

```bash
git diff --unified=0 docs/audit/handbook-traceability.yaml | grep '^[-+]' | grep -v '^[-+][-+]' | sort | uniq -c
```

Expected: additions only, all matching `+  severity: (critical|important|minor)`.

- [ ] **Step 4: Verify the matrix still validates and renders unchanged**

```bash
uv run python scripts/render_handbook_traceability.py --check
```

Expected: exit 0.

- [ ] **Step 5: Report the batch**

Same three headings as Task 1 Step 5: `## Severity assignments`, `## Deletion candidates`, `## Doubts`.

- [ ] **Step 6: Commit**

```bash
git add docs/audit/handbook-traceability.yaml
git commit -m "docs(#552): assign severity to the Part 2 and Part 3 rows

Refs #552"
```

---

### Task 3: Sweep batch C — Parts 4, 5 and 6

26 rows: 9 `three-layer-model/*`, 9 `agent-harness/*`, 8 `observability/*`.

**Files:**
- Modify: `docs/audit/handbook-traceability.yaml` (rows with ids starting `three-layer-model/`, `agent-harness/`, `observability/`)

**Interfaces:**
- Consumes: the field placement from Task 1.
- Produces: nothing later tasks depend on structurally.

One calibration anchor lives here (`observability/make-errors-diagnosable` = `important`); use it as given.

- [ ] **Step 1: Read the ground truth**

Read `docs/engineering/three-layer-model.md`, `docs/engineering/agent-harness.md` and `docs/engineering/observability.md` in full, then the matching rows.

- [ ] **Step 2: Assign a severity to every non-informative row in the batch**

Same format and rules as Task 1 Step 2.

Notes for this batch: Part 6 is the observability part, and most of it is `important` by construction — instrumentation clauses are about *being able to tell* what happened, which is the Important test almost verbatim. Resist flattening the whole part to one value: `keep-observability-out-of-the-models-context` is about what reaches the model's context and can change the output, which is a different kind of harm from a missing usage record. In Part 5, bounding an external call (timeouts, retries, caps) is unbounded-cost and hang territory — Important — while a clause about which alias names a model is closer to reproducibility.

- [ ] **Step 3: Verify nothing but severity changed**

```bash
git diff --unified=0 docs/audit/handbook-traceability.yaml | grep '^[-+]' | grep -v '^[-+][-+]' | sort | uniq -c
```

Expected: additions only, all matching `+  severity: (critical|important|minor)`.

- [ ] **Step 4: Verify the matrix still validates and renders unchanged**

```bash
uv run python scripts/render_handbook_traceability.py --check
```

Expected: exit 0.

- [ ] **Step 5: Report the batch**

Same three headings as Task 1 Step 5.

- [ ] **Step 6: Commit**

```bash
git add docs/audit/handbook-traceability.yaml
git commit -m "docs(#552): assign severity to the Part 4, 5 and 6 rows

Refs #552"
```

---

### Task 4: Sweep batch D — Parts 7 and 8

31 rows: 17 `evaluation/*`, 14 `documentation/*`.

**Files:**
- Modify: `docs/audit/handbook-traceability.yaml` (rows with ids starting `evaluation/` and `documentation/`)

**Interfaces:**
- Consumes: the field placement from Task 1.
- Produces: nothing later tasks depend on structurally.

- [ ] **Step 1: Read the ground truth**

Read `docs/engineering/evaluation.md` and `docs/engineering/documentation.md` in full, then the matching rows.

- [ ] **Step 2: Assign a severity to every non-informative row in the batch**

Same format and rules as Task 1 Step 2.

Notes for this batch: evaluation clauses divide sharply. A clause about *trusting a number that is wrong* (contaminated test set, judge never validated against human labels, a metric that does not measure the thing) is Important at least, because the whole point of the harness is knowing whether the system works — and where a bad number would ship a wrong answer to users unnoticed, weigh Critical against the Critical test rather than assuming evaluation caps at Important. A clause about how results are filed or named is Minor. In Part 8, `aim-for-docs-that-stand-alone…-a` argues a drifted doc is worse than none because it launders a stale belief; rate the drift clause on that harm, not on the tidiness of the fix.

- [ ] **Step 3: Verify nothing but severity changed**

```bash
git diff --unified=0 docs/audit/handbook-traceability.yaml | grep '^[-+]' | grep -v '^[-+][-+]' | sort | uniq -c
```

Expected: additions only, all matching `+  severity: (critical|important|minor)`.

- [ ] **Step 4: Verify the matrix still validates and renders unchanged**

```bash
uv run python scripts/render_handbook_traceability.py --check
```

Expected: exit 0.

- [ ] **Step 5: Report the batch**

Same three headings as Task 1 Step 5.

- [ ] **Step 6: Commit**

```bash
git add docs/audit/handbook-traceability.yaml
git commit -m "docs(#552): assign severity to the Part 7 and Part 8 rows

Refs #552"
```

---

### Task 5: Sweep batch E — Part 9, troubleshooting and coda

17 rows: 12 `security-supply-chain/*`, 4 `troubleshooting/*`, 1 `coda/*`. The troubleshooting and coda rows are all `informative` and get nothing; the real work is Part 9.

**Files:**
- Modify: `docs/audit/handbook-traceability.yaml` (rows with ids starting `security-supply-chain/`, `troubleshooting/`, `coda/`)

**Interfaces:**
- Consumes: the field placement from Task 1.
- Produces: the completed sweep — after this task every `static`/`artifact`/`process` row carries a severity, which Task 6's validation requires.

Five of the nine calibration anchors live in this batch (`secrets-…-a`, `grant-the-agent-the-least-privilege-it-needs`, `depend-only-on-what-you-can-account-for-b` and `-c`, `turn-every-fix-into-a-gate`). Use the severities Global Constraints fixes for them; do not re-derive them.

- [ ] **Step 1: Read the ground truth**

Read `docs/engineering/security-supply-chain.md`, `docs/engineering/troubleshooting.md` and `docs/engineering/coda.md` in full, then the matching rows.

- [ ] **Step 2: Assign a severity to every non-informative row in the batch**

Same format and rules as Task 1 Step 2.

Note for this batch: the trap named in Global Constraints bites hardest here. Part 9 is the security part, so the pull is to rate all twelve rows Critical. Apply the test per clause: `secrets-…-b` (rotate, do not merely delete) is Critical because an unrotated pushed credential is still live; `verify-against-the-real-artifacts` is about running the sweep at all, which is Important; the fifteen-item checklist row inherits from the clauses it recaps, so rate it at the highest severity it recaps and say so in the report.

- [ ] **Step 3: Verify the whole sweep is complete**

```bash
uv run python -c "
import yaml
rows = yaml.safe_load(open('docs/audit/handbook-traceability.yaml'))
missing = [r['id'] for r in rows if r['class'] != 'informative' and 'severity' not in r]
extra = [r['id'] for r in rows if r['class'] == 'informative' and 'severity' in r]
bad = [(r['id'], r.get('severity')) for r in rows if 'severity' in r and r['severity'] not in ('critical', 'important', 'minor')]
print('missing:', missing or 'none')
print('informative with severity:', extra or 'none')
print('bad values:', bad or 'none')
from collections import Counter
print(Counter(r.get('severity') for r in rows))
"
```

Expected: `missing: none`, `informative with severity: none`, `bad values: none`, and a Counter whose `None` count is exactly 16 (the informative rows) summing to 124.

- [ ] **Step 4: Verify the matrix still validates and renders unchanged**

```bash
uv run python scripts/render_handbook_traceability.py --check
```

Expected: exit 0.

- [ ] **Step 5: Report the batch and the distribution**

The three headings from Task 1 Step 5, plus `## Distribution`: the Counter output from Step 3, with one paragraph on whether the shape looks right — a matrix where 80% of rows are Critical has a calibration problem, and so does one with three.

- [ ] **Step 6: Commit**

```bash
git add docs/audit/handbook-traceability.yaml
git commit -m "docs(#552): assign severity to the Part 9, troubleshooting and coda rows

Refs #552"
```

---

### Task 6: Schema validation and rendering

**Files:**
- Modify: `scripts/render_handbook_traceability.py`
- Modify: `tests/scripts/test_render_handbook_traceability.py`
- Modify: `docs/audit/handbook-traceability.yaml` (header comment only)
- Regenerate: `docs/audit/handbook-traceability.md`

**Interfaces:**
- Consumes: every assessable row carries `severity`, from Tasks 1-5.
- Produces: `SEVERITIES`, `SEVERITY_LABELS` and `ASSESSABLE` module constants; the rendered Severity column, severity-grouped gap list and cross-tab.

**Six existing tests break on this change.** That is expected and their updates are specified below — do not work around a breakage by softening the new behaviour. The file drives everything off one `_valid_rows()` fixture and a table-driven `test_validate_catches_each_rule` that asserts an exact error count per case, so the fixture must gain severities before anything else passes.

- [ ] **Step 1: Give the shared fixture its severities**

In `tests/scripts/test_render_handbook_traceability.py`, add one `"severity"` key to each of the first three rows of `_valid_rows()` and none to the fourth. These specific values are load-bearing: they put the two gap-carrying rows in different severity groups (so ordering is testable) and exercise all three levels across the cross-tab.

```python
            "class": "static",
            "severity": "important",
```
```python
            "class": "artifact",
            "severity": "critical",
```
```python
            "class": "process",
            "severity": "minor",
```

The `coda/coda` row is `informative` and stays as it is.

- [ ] **Step 2: Add the failing validation cases**

Append four cases to the `cases` list in `test_validate_catches_each_rule`, matching the existing `(mutation, message fragment, expected total error count)` shape:

```python
        (lambda r: r[0].pop("severity"), "needs severity one of", 1),
        (lambda r: r[2].update(severity="blocker"), "needs severity one of", 1),
        (
            lambda r: r[3].update(severity="minor"),
            "informative rows carry no severity",
            1,
        ),
        (
            lambda r: r[3].update(gap={"recommendation": "extend-skill", "note": "x"}),
            "informative row must not carry a gap",
            1,
        ),
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/scripts/test_render_handbook_traceability.py -v`
Expected: `test_validate_catches_each_rule` FAILS on the four new cases (no severity validation exists yet). `test_validate_accepts_the_valid_fixture` still passes — `validate` ignores the unknown key until Step 4 adds the rules.

- [ ] **Step 4: Add the constants and the validation rules**

In `scripts/render_handbook_traceability.py`, after the existing `CLASSES` / `RECOMMENDATIONS` constants:

```python
SEVERITIES = ("critical", "important", "minor")
SEVERITY_LABELS = {"critical": "Critical", "important": "Important", "minor": "Minor"}
# Classes that make a normative claim, so a violation carries a risk worth rating.
ASSESSABLE = ("static", "artifact", "process")
```

In `validate()`, immediately after the existing `class` check (`if cls not in CLASSES: ...`):

```python
        sev = row.get("severity")
        if cls in ASSESSABLE and sev not in SEVERITIES:
            errors.append(
                f"{rid}: {cls} row needs severity one of {SEVERITIES}, got {sev!r}"
            )
        if cls == "informative" and sev is not None:
            errors.append(
                f"{rid}: informative rows carry no severity (got {sev!r}); "
                "severity is the risk of violating a normative claim, and an "
                "informative row makes none"
            )
```

And after the existing `gap` type check, so a gap can never land outside the severity-grouped gap list:

```python
        if cls == "informative" and gap:
            errors.append(
                f"{rid}: informative row must not carry a gap; the rendered gap "
                "list groups by severity, which an informative row has none of"
            )
```

- [ ] **Step 5: Run the tests to verify the validation rules pass**

Run: `uv run pytest tests/scripts/test_render_handbook_traceability.py -k validate -v`
Expected: every `validate` test PASSES, including the four new cases and `test_validate_accepts_the_valid_fixture`.

- [ ] **Step 6: Write the failing rendering tests**

Add four tests, all driven off the shared fixture like their neighbours:

```python
def test_render_emits_a_severity_column():
    out = rht.render(_valid_rows())
    assert "| Section / claim | Class | Severity | Mapped checks | Gap | Notes |" in out
    assert "| static | Important |" in out
    assert "| artifact | Critical |" in out
    # The informative row carries no severity and renders a placeholder.
    assert "| informative | - |" in out


def test_render_groups_the_gap_list_by_severity_worst_first():
    rows = _valid_rows()
    # A second gap, one level down, so the ordering is observable.
    rows[0]["gap"] = {"recommendation": "extend-skill", "note": "residue"}
    out = rht.render(rows)
    assert out.index("### Critical") < out.index("### Important")
    # The Critical row's bullet precedes the Important heading.
    assert out.index("`alpha/split-section-a`") < out.index("### Important")
    # Grouping is by severity now, not by recommendation.
    assert "### new-domain" not in out
    assert "### extend-skill" not in out


def test_render_cross_tabs_severity_against_mapped_status():
    out = rht.render(_valid_rows())
    assert "### Severity x coverage" in out
    # Critical: the artifact row, gapped and unmapped. Important: the static
    # row, fully mapped. Minor: the process row, auditable of neither kind.
    assert "| Critical | 0 | 0 | 1 | 1 | 0 |" in out
    assert "| Important | 1 | 0 | 0 | 1 | 0 |" in out
    assert "| Minor | 0 | 0 | 0 | 0 | 1 |" in out


def test_render_states_both_interpretation_rules_in_the_legend():
    out = rht.render(_valid_rows())
    assert "**Baseline, not verdict.**" in out
    assert "Only `informative` rows have none." in out
```

- [ ] **Step 7: Run the tests to verify they fail**

Run: `uv run pytest tests/scripts/test_render_handbook_traceability.py -v`
Expected: the four new rendering tests FAIL.

- [ ] **Step 8: Add the Severity column**

Add the cell helper next to the other `_*_cell` functions:

```python
def _severity_cell(row: dict[str, Any]) -> str:
    """Title-cased severity, or `-` for the informative rows that carry none."""
    return SEVERITY_LABELS.get(row.get("severity", ""), "-")
```

In `render()`, replace the per-part table header and row emission with:

```python
        out.append("| Section / claim | Class | Severity | Mapped checks | Gap | Notes |")
        out.append("|---|---|---|---|---|---|")
        for row in by_part[part]:
            out.append(
                f"| {_section_cell(row)} | {row['class']} | {_severity_cell(row)} "
                f"| {_checks_cell(row)} | {_gap_cell(row)} | {_note_cell(row)} |"
            )
```

- [ ] **Step 9: Regroup the gap list by severity**

Replace the gap-list block in `render()` (from `gaps = [...]` down to the end of the `for rec in RECOMMENDATIONS:` loop) with:

```python
    gaps = [r for r in rows if r.get("gap")]
    out.append("\n## Gap list\n")
    if not gaps:
        out.append("No gaps: every auditable row is mapped.")
    else:
        out.append(
            "Ordered by severity - the risk a violation carries - then by handbook "
            "order. Each entry names its recommendation (`extend-skill` / "
            "`new-domain` / `report-only`) and, where one exists, the issue that "
            "would close it."
        )
    for sev in SEVERITIES:
        group = [r for r in gaps if r.get("severity") == sev]
        if not group:
            continue
        out.append(f"\n### {SEVERITY_LABELS[sev]}\n")
        for r in group:
            url, marker = handbook_link(r)
            gap = r["gap"]
            # Bullets, not cells: a pipe is harmless here, a newline is not.
            bits = [f"**{gap['recommendation']}**"]
            if gap.get("target"):
                bits.append(_oneline(gap["target"]))
            if gap.get("note"):
                bits.append(_oneline(gap["note"]))
            out.append(f"- [`{r['id']}`]({url}){marker} - " + " - ".join(bits))
```

Validation guarantees every gap row is `static` or `artifact` and so carries a severity, which is what makes these three groups exhaustive — the `informative`-no-gap rule added in Step 3 is what closes the one hole that would silently drop a row from this list.

- [ ] **Step 10: Add the cross-tab to the coverage summary**

In `render()`, after the existing per-class count table and before the closing prose paragraph:

```python
    out.append("\n### Severity x coverage\n")
    out.append(
        "The actionable question: which high-risk clauses does nothing check? "
        "Auditable rows only in the first four columns; the process column counts "
        "rows that carry a severity but can never be checked from a snapshot, and "
        "so belong in report prose and an adoption roadmap."
    )
    out.append("")
    out.append("| Severity | Fully mapped | Partial | Unmapped | Auditable total | Process |")
    out.append("|---|---|---|---|---|---|")
    for sev in SEVERITIES:
        aud = [r for r in auditable if r.get("severity") == sev]
        n_full = sum(1 for r in aud if r.get("checks") and not r.get("gap"))
        n_partial = sum(1 for r in aud if r.get("checks") and r.get("gap"))
        n_proc = sum(
            1 for r in rows if r["class"] == "process" and r.get("severity") == sev
        )
        out.append(
            f"| {SEVERITY_LABELS[sev]} | {n_full} | {n_partial} "
            f"| {len(aud) - n_full - n_partial} | {len(aud)} | {n_proc} |"
        )
```

- [ ] **Step 11: Add the severity legend and the two interpretation rules**

In `_HEADER`, immediately after the existing Class table, insert:

```markdown
| Severity | Violating the clause means | Test |
|---|---|---|
| `critical` | Exposure that is hard to undo or reaches beyond the team: credentials or personal data leaked, licence or legal exposure, data loss, wrong output shipped to users unnoticed. | Could this appear in an incident report or a legal review? |
| `important` | You can still ship, but you can no longer tell whether what you shipped is right: silent incorrectness, unreproducible results, undiagnosable production failure, unbounded cost. | Does ignoring it destroy your ability to know the system works? |
| `minor` | Comfort, tidiness, or local velocity, with no effect on correctness, safety, or measurability. | Is the worst case "mildly annoying" or "harder to read"? |

Severity is orthogonal to class: class is *can we check it*, severity is *how bad if it is violated*. The scale is audit-core's own Critical / Important / Minor, so a matrix row and an audit finding speak the same language. Two rules govern how to read the column:

**Baseline, not verdict.** A row records the severity a violation *inherently* carries, independent of any repo's current state. An auditor may raise or lower it for a specific instance with a stated reason - a load-bearing production prompt and a throwaway eval prompt violate the same clause at different cost.

**`process` rows carry a severity too.** "Spec before code" cannot be checked from a snapshot but is not thereby harmless, and an adoption roadmap needs to know what to sequence first. Only `informative` rows have none.
```

- [ ] **Step 12: Update the four existing render tests the new output breaks**

These assert on the old table header and the old recommendation-grouped bullet format. Each is a real expectation that has legitimately changed — update the expected string, never the renderer.

`test_render_produces_tables_gap_list_and_summary` — the gap list no longer has a recommendation heading:

```python
    assert "### Critical" in out and "#516" in out
```
replacing the `assert "### new-domain" in out and "#516" in out` line.

`test_render_marks_split_rows_and_links_gap_entries` — the bullet now leads with the recommendation:

```python
    assert (
        f"- [`alpha/split-section-a`]({_ALPHA_URL}#split-section) (a) - "
        "**new-domain** - #516 - no lens yet" in out
    )
```

`test_render_joins_multiple_checks_and_a_gap_without_a_target` — same format, no target:

```python
    assert (
        f"- [`alpha/split-section-a`]({_ALPHA_URL}#split-section) (a) - "
        "**new-domain** - no lens yet" in out
    )
```

`test_render_shows_row_notes_in_the_notes_column` — the header and both cell assertions gain the Severity column:

```python
    assert "| Section / claim | Class | Severity | Mapped checks | Gap | Notes |" in out
    assert (
        "| process | Minor | - | - | Process \\| culture: not datable from a snapshot. |"
        in out
    )
    assert (
        f"[Coda]({rht.HANDBOOK_URL}/coda.md)<br>closing words | informative | - | - | - | - |"
        in out
    )
```

`test_render_keeps_gap_fields_from_breaking_the_table` also asserts on a gap bullet; update its bullet expectation to `"- **new-domain** - #516 | #548 - two lenses: neither owns the bound."`. Its table-cell assertion and its trailing-pipe loop are unaffected and must keep passing — that loop is what proves the new column did not break a row.

- [ ] **Step 13: Run the tests to verify they pass**

Run: `uv run pytest tests/scripts/test_render_handbook_traceability.py -v`
Expected: all tests PASS. If any test still fails, fix the renderer or the expectation the failure actually points at; do not delete a test to make the suite green.

- [ ] **Step 14: Document the field in the YAML header**

In `docs/audit/handbook-traceability.yaml`, extend the header comment block that currently documents the classes:

```yaml
# Severity: critical | important | minor - the risk a violation carries, not
# this repo's compliance with it. Required on static/artifact/process rows,
# absent on informative ones. Reuses audit-core's scale so a matrix row and an
# audit finding speak the same language. See the rendered legend for the tests.
```

- [ ] **Step 15: Regenerate the Markdown and run every gate**

```bash
uv run python scripts/render_handbook_traceability.py
uv run ruff check . && uv run ruff format --check . && uv run pyright
uv run pytest tests/scripts/ -v
uv run mkdocs build --strict && uv run python scripts/check_site_links.py site
```

Expected: all green. Read the regenerated `docs/audit/handbook-traceability.md` — specifically the cross-tab and the top of the Critical gap group — and report the headline number (how many Critical clauses are unmapped) in the report file.

- [ ] **Step 16: Commit**

```bash
git add scripts/render_handbook_traceability.py tests/scripts/test_render_handbook_traceability.py docs/audit/handbook-traceability.yaml docs/audit/handbook-traceability.md
git commit -m "feat(#552): validate and render the matrix severity axis

Refs #552"
```

---

### Task 7: Handbook hygiene — delete the keep-awake clause into a sidecar

**Files:**
- Create: `docs/engineering-notes.md`
- Modify: `docs/engineering/lifecycle.md` (the Part 1 blockquote)
- Modify: `docs/engineering/README.md` (link to the sidecar)
- Modify: `docs/README.md` (index entry)
- Modify: `docs/audit/handbook-traceability.yaml` (re-scope `lifecycle/step-by-step-one-issue-end-to-end-e`)
- Regenerate: `docs/audit/handbook-traceability.md`

**Interfaces:**
- Consumes: the completed sweep and renderer from Tasks 1-6.
- Produces: the sidecar the deletion-candidate batch from later reviews will extend.

Scope: **only** the keep-awake clause, which #552 pre-confirms for deletion. Deletion candidates surfaced by Tasks 1-5 are reported, not acted on — they need approval first.

- [ ] **Step 1: Read the clause in place**

Read the blockquote in `docs/engineering/lifecycle.md` (around line 54). It currently carries three clauses: start a background keep-awake for long subagent runs and kill it when done; scope each subagent to its brief; carry standing instructions in the dispatching prompt. Only the first is deleted. Read `docs/engineering/README.md` to find where the spine lists the parts, and `docs/README.md` for the index format.

- [ ] **Step 2: Create the sidecar**

Create `docs/engineering-notes.md`:

```markdown
# Engineering notes

Practices that were true enough to write down and not universal enough to keep in the [engineering handbook](engineering/README.md).

The handbook's value is that everything in it is normative and auditable, which is what justifies the [traceability matrix](audit/handbook-traceability.md) demanding a row for every section. A practice that is Minor *and* contingent on one execution environment fails that bar: a different but legitimate setup makes it meaningless rather than merely differently-implemented. It is still often true, so it lands here rather than in the bin.

Each entry names the practice, the environment it applies to, and why it is not normative. That last part is the point: this is the cutting-room floor with reasons, so a deleted clause is not re-proposed into the handbook a year later.

This file is deliberately outside `docs/engineering/`. Inside, it would need matrix rows for advisory content and would ride into the standalone handbook artifact as if it carried equal weight.

**Not for obsolete practices.** Contingent goes here; obsolete stays deleted. The rule against passing hash-comments to an agent's Bash tool (removed repo-wide in #549) is not recorded here, because it is not true anywhere any more - it worked around a tool-permission gate that no longer exists.

## Keep the host awake during a long agent run

**Practice.** Before dispatching a long-running sequence of subagents, start a background keep-awake process and kill it when the run completes. On macOS: `caffeinate -i -t <seconds> &`.

**Environment.** A laptop or workstation running the agent harness locally, where the OS suspends the machine on an idle timer and a suspended host kills an in-flight run.

**Why it is not normative.** It is contingent on where the harness runs. A cloud harness, a CI runner, or a server with no idle suspension makes the clause meaningless, and the handbook is not the place to encode one execution environment's power management. The failure it prevents is real but recoverable - you rerun the batch - which puts it at Minor even where it applies. Removed from Part 1 in #552.
```

- [ ] **Step 3: Delete the clause from the handbook**

In `docs/engineering/lifecycle.md`, edit the blockquote to drop the keep-awake sentence and keep the other two clauses intact. The paragraph stays one source line (the repo never hard-wraps Markdown), and the surrounding sentences must still read as continuous prose rather than as a sentence with a hole in it.

- [ ] **Step 4: Link the sidecar**

Add a line to the spine in `docs/engineering/README.md` pointing at `../engineering-notes.md`, describing it as advisory and explicitly not part of the handbook. Add an index entry in `docs/README.md` matching the format the neighbouring entries use.

- [ ] **Step 5: Re-scope both matrix rows that cite the deleted clause**

Two rows reference the keep-awake, not one. Leaving either would have the matrix asserting coverage of handbook prose that no longer exists — the drift failure Part 8 warns about, inside the document whose job is to prevent it.

In `docs/audit/handbook-traceability.yaml`:

- `lifecycle/step-by-step-one-issue-end-to-end-e` — edit the `claim` so it no longer mentions the keep-awake and describes only the two clauses that remain (scope each subagent to its brief; carry standing instructions in the dispatching prompt).
- `lifecycle/step-by-step-one-issue-end-to-end-a` — the keep-awake appears in **both** its `claim` ("dispatch a fresh implementer subagent per task behind a background keep-awake") and its `note` ("neither the order nor the keep-awake leaves a trace in the repo"). Remove it from both, leaving the rest of each field intact.

Re-check both rows' `severity` against the narrowed claims. Neither should change — the keep-awake is not what carries either row — but confirm rather than assume, and say so in the report. Leave every other field and every other row alone.

- [ ] **Step 6: Verify**

```bash
uv run python scripts/render_handbook_traceability.py
uv run pytest tests/scripts/ -v
uv run mkdocs build --strict && uv run python scripts/check_site_links.py site
grep -rn "caffeinate\|keep-awake\|keep the host awake" docs/engineering/ docs/audit/ || echo "clean"
```

Expected: renderer green (the section still exists, so no coverage hole), tests green, docs gates green, and the grep finding nothing under either `docs/engineering/` or `docs/audit/`. The `docs/audit/` half is what catches a matrix row left citing the deleted prose — a `docs/engineering/`-only grep passes while the matrix still asserts coverage of a clause that is gone.

Also confirm `docs/engineering-notes.md` is reachable: `mkdocs build --strict` fails on an orphaned page, and `check_site_links.py` catches a directory-style link that `--strict` misses.

- [ ] **Step 7: Report the deletion-candidate batch**

Collect the `## Deletion candidates` sections from all five sweep reports into one list in this task's report file: row id, severity, the environment it is contingent on, and why. This list is for the human's approval; do not act on it. State plainly if it is empty.

- [ ] **Step 8: Commit**

```bash
git add docs/engineering-notes.md docs/engineering/lifecycle.md docs/engineering/README.md docs/README.md docs/audit/handbook-traceability.yaml docs/audit/handbook-traceability.md
git commit -m "docs(#552): move the keep-awake clause out of the handbook into a sidecar

The clause is Minor and contingent on one execution environment: a cloud
harness or CI runner has no idle suspension to defeat, so it encodes one
setup's power management as a universal rule. Recorded in
docs/engineering-notes.md with the environment it applies to and why it is
not normative, so it is not re-proposed later.

Refs #552"
```

---

## Self-review

**Spec coverage** against #552's seven acceptance criteria:

| Criterion | Task |
|---|---|
| `severity` in the YAML schema, validated, with tests | 6 (steps 1-4, 12) |
| Every static/artifact/process row carries one; no informative row does | 1-5, enforced by 6 |
| Severity column, gap list ordered by severity, cross-tab, both legend rules | 6 (steps 5-11) |
| Deletion candidates reported as a batch before removal | 1-5 report them, 7 step 7 collects them |
| Keep-awake removed and its matrix row re-scoped | 7 (steps 3, 5) |
| `docs/engineering-notes.md` created, linked, entries carry environment and why-not-normative | 7 (steps 2, 4) |
| `--check` green, docs gates green | Every task's verify step; 6 step 13 and 7 step 6 run the full set |

**Placeholder scan:** every code step carries the literal code. The five sweep tasks are the exception by nature — a plan cannot pre-compute 108 judgment calls — so they are pinned by the scale, the nine anchors, the two traps, the per-batch notes, and a mechanical diff check that no other field moved.

**Type consistency:** `SEVERITIES`, `SEVERITY_LABELS`, `ASSESSABLE` and `_severity_cell` are defined once in Task 6 and used only there. The YAML key is `severity` throughout, lowercase values, title-cased only at render.

**Risk:** cross-batch calibration drift is the known failure mode. Mitigated by fixing nine anchors in Global Constraints rather than letting each batch invent its own, by requiring a `## Doubts` section so the reviewer checks calibration instead of re-deriving it, and by the distribution sanity check in Task 5. Each task review must verify the batch against the anchors, not merely that each rating is defensible on its own.
