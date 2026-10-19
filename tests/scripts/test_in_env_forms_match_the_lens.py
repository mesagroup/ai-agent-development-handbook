"""The engine's in-environment forms and the fixture lens's launcher agree (#202).

`audit-core/SKILL.md`'s `## Running a route` tells a real sweep how to run a
route carrying `in_env: true` on each package manager, and
`scripts/run_python_fixture_lens.py`'s `launcher` is what runs the same routes
against the seeded fixtures. Nothing else ties the two: the lens can change a
prefix after a measurement and leave the engine teaching the form it replaced,
or the engine can be reworded into a form the lens has never run. Either way
the sweep and the fixture run then disagree about how a route runs, and only
the fixture run has evidence behind it.

So the forms are derived from the lens, not transcribed: each fixtured
partition's granted `in_env` prefix is rendered with the engine's placeholders
in place of the lens's concrete values and must occur, as a code span, in the
paragraph that states the rule. Yarn is held from the other direction only -
the lens has no Yarn partition (#46), so its forms come from Yarn's
documentation, and what is held is that the paragraph says so.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from audit_checks import SKILLS_DIR
from run_python_fixture_lens import (
    PARTITIONS,
    TS_IN_ENV,
    VENV_BIN,
    Invocation,
    launcher,
)

AUDIT_CORE = Path(SKILLS_DIR) / "audit-core" / "SKILL.md"
OPENING = "**A route hands you the tool's own command line, not a runner's"

# The lens's concrete values, and the placeholder the engine writes for each.
TOOL = "some-tool"
SUBSTITUTIONS = {TOOL: "<tool>", f"{VENV_BIN}/python": "<venv-python>"}


def _paragraph() -> str:
    lines = [
        line
        for line in AUDIT_CORE.read_text(encoding="utf-8").splitlines()
        if line.startswith(OPENING)
    ]
    assert len(lines) == 1, (
        f"expected one paragraph opening {OPENING!r} in {AUDIT_CORE.name}, "
        f"found {len(lines)}"
    )
    return lines[0]


def _in_env_prefix(partition: str) -> tuple[str, ...]:
    inv = Invocation(check="c/x", tool=TOOL, argv=(TOOL,), in_env=True)
    return launcher(inv, partition, granted=True)


def _as_engine_writes_it(words: tuple[str, ...]) -> str:
    return " ".join(SUBSTITUTIONS.get(word, word) for word in words)


@pytest.mark.parametrize("partition", PARTITIONS)
def test_each_python_partition_s_in_env_form_is_the_engine_s(partition):
    """The lens's `uv run` form for this partition is written in the paragraph.

    The lens brings the tool in with `--with`, so its prefix ends in the tool
    and the engine's span ends in `<tool>`; the two non-`uv` details that
    matter - `--no-project` and the named interpreter - are inside the span,
    so dropping either from the prose or the lens fails here.
    """
    span = f"`{_as_engine_writes_it(_in_env_prefix(partition))}`"
    assert span in _paragraph(), (
        f"the lens runs an in_env route on {partition} as {span}, and "
        f"{AUDIT_CORE.name}'s paragraph does not write that form"
    )


@pytest.mark.parametrize("partition", sorted(TS_IN_ENV))
def test_each_typescript_partition_s_in_env_form_is_the_engine_s(partition):
    """The lens's tree-own-copy prefix for this manager is written in the paragraph.

    Read from `launcher` rather than from `TS_IN_ENV` directly, so a launcher
    that stopped consulting the table would fail here too. The tool is part of
    the record's argv on this side, so the engine's span ends in `<argv>`.
    """
    prefix = _in_env_prefix(partition)
    assert prefix == TS_IN_ENV[partition]
    span = f"`{_as_engine_writes_it(prefix)} <argv>`"
    assert span in _paragraph(), (
        f"the lens runs an in_env route on {partition} as {span}, and "
        f"{AUDIT_CORE.name}'s paragraph does not write that form"
    )


def test_the_yarn_forms_say_where_they_come_from():
    """Yarn has no fixture, so its forms must not read as measured ones."""
    assert "yarn" not in TS_IN_ENV, (
        "the lens now has a Yarn in_env form; hold it like npm's and pnpm's "
        "and drop the documentation-only wording from the paragraph"
    )
    text = _paragraph()
    assert "`yarn run -B <argv>`" in text
    assert "from Yarn's own documentation alone" in text


def test_the_substitutions_were_used():
    """Each placeholder mapping fires somewhere, so a renamed lens constant
    cannot leave a substitution that matches nothing and a span that only
    passes because the concrete value happens to be absent."""
    rendered = " ".join(
        _as_engine_writes_it(_in_env_prefix(p)) for p in (*PARTITIONS, *TS_IN_ENV)
    )
    for placeholder in SUBSTITUTIONS.values():
        assert placeholder in rendered, placeholder
