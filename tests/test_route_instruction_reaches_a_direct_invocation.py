"""Keep the route-running instruction where a directly invoked skill reads it (#70).

The deep-audit entry point is a `<domain>-audit` skill invoked by name. Such
a run reads that skill's own `SKILL.md`, `audit-core/SKILL.md` and the
records in its own `checks/` directory, and never `audit/SKILL.md` - so an
instruction kept in the sweep front door does not reach it, which is the
defect #70 records. The records are the other place it could have gone, and
the reason it did not is that it would then be copied once per record. The
instruction now lives in `audit-core`'s `## Running a route`.

Two properties hold that in place, and neither is checkable by reading one
file:

- **Every domain skill defers to `audit-core`**, which is why a section added
  there reaches all of them with no per-domain pointer. A new domain skill
  that forgets to defer is a domain skill the section does not reach, and
  nothing else in the suite would say so.
- **The contract has one copy.** #70's second acceptance criterion asks for
  exactly one, and the failure it guards against is not a missing copy but a
  reinstated one: a sentence of the contract reappearing in the sweep gives a
  domain agent two authorities for one rule, and the two then drift against
  the loader that validates the fields they describe.

The runner rule is deliberately *not* held to one copy. It is `restated` in
`docs/audit/sweep-obligations.md`, whose tests hold the anchor in
`audit-core` and the row's shape - not whether `audit/SKILL.md` still says
the thing. That half is the reading pass the ledger's own header asks for,
and the ledger says so itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
AUDIT_CORE = SKILLS_DIR / "audit-core" / "SKILL.md"
SWEEP = SKILLS_DIR / "audit" / "SKILL.md"

SECTION = "## Running a route"

# The domain skills, discovered rather than listed, so a skill added later is
# covered without editing this file - and so a rename cannot quietly shrink
# the checked set to nothing.
# `audit-core` is excluded by the suffix itself rather than by name.
DOMAIN_SKILLS = sorted(
    path / "SKILL.md"
    for path in SKILLS_DIR.iterdir()
    if path.is_dir() and path.name.endswith("-audit")
)

# The deferral, as every domain skill spells it. Matched as the link rather
# than as the string "audit-core": that string also occurs in each skill's
# frontmatter description and in its Announce line, so a check for the bare
# name stays green with the deferral itself deleted - which is the defect
# this file was written to catch, and it passed until the link was the test.
DEFERRAL = "](../audit-core/SKILL.md)"

# One sentence per field of the contract an agent has to read before it runs
# anything. Each is a phrase rather than a keyword on purpose: the field
# *names* still occur in the sweep, in the sentence that points at the
# section, and a name-based check would forbid the pointer along with the
# copy.
CONTRACT_SENTENCES = (
    "which applies regardless of the partition's language",
    "is the only one that hands you something to run",
    "names a package manager, not a version of one",
    "that is the record saying this partition has no command for the check",
    "and you run both, in the order the record writes them",
    "which says the prescribed command is complete as written",
    "is code the check computes over rather than invokes",
    "rather than guessing an invocation for it",
    "answers nothing for the check that lists it",
    "marks a route named only to warn against, never one to run",
    "does not by itself answer the check",
    "states a precondition the target must carry for the route to apply at all",
)


def test_the_engine_carries_the_section() -> None:
    """`audit-core` has the section every other assertion here points at."""
    assert SECTION in AUDIT_CORE.read_text(encoding="utf-8"), (
        f"{AUDIT_CORE.parent.name}/{AUDIT_CORE.name} has no {SECTION!r} heading - "
        "a directly invoked domain skill then reads no route instruction at all"
    )


def test_the_sweep_points_at_the_section_rather_than_carrying_it() -> None:
    """The sweep's pointer names the section, so a rename cannot orphan it."""
    assert SECTION in SWEEP.read_text(encoding="utf-8"), (
        f"{SWEEP.parent.name}/{SWEEP.name} does not name {SECTION!r}. It gave up "
        "its own copy of the contract, so a broken pointer leaves a dispatched "
        "domain agent with nothing telling it to read the section"
    )


@pytest.mark.parametrize("skill", DOMAIN_SKILLS, ids=lambda p: p.parent.name)
def test_every_domain_skill_defers_to_the_engine(skill: Path) -> None:
    """A domain skill names `audit-core`, so the section reaches a direct run.

    This is what makes one copy sufficient. A domain skill that does not
    defer is one whose direct invocation reads no route instruction, and the
    symptom is an agent inventing a command line rather than an error.
    """
    text = skill.read_text(encoding="utf-8")
    assert DEFERRAL in text, (
        f"{skill.parent.name}/{skill.name} does not link {DEFERRAL}, so a direct "
        f"invocation of it never reads {SECTION!r}. The skill's frontmatter and "
        "its Announce line both mention audit-core by name, so the name is not "
        "evidence that the deferral is still there"
    )
    assert SECTION in text, (
        f"{skill.parent.name}/{skill.name} defers to audit-core without naming "
        f"{SECTION!r}. The deferral summarises what that file owns, and an agent "
        "reading a summary as a table of contents stops at the loop - which is "
        "how the one section a direct run needs most goes unread"
    )


def test_the_domain_skills_were_found() -> None:
    """The parametrised check above ran over a real population.

    Discovery by directory suffix is convenient and silently yields nothing
    if the tree moves, which would leave the deferral check passing over an
    empty set.
    """
    assert len(DOMAIN_SKILLS) > 1, (
        f"found {len(DOMAIN_SKILLS)} domain skill(s) under {SKILLS_DIR}; the "
        "deferral check needs the real population to mean anything"
    )
    assert all(path.is_file() for path in DOMAIN_SKILLS)


def test_the_contract_sentences_cover_the_fields() -> None:
    """The hand-written tuple did not shrink.

    `DOMAIN_SKILLS` is discovered and has a floor; this tuple is written out,
    so an entry deleted to make a reword pass takes its field's rule out of
    both checks below with nothing to say so. The floor is the number of
    fields the contract covers, so it moves only when the contract does.
    """
    assert len(CONTRACT_SENTENCES) >= 12, (
        f"{len(CONTRACT_SENTENCES)} contract sentences, which is fewer than the "
        "route contract has fields with a rule. Add the sentence for the field "
        "you are covering rather than lowering this floor"
    )
    assert len(set(CONTRACT_SENTENCES)) == len(CONTRACT_SENTENCES)


@pytest.mark.parametrize("sentence", CONTRACT_SENTENCES)
def test_each_contract_sentence_is_in_the_engine(sentence: str) -> None:
    """The contract is where a directly invoked skill will look for it.

    Paired with the next test: this one fails if a sentence was dropped in a
    reword, that one if it was reinstated in the sweep. Either alone would
    pass over a contract that had moved back.
    """
    found = AUDIT_CORE.read_text(encoding="utf-8").count(sentence)
    assert found == 1, (
        f"{sentence!r} occurs {found} times in {AUDIT_CORE.name} (expected 1). "
        "Zero means the route contract lost a field's rule; more than one means "
        "the section says it twice"
    )


@pytest.mark.parametrize("sentence", CONTRACT_SENTENCES)
def test_no_contract_sentence_is_back_in_the_sweep(sentence: str) -> None:
    """One copy, which is #70's second acceptance criterion.

    The sweep may point at the section and may name the fields while doing
    so, and it may restate one where the ledger says it does and why - the
    runner bullet states the yarn instance of the `argv_by_partition` key
    rule, because choosing between a keyed entry and the shared `argv` on a
    Yarn classic partition is a runner choice. This check is over the
    engine's wording, so a deliberate restatement in the sweep's own words
    passes and a copy does not, which is the line the ledger draws too.
    What the sweep may not do is take a field's rule back: `sweep-obligations.md`
    dispositions these obligations `delegated` precisely because a second
    authority for one rule is the failure, and the fields are validated by
    `scripts/audit_checks.py`, so the copy that drifts is a contract
    disagreeing with itself rather than prose disagreeing with prose.
    """
    assert sentence not in SWEEP.read_text(encoding="utf-8"), (
        f"{SWEEP.parent.name}/{SWEEP.name} carries {sentence!r} again. The route "
        f"contract belongs to {AUDIT_CORE.name}'s {SECTION!r}; the sweep points "
        "at it. If the sweep genuinely needs to restate this rule, say so in "
        "docs/audit/sweep-obligations.md and change that row's disposition"
    )


def test_the_engine_s_worked_examples_still_exist() -> None:
    """The routes `## Running a route` names by id are still that shape.

    The section teaches the runner rule from two records: `test/coverage-reach`,
    whose `pytest` invocation needs the target's own environment and so takes
    `uv run --with`, and `test/new-code-coverage`, whose `diff-cover` is a PyPI
    package fetched onto a partition of any language. Both are cited by check
    id in normative prose, so a record edited later leaves the engine teaching
    from a route that no longer exists - and CLAUDE.md's rule is that a
    consistency property which can move into the validator does.

    Asserted on the shape the lesson depends on, not on the whole route: that
    the coverage route's command is `pytest` while its tool is not, which is
    what makes it the `uv run --with` case rather than the `uvx` one.
    """
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from audit_checks import load_checks

    checks, errors = load_checks(SKILLS_DIR)
    assert not errors, errors

    text = AUDIT_CORE.read_text(encoding="utf-8")
    for check_id in ("test/coverage-reach", "test/new-code-coverage"):
        assert check_id in text, (
            f"{AUDIT_CORE.name}'s {SECTION!r} no longer cites {check_id!r}. If the "
            "worked example moved, point this guard at the record it moved to"
        )
        assert check_id in checks, (
            f"{check_id!r} is cited in {SECTION!r} and does not exist"
        )

    coverage = [
        route
        for route in checks["test/coverage-reach"].routes
        if route.kind == "command" and route.argv and route.argv[0] == "pytest"
    ]
    assert len(coverage) == 1, (
        f"{SECTION!r} teaches the `uv run --with` case from test/coverage-reach's "
        f"`pytest` command route; found {len(coverage)} such route(s)"
    )
    assert coverage[0].in_env, (
        f"{SECTION!r} teaches the `uv run --with` case from that route because it "
        "carries `in_env`, which is what says the command must run inside the "
        "materialized environment. Without the field the route is an argument for "
        "the isolated runner instead, and the section's rule cites the wrong record"
    )
    assert coverage[0].tool != "pytest", (
        f"{SECTION!r} argues that route needs `uv run --with` because the command "
        f"is `pytest` while the package to fetch is {coverage[0].tool!r}. With the "
        "tool named `pytest` the example stops making that point"
    )

    diff_cover = [
        route
        for route in checks["test/new-code-coverage"].routes
        if route.tool == "diff-cover"
    ]
    assert diff_cover, (
        f"{SECTION!r} teaches the registry-not-lang rule from test/new-code-coverage's "
        "`diff-cover` route, which is no longer in that record"
    )
