"""KDP's paperback numbers: margins, spine, cover size and barcode area.

Every value is copied from KDP's help pages, named beside it, so a change
on KDP's side is a change to one constant here. All lengths are inches.
"""

from __future__ import annotations

from typing import Literal

Paper = Literal["white", "cream"]

# https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6
# ("Set Trim Size, Bleed, and Margins"): 5 x 8 in, black ink, cream paper.
MIN_PAGES = 24
MAX_PAGES = 828
# Inside (gutter) margin minimum by the highest page count it covers.
_GUTTER_BANDS = ((150, 0.375), (300, 0.5), (500, 0.625), (700, 0.75), (828, 0.875))
OUTSIDE_MARGIN_MIN_IN = 0.25

# https://kdp.amazon.com/en_US/help/topic/G201953020 ("Create a Paperback Cover").
_THICKNESS_IN = {"white": 0.002252, "cream": 0.0025}
BLEED_IN = 0.125
SPINE_TEXT_MIN_PAGES = 79
SPINE_TEXT_MARGIN_IN = 0.0625
COVER_SAFE_IN = 0.125

# https://kdp.amazon.com/en_US/help/topic/G201857950 ("Paperback Submission
# Guidelines"): KDP prints the barcode for its own ISBN in this area.
BARCODE_IN = (2.0, 1.2)
BARCODE_MARGIN_IN = 0.25


def _check_pages(pages: int) -> None:
    if not MIN_PAGES <= pages <= MAX_PAGES:
        raise ValueError(
            f"{pages} pages is outside KDP's paperback range, "
            f"{MIN_PAGES} to {MAX_PAGES}"
        )


def gutter_minimum(pages: int) -> float:
    """KDP's minimum inside margin for a book of ``pages`` pages.

    Raises:
        ValueError: ``pages`` is outside KDP's range.
    """
    _check_pages(pages)
    return next(inches for top, inches in _GUTTER_BANDS if pages <= top)


def spine_width(pages: int, paper: Paper) -> float:
    """The spine width KDP's formula gives for ``pages`` pages on ``paper``.

    Raises:
        ValueError: ``pages`` is outside KDP's range, or ``paper`` is not
            one KDP lists for black ink.
    """
    _check_pages(pages)
    if paper not in _THICKNESS_IN:
        raise ValueError(f"unknown paper {paper!r}; KDP lists {sorted(_THICKNESS_IN)}")
    return pages * _THICKNESS_IN[paper]


def spine_text_allowed(pages: int) -> bool:
    """Whether KDP allows text on the spine of a ``pages``-page book."""
    return pages >= SPINE_TEXT_MIN_PAGES


def cover_dimensions(
    trim: tuple[float, float], pages: int, paper: Paper
) -> tuple[float, float]:
    """The full wraparound cover's width and height, bleed included."""
    trim_w, trim_h = trim
    width = BLEED_IN + trim_w + spine_width(pages, paper) + trim_w + BLEED_IN
    return width, BLEED_IN + trim_h + BLEED_IN
