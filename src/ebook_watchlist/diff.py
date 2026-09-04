"""Turning Observations into Deltas.

The comparison is always *latest stored Observation* vs *what we just saw*, never
"since yesterday" — that is what makes a Run stateless with respect to its
schedule (ADR 4). A first sighting has nothing to compare against and is not a
Delta.
"""

from __future__ import annotations

from collections.abc import Container, Iterable, Mapping, Sequence

from .config import Profile
from .deals import is_strong_deal
from .junk import is_junk
from .models import Availability, Delta, DeltaKind, MatchReason, Observation

#: Kinds worth waking the reader for. Everything else is recorded but silent
#: (ADR 9 §6b: a title going *away* is not news).
NOTIFIABLE: frozenset[DeltaKind] = frozenset(
    {DeltaKind.FIRST_SEEN, DeltaKind.BECAME_AVAILABLE, DeltaKind.PRICE_DROP}
)

#: The two channels the reader did not name a title for. Turning up is not
#: enough here — a discovery has to be a deal to be worth reporting (ADR 19),
#: whereas a Watchlist Entry is reported at any price.
DISCOVERY_REASONS: frozenset[MatchReason] = frozenset(
    {MatchReason.PROFILE_AUTHOR, MatchReason.GENRE_CATEGORY}
)


def worth_announcing(observation: Observation, profile: Profile | None) -> bool:
    """Whether this item may reach the reader at all (ADR 19).

    A Watchlist Entry always may: the reader named this book, and the price is
    not what makes it interesting. A discovery has to be a deal.

    The exception is deliberately temporary. Until the rating gate exists, the
    price is the *only* sieve there is, and it sieves for the wrong thing:
    applied to the shelves it left 106 titles of which nine were by one
    English-language self-publisher and three were "Ich bin Heinz, der Metzger",
    while a new Jo Nesbø at 11,99 € went silent. A Reference Author is someone
    the reader already chose, so that channel is trusted until something better
    can judge it. Once the gate is in, the threshold applies to both alike —
    relevance is the gate's question, urgency is the price's.
    """
    if observation.match_reason is MatchReason.WATCHLIST:
        return True
    if is_junk(observation):
        return False
    if observation.match_reason is MatchReason.PROFILE_AUTHOR:
        return True
    return profile is not None and is_strong_deal(observation.price_cents, profile)


def compare(
    current: Observation, previous: Observation | None, profile: Profile | None = None
) -> list[Delta]:
    """Every change between two Observations of the same item, notifiable or not."""
    if previous is None:
        # Nothing is lost by staying quiet: the Observation is stored either
        # way, so a book first seen at full price surfaces the day it drops.
        if worth_announcing(current, profile):
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
            # The same bar a first sighting has to clear. Without this the rule
            # was strict at the front door and open at the back: a shelf title
            # slipping from 11,99 € to 11,49 € would have been reported after
            # being kept quiet at 11,99 €.
            if worth_announcing(current, profile):
                deltas.append(Delta(DeltaKind.PRICE_DROP, current, previous))
        elif current.price_cents > previous.price_cents:
            deltas.append(Delta(DeltaKind.PRICE_RISE, current, previous))

    return deltas


def compute_deltas(
    observations: Sequence[Observation],
    previous: Mapping[tuple[str, str], Observation],
    profile: Profile | None = None,
) -> list[Delta]:
    """The notifiable Deltas for one Run's worth of Observations."""
    return [
        delta
        for observation in observations
        for delta in compare(observation, previous.get(observation.key), profile)
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
        or delta.current.match_reason not in DISCOVERY_REASONS
        or discovery_scope(delta.current) in known_scopes
    ]
