"""Render the two fixture expectation records from the fixture spec.

`docs/audit/python-fixture-expectations.md` (#45) and
`docs/audit/typescript-fixture-expectations.md` (#181) are both generated: edit
`scripts/python_fixture_spec.py` and re-render. `--check` compares each with a
fresh render and is what stops them drifting apart; it fails if either is stale. It
prints nothing and exits 0 when they agree; on drift it prints a unified diff
to stderr and exits 1. That contract is the one the other generated record in
`docs/audit/` is gated by, so a reader who knows one gate knows this one.

Every number in the rendered document is computed from the module. A typed-in
count is a claim about the fixture that stops being true the first time a seed
is added, and nothing would fail - which is the same silence the spec module
exists to remove.

The grant axis is rendered as its own section rather than as a further column of
the expectation table: `Expectation.ungranted` is set on only the entries whose
answer the grant moves, and is prose long enough that a column would wrap
unreadably. How the remaining
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
    FORMS,
    FULL_PARTITION,
    PARTITIONS,
    SOURCE_FILES,
    THIN_EXTRA_CHECK,
    TS_CONFIGURED_FILES,
    TS_CORE,
    TS_DEFERRED_CHECKS,
    TS_DEPENDENCIES,
    TS_EXPECTATIONS,
    TS_LEAF,
    TS_MANAGER_PINS,
    TS_PARTITIONS,
    TS_ROOT,
    TS_SOURCE_FILES,
    TS_VERIFIED_ON,
    VERIFIED_ON,
    Expectation,
    expectations_for,
    manager_of,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "docs" / "audit" / "python-fixture-expectations.md"
TS_OUT_PATH = REPO_ROOT / "docs" / "audit" / "typescript-fixture-expectations.md"


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
        "The fixture trees themselves are generated and never committed to this repository. Each one is a git repository of its own with every file committed inside it, because some tools read only tracked files. This record and the module it comes from are the committed half here.",
        "",
        "## The shared dependency set",
        "",
        f"Every partition declares the same logical set in its own manifest format, so the set below is stated once rather than per partition. The expectation table further down is scoped where a partition changes the answer. {len([d for d in DEPENDENCIES if not d.pin])} of the {len(DEPENDENCIES)} entries are undeclared by design: they arrive transitively and are imported anyway, which is the seed a hygiene lens has to catch.",
        "",
        "| Package | Pin | Imported | Seeds | Evidence |",
        "|---|---|---|---|---|",
    ]
    for dependency in DEPENDENCIES:
        pin = f"`{_cell(dependency.pin)}`" if dependency.pin else "*(undeclared)*"
        out.append(
            f"| `{_cell(dependency.name)}` | {pin} "
            f"| {'yes' if dependency.imported else 'no'} "
            f"| {_cell(', '.join(dependency.seeds))} | {_cell(dependency.evidence)} |"
        )

    out += [
        "",
        "## What each partition runs",
        "",
        f"`{FULL_PARTITION}` carries every `python:` entry in the family, because it is the package manager the whole fixture set is built through: it resolves the tree, exports the requirements and PEP 751 partitions directly, and runs the poetry and pipenv lock steps as one-shot commands. The partition that has to answer every check is the one whose toolchain can build every fixture. The others carry the dependency records, which read each partition's own manifest and lock format and so ask a different question in each, plus `{THIN_EXTRA_CHECK}`, which exists to prove that partition's materialization route works rather than to re-test the tool.",
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
        f"{len(EXPECTATIONS)} entries over {len({e.check for e in EXPECTATIONS})} checks. A check whose answer differs by partition is written as one entry per scope, the scopes disjoint, rather than as one entry with a hedge - so a run against one partition has exactly one right answer to fail against.",
        "",
        f"The `Form` column takes one of {', '.join(f'`{f}`' for f in FORMS)}. `exact` states an observation that is fully determined: a correct tool reports it, and output that differs is a finding about the tool whether it reports less or more. `floor` states a location and a minimum, for the entries where an exact number would go stale on its own - advisories accumulate against a frozen pin, a mutation count moves with the operator set, and a thinly exercised suite makes over-reporting the correct answer. `absence` states that there is nothing of this kind to find, so any hit is a false positive.",
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
        f"{len(ungranted)} of the {len(EXPECTATIONS)} entries. The rest are derived from their check records and so are not restated per entry. On a record declaring `tooling:`, a check whose every Python tool carries a `needs` tier and whose `ungranted_note` is the `none` sentinel answers `no-evidence (not-permitted)` without the grant, and a check with an untiered Python tool answers its `claim` in both states. On a record declaring `routes:` the same two cases are read off the routes rather than off a note - a Python language whose every answering-kind, non-forbidden route needs the grant answers `no-evidence (not-permitted)`, and an untiered route left in that language is what still runs - and neither writes a second answer out here, because the routes counterpart of `ungranted_note` carries the sentinel and no prose of its own. A third case does write one: a language whose routes carry `answers`, with an untiered route on one axis beside tiered routes on another, answers half, `no-evidence (not-permitted)` in status and in the coverage count with its evidence naming the axis that answered and the one that did not, and the rows below that name an axis are that case.",
        "",
        "This axis exists because a correct ungranted run graded against the granted answer reads as a tool defect. The `deps/hygiene` rows below are the sharpest case, and they state the two answers rather than having them restated here, where the copy would be free to drift.",
        "",
        "| Check | Partitions | Without the grant |",
        "|---|---|---|",
    ]
    for expectation in ungranted:
        out.append(
            f"| `{expectation.check}` | {_partitions_cell(expectation)} "
            f"| {_cell(expectation.ungranted)} |"
        )

    owed = [e for e in EXPECTATIONS if e.owed]
    out += [
        "",
        "## What a result still owes",
        "",
        f"A check whose Python route says its own result does not answer the check - the record's `alone_insufficient` - carries what is still owed here, {len(owed)} of the {len(EXPECTATIONS)} entries, set by derivation from the records rather than by judgement. The harness writes the route's field onto each results row and the grader prints it beside the observation, so a tool that found the seed reads as a candidate for the confirmation below rather than as the check answered. The row's status is the engine's and does not move for it.",
        "",
        "| Check | Partitions | Still owed |",
        "|---|---|---|",
    ]
    for expectation in owed:
        out.append(
            f"| `{expectation.check}` | {_partitions_cell(expectation)} "
            f"| {_cell(expectation.owed)} |"
        )

    planted = {seed for f in SOURCE_FILES for seed in f.seeds}
    expected = {seed for e in EXPECTATIONS for seed in e.seeds}
    unexpected = sorted(planted - expected)
    out += [
        "",
        "## A seed nothing expects",
        "",
        "A seeded finding that no expectation names would be planted and then never looked for, which at review is indistinguishable from a fixture that never planted it. So the two sets are held equal in both directions by the suite rather than by reading.",
        "",
        ", ".join(f"`{seed}`" for seed in unexpected)
        if unexpected
        else f"None: all {len(planted)} seeds the source files plant are named by some expectation. The dependency set plants its own, counted separately.",
        "",
        "A seed that is expected and that no *tool* reports is a different thing and is not knowable from here - it is a finding about the skill family rather than a bug in the fixture, it is recorded as such when the fixtures are run, and the seed stays, because removing it would erase the evidence that the family has a hole there.",
    ]
    return "\n".join(out) + "\n"


def _ts_scope_cell(expectation: Expectation) -> str:
    """`all`, or the scoped TypeScript partitions in `TS_PARTITIONS` order."""
    if set(expectation.partitions) == set(TS_PARTITIONS):
        return "all"
    scoped = [p for p in TS_PARTITIONS if p in expectation.partitions]
    return ", ".join(f"`{p}`" for p in scoped)


def _ts_partition_checks_cell(partition: str) -> str:
    carried = {e.check for e in expectations_for(partition)}
    if carried == {e.check for e in TS_EXPECTATIONS}:
        return "every check in the expectation table"
    return ", ".join(f"`{c}`" for c in sorted(carried))


def _ts_member_cell(member: str) -> str:
    return "root" if member == TS_ROOT else f"`{member}`"


def render_typescript() -> str:
    """The whole published TypeScript record, newline-terminated."""
    ungranted = [e for e in TS_EXPECTATIONS if e.ungranted]
    owed = [e for e in TS_EXPECTATIONS if e.owed]
    out = [
        "<!-- GENERATED FILE - do not edit. Source: scripts/python_fixture_spec.py; run scripts/render_python_fixture_expectations.py after editing. -->",
        "",
        "# TypeScript fixture expectations",
        "",
        "What each `lang: typescript` command route in the audit skill family must observe when it runs against the seeded npm and pnpm fixture partitions, written down before the run. Generated from `scripts/python_fixture_spec.py` by `scripts/render_python_fixture_expectations.py`, the same module and renderer as the Python record beside it: edit the module and re-render, never this file. The `--check` flag of that renderer holds both records to the module, and CI runs it.",
        "",
        "A fixture whose expected output is not recorded first is just a smaller real target. Against a real repository an audit can only ask whether a command ran and returned something plausible; here the right answer is known before the tool speaks, so a route that runs cleanly and reports half the truth fails instead of passing.",
        "",
        f"Every pin below was checked against OSV and the npm registry on **{TS_VERIFIED_ON}**. A pin is frozen, but the advisories against it only accumulate and its latest release moves, so re-verifying one means querying both sources again and moving the date with it.",
        "",
        "The fixture trees are generated and never committed to this repository.",
        "",
        "## The shared dependency set",
        "",
        f"Every partition declares the same set at exact pins. The npm partitions are one package each and declare all of it in one `package.json`; the pnpm partition is a workspace, and the `Member` column says which of its manifests declares each entry - the root, `{TS_CORE}` (the seeded source) or `{TS_LEAF}` (the leaf, which also depends on the core package through `workspace:*`). The member is what decides whether a root-only read reaches a pin.",
        "",
        "| Package | Pin | Latest | Dev | Member | Seeds | Evidence |",
        "|---|---|---|---|---|---|---|",
    ]
    for d in TS_DEPENDENCIES:
        out.append(
            f"| `{_cell(d.name)}` | `{_cell(d.pin)}` | `{_cell(d.latest)}` "
            f"| {'yes' if d.dev else 'no'} | {_ts_member_cell(d.member)} "
            f"| {_cell(', '.join(d.seeds)) or '-'} | {_cell(d.evidence)} |"
        )

    out += [
        "",
        "## What each partition runs",
        "",
        "The `npm` and `pnpm` partitions carry every check in the expectation table but one, because each TypeScript command route there is either the partition's own package manager's subcommand or a tool that runs the same way on both, so each partition asks it a different question. `npm-layered` is the npm tree plus a dependency-cruiser config of its own, and carries `arch/layering` alone: that check's command route applies only where the project declares its own boundary, and the other two trees test the case where it does not. The `packageManager` pin is on the root manifest, which is where corepack reads it.",
        "",
        "| Partition | Manager pin | Expectations | Checks |",
        "|---|---|---|---|",
    ]
    for partition in TS_PARTITIONS:
        out.append(
            f"| `{partition}` | `{TS_MANAGER_PINS[manager_of(partition)]}` "
            f"| {len(expectations_for(partition))} "
            f"| {_ts_partition_checks_cell(partition)} |"
        )

    out += [
        "",
        "## Expected result per check",
        "",
        f"{len(TS_EXPECTATIONS)} entries over {len({e.check for e in TS_EXPECTATIONS})} checks. A check whose answer differs by partition is written as one entry per scope, the scopes disjoint. The `Form` column takes one of {', '.join(f'`{f}`' for f in FORMS)}, with the meanings the Python record gives them: `exact` is fully determined, `floor` states a location and a minimum where an exact number would go stale on its own, and `absence` states that any hit is a false positive. An entry with no seed states what a correct tool reports on a fixture that plants nothing for it.",
        "",
        "| Check | Partitions | Form | Seeds | Expected |",
        "|---|---|---|---|---|",
    ]
    for e in TS_EXPECTATIONS:
        out.append(
            f"| `{e.check}` | {_ts_scope_cell(e)} | {e.form} | {_seeds_cell(e)} "
            f"| {_cell(e.claim)} |"
        )

    out += [
        "",
        "## Without the grant",
        "",
        f"Every entry is run under two grant states, and the table above is the answer with the grant. Where withholding it changes what the check answers on that partition, the second answer is written out below - {len(ungranted)} of the {len(TS_EXPECTATIONS)} entries. It is judged per partition rather than per language, because an untiered TypeScript route can be one partition's own package manager: `npm sbom` needs no grant, but it reads `package-lock.json`, so it answers nothing on the pnpm partition. An entry not listed here answers its claim in both states.",
        "",
        "| Check | Partitions | Without the grant |",
        "|---|---|---|",
    ]
    for e in ungranted:
        out.append(f"| `{e.check}` | {_ts_scope_cell(e)} | {_cell(e.ungranted)} |")

    out += [
        "",
        "## What a result still owes",
        "",
        f"An entry whose check has a TypeScript route naming a tool that carries `alone_insufficient` states what is still owed, {len(owed)} of the {len(TS_EXPECTATIONS)} entries. The row's status is the engine's and does not move for it.",
        "",
        "| Check | Partitions | Still owed |",
        "|---|---|---|",
    ]
    for e in owed:
        out.append(f"| `{e.check}` | {_ts_scope_cell(e)} | {_cell(e.owed)} |")

    out += [
        "",
        "## Checks with no expectation",
        "",
        f"Every check with a `lang: typescript` route either has an expectation above or is listed here with its reason - {len(TS_DEFERRED_CHECKS)} checks. The suite holds the two sets to a partition of the family's TypeScript-route checks, read from the check records, so a new TypeScript route cannot drop out of the round unclassified.",
        "",
        "| Check | Why no expectation |",
        "|---|---|",
    ]
    for check in sorted(TS_DEFERRED_CHECKS):
        out.append(f"| `{check}` | {_cell(TS_DEFERRED_CHECKS[check])} |")

    planted = {s for f in TS_SOURCE_FILES + TS_CONFIGURED_FILES for s in f.seeds} | {
        s for d in TS_DEPENDENCIES for s in d.seeds
    }
    expected = {s for e in TS_EXPECTATIONS for s in e.seeds}
    unexpected = sorted(planted - expected)
    out += [
        "",
        "## A seed nothing expects",
        "",
        "A seeded finding no expectation names would be planted and never looked for, so the planted and expected seeds are held equal in both directions by the suite.",
        "",
        ", ".join(f"`{s}`" for s in unexpected)
        if unexpected
        else f"None: all {len(planted)} seeds the source files and the dependency set plant are named by some expectation.",
    ]
    return "\n".join(out) + "\n"


def _records() -> list[tuple[Path, str, str]]:
    """(path, rendered text, summary) for each record, read at call time.

    Looked up through the module globals on every call rather than bound once,
    so a test pointing `OUT_PATH` or `TS_OUT_PATH` at a temporary file redirects
    exactly that record.
    """
    return [
        (
            OUT_PATH,
            render(),
            f"{len(EXPECTATIONS)} expectations over {len(PARTITIONS)} partitions",
        ),
        (
            TS_OUT_PATH,
            render_typescript(),
            f"{len(TS_EXPECTATIONS)} expectations over {len(TS_PARTITIONS)} partitions",
        ),
    ]


def main(argv: list[str] | None = None) -> int:
    """Write the record, or under `--check` fail if the committed one is stale.

    Args:
        argv: Command-line arguments; `None` reads `sys.argv`.

    Returns:
        `0` on success, `1` under `--check` when either committed record differs
        from a fresh render or is missing.
    """
    parser = argparse.ArgumentParser(
        description="Render/verify the seeded Python and TypeScript fixture expectations."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the committed md is stale, without writing",
    )
    args = parser.parse_args(argv)

    records = _records()
    if not args.check:
        for path, generated, summary in records:
            path.write_text(generated)
            print(f"wrote {_display(path)} ({summary})")
        return 0

    # A missing file is drift, not an error to report differently: the record is
    # generated, so its absence and its staleness are closed the same way.
    stale = []
    for path, generated, _ in records:
        current = path.read_text() if path.exists() else ""
        if current == generated:
            continue
        stale.append(path)
        sys.stderr.writelines(
            difflib.unified_diff(
                current.splitlines(keepends=True),
                generated.splitlines(keepends=True),
                fromfile=_display(path),
                tofile="rendered",
            )
        )
    if not stale:
        return 0
    print(
        f"\n{', '.join(p.name for p in stale)} stale; run: "
        "uv run python scripts/render_python_fixture_expectations.py",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
