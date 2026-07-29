"""Tests for scripts/render_handbook_traceability.py (#543)."""

import importlib.util
import sys
from pathlib import Path

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
    cases = [
        (
            lambda r: r[0].update(id="alpha/mapped-section", section="Wrong text"),
            "does not match heading",
        ),
        (lambda r: r[0].update(id="nowhere/mapped-section"), "unknown handbook part"),
        (lambda r: r[0].update(id="alpha/no-such-anchor"), "does not resolve"),
        (lambda r: r[0].update(**{"class": "bogus"}), "class must be one of"),
        (lambda r: r[0].pop("checks"), "needs checks or a gap"),
        (
            lambda r: r[3].update(
                checks=[{"skill": "demo-audit", "dimension": "Injection"}]
            ),
            "must not carry checks",
        ),
        (lambda r: r[0]["checks"][0].update(skill="ghost-audit"), "unknown skill"),
        (
            lambda r: r[0]["checks"][0].update(dimension="Ghost dimension"),
            "no dimension",
        ),
        (
            lambda r: r[1]["gap"].update(recommendation="wontfix"),
            "recommendation must be one of",
        ),
        (lambda r: r.append(dict(r[0])), "duplicate id"),
        (lambda r: r.pop(3), "coda.md has no whole-part row"),
        (lambda r: (r.pop(1), r.pop(1)), "has no matrix row"),
    ]
    for mutate, expected in cases:
        rows = _valid_rows()
        mutate(rows)
        errors = rht.validate(rows, headings, dims)
        assert any(expected in e for e in errors), f"{expected!r} not in {errors}"


def test_render_produces_tables_gap_list_and_summary():
    rows = _valid_rows()
    out = rht.render(rows)
    assert "generated file" in out.lower()
    assert "[Mapped section](../engineering/alpha.md#mapped-section)" in out
    assert "`demo-audit` / Injection" in out
    assert "### new-domain" in out and "#516" in out
    assert "| static | 1 |" in out


def test_main_check_detects_a_stale_md(tmp_path, monkeypatch):
    headings_dir = tmp_path / "handbook"
    _fixture_dirs(tmp_path)
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


def test_allow_pending_parts_tolerates_unwalked_parts_only(tmp_path, monkeypatch):
    import yaml as _yaml

    _fixture_dirs(tmp_path)
    _write(tmp_path / "handbook" / "beta.md", "# Beta\n\n## Unwalked section\n\ntext\n")
    yaml_path = tmp_path / "handbook-traceability.yaml"
    md_path = tmp_path / "handbook-traceability.md"
    yaml_path.write_text(
        _yaml.safe_dump(_valid_rows(), sort_keys=False, allow_unicode=True)
    )
    monkeypatch.setattr(rht, "HANDBOOK_DIR", tmp_path / "handbook")
    monkeypatch.setattr(rht, "SKILLS_DIR", tmp_path / "skills")
    monkeypatch.setattr(rht, "YAML_PATH", yaml_path)
    monkeypatch.setattr(rht, "MD_PATH", md_path)
    monkeypatch.setattr(rht, "REPO_ROOT", tmp_path)
    assert rht.main([]) == 1  # beta.md uncovered -> strict fails
    assert rht.main(["--allow-pending-parts"]) == 0
    assert md_path.exists()
    rows = _valid_rows()
    del rows[
        0
    ]  # alpha stays walked but now misses a section -> fails even with the flag
    yaml_path.write_text(_yaml.safe_dump(rows, sort_keys=False, allow_unicode=True))
    assert rht.main(["--allow-pending-parts"]) == 1


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


def test_real_matrix_has_no_errors_beyond_pending_parts():
    """Staleness + schema gate on the real repo files.

    Until the content walk completes (plan Tasks 4-6), parts not yet walked
    produce 'coverage hole' errors; anything else is a real defect. Task 6
    replaces this test with the strict main(["--check"]) == 0 form.
    """
    import yaml as _yaml

    rows = _yaml.safe_load(rht.YAML_PATH.read_text())
    errors = rht.validate(
        rows,
        rht.handbook_headings(rht.HANDBOOK_DIR),
        rht.skill_dimensions(rht.SKILLS_DIR),
    )
    real = [e for e in errors if "coverage hole" not in e]
    assert real == []
    assert rht.MD_PATH.read_text() == rht.render(rows)
