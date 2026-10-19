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
no `Row` here ever carries a judged verdict: `verdict` reads `"unjudged"`
wherever an expectation was graded, and otherwise names the structural reason
there was nothing to grade (`orphan`, `unmatched-filter`) - never a pass and
never a fail.

A results entry never carries its own `findings_stream`: `run_python_fixture_lens.py`
uses the field internally to classify a row and never writes it into the row
dict (confirmed against `fixtures/python/results/pip-none.json`, a real written
run). So `observations_for` looks the stream up from the harness's own enumeration
rather than defaulting to stdout - the default that scores deptry, which writes
its whole report to stderr, as having found nothing. The enumeration is both of
the harness's sources, `INVOCATIONS`, the legacy slot, empty today, and the
routes read from the records that declare them, because a lookup
built from one of the two resolves nothing for every row of the other. Reading
only the table would leave every migrated check's row unresolved on every run,
which is not the rare staleness the sentinel below exists for.

That lookup can fail on a (check, tool) pair the enumeration does not carry, and
this is the second thing a naive grader would get wrong: defaulting to stdout
there would silently misread the row, but raising loses every other row in
the same run over one stale entry. `fe2b0e42` (#45) is a real instance rather
than a hypothetical - it dropped `ruff` from `arch/over-abstraction`'s tooling
and from `INVOCATIONS` in the same commit, but `fixtures/python/results/` is
gitignored and nothing regenerates it, so a results file written before that
commit still carries the `arch/over-abstraction` + `ruff` row and persists
across it. `_findings_stream_for` marks that row's stream
`UNRESOLVED_FINDINGS_STREAM` instead of raising or defaulting: `seed_signals`
reads the sentinel as a key the entry never set and gets back `""`, the same
empty read a check that never ran gets, never a false signal. The unresolved
fact still has to reach a reader, so `render` prints it beside the row rather
than only carrying it in `Observation.findings_stream`, which nothing outside
this module reads. This is not the orphan case below - the check is still
named by an expectation, only the tool is unresolvable - so the row goes
through `grade_row`'s normal path rather than `_orphan_row`'s.

`Expectation.ungranted` is the third thing a naive grader would get wrong: it
holds the answer a `none` run should read where the grant moves the answer, and
grading a `none` run against `claim` instead reads a correct ungranted deptry
run - which reports `markupsafe` as DEP001 rather than DEP003 - as a tool
defect. `grade_row` selects between the two by the run's own `grant`.

The fourth: a results entry this run did not grade. `grade_rows` only ever
iterates `expectations_for`, so left unchecked such an entry - `fixtures/` is
gitignored and nothing regenerates it, so a stale results file surviving a
check renamed or removed out of `EXPECTATIONS` is how one arrives - would
vanish with no row, no error and no count discrepancy, while the worksheet
still reads as full coverage. `grade_rows` renders a row per such check, and
which row is itself a claim: `_orphan_row` where no expectation carries the
check on this partition, `_out_of_scope_row` where one does and the run's own
`only_check` did not reach it. Collapsing the two would print the orphan
claim - that the spec names no such check - over a check the spec does name.

The fifth: a route whose result does not answer the check alone. The harness
classifies a scanner that ran and printed the seed as `ok`, the engine's status,
which does not move for the record's `alone_insufficient`; the harness writes
that field onto the row beside the status, and `observations_for` resolves it
for a results file older than the key from the same enumeration the stream
comes from, never reading a missing key as "the result stands alone". The
render prints it beside a run observation and appends the expectation's `owed`
to the claim, so a hit on the seed reads as a candidate rather than as the check
answered. An entry's own value, empty included, is never overridden.

The sixth: a run of the other language. The TypeScript partitions (#181) are
graded by this same module, and three of its tables are per language - the
expectations, the seed markers and the harness rows the stream and the
`alone_insufficient` caveat are looked up in. Each is picked by
`lang_of(run["partition"])`, never tried in turn: the two marker tables share
seed names, so a TypeScript row read through the Python table counts markers
its output can never hold, and the row lookups are kept per language because a
`(check, tool)` pair is unique only within one.

Usage:
    uv run python scripts/grade_python_fixture_run.py fixtures/python/results
    uv run python scripts/grade_python_fixture_run.py fixtures/typescript/results
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from python_fixture_spec import (
    SEED_MARKERS,
    TS_SEED_MARKERS,
    Expectation,
    expectations_for,
    lang_of,
)
from run_python_fixture_lens import INVOCATIONS, routed_invocations

# One results JSON, exactly as the harness wrote it. A plain dict rather than a
# dataclass or a TypedDict instance: `grade_rows` is exercised directly against
# a dict literal in its own tests, and wrapping loaded JSON in a constructor
# would force every caller through a step the tests never take.
Run = dict[str, object]

REQUIRED_RUN_KEYS = ("grant", "partition", "results")

# Which seed-marker table and which expectations table each language's rows
# are graded from. Keyed by `lang_of(run["partition"])` rather than tried in
# turn, because the two marker tables share seed names: `cycle` names Python
# `import` lines in one and TypeScript `from` clauses in the other, so a
# TypeScript row read through the Python table counts markers the TypeScript
# source can never contain, and reads a planted cycle as a zero.
_SEED_MARKERS_BY_LANG: dict[str, dict[str, tuple[str, ...]]] = {
    "python": SEED_MARKERS,
    "typescript": TS_SEED_MARKERS,
}
_EXPECTATIONS_NAME_BY_LANG = {"python": "EXPECTATIONS", "typescript": "TS_EXPECTATIONS"}


def _lang_of_run(run: Run) -> str:
    """The language a run's partition belongs to.

    `lang_of` raises on a partition neither language names, which is the same
    failure `expectations_for` raises for that run, so a run no expectation could
    ever grade fails here with the partition in the message.
    """
    return lang_of(str(run.get("partition", "")))


# What each (check, tool) pair reports its findings on, read from the harness's
# own enumeration rather than copied here. A results entry never carries this
# itself, so the enumeration is the only source, and a second copy of it here
# would be free to drift from the one the harness actually runs against. Both
# of its sources are read: a lookup built from `INVOCATIONS` alone leaves every
# row of every migrated record unresolved, which the grader test module holds
# against it.
def _enumeration(lang: str) -> tuple:
    """The harness's rows for one language: both sources for Python, whose
    legacy `INVOCATIONS` slot is a Python table, and the records' routes for
    TypeScript.

    Per language rather than one lookup over both, because a `(check, tool)`
    pair is only unique within a language: nothing stops a record from naming
    one tool on a Python route and a TypeScript route with different streams,
    and a merged lookup would answer one of them with the other's.
    """
    if lang == "python":
        return INVOCATIONS + routed_invocations()
    return routed_invocations(lang)


@cache
def _findings_stream_map(lang: str = "python") -> dict[tuple[str, str], str]:
    """The stream lookup for one language, built on first use rather than at import.

    Built lazily for one reason: `routed_invocations` reads the record tree and
    raises on a record whose routes contradict each other, and at module scope
    that turns a contradictory record into an import error - `--help` included,
    and every other function in this module with it. Lazily, the failure lands
    on the caller that needed the lookup and names the record.

    It is still a failure and not a sentinel, which is the boundary worth
    stating because this module's own history argues the other way. The
    sentinel below exists for a **stale results row**: a gitignored file naming
    a (check, tool) pair the harness no longer runs, where aborting would lose
    every other row in the same run over one dead entry. A contradictory
    record is not that. The harness cannot say what it would run, so a grade
    computed over it means nothing, and routing it to the sentinel would put
    two incompatible causes behind one value - a dead results row and a broken
    source record - which is exactly the ambiguity the sentinel was introduced
    to avoid.
    """
    return {
        (invocation.check, invocation.tool): invocation.findings_stream
        for invocation in _enumeration(lang)
    }


# Not a real stream name - `seed_signals` looks this key up on the entry
# itself (`entry.get(sentinel, "")`) and an entry never sets it, so the read
# always comes back empty rather than falling through to stdout. Stands in
# for a (check, tool) pair the enumeration no longer carries, so a stale
# results row can still be graded and rendered instead of aborting the run.
UNRESOLVED_FINDINGS_STREAM = "unresolved"


@cache
def _alone_insufficient_map(lang: str = "python") -> dict[tuple[str, str], str]:
    """What each (check, tool) pair's route says its own result still needs.

    Read from the harness's enumeration, as the stream is, for one kind of entry:
    a results file written before the harness recorded `alone_insufficient` on
    its rows. `fixtures/` is gitignored and nothing regenerates it, so such a
    file outlives the change, and reading its missing key as "the result stands
    alone" would grade a scanner hit that needs confirming as the check
    answered - the half-truth this round exists to catch, reintroduced by the
    grader. A pair the enumeration does not carry resolves to `""`, the same
    as a route whose result does stand alone; the stream's sentinel already
    renders that row as unresolved.
    """
    return {
        (invocation.check, invocation.tool): invocation.alone_insufficient
        for invocation in _enumeration(lang)
    }


def _alone_insufficient_for(entry: dict[str, object], lang: str = "python") -> str:
    """The entry's own `alone_insufficient`, else the enumeration's for its pair."""
    if "alone_insufficient" in entry:
        return str(entry["alone_insufficient"])
    key = (str(entry.get("check", "")), str(entry.get("tool", "")))
    return _alone_insufficient_map(lang).get(key, "")


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


def _findings_stream_for(entry: dict[str, object], lang: str = "python") -> str:
    """Which stream this entry reports findings on, among `lang`'s rows.

    The entry's own `findings_stream` where a caller has already set one - the
    tests that pin `seed_signals` directly do this, and neither carries a
    `check`/`tool` pair a lookup could resolve. Otherwise, the stream the
    harness's own enumeration says this (check, tool) pair uses - both of its
    sources, the hand-written table and the routes read from the records.

    Returns `UNRESOLVED_FINDINGS_STREAM` rather than raising on an unknown
    pair. A results entry naming a (check, tool) the harness never
    transcribed is not a fact this module can answer for, but it is also not
    a caller error: a stale results file naming a tool the enumeration used to
    carry for this check and no longer does (`fe2b0e42`, #45, is a real
    instance) is exactly the kind of drift `fixtures/` being gitignored
    invites, the same way an orphan row's check does. Defaulting to stdout
    would still silently misread it - the way this field exists to prevent -
    so the sentinel stands in instead: `seed_signals` reads it as a missing
    key on the entry and gets `""` back, never a false signal, and the caller
    renders the sentinel as an explicit fact rather than losing the row.
    """
    if "findings_stream" in entry:
        return str(entry["findings_stream"])
    key = (str(entry.get("check", "")), str(entry.get("tool", "")))
    return _findings_stream_map(lang).get(key, UNRESOLVED_FINDINGS_STREAM)


def _entries_for(run: Run, check: str) -> list[dict[str, object]]:
    """The raw result entries this run recorded for one check, unannotated.

    Separated from `observations_for` so an orphan row - one whose check no
    expectation names - can list what the run actually recorded without going
    through `_findings_stream_for`'s lookup, which has nothing to resolve for
    a (check, tool) pair the harness never transcribed and would only ever
    return the unresolved sentinel for it.
    """
    return [entry for entry in run.get("results", []) if entry.get("check") == check]


def observations_for(run: Run, check: str) -> list[dict[str, object]]:
    """Every result entry this run recorded for one check.

    Each entry comes back with `findings_stream` filled in wherever it was
    missing, so `seed_signals` always reads the stream the tool actually
    reports on rather than the stdout default that reads a deptry run
    backwards, and with `alone_insufficient` filled in the same way, so a
    results file older than the field still says which hits are candidates.
    Both are looked up among the rows of the run's own language, read off its
    partition.
    """
    lang = _lang_of_run(run)
    return [
        {
            **entry,
            "findings_stream": _findings_stream_for(entry, lang),
            "alone_insufficient": _alone_insufficient_for(entry, lang),
        }
        for entry in _entries_for(run, check)
    ]


def seed_signals(entry: dict[str, object], seeds: Sequence[str]) -> dict[str, int]:
    """Count each seed marker in the stream this entry reports findings on.

    The stream matters: a tool that writes its report to stderr scores zero on
    stdout, which is indistinguishable from a tool that ran and found nothing.
    """
    stream = str(entry.get(str(entry.get("findings_stream", "stdout")), ""))
    return {seed: stream.count(seed) for seed in seeds}


@dataclass(frozen=True)
class Observation:
    """One tool's answer to one check, as the run recorded it.

    `findings_stream` is `""` for a row built from the run's raw entries -
    `_orphan_row` and `_out_of_scope_row` both read those directly rather than
    through `observations_for`, which is what resolves one - and otherwise
    either a real stream name or `UNRESOLVED_FINDINGS_STREAM` - the second
    case is a fact the render has to surface, not just carry, so a stale row
    reads as unresolved instead of as a silent zero.

    `alone_insufficient` is the route's own statement of what its result still
    needs before it is the check's answer, empty where it stands alone. The
    `status` beside it is the engine's and does not move for it, so an `ok`
    from a scanner that found the seed is a candidate wherever this is set,
    and the render prints it for that reason rather than carrying it, beside
    an observation that ran. Like `findings_stream`, it is resolved only for
    rows built through `observations_for`; an orphan or out-of-scope row reads
    its raw entries and shows the key only where the entry carries it, which
    cannot misread a hit because such a row grades nothing.
    """

    tool: str
    ran: bool
    status: str
    reason: str
    findings_stream: str = ""
    alone_insufficient: str = ""


@dataclass(frozen=True)
class Row:
    """One expectation, graded against one whole run.

    `verdict` stays `"unjudged"` - see the module docstring. `signals` is the
    marker counts summed across every observation this run made of the check;
    a seed category the run's language's marker table carries no marker for
    (a dependency-level seed like `vulnerable` or `stale`, which no literal
    substring can name) contributes nothing, the same as an expectation naming no seed at all.
    `owed` is the expectation's statement of what a hit on this check still
    needs before it is the finding, set where the check's routes say their
    result does not answer alone; the render appends it to the claim.
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
    owed: str = ""


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


def _observation_tuple(entries: Sequence[dict[str, object]]) -> tuple[Observation, ...]:
    return tuple(
        Observation(
            tool=str(entry.get("tool", "")),
            ran=bool(entry.get("ran", False)),
            status=str(entry.get("status", "")),
            reason=str(entry.get("reason", "")),
            findings_stream=str(entry.get("findings_stream", "")),
            alone_insufficient=str(entry.get("alone_insufficient", "")),
        )
        for entry in entries
    )


def grade_row(expectation: Expectation, run: Run) -> Row:
    """One expectation, paired with every observation this run made of it.

    A route whose reporting half runs as a second command (`then`, which
    `test/coverage-reach`'s `coverage.py` route declares) is a known blind spot
    rather than something worked around: `seed_signals` reads only an entry's
    own top-level `stdout`/`stderr`, and the second command's output sits
    nested under `entry["then"]` instead, invisible to a mechanical count here.
    A route writing its evidence to a report file (`test/isolation`'s vitest
    route) is the same kind of blind spot: the file's content sits under
    `entry["report"]`, which this count does not read either.
    """
    observations = observations_for(run, expectation.check)
    seed_markers = _SEED_MARKERS_BY_LANG[_lang_of_run(run)]
    signals: dict[str, int] = {}
    for category in expectation.seeds:
        markers = seed_markers.get(category, ())
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
        observations=_observation_tuple(observations),
        signals=signals,
        owed=expectation.owed,
    )


def _ungraded_row(
    *,
    check: str,
    run: Run,
    form: str,
    claim: str,
    entries: Sequence[dict[str, object]],
) -> Row:
    """The mechanics every row that grades nothing has in common.

    Three rows reach the worksheet without an expectation behind them - the
    orphan, the out-of-scope entry and the unmatched filter - and each has to
    carry no seeds, no signals, and a `verdict` naming the structural reason
    rather than a grade. Sharing the construction puts that invariant in one
    place, so none of the three can drift into looking judged; the `claim` and
    the `form` stay at the call sites, because what is true of each is exactly
    what must not be shared.
    """
    return Row(
        check=check,
        partition=str(run.get("partition", "")),
        grant=str(run.get("grant", "")),
        form=form,
        claim=claim,
        seeds=(),
        observations=_observation_tuple(entries),
        signals={},
        verdict=form,
    )


def _orphan_row(check: str, run: Run) -> Row:
    """A row for result entries no expectation names.

    Which entry that is reads off `expectations_for`'s own partition-level list,
    never off the narrowed scope a run's `only_check` leaves behind - an entry
    the filter merely did not reach is `_out_of_scope_row`'s, and this claim
    would be false of it. `grade_row` only ever iterates expectations, so an
    entry whose check none of them names would otherwise vanish with no row, no
    error and no count discrepancy - the exact "reads clean, isn't" failure this
    round exists to catch, and the worst possible place to commit it is the
    grader's own inputs. `fixtures/` is gitignored and nothing regenerates it,
    so a stale results file surviving a check renamed or removed out of
    `EXPECTATIONS` is exactly how this happens, not a hypothetical.

    Built from `_entries_for` rather than `observations_for`: there is no
    expectation here to draw seeds from, so no signal is ever computed and no
    `findings_stream` lookup is needed - which matters, because the orphan
    entry's own (check, tool) pair is, by construction, not one `grade_rows`
    already confirmed a `Row` for, and may not be one `INVOCATIONS` names
    either.
    """
    return _ungraded_row(
        check=check,
        run=run,
        form="orphan",
        claim=(
            "no expectation in python_fixture_spec.py names this check for this "
            "partition; the entry is either a stale results file's leftover from "
            "a check renamed or removed out of "
            f"{_EXPECTATIONS_NAME_BY_LANG[_lang_of_run(run)]}, or a check the "
            "harness never should have run"
        ),
        entries=_entries_for(run, check),
    )


def _out_of_scope_row(check: str, run: Run, only_check: str) -> Row:
    """A row for an entry outside the filter a one-check run was graded under.

    The check here *is* one `python_fixture_spec.py` carries for this partition,
    which is what separates it from `_orphan_row`. Both rows exist because the
    entry was not graded, but they say different things about why, and printing
    the orphan claim over this entry would assert that no expectation names a
    check the partition demonstrably carries - a false sentence in the very
    worksheet this module writes to make silent misreads visible. The orphan
    claim stays reserved for the entry no expectation covers, because that is a
    real finding about the spec and softening it into a note about scope would
    hide it.

    Reachable the same way the unmatched filter is: a hand-edited or outlived
    one-check file in a gitignored directory nothing regenerates can mix an
    entry from a wider run into a narrower filter's file.
    """
    return _ungraded_row(
        check=check,
        run=run,
        form="out-of-scope",
        claim=(
            f"the run was graded under only_check {only_check!r} and this entry "
            "falls outside that filter; python_fixture_spec.py does carry an "
            "expectation for this check on this partition, so the entry is "
            "unaccounted for by the run's own scope rather than unrecognized by "
            "the spec"
        ),
        entries=_entries_for(run, check),
    )


def _unmatched_filter_row(only_check: str, run: Run) -> Row:
    """A row for a run whose `only_check` no expectation on its partition carries.

    Raising here loses every other run in the directory: `main` iterates the
    results glob with no handler, so one such file aborts grading of the whole
    matrix sitting beside it. That file is a stale input rather than a caller
    error - `fixtures/python/results/` is gitignored and nothing regenerates it,
    so a one-check run written before a spec change outlives the expectation
    that justified it, the same drift that left the `arch/over-abstraction` +
    `ruff` row behind (`fe2b0e42`, #45). Dropping the file quietly is the other
    half of the same mistake, so the fact reaches the worksheet as its own row,
    following the visible-rather-than-silent precedent `_orphan_row` and
    `UNRESOLVED_FINDINGS_STREAM` already set.

    States the fact about the filter and carries no observations: it is a row
    about the file's scope, and the entries the file recorded are itemized
    beside it by `grade_rows`, one row per check they name. Attributing them to
    this row instead would put every tool under a check name the spec does not
    recognize, hiding which check each answered - and it would swallow the
    orphan among them, which is a finding about the spec rather than a note
    about scope and has to keep its own row.
    """
    return _ungraded_row(
        check=only_check,
        run=run,
        form="unmatched-filter",
        claim=(
            f"the run names only_check {only_check!r} and no expectation in "
            "python_fixture_spec.py carries that check on this partition, so it "
            "graded nothing; the file is either hand-edited or has outlived the "
            "expectations, and whatever it did record is itemized in the rows "
            "beside this one"
        ),
        entries=(),
    )


def grade_rows(run: Run) -> list[Row]:
    """Every expectation this run's partition carries, graded against it, plus
    one row for every check `run["results"]` names that this run did not grade.

    The expectation rows alone are `expectations_for`'s own scope - one `Row`
    per expectation per partition per grant. The ungraded rows are the other
    direction of the same completeness question: without them, a results
    entry whose check the spec no longer recognizes disappears silently while
    every expectation row still renders, and the worksheet reads as full
    coverage of a run it did not fully account for.

    An ungraded check gets whichever of the two true statements applies, read
    off `partition_checks` rather than off the run's narrowed scope: no
    expectation carries it on this partition, which is `_orphan_row` and a
    finding about the spec, or an expectation does carry it and this run's
    `only_check` did not cover it, which is `_out_of_scope_row` and a fact about
    the file. Deriving both from the narrowed scope would print the orphan claim
    over every entry a matched filter left behind, asserting that no expectation
    names a check the partition demonstrably carries.

    A run carrying `only_check` narrows that scope to the one check it ran.
    `main` grades every `*.json` in a directory, so a one-check run sits beside
    the full matrix artifact for the same partition and grant; graded against
    the whole partition it would render a row per expectation it never ran, each
    reading `(no observation)` beside the matrix row that did observe it - a
    reported absence where the truth is that the run never claimed the scope. An
    empty value is the full run the harness writes it as, not a filter matching
    nothing, and a value naming a check the partition carries no expectation for
    gets one `_unmatched_filter_row` rather than grading to zero rows or raising:
    nothing the harness writes produces that pair, so it is a hand-edited or outlived
    file, reporting it as a run with nothing to cover is the silence this module
    exists to break, and raising over it loses every other run in the directory
    because `main` iterates the results glob with no handler.
    """
    partition = str(run.get("partition", ""))
    expectations = expectations_for(partition)
    partition_checks = {expectation.check for expectation in expectations}
    only_check = str(run.get("only_check", ""))
    if only_check:
        expectations = tuple(e for e in expectations if e.check == only_check)
    rows = [grade_row(expectation, run) for expectation in expectations]
    if only_check and not expectations:
        rows.append(_unmatched_filter_row(only_check, run))
    graded_checks = {expectation.check for expectation in expectations}
    ungraded_checks = sorted(
        {
            str(entry.get("check", ""))
            for entry in run.get("results", [])
            if str(entry.get("check", "")) not in graded_checks
        }
    )
    for check in ungraded_checks:
        if check in partition_checks:
            rows.append(_out_of_scope_row(check, run, only_check))
        else:
            rows.append(_orphan_row(check, run))
    return rows


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
        if observation.findings_stream == UNRESOLVED_FINDINGS_STREAM:
            detail += (
                " [findings stream unresolved: no invocation recorded for this "
                "check+tool; no signal computed]"
            )
        if observation.ran and observation.alone_insufficient:
            detail += (
                " [not the check's answer alone: "
                + _escape_cell(observation.alone_insufficient)
                + "]"
            )
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
                    _escape_cell(
                        f"{row.claim} Still owed: {row.owed}" if row.owed else row.claim
                    ),
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
