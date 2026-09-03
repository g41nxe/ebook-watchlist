"""The VÖBB Library Source.

v1 is entirely login-free: copy counts and queue lengths are public. Personal
holds need an authenticated scrape and are deferred to v2 (ADR 6).
"""

from __future__ import annotations

from urllib.parse import urljoin

from ...config import WatchlistEntry
from ...http import HttpClient, NotFound
from ...models import MatchReason, Observation
from ..base import LibrarySource, SourceStructureError
from . import parse
from . import selectors as sel

SOURCE_NAME = "voebb"


def title_id_from_url(url: str) -> str | None:
    """The stable id inside ``mediaInfo,0-0-<ID>-200-…`` — our ``source_item_id``."""
    tail = url.rsplit("/", 1)[-1]
    if not tail.startswith("mediaInfo,"):
        return None
    parts = tail.split(",", 1)[1].split("-")
    return parts[2] if len(parts) > 2 and parts[2].isdigit() else None


def require_title_id(url: str) -> str:
    """The Snapshot is keyed on this, so a URL we cannot key must not slip through
    under a made-up identity — that would silently split one title's history."""
    title_id = title_id_from_url(url)
    if title_id is None:
        raise SourceStructureError(
            f"VÖBB: cannot read a title id out of {url!r} — expected a mediaInfo path"
        )
    return title_id


class VoebbSource(LibrarySource):
    name = SOURCE_NAME

    def __init__(
        self, client: HttpClient, name: str = SOURCE_NAME, base: str = sel.BASE
    ) -> None:
        self.client = client
        self.name = name
        self.base = base

    def check(self, entry: WatchlistEntry) -> Observation | None:
        """Availability for an entry whose detail page is already pinned.

        An unpinned entry is skipped here; resolving title+author to a detail
        page is ticket 04's job (ADR 9).
        """
        link = entry.resolved_links.get(self.name)
        if not link:
            return None

        url = urljoin(self.base, link)
        try:
            html = self.client.get(url)
        except NotFound:
            # The title left the catalogue. That is news about one entry, not a
            # broken Source — the other entries must still be checked.
            return None
        detail = parse.parse_detail(html)

        return Observation(
            source=self.name,
            source_item_id=require_title_id(url),
            # The *scraped* title, not the watchlist one — a wrong auto-resolve
            # has to be visible in the Digest (ADR 9).
            title=detail.title or entry.title,
            author=detail.author or entry.author,
            match_reason=MatchReason.WATCHLIST,
            watchlist_key=entry.key,
            availability=detail.availability,
            reservation_count=detail.reservations,
            available_from=detail.available_from,
            url=url,
        )

    def probe(self) -> None:
        """Known-good page must still parse. Values are free to change."""
        parse.parse_detail(self.client.get(urljoin(self.base, sel.PROBE_DETAIL_PATH)))
