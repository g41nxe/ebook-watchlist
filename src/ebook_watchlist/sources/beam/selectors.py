"""Every beam-shop-specific string in one place (ADR 7).

Sourced from ``docs/research/beam-shop-interface.md``. The shop is Shopware 5,
so these are the stock Shopware listing classes with a custom theme on top —
they are shared by search results, category listings and author hubs alike.
"""

from __future__ import annotations

BASE = "https://www.beam-shop.de/"
SEARCH_PATH = "search"
AUTHOR_HUB_PATH = "autor-innenwelt/{slug}/"

#: Shopware ignores queries shorter than this and renders an empty result page.
MIN_QUERY_LENGTH = 4
#: ``n`` is clamped to this server-side; asking for more just wastes the request.
MAX_PAGE_SIZE = 100
#: What we ask for when resolving a single title — enough to see past the noise
#: without pulling a megabyte of HTML.
SEARCH_PAGE_SIZE = 48

SORT_BY_RELEASE_DATE = "1"

# --- product tile ---------------------------------------------------------

#: Each product appears two or three times in the DOM (overlay, image and list
#: slots), so tiles must be deduplicated by order number.
TILE = ".product--box[data-ordernumber]"
TILE_TITLE = "a.product--title"
TILE_SUBTITLE = ".product--subtitle"
TILE_AUTHOR = "a.product--author"
TILE_PRICE = ".price--default"
TILE_NOTE_BUTTON = "[data-note-article]"
TILE_BADGE = ".product--badge"
TILE_DESCRIPTION = ".product--description"

ATTR_ORDER_NUMBER = "data-ordernumber"
ATTR_CATEGORY_ID = "data-category-id"
ATTR_PRODUCT_ID = "data-note-article"

# --- product detail page --------------------------------------------------

#: A detail page embeds well over a hundred cross-sell tiles carrying the same
#: classes as the product itself, so every detail selector must be scoped to
#: this container or it will read a recommendation's price instead.
DETAIL_SCOPE = ".product--details"
DETAIL_TITLE = ".product--title"
DETAIL_PRICE_META = 'meta[itemprop="price"]'
#: Die Bestellnummer des Hauptprodukts — dieselbe Form wie auf der Kachel, und
#: im Gegensatz zur ISBN-Liste liegt sie innerhalb des Produktblocks. Auf der
#: ganzen Seite stehen 63 Bestellnummern, hier genau eine.
DETAIL_ORDER_NUMBER = 'input[name="sAdd"]'

# --- listing --------------------------------------------------------------

LISTING = ".listing"
ATTR_PAGES = "data-pages"

# --- literals -------------------------------------------------------------

AUTHOR_PREFIX = "von "
BADGE_NEW = "NEU"
BADGE_PREORDER = "Vorbestellbar"

# --- doctor probe ---------------------------------------------------------

PROBE_QUERY = "Krieg der Klone Scalzi"
