"""Tests for scripts/render_handbook_traceability.py (#543)."""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = REPO_ROOT / "scripts" / "render_handbook_traceability.py"

_spec = importlib.util.spec_from_file_location("rht", _SCRIPT)
assert _spec is not None and _spec.loader is not None
rht = importlib.util.module_from_spec(_spec)
sys.modules["rht"] = rht
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


def test_skill_dimensions_raises_on_an_unparseable_dimensions_section(tmp_path):
    # Reformatted bullets must not read as "this skill has no dimensions":
    # every check citing it would then fail as an unknown skill, blaming the
    # matrix for a change made in the skill.
    _write(
        tmp_path / "demo-audit" / "SKILL.md",
        "## 2. Dimensions (findings-matrix columns)\n\n* _Injection_ - reformatted.\n",
    )
    with pytest.raises(ValueError, match="no bullet matching"):
        rht.skill_dimensions(tmp_path)


def test_skill_dimensions_reads_bolded_bullets_until_next_heading(tmp_path):
    _write(
        tmp_path / "demo-audit" / "SKILL.md",
        "---\nname: demo-audit\n---\n\n## 1. Subject\n\ntext\n\n## 2. Dimensions (findings-matrix columns)\n\n"
        "- **Injection** — command, SQL.\n- **Secrets & credential handling** — keys in code.\n\n"
        "## 3. Evidence\n\n- **Not a dimension** — different section.\n"
        "## 6. Review dimensions (Phase-5 specialized reviewers)\n\n"
        "- **Exploitability** — would fail if captured.\n",
    )
    _write(
        tmp_path / "helper" / "SKILL.md",
        "---\nname: helper\n---\n\nNo dimensions heading.\n",
    )
    dims = rht.skill_dimensions(tmp_path)
    assert dims == {"demo-audit": ["Injection", "Secrets & credential handling"]}


def _fixture_dirs(tmp_path):
    _write(
        tmp_path / "handbook" / "alpha.md",
        "# Alpha\n\n## Mapped section\n\ntext\n\n## Split section\n\ntext\n",
    )
    _write(tmp_path / "handbook" / "coda.md", "# Coda\n\nno sections\n")
    _write(
        tmp_path / "skills" / "demo-audit" / "SKILL.md",
        "## 2. Dimensions (findings-matrix columns)\n\n- **Injection** — text.\n",
    )
    return rht.handbook_headings(tmp_path / "handbook"), rht.skill_dimensions(
        tmp_path / "skills"
    )


def _valid_rows():
    return [
        {
            "id": "alpha/mapped-section",
            "section": "Mapped section",
            "claim": "c1",
            "class": "static",
            "checks": [{"skill": "demo-audit", "dimension": "Injection"}],
        },
        {
            "id": "alpha/split-section-a",
            "section": "Split section",
            "claim": "c2a",
            "class": "artifact",
            "gap": {
                "recommendation": "new-domain",
                "target": "#516",
                "note": "no lens yet",
            },
        },
        {
            "id": "alpha/split-section-b",
            "section": "Split section",
            "claim": "c2b",
            "class": "process",
        },
        {
            "id": "coda/coda",
            "section": "Coda",
            "claim": "closing words",
            "class": "informative",
        },
    ]


def test_validate_accepts_the_valid_fixture(tmp_path):
    headings, dims = _fixture_dirs(tmp_path)
    assert rht.validate(_valid_rows(), headings, dims) == []


def test_validate_catches_each_rule(tmp_path):
    headings, dims = _fixture_dirs(tmp_path)
    # (mutation, expected message fragment, expected total error count) - the
    # count pins over-firing: a rule that also flags something else fails here.
    # A count of 2 means the mutation additionally orphans a real heading.
    cases = [
        (
            lambda r: r[0].update(id="alpha/mapped-section", section="Wrong text"),
            "does not match heading",
            1,
        ),
        (
            lambda r: r[0].update(id="nowhere/mapped-section"),
            "unknown handbook part",
            2,
        ),
        (lambda r: r[0].update(id="alpha/no-such-anchor"), "does not resolve", 2),
        (lambda r: r[0].update(**{"class": "bogus"}), "class must be one of", 1),
        (lambda r: r[0].pop("checks"), "needs checks or a gap", 1),
        (
            lambda r: r[3].update(
                checks=[{"skill": "demo-audit", "dimension": "Injection"}]
            ),
            "must not carry checks",
            1,
        ),
        (lambda r: r[0]["checks"][0].update(skill="ghost-audit"), "unknown skill", 1),
        (
            lambda r: r[0]["checks"][0].update(dimension="Ghost dimension"),
            "no dimension",
            1,
        ),
        # A bare `dimension:` parses to None; it must name the row, not raise.
        (
            lambda r: r[0]["checks"][0].update(dimension=None),
            "dimension must be a string",
            1,
        ),
        (
            lambda r: r[1]["gap"].update(recommendation="wontfix"),
            "recommendation must be one of",
            1,
        ),
        (lambda r: r.append(dict(r[0])), "duplicate id", 1),
        (lambda r: r.pop(3), "coda.md has no whole-part row", 1),
        (lambda r: (r.pop(1), r.pop(1)), "has no matrix row", 1),
    ]
    for mutate, expected, count in cases:
        rows = _valid_rows()
        mutate(rows)
        errors = rht.validate(rows, headings, dims)
        assert any(expected in e for e in errors), f"{expected!r} not in {errors}"
        assert len(errors) == count, f"{expected!r} produced {errors}"


_ALPHA_URL = f"{rht.HANDBOOK_URL}/alpha.md"


def test_render_produces_tables_gap_list_and_summary():
    rows = _valid_rows()
    out = rht.render(rows)
    assert "generated file" in out.lower()
    # Absolute GitHub URL: the handbook is excluded from the built site, so a
    # relative link would 404 there and fail the site link crawler.
    assert f"[Mapped section]({_ALPHA_URL}#mapped-section)<br>c1" in out
    assert "../engineering/" not in out
    assert "`demo-audit` / Injection" in out
    assert "### new-domain" in out and "#516" in out
    assert "| static | 1 |" in out


def test_render_marks_split_rows_and_links_gap_entries():
    out = rht.render(_valid_rows())
    # Both slices of a split section link to the same anchor, distinguished by
    # the marker; the claim is what tells them apart.
    assert f"[Split section]({_ALPHA_URL}#split-section) (a)<br>c2a" in out
    assert f"[Split section]({_ALPHA_URL}#split-section) (b)<br>c2b" in out
    # A whole-part row (no ## headings) links to the file, with no marker.
    assert f"[Coda]({rht.HANDBOOK_URL}/coda.md)<br>closing words |" in out
    # Every gap entry links back to its handbook section, marker included.
    assert (
        f"- [`alpha/split-section-a`]({_ALPHA_URL}#split-section) (a) (#516) - no lens yet"
        in out
    )


def test_render_reports_full_and_partial_coverage_apart():
    rows = _valid_rows()
    # A row that carries both a check and a residual gap is partial, not mapped.
    rows[0]["gap"] = {"recommendation": "extend-skill", "note": "residue"}
    out = rht.render(rows)
    assert "**0 fully mapped** (0%), **1 partially mapped**" in out
    assert "**1 unmapped**" in out
    assert "2 rows carry a gap entry in total" in out


def test_render_shows_row_notes_in_the_notes_column():
    rows = _valid_rows()
    rows[2]["note"] = "Process | culture:\nnot datable from a snapshot."
    out = rht.render(rows)
    assert "| Section / claim | Class | Mapped checks | Gap | Notes |" in out
    # Pipes escaped and the note folded onto the row's single table line.
    assert (
        "| process | - | - | Process \\| culture: not datable from a snapshot. |" in out
    )
    # A row without a note still renders a placeholder cell.
    assert (
        f"[Coda]({rht.HANDBOOK_URL}/coda.md)<br>closing words | informative | - | - | - |"
        in out
    )


def test_render_joins_multiple_checks_and_a_gap_without_a_target():
    rows = _valid_rows()
    rows[0]["checks"].append({"skill": "demo-audit", "dimension": "Secrets"})
    rows[1]["gap"].pop("target")
    out = rht.render(rows)
    # Two checks share one cell, separated by a break rather than a newline.
    assert "`demo-audit` / Injection<br>`demo-audit` / Secrets" in out
    # A target-less gap renders no empty parentheses, in cell and in bullet.
    assert "**new-domain** - no lens yet" in out
    assert (
        f"- [`alpha/split-section-a`]({_ALPHA_URL}#split-section) (a) - no lens yet"
        in out
    )
    assert "()" not in out


def test_render_keeps_gap_fields_from_breaking_the_table():
    rows = _valid_rows()
    rows[1]["gap"]["target"] = "#516 | #548"
    rows[1]["gap"]["note"] = "two lenses:\nneither owns the bound."
    out = rht.render(rows)
    # In a table cell both the pipe and the newline are fatal; escape and fold.
    assert (
        "**new-domain** - #516 \\| #548 - two lenses: neither owns the bound. |" in out
    )
    # In the gap-list bullet a pipe is harmless, but the newline still is not.
    assert "(#516 | #548) - two lenses: neither owns the bound." in out
    for line in out.splitlines():
        if line.startswith("| ["):
            assert line.endswith(" |"), line


def _patch_paths(monkeypatch, tmp_path, parts):
    monkeypatch.setattr(rht, "PART_ORDER", list(parts))
    monkeypatch.setattr(rht, "PART_TITLES", {p: p.title() for p in parts})
    monkeypatch.setattr(rht, "HANDBOOK_DIR", tmp_path / "handbook")
    monkeypatch.setattr(rht, "SKILLS_DIR", tmp_path / "skills")
    monkeypatch.setattr(rht, "YAML_PATH", tmp_path / "handbook-traceability.yaml")
    monkeypatch.setattr(rht, "MD_PATH", tmp_path / "handbook-traceability.md")
    monkeypatch.setattr(rht, "REPO_ROOT", tmp_path)


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
    headings, dims = _fixture_dirs(tmp_path)
    malformed_rows = [
        "bare string row",
        {
            "id": "alpha/mapped-section",
            "section": "Mapped section",
            "class": "static",
            "checks": "not a list",
        },
        {
            "id": "alpha/split-section-a",
            "section": "Split section",
            "class": "artifact",
            "checks": [
                "not a dict",
                {"skill": "demo-audit", "dimension": "Injection"},
            ],
            "gap": {"recommendation": "new-domain", "target": "#516"},
        },
        {
            "id": "coda/coda",
            "section": "Coda",
            "class": "informative",
            "gap": "not a dict",
        },
    ]
    errors = rht.validate(malformed_rows, headings, dims)
    assert "not a mapping" in str(errors)
    assert "checks must be a list" in str(errors)
    assert "check entries must be mappings" in str(errors)
    assert "gap must be a mapping" in str(errors)
    assert len(errors) == 5


def test_real_matrix_passes_the_strict_check():
    assert rht.main(["--check"]) == 0
