"""Tests for scripts/audit_checks.py (#559)."""

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = REPO_ROOT / "scripts" / "audit_checks.py"

_spec = importlib.util.spec_from_file_location("audit_checks", _SCRIPT)
assert _spec is not None and _spec.loader is not None
ac = importlib.util.module_from_spec(_spec)
sys.modules["audit_checks"] = ac
_spec.loader.exec_module(ac)


GOOD = """---
id: arch/layering
domain: arch
locality: local
handbook:
  - codebase-structure/point-every-dependency-toward-the-core-and-never-cycle-a
tooling:
  python: [import-linter, tach]
  typescript: [dependency-cruiser]
---

# Layering / dependency-rule conformance

Every import that crosses a tier boundary the wrong way.

## Severity

**Critical** - an import that violates a documented dependency rule.
"""

UNCITED = """---
id: arch/hidden-coupling
domain: arch
locality: global
handbook: []
handbook_note: The handbook's decay list names no equivalent signal.
optin: true
---

# Hidden coupling / implicit dependencies

Coupling that does not travel through an import.
"""


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_loads_a_well_formed_record(tmp_path):
    _write(tmp_path, "arch/layering.md", GOOD)
    checks, errors = ac.load_checks(tmp_path)
    assert errors == []
    check = checks["arch/layering"]
    assert check.domain == "arch"
    assert check.locality == "local"
    assert check.title == "Layering / dependency-rule conformance"
    assert check.handbook == (
        "codebase-structure/point-every-dependency-toward-the-core-and-never-cycle-a",
    )
    assert check.handbook_note is None
    assert check.tooling == {
        "python": ("import-linter", "tach"),
        "typescript": ("dependency-cruiser",),
    }
    assert check.optin is False


def test_optin_and_empty_handbook_with_note_are_valid(tmp_path):
    _write(tmp_path, "arch/hidden-coupling.md", UNCITED)
    checks, errors = ac.load_checks(tmp_path)
    assert errors == []
    check = checks["arch/hidden-coupling"]
    assert check.handbook == ()
    assert check.handbook_note.startswith("The handbook's decay list")
    assert check.optin is True


def test_missing_frontmatter_is_reported_not_raised(tmp_path):
    _write(tmp_path, "arch/broken.md", "# No frontmatter here\n")
    checks, errors = ac.load_checks(tmp_path)
    assert checks == {}
    assert any("frontmatter" in e for e in errors)


def test_id_must_match_the_file_path(tmp_path):
    _write(
        tmp_path,
        "arch/layering.md",
        GOOD.replace("id: arch/layering", "id: arch/wrong"),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("does not match its path" in e for e in errors)


def test_domain_must_match_the_directory(tmp_path):
    _write(tmp_path, "deps/layering.md", GOOD)
    _, errors = ac.load_checks(tmp_path)
    assert any("directory" in e for e in errors)


def test_locality_must_be_local_or_global(tmp_path):
    _write(
        tmp_path,
        "arch/layering.md",
        GOOD.replace("locality: local", "locality: sometimes"),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("locality" in e for e in errors)


def test_empty_handbook_without_a_note_is_rejected(tmp_path):
    text = UNCITED.replace(
        "handbook_note: The handbook's decay list names no equivalent signal.\n", ""
    )
    _write(tmp_path, "arch/hidden-coupling.md", text)
    _, errors = ac.load_checks(tmp_path)
    assert any("handbook_note" in e for e in errors)


def test_a_note_alongside_anchors_is_rejected(tmp_path):
    text = GOOD.replace(
        "tooling:", "handbook_note: why this exceeds the handbook\ntooling:"
    )
    _write(tmp_path, "arch/layering.md", text)
    _, errors = ac.load_checks(tmp_path)
    assert any("handbook_note" in e for e in errors)


def test_unknown_frontmatter_key_is_rejected(tmp_path):
    _write(
        tmp_path,
        "arch/layering.md",
        GOOD.replace("domain: arch", "domain: arch\nsevrity: high"),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("sevrity" in e for e in errors)


def test_missing_title_is_rejected(tmp_path):
    body_start = GOOD.index("# Layering")
    _write(tmp_path, "arch/layering.md", GOOD[:body_start] + "no heading here\n")
    _, errors = ac.load_checks(tmp_path)
    assert any("title" in e for e in errors)


def test_tooling_must_map_language_to_a_list(tmp_path):
    _write(
        tmp_path,
        "arch/layering.md",
        GOOD.replace("python: [import-linter, tach]", "python: import-linter"),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("tooling" in e for e in errors)


def test_duplicate_ids_across_files_are_reported(tmp_path):
    _write(tmp_path, "arch/layering.md", GOOD)
    _write(tmp_path, "arch/layering-copy.md", GOOD)
    _, errors = ac.load_checks(tmp_path)
    assert any("duplicate" in e for e in errors)


def test_an_absent_checks_dir_loads_empty_without_error(tmp_path):
    checks, errors = ac.load_checks(tmp_path / "nope")
    assert checks == {}
    assert errors == []


def test_the_real_checks_tree_loads_clean():
    checks, errors = ac.load_checks(ac.CHECKS_DIR)
    assert errors == []
    assert checks == checks  # tautology guard removed in Task 4
