"""Every section `audit-core` moved out of `SKILL.md` is still reached (#85).

Progressive disclosure trades one risk for another. Before it, `SKILL.md`
carried sections that most runs loaded and no run read. After it, a section
lives in `references/` and is read only if something points at it - so the new
failure is a reference nobody links, which is the same defect as an
instruction in a file the reader never opens. That one is silent: the file is
present, the prose is correct, and no run ever sees it.

So the properties here are about reachability rather than content: every
reference is linked from `SKILL.md`, every link resolves, and the pointer
replaced the text rather than sitting beside a copy of it. What none of them
can check is whether the pointer says enough for a reader to know when to
follow it, which is a reading pass.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_CORE = REPO_ROOT / ".agents" / "skills" / "audit-core" / "SKILL.md"
REFERENCES = AUDIT_CORE.parent / "references"

# A line long enough that finding it in two files means duplication rather
# than two files happening to share a short phrase.
_MIN_DUPLICATE = 120

_LINK_RE = re.compile(r"\]\((references/[^)\s]+)\)")


def _reference_files() -> list[Path]:
    return sorted(REFERENCES.glob("*.md"))


def test_the_references_directory_is_not_empty() -> None:
    """The vacuity guard: an empty directory passes every property below.

    Without this, deleting the references and inlining the sections again
    leaves this module green over a tree it no longer describes.
    """
    assert _reference_files(), (
        f"{REFERENCES} holds no reference file, so every property in this "
        "module is vacuous. If the sections were inlined again, delete this "
        "module rather than leaving it passing over nothing"
    )


def test_every_reference_is_linked_from_the_skill_file() -> None:
    """A reference nothing points at is a section no run reads.

    This is the defect progressive disclosure introduces, and the reason it is
    worth a test rather than a convention: an orphaned reference is a file that
    exists, reads correctly, and reaches nobody, which no other property here
    or in the suite would notice.
    """
    linked = {
        m.group(1) for m in _LINK_RE.finditer(AUDIT_CORE.read_text(encoding="utf-8"))
    }
    orphans = [
        p.name for p in _reference_files() if f"references/{p.name}" not in linked
    ]
    assert orphans == [], (
        f"{AUDIT_CORE.name} links none of: {orphans}. A reference is read only "
        "where something sends a reader to it, so an unlinked one is a section "
        "of this engine that no path through the family reaches"
    )


def test_every_reference_link_resolves() -> None:
    """The other direction: a pointer at a file that is not there.

    A run following it gets nothing and has no way to tell that the
    instruction it was sent for exists at all.
    """
    text = AUDIT_CORE.read_text(encoding="utf-8")
    missing = [
        target
        for target in {m.group(1) for m in _LINK_RE.finditer(text)}
        if not (AUDIT_CORE.parent / target).is_file()
    ]
    assert missing == [], (
        f"{AUDIT_CORE.name} points at files that do not exist: {missing}"
    )


def test_a_moved_section_is_not_also_still_inline() -> None:
    """The pointer replaced the text rather than joining a copy of it.

    Two authorities for one rule is what this family's record schema exists to
    avoid, and a move that left the prose behind would produce exactly that:
    the reference and the section it came from, drifting apart with nothing
    holding them together.
    """
    inline = AUDIT_CORE.read_text(encoding="utf-8")
    duplicated: list[str] = []
    for reference in _reference_files():
        for line in reference.read_text(encoding="utf-8").split("\n"):
            if len(line) >= _MIN_DUPLICATE and line in inline:
                duplicated.append(f"{reference.name}: {line[:80]}...")
    assert duplicated == [], (
        "these lines are in a reference and still in SKILL.md, so one rule has "
        f"two homes: {duplicated}"
    )
