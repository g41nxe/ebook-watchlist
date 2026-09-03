"""The Source contract (ADR 7).

A Source raises only when the *site* changed shape — a selector that no longer
matches, an unparseable page. A title that simply is not there returns ``None``
and is not an error. Whatever a Source raises fails that Source alone; the Run
finishes the others and reports the failure in the Digest.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from ..config import Profile, WatchlistEntry
from ..models import Observation


class SourceStructureError(Exception):
    """The page no longer looks the way the parser expects. Loud on purpose."""


class Source(ABC):
    """Anything a Run can poll."""

    #: Stable identifier used as ``observation.source`` — never change it for a
    #: live Source, the Snapshot is keyed on it.
    name: str

    @abstractmethod
    def collect(
        self, profile: Profile, watchlist: Sequence[WatchlistEntry]
    ) -> list[Observation]:
        """Everything this Source has to say this Run."""

    def probe(self) -> None:
        """Known-good self-check for ``ebw doctor`` (ticket 08). Raises on failure."""
        return None


class LibrarySource(Source):
    """Reports whether a title can be borrowed right now."""

    @abstractmethod
    def check(self, entry: WatchlistEntry) -> Observation | None: ...

    def collect(
        self, profile: Profile, watchlist: Sequence[WatchlistEntry]
    ) -> list[Observation]:
        observations = []
        for entry in watchlist:
            if not (entry.active and entry.check_library):
                continue
            observation = self.check(entry)
            if observation is not None:
                observations.append(observation)
        return observations


class ShopSource(Source):
    """Reports price and catalogue presence."""

    @abstractmethod
    def check(self, entry: WatchlistEntry) -> Observation | None: ...

    def by_author(self, author: str) -> list[Observation]:
        """Titles by a Reference Author. Implemented in ticket 06."""
        return []

    def collect(
        self, profile: Profile, watchlist: Sequence[WatchlistEntry]
    ) -> list[Observation]:
        observations = []
        for entry in watchlist:
            if not (entry.active and entry.check_shop):
                continue
            observation = self.check(entry)
            if observation is not None:
                observations.append(observation)
        for author in profile.reference_authors:
            observations.extend(self.by_author(author))
        return observations
