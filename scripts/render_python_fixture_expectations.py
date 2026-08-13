"""Render `docs/audit/python-fixture-expectations.md` from the fixture spec (#45).

The published record is generated: edit `scripts/python_fixture_spec.py` and
re-render. `--check` compares the two and is what stops them drifting apart. It
prints nothing and exits 0 when they agree, matching
`render_handbook_traceability.py`; on drift it prints a unified diff to stderr
and exits 1.

Every number in the rendered document is computed from the module. A typed-in
count is a claim about the fixture that stops being true the first time a seed
is added, and nothing would fail - which is the same silence the spec module
exists to remove.

The grant axis is rendered as its own section rather than as a further column of
the expectation table: `Expectation.ungranted` is set on a minority of entries
and is prose long enough that a column would wrap unreadably. How the remaining
entries are read without the grant is derived from their check records rather
than stated per entry, so this renderer states the derivation once and reads no
record itself - `tests/scripts/test_python_fixture_spec.py` is what holds the
field to that derivation.

Usage:
    uv run python scripts/render_python_fixture_expectations.py          # write the md
    uv run python scripts/render_python_fixture_expectations.py --check  # fail if stale
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from python_fixture_spec import (
    DEPENDENCIES,
    EXPECTATIONS,
    FULL_PARTITION,
    PARTITIONS,
    VERIFIED_ON,
    Expectation,
    expectations_for,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "docs" / "audit" / "python-fixture-expectations.md"


def _display(path: Path) -> str:
    """The output path as a reader would type it, absolute only if it has to be.

    A path outside the repository - which is what a test pointing `OUT_PATH` at
    a temporary directory produces - is printed whole rather than raising, so a
    message about the file cannot become the failure.
    """
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _cell(text: str) -> str:
    """Collapse a claim to one table-safe line.

    A newline ends a GFM table row and a bare pipe opens a column, so a claim
    reaching a cell has to lose both. `--check` is no safety net here: it
    compares a fresh render against the committed one, and both would carry the
    same broken table.
    """
    return " ".join(str(text).split()).replace("|", "\\|")


def _partitions_cell(expectation: Expectation) -> str:
    """`all`, or the scoped partitions in `PARTITIONS` order.

    Ordered by the module's own tuple rather than by the expectation's, so two
    entries scoped to the same partitions read the same way whichever order they
    were written in.
    """
    if set(expectation.partitions) == set(PARTITIONS):
        return "all"
    scoped = [p for p in PARTITIONS if p in expectation.partitions]
    return ", ".join(f"`{p}`" for p in scoped)


def _seeds_cell(expectation: Expectation) -> str:
    return ", ".join(expectation.seeds) if expectation.seeds else "-"


def _partition_checks_cell(partition: str) -> str:
    """What one partition carries, said in full where that is short.

    The partition carrying every check says so rather than repeating the table
    below it, and the comparison is against the checks the expectations actually
    name rather than against `FULL_PARTITION`, so the cell stays true if the
    scoping moves.
    """
    carried = {e.check for e in expectations_for(partition)}
    if carried == {e.check for e in EXPECTATIONS}:
        return "every check in the expectation table"
    return ", ".join(f"`{c}`" for c in sorted(carried))


def render() -> str:
    """The whole published record, newline-terminated."""
    ungranted = [e for e in EXPECTATIONS if e.ungranted]
    out = [
        "<!-- GENERATED FILE - do not edit. Source: scripts/python_fixture_spec.py; run scripts/render_python_fixture_expectations.py after editing. -->",
        "",
        "# Python fixture expectations",
        "",
        "What each `python:` tooling entry in the audit skill family must observe when it runs against the seeded fixture partitions, written down before the run. Generated from `scripts/python_fixture_spec.py` by `scripts/render_python_fixture_expectations.py`: edit the module and re-render, never this file. The `--check` flag of that renderer is what holds the two together, and CI runs it.",
        "",
        "The point of writing these down in advance is that a fixture whose expected output is not recorded first is just a smaller real target. Against a real repository an audit can only ask whether a command ran and returned something plausible; here the right answer is known before the tool speaks, so a tool that runs cleanly and reports half the truth fails instead of passing.",
        "",
        f"Every pin below was checked against OSV and PyPI on **{VERIFIED_ON}**. That date is what the evidence column is worth: a pin is frozen, but the advisories against it only accumulate, so re-verifying one means querying both sources again and moving the date with it.",
        "",
        "The fixture trees themselves are generated and never committed. This record and the module it comes from are the committed half.",
        "",
        "## The shared dependency set",
        "",
        "Every partition declares the same logical set in its own manifest format, so one expectation table serves every partition. The undeclared entry is the exception by design: it arrives transitively and is imported anyway, which is the seed a hygiene lens has to catch.",
        "",
        "| Package | Pin | Imported | Seeds | Evidence |",
        "|---|---|---|---|---|",
    ]
    for dependency in DEPENDENCIES:
        pin = f"`{dependency.pin}`" if dependency.pin else "*(undeclared)*"
        out.append(
            f"| `{dependency.name}` | {pin} | {'yes' if dependency.imported else 'no'} "
            f"| {', '.join(dependency.seeds)} | {_cell(dependency.evidence)} |"
        )

    out += [
        "",
        "## What each partition runs",
        "",
        f"`{FULL_PARTITION}` carries every `python:` entry in the family, because it is the one package manager here that both resolves the tree and exports the other partitions' lock formats - the partition that has to answer every check is the one whose toolchain can build every fixture. The others carry the dependency records, which read each partition's own manifest and lock format and so ask a different question in each, plus one `target-execution` check that exists to prove that partition's materialization route works rather than to re-test the tool.",
        "",
        "| Partition | Expectations | Checks |",
        "|---|---|---|",
    ]
    for partition in PARTITIONS:
        out.append(
            f"| `{partition}` | {len(expectations_for(partition))} "
            f"| {_partition_checks_cell(partition)} |"
        )

    out += [
        "",
        "## Expected result per check",
        "",
        f"{len(EXPECTATIONS)} entries over {len({e.check for e in EXPECTATIONS})} checks. A check whose answer differs by partition is written as two entries with disjoint scopes rather than as one entry with a hedge, so a run against one partition has exactly one right answer to fail against.",
        "",
        "`exact` is a claim a correct tool cannot miss. `floor` is used where the count moves with the tool's version, so the expectation is a location and a minimum rather than a number that goes stale silently. `absence` is a check whose expected finding is that nothing is configured.",
        "",
        "An entry with no seed is not an oversight: it states what a correct tool reports on a fixture that plants nothing for it, which is how a family finding is told apart from a fixture gap.",
        "",
        "| Check | Partitions | Form | Seeds | Expected |",
        "|---|---|---|---|---|",
    ]
    for expectation in EXPECTATIONS:
        out.append(
            f"| `{expectation.check}` | {_partitions_cell(expectation)} "
            f"| {expectation.form} | {_seeds_cell(expectation)} "
            f"| {_cell(expectation.claim)} |"
        )

    out += [
        "",
        "## Without the grant",
        "",
        "Every entry above is run under two grant states, and the table above is the answer with the grant. Where withholding it changes the answer rather than removing it, the second answer is written out below - "
        f"{len(ungranted)} of the {len(EXPECTATIONS)} entries. The rest are derived from their check records and so are not restated per entry: a check whose every Python tool carries a `needs` tier and whose record's `ungranted_note` is the `none` sentinel answers `no-evidence (not-permitted)` without the grant, and a check with an untiered Python tool answers its `claim` in both states.",
        "",
        "This axis exists because a correct ungranted run graded against the granted answer reads as a tool defect. `deps/hygiene` is the sharpest case: deptry reports the undeclared import as DEP003 with the tree and as DEP001 without it, both correct, and only one of them is in the table above.",
        "",
        "| Check | Partitions | Without the grant |",
        "|---|---|---|",
    ]
    for expectation in ungranted:
        out.append(
            f"| `{expectation.check}` | {_partitions_cell(expectation)} "
            f"| {_cell(expectation.ungranted)} |"
        )

    out += [
        "",
        "## A seed nothing detects",
        "",
        "A seeded finding that no tool reports is a finding about the skill family rather than a bug in the fixture. It is recorded as such and the seed stays, because removing it would erase the evidence that the family has a hole there.",
    ]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Write the record, or under `--check` fail if the committed one is stale.

    Args:
        argv: Command-line arguments; `None` reads `sys.argv`.

    Returns:
        `0` on success, `1` under `--check` when the committed Markdown differs
        from a fresh render or is missing.
    """
    parser = argparse.ArgumentParser(
        description="Render/verify the seeded Python fixture expectations."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the committed md is stale, without writing",
    )
    args = parser.parse_args(argv)

    generated = render()
    if not args.check:
        OUT_PATH.write_text(generated)
        print(
            f"wrote {_display(OUT_PATH)} "
            f"({len(EXPECTATIONS)} expectations over {len(PARTITIONS)} partitions)"
        )
        return 0

    # A missing file is drift, not an error to report differently: the record is
    # generated, so its absence and its staleness are closed the same way.
    current = OUT_PATH.read_text() if OUT_PATH.exists() else ""
    if current == generated:
        return 0
    sys.stderr.writelines(
        difflib.unified_diff(
            current.splitlines(keepends=True),
            generated.splitlines(keepends=True),
            fromfile=_display(OUT_PATH),
            tofile="rendered",
        )
    )
    print(
        f"\n{OUT_PATH.name} is stale; run: "
        "uv run python scripts/render_python_fixture_expectations.py",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
