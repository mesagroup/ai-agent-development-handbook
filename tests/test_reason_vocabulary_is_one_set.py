"""Keep the `no-evidence` reason vocabulary one set across its three copies (#74).

`audit-core/SKILL.md` defines the reasons, `audit/SKILL.md` restates them in
the list that tells a domain agent how to render `no-evidence`, and
`scripts/run_python_fixture_lens.py` mirrors the subset a run of that harness
can produce. Three copies in two languages, and nothing held them together:
adding a reason to the engine and forgetting the sweep leaves a domain agent
enumerating three where the engine has four, which does not fail any gate and
does not look like anything when read.

Both sets are **parsed out of the prose** rather than written here as a
literal. A test that spells the expected reasons would be a fourth copy, and
it would pass whenever it agreed with itself while the files disagreed.

**What this cannot reach is a copy that names no reason.** `data-protection-audit`
went stale on the fourth reason by paraphrase - "because a grant was withheld,
because no candidate could be obtained, or because one ran and failed - all
three of which a different environment would fix" - and nothing here matches a
sentence like that, because there is no reason name in it to parse. A reading
pass found it. So this module holds the copies that spell the names, and the
prose pass over the rest stays load-bearing rather than being replaced by a
green suite.

The lens is deliberately not equal to the engine's set. `not-prescribed` is a
check's verdict on a partition; a row in that harness is one invocation's
observation, and where a record prescribes no command there is no invocation
to report on - the harness represents that as an empty status, which its own
comment records. So this module asserts the exact difference rather than
equality, and a change to either side has to come here and say which it is.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_CORE = REPO_ROOT / ".agents" / "skills" / "audit-core" / "SKILL.md"
SWEEP = REPO_ROOT / ".agents" / "skills" / "audit" / "SKILL.md"

# The one reason the engine has and the harness cannot produce. Named here
# because the difference is the claim; if it ever becomes producible, this
# module is where that has to be said out loud.
LENS_CANNOT_PRODUCE = frozenset({"not-prescribed"})

# The engine writes each reason as `name` followed by its parenthesised gloss;
# the sweep writes each as `name` followed by the case it covers. Anchored to
# the paragraph in each file rather than run over the whole file, since both
# mention individual reason names in other sentences.
_CORE_SPAN = (
    "carries a reason, because the ways a check can fail to run",
    "Render the reason with the status",
)
_SWEEP_SPAN = (
    "Render `no-evidence` with the reason that produced it",
    "If the check has no lens",
)
_CORE_REASON = re.compile(r"`([a-z][a-z-]+)` \(")
_SWEEP_REASON = re.compile(r"`([a-z][a-z-]+)` where ")

# Every hyphenated code span in a vocabulary paragraph, whatever follows it.
# The strict patterns above encode the house style - a reason is written as a
# name then its gloss - and a reason introduced in some other style would slip
# past them silently, which is the same failure as a parse that finds nothing
# and is not caught by a floor. So each span is read twice and the two must
# agree.
_ANY_HYPHENATED = re.compile(r"`([a-z][a-z]*-[a-z][a-z-]*)`")

# Hyphenated names in those paragraphs that are not reasons. Both are statuses:
# the sweep's rendering sentence opens by naming the status it is rendering.
NOT_A_REASON = frozenset({"no-evidence", "not-applicable"})


def _paragraph(text: str, start: str, end: str) -> str:
    """The slice of `text` between two markers, both of which must be there."""
    i = text.find(start)
    assert i != -1, f"{start!r} is not in the file; the vocabulary paragraph moved"
    j = text.find(end, i)
    assert j != -1, f"{end!r} does not follow {start!r}; the paragraph's end moved"
    return text[i:j]


def _engine_span() -> str:
    return _paragraph(AUDIT_CORE.read_text(encoding="utf-8"), *_CORE_SPAN)


def _sweep_span() -> str:
    return _paragraph(SWEEP.read_text(encoding="utf-8"), *_SWEEP_SPAN)


def _engine_reasons() -> set[str]:
    return set(_CORE_REASON.findall(_engine_span()))


def _sweep_reasons() -> set[str]:
    return set(_SWEEP_REASON.findall(_sweep_span()))


def _lens_reasons() -> set[str]:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import run_python_fixture_lens

    return set(run_python_fixture_lens.REASONS)


def test_the_parse_found_a_real_vocabulary() -> None:
    """Neither extraction silently matched nothing.

    Both are regexes over prose, so the failure that matters is not a
    disagreement but a reword that makes one side parse to the empty set -
    whereupon every comparison below passes over nothing.
    """
    engine, sweep = _engine_reasons(), _sweep_reasons()
    assert len(engine) >= 4, (
        f"parsed {sorted(engine)} out of {AUDIT_CORE.name}, which is fewer reasons "
        "than the engine has. The gloss pattern changed, and this module is "
        "reading a paragraph it no longer understands"
    )
    assert len(sweep) >= 4, (
        f"parsed {sorted(sweep)} out of {SWEEP.name}, which is fewer reasons than "
        "its rendering list names"
    )
    # The floor is a lower bound, so it passes on a parse that found four of
    # five. Reading each span a second time with a pattern that does not care
    # what follows the name is what catches a reason written in a new style.
    for name, span, strict in (
        (AUDIT_CORE.name, _engine_span(), engine),
        (SWEEP.name, _sweep_span(), sweep),
    ):
        loose = set(_ANY_HYPHENATED.findall(span)) - NOT_A_REASON
        assert loose == strict, (
            f"{name}'s vocabulary paragraph names {sorted(loose)} and the house "
            f"style parses {sorted(strict)}. A reason written in a different "
            "shape is invisible to every comparison below - write it the way "
            "its neighbours are written, or, if it is not a reason at all, add "
            f"it to NOT_A_REASON in {Path(__file__).name} and say why"
        )


def test_the_sweep_enumerates_the_engine_s_reasons() -> None:
    """A reason the sweep omits is one a dispatched agent will not report."""
    engine, sweep = _engine_reasons(), _sweep_reasons()
    assert engine == sweep, (
        f"{AUDIT_CORE.name} defines {sorted(engine)} and {SWEEP.name}'s rendering "
        f"list names {sorted(sweep)}. Only in the engine means a domain agent "
        "never reports it; only in the sweep means it is rendered against a "
        "vocabulary the engine does not define"
    )


def test_the_lens_mirrors_the_engine_minus_what_it_cannot_observe() -> None:
    """The harness's subset is exactly the stated difference, not merely a subset.

    Asserted as an equality on the difference so it fails in both directions:
    a reason added to the engine and not considered here, and a reason dropped
    from the lens without saying why.
    """
    engine, lens = _engine_reasons(), _lens_reasons()
    assert lens <= engine, (
        f"the lens has {sorted(lens - engine)} which the engine does not define"
    )
    assert engine - lens == set(LENS_CANNOT_PRODUCE), (
        f"the engine defines {sorted(engine)} and the lens produces {sorted(lens)}, "
        f"a difference of {sorted(engine - lens)} where this module records "
        f"{sorted(LENS_CANNOT_PRODUCE)}. If the lens can now produce one of these, "
        "add it to REASONS and remove it here; if the engine grew a reason the "
        "lens cannot observe, say so here and in the tuple's own comment"
    )


def test_the_engine_says_which_reason_wins_where_two_are_true() -> None:
    """The precedence rule is what stops the new reason being a false lead.

    Without it a partition whose record prescribes nothing but which keeps a
    tiered route reads as unanswerable, when re-running with the grant answers
    it. Held in both files because the sweep's copy is the one an agent reads
    with a route in hand.
    """
    for name, span in ((AUDIT_CORE.name, _engine_span()), (SWEEP.name, _sweep_span())):
        assert "the one a reader can act on" in span, (
            f"{name}'s vocabulary paragraph no longer states which reason wins "
            "where more than one is true, so `not-prescribed` can be reported "
            "over an actionable `not-permitted`. Scoped to the paragraph on "
            "purpose: the rule has to be where the reasons are enumerated, not "
            "somewhere else in the file"
        )
