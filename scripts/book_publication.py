"""The paperback's undecided details, read from `docs/book/publication.toml`.

A detail left out of the file, or set to an empty string, is unresolved: the
print build prints its bracketed placeholder (`PLACEHOLDERS`) in its place,
and `require_resolved` refuses a release build while any remains.
"""

from __future__ import annotations

import dataclasses
import re
import tomllib
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class PublicationDetails:
    copyright_holder: str | None = None
    copyright_year: str | None = None
    isbn: str | None = None
    cover_art: str | None = None
    back_cover_text: str | None = None


PLACEHOLDERS = {
    "copyright_holder": "[Copyright holder]",
    "copyright_year": "[Year]",
    "isbn": "[ISBN]",
    "cover_art": "[Cover art]",
    "back_cover_text": "[Back cover text]",
}
_FIELDS = tuple(f.name for f in dataclasses.fields(PublicationDetails))
_ISBN_CHARS_RE = re.compile(r"[0-9]+(?:-[0-9]+)*")


def valid_isbn13(value: str) -> bool:
    """Whether ``value`` is an ISBN-13: 13 digits, optional hyphens, a valid check digit."""
    if not _ISBN_CHARS_RE.fullmatch(value):
        return False
    digits = [int(c) for c in value if c.isdigit()]
    if len(digits) != 13:
        return False
    total = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:12]))
    return (10 - total % 10) % 10 == digits[12]


def load_details(path: Path) -> PublicationDetails:
    """Read ``path``; an empty string counts as unset.

    Raises:
        SystemExit: The file names a key that is not a detail, a value is not
            a string, or the ISBN is not a valid ISBN-13.
    """
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    unknown = sorted(set(data) - set(_FIELDS))
    if unknown:
        raise SystemExit(
            f"{path}: unknown key(s) {unknown}; the details are {list(_FIELDS)}"
        )
    values: dict[str, str | None] = {}
    for key, value in data.items():
        if not isinstance(value, str):
            raise SystemExit(
                f"{path}: {key} must be a string, not {type(value).__name__}"
            )
        values[key] = value or None
    isbn = values.get("isbn")
    if isbn is not None and not valid_isbn13(isbn):
        raise SystemExit(f"{path}: isbn {isbn!r} is not a valid ISBN-13")
    return PublicationDetails(**values)


def unresolved(details: PublicationDetails) -> list[str]:
    """The details still unset, in field order."""
    return [name for name in _FIELDS if getattr(details, name) is None]


def require_resolved(details: PublicationDetails) -> None:
    """Raise unless every detail is set, naming every unset one at once.

    Raises:
        SystemExit: Any detail is unset.
    """
    missing = unresolved(details)
    if missing:
        raise SystemExit(
            "a release build needs every publication detail; unset in "
            f"docs/book/publication.toml: {', '.join(missing)}"
        )


def typst_inputs(details: PublicationDetails) -> dict[str, str]:
    """Each detail as a ``typst compile --input`` value, or its placeholder.

    Keys are the field names with ``-`` for ``_``, and ``isbn-set`` says
    whether the ISBN is real, since the copyright page and the cover leave
    KDP's barcode area clear only for a real one.
    """
    inputs = {
        name.replace("_", "-"): getattr(details, name) or PLACEHOLDERS[name]
        for name in _FIELDS
    }
    inputs["isbn-set"] = "true" if details.isbn else "false"
    return inputs
