"""Tests for scripts/render_handbook_traceability.py (<origin-repo>#543)."""

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = REPO_ROOT / "scripts" / "render_handbook_traceability.py"

_spec = importlib.util.spec_from_file_location("rht", _SCRIPT)
assert _spec is not None and _spec.loader is not None
rht = importlib.util.module_from_spec(_spec)
sys.modules["rht"] = rht

_ac_spec = importlib.util.spec_from_file_location(
    "audit_checks", REPO_ROOT / "scripts" / "audit_checks.py"
)
assert _ac_spec is not None and _ac_spec.loader is not None
audit_checks = importlib.util.module_from_spec(_ac_spec)
sys.modules["audit_checks"] = audit_checks

# Both register in sys.modules before either execs: rht's own `from
# audit_checks import ...` runs during its exec_module below, and it must
# find the module this test file controls already in sys.modules - not
# re-import scripts/audit_checks.py from disk under a second identity via
# the normal import machinery (scripts/ is on sys.path via conftest.py).
_ac_spec.loader.exec_module(audit_checks)
_spec.loader.exec_module(rht)


def test_slugify_matches_github_anchor_rules():
    assert rht.slugify("The staged screening funnel") == "the-staged-screening-funnel"
    assert (
        rht.slugify("Dimensions (findings-matrix columns)")
        == "dimensions-findings-matrix-columns"
    )
    assert rht.slugify("Aliases, profiles & CLIs") == "aliases-profiles--clis"
    assert rht.slugify("`code` in a heading") == "code-in-a-heading"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_handbook_headings_skips_fences_and_deeper_levels(tmp_path):
    _write(
        tmp_path / "alpha.md",
        "# Alpha\n\n## First section\n\ntext\n\n### Not this one\n\n```\n## not a heading\n```\n\n## Second section\n",
    )
    _write(tmp_path / "coda.md", "# Coda\n\nno sections here\n")
    headings = rht.handbook_headings(tmp_path)
    assert headings == {"alpha": ["First section", "Second section"], "coda": []}


def test_handbook_headings_raises_on_an_unclosed_fence(tmp_path):
    # A stuck fence would swallow "Second section", and the coverage check
    # cannot miss a heading it never saw - so this has to fail loudly.
    _write(
        tmp_path / "alpha.md",
        "# Alpha\n\n## First section\n\n```\nunclosed\n\n## Second section\n",
    )
    with pytest.raises(ValueError, match="never closed"):
        rht.handbook_headings(tmp_path)


def test_handbook_headings_raises_when_a_fence_closes_with_the_other_marker(tmp_path):
    _write(
        tmp_path / "alpha.md",
        "# Alpha\n\n```\nopened with backticks\n~~~\n\n## Orphaned section\n",
    )
    with pytest.raises(ValueError, match="never closed"):
        rht.handbook_headings(tmp_path)


def test_handbook_headings_accepts_both_markers_matched(tmp_path):
    _write(
        tmp_path / "alpha.md",
        "# Alpha\n\n~~~\n## not a heading\n~~~\n\n## Real section\n",
    )
    assert rht.handbook_headings(tmp_path) == {"alpha": ["Real section"]}


def test_handbook_part_numbers_reads_the_h1_number(tmp_path):
    _write(tmp_path / "alpha.md", "# Part 5. The Extended Agent Harness\n\n## S\n")
    _write(tmp_path / "coda.md", "# Coda\n\ntext\n")
    assert rht.handbook_part_numbers(tmp_path) == {"alpha": 5, "coda": None}


def test_validate_parts_catches_renumbering_and_missing_parts(monkeypatch):
    monkeypatch.setattr(rht, "PART_ORDER", ["alpha", "ghost"])
    monkeypatch.setattr(
        rht, "PART_TITLES", {"alpha": "Part 5: Alpha", "ghost": "Part 9: Ghost"}
    )
    # alpha renumbered upstream 5 -> 6; ghost has no file; beta is new on disk.
    errors = rht.validate_parts({"alpha": 6, "beta": 2})
    assert any("PART_TITLES says part 5, the handbook H1 says 6" in e for e in errors)
    assert any("beta: handbook part is missing from PART_ORDER" in e for e in errors)
    assert any("ghost: PART_ORDER names a part with no file" in e for e in errors)
    assert len(errors) == 3


def test_validate_parts_passes_on_the_real_handbook():
    assert rht.validate_parts(rht.handbook_part_numbers(rht.HANDBOOK_DIR)) == []


def _check(cid, title, handbook, note=None):
    """A `Check` built in memory, for fixtures that need no record on disk.

    `_checks_tree` below writes real files and is what the loader-facing
    tests use. These fixtures only need `validate` and `render` to resolve
    an id, so constructing the record directly keeps them from depending on
    the record file format.
    """
    return audit_checks.Check(
        id=cid,
        domain=cid.split("/", 1)[0],
        locality="local",
        title=title,
        handbook=tuple(handbook),
        handbook_note=note,
        tooling={},
        needs={},
        ungranted_note=None,
        routes=(),
        answers_ungranted=None,
        evidence=None,
        optin=False,
        path=Path(f"{cid}.md"),
    )


# `demo/secrets` declares no grounding, so it stays legitimately uncited by
# `_valid_rows`; only the render tests that append it cite it, and render
# does not enforce the bidirectional rule.
_DEMO_CHECKS = {
    "demo/injection": _check("demo/injection", "Injection", ["alpha/mapped-section"]),
    "demo/secrets": _check("demo/secrets", "Secrets", [], note="rendering fixture"),
}


def _write_demo_record(tmp_path):
    """Put `demo/injection` on disk, matching its `_DEMO_CHECKS` entry.

    The `main()` tests load records from `SKILLS_DIR` rather than being
    handed a dict, so the row that `_valid_rows` grounds needs a real file
    or every one of them fails on an unknown check id.
    """
    _write(
        tmp_path / "skills" / "demo-audit" / "checks" / "injection.md",
        "---\nid: demo/injection\ndomain: demo\nlocality: local\n"
        "handbook:\n  - alpha/mapped-section\n---\n\n# Injection\n\nclaim.\n",
    )


def _fixture_dirs(tmp_path):
    _write(
        tmp_path / "handbook" / "alpha.md",
        "# Alpha\n\n## Mapped section\n\ntext\n\n## Split section\n\ntext\n",
    )
    _write(tmp_path / "handbook" / "coda.md", "# Coda\n\nno sections\n")
    _write_demo_record(tmp_path)
    return rht.handbook_headings(tmp_path / "handbook")


def _fixture_dirs_with_extra_sections(tmp_path):
    """`_fixture_dirs` plus two more alpha sections, for multi-entry bands.

    A band needs more than one entry of a kind to exercise the plural
    branches, and every row must resolve to a real heading or `validate`
    rejects it.
    """
    _write(
        tmp_path / "handbook" / "alpha.md",
        "# Alpha\n\n## Mapped section\n\ntext\n\n## Split section\n\ntext\n"
        "\n## Second unmapped\n\ntext\n\n## Second process\n\ntext\n",
    )
    _write(tmp_path / "handbook" / "coda.md", "# Coda\n\nno sections\n")
    _write_demo_record(tmp_path)
    return rht.handbook_headings(tmp_path / "handbook")


def _valid_rows():
    return [
        {
            "id": "alpha/mapped-section",
            "section": "Mapped section",
            "claim": "c1",
            "class": "static",
            "severity": "important",
            "checks": ["demo/injection"],
        },
        {
            "id": "alpha/split-section-a",
            "section": "Split section",
            "claim": "c2a",
            "class": "artifact",
            "severity": "critical",
            "gap": {
                "recommendation": "new-domain",
                "target": "#2",
                "note": "no lens yet",
            },
        },
        {
            "id": "alpha/split-section-b",
            "section": "Split section",
            "claim": "c2b",
            "class": "process",
            "severity": "minor",
        },
        {
            "id": "coda/coda",
            "section": "Coda",
            "claim": "closing words",
            "class": "informative",
        },
    ]


def test_validate_accepts_the_valid_fixture(tmp_path):
    headings = _fixture_dirs(tmp_path)
    assert rht.validate(_valid_rows(), headings, _DEMO_CHECKS) == []


def test_validate_catches_each_rule(tmp_path):
    headings = _fixture_dirs(tmp_path)
    # (mutation, expected message fragment, expected total error count) - the
    # count pins over-firing: a rule that also flags something else fails here.
    # A mutation that costs row 0 its heading also orphans it, and one that
    # costs row 0 its citation also orphans `demo/injection`, since the
    # bidirectional rule reads the record and the matrix as one edge set.
    # Both are real second defects, so they are counted rather than excused.
    cases = [
        (
            lambda r: r[0].update(id="alpha/mapped-section", section="Wrong text"),
            "does not match heading",
            1,
        ),
        (
            lambda r: r[0].update(id="nowhere/mapped-section"),
            "unknown handbook part",
            3,
        ),
        (lambda r: r[0].update(id="alpha/no-such-anchor"), "does not resolve", 3),
        (lambda r: r[0].update(**{"class": "bogus"}), "class must be one of", 1),
        (lambda r: r[0].pop("checks"), "needs checks or a gap", 2),
        (
            lambda r: r[3].update(checks=["demo/injection"]),
            "must not carry checks",
            1,
        ),
        # An id with no record: the row's citation is dropped, which also
        # leaves demo/injection uncited, hence 2.
        (lambda r: r[0].update(checks=["demo/ghost"]), "unknown check id", 2),
        # A branch predating <origin-repo>#559 carries the pair form. It is named as such
        # rather than reported as a type error, so its author is sent to the
        # record that replaced it.
        (
            lambda r: r[0].update(
                checks=[{"skill": "demo-audit", "dimension": "Injection"}]
            ),
            "legacy {skill, dimension} entry",
            2,
        ),
        # Anything else that is not a string is a plain shape error.
        (lambda r: r[0].update(checks=[["demo/injection"]]), "must be a check id", 2),
        (
            lambda r: r[1]["gap"].update(recommendation="wontfix"),
            "recommendation must be one of",
            1,
        ),
        (lambda r: r.append(dict(r[0])), "duplicate id", 1),
        (lambda r: r.pop(3), "coda.md has no whole-part row", 1),
        (lambda r: (r.pop(1), r.pop(1)), "has no matrix row", 1),
        (lambda r: r[0].pop("severity"), "needs severity one of", 1),
        (lambda r: r[2].update(severity="blocker"), "needs severity one of", 1),
        (
            lambda r: r[3].update(severity="minor"),
            "informative rows carry no severity",
            1,
        ),
        (
            lambda r: r[3].update(gap={"recommendation": "extend-skill", "note": "x"}),
            "informative row must not carry a gap",
            1,
        ),
    ]
    for mutate, expected, count in cases:
        rows = _valid_rows()
        mutate(rows)
        errors = rht.validate(rows, headings, _DEMO_CHECKS)
        assert any(expected in e for e in errors), f"{expected!r} not in {errors}"
        assert len(errors) == count, f"{expected!r} produced {errors}"


_ALPHA_URL = f"{rht.HANDBOOK_URL}/alpha.md"


def test_render_produces_tables_gap_list_and_summary():
    rows = _valid_rows()
    out = rht.render(rows, _DEMO_CHECKS)
    assert "generated file" in out.lower()
    # Relative link, and no absolute one anywhere in the document. The guard is
    # the negative half: this file is read in the repo or on GitHub, so an
    # absolute URL only bakes the org and repository name into every report
    # the matrix is copied into. Forbidding
    # the scheme rather than one spelling of the org keeps the assertion from
    # passing on a URL nothing could produce.
    assert f"[Mapped section]({_ALPHA_URL}#mapped-section)<br>c1" in out
    assert "https://github.com/" not in out
    assert "`demo/injection` / Injection" in out
    assert "### Critical" in out and "#2" in out
    assert "| static | 1 |" in out


def test_render_marks_split_rows_and_links_gap_entries():
    out = rht.render(_valid_rows(), _DEMO_CHECKS)
    # Both slices of a split section link to the same anchor, distinguished by
    # the marker; the claim is what tells them apart.
    assert f"[Split section]({_ALPHA_URL}#split-section) (a)<br>c2a" in out
    assert f"[Split section]({_ALPHA_URL}#split-section) (b)<br>c2b" in out
    # A whole-part row (no ## headings) links to the file, with no marker.
    assert f"[Coda]({rht.HANDBOOK_URL}/coda.md)<br>closing words |" in out
    # Every gap entry links back to its handbook section, marker included.
    assert (
        f"- [`alpha/split-section-a`]({_ALPHA_URL}#split-section) (a) (unchecked) - "
        "**new-domain** - #2 - no lens yet" in out
    )


def test_render_reports_full_and_partial_coverage_apart():
    rows = _valid_rows()
    # A row that carries both a check and a residual gap is partial, not mapped.
    rows[0]["gap"] = {"recommendation": "extend-skill", "note": "residue"}
    out = rht.render(rows, _DEMO_CHECKS)
    assert "**0 fully mapped** (0%), **1 partially mapped**" in out
    assert "**1 unmapped**" in out


def test_render_reconciles_the_gap_total_when_no_process_row_gaps():
    rows = _valid_rows()
    rows[0]["gap"] = {"recommendation": "extend-skill", "note": "residue"}
    out = rht.render(rows, _DEMO_CHECKS)
    assert (
        "All 2 gap entries sit on auditable rows: the 1 unmapped one plus "
        "the 1 partial." in out
    )
    # The unreconciled phrasing is gone.
    assert "rows carry a gap entry in total" not in out


def test_render_reconciles_the_gap_total_when_a_process_row_gaps():
    # The case <origin-repo>#554 names: the closing total counted a population the
    # components above it never included. It is absent from today's matrix,
    # so only a fixture can hold the arithmetic honest.
    rows = _valid_rows()
    rows[0]["gap"] = {"recommendation": "extend-skill", "note": "residue"}
    rows[2]["gap"] = {"recommendation": "report-only", "note": "prose only"}
    out = rht.render(rows, _DEMO_CHECKS)
    assert "2 of the 3 gap entries sit on auditable rows" in out
    assert "all 1 unmapped" in out
    assert "plus the 1 partial" in out
    assert "the other 1 sits on a process row" in out


def test_render_reconciles_the_gap_total_in_the_plural(tmp_path):
    # Both branches alternate on count, and the singular fixtures above pin
    # only one side of each alternation. The real matrix does exercise the
    # plural today, but only through the golden .md - which is regenerated
    # by this same renderer, so it would ratify a typo rather than catch it.
    headings = _fixture_dirs_with_extra_sections(tmp_path)
    rows = _valid_rows()
    rows[0]["gap"] = {"recommendation": "extend-skill", "note": "residue"}
    rows[2]["gap"] = {"recommendation": "report-only", "note": "prose only"}
    rows.append(
        {
            "id": "alpha/second-unmapped",
            "section": "Second unmapped",
            "claim": "c3",
            "class": "static",
            "severity": "minor",
            "gap": {"recommendation": "new-domain", "note": "no owner"},
        }
    )
    rows.append(
        {
            "id": "alpha/second-process",
            "section": "Second process",
            "claim": "c4",
            "class": "process",
            "severity": "minor",
            "gap": {"recommendation": "report-only", "note": "prose only"},
        }
    )
    # The fixture stays schema-valid, so the arithmetic it pins is reachable.
    assert rht.validate(rows, headings, _DEMO_CHECKS) == []
    out = rht.render(rows, _DEMO_CHECKS)
    assert "3 of the 5 gap entries sit on auditable rows" in out
    assert "all 2 unmapped" in out
    assert "the other 2 sit on process rows" in out


def test_render_states_a_severity_band_that_carries_no_gap():
    # A band that clears its gaps must say so. Omitting the heading is
    # indistinguishable from a rendering fault, and this is the one piece of
    # good news the page can report.
    rows = _valid_rows()
    rows[1].pop("gap")
    rows[1]["checks"] = ["demo/injection"]
    rows[0]["gap"] = {"recommendation": "extend-skill", "note": "residue"}
    out = rht.render(rows, _DEMO_CHECKS)
    assert "### Critical\n\nNo Critical clause carries a gap.\n" in out
    assert "### Important\n\n1 residue.\n" in out


def test_render_emits_no_band_headings_when_nothing_gaps():
    # The whole-document empty state stands on its own; three "no gap"
    # bands under it would be noise.
    rows = _valid_rows()
    rows[1].pop("gap")
    rows[1]["checks"] = ["demo/injection"]
    out = rht.render(rows, _DEMO_CHECKS)
    assert "No gaps: every auditable row is mapped." in out
    assert "### Critical" not in out
    assert "### Important" not in out


def test_render_shows_row_notes_in_the_notes_column():
    rows = _valid_rows()
    rows[2]["note"] = "Process | culture:\nnot datable from a snapshot."
    out = rht.render(rows, _DEMO_CHECKS)
    assert "| Section / claim | Class | Severity | Mapped checks | Gap | Notes |" in out
    # Pipes escaped and the note folded onto the row's single table line.
    assert (
        "| process | Minor | - | - | Process \\| culture: not datable from a snapshot. |"
        in out
    )
    # A row without a note still renders a placeholder cell.
    assert (
        f"[Coda]({rht.HANDBOOK_URL}/coda.md)<br>closing words | informative | - | - | - | - |"
        in out
    )


def test_render_joins_multiple_checks_and_a_gap_without_a_target():
    rows = _valid_rows()
    rows[0]["checks"].append("demo/secrets")
    rows[1]["gap"].pop("target")
    out = rht.render(rows, _DEMO_CHECKS)
    # Two checks share one cell, separated by a break rather than a newline.
    assert "`demo/injection` / Injection<br>`demo/secrets` / Secrets" in out
    # A target-less gap renders no empty parentheses, in cell and in bullet.
    assert "**new-domain** - no lens yet" in out
    assert (
        f"- [`alpha/split-section-a`]({_ALPHA_URL}#split-section) (a) (unchecked) - "
        "**new-domain** - no lens yet" in out
    )
    assert "()" not in out


def test_render_keeps_gap_fields_from_breaking_the_table():
    rows = _valid_rows()
    rows[1]["gap"]["target"] = "#2 | #11"
    rows[1]["gap"]["note"] = "two lenses:\nneither owns the bound."
    out = rht.render(rows, _DEMO_CHECKS)
    # In a table cell both the pipe and the newline are fatal; escape and fold.
    assert "**new-domain** - #2 \\| #11 - two lenses: neither owns the bound. |" in out
    # In the gap-list bullet a pipe is harmless, but the newline still is not.
    assert "- **new-domain** - #2 | #11 - two lenses: neither owns the bound." in out
    for line in out.splitlines():
        if line.startswith("| ["):
            assert line.endswith(" |"), line


def test_render_emits_a_severity_column():
    out = rht.render(_valid_rows(), _DEMO_CHECKS)
    assert "| Section / claim | Class | Severity | Mapped checks | Gap | Notes |" in out
    assert "| static | Important |" in out
    assert "| artifact | Critical |" in out
    # The informative row carries no severity and renders a placeholder.
    assert "| informative | - |" in out


def test_render_groups_the_gap_list_by_severity_worst_first():
    rows = _valid_rows()
    # A second gap, one level down, so the ordering is observable.
    rows[0]["gap"] = {"recommendation": "extend-skill", "note": "residue"}
    out = rht.render(rows, _DEMO_CHECKS)
    assert out.index("### Critical") < out.index("### Important")
    # The Critical row's bullet precedes the Important heading.
    assert out.index("`alpha/split-section-a`") < out.index("### Important")
    # Grouping is by severity now, not by recommendation.
    assert "### new-domain" not in out
    assert "### extend-skill" not in out


def _rows_with_all_three_kinds():
    # One band holding all three kinds at once, so tags, counts, and ordering
    # are all observable from a single render.
    rows = _valid_rows()
    rows[0]["severity"] = "critical"
    rows[0]["gap"] = {"recommendation": "extend-skill", "note": "residue"}
    rows[2]["severity"] = "critical"
    rows[2]["gap"] = {"recommendation": "report-only", "note": "prose only"}
    return rows


def test_render_tags_each_gap_bullet_with_its_kind():
    # A bullet has to carry its own kind: #9 emits issues from single
    # entries, and a position in a list does not survive extraction.
    out = rht.render(_rows_with_all_three_kinds(), {})
    assert "- [`alpha/mapped-section`](" in out
    assert "#mapped-section) (residue) - **extend-skill**" in out
    assert "#split-section) (a) (unchecked) - **new-domain**" in out
    assert "#split-section) (b) (process) - **report-only**" in out


def test_render_opens_each_band_with_its_kind_split():
    out = rht.render(_rows_with_all_three_kinds(), {})
    assert "### Critical\n\n1 unchecked, 1 residue, 1 process row.\n" in out


def test_render_suppresses_zero_terms_in_the_kind_split():
    # A band with one kind states that kind alone, rather than padding two
    # zeroes a reader has to skip.
    out = rht.render(_valid_rows(), _DEMO_CHECKS)
    assert "### Critical\n\n1 unchecked.\n" in out
    assert "0 residue" not in out
    assert "0 process" not in out


def test_kind_split_line_pluralizes_a_kind_with_more_than_one_entry():
    # Task 1's plural branches ("residues", "process rows") were exercised
    # only indirectly, via the golden-file comparison in
    # test_real_matrix_passes_the_strict_check - which fails with a
    # confusing "handbook-traceability.md is stale" message rather than
    # pointing at the bug. A direct fixture with two residues in one band
    # pins the plural wording itself.
    # The rows carry a gap because that is the precondition the function
    # documents; it never reads the field, but a fixture that violates the
    # stated contract stops being evidence about the real call site.
    group = [
        {
            "class": "static",
            "checks": ["demo/injection"],
            "gap": {"recommendation": "extend-skill", "note": "residue"},
        },
        {
            "class": "static",
            "checks": ["demo/secrets"],
            "gap": {"recommendation": "extend-skill", "note": "residue"},
        },
    ]
    assert rht._kind_split_line(group) == "2 residues."


def test_render_orders_gap_bullets_unchecked_then_residue_then_process():
    out = rht.render(_rows_with_all_three_kinds(), {})
    # Anchors keep the closing paren + tag + " - " separator so they only
    # match a bullet's own kind tag, not the preamble prose naming the same
    # three tags (which would otherwise satisfy the index() check on its own).
    assert (
        out.index(") (a) (unchecked) - ")
        < out.index(") (residue) - ")
        < out.index(") (b) (process) - ")
    )


def test_render_cross_tabs_severity_against_mapped_status():
    out = rht.render(_valid_rows(), _DEMO_CHECKS)
    assert "### Severity x coverage" in out
    # Critical: the artifact row, gapped and unmapped. Important: the static
    # row, fully mapped. Minor: the process row, auditable of neither kind.
    assert "| Critical | 0 | 0 | 1 | 1 | 0 |" in out
    assert "| Important | 1 | 0 | 0 | 1 | 0 |" in out
    assert "| Minor | 0 | 0 | 0 | 0 | 1 |" in out


def test_render_states_both_interpretation_rules_in_the_legend():
    out = rht.render(_valid_rows(), _DEMO_CHECKS)
    assert "**Baseline, not verdict.**" in out
    assert "Only `informative` rows have none." in out


def _patch_paths(monkeypatch, tmp_path, parts):
    monkeypatch.setattr(rht, "PART_ORDER", list(parts))
    monkeypatch.setattr(rht, "PART_TITLES", {p: p.title() for p in parts})
    monkeypatch.setattr(rht, "HANDBOOK_DIR", tmp_path / "handbook")
    monkeypatch.setattr(rht, "SKILLS_DIR", tmp_path / "skills")
    monkeypatch.setattr(rht, "YAML_PATH", tmp_path / "handbook-traceability.yaml")
    monkeypatch.setattr(rht, "MD_PATH", tmp_path / "handbook-traceability.md")
    monkeypatch.setattr(rht, "REPO_ROOT", tmp_path)
    # SKILLS_DIR is where main() looks for check records too, so pointing it
    # at the fixture tree is what keeps a fixture run judged against its own
    # records - `demo/injection` alone, written by `_fixture_dirs`. The real
    # records under .agents/skills/ are never loaded here, and could not be:
    # they cite real handbook anchors the fixture handbook does not have.


def test_main_fails_when_the_handbook_renumbers_under_the_constants(
    tmp_path, monkeypatch
):
    import yaml as _yaml

    _fixture_dirs(tmp_path)
    _patch_paths(monkeypatch, tmp_path, ["alpha", "coda"])
    monkeypatch.setattr(rht, "PART_TITLES", {"alpha": "Part 5: Alpha", "coda": "Coda"})
    (tmp_path / "handbook" / "alpha.md").write_text(
        "# Part 6. Alpha\n\n## Mapped section\n\ntext\n\n## Split section\n\ntext\n"
    )
    (tmp_path / "handbook-traceability.yaml").write_text(
        _yaml.safe_dump(_valid_rows(), sort_keys=False, allow_unicode=True)
    )
    assert rht.main([]) == 1


def test_main_check_detects_a_stale_md(tmp_path, monkeypatch):
    headings_dir = tmp_path / "handbook"
    _fixture_dirs(tmp_path)
    monkeypatch.setattr(rht, "PART_ORDER", ["alpha", "coda"])
    monkeypatch.setattr(rht, "PART_TITLES", {"alpha": "Alpha", "coda": "Coda"})
    yaml_path = tmp_path / "handbook-traceability.yaml"
    md_path = tmp_path / "handbook-traceability.md"
    import yaml as _yaml

    yaml_path.write_text(
        _yaml.safe_dump(_valid_rows(), sort_keys=False, allow_unicode=True)
    )
    monkeypatch.setattr(rht, "HANDBOOK_DIR", headings_dir)
    monkeypatch.setattr(rht, "SKILLS_DIR", tmp_path / "skills")
    monkeypatch.setattr(rht, "YAML_PATH", yaml_path)
    monkeypatch.setattr(rht, "MD_PATH", md_path)
    monkeypatch.setattr(rht, "REPO_ROOT", tmp_path)
    assert rht.main(["--check"]) == 1  # md missing -> stale
    assert rht.main([]) == 0  # writes the md
    assert rht.main(["--check"]) == 0  # now fresh
    md_path.write_text(md_path.read_text() + "tampered\n")
    assert rht.main(["--check"]) == 1


def test_main_renders_a_populated_checks_tree(tmp_path, monkeypatch):
    """`main()` renders the id/title cell from a record it loaded itself.

    The other `main()` tests carry `_fixture_dirs`' record and so exercise
    load and cross-check, but none of them asserts the rendered cell. This
    one uses a record whose title differs from the id every row cites, so a
    cell that echoed the id instead of resolving it would show here.
    """
    import yaml as _yaml

    _fixture_dirs(tmp_path)
    _patch_paths(monkeypatch, tmp_path, ["alpha", "coda"])
    _write(
        tmp_path / "skills" / "demo-audit" / "checks" / "thing.md",
        "---\n"
        "id: demo/thing\n"
        "domain: demo\n"
        "locality: local\n"
        "handbook:\n"
        "  - alpha/mapped-section\n"
        "---\n\n"
        "# Thing\n\ntext\n",
    )
    rows = _valid_rows()
    # Both, so the fixture's own record stays cited and the bidirectional
    # rule does not fire on it.
    rows[0]["checks"] = ["demo/injection", "demo/thing"]
    (tmp_path / "handbook-traceability.yaml").write_text(
        _yaml.safe_dump(rows, sort_keys=False, allow_unicode=True)
    )
    assert rht.main([]) == 0
    assert "`demo/thing` / Thing" in (tmp_path / "handbook-traceability.md").read_text()
    assert rht.main(["--check"]) == 0


def test_main_fails_on_an_uncovered_handbook_part(tmp_path, monkeypatch):
    import yaml as _yaml

    _fixture_dirs(tmp_path)
    _write(tmp_path / "handbook" / "beta.md", "# Beta\n\n## Unwalked section\n\ntext\n")
    # beta is a known part, so the only thing wrong is its missing row.
    _patch_paths(monkeypatch, tmp_path, ["alpha", "beta", "coda"])
    (tmp_path / "handbook-traceability.yaml").write_text(
        _yaml.safe_dump(_valid_rows(), sort_keys=False, allow_unicode=True)
    )
    assert rht.main([]) == 1  # beta.md has no rows -> coverage hole, no escape hatch


def test_validate_reports_malformed_shapes_without_crashing(tmp_path):
    headings = _fixture_dirs(tmp_path)
    malformed_rows = [
        "bare string row",
        {
            "id": "alpha/mapped-section",
            "section": "Mapped section",
            "class": "static",
            "severity": "important",
            "checks": "not a list",
        },
        {
            "id": "alpha/split-section-a",
            "section": "Split section",
            "class": "artifact",
            "severity": "critical",
            "checks": [123],
            "gap": {"recommendation": "new-domain", "target": "#2"},
        },
        {
            "id": "coda/coda",
            "section": "Coda",
            "class": "informative",
            "gap": "not a dict",
        },
    ]
    # An empty checks tree: this test is about row shapes, and a populated
    # one would add bidirectional-integrity errors that say nothing about
    # whether a malformed row crashes the validator.
    errors = rht.validate(malformed_rows, headings, {})
    assert "not a mapping" in str(errors)
    assert "checks must be a list" in str(errors)
    assert "check entries must be a check id string" in str(errors)
    assert "gap must be a mapping" in str(errors)
    assert len(errors) == 5


def test_real_matrix_passes_the_strict_check():
    assert rht.main(["--check"]) == 0


def test_real_matrix_band_unchecked_counts_match_the_cross_tab():
    # <origin-repo>#553's second criterion, made mechanical rather than a counting
    # exercise: a band's printed unchecked figure is the same number as its
    # Unmapped column, and stays so as rows are added. Both are read out of
    # the rendered page, so a renderer that drifts them apart fails here.
    import re

    rows = yaml.safe_load(rht.YAML_PATH.read_text())
    out = rht.render(rows, _DEMO_CHECKS)

    printed = {}
    for sev in ("Critical", "Important", "Minor"):
        m = re.search(rf"### {sev}\n\n([^\n]+)\n", out)
        assert m, f"no kind-split line under ### {sev}"
        n = re.search(r"(\d+) unchecked", m.group(1))
        printed[sev] = int(n.group(1)) if n else 0

    cross_tab = {}
    for sev in ("Critical", "Important", "Minor"):
        m = re.search(rf"\| {sev} \| \d+ \| \d+ \| (\d+) \|", out)
        assert m, f"no cross-tab row for {sev}"
        cross_tab[sev] = int(m.group(1))

    assert printed == cross_tab


def _checks_tree(tmp_path, records):
    """Write a checks tree and load it, for validate()'s `checks` argument.

    Args:
        tmp_path: pytest tmp dir.
        records: Mapping of `<domain>/<slug>` to a frontmatter dict; the body
            title is derived from the slug.

    Returns:
        The id-keyed `Check` mapping `validate` expects.
    """
    root = tmp_path / "fixture-skills"
    for cid, meta in records.items():
        domain, slug = cid.split("/", 1)
        path = root / f"{domain}-audit" / "checks" / f"{slug}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        front = yaml.safe_dump({"id": cid, **meta}, sort_keys=False)
        path.write_text(f"---\n{front}---\n\n# {slug}\n\nclaim.\n")
    checks, errors = audit_checks.load_checks(root)
    assert errors == []
    return checks


_HEADINGS = {"alpha": ["First section"]}


def _row(**over):
    row = {
        "id": "alpha/first-section",
        "section": "First section",
        "class": "static",
        "severity": "minor",
        "checks": ["alpha/one"],
    }
    row.update(over)
    return row


def _one(**over):
    meta = {"domain": "alpha", "locality": "local", "handbook": ["alpha/first-section"]}
    meta.update(over)
    return meta


def test_string_check_entry_resolves_against_the_check_tree(tmp_path):
    checks = _checks_tree(tmp_path, {"alpha/one": _one()})
    assert rht.validate([_row()], _HEADINGS, checks) == []


def test_unknown_check_id_is_reported(tmp_path):
    checks = _checks_tree(tmp_path, {"alpha/one": _one()})
    errors = rht.validate([_row(checks=["alpha/nope"])], _HEADINGS, checks)
    assert any("unknown check id" in e for e in errors)


def test_legacy_skill_dimension_entry_is_named_not_typed(tmp_path):
    # The pair form is what a branch predating <origin-repo>#559 carries. "expected a
    # string" would send its author hunting a typo in the matrix; naming the
    # form points at the record that replaced it.
    checks = _checks_tree(
        tmp_path, {"alpha/one": _one(handbook=[], handbook_note="n/a")}
    )
    rows = [_row(checks=[{"skill": "docs-audit", "dimension": "Coverage"}])]
    errors = rht.validate(rows, _HEADINGS, checks)
    assert any("legacy {skill, dimension} entry" in e for e in errors)
    assert any("named by record id" in e for e in errors)


def test_handbook_anchor_must_resolve_to_a_heading(tmp_path):
    checks = _checks_tree(tmp_path, {"alpha/one": _one(handbook=["alpha/ghost"])})
    errors = rht.validate([_row()], _HEADINGS, checks)
    assert any("does not resolve" in e for e in errors)


def test_handbook_anchor_must_be_a_row_that_cites_the_check(tmp_path):
    # alpha/two is cited, so rule 5 is satisfied; the anchor it names is the
    # base row, which cites alpha/one only, so rule 4 must fire.
    checks = _checks_tree(tmp_path, {"alpha/one": _one(), "alpha/two": _one()})
    rows = [_row(), _row(id="alpha/first-section-b", checks=["alpha/two"])]
    errors = rht.validate(rows, _HEADINGS, checks)
    assert any("no matrix row citing" in e for e in errors)


def test_cited_check_may_not_claim_to_be_ungrounded(tmp_path):
    checks = _checks_tree(
        tmp_path, {"alpha/one": _one(handbook=[], handbook_note="why")}
    )
    errors = rht.validate([_row()], _HEADINGS, checks)
    assert any("empty handbook" in e for e in errors)


def test_uncited_check_must_not_claim_a_grounding(tmp_path):
    checks = _checks_tree(tmp_path, {"alpha/one": _one(), "alpha/two": _one()})
    errors = rht.validate([_row()], _HEADINGS, checks)
    assert any("alpha/two" in e and "no matrix row" in e for e in errors)


def test_an_uncited_check_reports_once_not_once_per_anchor(tmp_path):
    """One defect, one message - even when the record names several anchors.

    The summary rule and the per-anchor rule both recognise "nothing cites
    this check", so before they were made exclusive a record naming N
    anchors produced 1 + N messages for a single problem, against this
    module's one-message-per-problem contract.
    """
    checks = _checks_tree(
        tmp_path,
        {
            "alpha/one": _one(),
            "alpha/two": _one(
                handbook=["alpha/first-section", "alpha/first-section-b"]
            ),
        },
    )
    errors = rht.validate([_row()], _HEADINGS, checks)
    assert [e for e in errors if e.startswith("alpha/two:")] == [
        "alpha/two: cites 2 handbook anchor(s) but no matrix row cites this check; "
        "add the citation to the matrix or empty the handbook list and explain why "
        "in handbook_note"
    ]


def test_checks_cell_renders_id_and_title(tmp_path):
    checks = _checks_tree(tmp_path, {"alpha/one": _one()})
    cell = rht._checks_cell(_row(), checks)
    assert cell == "`alpha/one` / one"


def test_checks_cell_renders_an_unresolvable_id_bare():
    # `validate` has already reported the unknown id; the renderer's job is
    # to render whatever validation let through, not to raise a second time.
    assert (
        rht._checks_cell(_row(checks=["alpha/ghost"]), {})
        == "`alpha/ghost` / alpha/ghost"
    )
