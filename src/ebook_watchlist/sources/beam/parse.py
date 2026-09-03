"""Turning beam-shop listing HTML into values. Pure functions.

One parser serves search results, category listings and author hubs — Shopware
renders the same product tile on all three.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup, Tag

from ..base import SourceStructureError
from . import selectors as sel

#: de-DE money: "." groups thousands, "," is the decimal point.
_PRICE = re.compile(r"(\d{1,3}(?:\.\d{3})*|\d+),(\d{2})")
_TRAILING_ID = re.compile(r"/(\d+)/[^/]*$")

NO_RESULTS_MARKER = "keine Artikel gefunden"


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def parse_price(text: str) -> int | None:
    """``"9,99 €"`` → ``999``. Returns ``None`` when there is no price at all."""
    match = _PRICE.search(text.replace("\xa0", " "))
    if match is None:
        return None
    return int(match.group(1).replace(".", "")) * 100 + int(match.group(2))


def canonical_url(href: str, base: str = sel.BASE) -> str:
    """Product links carry a ``?c=<category>`` context param; the path is the identity."""
    parts = urlsplit(urljoin(base, href))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


@dataclass(frozen=True, slots=True)
class Tile:
    """One product as it appears in any listing."""

    product_id: str
    order_number: str
    title: str
    author: str | None
    price_cents: int | None
    url: str
    subtitle: str | None = None
    category_id: str | None = None
    badges: frozenset[str] = frozenset()

    @property
    def is_preorder(self) -> bool:
        return sel.BADGE_PREORDER in self.badges

    @property
    def is_new(self) -> bool:
        return sel.BADGE_NEW in self.badges


def _title_of(link: Tag) -> tuple[str, str | None]:
    """The clean title plus its subtitle.

    The link's text runs the two together — ``"Krieg der Klone Die Trilogie"`` —
    so the ``title`` attribute, which holds the title alone, is the better source.
    """
    subtitle_node = link.select_one(sel.TILE_SUBTITLE)
    subtitle = subtitle_node.get_text(" ", strip=True) if subtitle_node else None

    attr = link.get("title")
    if isinstance(attr, str) and attr.strip():
        return attr.strip(), subtitle

    if subtitle_node is not None:
        subtitle_node.extract()
    return link.get_text(" ", strip=True), subtitle


def _product_id(tile: Tag, url: str) -> str | None:
    note = tile.select_one(sel.TILE_NOTE_BUTTON)
    if note is not None:
        value = note.get(sel.ATTR_PRODUCT_ID)
        if isinstance(value, str) and value.strip():
            return value.strip()
    match = _TRAILING_ID.search(urlsplit(url).path)
    return match.group(1) if match else None


def _parse_tile(tile: Tag, base: str) -> Tile | None:
    link = tile.select_one(sel.TILE_TITLE)
    order_number = tile.get(sel.ATTR_ORDER_NUMBER)
    if link is None or not isinstance(order_number, str):
        return None

    href = link.get("href")
    if not isinstance(href, str) or not href:
        return None
    url = canonical_url(href, base)

    product_id = _product_id(tile, url)
    if product_id is None:
        return None

    title, subtitle = _title_of(link)
    if not title:
        return None

    author_node = tile.select_one(sel.TILE_AUTHOR)
    author = None
    if author_node is not None:
        author = author_node.get_text(" ", strip=True)
        if author.startswith(sel.AUTHOR_PREFIX):
            author = author[len(sel.AUTHOR_PREFIX) :]
        author = author or None

    price_node = tile.select_one(sel.TILE_PRICE)
    price_cents = parse_price(price_node.get_text(" ", strip=True)) if price_node else None

    category_id = tile.get(sel.ATTR_CATEGORY_ID)

    return Tile(
        product_id=product_id,
        order_number=order_number,
        title=title,
        author=author,
        price_cents=price_cents,
        url=url,
        subtitle=subtitle,
        category_id=category_id if isinstance(category_id, str) else None,
        # Badges repeat inside a tile once per layout slot.
        badges=frozenset(node.get_text(strip=True) for node in tile.select(sel.TILE_BADGE)),
    )


def parse_tiles(html: str, base: str = sel.BASE) -> list[Tile]:
    """Products from any beam listing page.

    An empty list means the shop said so in as many words. Tiles that will not
    parse mean the theme changed, and that raises.
    """
    page = soup(html)
    boxes = page.select(sel.TILE)

    if not boxes:
        if NO_RESULTS_MARKER in page.get_text(" ", strip=True):
            return []
        raise SourceStructureError(
            "beam-shop: no product tiles and no 'keine Artikel gefunden' message — "
            "the listing markup changed"
        )

    # A product can occupy several layout slots; the order number is its identity.
    tiles: dict[str, Tile] = {}
    for box in boxes:
        parsed = _parse_tile(box, base)
        if parsed is None:
            raise SourceStructureError(
                "beam-shop: a product tile is missing its title, link or id"
            )
        tiles.setdefault(parsed.order_number, parsed)
    return list(tiles.values())


@dataclass(frozen=True, slots=True)
class Detail:
    title: str | None
    price_cents: int | None


def parse_detail(html: str) -> Detail:
    """The pinned product's own page — the authoritative current price."""
    scope = soup(html).select_one(sel.DETAIL_SCOPE)
    if scope is None:
        raise SourceStructureError(
            f"beam-shop: no {sel.DETAIL_SCOPE} block on the product page — "
            "the detail markup changed"
        )

    meta = scope.select_one(sel.DETAIL_PRICE_META)
    content = meta.get("content") if meta else None
    if not isinstance(content, str):
        raise SourceStructureError("beam-shop: product page carries no machine-readable price")
    try:
        # The meta price uses a decimal point, unlike the visible de-DE one.
        price_cents = int(round(float(content) * 100))
    except ValueError as exc:
        raise SourceStructureError(f"beam-shop: unreadable price {content!r}") from exc

    title_node = scope.select_one(sel.DETAIL_TITLE)
    return Detail(
        title=title_node.get_text(" ", strip=True) if title_node else None,
        price_cents=price_cents,
    )


def total_pages(html: str) -> int | None:
    """``data-pages`` on the listing — how far ``?p=`` can usefully go."""
    listing = soup(html).select_one(sel.LISTING)
    if listing is None:
        return None
    value = listing.get(sel.ATTR_PAGES)
    return int(value) if isinstance(value, str) and value.isdigit() else None
