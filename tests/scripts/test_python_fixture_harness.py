"""Tests for scripts/run_python_fixture_lens.py (#45).

The harness holds each check record's prescribed invocation verbatim, so the
tests here are mostly guards on that transcription rather than on behaviour: an
invocation that had to be edited to run is the finding the round exists to
produce, and it only shows up as one if the transcription is held to the record.
"""

import re
from pathlib import Path

import pytest
from audit_checks import SKILLS_DIR, load_checks
from python_fixture_spec import (
    DEPS_CHECKS,
    EXPECTATIONS,
    FULL_PARTITION,
    PARTITIONS,
    expectations_for,
)
from run_python_fixture_lens import (
    GRANTS,
    INVOCATIONS,
    MATERIALIZE,
    REASONS,
    STATUSES,
    VENV_PARTITIONS,
    Invocation,
    _fixture_env,
    _run,
    argv_for,
    classify,
    grant_tier,
    invocations_for,
    launcher,
    main,
    packages_for,
    provision_command,
    reconstruct,
    run_partition,
    tools_named_in_records,
)

SKILLS = Path(__file__).resolve().parents[2] / ".agents" / "skills"


def _record_path(check: str) -> Path:
    domain, slug = check.split("/")
    return SKILLS / f"{domain}-audit" / "checks" / f"{slug}.md"


def test_every_python_tool_in_the_family_is_invoked():
    assert {i.tool for i in INVOCATIONS} == tools_named_in_records()


def test_no_check_invokes_the_same_tool_twice():
    pairs = [(i.check, i.tool) for i in INVOCATIONS]
    assert len(pairs) == len(set(pairs))


def test_a_tool_answering_several_checks_is_invoked_once_per_check():
    ruff_checks = {i.check for i in INVOCATIONS if i.tool == "ruff"}
    assert {"arch/complexity", "docs/docstring-coverage"} <= ruff_checks


def test_every_invocation_quotes_its_record_verbatim():
    for inv in INVOCATIONS:
        text = _record_path(inv.check).read_text()
        assert text.count(inv.record_quote) == 1, (
            f"{inv.check}: {inv.record_quote[:40]}"
        )


def test_classify_maps_a_missing_tool_to_no_evidence():
    status, reason = classify(127, "", "command not found", tool_present=False)
    assert status == "no-evidence"
    assert reason == "tool-unavailable"


def test_classify_maps_a_nonzero_exit_from_a_present_tool_to_tool_failed():
    status, reason = classify(2, "", "boom", tool_present=True)
    assert (status, reason) == ("no-evidence", "tool-failed")


def test_classify_maps_clean_output_to_ok():
    assert classify(0, "findings", "", tool_present=True) == ("ok", "")


def test_the_deps_checks_are_all_represented():
    assert set(DEPS_CHECKS) <= {i.check for i in INVOCATIONS}


# --- the exact-set guard -------------------------------------------------------


def test_the_harness_runs_exactly_the_checks_the_expectations_declare():
    """Three views of one set, held equal rather than kept in step by reading.

    The records carrying a `python:` entry are what the round exists to exercise;
    the expectations are what each one is graded against; the harness is what
    runs them. A check present in any one of the three and missing from another
    is either a check nobody grades or a claim nobody tests, and both look like
    a complete run.
    """
    checks, errors = load_checks(SKILLS_DIR)
    assert not errors, errors
    with_python = {c.id for c in checks.values() if c.tooling.get("python")}
    assert {i.check for i in INVOCATIONS} == with_python
    assert {e.check for e in EXPECTATIONS} == with_python


def test_every_invocation_names_a_tool_its_own_record_offers():
    """A tool transcribed onto the wrong check is invisible to the set guards.

    The union over every record equals the union over every invocation whichever
    check each tool landed on, so the exact-set guard on tool names passes on a
    table that gives `bandit` to `arch/cycles`.
    """
    checks, errors = load_checks(SKILLS_DIR)
    assert not errors, errors
    for inv in INVOCATIONS:
        assert inv.tool in checks[inv.check].tooling.get("python", ()), (
            inv.check,
            inv.tool,
        )


def test_every_python_tooling_entry_has_an_invocation():
    """One entry per (check, tool) pair, not per tool.

    A tool answering several checks needs a different invocation for each - ruff
    selects `C901` for complexity and the `D` rules for docstrings - so a table
    holding one entry per tool would exercise one rule selection and report it
    as several checks.
    """
    checks, errors = load_checks(SKILLS_DIR)
    assert not errors, errors
    declared = {
        (c.id, tool) for c in checks.values() for tool in c.tooling.get("python", ())
    }
    assert {(i.check, i.tool) for i in INVOCATIONS} == declared


# --- the transcription itself --------------------------------------------------


def test_a_completed_argv_says_why_it_had_to_be_completed():
    """The completion is the finding, so it never travels without its reason.

    A record whose command does not run as written is what the round is looking
    for. Completing it silently turns that finding into a clean run, so the
    dataclass refuses a completion with no note and this holds the refusal.
    """
    for inv in INVOCATIONS:
        assert bool(inv.completion) <= bool(inv.note), inv.check
    with pytest.raises(ValueError, match="completion"):
        Invocation(
            check="arch/cycles",
            tool="pydeps",
            argv=("pydeps",),
            completion=("src",),
            record_quote="x",
        )


def test_a_quote_is_a_sentence_rather_than_a_fragment():
    """Short fragments collide, and a colliding quote fails for the wrong reason.

    `C901` occurs in `arch/complexity-gate`'s fallback and again in its Fix
    section, so a quote that short would fail the verbatim guard on a record
    nobody had changed.
    """
    for inv in INVOCATIONS:
        assert len(inv.record_quote) >= 40, (inv.check, inv.tool, inv.record_quote)


def test_an_invocation_names_a_check_that_exists_and_a_partition_that_does():
    for inv in INVOCATIONS:
        assert _record_path(inv.check).exists(), inv.check
        named = {p for p, _ in inv.argv_by_partition}
        assert not named - set(PARTITIONS), (inv.check, sorted(named))


def test_the_placeholder_a_record_writes_never_reaches_a_command():
    """`bandit -r <pkg>` is a shape, not a command.

    A placeholder left in `argv` would be passed to the tool as a literal path
    and fail as though the tool were broken, which is the one failure mode this
    table cannot afford to invent.
    """
    for inv in INVOCATIONS:
        for partition in PARTITIONS:
            for word in argv_for(inv, partition):
                assert not re.fullmatch(r"<.+>", word), (inv.check, word)


# --- scoping and grant states --------------------------------------------------


def test_the_full_partition_runs_every_invocation():
    assert set(invocations_for(FULL_PARTITION)) == set(INVOCATIONS)


def test_a_thin_partition_runs_the_deps_checks_and_nothing_arch():
    carried = {i.check for i in invocations_for("poetry")}
    assert set(DEPS_CHECKS) <= carried
    assert not any(c.startswith("arch/") for c in carried)


def test_the_scope_of_a_partition_is_the_expectations_own_scope():
    """Derived from `expectations_for`, so the two cannot disagree.

    A second list of which checks a partition carries would be free to drift
    from the one the published record renders, and the run would then grade a
    partition against expectations it never ran.
    """
    for partition in PARTITIONS:
        assert {i.check for i in invocations_for(partition)} == {
            e.check for e in expectations_for(partition)
        }


def test_the_grant_tier_is_read_from_the_record_rather_than_transcribed():
    checks, errors = load_checks(SKILLS_DIR)
    assert not errors, errors
    assert grant_tier("deps/hygiene", "deptry") == "resolved-tree"
    assert grant_tier("test/coverage-reach", "pytest-cov") == "target-execution"
    assert grant_tier("security/crypto", "bandit") == ""
    for inv in INVOCATIONS:
        tiers = {
            tier for tier, tools in checks[inv.check].needs.items() if inv.tool in tools
        }
        assert grant_tier(inv.check, inv.tool) == (tiers.pop() if tiers else "")


def test_an_unknown_check_or_tool_is_rejected_by_name():
    with pytest.raises(ValueError, match="conda"):
        grant_tier("conda/whatever", "deptry")
    with pytest.raises(ValueError, match="madge"):
        grant_tier("deps/hygiene", "madge")
    with pytest.raises(ValueError, match="conda"):
        invocations_for("conda")


# --- classification ------------------------------------------------------------


def test_classify_maps_a_withheld_grant_to_not_permitted():
    status, reason = classify(0, "", "", tool_present=True, permitted=False)
    assert (status, reason) == ("no-evidence", "not-permitted")


def test_a_finding_tool_exiting_nonzero_is_still_a_run_that_answered():
    """bandit, ruff, deptry and pip-audit all exit 1 when they find something.

    Reading a non-zero exit as `tool-failed` would grade every correct run of
    the tools this round exists to exercise as a tool defect, which is the
    inverse of the failure the fixture is seeded to catch.
    """
    assert classify(1, "B602: subprocess call", "", tool_present=True) == ("ok", "")
    assert classify(1, "", "Traceback", tool_present=True) == (
        "no-evidence",
        "tool-failed",
    )


def test_classify_never_leaves_the_engines_vocabulary():
    observations = [
        (0, "", "", True, True),
        (1, "out", "", True, True),
        (2, "", "err", True, True),
        (127, "", "not found", False, True),
        (0, "out", "", True, False),
    ]
    for code, out, err, present, permitted in observations:
        status, reason = classify(
            code, out, err, tool_present=present, permitted=permitted
        )
        assert status in STATUSES, status
        assert reason in ("", *REASONS), reason


def test_no_prescribed_command_is_never_classified_as_a_tool_failure():
    """A record that prescribes a reading pass has not offered a command.

    Reporting that as `tool-failed` would blame a tool for a record that never
    asked it to run, and the run would read as a broken tool rather than as the
    reading pass the record actually prescribes.
    """
    reading = [i for i in INVOCATIONS if not i.argv and not i.argv_by_partition]
    assert reading, "some records prescribe a reading pass rather than a command"
    for inv in reading:
        assert argv_for(inv, FULL_PARTITION) == ()


# --- how a command is obtained and where it runs -------------------------------


def test_every_invoked_tool_resolves_to_a_package_that_can_be_fetched():
    for inv in INVOCATIONS:
        if argv_for(inv, FULL_PARTITION):
            packages = packages_for(inv.tool)
            assert packages and all(packages), inv.tool


def test_a_route_that_runs_the_suite_brings_a_runner_the_fixture_does_not_declare():
    """The fixture declares no pytest, so `coverage run -m pytest` has none.

    Provisioning only the tool named in the record leaves that route dying on
    `No module named pytest`, which the classifier would read as a tool that
    failed - a failure this harness invented, on an entry the record had right.
    """
    assert packages_for("coverage.py") == ("coverage", "pytest")
    assert packages_for("mutmut") == ("mutmut", "pytest")
    assert packages_for("bandit") == ("bandit",)

    coverage = next(
        i
        for i in INVOCATIONS
        if (i.check, i.tool) == ("test/coverage-reach", "coverage.py")
    )
    assert launcher(coverage, "uv", granted=True) == (
        "uv",
        "run",
        "--with",
        "coverage",
        "--with",
        "pytest",
    )
    assert launcher(coverage, "uv", granted=False) == (
        "uvx",
        "--from",
        "coverage",
        "--with",
        "pytest",
    )


def test_a_multi_package_route_installs_each_of_them_into_the_copy(
    tmp_path, monkeypatch
):
    source = tmp_path / "fixture" / "poetry"
    source.mkdir(parents=True)
    monkeypatch.setattr("run_python_fixture_lens._run", _fake_run([]))
    observed = run_partition(
        "poetry", source, tmp_path / "work", "target-execution", timeout=5
    )
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}
    installed = [
        entry["command"][-1]
        for entry in rows[("test/coverage-reach", "coverage.py")]["provision"]
    ]
    assert installed == ["coverage", "pytest"]


def test_a_deps_tool_runs_from_inside_the_materialized_environment():
    """Measured, not assumed: `uvx deptry` says DEP001 where the truth is DEP003.

    The one-shot runner's sandbox cannot see what the target resolved, so the
    same command reports a missing dependency where the truth is a transitive
    one - and a harness that gets this wrong makes a correct expectation fail.
    """
    in_env = {(i.check, i.tool) for i in INVOCATIONS if i.in_env}
    assert ("deps/hygiene", "deptry") in in_env
    assert ("deps/licenses", "pip-licenses") in in_env
    assert ("deps/freshness", "uv") in in_env
    assert ("security/crypto", "bandit") not in in_env


def test_an_in_env_tool_is_launched_through_the_partitions_own_environment():
    inv = next(
        i for i in INVOCATIONS if (i.check, i.tool) == ("deps/hygiene", "deptry")
    )
    assert launcher(inv, "uv", granted=True)[0] == "uv"
    assert launcher(inv, "poetry", granted=True)[:2] == ("poetry", "run")
    assert launcher(inv, "pipenv", granted=True)[:2] == ("pipenv", "run")


def test_a_venv_partition_is_launched_by_name_rather_than_through_python_m():
    """`pip-licenses` imports as `piplicenses`, so `python -m` has nothing to hand.

    The environment's own `bin` goes on `PATH` instead, which finds every tool
    by the command name the record wrote rather than by a module name the record
    never mentions.
    """
    inv = next(
        i for i in INVOCATIONS if (i.check, i.tool) == ("deps/licenses", "pip-licenses")
    )
    for partition in VENV_PARTITIONS:
        assert launcher(inv, partition, granted=True) == ()
    assert set(VENV_PARTITIONS) == {"pip", "pylock"}


def test_an_audit_owned_tool_is_installed_into_the_copy_this_run_owns():
    """`audit-core` bars installing into the target and prescribes a copy instead.

    Without the install the granted run reports every in-environment tool as
    `tool-unavailable` on four of the five partitions, which is a finding the
    harness invented rather than one the family has.
    """
    assert provision_command("poetry", "deptry") == (
        "poetry",
        "run",
        "pip",
        "install",
        "deptry",
    )
    assert provision_command("pipenv", "deptry")[:2] == ("pipenv", "run")
    assert provision_command("pip", "deptry") == (".venv/bin/pip", "install", "deptry")
    assert provision_command("uv", "deptry") == ()
    with pytest.raises(ValueError, match="conda"):
        provision_command("conda", "deptry")


def test_an_ungranted_run_never_launches_through_a_tree_it_does_not_have():
    inv = next(
        i for i in INVOCATIONS if (i.check, i.tool) == ("deps/hygiene", "deptry")
    )
    assert launcher(inv, "uv", granted=False)[0] == "uvx"


def test_every_partition_has_a_materialization_route():
    assert set(MATERIALIZE) == set(PARTITIONS)
    for partition, commands in MATERIALIZE.items():
        assert commands, partition
        for command in commands:
            assert all(isinstance(word, str) for word in command), partition


def test_a_partition_the_record_prescribes_no_route_for_runs_nothing():
    """`pip-audit` has no mode for a uv, poetry or pipenv tree, and that is the finding.

    Filling one in - a bare `pip-audit` from inside the environment - is the
    repair the transcription exists to make visible, so the entry names those
    partitions with an empty command instead.
    """
    inv = next(
        i
        for i in INVOCATIONS
        if (i.check, i.tool) == ("deps/vulnerabilities", "pip-audit")
    )
    assert argv_for(inv, "uv") == ()
    assert argv_for(inv, "pylock") == ("pip-audit", "--locked", ".")
    assert inv.prescribed("pip") == ("pip-audit", "-r", "requirements.txt")


def test_a_two_step_route_keeps_its_second_command():
    inv = next(
        i
        for i in INVOCATIONS
        if (i.check, i.tool) == ("test/coverage-reach", "coverage.py")
    )
    assert inv.then == ("coverage", "report", "--show-missing")


def test_an_entry_cannot_hold_both_a_shared_and_a_per_partition_command():
    with pytest.raises(ValueError, match="per-partition"):
        Invocation(
            check="deps/inventory",
            tool="cyclonedx-py",
            record_quote="x" * 40,
            argv=("cyclonedx-py",),
            argv_by_partition=(("uv", ("uv", "export")),),
        )


def test_naming_one_partition_twice_is_rejected():
    with pytest.raises(ValueError, match="twice"):
        Invocation(
            check="deps/inventory",
            tool="cyclonedx-py",
            record_quote="x" * 40,
            argv_by_partition=(("uv", ("a",)), ("uv", ("b",))),
        )


# --- the read-only invariant ---------------------------------------------------


def test_reconstructing_inside_the_target_is_refused(tmp_path):
    """Every tool writes something, so the copy never lives under the fixture.

    ruff leaves `.ruff_cache`, pytest leaves `.pytest_cache`, coverage leaves
    `.coverage`; each dirties a tree whose empty `git status --porcelain` is how
    a run proves it read without writing.
    """
    source = tmp_path / "uv"
    source.mkdir()
    with pytest.raises(ValueError, match="read-only invariant"):
        reconstruct("uv", source, source / "work")


def test_the_copy_carries_the_git_directory(tmp_path):
    source = tmp_path / "fixture" / "uv"
    (source / ".git").mkdir(parents=True)
    (source / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    (source / "pyproject.toml").write_text("[project]\n")
    copy = reconstruct("uv", source, tmp_path / "work")
    assert (copy / ".git" / "HEAD").exists()
    assert (copy / "pyproject.toml").exists()
    assert not str(copy.resolve()).startswith(str(source.resolve()))


def test_a_second_run_replaces_the_previous_copy(tmp_path):
    source = tmp_path / "fixture" / "uv"
    source.mkdir(parents=True)
    (source / "pyproject.toml").write_text("[project]\n")
    first = reconstruct("uv", source, tmp_path / "work")
    (first / "leftover.txt").write_text("from the previous run\n")
    second = reconstruct("uv", source, tmp_path / "work")
    assert not (second / "leftover.txt").exists()


# --- running --------------------------------------------------------------------


def test_the_run_environment_drops_the_handbooks_own_virtualenv(monkeypatch):
    """Otherwise every `deps` answer is about this repository rather than the fixture."""
    monkeypatch.setenv("VIRTUAL_ENV", "/somewhere/else")
    monkeypatch.setenv("PYTHONPATH", "/somewhere/else")
    env = _fixture_env()
    assert "VIRTUAL_ENV" not in env
    assert "PYTHONPATH" not in env
    assert env["PIPENV_IGNORE_VIRTUALENVS"] == "1"


def test_a_missing_binary_is_reported_as_absent_rather_than_as_a_failure(tmp_path):
    """The engine's two reasons depend on telling these apart.

    A tool that could not be obtained is `tool-unavailable` and says something
    about the audit environment; a tool that ran and errored is `tool-failed`
    and says something about the target.
    """
    outcome = _run(("definitely-not-a-real-binary-45",), tmp_path, timeout=5)
    assert outcome["tool_present"] is False
    assert "FileNotFoundError" in outcome["stderr"]
    status, reason = classify(
        1, "", str(outcome["stderr"]), tool_present=bool(outcome["tool_present"])
    )
    assert (status, reason) == ("no-evidence", "tool-unavailable")


def _fake_run(recorded):
    def run(command, cwd, timeout, bin_dir=None):
        recorded.append(list(command))
        return {
            "returncode": 0,
            "stdout": "output",
            "stderr": "",
            "tool_present": True,
        }

    return run


def test_an_ungranted_run_materializes_nothing_and_reports_not_permitted(
    tmp_path, monkeypatch
):
    source = tmp_path / "fixture" / "uv"
    source.mkdir(parents=True)
    (source / "pyproject.toml").write_text("[project]\n")
    recorded = []
    monkeypatch.setattr("run_python_fixture_lens._run", _fake_run(recorded))

    observed = run_partition("uv", source, tmp_path / "work", "none", timeout=5)

    assert observed["materialization"] == []
    assert all(cmd[0] != "uv" or cmd[1] != "sync" for cmd in recorded)
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}
    assert rows[("test/coverage-reach", "pytest-cov")]["reason"] == "not-permitted"
    assert rows[("security/crypto", "bandit")]["status"] == "ok"


def test_a_granted_run_materializes_first_and_then_runs_in_the_environment(
    tmp_path, monkeypatch
):
    source = tmp_path / "fixture" / "uv"
    source.mkdir(parents=True)
    (source / "pyproject.toml").write_text("[project]\n")
    recorded = []
    monkeypatch.setattr("run_python_fixture_lens._run", _fake_run(recorded))

    observed = run_partition(
        "uv", source, tmp_path / "work", "target-execution", timeout=5
    )

    assert [m["command"] for m in observed["materialization"]] == [["uv", "sync"]]
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}
    deptry = rows[("deps/hygiene", "deptry")]
    assert deptry["command"][:2] == ["uv", "run"]
    assert deptry["command"][-2:] == ["deptry", "."]
    assert deptry["status"] == "ok"
    follow_up = rows[("test/coverage-reach", "coverage.py")]["then"]
    assert follow_up["command"][-3:] == ["coverage", "report", "--show-missing"]


def test_a_record_with_no_command_is_recorded_as_such_rather_than_run(
    tmp_path, monkeypatch
):
    source = tmp_path / "fixture" / "uv"
    source.mkdir(parents=True)
    monkeypatch.setattr("run_python_fixture_lens._run", _fake_run([]))
    observed = run_partition("uv", source, tmp_path / "work", "none", timeout=5)
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}
    reading = rows[("test/property-based-gap", "hypothesis")]
    assert reading["ran"] is False
    assert reading["status"] == ""
    assert "prescribes no command" in reading["why"]


def test_an_unknown_grant_is_rejected_by_name(tmp_path):
    source = tmp_path / "fixture" / "uv"
    source.mkdir(parents=True)
    with pytest.raises(ValueError, match="sudo"):
        run_partition("uv", source, tmp_path / "work", "sudo", timeout=5)


def test_the_results_file_lands_beside_the_partitions_never_inside_one(
    tmp_path, monkeypatch, capsys
):
    """A results file written into the tree is the write the invariant forbids."""
    fixture_root = tmp_path / "fixtures"
    (fixture_root / "uv").mkdir(parents=True)
    monkeypatch.setattr("run_python_fixture_lens._run", _fake_run([]))

    exit_code = main(
        [
            "uv",
            "--grant",
            "none",
            "--fixture-root",
            str(fixture_root),
            "--work-dir",
            str(tmp_path / "work"),
        ]
    )

    assert exit_code == 0
    written = fixture_root / "results" / "uv-none.json"
    assert written.exists()
    assert not any((fixture_root / "uv").glob("*.json"))
    assert "written to" in capsys.readouterr().out


def test_the_two_grant_states_are_the_two_the_round_runs():
    assert GRANTS == ("none", "target-execution")
