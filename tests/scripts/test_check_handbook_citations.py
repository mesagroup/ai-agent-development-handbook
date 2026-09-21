"""Tests for the handbook citation check (#139)."""

from __future__ import annotations

from pathlib import Path

import check_handbook_citations as chc
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_a_url_fragment_targets_the_stem_and_fragment(tmp_path: Path):
    (tmp_path / "SKILL.md").write_text(
        "See https://example.invalid/blob/main/docs/engineering/lifecycle.md#fan-out "
        "and docs/engineering/evaluation.md#loop twice: docs/engineering/evaluation.md#loop\n"
    )
    found = chc.skill_citations(tmp_path)
    assert {c.target for c in found} == {"lifecycle-fan-out", "evaluation-loop"}
    assert all(c.kind == "url" for c in found)
    assert len(found) == 2  # the repeated citation is one entry


def test_a_whole_part_url_targets_the_part_anchor(tmp_path: Path):
    (tmp_path / "SKILL.md").write_text(
        "docs/engineering/README.md and docs/engineering/nope.md\n"
    )
    targets = {c.target for c in chc.skill_citations(tmp_path)}
    assert "top" in targets  # README's part anchor
    assert any(t.startswith("<no part") for t in targets)  # an unknown stem reports


def test_a_row_targets_its_section_slug_not_the_slug_in_its_id():
    """The heading is named by the row's `section:` title, and the id's slug is ignored.

    On the live matrix the two agree once the id's split letter is dropped,
    because the matrix validator holds each id against its heading; deriving
    from `section:` is what keeps this check true if a row id ever diverges.
    """
    assert (
        chc.row_target(
            "lifecycle/fan-work-out-b",
            "Fan work out to parallel agents, and merge it honestly",
        )
        == "lifecycle-fan-work-out-to-parallel-agents-and-merge-it-honestly"
    )
    assert chc.row_target("coda/coda", "Coda") == "coda-coda"


def test_resolve_splits_on_membership():
    cites = [chc.Citation("url", "a", "x-one"), chc.Citation("row", "b", "x-two")]
    resolved, unresolved = chc.resolve(cites, {"x-one"})
    assert [c.source for c in resolved] == ["a"]
    assert [c.source for c in unresolved] == ["b"]


def test_report_names_every_unresolved_citation_and_fails_on_one():
    cites = [
        chc.Citation("url", "a.md", "x-one"),
        chc.Citation("url", "b.md", "x-gone"),
    ]
    text, ok = chc.report({"x-one"}, cites, [])
    assert not ok
    assert "skill citations: 2 found, 1 resolved" in text
    assert "UNRESOLVED url b.md -> x-gone" in text
    text, ok = chc.report({"x-one"}, cites[:1], [])
    assert ok


def test_page_ids_reads_every_id_attribute():
    assert chc.page_ids('<h2 id="a-b">x</h2><section id="p1">') == {"a-b", "p1"}


def test_every_citation_the_tree_emits_resolves_in_the_page_it_would_render():
    """#139's second criterion, held on the live tree without the d2 CLI.

    Both shapes: every URL fragment under the skills, every matrix row id.
    Vacuity is refused on both, because a regex that stopped matching would
    otherwise pass by finding nothing to resolve.
    """
    pytest.importorskip("markdown")
    ids = chc.heading_ids(chc.DOCS_DIR)
    skills = chc.skill_citations(chc.SKILLS_DIR)
    rows = chc.row_citations(chc.MATRIX)
    assert skills, "no citation found under the skills; the check would hold vacuously"
    assert rows, "no matrix row found; the check would hold vacuously"
    _, unresolved_skills = chc.resolve(skills, ids)
    _, unresolved_rows = chc.resolve(rows, ids)
    assert unresolved_skills == [], unresolved_skills
    assert unresolved_rows == [], unresolved_rows
