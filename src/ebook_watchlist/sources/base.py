"""The Source contract (ADR 7).

A Source raises only when the *site* changed shape — a selector that no longer
matches, an unparseable page. A title that simply is not there returns ``None``
and is not an error. Whatever a Source raises fails that Source alone; the Run
finishes the others and reports the failure in the Digest.
"""

from __future__ import annotations

import dataclasses
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..config import Profile, WatchlistEntry
from ..matching import Confidence, Resolution
from ..models import Attention, Observation
from ..store import Store

#: How long a failed resolution is trusted before the Source tries again. Long
#: enough not to hammer a search endpoint, short enough that a title the library
#: acquires later is eventually found.
RESOLUTION_RETRY_AFTER = timedelta(days=7)


class SourceStructureError(Exception):
    """The page no longer looks the way the parser expects. Loud on purpose."""


@dataclass(slots=True)
class RunContext:
    """What a Source may reach for beyond its own configuration.

    Deliberately narrow: resolutions it has made before, and a place to report
    entries it could not place. Sources never touch the Snapshot directly.
    """

    profile_slug: str
    store: Store
    now: datetime
    attention: list[Attention] = field(default_factory=list)
    #: Suggestions waved away for good, per Source name.
    dismissed: Mapping[str, frozenset[str]] = field(default_factory=dict)
    #: Whether this Run also walks the weekly long tail of Reference Authors.
    sweep_extended: bool = False

    def is_dismissed(self, source: str, source_item_id: str) -> bool:
        return source_item_id in self.dismissed.get(source, frozenset())

    def remembered_link(self, source: str, entry: WatchlistEntry) -> tuple[str | None, bool]:
        """``(url, still_valid)`` for a previous resolution of this entry.

        ``still_valid`` is False when there is nothing remembered, or when a
        failed attempt has aged out and deserves another try.
        """
        row = self.store.get_resolution(self.profile_slug, source, entry.key)
        if row is None:
            return None, False
        if row.url:
            return row.url, True
        return None, self.now - row.resolved_at < RESOLUTION_RETRY_AFTER

    def remember(self, source: str, entry: WatchlistEntry, resolution: Resolution) -> None:
        best = resolution.best
        accepted = resolution.accepted
        self._store_resolution(
            source,
            entry,
            url=str(accepted.payload) if accepted else None,
            confidence=str(resolution.confidence),
            reason=resolution.reason,
            matched_title=best.candidate.title if best else None,
            matched_author=best.candidate.author if best else None,
        )

    def remember_absence(self, source: str, entry: WatchlistEntry, reason: str) -> None:
        """The catalogue simply does not have it — worth not asking again soon."""
        self._store_resolution(
            source,
            entry,
            url=None,
            confidence=str(Confidence.NO_MATCH),
            reason=reason,
            matched_title=None,
            matched_author=None,
        )

    def _store_resolution(
        self,
        source: str,
        entry: WatchlistEntry,
        *,
        url: str | None,
        confidence: str,
        reason: str,
        matched_title: str | None,
        matched_author: str | None,
    ) -> None:
        self.store.put_resolution(
            self.profile_slug,
            source,
            entry.key,
            url=url,
            confidence=confidence,
            reason=reason,
            matched_title=matched_title,
            matched_author=matched_author,
            resolved_at=self.now,
        )

    def needs_attention(
        self, source: str, entry: WatchlistEntry, resolution: Resolution
    ) -> None:
        best = resolution.best
        self.attention.append(
            Attention(
                source=source,
                entry_title=entry.title,
                entry_author=entry.author,
                reason=resolution.reason,
                best_guess=best.candidate.title if best else None,
                best_guess_url=best.candidate.payload if best else None,
            )
        )


class Source(ABC):
    """Anything a Run can poll."""

    #: Stable identifier used as ``observation.source`` — never change it for a
    #: live Source, the Snapshot is keyed on it.
    name: str

    @abstractmethod
    def collect(
        self, profile: Profile, watchlist: Sequence[WatchlistEntry], context: RunContext
    ) -> list[Observation]:
        """Everything this Source has to say this Run."""

    def probe(self) -> None:
        """Known-good self-check for ``ebw doctor`` (ticket 08). Raises on failure."""
        return None


class ResolvingSource(Source):
    """A Source that can find a title's own page from just title and author.

    The resolution itself is site-specific; the caching, the retry window and
    the "needs attention" reporting are the same everywhere and live here.
    """

    def resolve(self, entry: WatchlistEntry) -> Resolution | None:
        """Search for ``entry``. ``None`` means a genuine "not in this catalogue"."""
        return None

    def linked_entry(
        self, entry: WatchlistEntry, context: RunContext
    ) -> WatchlistEntry | None:
        """``entry`` with this Source's link filled in, or ``None`` to skip it."""
        if entry.resolved_links.get(self.name):
            return entry  # a hand-pinned link always wins

        remembered, still_valid = context.remembered_link(self.name, entry)
        if remembered:
            return dataclasses.replace(
                entry, resolved_links={**entry.resolved_links, self.name: remembered}
            )
        if still_valid:
            return None  # we looked recently and came up empty; don't ask again

        resolution = self.resolve(entry)
        if resolution is None:
            # Not in the catalogue at all. Remember that, quietly.
            context.remember_absence(self.name, entry, "not in this catalogue")
            return None

        context.remember(self.name, entry, resolution)
        accepted = resolution.accepted
        if accepted is None:
            context.needs_attention(self.name, entry, resolution)
            return None

        return dataclasses.replace(
            entry, resolved_links={**entry.resolved_links, self.name: str(accepted.payload)}
        )


class LibrarySource(ResolvingSource):
    """Reports whether a title can be borrowed right now."""

    @abstractmethod
    def check(self, entry: WatchlistEntry) -> Observation | None: ...

    def collect(
        self, profile: Profile, watchlist: Sequence[WatchlistEntry], context: RunContext
    ) -> list[Observation]:
        observations = []
        for entry in watchlist:
            if not (entry.active and entry.check_library):
                continue
            linked = self.linked_entry(entry, context)
            if linked is None:
                continue
            observation = self.check(linked)
            if observation is not None:
                observations.append(observation)
        return observations


class ShopSource(ResolvingSource):
    """Reports price and catalogue presence."""

    @abstractmethod
    def check(self, entry: WatchlistEntry) -> Observation | None: ...

    def by_author(self, author: str) -> list[Observation]:
        """Everything this shop stocks by one Reference Author."""
        return []

    def by_category(self, category_path: str) -> list[Observation]:
        """The newest arrivals on one of the shop's own shelves."""
        return []

    def collect(
        self, profile: Profile, watchlist: Sequence[WatchlistEntry], context: RunContext
    ) -> list[Observation]:
        observations = []
        for entry in watchlist:
            if not (entry.active and entry.check_shop):
                continue
            linked = self.linked_entry(entry, context)
            if linked is None:
                continue
            observation = self.check(linked)
            if observation is not None:
                observations.append(observation)

        # Discoveries must not collide with what the Watchlist already covers:
        # two Observations of one item in a single Run would leave the diff with
        # no single "latest" to compare against next time.
        seen = {observation.source_item_id for observation in observations}

        def take(discovered: list[Observation]) -> None:
            for observation in discovered:
                item_id = observation.source_item_id
                if item_id in seen or context.is_dismissed(self.name, item_id):
                    continue
                seen.add(item_id)
                observations.append(observation)

        for author in profile.authors_to_sweep(context.sweep_extended):
            take(self.by_author(author))
        for category in profile.genre_categories:
            take(self.by_category(category))
        return observations
