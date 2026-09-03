"""The values that flow through a Run: Observations in, Deltas out."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Availability(StrEnum):
    """What a Library Source reports about a title. Shop Sources leave this unset."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class MatchReason(StrEnum):
    """Why an item is in the Snapshot at all (see CONTEXT.md)."""

    WATCHLIST = "watchlist"
    PROFILE_AUTHOR = "profile_author"
    GENRE_CATEGORY = "genre_category"


class DeltaKind(StrEnum):
    BECAME_AVAILABLE = "became_available"
    BECAME_UNAVAILABLE = "became_unavailable"
    PRICE_DROP = "price_drop"
    PRICE_RISE = "price_rise"


@dataclass(frozen=True, slots=True)
class Observation:
    """One recording of an item's state as seen by one Source during one Run."""

    source: str
    source_item_id: str
    title: str
    match_reason: MatchReason
    author: str | None = None
    watchlist_key: str | None = None
    price_cents: int | None = None
    original_price_cents: int | None = None
    availability: Availability | None = None
    reservation_count: int | None = None
    available_from: str | None = None
    category: str | None = None
    url: str | None = None
    observed_at: datetime | None = None

    @property
    def key(self) -> tuple[str, str]:
        """Identity across Runs — the pair a diff is computed over."""
        return (self.source, self.source_item_id)


@dataclass(frozen=True, slots=True)
class Delta:
    """A reportable change between the latest Observation and the previous one."""

    kind: DeltaKind
    current: Observation
    previous: Observation


@dataclass(frozen=True, slots=True)
class SourceFailure:
    """A Source that raised. Collected rather than fatal — other Sources still run."""

    source: str
    message: str


@dataclass(frozen=True, slots=True)
class Attention:
    """A Watchlist Entry a Source could not confidently place.

    Not an error — the site answered fine, we just will not guess. The entry is
    skipped for this Run and named in the Digest so it can be pinned by hand.
    """

    source: str
    entry_title: str
    entry_author: str | None
    reason: str
    best_guess: str | None = None
    best_guess_url: str | None = None
