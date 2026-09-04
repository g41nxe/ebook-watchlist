from __future__ import annotations

import pytest

from ebook_watchlist.config import Profile
from ebook_watchlist.diff import compare, compute_deltas, suppress_unseeded
from ebook_watchlist.models import Availability, DeltaKind, MatchReason, Observation


def observation(**overrides) -> Observation:
    defaults = dict(
        source="fake",
        source_item_id="1",
        title="Ein Titel",
        match_reason=MatchReason.WATCHLIST,
    )
    return Observation(**{**defaults, **overrides})


def test_a_watchlist_titles_first_sighting_is_only_a_baseline() -> None:
    assert compare(observation(price_cents=999), None) == []


@pytest.mark.parametrize(
    "reason", [MatchReason.PROFILE_AUTHOR, MatchReason.GENRE_CATEGORY]
)
def test_a_discovery_turning_up_at_all_is_the_news(reason: MatchReason) -> None:
    deltas = compare(observation(price_cents=999, match_reason=reason), None)
    assert [d.kind for d in deltas] == [DeltaKind.FIRST_SEEN]
    assert deltas[0].previous is None


def test_a_discovery_is_only_news_once() -> None:
    before = observation(price_cents=999, match_reason=MatchReason.GENRE_CATEGORY)
    assert compare(before, before) == []


def test_unchanged_is_not_a_delta() -> None:
    before = observation(price_cents=999, availability=Availability.UNAVAILABLE)
    assert compare(before, before) == []


def test_becoming_available_is_a_delta() -> None:
    previous = observation(availability=Availability.UNAVAILABLE, reservation_count=3)
    current = observation(availability=Availability.AVAILABLE)
    assert [d.kind for d in compare(current, previous)] == [DeltaKind.BECAME_AVAILABLE]


def test_price_drop_and_rise_are_distinguished() -> None:
    previous = observation(price_cents=1299)
    assert [d.kind for d in compare(observation(price_cents=999), previous)] == [
        DeltaKind.PRICE_DROP
    ]
    assert [d.kind for d in compare(observation(price_cents=1499), previous)] == [
        DeltaKind.PRICE_RISE
    ]


def test_only_notifiable_kinds_reach_the_digest() -> None:
    """A price rise and a title going away are recorded, but they are not news."""
    previous = {
        ("fake", "1"): observation(price_cents=999),
        ("fake", "2"): observation(source_item_id="2", availability=Availability.AVAILABLE),
    }
    current = [
        observation(price_cents=1299),
        observation(source_item_id="2", availability=Availability.UNAVAILABLE),
    ]
    assert compute_deltas(current, previous) == []


def test_missing_field_on_one_side_is_not_a_delta() -> None:
    previous = observation(price_cents=None)
    assert compare(observation(price_cents=999), previous) == []


# --- a watchlist title that is already cheap ------------------------------

PROFILE = Profile(slug="t", name="T")  # Strong Deal unter 5,00 EUR


def test_an_already_cheap_watchlist_title_is_reported_on_sight() -> None:
    """Waiting for a 3,99 EUR title to get cheaper still would be a strange way
    to answer 'tell me when it is a bargain'."""
    deltas = compare(observation(price_cents=399), None, PROFILE)
    assert [d.kind for d in deltas] == [DeltaKind.FIRST_SEEN]


def test_a_normally_priced_watchlist_title_is_still_only_a_baseline() -> None:
    assert compare(observation(price_cents=1499), None, PROFILE) == []


def test_without_a_profile_nothing_changes_about_first_sightings() -> None:
    assert compare(observation(price_cents=399), None) == []


def test_the_cheap_title_is_reported_once_not_every_run() -> None:
    cheap = observation(price_cents=399)
    assert compare(cheap, cheap, PROFILE) == []


def test_a_title_with_no_price_is_not_a_bargain() -> None:
    assert compare(observation(price_cents=None), None, PROFILE) == []


def test_seeding_never_swallows_a_watchlist_bargain() -> None:
    """Discovery scopes are seeded quietly; a Watchlist Entry has no scope and
    must not be silenced by that mechanism."""
    deltas = compute_deltas([observation(price_cents=399)], {}, PROFILE)
    assert suppress_unseeded(deltas, known_scopes=set()) == deltas
