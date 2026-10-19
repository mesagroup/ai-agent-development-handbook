"""Tests for scripts/run_python_fixture_lens.py (#45).

The harness reads a row from one of two places, and that split is what most of
these tests are about. A record declaring its commands as `routes:` data is read
directly, so there is no transcription to guard: the record is what runs. A
record whose fallback still lived in prose was transcribed into the harness's own
table; that table is empty since the docs and security migration, the guards on
the transcription were dissolved with it (see the note where they stood), and
what remains here is the routed-row properties, the engine-owned tables, and the
prose extractor's example tests over synthetic text.

So a property here reads every row the harness runs, over both enumeration
paths, and the two guards about the table itself read `INVOCATIONS` by name:
that it is empty, and that no migrated record has a row in it.

**What the extractor reads, and the one thing it accepts not seeing.** A
prescription is found in a record's inline backtick spans, so two other shapes
escape it. A command in a fenced block is refused by the
loader rather than read here, because a fence is the idiomatic way to write a
command and would hide one in plain sight. A command written in prose with no
backticks at all is an accepted limit: reading unbackticked prose is not
mechanical, and it is the wrong goal anyway, since the answer is the convention
that every prescribed command appears in a span - stated in `CLAUDE.md` and
enforced for the shape that could otherwise satisfy it by accident. What the
limit costs is stated rather than minimised: an undecorated flag beside a
command whose span is already correct escapes every property here, because the
span it would have to change is unchanged. That is cheaper to hit than a fence,
being what someone writes while editing prose rather than documenting a command,
and the convention is the only thing standing against it.
"""

import ast
import json
import os
import re
from contextlib import contextmanager
from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace

import pytest
from audit_checks import (
    SKILLS_DIR,
    Route,
    _project_needs,
    _project_tooling,
    load_checks,
)
from build_python_fixtures import PINNED_MANAGERS
from python_fixture_spec import (
    DEPS_CHECKS,
    EXPECTATIONS,
    FULL_PARTITION,
    ISOLATION_TIMEOUT_SECONDS,
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
    SUPPLIED,
    SUPPLIED_REQUIREMENTS,
    TOOL_PACKAGES,
    VENV_BIN,
    VERSION_PROBE,
    Completion,
    Invocation,
    Supplied,
    _fixture_env,
    _forms_for,
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
    routed_invocations,
    run_partition,
    tools_named_in_records,
)

SKILLS = Path(__file__).resolve().parents[2] / ".agents" / "skills"


def _record_path(check: str) -> Path:
    domain, slug = check.split("/")
    return SKILLS / f"{domain}-audit" / "checks" / f"{slug}.md"


def _tokens(text: str) -> list[str]:
    """The words of a record span or a command, with Markdown's decoration removed.

    A record writes a command inside backticks and inside a sentence, so the raw
    split never matches: ``` `cyclonedx-py`'s ``` has to reduce to the command
    name and `metadata,` to the word. A token that strips to nothing keeps its
    raw form instead, because `.` is `deptry .`'s argument rather than
    punctuation, and dropping it would make `deptry .` and `deptry` one
    command, so a completion the round added would read as the record's own
    prescription.
    """
    out = []
    for raw in text.split():
        word = raw.strip('`*.,;:()[]!?"')
        word = re.sub(r"`?'s$", "", word).strip("`")
        out.append(word or raw)
    return out


#: The characters a head may end at for the mark after it to mean anything. Each
#: introduces a value rather than continuing an *option name*, which is the whole
#: of the claim: nothing but `--cov=<pkg>` is spelled `--cov=`, so no other flag
#: can satisfy that head. `file://` and `https://pypi.org/pypi/` are the same
#: shape, and both are real tree tokens rather than illustrations. `@` is here
#: because it is npm's version delimiter and this family prescribes `npx` and
#: `dlx` commands, so `pkg@<version>` is one record edit away - and for that
#: shape the guard's usual remedy of writing the value space-separated does not
#: exist.
#:
#: What the delimiter does not buy on its own is unambiguity among *values* that
#: share a namespace prefix: a mark reduced to `@stryker-mutator/` alone is
#: satisfied by `@stryker-mutator/core`, a different package named in the same
#: prescribed command. What closes that is the text after the placeholder rather
#: than a better delimiter, so a mark keeps the literal segments around its holes
#: and the delimiter rule below decides only whether the *head* earns one; see
#: `test_a_mark_is_not_satisfied_by_a_sibling_in_the_same_namespace`.
_VALUE_DELIMITERS = "=:/@"


def _marked(wanted: str) -> bool:
    """Whether `_concrete` left this token holes for the caller to fill.

    One place decides what the mark is, because two readers have to agree on it:
    `_matches` fills a marked token's holes, and the coverage property holds
    order among the unmarked tokens and presence for the marked ones. A
    disagreement about which is which would move a token quietly from one rule to
    the other.

    A marked token is its literal segments separated by `<`, one per placeholder
    the record glued into it, so `--cov=<` is a head and an empty tail while
    `@stryker-mutator/<-runner` is a head and a real one. The head is what this
    rule judges; the tail is what `_matches` then demands, and it is the tail
    that separates two packages sharing a namespace.

    The head counts only where a name ends at a value delimiter, which is two
    conditions and not one. Without the delimiter, `-r<` from a record writing
    `-r<file>` is a mark by shape alone and accepts `-rf`, a different flag,
    while `-<` accepts every flag there is. Without the name, `/<` and `=<` are
    marks whose head is the delimiter itself, which accepts any value at all -
    the same "asserts nothing while looking like an assertion" shape surviving at
    one character. Length is the wrong test for both: `-abc<` has a longer head
    than the legitimate `p/<` and degenerates where `p/<` does not.

    An interior segment is refused when it is empty, which is two placeholders
    written adjacent. There is no token a fill could produce that such a mark
    describes, so honouring it would be a comparison that cannot fire - the
    false-clean shape this rule exists to refuse, arriving between the holes
    rather than before them.

    A token still carrying a `>` is refused outright, because only `_concrete`
    makes a mark and `_concrete` consumes every placeholder's `>`. What that
    protects is a record's OWN tokens wherever a caller compares them
    unreduced: `--cov=<pkg>` has a delimited head, so reading it as a mark
    would hole-fill it and let a token writing `<pkg>` be satisfied by one
    writing `<mypkg>`, whose placeholder name merely ends with it. Those two
    are different prescriptions. The invariant `_is_subsequence` names - that
    a record's own tokens close a placeholder with `>` and so compare by
    equality - is stated there and enforced here.

    `test_a_glued_placeholder_needs_a_value_delimiter_before_its_mark` refuses
    every shape this returns False for in a record, so a False here never has to
    stand in as the diagnosis.
    """
    if "<" not in wanted or ">" in wanted:
        return False
    segments = wanted.split("<")
    head = segments[0]
    if len(head) < 2 or head[-1] not in _VALUE_DELIMITERS:
        return False
    return all(segment for segment in segments[1:-1])


def _matches(wanted: str, token: str) -> bool:
    """Whether one command token satisfies one token the record wrote.

    Equality, except for a token `_concrete` reduced to the part before a
    placeholder and left a trailing `<` on as the mark: `--cov=<` is satisfied by
    any token beginning `--cov=` that carries something after it, which is what
    the caller supplied.

    What keeps this from being a blanket prefix test is `_marked`, and both halves
    of that matter. A token with no mark compares by equality, so `-r` is not
    satisfied by `-rf`. A token whose mark sits on a head that does not end at a
    value delimiter is not marked either, so `-r<` also compares by equality: the
    prefix test applies where the head can only be its own option's, never where
    it is a prefix of other options too.

    A record's own tokens never carry a bare `<`, because the placeholder it
    writes closes with `>`, so a caller passing an unreduced record token
    through `_is_subsequence` still gets equality.

    Each hole must consume at least one character. Two literals meeting is not a
    fill: `@stryker-mutator/-runner` satisfies both ends of
    `@stryker-mutator/<-runner` and named no package, and `--cov=` is a flag
    whose value never arrived.
    """
    if _marked(wanted):
        segments = wanted.split("<")
        if not token.startswith(segments[0]) or not token.endswith(segments[-1]):
            return False
        at = len(segments[0])
        for segment in segments[1:-1]:
            found = token.find(segment, at + 1)
            if found < 0:
                return False
            at = found + len(segment)
        return len(token) >= at + 1 + len(segments[-1])
    return token == wanted


def _is_subsequence(needle: list[str], haystack: list[str]) -> bool:
    """Whether every token of `needle` occurs in `haystack`, in order.

    In order but not adjacent, because a record writes a placeholder where the
    caller supplies a value: the form `pytest --cov=<pkg> --cov-branch` reduces
    to the ordered tokens `pytest` and `--cov-branch` with the marked `--cov=<`
    held separately, and the command that fills it carries `--cov=fixture_app`
    between the two, so a contiguity test would fail on that correct entry.

    Token equality goes through `_matches` rather than `==`, but every caller
    passes unmarked tokens, so today that reduces to `==` on every comparison this
    makes: the coverage property passes the tokens it has already filtered to the
    unmarked ones, holding order there and presence separately for the marked
    ones, and a record's own tokens close a placeholder with `>` rather than the
    `<` that marks a truncation. Calling `_matches` is what keeps a marked needle
    behaving as a prefix if a caller ever hands one over, rather than silently
    demanding the mark be matched literally.
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
    checked - which is what `_lead_words` supplies, one call per word, in the
    example tests that exercise the pair. Held to one word either way: a rule matching the name anywhere in the span would
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
    tool's name alone, `_command_forms` returns nothing for those, which reads
    as a record that prescribed nothing at all.
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
    `arch/cycles` wrote "Append `--show-dot` to that `pydeps` invocation", and
    a rule keyed on the tool's name would miss exactly that flag. Reached by
    its example test alone since the flag property was dissolved, and kept as
    part of the extractor the backtick convention cites, whose next subject is
    #58's prose-command gate.
    """
    return {span for span in _spans(paragraph) if span.startswith("-")}


def _concrete(tokens: list[str]) -> list[str]:
    """A record's tokens reduced to the part a command can carry.

    A record writes `<requirements>` where the caller supplies a path, so the
    placeholder can never occur in a command and the token goes. Dropping it is
    what lets the coverage property watch a form that writes one, `pip-audit -r
    <requirements>` being the case it was written for.

    Where the placeholder is glued to the rest of a token, the token is *reduced*
    rather than dropped: each placeholder collapses to a bare `<` and everything
    around it is kept, which `_marked` reads as a mark where the head ends at a
    value delimiter and refuses where it does not. `--cov=<pkg>` becomes
    `--cov=<`, which any `--cov=` token carrying a package name satisfies, and
    `@stryker-mutator/<runner>-runner` becomes `@stryker-mutator/<-runner`, which
    a sibling in the same namespace does not.

    Keeping what follows the placeholder is the whole of that second case. A
    reduction to the head alone made the mark for the runner package satisfied by
    the core package named two tokens earlier in the same prescribed command, so
    an argv that dropped the runner half passed the presence check.

    Dropping the whole token instead reopens the drift this file exists to catch
    - a paragraph that grows `--cov-config=<file>` would reduce to nothing at
    all, `all([])` is vacuously true, and a newly prescribed flag nothing
    transcribes would have passed the flag property, while it stood, in silence. It also degrades the
    coverage property to a check on the lead word alone, since `pytest
    --randomly-seed=<n>` would reduce to `pytest` and be satisfied by an argv
    running the suite bare.

    A token whose `<` never closes keeps the older behaviour of truncating there,
    because there is no placeholder to collapse and the text after an unclosed
    `<` is not a literal a command can be held to. The tree writes none - every
    glued placeholder in it closes - so this is a defined edge rather than a case
    the records exercise.
    """
    out = []
    for token in tokens:
        if "<" not in token:
            out.append(token)
            continue
        reduced, at = [], 0
        while at < len(token):
            if token[at] != "<":
                reduced.append(token[at])
                at += 1
                continue
            reduced.append("<")
            closed = token.find(">", at)
            if closed < 0:
                break
            at = closed + 1
        collapsed = "".join(reduced)
        # A token that is only holes says nothing a command can be held to, and
        # a standalone `<requirements>` is exactly that: dropping it is what lets
        # the coverage property watch a form that writes one.
        if not collapsed.startswith("<"):
            out.append(collapsed)
    return out


def every_invocation() -> tuple[Invocation, ...]:
    """Every row the harness runs, over both enumeration paths.

    `INVOCATIONS + routed_invocations()`, named for what it returns rather
    than for how it is built. A property about what a run does - which tool
    a row names, whether a placeholder reaches a command, how a tool is
    launched, whether the engine can grade its exit code - has to read this
    to still cover the checks that migrated; reading `INVOCATIONS` alone
    would silently stop watching them while staying green. The tests that name
    `INVOCATIONS` directly are the two about the table itself, that it is
    empty and that no migrated record has a row in it, and the set unions that
    spell both paths by hand.
    """
    return tuple(INVOCATIONS) + routed_invocations()


def _prescribed_commands(inv: Invocation) -> list[tuple[str, tuple[str, ...]]]:
    """Every distinct command this entry says its record prescribes.

    Labelled by the first partition naming it, and distinct rather than one row
    per partition: `prescribed` answers a shared `argv` for all five, so a
    per-partition list would report one command as five routes in every failure
    message an entry with a shared argv produces.

    A supplied route is not here. It is authored round-side rather than
    transcribed from a record - in the `SUPPLIED` overlay, keyed `(check, tool)`
    - so it answers to no declaration the record makes:
    `deps/vulnerabilities` declares `pip-audit -r <requirements>` `superseded`
    truthfully while the uv partition's supplied route runs that form. Excluding
    it is what keeps that from reading as a contradiction, rather than what stops
    a comparison firing - a supplied step is written in full, including the
    runner that fetches its tool, so it does not equal a form the record writes
    bare in any case.
    """
    out: dict[tuple[str, ...], str] = {}
    for partition in PARTITIONS:
        argv = inv.prescribed(partition)
        if argv and argv not in out:
            out[argv] = partition
    return [(partition, argv) for argv, partition in out.items()]


def _runs_as_written(command: tuple[str, ...], form: str) -> bool:
    """Whether the command is this form exactly and carries nothing else.

    Equality rather than containment, because a record supersedes a form by
    extending it as often as by replacing it: `pydeps --show-cycles` is
    superseded by the same command carrying `--show-dot`, and every `superseded`
    form in the family is a subsequence of the command that narrows it. Asking
    whether a command *contains* such a form answers yes for a correct entry.

    A placeholder standing as its own word matches whatever the caller supplied
    there, and counts as one token while it does. `_concrete` cannot serve here
    even though it serves everywhere else in this file: it *drops* such a token
    rather than truncating it, so `pip-audit -r <requirements>` would reduce to
    two words, never equal the three-word command that fills it, and report the
    form as one nothing runs - a comparison that cannot fire, reading exactly
    like an entry with nothing to find. A placeholder glued to a flag still goes
    through `_concrete`, where truncating leaves the flag as a prefix `_matches`
    can satisfy - where the head ends at a value delimiter. Where it does not,
    `-r<file>` being the shape, the truncation is compared by equality and the
    record is refused by the guard rather than matched loosely.
    """
    wanted = _tokens(form)
    tokens = _tokens(" ".join(command))
    if len(wanted) != len(tokens):
        return False
    for want, token in zip(wanted, tokens, strict=True):
        if want.startswith("<") and want.endswith(">"):
            continue
        reduced = _concrete([want])
        if not reduced or not _matches(reduced[0], token):
            return False
    return True


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

    This is what lets the coverage property watch a form that writes a
    placeholder as its own token, `<requirements>` on `deps/vulnerabilities`
    being the case it was written for.
    """
    assert _concrete(_tokens("pip-audit -r <requirements> --no-deps")) == [
        "pip-audit",
        "-r",
        "--no-deps",
    ]


def test_a_placeholder_glued_to_a_flag_keeps_the_literals_around_it():
    """`--cov=<pkg>` is the same phenomenon, and dropping it goes too far.

    A record writes the value the caller supplies inside the flag, so no command
    can carry that token as written. Left whole, a form carrying `--cov=<pkg>`
    reads as one the harness does not run. Dropped whole, the flag stops being
    held at all, which is worse: it is the drift shape these properties exist to
    catch.

    What survives the reduction is every literal the record wrote, not the head
    alone - a placeholder in the middle leaves a head and a tail, and a token
    carrying two leaves an interior segment between them.
    """
    assert _concrete(_tokens("pytest --cov=<pkg> --cov-branch")) == [
        "pytest",
        "--cov=<",
        "--cov-branch",
    ]
    assert _concrete(_tokens("pip-audit -r <requirements>")) == ["pip-audit", "-r"]
    assert _concrete(["@stryker-mutator/<runner>-runner"]) == [
        "@stryker-mutator/<-runner"
    ]
    assert _concrete(["https://pypi.org/pypi/<name>/<version>/json"]) == [
        "https://pypi.org/pypi/</</json"
    ]


def test_every_glued_placeholder_the_routes_carry_keeps_its_behaviour():
    """The five tokens in the tree's route argvs, each read through the change.

    The reduction's representation changed, so "nothing went red" is evidence
    about the tree and not about these five: four of them have an empty tail and
    must behave exactly as they did, and the fifth is the one this change exists
    for. Asserting each is what separates the two.

    Computed rather than restated: five glued tokens across three routes in two
    records, `test/determinism`'s two seeds and `test/mutation`'s three spellings
    of the Stryker runner package. The guard below holds the tree's own count at
    zero offenders; this holds each token's meaning.
    """
    seeds = _concrete(["--randomly-seed=<n>", "--sequence.seed=<n>"])
    assert seeds == ["--randomly-seed=<", "--sequence.seed=<"]
    assert _matches(seeds[0], "--randomly-seed=4242")
    assert not _matches(seeds[0], "--randomly-seed=")
    assert not _matches(seeds[0], "--randomly-seed-extra=4242")
    assert _matches(seeds[1], "--sequence.seed=4242")
    assert not _matches(seeds[1], "--sequence.seed=")

    # The three Stryker spellings, including the `pnpm` override whose head ends
    # at `/` rather than at the `=` earlier in the same token.
    bare = _concrete(["@stryker-mutator/<runner>-runner"])[0]
    flagged = _concrete(["--package=@stryker-mutator/<runner>-runner"])[0]
    assert flagged == "--package=@stryker-mutator/<-runner"
    for mark, core, runner in (
        (bare, "@stryker-mutator/core", "@stryker-mutator/jest-runner"),
        (
            flagged,
            "--package=@stryker-mutator/core",
            "--package=@stryker-mutator/jest-runner",
        ),
    ):
        assert _marked(mark)
        assert not _matches(mark, core)
        assert _matches(mark, runner)


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


def test_a_mark_on_a_head_that_is_a_prefix_of_other_flags_is_not_a_mark():
    """The one shape of this file's own matching that failed the clean way.

    `_concrete` truncates at the `<` whatever the head looks like, so a record
    writing `-r<file>` yields `-r<` and one writing `-<n>` yields `-<`. Read as a
    prefix, the first accepts `-rf`, a different flag, and the second accepts
    every flag there is - a token that asserts nothing while looking like an
    assertion, which is the false-clean direction and the reason this is the hole
    worth closing rather than the two that only fail to see a prescription.

    The delimiter is what separates these rows from the `--cov=` rows above, and
    it is the property rather than the length: `-abc<` has a longer head than the
    legitimate `p/<` and degenerates where `p/<` does not. A head that is nothing
    but the delimiter degenerates too, which is the `/<` row. So each of these
    compares by equality, which no real command token satisfies - and a record
    that writes one is refused by
    `test_a_glued_placeholder_needs_a_value_delimiter_before_its_mark` rather than
    left to fail here as a token it did write going missing.
    """
    assert not _matches("-r<", "-rf")
    assert not _matches("-r<", "-rrequirements.txt")
    assert not _matches("-<", "-x")
    assert not _matches("-<", "--verbose")
    assert not _matches("-abc<", "-abcd")
    assert not _matches("/<", "/etc/passwd")
    assert not _matches("=<", "=anything")
    assert _matches("file://<", "file:///tmp/fixture")
    assert _matches("@stryker-mutator/<", "@stryker-mutator/jest-runner")
    assert _matches("p/<", "p/ci")


def test_a_record_token_that_still_closes_its_placeholder_is_not_a_mark():
    """The invariant `_is_subsequence` rests on, enforced rather than assumed.

    A mark is what `_concrete` leaves behind, and `_concrete` consumes every
    placeholder's `>`. So a token still carrying one was never reduced, and a
    caller comparing a record's own tokens unreduced is passing exactly those.

    Reading such a token as a mark is the false-clean direction. `--cov=<pkg>`
    has a delimited head, so hole-filling it would let a token writing `<pkg>` be
    satisfied by one writing `<mypkg>` - a different prescription whose
    placeholder name merely ends with the first.

    Found by review on this branch: widening the mark from "ends with `<`" to
    "contains `<`" silently took the raw tokens in with the reduced ones.
    """
    assert not _marked("--cov=<pkg>")
    assert not _marked("@stryker-mutator/<runner>-runner")
    assert _matches("--cov=<pkg>", "--cov=<pkg>")
    assert not _matches("--cov=<pkg>", "--cov=<mypkg>")
    assert not _is_subsequence(["--cov=<pkg>"], ["--cov=<mypkg>"])
    # And the reduction of that same token still is a mark, so the refusal is
    # about the `>` rather than about the shape as a whole.
    assert _marked(_concrete(["--cov=<pkg>"])[0])


def test_a_mark_is_not_satisfied_by_a_sibling_in_the_same_namespace():
    """The limit the delimiter rule does not close, closed by the suffix.

    A delimiter makes a head unambiguous among *option names* - nothing but
    `--cov=<pkg>` is spelled `--cov=`. It buys nothing among *values* sharing a
    namespace prefix, and the tree writes one: `test/mutation` prescribes
    `--package @stryker-mutator/core --package @stryker-mutator/<runner>-runner`,
    so a mark that kept only the head was satisfied by the core package named two
    tokens earlier, and an argv that dropped the runner half passed the presence
    check.

    What closes it is the text after the placeholder. A mark carries the literal
    segments around its holes, so `@stryker-mutator/<runner>-runner` demands a
    token that begins `@stryker-mutator/` AND ends `-runner` with something
    between. The head alone no longer decides.

    Asserted through `_concrete` rather than on a hand-written mark, because the
    representation is what changed: a literal would test this file's encoding of
    a mark, and what is worth holding is the contract from the token a record
    writes to the tokens a command may carry.
    """
    mark = _concrete(["@stryker-mutator/<runner>-runner"])[0]
    assert _marked(mark)
    assert not _matches(mark, "@stryker-mutator/core")
    assert _matches(mark, "@stryker-mutator/jest-runner")
    assert _matches(mark, "@stryker-mutator/vitest-runner")
    # The hole is not optional: the two literals meeting is not a fill.
    assert not _matches(mark, "@stryker-mutator/-runner")
    # A sibling long enough that the length floor alone would admit it. The
    # tree's own `@stryker-mutator/core` is shorter than the two literals put
    # together, so it is refused whether or not the tail is demanded - which
    # makes it, on its own, evidence for the wrong property. This row is the one
    # that fails when the tail stops being read, found by mutating that demand
    # away and watching the assertions above stay green.
    assert not _matches(mark, "@stryker-mutator/core-runner-plugin")


def _unverifiable_glue(concrete: str) -> bool:
    """Whether this truncated token is one no reader here can verify.

    A token `_concrete` reduced but `_marked` will not honour. Two shapes reach
    it: a head that does not end at a value delimiter, so the mark is there and
    the head does not earn it; and two placeholders written adjacent, whose empty
    interior segment describes no token a fill could produce. Split out from the
    guard below so the detection is testable on a literal - a guard whose only
    input is the tree passes for two different reasons, one of them being that
    `_marked` regressed and now honours everything.
    """
    return "<" in concrete and not _marked(concrete)


def test_the_unverifiable_shapes_are_detected_on_literals():
    """The guard's own detection, held on tokens rather than on the tree.

    The tree carries none of the refused shapes, so the guard below cannot show
    that it would catch one. These are the shapes `_marked` refuses - a head that
    does not end at a value delimiter, and two placeholders written adjacent -
    and the ones the tree actually writes, each read through the same predicate
    the guard uses.

    `pkg@<a><b>` is the adjacent pair, which has a delimiter and still describes
    no token: the empty segment between its holes is a literal a fill can never
    produce. The pypi URL is its legitimate neighbour, two holes with a real
    segment between them, and the tree writes it twice.
    """
    assert _unverifiable_glue(_concrete(["-r<file>"])[0])
    assert _unverifiable_glue(_concrete(["-<n>"])[0])
    assert _unverifiable_glue(_concrete(["coverage.<n>.xml"])[0])
    assert _unverifiable_glue(_concrete(["pkg@<a><b>"])[0])
    assert not _unverifiable_glue(_concrete(["--cov=<pkg>"])[0])
    assert not _unverifiable_glue(_concrete(["file://<dir>"])[0])
    assert not _unverifiable_glue(_concrete(["pkg@<version>"])[0])
    assert not _unverifiable_glue(
        _concrete(["https://pypi.org/pypi/<name>/<version>/json"])[0]
    )


def test_a_glued_placeholder_needs_a_value_delimiter_before_its_mark():
    """No record writes a glued placeholder this file cannot verify.

    `_matches` refusing to treat `-r<` as a mark makes the matcher safe and makes
    a record writing `-r<file>` fail somewhere unhelpful: the token is real, no
    command token equals it, and the coverage property reports it missing - and
    on the routes schema it fails as a bare tuple, having lost the named
    diagnosis the `supplied` branch used to give it. This is where that shape is
    named instead, so the fix is legible.

    Every field a record can write a command in is read, because they are
    different fields and only one of them has backticks: the prose spans, and
    each route's `argv`, `argv_by_partition` and `then`. Five glued tokens across
    three routes in two records live in the argv fields, so a guard reading spans
    alone would be reading the field the shape is least likely to appear in.

    `then` is read because it is a prescribed command too, not because anything
    in the tree needs it: one route carries a `then` and it has no placeholder at
    all. A `then` on a `runs` route gives that row a second `runs` form, and that
    form goes through `_concrete` and the ordered/supplied split exactly as the
    argv's does, so unverifiable glue there would fail as the bare tuple this
    guard exists to replace. Found by review, having been left out on the
    assumption that a command lives in an argv.

    The floor is the tree's own count and the tree's count is zero, so this fires
    on the first such token rather than on a number that has to be maintained.
    """
    offenders = []
    for path in sorted(SKILLS.rglob("*.md")):
        if path.parent.name != "checks":
            continue
        for span in _spans(path.read_text()):
            for concrete in _concrete(_tokens(span)):
                if _unverifiable_glue(concrete):
                    offenders.append(
                        f"{path.relative_to(SKILLS)}: span {span!r} -> {concrete!r}"
                    )
    checks, errors = load_checks(SKILLS_DIR)
    assert errors == [], errors
    for cid, check in sorted(checks.items()):
        for route in check.routes or ():
            argvs = [("argv", route.argv or ()), ("then", route.then or ())]
            argvs += [
                (f"argv_by_partition[{name}]", argv)
                for name, argv in sorted((route.argv_by_partition or {}).items())
            ]
            for field, argv in argvs:
                for concrete in _concrete(list(argv)):
                    if _unverifiable_glue(concrete):
                        offenders.append(f"{cid} {route.lang} {field}: -> {concrete!r}")
    assert offenders == [], (
        "a placeholder glued to a head that does not end at a value delimiter "
        f"({_VALUE_DELIMITERS!r}) cannot be verified: the head is a prefix of "
        "other tokens too, so matching it would accept a different flag or a "
        "different file. Write the value as its own token where the command "
        "allows it, as `pip-audit -r <requirements>` does. Where it does not - a "
        "placeholder in the middle of a value, or one inside single quotes, which "
        "`_tokens` keeps where it strips a double quote - the shape has to change "
        "rather than the spacing:\n  " + "\n  ".join(offenders)
    )


def test_a_form_led_by_a_runner_is_found_through_the_argvs_own_first_word():
    """The extraction the tool-name rule cannot reach.

    An entry whose prescribed command is led by something other than the tool
    being checked declares no form at all under a rule keyed on the tool's own
    name, and an entry declaring no form is indistinguishable from a record
    that prescribes nothing. A pytest plugin is that shape by construction: the
    thing installed and the thing invoked are different names, and the record
    writes the invocation.

    Both sides are built here rather than read out of a live record: a routed
    row carries no copy of its record's prose, so the paragraph half cannot be
    read off a record once that record migrates, and re-pointing this at
    whichever record is still on the legacy schema buys one stage of green.
    The sentence is the one `test/determinism` carried while its fallback
    lived in prose, and the entry carries that record's `pytest-randomly` argv
    and tool - which is all `_lead_words` reads, so the row's other fields are
    left off rather than transcribed.
    """
    inv = Invocation(
        check="test/determinism",
        tool="pytest-randomly",
        argv=("pytest",),
        in_env=True,
    )
    assert _lead_words(inv) == {"pytest", "pytest-randomly"}
    paragraph = (
        "`pytest-randomly` randomizes the order as soon as it is installed, so "
        "the command is `pytest` itself; re-run a failing order with `pytest "
        "--randomly-seed=<n>`."
    )
    assert _command_forms(paragraph, "pytest-randomly") == set()
    assert _command_forms(paragraph, "pytest") == {"pytest --randomly-seed=<n>"}


def test_a_lead_word_stays_one_word_so_a_neighbours_command_is_not_pulled_in():
    """The reason this is not simply "the tool's name occurs anywhere in the span".

    A record naming `uv pip list --outdated` and `pip list --outdated` in one
    sentence gives the `pip` entry a neighbour whose command carries its own
    name. An anywhere-in-the-span rule would attribute the first to that entry,
    which would then have to declare a form it never runs; keyed on the argv's
    own first token, it leads with `pip` and sees only its own.

    Both sides are built here rather than read out of a live record, so the
    property survives the migration of whichever record happens to be that
    shape today: the sentence is the one `deps/freshness` carried while its
    fallback lived in prose, and the entry is that record's `pip` row.
    """
    inv = Invocation(
        check="deps/freshness",
        tool="pip",
        argv=("pip", "list", "--outdated"),
    )
    assert _lead_words(inv) == {"pip"}
    paragraph = (
        "`uv pip list --outdated` / `pip list --outdated`, both of which read "
        "the installed environment rather than the lockfile."
    )
    extracted = set()
    for lead in _lead_words(inv):
        extracted |= _command_forms(paragraph, lead)
    assert extracted == {"pip list --outdated"}
    assert all(not form.startswith("uv ") for form in extracted), extracted


def test_a_shared_argv_is_one_command_rather_than_one_per_partition():
    """The label names the first partition carrying it, and the command is distinct.

    An entry with a shared `argv` prescribes one command, and `prescribed`
    answers with it for every partition. Listed once per partition instead, a
    failure message would name five identical commands and a reader would look
    for five routes.
    """
    shared = Invocation(
        check="deps/hygiene",
        tool="deptry",
        argv=("deptry",),
        completion=(".",),
        note="deptry takes the path to scan and the record names none",
    )
    assert _prescribed_commands(shared) == [("uv", ("deptry",))]
    split = Invocation(
        check="deps/inventory",
        tool="cyclonedx-py",
        argv_by_partition=(
            ("uv", ("cyclonedx-py", "environment")),
            ("pip", ("cyclonedx-py", "requirements")),
        ),
    )
    assert _prescribed_commands(split) == [
        ("uv", ("cyclonedx-py", "environment")),
        ("pip", ("cyclonedx-py", "requirements")),
    ]


def test_a_command_carrying_a_form_is_not_the_same_as_running_it():
    """Containment cannot be the test, so equality is.

    A record commonly supersedes a form by *extending* it, and every
    `superseded` form in the family is a subsequence of the longer command that
    narrows it. A containment rule would fire on all of them. Equality asks the
    question that matters instead: whether the harness runs the form the record
    warns against and nothing more.
    """
    narrowed = ("pydeps", "--show-cycles", "--show-dot")
    assert not _runs_as_written(narrowed, "pydeps --show-cycles")
    assert _runs_as_written(("pydeps", "--show-cycles"), "pydeps --show-cycles")
    assert _runs_as_written(narrowed, "pydeps --show-cycles --show-dot")


def test_a_form_the_record_writes_with_a_placeholder_compares_as_written():
    """`pip-audit -r <requirements>` against the file the caller supplied.

    A placeholder standing as its own word is one token and matches whatever
    filled it. Reducing the form with `_concrete` first is what breaks this
    comparison rather than helping it: that drops such a token instead of
    truncating it, leaving a two-word form that can never equal the three-word
    command, so the form reports as one nothing runs - a comparison that cannot
    fire reads exactly like an entry with nothing to find. A placeholder glued to
    a flag is the case `_concrete` does serve, and both paths are held here.
    """
    assert _runs_as_written(
        ("pip-audit", "-r", "requirements.txt"), "pip-audit -r <requirements>"
    )
    assert not _runs_as_written(
        ("pip-audit", "-r", "requirements.txt", "--no-deps"),
        "pip-audit -r <requirements>",
    )
    assert _runs_as_written(("pytest", "--cov=fixture_app"), "pytest --cov=<pkg>")
    assert not _runs_as_written(("pytest", "--cov"), "pytest --cov=<pkg>")


def test_every_python_tool_in_the_family_is_invoked():
    invoked = {i.tool for i in INVOCATIONS} | {i.tool for i in routed_invocations()}
    assert invoked == tools_named_in_records()


def test_no_check_invokes_the_same_tool_twice():
    """Held over both enumeration paths: a duplicate row runs the same command twice.

    `routed_invocations()` cannot produce one on its own - it groups by tool
    per check - so the only way this fails is a (check, tool) pair straddling
    both tables, which is exactly what a hand-written entry surviving its
    record's migration would look like.
    """
    pairs = [(i.check, i.tool) for i in every_invocation()]
    assert len(pairs) == len(set(pairs))


def test_a_tool_answering_several_checks_is_invoked_once_per_check():
    """The whole set, not a subset of it.

    A superset assertion passes on a table that has quietly grown a ruff entry
    for a check whose record never offered ruff, which is the mistranscription
    the per-check split exists to make visible. Read over both enumeration
    paths: `arch/complexity` and `arch/complexity-gate` name ruff through their
    routes now, not through a hand-written entry.
    """
    ruff_checks = {i.check for i in INVOCATIONS if i.tool == "ruff"} | {
        i.check for i in routed_invocations() if i.tool == "ruff"
    }
    assert ruff_checks == {
        "arch/complexity",
        "arch/complexity-gate",
        "docs/docstring-coverage",
        "security/crypto",
        "security/dangerous-calls",
        "security/injection",
        "security/unsafe-io",
    }


# Five properties stood here until the docs and security migration: every
# invocation quotes its record verbatim, every command form the record names is
# declared, every flag the record names occurs in a declared form, a
# prescription stays in the paragraph the guard watches, and a form naming a
# lead word off the front is led by some invocation; and, further down, the two
# completion-provenance guards, that folding a completion into the argv breaks
# the anchor and that a token the record prescribes never hides in the
# completion, which pinned a count of five completed rows and the one `D`
# exception. Each held a hand-written
# `INVOCATIONS` row against the `## Tooling fallback` prose it transcribed, and
# each was scoped to `PROSE_FALLBACK_CHECKS`. That table is empty now: every
# record the harness invokes declares `routes:`, so a row's command is read from
# the record's own data by `routed_invocations` and there is no transcription
# left to drift from. The properties were dissolved rather than kept vacuous,
# because a property scoped to an empty set passes over anything, and rather
# than restated against the routes, because the routes side already carries
# its own equalities (`test_the_harness_runs_exactly_the_checks_the_expectations_declare`,
# `test_no_migrated_check_has_a_hand_written_entry`). The field the quote
# lived in, `record_quote`, then left `Invocation`, and with it went every
# reader of a transcription: the anchor and order helpers that traced a
# command through the quote, the completion-demotion helper, and the
# paragraph selectors over a `## Tooling fallback` section, each reached by
# nothing but its own example test once the properties were gone; the three
# hand-written-table loops that had been left in place to hold nothing - the
# quote-is-a-sentence, command-in-the-quote and tool-its-record-offers
# guards, the one-transcription split, and the two-command order held against
# the quote - went with it, the last restated below against the routes. The
# prose extractor itself stays. `_spans` is reached by
# `test_a_glued_placeholder_needs_a_value_delimiter_before_its_mark`, which
# sweeps every record's spans through it, the records still on `tooling:`
# included, and the backtick convention `CLAUDE.md` states cites that sweep
# as its reason. `_command_forms`, `_lead_words` and `_flag_spans` are
# reached by their example tests alone, and are kept on the reading the
# migration recorded for a helper an example test exercises, because they are
# the form extractor the convention names and #58's prose-command gate, which
# #69 ticks, is their next subject. What separates them from the nine deleted
# above is what they read: a span in any paragraph, rather than a
# transcription or a `## Tooling fallback` section, subjects that cannot
# return without `record_quote`.


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
    """Every one of `DEPS_CHECKS` has migrated, and the claim is about the harness.

    Read over the union rather than `INVOCATIONS` alone, which is what makes
    that survivable: a `deps/` check that migrates keeps its row in
    `routed_invocations()` instead, and a property still reading only the
    hand-written table would report all six as dropped. The claim is that the
    harness runs them, not which path it finds them on.
    """
    assert set(DEPS_CHECKS) <= {i.check for i in every_invocation()}


# --- the exact-set guard -------------------------------------------------------


def test_no_migrated_check_has_a_hand_written_entry():
    """Two enumeration paths, and a row belongs to exactly one.

    A stale entry is the silent failure this change opens: it keeps a check
    running after its record stops being the source, so editing the record
    has no effect on the run and nothing goes red. Held on the schema the
    record declares rather than on a list of check ids, so a record migrating
    in stage 4 fails here until its entry goes.
    """
    checks, errors = load_checks(SKILLS_DIR)
    assert not errors, errors
    migrated = {cid for cid, c in checks.items() if c.routes}
    stale = sorted({i.check for i in INVOCATIONS} & migrated)
    assert not stale, (
        f"{stale} declare routes and still have a hand-written entry, so the "
        "record is no longer what the run reads"
    )


def test_the_hand_written_table_is_empty_because_every_invoked_record_declares_routes():
    """`INVOCATIONS` is empty, and the emptiness is the claim.

    Until the docs and security migration this test named the five records
    whose commands still lived in prose and pinned their row count as a
    ratchet. Those five declare `routes:` now, and every record the harness
    invokes reads its own routes through `routed_invocations`, so a
    hand-written row would be a second copy of a command the record already
    states as data - which `test_no_migrated_check_has_a_hand_written_entry`
    refuses. Asserting emptiness rather than deleting the test keeps the
    table's meaning stated: a record authored on the legacy schema and
    invoked by the harness would have to add a row here, and this would fail
    until whoever adds it says why the record is not on routes.
    """
    assert INVOCATIONS == ()


def test_the_harness_runs_exactly_the_checks_the_expectations_declare():
    """Three views of one set, held equal, over both enumeration paths.

    The records carrying a `python:` entry are what the round exists to
    exercise; the expectations are what each one is graded against; the
    harness is what runs them. A check present in any one of the three and
    missing from another is either a check nobody grades or a claim nobody
    tests, and both look like a complete run.

    The harness's view is a union whose hand-written half is empty: entries for the checks
    whose fallback lives in prose, routed rows for the records that declare
    their routes. A check dropped by the enumeration, invented by it, or
    claimed by both paths fails here.
    """
    checks, errors = load_checks(SKILLS_DIR)
    assert not errors, errors
    with_python = {c.id for c in checks.values() if c.tooling.get("python")}
    from_table = {i.check for i in INVOCATIONS}
    from_records = {r.check for r in routed_invocations()}
    assert from_table | from_records == with_python, sorted(
        (from_table | from_records) ^ with_python
    )
    assert not from_table & from_records
    assert {e.check for e in EXPECTATIONS} == with_python


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
    enumerated = {(i.check, i.tool) for i in INVOCATIONS} | {
        (i.check, i.tool) for i in routed_invocations()
    }
    assert enumerated == declared


# --- version routes -------------------------------------------------------------


def test_every_invoked_tool_has_a_version_route_or_a_stated_absence():
    invoked = {inv.tool for inv in INVOCATIONS} | {
        inv.tool for inv in routed_invocations()
    }
    assert set(VERSION_PROBE) == invoked


def _tools_owing_a_stated_reason(probes: dict, stated: dict) -> tuple[set, set]:
    """The two ways a `None` probe and its stated reason can fail to match up.

    Returns the tools whose probe is `None` with no usable reason beside it, and
    the tools named as having no route while carrying a real probe. Both are
    drift, in opposite directions, and neither has an instance in the live
    tables - `NO_VERSION_ROUTE` is empty and no `VERSION_PROBE` value is
    `None`, so a property holding this over the tables alone iterates nothing.
    That is why the rule is a function: the property below reads the live
    tables and the example test beside it reads literals, so the rule keeps a
    subject the tables do not currently supply.
    """
    unexplained = {
        tool
        for tool, argv in probes.items()
        if argv is None and not (stated.get(tool) or "").strip()
    }
    stale = {tool for tool in stated if probes.get(tool) is not None}
    return unexplained, stale


def test_a_tool_with_no_version_route_says_so_by_name():
    """`None` is a positive claim, so it travels with a reason - never silently.

    The reverse direction is checked too, mirroring `ungranted_note`'s vacuity
    rule: a name in `NO_VERSION_ROUTE` for a tool that *does* carry a probe would
    be a stale reason nothing reads, which is the same kind of drift a leftover
    `ungranted_note` would be.

    Both tables are empty of the shape this reads - measured, not assumed:
    `NO_VERSION_ROUTE` is `{}` and every `VERSION_PROBE` value is a real argv.
    So this holds the rule over a population of nothing and passes, which is
    the failure this file has twice had to repair elsewhere. The rule itself is
    exercised by `test_a_missing_probe_and_a_stale_reason_are_both_drift`
    below, over literals; what this one contributes is that the live tables
    have not grown an instance nobody explained.
    """
    unexplained, stale = _tools_owing_a_stated_reason(VERSION_PROBE, NO_VERSION_ROUTE)
    assert not unexplained, (
        f"{sorted(unexplained)} have no version probe and no stated reason"
    )
    assert not stale, (
        f"NO_VERSION_ROUTE names {sorted(stale)}, which carry a real probe"
    )


def test_a_missing_probe_and_a_stale_reason_are_both_drift():
    """The rule above, on tables written here, because the live ones hold neither.

    Four cases, and the pairs are what make the rule more than a spelling of
    `set(stated) <= {t for t, a in probes.items() if a is None}`: a `None`
    probe whose reason is present but blank is as silent as one with no reason
    at all, which is why the live property strips before believing it.
    """
    explained = {"t": None}
    assert _tools_owing_a_stated_reason(explained, {"t": "why"}) == (set(), set())
    assert _tools_owing_a_stated_reason(explained, {}) == ({"t"}, set())
    assert _tools_owing_a_stated_reason(explained, {"t": "   "}) == ({"t"}, set())
    assert _tools_owing_a_stated_reason({"t": ("t", "--version")}, {"t": "why"}) == (
        set(),
        {"t"},
    )


# --- completions and routed rows -----------------------------------------------


def test_a_completed_argv_says_why_it_had_to_be_completed():
    """The completion is the finding, so it never travels without its reason.

    A record whose command does not run as written is what the round is looking
    for. Completing it silently turns that finding into a clean run, so the
    dataclass refuses a completion with no note and this holds the refusal.

    `Invocation.__post_init__` raises on a completion with no note for any
    instance, routed or hand-written, so no loop over either population can
    observe a violation; the `pytest.raises` call is the whole exercise, and
    the loop that used to precede it over the hand-written table went with
    `record_quote` rather than staying to hold nothing over an empty table.
    """
    with pytest.raises(ValueError, match="completion"):
        Invocation(
            check="arch/cycles",
            tool="pydeps",
            argv=("pydeps",),
            completion=("src",),
        )


def test_a_routed_row_prescribing_no_command_carries_the_records_reason():
    """The artifact says why a row ran nothing, in the record's own words.

    `note` is written into the results row, so a row prescribing no command
    and carrying no reason degrades the round's output rather than only its
    docstrings: a reader sees an empty explanation where the record has one.
    The reason is the record's, not this module's, which is the whole of why
    it is read rather than transcribed.

    A per-partition command is a command for this property's purposes, which is
    why `argv_by_partition` is skipped beside `argv`: such a row prescribes a
    command on the partitions its map names, and `routed_invocations` leaves
    its `note` empty for the same reason it does on a shared argv - a command
    that ran as written explains itself. What the record says about the
    partitions the map does not name stays on the route, which is where a
    reader of the record finds it; a row-level note would be a second copy of
    it keyed on the row rather than on the partition it is about.
    """
    for row in routed_invocations():
        if row.argv or row.argv_by_partition or row.completion:
            continue
        assert row.note, (row.check, row.tool)


def test_an_invocation_names_a_check_that_exists_and_a_partition_that_does():
    """Every field naming a partition, not only the one that maps commands.

    `own_runner` is the one where a typo costs nothing visible: `prescribed`
    falls back to a shared `argv` for any string, so an unknown partition passes
    the field's own validation and then suppresses a prefix for a partition that
    never runs. `supplied_by_partition` fails the same silent way and from one
    more direction now that a routed row can carry one: `run_partition` looks a
    supplied route up by the partition it is running, so a misspelt name is a
    route nobody runs and no status reports missing, and neither `Supplied` nor
    `_check_supplied` compares those names against `PARTITIONS` - each is
    checking a shape rather than a vocabulary.

    Reads both paths. It once read `INVOCATIONS` alone, on the premise that
    `routed_invocations` set neither field - true when `argv_by_partition` and
    `own_runner` had no route counterpart, false now that `argv_by_partition`
    and `own_runner` are route fields the enumeration threads. A routed row's
    names do come out subset-of-`PARTITIONS` today, but by construction
    through two guards elsewhere: the enumeration raises on an
    `argv_by_partition` key that is not a partition, and the loader rejects an
    `own_runner` naming a partition the route does not carry. Holding it
    directly here costs one loop and does not depend on either of those
    staying where it is.
    """
    for inv in every_invocation():
        assert _record_path(inv.check).exists(), inv.check
        named = (
            {p for p, _ in inv.argv_by_partition}
            | set(inv.own_runner)
            | {p for p, _ in inv.supplied_by_partition}
        )
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

    Held over both enumeration paths: a routed row fills the same kind of gap
    through `COMPLETIONS`, keyed on `(check, tool)` rather than on which table
    the row belongs to, so a migrated check can carry a bare placeholder in a
    completion exactly as a hand-written one could.

    What it cannot reach is a route no row is built from. This module reads
    `routed_invocations` at its default, `lang: python` routes naming a tool,
    so a placeholder in a
    `lang: any` or `lang: typescript` route's argv is invisible here -
    `test/new-code-coverage`'s `<report>` is the live one. That is not a gap
    to close with a wider rule: several typescript routes prescribe a
    placeholder the caller fills, by the record's own prescription, so a rule
    reading every route's argv would fail on records that are right. The
    reach is the rows the harness runs, and it grows when a lens does.
    """
    for inv in every_invocation():
        for partition in PARTITIONS:
            commands = [argv_for(inv, partition), *inv.supplied(partition)]
            for command in commands:
                for word in command:
                    assert not re.search(r"<[^>]+>", word), (inv.check, word)


# --- the record-to-harness direction -------------------------------------------


def test_a_route_in_the_tree_still_carries_a_then():
    """The two-command shape has not left the tree.

    The order of a two-command route was once held against the record's
    sentence; a routed row's `argv` and `then` are two fields of one route,
    read in that order, so there is nothing to hold and that guard is gone.
    What its emptiness must not be allowed to mean is that the shape left the
    tree: a `then` deleted from the record it was written for would leave
    every `then`-reading property passing over nothing. So the premise is
    asserted here, and the order is the loader's and `routed_invocations`'s to
    keep.
    """
    assert [i for i in routed_invocations() if i.then], (
        "no route carries a `then`, so the two-command shape has left the tree "
        "and every property reading `then` passes by having nothing to read"
    )


def test_every_form_the_harness_runs_appears_in_an_argv():
    """The other half: a form declared `runs` that no command carries.

    The declaration and flag properties, while they stood, compared sets of
    spans and never read a disposition, so each passed on a form declared
    `runs` beside an argv that had stopped matching it. This one holds a
    declared form against the commands the row runs.
    The entry that first needed it was `deps/vulnerabilities`, whose
    placeholder had put it in an exception set the anchor guard, since
    dissolved, then carried, so
    the guard that would have noticed a flag pair being added to the prescribed
    form was switched off for exactly that entry. Dropping the placeholder token
    instead of excusing the entry is what let this property watch it, and the
    exception set went with the entry when that record migrated - so what this
    holds now is the general rule the exception used to carve out of.

    `then` counts as a command of its own: `coverage run -m pytest` and `coverage
    report --show-missing` are one route the record splits in two, and reading
    the argv alone would report the half that prints the report as a form nothing
    runs. Each command comes from `argv_for`, so it carries the entry's
    completion as well, which is what lets a form declare a flag whose value the
    completion supplies: reading the prescribed argv alone would have to drop
    that token instead, and a flag with a glued placeholder would go invisible.
    No form in the tree needs that today - see the paragraph below on what still
    takes the `supplied` branch - so this reads as the mechanism it is rather
    than as an entry to go and look at. Reading two fields of the row is not
    folding a completion into the `argv` field, where nothing could tell it
    from what the record prescribed: the two stay separate fields, and the
    results row renders the prescribed one as `record_argv` on its own.

    Order is held among the tokens the record writes in full, and presence only
    for a token whose tail the caller supplies. That split is what keeps the
    relaxation to the tokens that need it: a completion is appended at the end of
    the command while a record can write the token it supplies inside the form,
    so an ordered test over the whole form fails on a form like `pytest
    --cov=<pkg> --cov-branch --cov-report=term-missing`, whose `--cov=` arrives
    last. Which forms can need the relaxation is enforced below rather than
    assumed. The loader permits a glued placeholder in a route's `argv` - five
    tokens across three routes in two records are written in the tree, the
    Stryker one-shot route's `@stryker-mutator/<runner>-runner` among them - so a
    route staying out of the `supplied` branch is a convention and not a schema
    fact, and the assertion holds the rows this property reads to it. Do not read
    those routes as the thing the assertion is guarding against, but read what
    shields each one, because no two of the three are shielded by the same thing:

    - `test/determinism`'s python `--randomly-seed=<n>` is on a `pytest-randomly`
      route that DOES build a routed row. What keeps it out of this branch is
      `disposition: alternative` alone, since only a `runs` form is read here.
    - `test/determinism`'s typescript `--sequence.seed=<n>` is `disposition:
      runs`, so `lang` is its only shield here - this module reads the python
      selection, and the TypeScript selection, which does build that row,
      fills `<n>` through `TS_COMPLETIONS`.
    - `test/mutation`'s three Stryker spellings have both.

    So "doubly guarded" is true of one of the three. The TypeScript selection
    walks into the second, which is why it completes the seed, and reading a
    `runs` form off an `alternative` route walks into the first. The convention
    the assertion holds a python route to is to leave such a placeholder in
    the route's `note`, which derives no form.

    So no form on either path takes the `supplied` branch today, and it stays
    because the shape is legal for a row: a record writes the token it
    supplies inside the form, and `_concrete` keeps a glued placeholder as a
    prefix `_marked` honours, where its head ends at a value delimiter, while
    dropping a standalone one - which is why `bandit -r <pkg>` does
    not take it and `pytest --randomly-seed=<n>` would, were its disposition not
    `alternative`. The assertion beneath refuses the branch on a routed row, so
    what it is kept for is a hand-written row, and the table that would hold
    one is empty.

    A form reachable only through `then` is held
    here, and this is the only property that holds one: a routed row's `argv`
    and `then` are two fields of one route, read in that order, so their order
    is true of it by construction and nothing else reads it.

    Reads both paths, and the reason it once read `INVOCATIONS` alone is worth
    keeping as a record of how the premise failed. It rested on a routed row
    having one `runs` form built from the same `Route` the row's `argv` came
    from, so the form's tokens were a leading subsequence of every carried
    command by construction. Two route fields broke both halves. A `then` on
    the `runs` route gives that row a second `runs` form, and an
    `argv_by_partition` makes the row's `argv` empty while its forms still
    come from the route's shared `argv` - so a partition override that no
    longer matches the shared form is a form declared `runs` that no
    partition's command carries, which is exactly what this property is for.
    """
    routed = {(i.check, i.tool) for i in routed_invocations()}
    for inv in every_invocation():
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
            assert not supplied or (inv.check, inv.tool) not in routed, (
                f"{inv.check}/{inv.tool}: the routed form {form!r} carries a "
                "token whose tail the caller supplies, so the relaxation this "
                "property grants a transcription has reached a route. Leave "
                "the placeholder in the route's `note`, which derives no "
                "form, rather than in the argv the forms come from"
            )
            assert any(
                _is_subsequence(ordered, tokens)
                and all(any(_matches(w, token) for token in tokens) for w in supplied)
                for tokens in carried
            ), (inv.check, inv.tool, form)


def test_no_prescribed_command_is_exactly_a_form_the_record_warns_against():
    """The disposition's other half, which had no property at all.

    The coverage property above reads the `runs` half, so a form declared
    `alternative` or `superseded` is held against nothing - which makes the
    disposition a per-form off-switch. Flipped, a second edit can drop the
    narrowing token from the argv, and the harness ships running exactly the
    form the record warns against.

    Both the command the record prescribes and the command the harness runs,
    which differ by the completion. Reading the prescribed half alone leaves the
    executed form unwatched: an entry whose completion supplies exactly the
    tokens its record warns against runs that form as written while its
    prescribed half equals nothing, and the flag property, while it stood,
    passed it too, because those tokens did occur in a declared form. The two are labelled apart in the
    failure message, since a form the record prescribes and a form a completion
    built are different corrections to make.

    Two limits, both real. Equality, so a non-`runs` form run as a strict prefix
    plus some unrelated token still passes: containment cannot be the test
    because a record supersedes a form by extending it, and every `superseded`
    form in the family is a subsequence of the command that narrows it. And this
    reads the declaration rather than the record - which form a record warns
    against is not mechanically extractable, so a disposition simply wrong about
    its record stays a reading pass.

    Held over both enumeration paths, not held vacuously there: a routed row
    can carry a `superseded` route beside a `runs` one for the same tool -
    `arch/cycles`'s `pydeps --show-cycles` narrowed by `--show-dot` is the
    live instance - and its argv comes from `COMPLETIONS` the same way a
    hand-written entry's does, so the same drift this property exists to
    catch is reachable there too.
    """
    for inv in every_invocation():
        prescribed = _prescribed_commands(inv)
        commands = list(prescribed)
        if inv.completion:
            commands += [
                (f"{partition} as run", argv_for(inv, partition))
                for partition, _ in prescribed
            ]
        if inv.then:
            commands.append(("then", inv.then))
        for form, disposition in inv.forms:
            if disposition == "runs":
                continue
            for label, command in commands:
                assert not _runs_as_written(command, form), (
                    f"{inv.check}/{inv.tool}: the {label} command runs {form!r} "
                    f"as written while the record declares it {disposition}"
                )


def test_an_entry_declaring_forms_declares_one_it_runs():
    """What still holds once the flip's other guard has gone silent.

    An entry whose declared forms include none marked `runs` has switched the
    coverage property off for itself entirely. The property above catches that
    only while some command still equals a form the record declares, and whether
    it does depends on the entry. Where an entry's single form is its argv token
    for token, flipping that form's disposition fails both properties at once;
    drop a token from the argv as well and the argv equals no declared form, the
    equality property goes silent on the length, and this one is the only thing
    left failing - it never reads an argv, so nothing done to one quiets it.

    Held with no exception set at all, which is strictly stronger than the one
    exception that used to stand here: any entry declaring forms and none it
    runs fails. That exception belonged to the transcription rather than to the
    schema. A transcribed entry could truthfully declare a single `alternative`
    form and no other - the record's only *named* form being one the harness
    deliberately does not run, with the plain command it ran instead anchored in
    the record's sentence rather than declared as a form of its own. A routed row
    cannot take that shape: `_forms_for` derives a form from every command route
    the row carries, and the route whose argv the row runs is the `runs` one by
    construction. So only a transcribed entry of that shape brings the exception
    back, and re-adding it then means naming the entry and asserting that it is
    exercised, because an exception nothing exercises reads as coverage.

    Held over both enumeration paths: `forms` on a routed row is the same
    field, built the same way, from routes that can equally decline to mark
    any of them `runs` - the guard has to hold there too, not only on the
    table this file writes by hand.
    """
    declaring = [inv for inv in every_invocation() if inv.forms]
    assert declaring, (
        "no entry declares a form at all, so this property holds nothing - the "
        "form vocabulary has moved and this guard needs re-pointing"
    )
    for inv in declaring:
        runs = [form for form, disposition in inv.forms if disposition == "runs"]
        assert runs, (
            f"{inv.check}/{inv.tool}: declares {len(inv.forms)} forms and none "
            "it runs, so the coverage property holds nothing on it"
        )


def test_every_disposition_in_the_vocabulary_is_used():
    """A value nothing uses is ceremony that reads as coverage.

    No other property here reads the vocabulary as a whole: each reads the
    disposition on a form it already has. So a value could sit in `DISPOSITIONS`
    with no user, and `forbidden` did. What keeps `forbidden` out of this module
    is not that no record declares one - several do - but that every one of them
    is on a `lang: typescript` or a `lang: any` route, and this module's
    selection is `lang: python` literally, so neither is reached.
    `routed_invocations` drops a `forbidden` route before grouping, in either
    language, and that is the statement to trust: this vocabulary is the lens's
    own, not the loader's.

    Records do warn against multi-token forms, and a routed row's `superseded`
    and `alternative` forms come from the routes that name them. `arch/cycles`
    warns against `pydeps --show-cycles`, declared `superseded` because the
    record narrows the same command, and `deps/inventory` says it has no route
    through `cyclonedx-py poetry`, declared `runs` because the harness runs that
    form on the partition whose manifest it does read. Both records are routed
    now, so those two forms come from `_forms_for` over their routes and the
    extractor never sees either - they are examples of what a record does with a
    warning, not of how this module reads one. Written as an equality rather
    than a subset in either direction, because the two failures are different
    findings: an unused value is ceremony, and a used value missing from the
    tuple is already rejected by `Invocation`.

    Read over both enumeration paths, and the union is load-bearing now rather
    than as insurance. Measured: the hand-written table carries no forms at all, so every
    value survives only on the routed side. The reason is the one this property was written for, arrived
    at: a value's users migrate, every record that declares its routes moves its
    forms out of this table, and the day the last hand-written user of a value
    goes the version reading one population starts failing on a vocabulary still
    in use. That day has passed for all three values.
    """
    assert {d for inv in every_invocation() for _, d in inv.forms} == set(DISPOSITIONS)


# --- scoping and grant states --------------------------------------------------


def test_the_full_partition_runs_every_invocation():
    assert set(invocations_for(FULL_PARTITION)) == set(every_invocation())


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
    """Held over both enumeration paths, and read per route on a migrated one.

    This property used to assert `grant_tier` equalled the projected
    `checks[check].needs` reading for every row, on the argument that a bug in
    the projection specific to a migrated record would otherwise go unasked.
    The projection turned out to be the bug: it collapses a record's routes
    onto their tools, so one tiered `alternative` route tiers the tool and
    `run_partition` then withholds the whole row. `deps/inventory` is the
    instance - `cyclonedx-py` prescribes file-parsing subcommands that read a
    lockfile and, as an `alternative`, `environment`, which reads the
    installed environment by starting its interpreter and is correctly tiered
    for it. Under the old
    reading that check reported `no-evidence (not-permitted)` at
    `--grant none` having run nothing it could have run.

    So the two readings are asserted to agree everywhere except where a tool's
    routes tier unevenly, and that exception is named rather than tolerated:
    it is the whole reason `grant_tier` reads the prescribed route.
    """
    checks, errors = load_checks(SKILLS_DIR)
    assert not errors, errors
    assert grant_tier("deps/hygiene", "deptry") == "resolved-tree"
    assert grant_tier("test/coverage-reach", "pytest-cov") == "target-execution"
    assert grant_tier("security/crypto", "bandit") == ""
    # The row whose prescribed command answers from a clone while another of
    # the same tool's routes starts the target's interpreter.
    assert grant_tier("deps/inventory", "cyclonedx-py") == ""
    assert checks["deps/inventory"].needs == {"target-execution": ("cyclonedx-py",)}
    disagreed = []
    for inv in every_invocation():
        tiers = {
            tier for tier, tools in checks[inv.check].needs.items() if inv.tool in tools
        }
        projected = tiers.pop() if tiers else ""
        if grant_tier(inv.check, inv.tool) != projected:
            disagreed.append((inv.check, inv.tool))
    assert sorted(set(disagreed)) == [("deps/inventory", "cyclonedx-py")], disagreed


def _projected_record(*routes):
    """A fake record carrying the pair the loader would project from its routes.

    `_fake_record` gives a namespace only `routes`, which is all
    `routed_invocations` reads. `grant_tier` also reads the projected
    `tooling`/`needs`, and the whole point of the rule under test is that the
    two can disagree - so projecting them here with the loader's own functions
    rather than writing them by hand is what keeps the disagreement real
    instead of arranged.
    """
    return SimpleNamespace(
        routes=routes,
        tooling=_project_tooling(routes),
        needs=_project_needs(routes),
    )


def test_the_tier_gating_a_row_is_the_prescribed_routes_not_the_tools(monkeypatch):
    """Stated on a constructed record, so the rule survives its instance.

    The tree pins `deps/inventory` in the property above, which fails if the
    rule regresses and also if a second record quietly grows the shape. This
    one fails only if the rule itself goes, and it is the one that says what
    the rule is: the tier that decides whether a row may run is carried by the
    route whose command the row runs, and a tier on a sibling route of the
    same tool is not a claim about it.
    """
    prescribed_from_a_clone = _projected_record(
        _fake_route(argv=("t", "file")),
        _fake_route(
            argv=("t", "environment"),
            disposition="alternative",
            needs="resolved-tree",
        ),
    )
    # The projection says the tool needs the tree, because one route does.
    assert prescribed_from_a_clone.needs == {"resolved-tree": ("t",)}
    with _records_replaced_by(monkeypatch, {"x/y": prescribed_from_a_clone}):
        assert grant_tier("x/y", "t") == ""

    # The converse: tier the route the row runs, and the row is gated.
    prescribed_needs_the_tree = _projected_record(
        _fake_route(argv=("t", "file"), needs="target-execution"),
        _fake_route(argv=("t", "environment"), disposition="alternative"),
    )
    with _records_replaced_by(monkeypatch, {"x/y": prescribed_needs_the_tree}):
        assert grant_tier("x/y", "t") == "target-execution"


def test_an_unknown_check_or_tool_is_rejected_by_name():
    with pytest.raises(ValueError, match="conda"):
        grant_tier("conda/whatever", "deptry")
    with pytest.raises(ValueError, match="madge"):
        grant_tier("deps/hygiene", "madge")
    with pytest.raises(ValueError, match="conda"):
        invocations_for("conda")


def test_a_filtered_run_names_only_the_check_it_was_given():
    everything = every_invocation()
    assert [i.check for i in invocations_for("uv", only_check="arch/cycles")] == [
        "arch/cycles"
    ] * len([i for i in everything if i.check == "arch/cycles"])


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
    everything = every_invocation()
    assert {(i.check, i.tool) for i in everything if i.findings_stream == "stderr"} == {
        ("deps/hygiene", "deptry"),
        ("arch/complexity", "xenon"),
    }
    assert all(i.findings_stream in ("stdout", "stderr") for i in everything)
    with pytest.raises(ValueError, match="findings_stream"):
        Invocation(
            check="deps/hygiene",
            tool="deptry",
            argv=("deptry",),
            findings_stream="both",
        )


def _tools_that_can_run_a_command() -> set[str]:
    """Every tool either enumeration path could actually hand `classify` an exit code.

    A tool named only in entries with no `argv`, no `argv_by_partition` and no
    `supplied_by_partition` never runs a command at all, so it never reaches
    `classify` and has nothing to state a non-zero-exit meaning about. It is
    the tool rather than the row that has to qualify: `ruff` and `radon` each
    name a route that runs nothing and another that runs a command, so they
    are not in this class. `grep tool: .agents/skills/*/checks/*.md` beside
    the routes' `argv` is how to ask which tools are, rather than a list here
    that a migration moves.
    """
    everything = every_invocation()
    return {
        i.tool
        for i in everything
        if i.argv or i.argv_by_partition or i.supplied_by_partition
    }


def test_nonzero_exit_meaning_covers_exactly_the_tools_that_can_run_a_command():
    """The exact-set guard: a tool added to `INVOCATIONS` with a real command
    and no entry here would silently default `classify` to `findings`, which is
    precisely the silent claim this table exists to forbid.

    `_tools_that_can_run_a_command` already reads both enumeration paths, so
    this holds over a tool a migrated record's route names too.
    """
    assert set(NONZERO_EXIT_MEANING) == _tools_that_can_run_a_command()


def test_every_tool_the_harness_runs_carries_an_engine_grading_rule():
    """Engine-owned tables cover both enumeration paths, not just the table.

    The record says what to run; this module says how to read a nonzero exit
    from it. A routed row whose tool no rule grades would be classified by a
    default nobody chose, so it fails here instead.
    """
    for inv in every_invocation():
        if not inv.argv and not inv.argv_by_partition:
            continue
        assert nonzero_exit_meaning(inv.tool) in NONZERO_EXIT_KINDS, inv.tool


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

    Held over both enumeration paths because `run_partition` runs the same union
    `invocations_for` scopes to, and read that way rather than over the routed
    side alone even though every row it finds is routed today: measured, all 18
    rows prescribing no command come from records that declare their routes, and
    no hand-written entry is one - the table is empty. A hand-written entry of
    this shape is a thing the table can still express, so narrowing the property
    to where its subjects happen to live would make the narrowing the claim.
    """
    reading = [i for i in every_invocation() if not i.argv and not i.argv_by_partition]
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

    Held over both enumeration paths: a routed row runs on `FULL_PARTITION`
    exactly as a hand-written one does, through the same `launcher`, so its
    tool has to resolve to a fetchable package too.
    """
    assert TOOL_PACKAGES == {
        "coverage.py": ("coverage", "pytest"),
        "cyclonedx-py": ("cyclonedx-bom",),
        "mutmut": ("mutmut", "pytest"),
    }
    for inv in every_invocation():
        if argv_for(inv, FULL_PARTITION):
            packages = packages_for(inv.tool)
            assert packages and all(packages), inv.tool
    assert launcher(_entry("deps/inventory", "cyclonedx-py"), "pip", granted=False) == (
        "uvx",
        "--from",
        "cyclonedx-bom",
    )


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

    Fetches the `coverage.py` row through `_entry`, which reads both
    populations: `launcher` treats every `Invocation` alike regardless of which
    table built it, and the row naming this tool is a routed one, so a lookup
    pinned to `INVOCATIONS` would raise before asserting anything rather than
    narrowing the property to a population this launcher does not distinguish.
    """
    assert packages_for("coverage.py") == ("coverage", "pytest")
    assert packages_for("mutmut") == ("mutmut", "pytest")
    assert packages_for("bandit") == ("bandit",)

    coverage = _entry("test/coverage-reach", "coverage.py")
    assert launcher(coverage, "uv", granted=True) == (
        "uv",
        "run",
        "--no-sync",
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

    Held over both enumeration paths: `in_env` is a route field a migrated
    record can set too, and `launcher` reads it the same way regardless of
    which table built the row.
    """
    in_env = {(i.check, i.tool) for i in every_invocation() if i.in_env}
    assert ("deps/hygiene", "deptry") in in_env
    assert ("deps/licenses", "pip-licenses") in in_env
    assert ("deps/freshness", "uv") in in_env
    assert ("security/crypto", "bandit") not in in_env


def test_an_in_env_tool_is_launched_through_the_partitions_own_environment():
    """`uv` is the round's known-good reference route and keeps its own shape;
    every other partition reaches the same environment through `--python`
    rather than through that manager's own runner.

    Fetches `deps/hygiene`'s `deptry` row, which its record now declares as a
    route: `launcher` is agnostic of which table an `Invocation` came from, so
    the example holds the same thing on either side of that row's migration.
    """
    inv = _entry("deps/hygiene", "deptry")
    assert launcher(inv, "uv", granted=True) == (
        "uv",
        "run",
        "--no-sync",
        "--with",
        "deptry",
    )
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

    Fetches the `deps/licenses` row for the same reason the `deptry` example
    above does: `launcher` does not distinguish the table its argument came
    from.
    """
    inv = _entry("deps/licenses", "pip-licenses")
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

    Held over both enumeration paths, for the same reason: `launcher` does
    not read which table built the row it was handed, only its `in_env`
    field, so a migrated route marking itself `in_env` would take the same
    path this guards.
    """
    for inv in every_invocation():
        if not inv.in_env:
            continue
        for partition in PARTITIONS:
            prefix = launcher(inv, partition, granted=True)
            assert "install" not in prefix, (inv.check, inv.tool, partition)


def test_an_ungranted_run_never_launches_through_a_tree_it_does_not_have():
    """Fetches the same `deptry` row as the examples above; `launcher` is
    agnostic of which table built the `Invocation` it is given.
    """
    inv = _entry("deps/hygiene", "deptry")
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
    """One row by name, over both enumeration paths.

    Each caller fetches the single row it names, so the helper's population is
    not a scoping claim about any field - `own_runner`, `argv_by_partition`
    and `supplied_by_partition` all reach a routed row, the first two as route
    fields and the third through the `SUPPLIED` overlay, which is why the
    claim that used to stand here (that no route ever populates them) is
    gone rather than narrowed. How many entries the overlay holds is a fact
    about its contents rather than about the path, so it is not what this
    helper's callers rest on. Reading both populations is what keeps a caller
    naming a row alive across that row's own migration: the pair is unique
    across the two, which
    `test_no_check_invokes_the_same_tool_twice` holds.
    """
    return next(i for i in every_invocation() if (i.check, i.tool) == (check, tool))


def test_a_partition_the_record_prescribes_no_route_for_runs_nothing():
    """`pip-audit` has no mode for a uv, poetry or pipenv tree, and that is the finding.

    Filling one in - a bare `pip-audit` from inside the environment - is the
    repair the record's silence exists to make visible, so the row names those
    partitions with an empty command instead.

    The whole mapping is pinned rather than only the two partitions the record
    prescribes for, because an empty command and an absent one are the same
    answer read two ways: the row says "no command here", and a reader who sees
    only the two populated entries cannot tell that from "nobody looked". The
    row is derived now - `_argv_by_partition` iterates `PARTITIONS`, so all five
    are always named and no partition can drop out by omission - which retires
    one of the two ways this used to be lost and leaves the other. What the
    pinning still catches is a route arriving for one of those three, or leaving
    one of these two, which is a change in what the record prescribes and
    belongs in the record's own diff rather than showing up as a quieter run.
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

    Reads both populations, because both can carry one: a hand-written entry
    holds its supplied route in its own literal and a routed row takes it from
    `SUPPLIED`, and a set pinned over one path would go on passing while the
    other grew a route nobody named. Both of these arrive through `SUPPLIED`
    today, which is a fact about where the two records that leave holes have
    got to rather than about the paths.
    """
    supplied = {
        (i.check, i.tool, p): steps
        for i in every_invocation()
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

    Reads both populations, for the same reason as the pinned set above: a
    supplied route reaches a row from a literal here or from `SUPPLIED`, and
    the relationship it has to hold against the rest of the row is the same
    either way.
    """
    for inv in every_invocation():
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
            supplied_by_partition=(("uv", (("uv", "export"),)),),
        )
    with pytest.raises(ValueError, match="both a prescribed route and a supplied"):
        Invocation(
            check="deps/inventory",
            tool="cyclonedx-py",
            argv_by_partition=(("uv", ("cyclonedx-py", "requirements")),),
            supplied_by_partition=(("uv", (("uv", "export"),)),),
            supplied_note="why",
        )
    with pytest.raises(ValueError, match="twice in supplied_by_partition"):
        Invocation(
            check="deps/inventory",
            tool="cyclonedx-py",
            supplied_by_partition=(("uv", (("a",),)), ("uv", (("b",),))),
            supplied_note="why",
        )
    with pytest.raises(ValueError, match="no launcher prefix"):
        Invocation(
            check="deps/hygiene",
            tool="deptry",
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
            argv_by_partition=(("pip", ("cyclonedx-py", "requirements")),),
            own_runner=("uv",),
        )
    with pytest.raises(ValueError, match="has no prescribed command"):
        Invocation(
            check="deps/inventory",
            tool="cyclonedx-py",
            own_runner=("uv",),
            supplied_by_partition=(("uv", (("uv", "export"),)),),
            supplied_note="why",
        )
    with pytest.raises(ValueError, match="both a prescribed route and a supplied"):
        Invocation(
            check="deps/inventory",
            tool="cyclonedx-py",
            argv_by_partition=(("uv", ("uv", "export")),),
            own_runner=("uv",),
            supplied_by_partition=(("uv", (("uv", "export"),)),),
            supplied_note="why",
        )
    with pytest.raises(ValueError, match="own_runner partition takes no launcher"):
        Invocation(
            check="deps/hygiene",
            tool="deptry",
            argv=("deptry", "."),
            in_env=True,
            own_runner=("uv",),
        )


def test_a_form_carrying_an_unknown_disposition_is_rejected():
    with pytest.raises(ValueError, match="not one of"):
        Invocation(
            check="arch/cycles",
            tool="pydeps",
            forms=(("pydeps --show-cycles", "maybe"),),
        )


def test_an_empty_form_is_rejected():
    with pytest.raises(ValueError, match="empty command form"):
        Invocation(
            check="arch/cycles",
            tool="pydeps",
            forms=(("   ", "runs"),),
        )


def test_the_same_form_declared_twice_is_rejected():
    with pytest.raises(ValueError, match="twice"):
        Invocation(
            check="arch/cycles",
            tool="pydeps",
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


def test_an_entry_cannot_hold_both_a_shared_and_a_per_partition_command():
    with pytest.raises(ValueError, match="per-partition"):
        Invocation(
            check="deps/inventory",
            tool="cyclonedx-py",
            argv=("cyclonedx-py",),
            argv_by_partition=(("uv", ("uv", "export")),),
        )


def test_naming_one_partition_twice_is_rejected():
    with pytest.raises(ValueError, match="twice"):
        Invocation(
            check="deps/inventory",
            tool="cyclonedx-py",
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
    """A granted run materializes the environment, then runs the route inside it.

    What counts as the follow-up is read from the entry rather than written out
    here. The claim is that the second command reaches execution unmangled, and
    a tuple repeated in the assertion adds a second claim nobody asked for -
    that the record's second command is still the one it was on the day this was
    written - which fails as a stale literal rather than as a route that did not
    run.
    """
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
    expected = list(_entry("test/coverage-reach", "coverage.py").then)
    assert follow_up["command"][-len(expected) :] == expected


def test_the_interpreter_the_freshness_record_names_reaches_the_argv():
    """Unit-level: `--python` is the record's word, its value is the harness's.

    The flag reached the run as a suffix the harness appended before the record
    prescribed it, and a suffix is invisible to every guard that reads `argv`.
    Carried in the argv the record's own route declares, the flag travels with
    the command and only the path - the record's `<path-to-venv-python>` - is
    left to the completion. `pip` is the contrast: the record says it needs no
    such flag, so its row carries none.
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
    same gap was confirmed on the `uv` partition's own native route, then
    `uv run --with uv uv pip list --outdated` and now with `--no-sync` before
    `--with`, no `--no-project` involved in either, which is
    why both partitions are checked here rather than only the overlay one.
    The record names the interpreter for that reason, so what this asserts is
    that the record's command and its completion still reach the run in that
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

    Which command counts as the reporting half is read from the entry rather than
    repeated here. Repeated, this test goes red whenever that command changes for
    any reason at all - a swapped route, a renamed subcommand - with no injected
    failure ever occurring, and the failure it prints then reads as a literal
    somebody needs to update. Read from the entry, it asserts the thing it is for
    and leaves the record's order to the property that holds it.
    """
    source = tmp_path / "fixture" / "uv"
    source.mkdir(parents=True)
    reporting = list(_entry("test/coverage-reach", "coverage.py").then)
    assert reporting, "an empty tail would match the whole of every command"
    monkeypatch.setattr(
        "run_python_fixture_lens._run",
        _fake_run(
            [],
            respond=lambda command: (
                _outcome(returncode=1, stdout="", stderr="no data")
                if command[-len(reporting) :] == reporting
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
    everything = every_invocation()
    assert set(observed["versions"]) == {
        inv.tool for inv in everything if inv.check == "arch/cycles"
    }
    assert "written to" in capsys.readouterr().out


def test_an_unknown_check_is_rejected_before_anything_is_copied_or_synced(
    tmp_path, monkeypatch, capsys
):
    """The one argument whose typo used to cost a tree copy and a network sync.

    `partition` and `--grant` are argparse `choices` and `--fixture-root` is
    checked against the filesystem, so `--check` was the only argument reaching
    `run_partition` unvalidated - and the rejection there arrives after the copy
    and after `uv sync --frozen`, as a bare traceback rather than a usage message.
    Asserted by making the run fail if it starts at all: `_run` raises, so a
    `SystemExit` carrying argparse's code 2 is evidence the parser rejected the
    argument rather than that the run did.
    """

    def _never(*args, **kwargs):
        raise AssertionError("the run started on an unknown check id")

    fixture_root = tmp_path / "fixtures"
    (fixture_root / "uv").mkdir(parents=True)
    monkeypatch.setattr("run_python_fixture_lens._run", _never)

    with pytest.raises(SystemExit) as caught:
        main(
            [
                "uv",
                "--grant",
                "none",
                "--check",
                "arch/cylces",
                "--fixture-root",
                str(fixture_root),
                "--work-dir",
                str(tmp_path / "work"),
            ]
        )

    assert caught.value.code == 2
    assert "arch/cylces" in capsys.readouterr().err
    assert not (fixture_root / "results").exists()
    assert not (tmp_path / "work").exists()


def test_the_two_grant_states_are_the_two_the_round_runs():
    assert GRANTS == ("none", "target-execution")


def test_every_vocabulary_is_pinned_rather_than_merely_non_empty():
    """A membership test passes on a scale that has grown a fourth member.

    Pinned so that a member added to either arrives visibly, which is a reason
    to pin that survives the engine growing one. `audit-core` has a fourth
    reason, `not-prescribed`, and the lens cannot produce it - that reason is a
    check's verdict on a partition, while a row here is one invocation's
    observation - so the two sets differ on purpose and the difference belongs
    in a pin rather than in a membership test that would accept either.

    A fourth member arriving here would be a value the pass that grades this
    file has no row for, and it would arrive silently, because every existing
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

    Held over both enumeration paths: `probe_versions` calls `launcher` for
    every tool `invocations_for` names, hand-written or routed, so the same
    silent default would misgrade a migrated check offering one of these
    plugins exactly as it did `pytest-rerunfailures`.
    """
    plugins = {
        "pytest-cov",
        "pytest-randomly",
        "pytest-rerunfailures",
        "pytest-timeout",
    }
    for inv in every_invocation():
        if inv.tool in plugins:
            assert inv.in_env, inv.tool
    rerun = _entry("test/determinism", "pytest-rerunfailures")
    # The property that actually broke: the granted launcher must resolve into
    # an environment, not fall back to a bare one-shot fetch.
    assert launcher(rerun, "uv", granted=True) != ("uvx",)
    assert launcher(rerun, "uv", granted=True) == (
        "uv",
        "run",
        "--no-sync",
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
    expected = (
        "uv",
        "run",
        "--no-sync",
        "--with",
        "pytest-rerunfailures",
    ) + VERSION_PROBE["pytest-rerunfailures"]
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


# The routes oracle stood here, with the tripwire that guarded its reach beside
# it. It held a migrated record's routes against this module's transcription of
# them, and while both copies existed it was the only check on the migration.
# `routed_invocations` is now the single source, so the oracle had nothing left
# to compare - a derivation cannot disagree with itself - and the tripwire had
# nothing left to guard the reach of.
#
# What neither ever held, and what still nothing holds, is whether a route is
# true. `arch/size`'s `cloc` argv and `arch/coupling`'s `typescript@^5` pin can
# each be edited to contradict their own notes with this suite green, before
# this change and after it. That is answered by running a route against a
# seeded fixture, which is epic #44, and reading these deletions as having
# closed it would be exactly backwards.


def test_a_routed_row_is_one_per_check_and_tool_rather_than_one_per_route():
    """`arch/cycles` declares four python routes and has three rows.

    Its `superseded` `pydeps --show-cycles` is a second form of the same tool,
    not a second row. A rule keyed on routes would run a form the record
    narrows against as though it prescribed it.
    """
    rows = {(r.check, r.tool) for r in routed_invocations()}
    cycles = sorted(t for c, t in rows if c == "arch/cycles")
    assert cycles == ["grimp", "import-linter", "pydeps"]
    pydeps = next(
        r
        for r in routed_invocations()
        if r.check == "arch/cycles" and r.tool == "pydeps"
    )
    assert pydeps.argv == ("pydeps", "--show-cycles", "--show-dot")
    assert set(pydeps.forms) == {
        ("pydeps --show-cycles --show-dot", "runs"),
        ("pydeps --show-cycles", "superseded"),
    }


def test_a_route_that_is_not_a_command_still_produces_a_row():
    """`arch/complexity-gate`'s three `subject` routes are three rows.

    The engine grades a row prescribing no command as exactly that, so
    dropping these would shrink the round's evidence rather than simplify it.
    """
    rows = [r for r in routed_invocations() if r.check == "arch/complexity-gate"]
    assert sorted(r.tool for r in rows) == ["radon", "ruff", "xenon"]
    assert all(r.argv == () and r.forms == () for r in rows)


def test_a_route_naming_no_tool_produces_no_row():
    """A `procedure` route with no tool is a reading pass, not a row.

    `arch/martin-metrics` declares two python routes and has one row.
    """
    rows = [r for r in routed_invocations() if r.check == "arch/martin-metrics"]
    assert [r.tool for r in rows] == ["grimp"]


def test_a_record_with_no_python_route_produces_no_row():
    """`arch/size` declares `lang: any` routes only, and selection is python.

    Widening selection is #44's territory: it changes the set of checks the
    round runs, and `arch/size` is in neither the expectations' declared scope
    nor the three-way equality that holds the harness to them.
    """
    assert not [r for r in routed_invocations() if r.check == "arch/size"]


def test_a_routed_row_carries_the_rounds_completion_and_its_reason():
    """The completion is round-owned and travels with why it was needed."""
    row = next(
        r
        for r in routed_invocations()
        if r.check == "arch/dead-code" and r.tool == "vulture"
    )
    assert row.completion == ("src", "tests")
    assert "the record names none" in row.note


def test_the_deps_rows_survive_their_records_migration():
    """The five rows these records prescribe, held against what they ran before.

    A migration that changes what runs is not a migration. The values are
    written out rather than read from a baseline file because the point is to
    fail when the record changes, not when a scratch file goes missing.
    """
    expected = {
        ("deps/freshness", "uv"): (
            ("uv", "pip", "list", "--outdated", "--python"),
            True,
            "stdout",
        ),
        ("deps/freshness", "pip"): (("pip", "list", "--outdated"), True, "stdout"),
        ("deps/hygiene", "deptry"): (("deptry",), True, "stderr"),
        ("deps/licenses", "pip-licenses"): (("pip-licenses",), True, "stdout"),
        ("deps/transitive-licenses", "pip-licenses"): (
            ("pip-licenses",),
            True,
            "stdout",
        ),
    }
    rows = {(i.check, i.tool): i for i in routed_invocations()}
    for key, (argv, in_env, stream) in expected.items():
        row = rows[key]
        assert row.argv == argv, key
        assert row.in_env is in_env, key
        assert row.findings_stream == stream, key


def test_the_per_partition_deps_rows_survive_their_records_migration():
    """All five partitions present, the ones the record prescribes nothing for empty.

    `prescribed()` falls back to the shared `argv` when the row carries no
    per-partition map at all, so a row that lost its map would answer these
    assertions with the shared command rather than with nothing - which is why
    the empty `argv` is asserted beside them.
    """
    rows = {(i.check, i.tool): i for i in routed_invocations()}
    inv = rows[("deps/inventory", "cyclonedx-py")]
    assert inv.argv == ()
    assert inv.argv_by_partition == (
        ("uv", ("uv", "export", "--format=cyclonedx1.5", "--frozen")),
        ("pip", ("cyclonedx-py", "requirements")),
        ("poetry", ("cyclonedx-py", "poetry")),
        ("pipenv", ("cyclonedx-py", "pipenv")),
        ("pylock", ()),
    )
    assert inv.own_runner == ("uv",)
    assert inv.supplied("pylock") == (
        ("uvx", "cyclonedx-py", "requirements", "pylock.toml"),
    )
    vuln = rows[("deps/vulnerabilities", "pip-audit")]
    assert vuln.argv == ()
    assert vuln.prescribed("pip") == (
        "pip-audit",
        "-r",
        "requirements.txt",
        "--no-deps",
        "--disable-pip",
    )
    assert vuln.prescribed("pylock") == ("pip-audit", "--locked", ".")
    assert [p for p in PARTITIONS if not vuln.prescribed(p)] == [
        "uv",
        "poetry",
        "pipenv",
    ]
    assert vuln.supplied("uv")[0][:3] == ("uv", "export", "--frozen")
    assert rows[("deps/vulnerabilities", "safety")].argv == ()
    # `in_env` and the findings stream are pinned here for the same reason the
    # shared-argv rows above pin them: both decide how a row is run and read
    # rather than what it runs, so a route gaining `in_env: true` would launch
    # every one of these commands through the partition's own environment
    # instead of a one-shot runner, and a route naming stderr would move which
    # stream `classify` grades - each with every argv above still matching and
    # the whole suite green.
    for row in (inv, vuln, rows[("deps/vulnerabilities", "safety")]):
        assert row.in_env is False, (row.check, row.tool)
        assert row.findings_stream == "stdout", (row.check, row.tool)


def test_the_coverage_and_mutation_rows_survive_their_records_migration():
    """The `then`'s order is the record's, and the row that runs nothing keeps in_env.

    Written out rather than read from a baseline file for the reason the deps
    rows above are: the point is to fail when the record changes, not when a
    scratch file goes missing.
    """
    rows = {(i.check, i.tool): i for i in routed_invocations()}
    cov = rows[("test/coverage-reach", "coverage.py")]
    assert cov.argv == ("coverage", "run", "-m", "pytest")
    assert cov.then == ("coverage", "report", "--show-missing")
    pcov = rows[("test/coverage-reach", "pytest-cov")]
    assert pcov.argv == ("pytest", "--cov-branch", "--cov-report=term-missing")
    assert pcov.completion == (f"--cov={PACKAGE}",)
    assert rows[("test/mutation", "mutmut")].argv == ("mutmut", "run")
    cosmic = rows[("test/mutation", "cosmic-ray")]
    assert cosmic.argv == ()
    assert cosmic.in_env is True
    for row in (cov, pcov, rows[("test/mutation", "mutmut")]):
        assert row.in_env is True, (row.check, row.tool)


def test_the_remaining_test_rows_survive_their_records_migration():
    """Four rows, and the two records that produce none still produce none.

    Written out rather than read from a baseline file for the reason the rows
    above are: the point is to fail when the record changes, not when a scratch
    file goes missing.

    The two checks asserted absent are absent for two different reasons, and
    naming them together is what makes the pair readable as one property rather
    than as an accident. `test/assertion-strength` offers a route naming no
    tool, and `routed_invocations` builds a row per `(check, tool)`, so there is
    no pair for it to key one by. `test/new-code-coverage` names a tool on a
    `lang: any` route, which that selection excludes because a row it built
    there would be graded by no expectation.
    """
    routed = routed_invocations()
    rows = {(i.check, i.tool): i for i in routed}
    assert rows[("test/determinism", "pytest-randomly")].argv == ("pytest",)
    rerun = rows[("test/determinism", "pytest-rerunfailures")]
    assert rerun.argv == ()
    assert rerun.in_env is True
    iso = rows[("test/isolation", "pytest-timeout")]
    assert iso.argv == ("pytest", "--durations=25")
    assert iso.completion == (f"--timeout={ISOLATION_TIMEOUT_SECONDS}",)
    assert rows[("test/property-based-gap", "hypothesis")].argv == ()
    assert not {i.check for i in routed} & {
        "test/assertion-strength",
        "test/new-code-coverage",
    }


def _fake_record(*routes):
    return SimpleNamespace(routes=routes)


def _fake_route(**kw):
    field = {
        "lang": "python",
        "kind": "command",
        "tool": "t",
        "argv": ("t",),
        "disposition": "runs",
        "findings_stream": "stdout",
        "in_env": False,
        "needs": None,
        "applies_when": None,
        "alone_insufficient": None,
        "note": "",
        "then": (),
        "own_runner": False,
        "argv_by_partition": {},
        "answers": None,
    }
    field.update(kw)
    # `package` defaults to `tool` in the loader, so it has to follow an
    # overridden tool here too - a fixed default would silently describe a
    # different installable from the one the route names.
    field.setdefault("package", field["tool"])
    # `registry` defaults to nothing, because that is what the loader stores
    # for a route that declares no key: it keeps the declared value and
    # `registry_for` does the deriving, so a real `lang: python` route carries
    # `None` and resolves to `pypi` only when something asks. Defaulting to
    # `pypi` here would make the fake carry what no real route carries, which
    # is the one thing a duck-typed double must not do.
    field.setdefault("registry", None)
    return SimpleNamespace(**field)


def test_the_fake_route_carries_every_field_the_real_one_does():
    """`_fake_route` duck-types `Route`, and nothing else holds the two together.

    Every field the enumeration or `grant_tier` reads has had to be added here
    by hand as those readers grew - `applies_when` and `needs` both arrived
    that way, each surfacing as an `AttributeError` in whichever test happened
    to construct a route without it. The failure is a missing attribute rather
    than a wrong answer, so it is loud; what it is not is early, and a fake
    carrying a field the dataclass has dropped is the quiet direction. Compare
    the two field sets instead, so adding a field to `Route` fails here with
    its name rather than in an unrelated test.
    """
    assert set(_fake_route().__dict__) == {f.name for f in fields(Route)}


@contextmanager
def _records_replaced_by(monkeypatch, records):
    routed_invocations.cache_clear()
    monkeypatch.setattr("run_python_fixture_lens._records", lambda: records)
    try:
        yield
    finally:
        routed_invocations.cache_clear()


def test_a_completion_with_no_tokens_or_no_reason_is_rejected():
    with pytest.raises(ValueError, match="not a completion"):
        Completion(tokens=(), note="why")
    with pytest.raises(ValueError, match="repaired command as a clean run"):
        Completion(tokens=("src",), note="")


def test_a_supplied_route_with_no_steps_is_rejected():
    with pytest.raises(ValueError, match="no steps is not a route"):
        Supplied(by_partition=(), note="why")


def test_a_supplied_route_with_no_note_is_rejected():
    with pytest.raises(ValueError, match="needs the reason the record has none"):
        Supplied(by_partition=(("pylock", (("uvx", "t"),)),), note="")


def test_a_supplied_route_step_with_no_tokens_is_rejected():
    """`(("pylock", ((),)),)` is a step, not an absent one.

    `Supplied` still holds one row of `by_partition`, so the no-steps guard
    above never sees it, and an empty step would otherwise reach
    `_run_supplied` and execute as an empty command - which reports as a tool
    that failed rather than as the hole in the record this class exists to
    name.
    """
    with pytest.raises(ValueError, match="empty command to execute"):
        Supplied(by_partition=(("pylock", ((),)),), note="why")


def test_a_supplied_route_naming_a_partition_twice_is_rejected_at_the_literal():
    """`Invocation` rejects this too, and the two rejections catch it at different moments.

    Every supplied route in the tree now arrives through `SUPPLIED`, so every
    one reaches `Invocation` with `Supplied` having already validated it - the
    copy on `_check_supplied` is a second guard rather than a first. Keeping it
    is a claim about the constructor rather than about the population: a
    hand-written entry can still pass `supplied_by_partition` directly, and none
    does only because both records that had one have migrated.

    What this test holds is the earlier of the two. An entry written in the
    overlay fails here, at the literal carrying the mistake rather than at the
    row it is later copied onto, which is the difference between a message
    naming a file somebody is editing and one naming a check id.
    """
    with pytest.raises(ValueError, match="names a partition twice"):
        Supplied(
            by_partition=(
                ("pylock", (("uvx", "t"),)),
                ("pylock", (("uvx", "u"),)),
            ),
            note="why",
        )


def test_a_migrated_record_reads_its_supplied_route_from_the_overlay(monkeypatch):
    """The round's contribution stays round-owned after a record migrates.

    `Supplied` validates its own shape - a steps tuple that is empty, a
    missing note, a step with no tokens - so this fake record needs none of
    that repeated here. What it does need is a route that leaves `pylock`
    with no prescribed command: a shared `argv` covers every partition
    including `pylock`, and `_check_supplied` rejects that as a partition
    carrying both a prescribed route and a supplied one, so the fake route
    below prescribes nothing at all rather than reusing `_fake_route()`'s
    default `argv=("t",)`.
    """
    steps = (("uvx", "t", "sub", "pylock.toml"),)
    # The overlay has to be set before `_records_replaced_by` is entered:
    # `routed_invocations` is cached and the context manager clears that cache
    # only on entry and exit, so setting the overlay after entry would build
    # the row from a cache filled before `SUPPLIED` carried anything, and the
    # assertions below would pass for a row that never read it.
    monkeypatch.setitem(
        SUPPLIED,
        ("x/y", "t"),
        Supplied(
            by_partition=(("pylock", steps),),
            note="the record names no route at all for a PEP 751 file",
        ),
    )
    with _records_replaced_by(monkeypatch, {"x/y": _fake_record(_fake_route(argv=()))}):
        (row,) = routed_invocations()
    assert row.supplied("pylock") == steps
    assert row.supplied_note


@pytest.mark.parametrize(
    "routes, expected",
    [
        (
            # Not `forbidden`, which is dropped before grouping and has its own
            # test in the TypeScript harness file: a value outside both the
            # loader's vocabulary and this module's, which only a double reaches.
            (_fake_route(disposition="deprecated"),),
            "does not carry",
        ),
        (
            (_fake_route(argv=("t", "a")), _fake_route(argv=("t", "b"))),
            "declare `runs`",
        ),
        (
            (
                _fake_route(),
                _fake_route(disposition="superseded", findings_stream="stderr"),
            ),
            "disagree on findings_stream",
        ),
        (
            (_fake_route(), _fake_route(disposition="superseded", in_env=True)),
            "disagree on in_env",
        ),
        (
            (
                _fake_route(kind="library", argv=()),
                _fake_route(kind="procedure", argv=()),
            ),
            "none of which carries a note",
        ),
    ],
)
def test_an_ambiguous_group_is_refused_by_name(monkeypatch, routes, expected):
    """Each raise names the group and what is wrong with it.

    The first four are ambiguity: each resolves silently to whichever route
    came first if the guard is removed, and each is a shape the record set
    does not currently contain - so the message is the only thing a future
    reader gets, and it is read here rather than assumed. That absence needs
    no test holding it, and stating why is the point: a record growing one of
    those shapes makes `routed_invocations` raise, and the enumeration is read
    by enough of this file that the suite goes red rather than quietly
    disagreeing with this sentence.

    The last case is not ambiguity, and its shape is **not** absent. A group
    prescribing no command and declaring more than one route is present in the
    tree, all `lang: typescript`, held by identity in
    `test_the_multi_route_no_command_groups_are_the_ones_the_rule_was_written_for`
    - and it does not raise, because `_reason_for_no_command` composes those
    routes' notes rather than choosing between them. This case is the
    note-less variant: several prescribed routes with no note anywhere among
    them, where there is nothing to compose and nothing to attribute the
    absence to either. Removing that guard would not resolve to the first
    route; it would put a row in the artifact saying it ran nothing and not
    why.
    """
    with (
        _records_replaced_by(monkeypatch, {"x/y": _fake_record(*routes)}),
        pytest.raises(ValueError, match=expected),
    ):
        routed_invocations()


def test_a_group_prescribing_no_command_composes_the_notes_it_prescribes(monkeypatch):
    """Two routes explaining one absence contribute both explanations.

    The guard this replaced raised here, because a row taking one of two notes
    attributes the wrong explanation to a run. Refusing to choose is right;
    refusing to build the row is not, and the record shapes that reach this
    are ones no other spelling can express - `arch/complexity` distinguishes
    its two `eslint` routes by `needs` alone, and a route carries one `needs`,
    so merging them into the single route the old rule demanded means dropping
    a tier the record needs.

    Each note is prefixed by its own `applies_when`, which is what keeps the
    composition readable: a note written under a precondition can be nonsense
    without it.
    """
    with _records_replaced_by(
        monkeypatch,
        {
            "x/y": _fake_record(
                _fake_route(
                    kind="procedure",
                    argv=(),
                    applies_when="Where the runner is Vitest.",
                    note="Never reach for it - it reports a false clean.",
                ),
                _fake_route(
                    kind="procedure",
                    argv=(),
                    applies_when="Where the runner runs in the process.",
                    note="Its plain form remains the measurement there.",
                ),
            )
        },
    ):
        (row,) = routed_invocations()
    assert row.note == (
        "Where the runner is Vitest. Never reach for it - it reports a false clean."
        "\n\n"
        "Where the runner runs in the process. Its plain form remains the "
        "measurement there."
    )


def test_a_composed_note_carries_both_notes_where_neither_has_a_precondition(
    monkeypatch,
):
    """`arch/complexity`'s two `eslint` routes are this shape.

    They are distinguished only by their tier, and that record's own note says
    nothing machine-readable tells the modes apart. So the row carries both, in
    record order, which is honest rather than resolved - the alternative is
    picking one and reporting the wrong invocation mode's reason.
    """
    with _records_replaced_by(
        monkeypatch,
        {
            "x/y": _fake_record(
                _fake_route(kind="procedure", argv=(), note="Under an audit config."),
                _fake_route(kind="procedure", argv=(), note="Under the target's own."),
            )
        },
    ):
        (row,) = routed_invocations()
    assert row.note == "Under an audit config.\n\nUnder the target's own."


def test_an_alternative_route_does_not_explain_an_absence_a_runs_route_owns(
    monkeypatch,
):
    """`test/mutation`'s Stryker group is this shape.

    A `procedure: runs` install-and-run beside a `command: alternative`
    one-shot. The `alternative` route's command is already carried as a form,
    and it is not what a default run took, so the reason the row prescribes no
    command is the `runs` route's alone. Composing both would attribute the
    one-shot runner's caveat to a row that never reached for it.
    """
    with _records_replaced_by(
        monkeypatch,
        {
            "x/y": _fake_record(
                _fake_route(
                    kind="procedure", argv=(), note="Install it and run there."
                ),
                _fake_route(
                    disposition="alternative",
                    argv=("npx", "--package", "t", "--", "t", "run"),
                    note="Where you reach for a one-shot runner anyway.",
                ),
            )
        },
    ):
        (row,) = routed_invocations()
    assert row.note == "Install it and run there."
    assert any("npx" in form for form, _ in row.forms), row.forms


def test_a_group_with_no_prescribed_route_falls_back_to_every_route(monkeypatch):
    """`arch/size`'s `wc` is one `alternative` route and nothing else.

    Restricting to `disposition: runs` would leave no candidate at all there,
    so the fallback is every route in the group - which for a lone route is
    the route itself, exactly what the rule this replaced did for it.
    """
    with _records_replaced_by(
        monkeypatch,
        {
            "x/y": _fake_record(
                _fake_route(disposition="alternative", argv=(), note="A rougher count.")
            )
        },
    ):
        (row,) = routed_invocations()
    assert row.note == "A rougher count."


def test_the_multi_route_no_command_groups_are_the_ones_the_rule_was_written_for():
    """Held by identity, because the rule is invisible on the python selection.

    Every one is `lang: typescript`, so the python `routed_invocations` builds
    no row from any of them and this file exercises the composition only on
    constructed records; the TypeScript harness builds those rows. That is the
    whole reason this property exists here: if
    these groups leave the tree, the rule stops having a subject and nothing
    else would say so, and a new arrival should be read against the three axes
    the rule settles - `needs`, `applies_when` and `disposition` - rather than
    discovered by a crash in whoever widens the selection.

    Seven groups are discriminated by exactly one of those axes -
    `test/mutation/@stryker-mutator/core` on `disposition`, the six ESLint
    groups on `needs` - and `test/coverage-reach/c8` differs on `needs`,
    `applies_when` and `disposition` together, since its Vitest route is
    `forbidden` and carries neither tier nor axis; no group in the tree splits
    on `applies_when` alone. The ESLint groups are an audit-owned flat config that
    carries no tier beside the target's own config that carries
    `target-execution`. `arch/hidden-coupling/eslint` was read against the
    three when it arrived and is a second instance of the `needs` axis rather
    than a fourth shape, which is why it is added here rather than sent back to
    the rule.
    """
    checks, errors = load_checks(SKILLS_DIR)
    assert not errors, errors
    groups: dict[tuple[str, str, str], list] = {}
    for check_id, record in checks.items():
        for route in record.routes:
            if route.tool:
                groups.setdefault((check_id, route.lang, route.tool), []).append(route)
    multi = {
        f"{check_id}/{tool}"
        for (check_id, _, tool), routes in groups.items()
        if len(routes) > 1
        and not any(
            r.kind == "command"
            and r.disposition == "runs"
            and (r.argv or r.argv_by_partition)
            for r in routes
        )
    }
    assert multi == {
        "arch/complexity/eslint",
        "arch/hidden-coupling/eslint",
        "security/crypto/eslint",
        "security/dangerous-calls/eslint",
        "security/injection/eslint",
        "security/unsafe-io/eslint",
        "test/coverage-reach/c8",
        "test/mutation/@stryker-mutator/core",
    }, multi


def test_a_routed_row_carries_the_records_second_command(monkeypatch):
    with _records_replaced_by(
        monkeypatch,
        {
            "x/y": _fake_record(
                _fake_route(
                    tool="coverage.py",
                    argv=("coverage", "run", "-m", "pytest"),
                    then=("coverage", "report", "--show-missing"),
                )
            )
        },
    ):
        (row,) = routed_invocations()
    assert row.then == ("coverage", "report", "--show-missing")


def test_a_second_command_is_a_form_of_its_own(monkeypatch):
    """A `then` that contributed no form would drop the second command out of
    `forms` while the row still ran it, and every property reading forms would
    pass. It takes the route's disposition because it is that route's second
    half rather than a route of its own.
    """
    with _records_replaced_by(
        monkeypatch,
        {
            "x/y": _fake_record(
                _fake_route(argv=("t", "run"), then=("t", "report")),
                _fake_route(
                    argv=("t", "old"),
                    then=("t", "old-report"),
                    disposition="superseded",
                ),
            )
        },
    ):
        (row,) = routed_invocations()
    assert row.forms == (
        ("t run", "runs"),
        ("t report", "runs"),
        ("t old", "superseded"),
        ("t old-report", "superseded"),
    )
    assert row.then == ("t", "report")


def test_a_route_with_no_shared_argv_takes_its_forms_from_the_per_partition_commands():
    """Otherwise the row declares the empty string as a form.

    `Invocation._check_forms` raises on it, so the failure is loud rather than
    silent - which is the only reason this is a design decision and not a
    defect waiting for the first record to carry the shape. Each per-partition
    command is a command the row runs, so each is a form; a form no command
    carries and a command no form declares are the two halves the guards hold
    against each other, and a form derived from the shared argv alone would
    leave every per-partition command in the second category.
    """
    route = _fake_route(
        kind="command",
        tool="t",
        argv=(),
        argv_by_partition={"uv": ("t", "u"), "pip": ("t", "p")},
    )
    assert _forms_for("c/x", "t", route) == (("t u", "runs"), ("t p", "runs"))


def test_two_partitions_prescribing_the_same_command_declare_it_once():
    """`_check_forms` raises on a duplicate form, and one command is one form."""
    route = _fake_route(
        kind="command",
        tool="t",
        argv=(),
        argv_by_partition={"uv": ("t", "s"), "pip": ("t", "s")},
    )
    assert _forms_for("c/x", "t", route) == (("t s", "runs"),)


def test_two_partitions_prescribing_argv_that_joins_the_same_are_one_form():
    """Dedup is on the joined string, not the argv tuple.

    `("t", "run part")` and `("t", "run", "part")` are distinct tuples that
    both join to `"t run part"`. Deduplicating tuples would let both through
    as separate forms, and `_check_forms` would then raise on the joined
    duplicate - the dedup here has to anticipate that, not just match it.
    """
    route = _fake_route(
        kind="command",
        tool="t",
        argv=(),
        argv_by_partition={"uv": ("t", "run part"), "pip": ("t", "run", "part")},
    )
    assert _forms_for("c/x", "t", route) == (("t run part", "runs"),)


def test_a_routed_row_expands_a_per_partition_argv(monkeypatch):
    """A route may carry both a shared argv and per-partition ones, and an
    unnamed partition then takes the shared argv. That combination is still
    the one shape #67 leaves unexpressed after this: a route with no shared
    argv at all can now say a partition the map does not name has none, but
    a route that also carries a shared argv, like this one, still cannot
    single one partition out from the rest.

    Asserts `row.forms` too, not only `row.argv` and `row.argv_by_partition`,
    and that assertion is the point of the test rather than a decoration on
    it. No check record carries the mixed shape, so the 50-row baseline
    comparison has nothing to hold a `forms` derivation for it against. When
    a record does arrive, its expectations are generated from this same code,
    so a wrong derivation for the mixed case would self-certify rather than
    fail. Other tests construct the mixed shape for what they are each
    about - `own_runner`'s fallback partitions, in the sibling below - and
    none of them reads `forms`, so this assertion is where a wrong mixed-case
    derivation is caught and deleting it as redundant loses that.
    """
    with _records_replaced_by(
        monkeypatch,
        {
            "x/y": _fake_record(
                _fake_route(
                    tool="cyclonedx-py",
                    argv=("cyclonedx-py", "requirements"),
                    argv_by_partition={"uv": ("uv", "export", "--frozen")},
                    own_runner=("uv",),
                )
            )
        },
    ):
        (row,) = routed_invocations()
    assert row.argv == ()
    assert dict(row.argv_by_partition)["uv"] == ("uv", "export", "--frozen")
    assert dict(row.argv_by_partition)["pip"] == ("cyclonedx-py", "requirements")
    assert row.own_runner == ("uv",)
    assert row.forms == (
        ("cyclonedx-py requirements", "runs"),
        ("uv export --frozen", "runs"),
    )


def test_own_runner_true_covers_every_partition(monkeypatch):
    with _records_replaced_by(
        monkeypatch,
        {"x/y": _fake_record(_fake_route(argv=("npx", "cloc"), own_runner=True))},
    ):
        (row,) = routed_invocations()
    assert row.own_runner == PARTITIONS
    assert row.argv == ("npx", "cloc")


def test_own_runner_true_covers_the_partitions_a_shared_argv_falls_back_to(monkeypatch):
    """The combination `true` means, and the claim no validator can check.

    A route may carry a shared `argv` and override only some partitions.
    `true` there says every command the route prescribes is complete as
    written - the overrides and the shared fallback alike - so it threads to
    every partition, including the ones running the fallback. That is the
    semantics, pinned here because nothing else in the suite exercised the
    pair and the enumeration's behaviour on it would otherwise be incidental.

    It is also the shape an author can get wrong with no error anywhere.
    Whether a command needs a runner in front of it is a fact about the
    command, not about the schema, so neither form of this field is verifiable
    by the loader or here: `true` on a route whose overrides are runner-led and
    whose shared fallback is not - `cyclonedx-py requirements`, which needs
    fetching - claims the fallback is complete and every partition running it
    then goes unfetched. The list form is the correct spelling there, naming
    the partitions whose command really is complete. Recorded rather than
    guarded, because the alternative is inferring the claim from whether the
    first token looks like a runner, which is the mechanism this whole schema
    exists to replace.
    """
    with _records_replaced_by(
        monkeypatch,
        {
            "x/y": _fake_record(
                _fake_route(
                    argv=("cyclonedx-py", "requirements"),
                    argv_by_partition={"uv": ("uv", "export", "--frozen")},
                    own_runner=True,
                )
            )
        },
    ):
        (row,) = routed_invocations()
    assert row.own_runner == PARTITIONS
    carried = dict(row.argv_by_partition)
    assert carried["uv"] == ("uv", "export", "--frozen")
    assert carried["pip"] == ("cyclonedx-py", "requirements")
    assert set(carried) == set(PARTITIONS)


def test_own_runner_true_on_a_route_with_no_shared_argv_covers_its_own_partitions(
    monkeypatch,
):
    """`true` on a route with no shared argv used to raise regardless of
    which partitions it named.

    `_own_runner_partitions` expanded `true` to every entry in `PARTITIONS`
    unconditionally, and `Invocation._check_own_runner` raises for an
    own_runner partition with nothing prescribed - which every partition
    this route's map does not name legitimately has, once a route may omit
    the shared argv at all. A record writing exactly this shape would load
    cleanly and then raise at `routed_invocations()`. `true` now covers only
    the partitions the route prescribes a command for, so this shape loads
    and enumerates instead.
    """
    with _records_replaced_by(
        monkeypatch,
        {
            "x/y": _fake_record(
                _fake_route(
                    tool="t",
                    argv=(),
                    argv_by_partition={"uv": ("t", "u"), "pip": ("t", "p")},
                    own_runner=True,
                )
            )
        },
    ):
        (row,) = routed_invocations()
    assert row.own_runner == ("uv", "pip")


def test_a_key_that_is_not_a_partition_is_refused_by_name(monkeypatch):
    """A python route's `argv_by_partition` keys are this lens's partition
    names. A key that is not one threads into an `argv_by_partition` entry
    `prescribed` never finds, so the command silently never runs.
    """
    with (
        _records_replaced_by(
            monkeypatch,
            {
                "x/y": _fake_record(
                    _fake_route(argv=("t",), argv_by_partition={"pnpm": ("pnpm", "t")})
                )
            },
        ),
        pytest.raises(ValueError, match="not a partition"),
    ):
        routed_invocations()


def test_a_bad_key_on_a_superseded_only_route_is_refused_too(monkeypatch):
    """`_partition_keys`'s raise must fire from `_forms_for` on its own,
    not only by way of `_argv_by_partition`.

    The test above goes through `_argv_by_partition`, which only runs for
    the `runs` route. A record whose only python command route for a tool is
    `superseded`, with no `runs` route alongside it, never reaches
    `_argv_by_partition` at all - `_forms_for` is the only call that ever
    checks this route's keys, which is why it is called for every command
    route rather than only the `runs` one.
    """
    with (
        _records_replaced_by(
            monkeypatch,
            {
                "x/y": _fake_record(
                    _fake_route(
                        tool="t",
                        argv=(),
                        argv_by_partition={"pnpm": ("pnpm", "t")},
                        disposition="superseded",
                    )
                )
            },
        ),
        pytest.raises(ValueError, match="not a partition"),
    ):
        routed_invocations()


def test_no_completion_hardcodes_a_name_the_fixture_spec_owns():
    """A completion derives a seeded name rather than spelling it out.

    A completion names paths inside the fixture tree, and `python_fixture_spec`
    owns those names. A token spelling one out reads identically to one
    deriving it - both produce
    `src/fixture_app` today - so no assertion over the built value can tell
    them apart, and the difference only appears the day the spec renames the
    package: every derived site follows and a spelled-out one silently does
    not.

    So this reads the source of the `COMPLETIONS` literal rather than its
    value. `arch/cycles`'s `pydeps` completion is the live instance: it was
    `f"src/{PACKAGE}"` in the table this overlay replaced, became the literal
    when the value was transcribed instead of the expression, and nothing
    that compares built tokens could have caught it.
    """
    source = (REPO_ROOT / "scripts" / "run_python_fixture_lens.py").read_text()
    tree = ast.parse(source)
    literal = next(
        node
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "COMPLETIONS"
    )
    block = ast.get_source_segment(source, literal)
    assert PACKAGE not in block, (
        f"a COMPLETIONS token spells out {PACKAGE!r} rather than deriving it "
        "from PACKAGE, so it will not follow a rename of the seeded package"
    )


def test_a_scanner_hit_that_needs_confirming_reaches_the_grade_as_a_candidate(
    tmp_path, monkeypatch
):
    """The route's `alone_insufficient` travels from the record to the worksheet.

    `security/injection`'s scanner routes each say a hit is a candidate until a
    source-to-sink trace confirms it, and the lens classifies a scanner that
    ran and printed the seed as `ok` - the engine's status, which does not move
    for the caveat. So the results row has to carry the caveat beside the
    status, and the grade has to print it, or a hit on the seed reads as the
    check answered, which is #154's defect. A route whose result does stand
    alone, `security/crypto`'s `bandit`, carries nothing, so the field is not
    set on every row regardless of what the record says.
    """
    import grade_python_fixture_run as grader

    source = tmp_path / "fixture" / "uv"
    source.mkdir(parents=True)
    (source / "pyproject.toml").write_text("[project]\n")
    monkeypatch.setattr(
        "run_python_fixture_lens._run",
        _fake_run([], respond=lambda command: _outcome(stdout="B602 shell=True")),
    )

    observed = run_partition("uv", source, tmp_path / "work", "none", timeout=5)

    checks, errors = load_checks(SKILLS_DIR)
    assert not errors, errors
    rows = {(r["check"], r["tool"]): r for r in observed["results"]}
    for route in checks["security/injection"].routes:
        if route.lang == "python" and route.kind == "command":
            row = rows[("security/injection", route.tool)]
            assert row["alone_insufficient"] == route.alone_insufficient, route.tool
            assert row["alone_insufficient"], route.tool
    assert rows[("security/crypto", "bandit")]["alone_insufficient"] == ""

    graded = [r for r in grader.grade_rows(observed) if r.check == "security/injection"]
    assert graded and graded[0].owed
    candidates = [o for o in graded[0].observations if o.status == "ok"]
    assert candidates and all(o.alone_insufficient for o in candidates)
    text = grader.render(graded)
    assert "not the check's answer alone" in text
    assert "Still owed:" in text


def test_the_rows_carrying_a_caveat_are_the_records_saying_their_result_needs_one():
    """The lens's rows carry `alone_insufficient` exactly where the records do.

    The spec derives which expectations state `owed` from the records; this
    holds the lens's own rows to the same population, so a lens that dropped
    the field on one branch of `routed_invocations` - the no-command branch is
    the one the `grimp` library rows take - fails here rather than reading as
    a route whose result stands alone.
    """
    checks, errors = load_checks(SKILLS_DIR)
    assert not errors, errors
    expected = {
        check_id
        for check_id, record in checks.items()
        for route in record.routes
        if route.lang == "python"
        and route.tool
        and route.disposition != "forbidden"
        and route.alone_insufficient
    }
    carried = {i.check for i in routed_invocations() if i.alone_insufficient}
    assert carried == expected


def test_disagreeing_caveats_on_a_row_with_no_command_are_composed(monkeypatch):
    """A group with no `runs` route has no one route to read the field from.

    So the row carries each caveat, in record order, as it carries each note.
    Refusing the row instead made the TypeScript selection raise over
    `arch/hidden-coupling`'s two `eslint` modes, which each state a caveat of
    their own; a caveat two routes share is carried once.
    """
    records = {
        "x/y": _fake_record(
            _fake_route(kind="library", argv=(), note="a", alone_insufficient="one"),
            _fake_route(kind="library", argv=(), note="b", alone_insufficient="two"),
            _fake_route(kind="library", argv=(), note="c", alone_insufficient="one"),
        )
    }
    with _records_replaced_by(monkeypatch, records):
        (row,) = routed_invocations()
    assert row.alone_insufficient == "one\n\ntwo"


def test_the_inventory_environment_route_reads_the_venv_through_its_interpreter():
    """`cyclonedx-py environment` names the venv's interpreter and runs isolated.

    Inside the environment, with the tool layered on by `uv run --with`, the
    SBOM lists the overlay's packages beside the target's - 37 components
    against the seeded uv partition's 7, with `packaging` at two versions - so
    the route is not `in_env`; given the interpreter, the isolated tool lists
    the 7. Starting that interpreter runs its `.pth` files, which is execution,
    so the tier is `target-execution`.
    """
    checks, errors = load_checks(SKILLS_DIR)
    assert not errors, errors
    (route,) = [
        r
        for r in checks["deps/inventory"].routes
        if r.tool == "cyclonedx-py" and r.argv and "environment" in r.argv
    ]
    assert route.argv == ("cyclonedx-py", "environment", "<path-to-venv-python>")
    assert route.package == "cyclonedx-bom"
    assert not route.in_env
    assert route.needs == "target-execution"
    assert route.disposition == "alternative"
