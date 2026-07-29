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
