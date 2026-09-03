from __future__ import annotations

from ebook_watchlist.diff import compare, compute_deltas
from ebook_watchlist.models import Availability, DeltaKind, MatchReason, Observation


def observation(**overrides) -> Observation:
    defaults = dict(
        source="fake",
        source_item_id="1",
        title="Ein Titel",
        match_reason=MatchReason.WATCHLIST,
    )
    return Observation(**{**defaults, **overrides})


def test_first_sighting_is_not_a_delta() -> None:
    assert compare(observation(price_cents=999), None) == []


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
