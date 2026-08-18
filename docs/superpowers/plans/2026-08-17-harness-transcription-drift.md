# Harness Transcription Drift Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the harness fail when a check record grows a prescribed command the harness does not run, and repair the two entries where that has already happened.

**Architecture:** Each `Invocation` gains a `forms` field declaring every command form its record's prescribing paragraph names, each with a disposition. Four test properties compare that declaration against the record, mechanically extracted from the paragraph containing `record_quote`. The existing three guards all run harness to record; these run record to harness, which is the direction both known defects live in.

**Tech Stack:** Python 3.11+, pytest, ruff, uv. No new dependencies.

**Spec:** [`../specs/2026-08-17-harness-transcription-drift-design.md`](../specs/2026-08-17-harness-transcription-drift-design.md)

## Global Constraints

- Never write into `fixtures/python/<partition>`. Those are seeded audit targets and their contents are ground truth.
- No em-dash (U+2014) anywhere in `docs/engineering/`, `docs/superpowers/specs/`, `docs/superpowers/plans/`. Use ` - `.
- Markdown is never hard-wrapped: one paragraph is one source line. Never reflow a line you did not change.
- A commit touching a check record is a prompt change: it goes in its own commit and its message says WHY, not just what.
- Every commit message carries `Refs #51`.
- Run `uv run ruff check .` and `uv run ruff format --check .` before every commit. CI runs both.
- Run `uv run pytest tests/ -q` before every commit. The suite is at 484 tests at the start of this plan; it only goes up.
- Never assert a count you did not compute. Compute it in the same breath or state no number.
- No bare `except Exception: pass`. Every exception is reported with type and message, logged, or re-raised.
- Links in `.agents/skills/` to files in this repo are absolute GitHub URLs. Everything under `docs/` links relatively.
- New code ships with unit tests, and adding code must not lower coverage.
- Scripts are loaded in tests via `importlib.util.spec_from_file_location`, with `scripts/` already on `sys.path` through `tests/scripts/conftest.py`.

## File Structure

| File | Responsibility | Tasks |
|---|---|---|
| `scripts/run_python_fixture_lens.py` | `DISPOSITIONS` vocabulary, the `forms` field and its validation, the re-transcribed argv, the `--check` filter | 1, 3, 4, 5, 8 |
| `tests/scripts/test_python_fixture_harness.py` | the extractor helpers and the four properties | 1, 2, 5, 6 |
| `.agents/skills/arch-audit/checks/cycles.md` | the reworded prescription, and the two sentences the re-run falsifies | 3, 7, 8 |
| `.agents/skills/deps-audit/checks/vulnerabilities.md` | the provenance sentence | 7 |
| `docs/audit/python-lens-smoke-run.md` | the re-run's published observation, with its own date | 8 |

---

### Task 1: The `forms` field and its vocabulary

**Files:**
- Modify: `scripts/run_python_fixture_lens.py` (add `DISPOSITIONS` beside `NO_VERSION_ROUTE` at line 303; add the field and its validator to `Invocation`, whose `__post_init__` is at line 391)
- Test: `tests/scripts/test_python_fixture_harness.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `DISPOSITIONS: tuple[str, ...]`, and `Invocation.forms: tuple[tuple[str, str], ...]` defaulting to `()`. Later tasks import `DISPOSITIONS` into the test module and populate `forms` on every entry.

The field defaults to `()` so this task changes no existing entry and the suite stays green. Task 5 populates it and turns on the property that makes an empty declaration a failure.

- [ ] **Step 1: Write the failing tests**

Add to `tests/scripts/test_python_fixture_harness.py`, beside the other `Invocation` validation tests:

```python
def test_a_form_carrying_an_unknown_disposition_is_rejected():
    with pytest.raises(ValueError, match="not one of"):
        Invocation(
            check="arch/cycles",
            tool="pydeps",
            record_quote="x" * 40,
            forms=(("pydeps --show-cycles", "maybe"),),
        )


def test_an_empty_form_is_rejected():
    with pytest.raises(ValueError, match="empty command form"):
        Invocation(
            check="arch/cycles",
            tool="pydeps",
            record_quote="x" * 40,
            forms=(("   ", "runs"),),
        )


def test_the_same_form_declared_twice_is_rejected():
    with pytest.raises(ValueError, match="twice"):
        Invocation(
            check="arch/cycles",
            tool="pydeps",
            record_quote="x" * 40,
            forms=(("pydeps --show-cycles", "runs"), ("pydeps --show-cycles", "superseded")),
        )
```

Add `DISPOSITIONS` to the `from run_python_fixture_lens import (...)` block at the top of the file, in alphabetical position.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -k "disposition or empty_form or declared_twice" -v`
Expected: FAIL - `ImportError: cannot import name 'DISPOSITIONS'`.

- [ ] **Step 3: Add the vocabulary**

In `scripts/run_python_fixture_lens.py`, immediately after `NO_VERSION_ROUTE` (line 303):

```python
# What a declared command form is for. `runs` is the only value the harness acts
# on; the other three are the ways a record's paragraph names a command it does
# not want run here. Naming them is the point: without a disposition, a form the
# harness does not run is indistinguishable from a form nobody noticed, which is
# how `--show-dot` sat unprescribed in `arch/cycles` through three green guards.
DISPOSITIONS: tuple[str, ...] = ("runs", "alternative", "superseded", "forbidden")
```

- [ ] **Step 4: Add the field and its validator**

Add to the `Invocation` field list, after `findings_stream` (line 389):

```python
    forms: tuple[tuple[str, str], ...] = ()
```

Add to the `Args:` block of the class docstring, after the `record_quote` entry:

```
        forms: Every command form this record's prescribing paragraph names for
            this tool, as `(form, disposition)` pairs, taken by reading it. The
            declaration is what the record-to-harness guards compare: the three
            older guards all run the other way, holding the transcription
            against the record, so a record that *grows* a prescription leaves
            them green while the harness quietly stops running what it says it
            runs.
```

Call the validator from `__post_init__`, on the line after `self._check_supplied()`:

```python
        self._check_forms()
```

And add the method after `_check_supplied`:

```python
    def _check_forms(self) -> None:
        """The three ways a declared form would stop meaning anything."""
        seen: set[str] = set()
        for form, disposition in self.forms:
            if not form.strip():
                raise ValueError(
                    f"{self.check}/{self.tool}: declares an empty command form, "
                    "which no extraction can ever match"
                )
            if disposition not in DISPOSITIONS:
                raise ValueError(
                    f"{self.check}/{self.tool}: {form!r} carries disposition "
                    f"{disposition!r}, which is not one of {DISPOSITIONS}"
                )
            if form in seen:
                raise ValueError(
                    f"{self.check}/{self.tool}: declares {form!r} twice, so which "
                    "disposition applies would depend on reading this file"
                )
            seen.add(form)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q`
Expected: PASS, with three more tests than before.

- [ ] **Step 6: Run the full gate**

Run: `caffeinate bash -c 'uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check .'`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add scripts/run_python_fixture_lens.py tests/scripts/test_python_fixture_harness.py
git commit -m "feat: let an invocation declare the command forms its record names

Refs #51" -- scripts/run_python_fixture_lens.py tests/scripts/test_python_fixture_harness.py
```

---

### Task 2: The extractor

**Files:**
- Modify: `tests/scripts/test_python_fixture_harness.py` (helpers beside `_tokens` at line 68 and `_is_subsequence` at line 86)

**Interfaces:**
- Consumes: `_record_path(check)` and `_tokens(text)`, already in the test module.
- Produces: `_spans(paragraph) -> list[str]`, `_command_forms(paragraph, tool) -> set[str]`, `_flag_spans(paragraph) -> set[str]`, `_prescribing_paragraph(check, quote) -> str`, and `_concrete(tokens) -> list[str]`. Tasks 5 and 6 build every property on these.

The extractor is tested against inline strings rather than the real records, so its behaviour is pinned independently of what any record currently says. A test that reads a record to prove the extractor works fails the day the record changes, for a reason that has nothing to do with the extractor.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_span_that_is_only_the_tool_name_is_a_mention_not_a_form():
    """A record names a bare command in order to forbid it.

    `deps/vulnerabilities` writes "Run `pip-audit` with no arguments and it
    audits whatever environment it was launched from ... so don't". Reading that
    as a prescription would demand a declaration for the one command the record
    tells the reader not to run.
    """
    paragraph = "Run `pip-audit` with no arguments, so don't. Use `pip-audit --locked .`."
    assert _command_forms(paragraph, "pip-audit") == {"pip-audit --locked ."}


def test_a_form_is_recognised_only_for_the_tool_that_leads_it():
    paragraph = "`uv export --frozen` writes the set that `pip-audit -r <file>` reads."
    assert _command_forms(paragraph, "pip-audit") == {"pip-audit -r <file>"}
    assert _command_forms(paragraph, "uv") == {"uv export --frozen"}


def test_flag_spans_are_pooled_across_the_paragraph():
    """A record prescribes a flag without repeating the command it belongs to."""
    paragraph = "Append `--show-dot` to that `pydeps` invocation; `pydeps --show-cycles` alone prints nothing."
    assert _flag_spans(paragraph) == {"--show-dot"}


def test_a_placeholder_token_is_dropped_before_matching_an_argv():
    """A record writes what the caller supplies; an argv writes what it supplied.

    This is what lets the coverage property watch `deps/vulnerabilities`, whose
    placeholder had to switch off the anchor guard entirely.
    """
    assert _concrete(_tokens("pip-audit -r <requirements> --no-deps")) == [
        "pip-audit",
        "-r",
        "--no-deps",
    ]


def test_the_prescribing_paragraph_is_the_line_holding_the_quote():
    quote = "`pydeps` gives a visual; the counts are the evidence."
    paragraph = _prescribing_paragraph("arch/cycles", quote)
    assert quote in paragraph
    assert paragraph.count("\n") == 0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -k "mention or leads_it or pooled or placeholder or prescribing_paragraph" -v`
Expected: FAIL with `NameError: name '_command_forms' is not defined`.

- [ ] **Step 3: Write the helpers**

Add after `_is_subsequence` (line 95):

```python
def _spans(paragraph: str) -> list[str]:
    """Every backtick span in the paragraph, in order, duplicates collapsed."""
    return list(dict.fromkeys(re.findall(r"`([^`]+)`", paragraph)))


def _command_forms(paragraph: str, tool: str) -> set[str]:
    """The command forms the paragraph prescribes for one tool.

    A span whose first token is the tool's own name and which carries at least
    one argument. A span that is only the bare name is a mention: a record names
    a bare command in order to warn against it, and treating that as a
    prescription would demand a declaration for the command it forbids.
    """
    return {
        span
        for span in _spans(paragraph)
        if len(span.split()) > 1 and span.split()[0] == tool
    }


def _flag_spans(paragraph: str) -> set[str]:
    """Every span the paragraph writes as a bare flag.

    Pooled across the paragraph rather than attributed to a tool, because a
    record prescribing a flag does not repeat the command it belongs to:
    `arch/cycles` writes "Append `--show-dot` to that `pydeps` invocation", and
    a rule keyed on the tool's name would miss the very drift this guards.
    """
    return {span for span in _spans(paragraph) if span.startswith("-")}


def _concrete(tokens: list[str]) -> list[str]:
    """A form's tokens with the record's placeholders removed.

    A record writes `<requirements>` where the caller supplies a path, so the
    placeholder can never occur in an argv. Dropping it is what lets the
    coverage property watch the entry whose placeholder forced the anchor guard
    to be switched off for it.
    """
    return [t for t in tokens if not (t.startswith("<") and t.endswith(">"))]


def _prescribing_paragraph(check: str, quote: str) -> str:
    """The source line the record's prescribing sentence sits in.

    Markdown here is never hard-wrapped, so one paragraph is one line and the
    quote's line is the whole prescribing paragraph. Anchoring on the quote
    rather than on the `**Python**` review-lens line is what covers the records
    carrying a python: entry and no such line at all.
    """
    lines = [
        line for line in _record_path(check).read_text().splitlines() if quote in line
    ]
    if len(lines) != 1:
        raise AssertionError(
            f"{check}: its quote occurs in {len(lines)} source lines, so which "
            "paragraph prescribes it is not decidable"
        )
    return lines[0]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q`
Expected: PASS.

- [ ] **Step 5: Run the full gate and commit**

```bash
caffeinate bash -c 'uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check .'
git add tests/scripts/test_python_fixture_harness.py
git commit -m "test: extract a record's prescribed command forms from its paragraph

Refs #51" -- tests/scripts/test_python_fixture_harness.py
```

---

### Task 3: Reword `arch/cycles` and re-transcribe both drifted entries

**Files:**
- Modify: `.agents/skills/arch-audit/checks/cycles.md:28`
- Modify: `scripts/run_python_fixture_lens.py` (the `arch/cycles` + `pydeps` entry and the `deps/vulnerabilities` + `pip-audit` entry in `INVOCATIONS`)

**Interfaces:**
- Consumes: nothing.
- Produces: `arch/cycles` + `pydeps` with `argv=("pydeps", "--show-cycles", "--show-dot")` and its `record_quote` moved to the reworded sentence; `deps/vulnerabilities` + `pip-audit` with the `pip` partition's argv carrying `--no-deps --disable-pip`.

**This task makes two commits.** The record edit is a prompt change and goes in its own commit, before the transcription commit that follows it.

- [ ] **Step 1: Reword the record**

In `.agents/skills/arch-audit/checks/cycles.md`, inside the single `**Python** - ` source line, replace:

```
**Append `--show-dot` to that `pydeps` invocation - `pydeps --show-cycles` alone has no textual output channel at all.**
```

with:

```
**Run `pydeps --show-cycles --show-dot`: `--show-cycles` alone has no textual output channel at all.**
```

Change nothing else on that line. The sentences after it still read correctly: "It exits 0 with empty stdout and empty stderr" continues to refer to `--show-cycles` alone.

- [ ] **Step 2: Verify the reworded sentence can anchor**

Run:

```bash
caffeinate uv run python -c "
import pathlib, re
line = [l for l in pathlib.Path('.agents/skills/arch-audit/checks/cycles.md').read_text().splitlines() if l.startswith('**Python** ')][0]
spans = re.findall(r'\`([^\`]+)\`', line)
print('forms:', sorted({s for s in spans if s.split()[0] == 'pydeps' and len(s.split()) > 1}))
print('flag spans:', sorted({s for s in spans if s.startswith('-')}))
"
```

Expected: forms are `pydeps --show-cycles` and `pydeps --show-cycles --show-dot`, and the flag spans are `--show-cycles` and `--show-dot`. Both flags still appear bare, because a later explanatory sentence on the same line writes "`--show-dot` prints the underlying dot source as text instead" and this task does not touch it. What matters is not that the bare spans disappear but that every one of them now occurs inside a declared form, which is what the flag property in Task 6 asserts. If a flag span appears that no form contains, the reword did not take.

- [ ] **Step 3: Commit the record edit on its own**

```bash
git add .agents/skills/arch-audit/checks/cycles.md
git commit -F - -- .agents/skills/arch-audit/checks/cycles.md <<'EOF'
prompt: prescribe the whole pydeps command instead of a flag to append

The record told the reader to append `--show-dot` to a command named two
sentences earlier. No single sentence then carries the whole command in
argument order, so no quote can anchor the transcription against it - which is
why the harness went on running the bare form through three green guards. A
record that prescribes a whole command can be held to it. `deps/freshness`
already writes its corrected command whole, so this is the family's existing
shape rather than a new one.

Refs #51
EOF
```

- [ ] **Step 4: Re-transcribe the `arch/cycles` entry**

In `INVOCATIONS`, on the `arch/cycles` + `pydeps` entry: set `argv=("pydeps", "--show-cycles", "--show-dot")` and replace `record_quote` with the reworded sentence, verbatim and including its bold markers:

```python
        record_quote=(
            "**Run `pydeps --show-cycles --show-dot`: `--show-cycles` alone has "
            "no textual output channel at all.**"
        ),
```

Leave `completion=("src/fixture_app",)` and its `note` as they are.

- [ ] **Step 5: Re-transcribe the `deps/vulnerabilities` entry**

On the `deps/vulnerabilities` + `pip-audit` entry, change the `pip` partition's argv from `("pip-audit", "-r", "requirements.txt")` to:

```python
            ("pip", ("pip-audit", "-r", "requirements.txt", "--no-deps", "--disable-pip")),
```

Leave the `pylock` partition's `("pip-audit", "--locked", ".")` unchanged, and leave the entry's `record_quote` unchanged: it already spans the two adjacent sentences prescribing `--locked` and `-r`.

- [ ] **Step 6: Run the existing guards**

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q`
Expected: PASS. In particular `test_every_invocation_quotes_its_record_verbatim`, `test_a_quote_is_a_sentence_rather_than_a_fragment`, `test_a_transcribed_command_occurs_in_the_sentence_that_prescribes_it` and `test_folding_a_completion_into_the_argv_breaks_the_anchor` must all still pass. If the last one fails, the completion count it pins has moved; recompute it with the command in Task 6 Step 6 rather than editing the number to whatever makes it green.

- [ ] **Step 7: Run the full gate and commit**

```bash
caffeinate bash -c 'uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check .'
git add scripts/run_python_fixture_lens.py
git commit -m "fix: transcribe the corrected pydeps and pip-audit commands

Refs #51" -- scripts/run_python_fixture_lens.py
```

---

### Task 4: The re-transcription reading pass

**Files:**
- Modify: `scripts/run_python_fixture_lens.py` (only where the pass finds drift)

**Interfaces:**
- Consumes: the two entries Task 3 repaired.
- Produces: an `INVOCATIONS` table re-verified against all 26 records, and a written list of what the pass found.

Issue #51's first acceptance criterion requires re-verifying by reading the records rather than the previous transcription. Reading the table first and looking for records that disagree is how the drift survived: the table is persuasive, and a reader who starts there confirms it. So read each record's prescribing paragraph first, write down what it prescribes, and only then compare.

- [ ] **Step 1: List the entries to read**

Run:

```bash
caffeinate uv run python -c "
import importlib.util, sys
sys.path.insert(0, 'scripts')
spec = importlib.util.spec_from_file_location('lens', 'scripts/run_python_fixture_lens.py')
m = importlib.util.module_from_spec(spec); sys.modules['lens'] = m; spec.loader.exec_module(m)
for i in m.INVOCATIONS:
    print(f'{i.check}\t{i.tool}\t{i.argv or i.argv_by_partition}')
"
```

Expected: one line per invocation. Record the count printed; it is the number of entries this pass must cover.

- [ ] **Step 2: Read each record's prescribing paragraph**

For each `(check, tool)`, open `.agents/skills/<domain>-audit/checks/<slug>.md`, find the paragraph containing that entry's `record_quote`, and write down every command form it names for that tool - before looking at the table's argv. Note any case where the paragraph prescribes something the argv does not carry, or carries something the paragraph does not prescribe.

- [ ] **Step 3: Repair what the pass found**

For each disagreement, correct the transcription to match the record. Where the record's prescription cannot be transcribed because it names a flag to append rather than a whole command - the shape Task 3 removed from `arch/cycles` - fix the record in its own prompt commit first, using Task 3 Step 3's message shape, then transcribe.

- [ ] **Step 4: Write down what the pass found**

Append to the task's report file a list of every entry the pass changed and every entry it confirmed unchanged. A pass that reports only what it changed cannot be distinguished from a pass that stopped early.

- [ ] **Step 5: Run the full gate and commit**

```bash
caffeinate bash -c 'uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check .'
git add scripts/run_python_fixture_lens.py
git commit -m "fix: re-verify every transcription against its record

Refs #51" -- scripts/run_python_fixture_lens.py
```

If the pass found nothing beyond Task 3's two entries, make no commit and say so in the report. An empty commit would claim work that did not happen.

---

### Task 4b: Records that name a flag but never a command, and a route that names its own runner

**Runs between Task 4 and Task 5.** Task 4 measured that the flag property fails on three pairs that no mechanical rule can fix, because two records name a tool and its flags without ever writing a whole command. That is the same unanchorable shape the round already removed from `arch/cycles`, in a third form. This task removes it at the source and settles the runner question Task 4 escalated.

**Files:**
- Modify: `.agents/skills/deps-audit/checks/licenses.md`
- Modify: `.agents/skills/test-audit/checks/determinism.md`
- Modify: `.agents/skills/deps-audit/checks/inventory.md` only if the promotion in Step 3 needs the record to say something it does not already say
- Modify: `scripts/run_python_fixture_lens.py`
- Test: `tests/scripts/test_python_fixture_harness.py`

**Interfaces:**
- Consumes: nothing from Task 4 beyond its repaired table.
- Produces: `Invocation.own_runner: tuple[str, ...]`, naming the partitions whose prescribed argv is complete as written and must take no launcher prefix; and `deps/inventory`'s `uv` row moved from `supplied_by_partition` into `argv_by_partition`.

Each record edit is a prompt change and takes its own commit stating WHY. The harness change is a separate commit.

- [ ] **Step 1: Give `deps/licenses` a whole command, and stop it claiming SPDX**

The record writes "`pip-licenses` (with `--format` for SPDX-ish output)". Two defects in one clause. The tool name appears bare, so no command form is extractable and the flag has nothing to sit inside. And the SPDX claim is false: `pip-licenses`'s own `--format` selects presentation only, and no style it offers emits SPDX. Verify that yourself against `pip-licenses --help` before you write the replacement, and quote what you saw in your report.

Rewrite the clause so it names a whole command including the format flag as the tool actually spells it, and so it says what `--format` really does. Do not claim an SPDX route exists. If a real SPDX generator is needed for this check, that is a separate finding for your report, not something to invent here.

- [ ] **Step 2: Give `test/determinism` a command that carries its seed flag**

The record prescribes running the suite in randomized order, names `pytest-randomly` as the plugin, and writes `--randomly-seed=<n>` for reproducing a failing order - but never names the runner, which is why this entry is one of the three standing exceptions in the anchor guard. Name the whole command so the seed flag sits inside it.

This changes what the anchor-guard exception set must contain. `tests/scripts/test_python_fixture_harness.py` asserts that set is exactly exercised - "an exception nothing exercises is a stale exception" - so if this entry stops needing its exception, remove it from the set rather than leaving it. Do the same check for `pytest-rerunfailures`, which shares the paragraph.

- [ ] **Step 3: Let a prescribed route name its own runner**

`deps/inventory`'s uv route is currently a supplied route rather than a transcription, for a mechanical reason Task 4's review verified: `TOOL_PACKAGES["cyclonedx-py"]` is `("cyclonedx-bom",)`, so `launcher` would put `uvx --from cyclonedx-bom` in front of the record's `uv export --format=cyclonedx1.5 --frozen`, fetching a package the command never calls. The record does name that command, so calling it "supplied" understates what the record prescribes.

Add a field to `Invocation`:

```python
    own_runner: tuple[str, ...] = ()
```

naming the partitions whose prescribed argv is complete as written. Where a partition is named there, `launcher` contributes no prefix and the argv runs as transcribed. Validate in `__post_init__`, beside the existing `_check_supplied`: a partition in `own_runner` must have a prescribed argv for that partition, and must not also carry a supplied route - otherwise the field would silently apply to nothing, or to two routes at once.

Document on the field WHY it exists: a record may prescribe a command whose first word is a runner or a different tool entirely, and the launcher's fetch is keyed on the check's tool name rather than on the command, so without this the harness either fetches a package the command never calls or the route has to be demoted to prose.

Then move `deps/inventory`'s `uv` row out of `supplied_by_partition` into `argv_by_partition`, name `uv` in `own_runner`, and delete the part of `supplied_note` that said the record named no such command. Keep whatever the note says that is still true.

- [ ] **Step 4: Prove the promoted route runs the same command**

The point of the promotion is provenance, not behaviour. Show that the command executed for `deps/inventory` on the `uv` partition is the same before and after, by printing what the harness builds:

```bash
caffeinate uv run python -c "
import importlib.util, sys
sys.path.insert(0, 'scripts')
spec = importlib.util.spec_from_file_location('lens', 'scripts/run_python_fixture_lens.py')
m = importlib.util.module_from_spec(spec); sys.modules['lens'] = m; spec.loader.exec_module(m)
for i in m.INVOCATIONS:
    if i.check == 'deps/inventory':
        print(i.tool, '|argv=', i.argv or i.argv_by_partition, '|own_runner=', i.own_runner, '|supplied=', i.supplied_by_partition)
"
```

If the executed command changes, say so in the report rather than adjusting it to match: a promotion that alters what runs is a new measurement, not a re-labelling, and the published record would then be describing a command nothing observed.

- [ ] **Step 5: Add unit tests**

Cover the new validation both ways - a partition named in `own_runner` with no prescribed argv, and one carrying both a prescribed and a supplied route - and cover that `launcher` contributes no prefix for a partition named in `own_runner` while still prefixing one that is not.

- [ ] **Step 6: Run the full gate and commit**

Three or four commits: one per record edited, each stating WHY, then the harness change with its tests.

```bash
caffeinate bash -c 'uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check . && uv run python scripts/render_python_fixture_expectations.py --check'
```

---

### Task 5: Populate `forms` and turn on the declaration property

**Files:**
- Modify: `scripts/run_python_fixture_lens.py` (every entry in `INVOCATIONS`)
- Modify: `tests/scripts/test_python_fixture_harness.py`

**Interfaces:**
- Consumes: `DISPOSITIONS` and `Invocation.forms` from Task 1; `_command_forms`, `_prescribing_paragraph` from Task 2.
- Produces: a populated `forms` on every entry, and `test_every_command_form_the_record_names_is_declared`.

- [ ] **Step 1: Compute what each entry must declare**

Run:

```bash
caffeinate uv run python -c "
import importlib.util, re, sys, pathlib
sys.path.insert(0, 'scripts')
spec = importlib.util.spec_from_file_location('lens', 'scripts/run_python_fixture_lens.py')
m = importlib.util.module_from_spec(spec); sys.modules['lens'] = m; spec.loader.exec_module(m)
skills = pathlib.Path('.agents/skills')
for i in m.INVOCATIONS:
    domain, slug = i.check.split('/')
    text = (skills / f'{domain}-audit' / 'checks' / f'{slug}.md').read_text()
    line = [l for l in text.splitlines() if i.record_quote in l]
    if len(line) != 1:
        print(f'{i.check}\t{i.tool}\tQUOTE IN {len(line)} LINES')
        continue
    spans = list(dict.fromkeys(re.findall(r'\`([^\`]+)\`', line[0])))
    forms = sorted({s for s in spans if len(s.split()) > 1 and s.split()[0] == i.tool})
    print(f'{i.check}\t{i.tool}\t{forms}')
"
```

Expected: one line per invocation with the forms it must declare. Any `QUOTE IN 0 LINES` or `QUOTE IN 2 LINES` line is a defect to fix before continuing, not a case to skip.

- [ ] **Step 2: Write the failing test**

```python
def test_every_command_form_the_record_names_is_declared():
    """The record-to-harness direction the three older guards do not run.

    Those guards hold the transcription against the record, so a record that
    *grows* a prescription leaves all three green. This one fails instead,
    naming the span nothing declares.
    """
    for inv in INVOCATIONS:
        paragraph = _prescribing_paragraph(inv.check, inv.record_quote)
        assert _command_forms(paragraph, inv.tool) == {f for f, _ in inv.forms}, (
            inv.check,
            inv.tool,
        )
```

- [ ] **Step 3: Run it to verify it fails**

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -k form_the_record_names -v`
Expected: FAIL on the first entry, whose declared set is empty.

- [ ] **Step 4: Populate every entry**

Add `forms=(...)` to each entry in `INVOCATIONS`, using Step 1's output for the form strings and reading the record for the disposition. Decide each disposition by what the paragraph says about that form, not by whether the harness happens to run it:

- `runs` - this is the form the harness executes on at least one partition
- `alternative` - a form for a partition shape these five fixtures do not have
- `superseded` - a form the record names and then narrows, such as `pip-audit -r <requirements>` before the `--no-deps` pair
- `forbidden` - a form the record names in order to warn against

An entry whose paragraph names no form for its tool declares `forms=()`; that is a fact about the record, in the same way an empty `argv` already is.

- [ ] **Step 5: Run the test to verify it passes**

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q`
Expected: PASS.

- [ ] **Step 6: Run the full gate and commit**

```bash
caffeinate bash -c 'uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check .'
git add scripts/run_python_fixture_lens.py tests/scripts/test_python_fixture_harness.py
git commit -m "feat: hold every declared form against the record that names it

Refs #51" -- scripts/run_python_fixture_lens.py tests/scripts/test_python_fixture_harness.py
```

---

### Task 6: The three remaining properties

**Files:**
- Modify: `tests/scripts/test_python_fixture_harness.py`

**Interfaces:**
- Consumes: everything from Tasks 1, 2 and 5.
- Produces: the flag property, the coverage property, the vocabulary property and the containment property.

- [ ] **Step 0: Extract by the command's own lead word, not by the tool's name, and drop the dead disposition**

Task 5 populated the declarations and measured two things this task has to act on before any property is written.

**Eleven entries declare no form while their record prescribes a command.** Seven of those are correct: their record names the tool bare, and a bare name is a mention rather than a form. The other four are blind spots, and they are blind because `_command_forms` keys on the tool's name while the record names a command led by something else. Measured, with the forms each one currently hides:

| Entry | `argv[0]` | The form the tool-name rule cannot see |
|---|---|---|
| `test/coverage-reach` + `pytest-cov` | `pytest` | `pytest --cov=<pkg> --cov-branch --cov-report=term-missing` |
| `test/coverage-reach` + `coverage.py` | `coverage` | `coverage run -m pytest` and `coverage report --show-missing` |
| `test/determinism` + `pytest-randomly` | `pytest` | `pytest --randomly-seed=<n>` |
| `test/isolation` + `pytest-timeout` | `pytest` | `pytest --durations=25` |

Change the lead word from the tool's name to **the first token of the entry's own transcribed argv, falling back to the tool's name where the entry prescribes no command**. This keeps the guard anchored to one specific word, so it cannot misattribute `uv pip list --outdated` to the `pip` entry the way an anywhere-in-the-span rule would: that entry's argv leads with `pip`. Add a helper beside the others in the test module:

```python
def _lead_words(inv) -> set[str]:
    """The words a form for this entry may lead with.

    The tool's name is the obvious one and it is not enough: a record names the
    command it wants run, and that command's first word is often a runner rather
    than the tool being checked - `pytest --randomly-seed=<n>` for
    `pytest-randomly`, `coverage run -m pytest` for `coverage.py`. Keyed on the
    tool's name alone, the extractor returns nothing for those and an empty
    declaration then passes as though the record prescribed nothing at all.
    Keyed on the argv's own first token, it stays anchored to one word, so it
    still cannot pull a neighbour's command in: `deps/freshness` prescribes both
    `uv pip list --outdated` and `pip list --outdated`, and the `pip` entry's
    argv leads with `pip`.
    """
    argvs = [a for a in [inv.argv, *(a for _, a in inv.argv_by_partition)] if a]
    return {a[0] for a in argvs} | {inv.tool}
```

Extract with every lead word, declare the forms the four entries were hiding, and give each a disposition by reading the record as Task 5 did. Note that `coverage report --show-missing` is the entry's `then` command rather than its `argv`, so the coverage property in Step 2 must look at `then` as well as `argv` or it will call a `runs` form uncarried.

**`forbidden` has no user and structurally cannot get one.** The only command any record names in order to warn against is a bare `pip-audit`, which the mention rule excludes by design. Delete `forbidden` from `DISPOSITIONS`. This is the vocabulary property in Step 3 doing its job in advance: a value nothing uses is ceremony that reads as coverage. While there, remove the `# noqa: F401` from the `DISPOSITIONS` import in the test module, which Step 3 makes a real use.

- [ ] **Step 1: Write the flag property**

Two things this property must get right, both measured over all 50 invocations rather than reasoned about. **The flags pool across the paragraph, not the tool.** One paragraph can prescribe for several tools - `deps/freshness` carries a `uv` invocation and a `pip` one sharing a single quote - so a flag belonging to the neighbour's command is still accounted for. Checking each tool against only its own forms fails on 12 (entry, flag) pairs; pooling across the paragraph's invocations cuts that to 5. **And a placeholder token can never appear in a form's tokens the way the record writes it**, so `_concrete` applies to the flag as well: that cuts 5 to 3.

```python
def test_every_flag_the_record_names_occurs_in_a_declared_form():
    """A flag in no declared form is a prescription nothing transcribed.

    This is the shape `arch/cycles` drifted in: the record grew "Append
    `--show-dot` to that `pydeps` invocation" in a later sentence of the same
    paragraph, and the flag belongs to a command the sentence does not repeat.

    Pooled across every invocation sharing the paragraph, because one paragraph
    prescribes for several tools: `deps/freshness` writes `uv pip list
    --outdated --python <path>` and `pip list --outdated` in one sentence, and
    `--python` belongs to the first. Held against one tool's own forms it fails
    on a dozen pairs that are not drift at all.
    """
    for inv in INVOCATIONS:
        paragraph = _prescribing_paragraph(inv.check, inv.record_quote)
        pooled = _tokens(
            " ".join(
                form
                for other in INVOCATIONS
                if other.check == inv.check
                for form, _ in other.forms
            )
        )
        for flag in _flag_spans(paragraph):
            assert all(t in pooled for t in _concrete(_tokens(flag))), (
                inv.check,
                inv.tool,
                flag,
            )
```

The remaining 3 are not mechanical and Task 4b removes them at the source: they are records naming a tool and its flags without ever writing a whole command. If this property still fails after Task 4b, the failing pair is a record with that same shape and the repair is the record, not the test.

- [ ] **Step 2: Write the coverage property**

```python
def test_every_form_the_harness_runs_appears_in_an_argv():
    """The half that catches `deps/vulnerabilities`.

    Its placeholder put it in the anchor guard's `unanchored` set, so the guard
    that would have noticed a flag pair being added to the prescribed form was
    switched off for exactly that entry. Dropping the placeholder token instead
    of excusing the entry is what lets this one watch it.
    """
    for inv in INVOCATIONS:
        argvs = [a for a in [inv.argv, *(a for _, a in inv.argv_by_partition)] if a]
        for form, disposition in inv.forms:
            if disposition != "runs":
                continue
            wanted = _concrete(_tokens(form))
            assert any(
                _is_subsequence(wanted, _tokens(" ".join(argv))) for argv in argvs
            ), (inv.check, inv.tool, form)
```

- [ ] **Step 3: Write the vocabulary property**

```python
def test_every_disposition_in_the_vocabulary_is_used():
    """A value nothing uses is ceremony that reads as coverage."""
    assert {d for inv in INVOCATIONS for _, d in inv.forms} == set(DISPOSITIONS)
```

If this fails because a value has no user, delete that value from `DISPOSITIONS` rather than inventing an entry for it.

- [ ] **Step 4: Measure the containment property before writing it**

Run:

```bash
caffeinate uv run python -c "
import importlib.util, re, sys, pathlib
sys.path.insert(0, 'scripts')
spec = importlib.util.spec_from_file_location('lens', 'scripts/run_python_fixture_lens.py')
m = importlib.util.module_from_spec(spec); sys.modules['lens'] = m; spec.loader.exec_module(m)
skills = pathlib.Path('.agents/skills')
for i in m.INVOCATIONS:
    domain, slug = i.check.split('/')
    lines = (skills / f'{domain}-audit' / 'checks' / f'{slug}.md').read_text().splitlines()
    start = next((n for n, l in enumerate(lines) if l.startswith('## Tooling fallback')), None)
    if start is None:
        continue
    end = next((n for n in range(start + 1, len(lines)) if lines[n].startswith('## ')), len(lines))
    for line in lines[start + 1:end]:
        if i.record_quote in line or not line.strip():
            continue
        spans = re.findall(r'\`([^\`]+)\`', line)
        stray = sorted({s for s in spans if len(s.split()) > 1 and s.split()[0] == i.tool})
        if stray:
            print(f'{i.check}\t{i.tool}\t{stray}')
"
```

Expected: this prints the cases where a tool's command form appears in the fallback section outside the quoted paragraph. If it prints nothing, the property holds clean. If it prints rows, each is either real drift to repair or a legitimate mention in another language's paragraph, which becomes a named exception carrying the same "an exception nothing exercises is a stale exception" assertion the `unanchored` set already uses.

- [ ] **Step 5: Write the containment property**

Write it to match what Step 4 measured, with the exception set - if any - written as a literal beside the assertion, and the stale-exception check at the end:

```python
def test_a_prescription_stays_in_the_paragraph_the_guard_watches():
    """Otherwise the blind spot moves up one level.

    Every property here is scoped to the paragraph holding `record_quote`. A
    correction that appends a whole new paragraph instead of a sentence lands
    outside all of them, which is this same defect one level up.
    """
    ...
```

- [ ] **Step 6: Recompute the completion count**

Run:

```bash
caffeinate uv run python -c "
import importlib.util, sys
sys.path.insert(0, 'scripts')
spec = importlib.util.spec_from_file_location('lens', 'scripts/run_python_fixture_lens.py')
m = importlib.util.module_from_spec(spec); sys.modules['lens'] = m; spec.loader.exec_module(m)
print('with completion:', len([i for i in m.INVOCATIONS if i.completion]))
"
```

If this differs from the number pinned in `test_folding_a_completion_into_the_argv_breaks_the_anchor`, update the pin to the computed value and say in the commit message which entry moved and why.

- [ ] **Step 7: Write the accounted-for property**

`_command_forms` recognises a form only where the tool's own name leads the span, so a record prescribing `uvx pydeps --show-cycles` yields no form at all, `forms=()` satisfies the declaration property, and the guard is blind to the prescription. Loosening the match is the wrong repair: a span naming the tool anywhere would attribute `uv pip list --outdated` to the **`pip`** invocation on `deps/freshness`, whose paragraph carries a `uv` invocation and a `pip` one sharing one quote, so the `pip` entry would have to declare a form it does not run. Make the blindness loud instead.

```python
def test_a_form_naming_the_tool_off_the_front_is_led_by_some_invocation():
    """A prescription the leading-name rule cannot see must not vanish.

    `deps/freshness` writes `uv pip list --outdated` in the paragraph its `pip`
    entry also quotes, and that span is the `uv` entry's form rather than the
    `pip` entry's. What must never happen is a span naming a tool that no
    invocation on that paragraph leads: `uvx pydeps --show-cycles` would be a
    prescription with no declaration and no failure.
    """
    for inv in INVOCATIONS:
        paragraph = _prescribing_paragraph(inv.check, inv.record_quote)
        led = {
            form.split()[0]
            for other in INVOCATIONS
            if other.check == inv.check
            for lead in _lead_words(other)
            for form in _command_forms(paragraph, lead)
        }
        for span in _spans(paragraph):
            words = span.split()
            if len(words) > 1 and inv.tool in words[1:]:
                assert words[0] in led, (inv.check, inv.tool, span)
```

Run it. If it fails on a record other than through the `deps/freshness` case described above, that record is hiding a prescription behind a runner prefix and the finding goes in the report rather than being silenced by widening the test.

- [ ] **Step 8: Run the full gate and commit**

```bash
caffeinate bash -c 'uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check .'
git add tests/scripts/test_python_fixture_harness.py scripts/run_python_fixture_lens.py
git commit -m "test: fail when a record prescribes what the harness does not run

Refs #51" -- tests/scripts/test_python_fixture_harness.py scripts/run_python_fixture_lens.py
```

---

### Task 7: The prose the corrections falsified

**Files:**
- Modify: `scripts/run_python_fixture_lens.py` (`inner_uv_target`'s docstring, at line 1217)
- Modify: `.agents/skills/deps-audit/checks/vulnerabilities.md`

**Interfaces:**
- Consumes: the transcriptions from Tasks 3 and 4.
- Produces: no code changes, only prose that matches what the records now claim.

- [ ] **Step 1: Superseded - do not do it**

This step planned to reword `inner_uv_target`'s docstring. Task 4 found that the function was the drift: `deps/freshness` had prescribed `--python <path-to-venv-python>` since the records were reworded, and the harness was appending the flag at runtime through that helper, where no argv-reading guard could see it. Transcribing the flag properly left the helper with nothing to do and it was deleted. There is no docstring left to fix. Confirm `grep -c inner_uv_target scripts/run_python_fixture_lens.py` prints 0 and move to Step 2.

- [ ] **Step 1b: Clear the three prose defects Task 4's review left**

In `scripts/python_fixture_spec.py`, the new sentence about the uv SBOM route writes `uv export --format cyclonedx1.5 --frozen` with a space where `.agents/skills/deps-audit/checks/inventory.md` writes `--format=cyclonedx1.5`. uv accepts both and no gate compares them, which is exactly why it matters: that sentence's whole job is to state what the record names, in a round that exists because prose drifted from records. Match the record's token, then re-render with `uv run python scripts/render_python_fixture_expectations.py`.

In `scripts/run_python_fixture_lens.py`, the `supplied_by_partition` docstring has a dangling one-word line from an earlier insert; reflow that paragraph. The same docstring names `deps/inventory`'s `uv` row as its example, which the project's stale-prose rule warns against - the fact already lives in that row's own `supplied_note`, where it stays true, so drop the sibling reference and state the structural reason instead.

- [ ] **Step 2: State the provenance in `deps/vulnerabilities`**

The record now prescribes `pip-audit -r <requirements> --no-deps --disable-pip`, and the lens run's published observation for that entry was taken with the older form. Add one sentence to the `**Python** - ` paragraph saying so, in the record's own voice: what the published observation used, and that the flags are unexercised here rather than tested and found wanting. Do not narrate the correction's history - state what is true of the current evidence.

- [ ] **Step 3: Run the gate and commit, prose separately**

```bash
caffeinate bash -c 'uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check .'
git add .agents/skills/deps-audit/checks/vulnerabilities.md
git commit -F - -- .agents/skills/deps-audit/checks/vulnerabilities.md <<'EOF'
prompt: say which pip-audit form the published observation used

The record prescribes the `--no-deps --disable-pip` pair; the observation
published for this entry was taken with the older form, and this host cannot
run either - `ensurepip` aborts with SIGABRT. Without the sentence the record
reads as though the prescribed flags had been exercised.

Refs #51
EOF
git add scripts/run_python_fixture_lens.py
git commit -m "docs: --python is a record claim now, not harness plumbing

Refs #51" -- scripts/run_python_fixture_lens.py
```

---

### Task 8: Re-run `arch/cycles` and publish it

**Files:**
- Modify: `scripts/run_python_fixture_lens.py` (`run_partition` at line 1756, `main` at line 1891)
- Modify: `.agents/skills/arch-audit/checks/cycles.md`
- Modify: `docs/audit/python-lens-smoke-run.md`
- Test: `tests/scripts/test_python_fixture_harness.py`

**Interfaces:**
- Consumes: the re-transcribed `arch/cycles` entry from Task 3.
- Produces: a `--check` filter on the harness, and a published observation for `arch/cycles` carrying its own date and tool versions.

`arch/cycles` runs on the `uv` partition only, and `pydeps` carries the `resolved-tree` tier, so the re-run is one cell: `uv`, `target-execution`.

- [ ] **Step 1: Write the failing test for the filter**

```python
def test_a_filtered_run_names_only_the_check_it_was_given():
    assert [i.check for i in invocations_for("uv", only_check="arch/cycles")] == [
        "arch/cycles"
    ] * len([i for i in INVOCATIONS if i.check == "arch/cycles"])


def test_an_unknown_check_filter_is_refused():
    with pytest.raises(ValueError, match="no invocation"):
        invocations_for("uv", only_check="arch/nonexistent")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -k filtered_run -v`
Expected: FAIL with `TypeError: invocations_for() got an unexpected keyword argument`.

- [ ] **Step 3: Add the filter**

Give `invocations_for` an `only_check: str | None = None` keyword; when set, return only that check's invocations and raise `ValueError` naming the check when none match. Thread it through `run_partition` as a keyword and add the `--check` argument to `main`:

```python
    parser.add_argument(
        "--check",
        default=None,
        help="run only this check id; the output file gains its slug, so a "
        "partial run cannot overwrite a full matrix artifact",
    )
```

When `--check` is given, the output path becomes `f"{args.partition}-{args.grant}-{slug}.json"` where `slug` is the check id with `/` replaced by `-`. A partial run must never write the filename a full run writes: the grader reads those files, and a partial artifact under a full run's name would report 1 row where the record claims the matrix.

- [ ] **Step 4: Run the tests and the gate**

Run: `caffeinate bash -c 'uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check .'`
Expected: all pass.

- [ ] **Step 5: Build the fixture and re-run the cell**

```bash
caffeinate uv run python scripts/build_python_fixtures.py --all
caffeinate uv run python scripts/run_python_fixture_lens.py uv --grant target-execution --check arch/cycles
```

Confirm `git -C fixtures/python/uv status --porcelain` is empty before and after. Never edit anything under `fixtures/python/`.

- [ ] **Step 6: Read what came back**

Read the written JSON. The `pydeps` row must carry a non-empty stdout containing both directed edges of the seeded cycle. If it does not, that is the finding: record it rather than adjusting the command until it produces one.

- [ ] **Step 7: Publish it**

In `docs/audit/python-lens-smoke-run.md`, add the re-run's observation with **its own date and the tool versions the re-run probed**, not folded into the 2026-08-14 rows. `uvx` resolves the latest release at run time, so a re-run can see a different `pydeps` than the original round did, and one date over two measurements would claim a run that did not happen.

- [ ] **Step 8: Fix the sentence the re-run falsified**

`.agents/skills/arch-audit/checks/cycles.md` currently says the `--show-dot` behaviour was "measured in a scratch copy carrying a real two-module cycle, not as an artifact of the python lens smoke run, whose own results show only the bare `--show-cycles` form". Both halves are false once Step 7 publishes. Rewrite to describe the current evidence, citing the fixture partition that produced it.

- [ ] **Step 9: Run the full gate and commit**

```bash
caffeinate bash -c 'uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check . && uv run python scripts/render_handbook_traceability.py --check && uv run python scripts/render_python_fixture_expectations.py --check'
git add scripts/run_python_fixture_lens.py tests/scripts/test_python_fixture_harness.py
git commit -m "feat: let the harness run one check without clobbering the matrix

Refs #51" -- scripts/run_python_fixture_lens.py tests/scripts/test_python_fixture_harness.py
git add .agents/skills/arch-audit/checks/cycles.md
git commit -F - -- .agents/skills/arch-audit/checks/cycles.md <<'EOF'
prompt: cite the lens run for the --show-dot measurement

The record said the dot output was measured in a scratch copy and not by the
lens run, whose results showed only the bare form. The re-run of arch/cycles
under the corrected command makes both halves false.

Refs #51
EOF
git add docs/audit/python-lens-smoke-run.md
git commit -m "docs: publish the arch/cycles re-run under its own date

Refs #51" -- docs/audit/python-lens-smoke-run.md
```

---

## Self-review

**Spec coverage.** Every spec section maps to a task: the defect analysis informs Tasks 3 and 5; extraction is Task 2; dispositions are Tasks 1 and 5; the four properties are Tasks 5 and 6; the reword is Task 3; the re-transcription pass is Task 4; the scoped re-run and both of its consequences are Tasks 7 and 8; the two smaller items are Tasks 6 Step 6 and 7. The spec's six acceptance criteria are covered by Tasks 4, 6, 3, 7, 8 and 8 respectively.

**Placeholders.** The one `...` in the plan is Task 6 Step 5's containment property, and it is deliberate: its exception set cannot be written before Step 4 measures whether any exception is needed, and inventing one here would put a stale exception in the code on the day it lands.

**Naming.** `DISPOSITIONS`, `Invocation.forms`, `_spans`, `_command_forms`, `_flag_spans`, `_concrete`, `_prescribing_paragraph` and `only_check` are used with the same spelling in every task that references them.

**Counts.** The plan states 26 records, 484 tests at its start and one re-run cell. Every other number is computed by a step rather than asserted here - the completion pin in Task 6 Step 6 and the invocation total in Task 4 Step 1 especially, because both moved during the round that produced this drift.
