"""Die Aufräumarbeit an dem, was die Quellen liefern (Ticket 16).

Jeder Fall unten stammt aus einem echten Lauf vom 2026-09-04.
"""

from __future__ import annotations

import pytest

from ebook_watchlist.cleaning import (
    author_key,
    clean_blurb,
    group_spellings,
    is_truncated,
    preferred_spelling,
)

# --- Klappentexte ----------------------------------------------------------


def test_the_shops_icon_ligature_never_reaches_the_reader() -> None:
    """Alle 316 Klappentexte eines Laufs endeten so."""
    raw = (
        "Mein Name ist Lea. Ich habe einen geheimnisvollen Beschützer. Doch seine "
        "Freundschaft ist tödlich... Mehr navigate_next"
    )
    cleaned = clean_blurb(raw)
    assert cleaned is not None
    assert "navigate_next" not in cleaned
    assert "Mehr" not in cleaned.split(".")[-1]
    assert cleaned.endswith("tödlich...")


def test_the_ellipsis_survives_because_the_text_really_is_cut_off() -> None:
    """Ein Torso darf nicht wie ein ganzer Klappentext aussehen."""
    cleaned = clean_blurb("Sydney wollte nur etwas Geld verdienen... Mehr navigate_next")
    assert cleaned == "Sydney wollte nur etwas Geld verdienen..."
    assert is_truncated(cleaned)


def test_a_ligature_in_the_middle_is_removed_too() -> None:
    assert clean_blurb("Erst dies navigate_next dann das") == "Erst dies dann das"


@pytest.mark.parametrize("blurb", [None, "", "   "])
def test_nothing_in_nothing_out(blurb: str | None) -> None:
    assert clean_blurb(blurb) is None


def test_a_clean_blurb_is_left_alone() -> None:
    text = "Ein Massaker auf Föhr und Sylt, wie auch mehrfache Grabschändungen."
    assert clean_blurb(text) == text
    assert not is_truncated(text)


# --- Schreibweisen ---------------------------------------------------------


def test_three_spellings_are_one_person() -> None:
    """So stand er im Snapshot: 33-mal, 15-mal und einmal."""
    assert author_key("Jo Nesbø") == author_key("Jo Nesbo") == author_key("Nesbø, Jo")


def test_the_spelling_with_the_diacritic_wins() -> None:
    assert preferred_spelling(["Jo Nesbo", "Jo Nesbø", "Nesbø, Jo"]) == "Jo Nesbø"


def test_given_name_first_beats_sort_order() -> None:
    assert preferred_spelling(["Dusse, Karsten", "Karsten Dusse"]) == "Karsten Dusse"
    assert preferred_spelling(["Scalzi, John", "John Scalzi"]) == "John Scalzi"


def test_frequency_does_not_decide() -> None:
    """Eine falsche Schreibweise wird nicht richtig, weil ein Shop sie
    häufiger verwendet — hier stünde 'Jo Nesbo' 15-mal gegen einmal."""
    assert preferred_spelling(["Jo Nesbo"] * 15 + ["Jo Nesbø"]) == "Jo Nesbø"


def test_the_choice_is_stable() -> None:
    names = ["Anna Meier", "Anna Meier"]
    assert preferred_spelling(names) == preferred_spelling(list(reversed(names)))


def test_grouping_maps_every_spelling_to_the_best_one() -> None:
    resolved = group_spellings(["Jo Nesbo", "Nesbø, Jo", "Jo Nesbø", "Simon Beckett"])
    assert resolved["Jo Nesbo"] == "Jo Nesbø"
    assert resolved["Nesbø, Jo"] == "Jo Nesbø"
    assert resolved["Simon Beckett"] == "Simon Beckett"


def test_two_different_people_stay_apart() -> None:
    resolved = group_spellings(["Chris Carter", "Karsten Dusse"])
    assert set(resolved.values()) == {"Chris Carter", "Karsten Dusse"}


def test_nothing_to_group() -> None:
    assert group_spellings([]) == {}
    assert preferred_spelling([]) is None
