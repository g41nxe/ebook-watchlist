"""Das Bewertungstor (ADR 19, Ticket 12).

Kein Test hier ruft ein Modell. Der Bewerter ist ein Protokoll mit einer
Methode — genau damit ein Stub genügt.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from ebook_watchlist import gate
from ebook_watchlist.models import Delta, DeltaKind, MatchReason, Observation
from ebook_watchlist.rating import (
    Rating,
    RatingUnavailable,
    parse_answer,
    prompt_for,
    rubric_version,
)
from ebook_watchlist.store import Store

NOW = datetime(2026, 9, 4, 22, 0)
RUBRIC = "Maßstabsversion: 1\n\nHier stünde der Maßstab."


def discovery(**overrides) -> Observation:
    defaults = dict(
        source="beam",
        source_item_id="1",
        title="Ein Fund",
        match_reason=MatchReason.GENRE_CATEGORY,
        price_cents=399,
    )
    return Observation(**{**defaults, **overrides})


def first_seen(observation: Observation) -> Delta:
    return Delta(DeltaKind.FIRST_SEEN, observation, None)


class StubRater:
    def __init__(self, rating: Rating | Exception) -> None:
        self.rating = rating
        self.calls: list[Observation] = []

    def rate(self, observation: Observation) -> Rating:
        self.calls.append(observation)
        if isinstance(self.rating, Exception):
            raise self.rating
        return self.rating


def rating(stars: int) -> Rating:
    return Rating(stars=stars, reason="Achse D: isoliertes Setting", confidence="teils",
                  rubric_version=1)


# --- der Maßstab ------------------------------------------------------------


def test_the_rubric_states_its_version() -> None:
    assert rubric_version(RUBRIC) == 1


def test_a_rubric_without_a_version_is_refused() -> None:
    """Ohne Version stünden irgendwann Sterne aus drei Maßstäben nebeneinander."""
    with pytest.raises(RatingUnavailable, match="Maßstabsversion"):
        rubric_version("Kein Hinweis auf eine Version.")


# --- der Prompt -------------------------------------------------------------


def test_the_prompt_carries_only_public_facts() -> None:
    """Kein Watchlist-Inhalt, kein Besitz, keine Identität der Leserin (ADR 19)."""
    text = prompt_for(discovery(author="Max Barry", blurb="Ein Schiff, allein."), RUBRIC)

    assert "Max Barry" in text
    assert "Ein Schiff, allein." in text
    assert "Maßstabsversion" in text


def test_a_truncated_blurb_says_so() -> None:
    """Ein Modell, das nicht weiß, wie dünn seine Grundlage ist, urteilt zu sicher."""
    text = prompt_for(discovery(blurb="Sydney wollte nur Geld verdienen..."), RUBRIC)
    assert "abgeschnitten" in text


def test_a_whole_blurb_is_not_flagged() -> None:
    text = prompt_for(discovery(blurb="Ein vollständiger Satz."), RUBRIC)
    assert "abgeschnitten" not in text


# --- die Antwort ------------------------------------------------------------


def test_a_clean_answer_is_read() -> None:
    answer = '{"stars": 4, "confidence": "teils", "reason": "Achse A: Reihe"}'
    result = parse_answer(answer, version=1)

    assert (result.stars, result.confidence) == (4, "teils")
    assert result.rubric_version == 1


def test_json_wrapped_in_chatter_is_still_read() -> None:
    result = parse_answer('Gern:\n{"stars": 2, "confidence": "vermutet", "reason": "x"}\n', 1)
    assert result.stars == 2


@pytest.mark.parametrize(
    "answer",
    [
        "gar kein JSON",
        '{"stars": 7, "confidence": "teils", "reason": "x"}',
        '{"stars": 3, "confidence": "sicher", "reason": "x"}',
        '{"stars": 3, "confidence": "teils"}',
        '{"confidence": "teils", "reason": "x"}',
    ],
)
def test_an_unusable_answer_is_refused_rather_than_guessed(answer: str) -> None:
    with pytest.raises(RatingUnavailable):
        parse_answer(answer, version=1)


# --- das Tor ----------------------------------------------------------------


def test_a_good_fit_passes(store: Store) -> None:
    deltas = [first_seen(discovery(isbn="9783104911854"))]
    kept, report = gate.apply(
        deltas, store=store, rater=StubRater(rating(4)), rubric_version=1,
        threshold=3, now=NOW,
    )
    assert kept == deltas
    assert report.held_back == 0


def test_a_poor_fit_never_reaches_the_pile(store: Store) -> None:
    deltas = [first_seen(discovery(isbn="9783104911854"))]
    kept, report = gate.apply(
        deltas, store=store, rater=StubRater(rating(1)), rubric_version=1,
        threshold=3, now=NOW,
    )
    assert kept == []
    assert report.held_back == 1


def test_a_book_is_judged_once_not_every_run(store: Store) -> None:
    """Ein Lauf, der es wiedersieht, darf keinen Aufruf mehr kosten."""
    rater = StubRater(rating(4))
    deltas = [first_seen(discovery(isbn="9783104911854"))]

    gate.apply(deltas, store=store, rater=rater, rubric_version=1, threshold=3, now=NOW)
    _, second = gate.apply(
        deltas, store=store, rater=rater, rubric_version=1, threshold=3, now=NOW
    )

    assert len(rater.calls) == 1
    assert second.reused == 1


def test_a_new_rubric_invalidates_the_judgement(store: Store) -> None:
    """Die eine Änderung, bei der ein erneuter Aufruf richtig ist."""
    rater = StubRater(rating(4))
    deltas = [first_seen(discovery(isbn="9783104911854"))]

    gate.apply(deltas, store=store, rater=rater, rubric_version=1, threshold=3, now=NOW)
    gate.apply(deltas, store=store, rater=rater, rubric_version=2, threshold=3, now=NOW)

    assert len(rater.calls) == 2


def test_the_gate_never_fails_closed(store: Store) -> None:
    """Ohne Urteil wird gezeigt. Ein Tor, das im Zweifel schließt, verschluckt
    Neuzugänge stillschweigend — das eine Verhalten, das verboten ist."""
    deltas = [first_seen(discovery(isbn="9783104911854"))]
    kept, report = gate.apply(
        deltas,
        store=store,
        rater=StubRater(RatingUnavailable("kein Netz")),
        rubric_version=1,
        threshold=3,
        now=NOW,
    )
    assert kept == deltas
    assert report.unrated == 1


def test_without_a_rater_nothing_is_held_back(store: Store) -> None:
    deltas = [first_seen(discovery())]
    kept, report = gate.apply(
        deltas, store=store, rater=None, rubric_version=1, threshold=3, now=NOW
    )
    assert kept == deltas
    assert report.held_back == 0


def test_a_watchlist_title_is_never_judged(store: Store) -> None:
    """Die Leserin hat es selbst gewählt — es gegen ihr eigenes Profil
    abzulehnen wäre anmaßend."""
    rater = StubRater(rating(0))
    deltas = [first_seen(discovery(match_reason=MatchReason.WATCHLIST))]

    kept, _ = gate.apply(
        deltas, store=store, rater=rater, rubric_version=1, threshold=3, now=NOW
    )

    assert kept == deltas
    assert rater.calls == []


def test_a_price_drop_is_not_judged_again(store: Store) -> None:
    """Es betrifft ein Buch, das schon einmal durchgelassen wurde."""
    rater = StubRater(rating(0))
    drop = Delta(DeltaKind.PRICE_DROP, discovery(price_cents=299), discovery(price_cents=999))

    kept, _ = gate.apply(
        [drop], store=store, rater=rater, rubric_version=1, threshold=3, now=NOW
    )

    assert kept == [drop]
    assert rater.calls == []


def test_the_judgement_follows_the_isbn_across_sources(store: Store) -> None:
    """Dasselbe Buch bei zwei Shops kostet ein Urteil, nicht zwei."""
    rater = StubRater(rating(4))
    at_beam = first_seen(discovery(source="beam", source_item_id="1", isbn="9783104911854"))
    at_voebb = first_seen(
        discovery(source="voebb", source_item_id="9", isbn="9783104911854",
                  match_reason=MatchReason.PROFILE_AUTHOR)
    )

    gate.apply([at_beam], store=store, rater=rater, rubric_version=1, threshold=3, now=NOW)
    gate.apply([at_voebb], store=store, rater=rater, rubric_version=1, threshold=3, now=NOW)

    assert len(rater.calls) == 1


def test_without_an_isbn_the_find_itself_is_the_subject(store: Store) -> None:
    """Bündel und Einzelfolgen haben keine — ein Urteil je Quelle ist ehrlicher
    als eines, das über den Titel geraten wäre."""
    assert gate.subject_of(discovery(isbn=None)) == "item:beam:1"
    assert gate.subject_of(discovery(isbn="9783104911854")) == "isbn:9783104911854"
