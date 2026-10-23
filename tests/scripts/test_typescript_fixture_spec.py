"""Tests for the TypeScript half of scripts/python_fixture_spec.py (#181).

The TypeScript tables share the module and the renderer with the Python half,
so these mirror what `test_python_fixture_spec.py` holds for Python where the
property carries over, and add what the npm and pnpm partitions need of their
own: a `packageManager` pin per partition and a workspace whose leaf, not its
root, declares the stale pin.
"""

import importlib.util
import json
import re
from pathlib import Path

import pytest
import python_fixture_spec as spec
import yaml
from audit_checks import SKILLS_DIR, load_checks
from python_fixture_spec import (
    EXPECTATIONS,
    FORMS,
    PARTITIONS,
    TS_CONFIGURED_FILES,
    TS_CORE,
    TS_DEFERRED_CHECKS,
    TS_DEPENDENCIES,
    TS_EXPECTATIONS,
    TS_LEAF,
    TS_MANAGER_PINS,
    TS_PARTITIONS,
    TS_ROOT,
    TS_SEED_MARKERS,
    TS_SOURCE_FILES,
    TS_VERIFIED_ON,
    Expectation,
    expectations_for,
    lang_of,
    ts_render_manifests,
    ts_source_tree,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RENDERER = _REPO_ROOT / "scripts" / "render_python_fixture_expectations.py"
_RECORD = _REPO_ROOT / "docs" / "audit" / "typescript-fixture-expectations.md"
_MANAGERS = ("npm", "pnpm", "yarn")


def _load_renderer():
    spec_ = importlib.util.spec_from_file_location(
        "render_python_fixture_expectations", _RENDERER
    )
    module = importlib.util.module_from_spec(spec_)
    spec_.loader.exec_module(module)
    return module


def _checks():
    checks, errors = load_checks(SKILLS_DIR)
    assert not errors, errors
    return checks


def _ts_routes(record):
    return [r for r in record.routes if r.lang == "typescript"]


def _runnable(route) -> bool:
    """A route the stage-4 harness would execute: a command, with an argv, offered."""
    return (
        route.kind == "command"
        and bool(route.argv or route.argv_by_partition)
        and route.disposition != "forbidden"
    )


def _applies_to(route, partition: str) -> bool:
    """Whether a command route can run on this partition at all.

    A route led by a package manager is that manager's subcommand and reads that
    manager's lockfile, so it runs only on that manager's partition; `npm sbom`
    on the pnpm partition has no `package-lock.json` to read. Any other leader -
    `madge`, `vitest`, `npx` - runs the same way on both.
    """
    leader = route.argv[0] if route.argv else ""
    return leader not in _MANAGERS or leader == spec.manager_of(partition)


def _manifests(partition: str) -> dict[str, dict]:
    return {
        path: json.loads(body)
        for path, body in ts_render_manifests(partition).items()
        if path.endswith(".json")
    }


# --- the seeds ---------------------------------------------------------------


def test_every_planted_seed_is_expected_and_every_expected_seed_is_planted():
    """Both seed sources and both directions, as on the Python side."""
    planted = {s for f in TS_SOURCE_FILES + TS_CONFIGURED_FILES for s in f.seeds} | {
        s for d in TS_DEPENDENCIES for s in d.seeds
    }
    expected = {s for e in TS_EXPECTATIONS for s in e.seeds}
    assert planted, "no seed is planted"
    assert planted - expected == set()
    assert expected - planted == set()


def test_every_planted_source_seed_has_a_marker():
    """Every TypeScript source seed is a construct, so every one needs a marker.

    There is no TypeScript counterpart of `ABSENCE_SEEDS`, so the marker mapping
    must name exactly the seeds the source files plant, the configured
    partitions' extra files included.
    """
    planted = {s for f in TS_SOURCE_FILES + TS_CONFIGURED_FILES for s in f.seeds}
    assert set(TS_SEED_MARKERS) == planted


def test_every_marker_appears_in_a_file_carrying_its_seed():
    """The construct, not the seed name, has to survive in the rendered source.

    Checked on every partition that plants the seed: the configured partitions'
    extra files carry seeds the others do not, and every seed is planted in at
    least one partition.
    """
    carried_somewhere = set()
    for partition in TS_PARTITIONS:
        tree = ts_source_tree(partition)
        prefix = spec._ts_source_prefix(partition)
        for seed, markers in TS_SEED_MARKERS.items():
            carriers = [
                tree[f"{prefix}{f.path}"]
                for f in TS_SOURCE_FILES + TS_CONFIGURED_FILES
                if seed in f.seeds and f"{prefix}{f.path}" in tree
            ]
            if not carriers:
                continue
            carried_somewhere.add(seed)
            for marker in markers:
                assert any(marker in body for body in carriers), (seed, marker)
    assert carried_somewhere == set(TS_SEED_MARKERS)


def test_the_order_dependent_pair_is_in_one_file():
    """A shuffle that only reorders files cannot reverse a pair split across two."""
    carriers = [f for f in TS_SOURCE_FILES if "order-dependence" in f.seeds]
    assert len(carriers) == 1
    assert carriers[0].body.count("test(") == 2


def test_the_clamp_test_reaches_neither_guard():
    """The uncovered-branch seed is only real while no test leaves the range."""
    test_file = next(f for f in TS_SOURCE_FILES if f.path == "test/clamp.test.ts")
    calls = re.findall(r"clamp\((-?\d+), (-?\d+), (-?\d+)\)", test_file.body)
    assert calls
    for value, low, high in calls:
        assert int(low) <= int(value) <= int(high)


def test_the_tsconfig_extends_nothing():
    """madge's `--ts-config` route applies only where no base is extended."""
    config = next(f for f in TS_SOURCE_FILES if f.path == "tsconfig.json")
    parsed = json.loads(config.body)
    assert "extends" not in parsed
    assert "paths" not in parsed.get("compilerOptions", {})


def test_the_slow_test_sits_between_the_two_vitest_defaults():
    """Over the slow threshold and under the timeout, and the claim says both."""
    assert (
        spec.VITEST_SLOW_TEST_THRESHOLD_MS
        < spec.TS_SLOW_TEST_MS
        < spec.VITEST_TEST_TIMEOUT_MS
    )
    claim = next(e for e in TS_EXPECTATIONS if e.check == "test/isolation").claim
    for number in (
        spec.TS_SLOW_TEST_MS,
        spec.VITEST_SLOW_TEST_THRESHOLD_MS,
        spec.VITEST_TEST_TIMEOUT_MS,
    ):
        assert f"{number}ms" in claim, number


def test_the_source_tree_lands_under_the_core_member_on_pnpm():
    assert all(not p.startswith(TS_CORE) for p in ts_source_tree("npm"))
    assert all(p.startswith(f"{TS_CORE}/") for p in ts_source_tree("pnpm"))
    assert len(ts_source_tree("npm")) == len(TS_SOURCE_FILES)


def test_no_source_path_collides_with_a_manifest():
    for partition in TS_PARTITIONS:
        assert not set(ts_source_tree(partition)) & set(ts_render_manifests(partition))


# --- the partitions ------------------------------------------------------------


def test_lang_of_names_each_partition_s_language():
    for partition in PARTITIONS:
        assert lang_of(partition) == "python"
    for partition in TS_PARTITIONS:
        assert lang_of(partition) == "typescript"
    assert not set(PARTITIONS) & set(TS_PARTITIONS)


def test_lang_of_rejects_an_unknown_partition_by_name():
    with pytest.raises(ValueError, match="yarn"):
        lang_of("yarn")


def test_expectations_for_dispatches_on_the_language():
    for partition in TS_PARTITIONS:
        carried = expectations_for(partition)
        assert carried
        assert all(e in TS_EXPECTATIONS for e in carried)
    for partition in PARTITIONS:
        assert all(e in EXPECTATIONS for e in expectations_for(partition))


def test_the_python_tuples_stay_python_only():
    """`PARTITIONS` and `EXPECTATIONS` are read by the Python harness as Python's."""
    assert all(lang_of(p) == "python" for e in EXPECTATIONS for p in e.partitions)
    assert all(
        lang_of(p) == "typescript" for e in TS_EXPECTATIONS for p in e.partitions
    )


def test_an_expectation_scoped_across_languages_is_rejected():
    with pytest.raises(ValueError, match="across languages"):
        Expectation("arch/cycles", ("uv", "npm"), "exact", "claim", ())


def test_an_expectation_scoped_to_an_unknown_partition_is_rejected_by_name():
    with pytest.raises(ValueError, match="bun"):
        Expectation("arch/cycles", ("bun",), "exact", "claim", ())


def test_every_ts_expectation_names_a_partition_a_form_and_a_claim():
    for e in TS_EXPECTATIONS:
        assert e.partitions, e.check
        assert set(e.partitions) <= set(TS_PARTITIONS), e.check
        assert e.form in FORMS, e.check
        assert e.claim.strip(), e.check


def test_no_check_states_two_expectations_for_one_partition():
    seen: set[tuple[str, str]] = set()
    for e in TS_EXPECTATIONS:
        for partition in e.partitions:
            assert (e.check, partition) not in seen, (e.check, partition)
            seen.add((e.check, partition))


def test_every_expected_check_is_answered_on_every_partition_it_belongs_to():
    """A check split by partition has to cover each tree of its kind, not one.

    Every check covers the trees carrying no dependency-cruiser config of their
    own, except one whose expectation is scoped to the configured trees, which
    covers exactly those.
    """
    configured = set(spec.TS_CONFIGURED_PARTITIONS)
    unconfigured = set(TS_PARTITIONS) - configured
    for check in {e.check for e in TS_EXPECTATIONS}:
        covered = {p for e in TS_EXPECTATIONS if e.check == check for p in e.partitions}
        assert covered in (unconfigured, configured), check


# --- the checks the round covers -------------------------------------------------


def test_expectations_and_deferrals_partition_the_typescript_route_checks():
    """The loader's set, computed from the records, split in two and never both."""
    checks = _checks()
    ts_checks = {cid for cid, record in checks.items() if _ts_routes(record)}
    expected = {e.check for e in TS_EXPECTATIONS}
    deferred = set(TS_DEFERRED_CHECKS)
    assert not expected & deferred, expected & deferred
    assert expected | deferred == ts_checks


def test_only_checks_with_a_runnable_typescript_command_route_are_expected():
    checks = _checks()
    for check in {e.check for e in TS_EXPECTATIONS}:
        assert any(_runnable(r) for r in _ts_routes(checks[check])), check


def test_every_deferral_carries_a_reason():
    for check, reason in TS_DEFERRED_CHECKS.items():
        assert reason.strip(), check


def test_a_deferred_check_with_a_runnable_route_says_why_it_is_not_run():
    """A deferred runnable check drops out of the round, so its reason must not
    claim the record has no command route when it has one."""
    checks = _checks()
    for check, reason in TS_DEFERRED_CHECKS.items():
        runnable = any(_runnable(r) for r in _ts_routes(checks[check]))
        assert runnable != reason.startswith("no TypeScript command route"), check


def test_the_ungranted_answer_is_stated_exactly_where_the_grant_moves_it():
    """Derived per partition, which is where TypeScript differs from Python.

    The Python derivation reads per language, and that is wrong here: `npm sbom`
    is an untiered TypeScript route, so at the language level `deps/licenses`
    answers in both states, but it reads `package-lock.json` and so does nothing
    on the pnpm partition, where the only command route left is tiered. An entry
    states the ungranted answer where some command route applies to its
    partitions and every one that does needs the grant.
    """
    checks = _checks()
    for e in TS_EXPECTATIONS:
        routes = [r for r in _ts_routes(checks[e.check]) if _runnable(r)]
        for partition in e.partitions:
            applicable = [r for r in routes if _applies_to(r, partition)]
            moves = bool(applicable) and all(r.needs for r in applicable)
            assert bool(e.ungranted) == moves, (e.check, partition, moves)


def test_what_a_result_owes_is_stated_exactly_where_a_route_does_not_stand_alone():
    checks = _checks()
    owing = {
        cid
        for cid, record in checks.items()
        for r in _ts_routes(record)
        if r.tool and r.disposition != "forbidden" and r.alone_insufficient
    }
    for e in TS_EXPECTATIONS:
        assert bool(e.owed) == (e.check in owing), e.check


# --- the pins ----------------------------------------------------------------------


def test_the_vulnerability_floor_names_every_verified_cve():
    lodash = spec._ts_by_name("lodash")
    evidenced = set(re.findall(r"CVE-\d{4}-\d+", lodash.evidence))
    assert evidenced
    expectation = next(e for e in TS_EXPECTATIONS if e.check == "deps/vulnerabilities")
    assert expectation.form == "floor"
    assert evidenced <= set(re.findall(r"CVE-\d{4}-\d+", expectation.claim))
    assert f"at least {len(evidenced)} distinct CVEs" in expectation.claim


def test_the_freshness_claims_name_every_outdated_pin_and_every_control():
    outdated = [d for d in TS_DEPENDENCIES if d.pin != d.latest]
    current = [d for d in TS_DEPENDENCIES if d.pin == d.latest]
    assert outdated and current
    assert "is-odd" in {d.name for d in current}
    assert [d.name for d in spec._TS_CONTROLS] == ["is-odd"]
    for e in (e for e in TS_EXPECTATIONS if e.check == "deps/freshness"):
        for d in outdated + current:
            assert f"{d.name} {d.pin}" in e.claim, (e.partitions, d.name)


def test_the_pnpm_freshness_claim_names_what_a_root_only_run_reaches():
    e = next(
        e
        for e in TS_EXPECTATIONS
        if e.check == "deps/freshness" and e.partitions == ("pnpm",)
    )
    root_outdated = [
        d for d in TS_DEPENDENCIES if d.pin != d.latest and d.member == TS_ROOT
    ]
    leaf_stale = [d for d in TS_DEPENDENCIES if "leaf-only" in d.seeds]
    assert root_outdated and leaf_stale
    reach = e.claim.split("run bare from the root it can report", 1)[1]
    reached = reach.split("nothing declared in", 1)[0]
    for d in root_outdated:
        assert f"{d.name} {d.pin}" in reached, d.name
    for d in leaf_stale:
        assert f"{d.name} {d.pin}" not in reached, d.name
    assert "leaf-only" in e.seeds
    assert all(d.member == TS_LEAF for d in leaf_stale)
    assert "pnpm outdated -r" in e.claim


def test_every_pin_is_exact_and_every_member_is_known():
    for d in TS_DEPENDENCIES:
        assert re.fullmatch(r"\d+\.\d+\.\d+", d.pin), d.name
        assert re.fullmatch(r"\d+\.\d+\.\d+", d.latest), d.name
        assert d.evidence.strip(), d.name


def test_an_unknown_member_is_rejected_by_name():
    with pytest.raises(ValueError, match="libs/x"):
        spec.TsDependency("x", "1.0.0", "1.0.0", False, "libs/x", (), "e")


# --- the manifests -------------------------------------------------------------------


def test_every_json_manifest_parses_and_the_workspace_file_parses_as_yaml():
    parsed = 0
    for partition in TS_PARTITIONS:
        for path, body in ts_render_manifests(partition).items():
            if path.endswith(".json"):
                json.loads(body)
            else:
                assert path.endswith(".yaml"), path
                yaml.safe_load(body)
            parsed += 1
    # npm and npm-layered render one manifest each, pnpm its root, workspace
    # file and two members.
    assert parsed == 6, parsed


def test_the_root_manifest_carries_the_partition_s_manager_pin():
    assert TS_MANAGER_PINS == {"npm": spec.NPM_PIN, "pnpm": spec.PNPM_PIN}
    assert spec.NPM_PIN == "npm@11.19.0"
    assert spec.PNPM_PIN == "pnpm@9.15.9"
    for partition in TS_PARTITIONS:
        manifests = _manifests(partition)
        assert (
            manifests["package.json"]["packageManager"]
            == TS_MANAGER_PINS[spec.manager_of(partition)]
        )
        for path, document in manifests.items():
            if path != "package.json":
                assert "packageManager" not in document, (partition, path)


def test_the_npm_partition_declares_every_pin_in_its_one_manifest():
    manifests = _manifests("npm")
    assert list(manifests) == ["package.json"]
    document = manifests["package.json"]
    for d in TS_DEPENDENCIES:
        table = "devDependencies" if d.dev else "dependencies"
        assert document[table][d.name] == d.pin, d.name


def test_each_pnpm_member_declares_exactly_its_own_pins():
    """Each dependency lands in its member's manifest and in no other."""
    paths = {
        TS_ROOT: "package.json",
        TS_CORE: f"{TS_CORE}/package.json",
        TS_LEAF: f"{TS_LEAF}/package.json",
    }
    manifests = _manifests("pnpm")
    for d in TS_DEPENDENCIES:
        table = "devDependencies" if d.dev else "dependencies"
        for member, path in paths.items():
            declared = manifests[path].get(table, {}).get(d.name)
            if member == d.member:
                assert declared == d.pin, (d.name, path)
            else:
                assert declared is None, (d.name, path)


def test_the_pnpm_leaf_holds_the_leaf_only_pin_and_the_root_does_not():
    manifests = _manifests("pnpm")
    commander = spec._ts_by_name("commander")
    leaf = manifests[f"{TS_LEAF}/package.json"]
    root = manifests["package.json"]
    assert leaf["dependencies"]["commander"] == commander.pin
    for table in ("dependencies", "devDependencies"):
        assert "commander" not in root.get(table, {})


def test_the_pnpm_workspace_covers_both_members_and_links_the_core():
    workspace = yaml.safe_load(ts_render_manifests("pnpm")["pnpm-workspace.yaml"])
    globs = workspace["packages"]
    for member in (TS_CORE, TS_LEAF):
        parent = member.split("/")[0]
        assert f"{parent}/*" in globs, member
    leaf = _manifests("pnpm")[f"{TS_LEAF}/package.json"]
    core = _manifests("pnpm")[f"{TS_CORE}/package.json"]
    assert leaf["dependencies"][core["name"]] == "workspace:*"


def test_ts_render_manifests_rejects_a_python_partition():
    with pytest.raises(ValueError, match="uv"):
        ts_render_manifests("uv")


# --- the rendered record -----------------------------------------------------------

_TS_EXPECTATION_HEADER = "| Check | Partitions | Form | Seeds | Expected |"
_TS_UNGRANTED_HEADER = "| Check | Partitions | Without the grant |"
_TS_OWED_HEADER = "| Check | Partitions | Still owed |"
_TS_DEPENDENCY_HEADER = "| Package | Pin | Latest | Dev | Member | Seeds | Evidence |"
_TS_PARTITION_HEADER = "| Partition | Manager pin | Expectations | Checks |"
_TS_DEFERRED_HEADER = "| Check | Why no expectation |"


def _table_rows(text: str, header: str) -> list[str]:
    lines = text.splitlines()
    start = lines.index(header) + 2
    rows = []
    for line in lines[start:]:
        if not line.startswith("|"):
            break
        rows.append(line)
    return rows


def _cells(row: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", row.strip().strip("|"))]


def test_every_table_has_one_row_per_entry_and_the_declared_column_count():
    renderer = _load_renderer()
    text = renderer.render_typescript()
    counts = {
        _TS_EXPECTATION_HEADER: len(TS_EXPECTATIONS),
        _TS_UNGRANTED_HEADER: len([e for e in TS_EXPECTATIONS if e.ungranted]),
        _TS_OWED_HEADER: len([e for e in TS_EXPECTATIONS if e.owed]),
        _TS_DEPENDENCY_HEADER: len(TS_DEPENDENCIES),
        _TS_PARTITION_HEADER: len(TS_PARTITIONS),
        _TS_DEFERRED_HEADER: len(TS_DEFERRED_CHECKS),
    }
    for header, count in counts.items():
        rows = _table_rows(text, header)
        assert len(rows) == count, header
        for row in rows:
            assert row.replace("\\|", "").count("|") == header.count("|"), row


def test_every_expectation_row_pairs_its_check_with_its_own_answer():
    renderer = _load_renderer()
    rows = [
        _cells(r)
        for r in _table_rows(renderer.render_typescript(), _TS_EXPECTATION_HEADER)
    ]
    for e in TS_EXPECTATIONS:
        scope = renderer._ts_scope_cell(e)
        matching = [r for r in rows if r[0] == f"`{e.check}`" and r[1] == scope]
        assert len(matching) == 1, (e.check, scope)
        _, _, form, seeds, claim = matching[0]
        assert form == e.form
        assert seeds == renderer._seeds_cell(e)
        assert claim == renderer._cell(e.claim)


def test_every_partition_row_states_its_pin_and_count():
    renderer = _load_renderer()
    rows = [
        _cells(r)
        for r in _table_rows(renderer.render_typescript(), _TS_PARTITION_HEADER)
    ]
    for partition in TS_PARTITIONS:
        matching = [r for r in rows if r[0] == f"`{partition}`"]
        assert len(matching) == 1, partition
        _, pin, count, checks = matching[0]
        assert pin == f"`{TS_MANAGER_PINS[spec.manager_of(partition)]}`"
        assert count == str(len(expectations_for(partition)))
        assert checks == renderer._ts_partition_checks_cell(partition)


def test_the_rendered_record_dates_the_evidence_and_uses_no_em_dash():
    text = _load_renderer().render_typescript()
    assert TS_VERIFIED_ON in text
    assert "—" not in text
    assert text.endswith("\n") and not text.endswith("\n\n")


def test_the_committed_record_matches_the_module():
    assert _RECORD.read_text() == _load_renderer().render_typescript()


def test_check_fails_when_only_the_typescript_record_has_drifted(
    tmp_path, monkeypatch, capsys
):
    """`--check` has to see the second record, not only the first."""
    renderer = _load_renderer()
    stale = tmp_path / "typescript-fixture-expectations.md"
    stale.write_text(renderer.render_typescript() + "drift\n")
    monkeypatch.setattr(renderer, "TS_OUT_PATH", stale)
    assert renderer.main(["--check"]) == 1
    err = capsys.readouterr().err
    assert "drift" in err
    assert "typescript-fixture-expectations.md" in err


def test_check_treats_a_missing_typescript_record_as_drift(tmp_path, monkeypatch):
    renderer = _load_renderer()
    monkeypatch.setattr(renderer, "TS_OUT_PATH", tmp_path / "absent.md")
    assert renderer.main(["--check"]) == 1


def test_rendering_writes_both_records(tmp_path, monkeypatch, capsys):
    renderer = _load_renderer()
    python_out = tmp_path / "python.md"
    ts_out = tmp_path / "typescript.md"
    monkeypatch.setattr(renderer, "OUT_PATH", python_out)
    monkeypatch.setattr(renderer, "TS_OUT_PATH", ts_out)
    assert renderer.main([]) == 0
    assert python_out.read_text() == renderer.render()
    assert ts_out.read_text() == renderer.render_typescript()
    assert capsys.readouterr().out.count("wrote") == 2
