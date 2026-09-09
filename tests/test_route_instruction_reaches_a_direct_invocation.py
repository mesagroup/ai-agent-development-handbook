"""Keep the route-running instruction where a directly invoked skill reads it (#70).

The deep-audit entry point is a `<domain>-audit` skill invoked by name. Such
a run reads that skill's own `SKILL.md` and `audit-core/SKILL.md`, and never
`audit/SKILL.md` - so an instruction kept in the sweep front door does not
reach it, which is the defect #70 records. The instruction now lives in
`audit-core`'s `## Running a route`.

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
`docs/audit/sweep-obligations.md`, and that ledger's own tests hold the
restatement.
"""

from __future__ import annotations

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
DOMAIN_SKILLS = sorted(
    path / "SKILL.md"
    for path in SKILLS_DIR.iterdir()
    if path.is_dir() and path.name.endswith("-audit") and path.name != "audit-core"
)

# One sentence per field of the contract an agent has to read before it runs
# anything. Each is a phrase rather than a keyword on purpose: the field
# *names* still occur in the sweep, in the sentence that points at the
# section, and a name-based check would forbid the pointer along with the
# copy.
CONTRACT_SENTENCES = (
    "which applies regardless of the partition's language",
    "is the only one that hands you something to run",
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
    assert "audit-core" in skill.read_text(encoding="utf-8"), (
        f"{skill.parent.name}/{skill.name} does not name audit-core, so a direct "
        f"invocation of it never reads {SECTION!r}"
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
    so. What it may not do is describe them again: `sweep-obligations.md`
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
