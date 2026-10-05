"""KDP's paperback numbers, against the values KDP publishes.

Sources: https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6 (margins)
and https://kdp.amazon.com/en_US/help/topic/G201953020 (cover and spine).
"""

import kdp_print as kp
import pytest


@pytest.mark.parametrize(
    ("pages", "inches"),
    [(24, 0.375), (150, 0.375), (151, 0.5), (300, 0.5), (301, 0.625),
     (500, 0.625), (501, 0.75), (700, 0.75), (701, 0.875), (828, 0.875)],
)  # fmt: skip
def test_gutter_minimum_follows_kdps_bands(pages, inches):
    assert kp.gutter_minimum(pages) == inches


@pytest.mark.parametrize("pages", [0, 23, 829])
def test_a_page_count_outside_kdps_range_raises(pages):
    with pytest.raises(ValueError, match=str(pages)):
        kp.gutter_minimum(pages)
    with pytest.raises(ValueError, match=str(pages)):
        kp.spine_width(pages, "cream")


def test_spine_width_is_pages_times_the_papers_thickness():
    assert kp.spine_width(100, "cream") == pytest.approx(0.25)
    assert kp.spine_width(100, "white") == pytest.approx(0.2252)
    assert kp.spine_width(120, "cream") == pytest.approx(0.3)


def test_an_unknown_paper_raises():
    with pytest.raises(ValueError, match="glossy"):
        kp.spine_width(100, "glossy")


def test_spine_text_needs_more_than_79_pages():
    assert not kp.spine_text_allowed(79)
    assert kp.spine_text_allowed(80)


def test_cream_paper_stops_at_776_pages_and_white_at_828():
    assert kp.spine_width(776, "cream") == pytest.approx(1.94)
    with pytest.raises(ValueError, match="777"):
        kp.spine_width(777, "cream")
    assert kp.spine_width(828, "white") == pytest.approx(828 * 0.002252)


def test_cover_dimensions_add_bleed_on_the_outside_edges_and_the_spine_between():
    width, height = kp.cover_dimensions((5.0, 8.0), 120, "cream")
    assert width == pytest.approx(0.125 + 5.0 + 0.3 + 5.0 + 0.125)
    assert height == pytest.approx(0.125 + 8.0 + 0.125)
