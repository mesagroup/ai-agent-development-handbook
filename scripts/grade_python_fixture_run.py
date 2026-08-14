"""Grade a fixture run against the expectations written before it (#45).

`run_python_fixture_lens.py` classifies each result into the engine's status
vocabulary - `ok`, `no-evidence` with a reason, or the absence of a run at all.
That is triage: it says a tool ran and produced something, not that it produced
the truth. The grade this module computes is whether the observation matches
the expectation `python_fixture_spec.py` wrote down before the run, and it
stops at exactly that: pairing the claim with the mechanical signal, never
inferring a verdict from a substring match. `Expectation.claim` is prose
written for a human reader, and a marker's count proves only that the byte
sequence occurred somewhere in a tool's output - never that the finding it
names is the one the tool actually reported. A grader that guessed would
manufacture exactly the false-clean result this whole round exists to catch, so
every `Row` here carries `verdict = "unjudged"` and nothing computes past it.

A results entry never carries its own `findings_stream`: `run_python_fixture_lens.py`
uses the field internally to classify a row and never writes it into the row
dict (confirmed against `fixtures/python/results/pip-none.json`, a real written
run). So `observations_for` looks the stream up from the harness's own
`INVOCATIONS` table rather than defaulting to stdout - the default that scores
deptry, which writes its whole report to stderr, as having found nothing.

`Expectation.ungranted` is the second thing a naive grader would get wrong: it
holds the answer a `none` run should read where the grant moves the answer, and
grading a `none` run against `claim` instead reads a correct ungranted deptry
run - which reports `markupsafe` as DEP001 rather than DEP003 - as a tool
defect. `grade_row` selects between the two by the run's own `grant`.

Usage:
    uv run python scripts/grade_python_fixture_run.py fixtures/python/results
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from python_fixture_spec import SEED_MARKERS, Expectation, expectations_for
from run_python_fixture_lens import INVOCATIONS

# One results JSON, exactly as the harness wrote it. A plain dict rather than a
# dataclass or a TypedDict instance: `grade_rows` is exercised directly against
# a dict literal in its own tests, and wrapping loaded JSON in a constructor
# would force every caller through a step the tests never take.
Run = dict[str, object]

REQUIRED_RUN_KEYS = ("grant", "partition", "results")

# What each (check, tool) pair reports its findings on, read from the harness's
# own `Invocation` table rather than copied here. A results entry never carries
# this itself, so the table is the only source, and a second copy of it here
# would be free to drift from the one the harness actually runs against.
_FINDINGS_STREAM: dict[tuple[str, str], str] = {
    (invocation.check, invocation.tool): invocation.findings_stream
    for invocation in INVOCATIONS
}


def load_run(path: Path) -> Run:
    """Parse one results JSON exactly as the harness wrote it.

    Returns the parsed mapping itself rather than a wrapping class, because
    every consumer here reads it by key and `grade_rows`'s own tests construct
    a run as a plain dict literal.

    `versions` is never required: `fixtures/python/results/pip-none.json` is a
    real written run that predates the key the harness added later, and a run
    missing it is still a run worth grading.
    """
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object, got {type(data).__name__}")
    missing = [key for key in REQUIRED_RUN_KEYS if key not in data]
    if missing:
        raise ValueError(f"{path}: missing required key(s) {missing}")
    return data


def _findings_stream_for(entry: dict[str, object]) -> str:
    """Which stream this entry reports findings on.

    The entry's own `findings_stream` where a caller has already set one - the
    tests that pin `seed_signals` directly do this, and neither carries a
    `check`/`tool` pair a lookup could resolve. Otherwise, the stream the
    harness's own `INVOCATIONS` table says this (check, tool) pair uses. Raises
    rather than defaulting on an unknown pair: a results entry naming a
    (check, tool) the harness never transcribed is not a fact this module can
    answer for, and defaulting to stdout would silently misread it exactly the
    way this whole field exists to prevent.
    """
    if "findings_stream" in entry:
        return str(entry["findings_stream"])
    key = (str(entry.get("check", "")), str(entry.get("tool", "")))
    if key not in _FINDINGS_STREAM:
        raise ValueError(
            f"no invocation for check={key[0]!r} tool={key[1]!r}; "
            "run_python_fixture_lens.INVOCATIONS carries no findings_stream to "
            "look up for this (check, tool) pair"
        )
    return _FINDINGS_STREAM[key]


def observations_for(run: Run, check: str) -> list[dict[str, object]]:
    """Every result entry this run recorded for one check.

    Each entry comes back with `findings_stream` filled in wherever it was
    missing, so `seed_signals` always reads the stream the tool actually
    reports on rather than the stdout default that reads a deptry run
    backwards.
    """
    entries = []
    for entry in run.get("results", []):
        if entry.get("check") != check:
            continue
        entries.append({**entry, "findings_stream": _findings_stream_for(entry)})
    return entries


def seed_signals(entry: dict[str, object], seeds: Sequence[str]) -> dict[str, int]:
    """Count each seed marker in the stream this entry reports findings on.

    The stream matters: a tool that writes its report to stderr scores zero on
    stdout, which is indistinguishable from a tool that ran and found nothing.
    """
    stream = str(entry.get(str(entry.get("findings_stream", "stdout")), ""))
    return {seed: stream.count(seed) for seed in seeds}


@dataclass(frozen=True)
class Observation:
    """One tool's answer to one check, as the run recorded it."""

    tool: str
    ran: bool
    status: str
    reason: str


@dataclass(frozen=True)
class Row:
    """One expectation, graded against one whole run.

    `verdict` stays `"unjudged"` - see the module docstring. `signals` is the
    marker counts summed across every observation this run made of the check;
    a seed category `SEED_MARKERS` carries no marker for (a dependency-level
    seed like `vulnerable` or `stale`, which no literal substring can name)
    contributes nothing, the same as an expectation naming no seed at all.
    """

    check: str
    partition: str
    grant: str
    form: str
    claim: str
    seeds: tuple[str, ...]
    observations: tuple[Observation, ...]
    signals: dict[str, int]
    verdict: str = "unjudged"


def _claim_for(expectation: Expectation, run: Run) -> str:
    """The prose to grade this run against.

    `expectation.claim` is the answer under a grant; `expectation.ungranted` is
    set on exactly the checks where a `none` run answers something else, per
    the field's own docstring. A `none` run graded against `claim` on one of
    those checks would read a correct ungranted answer as a tool defect -
    `deps/hygiene` reporting `markupsafe` as DEP001 rather than DEP003 under no
    grant is the record's own example. Where `ungranted` is unset, the grant
    does not move the answer (either no tool needs one, or the unset default
    already covers the no-evidence-not-permitted case), so `claim` holds either
    way.
    """
    if run.get("grant") == "none" and expectation.ungranted:
        return expectation.ungranted
    return expectation.claim


def grade_row(expectation: Expectation, run: Run) -> Row:
    """One expectation, paired with every observation this run made of it.

    A route whose reporting half runs as a second command (`then`, currently
    only `test/coverage-reach`'s `coverage.py` route) is a known blind spot
    rather than something worked around: `seed_signals` reads only an entry's
    own top-level `stdout`/`stderr`, and the second command's output sits
    nested under `entry["then"]` instead, invisible to a mechanical count here.
    """
    observations = observations_for(run, expectation.check)
    signals: dict[str, int] = {}
    for category in expectation.seeds:
        markers = SEED_MARKERS.get(category, ())
        for entry in observations:
            for marker, count in seed_signals(entry, markers).items():
                signals[marker] = signals.get(marker, 0) + count
    return Row(
        check=expectation.check,
        partition=str(run.get("partition", "")),
        grant=str(run.get("grant", "")),
        form=expectation.form,
        claim=_claim_for(expectation, run),
        seeds=expectation.seeds,
        observations=tuple(
            Observation(
                tool=str(entry.get("tool", "")),
                ran=bool(entry.get("ran", False)),
                status=str(entry.get("status", "")),
                reason=str(entry.get("reason", "")),
            )
            for entry in observations
        ),
        signals=signals,
    )


def grade_rows(run: Run) -> list[Row]:
    """Every expectation this run's partition carries, graded against it.

    One `Row` per expectation - `expectations_for` already scopes by partition,
    so a caller running this once per file in a results directory gets one row
    per expectation per partition per grant, never a set the published
    expectations do not cover.
    """
    partition = str(run.get("partition", ""))
    return [grade_row(expectation, run) for expectation in expectations_for(partition)]


_TABLE_HEADER = (
    "| Check | Partition | Grant | Form | Observations | Signals | Claim | Verdict |"
)
_TABLE_SEPARATOR = "| --- | --- | --- | --- | --- | --- | --- | --- |"


def _escape_cell(text: str) -> str:
    """One Markdown table cell holds one line; a claim never gets to add one.

    `|` closes a cell early - `arch/martin-metrics`'s own claim quotes
    `D = |A + I - 1| = 0.5` - and a literal newline splits the row, so both are
    escaped rather than trusted to be absent from prose nobody wrote for a
    table.
    """
    return text.replace("|", "\\|").replace("\n", " ")


def _observations_cell(observations: Sequence[Observation]) -> str:
    if not observations:
        return "(no observation)"
    parts = []
    for observation in observations:
        detail = f"{observation.tool}: {observation.status or '(not run)'}"
        if observation.reason:
            detail += f" ({observation.reason})"
        parts.append(detail)
    return "; ".join(parts)


def _signals_cell(signals: dict[str, int]) -> str:
    if not signals:
        return "(none)"
    return ", ".join(f"{marker}={count}" for marker, count in sorted(signals.items()))


def render(rows: Sequence[Row]) -> str:
    """One Markdown table, one line per row - a working worksheet, not a record.

    Not gated by `--check`: this is evidence about one dated run rather than a
    generated view of the tree, so there is nothing for an integrity check to
    compare it against.
    """
    lines = [_TABLE_HEADER, _TABLE_SEPARATOR]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row.check,
                    row.partition,
                    row.grant,
                    row.form,
                    _observations_cell(row.observations),
                    _signals_cell(row.signals),
                    _escape_cell(row.claim),
                    row.verdict,
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Grade every run in a results directory and write the worksheet.

    Args:
        argv: Command-line arguments; `None` reads `sys.argv`.

    Returns:
        `0` once the worksheet is written.
    """
    parser = argparse.ArgumentParser(
        description="Grade every fixture run in a results directory against the "
        "written-down expectations."
    )
    parser.add_argument(
        "results_dir", type=Path, help="directory holding the harness's *.json runs"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="where to write the worksheet (default: <results_dir>/worksheet.md)",
    )
    args = parser.parse_args(argv)

    if not args.results_dir.is_dir():
        parser.error(f"{args.results_dir} is not a directory")

    run_paths = sorted(args.results_dir.glob("*.json"))
    if not run_paths:
        parser.error(f"no *.json runs found under {args.results_dir}")

    rows: list[Row] = []
    for path in run_paths:
        rows.extend(grade_rows(load_run(path)))

    out_path = args.out or (args.results_dir / "worksheet.md")
    out_path.write_text(render(rows))
    print(f"graded {len(rows)} rows from {len(run_paths)} runs, written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
