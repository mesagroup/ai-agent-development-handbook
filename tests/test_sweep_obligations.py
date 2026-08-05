"""Keep `docs/audit/sweep-obligations.md` describing the files it cites (#23).

The ledger records, one row per obligation, how the `audit` sweep discharges
each rule `audit-core` states. Its exposure is not that a row is wrong - a
reader has to judge that - but that the files get reworded and every row
silently stops pointing at anything. Each row quotes a verbatim anchor, and
that is checkable: an anchor no longer present in `audit-core/SKILL.md` means
the obligation moved, changed wording, or was removed, and the row needs
re-reading either way.

**If a test here fails, find the obligation and re-read the row. Do not
weaken the assertion** - in particular, do not trim an anchor down to
whatever fragment survived a rewording. A shortened anchor still passes
while pinning a sentence nobody checked, which is the failure this module
exists to catch rather than a fix for it.

The vacuity risk is the one worth guarding hardest: a ledger the parser
walks only part of leaves a green suite behind while most rows go
unexamined. So the parser takes every table in the file, requires each to be
one it recognises, and fails on a row it cannot read rather than skipping it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER = REPO_ROOT / "docs" / "audit" / "sweep-obligations.md"
AUDIT_CORE = REPO_ROOT / ".agents" / "skills" / "audit-core" / "SKILL.md"
SWEEP = REPO_ROOT / ".agents" / "skills" / "audit" / "SKILL.md"

# Tables are identified by their own headers rather than by position, so
# adding prose or splitting the obligations across sub-headings does not
# silently select one table and drop the rest.
_ANCHOR_HEADER = "`audit-core` anchor"
_DISPOSITION_HEADER = "Disposition"
_VOCABULARY_HEADER = ("Disposition", "Meaning")

# A quote long enough to be a quote rather than a turn of phrase. Every one
# in the ledger must be verbatim from a file it describes.
_MIN_QUOTE = 40
_SEPARATOR_CELL = re.compile(r"^:?-+:?$")


def _cells(line: str) -> list[str]:
    """Split one Markdown table row into its trimmed cells."""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _plain(cell: str) -> str:
    """Strip the emphasis and code-span markup a table cell may carry."""
    return re.sub(r"[*`]", "", cell).strip()


def _is_separator(line: str) -> bool:
    """Whether a line is a Markdown table's `|---|---|` separator row."""
    return line.startswith("|") and all(
        _SEPARATOR_CELL.match(cell) for cell in _cells(line)
    )


def _scan(
    lines: list[str],
) -> tuple[list[tuple[tuple[str, ...], list[tuple[int, str]]]], list[int]]:
    """Find every Markdown table, and every `|` line that is in none of them.

    One walk produces both, so the set of rows checked and the set reported
    as orphaned cannot disagree about what a table is.

    Args:
        lines: The file's lines, without terminators.

    Returns:
        One entry per table - its header cells and its data rows as
        (1-indexed line number, raw line) pairs - and the 1-indexed line
        numbers of `|` lines belonging to no table. A row separated from its
        table by a blank line, or a table whose separator row was deleted,
        lands in the second list rather than vanishing from the first.
    """
    tables: list[tuple[tuple[str, ...], list[tuple[int, str]]]] = []
    claimed: set[int] = set()
    i = 0
    while i < len(lines):
        # A table is a header, a separator, then rows.
        if (
            lines[i].startswith("|")
            and i + 1 < len(lines)
            and _is_separator(lines[i + 1])
        ):
            rows: list[tuple[int, str]] = []
            j = i + 2
            while j < len(lines) and lines[j].startswith("|"):
                rows.append((j + 1, lines[j]))
                j += 1
            tables.append((tuple(_cells(lines[i])), rows))
            claimed.update(range(i + 1, j + 1))
            i = j
        else:
            i += 1
    orphans = [
        n
        for n, line in enumerate(lines, 1)
        if line.startswith("|") and n not in claimed
    ]
    return tables, orphans


_LINES = LEDGER.read_text(encoding="utf-8").splitlines()
_TABLES, _ORPHANS = _scan(_LINES)

_OBLIGATION_TABLES = [t for t in _TABLES if _ANCHOR_HEADER in t[0]]
_VOCABULARY_TABLES = [t for t in _TABLES if t[0] == _VOCABULARY_HEADER]


def _vocabulary(problems: list[str]) -> frozenset[str]:
    """The dispositions the ledger itself defines.

    Read from the ledger rather than duplicated here, so the ledger's claim
    that a row's disposition comes "from the vocabulary above" is enforced
    against the vocabulary a reader actually sees.

    Args:
        problems: Collector; a message is appended rather than raised.
    """
    if len(_VOCABULARY_TABLES) != 1:
        problems.append(
            f"{LEDGER.name} needs exactly one {_VOCABULARY_HEADER} table defining "
            f"the dispositions; found {len(_VOCABULARY_TABLES)}"
        )
        return frozenset()
    return frozenset(_plain(row.split("|")[1]) for _, row in _VOCABULARY_TABLES[0][1])


def _rows(problems: list[str]) -> list[tuple[int, str, str, str, str]]:
    """Read every obligations row as (line, obligation, anchor, disposition, how).

    A row whose cells do not match its header is reported and skipped rather
    than raised on. Parsing runs at import, so raising would abort collection
    and take every test in this module down with it - including the ones that
    would have named the real problem. Same shape as `load_checks`: collect,
    then let one test report them all.

    Args:
        problems: Collector; one message per unreadable row.
    """
    out: list[tuple[int, str, str, str, str]] = []
    for header, rows in _OBLIGATION_TABLES:
        anchor_col = header.index(_ANCHOR_HEADER)
        disposition_col = header.index(_DISPOSITION_HEADER)
        how_col = len(header) - 1
        for line_no, raw in rows:
            cells = _cells(raw)
            if len(cells) != len(header):
                problems.append(
                    f"{LEDGER.name}:{line_no} has {len(cells)} cells where its "
                    f"table header has {len(header)}: {raw!r}"
                )
                continue
            how = cells[how_col] if how_col > max(anchor_col, disposition_col) else ""
            out.append(
                (
                    line_no,
                    cells[0],
                    cells[anchor_col].strip("`"),
                    _plain(cells[disposition_col]),
                    how,
                )
            )
    return out


PROBLEMS: list[str] = []
DISPOSITIONS = _vocabulary(PROBLEMS)
ROWS = _rows(PROBLEMS)
_IDS = [f"L{line}:{obligation[:48]}" for line, obligation, *_ in ROWS]


def test_the_ledger_parses() -> None:
    """Every row and the vocabulary table were readable.

    An unreadable row is excluded from the parametrised checks below, so
    without this it would be a row nobody verified rather than a failure.
    """
    assert not PROBLEMS, "\n".join(PROBLEMS)


def test_every_table_is_one_the_parser_recognises() -> None:
    """No table in the ledger is silently outside the checked set."""
    unknown = [
        t[0]
        for t in _TABLES
        if t not in _OBLIGATION_TABLES and t not in _VOCABULARY_TABLES
    ]
    assert not unknown, (
        f"{LEDGER.name} has table(s) this module does not check: {unknown}. Either "
        f"give the table a {_ANCHOR_HEADER!r} column so its rows are verified, or "
        "check it here - an unrecognised table is rows nobody validates"
    )


def test_no_table_row_is_orphaned() -> None:
    """Every `|` line belongs to a table, so none drops out of the checked set."""
    assert not _ORPHANS, (
        f"{LEDGER.name} has table row(s) at line(s) {_ORPHANS} that belong to no "
        "table - a blank line inside a table, or a missing separator row, ends "
        "collection early and leaves the rows after it unchecked"
    )


def test_the_obligations_table_is_not_empty() -> None:
    """A ledger that parsed to nothing would pass every parametrised test."""
    assert _OBLIGATION_TABLES, f"{LEDGER.name} has no {_ANCHOR_HEADER!r} table"
    assert ROWS, "the obligations table(s) parsed to zero rows"


@pytest.mark.parametrize("row", ROWS, ids=_IDS)
def test_anchor_occurs_exactly_once_in_audit_core(row: tuple) -> None:
    """Each anchor pins one sentence in `audit-core/SKILL.md`, not zero or many.

    Exactly-once rather than merely present: these anchors are short, and a
    phrase repeated in a later recap would let the row keep passing while the
    sentence it was written to pin got reworded.
    """
    line_no, obligation, anchor, _, _ = row
    assert obligation, f"{LEDGER.name}:{line_no} names no obligation"
    assert anchor, f"{obligation!r} has an empty anchor"
    found = AUDIT_CORE.read_text(encoding="utf-8").count(anchor)
    assert found == 1, (
        f"{LEDGER.name}:{line_no} anchors {obligation!r} on {anchor!r}, which "
        f"occurs {found} times in {AUDIT_CORE.name} (expected 1). Zero means the "
        "obligation was reworded, moved or removed; more than one means the "
        "anchor no longer identifies a single sentence. Re-read the obligation "
        "and rewrite the row - do not shorten the anchor to make this pass"
    )


@pytest.mark.parametrize("row", ROWS, ids=_IDS)
def test_row_commits_to_a_disposition_and_justifies_it(row: tuple) -> None:
    """Each row picks a defined disposition and says how the sweep discharges it."""
    line_no, obligation, _, disposition, how = row
    assert disposition in DISPOSITIONS, (
        f"{LEDGER.name}:{line_no} gives {obligation!r} the disposition "
        f"{disposition!r}; the ledger's own vocabulary table defines "
        f"{sorted(DISPOSITIONS)}"
    )
    assert how, (
        f"{LEDGER.name}:{line_no} leaves {obligation!r} with no 'how' - that "
        "column is where a disposition is justified, and an empty one asserts "
        "the row without grounding it"
    )


def test_quotes_in_the_ledger_are_verbatim() -> None:
    """Every long quote in the ledger is real text from a file it describes.

    The ledger's premise is a quotation of the sweep's own promise. Anchors
    guard the `audit-core` side; without this, a reword on the sweep's side
    leaves the ledger quoting a sentence that no longer exists.
    """
    sources = SWEEP.read_text(encoding="utf-8") + AUDIT_CORE.read_text(encoding="utf-8")
    # Line-scoped: a quote spanning a newline is not a quote, and `[^"]`
    # would otherwise run from one quote mark to a far-off later one.
    quoted = re.findall(
        rf'"([^"\n]{{{_MIN_QUOTE},}})"', LEDGER.read_text(encoding="utf-8")
    )
    missing = [q for q in quoted if q not in sources]
    assert not missing, (
        f"{LEDGER.name} quotes text found in neither {SWEEP.name} nor "
        f"{AUDIT_CORE.name}: {missing}. A quotation marks itself as verbatim; "
        "paraphrase without the quotation marks, or fix the quote"
    )


def test_the_sweep_points_at_the_ledger() -> None:
    """The sweep links the ledger, so a reader of either finds the other.

    Without the link the ledger is discoverable only by whoever already knows
    it exists, which is the population that does not need it.
    """
    assert LEDGER.name in SWEEP.read_text(encoding="utf-8"), (
        f"{SWEEP.parent.name}/{SWEEP.name} does not mention {LEDGER.name}"
    )
