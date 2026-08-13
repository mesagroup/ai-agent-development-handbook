"""Tests for scripts/run_python_fixture_lens.py (#45).

The harness holds each check record's prescribed invocation verbatim, so the
tests here are mostly guards on that transcription rather than on behaviour: an
invocation that had to be edited to run is the finding the round exists to
produce, and it only shows up as one if the transcription is held to the record.
"""

import os
import re
from pathlib import Path

import pytest
from audit_checks import SKILLS_DIR, load_checks
from python_fixture_spec import (
    DEPS_CHECKS,
    EXPECTATIONS,
    FULL_PARTITION,
    PACKAGE,
    PARTITIONS,
    expectations_for,
)
from run_python_fixture_lens import (
    DETAILS,
    GRANTS,
    INVOCATIONS,
    MATERIALIZE,
    REASONS,
    REPO_ROOT,
    STATUSES,
    SUPPLIED_REQUIREMENTS,
    TOOL_PACKAGES,
    VENV_BIN,
    VENV_PARTITIONS,
    Invocation,
    _fixture_env,
    _run,
    argv_for,
    classify,
    grant_tier,
    invocations_for,
    launcher,
    launcher_missed,
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


def _tokens(text: str) -> list[str]:
    """The words of a quote or a command, with Markdown's decoration removed.

    A record writes a command inside backticks and inside a sentence, so the raw
    split never matches: ``` `cyclonedx-py`'s ``` has to reduce to the command
    name and `metadata,` to the word. A token that strips to nothing keeps its
    raw form instead, because `.` is `deptry .`'s argument rather than
    punctuation, and dropping it would let that completion fold into the argv
    unnoticed - which is the one thing this tokenizer exists to prevent.
    """
    out = []
    for raw in text.split():
        word = raw.strip('`*.,;:()[]!?"')
        word = re.sub(r"`?'s$", "", word).strip("`")
        out.append(word or raw)
    return out


def _is_subsequence(needle: list[str], haystack: list[str]) -> bool:
    """Whether every token of `needle` occurs in `haystack`, in order.

    In order but not adjacent, because a record writes a placeholder where the
    caller supplies a value: `pytest --cov=<pkg> --cov-branch` prescribes the
    command whose transcription drops `--cov=<pkg>` from the middle, and a
    contiguity test would fail on a correct entry.
    """
    remaining = iter(haystack)
    return all(any(token == word for word in remaining) for token in needle)


def test_every_python_tool_in_the_family_is_invoked():
    assert {i.tool for i in INVOCATIONS} == tools_named_in_records()


def test_no_check_invokes_the_same_tool_twice():
    pairs = [(i.check, i.tool) for i in INVOCATIONS]
    assert len(pairs) == len(set(pairs))


def test_a_tool_answering_several_checks_is_invoked_once_per_check():
    """The whole set, not a subset of it.

    A superset assertion passes on a table that has quietly grown a ruff entry
    for a check whose record never offered ruff, which is the mistranscription
    the per-check split exists to make visible.
    """
    assert {i.check for i in INVOCATIONS if i.tool == "ruff"} == {
        "arch/complexity",
        "arch/complexity-gate",
        "arch/over-abstraction",
        "docs/docstring-coverage",
        "security/crypto",
        "security/dangerous-calls",
        "security/injection",
        "security/unsafe-io",
    }


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


def test_classify_maps_a_nonzero_exit_with_no_findings_to_tool_failed():
    """Named for the rule that holds: the exit code alone decides nothing.

    A non-zero exit from a present tool is `ok` whenever the tool reported
    something, which is what every finding tool in this family does, so a name
    promising that a non-zero exit means `tool-failed` would describe a rule
    this function is written not to have.
    """
    assert classify(2, "", "boom", tool_present=True) == ("no-evidence", "tool-failed")
    assert classify(2, "B602: found", "boom", tool_present=True) == ("ok", "")


def test_classify_maps_clean_output_to_ok():
    assert classify(0, "findings", "", tool_present=True) == ("ok", "")


def test_a_silent_clean_tool_is_ok_rather_than_a_tool_failure():
    """A clean `xenon` and a clean `vulture` exit 0 having printed nothing.

    Reading the empty output alone would turn every one of them into
    `tool-failed`, which manufactures a finding against a record that is right
    and a tool that ran correctly - so the rc-0 half of the rule is what stops
    a silent pass being reported as a defect.
    """
    assert classify(0, "", "", tool_present=True) == ("ok", "")
    assert classify(0, "", "", tool_present=True, findings_stream="stderr") == (
        "ok",
        "",
    )


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

    A length floor alone does not say this, though: a quote silently truncated
    to a mid-sentence fragment stays over any floor and stays unique, so the
    verbatim guard keeps passing while what it compares has stopped being the
    record's prescription. Ending at a sentence boundary is what a truncation
    breaks, so that is what is held.
    """
    for inv in INVOCATIONS:
        assert len(inv.record_quote) >= 40, (inv.check, inv.tool, inv.record_quote)
        assert re.search(r"[.!?)][`*]*$", inv.record_quote), (
            inv.check,
            inv.tool,
            inv.record_quote[-40:],
        )


def test_a_transcribed_command_occurs_in_the_sentence_that_prescribes_it():
    """Otherwise the verbatim guard watches prose the command is not in.

    The guard's whole value is that a record whose prescription changes breaks
    the transcription. Anchored off a sentence that never named the command,
    it breaks only when unrelated prose is reworded, and stays silent through
    exactly the edit it exists to catch.

    Three entries genuinely cannot satisfy this, and each is named rather than
    excused by a loophole in the rule: two because the record writes a
    placeholder or delegates instead of naming a command, one because it
    prescribes running the suite without naming what runs it.
    """
    unanchored = {
        # The record delegates: "Same tools and same precedence as
        # `deps/licenses`", and the delegation is the prescription.
        ("deps/transitive-licenses", "pip-licenses"),
        # The record writes `pip-audit -r <requirements>`; the fixture's own
        # file is what the placeholder resolves to.
        ("deps/vulnerabilities", "pip-audit"),
        # The record prescribes running the suite in randomized order and names
        # the plugin that randomizes it, never the runner that runs it.
        ("test/determinism", "pytest-randomly"),
    }
    seen = set()
    for inv in INVOCATIONS:
        quote = _tokens(inv.record_quote)
        for partition in PARTITIONS:
            argv = inv.prescribed(partition)
            if not argv:
                continue
            anchored = _is_subsequence(_tokens(" ".join(argv)), quote)
            if (inv.check, inv.tool) in unanchored:
                seen.add((inv.check, inv.tool))
            else:
                assert anchored, (inv.check, inv.tool, partition, argv)
            break
    assert seen == unanchored, "an exception nothing exercises is a stale exception"


def test_folding_a_completion_into_the_argv_breaks_the_anchor():
    """The completion is this round's deliverable, so it may not hide in `argv`.

    Folded in, the same command still runs and the results still say a tool
    answered - what changes is the provenance, which stops distinguishing what
    the record prescribed from what had to be added to make it run. Nothing
    about the run looks different, so the guard has to be on the transcription:
    the argv alone traces through the record's sentence and the argv carrying
    its completion does not.
    """
    completed = [i for i in INVOCATIONS if i.completion]
    assert len(completed) == 12, len(completed)
    for inv in completed:
        quote = _tokens(inv.record_quote)
        argv = inv.argv or next(a for _, a in inv.argv_by_partition if a)
        assert _is_subsequence(_tokens(" ".join(argv)), quote), (inv.check, inv.tool)
        assert not _is_subsequence(
            _tokens(" ".join((*argv, *inv.completion))), quote
        ), (inv.check, inv.tool, inv.completion)


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
            commands = [argv_for(inv, partition), *inv.supplied(partition)]
            for command in commands:
                for word in command:
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


def test_a_tool_reporting_on_stderr_is_classified_on_stderr():
    """Measured: `deptry .` on a seeded partition writes nothing to stdout.

    It exits 1 with its whole DEP002/DEP001 report on stderr, so classifying it
    on stdout inverts the grade exactly: a run that finds every planted seed
    reads as `tool-failed`, and a run that finds nothing reads as `ok`.
    """
    report = "DEP002 'six' defined as a dependency but not used\n"
    assert classify(1, "", report, tool_present=True, findings_stream="stderr") == (
        "ok",
        "",
    )
    assert classify(1, "", report, tool_present=True) == ("no-evidence", "tool-failed")
    assert classify(1, "", "", tool_present=True, findings_stream="stderr") == (
        "no-evidence",
        "tool-failed",
    )


def test_deptry_is_the_entry_that_reports_on_stderr():
    """The exact set, so a stream silently moved onto another entry fails here."""
    assert {
        (i.check, i.tool) for i in INVOCATIONS if i.findings_stream == "stderr"
    } == {("deps/hygiene", "deptry")}
    assert all(i.findings_stream in ("stdout", "stderr") for i in INVOCATIONS)
    with pytest.raises(ValueError, match="findings_stream"):
        Invocation(
            check="deps/hygiene",
            tool="deptry",
            record_quote="x" * 40,
            argv=("deptry",),
            findings_stream="both",
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


def test_no_prescribed_command_is_never_classified_as_a_tool_failure(
    tmp_path, monkeypatch
):
    """A record that prescribes a reading pass has not offered a command.

    Reporting that as `tool-failed` would blame a tool for a record that never
    asked it to run, and the run would read as a broken tool rather than as the
    reading pass the record actually prescribes. The name is a claim about how
    such an entry is *classified*, so the classification is what the body has to
    reach: checking only that `argv_for` came back empty leaves the half that
    turns an empty command into a status untested.

    `cosmic-ray` is the case that made it matter. Its record names the tool and
    no subcommand, and run bare it exits non-zero having printed nothing - so
    the row would read as a tool that failed rather than as a record with
    nothing runnable in it.
    """
    reading = [i for i in INVOCATIONS if not i.argv and not i.argv_by_partition]
    assert reading, "some records prescribe a reading pass rather than a command"
    assert ("test/mutation", "cosmic-ray") in {(i.check, i.tool) for i in reading}
    for inv in reading:
        assert argv_for(inv, FULL_PARTITION) == ()
        assert inv.supplied(FULL_PARTITION) == ()

    source = tmp_path / "fixture" / FULL_PARTITION
    source.mkdir(parents=True)
    recorded = []
    monkeypatch.setattr("run_python_fixture_lens._run", _fake_run(recorded))
    observed = run_partition(
        FULL_PARTITION, source, tmp_path / "work", "none", timeout=5
    )
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}
    for inv in reading:
        row = rows[(inv.check, inv.tool)]
        assert row["ran"] is False, inv.check
        assert (row["status"], row["reason"]) == ("", ""), inv.check
        assert row["reason"] not in REASONS, inv.check
        assert "prescribes no command" in row["why"], inv.check
    assert not any(command == ["uvx", "cosmic-ray"] for command in recorded)


# --- how a command is obtained and where it runs -------------------------------


def test_every_invoked_tool_resolves_to_a_package_that_can_be_fetched():
    """Non-emptiness is not resolvability, and the difference is a silent one.

    The whole map is pinned because an entry is only ever here to correct a
    name a runner would otherwise resolve wrongly - `coverage.py` to the
    distribution published as `coverage`, `cyclonedx-py` to `cyclonedx-bom` -
    and a resolution that goes wrong produces a tool that runs and reports
    nothing rather than an error. Dropping an entry restores exactly that.
    """
    assert TOOL_PACKAGES == {
        "coverage.py": ("coverage", "pytest"),
        "cyclonedx-py": ("cyclonedx-bom",),
        "mutmut": ("mutmut", "pytest"),
    }
    for inv in INVOCATIONS:
        if argv_for(inv, FULL_PARTITION):
            packages = packages_for(inv.tool)
            assert packages and all(packages), inv.tool
    assert launcher(
        next(i for i in INVOCATIONS if i.tool == "cyclonedx-py"), "pip", granted=False
    ) == ("uvx", "--from", "cyclonedx-bom")


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
    """Pinned whole, because a route is wrong by what it omits.

    The seeded package is src-layout, so every route installs the project and
    not only its dependencies: without that step `import fixture_app` raises
    `ModuleNotFoundError` and every route that runs the suite dies, which reads
    as a broken fixture rather than an incomplete install. Dropping the step
    leaves a route that still runs, still succeeds, and still looks like a
    route - so nothing short of the whole mapping holds it.
    """
    assert MATERIALIZE == {
        "uv": (("uv", "sync"),),
        "pip": (
            ("python", "-m", "venv", ".venv"),
            (".venv/bin/pip", "install", "-r", "requirements.txt"),
            (".venv/bin/pip", "install", "-e", ".", "--no-deps"),
        ),
        "poetry": (("poetry", "install"),),
        "pipenv": (
            ("pipenv", "install"),
            ("pipenv", "run", "pip", "install", "-e", ".", "--no-deps"),
        ),
        "pylock": (
            ("uv", "venv", ".venv"),
            ("uv", "pip", "install", "-r", "pylock.toml"),
            ("uv", "pip", "install", "-e", ".", "--no-deps"),
        ),
    }
    assert set(MATERIALIZE) == set(PARTITIONS)


def test_every_materialization_route_ends_by_installing_the_project_itself():
    """Stated as the property rather than left to the pin above to imply.

    `uv sync` and `poetry install` install the project from its own manifest;
    the other three end in an editable install of it. A route that installed
    only dependencies would leave the package unimportable on a partition whose
    checks run its suite.
    """
    for partition, commands in MATERIALIZE.items():
        last = commands[-1]
        assert last[-1] in ("--no-deps", "sync", "install"), (partition, last)
        if last[-1] == "--no-deps":
            assert "-e" in last and "." in last, (partition, last)


def _entry(check: str, tool: str) -> Invocation:
    return next(i for i in INVOCATIONS if (i.check, i.tool) == (check, tool))


def test_a_partition_the_record_prescribes_no_route_for_runs_nothing():
    """`pip-audit` has no mode for a uv, poetry or pipenv tree, and that is the finding.

    Filling one in - a bare `pip-audit` from inside the environment - is the
    repair the transcription exists to make visible, so the entry names those
    partitions with an empty command instead.

    The whole mapping is pinned, and every partition is named in it, because
    both ways of losing a route look like the record having none: emptying a
    row says the record prescribes nothing where it prescribes something, and
    dropping a partition out of the table says the same by omission. The
    per-partition routing *is* this entry's finding, so there is nothing left
    to catch either.
    """
    inv = _entry("deps/vulnerabilities", "pip-audit")
    assert inv.argv_by_partition == (
        ("uv", ()),
        ("pip", ("pip-audit", "-r", "requirements.txt")),
        ("poetry", ()),
        ("pipenv", ()),
        ("pylock", ("pip-audit", "--locked", ".")),
    )
    assert {p for p, _ in inv.argv_by_partition} == set(PARTITIONS)
    assert argv_for(inv, "uv") == ()
    assert argv_for(inv, "pylock") == ("pip-audit", "--locked", ".")


def test_the_sbom_route_is_the_partitions_own_dependency_file_in_every_case():
    """The subcommand is the finding here, so repointing one has to fail.

    The record prescribes "the subcommand matching the partition's own
    dependency file", which makes each row a separate claim about that record -
    and a row pointed at the wrong subcommand still runs a real tool and still
    produces a document, so nothing downstream distinguishes it.
    """
    inv = _entry("deps/inventory", "cyclonedx-py")
    assert inv.argv_by_partition == (
        ("uv", ()),
        ("pip", ("cyclonedx-py", "requirements")),
        ("poetry", ("cyclonedx-py", "poetry")),
        ("pipenv", ("cyclonedx-py", "pipenv")),
        ("pylock", ()),
    )
    assert {p for p, _ in inv.argv_by_partition} == set(PARTITIONS)


# --- routes this round supplied rather than transcribed ------------------------


def test_a_supplied_route_is_exactly_the_two_named_holes():
    """Pinned whole, because the mechanism's value is that it stays small.

    A supplied route is the audit's own answer to a hole the record leaves, and
    the rule that nothing corrects a record survives only while every one of
    them is visible as supplied rather than prescribed. A fourth appearing
    unnoticed is a correction made by the harness.
    """
    supplied = {
        (i.check, i.tool, p): steps
        for i in INVOCATIONS
        for p, steps in i.supplied_by_partition
    }
    assert supplied == {
        ("deps/inventory", "cyclonedx-py", "uv"): (
            ("uv", "export", "--format", "cyclonedx1.5", "--frozen"),
        ),
        ("deps/inventory", "cyclonedx-py", "pylock"): (
            ("uvx", "cyclonedx-py", "requirements", "pylock.toml"),
        ),
        ("deps/vulnerabilities", "pip-audit", "uv"): (
            (
                "uv",
                "export",
                "--frozen",
                "--format",
                "requirements.txt",
                "-o",
                SUPPLIED_REQUIREMENTS,
            ),
            ("uvx", "pip-audit", "-r", SUPPLIED_REQUIREMENTS),
        ),
    }


def test_a_supplied_partition_is_never_one_the_record_prescribes_a_route_for():
    """The two are alternatives, so a partition carrying both says neither.

    `record_argv` stays empty on a supplied row, which is what makes the
    results readable: an empty prescribed command beside a populated supplied
    one says the record had no route and this round proposed one.
    """
    for inv in INVOCATIONS:
        for partition, steps in inv.supplied_by_partition:
            assert steps, (inv.check, partition)
            assert inv.prescribed(partition) == (), (inv.check, partition)
            assert argv_for(inv, partition) == (), (inv.check, partition)
            assert inv.supplied_note, (inv.check, inv.tool)


def test_a_supplied_route_refuses_to_travel_without_its_reason():
    with pytest.raises(ValueError, match="supplied route needs a note"):
        Invocation(
            check="deps/inventory",
            tool="cyclonedx-py",
            record_quote="x" * 40,
            supplied_by_partition=(("uv", (("uv", "export"),)),),
        )
    with pytest.raises(ValueError, match="both a prescribed route and a supplied"):
        Invocation(
            check="deps/inventory",
            tool="cyclonedx-py",
            record_quote="x" * 40,
            argv_by_partition=(("uv", ("cyclonedx-py", "requirements")),),
            supplied_by_partition=(("uv", (("uv", "export"),)),),
            supplied_note="why",
        )
    with pytest.raises(ValueError, match="twice in supplied_by_partition"):
        Invocation(
            check="deps/inventory",
            tool="cyclonedx-py",
            record_quote="x" * 40,
            supplied_by_partition=(("uv", (("a",),)), ("uv", (("b",),))),
            supplied_note="why",
        )
    with pytest.raises(ValueError, match="no launcher prefix"):
        Invocation(
            check="deps/hygiene",
            tool="deptry",
            record_quote="x" * 40,
            in_env=True,
            supplied_by_partition=(("uv", (("deptry", "."),)),),
            supplied_note="why",
        )


def test_a_supplied_route_never_renders_as_the_records_own_command(
    tmp_path, monkeypatch
):
    """The provenance is the deliverable, so the results row has to keep it.

    Emitting the supplied steps as `record_argv` would run the same commands
    and report a candidate answer as something the record already prescribed -
    which is the one claim this round is not allowed to make.
    """
    source = tmp_path / "fixture" / "uv"
    source.mkdir(parents=True)
    recorded = []
    monkeypatch.setattr("run_python_fixture_lens._run", _fake_run(recorded))
    observed = run_partition(
        "uv", source, tmp_path / "work", "target-execution", timeout=5
    )
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}

    sbom = rows[("deps/inventory", "cyclonedx-py")]
    assert sbom["record_argv"] == []
    assert sbom["supplied"] == [
        ["uv", "export", "--format", "cyclonedx1.5", "--frozen"]
    ]
    assert "prescribes" in sbom["supplied_note"] or sbom["supplied_note"]
    assert sbom["ran"] is True
    assert sbom["status"] == "ok"

    audit = rows[("deps/vulnerabilities", "pip-audit")]
    assert audit["record_argv"] == []
    assert [step["command"] for step in audit["steps"]] == [
        [
            "uv",
            "export",
            "--frozen",
            "--format",
            "requirements.txt",
            "-o",
            SUPPLIED_REQUIREMENTS,
        ],
        ["uvx", "pip-audit", "-r", SUPPLIED_REQUIREMENTS],
    ]


def test_a_supplied_route_stops_at_the_step_that_failed(tmp_path, monkeypatch):
    """A failed export is never followed by an audit of the file it did not write."""
    source = tmp_path / "fixture" / "uv"
    source.mkdir(parents=True)
    recorded = []
    monkeypatch.setattr(
        "run_python_fixture_lens._run",
        _fake_run(
            recorded,
            respond=lambda command: (
                _outcome(returncode=2, stdout="")
                if command[:2] == ["uv", "export"] and "--frozen" in command
                else None
            ),
        ),
    )
    observed = run_partition(
        "uv", source, tmp_path / "work", "target-execution", timeout=5
    )
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}
    audit = rows[("deps/vulnerabilities", "pip-audit")]
    assert len(audit["steps"]) == 1
    assert (audit["status"], audit["reason"]) == ("no-evidence", "tool-failed")
    assert not any(command[:2] == ["uvx", "pip-audit"] for command in recorded)


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
    (source / "pyproject.toml").write_text("[project]\n")
    with pytest.raises(ValueError, match="read-only invariant"):
        reconstruct("uv", source, source / "work")

    # The destructive step is `rmtree` on `work_root / partition`, not on
    # `work_root`, so a work directory that is the fixture *root* passes the
    # guard above and then deletes the seeded partition it was about to copy.
    # `--work-dir fixtures/python` is the obvious choice and is exactly this.
    with pytest.raises(ValueError, match="land on the fixture itself"):
        reconstruct("uv", source, source.parent)
    assert (source / "pyproject.toml").exists()


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


def test_the_handbooks_own_bin_directory_is_off_the_subprocess_path(monkeypatch):
    """It carries a `pytest` and a `ruff`, and `uv run` puts it first.

    Left there, a partition whose provisioning failed still resolves a bare
    `pytest` or `ruff` - from this repository's environment, against a copy of
    somebody else's tree - and answers about the wrong project while looking
    like a clean run. The launchers are installed elsewhere, so dropping this
    one directory leaves them findable.
    """
    own_bin = str(REPO_ROOT / ".venv" / "bin")
    monkeypatch.setenv(
        "PATH", os.pathsep.join([own_bin, "/usr/local/bin", own_bin + "/", "/usr/bin"])
    )
    path = _fixture_env()["PATH"].split(os.pathsep)
    assert own_bin not in path
    assert not any(os.path.normpath(entry) == own_bin for entry in path)
    assert path == ["/usr/local/bin", "/usr/bin"]


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


def _outcome(returncode=0, stdout="output", stderr="", tool_present=True):
    return {
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "tool_present": tool_present,
    }


def _fake_run(recorded, respond=None, launches=None):
    """A stand-in for `_run` that answers cleanly unless `respond` says otherwise.

    Args:
        recorded: Gets each command, as a list.
        respond: Called with the command; return an outcome to override the
            clean default, or `None` to take it.
        launches: Gets `(command, bin_dir)` for each call, for the tests about
            where a partition finds its tools.
    """

    def run(command, cwd, timeout, bin_dir=None):
        recorded.append(list(command))
        if launches is not None:
            launches.append((tuple(command), bin_dir))
        if respond is not None:
            override = respond(list(command))
            if override is not None:
                return override
        return _outcome()

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


def test_an_unknown_grant_is_rejected_by_name(tmp_path, monkeypatch):
    """`_run` is stubbed even though the guard is meant to raise before it.

    Without the stub this test's safety depends on the very refusal it is
    testing: remove the refusal and it stops being a unit test and starts
    running `uv sync` against a real tree over the network, which is slow, is
    not what a unit test may do, and hides the regression behind a pass.
    """
    source = tmp_path / "fixture" / "uv"
    source.mkdir(parents=True)
    recorded = []
    monkeypatch.setattr("run_python_fixture_lens._run", _fake_run(recorded))
    with pytest.raises(ValueError, match="sudo"):
        run_partition("uv", source, tmp_path / "work", "sudo", timeout=5)
    assert recorded == []


# --- what a failed materialization does to the rows that needed it -------------


def test_a_failed_materialization_stops_the_rest_of_the_route(tmp_path, monkeypatch):
    """The remaining steps are written against a tree the first one did not build.

    `pip install -r requirements.txt` into a virtualenv `python -m venv` failed
    to create does not install anything; it fails differently, and the second
    failure is the one that gets recorded.
    """
    source = tmp_path / "fixture" / "pip"
    source.mkdir(parents=True)
    recorded = []
    monkeypatch.setattr(
        "run_python_fixture_lens._run",
        _fake_run(
            recorded,
            respond=lambda command: (
                _outcome(returncode=1, stdout="", stderr="no python")
                if command[:2] == ["python", "-m"]
                else None
            ),
        ),
    )
    observed = run_partition(
        "pip", source, tmp_path / "work", "target-execution", timeout=5
    )
    assert [m["command"] for m in observed["materialization"]] == [
        ["python", "-m", "venv", ".venv"]
    ]
    assert not any(command[:1] == [".venv/bin/pip"] for command in recorded)


def test_a_row_needing_the_tree_says_the_materialization_failed_rather_than_running(
    tmp_path, monkeypatch
):
    """Otherwise each dependent row invents a finding of its own.

    Run against a copy nothing resolved, one such row exits non-zero with
    nothing to say and grades `tool-failed`, the next prints a usage banner and
    grades `ok`, and the file that comes out names no common cause - so a later
    pass reads a spread of tool defects where there was one failed install.
    Every row is stamped with the command that stopped, and none of them runs.
    """
    source = tmp_path / "fixture" / "pip"
    source.mkdir(parents=True)
    recorded = []
    monkeypatch.setattr(
        "run_python_fixture_lens._run",
        _fake_run(
            recorded,
            respond=lambda command: (
                _outcome(returncode=1, stderr="no python")
                if command[:2] == ["python", "-m"]
                else None
            ),
        ),
    )
    observed = run_partition(
        "pip", source, tmp_path / "work", "target-execution", timeout=5
    )
    dependent = [
        r
        for r in observed["results"]
        if (r["needs"] or r["in_env"]) and r["record_argv"]
    ]
    assert dependent, "the pip partition carries rows that need the tree"
    for row in dependent:
        assert row["ran"] is False, row["check"]
        assert (row["status"], row["reason"]) == ("no-evidence", "tool-unavailable")
        assert row["detail"] == "environment-unmaterialized"
        assert row["blocked_by"] == ["python", "-m", "venv", ".venv"]
        assert "python -m venv .venv" in row["why"]
    assert not any("deptry" in command for command in recorded)


def test_a_row_that_needs_nothing_still_runs_after_a_failed_materialization(
    tmp_path, monkeypatch
):
    """Refusing the whole granted run would cost the rows that never needed it.

    bandit and ruff answer from a read-only clone, so a failed install says
    nothing about them; blanking them would trade one invented finding for a
    page of `no-evidence` on checks that could have been answered.
    """
    source = tmp_path / "fixture" / "uv"
    source.mkdir(parents=True)
    monkeypatch.setattr(
        "run_python_fixture_lens._run",
        _fake_run(
            [],
            respond=lambda command: (
                _outcome(returncode=1, stderr="lock conflict")
                if command == ["uv", "sync"]
                else None
            ),
        ),
    )
    observed = run_partition(
        "uv", source, tmp_path / "work", "target-execution", timeout=5
    )
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}
    assert rows[("security/crypto", "bandit")]["ran"] is True
    assert rows[("security/crypto", "bandit")]["status"] == "ok"
    assert rows[("deps/hygiene", "deptry")]["ran"] is False
    # `pydeps` carries a tier and launches through `uvx` rather than in the
    # environment, so gating on `in_env` alone would have let it run.
    assert rows[("arch/cycles", "pydeps")]["in_env"] is False
    assert rows[("arch/cycles", "pydeps")]["needs"] == "resolved-tree"
    assert rows[("arch/cycles", "pydeps")]["detail"] == "environment-unmaterialized"


# --- the parts of a route that the verdict has to reach ------------------------


def test_a_route_whose_reporting_half_fails_is_not_a_clean_run(tmp_path, monkeypatch):
    """`coverage run` measures and `coverage report` prints; one route, two commands.

    Classifying on the first alone grades a route whose report died as `ok`
    with no coverage table behind it - a check that answered nothing, recorded
    as a check that answered.
    """
    source = tmp_path / "fixture" / "uv"
    source.mkdir(parents=True)
    monkeypatch.setattr(
        "run_python_fixture_lens._run",
        _fake_run(
            [],
            respond=lambda command: (
                _outcome(returncode=1, stdout="", stderr="no data")
                if command[-2:] == ["report", "--show-missing"]
                else None
            ),
        ),
    )
    observed = run_partition(
        "uv", source, tmp_path / "work", "target-execution", timeout=5
    )
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}
    row = rows[("test/coverage-reach", "coverage.py")]
    assert row["then"]["returncode"] == 1
    assert (row["status"], row["reason"]) == ("no-evidence", "tool-failed")


def test_a_hung_command_is_a_failure_and_says_it_was_a_timeout(tmp_path, monkeypatch):
    """A timeout exits nowhere, and `None` is not zero.

    Mapping that missing exit status to 0 reads every hung command as a clean
    run, which is the worst direction for it to fail in: the slowest tools here
    are the ones a timeout actually catches. `tool-failed` is what the engine
    has for it, and the detail is what tells it apart from a tool that ran and
    broke - the two need different responses and the reason cannot say which.
    """
    source = tmp_path / "fixture" / "uv"
    source.mkdir(parents=True)
    monkeypatch.setattr(
        "run_python_fixture_lens._run",
        _fake_run(
            [],
            respond=lambda command: (
                {
                    "returncode": None,
                    "stdout": "",
                    "stderr": "TimeoutExpired: ...",
                    "tool_present": True,
                }
                if "bandit" in command
                else None
            ),
        ),
    )
    observed = run_partition("uv", source, tmp_path / "work", "none", timeout=5)
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}
    row = rows[("security/crypto", "bandit")]
    assert (row["status"], row["reason"]) == ("no-evidence", "tool-failed")
    assert row["detail"] == "timed-out"
    assert row["detail"] in DETAILS
    # A missing binary is also `returncode: None` and is a different fact.
    assert rows[("security/crypto", "ruff")].get("detail", "") == ""


def test_a_launcher_that_cannot_fetch_the_tool_reports_it_as_unavailable(
    tmp_path, monkeypatch
):
    """Measured: `uvx no-such-package-45xyzq` exits 1 saying the registry has none.

    `_run` sees `FileNotFoundError` only where the command *is* the tool, and
    `uvx`, `poetry run` and `pipenv run` always exist - so on three of the five
    partitions a tool nobody could fetch came back as a tool that ran and
    failed, and `tool-unavailable` was unreachable.
    """
    assert launcher_missed(
        ("uvx", "nope"), 1, "error: `nope` was not found in the package registry"
    )
    assert launcher_missed(("poetry", "run", "nope"), 1, "Command not found: nope")
    assert launcher_missed(
        ("pipenv", "run", "nope"), 1, "the command could not be found within PATH"
    )
    assert not launcher_missed(("uvx", "bandit"), 1, "B602 found")
    assert not launcher_missed(("uvx", "nope"), 0, "not found in the package registry")
    assert not launcher_missed(("bandit",), 1, "not found in the package registry")

    source = tmp_path / "fixture" / "uv"
    source.mkdir(parents=True)
    monkeypatch.setattr(
        "run_python_fixture_lens._run",
        _fake_run(
            [],
            respond=lambda command: (
                _outcome(
                    returncode=1,
                    stdout="",
                    stderr="error: `semgrep` was not found in the package registry",
                )
                if "semgrep" in command
                else None
            ),
        ),
    )
    observed = run_partition("uv", source, tmp_path / "work", "none", timeout=5)
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}
    assert rows[("security/crypto", "semgrep")]["reason"] == "tool-unavailable"


# --- what a results row says about where its command came from -----------------


def test_a_completed_row_reports_the_record_and_the_command_as_two_things(
    tmp_path, monkeypatch
):
    """The completion is the round's output, so the row cannot flatten it.

    Two ways of losing it leave every other assertion here intact: emitting the
    record's own argv as the command that ran, and dropping the note. The first
    reports a repaired command as a clean transcription; the second leaves the
    repair with nothing saying why it was needed.
    """
    source = tmp_path / "fixture" / "uv"
    source.mkdir(parents=True)
    monkeypatch.setattr("run_python_fixture_lens._run", _fake_run([]))
    observed = run_partition("uv", source, tmp_path / "work", "none", timeout=5)
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}

    completed = [
        r for r in observed["results"] if r["completion"] and r.get("ran") is True
    ]
    assert completed, "the ungranted run reaches entries carrying a completion"
    for row in completed:
        assert row["note"], row["check"]
        assert row["record_argv"] != row["command"], row["check"]
        assert row["command"][-len(row["completion"]) :] == row["completion"], row[
            "check"
        ]

    bandit = rows[("security/crypto", "bandit")]
    assert bandit["record_argv"] == ["bandit", "-r"]
    assert bandit["command"] == ["uvx", "bandit", "-r", f"src/{PACKAGE}"]
    assert bandit["completion"] == [f"src/{PACKAGE}"]
    assert "placeholder" in bandit["note"]


def test_the_venv_partitions_find_their_tools_on_the_copys_own_path(
    tmp_path, monkeypatch
):
    """`pip` and `pylock` are the two partitions with no launcher words at all.

    They run a bare command name and rely on the copy's `.venv/bin` being put
    in front of `PATH`, which is wiring nothing exercises if `run_partition` is
    only ever driven with `uv` and `poetry` - the two partitions that never
    take that branch.
    """
    for partition in ("pip", "pylock"):
        source = tmp_path / "fixture" / partition
        source.mkdir(parents=True)
        launches = []
        monkeypatch.setattr(
            "run_python_fixture_lens._run", _fake_run([], launches=launches)
        )
        work = tmp_path / f"work-{partition}"
        observed = run_partition(partition, source, work, "target-execution", timeout=5)
        rows = {(r["check"], r["tool"]): r for r in observed["results"]}
        deptry = rows[("deps/hygiene", "deptry")]
        assert deptry["command"] == ["deptry", "."], partition
        assert deptry["status"] == "ok", partition
        bin_dirs = {
            bin_dir for command, bin_dir in launches if command == ("deptry", ".")
        }
        assert bin_dirs == {work / partition / VENV_BIN}, partition
        assert (".venv/bin/pip", "install", "deptry") in [c for c, _ in launches], (
            partition
        )


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


def test_every_vocabulary_is_pinned_rather_than_merely_non_empty():
    """A membership test passes on a scale that has grown a fourth member.

    `audit-core` fixes both scales - three statuses, and "the three ways a check
    can fail to run" - so a fourth member of either is a value the pass that
    grades this file has no row for, and it arrives silently: every existing
    row still classifies into the vocabulary it always did.
    """
    assert STATUSES == ("ok", "no-evidence", "not-applicable")
    assert REASONS == ("not-permitted", "tool-unavailable", "tool-failed")
    assert DETAILS == ("timed-out", "environment-unmaterialized")


def test_not_applicable_is_in_the_scale_and_is_never_what_classify_returns():
    """It is the engine's, and it is settled before an observation exists.

    `not-applicable` means the check has no lens in the partition's languages,
    which the record answers rather than a run - so the status belongs in the
    scale the results are read against and can never be the outcome of running
    something. Holding it here stops a later reader taking its absence from the
    outputs as a gap to fill.
    """
    observations = [
        (0, "", "", True, True),
        (1, "out", "", True, True),
        (2, "", "err", True, True),
        (127, "", "not found", False, True),
        (0, "out", "", True, False),
    ]
    returned = {
        classify(code, out, err, tool_present=present, permitted=permitted)[0]
        for code, out, err, present, permitted in observations
    }
    assert "not-applicable" in STATUSES
    assert "not-applicable" not in returned
