"""The TypeScript half of the fixture lens (#181), held without running anything.

`scripts/run_python_fixture_lens.py` reads the `lang: typescript` routes the same
way it reads the python ones and differs in its `TS_` tables. Each table is held
here to an exact set derived from the records or the spec, so a record growing a
route, a precondition or a manager subcommand fails a test instead of reaching a
run as a silent default. Every test is offline: `_run` is replaced wherever a
command would otherwise execute.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from audit_checks import SKILLS_DIR, load_checks
from build_python_fixtures import PUBLIC_NPM_REGISTRY
from python_fixture_spec import TS_CORE, TS_EXPECTATIONS, TS_PARTITIONS
from run_python_fixture_lens import (
    NONZERO_EXIT_KINDS,
    PARTITION_KEYS,
    PLUGIN_ROOT_VARIABLE,
    REPO_ROOT,
    TS_APPLIES_WHEN,
    TS_COMPLETIONS,
    TS_COREPACK_MANAGED,
    TS_IN_ENV,
    TS_MANAGER_TOOLS,
    TS_MATERIALIZE,
    TS_NO_VERSION_ROUTE,
    TS_NONZERO_EXIT_MEANING,
    TS_ONE_SHOT,
    TS_RUN_IN_PACKAGE,
    TS_SHIM_DIRNAME,
    TS_SHUFFLE_SEED,
    TS_VERSION_PROBE,
    Invocation,
    TsCompletion,
    _partition_keys,
    _ts_fixture_env,
    argv_for,
    expand_plugin_root,
    grant_tier,
    invocations_for,
    launcher,
    not_run_on,
    routed_invocations,
    run_partition,
    tools_named_in_records,
    workdir_for,
)

LANG = "typescript"


def _records():
    checks, errors = load_checks(SKILLS_DIR)
    assert not errors, errors
    return checks


def _ts_routes():
    """Every `lang: typescript` route in the tree, with its check id."""
    return [
        (check_id, route)
        for check_id, record in sorted(_records().items())
        for route in record.routes
        if route.lang == LANG
    ]


def _runs_command_routes():
    return [
        (check_id, route)
        for check_id, route in _ts_routes()
        if route.kind == "command" and route.disposition == "runs" and route.tool
    ]


def _rows_on(partition):
    """`(invocation, argv)` for every row on `partition` that prescribes a command."""
    return [
        (inv, argv)
        for inv in invocations_for(partition)
        if (argv := argv_for(inv, partition))
    ]


def _runnable_on(partition):
    """The rows that would actually run a command on `partition`."""
    return [
        (inv, argv)
        for inv, argv in _rows_on(partition)
        if not_run_on(inv, partition) is None
    ]


def _commands_run(partition, granted):
    """Every full command a row would run, launcher words included."""
    out = []
    for inv, argv in _runnable_on(partition):
        prefix = launcher(inv, partition, granted=granted)
        out.append((inv, (*prefix, *argv)))
        if inv.then:
            out.append((inv, (*prefix, *inv.then)))
    return out


# --- scope --------------------------------------------------------------------


@pytest.mark.parametrize("partition", TS_PARTITIONS)
def test_the_harness_runs_exactly_the_checks_the_typescript_expectations_declare(
    partition,
):
    expected = {e.check for e in TS_EXPECTATIONS if partition in e.partitions}
    assert {i.check for i in invocations_for(partition)} == expected


def test_every_typescript_expectation_has_an_invocation_on_each_partition_it_names():
    """And a command that actually runs there, on every partition it names.

    No exception is carried. The cell nearest to being one is `deps/inventory`
    on pnpm: `npm sbom` is npm's subcommand and runs on no pnpm tree, so the
    record's `@cdxgen/cdxgen` command route is the only command there. A check
    losing its last runnable command on a partition fails here rather than
    reading as a row the round simply had nothing for.
    """
    without_a_command = set()
    for expectation in TS_EXPECTATIONS:
        for partition in expectation.partitions:
            rows = [
                i for i in invocations_for(partition) if i.check == expectation.check
            ]
            assert rows, (expectation.check, partition)
            if not any(
                inv.check == expectation.check for inv, _ in _runnable_on(partition)
            ):
                without_a_command.add((expectation.check, partition))
    assert without_a_command == set()


CDXGEN = "@cdxgen/cdxgen"
CDXGEN_ARGV = ("cdxgen", "-t", "js", "--no-install-deps", "-o", "-", ".")


@pytest.mark.parametrize("granted", [False, True])
def test_the_pnpm_inventory_command_is_cdxgen_fetched_by_its_package(granted):
    """The exact command the pnpm partition runs for `deps/inventory`.

    Pinned whole because each word is a claim the fixture run measured. The
    launcher names the package, `@cdxgen/cdxgen`, and not the bin: the bin is
    `cdxgen`, and the record's note says `@cyclonedx/cdxgen` is the superseded
    v12 line. `--no-install-deps` keeps cdxgen from installing into the tree it
    reads, and `-o -` sends the document to stdout instead of a `bom.json` in
    the working directory - the copy the lens runs in, which every later row
    then reads. The route is untiered, so the grant changes nothing here.
    """
    commands = [
        command
        for inv, command in _commands_run("pnpm", granted)
        if inv.check == "deps/inventory"
    ]
    assert commands == [
        ("pnpm", f"--package={CDXGEN}", "dlx", *CDXGEN_ARGV),
    ], commands


def test_the_inventory_route_writes_its_document_to_stdout_and_installs_nothing():
    """The two flags that keep the route from writing into the target.

    Held on the record rather than on the lens, because the record is what an
    audit outside this repository runs. Without `-o -` cdxgen writes
    `bom.json` into the directory it scans; without `--no-install-deps` it
    installs the dependencies it is meant to be reading off the lockfile.
    """
    route = next(
        r
        for r in _records()["deps/inventory"].routes
        if r.lang == LANG and r.tool == CDXGEN
    )
    assert route.kind == "command" and route.disposition == "runs"
    assert tuple(route.argv) == CDXGEN_ARGV
    argv = list(route.argv)
    assert argv[argv.index("-o") + 1] == "-"
    assert "--no-install-deps" in argv
    assert "--dry-run" not in argv
    assert not route.needs


def test_every_typescript_tooling_entry_has_a_routed_row():
    declared = {
        (c.id, tool) for c in _records().values() for tool in c.tooling.get(LANG, ())
    }
    assert {(i.check, i.tool) for i in routed_invocations(LANG)} == declared
    assert {t for _, t in declared} == tools_named_in_records(LANG)


# --- forbidden routes -----------------------------------------------------------


def test_a_forbidden_route_contributes_no_row_and_no_form():
    forbidden = [(c, r) for c, r in _ts_routes() if r.disposition == "forbidden"]
    assert forbidden, "the rule has no subject in the tree"
    rows = {(i.check, i.tool): i for i in routed_invocations(LANG)}
    for check_id, route in forbidden:
        others = [
            r
            for c, r in _ts_routes()
            if c == check_id and r.tool == route.tool and r.disposition != "forbidden"
        ]
        if not others:
            assert (check_id, route.tool) not in rows, (check_id, route.tool)
        declared = {form for inv in rows.values() for form, _ in inv.forms}
        if route.argv:
            assert " ".join(route.argv) not in declared, (check_id, route.argv)


@pytest.mark.parametrize("granted", (False, True))
@pytest.mark.parametrize("partition", TS_PARTITIONS)
def test_no_forbidden_argv_prefixes_any_command_a_row_runs(partition, granted):
    """Read as a prefix, and as a prefix once the runner word is dropped.

    Not as a contiguous subsequence: the prescribed
    `pnpm --package=... dlx depcruise` legitimately carries `dlx depcruise`,
    which is the forbidden form only when nothing names the package in front
    of it - and that is `pnpm dlx depcruise`, whose tail is the prefix below.
    """
    forbidden = [
        tuple(r.argv)
        for _, r in _ts_routes()
        if r.disposition == "forbidden" and r.argv
    ]
    assert forbidden
    for inv, command in _commands_run(partition, granted):
        for bad in forbidden:
            for tail in (command, command[1:]):
                assert tuple(tail[: len(bad)]) != bad, (inv.check, command, bad)


# --- forms ----------------------------------------------------------------------


@pytest.mark.parametrize("partition", TS_PARTITIONS)
def test_every_prescribed_command_is_a_declared_runs_form(partition):
    for inv, _ in _rows_on(partition):
        form = " ".join(inv.prescribed(partition))
        assert (form, "runs") in inv.forms, (inv.check, inv.tool, form, inv.forms)


def test_every_runs_form_is_prescribed_on_a_partition_except_the_yarn_ones():
    """A `yarn`-keyed form is declared, and no fixture partition is yarn.

    Prescribed, not run: a yarn subcommand's shared argv is prescribed on every
    partition and runs on none, which `not_run_on` decides and the manager tests
    hold, so it is not an exception here.
    """
    uncovered = set()
    for inv in routed_invocations(LANG):
        prescribed = {" ".join(inv.prescribed(p)) for p in TS_PARTITIONS}
        for form, disposition in inv.forms:
            if disposition == "runs" and form not in prescribed:
                uncovered.add((inv.check, inv.tool, form))
    yarn_forms = {
        (check_id, route.tool, " ".join(route.argv_by_partition["yarn"]))
        for check_id, route in _runs_command_routes()
        if "yarn" in route.argv_by_partition
    }
    assert uncovered == yarn_forms


@pytest.mark.parametrize("partition", TS_PARTITIONS)
def test_no_placeholder_a_record_writes_reaches_a_command_that_runs(partition):
    for inv, argv in _runnable_on(partition):
        assert not any("<" in token for token in argv), (inv.check, argv)


def test_the_rows_run_from_the_package_are_exactly_the_tsconfig_relative_ones():
    """Derived from the records: a route whose argv takes `<tsconfig>` runs beside it.

    dependency-cruiser resolves the tsconfig's `include` against its working
    directory, so the operand only means what the record says from there. madge
    takes `--ts-config` too but as a trailing completion rather than the
    `<tsconfig>` placeholder, and resolves it against the file's own directory.
    """
    tsconfig_relative = {
        (check_id, route.tool)
        for check_id, route in _runs_command_routes()
        if any(
            "<tsconfig>" in argv
            for argv in (route.argv, *route.argv_by_partition.values())
        )
    }
    assert tsconfig_relative
    assert set(TS_RUN_IN_PACKAGE) == tsconfig_relative
    for inv in routed_invocations(LANG):
        key = (inv.check, inv.tool)
        assert workdir_for(inv, "npm") == ""
        assert workdir_for(inv, "pnpm") == (TS_CORE if key in tsconfig_relative else "")


def test_every_plugin_root_path_a_route_spells_is_a_file_this_checkout_ships():
    """A `${CLAUDE_PLUGIN_ROOT}/` token names a tracked file, in every language.

    The variable is the plugin install's directory, and an install carries this
    repository, so a path under it that resolves to nothing here resolves to
    nothing in the cache either.
    """
    spelled = set()
    for record in _records().values():
        for route in record.routes:
            for argv in (route.argv, *route.argv_by_partition.values(), route.then):
                for token in argv or ():
                    if PLUGIN_ROOT_VARIABLE in token:
                        assert token.startswith(f"{PLUGIN_ROOT_VARIABLE}/"), token
                        spelled.add(token)
    assert spelled
    for token in spelled:
        path = REPO_ROOT / token.removeprefix(f"{PLUGIN_ROOT_VARIABLE}/")
        assert path.is_file(), token
        assert "checks" not in path.relative_to(REPO_ROOT).parts, token


@pytest.mark.parametrize("partition", TS_PARTITIONS)
def test_no_plugin_root_variable_reaches_a_command_that_runs(partition):
    for inv, argv in _runnable_on(partition):
        composed = expand_plugin_root(argv)
        assert not any("${" in token for token in composed), (inv.check, composed)


def test_the_dependency_cruiser_routes_read_the_json_output():
    """With no rules in the shipped config, the default `err` output is a false clean.

    `arch/layering` is not among them: its route applies only where the project
    carries its own config, whose rules are the boundary that check tests.
    """
    shipped = ("arch/cycles", "arch/coupling", "arch/over-decomposition")
    rows = [
        i
        for i in routed_invocations(LANG)
        if i.tool == "dependency-cruiser" and i.check in shipped
    ]
    assert sorted(i.check for i in rows) == sorted(shipped)
    for inv in rows:
        for partition in TS_PARTITIONS:
            argv = inv.prescribed(partition)
            assert argv[argv.index("--output-type") + 1] == "json", inv.check
            config = argv[argv.index("--config") + 1]
            assert config.startswith(f"{PLUGIN_ROOT_VARIABLE}/"), (inv.check, config)


def test_the_shuffle_seed_fills_the_records_placeholder_and_not_the_record():
    (row,) = [
        i
        for i in invocations_for("npm")
        if (i.check, i.tool) == ("test/determinism", "vitest")
    ]
    assert "--sequence.seed=<n>" in row.prescribed("npm")
    assert f"--sequence.seed={TS_SHUFFLE_SEED}" in argv_for(row, "npm")


# --- partition keys -------------------------------------------------------------


def _route(**kw):
    from types import SimpleNamespace

    return SimpleNamespace(
        **({"argv": (), "argv_by_partition": {}, "own_runner": False} | kw)
    )


def test_a_yarn_key_is_a_typescript_partition_key_that_applies_to_no_partition():
    route = _route(argv_by_partition={"pnpm": ("p",), "yarn": ("y",)})
    assert _partition_keys("c/x", "t", route, LANG) == ("pnpm", "yarn")
    with pytest.raises(ValueError, match="yarn"):
        _partition_keys("c/x", "t", route)
    assert "yarn" in PARTITION_KEYS[LANG] and "yarn" not in TS_PARTITIONS


def test_a_key_that_is_no_package_manager_is_refused_by_name():
    with pytest.raises(ValueError, match="bun"):
        _partition_keys("c/x", "t", _route(argv_by_partition={"bun": ("b",)}), LANG)


def test_a_fetcher_led_route_is_its_own_runner_on_both_partitions():
    rows = [i for i in routed_invocations(LANG) if i.tool == "dependency-cruiser"]
    assert rows
    for row in rows:
        assert set(row.own_runner) == set(TS_PARTITIONS), row.check
        for partition in TS_PARTITIONS:
            assert launcher(row, partition, granted=True) == ()
            assert launcher(row, partition, granted=False) == ()


# --- launcher -------------------------------------------------------------------


def _inv(tool="madge", in_env=False, **kw):
    return Invocation(check="c/x", tool=tool, argv=(tool,), in_env=in_env, **kw)


@pytest.mark.parametrize(
    "partition, granted, in_env, expected",
    [
        ("npm", False, False, ("npx", "--yes", "--package=madge", "--")),
        ("npm", True, False, ("npx", "--yes", "--package=madge", "--")),
        ("npm", False, True, ("npx", "--yes", "--package=madge", "--")),
        ("npm", True, True, ("npx", "--no", "--")),
        ("pnpm", False, False, ("pnpm", "--package=madge", "dlx")),
        ("pnpm", True, False, ("pnpm", "--package=madge", "dlx")),
        ("pnpm", False, True, ("pnpm", "--package=madge", "dlx")),
        (
            "pnpm",
            True,
            True,
            ("pnpm", "--config.verify-deps-before-run=false", "exec"),
        ),
    ],
)
def test_the_launcher_prefix_per_manager(partition, granted, in_env, expected):
    assert launcher(_inv(in_env=in_env), partition, granted=granted) == expected


def test_the_launcher_tables_name_both_partitions():
    assert set(TS_ONE_SHOT) == set(TS_IN_ENV) == set(TS_PARTITIONS)


def test_every_npx_prefix_ends_npx_options_before_the_tool():
    """Without `--`, npx reads a flag after the tool name as its own.

    Measured: `npx --no vitest --version` printed npm's version, so the granted
    npm run's version map recorded `11.19.0` for vitest and jest. Every npx
    prefix, one-shot and in-environment alike, ends with `--`.
    """
    for prefix in (TS_ONE_SHOT["npm"], TS_IN_ENV["npm"]):
        assert prefix[0] == "npx"
        assert prefix[-1] == "--", prefix


def test_the_in_env_version_probe_reaches_the_tool_on_npm():
    (row,) = [
        i
        for i in routed_invocations(LANG)
        if (i.check, i.tool) == ("test/isolation", "vitest")
    ]
    prefix = launcher(row, "npm", granted=True, honour_own_runner=False)
    assert (*prefix, *TS_VERSION_PROBE["vitest"]) == (
        "npx",
        "--no",
        "--",
        "vitest",
        "--version",
    )


@pytest.mark.parametrize("tool", sorted(TS_MANAGER_TOOLS))
def test_a_manager_subcommand_runs_bare(tool):
    inv = Invocation(check="c/x", tool=tool, argv=tuple(tool.split()))
    for partition in TS_PARTITIONS:
        assert launcher(inv, partition, granted=True) == ()
        assert launcher(inv, partition, granted=False) == ()


def test_the_version_probe_still_fetches_what_an_own_runner_route_never_does():
    (row,) = [
        i
        for i in routed_invocations(LANG)
        if (i.check, i.tool) == ("arch/cycles", "dependency-cruiser")
    ]
    assert launcher(row, "pnpm", granted=True, honour_own_runner=False) == (
        "pnpm",
        "--package=dependency-cruiser",
        "dlx",
    )


def test_the_testing_tools_run_inside_the_materialized_tree():
    """`in_env` on every vitest and jest row, which the records now declare."""
    rows = [i for i in routed_invocations(LANG) if i.tool in ("vitest", "jest")]
    assert rows
    assert all(row.in_env for row in rows), [r.check for r in rows if not r.in_env]


# --- tables: exact sets -----------------------------------------------------------


def test_the_manager_tools_are_exactly_the_routes_led_by_a_package_manager():
    derived = {
        route.tool: route.argv[0]
        for _, route in _runs_command_routes()
        if route.argv and route.argv[0] in PARTITION_KEYS[LANG] and not route.own_runner
    }
    assert derived == TS_MANAGER_TOOLS


def test_a_manager_subcommand_runs_only_on_its_own_managers_partition():
    for partition in TS_PARTITIONS:
        for inv, _ in _rows_on(partition):
            manager = TS_MANAGER_TOOLS.get(inv.tool)
            if manager is None:
                continue
            skipped = not_run_on(inv, partition)
            if manager == partition:
                assert skipped is None or skipped[0] != "manager", inv.tool
            else:
                assert skipped is not None and skipped[0] == "manager", inv.tool


def test_the_applies_when_answers_cover_exactly_the_routes_that_carry_one():
    derived = {
        (check_id, route.tool)
        for check_id, route in _runs_command_routes()
        if route.applies_when
    }
    assert set(TS_APPLIES_WHEN) == derived


def test_the_applies_when_answers_are_the_fixtures_own():
    holds = {key: answer.holds for key, answer in TS_APPLIES_WHEN.items()}
    assert holds == {
        ("arch/cycles", "madge"): True,
        ("arch/layering", "dependency-cruiser"): False,
        ("test/coverage-reach", "vitest"): True,
        ("test/coverage-reach", "jest"): False,
        ("test/determinism", "vitest"): True,
        ("test/determinism", "jest"): False,
        ("test/isolation", "vitest"): True,
        ("deps/licenses", "yarn licenses list"): False,
        ("deps/transitive-licenses", "yarn licenses list"): False,
    }


def test_the_materialization_installs_from_the_lockfile_without_scripts():
    assert TS_MATERIALIZE == {
        "npm": (("npm", "ci", "--ignore-scripts"),),
        "pnpm": (("pnpm", "install", "--frozen-lockfile", "--ignore-scripts"),),
    }


def _probed_tools():
    """Every tool a TypeScript partition probes: invoked there, and not another
    manager's subcommand, which `probe_versions` skips."""
    return {
        inv.tool
        for partition in TS_PARTITIONS
        for inv in invocations_for(partition)
        if TS_MANAGER_TOOLS.get(inv.tool, partition) == partition
    }


def test_every_probed_tool_has_a_version_route_or_a_stated_absence():
    assert set(TS_VERSION_PROBE) == _probed_tools()
    absent = {tool for tool, probe in TS_VERSION_PROBE.items() if probe is None}
    assert absent == set(TS_NO_VERSION_ROUTE)
    assert all(reason.strip() for reason in TS_NO_VERSION_ROUTE.values())


def test_a_manager_subcommand_probes_its_managers_version():
    for tool, manager in TS_MANAGER_TOOLS.items():
        if tool in TS_VERSION_PROBE:
            assert TS_VERSION_PROBE[tool] == (manager, "--version")


def test_every_tool_that_can_run_a_command_carries_a_nonzero_exit_meaning():
    can_run = {
        inv.tool
        for partition in TS_PARTITIONS
        for inv, _ in _rows_on(partition)
        if TS_MANAGER_TOOLS.get(inv.tool, partition) == partition
    }
    assert set(TS_NONZERO_EXIT_MEANING) == can_run
    assert set(TS_NONZERO_EXIT_MEANING.values()) <= set(NONZERO_EXIT_KINDS)


def test_the_completions_are_exactly_the_incomplete_commands():
    assert set(TS_COMPLETIONS) == {
        ("arch/cycles", "madge"),
        ("arch/cycles", "dependency-cruiser"),
        ("arch/coupling", "dependency-cruiser"),
        ("arch/over-decomposition", "dependency-cruiser"),
        ("test/determinism", "vitest"),
    }
    commanded = {(inv.check, inv.tool) for p in TS_PARTITIONS for inv, _ in _rows_on(p)}
    assert set(TS_COMPLETIONS) <= commanded


def test_a_path_completion_lands_in_the_seeded_package_on_each_partition():
    """Derived from `TS_CORE`, never spelled: on pnpm the seeded source is a member."""
    for key, completion in TS_COMPLETIONS.items():
        for partition, tokens in completion.by_partition:
            prefix = "" if partition == "npm" else f"{TS_CORE}/"
            assert all(token.startswith(prefix) for token in tokens), key
            if partition == "npm":
                assert not any(token.startswith(TS_CORE) for token in tokens), key


def test_a_completion_needs_tokens_or_fills_and_a_reason():
    with pytest.raises(ValueError, match="not one"):
        TsCompletion(note="why")
    with pytest.raises(ValueError, match="clean run"):
        TsCompletion(note="", fills=(("<n>", "1"),))
    with pytest.raises(ValueError, match="TypeScript partition"):
        TsCompletion(note="why", by_partition=(("uv", ("src",)),))


# --- grants ------------------------------------------------------------------------


def test_the_grant_tier_is_the_prescribed_typescript_routes():
    assert grant_tier("deps/vulnerabilities", "npm audit", LANG) == ""
    assert grant_tier("deps/freshness", "pnpm outdated", LANG) == "resolved-tree"
    assert grant_tier("test/isolation", "vitest", LANG) == "target-execution"
    with pytest.raises(ValueError, match="typescript"):
        grant_tier("deps/vulnerabilities", "pip-audit", LANG)


# --- environment and run -------------------------------------------------------------


def test_the_typescript_environment_drops_every_registry_override(monkeypatch):
    monkeypatch.setenv("npm_config_registry", "https://registry.example.test/")
    monkeypatch.setenv("NPM_CONFIG_@scope:registry", "https://registry.example.test/")
    monkeypatch.setenv("PATH", "/usr/bin")
    env = _ts_fixture_env(Path("/shims"))
    assert env["npm_config_registry"] == PUBLIC_NPM_REGISTRY
    assert not [
        n for n in env if n.lower().endswith("registry") and n != "npm_config_registry"
    ]
    assert env["COREPACK_ENABLE_DOWNLOAD_PROMPT"] == "0"
    assert env["COREPACK_ENABLE_AUTO_PIN"] == "0"
    assert env["PATH"].split(os.pathsep)[0] == "/shims"


def _outcome(returncode=0, stdout="out", stderr=""):
    return {
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "tool_present": True,
    }


def _fake_run(calls):
    def run(command, cwd, timeout, env=None):
        calls.append({"command": tuple(command), "cwd": Path(cwd), "env": env})
        return _outcome()

    return run


@pytest.mark.parametrize("partition", TS_PARTITIONS)
def test_a_granted_run_materializes_only_inside_the_copy(
    tmp_path, monkeypatch, partition
):
    source = tmp_path / "fixtures" / partition
    source.mkdir(parents=True)
    work = tmp_path / "work"
    work.mkdir()
    calls = []
    monkeypatch.setattr("run_python_fixture_lens._run", _fake_run(calls))
    observed = run_partition(partition, source, work, "target-execution", 5)

    copy = work / partition
    # A row `TS_RUN_IN_PACKAGE` names runs from the seeded package, which is the
    # copy's root on npm and a member inside it on pnpm; nothing runs outside it.
    in_package = copy / TS_CORE if partition != "npm" else copy
    allowed = {copy, in_package}
    assert all(call["cwd"] in allowed for call in calls), {c["cwd"] for c in calls}
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}
    for key in TS_RUN_IN_PACKAGE:
        assert rows[key].get("workdir", "") == ("" if partition == "npm" else TS_CORE)
        ran = [c for c in calls if c["command"] == tuple(rows[key]["command"])]
        assert ran and all(c["cwd"] == in_package for c in ran), key
    assert all(call["env"] is not None for call in calls)
    commands = [call["command"] for call in calls]
    shim = work / TS_SHIM_DIRNAME
    if partition in TS_COREPACK_MANAGED:
        assert commands[0] == (
            "corepack",
            "enable",
            partition,
            "--install-directory",
            str(shim),
        )
        assert observed["setup"][0]["command"] == list(commands[0])
        assert all(c["env"]["PATH"].split(os.pathsep)[0] == str(shim) for c in calls)
        commands = commands[1:]
    else:
        assert observed["setup"] == []
    assert (
        tuple(commands[: len(TS_MATERIALIZE[partition])]) == TS_MATERIALIZE[partition]
    )


def test_a_row_the_partition_cannot_run_is_recorded_with_its_reason(
    tmp_path, monkeypatch
):
    source = tmp_path / "fixtures" / "pnpm"
    source.mkdir(parents=True)
    calls = []
    monkeypatch.setattr("run_python_fixture_lens._run", _fake_run(calls))
    observed = run_partition("pnpm", source, tmp_path / "work", "target-execution", 5)
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}

    npm_audit = rows[("deps/vulnerabilities", "npm audit")]
    assert (npm_audit["ran"], npm_audit["not_run"], npm_audit["status"]) == (
        False,
        "manager",
        "",
    )
    jest = rows[("test/coverage-reach", "jest")]
    assert (jest["ran"], jest["not_run"]) == (False, "applies-when")
    ran = {tuple(c["command"]) for c in calls}
    assert ("npm", "audit") not in ran
    assert ("pnpm", "audit") in ran
    assert "npm audit" not in observed["versions"]


def test_an_ungranted_typescript_run_materializes_nothing_and_gates_the_tiers(
    tmp_path, monkeypatch
):
    source = tmp_path / "fixtures" / "npm"
    source.mkdir(parents=True)
    calls = []
    monkeypatch.setattr("run_python_fixture_lens._run", _fake_run(calls))
    observed = run_partition("npm", source, tmp_path / "work", "none", 5)
    assert observed["materialization"] == []
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}
    assert rows[("test/isolation", "vitest")]["reason"] == "not-permitted"
    assert rows[("deps/vulnerabilities", "npm audit")]["ran"] is True
    assert ("npm", "ci", "--ignore-scripts") not in {c["command"] for c in calls}


def test_a_typescript_launcher_that_cannot_fetch_the_tool_is_a_miss():
    """The measured messages, each on the command shape that prints it."""
    from run_python_fixture_lens import launcher_missed

    npx_err = "npm error code E404\nnpm error 404 Not Found - GET https://registry.npmjs.org/x"
    assert launcher_missed(["npx", "--yes", "--package=x", "--", "x"], 1, npx_err)
    assert launcher_missed(["npx", "--no", "--", "x"], 1, npx_err)
    dlx_err = " ERR_PNPM_FETCH_404  GET https://registry.npmjs.org/x: Not Found - 404"
    assert launcher_missed(["pnpm", "--package=x", "dlx", "x"], 1, dlx_err)
    assert not launcher_missed(["pnpm", "--package=x", "dlx", "x"], 0, dlx_err)


def test_a_package_manager_subcommand_404_is_not_a_missing_tool():
    """`pnpm audit` or `npm outdated` fetch no tool, so a 404 there is about the target."""
    from run_python_fixture_lens import launcher_missed

    assert not launcher_missed(["pnpm", "audit"], 1, " ERR_PNPM_FETCH_404  GET ...")
    assert not launcher_missed(["npm", "outdated"], 1, "npm error code E404")
