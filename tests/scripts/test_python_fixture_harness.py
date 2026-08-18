"""Tests for scripts/run_python_fixture_lens.py (#45).

The harness holds each check record's prescribed invocation verbatim, so the
tests here are mostly guards on that transcription rather than on behaviour: an
invocation that had to be edited to run is the finding the round exists to
produce, and it only shows up as one if the transcription is held to the record.
"""

import json
import os
import re
from pathlib import Path

import pytest
from audit_checks import SKILLS_DIR, load_checks
from build_python_fixtures import PINNED_MANAGERS
from python_fixture_spec import (
    DEPS_CHECKS,
    EXPECTATIONS,
    FULL_PARTITION,
    PACKAGE,
    PARTITIONS,
    expectations_for,
    render_manifests,
)
from run_python_fixture_lens import (
    DETAILS,
    DISPOSITIONS,
    FROZEN_FORM,
    GRANTS,
    INVOCATIONS,
    MATERIALIZE,
    NO_VERSION_ROUTE,
    NONZERO_EXIT_KINDS,
    NONZERO_EXIT_MEANING,
    REASONS,
    REPO_ROOT,
    STATUSES,
    SUPPLIED_REQUIREMENTS,
    TOOL_PACKAGES,
    VENV_BIN,
    VERSION_PROBE,
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
    nonzero_exit_meaning,
    packages_for,
    probe_versions,
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


def _marked(wanted: str) -> bool:
    """Whether `_concrete` left this token a prefix for the caller to complete.

    One place decides what the mark is, because two readers have to agree on it:
    `_matches` treats a marked token as a prefix, and the coverage property holds
    order among the unmarked tokens and presence for the marked ones. A
    disagreement about which is which would move a token quietly from one rule to
    the other.
    """
    return wanted.endswith("<")


def _matches(wanted: str, token: str) -> bool:
    """Whether one command token satisfies one token the record wrote.

    Equality, except for a token `_concrete` reduced to the part before a
    placeholder and left a trailing `<` on as the mark: `--cov=<` is satisfied by
    any token beginning `--cov=` that carries something after it, which is what
    the caller supplied. The mark is what keeps this from being a blanket prefix
    test - `-r` would otherwise be satisfied by `-rf`, and an exact token must
    stay exact.

    A record's own tokens never end in `<`, because the placeholder it writes
    closes with `>`, so the older guards passing raw tokens through
    `_is_subsequence` still compare by equality.
    """
    if _marked(wanted):
        prefix = wanted[:-1]
        return token.startswith(prefix) and len(token) > len(prefix)
    return token == wanted


def _is_subsequence(needle: list[str], haystack: list[str]) -> bool:
    """Whether every token of `needle` occurs in `haystack`, in order.

    In order but not adjacent, because a record writes a placeholder where the
    caller supplies a value: `pytest --cov=<pkg> --cov-branch` prescribes the
    command whose transcription drops `--cov=<pkg>` from the middle, and a
    contiguity test would fail on a correct entry.

    Token equality goes through `_matches` rather than `==`, but every caller
    passes unmarked tokens, so today that reduces to `==` on every comparison this
    makes. The anchor guards pass `_tokens` output, and a record's own tokens close
    a placeholder with `>` rather than the `<` that marks a truncation; the
    coverage property passes the tokens it has already filtered to the unmarked
    ones, holding order there and presence separately for the marked ones. Calling
    `_matches` is what keeps a marked needle behaving as a prefix if a caller ever
    hands one over, rather than silently demanding the mark be matched literally.
    """
    remaining = iter(haystack)
    return all(any(_matches(token, word) for word in remaining) for token in needle)


def _spans(paragraph: str) -> list[str]:
    """Every backtick span in the paragraph, in order, duplicates collapsed.

    Collapsed because a record naming the same command twice prescribes it once,
    and every reader of this is a set membership or an equality against a
    declaration that carries each form once. Kept in order because a reader of the
    list wants the paragraph's own sequence when a failure names a span.
    """
    return list(dict.fromkeys(re.findall(r"`([^`]+)`", paragraph)))


def _command_forms(paragraph: str, lead: str) -> set[str]:
    """The command forms the paragraph prescribes under one lead word.

    A span whose first token is that word and which carries at least one
    argument. A span that is only the bare word is a mention: a record names a
    bare command in order to warn against it, and treating that as a
    prescription would demand a declaration for the command it forbids.

    The lead word is a tool's name for most entries, and a runner's wherever the
    record prescribes a command led by something other than the tool being
    checked - which is what `_lead_words` supplies, one call per word. Held to one
    word either way: a rule matching the name anywhere in the span would
    attribute a neighbour's command to the wrong entry.
    """
    return {
        span
        for span in _spans(paragraph)
        if len(span.split()) > 1 and span.split()[0] == lead
    }


def _lead_words(inv: Invocation) -> set[str]:
    """The words a form for this entry may lead with.

    The tool's name is the obvious one and it is not enough: a record names the
    command it wants run, and that command's first word is often a runner rather
    than the tool being checked - `pytest --randomly-seed=<n>` for
    `pytest-randomly`, `coverage run -m pytest` for `coverage.py`. Keyed on the
    tool's name alone, the extractor returns nothing for those and an empty
    declaration then passes as though the record prescribed nothing at all.
    Keyed on the argv's own first token, it stays anchored to one word, so it
    still cannot pull a neighbour's command in: `deps/freshness` prescribes both
    `uv pip list --outdated` and `pip list --outdated`, and the `pip` entry's
    argv leads with `pip`.
    """
    argvs = [a for a in [inv.argv, *(a for _, a in inv.argv_by_partition)] if a]
    return {a[0] for a in argvs} | {inv.tool}


def _flag_spans(paragraph: str) -> set[str]:
    """Every span the paragraph writes as a bare flag.

    Pooled across the paragraph rather than attributed to a tool, because a
    record prescribing a flag does not repeat the command it belongs to:
    `arch/cycles` writes "Append `--show-dot` to that `pydeps` invocation", and
    a rule keyed on the tool's name would miss the very drift this guards.
    """
    return {span for span in _spans(paragraph) if span.startswith("-")}


def _concrete(tokens: list[str]) -> list[str]:
    """A record's tokens reduced to the part a command can carry.

    A record writes `<requirements>` where the caller supplies a path, so the
    placeholder can never occur in a command and the token goes. Dropping it is
    what lets the coverage property watch the entry whose placeholder forced the
    anchor guard to be switched off for it.

    Where the placeholder is glued to a flag the token is *truncated* rather than
    dropped, keeping the `<` as the mark `_matches` reads: `--cov=<pkg>` becomes
    `--cov=<`, which the seeded `--cov=fixture_pkg` satisfies. Dropping the whole
    token instead reopens the drift this file exists to catch - a paragraph that
    grows `--cov-config=<file>` would reduce to nothing at all, `all([])` is
    vacuously true, and a newly prescribed flag nothing transcribes would pass
    the flag property in silence. It also degrades the coverage property to a
    check on the lead word alone, since `pytest --randomly-seed=<n>` would reduce
    to `pytest` and be satisfied by an argv running the suite bare.
    """
    out = []
    for token in tokens:
        if "<" not in token:
            out.append(token)
            continue
        head = token.split("<", 1)[0]
        if head:
            out.append(head + "<")
    return out


def _prescribing_paragraph(check: str, quote: str) -> str:
    """The source line the record's prescribing sentence sits in.

    Markdown here is never hard-wrapped, so one paragraph is one line and the
    quote's line is the whole prescribing paragraph. Anchoring on the quote
    rather than on the `**Python**` review-lens line is what covers the records
    carrying a python: entry and no such line at all.
    """
    lines = [
        line for line in _record_path(check).read_text().splitlines() if quote in line
    ]
    if len(lines) != 1:
        raise AssertionError(
            f"{check}: its quote occurs in {len(lines)} source lines, so which "
            "paragraph prescribes it is not decidable"
        )
    return lines[0]


def _fallback_paragraphs(check: str) -> list[tuple[str, str]]:
    """Every paragraph of the record's `## Tooling fallback`, with its lens label.

    The label is what makes a paragraph this lens's business: records prefix each
    review lens with `**<Label>** - `, so a span under another language's label is
    that lens's prescription and not a correction this one lost. The label is the
    empty string where the paragraph carries none, which is the case the
    containment property must still watch - `arch/complexity-gate` prescribes
    inside an unlabelled bolded directive.

    A record with no such section raises rather than returning nothing: the
    containment property would then watch no paragraph on it and report the same
    silence as a record whose every paragraph is clean.
    """
    lines = _record_path(check).read_text().splitlines()
    start = next(
        (n for n, line in enumerate(lines) if line.startswith("## Tooling fallback")),
        None,
    )
    if start is None:
        raise AssertionError(
            f"{check}: has no `## Tooling fallback` section, so a prescription "
            "growing outside the quoted paragraph has nowhere this can see it"
        )
    end = next(
        (n for n in range(start + 1, len(lines)) if lines[n].startswith("## ")),
        len(lines),
    )
    out = []
    for line in lines[start + 1 : end]:
        if not line.strip():
            continue
        label = re.match(r"\*\*([^*]+)\*\* - ", line.strip())
        out.append((label.group(1) if label else "", line))
    return out


# --- the extractor helpers ----------------------------------------------------


def test_a_span_that_is_only_the_tool_name_is_a_mention_not_a_form():
    """A record names a bare command in order to forbid it.

    `deps/vulnerabilities` writes "Run `pip-audit` with no arguments and it
    audits whatever environment it was launched from ... so don't". Reading that
    as a prescription would demand a declaration for the one command the record
    tells the reader not to run.
    """
    paragraph = (
        "Run `pip-audit` with no arguments, so don't. Use `pip-audit --locked .`."
    )
    assert _command_forms(paragraph, "pip-audit") == {"pip-audit --locked ."}


def test_a_form_is_recognised_only_for_the_tool_that_leads_it():
    paragraph = "`uv export --frozen` writes the set that `pip-audit -r <file>` reads."
    assert _command_forms(paragraph, "pip-audit") == {"pip-audit -r <file>"}
    assert _command_forms(paragraph, "uv") == {"uv export --frozen"}


def test_flag_spans_are_pooled_across_the_paragraph():
    """A record prescribes a flag without repeating the command it belongs to."""
    paragraph = "Append `--show-dot` to that `pydeps` invocation; `pydeps --show-cycles` alone prints nothing."
    assert _flag_spans(paragraph) == {"--show-dot"}


def test_a_placeholder_token_is_dropped_before_matching_an_argv():
    """A record writes what the caller supplies; an argv writes what it supplied.

    This is what lets the coverage property watch `deps/vulnerabilities`, whose
    placeholder had to switch off the anchor guard entirely.
    """
    assert _concrete(_tokens("pip-audit -r <requirements> --no-deps")) == [
        "pip-audit",
        "-r",
        "--no-deps",
    ]


def test_a_placeholder_glued_to_a_flag_keeps_the_flag_as_a_prefix():
    """`--cov=<pkg>` is the same phenomenon, and dropping it goes too far.

    A record writes the value the caller supplies inside the flag, so no command
    can carry that token as written. Left whole, `test/coverage-reach`'s
    prescribed form reads as one the harness does not run. Dropped whole, the
    flag stops being held at all, which is worse: it is the drift shape these
    properties exist to catch.
    """
    assert _concrete(_tokens("pytest --cov=<pkg> --cov-branch")) == [
        "pytest",
        "--cov=<",
        "--cov-branch",
    ]
    assert _concrete(_tokens("pip-audit -r <requirements>")) == ["pip-audit", "-r"]


def test_a_truncated_flag_is_satisfied_by_a_value_and_by_nothing_else():
    """The mark is what makes truncation safe to match on.

    Satisfied by the value the caller supplied, and by neither a longer flag that
    merely starts the same way nor the bare flag with no value - the first is how
    a newly prescribed `--cov-config=<file>` would hide behind `--cov=<pkg>`, and
    the second is a flag whose value never arrived.
    """
    assert _matches("--cov=<", "--cov=fixture_pkg")
    assert not _matches("--cov=<", "--cov=")
    assert not _matches("--cov-config=<", "--cov=fixture_pkg")
    assert not _matches("-r", "-rf")
    assert _matches("-r", "-r")


def test_a_form_led_by_a_runner_is_found_through_the_argvs_own_first_word():
    """The extraction the tool-name rule cannot reach.

    Four entries prescribed a command led by something other than the tool being
    checked and so declared no form at all, which is indistinguishable from a
    record that prescribes nothing.
    """
    inv = _entry("test/determinism", "pytest-randomly")
    assert _lead_words(inv) == {"pytest", "pytest-randomly"}
    paragraph = _prescribing_paragraph(inv.check, inv.record_quote)
    assert _command_forms(paragraph, "pytest-randomly") == set()
    assert _command_forms(paragraph, "pytest") == {"pytest --randomly-seed=<n>"}


def test_a_lead_word_stays_one_word_so_a_neighbours_command_is_not_pulled_in():
    """The reason this is not simply "the tool's name occurs anywhere in the span".

    `deps/freshness` writes `uv pip list --outdated` and `pip list --outdated` in
    one sentence. An anywhere-in-the-span rule would attribute the first to the
    `pip` entry, which would then have to declare a form it never runs; keyed on
    the argv's own first token, that entry leads with `pip` and sees only its
    own.
    """
    inv = _entry("deps/freshness", "pip")
    assert _lead_words(inv) == {"pip"}
    paragraph = _prescribing_paragraph(inv.check, inv.record_quote)
    extracted = set()
    for lead in _lead_words(inv):
        extracted |= _command_forms(paragraph, lead)
    assert all(not form.startswith("uv ") for form in extracted), extracted


def test_the_prescribing_paragraph_is_the_line_holding_the_quote():
    quote = "Run `pydeps --show-cycles --show-dot`: `--show-cycles` alone has no textual output channel at all."
    paragraph = _prescribing_paragraph("arch/cycles", quote)
    assert quote in paragraph
    assert paragraph.count("\n") == 0


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


# --- version routes -------------------------------------------------------------


def test_every_invoked_tool_has_a_version_route_or_a_stated_absence():
    invoked = {inv.tool for inv in INVOCATIONS}
    assert set(VERSION_PROBE) == invoked


def test_a_tool_with_no_version_route_says_so_by_name():
    """`None` is a positive claim, so it travels with a reason - never silently.

    The reverse direction is checked too, mirroring `ungranted_note`'s vacuity
    rule: a name in `NO_VERSION_ROUTE` for a tool that *does* carry a probe would
    be a stale reason nothing reads, which is the same kind of drift a leftover
    `ungranted_note` would be.
    """
    for tool, argv in VERSION_PROBE.items():
        if argv is None:
            assert tool in NO_VERSION_ROUTE, (
                f"{tool} has no version probe and no stated reason"
            )
            assert NO_VERSION_ROUTE[tool].strip()
    no_route = {tool for tool, argv in VERSION_PROBE.items() if argv is None}
    assert set(NO_VERSION_ROUTE) <= no_route, (
        "NO_VERSION_ROUTE names a tool that carries a real probe"
    )


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

    The entries that genuinely cannot satisfy it are named rather than excused
    by a loophole in the rule, and each is here because the record writes a
    placeholder or delegates instead of naming a command - never because the
    record names no command at all, which is a record to correct.
    """
    unanchored = {
        # The record delegates: "Same tools and same precedence as
        # `deps/licenses`", and the delegation is the prescription.
        ("deps/transitive-licenses", "pip-licenses"),
        # The record writes `pip-audit -r <requirements>`; the fixture's own
        # file is what the placeholder resolves to.
        ("deps/vulnerabilities", "pip-audit"),
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
                # Asserted, not merely recorded: an entry that has *become*
                # anchored still counts as exercising its exception, so without
                # this the exception outlives the defect it was written for and
                # removing it depends on somebody noticing.
                assert not anchored, (inv.check, inv.tool, partition, argv)
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

    One direction only, and the other has no guard anywhere. This holds that a
    completion has not been folded into `argv`; nothing holds that a token the
    record does prescribe has not been moved the other way, out of `argv` and into
    `completion`. Moved that way the run stays correct and every property passes:
    the shorter argv still traces through the quote, and the coverage property
    reads `argv_for`, which re-appends the completion before matching. What
    inverts is the published provenance - the round would report that a record
    failed to prescribe a flag the record bolds, and since this round's deliverable
    is the list of records needing correction, that is the output falsified under a
    green suite. Read a `note` claiming a record omitted something as a claim to
    check against the record, not as one this file has verified.
    """
    completed = [i for i in INVOCATIONS if i.completion]
    assert len(completed) == 13, len(completed)
    for inv in completed:
        quote = _tokens(inv.record_quote)
        argv = inv.argv or next(a for _, a in inv.argv_by_partition if a)
        assert _is_subsequence(_tokens(" ".join(argv)), quote), (inv.check, inv.tool)
        assert not _is_subsequence(
            _tokens(" ".join((*argv, *inv.completion))), quote
        ), (inv.check, inv.tool, inv.completion)


def test_an_invocation_names_a_check_that_exists_and_a_partition_that_does():
    """Every field naming a partition, not only the one that maps commands.

    `own_runner` is the one where a typo costs nothing visible: `prescribed`
    falls back to a shared `argv` for any string, so an unknown partition passes
    the field's own validation and then suppresses a prefix for a partition that
    never runs.
    """
    for inv in INVOCATIONS:
        assert _record_path(inv.check).exists(), inv.check
        named = {p for p, _ in inv.argv_by_partition} | set(inv.own_runner)
        assert not named - set(PARTITIONS), (inv.check, sorted(named))


def test_the_placeholder_a_record_writes_never_reaches_a_command():
    """`bandit -r <pkg>` is a shape, not a command.

    A placeholder left in `argv` would be passed to the tool as a literal path
    and fail as though the tool were broken, which is the one failure mode this
    table cannot afford to invent.

    Matched anywhere in the word rather than against the whole of it, because a
    record glues the placeholder to a flag as often as it writes it alone:
    `--cov=<pkg>` handed to pytest names a package called `<pkg>` and fails the
    same way, and a whole-word test never sees it.
    """
    for inv in INVOCATIONS:
        for partition in PARTITIONS:
            commands = [argv_for(inv, partition), *inv.supplied(partition)]
            for command in commands:
                for word in command:
                    assert not re.search(r"<[^>]+>", word), (inv.check, word)


# --- the record-to-harness direction -------------------------------------------


def test_every_command_form_the_record_names_is_declared():
    """The record-to-harness direction the three older guards do not run.

    Those guards hold the transcription against the record, so a record that
    *grows* a prescription leaves all three green. This one fails instead,
    naming the span nothing declares.
    """
    for inv in INVOCATIONS:
        paragraph = _prescribing_paragraph(inv.check, inv.record_quote)
        extracted = set()
        for lead in _lead_words(inv):
            extracted |= _command_forms(paragraph, lead)
        assert extracted == {f for f, _ in inv.forms}, (inv.check, inv.tool)


def test_every_flag_the_record_names_occurs_in_a_declared_form():
    """A flag in no declared form is a prescription nothing transcribed.

    What the declaration property cannot see: a record that names a flag without
    repeating the command it belongs to leaves the extracted set unchanged, so
    that property stays green. This is the shape `arch/cycles` drifted in - the
    record grew "Append `--show-dot` to that `pydeps` invocation" in a later
    sentence of the same paragraph, and the flag belongs to a command the
    sentence does not repeat.

    Pooled across every invocation sharing the record, because one paragraph
    prescribes for several tools: `deps/freshness` writes `uv pip list
    --outdated --python <path>` and `pip list --outdated` in one sentence, and
    `--python` belongs to the first. Held against one tool's own forms, every
    flag a neighbour's command carries fails - not because the record drifted,
    but because the flag was never that tool's to declare.

    `_concrete` applies to the flag for the same reason it applies to a form, and
    not because the form carries a concrete value where the flag carries a
    placeholder: `deps/freshness` writes the span as `--python <path>` and the
    declared form as `--python <path-to-venv-python>`, two placeholders for the
    same hole, so neither side can ever match the other as written. Dropping the
    placeholder from both is what leaves the flag itself to match.
    """
    for inv in INVOCATIONS:
        paragraph = _prescribing_paragraph(inv.check, inv.record_quote)
        pooled = _tokens(
            " ".join(
                form
                for other in INVOCATIONS
                if other.check == inv.check
                for form, _ in other.forms
            )
        )
        for flag in _flag_spans(paragraph):
            wanted = _concrete(_tokens(flag))
            # A span that reduced to nothing would satisfy the `all` below
            # vacuously, which is how a newly prescribed flag would pass in
            # silence. `_concrete` truncates rather than drops for that reason,
            # so this is unreachable while it does - and loud if it stops.
            assert wanted, (inv.check, flag)
            assert all(any(_matches(w, t) for t in pooled) for w in wanted), (
                inv.check,
                flag,
            )


def test_every_form_the_harness_runs_appears_in_an_argv():
    """The other half: a form declared `runs` that no command carries.

    The declaration property compares sets of spans, so it passes on a form
    declared `runs` beside an argv that has stopped matching it, and the flag
    property never reads a disposition at all. This one holds the two together,
    which is what catches `deps/vulnerabilities`: its placeholder put it in the
    anchor guard's `unanchored` set, so the guard that would have noticed a flag
    pair being added to the prescribed form was switched off for exactly that
    entry. Dropping the placeholder token instead of excusing the entry is what
    lets this one watch it.

    `then` counts as a command of its own: `coverage run -m pytest` and `coverage
    report --show-missing` are one route the record splits in two, and reading
    the argv alone would report the half that prints the report as a form nothing
    runs. Each command comes from `argv_for`, so it carries the entry's
    completion as well - the form `pytest --cov=<pkg> ...` is satisfied by the
    `--cov=` the completion supplies, and reading the prescribed argv alone would
    have to drop that token instead, which is what makes a flag with a glued
    placeholder invisible. Reading two fields of the table is not the folding the
    provenance guard forbids: that one forbids a completion hiding inside the
    `argv` field, where nothing could tell it from what the record prescribed.

    Order is held among the tokens the record writes in full, and presence only
    for a token whose tail the caller supplies. That split is what keeps the
    relaxation to the single token that needs it: a completion is appended at the
    end of the command while the record writes the token it supplies inside the
    form, so an ordered test over the whole form fails on `pytest --cov=<pkg>
    --cov-branch --cov-report=term-missing`, whose `--cov=` arrives last. Measured
    over every form declared `runs`, that is the only token in the table any
    command satisfies by completion alone, so it is the only one this exempts.

    Nothing else in the suite holds a form's order for it. The guard that traces
    a transcribed command through the record's sentence reads one argv per entry -
    the first partition with a command - and never reads `then`, and it asserts
    the *absence* of an anchor for the entries it excepts, so a form reachable
    only through another partition's argv, only through `then`, or on an excepted
    entry gets its order from here or from nowhere.
    """
    for inv in INVOCATIONS:
        commands = [c for c in (argv_for(inv, p) for p in PARTITIONS) if c]
        if inv.then:
            commands.append(inv.then)
        carried = [_tokens(" ".join(command)) for command in commands]
        for form, disposition in inv.forms:
            if disposition != "runs":
                continue
            wanted = _concrete(_tokens(form))
            # The vacuity its sibling refuses, refused here too: a form reducing
            # to nothing would satisfy the `all` below however the command reads.
            assert wanted, (inv.check, inv.tool, form)
            ordered = [w for w in wanted if not _marked(w)]
            supplied = [w for w in wanted if _marked(w)]
            assert any(
                _is_subsequence(ordered, tokens)
                and all(any(_matches(w, token) for token in tokens) for w in supplied)
                for tokens in carried
            ), (inv.check, inv.tool, form)


def test_every_disposition_in_the_vocabulary_is_used():
    """A value nothing uses is ceremony that reads as coverage.

    No other property here reads the vocabulary as a whole: each reads the
    disposition on a form it already has. So a value could sit in `DISPOSITIONS`
    with no user, and `forbidden` did. What keeps it unused is disposition
    precedence rather than anything structural: records do warn against
    multi-token forms and the extractor reads those spans as forms - `arch/cycles`
    warns against `pydeps --show-cycles`, declared `superseded` because the record
    narrows the same command, and `deps/inventory` says it has no route through
    `cyclonedx-py poetry`, declared `runs` because the harness runs that form on
    the partition whose manifest it does read. A form the harness runs is `runs`
    and a form the record narrows is `superseded`, so every warning in the family
    today is already answered by one of those. A record writing "never run `foo
    --bar`", a form neither run nor narrowed, would give `forbidden` a user
    immediately. Written as an equality rather than a subset in either direction,
    because the two failures are different findings: an unused value is ceremony,
    and a used value missing from the tuple is already rejected by `Invocation`.
    """
    assert {d for inv in INVOCATIONS for _, d in inv.forms} == set(DISPOSITIONS)


def test_a_prescription_stays_in_the_paragraph_the_guard_watches():
    """Otherwise the blind spot moves up one level.

    Every property that reads a record is scoped to the paragraph holding
    `record_quote`. A correction that appends a whole new paragraph instead of a
    sentence lands outside all of them, which is this same defect one level up -
    and it is the shape `arch/complexity-gate` was found in, whose whole fallback
    section is an unlabelled bolded directive rather than a labelled lens
    paragraph.

    Scoped by review-lens label rather than by naming the records that trip it.
    `semgrep` is one tool named in both the Python and the TypeScript paragraph
    of the `security` records, and `semgrep scan --config p/javascript` is a
    sibling lens's prescription rather than drift; a set of excepted records
    would list those records today and grow with every tool two language
    paragraphs share. The label is the ecosystem-neutral instrument, and only a
    label naming another language lens is skipped - a paragraph labelled for a
    condition rather than a language, of which these sections carry several,
    holds Python prescriptions too, so a blanket skip of every label that is not
    `Python` would unwatch exactly where a Python correction would land.

    The consequence of that exception, stated because a reader who sees the
    skipped set would otherwise read it as a narrow one: a Python prescription
    written inside a `**TypeScript**`-labelled paragraph is watched by nothing at
    all. This property skips it as a sibling lens's business, and every other
    property here reads only the paragraph holding `record_quote`, which that one
    is not. The label decides which lens a paragraph belongs to, so a paragraph
    labelled for the wrong lens takes its contents out of reach with it.

    A second limit, and it is not hypothetical. Every property in this file is
    scoped either to the source line holding `record_quote` or - here - to the
    paragraphs of `## Tooling fallback`, so a prescription written in any other
    section of a record is invisible to all of them. `arch/complexity-gate`
    carries `ruff --select C901` in its `## Fix` section and `deps/freshness`
    carries `uv lock` in its, each led by a tool the harness invokes, neither
    declared in `forms`, and the suite is green over both. A command in `## Fix`
    is unwatched: the section scoping is what buys the anchoring on `record_quote`
    that lets a record with no `**Python**` line be watched at all, and it is paid
    for in every section the scoping excludes.

    One residual gap, and nothing closes it. A record that prescribes a tool in
    prose without listing it under `tooling:` has no invocation here, so no lead
    word of any entry leads its span and every property in this file passes over
    it in silence. No other rule catches it either: `audit_checks` holds a
    record's `needs` names against its `tooling` list, and nothing anywhere holds
    its prose against either.
    """
    # Pinned rather than derived: a stray span under a lens this list does not
    # name fails, and somebody reads the paragraph before extending it.
    sibling_lenses = {"TypeScript"}
    skipped = set()
    for inv in INVOCATIONS:
        for label, paragraph in _fallback_paragraphs(inv.check):
            if inv.record_quote in paragraph:
                continue
            stray: set[str] = set()
            for lead in _lead_words(inv):
                stray |= _command_forms(paragraph, lead)
            if not stray:
                continue
            if label in sibling_lenses:
                skipped.add(label)
                continue
            raise AssertionError(
                f"{inv.check}/{inv.tool}: {sorted(stray)} sits in a "
                f"{label or 'unlabelled'} paragraph of `## Tooling fallback` that "
                "no property watches, because the quoted one is elsewhere"
            )
    assert skipped == sibling_lenses, (
        f"a lens nothing is skipped for is a stale exception: {sorted(skipped)}"
    )


def test_a_form_naming_the_tool_off_the_front_is_led_by_some_invocation():
    """A prescription no lead word leads must not vanish.

    The declaration property compares what the lead words extract, so a span no
    lead word leads is absent from both sides of that equality and it passes.
    `deps/freshness` writes `uv pip list --outdated` in the paragraph its `pip`
    entry also quotes, and that span is the `uv` entry's form rather than the
    `pip` entry's. What must never happen is a span naming a tool that no
    invocation on that record leads: `uvx pydeps --show-cycles` would be a
    prescription with no declaration and no failure.

    Keyed on the entry's lead words rather than on its tool name, because the tool
    name is not always a word any command carries. Four entries are named for a
    plugin or a distribution the prescribed command never mentions -
    `test/coverage-reach`'s `pytest-cov` and `coverage.py`, `test/determinism`'s
    `pytest-randomly`, `test/isolation`'s `pytest-timeout` - and a rule looking for
    that name off the front of a span fires on none of their paragraphs, so those
    four got none of this protection while the docstring promised it to them.
    `_lead_words` already carries the runner the record actually writes, so keying
    here on the same set is what makes the promise hold for every entry: it is the
    `coverage run -m pytest` span in `test/coverage-reach`'s paragraph that the
    tool-name rule passed over and this one now reads.
    """
    for inv in INVOCATIONS:
        paragraph = _prescribing_paragraph(inv.check, inv.record_quote)
        led = {
            form.split()[0]
            for other in INVOCATIONS
            if other.check == inv.check
            for lead in _lead_words(other)
            for form in _command_forms(paragraph, lead)
        }
        leads = _lead_words(inv)
        for span in _spans(paragraph):
            words = span.split()
            if len(words) > 1 and any(lead in words[1:] for lead in leads):
                assert words[0] in led, (inv.check, inv.tool, span)


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


def test_a_filtered_run_names_only_the_check_it_was_given():
    assert [i.check for i in invocations_for("uv", only_check="arch/cycles")] == [
        "arch/cycles"
    ] * len([i for i in INVOCATIONS if i.check == "arch/cycles"])


def test_an_unknown_check_filter_is_refused():
    with pytest.raises(ValueError, match="no invocation"):
        invocations_for("uv", only_check="arch/nonexistent")


def test_a_check_the_partition_does_not_carry_is_refused_by_the_filter():
    """`arch/cycles` exists, and the poetry partition does not run it.

    The refusal is about the pair rather than about the check: a filter naming a
    check the partition's expectations exclude would otherwise return nothing
    and write an artifact of zero rows, which reads as a check that ran and
    found no tools rather than as a run that was never in scope.
    """
    with pytest.raises(ValueError, match="no invocation"):
        invocations_for("poetry", only_check="arch/cycles")


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


def test_a_tool_that_did_no_work_is_never_graded_ok_on_a_nonzero_exit():
    """A tool marked `failure` never reads its own noise as a report.

    `mutmut run` writes a spinner and status text to stdout on every run,
    survivors or not - measured, a run that got as far as `Failed to run clean
    test` and tested zero mutants still has non-empty stdout. Grading on
    content the way `findings` does would call that a clean pass; the
    `nonzero_meaning="failure"` branch refuses regardless of what is on either
    stream, because a tool that may have done nothing must never grade `ok`.
    """
    spinner_text = (
        "⠋ Generating mutants\n    done in 77ms (10 files mutated, 0 ignored, "
        "0 unmodified)\n\nF\nFAILED tests/test_order.py::test_appends\nFailed to "
        "run clean test\n"
    )
    assert classify(
        1, spinner_text, "", tool_present=True, nonzero_meaning="failure"
    ) == ("no-evidence", "tool-failed")
    # Content on stderr instead changes nothing: `failure` never reads either
    # stream as a report.
    assert classify(
        1,
        "",
        spinner_text,
        tool_present=True,
        findings_stream="stderr",
        nonzero_meaning="failure",
    ) == ("no-evidence", "tool-failed")
    # A clean exit is still `ok` - `failure` only refuses to read a non-zero
    # exit as a report, it does not invert the rc-0 case.
    assert classify(
        0, spinner_text, "", tool_present=True, nonzero_meaning="failure"
    ) == (
        "ok",
        "",
    )


def test_an_ambiguous_tool_is_as_conservative_as_a_proven_failure():
    """`ambiguous` and `failure` behave identically on a non-zero exit.

    They are named apart because one is proven (`mutmut`, from reading its own
    source) and the other is an honest "not known" for a reporting tool this
    round never observed exiting non-zero - but neither ever turns content
    into `ok` the way `findings` does, so a future promotion out of `ambiguous`
    has to be a stated decision, not a difference this function already makes.
    """
    assert classify(
        1, "some output", "", tool_present=True, nonzero_meaning="ambiguous"
    ) == (
        "no-evidence",
        "tool-failed",
    )
    assert classify(0, "", "", tool_present=True, nonzero_meaning="ambiguous") == (
        "ok",
        "",
    )


def test_classify_rejects_an_unknown_nonzero_meaning():
    with pytest.raises(ValueError, match="nonzero_meaning"):
        classify(1, "x", "", tool_present=True, nonzero_meaning="vibes")


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


def test_deptry_and_xenon_are_the_entries_that_report_on_stderr():
    """The exact set, so a stream silently moved onto another entry fails here.

    `xenon` joined this set once its own finding was measured: `uvx xenon
    --max-absolute B src` on the seeded partition exits 1 with stdout empty and
    the whole `ERROR:xenon:block ... has a rank of C` on stderr - left at the
    stdout default, that finding was invisible and the row graded
    `tool-failed` instead of the hit it actually was.
    """
    assert {
        (i.check, i.tool) for i in INVOCATIONS if i.findings_stream == "stderr"
    } == {("deps/hygiene", "deptry"), ("arch/complexity", "xenon")}
    assert all(i.findings_stream in ("stdout", "stderr") for i in INVOCATIONS)
    with pytest.raises(ValueError, match="findings_stream"):
        Invocation(
            check="deps/hygiene",
            tool="deptry",
            record_quote="x" * 40,
            argv=("deptry",),
            findings_stream="both",
        )


def _tools_that_can_run_a_command() -> set[str]:
    """Every tool `INVOCATIONS` could actually hand `classify` an exit code.

    A tool named only in an entry with no `argv`, no `argv_by_partition` and no
    `supplied_by_partition` never runs a command at all - `grimp`, `safety`,
    `cosmic-ray`, `hypothesis` - so it never reaches `classify` and has nothing
    to state a non-zero-exit meaning about.
    """
    return {
        i.tool
        for i in INVOCATIONS
        if i.argv or i.argv_by_partition or i.supplied_by_partition
    }


def test_nonzero_exit_meaning_covers_exactly_the_tools_that_can_run_a_command():
    """The exact-set guard: a tool added to `INVOCATIONS` with a real command
    and no entry here would silently default `classify` to `findings`, which is
    precisely the silent claim this table exists to forbid.
    """
    assert set(NONZERO_EXIT_MEANING) == _tools_that_can_run_a_command()


def test_every_stated_meaning_is_one_of_the_three_kinds():
    assert set(NONZERO_EXIT_MEANING.values()) <= set(NONZERO_EXIT_KINDS)


def test_mutmuts_nonzero_exit_is_a_stated_failure_not_a_finding():
    """Proven rather than assumed - see `NONZERO_EXIT_MEANING`'s own comment.

    `mutmut run` (the record's own bare invocation) only calls `exit()` from
    setup/collection failures; the loop that tests generated mutants and tallies
    survivors never exits non-zero on their account, so there is no path from
    "mutants survived" to this command's non-zero exit - it is always a genuine
    failure, never a report.
    """
    assert NONZERO_EXIT_MEANING["mutmut"] == "failure"


def test_nonzero_exit_meaning_raises_for_a_tool_with_no_stated_meaning():
    with pytest.raises(ValueError, match="xylophone"):
        nonzero_exit_meaning("xylophone")
    assert nonzero_exit_meaning("mutmut") == "failure"


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


def test_a_route_naming_its_own_runner_takes_no_prefix():
    """And a sibling partition of the same entry still takes one.

    Both directions on one entry, because the fetch is keyed on the entry's tool
    and not on the command: a prefix suppressed for the whole entry would send
    the partitions whose command really is `cyclonedx-py` off to a tool nothing
    fetched, and a prefix applied to all of them would front a command that
    never calls `cyclonedx-bom` with a fetch for it.
    """
    inv = _entry("deps/inventory", "cyclonedx-py")
    for granted in (True, False):
        assert launcher(inv, "uv", granted=granted) == ()
        assert launcher(inv, "pip", granted=granted) == (
            "uvx",
            "--from",
            "cyclonedx-bom",
        )


def test_the_version_probe_obtains_a_tool_its_route_never_fetches():
    """The probe is not the record's command, so the suppression is not its own.

    `own_runner` says one partition's *prescribed command* arrives complete.
    `VERSION_PROBE` runs the tool's own `--version` instead, which still has to
    be fetched - probed bare it would report a missing tool on the partition
    where the record's route is fine, which reads as the tool being broken.
    """
    inv = _entry("deps/inventory", "cyclonedx-py")
    assert launcher(inv, "uv", granted=True, honour_own_runner=False) == (
        "uvx",
        "--from",
        "cyclonedx-bom",
    )


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


def test_a_multi_package_route_carries_one_with_per_package_in_the_overlay(
    tmp_path, monkeypatch
):
    """`coverage.py` needs `pytest` alongside it; both arrive as `--with` flags
    on the same `uv run` rather than as separate installs into the copy.
    """
    source = tmp_path / "fixture" / "poetry"
    source.mkdir(parents=True)
    monkeypatch.setattr("run_python_fixture_lens._run", _fake_run([]))
    observed = run_partition(
        "poetry", source, tmp_path / "work", "target-execution", timeout=5
    )
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}
    command = rows[("test/coverage-reach", "coverage.py")]["command"]
    assert command[:8] == [
        "uv",
        "run",
        "--no-project",
        "--python",
        f"{VENV_BIN}/python",
        "--with",
        "coverage",
        "--with",
    ]
    assert command[8] == "pytest"
    assert "provision" not in rows[("test/coverage-reach", "coverage.py")]


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
    """`uv` is the round's known-good reference route and keeps its own shape;
    every other partition reaches the same environment through `--python`
    rather than through that manager's own runner.
    """
    inv = next(
        i for i in INVOCATIONS if (i.check, i.tool) == ("deps/hygiene", "deptry")
    )
    assert launcher(inv, "uv", granted=True) == ("uv", "run", "--with", "deptry")
    for partition in ("pip", "poetry", "pipenv", "pylock"):
        assert launcher(inv, partition, granted=True) == (
            "uv",
            "run",
            "--no-project",
            "--python",
            f"{VENV_BIN}/python",
            "--with",
            "deptry",
        ), partition


def test_a_venv_partition_is_launched_through_the_overlay_rather_than_by_name():
    """`pip-licenses` imports as `piplicenses`, so `python -m` has nothing to
    hand - and installing it into the copy is the write `audit-core` bars, so
    neither a bare command name on `PATH` nor an install is the route.
    """
    inv = next(
        i for i in INVOCATIONS if (i.check, i.tool) == ("deps/licenses", "pip-licenses")
    )
    for partition in ("pip", "pylock"):
        assert launcher(inv, partition, granted=True) == (
            "uv",
            "run",
            "--no-project",
            "--python",
            f"{VENV_BIN}/python",
            "--with",
            "pip-licenses",
        )


def test_no_audit_owned_tool_is_ever_installed_into_a_materialized_copy():
    """`audit-core` bars installing into the target and prescribes a copy
    outside it instead - measured on the poetry partition, installing `deptry`
    the other way pulled in a newer `packaging` and printed
    `Uninstalling packaging-20.9`, silently replacing the exact pin the fixture
    seeded for `deps/freshness` to find outdated. `launcher` is the only thing
    that decides how a tool is obtained, so a route with no separate
    provisioning step is a property of every `in_env` invocation on every
    partition rather than something asserted partition by partition.
    """
    for inv in INVOCATIONS:
        if not inv.in_env:
            continue
        for partition in PARTITIONS:
            prefix = launcher(inv, partition, granted=True)
            assert "install" not in prefix, (inv.check, inv.tool, partition)


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
    assert {
        "uv": (("uv", "sync", "--frozen"),),
        "pip": (
            ("uv", "venv", "--seed", ".venv"),
            (".venv/bin/pip", "install", "-r", "requirements.txt"),
            (".venv/bin/pip", "install", "-e", ".", "--no-deps"),
        ),
        "poetry": (("uvx", PINNED_MANAGERS["poetry"], "install"),),
        "pipenv": (
            ("uvx", PINNED_MANAGERS["pipenv"], "sync"),
            (
                "uvx",
                PINNED_MANAGERS["pipenv"],
                "run",
                "pip",
                "install",
                "-e",
                ".",
                "--no-deps",
            ),
        ),
        "pylock": (
            ("uv", "venv", ".venv"),
            ("uv", "pip", "install", "-r", "pylock.toml"),
            ("uv", "pip", "install", "-e", ".", "--no-deps"),
        ),
    } == MATERIALIZE
    assert set(MATERIALIZE) == set(PARTITIONS)


def test_materialization_pins_the_same_manager_versions_the_generator_used():
    """A pin that drifts between the two files materializes with a manager
    different from the one that built the lock in the first place.

    Compared against the rendered `MATERIALIZE` commands rather than against
    `PINNED_MANAGERS` itself, so a call site that hardcoded a version instead
    of reading the constant would still be caught - comparing the constant to
    itself would not.
    """
    for partition in ("poetry", "pipenv"):
        tokens = [token for command in MATERIALIZE[partition] for token in command]
        assert PINNED_MANAGERS[partition] in tokens, partition
        assert tokens.count(PINNED_MANAGERS[partition]) == len(
            MATERIALIZE[partition]
        ), partition


def test_every_materialization_route_ends_by_installing_the_project_itself():
    """Stated as the property rather than left to the pin above to imply.

    `uv sync` and `poetry install` install the project from its own manifest;
    the other three end in an editable install of it. A route that installed
    only dependencies would leave the package unimportable on a partition whose
    checks run its suite.
    """
    for partition, commands in MATERIALIZE.items():
        last = commands[-1]
        assert last[-1] in ("--no-deps", "sync", "install", "--frozen"), (
            partition,
            last,
        )
        if last[-1] == "--no-deps":
            assert "-e" in last and "." in last, (partition, last)


def test_every_materialization_route_installs_from_the_committed_lock():
    """A route that re-resolves observes a tree the fixture never committed.

    `uv sync` and `pipenv install` both re-resolve when they judge the lock
    stale, so the frozen form is what holds the observation to the resolution
    the fixture was built with - and the build smoke that established the
    ground truth materialized with `uv sync --frozen`, so without it the two
    would be measuring different trees with nothing to say so. The refresh
    never reaches a fixture, since materialization runs in a copy; what it
    reaches is the answer.

    Neither manager fails loudly when the flag is missing. Both quietly use the
    lock while it happens to be current, which is why this is asserted rather
    than left to be noticed.
    """
    assert set(FROZEN_FORM) == set(MATERIALIZE)
    for partition, form in FROZEN_FORM.items():
        if not form:
            continue
        tokens = [token for command in MATERIALIZE[partition] for token in command]
        assert form in tokens, (partition, form, tokens)


def test_the_partitions_needing_no_frozen_form_carry_their_resolution_in_a_file():
    """An empty entry is a claim, so it has to be one something can check.

    `pip` and `pylock` install straight from a file that already *is* the
    resolution, so there is no lock for an installer to refresh. Read from the
    manifests rather than named here, so a partition that stopped shipping that
    file could not keep an empty entry.
    """
    for partition, form in FROZEN_FORM.items():
        if form:
            continue
        manifests = set(render_manifests(partition)) | {"pylock.toml"}
        installed_from = [
            command[command.index("-r") + 1]
            for command in MATERIALIZE[partition]
            if "-r" in command
        ]
        assert installed_from, partition
        for source in installed_from:
            assert source in manifests, (partition, source, manifests)


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
        ("pip", ("pip-audit", "-r", "requirements.txt", "--no-deps", "--disable-pip")),
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
    produces a document, so nothing downstream distinguishes it. The uv row is
    the same claim about the same record: what it names there is the native
    export, whose first word is `uv` rather than this entry's tool, which is why
    that row is the one naming its own runner.
    """
    inv = _entry("deps/inventory", "cyclonedx-py")
    assert inv.argv_by_partition == (
        ("uv", ("uv", "export", "--format=cyclonedx1.5", "--frozen")),
        ("pip", ("cyclonedx-py", "requirements")),
        ("poetry", ("cyclonedx-py", "poetry")),
        ("pipenv", ("cyclonedx-py", "pipenv")),
        ("pylock", ()),
    )
    assert inv.own_runner == ("uv",)
    assert {p for p, _ in inv.argv_by_partition} == set(PARTITIONS)


# --- routes this round supplied rather than transcribed ------------------------


def test_a_supplied_route_is_exactly_the_two_named_holes():
    """Pinned whole, because the mechanism's value is that it stays small.

    A supplied route is the audit's own answer to a hole the record leaves, and
    the rule that nothing corrects a record survives only while every one of
    them is visible as supplied rather than prescribed. One appearing here
    unnoticed is a correction made by the harness.
    """
    supplied = {
        (i.check, i.tool, p): steps
        for i in INVOCATIONS
        for p, steps in i.supplied_by_partition
    }
    assert supplied == {
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


def test_an_own_runner_partition_needs_a_command_of_its_own_to_run():
    """Named against nothing, the field silently covers no route at all.

    The third shape - a partition carrying a supplied route as well - is
    rejected by `_check_supplied` rather than here, from whichever side it is
    written: with no prescribed command the first case below fires, and with one
    the supplied guard does.
    """
    with pytest.raises(ValueError, match="has no prescribed command"):
        Invocation(
            check="deps/inventory",
            tool="cyclonedx-py",
            record_quote="x" * 40,
            argv_by_partition=(("pip", ("cyclonedx-py", "requirements")),),
            own_runner=("uv",),
        )
    with pytest.raises(ValueError, match="has no prescribed command"):
        Invocation(
            check="deps/inventory",
            tool="cyclonedx-py",
            record_quote="x" * 40,
            own_runner=("uv",),
            supplied_by_partition=(("uv", (("uv", "export"),)),),
            supplied_note="why",
        )
    with pytest.raises(ValueError, match="both a prescribed route and a supplied"):
        Invocation(
            check="deps/inventory",
            tool="cyclonedx-py",
            record_quote="x" * 40,
            argv_by_partition=(("uv", ("uv", "export")),),
            own_runner=("uv",),
            supplied_by_partition=(("uv", (("uv", "export"),)),),
            supplied_note="why",
        )
    with pytest.raises(ValueError, match="own_runner partition takes no launcher"):
        Invocation(
            check="deps/hygiene",
            tool="deptry",
            record_quote="x" * 40,
            argv=("deptry", "."),
            in_env=True,
            own_runner=("uv",),
        )


def test_a_form_carrying_an_unknown_disposition_is_rejected():
    with pytest.raises(ValueError, match="not one of"):
        Invocation(
            check="arch/cycles",
            tool="pydeps",
            record_quote="x" * 40,
            forms=(("pydeps --show-cycles", "maybe"),),
        )


def test_an_empty_form_is_rejected():
    with pytest.raises(ValueError, match="empty command form"):
        Invocation(
            check="arch/cycles",
            tool="pydeps",
            record_quote="x" * 40,
            forms=(("   ", "runs"),),
        )


def test_the_same_form_declared_twice_is_rejected():
    with pytest.raises(ValueError, match="twice"):
        Invocation(
            check="arch/cycles",
            tool="pydeps",
            record_quote="x" * 40,
            forms=(
                ("pydeps --show-cycles", "runs"),
                ("pydeps --show-cycles", "superseded"),
            ),
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

    # The other direction of the same provenance claim: this row's command is
    # the record's own, so it renders as `record_argv` with no supplied step
    # beside it and no launcher prefix in front of it.
    sbom = rows[("deps/inventory", "cyclonedx-py")]
    assert sbom["record_argv"] == [
        "uv",
        "export",
        "--format=cyclonedx1.5",
        "--frozen",
    ]
    assert "supplied" not in sbom
    assert sbom["command"] == sbom["record_argv"]
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
    # `[:3]` rather than `[:2]`: the version probe also runs `uvx pip-audit
    # --version`, which is a real and separate route, so the guard has to name
    # the supplied route's own `-r` step rather than the shared `uvx pip-audit`
    # prefix both commands start with.
    assert not any(command[:3] == ["uvx", "pip-audit", "-r"] for command in recorded)


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


def test_the_run_environment_puts_every_managers_venv_in_the_copy():
    """`launcher`'s `--python .venv/bin/python` only resolves anything because
    of these two: left unset, poetry writes its venv to its own cache
    directory and pipenv to `~/.local/share/virtualenvs`, neither of which is
    `.venv` inside the copy the route points at.

    The opposite of `build_python_fixtures._fixture_env`, which pops the same
    two names - that function protects the committed fixture from ever
    carrying a venv, this one guarantees materialization writes one into the
    throwaway copy where the launcher can reach it. Both enforce "no venv in
    the tree that must stay clean, a venv in the tree that may not."
    """
    env = _fixture_env()
    assert env["POETRY_VIRTUALENVS_IN_PROJECT"] == "1"
    assert env["PIPENV_VENV_IN_PROJECT"] == "1"


def test_the_handbooks_own_bin_directory_is_off_the_subprocess_path(monkeypatch):
    """It carries a `pytest` and a `ruff`, and `uv run` puts it first.

    Left there, a bare `pytest` or `ruff` invoked in a fixture copy still
    resolves from this repository's environment, against a copy of somebody
    else's tree, and answers about the wrong project while looking like a
    clean run. The launchers are installed elsewhere, so dropping this one
    directory leaves them findable.
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
        launches: Gets each command as a tuple, for the tests about which
            words a partition's route puts in front of the record's own
            command.
    """

    def run(command, cwd, timeout):
        recorded.append(list(command))
        if launches is not None:
            launches.append(tuple(command))
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

    assert [m["command"] for m in observed["materialization"]] == [
        ["uv", "sync", "--frozen"]
    ]
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}
    deptry = rows[("deps/hygiene", "deptry")]
    assert deptry["command"][:2] == ["uv", "run"]
    assert deptry["command"][-2:] == ["deptry", "."]
    assert deptry["status"] == "ok"
    follow_up = rows[("test/coverage-reach", "coverage.py")]["then"]
    assert follow_up["command"][-3:] == ["coverage", "report", "--show-missing"]


def test_the_interpreter_the_freshness_record_names_is_transcribed():
    """Unit-level: `--python` is the record's word, its value is the harness's.

    The flag reached the run as a suffix the harness appended before the record
    prescribed it, and a suffix is invisible to every guard that reads `argv`.
    Transcribed, the flag travels with the command and only the path - the
    record's `<path-to-venv-python>` - is left to the completion. `pip` is the
    contrast: the record says it needs no such flag, so its entry carries none.
    """
    uv_inv = _entry("deps/freshness", "uv")
    pip_inv = _entry("deps/freshness", "pip")
    assert uv_inv.argv == ("uv", "pip", "list", "--outdated", "--python")
    assert uv_inv.completion == (f"{VENV_BIN}/python",)
    assert pip_inv.argv == ("pip", "list", "--outdated")
    assert pip_inv.completion == ()


def test_an_inner_uv_command_is_told_which_interpreter_to_read(tmp_path, monkeypatch):
    """Regression for Defect D, end to end through `run_partition`.

    Measured: `uv run --no-project --python .venv/bin/python --with uv uv pip
    list --outdated` - the shape every non-`uv` partition's overlay route
    already produces for an `in_env` tool - prints nothing at exit 0 on an
    environment with three outdated packages; the same command with a
    trailing `--python .venv/bin/python` on the *inner* `uv` lists them. The
    same gap was confirmed on the `uv` partition's own native route (`uv run
    --with uv uv pip list --outdated`, no `--no-project` involved), which is
    why both partitions are checked here rather than only the overlay one.
    The record names the interpreter for that reason, so what this asserts is
    that the transcribed command and its completion still reach the run in that
    shape, whichever partition's route puts the words in front of them.
    """
    for partition in ("uv", "pip"):
        source = tmp_path / "fixture" / partition
        source.mkdir(parents=True)
        recorded: list[list[str]] = []
        monkeypatch.setattr("run_python_fixture_lens._run", _fake_run(recorded))
        observed = run_partition(
            partition, source, tmp_path / f"work-{partition}", "target-execution", 5
        )
        rows = {(r["check"], r["tool"]): r for r in observed["results"]}
        uv_row = rows[("deps/freshness", "uv")]
        assert uv_row["command"][-2:] == ["--python", f"{VENV_BIN}/python"], (
            partition,
            uv_row["command"],
        )
        # `pip` carries no `--python` of its own: the one that can appear in its
        # command is the prefix's (pointing the overlay's interpreter at the
        # copy's venv), never a second one after its argv.
        pip_row = rows[("deps/freshness", "pip")]
        assert pip_row["command"][-3:] == ["pip", "list", "--outdated"], (
            partition,
            pip_row["command"],
        )
        assert pip_row["command"].count("--python") <= 1, (
            partition,
            pip_row["command"],
        )


def test_mutmuts_own_output_never_masks_a_run_that_tested_nothing(
    tmp_path, monkeypatch
):
    """Regression for Defect C's most dangerous shape: a false `ok`.

    Real `mutmut run` output, captured from a prior matrix run: it generated
    mutants, then failed its own clean-tests baseline and tested zero of them -
    `Failed to run clean test` on stdout, exit 1. Reading any non-empty stdout
    as a report - which is what a bare content check does - graded this `ok`;
    a tool that did no work must never grade `ok`.
    """
    source = tmp_path / "fixture" / "uv"
    source.mkdir(parents=True)
    real_mutmut_stdout = (
        "\n⠋ Generating mutants\n    done in 77ms (10 files mutated, 0 "
        "ignored, 0 unmodified)\n\n⠸ Running stats\n    done\n\n⠸ "
        "Running clean tests\nF\n=================================== FAILURES "
        "===================================\n_________________________________ "
        "test_appends _________________________________\nAssertionError: assert "
        "[1, 1] == [1]\n=========================== short test summary info "
        "============================\nFAILED tests/test_order.py::test_appends "
        "- assert [1, 1] == [1]\n1 failed in 0.01s\nFailed to run clean test\n\n"
    )

    def respond(command):
        if "mutmut" in command and "run" in command:
            return _outcome(returncode=1, stdout=real_mutmut_stdout, stderr="")
        return None

    monkeypatch.setattr("run_python_fixture_lens._run", _fake_run([], respond=respond))
    observed = run_partition(
        "uv", source, tmp_path / "work", "target-execution", timeout=5
    )
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}
    mutmut_row = rows[("test/mutation", "mutmut")]
    assert mutmut_row["status"] == "no-evidence", mutmut_row
    assert mutmut_row["reason"] == "tool-failed", mutmut_row


def test_xenons_stderr_finding_is_graded_ok_end_to_end(tmp_path, monkeypatch):
    """Regression for Defect C's other half: a real hit graded as a failure.

    Real `xenon` output, measured on the seeded partition (`uvx xenon
    --max-absolute B src`): stdout empty, the finding entirely on stderr, exit
    1. Before `findings_stream="stderr"` was set on this entry, `classify` read
    the empty stdout and graded the row `tool-failed`.
    """
    source = tmp_path / "fixture" / "uv"
    source.mkdir(parents=True)
    xenon_stderr = (
        'ERROR:xenon:block "src/fixture_app/complexity.py:4 classify" has a rank of C\n'
    )

    def respond(command):
        if "xenon" in command:
            return _outcome(returncode=1, stdout="", stderr=xenon_stderr)
        return None

    monkeypatch.setattr("run_python_fixture_lens._run", _fake_run([], respond=respond))
    observed = run_partition(
        "uv", source, tmp_path / "work", "target-execution", timeout=5
    )
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}
    xenon_row = rows[("arch/complexity", "xenon")]
    assert xenon_row["status"] == "ok", xenon_row


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

    `pip install -r requirements.txt` into a virtualenv `uv venv --seed` failed
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
                _outcome(returncode=1, stdout="", stderr="no venv")
                if command[:2] == ["uv", "venv"]
                else None
            ),
        ),
    )
    observed = run_partition(
        "pip", source, tmp_path / "work", "target-execution", timeout=5
    )
    assert [m["command"] for m in observed["materialization"]] == [
        ["uv", "venv", "--seed", ".venv"]
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
                _outcome(returncode=1, stderr="no venv")
                if command[:2] == ["uv", "venv"]
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
        assert row["blocked_by"] == ["uv", "venv", "--seed", ".venv"]
        assert "uv venv --seed .venv" in row["why"]
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
                if command == ["uv", "sync", "--frozen"]
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


def test_a_binary_that_was_never_there_reaches_the_row_as_unavailable(
    tmp_path, monkeypatch
):
    """`_run` reports absence, and the row is where that has to still be true.

    Absence and a timeout arrive identically - no exit status at all - and only
    `tool_present` separates them, so the branch that reads it is the one place
    a missing tool can quietly become a clean run. Asserting it on `classify`
    alone leaves that branch untested, because `classify` is not what decides
    it for a command that never exited.
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
                    "stderr": "FileNotFoundError: [Errno 2] No such file or directory",
                    "tool_present": False,
                }
                if "vulture" in command
                else None
            ),
        ),
    )
    observed = run_partition("uv", source, tmp_path / "work", "none", timeout=5)
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}
    row = rows[("arch/dead-code", "vulture")]
    assert (row["status"], row["reason"]) == ("no-evidence", "tool-unavailable")
    assert row.get("detail", "") == ""


def test_a_hung_tool_that_reports_on_stderr_is_still_a_timeout(tmp_path, monkeypatch):
    """The stderr of a timeout is the harness's own message, not the tool's.

    `_run` synthesizes `TimeoutExpired: ...` on that stream, so on the one entry
    whose findings stream *is* stderr the classification reads the harness's
    exception text as a report and grades a hung deptry `ok` - the timeout
    defect surviving on exactly the entry the stream field was added for. The
    two facts have to be settled in the right order.
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
                    "stderr": "TimeoutExpired: Command '['deptry', '.']' timed out",
                    "tool_present": True,
                }
                if command[-2:] == ["deptry", "."]
                else None
            ),
        ),
    )
    observed = run_partition(
        "uv", source, tmp_path / "work", "target-execution", timeout=5
    )
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}
    row = rows[("deps/hygiene", "deptry")]
    assert _entry("deps/hygiene", "deptry").findings_stream == "stderr"
    assert (row["status"], row["reason"]) == ("no-evidence", "tool-failed")
    assert row["detail"] == "timed-out"


def test_a_launcher_that_cannot_fetch_the_tool_reports_it_as_unavailable(
    tmp_path, monkeypatch
):
    """Measured: `uvx no-such-package-45xyzq` exits 1 saying the registry has none.

    `_run` sees `FileNotFoundError` only where the command *is* the tool, and
    `uvx`/`uv` always exist - so a tool nobody could fetch came back as a tool
    that ran and failed, and `tool-unavailable` was unreachable.
    """
    assert launcher_missed(
        ("uvx", "nope"), 1, "error: `nope` was not found in the package registry"
    )
    assert launcher_missed(
        ("uv", "run", "--with", "nope", "nope"),
        1,
        "error: `nope` was not found in the package registry",
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


def test_every_partition_but_uv_reaches_its_tools_through_the_overlay_route(
    tmp_path, monkeypatch
):
    """Every partition but `uv` runs an in-env tool by pointing `uv run` at its
    own `.venv/bin/python`, never by installing the tool into that venv.

    `--no-project` matters as much as `--python` here: `pip` and `pylock`
    partitions differ in whether their copy carries a `pyproject.toml` at all,
    and a bare `uv run` would do project discovery from `cwd` on the ones that
    do, which is exactly the corruption this route exists to avoid.
    """
    for partition in ("pip", "poetry", "pipenv", "pylock"):
        source = tmp_path / "fixture" / partition
        source.mkdir(parents=True)
        recorded = []
        monkeypatch.setattr("run_python_fixture_lens._run", _fake_run(recorded))
        work = tmp_path / f"work-{partition}"
        observed = run_partition(partition, source, work, "target-execution", timeout=5)
        rows = {(r["check"], r["tool"]): r for r in observed["results"]}
        deptry = rows[("deps/hygiene", "deptry")]
        assert deptry["command"] == [
            "uv",
            "run",
            "--no-project",
            "--python",
            f"{VENV_BIN}/python",
            "--with",
            "deptry",
            "deptry",
            ".",
        ], partition
        assert deptry["status"] == "ok", partition
        # The record's own argv is untouched by any of this - only the words
        # placed in front of it differ from the bare `deptry` the record
        # prescribes (`.` is this file's own completion, not the record's).
        assert deptry["record_argv"] == ["deptry"], partition
        for row in observed["results"]:
            assert "provision" not in row, (partition, row["check"], row["tool"])


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


def test_a_filtered_run_never_writes_the_filename_a_full_run_writes(
    tmp_path, monkeypatch, capsys
):
    """The slug in the name is what keeps a one-check run out of the grader.

    The grading pass reads `<partition>-<grant>.json` as the whole matrix for
    that cell. A partial run landing on that name leaves a file of one row where
    the published record claims every check, and nothing about it looks wrong -
    so the filter earns its own filename rather than a flag somebody has to
    remember to pair with `--work-dir`.
    """
    fixture_root = tmp_path / "fixtures"
    (fixture_root / "uv").mkdir(parents=True)
    monkeypatch.setattr("run_python_fixture_lens._run", _fake_run([]))

    exit_code = main(
        [
            "uv",
            "--grant",
            "none",
            "--check",
            "arch/cycles",
            "--fixture-root",
            str(fixture_root),
            "--work-dir",
            str(tmp_path / "work"),
        ]
    )

    assert exit_code == 0
    written = fixture_root / "results" / "uv-none-arch-cycles.json"
    assert written.exists()
    assert not (fixture_root / "results" / "uv-none.json").exists()
    observed = json.loads(written.read_text())
    assert {row["check"] for row in observed["results"]} == {"arch/cycles"}
    assert set(observed["versions"]) == {
        inv.tool for inv in INVOCATIONS if inv.check == "arch/cycles"
    }
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


# --- probing tool versions -------------------------------------------------------


def test_the_results_file_carries_a_version_for_every_tool_the_partition_invokes(
    tmp_path, monkeypatch
):
    """`versions` is a top-level key, keyed by exactly the partition's own tools.

    Not the whole family's: a thin partition like `poetry` never invokes
    `ruff`, and a version entry for a tool it never runs would be as
    unaccountable as a `results` row for a check it never carries.
    """
    source = tmp_path / "fixture" / "uv"
    source.mkdir(parents=True)
    monkeypatch.setattr("run_python_fixture_lens._run", _fake_run([]))
    observed = run_partition(
        "uv", source, tmp_path / "work", "target-execution", timeout=5
    )
    assert set(observed["versions"]) == {i.tool for i in invocations_for("uv")}
    assert observed["versions"]["ruff"] == "output"


def test_a_probe_that_fails_is_recorded_as_its_failure_text_rather_than_dropped(
    tmp_path, monkeypatch
):
    """An absent version is a fact about the run, so the key still has to exist."""
    monkeypatch.setattr(
        "run_python_fixture_lens._run",
        _fake_run(
            [],
            respond=lambda command: (
                _outcome(returncode=1, stdout="", stderr="boom")
                if command == ["uvx", "ruff", "--version"]
                else None
            ),
        ),
    )
    versions = probe_versions("uv", "target-execution", tmp_path, timeout=5)
    assert versions["ruff"] == "boom"
    assert "ruff" in versions


def test_a_blocked_materialization_stops_an_in_env_probe_rather_than_running_it(
    tmp_path, monkeypatch
):
    """Otherwise a probe against a tree that was never built invents a finding.

    The same shape as `run_partition`'s own dependent rows: the version is
    recorded as blocked, and no command referring to the tool is ever launched.
    """
    recorded = []
    monkeypatch.setattr("run_python_fixture_lens._run", _fake_run(recorded))
    blocked_by = ["python", "-m", "venv", ".venv"]
    versions = probe_versions(
        "pip", "target-execution", tmp_path, timeout=5, blocked_by=blocked_by
    )
    assert "environment-unmaterialized" in versions["deptry"]
    assert "python -m venv .venv" in versions["deptry"]
    assert not any("deptry" in command for command in recorded)
    # A tool that answers from a read-only clone needs no environment, so its
    # probe still runs even though the materialization failed.
    assert versions["pip-audit"] == "output"


def test_a_tool_with_no_version_route_reports_the_stated_reason_rather_than_running(
    tmp_path, monkeypatch
):
    """`None` is read from the table, not assumed - `VERSION_PROBE` holds none
    of its own today, so this exercises the branch by substitution rather than
    waiting for a tool that genuinely has no route.
    """
    monkeypatch.setitem(VERSION_PROBE, "ruff", None)
    monkeypatch.setitem(NO_VERSION_ROUTE, "ruff", "substituted for this test")
    recorded = []
    monkeypatch.setattr("run_python_fixture_lens._run", _fake_run(recorded))
    versions = probe_versions("uv", "target-execution", tmp_path, timeout=5)
    assert versions["ruff"] == "no version route: substituted for this test"
    assert not any("ruff" in command for command in recorded)


def test_a_non_uv_partitions_probe_reaches_its_in_env_tool_through_the_overlay(
    tmp_path, monkeypatch
):
    """`pip` and `pylock` carry the same launcher words as the real invocation.

    Without `--python .venv/bin/python` in front, a bare `pip-licenses
    --version` would resolve nothing in the copy and every in-env probe on
    these partitions would read as a missing tool rather than the version
    actually installed.
    """
    launches = []
    monkeypatch.setattr(
        "run_python_fixture_lens._run", _fake_run([], launches=launches)
    )
    versions = probe_versions("pip", "target-execution", tmp_path, timeout=5)
    assert versions["pip-licenses"] == "output"
    assert (
        "uv",
        "run",
        "--no-project",
        "--python",
        f"{VENV_BIN}/python",
        "--with",
        "pip-licenses",
        "pip-licenses",
        "--version",
    ) in launches


def test_every_pytest_plugin_carries_in_env_so_its_probe_resolves_into_an_environment():
    """A bare `python -c` probe only reports a real version if `launcher`
    resolves it into an environment already carrying the package - which an
    `in_env=True` tool gets and one that is not does not.

    `pytest-rerunfailures` briefly failed this: its `Invocation` carries no
    `argv` (a reading pass), and nothing in the real check path ever reads
    `in_env` for an entry with no command to run, so it was left at the
    dataclass default of `False`. `probe_versions` calls `launcher`
    unconditionally, so that default made `launcher` return a bare `("uvx",)`
    for every partition and grant - a throwaway interpreter with the plugin
    never installed, reporting `PackageNotFoundError` forever rather than a
    version.
    """
    plugins = {
        "pytest-cov",
        "pytest-randomly",
        "pytest-rerunfailures",
        "pytest-timeout",
    }
    for inv in INVOCATIONS:
        if inv.tool in plugins:
            assert inv.in_env, inv.tool
    rerun = _entry("test/determinism", "pytest-rerunfailures")
    # The property that actually broke: the granted launcher must resolve into
    # an environment, not fall back to a bare one-shot fetch.
    assert launcher(rerun, "uv", granted=True) != ("uvx",)
    assert launcher(rerun, "uv", granted=True) == (
        "uv",
        "run",
        "--with",
        "pytest-rerunfailures",
    )


def test_a_granted_uv_partition_resolves_the_rerunfailures_probe_into_an_environment(
    tmp_path, monkeypatch
):
    """End to end through `probe_versions`, not just the `launcher` unit above.

    Before the fix this dispatched `("uvx", "python", "-c", ...)`: a bare
    interpreter with `pytest-rerunfailures` never installed, on every partition
    and every grant - the opposite of `grimp` and `hypothesis`, whose hardcoded
    `--with <pkg>` is only safe because they are `in_env=False` everywhere.
    """
    recorded = []
    monkeypatch.setattr("run_python_fixture_lens._run", _fake_run(recorded))
    probe_versions("uv", "target-execution", tmp_path, timeout=5)
    expected = ("uv", "run", "--with", "pytest-rerunfailures") + VERSION_PROBE[
        "pytest-rerunfailures"
    ]
    assert expected in {tuple(c) for c in recorded}


def test_the_uv_partition_still_probes_the_tool_its_sbom_route_never_runs(
    tmp_path, monkeypatch
):
    """End to end through `probe_versions`, not just the `launcher` unit above.

    The unit test fixes the argument; only this one fixes the call site, and the
    call site is the whole of the behaviour: drop the override there and the
    probe dispatches a bare `cyclonedx-py --version` on the partition whose
    record names another tool's command, recording a missing tool as this tool's
    version.
    """
    recorded = []
    monkeypatch.setattr("run_python_fixture_lens._run", _fake_run(recorded))
    probe_versions("uv", "target-execution", tmp_path, timeout=5)
    expected = ("uvx", "--from", "cyclonedx-bom") + VERSION_PROBE["cyclonedx-py"]
    assert expected in {tuple(c) for c in recorded}
