from pathlib import Path

import book_publication as bp
import pytest

FIELDS = ("copyright_holder", "copyright_year", "isbn", "cover_art", "back_cover_text")


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "publication.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_an_empty_file_leaves_every_detail_unresolved(tmp_path):
    details = bp.load_details(_write(tmp_path, ""))
    assert bp.unresolved(details) == list(FIELDS)


def test_the_committed_file_parses_and_names_every_field():
    path = Path(__file__).resolve().parents[2] / "docs" / "book" / "publication.toml"
    bp.load_details(path)
    text = path.read_text()
    for field in FIELDS:
        assert f"# {field} = " in text or f"{field} = " in text, field


def test_a_set_detail_is_resolved(tmp_path):
    details = bp.load_details(_write(tmp_path, 'copyright_holder = "A B"\n'))
    assert details.copyright_holder == "A B"
    assert "copyright_holder" not in bp.unresolved(details)


def test_an_unknown_key_is_refused(tmp_path):
    with pytest.raises(SystemExit, match="copyright_holdr"):
        bp.load_details(_write(tmp_path, 'copyright_holdr = "x"\n'))


def test_an_empty_string_counts_as_unset(tmp_path):
    details = bp.load_details(_write(tmp_path, 'isbn = ""\n'))
    assert "isbn" in bp.unresolved(details)


@pytest.mark.parametrize("isbn", ["978-0-306-40615-7", "9780306406157"])
def test_a_valid_isbn13_loads(tmp_path, isbn):
    assert bp.load_details(_write(tmp_path, f'isbn = "{isbn}"\n')).isbn == isbn


@pytest.mark.parametrize(
    "isbn",
    # The last is a TOML escape: the value ends in a newline.
    [
        "978-0-306-40615-8",
        "97803064061",
        "978030640615X",
        "978 0306406157",
        "9780306406157\\n",
    ],
)
def test_an_invalid_isbn_is_refused_at_load(tmp_path, isbn):
    with pytest.raises(SystemExit, match="ISBN"):
        bp.load_details(_write(tmp_path, f'isbn = "{isbn}"\n'))


def test_require_resolved_names_every_unset_field_at_once(tmp_path):
    details = bp.load_details(_write(tmp_path, 'isbn = "9780306406157"\n'))
    with pytest.raises(SystemExit) as exc:
        bp.require_resolved(details)
    message = str(exc.value)
    for field in FIELDS:
        assert (field in message) == (field != "isbn"), field


def test_typst_inputs_print_a_placeholder_for_each_unset_field(tmp_path):
    details = bp.load_details(_write(tmp_path, 'copyright_holder = "A*B #1"\n'))
    inputs = bp.typst_inputs(details)
    assert inputs["copyright-holder"] == "A*B #1"
    assert inputs["isbn"] == bp.PLACEHOLDERS["isbn"]
    assert inputs["isbn-set"] == "false"
    assert all(p.startswith("[") and p.endswith("]") for p in bp.PLACEHOLDERS.values())
