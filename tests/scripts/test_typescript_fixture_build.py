"""The generator's TypeScript half, offline (#181).

What is tested here is decided before a package manager runs: what each
TypeScript partition's tree contains, which command locks it and under what
environment, which manager version a build refuses, and what the finished
commit holds. `build` itself is exercised with the version probe and the lock
step stubbed, so the git half runs for real and the network half does not: the
lockfiles a real npm and a corepack-provided pnpm produce are covered by the
recorded build smoke instead, where a stub would assert itself.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import build_python_fixtures
import pytest
from build_python_fixtures import (
    FIXTURE_README,
    LOCK_ARTIFACTS,
    PUBLIC_NPM_REGISTRY,
    _fixture_env,
    _git,
    build,
    check_manager_version,
    committed_files,
    declaring_manifest,
    discard_after_lock,
    fixture_readme,
    lock_command,
    lock_env,
    main,
    manager_version_command,
    measure_manager_version,
    plan_tree,
    prelock_commands,
    ts_declaring_manifests,
    ts_fixture_env,
)
from python_fixture_spec import (
    PARTITIONS,
    TS_MANAGER_PINS,
    TS_PARTITIONS,
    ts_render_manifests,
    ts_source_tree,
)

# Written out rather than derived from the spec, so the assertion does not hold
# whatever the renderers return: the seeded package's prefix and the workspace
# layout are the properties a lens route's cwd depends on.
SEEDED = (
    "tsconfig.json",
    "src/clamp.ts",
    "src/domain/model.ts",
    "src/infra/store.ts",
    "test/clamp.test.ts",
    "test/order.test.ts",
    "test/slow.test.ts",
)
COMMITTED = {
    "npm": tuple(
        sorted({"package.json", "package-lock.json", FIXTURE_README, *SEEDED})
    ),
    "pnpm": tuple(
        sorted(
            {
                "package.json",
                "pnpm-workspace.yaml",
                "pnpm-lock.yaml",
                "packages/core/package.json",
                "apps/api/package.json",
                FIXTURE_README,
                *(f"packages/core/{p}" for p in SEEDED),
            }
        )
    ),
}
LOCK = {
    "npm": (
        "npm",
        "install",
        "--package-lock-only",
        "--ignore-scripts",
        "--no-audit",
        "--no-fund",
    ),
    "pnpm": ("corepack", "pnpm", "install", "--lockfile-only", "--ignore-scripts"),
}
ARTIFACT = {"npm": ("package-lock.json",), "pnpm": ("pnpm-lock.yaml",)}
PINNED = {"npm": "11.19.0", "pnpm": "9.15.9"}


def _row(readme: str, label: str) -> str:
    rows = [line for line in readme.splitlines() if line.startswith(f"| {label} |")]
    assert len(rows) == 1, f"expected one {label!r} row, found {rows}"
    return rows[0]


def _pinned_probe(calls: list | None = None):
    """A probe that answers with the partition's pin, recording what it saw."""

    def probe(command, cwd, env):
        manifest = json.loads((Path(cwd) / "package.json").read_text())
        if calls is not None:
            calls.append((tuple(command), manifest, dict(env)))
        return manifest["packageManager"].split("@", 1)[1] + "\n"

    return probe


def _stub_lock(monkeypatch):
    """Replace the lock step with one that writes the partition's artifact."""

    def fake(partition):
        (name,) = LOCK_ARTIFACTS[partition]
        return (sys.executable, "-c", f"open({name!r}, 'w').write('lock\\n')")

    monkeypatch.setattr(build_python_fixtures, "lock_command", fake)


def test_each_partition_plans_its_manifests_and_the_prefixed_source():
    assert set(plan_tree("npm")) == {"package.json", *SEEDED}
    assert set(plan_tree("pnpm")) == {
        "package.json",
        "pnpm-workspace.yaml",
        "packages/core/package.json",
        "apps/api/package.json",
        *(f"packages/core/{p}" for p in SEEDED),
    }


def test_the_planned_tree_is_the_spec_rendering_and_nothing_else():
    for partition in TS_PARTITIONS:
        expected = ts_render_manifests(partition) | ts_source_tree(partition)
        assert plan_tree(partition) == expected, partition


def test_each_partition_commits_its_plan_its_lockfile_and_the_readme():
    for partition in TS_PARTITIONS:
        assert committed_files(partition) == COMMITTED[partition], partition
        assert LOCK_ARTIFACTS[partition] == ARTIFACT[partition], partition


def test_each_partition_locks_without_installing_and_without_scripts():
    for partition in TS_PARTITIONS:
        assert lock_command(partition) == LOCK[partition], partition
        assert prelock_commands(partition) == (), partition
        assert discard_after_lock(partition) == (), partition


def test_pnpm_is_provisioned_through_corepack_rather_than_taken_from_path():
    assert lock_command("pnpm")[:2] == ("corepack", "pnpm")
    assert manager_version_command("pnpm") == ("corepack", "pnpm", "--version")
    assert manager_version_command("npm") == ("npm", "--version")


def test_the_lock_environment_drops_every_registry_override():
    base = {
        "PATH": "/usr/bin",
        "npm_config_registry": "https://mirror.example.test/",
        "NPM_CONFIG_REGISTRY": "https://mirror.example.test/",
        "npm_config_@fixture:registry": "https://scoped.example.test/",
        "npm_config_cache": "/cache",
        "VIRTUAL_ENV": "/elsewhere/.venv",
    }
    for partition in TS_PARTITIONS:
        env = lock_env(partition, base)
        registry_keys = sorted(
            k for k in env if k.lower().startswith("npm_config_") and "registry" in k
        )
        assert registry_keys == ["npm_config_registry"], partition
        assert env["npm_config_registry"] == PUBLIC_NPM_REGISTRY, partition
        assert env["COREPACK_ENABLE_DOWNLOAD_PROMPT"] == "0", partition
        assert env["COREPACK_ENABLE_AUTO_PIN"] == "0", partition
        # What is not a registry setting passes through, and the Python-side
        # removals still apply: the generator runs under `uv run` either way.
        assert env["PATH"] == "/usr/bin", partition
        assert env["npm_config_cache"] == "/cache", partition
        assert "VIRTUAL_ENV" not in env, partition
    # The input is not mutated, so one base can serve every partition.
    assert base["NPM_CONFIG_REGISTRY"] == "https://mirror.example.test/"


def test_a_python_partition_keeps_the_environment_it_had():
    base = {"PATH": "/usr/bin", "npm_config_registry": "https://mirror.example.test/"}
    for partition in PARTITIONS:
        assert lock_env(partition, base) == _fixture_env(base), partition
    assert ts_fixture_env(base) != _fixture_env(base)


def test_the_pinned_version_passes_and_any_other_is_refused():
    for partition in TS_PARTITIONS:
        assert (
            check_manager_version(partition, PINNED[partition] + "\n")
            == (PINNED[partition])
        )
    with pytest.raises(RuntimeError) as refused:
        check_manager_version("pnpm", "12.6.0")
    message = str(refused.value)
    assert "refusing to build 'pnpm'" in message
    assert "'12.6.0'" in message
    assert TS_MANAGER_PINS["pnpm"] in message


def test_the_probe_runs_where_corepack_can_read_the_pin():
    calls: list = []
    for partition in TS_PARTITIONS:
        assert (
            measure_manager_version(partition, _pinned_probe(calls))
            == (PINNED[partition])
        )
    for (command, manifest, env), partition in zip(calls, TS_PARTITIONS, strict=True):
        assert command == manager_version_command(partition)
        assert manifest["packageManager"] == TS_MANAGER_PINS[partition]
        assert env["COREPACK_ENABLE_DOWNLOAD_PROMPT"] == "0"


def test_a_build_on_the_wrong_manager_is_refused_before_anything_is_written(
    tmp_path, monkeypatch
):
    _stub_lock(monkeypatch)
    root = tmp_path / "npm"
    with pytest.raises(RuntimeError, match="refusing to build 'npm'"):
        build("npm", root, probe=lambda command, cwd, env: "10.9.2\n")
    assert not root.exists()


def test_each_partition_builds_into_exactly_the_files_it_planned(tmp_path, monkeypatch):
    # The lock step is the one stub; git and the filesystem run for real, so the
    # committed-set comparison and the dirty-tree refusal are both exercised.
    # The readme equality below compares against the stubbed `lock_command` too,
    # so its `Built by` row is the stub's; the real row is asserted separately.
    _stub_lock(monkeypatch)
    for partition in TS_PARTITIONS:
        root = tmp_path / partition
        summary = build(partition, root, probe=_pinned_probe())
        tracked = sorted(_git(root, "ls-files").splitlines())
        assert tracked == list(COMMITTED[partition]), partition
        assert summary["tracked"] == str(len(COMMITTED[partition])), partition
        assert _git(root, "status", "--porcelain") == "", partition
        log = _git(root, "log", "--format=%s").splitlines()
        assert log == [
            f"Lock the dependency set for {partition}",
            f"Seeded fixture source, {partition} manifests",
        ], partition
        assert (root / FIXTURE_README).read_text() == fixture_readme(
            partition, PINNED[partition]
        )


def test_the_readme_records_the_manager_the_registry_and_the_route():
    npm = fixture_readme("npm", "11.19.0")
    assert _row(npm, "Built by") == f"| Built by | `{' '.join(LOCK['npm'])}` |"
    assert _row(npm, "Lock artifact") == "| Lock artifact | `package-lock.json` |"
    assert PUBLIC_NPM_REGISTRY in _row(npm, "Registry")
    assert "`npm 11.19.0`" in _row(npm, "Manager")
    pnpm = fixture_readme("pnpm", "9.15.9")
    assert "corepack" in _row(pnpm, "Manager")
    assert "`pnpm 9.15.9`" in _row(pnpm, "Manager")
    assert _row(pnpm, "Declares the dependency set in") == (
        "| Declares the dependency set in | `apps/api/package.json`, "
        "`package.json`, `packages/core/package.json` |"
    )
    for readme in (npm, pnpm):
        assert "typescript-fixture-expectations.md" in readme
        assert "do not resolve or install inside this directory" in readme
        assert "uv" not in _row(readme, "Manager")


def test_every_package_json_is_reported_as_a_declaration():
    assert ts_declaring_manifests("npm") == ("package.json",)
    assert len(ts_declaring_manifests("pnpm")) == 3


def test_the_python_only_helpers_refuse_a_typescript_partition_by_name():
    with pytest.raises(ValueError, match="'npm' is a typescript partition"):
        declaring_manifest("npm")
    with pytest.raises(ValueError, match="'uv' is not a TypeScript partition"):
        ts_declaring_manifests("uv")


def _record_builds(monkeypatch):
    calls: list = []
    monkeypatch.setattr(
        build_python_fixtures,
        "build",
        lambda partition, root, uv_version=None: (
            calls.append((partition, root, uv_version))
            or {"partition": partition, "root": str(root), "tracked": "0"}
        ),
    )
    measured: list = []
    monkeypatch.setattr(
        build_python_fixtures,
        "_measure_uv_version",
        lambda: measured.append(True) or "uv 0.0.0",
    )
    return calls, measured


def test_all_builds_both_languages_into_their_own_default_roots(monkeypatch, capsys):
    calls, measured = _record_builds(monkeypatch)
    assert main(["--all"]) == 0
    assert [c[0] for c in calls] == [*PARTITIONS, *TS_PARTITIONS]
    roots = {partition: root for partition, root, _ in calls}
    assert roots["uv"] == build_python_fixtures.DEFAULT_OUTPUT_DIR / "uv"
    assert roots["npm"] == build_python_fixtures.TS_DEFAULT_OUTPUT_DIR / "npm"
    assert roots["pnpm"] == build_python_fixtures.TS_DEFAULT_OUTPUT_DIR / "pnpm"
    assert measured == [True]


def test_typescript_partitions_are_named_like_python_ones(monkeypatch, tmp_path):
    calls, measured = _record_builds(monkeypatch)
    assert main(["npm", "pnpm", "--output-dir", str(tmp_path)]) == 0
    assert [(c[0], c[1]) for c in calls] == [
        ("npm", tmp_path / "npm"),
        ("pnpm", tmp_path / "pnpm"),
    ]
    # No Python partition was asked for, so no uv version was needed.
    assert measured == []


def test_run_passes_the_callers_environment_to_the_subprocess(tmp_path, monkeypatch):
    """The lock steps' environment is the whole point of passing one.

    A `_run` that accepted `env` and ran under `_fixture_env()` anyway would
    keep a user's registry override and corepack's prompt in the lock step, and
    every planner test above would still pass, because they test the value
    handed over rather than the value used.
    """
    import subprocess

    import build_python_fixtures as bf

    seen = []

    def fake_run(command, **kwargs):
        seen.append(kwargs.get("env"))
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr(bf.subprocess, "run", fake_run)
    wanted = {"PATH": "/bin", "COREPACK_ENABLE_DOWNLOAD_PROMPT": "0"}
    bf._run(["true"], tmp_path, env=wanted)
    bf._run(["true"], tmp_path)
    assert seen[0] == wanted
    assert seen[1] == bf._fixture_env()
