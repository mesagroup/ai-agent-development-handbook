# Gap-entry kinds in the traceability matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the gap list distinguish its three kinds of entry (unchecked / residue / process) explicitly, and make the coverage summary's closing total reconcile with the components above it.

**Architecture:** All changes are in one rendering script and its test module. A new `_gap_kind()` classifier is the single source of truth for the three kinds; the gap list uses it for a per-bullet tag, a per-band count line, and ordering, and the coverage summary uses it for a reconciling closing sentence. The `_critical_purity_note()` helper is deleted, subsumed by the per-band counts. The matrix YAML is not touched.

**Tech Stack:** Python 3.11+, pytest, `scripts/render_handbook_traceability.py`, `docs/audit/handbook-traceability.yaml`.

**Design:** `docs/superpowers/specs/2026-07-30-gap-entry-kinds-design.md`

## Global Constraints

- **Do not change `docs/audit/handbook-traceability.yaml`.** No row's data is wrong; only the renderer's reporting is. A task that edits the YAML has misread the spec.
- **Do not add or tighten any `validate()` rule.** In particular, do NOT forbid `gap` on a `process` row and do NOT require `report-only` on one. The spec rejects both explicitly; `<origin-repo>#554` says "Do not fix this by forbidding the shape."
- **No em-dashes (U+2014) anywhere.** This codebase writes ` - ` (space hyphen space) in rendered prose. Match the surrounding strings exactly.
- **Google-style docstrings** on every new function, with `Args:` / `Returns:` sections. No reStructuredText roles or directives. This is a CLAUDE.md rule.
- **No environment-specific values** in any committed file (no absolute machine paths, personal profiles, hostnames).
- New code ships with unit tests. `scripts/` is not exempt: the existing `tests/scripts/test_render_handbook_traceability.py` loads the script via `importlib` and is where all new tests go.
- Before each commit run `uv run ruff check .` AND `uv run ruff format --check .`. Both gate CI.
- Commit messages explain **why**, not just what. No Claude credits.

---

### Task 1: Three-way kind classification in the gap list

**Files:**
- Modify: `scripts/render_handbook_traceability.py` (add `KINDS` / `KIND_LABELS` constants near line 87; add `_gap_kind` and `_kind_split_line`; delete `_critical_purity_note` at lines 496-523; rewrite the gap-list block inside `render()` at lines 607-635; adjust the cross-tab preamble at lines 649-658)
- Test: `tests/scripts/test_render_handbook_traceability.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `_gap_kind(row: dict[str, Any]) -> str` returning exactly one of `"unchecked"`, `"residue"`, `"process"`; the module constant `KINDS = ("unchecked", "residue", "process")`. Task 2 uses both.

**Context the implementer needs:**

`validate()` already guarantees the invariants this task relies on, so do not re-check them at render time:
- an `informative` row can never carry a `gap` (line 370), so every gap row is `static`, `artifact`, or `process`;
- every `static` / `artifact` / `process` row carries one of the three severities (line 350), so grouping the gap list by severity loses nothing;
- a `process` row can never carry `checks` (line 378).

The three kinds therefore partition the gap list exactly, which is the property the tests pin.

The fixture `_valid_rows()` (test file line 139) already contains a `process` row: `alpha/split-section-b`, `severity: minor`, no gap. Giving it a gap is how tests reach the third kind. The fixture's other rows: `alpha/mapped-section` (static, important, checked, no gap), `alpha/split-section-a` (artifact, critical, gapped, unchecked), `coda/coda` (informative).

- [ ] **Step 1: Write the failing tests for the tag, the split line, and the ordering**

Add these four tests to `tests/scripts/test_render_handbook_traceability.py`, immediately after `test_render_groups_the_gap_list_by_severity_worst_first` (line 348-359):

```python
def _rows_with_all_three_kinds():
    # One band holding all three kinds at once, so tags, counts, and ordering
    # are all observable from a single render.
    rows = _valid_rows()
    rows[0]["severity"] = "critical"
    rows[0]["gap"] = {"recommendation": "extend-skill", "note": "residue"}
    rows[2]["severity"] = "critical"
    rows[2]["gap"] = {"recommendation": "report-only", "note": "prose only"}
    return rows


def test_render_tags_each_gap_bullet_with_its_kind():
    # A bullet has to carry its own kind: #9 emits issues from single
    # entries, and a position in a list does not survive extraction.
    out = rht.render(_rows_with_all_three_kinds())
    assert "- [`alpha/mapped-section`](" in out
    assert "#mapped-section) (residue) - **extend-skill**" in out
    assert "#split-section) (a) (unchecked) - **new-domain**" in out
    assert "#split-section) (b) (process) - **report-only**" in out


def test_render_opens_each_band_with_its_kind_split():
    out = rht.render(_rows_with_all_three_kinds())
    assert "### Critical\n\n1 unchecked, 1 residue, 1 process row.\n" in out


def test_render_suppresses_zero_terms_in_the_kind_split():
    # A band with one kind states that kind alone, rather than padding two
    # zeroes a reader has to skip.
    out = rht.render(_valid_rows())
    assert "### Critical\n\n1 unchecked.\n" in out
    assert "0 residue" not in out
    assert "0 process" not in out


def test_render_orders_gap_bullets_unchecked_then_residue_then_process():
    out = rht.render(_rows_with_all_three_kinds())
    assert (
        out.index("(a) (unchecked)")
        < out.index("(residue)")
        < out.index("(b) (process)")
    )
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/scripts/test_render_handbook_traceability.py -k "kind or tags or split or orders" -v`
Expected: FAIL. The tag assertions fail on missing `(unchecked)` text; the split-line assertions fail on the absent count line.

- [ ] **Step 3: Add the kind constants and the classifier**

In `scripts/render_handbook_traceability.py`, after the `SEVERITY_LABELS` line (line 88), add:

```python
KINDS = ("unchecked", "residue", "process")
# Singular and plural for the per-band count line; "unchecked" is invariant.
KIND_LABELS = {
    "unchecked": ("unchecked", "unchecked"),
    "residue": ("residue", "residues"),
    "process": ("process row", "process rows"),
}
```

Then add these two functions in place of `_critical_purity_note` (delete lines 496-523 entirely and put these there):

```python
def _gap_kind(row: dict[str, Any]) -> str:
    """Which of the three gap-entry kinds a gap-carrying row is.

    The three are not interchangeable downstream: an unchecked clause needs
    new capability, a residue widens something that already runs, and a
    process claim closes in report prose rather than in any skill's matrix.
    They also land in different cross-tab columns, so a two-way split would
    file a process gap under Unmapped and break the band arithmetic.

    Args:
        row: A gap-carrying matrix row, already through `validate`.

    Returns:
        One of `"unchecked"`, `"residue"`, `"process"`.
    """
    if row["class"] == "process":
        return "process"
    return "residue" if row.get("checks") else "unchecked"


def _kind_split_line(group: list[dict[str, Any]]) -> str:
    """The band's own split across the three kinds, zero terms omitted.

    Printing the split is what makes the band's unchecked figure readable
    rather than a counting exercise: it is the same number as the band's
    Unmapped column in the cross-tab.

    Args:
        group: The gap-carrying rows of one severity band.

    Returns:
        A sentence such as `"30 unchecked, 17 residues."`.
    """
    parts = []
    for kind in KINDS:
        n = sum(1 for r in group if _gap_kind(r) == kind)
        if not n:
            continue
        singular, plural = KIND_LABELS[kind]
        parts.append(f"{n} {singular if n == 1 else plural}")
    return ", ".join(parts) + "."
```

- [ ] **Step 4: Rewrite the gap-list block**

Replace lines 607-635 of `render()` (the block from `gaps = [...]` through the bullet `out.append(...)`) with:

```python
    gaps = [r for r in rows if r.get("gap")]
    out.append("\n## Gap list\n")
    if not gaps:
        out.append("No gaps: every auditable row is mapped.")
    else:
        out.append(
            "Ordered by severity - the risk a violation carries - then by kind, "
            "then by handbook order. Each entry names its kind, its "
            "recommendation (`extend-skill` / `new-domain` / `report-only`) and, "
            "where one exists, the issue that would close it. Three kinds "
            "appear, and they are different work: `(unchecked)` is a clause "
            "nothing checks, so closing it means new capability; `(residue)` is "
            "the part of a claim a mapped check does not reach, so closing it "
            "widens something that already runs; `(process)` is a claim no "
            "snapshot can settle, which closes in report prose and an adoption "
            "roadmap rather than in any skill's matrix. Each band opens with its "
            "own split, and a band's unchecked count is the same number as its "
            "[cross-tab](#severity-x-coverage) Unmapped column."
        )
    for sev in SEVERITIES:
        group = [r for r in gaps if r.get("severity") == sev]
        if not group:
            continue
        out.append(f"\n### {SEVERITY_LABELS[sev]}\n")
        out.append(_kind_split_line(group))
        out.append("")
        for kind in KINDS:
            for r in (g for g in group if _gap_kind(g) == kind):
                url, marker = handbook_link(r)
                gap = r["gap"]
                # Bullets, not cells: a pipe is harmless here, a newline is not.
                bits = [f"**{gap['recommendation']}**"]
                if gap.get("target"):
                    bits.append(_oneline(gap["target"]))
                if gap.get("note"):
                    bits.append(_oneline(gap["note"]))
                out.append(
                    f"- [`{r['id']}`]({url}){marker} ({kind}) - " + " - ".join(bits)
                )
```

Note: `_critical_purity_note` is gone, so nothing calls it. Confirm with `grep -rn "_critical_purity_note" .` that no reference survives in either the script or the tests.

- [ ] **Step 5: Point the cross-tab preamble at the tag**

In the cross-tab preamble (line ~652), change the phrase

```
"listed by name under the matching heading in the [gap list](#gap-list) "
```

to

```
"listed by name, tagged `(unchecked)`, under the matching heading in the "
"[gap list](#gap-list) "
```

so the sentence names exactly which bullets the Unmapped column refers to. Before the tag existed the heading also held partials, which made this sentence imprecise; it is now exact.

- [ ] **Step 6: Delete the superseded purity-note test**

Delete `test_render_states_whether_the_critical_band_is_all_unchecked` (lines 361-374) in full, including its comment block. The per-band count line prints the same fact for every band, so the narrower test now pins a mechanism that no longer exists.

- [ ] **Step 7: Update the three existing tests that assert bullet text**

The tag sits between the link (with its split marker) and the recommendation, so three existing assertions need it inserted.

In `test_render_marks_split_rows_and_links_gap_entries` (line 274-277), change:

```python
    assert (
        f"- [`alpha/split-section-a`]({_ALPHA_URL}#split-section) (a) - "
        "**new-domain** - #2 - no lens yet" in out
    )
```

to:

```python
    assert (
        f"- [`alpha/split-section-a`]({_ALPHA_URL}#split-section) (a) (unchecked) - "
        "**new-domain** - #2 - no lens yet" in out
    )
```

In `test_render_joins_multiple_checks_and_a_gap_without_a_target` (line 316-319), change:

```python
    assert (
        f"- [`alpha/split-section-a`]({_ALPHA_URL}#split-section) (a) - "
        "**new-domain** - no lens yet" in out
    )
```

to:

```python
    assert (
        f"- [`alpha/split-section-a`]({_ALPHA_URL}#split-section) (a) (unchecked) - "
        "**new-domain** - no lens yet" in out
    )
```

`test_render_keeps_gap_fields_from_breaking_the_table` (line 333) asserts only the tail `"- **new-domain** - #2 | #11 - two lenses: neither owns the bound."`, which the tag does not touch. Leave it unchanged.

- [ ] **Step 8: Run the tests**

Run: `uv run pytest tests/scripts/test_render_handbook_traceability.py -v`
Expected: all pass, with `test_render_states_whether_the_critical_band_is_all_unchecked` absent from the list.

- [ ] **Step 9: Lint and format**

```bash
uv run ruff check .
uv run ruff format --check .
```
Expected: both clean. If `ruff format --check` reports the script or the test file, run `uv run ruff format .` and re-run.

- [ ] **Step 10: Commit**

```bash
git add scripts/render_handbook_traceability.py tests/scripts/test_render_handbook_traceability.py
git commit -m "fix(<origin-repo>#553): tag every gap entry with its kind"
```

The body must say why a tag rather than ordering alone (an entry extracted by #9 loses its position but keeps its tag), and why `_critical_purity_note` is removed rather than kept (the per-band count states the same fact for all three bands, so keeping both would print it twice in two shapes).

---

### Task 2: Reconcile the coverage summary's gap total

**Files:**
- Modify: `scripts/render_handbook_traceability.py` (the closing summary sentence in `render()`, currently lines 676-686)
- Test: `tests/scripts/test_render_handbook_traceability.py`
- Regenerate: `docs/audit/handbook-traceability.md`

**Interfaces:**
- Consumes: `_gap_kind` and `KINDS` from Task 1.
- Produces: nothing further.

**Context the implementer needs:**

The defect is the sentence `f"{len(gaps)} rows carry a gap entry in total. "`. `gaps` counts every gap-carrying row, while the `full` / `partial` / `unmapped` figures before it partition auditable rows only. Today the two populations happen to coincide because no `process` row carries a gap, so the arithmetic is correct only by absence.

Note the schema guarantee that makes the reconciliation exact: an auditable row with no checks must carry a gap (`validate` line 376), so *every* unmapped row is a gap entry. Auditable gap entries are therefore exactly `unmapped + partial`.

- [ ] **Step 1: Write the failing tests for both branches**

Replace `test_render_reports_full_and_partial_coverage_apart` (lines 280-287) with the version below, and add the two new tests after it:

```python
def test_render_reports_full_and_partial_coverage_apart():
    rows = _valid_rows()
    # A row that carries both a check and a residual gap is partial, not mapped.
    rows[0]["gap"] = {"recommendation": "extend-skill", "note": "residue"}
    out = rht.render(rows)
    assert "**0 fully mapped** (0%), **1 partially mapped**" in out
    assert "**1 unmapped**" in out


def test_render_reconciles_the_gap_total_when_no_process_row_gaps():
    rows = _valid_rows()
    rows[0]["gap"] = {"recommendation": "extend-skill", "note": "residue"}
    out = rht.render(rows)
    assert (
        "All 2 gap entries sit on auditable rows: the 1 unmapped ones plus "
        "the 1 partial." in out
    ) or (
        "All 2 gap entries sit on auditable rows: the 1 unmapped one plus "
        "the 1 partial." in out
    )
    # The unreconciled phrasing is gone.
    assert "rows carry a gap entry in total" not in out


def test_render_reconciles_the_gap_total_when_a_process_row_gaps():
    # The case <origin-repo>#554 names: the closing total counted a population the
    # components above it never included. It is absent from today's matrix,
    # so only a fixture can hold the arithmetic honest.
    rows = _valid_rows()
    rows[0]["gap"] = {"recommendation": "extend-skill", "note": "residue"}
    rows[2]["gap"] = {"recommendation": "report-only", "note": "prose only"}
    out = rht.render(rows)
    assert "2 of the 3 gap entries sit on auditable rows" in out
    assert "all 1 unmapped" in out
    assert "plus the 1 partial" in out
    assert "the other 1 sits on a process row" in out
```

The first test's `or` is a placeholder that Step 3 removes: pick whichever singular phrasing the implementation produces and delete the other branch, so the assertion pins one exact string.

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/scripts/test_render_handbook_traceability.py -k "reconciles or full_and_partial" -v`
Expected: FAIL, on the still-present `"rows carry a gap entry in total"` phrasing.

- [ ] **Step 3: Write the reconciling sentence**

In `render()`, after the existing `unmapped = [...]` line, add:

```python
    process_gaps = [r for r in gaps if _gap_kind(r) == "process"]
```

Then replace the whole closing `out.append(...)` (lines 676-686) with:

```python
    if process_gaps:
        n = len(process_gaps)
        reconciliation = (
            f"{len(gaps) - n} of the {len(gaps)} gap entries sit on auditable "
            f"rows (all {len(unmapped)} unmapped, plus the {len(partial)} "
            f"partial); the other {n} "
            + ("sits on a process row" if n == 1 else "sit on process rows")
            + ", whose claim is auditable in principle but belongs in report "
            "prose rather than in any skill's matrix. "
        )
    else:
        reconciliation = (
            f"All {len(gaps)} gap entries sit on auditable rows: the "
            f"{len(unmapped)} unmapped "
            + ("one" if len(unmapped) == 1 else "ones")
            + f" plus the {len(partial)} partial. "
        )
    out.append(
        f"{len(rows)} rows total. Of the {len(auditable)} auditable rows "
        f"({counts['static']} static + {counts['artifact']} artifact): "
        f"**{len(full)} fully mapped** ({pct}%), **{len(partial)} partially mapped** "
        f"(a check that reaches part of the claim, with the residue recorded as a gap), "
        f"and **{len(unmapped)} unmapped** (no check reaches the claim; every one of "
        f"them still carries a gap entry saying so and why, which the schema requires). "
        + reconciliation
        + f"The remaining {counts['process']} process and {counts['informative']} informative "
        f"rows are not auditable by design - the honest record of what a snapshot cannot settle."
    )
```

Then go back to the first test of Step 1 and collapse its `or` into the single branch this produces (`"the 1 unmapped one plus the 1 partial."`).

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/scripts/test_render_handbook_traceability.py -v`
Expected: all pass.

- [ ] **Step 5: Add the real-matrix invariant test**

`test_real_matrix_passes_the_strict_check` (the file's last test) only calls `rht.main(["--check"])`, so the module has no YAML import yet. Add `import yaml` to the import block at the top of the file, keeping isort order (it is a third-party import, so it belongs beside `import pytest`).

Then append this to the end of `tests/scripts/test_render_handbook_traceability.py`, after `test_real_matrix_passes_the_strict_check`:

```python
def test_real_matrix_band_unchecked_counts_match_the_cross_tab():
    # <origin-repo>#553's second criterion, made mechanical rather than a counting
    # exercise: a band's printed unchecked figure is the same number as its
    # Unmapped column, and stays so as rows are added. Both are read out of
    # the rendered page, so a renderer that drifts them apart fails here.
    import re

    rows = yaml.safe_load(rht.YAML_PATH.read_text())
    out = rht.render(rows)

    printed = {}
    for sev in ("Critical", "Important", "Minor"):
        m = re.search(rf"### {sev}\n\n([^\n]+)\n", out)
        assert m, f"no kind-split line under ### {sev}"
        n = re.search(r"(\d+) unchecked", m.group(1))
        printed[sev] = int(n.group(1)) if n else 0

    cross_tab = {}
    for sev in ("Critical", "Important", "Minor"):
        m = re.search(rf"\| {sev} \| \d+ \| \d+ \| (\d+) \|", out)
        assert m, f"no cross-tab row for {sev}"
        cross_tab[sev] = int(m.group(1))

    assert printed == cross_tab
```

Move `import re` to the module's import block if ruff's isort rule objects to the function-local import; a local import is fine here and keeps the test self-contained, but `ruff check` is the arbiter.

- [ ] **Step 6: Run the tests again**

Run: `uv run pytest tests/scripts/test_render_handbook_traceability.py -v`
Expected: all pass, including the new invariant test.

- [ ] **Step 7: Regenerate the rendered matrix**

```bash
uv run python scripts/render_handbook_traceability.py
uv run python scripts/render_handbook_traceability.py --check
```
Expected: the first writes the file, the second exits 0.

Then read the regenerated `docs/audit/handbook-traceability.md` gap list and confirm by eye: every bullet carries a tag, each band opens with its split, and the Critical band reads `4 unchecked.` with no residue or process term.

- [ ] **Step 8: Run the documentation gates**

```bash
uv run mkdocs build --strict
uv run python scripts/check_site_links.py site
```
Expected: both succeed. The `#severity-x-coverage` and `#gap-list` anchors are unchanged, so no link should break.

- [ ] **Step 9: Lint and format**

```bash
uv run ruff check .
uv run ruff format --check .
```
Expected: both clean.

- [ ] **Step 10: Commit**

```bash
git add scripts/render_handbook_traceability.py tests/scripts/test_render_handbook_traceability.py docs/audit/handbook-traceability.md
git commit -m "fix(<origin-repo>#554): reconcile the gap total with the coverage components"
```

The body must say that the old total drew on a different population from the components above it, that the mismatch is invisible today only because no process row carries a gap, and that a fixture rather than the live matrix is what holds the arithmetic honest.

---

## Self-review notes

- **Spec coverage:** decision 1 (tag on every bullet) is Task 1 Steps 3-4 and 7; decision 2 (per-band count line, zeros suppressed) is Task 1 Steps 3-4, tested in Step 1; decision 3 (ordering) is Task 1 Step 4, tested in Step 1; decision 4 (`_critical_purity_note` removed) is Task 1 Steps 3 and 6; decision 5 (reconciling closing sentence, both branches) is Task 2 Steps 1-3; decision 6 (#9 treats the kinds as different work) is recorded in the gap-list preamble prose, Task 1 Step 4. The scope boundary (cross-tab unchanged) holds: Task 1 Step 5 edits only the preamble sentence, not the table.
- **Placeholder scan:** the only deliberate placeholder is the `or` in Task 2 Step 1's first assertion, which Step 3 explicitly collapses to one branch. Everything else is literal code.
- **Type consistency:** `_gap_kind` returns strings drawn from `KINDS`, and every consumer (`_kind_split_line`, the bullet loop, `process_gaps`) iterates or compares against that same tuple. `KIND_LABELS` is keyed by the same three strings.
- **Ordering:** Task 2's real-matrix invariant test (Step 5) depends on Task 1's split line existing, which is why it sits in Task 2 rather than Task 1.
