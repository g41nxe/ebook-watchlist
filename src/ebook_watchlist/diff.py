"""Turning Observations into Deltas.

The comparison is always *latest stored Observation* vs *what we just saw*, never
"since yesterday" — that is what makes a Run stateless with respect to its
schedule (ADR 4). A first sighting has nothing to compare against and is not a
Delta.
"""

from __future__ import annotations

from collections.abc import Container, Iterable, Mapping, Sequence

from .models import Availability, Delta, DeltaKind, MatchReason, Observation

#: Kinds worth waking the reader for. Everything else is recorded but silent
#: (ADR 9 §6b: a title going *away* is not news).
NOTIFIABLE: frozenset[DeltaKind] = frozenset(
    {DeltaKind.FIRST_SEEN, DeltaKind.BECAME_AVAILABLE, DeltaKind.PRICE_DROP}
)

#: Match reasons for which turning up at all is the news. A Watchlist Entry is
#: not one of them: its first sighting only establishes the baseline the next
#: Run will diff against.
DISCOVERY_REASONS: frozenset[MatchReason] = frozenset(
    {MatchReason.PROFILE_AUTHOR, MatchReason.GENRE_CATEGORY}
)


def compare(current: Observation, previous: Observation | None) -> list[Delta]:
    """Every change between two Observations of the same item, notifiable or not."""
    if previous is None:
        if current.match_reason in DISCOVERY_REASONS:
            return [Delta(DeltaKind.FIRST_SEEN, current, None)]
        return []

    deltas: list[Delta] = []

    if current.availability is not None and previous.availability is not None:
        if current.availability != previous.availability:
            if current.availability is Availability.AVAILABLE:
                deltas.append(Delta(DeltaKind.BECAME_AVAILABLE, current, previous))
            elif previous.availability is Availability.AVAILABLE:
                deltas.append(Delta(DeltaKind.BECAME_UNAVAILABLE, current, previous))

    if current.price_cents is not None and previous.price_cents is not None:
        if current.price_cents < previous.price_cents:
            deltas.append(Delta(DeltaKind.PRICE_DROP, current, previous))
        elif current.price_cents > previous.price_cents:
            deltas.append(Delta(DeltaKind.PRICE_RISE, current, previous))

    return deltas


def compute_deltas(
    observations: Sequence[Observation],
    previous: Mapping[tuple[str, str], Observation],
) -> list[Delta]:
    """The notifiable Deltas for one Run's worth of Observations."""
    return [
        delta
        for observation in observations
        for delta in compare(observation, previous.get(observation.key))
        if delta.kind in NOTIFIABLE
    ]


def keys_of(observations: Iterable[Observation]) -> list[tuple[str, str]]:
    return [observation.key for observation in observations]


def discovery_scope(observation: Observation) -> tuple[str, str, str]:
    """What a discovery belongs to: a Source, a kind of discovery, and a shelf."""
    return (observation.source, str(observation.match_reason), observation.category or "")


def suppress_unseeded(
    deltas: Sequence[Delta], known_scopes: Container[tuple[str, str, str]]
) -> list[Delta]:
    """Drop first sightings from a shelf we have never looked at before.

    The first time a category is followed, its entire front page is technically
    new — a hundred entries, none of them news. Seeding a scope silently means
    the next Run reports what genuinely arrived since.
    """
    return [
        delta
        for delta in deltas
        if delta.kind is not DeltaKind.FIRST_SEEN
        or discovery_scope(delta.current) in known_scopes
    ]
