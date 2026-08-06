# Ungranted answerability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give a check record a validated way to say what it still answers when its tools' grants are withheld, so `audit-core` stops deriving a check-level conclusion from tool-level facts and getting it wrong.

**Architecture:** One optional frontmatter string, `ungranted_note`, required exactly where every tool in some language carries a `needs:` tier and rejected as vacuous anywhere else. `scripts/audit_checks.py` enforces the shape; the three places that restate the derived rule (`audit-core` step 1, the sweep's step 0 grants bullet, the sweep's fan-out brief) defer to the field; eleven records gain a note. `tooling:` and `needs:` do not change anywhere.

**Tech Stack:** Python 3, PyYAML, pytest, ruff. Markdown skill prose. No new dependencies.

## Global Constraints

Every task's requirements implicitly include these.

- **Never change any record's `tooling:` or `needs:`.** The sweep behind this plan found only procedures, not packages, so no record gains a tool name and none drops out of the fully-tiered set. A `needs:` edit would also break `test_a_tool_has_one_tier_across_the_family`.
- **Markdown is never hard-wrapped: one paragraph is one source line.** Never reflow a line you did not change.
- **No em-dash (U+2014) in this plan or in `docs/superpowers/specs/`.** Use ` - `. Skill records under `.agents/skills/` also use ` - `, matching their existing prose.
- **Never assert a count you did not compute.** Compute it in the same breath or state no number.
- Commit messages reference `Refs #26`. No Claude credits.
- Run Python via `uv run`. Before every commit: `uv run ruff check .` and `uv run ruff format --check .`, plus `uv run pytest tests/ -q` and `uv run python scripts/render_handbook_traceability.py --check`.
- Ledger anchors in `docs/audit/sweep-obligations.md` must occur in `audit-core/SKILL.md` **exactly once** and must contain **no inline backticks** - `tests/test_sweep_obligations.py` strips only outer backticks, so an anchor with an inner one can never match.
- The sentinel is the lowercase string `none`. Nothing else means "nothing answers".

## File Structure

| File | Responsibility |
|---|---|
| `scripts/audit_checks.py` | The field, the `Check` member, the `_fully_tiered_languages` helper, the validation rules, and the frontmatter documentation |
| `tests/scripts/test_audit_checks.py` | One case per validation rule, plus the family-wide prose-note floor |
| `tests/scripts/test_render_handbook_traceability.py` | Its in-memory `Check` fixture gains the new member |
| `.agents/skills/audit-core/SKILL.md` | The step 1 conditional and the authoring frontmatter list |
| `.agents/skills/audit/SKILL.md` | The step 0 grants bullet and the fan-out brief |
| Eleven check records under `.agents/skills/*/checks/` | Their notes |
| `docs/audit/sweep-obligations.md` | A row per obligation this adds to `audit-core` |
| `CLAUDE.md` | The check-records paragraph |

**Sequencing matters and is not negotiable.** The required-iff rule cannot land before the records carry notes, or `render_handbook_traceability.py --check` and every real-tree test fail on the intermediate commit. So: Task 1 adds the field and the shape rules only, Task 2 writes the eleven notes, Task 3 turns on the requirement. Each of those three commits leaves the gate green.

---

### Task 1: The field, its shape rules, and the vacuity rejection

**Files:**
- Modify: `scripts/audit_checks.py`
- Modify: `tests/scripts/test_audit_checks.py`
- Modify: `tests/scripts/test_render_handbook_traceability.py:118-129`

**Interfaces:**
- Produces: `Check.ungranted_note: str | None`; module constant `UNGRANTED_NONE = "none"`; helper `_fully_tiered_languages(tooling, needs) -> tuple[str, ...]`.
- Consumes: the existing `tooling` and `needs` dicts built earlier in `_parse_record`.

**Do NOT add the required-iff rule in this task.** No record carries the field yet, so requiring it would fail the real-tree gate. Task 3 adds it.

- [ ] **Step 1: Write the failing tests**

Add to `tests/scripts/test_audit_checks.py`. The file already has helpers for writing a record tree; follow the pattern of the existing `needs:` tests beside them.

```python
def test_the_sentinel_is_accepted(tmp_path):
    """A record with nothing to answer writes the lowercase sentinel."""
    check = _record(
        tooling={"python": ["pip-licenses"]},
        needs={"resolved-tree": ["pip-licenses"]},
        extra="ungranted_note: none\n",
    )
    checks, errors = _load_one(tmp_path, check)
    assert errors == []
    assert checks["demo/thing"].ungranted_note == "none"


def test_prose_is_accepted_and_stripped(tmp_path):
    check = _record(
        tooling={"python": ["pip-licenses"]},
        needs={"resolved-tree": ["pip-licenses"]},
        extra="ungranted_note: |\n  Reading the lockfile answers the pinned set.\n",
    )
    checks, errors = _load_one(tmp_path, check)
    assert errors == []
    assert checks["demo/thing"].ungranted_note == (
        "Reading the lockfile answers the pinned set."
    )


@pytest.mark.parametrize("spelling", ["None", "NONE", "nOnE"])
def test_a_miscased_sentinel_is_rejected_by_name(tmp_path, spelling):
    """YAML leaves `None` and `NONE` as ordinary strings, so a miscased
    sentinel would be read as a claim that something answers. Reject it
    with a message naming the spelling to use.
    """
    check = _record(
        tooling={"python": ["pip-licenses"]},
        needs={"resolved-tree": ["pip-licenses"]},
        extra=f"ungranted_note: {spelling}\n",
    )
    _, errors = _load_one(tmp_path, check)
    assert any("write the sentinel as 'none'" in e for e in errors)


@pytest.mark.parametrize("value", ["null", "~", ""])
def test_a_null_note_is_rejected_as_indistinguishable_from_omission(tmp_path, value):
    """YAML turns `null`, `~` and a bare key into nothing, which the loader
    cannot tell from an absent key. Say so rather than silently treating
    the record as unclassified.
    """
    check = _record(
        tooling={"python": ["pip-licenses"]},
        needs={"resolved-tree": ["pip-licenses"]},
        extra=f"ungranted_note: {value}\n",
    )
    _, errors = _load_one(tmp_path, check)
    assert any("ungranted_note is empty" in e for e in errors)


def test_a_blank_note_is_rejected(tmp_path):
    check = _record(
        tooling={"python": ["pip-licenses"]},
        needs={"resolved-tree": ["pip-licenses"]},
        extra='ungranted_note: "   "\n',
    )
    _, errors = _load_one(tmp_path, check)
    assert any("ungranted_note is blank" in e for e in errors)


def test_a_non_string_note_is_rejected(tmp_path):
    check = _record(
        tooling={"python": ["pip-licenses"]},
        needs={"resolved-tree": ["pip-licenses"]},
        extra="ungranted_note: [a, b]\n",
    )
    _, errors = _load_one(tmp_path, check)
    assert any("must be prose or 'none'" in e for e in errors)


def test_a_note_on_a_record_that_keeps_an_untiered_tool_is_vacuous(tmp_path):
    """The field describes a withheld grant leaving the record with nothing
    to run. A record keeping a tool that answers from a read-only clone
    cannot reach that state, so a note there describes nothing and must
    not be mistaken for one that is doing work.
    """
    check = _record(
        tooling={"python": ["pip-licenses", "osv-scanner"]},
        needs={"resolved-tree": ["pip-licenses"]},
        extra="ungranted_note: none\n",
    )
    _, errors = _load_one(tmp_path, check)
    assert any("cannot happen here" in e for e in errors)


def test_a_language_with_no_tools_is_not_fully_tiered(tmp_path):
    """`all()` is vacuously true over an empty list. A record listing a
    language with no tools has said nothing about grants, so it must not
    read as silenced - which would demand a note it has no basis to write.
    """
    check = _record(
        tooling={"python": ["pip-licenses"], "typescript": []},
        needs={"resolved-tree": ["pip-licenses"]},
        extra="ungranted_note: none\n",
    )
    _, errors = _load_one(tmp_path, check)
    assert errors == [], errors
    assert ac._fully_tiered_languages(
        {"python": ("pip-licenses",), "typescript": ()},
        {"resolved-tree": ("pip-licenses",)},
    ) == ("python",)
```

If `_record` and `_load_one` helpers with those signatures do not already exist in the file, write thin wrappers over whatever the existing `needs:` tests use, rather than restructuring those tests. Keep the record id `demo/thing` consistent with the file's existing fixtures.

- [ ] **Step 2: Run them to watch them fail**

Run: `uv run pytest tests/scripts/test_audit_checks.py -q -k "sentinel or ungranted or vacuous or fully_tiered"`
Expected: FAIL. The `unknown frontmatter key 'ungranted_note'` error appears instead of the messages asserted, and `_fully_tiered_languages` does not exist.

- [ ] **Step 3: Add the constant, the field and the helper**

In `scripts/audit_checks.py`, beside `NEEDS_TIERS`:

```python
# The sentinel a record writes when a withheld grant really does leave it
# nothing to answer. Spelled lowercase because YAML turns `None` and `NONE`
# into ordinary strings, which would read as a fallback claim, and turns
# `null` and an empty value into nothing at all, which reads as an omitted
# key. The loader rejects each of those by name rather than guessing.
UNGRANTED_NONE = "none"
```

Add `"ungranted_note"` to `FIELDS`, between `"needs"` and `"optin"`.

Add the member to `Check`, after `needs`:

```python
    ungranted_note: str | None
```

Add the helper beside `_str_list`:

```python
def _fully_tiered_languages(
    tooling: dict[str, tuple[str, ...]], needs: dict[str, tuple[str, ...]]
) -> tuple[str, ...]:
    """Languages whose every offered tool needs a grant.

    These are the (record, language) pairs the engine silences: with no
    grant held, a check has nothing left to run in that language, so it
    reports `no-evidence (not-permitted)` unless the record says otherwise.
    A language offering no tools at all is not one of them - `all()` is
    vacuously true over an empty list, and a record that lists a language
    with no tools has said nothing about grants.

    Args:
        tooling: Language to the tools the record offers.
        needs: Tier to the tools that need it.

    Returns:
        The languages, sorted, so a message naming them is stable.
    """
    tiered = {name for names in needs.values() for name in names}
    return tuple(
        lang
        for lang, names in sorted(tooling.items())
        if names and all(name in tiered for name in names)
    )
```

- [ ] **Step 4: Add the validation block**

In `_parse_record`, between the `needs` block (which ends with `needs[tier] = names`) and the `optin` block:

```python
    silenced = _fully_tiered_languages(tooling, needs)
    ungranted = meta.get("ungranted_note")
    if "ungranted_note" in meta:
        if ungranted is None:
            errors.append(
                f"{where}: ungranted_note is empty - YAML reads `null`, `~` and a "
                f"bare key as nothing, which is indistinguishable from omitting "
                f"the key. Write {UNGRANTED_NONE!r} if nothing answers without a "
                "grant, or say what does"
            )
        elif not isinstance(ungranted, str):
            errors.append(
                f"{where}: ungranted_note must be prose or {UNGRANTED_NONE!r}, "
                f"got {ungranted!r}"
            )
        elif not ungranted.strip():
            errors.append(
                f"{where}: ungranted_note is blank - write {UNGRANTED_NONE!r} if "
                "nothing answers without a grant, or say what does"
            )
        elif (
            ungranted.strip().lower() == UNGRANTED_NONE
            and ungranted.strip() != UNGRANTED_NONE
        ):
            errors.append(
                f"{where}: write the sentinel as {UNGRANTED_NONE!r}, not "
                f"{ungranted!r} - YAML leaves the capitalised spellings as "
                "ordinary strings, so this would be read as a claim that "
                "something answers"
            )
        else:
            ungranted = ungranted.strip()
    else:
        ungranted = None

    if not silenced and "ungranted_note" in meta:
        errors.append(
            f"{where}: ungranted_note describes a withheld grant leaving this "
            "record with nothing to run, which cannot happen here - every "
            "language it offers keeps a tool that answers from a read-only clone"
        )
```

Note the miscased-sentinel branch compares `ungranted.strip()` on both sides, so ` None ` is reported as a miscased sentinel rather than accepted as prose.

Pass it to the constructor: `ungranted_note=ungranted,` after `needs=needs,`.

- [ ] **Step 5: Update the render test's in-memory fixture**

`tests/scripts/test_render_handbook_traceability.py:118-129` builds a `Check` directly. Add `ungranted_note=None,` after `needs={},`.

- [ ] **Step 6: Document the field**

In the module docstring's frontmatter table, after the `needs` row:

```
| `ungranted_note` | no | What the check still answers when that grant is withheld |
```

The `Required` column says `no` because at this commit it is optional; Task 3 changes it to `iff every tool in a language needs a grant` when the rule that makes it true lands. Do not write the stronger claim here - a commit whose documentation describes a rule the loader does not yet enforce is a commit that lies about itself.

Then add a paragraph after the existing `needs` paragraph:

```
`ungranted_note` answers a third question, and it is about the check rather
than about any tool: when the tools need a grant this run does not hold,
what can the check still answer? `needs` cannot express this, because it
is per-tool, and the engine's rule - a check whose every tool needs a
grant is `no-evidence` without it - is a check-level conclusion derived
from tool-level facts. That derivation is wrong wherever a check has an
axis needing no tool, which is why the field exists rather than the
records arguing with their own frontmatter in prose. The value is either
what still answers, or the sentinel `none` where nothing does, and it is
rejected on a record that keeps a tool answering from a read-only clone,
because there the withheld-grant situation it describes cannot arise.
```

Say nothing here about the field being required; Task 3 adds that sentence with the rule.

- [ ] **Step 7: Run the tests and the gate**

Run: `uv run pytest tests/ -q` - all pass, including the real-tree tests, because no record carries the key yet.
Run: `uv run python scripts/render_handbook_traceability.py --check` - exit 0.
Run: `uv run ruff check . && uv run ruff format --check .` - clean.

- [ ] **Step 8: Commit**

```bash
git add scripts/audit_checks.py tests/scripts/test_audit_checks.py tests/scripts/test_render_handbook_traceability.py
git commit -m "feat: let a record say what it answers without a grant

Refs #26"
```

Write the real message per the repository's convention: say WHY the field
exists (the derived check-level conclusion is wrong wherever a check has a
tool-free axis), not only that a field was added.

---

### Task 2: Write the eleven notes

**Files:**
- Modify: `.agents/skills/arch-audit/checks/complexity.md`
- Modify: `.agents/skills/arch-audit/checks/complexity-gate.md`
- Modify: `.agents/skills/arch-audit/checks/hidden-coupling.md`
- Modify: `.agents/skills/deps-audit/checks/freshness.md`
- Modify: `.agents/skills/deps-audit/checks/hygiene.md`
- Modify: `.agents/skills/deps-audit/checks/licenses.md`
- Modify: `.agents/skills/deps-audit/checks/transitive-licenses.md`
- Modify: `.agents/skills/test-audit/checks/coverage-reach.md`
- Modify: `.agents/skills/test-audit/checks/determinism.md`
- Modify: `.agents/skills/test-audit/checks/isolation.md`
- Modify: `.agents/skills/test-audit/checks/mutation.md`

**Interfaces:**
- Consumes: `ungranted_note` from Task 1, which accepts the key but does not yet require it.
- Produces: eleven records satisfying Task 3's requirement.

These eleven are the complete set the engine currently silences, verified by loading every record and taking the (record, language) pairs whose every tool carries a tier. Add the key **after** `needs:` in the frontmatter, using YAML block scalar `>-` for prose. Change nothing else in any record except where a step below says so.

The note text below is the deliverable. It is the product of a verification sweep; do not paraphrase it into something shorter, and do not add a claim it does not make.

- [ ] **Step 1: `arch/complexity` - verify the ESLint invocation before writing it**

The note claims ESLint can measure complexity without the target's `node_modules`. `--no-config-lookup` and `-c/--config` are confirmed present on the ESLint a one-shot runner fetches. What is **not** yet confirmed end to end is the parser: TypeScript needs one, and it must come from the audit rather than the target.

Verify it, in a scratch directory outside the repository: write a `.ts` file with a deliberately branch-heavy function and a minimal flat config enabling only the core `complexity` rule, then run ESLint through `npx` with a TypeScript parser fetched alongside it, with no `node_modules` in the fixture. Record the exact command that works.

If it works, write the note with that command shape. **If it does not, drop the ESLint sentence entirely** and keep only the syntax-tree sentence, which needs no verification because the record already prescribes it. Report which happened.

```yaml
ungranted_note: >-
  Cyclomatic complexity is a property of the syntax tree, so the branch-point count
  the `With none of them installed` paragraph below describes answers the metric on any
  partition with nothing installed, in either language. ESLint answers it too under a
  config the audit supplies rather than the target's: pointed at an audit-owned flat
  config with `--config` and `--no-config-lookup`, with a TypeScript parser fetched
  alongside ESLint rather than taken from the target, the core `complexity` and
  `max-depth` rules read the target's source without loading the target's own flat
  config, so no `node_modules` is needed. What the grant buys is the thresholds the
  project set for itself, and `eslint-plugin-sonarjs`'s type-aware cognitive-complexity
  rules, which need a real TypeScript program over the installed tree.
```

- [ ] **Step 2: `arch/complexity-gate` - move the prose into the field**

```yaml
ungranted_note: >-
  Whether a threshold is set, and whether a CI job fails the build on it, is read from
  the partition's linter configuration and its CI workflow files, both present on a
  read-only clone, so the gate question is answered in full with no grant. The
  classified tools are the gate's subject rather than its instrument: running one
  measures code against the threshold, which is `arch/complexity`'s question.
```

Then **delete** the second bolded paragraph of `## Tooling fallback` (the one beginning `**The gate question itself needs no grant`) - the field now carries it, and leaving both makes the record state the same thing twice with no rule about which governs. Keep the first paragraph, including its `ERR_MODULE_NOT_FOUND` sentence, which is about not misreading an abort rather than about grants.

- [ ] **Step 3: `arch/hidden-coupling`**

```yaml
ungranted_note: >-
  The tells this check looks for are patterns in source, and the TypeScript half lists
  the same ones the Python half greps for: mutable module-level exports, string-keyed
  container lookups, side-effectful top-level code, and dynamic `import()`. Reading
  TypeScript source for them needs nothing installed. What a withheld grant costs is
  `knip`'s export graph, which is what shows an exported binding written from more than
  one module rather than merely exported - so the single-module tells survive and the
  cross-module correlation does not.
```

- [ ] **Step 4: `deps/freshness`**

```yaml
ungranted_note: >-
  The pins are already in the clone. Read `uv.lock`, `poetry.lock` or the pip-compile
  output for the direct and transitive pins, then ask the registry per package:
  `https://pypi.org/pypi/<name>/json` reports the latest release in `info.version`,
  which is the comparison the tiered tools would have made, and
  `https://pypi.org/pypi/<name>/<version>/json` reports `yanked` for the pinned
  release. Take the latest release from the project endpoint rather than the
  per-version one, which describes only the version asked for and cannot tell you
  something newer exists. That path needs network rather than the tree, so it survives
  a withheld grant and fails instead where the audit has no network, which is
  `no-evidence (tool-unavailable)` rather than `not-permitted`. What the resolved tree
  adds is the versions actually installed, which can differ from the pins; on a foreign
  repository the pins are the more faithful subject anyway.
```

- [ ] **Step 5: `deps/hygiene`**

```yaml
ungranted_note: >-
  Duplicate and conflicting pins, and a dependency declared in the wrong group, are
  read from the manifest and the lockfile with nothing installed. The scanners give a
  partial signal without the tree and must be reported with its limit rather than at
  face value: `deptry` is correct where a distribution name equals its import name and
  misreports in both directions at once where they diverge, emitting a
  declared-but-unused finding for the distribution and a missing-dependency finding for
  the import it could not resolve; `depcheck` resolves plain `require` and `import`
  usage without `node_modules`, and its `bin` and config specials are exactly the part
  that needs the tree. `knip` answers nothing trustworthy without it.
```

- [ ] **Step 6: `deps/licenses`**

```yaml
ungranted_note: >-
  For a partition with a lockfile, the licence of each pinned release is available from
  the registry without installing it: `https://pypi.org/pypi/<name>/<version>/json`
  carries the same three metadata channels the installed `METADATA` would, and all
  three must be read because none is universally populated - `license_expression` where
  the release declares an SPDX expression, `license` where it does not, and the
  `License ::` classifiers where neither is set. Read `license` with care: on older
  releases it holds the full licence text rather than an identifier, so a report
  echoing it verbatim prints a licence body where a name belongs. What the grant buys
  is the licences of what is actually installed, and coverage of any package the
  lockfile does not pin.
```

- [ ] **Step 7: `deps/transitive-licenses`**

```yaml
ungranted_note: >-
  The registry procedure `deps/licenses` describes answers this check too, and the
  extra depth costs nothing: a complete lockfile already pins the transitive graph, so
  the set to query is the whole of it rather than the direct dependencies. It is
  conditional on that lockfile existing - a partition pinning only its direct
  dependencies leaves the transitive set unenumerable without the tree, and that is
  `no-evidence (not-permitted)` rather than a clean result.
```

- [ ] **Step 8: `test/coverage-reach`**

```yaml
ungranted_note: >-
  What is excluded from measurement is readable with nothing installed:
  `[tool.coverage.run]`'s `source` and `omit`, and `exclude_lines`, in `pyproject.toml`
  or `.coveragerc`, name the code no coverage number will ever account for, which is
  part of what this check asks. The reach measurement itself runs the suite and does
  not survive a withheld grant. Whether a coverage threshold is *enforced* is a
  different check's question - `ci/gate-enforcement` owns whether an intended gate is
  actually required - so do not answer it here.
```

- [ ] **Step 9: `test/determinism`**

```yaml
ungranted_note: >-
  Grepping tests for `time.time()`, `datetime.now()`, `random.` without a seed, and
  live network calls answers the non-determinism axis with nothing installed. The
  randomized-order and repeat-run passes run the target's own suite and do not survive
  a withheld grant, so order-dependence specifically goes unmeasured. Ruff is not a
  substitute for the grep, though it looks like one: `DTZ005` asks whether a
  `datetime.now()` is timezone-aware rather than whether it is deterministic, so it
  stays silent on `datetime.now(tz=...)`, which is exactly as non-deterministic; and
  `S311` flags `random.` as cryptographically weak whether or not a seed was set on the
  line above, so it fires on the deterministic case.
```

The ruff sentences are there because that substitution was proposed during this work and refuted empirically. Leave them in: the field is where a future author looks.

- [ ] **Step 10: `test/isolation`**

```yaml
ungranted_note: >-
  Reading test source for calls that hit the network, the filesystem or a database
  answers the real-I/O axis with nothing installed. The `--durations` pass runs the
  target's own suite, so without the grant the timing evidence is missing and this
  check is answered on the I/O axis rather than `no-evidence` as a whole.
```

- [ ] **Step 11: `test/mutation` - the only sentinel**

```yaml
ungranted_note: none
```

The record's `## Tooling fallback` already says `Without the grant it is no-evidence (not-permitted)`. Leave that sentence: it is the sentinel in words, in the place an agent reads for what to do, and it does not contradict the field.

- [ ] **Step 12: Verify the set is exactly right**

Run this, which recomputes the silenced set from the tree rather than trusting the list above:

```bash
uv run python -c "
import importlib.util, pathlib, sys
r = pathlib.Path('.')
s = importlib.util.spec_from_file_location('ac', r / 'scripts' / 'audit_checks.py')
m = importlib.util.module_from_spec(s); sys.modules['ac'] = m; s.loader.exec_module(m)
by_id, errs = m.load_checks(r / '.agents' / 'skills')
assert not errs, errs
need = {c.id for c in by_id.values() if m._fully_tiered_languages(c.tooling, c.needs)}
have = {c.id for c in by_id.values() if c.ungranted_note is not None}
print('silenced, so required:', len(need))
print('carrying a note:', len(have))
print('missing:', sorted(need - have))
print('vacuous:', sorted(have - need))
"
```

Expected: the two counts equal, and both `missing` and `vacuous` empty.

- [ ] **Step 13: Run the gate and commit**

Run: `uv run pytest tests/ -q`, `uv run python scripts/render_handbook_traceability.py --check`, `uv run ruff check . && uv run ruff format --check .`

```bash
git add .agents/skills/arch-audit/checks/complexity.md .agents/skills/arch-audit/checks/complexity-gate.md .agents/skills/arch-audit/checks/hidden-coupling.md .agents/skills/deps-audit/checks/freshness.md .agents/skills/deps-audit/checks/hygiene.md .agents/skills/deps-audit/checks/licenses.md .agents/skills/deps-audit/checks/transitive-licenses.md .agents/skills/test-audit/checks/coverage-reach.md .agents/skills/test-audit/checks/determinism.md .agents/skills/test-audit/checks/isolation.md .agents/skills/test-audit/checks/mutation.md
git commit
```

This is a prompt change: the message must say WHY. Lead with the finding - the derived rule was silencing eleven records and ten of them can answer something - and name the corrections the sweep produced.

---

### Task 3: Require the note where the derivation bites

**Files:**
- Modify: `scripts/audit_checks.py`
- Modify: `tests/scripts/test_audit_checks.py`

**Interfaces:**
- Consumes: `_fully_tiered_languages` from Task 1 and the eleven notes from Task 2.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_silenced_record_must_say_what_still_answers(tmp_path):
    """An absent note on a record the engine silences is not a claim, it is
    an omission - and the engine cannot tell the two apart, which is the
    whole reason the field is required here.
    """
    check = _record(
        tooling={"python": ["pip-licenses"]},
        needs={"resolved-tree": ["pip-licenses"]},
    )
    _, errors = _load_one(tmp_path, check)
    assert any("silences the check" in e for e in errors)


def test_the_requirement_names_every_silenced_language(tmp_path):
    check = _record(
        tooling={"python": ["deptry"], "typescript": ["knip"]},
        needs={"resolved-tree": ["deptry"], "target-execution": ["knip"]},
    )
    _, errors = _load_one(tmp_path, check)
    assert any("python, typescript" in e for e in errors)


def test_an_unsilenced_record_needs_no_note(tmp_path):
    check = _record(
        tooling={"python": ["pip-licenses", "osv-scanner"]},
        needs={"resolved-tree": ["pip-licenses"]},
    )
    _, errors = _load_one(tmp_path, check)
    assert errors == [], errors


def test_the_notes_are_not_all_sentinels():
    """The requirement can be satisfied without thought by writing `none`
    everywhere. Nothing can tell a correct `none` from a lazy one, so hold
    the number of records that say something real: the sweep behind #26
    produced ten, and a change that drops one must say why rather than
    pass quietly. Raise this floor when a later sweep adds notes; never
    lower it to make a deletion pass.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    prose = [
        c.id
        for c in checks.values()
        if c.ungranted_note is not None and c.ungranted_note != ac.UNGRANTED_NONE
    ]
    assert len(prose) >= 10, f"only {len(prose)} records answer anything: {sorted(prose)}"
```

- [ ] **Step 2: Run them to watch the first two fail**

Run: `uv run pytest tests/scripts/test_audit_checks.py -q -k "silenced or every_silenced_language or all_sentinels"`
Expected: the two requirement tests FAIL (no error is produced), `test_the_notes_are_not_all_sentinels` PASSES already because Task 2 landed the notes.

- [ ] **Step 3: Add the rule**

In `_parse_record`, immediately before the `not silenced` vacuity check added in Task 1:

```python
    if silenced and "ungranted_note" not in meta:
        errors.append(
            f"{where}: every tool this record offers for {', '.join(silenced)} "
            "needs a grant, so a withheld grant silences the check - add an "
            "ungranted_note saying what still answers, or "
            f"{UNGRANTED_NONE!r} if nothing does"
        )
```

- [ ] **Step 4: Make the documentation match the rule that now exists**

Task 1 deliberately documented the field as optional, because it was. Now it is not.

In the module docstring's frontmatter table, change the `ungranted_note` row's `Required` column from `no` to `iff every tool in a language needs a grant`. Then append to the `ungranted_note` paragraph:

```
It is required on exactly the records this rule would silence, so an absent
key is never a silent claim - which is the hazard `needs` still carries and
this field does not.
```

- [ ] **Step 5: Run everything**

Run: `uv run pytest tests/ -q` - all pass, because Task 2 already wrote all eleven notes.
Run: `uv run python scripts/render_handbook_traceability.py --check` - exit 0.

Confirm the requirement is live by temporarily deleting the `ungranted_note` line from one record, running `--check`, seeing it fail, and restoring it. Report the error text you saw. Confirm with `git status --short` that the record is unmodified before you commit.

- [ ] **Step 6: Commit**

```bash
git add scripts/audit_checks.py tests/scripts/test_audit_checks.py
git commit -m "feat: require the note on exactly the records the rule silences

Refs #26"
```

Expand the message: an absent key on a silenced record reads as a claim rather than as an omission, which is the hazard `needs:` still has and this field no longer does.

---

### Task 4: `audit-core` defers to the field

**Files:**
- Modify: `.agents/skills/audit-core/SKILL.md`

This is a prompt change and it belongs in its own commit, separate from code.

- [ ] **Step 1: Replace the derived-rule sentence in step 1**

Find this sentence at the end of the `Never install into the target; reconstruct outside it` paragraph:

```
Where the run holds no grant, the checks whose only tools need one are `no-evidence`, never clean.
```

Replace it with:

```
Where the run holds no grant, a check whose every tool in this partition's language needs one is `no-evidence (not-permitted)` rather than clean - **unless its record carries an `ungranted_note`, which says what the check still answers without the grant.** That field is required on exactly the records this rule would silence, so the answer is there to read rather than inferred: a note naming a source-reading, syntax-tree or registry pass means the check reports the domain's own status with the missing axis named, and only the sentinel `none` means the whole question is unanswerable here. Assigning `no-evidence` to a check whose record says otherwise records an unanswered question that the clone could have answered, which is the same false negative as reporting a tool's empty output as a clean result.
```

- [ ] **Step 2: Add the field to the authoring frontmatter list**

In the `**Checks are records, not prose.**` paragraph, the list reads `(`id`, `domain`, `locality`, `handbook`, `tooling`, `needs`, `optin`)`. Insert `ungranted_note` between `needs` and `optin`.

Then, in the same paragraph, after the sentence ending `and explained where an agent reads what to do instead.`, add:

```
A record whose every tool in some language needs a grant also carries an `ungranted_note` saying what the check still answers when that grant is withheld, because what a tool needs and what a check can do without it are different claims, and deriving the second from the first is wrong wherever the check has an axis that needs no tool at all.
```

- [ ] **Step 3: Check the anchors are unique and backtick-free**

Task 6 will pin ledger rows to phrases from the text above. Verify each of these occurs **exactly once** in `audit-core/SKILL.md` and contains no backtick:

```bash
for a in "says what the check still answers without the grant" "required on exactly the records this rule would silence" "what a tool needs and what a check can do without it are different claims"; do
  printf '%s -> %s\n' "$a" "$(grep -c -- "$a" .agents/skills/audit-core/SKILL.md)"
done
```

Expected: `1` for each. If any is `0`, the wording above was not inserted verbatim; if any is `2`, shorten it until unique.

- [ ] **Step 4: Run the gate and commit**

Run: `uv run pytest tests/ -q` and `uv run python scripts/render_handbook_traceability.py --check`.

Commit `.agents/skills/audit-core/SKILL.md` alone. The message says WHY: the engine was deriving a check-level conclusion from tool-level facts, and the derivation is wrong wherever a check has a tool-free axis, which five records had already resorted to contradicting in prose.

---

### Task 5: The sweep defers to the field

**Files:**
- Modify: `.agents/skills/audit/SKILL.md`

Its own commit, for the same reason as Task 4.

- [ ] **Step 1: The step 0 grants bullet**

In the bullet beginning `**Grants for tooling that needs more than a read-only clone`, find:

```
Where a grant is withheld, the checks whose only tools need it are `no-evidence (not-permitted)`, which is a different report from `no-evidence (tool-unavailable)` and must not be merged into it.
```

Replace with:

```
Where a grant is withheld, a check whose only tools need it is `no-evidence (not-permitted)` - which is a different report from `no-evidence (tool-unavailable)` and must not be merged into it - **unless its record carries an `ungranted_note`, in which case the check answers on the axis that note names and reports the domain's own status with the missing evidence stated.** A withheld grant is not the same as an unanswerable question, and on the current record set most of the checks it silences can still answer something.
```

- [ ] **Step 2: The fan-out brief**

In the long detection-tooling bullet, find:

```
and where the grant is absent, report `no-evidence (not-permitted)` rather than running the tool against an unresolved graph, which returns an empty result that reads exactly like a clean one.
```

Replace with:

```
and where the grant is absent, do not run the tool against an unresolved graph, which returns an empty result that reads exactly like a clean one - read the record's `ungranted_note` instead, which every record this applies to carries: it names what the check still answers with nothing installed, and only the sentinel `none` licenses reporting `no-evidence (not-permitted)` for the check as a whole.
```

- [ ] **Step 3: Tell the domain agent the field exists**

In the fan-out payload list, the bullet beginning `**The grants, named explicitly, including the ones withheld**` ends with a sentence about a withheld grant turning "the tool did not run" into `no-evidence (not-permitted)`. Append to that bullet:

```
A withheld grant is where the record's `ungranted_note` becomes load-bearing rather than decorative, so an agent handed a withheld grant reads that field before it assigns any status.
```

- [ ] **Step 4: Run the gate and commit**

Run: `uv run pytest tests/ -q` - `tests/test_sweep_obligations.py` verifies every quotation in the ledger is still verbatim from one of the two files, so a reworded sentence a ledger row quotes fails here. If it does, Task 6 is where the row is updated; note the failure and fix it there rather than reverting this task.

Commit `.agents/skills/audit/SKILL.md` alone, with a WHY message.

---

### Task 6: The obligations ledger

**Files:**
- Modify: `docs/audit/sweep-obligations.md`

`CLAUDE.md` requires this file be checked whenever `audit-core/SKILL.md` or `audit/SKILL.md` changes. Tasks 4 and 5 changed both, so this task is not optional.

- [ ] **Step 1: Add a row per new obligation**

Append to the obligations table. The `Disposition` value must come from the vocabulary table in the same file. Both new obligations are **restated**, because the sweep carries them in its own words.

```
| A record says what it answers without a grant | `says what the check still answers without the grant` | restated | Step 0's grants bullet and the fan-out brief both carry the deferral: a withheld grant produces `no-evidence (not-permitted)` only where the record's `ungranted_note` is the sentinel, and otherwise the check answers on the axis the note names with the missing evidence stated. The fan-out payload's grants bullet also tells the domain agent to read that field before assigning any status, because the sweep resolves the grants at step 0 and a dispatched agent that is not told a withheld grant is not the end of the question will treat it as one. |
| The note is required where the rule would silence the check | `required on exactly the records this rule would silence` | restated | Restated as a fact the sweep can rely on rather than a rule it enforces: the brief tells a domain agent that every record the withheld-grant rule applies to carries the field, which is what makes "read the note" a safe instruction rather than one that fails on a record that omitted it. The enforcement itself is `scripts/audit_checks.py` and its integrity gate, outside either skill. |
```

- [ ] **Step 2: Check the third anchor needs no row**

The `what a tool needs and what a check can do without it are different claims` sentence added in Task 4 step 2 is authoring guidance for whoever writes a record, not an instruction to a run. Read the existing rows for how authoring obligations are dispositioned - if the ledger already has a row covering the record schema's authoring rules, extend it rather than adding a fourth. If it does not, add a row with disposition **out of scope**, and say which of the two out-of-scope cases applies: the sweep reaches the step but the obligation serves record authoring rather than any step the sweep runs.

- [ ] **Step 3: Run the ledger tests**

Run: `uv run pytest tests/test_sweep_obligations.py -q`

This checks that each anchor occurs in `audit-core/SKILL.md` exactly once, that each row's disposition is in the vocabulary, that each justification is non-empty, and that every quotation in the file is verbatim from one of the two skills. If Task 5 reworded a sentence an existing row quotes, fix that row here.

- [ ] **Step 4: Run everything and commit**

Run: `uv run pytest tests/ -q` and `uv run python scripts/render_handbook_traceability.py --check`.

Commit `docs/audit/sweep-obligations.md` alone.

---

### Task 7: `CLAUDE.md`, and the stale-prose pass

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add the field to the check-records paragraph**

In the `## Check records` section, the first sentence lists the frontmatter fields. Add `ungranted_note` after `needs`, described as required when every tool in a language carries a tier. Then add a paragraph after the existing `needs` paragraph:

```
`ungranted_note` is the third claim, and it is about the check rather than about a tool. `needs` says what each tool requires; the engine turns that into a conclusion about the check - every tool needs a grant, so a withheld grant means `no-evidence` - and that derivation is wrong wherever the check has an axis needing no tool. Five records had resorted to contradicting their own frontmatter in prose before this field existed. It is required on exactly the records the rule would silence and rejected as vacuous elsewhere, so absence is never a silent claim the way an absent `needs` tier still is. The value is either what still answers or the sentinel `none`; the loader rejects `None`, `NONE`, `null` and an empty value by name, because YAML turns the first two into ordinary strings that read as a fallback claim and the last two into nothing at all. `tests/scripts/test_audit_checks.py` holds a floor on how many records say something real, which is the only guard against satisfying the requirement with `none` everywhere - it cannot tell a correct `none` from a lazy one.
```

- [ ] **Step 2: The stale-prose pass**

Per `CLAUDE.md`, scope this by blast radius rather than by the diff, and dispatch it to a subagent that has not seen the implementation. Pass the subagent the worktree's absolute root and require it to confirm `git rev-parse --show-toplevel` matches before reading.

Ask it to grep for and read every mention of: the frontmatter field list, the phrase `no-evidence`, the phrase `not-permitted`, `needs:`, and the sentence patterns Tasks 4 and 5 replaced. Specifically check whether any record, skill or doc still asserts that a withheld grant makes a check `no-evidence` without qualification, and whether `arch/complexity-gate`'s deleted paragraph is referenced anywhere that now dangles.

- [ ] **Step 3: Fix what it finds, then run everything**

Run: `uv run pytest tests/ -q`, `uv run python scripts/render_handbook_traceability.py --check`, `uv run ruff check . && uv run ruff format --check .`

- [ ] **Step 4: Commit**

Commit `CLAUDE.md` and anything the stale-prose pass corrected, naming in the message what the pass found - or that it found nothing, which is also worth recording.
