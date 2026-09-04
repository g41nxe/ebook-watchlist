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
from ..models import Attention, LinkOutcome, Observation
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
    #: Watchlist-Key -> Buch-Id, damit ein Eintrag nicht pro Quelle neu
    #: gesucht wird.
    _books: dict[str, int] = field(default_factory=dict)

    def is_dismissed(self, source: str, source_item_id: str) -> bool:
        return source_item_id in self.dismissed.get(source, frozenset())

    def book_for(self, entry: WatchlistEntry) -> int:
        """Die Buch-Zeile zu diesem Watchlist-Eintrag, angelegt falls noetig.

        Der Eintrag kommt in diesem Schnitt noch aus der YAML und traegt keine
        ISBN; die Identitaet entsteht also ueber Titel und Autor:in und wird
        spaeter durch die ISBN geschaerft, sobald eine Beobachtung eine
        mitbringt (ADR 18).
        """
        cached = self._books.get(entry.key)
        if cached is not None:
            return cached
        row = self.store.find_or_create_book(
            isbn=None, title=entry.title, author=entry.author, now=self.now
        )
        self._books[entry.key] = row.id
        return row.id

    def remembered_link(self, source: str, entry: WatchlistEntry) -> tuple[str | None, bool]:
        """``(url, still_valid)`` for a previous resolution of this entry.

        ``still_valid`` is False when there is nothing remembered, or when a
        failed attempt has aged out and deserves another try.
        """
        row = self.store.get_book_source(self.book_for(entry), source)
        if row is None:
            return None, False
        if row.url:
            return row.url, True
        return None, self.now - row.resolved_at < RESOLUTION_RETRY_AFTER

    def remember(self, source: str, entry: WatchlistEntry, resolution: Resolution) -> None:
        best = resolution.best
        accepted = resolution.accepted
        if accepted is not None:
            outcome = LinkOutcome.LINKED
        elif resolution.confidence is Confidence.PROVISIONAL:
            outcome = LinkOutcome.UNSURE
        else:
            # Kandidaten gab es, aber keiner war es. Das ist eine Antwort, keine
            # Frage — und es gehoert nicht auf eine Liste, die um Mithilfe bittet.
            outcome = LinkOutcome.NOT_FOUND
        self.store.put_book_source(
            self.book_for(entry),
            source,
            outcome=str(outcome),
            url=str(accepted.payload) if accepted else None,
            resolved_at=self.now,
            reason=resolution.reason,
            # Titel und Autor:in *so, wie diese Quelle sie schreibt* — daran
            # bleibt eine falsche automatische Zuordnung sichtbar (ADR 9).
            matched_title=best.candidate.title if best else None,
            matched_author=best.candidate.author if best else None,
        )

    def remember_absence(self, source: str, entry: WatchlistEntry, reason: str) -> None:
        """The catalogue simply does not have it — worth not asking again soon."""
        self.store.put_book_source(
            self.book_for(entry),
            source,
            outcome=str(LinkOutcome.NOT_FOUND),
            url=None,
            resolved_at=self.now,
            reason=reason,
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
            # Nur ein *plausibler* Treffer ist eine Frage an einen Menschen.
            # "Nichts passt" auf dieselbe Liste zu setzen hat sie mit Zeilen
            # gefuellt, bei denen es nichts zu entscheiden gab (Ticket 04).
            if resolution.confidence is Confidence.PROVISIONAL:
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
                observations.append(
                    dataclasses.replace(observation, book_id=context.book_for(entry))
                )
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
                observations.append(
                    dataclasses.replace(observation, book_id=context.book_for(entry))
                )

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
