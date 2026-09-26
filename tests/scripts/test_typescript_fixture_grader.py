"""Tests for the TypeScript half of scripts/grade_python_fixture_run.py (#181).

Offline, as the Python grader tests are: every run here is a dict literal or a
small JSON file this module writes itself, shaped like the files
`run_python_fixture_lens.py` writes for the npm and pnpm partitions, and none of
them reads the gitignored `fixtures/typescript/results/` tree, which a fresh
clone or a CI run never has.
"""

import json

import grade_python_fixture_run as grader
import pytest
import python_fixture_spec as spec
from run_python_fixture_lens import routed_invocations


def _run(partition: str, grant: str, results: list[dict]) -> dict:
    return {"partition": partition, "grant": grant, "results": results}


def _row(rows, check: str):
    matching = [r for r in rows if r.check == check]
    assert len(matching) == 1, [r.check for r in rows]
    return matching[0]


def test_a_typescript_row_counts_the_typescript_markers_for_a_shared_seed_name():
    """`cycle` names Python imports in one table and TypeScript `from` clauses in
    the other, so the table has to follow the run's language.

    Read through the Python table, this row would count `import
    fixture_app.infra.store`, which no TypeScript output can contain, and report
    a planted cycle as a zero.
    """
    stdout = 'model.ts: from "../infra/store"\nstore.ts: from "../domain/model"\n'
    run = _run(
        "npm",
        "none",
        [
            {
                "check": "arch/cycles",
                "tool": "madge",
                "ran": True,
                "status": "ok",
                "stdout": stdout,
                "stderr": "",
            }
        ],
    )
    row = _row(grader.grade_rows(run), "arch/cycles")
    assert set(row.signals) == set(spec.TS_SEED_MARKERS["cycle"])
    assert all(count == 1 for count in row.signals.values())
    assert not set(row.signals) & set(spec.SEED_MARKERS["cycle"])


def test_a_python_row_still_counts_the_python_markers():
    stdout = "import fixture_app.infra.store\nimport fixture_app.domain.model\n"
    run = _run(
        "uv",
        "target-execution",
        [
            {
                "check": "arch/cycles",
                "tool": "pydeps",
                "ran": True,
                "status": "ok",
                "stdout": stdout,
                "stderr": "",
            }
        ],
    )
    row = _row(grader.grade_rows(run), "arch/cycles")
    assert set(row.signals) == set(spec.SEED_MARKERS["cycle"])


def test_every_typescript_row_the_harness_can_produce_resolves_a_findings_stream():
    """The lookup reads the TypeScript routes, not only the Python enumeration.

    Built from the Python sources alone, every TypeScript row would read as a
    stale pair and be graded as an empty stream on every run.
    """
    unresolved = sorted(
        (inv.check, inv.tool)
        for inv in routed_invocations("typescript")
        if grader._findings_stream_for(
            {"check": inv.check, "tool": inv.tool}, "typescript"
        )
        == grader.UNRESOLVED_FINDINGS_STREAM
    )
    assert not unresolved


def test_the_lookup_is_per_language_rather_than_merged():
    """A TypeScript pair asked about as Python is not answered from the other table."""
    entry = {"check": "deps/freshness", "tool": "pnpm outdated"}
    assert grader._findings_stream_for(entry) == grader.UNRESOLVED_FINDINGS_STREAM
    assert grader._findings_stream_for(entry, "typescript") == "stdout"


def test_a_typescript_entry_without_the_field_resolves_alone_insufficient():
    """`deps/freshness`'s `pnpm outdated` route carries the field, so a results
    file older than the key still marks the outdated list as a candidate."""
    run = _run(
        "pnpm",
        "target-execution",
        [
            {
                "check": "deps/freshness",
                "tool": "pnpm outdated",
                "ran": True,
                "status": "ok",
                "reason": "",
                "stdout": "typescript (dev) 5.9.3 7.0.2",
                "stderr": "",
            }
        ],
    )
    row = _row(grader.grade_rows(run), "deps/freshness")
    assert row.observations[0].findings_stream == "stdout"
    assert row.observations[0].alone_insufficient
    assert "not the check's answer alone" in grader.render([row])


@pytest.mark.parametrize("partition", spec.TS_PARTITIONS)
def test_grade_rows_covers_every_typescript_expectation_of_the_partition(partition):
    rows = grader.grade_rows(_run(partition, "target-execution", []))
    assert [r.check for r in rows] == [
        e.check for e in spec.expectations_for(partition)
    ]
    assert all(r.verdict == "unjudged" for r in rows)


def test_a_typescript_none_run_is_graded_against_the_ungranted_claim():
    expectation = next(
        e
        for e in spec.expectations_for("pnpm")
        if e.check == "deps/licenses" and e.ungranted
    )
    row = _row(grader.grade_rows(_run("pnpm", "none", [])), "deps/licenses")
    assert row.claim == expectation.ungranted
    granted = _row(
        grader.grade_rows(_run("pnpm", "target-execution", [])), "deps/licenses"
    )
    assert granted.claim == expectation.claim


def test_a_typescript_orphan_names_the_typescript_table():
    run = _run(
        "npm",
        "none",
        [{"check": "arch/not-a-check", "tool": "madge", "ran": False, "status": ""}],
    )
    row = _row(grader.grade_rows(run), "arch/not-a-check")
    assert row.verdict == "orphan"
    assert "TS_EXPECTATIONS" in row.claim


def test_a_python_orphan_still_names_the_python_table():
    run = _run(
        "uv",
        "none",
        [{"check": "arch/not-a-check", "tool": "ruff", "ran": False, "status": ""}],
    )
    row = _row(grader.grade_rows(run), "arch/not-a-check")
    assert "out of EXPECTATIONS," in row.claim
    assert "TS_EXPECTATIONS" not in row.claim


def test_a_run_on_a_partition_no_language_names_fails_naming_it():
    with pytest.raises(ValueError, match="yarn"):
        grader.grade_rows(_run("yarn", "none", []))


def test_main_grades_python_and_typescript_runs_side_by_side(tmp_path):
    for partition in ("npm", "pnpm", "uv"):
        (tmp_path / f"{partition}-none.json").write_text(
            json.dumps(_run(partition, "none", []))
        )
    assert grader.main([str(tmp_path)]) == 0
    worksheet = (tmp_path / "worksheet.md").read_text()
    assert "| deps/freshness | pnpm | none |" in worksheet
    assert "| deps/freshness | npm | none |" in worksheet
    assert "| deps/freshness | uv | none |" in worksheet
