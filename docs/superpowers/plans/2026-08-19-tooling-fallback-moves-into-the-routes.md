# The routes are the tooling fallback - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete the `## Tooling fallback` section from the eleven `arch-audit` check records that declare `routes:`, having first moved every claim it holds that no field carries into the field it belongs to, and make the loader reject the section on a routes record from then on.

**Architecture:** One optional record-level field (`evidence:`) receives the check-level measurement claims that belong to no single route. One predicate (`fallback_lives_in_prose`) scopes every test property whose other side is the record's body prose to the records still declaring `tooling:`. The deletion runs record by record, ordered by triage risk. A loader rule lands last, once no record can violate it, and turns the convention into a gate failure.

**Tech Stack:** Python 3, `pytest`, `ruff`, `PyYAML`. Records are Markdown with YAML frontmatter under `.agents/skills/<domain>-audit/checks/`.

**Spec:** `docs/superpowers/specs/2026-08-19-tooling-fallback-moves-into-the-routes-design.md`. **Issue:** #61.

## Global Constraints

- Markdown is never hard-wrapped: one paragraph is one source line. Never reflow a line you did not change.
- No em-dash (U+2014) anywhere under `docs/engineering/`, `docs/superpowers/specs/`, `docs/superpowers/plans/`. Use ` - `.
- Links in `.agents/skills/` to files in this repo are absolute GitHub URLs rooted at `https://github.com/mesagroup/ai-agent-development-handbook/blob/main/`. Links under `docs/` are relative.
- Never assert a count you did not compute. Compute it in the same breath, or state no number.
- Name a thing, don't number it: "the `checks` argument", not "the fourth argument".
- Never write into `fixtures/python/<partition>` - those trees are seeded audit targets and their contents are ground truth.
- No bare `except Exception: pass`. Every exception is reported, logged at the right level, or re-raised.
- Never run `ruff` against `docs/`. `extend-exclude = ["docs"]` in `pyproject.toml` is load-bearing.
- Run Python through `uv run`. Prepend `caffeinate` to any Bash command that waits.
- `git commit -F - -- <paths>` with explicit paths. Never `git add -A`, `git add .`, `git commit -a`, `git stash`, `git checkout -- .`, `git clean`.
- Every commit message carries `Refs #61`.
- A commit touching `.agents/skills/**/SKILL.md` or `CLAUDE.md` is a prompt change: it goes in its own commit, separate from code, and says WHY rather than only what.
- The gate commands, all three of which must exit 0 before any commit lands:
  - `uv run pytest tests/ -q`
  - `uv run ruff check . && uv run ruff format --check .`
  - `uv run python scripts/render_handbook_traceability.py --check`
  - `uv run python scripts/render_python_fixture_expectations.py --check`

## The eleven records

`.agents/skills/arch-audit/checks/`: `complexity-gate.md`, `complexity.md`, `coupling.md`, `cycles.md`, `dead-code.md`, `hidden-coupling.md`, `layering.md`, `martin-metrics.md`, `over-abstraction.md`, `over-decomposition.md`, `size.md`. All eleven declare `routes:`; no record in any other domain does.

## The triage, resolved at plan time

Computed on 2026-08-19 by diffing each record's `## Tooling fallback` tokens against every other token in the same file, frontmatter and remaining body both. "concrete" counts tokens carrying a digit, a path, a flag prefix or a namespace separator - the ones that can be an operative claim rather than connective prose.

| record | prose-only / concrete | disposition |
|---|---|---|
| `complexity-gate` | 1 / 0 | Delete. The threshold directive is already the `lang: none` route's note. |
| `martin-metrics` | 4 / 0 | Delete. The five formulas are in the `grimp` note and the lead prose. |
| `hidden-coupling` | 7 / 0 | Delete. |
| `complexity` | 8 / 1 | Delete. `--select C901` is in the `ruff` route's `argv`; the one concrete token is a tokenizer artifact, see below. |
| `dead-code` | 9 / 0 | Delete. The vulture-confidence caveat is in the `vulture` note. |
| `size` | 12 / 0 | `evidence:` gains the measurement, then delete. |
| `over-abstraction` | 43 / 6 | Three route-note additions, one `evidence:`, one smoke-run addition, then delete. |
| `cycles` | 132 / 17 | Two smoke-run links into route fields, then delete. |
| `coupling` | 138 / 18 | One smoke-run link into a route field, then delete. |
| `layering` | 170 / 24 | One smoke-run link plus `.madgerc`, then delete. |
| `over-decomposition` | 186 / 22 | One smoke-run link plus `.madgerc`, then delete. |

Two facts behind the right-hand column, both established by checking rather than assumed:

- **No arch record's frontmatter carries the smoke-run link.** `coupling`, `cycles`, `layering` and `over-decomposition` link `docs/audit/typescript-lens-smoke-run.md` from the prose being deleted and from nowhere else; `cycles` also links `docs/audit/python-lens-smoke-run.md` there. Deleting the prose drops the pointer to where the observed behaviour lives.
- **Two measurements have no home.** `docs/audit/typescript-lens-smoke-run.md` carries `9.15.9`, `18.2.0`, `--no-config`, `281`, `totalCruised`, `1090`, `122`, `tsconfig.app.json`, `45` and `31`; it does **not** carry `.madgerc`. No file under `docs/audit/` carries `arch/over-abstraction`'s `502`, `484` or `150`.

**The concrete count over-reports, and the over-report is not one shape.** The tokenizer strips backticks before splitting, so a sentence ending `` `xenon`. `` leaves a bare `.` behind and the `CONCRETE` regex matches it on its leading dot; that is the whole of `complexity`'s single concrete token, and computed across the other five records it is the whole of nobody else's. `coupling`, `cycles` and `over-decomposition` each carry `...` instead, and `layering` and `over-abstraction` carry no punctuation token at all - their over-report is word fragments the stripping broke. So read each concrete list rather than counting it: a token that is punctuation, or a fragment rather than a word, is an artifact and not a claim.

## The triage script

Re-run this before and after each deletion task. It is a throwaway - write it under the session scratchpad, never into the repo.

```python
import re
from pathlib import Path

CHECKS = Path(".agents/skills/arch-audit/checks")
CONCRETE = re.compile(r"^(--|-[a-z]$|\.|/)|\d|\.(md|json|py|ts|toml)|[/@]|_")


def tokens(t):
    t = re.sub(r"[`*\[\]()\"']", " ", t)
    return [x for x in re.split(r"[\s,;:]+", t.lower()) if x]


def fallback(text):
    lines = text.splitlines()
    s = next((n for n, l in enumerate(lines) if l.startswith("## Tooling fallback")), None)
    if s is None:
        return ""
    e = next((n for n in range(s + 1, len(lines)) if lines[n].startswith("## ")), len(lines))
    return "\n".join(lines[s + 1 : e]).strip()


for p in sorted(CHECKS.glob("*.md")):
    text = p.read_text()
    m = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", text, re.DOTALL)
    fm, body = m.group(1), m.group(2)
    fb = fallback(text)
    if not fb:
        print(f"--- {p.stem}: NO SECTION")
        continue
    known = set(tokens(fm)) | set(tokens(body.replace(fb, "")))
    only = sorted({t for t in tokens(fb) if t not in known})
    hard = [t for t in only if CONCRETE.search(t)]
    print(f"--- {p.stem}: {len(only)} prose-only, {len(hard)} concrete")
    if hard:
        print("    CONCRETE: " + " ".join(hard))
```

---

### Task 1: The `evidence:` field

**Files:**
- Modify: `scripts/audit_checks.py` (frontmatter doc table at lines 25-40, `FIELDS` at line 200, `Check` at line 250, validation beside `handbook_note` at lines 796-810, the `Check(...)` construction at line 1027)
- Test: `tests/scripts/test_audit_checks.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `Check.evidence: str | None`. Task 5 and Task 4 write `evidence:` into records; nothing else reads it.

`evidence:` is a record-level field on **either** schema, not a routes-only one. A legacy record could carry it, and no branch on the declared schema is added for it - the smaller rule, and the field is about the check rather than about how the check declares its tools.

- [ ] **Step 1: Write the failing tests**

Append to `tests/scripts/test_audit_checks.py`, beside the `ungranted_note` tests that use the same two helpers. `_record(tooling=None, needs=None, extra="")` renders a minimal `demo/thing` record and inserts `extra` as sibling frontmatter at column 0; `_load_one(tmp_path, check)` writes it as the only record in a fresh tree and loads it.

```python
def test_evidence_is_absent_rather_than_blank_when_the_routes_carry_it(tmp_path):
    """A record with nothing check-level to say about measurement omits it.

    Unlike `needs`, whose absence is the positive claim that no tool here needs
    a grant, an absent `evidence` claims nothing at all: what to measure is in
    the routes, which is where a per-tool measurement belongs.
    """
    checks, errors = _load_one(tmp_path, _record(tooling={"python": ["t"]}))
    assert errors == []
    assert checks["demo/thing"].evidence is None


def test_evidence_carries_the_check_level_measurement(tmp_path):
    check = _record(
        tooling={"python": ["t"]},
        extra="evidence: Line counts per file; flag outliers.\n",
    )
    checks, errors = _load_one(tmp_path, check)
    assert errors == []
    assert checks["demo/thing"].evidence == "Line counts per file; flag outliers."


@pytest.mark.parametrize(
    ("extra", "fragment"),
    [
        ("evidence:\n", "evidence is empty"),
        ("evidence: ''\n", "evidence is blank"),
        ("evidence: '   '\n", "evidence is blank"),
    ],
)
def test_an_empty_evidence_key_is_rejected_rather_than_read_as_absent(
    tmp_path, extra, fragment
):
    """The key present and saying nothing is the one state that must not pass.

    YAML turns a bare `evidence:` into `None`, which is indistinguishable from
    omitting the key by the time it reaches the dataclass - and the two mean
    opposite things, so the difference has to be caught where it is still
    visible. Asserted on the message rather than on the word `evidence`
    appearing somewhere in the error list, because the unknown-key rule already
    produces an error naming `evidence` and these would pass against it.
    """
    _, errors = _load_one(tmp_path, _record(tooling={"python": ["t"]}, extra=extra))
    assert any(fragment in e for e in errors), errors


def test_evidence_must_be_prose_not_a_list(tmp_path):
    check = _record(tooling={"python": ["t"]}, extra="evidence: [a, b]\n")
    _, errors = _load_one(tmp_path, check)
    assert any("evidence must be a string" in e for e in errors), errors
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `caffeinate uv run pytest tests/scripts/test_audit_checks.py -q -k evidence`
Expected: all six FAIL. `FIELDS` rejects an unknown frontmatter key (line 757), so the four that write the key fail with `unknown frontmatter key 'evidence'`, and the first fails on `AttributeError: 'Check' object has no attribute 'evidence'`. That the empty-key cases assert a specific message rather than the word `evidence` is what makes them fail here rather than pass against the unknown-key error.

- [ ] **Step 3: Add the field**

In `FIELDS` (line 200), add `"evidence",` in the position matching the doc table's order - after `"answers_ungranted"` and before `"optin"`.

In the doc table (lines 30-38), add this row after the `answers_ungranted` row:

```
| `evidence` | no, and non-empty where present | What this check measures and what a row records as its evidence, where that belongs to the check rather than to any one route |
```

In `Check` (line 250), after `answers_ungranted: str | None`:

```python
    evidence: str | None
```

Beside the `handbook_note` validation, after the `if handbook and note:` block ending at line 810:

```python
    evidence = meta.get("evidence")
    if "evidence" in meta:
        if evidence is None:
            errors.append(
                f"{where}: evidence is empty - YAML reads a bare key as `None`, "
                "which is indistinguishable from omitting it once it reaches the "
                "dataclass, and the two say opposite things. Write what the check "
                "measures, or drop the key"
            )
        elif not isinstance(evidence, str):
            errors.append(
                f"{where}: evidence must be a string, got {evidence!r} - it is one "
                "statement about the check, not a list of them"
            )
            evidence = None
        elif not evidence.strip():
            errors.append(
                f"{where}: evidence is blank - write what the check measures, or "
                "drop the key"
            )
```

In the `Check(...)` construction (line 1027 onwards), add `evidence=evidence,` after `answers_ungranted=answers_ungranted,`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `caffeinate uv run pytest tests/scripts/test_audit_checks.py -q -k evidence`
Expected: PASS.

- [ ] **Step 5: Run the whole gate**

Run: `caffeinate uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check . && uv run python scripts/render_handbook_traceability.py --check && uv run python scripts/render_python_fixture_expectations.py --check`
Expected: all green, all four exit 0. A test elsewhere that constructs `Check(...)` positionally or exhaustively will fail here - fix it by naming the new field rather than by reordering.

- [ ] **Step 6: Commit**

```bash
git commit -F - -- scripts/audit_checks.py tests/scripts/test_audit_checks.py <<'MSG'
schema: add an optional evidence: field for a check-level measurement

Some of what a fallback section says is neither a route's claim nor the
check's claim about what it looks for: it is what to measure and what a
row records as evidence. arch/size measures line counts whichever of its
three tools runs, and arch/over-abstraction's "one is the trigger"
governs four counts across two languages. With nowhere to put that, the
deletion of the prose that holds it would be a drop.

Optional on either schema rather than only under routes:, because the
field is about the check and not about how the check declares its tools.
Rejected empty where present, for the reason ungranted_note is: YAML
reads a bare key as None, which is indistinguishable from omitting it by
the time it reaches the dataclass, and absent means "the routes say it"
while blank means nothing at all.

Refs #61
MSG
```

---

### Task 2: One predicate, and the properties it scopes

**Files:**
- Modify: `scripts/audit_checks.py` (a new module-level function)
- Modify: `tests/scripts/test_audit_checks.py` (`test_a_record_that_classifies_a_tool_states_a_fallback` at line 2268)
- Modify: `tests/scripts/test_python_fixture_harness.py` (five properties, two helper unit tests)
- Test: `tests/scripts/test_audit_checks.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `audit_checks.fallback_lives_in_prose(check: Check) -> bool`, and `PROSE_FALLBACK_CHECKS: frozenset[str]` in `tests/scripts/test_python_fixture_harness.py`.

**This task must land before any deletion.** `_fallback_paragraphs` raises by design on a record with no section, and `test_every_invocation_quotes_its_record_verbatim` counts the quote in the record text and would find zero. Deleting even one section first is a red suite mid-branch.

- [ ] **Step 1: Write the failing test for the predicate**

Append to `tests/scripts/test_audit_checks.py`:

```python
def test_the_prose_fallback_predicate_follows_the_declared_schema():
    """One predicate, so a property's scope cannot drift from the test's.

    Read off the declared schema rather than off the presence of the section:
    presence is what several of these properties are there to check, so keying
    the scope on it would make each one vacuous on exactly the record it was
    written to catch.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    prose = {c for c, k in checks.items() if ac.fallback_lives_in_prose(k)}
    routed = {c for c, k in checks.items() if not ac.fallback_lives_in_prose(k)}
    assert prose and routed, (len(prose), len(routed))
    assert prose | routed == set(checks)
    assert not prose & routed
    assert routed == {c for c, k in checks.items() if k.routes}
```

- [ ] **Step 2: Run it to verify it fails**

Run: `caffeinate uv run pytest tests/scripts/test_audit_checks.py -q -k prose_fallback_predicate`
Expected: FAIL with `AttributeError: module 'audit_checks' has no attribute 'fallback_lives_in_prose'`.

- [ ] **Step 3: Add the predicate**

In `scripts/audit_checks.py`, after `load_checks`:

```python
def fallback_lives_in_prose(check: Check) -> bool:
    """Whether this record's `## Tooling fallback` prose is its source of truth.

    A record declaring `tooling:` states what to run instead in that section and
    nowhere else, so a property holding a transcription against the record reads
    it there. A record declaring `routes:` states the same thing per route - the
    `note`, the `alone_insufficient` and the `needs` - and carries no such
    section at all, so the same property has no prose to read and its subject is
    the routes.

    Keyed on the declared schema rather than on whether the section is present.
    Presence is what several of those properties exist to check, and a scope
    keyed on it would switch each one off on exactly the record it was written
    to catch.
    """
    return not check.routes
```

- [ ] **Step 4: Run it to verify it passes**

Run: `caffeinate uv run pytest tests/scripts/test_audit_checks.py -q -k prose_fallback_predicate`
Expected: PASS.

- [ ] **Step 5: Scope the fallback-section test**

In `tests/scripts/test_audit_checks.py`, `test_a_record_that_classifies_a_tool_states_a_fallback` currently selects on `check.needs` alone:

```python
    silent = sorted(
        check_id
        for check_id, check in checks.items()
        if check.needs
        and not re.search(
```

Change the condition to:

```python
    silent = sorted(
        check_id
        for check_id, check in checks.items()
        if check.needs
        and ac.fallback_lives_in_prose(check)
        and not re.search(
```

Append this paragraph to that test's docstring, as a new final paragraph:

```
    Scoped to the records whose fallback lives in prose. On a record declaring
    `routes:` the same requirement is machine-enforced instead of being a
    section that exists: a language whose every answering route needs a grant
    must carry `answers_ungranted`, and what to do instead is the untiered
    route itself. The projected `needs` still reports a tier there, so without
    the predicate this would demand a section the schema has replaced.
```

- [ ] **Step 6: Add the scoping set and its guard to the harness tests**

In `tests/scripts/test_python_fixture_harness.py`, change the import on line 15 and add the set below the other module-level constants (beside `SIBLING_LENS_LANGUAGES`, line 307):

```python
from audit_checks import SKILLS_DIR, fallback_lives_in_prose, load_checks
```

```python
_LOADED_CHECKS, _LOAD_ERRORS = load_checks(SKILLS_DIR)
PROSE_FALLBACK_CHECKS = frozenset(
    check_id
    for check_id, check in _LOADED_CHECKS.items()
    if fallback_lives_in_prose(check)
)
```

Then the guard, without which every scoped property below is a no-op that reads as green:

```python
def test_the_prose_fallback_scope_is_not_empty_and_holds_no_migrated_record():
    """The set every property below narrows to, held against both ways it fails.

    Empty is the dangerous direction: each property scoped by this set would
    iterate nothing, assert nothing and pass, so the whole file would go green
    over a tree it had stopped reading. The other direction is a migrated
    record left in the set, where a property looks for prose the record no
    longer has and fails for a reason that is not drift.
    """
    assert _LOAD_ERRORS == []
    assert PROSE_FALLBACK_CHECKS
    assert not any(c.startswith("arch/") for c in PROSE_FALLBACK_CHECKS)
    watched = {i.check for i in INVOCATIONS if not i.check.startswith("arch/")}
    assert watched <= PROSE_FALLBACK_CHECKS, watched - PROSE_FALLBACK_CHECKS
```

- [ ] **Step 7: Scope the five prose-anchored properties**

Each takes the same guard as the first statement of its `for inv in INVOCATIONS:` body:

```python
        if inv.check not in PROSE_FALLBACK_CHECKS:
            continue
```

The five, by name:
- `test_every_invocation_quotes_its_record_verbatim` (line 891)
- `test_every_command_form_the_record_names_is_declared` (line 1263)
- `test_every_flag_the_record_names_occurs_in_a_declared_form` (line 1318)
- `test_a_prescription_stays_in_the_paragraph_the_guard_watches` (line 1556)
- `test_a_form_naming_a_lead_word_off_the_front_is_led_by_some_invocation` (line 1603)

Add this paragraph to each of the five docstrings, adapted to that property's own subject rather than pasted identically:

```
    Read only over the records whose fallback lives in prose. A migrated record
    has no second copy to drift from, and the routes-to-`INVOCATIONS` oracle
    binds its declared forms directly.
```

**`_route_anchoring`'s two consumers stay unscoped**, deliberately: `test_a_transcribed_command_occurs_in_the_sentence_that_prescribes_it` (line 1088) and `test_every_partitions_route_is_held_against_the_quote` (line 1119) hold an entry's argv against that entry's own `record_quote`, both of them fields of the same table, so deleting the record's prose leaves neither side unavailable. What it does change is what the quote is on an arch entry: a frozen prescription rather than a live citation. Record that in a comment immediately above the arch block of `INVOCATIONS` in `scripts/run_python_fixture_lens.py`:

```python
# On a migrated record the `record_quote` below is no longer a citation: the
# prose it was lifted from is gone, and `PROSE_FALLBACK_CHECKS` scopes the
# properties that held it against the record out of these entries. It stays as
# the prescription the argv is still held against - `_route_anchoring`'s two
# consumers read both sides from this table - so an argv edited away from what
# the record prescribed still fails, and editing one means editing the other.
```

- [ ] **Step 8: Move the two helper unit tests off `arch/cycles`**

`test_the_prescribing_paragraph_is_the_line_holding_the_quote` (line 595) and `test_the_watched_paragraphs_are_the_python_side_of_the_section` (line 635) hardcode `arch/cycles`, so they break on deletion whatever the scoping does. `test/coupling-reach` is not a record; the substitute is **`test/coverage-reach`**, verified to carry the same three cases: its quote sits in the `**Python**` paragraph, `**Both**` is a watched non-sibling paragraph, and `**TypeScript**` is a sibling lens.

```python
def test_the_prescribing_paragraph_is_the_line_holding_the_quote():
    quote = "`pytest --cov=<pkg> --cov-branch --cov-report=term-missing` (or `coverage run -m pytest` + `coverage report --show-missing`)."
    paragraph = _prescribing_paragraph("test/coverage-reach", quote)
    assert quote in paragraph
    assert paragraph.count("\n") == 0


def test_the_watched_paragraphs_are_the_python_side_of_the_section():
    """Every paragraph a Python correction can land in, and no sibling lens's.

    `test/coverage-reach` carries all three cases: the `**Python**` paragraph
    its quote sits in, a `**Both**` paragraph labelled for a condition rather
    than a language and so watched, and a `**TypeScript**` paragraph that is
    another lens's prescription.

    On a record whose fallback lives in prose, because the helper reads that
    section and a migrated record has none.
    """
    quote = "`pytest --cov=<pkg> --cov-branch --cov-report=term-missing` (or `coverage run -m pytest` + `coverage report --show-missing`)."
    watched = _watched_paragraphs("test/coverage-reach", quote)
    labels = {
        label
        for label, paragraph in _fallback_paragraphs("test/coverage-reach")
        if paragraph in watched
    }
    assert "Both" in labels
    assert "TypeScript" not in labels
    assert _prescribing_paragraph("test/coverage-reach", quote) in watched
```

Then grep the rest of the file for helper unit tests naming an arch record in an assertion rather than in a docstring, and move each the same way:

Run: `grep -n 'arch/' tests/scripts/test_python_fixture_harness.py`

A docstring naming `arch/cycles` as the record a defect was first seen in is history and stays. An assertion reading an arch record's body does not.

- [ ] **Step 9: Confirm the sibling-lens allowance is still live**

`test_a_prescription_stays_in_the_paragraph_the_guard_watches` ends in `assert skipped`, which fails if `_is_sibling_lens` never grants its exception. That set was verified to be fed exclusively by four `security/*` semgrep entries, all of which stay in scope - so scoping arch out must not empty it.

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q`
Expected: PASS, `assert skipped` included. If it fails, the verification was wrong and the fix is to keep the arch entries in that one property, not to weaken the assertion.

- [ ] **Step 10: Run the whole gate**

Run: `caffeinate uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check . && uv run python scripts/render_handbook_traceability.py --check && uv run python scripts/render_python_fixture_expectations.py --check`
Expected: all green. Nothing has been deleted yet, so every property still reads the prose it always read on the 66 legacy records, and the arch records pass by scope rather than by content.

- [ ] **Step 11: Commit**

```bash
git commit -F - -- scripts/audit_checks.py scripts/run_python_fixture_lens.py tests/scripts/test_audit_checks.py tests/scripts/test_python_fixture_harness.py <<'MSG'
tests: scope the prose-anchored properties by the schema the record declares

Six properties read a record's `## Tooling fallback` and hold a
transcription against it. They are drift instruments: they catch a
prescription written in prose diverging from the declared form. A record
declaring routes: has one copy, so there is nothing to drift, and
`_fallback_paragraphs` raises by design where the section is absent -
which would make the deletion this branch performs a red suite rather
than a passing one.

One predicate in audit_checks rather than a condition per property, so a
property's scope cannot drift from its neighbour's, and keyed on the
declared schema rather than on whether the section is present: presence
is what several of these properties exist to check, and keying on it
would switch each off on the record it was written to catch.

The scoping set carries its own guard. Empty is the failure that reads
as success - every scoped property would iterate nothing and pass - so
the guard holds it non-empty, holds no migrated record in it, and holds
every non-arch watched record inside it.

Two helper unit tests read arch/cycles' body directly and move to
test/coverage-reach, which carries the same three paragraph cases.
_route_anchoring's two consumers stay unscoped: both sides live in the
INVOCATIONS table, so the arch quotes go on binding their argvs. A
comment on that block says what those quotes are now.

Refs #61
MSG
```

---

### Task 3: The two measurements with no home

**Files:**
- Modify: `docs/audit/typescript-lens-smoke-run.md`

**Interfaces:**
- Consumes: nothing.
- Produces: the anchor Task 5 and Task 6 point their route-field links at.

This is the only step that can destroy information, so it lands before any deletion. Both additions are observed behaviour, which is what that document is for.

- [ ] **Step 1: Read the document and find where each belongs**

Run: `caffeinate grep -n 'madge\|ts-morph\|knip' docs/audit/typescript-lens-smoke-run.md`

Read the whole file before writing. It has a structure - a section per tool or per run - and both additions go into the section that already covers that tool, not into a new one at the end. This is a `docs/` file, so links inside it are relative and `ruff` never runs against it.

- [ ] **Step 2: Add `.madgerc`**

`arch/layering` and `arch/over-decomposition` both prescribe reading `.madgerc` as one of the two things that can supply madge a `tsConfig` when the flag is absent, and the smoke-run document does not mention it. Add it to the madge section as the observed fact it is: madge's `tsConfig` option is documented with a default of `null` and madge discovers no config on its own, so only a `.madgerc` or a `madge` key in the partition's `package.json` supplies one when `--ts-config` is not passed.

- [ ] **Step 3: Add `arch/over-abstraction`'s three counts**

`502` interfaces, `484` of them with no implementer at all, and `150` single-export modules, produced by a `ts-morph` walk run from an audit-owned install directory against the same real npm target. Record with them the reason the record gives for why `knip` could not have corroborated them: without the resolved tree it reports first-party files and imported packages alike as unused, which inflates exactly these counts.

Write what was observed. Do not write that the numbers were moved here, or from where.

- [ ] **Step 4: Verify**

Run: `caffeinate bash -c 'for t in .madgerc 502 484 150 ts-morph; do printf "%-12s %s\n" "$t" "$(grep -c -- "$t" docs/audit/typescript-lens-smoke-run.md)"; done'`
Expected: every count at least 1.

- [ ] **Step 5: Run the whole gate**

Run: `caffeinate uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check . && uv run python scripts/render_handbook_traceability.py --check && uv run python scripts/render_python_fixture_expectations.py --check`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git commit -F - -- docs/audit/typescript-lens-smoke-run.md <<'MSG'
docs: record the madge config-discovery fact and the ts-morph fan-in counts

Two observations lived only in arch record prose that is about to be
deleted, and this is the document that holds observed tool behaviour.

madge's `.madgerc` is one of the two things that can supply a tsConfig
when --ts-config is absent, which is why passing the flag is not
optional; two records prescribe reading it and nothing here mentioned it.

The 502/484/150 fan-in counts are the only measurement behind
arch/over-abstraction's TypeScript route, and no file under docs/audit/
carried them - so deleting the prose would have been a drop rather than
a move.

Refs #61
MSG
```

---

### Task 4: Delete the six with no concrete residue

**Files:**
- Modify: `.agents/skills/arch-audit/checks/complexity-gate.md`, `complexity.md`, `dead-code.md`, `hidden-coupling.md`, `martin-metrics.md`, `size.md`

**Interfaces:**
- Consumes: `Check.evidence` from Task 1, `PROSE_FALLBACK_CHECKS` from Task 2.
- Produces: six records with no `## Tooling fallback`. Task 7's loader rule requires all eleven.

These six carry no concrete prose-only token, so the residue is connective prose over claims the frontmatter already states. They go first because they prove the deletion end to end at no triage risk.

- [ ] **Step 1: Read each section against its frontmatter, sentence by sentence**

For each of the six, print the section and the frontmatter side by side and read every sentence:

Run: `caffeinate bash -c 'for r in complexity-gate complexity dead-code hidden-coupling martin-metrics size; do echo "########## $r"; awk "/^## Tooling fallback/{on=1;next} /^## /{on=0} on \&\& NF" .agents/skills/arch-audit/checks/$r.md; done'`

The concrete-token count being zero says no flag, path or number is unique to the prose. It does **not** say every sentence is duplicated - a claim written entirely in ordinary words is invisible to it. So read for those, and there is one known case, handled in the next step.

- [ ] **Step 2: `size` gains its `evidence:`**

`arch/size`'s section opens with the check's measurement, and its three tools measure the same thing, so it belongs to no route. Add to `.agents/skills/arch-audit/checks/size.md`'s frontmatter, after `locality: local` and before `handbook:`:

```yaml
evidence: >-
  Line counts per file; flag outliers and anything over a documented norm.
```

The lead prose above `## Severity` already carries the norm-and-outliers judgment, so this states the measurement it is read from.

- [ ] **Step 3: Delete the six sections**

Delete the `## Tooling fallback` heading and its paragraphs from each of the six, leaving `## Severity` followed directly by `## Fix`. Delete the blank line that separated the section from its neighbour, not two. Touch nothing else in any of the six files.

- [ ] **Step 4: Re-run the triage script**

Expected: those six print `NO SECTION`; the other five print their counts unchanged from the table above.

- [ ] **Step 5: Run the whole gate**

Run: `caffeinate uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check . && uv run python scripts/render_handbook_traceability.py --check && uv run python scripts/render_python_fixture_expectations.py --check`
Expected: all green. A failure naming one of the six is Task 2's scoping being incomplete - fix the scoping, do not restore a section.

- [ ] **Step 6: Commit**

```bash
git commit -F - -- .agents/skills/arch-audit/checks/complexity-gate.md .agents/skills/arch-audit/checks/complexity.md .agents/skills/arch-audit/checks/dead-code.md .agents/skills/arch-audit/checks/hidden-coupling.md .agents/skills/arch-audit/checks/martin-metrics.md .agents/skills/arch-audit/checks/size.md <<'MSG'
record: delete the six fallback sections the routes already state in full

Each of these six restates its own frontmatter. Diffed token by token
against the rest of the file, none carries a flag, path or number the
routes do not: complexity's --select C901 is in the ruff route's argv,
dead-code's vulture-confidence caveat is in the vulture note,
complexity-gate's threshold directive is the lang: none route's note, and
martin-metrics' five formulas are in the grimp note and the lead prose.

size is the exception and gains an evidence: field first. Its three tools
measure the same thing, so "line counts per file" is the check's claim
and no route's, and it was in no field at all.

Refs #61
MSG
```

---

### Task 5: `over-abstraction`

**Files:**
- Modify: `.agents/skills/arch-audit/checks/over-abstraction.md`

**Interfaces:**
- Consumes: `Check.evidence` from Task 1, the smoke-run additions from Task 3.
- Produces: a tenth record with no `## Tooling fallback`.

Its six concrete prose-only tokens are `/class`, `@abstractmethod`, `registrants/arms`, `502`, `484`, `150`. Two operative claims are also prose-only without being concrete, and they are the ones that matter most.

- [ ] **Step 1: Read the section and the frontmatter together**

Run: `caffeinate bash -c 'sed -n "/^---$/,/^---$/p" .agents/skills/arch-audit/checks/over-abstraction.md; echo "########## SECTION"; awk "/^## Tooling fallback/{on=1;next} /^## /{on=0} on \&\& NF" .agents/skills/arch-audit/checks/over-abstraction.md'`

- [ ] **Step 2: Add the trigger threshold and the recording rule as `evidence:`**

The section says "**one** (or zero) is the trigger" against each of four counts, and "**Record the count and the `file:line` of both the abstraction and its lone consumer**". Both govern all four counts across both languages, so neither is any route's claim. Add to the frontmatter after `locality: global` and before `handbook:`:

```yaml
evidence: >-
  Every count this check takes is read against the same trigger: one
  concrete subclass, one call site, one registrant or arm, one distinct
  bound value - or zero - is the trigger, and more than one is not. Record
  the count and the `file:line` of both the abstraction and its lone
  consumer.
```

- [ ] **Step 3: Add the three criteria the routes drop**

The `lang: python`, `kind: library`, `tool: grimp` route's `note` names the four counts but not what makes something an abstraction, and not the `match`-dispatch arm. Extend that note so it carries all three prose-only criteria:

- the abstraction is an `ABC` base, a `Protocol` base, **or any class carrying `@abstractmethod`** - the third is the one the note drops
- the subclass count is of **concrete** subclasses across the tree
- the registry count is of registrants **or `match` arms**
- the call sites for a single-function module or one-method wrapper class come from `grimp` refs **or a scoped grep**

Keep the note one folded scalar and keep it a description of what the record prescribes, in the voice the neighbouring notes use.

- [ ] **Step 4: Point the TypeScript route at the smoke run**

The `lang: typescript`, `kind: library`, `tool: ts-morph` route's note already carries the `ERR_MODULE_NOT_FOUND` behaviour and the install-into-an-audit-owned-directory prescription. Add one sentence to it linking the counts that install produced, absolute-URL form because this is a file under `.agents/skills/`:

```
The counts this produced on the target it was first run against are recorded in [the smoke run](https://github.com/mesagroup/ai-agent-development-handbook/blob/main/docs/audit/typescript-lens-smoke-run.md).
```

Do not restate `502`, `484` or `150` here. The numbers live in the smoke run; the record carries the pointer.

- [ ] **Step 5: Delete the section**

- [ ] **Step 6: Re-run the triage script**

Expected: `over-abstraction` prints `NO SECTION`. Seven of the eleven now do.

- [ ] **Step 7: Run the whole gate**

Run: `caffeinate uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check . && uv run python scripts/render_handbook_traceability.py --check && uv run python scripts/render_python_fixture_expectations.py --check`
Expected: all green.

- [ ] **Step 8: Commit**

```bash
git commit -F - -- .agents/skills/arch-audit/checks/over-abstraction.md <<'MSG'
record: move over-abstraction's trigger and criteria into its frontmatter

Its fallback section held three things no field carried. The trigger -
one, or zero, is a finding and more than one is not - governs all four
counts in both languages, so it is the check's claim and becomes
evidence:, together with the rule that a row records the count and the
file:line of the abstraction and of its lone consumer.

Three criteria the grimp note dropped go back into it: an abstraction is
an ABC base, a Protocol base or any class carrying @abstractmethod; the
subclass count is of concrete subclasses; a registry's count includes
match arms. A count taken against a narrower definition of its own
subject is a wrong answer that looks like a clean one.

The ts-morph route now links the smoke run rather than restating the
counts it produced.

Refs #61
MSG
```

---

### Task 6: The four TypeScript-heavy records

**Files:**
- Modify: `.agents/skills/arch-audit/checks/coupling.md`, `cycles.md`, `layering.md`, `over-decomposition.md`

**Interfaces:**
- Consumes: the smoke-run additions from Task 3.
- Produces: all eleven records with no `## Tooling fallback`, which is Task 7's precondition.

Between them these four hold most of the deleted bytes, and almost all of it is measured observation the smoke-run document already carries. The claim that survives deletion only if it is moved is the **link**.

- [ ] **Step 1: Resolve every concrete token, per record**

Run the triage script and, for each of the four, take its concrete list and place each token in one of three buckets. Record the result as a comment on issue #61 before editing any of the four - that comment is the triage record the spec requires.

- **already in a field on this record** - `coupling`'s `.madgerc` and `options.tsConfig` are in its madge note and its `alone_insufficient`; nothing to do.
- **measured observation** - `1090`, `122`, `18.2.0`, `9.15.9`, `11`, `281`, `31`, `45`, `6`, `7`, `--info`, `--circular`, `--no-config`, `.cjs`, `.js`, `.jsx`, `.mjs`, `@tsconfig/`, `tsconfig.app.json`, `package.json`. Confirm each is in `docs/audit/typescript-lens-smoke-run.md`, or in `docs/audit/python-lens-smoke-run.md` for `cycles`' Python-side numbers, before deleting the sentence that carries it. Task 3 added the two that were missing; verify rather than assume, per token, and if one is still absent add it there first.
- **operative and in no field** - the smoke-run link, on all four. Handled in the next step.

A token that fits none of the three is a conscious drop: name it in the #61 comment with the reason, and do not delete it silently.

- [ ] **Step 2: Move the link into a route field, on each of the four**

Each of the four links `docs/audit/typescript-lens-smoke-run.md` from prose and nowhere else, and `cycles` also links `docs/audit/python-lens-smoke-run.md`. Add the pointer to the route field whose claim the observation supports - the `dependency-cruiser` route's `alone_insufficient` where the observation is about `--config` and `--no-config`, the madge route's `note` where it is about `--ts-config` - in absolute-URL form:

```
[the smoke run](https://github.com/mesagroup/ai-agent-development-handbook/blob/main/docs/audit/typescript-lens-smoke-run.md)
```

One link per route field that needs one. Do not add a link to a route whose claim the smoke run says nothing about.

- [ ] **Step 3: Delete the four sections**

- [ ] **Step 4: Re-run the triage script**

Expected: all eleven print `NO SECTION`.

- [ ] **Step 5: Verify no link was lost**

Run: `caffeinate bash -c 'grep -rc "smoke-run" .agents/skills/arch-audit/checks/ | grep -v ":0"'`
Expected: `coupling.md`, `cycles.md`, `layering.md`, `over-decomposition.md` and `over-abstraction.md` each report at least 1, all of them now inside the frontmatter.

Run: `caffeinate bash -c 'for f in .agents/skills/arch-audit/checks/*.md; do n=$(sed -n "/^---$/,/^---$/p" "$f" | grep -c "smoke-run"); t=$(grep -c "smoke-run" "$f"); [ "$n" = "$t" ] || echo "OUTSIDE FRONTMATTER: $f $n of $t"; done'`
Expected: no output.

- [ ] **Step 6: Run the whole gate**

Run: `caffeinate uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check . && uv run python scripts/render_handbook_traceability.py --check && uv run python scripts/render_python_fixture_expectations.py --check`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git commit -F - -- .agents/skills/arch-audit/checks/coupling.md .agents/skills/arch-audit/checks/cycles.md .agents/skills/arch-audit/checks/layering.md .agents/skills/arch-audit/checks/over-decomposition.md <<'MSG'
record: delete the four TypeScript fallback sections, keeping the smoke-run link

Most of what these four sections held beyond their routes is measured
observation - the edge count thinning under a missing --ts-config, the
transpiler that never arrives under an unpinned co-package, the empty
cycle set under --no-config - and every one of those numbers is in the
smoke-run record that the prose linked.

The link itself was in no field on any of the eleven, so deleting the
prose would have left the routes making claims with no pointer to what
was observed behind them. It moves into the route field whose claim each
observation supports.

Refs #61
MSG
```

---

### Task 7: The loader rejects the section on a routes record

**Files:**
- Modify: `scripts/audit_checks.py` (a module-level regex, and a check beside the title validation at line 1009)
- Test: `tests/scripts/test_audit_checks.py`

**Interfaces:**
- Consumes: all eleven records already deleted (Tasks 4, 5, 6). This rule errors on every one of them until then.
- Produces: the gate that makes the convention enforced rather than observed.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_routes_record_may_not_carry_a_fallback_section(tmp_path):
    """The direction the scoping cannot catch.

    Scoping the prose properties to records declaring `tooling:` stops them
    reading a section that is not there. It says nothing about a section coming
    back: a migrated record that grows one again carries a second copy of its
    routes that no property reads and nothing holds against them, which is the
    state this whole change exists to end.
    """
    text = _routes_frontmatter("kind: command\n    tool: t\n    argv: [t]")
    _write(
        tmp_path,
        "demo-audit/checks/thing.md",
        text + "\n## Tooling fallback\n\nRun `t` over the package.\n",
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("Tooling fallback" in e for e in errors), errors


def test_a_tooling_record_may_carry_a_fallback_section(tmp_path):
    """The 66 records still on the old schema keep theirs, and must."""
    _write(
        tmp_path,
        "demo-audit/checks/thing.md",
        _record(tooling={"python": ["t"]})
        + "\n## Tooling fallback\n\nRun `t` over the package.\n",
    )
    _, errors = ac.load_checks(tmp_path)
    assert errors == [], errors
```

Both build the record text and write it with `_write` rather than going through `_one_route_record` or `_load_one`, because those two render the body themselves and neither takes a body argument. Do not add a body parameter to them for two tests.

- [ ] **Step 2: Run them to verify the first fails**

Run: `caffeinate uv run pytest tests/scripts/test_audit_checks.py -q -k fallback_section`
Expected: the first FAILs on an empty `errors`; the second PASSes already.

- [ ] **Step 3: Add the rule**

Beside `_TITLE_RE` at line 217:

```python
_FALLBACK_SECTION_RE = re.compile(r"^## Tooling fallback\s*$", re.M)
```

After the title validation block (line 1009 onwards), before `if errors:`:

```python
    if raw_routes is not None and _FALLBACK_SECTION_RE.search(body):
        errors.append(
            f"{where}: declares routes: and carries a `## Tooling fallback` "
            "section. On this schema the routes are the fallback - a route's "
            "note says what to run, its alone_insufficient says what running it "
            "is not enough for on its own, and its needs says what must be "
            "present first. A section beside them is a second copy nothing "
            "holds against the first, and the properties that would have read "
            "it do not read a migrated record"
        )
```

Add the rule to the module docstring, as a sentence in the paragraph describing `routes`.

- [ ] **Step 4: Run them to verify both pass**

Run: `caffeinate uv run pytest tests/scripts/test_audit_checks.py -q -k fallback_section`
Expected: PASS.

- [ ] **Step 5: Mutation-verify both directions**

Direction A - reintroducing a section on a migrated record must fail:

```bash
caffeinate bash -c '
printf "\n## Tooling fallback\n\nLine counts per file.\n" >> .agents/skills/arch-audit/checks/size.md
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/render_handbook_traceability.py --check; echo "gate exit: $?"
PYTHONDONTWRITEBYTECODE=1 uv run pytest tests/scripts/test_audit_checks.py -q 2>&1 | tail -3
git checkout -- .agents/skills/arch-audit/checks/size.md
git diff --stat -- .agents/skills/arch-audit/checks/size.md
'
```
Expected: the gate exits non-zero naming `arch/size`, the suite fails, and the final `git diff --stat` is empty. Note the pathspec on the `git checkout` - the bare `git checkout -- .` form is banned.

Direction B - removing a section from a legacy record with a tiered tool must fail:

```bash
caffeinate bash -c '
uv run python -c "
import sys; sys.path.insert(0, \"scripts\")
from audit_checks import SKILLS_DIR, load_checks, fallback_lives_in_prose
checks, errors = load_checks(SKILLS_DIR)
assert errors == []
victims = sorted(c for c, k in checks.items() if k.needs and fallback_lives_in_prose(k))
print(victims[0])
"
'
```

Take the id it prints, delete that record's `## Tooling fallback` section, run `PYTHONDONTWRITEBYTECODE=1 uv run pytest tests/scripts/test_audit_checks.py -q`, confirm `test_a_record_that_classifies_a_tool_states_a_fallback` fails and names that record, then restore it with `git checkout -- <that path>` and confirm `git diff --stat` on it is empty.

Both mutations must be reverted before the commit. Verify with `git status --short` that the only modified paths are the ones this task owns.

- [ ] **Step 6: Run the whole gate**

Run: `caffeinate uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check . && uv run python scripts/render_handbook_traceability.py --check && uv run python scripts/render_python_fixture_expectations.py --check`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git commit -F - -- scripts/audit_checks.py tests/scripts/test_audit_checks.py <<'MSG'
schema: reject a `## Tooling fallback` section on a record declaring routes:

Scoping the prose properties to the records still declaring tooling:
stops them reading a section that is not there. It cannot catch the
section coming back - a migrated record that regrows one carries a second
copy of its routes that no property reads and nothing holds against them,
which is the state this change exists to end.

In the validator rather than in a test, so the integrity gate reports it
with everything else the loader finds, and because it is a consistency
property that can be decided from the file alone.

Lands after the eleventh deletion: until then it errors on every migrated
record, correctly.

Refs #61
MSG
```

---

### Task 8: The agent-facing prose

**Files:**
- Modify: `.agents/skills/audit/SKILL.md` (line 52)
- Modify: `.agents/skills/audit-core/SKILL.md` (lines 34, 36, 38, 66)
- Modify: `CLAUDE.md` (the check-records section)
- Read: `docs/audit/sweep-obligations.md`

**Interfaces:**
- Consumes: everything above. This describes the finished state.
- Produces: nothing code reads.

This is a prompt change and takes its own commit, saying why. Both sentences are live instructions that stop being true for a migrated record, so an agent reading them looks for a section that is not there.

- [ ] **Step 1: `audit/SKILL.md`**

Line 52 tells an agent "if it has none, fall back to the record's `## Tooling fallback`". Make it say what to read on each schema: the section on a record declaring `tooling:`, and the record's own routes on a record declaring `routes:`, where a route's `note`, `alone_insufficient` and `needs` are what the section used to say.

- [ ] **Step 2: `audit-core/SKILL.md`, the body-sections list**

Line 66 enumerates the frontmatter fields and lists the body sections. Two edits in that one line:

- The field list reads `(id, domain, locality, handbook, optin, and one of two mutually exclusive schemas for what the check runs: tooling/needs/ungranted_note, or routes/answers_ungranted)`. Add `evidence` to it, as the optional record-level field carrying what the check measures where that belongs to no single route. A field an agent is never told about is data nothing reads.
- The section list reads `## Severity`, `## Tooling fallback`, `## Fix`, `## Review lens`. Say that `## Tooling fallback` is a section of a record declaring `tooling:`, and that a record declaring `routes:` has none because its routes carry it.

- [ ] **Step 3: `audit-core/SKILL.md`, the detects-before-it-prescribes rule**

The same line 66 says "Every `## Tooling fallback` **detects before it prescribes**". That rule is about the record, not about the section: it must still bind a routes record, through the routes. Rewrite it so the obligation attaches to the record and names where each schema discharges it.

- [ ] **Step 4: Re-read the withheld-grant passage**

Lines 34, 36 and 38 decide the withheld-grant outcome and already distinguish the two schemas per field. Read all three for any sentence that assumes the section exists on a migrated record - that is the passage where a missed edit silences a check rather than merely misdirecting a read. Change only what is now false.

- [ ] **Step 5: `CLAUDE.md`**

The `## Check records` section enumerates the frontmatter fields and the two schemas. Add `evidence` to it with the same one-line meaning, and add that a record declaring `routes:` carries no `## Tooling fallback` section and that the loader rejects one.

- [ ] **Step 6: The sweep-obligations reading pass**

`docs/audit/sweep-obligations.md` is hand-maintained, and `tests/test_sweep_obligations.py` catches an anchor that no longer occurs in `audit-core` exactly once and a quotation that is no longer verbatim - it cannot judge whether a row's disposition is still true. Editing `audit-core/SKILL.md` obliges a read of the whole file.

Run: `caffeinate uv run pytest tests/test_sweep_obligations.py -q`

Then read every row and check its disposition against the edited `audit-core`. Verified before this plan was written: no row names `## Tooling fallback`, so no row is expected to move. If one does, edit it in this commit.

- [ ] **Step 7: Verify the running session sees the skills**

Run: `caffeinate uv run python -c "import sys; sys.path.insert(0, 'scripts'); from audit_checks import SKILLS_DIR, load_checks; c, e = load_checks(SKILLS_DIR); print(len(c), e)"`
Expected: the record count and an empty error list, proving the records parse from this tree. Do not run `claude plugin details` - it reads the installed marketplace clone, which tracks a pushed commit and cannot see this branch.

- [ ] **Step 8: Run the whole gate**

Run: `caffeinate uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check . && uv run python scripts/render_handbook_traceability.py --check && uv run python scripts/render_python_fixture_expectations.py --check`
Expected: all green.

- [ ] **Step 9: Commit**

```bash
git commit -F - -- .agents/skills/audit/SKILL.md .agents/skills/audit-core/SKILL.md CLAUDE.md <<'MSG'
prompt: tell an executing agent where a routes record's fallback lives

Two live instructions send an agent to a section that no longer exists on
a migrated record. audit/SKILL.md says to fall back to the record's
`## Tooling fallback` where a partition names no tool of its own;
audit-core lists that section among a record's body sections and hangs
the detects-before-it-prescribes rule on it. An agent following either
on one of the eleven arch records finds nothing and has no instruction
for what to read instead - which is a check reporting no-evidence for a
reason the record could have answered.

Both now name the schema: the section on a record declaring tooling:, the
routes on a record declaring routes:, where a route's note,
alone_insufficient and needs carry what the section carried. The
detects-before-it-prescribes obligation attaches to the record rather
than to the section, so it still binds where the section is gone.

The field enumerations gain evidence:. A field the reading agent is never
told about is data nothing reads.

Refs #61
MSG
```

---

### Task 9: Closure

**Files:**
- Modify: whatever the stale-prose pass turns up
- Read: `tests/scripts/test_python_fixture_harness.py`, `scripts/run_python_fixture_lens.py`

**Interfaces:**
- Consumes: everything above.
- Produces: the branch, ready for a PR.

- [ ] **Step 1: Account for every surviving mention of the section**

Run: `caffeinate grep -rn "Tooling fallback" --include='*.md' --include='*.py' . | grep -v '^./docs/superpowers/'`

Every survivor must be one of: a legacy record's own section, a scoped test or helper that reads one, the loader's new error message, the loader's docstring, `CLAUDE.md`, a `SKILL.md` sentence naming the schema, or a docstring recording where a defect was first seen. Anything else is stale prose. List them and their category before changing anything.

- [ ] **Step 2: The stale-prose pass, scoped by blast radius**

The deletion falsified example sentences in prose that no diff hunk touches. Read, in full rather than by hunk:

- `_fallback_paragraphs`' docstring cites `arch/complexity-gate` as the record that "prescribes inside an unlabelled bolded directive". That record now has no section.
- `_is_sibling_lens`' docstring cites `With none of them installed` as a label holding the Python fallback. Check whether any legacy record still carries that label; if none does, the example is about records that no longer exist.
- `_watched_paragraphs`' docstring cites `arch/cycles`' append shape.
- `scripts/run_python_fixture_lens.py`'s comments around `INVOCATIONS` reference record prose - lines 237, 242 and 302 among them.

Run: `caffeinate grep -rn "arch/" tests/scripts/test_python_fixture_harness.py scripts/run_python_fixture_lens.py`

A sentence recording where a defect was first seen is history and stays true - the defect was seen there. A sentence asserting present tense about a record's current content does not. Rewrite the second kind; leave the first.

Dispatch this pass to a subagent that has not seen the implementation, per the repository's own instruction. Pass it the worktree's absolute root and require it to confirm `git rev-parse --show-toplevel` matches before it reads or edits.

- [ ] **Step 3: Confirm the byte count moved**

Run: `caffeinate bash -c 'wc -c .agents/skills/arch-audit/checks/*.md | tail -1'`

State the figure in the PR body. Do not state a figure you did not compute.

- [ ] **Step 4: Run the whole gate one last time**

Run: `caffeinate uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check . && uv run python scripts/render_handbook_traceability.py --check && uv run python scripts/render_python_fixture_expectations.py --check`
Expected: all green, all four exit 0. Record the test count.

- [ ] **Step 5: Commit whatever the pass changed**

```bash
git commit -F - -- <the paths the stale-prose pass touched> <<'MSG'
docs: correct the prose the deletion falsified

Four docstrings and a comment block cite an arch record's fallback prose
as a present-tense example of a shape they watch. The prose is gone, so
each reads as a claim about a section the record does not have.

A sentence recording where a defect was first seen stays: the defect was
seen there, and that is still true. A sentence asserting what a record
currently carries is rewritten.

Refs #61
MSG
```

- [ ] **Step 6: Comment on #54**

```bash
gh issue comment 54 --body "$(cat <<'EOF'
#61 shrinks this issue's scope rather than resolving it.

This issue asks the transcription guards to watch the whole record rather than one section, because a prescription written in `## Fix` is invisible to them. On a record declaring `routes:` there is no longer a prescription outside the frontmatter to watch: the eleven `arch-audit` records have no `## Tooling fallback`, the loader rejects one, and their prescriptions live in route fields the routes-to-`INVOCATIONS` oracle binds.

So what remains here is the records still declaring `tooling:`, for as long as they wait to migrate, and the guards that read them are now scoped to exactly those by `audit_checks.fallback_lives_in_prose`. The scope shrinks with each domain that migrates and closes when the last one does.

One thing #61 does not close, and #58 carries it: the oracle binds `command` routes, so a `procedure` or `library` route's note was watched by the prose properties and is watched by nothing now. Deletion removes drift as a failure mode, not a wrong note.
EOF
)"
```

- [ ] **Step 7: Hand off**

The plan is complete. `superpowers:finishing-a-development-branch` opens the PR. Do not merge.

## Self-review

**Spec coverage.** Each acceptance criterion against the task that discharges it:

| criterion | task |
|---|---|
| `evidence:` specified and validated, rejected empty where present | 1 |
| Evidence triage recorded per record | plan-time table above, plus Task 6 step 1's #61 comment for the four |
| No arch record has the section, and no claim lost | 4, 5, 6 |
| One predicate scopes the fallback-section test and the harness's fallback-paragraph and `record_quote` properties | 2 |
| Arch `INVOCATIONS` retained, oracle binding both directions | 2 (the entries are untouched; `_route_anchoring`'s consumers stay unscoped) |
| Both `SKILL.md` files updated in a prompt commit of their own saying why | 8 |
| Scoping mutation-verified in both directions | 7 step 5 |
| New code ships with unit tests, coverage does not drop | 1, 2, 7 |
| Suite green, ruff clean, both gates exit 0 | every task's penultimate step, and 9 step 4 |
| #54 commented | 9 step 6 |

**Ordering.** Task 2 before any deletion, or the suite is red on the first one. Task 3 before Tasks 5 and 6, or a measurement is destroyed. Task 7 after the last deletion, or it errors on all eleven. Task 1 before Tasks 4 and 5, which write `evidence:`.

**Known residuals, both recorded rather than closed.** A `procedure` or `library` route's `note` was watched by the prose properties and is watched by nothing afterwards - the oracle binds `command` routes. That is #58's, and Task 9 step 6 says so on #54. And on an arch entry `record_quote` becomes a frozen prescription rather than a citation; Task 2 step 7 puts that in a comment where the quotes live.
