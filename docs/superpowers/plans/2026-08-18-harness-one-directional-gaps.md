# Harness One-Directional Gaps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the three ways a token can move across the harness's prescribed/supplied line while the whole suite stays green, and correct the prose that documents those ways as open.

**Architecture:** Four new properties in `tests/scripts/test_python_fixture_harness.py`, each with a small named helper and a unit test built on a synthetic `Invocation`. Nothing about the harness's behaviour changes: `scripts/run_python_fixture_lens.py` takes docstring corrections only, and no check record is edited.

**Tech Stack:** Python 3, pytest, `uv` for running everything. No new dependencies.

## Global Constraints

- Run every command through `uv run`. The suite is `uv run pytest tests/ -q`.
- `uv run ruff check .` and `uv run ruff format --check .` must both pass before any commit. CI runs both.
- Reference the issue in every commit message: `Refs #55`.
- Never `git add -A`, `git add .`, or `git commit -a`. Commit with an explicit pathspec: `git commit -F - -- <paths>`.
- Never write into `fixtures/python/<partition>`. Those trees are seeded audit targets and their contents are ground truth.
- Never commit environment-specific values: absolute personal paths, hostnames, emails, profile names.
- Never assert a count you did not compute. Compute it in the same breath, or state no number.
- Markdown is never hard-wrapped: one paragraph is one source line. Never reflow lines you did not change.
- No em-dash (U+2014) anywhere under `docs/`. Use ` - `.
- Prose about the code states the structural reason rather than the current snapshot, and names a thing rather than numbering it: "the `checks` argument", not "the fourth argument".
- An exception set takes this file's existing idiom: the property **asserts** each named entry still needs its exception, so an entry that stops needing one fails the suite rather than carrying it forever. `test_a_transcribed_command_occurs_in_the_sentence_that_prescribes_it`'s `unanchored` set is the model to copy, including its closing `assert seen == <set>` line.
- Every new property passes on the tree as it stands. That is expected and is not evidence the property works: the tree satisfies all four today, which is why each task carries both a unit test on a synthetic `Invocation` (red before the helper exists, green after) and a mutation step (green tree, red under the mutation the property exists to catch).
- Revert every mutation before committing, and confirm `git status --short` is empty of it.

---

## File Structure

- `tests/scripts/test_python_fixture_harness.py` - every new helper, property and unit test. Helpers go beside the existing extractor helpers, above the `# --- the extractor helpers ---` divider's properties; properties go in the section named in each task.
- `scripts/run_python_fixture_lens.py` - docstring corrections to `Invocation.forms` and `Invocation.then` only. No behaviour change, no new field, no changed field.
- No file is created. No check record under `.agents/skills/` is touched.

---

### Task 1: `argv` is maximal against the quote

**Files:**
- Modify: `tests/scripts/test_python_fixture_harness.py`

**Interfaces:**
- Consumes: `_tokens(text: str) -> list[str]`, `INVOCATIONS`, `Invocation` - all already imported in the file.
- Produces: `_demoted_tokens(inv: Invocation) -> list[str]`, used by nothing else in this plan.

- [ ] **Step 1: Write the unit tests**

Add these two tests immediately after `test_the_watched_paragraphs_are_the_python_side_of_the_section`, before the `def test_every_python_tool_in_the_family_is_invoked():` line:

```python
def test_a_token_the_record_writes_concretely_is_not_a_completion():
    """The demotion this file had no guard against.

    `arch/cycles` prescribes `pydeps --show-cycles --show-dot` and the record
    bolds `--show-dot`. Moved out of the argv and into the completion the run
    stays correct, the shorter argv still traces through the quote, and the
    round reports that the record failed to prescribe a flag the record
    prescribes. Built here rather than asserted about the tree, because no entry
    in the tree carries the demotion, so the tree cannot distinguish a rule that
    catches it from one that does not.
    """
    quote = (
        "Run `pydeps --show-cycles --show-dot`: `--show-cycles` alone has no "
        "textual output channel at all."
    )
    honest = Invocation(
        check="arch/cycles",
        tool="pydeps",
        argv=("pydeps", "--show-cycles", "--show-dot"),
        completion=("src/fixture_app",),
        note="pydeps takes the package to graph and the record names none",
        record_quote=quote,
    )
    demoted = Invocation(
        check="arch/cycles",
        tool="pydeps",
        argv=("pydeps", "--show-cycles"),
        completion=("--show-dot", "src/fixture_app"),
        note="pydeps takes the package to graph and the record names none",
        record_quote=quote,
    )
    assert _demoted_tokens(honest) == []
    assert _demoted_tokens(demoted) == ["--show-dot"]


def test_a_placeholder_the_record_leaves_open_is_a_legitimate_completion():
    """The shape the rule must not fire on, and why the quote stays raw.

    Filling a placeholder is what a completion is for: the record writes
    `--cov=<pkg>` and the caller supplies the package. The two are never equal,
    so comparing the completion against the quote's own tokens leaves the
    legitimate shape alone. Reducing the quote with `_concrete` first is what
    would break it - `--cov=<pkg>` becomes the marked `--cov=<`, which
    `_matches` satisfies with any `--cov=` token, so the canonical completion
    would read as a demoted prescription.
    """
    inv = Invocation(
        check="test/coverage-reach",
        tool="pytest-cov",
        argv=("pytest", "--cov-branch", "--cov-report=term-missing"),
        completion=("--cov=fixture_app",),
        note="`<pkg>` is a placeholder the record leaves to the caller",
        record_quote=(
            "`pytest --cov=<pkg> --cov-branch --cov-report=term-missing` (or "
            "`coverage run -m pytest` + `coverage report --show-missing`)."
        ),
    )
    assert _demoted_tokens(inv) == []
    marked = _concrete(_tokens(inv.record_quote))
    assert any(_matches(w, "--cov=fixture_app") for w in marked)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q -k "writes_concretely or leaves_open"`

Expected: FAIL, `NameError: name '_demoted_tokens' is not defined`.

- [ ] **Step 3: Write the helper**

Add it directly after `_unaccounted_flags`, before the `# --- the extractor helpers ---` divider line:

```python
def _demoted_tokens(inv: Invocation) -> list[str]:
    """The completion tokens the record's own sentence writes concretely.

    A token the record writes in full is a token the record prescribes, so it
    belongs in `argv`. Sitting in `completion` instead it inverts the round's
    output: the results report a record that failed to prescribe a flag the
    record prescribes, and since the deliverable is the list of records needing
    correction, that is the output falsified while the executed command stays
    byte-identical.

    Compared against the quote's raw tokens rather than `_concrete`'s reduction
    of them, which is what leaves a placeholder fill alone. The record writes
    `--cov=<pkg>` and the completion supplies `--cov=fixture_app`; those are
    never equal, so the canonical completion cannot hit this. Reduce the quote
    first and `--cov=<pkg>` becomes the marked `--cov=<`, which `_matches`
    satisfies with any `--cov=` token, and the one shape a completion exists for
    reads as a demotion.

    Equality is the whole comparison because a record's own tokens are never
    marked: the placeholder a record writes closes with `>`, and only
    `_concrete` leaves the trailing `<` that turns a token into a prefix.
    """
    quote = _tokens(inv.record_quote)
    return [token for token in inv.completion if token in quote]
```

- [ ] **Step 4: Run the unit tests to verify they pass**

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q -k "writes_concretely or leaves_open"`

Expected: 2 passed.

- [ ] **Step 5: Write the property over the tree**

Add it immediately after `test_folding_a_completion_into_the_argv_breaks_the_anchor`, before `def test_an_invocation_names_a_check_that_exists_and_a_partition_that_does():`:

```python
def test_a_token_the_record_prescribes_never_hides_in_the_completion():
    """The direction the folding guard above does not run.

    That one holds that a completion has not been folded into `argv`. This one
    holds the opposite move, which leaves every other property in this file
    green: a token the record writes concretely, sitting in `completion` as
    though the record had omitted it.

    One entry genuinely cannot satisfy it, and the reason is structural rather
    than a judgement. `docs/docstring-coverage` runs `ruff check --select D`
    against a record naming ruff's `D` rules, so `D` is prescribed - but a
    completion is *appended*, and putting `D` in the argv would need `check
    --select` inserted between `ruff` and it. The exception is asserted rather
    than merely allowed, so a record that grows a real command line fails here
    instead of carrying a dead exception.

    The rule fails safe in the direction it does not guard. A future completion
    token colliding with a word of its own quote's prose fails loudly and gets
    named or corrected; nothing about that direction passes in silence.
    """
    demoted = {
        # `ruff check --select D` against "`ruff` `D` rules": `D` is prescribed
        # and cannot reach the argv, because `check --select` would have to be
        # inserted rather than appended.
        ("docs/docstring-coverage", "ruff"),
    }
    seen = set()
    for inv in INVOCATIONS:
        hits = _demoted_tokens(inv)
        if (inv.check, inv.tool) in demoted:
            assert hits, (inv.check, inv.tool)
            seen.add((inv.check, inv.tool))
        else:
            assert not hits, (
                f"{inv.check}/{inv.tool}: {hits} sits in `completion` while the "
                "record's own sentence writes it, so the round reports a "
                "prescription the record makes as one it omitted"
            )
    assert seen == demoted, "an exception nothing exercises is a stale exception"
```

- [ ] **Step 6: Run the whole suite**

Run: `caffeinate uv run pytest tests/ -q`

Expected: PASS. Every test, including the new property, which the tree satisfies.

- [ ] **Step 7: Mutate to prove the property has teeth**

Edit `scripts/run_python_fixture_lens.py`: find the `arch/cycles` entry with `tool="pydeps"`, and move `"--show-dot"` out of its `argv` tuple into the front of its `completion` tuple. The two lines become:

```python
        argv=("pydeps", "--show-cycles"),
        completion=("--show-dot", f"src/{PACKAGE}"),
```

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q 2>&1 | tail -20`

Expected: FAIL, and the failure names `test_a_token_the_record_prescribes_never_hides_in_the_completion` with `['--show-dot']` in the message. Record how many tests failed and which.

- [ ] **Step 8: Revert the mutation**

Run: `git checkout -- scripts/run_python_fixture_lens.py && git status --short`

Expected: only `tests/scripts/test_python_fixture_harness.py` is modified.

Then run `caffeinate uv run pytest tests/ -q` again and confirm it is green.

- [ ] **Step 9: Correct the prose the property invalidated**

`test_folding_a_completion_into_the_argv_breaks_the_anchor`'s docstring opens its second paragraph with "One direction only, and the other has no guard anywhere." and closes with an instruction to read a `note` as an unverified claim. Both are now false as written. Replace that whole second paragraph, which begins `One direction only,` and ends `not as one this file has verified.`, with:

```
    The other direction is held by
    `test_a_token_the_record_prescribes_never_hides_in_the_completion` rather
    than here, and neither implies the other: this one holds that a completion
    has not been folded into `argv`, that one holds that a token the record
    writes concretely has not been moved the other way. The move that way was
    what left every property in this file green while inverting the published
    provenance - the shorter argv still traces through the quote, and the
    coverage property reads `argv_for`, which re-appends the completion before
    matching - so the round would report that a record failed to prescribe a
    flag the record bolds. A `note` claiming the record omitted a token the
    record writes concretely is now checked against the record's own sentence.
    One about a placeholder the record leaves to the caller is not, and stays a
    claim to read against the record rather than one this file has verified.
```

- [ ] **Step 10: Run the gates**

Run: `caffeinate uv run pytest tests/ -q && caffeinate uv run ruff check . && caffeinate uv run ruff format --check .`

Expected: all three clean.

- [ ] **Step 11: Commit**

```bash
git commit -F - -- tests/scripts/test_python_fixture_harness.py <<'EOF'
test: hold the argv maximal against the record's own sentence

The folding guard runs one direction: a completion may not hide inside
`argv`. Nothing held the reverse, so a token the record writes
concretely could sit in `completion` instead, leaving the executed
command byte-identical and every property green while the round
reported the record as having omitted a flag it prescribes.

The comparison is against the quote's raw tokens rather than
`_concrete`'s reduction of them, which is what leaves a placeholder fill
alone: `--cov=<pkg>` and `--cov=fixture_app` are never equal, while the
reduced `--cov=<` would match it and read the one shape a completion
exists for as a demotion.

Refs #55
EOF
```

---

### Task 2: A disposition cannot silence what the suite checks

**Files:**
- Modify: `tests/scripts/test_python_fixture_harness.py`
- Modify: `scripts/run_python_fixture_lens.py` (one docstring paragraph, no behaviour change)

**Interfaces:**
- Consumes: `_tokens`, `_concrete`, `_matches`, `PARTITIONS`, `INVOCATIONS`, `Invocation` - all already available in the file.
- Produces: `_prescribed_commands(inv: Invocation) -> list[tuple[str, tuple[str, ...]]]` returning `(label, command)` pairs where `label` is the first partition naming that command; and `_runs_as_written(command: tuple[str, ...], form: str) -> bool`. Task 3 consumes `_prescribed_commands`.

- [ ] **Step 1: Write the unit tests**

Add these three tests immediately after `test_a_placeholder_the_record_leaves_open_is_a_legitimate_completion` from Task 1:

```python
def test_a_shared_argv_is_one_command_rather_than_one_per_partition():
    """The label names the first partition carrying it, and the command is distinct.

    An entry with a shared `argv` prescribes one command, and `prescribed`
    answers with it for every partition. Listed once per partition instead, a
    failure message would name five identical commands and a reader would look
    for five routes.
    """
    shared = Invocation(
        check="deps/hygiene",
        tool="deptry",
        argv=("deptry",),
        completion=(".",),
        note="deptry takes the path to scan and the record names none",
        record_quote="Run `deptry` over the package to list unused declarations.",
    )
    assert _prescribed_commands(shared) == [("uv", ("deptry",))]
    split = Invocation(
        check="deps/inventory",
        tool="cyclonedx-py",
        argv_by_partition=(
            ("uv", ("cyclonedx-py", "environment")),
            ("pip", ("cyclonedx-py", "requirements")),
        ),
        record_quote="Run the subcommand matching the partition's own dependency file.",
    )
    assert _prescribed_commands(split) == [
        ("uv", ("cyclonedx-py", "environment")),
        ("pip", ("cyclonedx-py", "requirements")),
    ]


def test_a_command_carrying_a_form_is_not_the_same_as_running_it():
    """Containment cannot be the test, so equality is.

    A record commonly supersedes a form by *extending* it, and every
    `superseded` form in the family is a subsequence of the longer command that
    narrows it. A containment rule would fire on all of them. Equality asks the
    question that matters instead: whether the harness runs the form the record
    warns against and nothing more.
    """
    narrowed = ("pydeps", "--show-cycles", "--show-dot")
    assert not _runs_as_written(narrowed, "pydeps --show-cycles")
    assert _runs_as_written(("pydeps", "--show-cycles"), "pydeps --show-cycles")
    assert _runs_as_written(narrowed, "pydeps --show-cycles --show-dot")


def test_a_form_the_record_writes_with_a_placeholder_compares_as_written():
    """`pip-audit -r <requirements>` against the file the caller supplied.

    A placeholder standing as its own word is one token and matches whatever
    filled it. Reducing the form with `_concrete` first is what breaks this
    comparison rather than helping it: that drops such a token instead of
    truncating it, leaving a two-word form that can never equal the three-word
    command, so the form reports as one nothing runs - a comparison that cannot
    fire reads exactly like an entry with nothing to find. A placeholder glued to
    a flag is the case `_concrete` does serve, and both paths are held here.
    """
    assert _runs_as_written(
        ("pip-audit", "-r", "requirements.txt"), "pip-audit -r <requirements>"
    )
    assert not _runs_as_written(
        ("pip-audit", "-r", "requirements.txt", "--no-deps"),
        "pip-audit -r <requirements>",
    )
    assert _runs_as_written(("pytest", "--cov=fixture_app"), "pytest --cov=<pkg>")
    assert not _runs_as_written(("pytest", "--cov"), "pytest --cov=<pkg>")
```

- [ ] **Step 2: Run them to verify they fail**

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q -k "one_command_rather or carrying_a_form or writes_with_a_placeholder"`

Expected: FAIL, `NameError` on `_prescribed_commands` and `_runs_as_written`.

- [ ] **Step 3: Write the helpers**

Add both directly after `_demoted_tokens` from Task 1:

```python
def _prescribed_commands(inv: Invocation) -> list[tuple[str, tuple[str, ...]]]:
    """Every distinct command this entry says its record prescribes.

    Labelled by the first partition naming it, and distinct rather than one row
    per partition: `prescribed` answers a shared `argv` for all five, so a
    per-partition list would report one command as five routes in every failure
    message an entry with a shared argv produces.

    A supplied route is not here. It is authored in this table rather than
    transcribed from a record, so it answers to no declaration the record makes,
    which is what lets `deps/vulnerabilities` declare `pip-audit -r
    <requirements>` `superseded` truthfully while the uv partition's supplied
    route runs exactly that form.
    """
    out: dict[tuple[str, ...], str] = {}
    for partition in PARTITIONS:
        argv = inv.prescribed(partition)
        if argv and argv not in out:
            out[argv] = partition
    return [(partition, argv) for argv, partition in out.items()]


def _runs_as_written(command: tuple[str, ...], form: str) -> bool:
    """Whether the command is this form exactly and carries nothing else.

    Equality rather than containment, because a record supersedes a form by
    extending it as often as by replacing it: `pydeps --show-cycles` is
    superseded by the same command carrying `--show-dot`, and every `superseded`
    form in the family is a subsequence of the command that narrows it. Asking
    whether a command *contains* such a form answers yes for a correct entry.

    A placeholder standing as its own word matches whatever the caller supplied
    there, and counts as one token while it does. `_concrete` cannot serve here
    even though it serves everywhere else in this file: it *drops* such a token
    rather than truncating it, so `pip-audit -r <requirements>` would reduce to
    two words, never equal the three-word command that fills it, and report the
    form as one nothing runs - a comparison that cannot fire, reading exactly
    like an entry with nothing to find. A placeholder glued to a flag still goes
    through `_concrete`, where truncating leaves the flag as a prefix `_matches`
    can satisfy.
    """
    wanted = _tokens(form)
    tokens = _tokens(" ".join(command))
    if len(wanted) != len(tokens):
        return False
    for want, token in zip(wanted, tokens):
        if want.startswith("<") and want.endswith(">"):
            continue
        reduced = _concrete([want])
        if not reduced or not _matches(reduced[0], token):
            return False
    return True
```

- [ ] **Step 4: Run the unit tests to verify they pass**

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q -k "one_command_rather or carrying_a_form or writes_with_a_placeholder"`

Expected: 3 passed.

- [ ] **Step 5: Write both properties over the tree**

Add both immediately after `test_every_form_the_harness_runs_appears_in_an_argv`, before `def test_every_disposition_in_the_vocabulary_is_used():`:

```python
def test_no_prescribed_command_is_exactly_a_form_the_record_warns_against():
    """The disposition's other half, which had no property at all.

    The coverage property above reads the `runs` half, so a form declared
    `alternative` or `superseded` is held against nothing - which makes the
    disposition a per-form off-switch. Flipped, a second edit can drop the
    narrowing token from the argv, and the harness ships running exactly the
    form the record warns against.

    Two limits, both real. Equality, so a non-`runs` form run as a strict prefix
    plus some unrelated token still passes: containment cannot be the test
    because a record supersedes a form by extending it, and every `superseded`
    form in the family is a subsequence of the command that narrows it. And this
    reads the declaration rather than the record - which form a record warns
    against is not mechanically extractable, so a disposition simply wrong about
    its record stays a reading pass.
    """
    for inv in INVOCATIONS:
        commands = _prescribed_commands(inv)
        if inv.then:
            commands = [*commands, ("then", inv.then)]
        for form, disposition in inv.forms:
            if disposition == "runs":
                continue
            for label, command in commands:
                assert not _runs_as_written(command, form), (
                    f"{inv.check}/{inv.tool}: the {label} command runs {form!r} "
                    f"as written while the record declares it {disposition}"
                )


def test_an_entry_declaring_forms_declares_one_it_runs():
    """What makes the flip fail at its first edit rather than its second.

    An entry whose declared forms include none marked `runs` has switched the
    coverage property off for itself entirely, and the property above catches
    the consequence only where the shortened argv happens to equal another form
    the record already declares. Where an entry's `runs` forms number one,
    flipping it leaves the argv equal to no declared form at all, and the second
    edit is unguarded - measured on `test/isolation`, whose single form is
    `pytest --durations=25`.

    The two entries named here declare a single `alternative` form truthfully:
    the record's only named form is one the harness deliberately does not run,
    and what it runs instead is the plain command the quote prescribes, which
    the anchor guard holds. Asserted rather than allowed, so an entry that grows
    a `runs` form fails here rather than keeping an exception it no longer
    needs.
    """
    silenced = {
        # The record names `pip-licenses --format json` as the alternative; the
        # harness runs the plain command the quote prescribes.
        ("deps/licenses", "pip-licenses"),
        # The record names `pytest --randomly-seed=<n>` for reproducing one
        # ordering; the harness runs the suite as the record prescribes it.
        ("test/determinism", "pytest-randomly"),
    }
    seen = set()
    for inv in INVOCATIONS:
        if not inv.forms:
            continue
        runs = [form for form, disposition in inv.forms if disposition == "runs"]
        if (inv.check, inv.tool) in silenced:
            assert not runs, (inv.check, inv.tool, runs)
            seen.add((inv.check, inv.tool))
        else:
            assert runs, (
                f"{inv.check}/{inv.tool}: declares {len(inv.forms)} forms and none "
                "it runs, so the coverage property holds nothing on it"
            )
    assert seen == silenced, "an exception nothing exercises is a stale exception"
```

- [ ] **Step 6: Run the whole suite**

Run: `caffeinate uv run pytest tests/ -q`

Expected: PASS.

- [ ] **Step 7: Mutate the first edit of the flip**

Edit `scripts/run_python_fixture_lens.py`: on the `test/isolation` entry with `tool="pytest-timeout"`, change its single form's disposition from `"runs"` to `"alternative"`:

```python
        forms=(("pytest --durations=25", "alternative"),),
```

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q 2>&1 | tail -20`

Expected: FAIL, naming `test_an_entry_declaring_forms_declares_one_it_runs`. Record which tests failed.

- [ ] **Step 8: Mutate the flip and the drop together**

Keep the flip from Step 7 in place and additionally, on the `arch/cycles` entry with `tool="pydeps"`, flip its `runs` form to `"alternative"` and drop `--show-dot` from the argv:

```python
        argv=("pydeps", "--show-cycles"),
```
```python
        forms=(
            ("pydeps --show-cycles", "superseded"),
            ("pydeps --show-cycles --show-dot", "alternative"),
        ),
```

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q 2>&1 | tail -30`

Expected: FAIL naming both `test_no_prescribed_command_is_exactly_a_form_the_record_warns_against` (the argv now *is* the superseded form) and `test_an_entry_declaring_forms_declares_one_it_runs`. Record both.

- [ ] **Step 9: Revert both mutations**

Run: `git checkout -- scripts/run_python_fixture_lens.py && git status --short`

Expected: only `tests/scripts/test_python_fixture_harness.py` modified. Then `caffeinate uv run pytest tests/ -q` green.

- [ ] **Step 10: Correct the prose the properties invalidated**

In `scripts/run_python_fixture_lens.py`, the `Invocation.forms` docstring contains a paragraph beginning `A disposition is a claim about the record and not about this table:` whose middle asserts that "a form the harness *does* run while declaring it `superseded` or `alternative` passes every test in the suite, because that property reads only the `runs` half and no property reads the other", and then that "the disposition doubles as a per-form off-switch for that property". That is now false. Replace the text from `The two diverge in one direction with no mechanical net.` through `what the suite checks to the forms still declared `runs`.` with:

```
            The two can still diverge, inside bounds two properties now set. A
            form declared `runs` that no argv carries fails the coverage
            property. A form the harness runs *as written* while declaring it
            `superseded` or `alternative` fails a second one, and flipping the
            last `runs` form off an entry fails a third before any argv is
            touched, which is what keeps the disposition from working as a
            per-form off-switch for the coverage property. What is left is
            narrower and stated where it is held: a non-`runs` form run as a
            strict prefix plus an unrelated token, and a disposition simply
            wrong about its record, which no extraction can read out of prose.
```

Keep the paragraph's opening two sentences and its closing `deps/vulnerabilities` example unchanged: both stay true.

- [ ] **Step 11: Run the gates**

Run: `caffeinate uv run pytest tests/ -q && caffeinate uv run ruff check . && caffeinate uv run ruff format --check .`

Expected: all three clean.

- [ ] **Step 12: Commit**

The docstring correction rides with the properties that make it true, in one commit:

```bash
git commit -F - -- tests/scripts/test_python_fixture_harness.py scripts/run_python_fixture_lens.py <<'EOF'
test: bound the disposition so it cannot silence what the suite checks

A disposition was a per-form off-switch for the coverage property: flip
one form off `runs` and nothing held it against any command, after which
dropping the token from the argv shipped the harness running a form the
record warns against. Green at both steps.

Two properties, because one edit is caught by each. No prescribed
command may *be* a non-`runs` form as written, which catches the drop
where the shortened argv comes to equal a form already declared
`superseded`. And an entry declaring forms must declare one it runs,
which catches the flip itself - on an entry whose `runs` forms number
one, the shortened argv equals no declared form at all and the equality
rule has nothing to fire on.

Equality rather than containment: a record supersedes a form by
extending it, so every `superseded` form in the family is a subsequence
of the command that narrows it, and a containment rule would fire on
correct entries.

Refs #55
EOF
```

---

### Task 3: The second command follows the first in the record

**Files:**
- Modify: `tests/scripts/test_python_fixture_harness.py`
- Modify: `scripts/run_python_fixture_lens.py` (one docstring paragraph, no behaviour change)

**Interfaces:**
- Consumes: `_prescribed_commands` from Task 2, plus `_tokens` and `_is_subsequence`, already in the file.
- Produces: nothing later tasks use.

- [ ] **Step 1: Write the unit test**

Add it immediately after `test_a_form_the_record_writes_with_a_placeholder_compares_as_written` from Task 2:

```python
def test_swapping_the_two_commands_breaks_the_records_order():
    """The order the record writes, held against the record.

    `coverage run -m pytest` then `coverage report --show-missing` is one route,
    and swapped it prints the report before the suite that produces it. The
    swap's only guard was a literal tuple pinned in a test, whose failure
    message reads as a stale literal to update. Built on a synthetic entry
    because the tree carries the order correctly, so it cannot tell a rule that
    holds the order from one that does not.
    """
    quote = (
        "`pytest --cov=<pkg> --cov-branch --cov-report=term-missing` (or `coverage "
        "run -m pytest` + `coverage report --show-missing`)."
    )
    forward = Invocation(
        check="test/coverage-reach",
        tool="coverage.py",
        argv=("coverage", "run", "-m", "pytest"),
        then=("coverage", "report", "--show-missing"),
        record_quote=quote,
    )
    swapped = Invocation(
        check="test/coverage-reach",
        tool="coverage.py",
        argv=("coverage", "report", "--show-missing"),
        then=("coverage", "run", "-m", "pytest"),
        record_quote=quote,
    )
    assert _follows_in_the_record(forward)
    assert not _follows_in_the_record(swapped)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q -k swapping_the_two`

Expected: FAIL, `NameError: name '_follows_in_the_record' is not defined`.

- [ ] **Step 3: Write the helper**

Add it directly after `_runs_as_written` from Task 2:

```python
def _follows_in_the_record(inv: Invocation) -> bool:
    """Whether every prescribed command precedes its `then` in the quote.

    A two-command route has an order, and the record writes it: `coverage run -m
    pytest` before `coverage report --show-missing`. Nothing held that order
    against the record - the anchor guard traces one command at a time and never
    reads `then` - so the swap failed only tests pinning the tuples as literals,
    which reads as a literal to update rather than as a route reversed.
    """
    quote = _tokens(inv.record_quote)
    return all(
        _is_subsequence(_tokens(" ".join((*argv, *inv.then))), quote)
        for _, argv in _prescribed_commands(inv)
    )
```

- [ ] **Step 4: Run the unit test to verify it passes**

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q -k swapping_the_two`

Expected: 1 passed.

- [ ] **Step 5: Write the property and remove the literal pin**

Add the property immediately after `test_a_token_the_record_prescribes_never_hides_in_the_completion` from Task 1:

```python
def test_a_two_command_route_runs_them_in_the_records_order():
    """Held against the record rather than against a pinned tuple.

    Every entry carrying a `then`, which is the one route the family prescribes
    in two commands. A count is not asserted here: the property is that each
    such entry's order traces through its own quote, and an entry growing a
    `then` should be held by it rather than fail an arithmetic claim about how
    many there are.
    """
    for inv in INVOCATIONS:
        if not inv.then:
            continue
        assert _follows_in_the_record(inv), (
            f"{inv.check}/{inv.tool}: the record writes {inv.then} before the "
            "command this entry runs first, so the route is reversed against it"
        )
```

Then delete `test_a_two_step_route_keeps_its_second_command` entirely - the whole function including its `inv = next(...)` lookup and its `assert inv.then == ("coverage", "report", "--show-missing")` line. The property above subsumes what it guarded and does it without a literal.

Leave `test_a_granted_run_materializes_first_and_then_runs_in_the_environment` alone. Its `follow_up["command"][-3:]` assertion is about a command the run actually executed, which is a different claim from the transcription's order.

- [ ] **Step 6: Run the whole suite**

Run: `caffeinate uv run pytest tests/ -q`

Expected: PASS, with one test fewer than before this step and one more property.

- [ ] **Step 7: Mutate to prove the property has teeth**

Edit `scripts/run_python_fixture_lens.py`: on the `test/coverage-reach` entry with `tool="coverage.py"`, swap the two commands:

```python
        argv=("coverage", "report", "--show-missing"),
        then=("coverage", "run", "-m", "pytest"),
```

Run: `caffeinate uv run pytest tests/scripts/test_python_fixture_harness.py -q 2>&1 | tail -20`

Expected: FAIL naming `test_a_two_command_route_runs_them_in_the_records_order`. Record every test that failed, and note whether any of them is a literal pin the deletion in Step 5 missed.

- [ ] **Step 8: Revert the mutation**

Run: `git checkout -- scripts/run_python_fixture_lens.py && git status --short`

Expected: only `tests/scripts/test_python_fixture_harness.py` modified. Then `caffeinate uv run pytest tests/ -q` green.

- [ ] **Step 9: Correct the `then` docstring**

In `scripts/run_python_fixture_lens.py`, `Invocation.then`'s docstring says what the field holds and nothing about what holds its order. Append to it, inside the same field description:

```
            The order is the record's and is held against it rather than against
            a literal in the suite: the two commands concatenated trace through
            the quote in the order the record writes them, so swapping them
            fails as a reversed route rather than as a tuple somebody needs to
            update.
```

- [ ] **Step 10: Run the gates**

Run: `caffeinate uv run pytest tests/ -q && caffeinate uv run ruff check . && caffeinate uv run ruff format --check .`

Expected: all three clean.

- [ ] **Step 11: Commit**

```bash
git commit -F - -- tests/scripts/test_python_fixture_harness.py scripts/run_python_fixture_lens.py <<'EOF'
test: hold a two-command route's order against the record

Swapping an entry's `argv` and `then` printed the coverage report
before the suite that produces it, and failed only tests pinning the
tuples as literals - whose messages read as a stale literal to update,
which is an invitation to ship the swap. Nothing property-shaped held
the order against the record's own sentence.

The two commands concatenated now trace through the quote in the order
the record writes them. The literal pin goes with it; the end-to-end
assertion on the executed command stays, because running the second
command is a different claim from transcribing it in order.

Refs #55
EOF
```

---

### Task 4: The stale-prose sweep

**Files:**
- Modify: `tests/scripts/test_python_fixture_harness.py` (prose only)
- Modify: `scripts/run_python_fixture_lens.py` (prose only)

**Interfaces:**
- Consumes: nothing. This task reads the two files as they now stand and changes no behaviour.
- Produces: nothing.

The implementer for this task must be a subagent that has **not** seen the implementation of Tasks 1 to 3. Its brief is the sweep itself, not the diff.

- [ ] **Step 1: Read both files whole**

Read `tests/scripts/test_python_fixture_harness.py` and `scripts/run_python_fixture_lens.py` in full. Do not read the diff, the plan, or the spec first - the point of the pass is to find prose a reader would believe, without knowing which lines were edited.

- [ ] **Step 2: List every passage that describes what the suite does not hold**

Search both files for prose asserting an absence, and check each against the code as it now stands. The phrases that mark such a claim: `no guard`, `no property`, `nothing holds`, `nothing here`, `passes every test`, `leaves the suite green`, `one direction`, `unguarded`, `off-switch`, `stays green`, `reads only`, `never reads`, `cannot see`, `invisible`, `documented limit`, `stated limit`.

Run: `caffeinate grep -n "no guard\|no property\|nothing holds\|passes every test\|leaves the suite green\|one direction\|unguarded\|off-switch\|stays green\|never reads\|cannot see" tests/scripts/test_python_fixture_harness.py scripts/run_python_fixture_lens.py`

For each hit, decide whether the claim is still true of the code. A claim that is no longer true is a finding; a claim that is still true is not, and must be left exactly as written.

- [ ] **Step 3: Check the four field docstrings against their guards**

Read `Invocation`'s `completion`, `then`, `forms` and `argv` field descriptions in `scripts/run_python_fixture_lens.py`, and for each ask: does some property hold the claim it makes, and does the docstring name what does? Report any that describes a guarantee no test enforces, or an absence a test now closes.

- [ ] **Step 4: Fix every finding in place**

Rewrite each false passage to state what is true now, including the limits. Do not narrate the change: no "previously", no "this used to", no issue numbers. State the current contract. Keep the file's voice - state the structural reason rather than the current snapshot, name a thing rather than numbering it, and never assert a count you did not compute.

Markdown and docstring prose in this repository is never hard-wrapped by reflowing lines you did not change: keep edits inside the paragraph you are correcting.

- [ ] **Step 5: Run the gates**

Run: `caffeinate uv run pytest tests/ -q && caffeinate uv run ruff check . && caffeinate uv run ruff format --check .`

Expected: all three clean. Prose-only edits change no behaviour, so a failing suite here means an edit landed inside code.

- [ ] **Step 6: Commit**

If the sweep found nothing, commit nothing and report that, naming the passages checked. Otherwise:

```bash
git commit -F - -- tests/scripts/test_python_fixture_harness.py scripts/run_python_fixture_lens.py <<'EOF'
docs: correct the prose the new properties made false

Passages describing a gap as open, read by somebody deciding what the
suite guarantees, are the ones that mislead hardest once it is closed.

Refs #55
EOF
```

---

## Verification

After Task 4, before the PR:

- [ ] `caffeinate uv run pytest tests/ -q` - green, and the count is higher than the branch base by the properties and unit tests added minus the one literal pin removed. Compute both numbers; do not assume either.
- [ ] `caffeinate uv run ruff check . && caffeinate uv run ruff format --check .` - clean.
- [ ] `caffeinate uv run python scripts/render_handbook_traceability.py --check` - exit 0.
- [ ] `caffeinate uv run python scripts/render_python_fixture_expectations.py --check` - exit 0.
- [ ] `git status --short` - empty. Every mutation reverted.
- [ ] `git diff origin/main --stat` - names exactly `tests/scripts/test_python_fixture_harness.py`, `scripts/run_python_fixture_lens.py`, and the two files under `docs/superpowers/`. No check record, no fixture.
