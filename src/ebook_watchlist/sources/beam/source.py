"""The beam-shop Shop Source.

Shopware's search is deliberately fuzzy — a query for "Redshirts" happily
returns an Amazon Redshift cookbook — so ranking is never trusted and every
tile is re-matched before anything is pinned.
"""

from __future__ import annotations

from urllib.parse import urljoin

from ...config import WatchlistEntry
from ...http import HttpClient, NotFound
from ...matching import Candidate, Query, Resolution, match
from ...models import MatchReason, Observation
from ..base import ShopSource, SourceStructureError
from . import parse
from . import selectors as sel

SOURCE_NAME = "beam"


class BeamSource(ShopSource):
    name = SOURCE_NAME

    def __init__(
        self, client: HttpClient, name: str = SOURCE_NAME, base: str = sel.BASE
    ) -> None:
        self.client = client
        self.name = name
        self.base = base

    # --- fetching ----------------------------------------------------------

    def search(
        self, query: str, page_size: int = sel.SEARCH_PAGE_SIZE, page: int | None = None
    ) -> list[parse.Tile]:
        """Search results as tiles. Short queries are refused before the request:
        Shopware silently returns nothing for fewer than four characters."""
        if len(query.strip()) < sel.MIN_QUERY_LENGTH:
            return []
        params = {"sSearch": query, "n": str(min(page_size, sel.MAX_PAGE_SIZE))}
        if page is not None:
            params["p"] = str(page)
        return parse.parse_tiles(
            self.client.get(urljoin(self.base, sel.SEARCH_PATH), params=params), self.base
        )

    # --- resolution --------------------------------------------------------

    def resolve(self, entry: WatchlistEntry) -> Resolution | None:
        query = " ".join(part for part in (entry.title, entry.author) if part)
        tiles = self.search(query)
        if not tiles:
            return None

        resolution = match(
            Query(title=entry.title, author=entry.author),
            [
                Candidate(title=tile.title, author=tile.author, payload=tile.url)
                for tile in tiles
            ],
        )
        return resolution

    # --- observation -------------------------------------------------------

    def check(self, entry: WatchlistEntry) -> Observation | None:
        link = entry.resolved_links.get(self.name)
        if not link:
            return None

        url = parse.canonical_url(link, self.base)
        try:
            detail = parse.parse_detail(self.client.get(url))
        except NotFound:
            # Delisted. One title going away must not blind the rest.
            return None

        return Observation(
            source=self.name,
            source_item_id=_product_id_from_url(url),
            title=detail.title or entry.title,
            author=entry.author,
            match_reason=MatchReason.WATCHLIST,
            watchlist_key=entry.key,
            price_cents=detail.price_cents,
            # Fixed-book-price law: this shop never renders a struck price, so
            # the Deal tier can only ever fire on an observed drop (ADR 5).
            original_price_cents=None,
            url=url,
        )

    def probe(self) -> None:
        tiles = self.search(sel.PROBE_QUERY)
        if not tiles:
            raise SourceStructureError(
                f"beam-shop: the probe query {sel.PROBE_QUERY!r} returned no parseable tiles"
            )
        if all(tile.price_cents is None for tile in tiles):
            raise SourceStructureError("beam-shop: no tile carried a parseable price")


def _product_id_from_url(url: str) -> str:
    """``…/606983/krieg-der-klone`` → ``606983``. The Snapshot is keyed on it."""
    parts = [part for part in url.split("?")[0].split("/") if part]
    for part in reversed(parts):
        if part.isdigit():
            return part
    raise SourceStructureError(f"beam-shop: no product id in {url!r}")
