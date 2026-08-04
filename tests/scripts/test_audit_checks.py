"""Tests for scripts/audit_checks.py (#559)."""

import importlib.util
import re
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
    _write(tmp_path, "arch-audit/checks/layering.md", GOOD)
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
    _write(tmp_path, "arch-audit/checks/hidden-coupling.md", UNCITED)
    checks, errors = ac.load_checks(tmp_path)
    assert errors == []
    check = checks["arch/hidden-coupling"]
    assert check.handbook == ()
    assert check.handbook_note.startswith("The handbook's decay list")
    assert check.optin is True


def test_missing_frontmatter_is_reported_not_raised(tmp_path):
    _write(tmp_path, "arch-audit/checks/broken.md", "# No frontmatter here\n")
    checks, errors = ac.load_checks(tmp_path)
    assert checks == {}
    assert any("frontmatter" in e for e in errors)


def test_id_must_match_the_file_path(tmp_path):
    _write(
        tmp_path,
        "arch-audit/checks/layering.md",
        GOOD.replace("id: arch/layering", "id: arch/wrong"),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("does not match its path" in e for e in errors)


def test_domain_must_match_the_owning_skill(tmp_path):
    _write(tmp_path, "deps-audit/checks/layering.md", GOOD)
    _, errors = ac.load_checks(tmp_path)
    assert any("does not match its owning skill 'deps-audit'" in e for e in errors)


def test_a_checks_dir_outside_a_domain_skill_is_ignored(tmp_path):
    _write(tmp_path, "some-helper/checks/layering.md", GOOD)
    checks, errors = ac.load_checks(tmp_path)
    assert (checks, errors) == ({}, [])


def test_locality_must_be_local_or_global(tmp_path):
    _write(
        tmp_path,
        "arch-audit/checks/layering.md",
        GOOD.replace("locality: local", "locality: sometimes"),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("locality" in e for e in errors)


def test_empty_handbook_without_a_note_is_rejected(tmp_path):
    text = UNCITED.replace(
        "handbook_note: The handbook's decay list names no equivalent signal.\n", ""
    )
    _write(tmp_path, "arch-audit/checks/hidden-coupling.md", text)
    _, errors = ac.load_checks(tmp_path)
    assert any("handbook_note" in e for e in errors)


def test_a_note_alongside_anchors_is_rejected(tmp_path):
    text = GOOD.replace(
        "tooling:", "handbook_note: why this exceeds the handbook\ntooling:"
    )
    _write(tmp_path, "arch-audit/checks/layering.md", text)
    _, errors = ac.load_checks(tmp_path)
    assert any("handbook_note" in e for e in errors)


def test_unknown_frontmatter_key_is_rejected(tmp_path):
    _write(
        tmp_path,
        "arch-audit/checks/layering.md",
        GOOD.replace("domain: arch", "domain: arch\nsevrity: high"),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("sevrity" in e for e in errors)


def test_missing_title_is_rejected(tmp_path):
    body_start = GOOD.index("# Layering")
    _write(
        tmp_path,
        "arch-audit/checks/layering.md",
        GOOD[:body_start] + "no heading here\n",
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("title" in e for e in errors)


def test_tooling_must_map_language_to_a_list(tmp_path):
    _write(
        tmp_path,
        "arch-audit/checks/layering.md",
        GOOD.replace("python: [import-linter, tach]", "python: import-linter"),
    )
    _, errors = ac.load_checks(tmp_path)
    assert any("tooling" in e for e in errors)


def test_duplicate_ids_across_files_are_reported(tmp_path):
    _write(tmp_path, "arch-audit/checks/layering.md", GOOD)
    _write(tmp_path, "arch-audit/checks/layering-copy.md", GOOD)
    _, errors = ac.load_checks(tmp_path)
    assert any("duplicate" in e for e in errors)


def test_an_absent_checks_dir_loads_empty_without_error(tmp_path):
    checks, errors = ac.load_checks(tmp_path / "nope")
    assert checks == {}
    assert errors == []


def test_a_record_at_the_wrong_depth_is_reported_not_skipped(tmp_path):
    _write(tmp_path, "arch-audit/checks/nested/deep.md", GOOD)
    checks, errors = ac.load_checks(tmp_path)
    assert checks == {}
    assert [e.split(":")[0] for e in errors] == ["arch-audit/checks/nested/deep.md"]
    assert all("would never be loaded" in e for e in errors)


def test_an_unreadable_record_is_reported_not_raised(tmp_path):
    root = tmp_path / "arch-audit" / "checks"
    root.mkdir(parents=True)
    (root / "binary.md").write_bytes(b"---\nid: arch/binary\n---\n\xff\xfe")
    (root / "adir.md").mkdir()
    checks, errors = ac.load_checks(tmp_path)
    assert checks == {}
    assert any(e == "arch-audit/checks/binary.md: not valid UTF-8" for e in errors)
    assert any(
        e.startswith("arch-audit/checks/adir.md: cannot be read:") for e in errors
    )


def test_frontmatter_with_an_empty_body_is_not_reported_as_missing(tmp_path):
    _write(
        tmp_path,
        "arch-audit/checks/layering.md",
        "---\nid: arch/layering\ndomain: arch\n---",
    )
    _, errors = ac.load_checks(tmp_path)
    assert not any("missing YAML frontmatter" in e for e in errors)
    assert any("title" in e for e in errors)


def test_every_audit_skill_has_a_non_empty_checks_directory():
    """Regression net for #559 PR 2: the `/audit` front door now detects
    which domains are available from `<domain>-audit/checks/` instead of a
    fixed list, so a domain skill with an empty or missing `checks/` would
    silently drop out of `/audit all`. If this fails, go find which
    `*-audit` skill lost its checks - do not weaken the assertion.
    """
    skill_dirs = sorted(
        p for p in ac.SKILLS_DIR.glob(f"*{ac.SKILL_SUFFIX}") if p.is_dir()
    )
    assert skill_dirs, "no *-audit skills found under the real skills directory"
    empty = [p.name for p in skill_dirs if not any((p / ac.CHECKS_SUBDIR).glob("*.md"))]
    assert empty == [], f"these *-audit skills have no checks records: {empty}"


def test_the_real_checks_tree_covers_every_domain():
    """Structural complement to `test_the_real_checks_tree_loads_clean`'s
    exact id list: this asserts the *shape* the front door now depends on -
    zero load errors and full domain coverage - so it stays meaningful as
    individual check ids are added, renamed, or removed.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    domains = {check.domain for check in checks.values()}
    assert domains == {
        "arch",
        "ci",
        "deps",
        "docs",
        "eval",
        "prompt",
        "security",
        "test",
    }


def test_the_real_checks_tree_loads_clean():
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    assert sorted(checks) == [
        "arch/complexity",
        "arch/complexity-gate",
        "arch/coupling",
        "arch/cycles",
        "arch/dead-code",
        "arch/hidden-coupling",
        "arch/layering",
        "arch/martin-metrics",
        "arch/over-abstraction",
        "arch/over-decomposition",
        "arch/size",
        "ci/action-supply-chain",
        "ci/branch-protection",
        "ci/deploy-safety",
        "ci/efficiency",
        "ci/gate-enforcement",
        "ci/permissions-secrets",
        "ci/self-hosted-runners",
        "ci/trigger-safety",
        "ci/workflow-correctness",
        "deps/freshness",
        "deps/hygiene",
        "deps/inventory",
        "deps/licenses",
        "deps/transitive-licenses",
        "deps/vulnerabilities",
        "docs/coverage",
        "docs/cross-referencing",
        "docs/docstring-coverage",
        "docs/docstring-staleness",
        "docs/docstring-standard",
        "docs/organization",
        "eval/adversarial",
        "eval/contamination",
        "eval/cost-latency",
        "eval/coverage",
        "eval/judge-calibration",
        "eval/methodology",
        "eval/prompt-quality",
        "eval/regression-tracking",
        "eval/reproducibility",
        "eval/smoke-test-gate",
        "prompt/cognitive-load",
        "prompt/cross-prompt-consistency",
        "prompt/examples-delimiters",
        "prompt/grounding",
        "prompt/instruction-precision",
        "prompt/internal-consistency",
        "prompt/output-contract",
        "prompt/positive-framing",
        "prompt/role-objective",
        "prompt/sop-naming",
        "prompt/sop-rfc2119",
        "prompt/sop-structure",
        "security/crypto",
        "security/dangerous-calls",
        "security/injection",
        "security/secret-history",
        "security/secrets-in-code",
        "security/sensitive-data",
        "security/unsafe-io",
        "test/assertion-strength",
        "test/coverage-reach",
        "test/determinism",
        "test/isolation",
        "test/mutation",
        "test/new-code-coverage",
        "test/property-based-gap",
    ]
    assert {c.locality for c in checks.values()} == {"local", "global"}
    assert [c.id for c in checks.values() if c.optin] == [
        "arch/martin-metrics",
        "ci/branch-protection",
        "ci/self-hosted-runners",
        "deps/inventory",
        "deps/transitive-licenses",
        "docs/docstring-coverage",
        "docs/docstring-staleness",
        "docs/docstring-standard",
        "eval/adversarial",
        "eval/cost-latency",
        "eval/judge-calibration",
        "prompt/cross-prompt-consistency",
        "security/secret-history",
        "test/mutation",
        "test/property-based-gap",
    ]


def test_every_tool_less_check_states_a_reading_procedure():
    """#567 item 5: a record may omit `tooling:` when its detection is
    reading rather than running something - but it must then say so under
    `## Tooling fallback`, or the executing agent has nothing to run and
    nothing told to read. If this fails, add the section to the named
    record - do not weaken the assertion.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    missing = sorted(
        check_id
        for check_id, check in checks.items()
        if not check.tooling and "\n## Tooling fallback" not in check.path.read_text()
    )
    assert missing == [], (
        f"these checks declare no tooling and state no fallback: {missing}"
    )


def test_every_review_lens_paragraph_carries_a_label():
    """#567 item 4: a `## Review lens` paragraph opens with a bold label
    naming what it judges, so a whole-branch reviewer assembling lenses
    from several records can tell them apart. If this fails, label the
    paragraph - do not weaken the assertion.
    """
    checks, errors = ac.load_checks(ac.SKILLS_DIR)
    assert errors == []
    unlabeled = []
    for check_id, check in sorted(checks.items()):
        section = re.search(
            r"^## Review lens\n(.*?)(?=\n## |\Z)",
            check.path.read_text(),
            re.S | re.M,
        )
        if section is None:
            continue
        for para in section.group(1).strip().split("\n\n"):
            if para.strip() and not para.strip().startswith("**"):
                unlabeled.append(f"{check_id}: {para.strip()[:60]}")
    assert unlabeled == [], f"unlabeled review-lens paragraphs: {unlabeled}"
