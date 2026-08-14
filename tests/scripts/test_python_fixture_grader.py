"""Tests for scripts/grade_python_fixture_run.py (#45).

None of these read the gitignored `fixtures/python/results/` tree:
`build_python_fixtures.py` writes it, nothing here regenerates it, and a fresh
clone or a CI run never has it - the same reason `test_python_fixture_build.py`
and `test_python_fixture_harness.py` build their own inputs rather than reading
a materialized one. Every run here is a dict literal or a small JSON file this
test file writes itself, shaped like a real one (confirmed once by hand against
`fixtures/python/results/pip-none.json`, which is why it predates `versions`).
"""

import json
import re
from pathlib import Path

import grade_python_fixture_run as grader_module
import pytest
import python_fixture_spec


@pytest.fixture
def grader():
    """The module under test, referenced by name as its own tests do."""
    return grader_module


@pytest.fixture
def spec():
    """`python_fixture_spec`, for tests that read its definitions directly."""
    return python_fixture_spec


def test_a_seed_marker_absent_from_the_findings_stream_counts_zero(grader):
    entry = {"stdout": "no issues found", "stderr": "", "ran": True}
    assert grader.seed_signals(entry, ("eval(",)) == {"eval(": 0}


def test_a_seed_marker_is_counted_in_the_stream_the_entry_names(grader):
    entry = {
        "stdout": "",
        "stderr": "DEP002 markupsafe",
        "ran": True,
        "findings_stream": "stderr",
    }
    assert grader.seed_signals(entry, ("markupsafe",)) == {"markupsafe": 1}


def test_findings_stream_is_looked_up_when_the_entry_carries_none(grader):
    """Real results entries never carry `findings_stream` themselves.

    `run_python_fixture_lens.py` never writes the key into a row (confirmed
    against `fixtures/python/results/pip-none.json`), so `observations_for` has
    to look the stream up from the harness's own `INVOCATIONS` table rather
    than default to stdout - the default that reads a deptry run backwards.
    """
    run = {
        "partition": "pip",
        "grant": "none",
        "results": [
            {
                "check": "deps/hygiene",
                "tool": "deptry",
                "ran": True,
                "status": "ok",
                "stdout": "",
                "stderr": "DEP002 six\nDEP003 markupsafe",
            }
        ],
    }
    entries = grader.observations_for(run, "deps/hygiene")
    assert entries[0]["findings_stream"] == "stderr"
    assert grader.seed_signals(entries[0], ("markupsafe",)) == {"markupsafe": 1}


def test_observations_for_raises_when_the_pair_is_not_in_the_invocation_table(grader):
    run = {
        "partition": "uv",
        "grant": "none",
        "results": [{"check": "deps/hygiene", "tool": "no-such-tool", "ran": False}],
    }
    with pytest.raises(ValueError, match="no-such-tool"):
        grader.observations_for(run, "deps/hygiene")


def test_observations_for_only_returns_entries_for_the_named_check(grader):
    run = {
        "partition": "uv",
        "grant": "none",
        "results": [
            {"check": "deps/hygiene", "tool": "deptry", "ran": False},
            {"check": "deps/licenses", "tool": "pip-licenses", "ran": False},
        ],
    }
    entries = grader.observations_for(run, "deps/licenses")
    assert [e["tool"] for e in entries] == ["pip-licenses"]


def test_a_row_pairs_the_claim_with_the_observation_and_leaves_the_verdict_open(
    grader,
):
    run = {
        "partition": "uv",
        "grant": "none",
        "versions": {},
        "results": [
            {
                "check": "security/dangerous-calls",
                "tool": "bandit",
                "ran": True,
                "status": "ok",
                "stdout": "B307 eval(",
                "stderr": "",
            }
        ],
    }
    rows = [r for r in grader.grade_rows(run) if r.check == "security/dangerous-calls"]
    assert rows
    assert rows[0].verdict == "unjudged"
    assert rows[0].signals


def test_grade_rows_covers_every_expectation_the_partition_carries(grader, spec):
    run = {"partition": "poetry", "grant": "none", "results": []}
    rows = grader.grade_rows(run)
    assert len(rows) == len(spec.expectations_for("poetry"))


def test_an_orphan_entry_gets_its_own_row_instead_of_vanishing(grader, spec):
    """A results entry no expectation names must not disappear silently.

    Without a row for it, a stale results file surviving a check renamed or
    removed out of `EXPECTATIONS` would have its now-orphaned entry dropped
    with no row, no error and no count discrepancy - `grade_rows` would still
    return exactly `len(expectations_for(partition))` rows, reading as full
    coverage of a run it did not fully account for.
    """
    run = {
        "partition": "uv",
        "grant": "none",
        "results": [
            {
                "check": "made/up-check",
                "tool": "ghost-tool",
                "ran": True,
                "status": "ok",
                "stdout": "FOUND SOMETHING",
                "stderr": "",
            }
        ],
    }
    rows = grader.grade_rows(run)
    assert len(rows) == len(spec.expectations_for("uv")) + 1
    orphan = next(r for r in rows if r.check == "made/up-check")
    assert orphan.verdict == "orphan"
    assert orphan.observations
    assert orphan.observations[0].tool == "ghost-tool"
    text = grader.render(rows)
    assert "made/up-check" in text
    assert "ghost-tool" in text


def test_an_orphan_entry_does_not_raise_even_when_the_tool_is_unknown(grader):
    """The (check, tool) pair here is not in `INVOCATIONS` either.

    `observations_for` raises on an unknown pair (by design, for a genuine
    caller error); an orphan row must not go through that lookup at all, since
    an orphan is unknown to the harness by construction.
    """
    run = {
        "partition": "uv",
        "grant": "none",
        "results": [
            {"check": "made/up-check", "tool": "ghost-tool", "ran": True},
        ],
    }
    grader.grade_rows(run)  # must not raise


def test_grade_rows_groups_multiple_orphan_tools_under_one_row_per_check(grader):
    run = {
        "partition": "uv",
        "grant": "none",
        "results": [
            {"check": "made/up-check", "tool": "ghost-tool-a", "ran": True},
            {"check": "made/up-check", "tool": "ghost-tool-b", "ran": True},
        ],
    }
    rows = [r for r in grader.grade_rows(run) if r.check == "made/up-check"]
    assert len(rows) == 1
    assert {o.tool for o in rows[0].observations} == {"ghost-tool-a", "ghost-tool-b"}


def test_a_dependency_level_seed_has_no_marker_to_search_for(grader, spec):
    """`vulnerable` names a CVE floor, not a literal substring.

    `SEED_MARKERS` deliberately carries no entry for a dependency-level seed -
    what proves it moves with a registry or a CVE database - so the mechanical
    signal is empty even though the run did produce an observation.
    """
    expectation = next(
        e for e in spec.EXPECTATIONS if e.check == "deps/vulnerabilities"
    )
    assert "vulnerable" not in spec.SEED_MARKERS
    run = {
        "partition": "uv",
        "grant": "target-execution",
        "results": [
            {
                "check": "deps/vulnerabilities",
                "tool": "pip-audit",
                "ran": True,
                "status": "ok",
                "stdout": "CVE-2024-22195 jinja2",
                "stderr": "",
            }
        ],
    }
    row = grader.grade_row(expectation, run)
    assert row.signals == {}
    assert row.observations[0].tool == "pip-audit"


def test_an_absence_expectation_carries_no_seeds_to_search_for(grader, spec):
    expectation = next(e for e in spec.EXPECTATIONS if e.form == "absence")
    run = {
        "partition": expectation.partitions[0],
        "grant": "target-execution",
        "results": [],
    }
    row = grader.grade_row(expectation, run)
    assert row.signals == {}
    assert row.seeds == ()


def test_an_ungranted_run_is_graded_against_the_ungranted_claim(grader, spec):
    """A `none` run of a check whose grant moves the answer reads the record's
    ungranted prose, not the granted one - grading it against `claim` would
    read a correct ungranted deptry run as a tool defect, which is the
    `Expectation.ungranted` docstring's own example.
    """
    expectation = next(
        e
        for e in spec.EXPECTATIONS
        if e.check == "deps/hygiene" and "pipenv" not in e.partitions
    )
    assert expectation.ungranted
    run = {"partition": "pip", "grant": "none", "results": []}
    row = grader.grade_row(expectation, run)
    assert row.claim == expectation.ungranted
    assert row.claim != expectation.claim


def test_a_granted_run_is_graded_against_the_granted_claim(grader, spec):
    expectation = next(
        e
        for e in spec.EXPECTATIONS
        if e.check == "deps/hygiene" and "pipenv" not in e.partitions
    )
    run = {"partition": "pip", "grant": "target-execution", "results": []}
    row = grader.grade_row(expectation, run)
    assert row.claim == expectation.claim


def test_a_none_run_falls_back_to_the_granted_claim_when_no_ungranted_is_set(
    grader, spec
):
    expectation = next(
        e for e in spec.EXPECTATIONS if e.check == "deps/vulnerabilities"
    )
    assert expectation.ungranted == ""
    run = {"partition": "uv", "grant": "none", "results": []}
    row = grader.grade_row(expectation, run)
    assert row.claim == expectation.claim


def test_render_shows_the_mechanical_columns_for_a_graded_row(grader):
    run = {
        "partition": "uv",
        "grant": "target-execution",
        "results": [
            {
                "check": "security/dangerous-calls",
                "tool": "bandit",
                "ran": True,
                "status": "ok",
                "reason": "",
                "stdout": "B307 eval(",
                "stderr": "",
            }
        ],
    }
    rows = [r for r in grader.grade_rows(run) if r.check == "security/dangerous-calls"]
    text = grader.render(rows)
    assert "security/dangerous-calls" in text
    assert "bandit: ok" in text
    assert "eval(=1" in text
    assert text.strip().endswith("| unjudged |")


def test_render_covers_every_status_and_reason_shape(grader):
    """Both `_observations_cell` branches: a reason beside a status, and a
    tool that never ran at all.
    """
    run = {
        "partition": "uv",
        "grant": "none",
        "results": [
            {
                "check": "security/dangerous-calls",
                "tool": "bandit",
                "ran": False,
                "status": "no-evidence",
                "reason": "not-permitted",
            },
            {
                "check": "security/dangerous-calls",
                "tool": "ruff",
                "ran": False,
                "status": "",
                "reason": "",
            },
        ],
    }
    rows = [r for r in grader.grade_rows(run) if r.check == "security/dangerous-calls"]
    text = grader.render(rows)
    assert "bandit: no-evidence (not-permitted)" in text
    assert "ruff: (not run)" in text


def test_render_escapes_a_claim_containing_a_literal_pipe(grader, spec):
    """A cell that keeps its literal `|` splits the row into an extra column.

    Counting unescaped pipes (`re.findall` skipping any preceded by `\\`) is
    the check that actually catches that: a naive `str.count("|")` would still
    count an escaped pipe as one, so it cannot tell a well-formed row from a
    broken one the way a Markdown table renderer does.
    """
    expectation = next(e for e in spec.EXPECTATIONS if e.check == "arch/martin-metrics")
    assert "|" in expectation.claim
    run = {"partition": "uv", "grant": "target-execution", "results": []}
    row = grader.grade_row(expectation, run)
    text = grader.render([row])
    lines = text.splitlines()
    header_columns = len(re.findall(r"(?<!\\)\|", lines[0]))
    data_line = next(line for line in lines if line.startswith("| arch/martin-metrics"))
    data_columns = len(re.findall(r"(?<!\\)\|", data_line))
    assert data_columns == header_columns
    assert "\\|" in data_line


def test_render_reports_no_observation_when_the_check_never_ran(grader, spec):
    expectation = next(e for e in spec.EXPECTATIONS if e.check == "arch/martin-metrics")
    run = {"partition": "uv", "grant": "target-execution", "results": []}
    row = grader.grade_row(expectation, run)
    text = grader.render([row])
    assert "(no observation)" in text


def test_load_run_does_not_require_versions(grader, tmp_path):
    """A run predating the `versions` key is still a run worth grading.

    `fixtures/python/results/pip-none.json` is a real written run that carries
    no `versions` key; this file writes its own copy of that shape rather than
    reading the gitignored original, which a fresh clone never has.
    """
    path = tmp_path / "pip-none.json"
    path.write_text(
        json.dumps(
            {
                "grant": "none",
                "materialization": [],
                "partition": "pip",
                "results": [
                    {
                        "check": "deps/hygiene",
                        "tool": "deptry",
                        "ran": False,
                        "status": "no-evidence",
                        "reason": "not-permitted",
                        "record_argv": ["deptry"],
                    }
                ],
                "source": "fixtures/python/pip",
            }
        )
    )
    run = grader.load_run(path)
    assert run["partition"] == "pip"
    assert run["grant"] == "none"
    assert "versions" not in run
    rows = grader.grade_rows(run)
    assert rows


def test_load_run_names_every_missing_required_key(grader, tmp_path):
    path = tmp_path / "broken.json"
    path.write_text(json.dumps({"grant": "none"}))
    with pytest.raises(ValueError, match=r"partition.*results|results.*partition"):
        grader.load_run(path)


def test_load_run_rejects_a_json_array(grader, tmp_path):
    path = tmp_path / "not-an-object.json"
    path.write_text(json.dumps([1, 2, 3]))
    with pytest.raises(ValueError, match="JSON object"):
        grader.load_run(path)


def _write_run(path: Path, *, partition: str, grant: str) -> None:
    path.write_text(
        json.dumps(
            {
                "grant": grant,
                "materialization": [],
                "partition": partition,
                "results": [
                    {
                        "check": "deps/hygiene",
                        "tool": "deptry",
                        "ran": False,
                        "status": "no-evidence",
                        "reason": "not-permitted",
                        "record_argv": ["deptry"],
                    }
                ],
                "source": f"fixtures/python/{partition}",
            }
        )
    )


def test_main_writes_a_worksheet_for_every_run_in_the_directory(grader, tmp_path):
    _write_run(tmp_path / "pip-none.json", partition="pip", grant="none")
    exit_code = grader.main([str(tmp_path)])
    assert exit_code == 0
    out = tmp_path / "worksheet.md"
    assert out.exists()
    text = out.read_text()
    assert text.startswith("| Check |")
    assert "deps/hygiene" in text


def test_main_writes_to_the_requested_output_path(grader, tmp_path):
    _write_run(tmp_path / "pip-none.json", partition="pip", grant="none")
    out_path = tmp_path / "custom.md"
    exit_code = grader.main([str(tmp_path), "--out", str(out_path)])
    assert exit_code == 0
    assert out_path.exists()


def test_main_errors_when_the_directory_holds_no_runs(grader, tmp_path):
    with pytest.raises(SystemExit):
        grader.main([str(tmp_path)])


def test_main_errors_when_the_directory_does_not_exist(grader, tmp_path):
    with pytest.raises(SystemExit):
        grader.main([str(tmp_path / "does-not-exist")])
