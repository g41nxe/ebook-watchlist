"""Titelbilder — einmal geholt, danach lokal (Ticket 15).

Kein Test hier geht ins Netz.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import beam_fixture, beam_tiles
from ebook_watchlist.covers import MIN_BYTES, CoverStore, file_name
from ebook_watchlist.http import FetchError, NotFound, RateLimited
from ebook_watchlist.sources.beam import parse as beam_parse

BEAM = Path(__file__).parent / "fixtures" / "beam"

IMAGE = b"\xff\xd8\xff" + b"x" * MIN_BYTES  # gross genug, um kein Platzhalter zu sein


class StubClient:
    """Zaehlt, wie oft geholt wurde — der Punkt der ganzen Uebung."""

    def __init__(self, payload: bytes | Exception = IMAGE) -> None:
        self.payload = payload
        self.calls: list[str] = []

    def get_bytes(self, url: str) -> bytes:
        self.calls.append(url)
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


# --- aus den Seiten lesen ---------------------------------------------------


def test_every_tile_carries_a_cover() -> None:
    tiles = beam_tiles("search-hits.html")
    with_cover = [tile for tile in tiles if tile.cover_url]

    assert len(with_cover) == len(tiles) == 48
    assert all(url.startswith("https://") for url in (tile.cover_url for tile in with_cover))


def test_the_address_comes_from_the_srcset_not_the_placeholder_pixel() -> None:
    """Das Theme laedt die Bilder nach; im ``src`` steht nur ein Pixel."""
    tiles = beam_tiles("search-hits.html")
    krieg = next(tile for tile in tiles if tile.product_id == "606983")

    assert krieg.cover_url == (
        "https://www.beam-shop.de/media/image/5b/f2/e2/9783104911854_200x200.jpg"
    )
    assert "pixel.jpg" not in (krieg.cover_url or "")


def test_the_detail_page_offers_the_larger_one() -> None:
    detail = beam_parse.parse_detail(beam_fixture("product-detail.html"))
    assert detail.cover_url is not None
    assert "600x600" in detail.cover_url


def test_a_page_without_an_image_simply_has_none() -> None:
    html = (
        '<html><body><div class="product--details">'
        '<meta itemprop="price" content="9.99"></div></body></html>'
    )
    assert beam_parse.parse_detail(html).cover_url is None


# --- ablegen ----------------------------------------------------------------


def test_the_name_carries_the_book_and_the_address(tmp_path: Path) -> None:
    name = file_name(17, "https://example.invalid/a/9783104911854_200x200.jpg")
    assert name.startswith("17-")
    assert name.endswith(".jpg")


def test_a_changed_cover_becomes_a_new_file() -> None:
    """Sonst zeigte ein alter Verweis stillschweigend auf ein anderes Bild."""
    first = file_name(17, "https://example.invalid/alt.jpg")
    second = file_name(17, "https://example.invalid/neu.jpg")
    assert first != second


def test_it_is_fetched_once_and_then_read_from_disk(tmp_path: Path) -> None:
    store = CoverStore(tmp_path / "covers")
    client = StubClient()

    name = store.fetch(client, 1, "https://example.invalid/a.jpg")
    assert name is not None
    assert store.has(name)
    assert len(client.calls) == 1

    assert store.fetch(client, 1, "https://example.invalid/a.jpg") == name
    assert len(client.calls) == 1  # nicht noch einmal


def test_a_placeholder_pixel_is_not_kept(tmp_path: Path) -> None:
    """Shopware liefert ein 1x1-Pixel, solange das echte Bild fehlt."""
    store = CoverStore(tmp_path / "covers")
    assert store.fetch(StubClient(b"tiny"), 1, "https://example.invalid/a.jpg") is None
    assert not (tmp_path / "covers").exists() or not any((tmp_path / "covers").iterdir())


@pytest.mark.parametrize("failure", [FetchError("weg"), NotFound("weg")])
def test_a_missing_image_is_not_a_reason_to_fail_a_run(
    tmp_path: Path, failure: Exception
) -> None:
    """Ein Buch ohne Bild ist ein Buch mit einem Platzhalter."""
    store = CoverStore(tmp_path / "covers")
    assert store.fetch(StubClient(failure), 1, "https://example.invalid/a.jpg") is None


def test_throttling_is_passed_through(tmp_path: Path) -> None:
    """Da hat der Shop ausdruecklich Halt gesagt — das gilt fuer alles Weitere."""
    store = CoverStore(tmp_path / "covers")
    with pytest.raises(RateLimited):
        store.fetch(StubClient(RateLimited("429")), 1, "https://example.invalid/a.jpg")
