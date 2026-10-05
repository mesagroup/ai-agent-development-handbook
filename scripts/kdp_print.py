"""KDP's paperback numbers: margins, spine, cover size and barcode area.

Every value is copied from KDP's help pages, named beside it, so a change
on KDP's side is a change to one constant here. All lengths are inches.
"""

from __future__ import annotations

from typing import Literal

Paper = Literal["white", "cream"]

# https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6
# ("Set Trim Size, Bleed, and Margins"). The page range is the 5 x 8 in row
# for black ink, by paper; the gutter table runs to the longest of them.
MIN_PAGES = 24
MAX_PAGES = {"white": 828, "cream": 776}
# Inside (gutter) margin minimum by the highest page count it covers.
_GUTTER_BANDS = ((150, 0.375), (300, 0.5), (500, 0.625), (700, 0.75), (828, 0.875))
# The outside margin without bleed; the interior has none.
OUTSIDE_MARGIN_MIN_IN = 0.25

# https://kdp.amazon.com/en_US/help/topic/G201953020 ("Create a Paperback Cover").
_THICKNESS_IN = {"white": 0.002252, "cream": 0.0025}
BLEED_IN = 0.125
# "We only print spine text on books with more than 79 pages." The same page
# also says "at least 79"; the strict reading never prints text KDP refuses.
SPINE_TEXT_MIN_PAGES = 80
SPINE_TEXT_MARGIN_IN = 0.0625
COVER_SAFE_IN = 0.125

# https://kdp.amazon.com/en_US/help/topic/G5HDYGP4BXLX4RUW ("Barcodes"): the
# suggested size, at least this far from the spine and the trim, on white.
BARCODE_IN = (2.0, 1.2)
BARCODE_MARGIN_IN = 0.25


def _check_pages(pages: int, top: int) -> None:
    if not MIN_PAGES <= pages <= top:
        raise ValueError(
            f"{pages} pages is outside KDP's paperback range, {MIN_PAGES} to {top}"
        )


def gutter_minimum(pages: int) -> float:
    """KDP's minimum inside margin for a book of ``pages`` pages.

    Raises:
        ValueError: ``pages`` is outside KDP's range.
    """
    _check_pages(pages, _GUTTER_BANDS[-1][0])
    return next(inches for top, inches in _GUTTER_BANDS if pages <= top)


def spine_width(pages: int, paper: Paper) -> float:
    """The spine width KDP's formula gives for ``pages`` pages on ``paper``.

    Raises:
        ValueError: ``pages`` is outside KDP's range for ``paper``, or
            ``paper`` is not one KDP lists for black ink.
    """
    if paper not in _THICKNESS_IN:
        raise ValueError(f"unknown paper {paper!r}; KDP lists {sorted(_THICKNESS_IN)}")
    _check_pages(pages, MAX_PAGES[paper])
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
