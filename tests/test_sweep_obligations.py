"""Keep `docs/audit/sweep-obligations.md` describing the `audit-core` it cites.

The ledger records, one row per obligation, how the `audit` sweep discharges
each rule `audit-core` states. Its exposure is not that a row is wrong - a
reader has to judge that - but that `audit-core` gets reworded and every row
silently stops pointing at anything. Each row therefore quotes a verbatim
anchor, and that is checkable: an anchor no longer present in
`audit-core/SKILL.md` means the obligation moved, changed wording, or was
removed, and the row needs re-reading either way.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER = REPO_ROOT / "docs" / "audit" / "sweep-obligations.md"
AUDIT_CORE = REPO_ROOT / ".agents" / "skills" / "audit-core" / "SKILL.md"
SWEEP = REPO_ROOT / ".agents" / "skills" / "audit" / "SKILL.md"

DISPOSITIONS = frozenset({"restated", "adapted", "delegated", "out of scope"})

# The obligations table, identified by its own header rather than by position,
# so adding prose or another table above it does not silently select the wrong
# one - and so a renamed column fails here instead of yielding zero rows.
_ANCHOR_HEADER = "`audit-core` anchor"


def _cells(line: str) -> list[str]:
    """Split one Markdown table row into its trimmed cells."""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _obligation_rows() -> list[tuple[str, str, str]]:
    """Read the obligations table as (obligation, anchor, disposition) triples.

    Returns:
        One triple per data row, with the anchor unwrapped from its code span.
    """
    lines = LEDGER.read_text(encoding="utf-8").splitlines()
    header_idx = next(
        (
            i
            for i, line in enumerate(lines)
            if line.startswith("|") and _ANCHOR_HEADER in line
        ),
        None,
    )
    assert header_idx is not None, (
        f"{LEDGER.name} has no table with an {_ANCHOR_HEADER!r} column; the "
        "ledger's obligations table is what this module checks"
    )
    columns = _cells(lines[header_idx])
    anchor_col = columns.index(_ANCHOR_HEADER)
    disposition_col = columns.index("Disposition")

    rows: list[tuple[str, str, str]] = []
    # The separator row follows the header; data rows run to the first
    # non-table line.
    for line in lines[header_idx + 2 :]:
        if not line.startswith("|"):
            break
        cells = _cells(line)
        anchor = cells[anchor_col].strip("`")
        disposition = re.sub(r"[*`]", "", cells[disposition_col]).strip()
        rows.append((cells[0], anchor, disposition))
    return rows


ROWS = _obligation_rows()


def test_table_is_not_empty() -> None:
    """A ledger that parsed to nothing would pass every other test here."""
    assert ROWS, "the obligations table parsed to zero rows"


@pytest.mark.parametrize("obligation, anchor", [(r[0], r[1]) for r in ROWS])
def test_anchor_is_still_in_audit_core(obligation: str, anchor: str) -> None:
    """Each row's anchor is a verbatim substring of `audit-core/SKILL.md`."""
    assert anchor, f"{obligation!r} has an empty anchor"
    assert anchor in AUDIT_CORE.read_text(encoding="utf-8"), (
        f"{obligation!r} anchors on {anchor!r}, which is no longer in "
        f"{AUDIT_CORE.name} - the obligation was reworded, moved or removed, "
        "so re-read it and update the row"
    )


@pytest.mark.parametrize("obligation, disposition", [(r[0], r[2]) for r in ROWS])
def test_disposition_is_in_the_vocabulary(obligation: str, disposition: str) -> None:
    """Each row commits to one of the four dispositions the ledger defines."""
    assert disposition in DISPOSITIONS, (
        f"{obligation!r} has disposition {disposition!r}; the ledger defines "
        f"{sorted(DISPOSITIONS)}"
    )


def test_the_sweep_points_at_the_ledger() -> None:
    """The sweep links the ledger, so a reader of either finds the other.

    Without the link the ledger is discoverable only by whoever already knows
    it exists, which is the population that does not need it.
    """
    assert LEDGER.name in SWEEP.read_text(encoding="utf-8"), (
        f"{SWEEP.parent.name}/{SWEEP.name} does not mention {LEDGER.name}"
    )
