"""Titelbilder — einmal geholt, danach lokal (Ticket 15).

Kein Test hier geht ins Netz.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from conftest import beam_fixture, beam_tiles
from ebook_watchlist.covers import MIN_BYTES, CoverStore, file_name
from ebook_watchlist.http import FetchError, NotFound, RateLimited
from ebook_watchlist.sources.beam import parse as beam_parse

BEAM = Path(__file__).parent / "fixtures" / "beam"
NOW = datetime(2026, 9, 4, 20, 0)

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


# --- ein Bild darf keinen Lauf kosten (Review-Befund 3) ---------------------


def test_a_refusal_by_the_shop_is_a_fetch_error(tmp_path: Path) -> None:
    """403 ist die Antwort, mit der ein Shop aussperrt. Sie kam bis hierher als
    ``requests.HTTPError`` an — den fängt dieser Weg nicht, und der Lauf starb
    daran."""
    store = CoverStore(tmp_path / "covers")
    assert store.fetch(StubClient(FetchError("403")), 1, "https://example.invalid/a.jpg") is None


def test_one_broken_image_does_not_stop_the_others(tmp_path: Path, monkeypatch) -> None:
    """Dieselbe Überlegung wie bei einer einzelnen Quelle: was hier schiefgeht,
    darf höchstens dieses eine Bild kosten."""
    import requests

    from ebook_watchlist import paths
    from ebook_watchlist.models import MatchReason, Observation
    from ebook_watchlist.run import _fetch_covers
    from ebook_watchlist.store import Store

    monkeypatch.setenv("EBW_DATA_DIR", str(tmp_path))
    store = Store(paths.db_path())
    first = store.find_or_create_book(isbn=None, title="Eins", now=NOW)
    second = store.find_or_create_book(isbn=None, title="Zwei", now=NOW)

    class Blocking:
        def __init__(self) -> None:
            self.calls = 0

        def get_bytes(self, url: str) -> bytes:
            self.calls += 1
            if self.calls == 1:
                raise requests.HTTPError("403 Client Error")
            return IMAGE

    def seen(book_id: int) -> Observation:
        return Observation(
            source="beam",
            source_item_id=str(book_id),
            title="Egal",
            match_reason=MatchReason.WATCHLIST,
            book_id=book_id,
            cover_url=f"https://example.invalid/{book_id}.jpg",
        )

    client = Blocking()
    _fetch_covers(store, client, [seen(first.id), seen(second.id)])

    assert client.calls == 2
    assert store.book(first.id).cover_file is None
    assert store.book(second.id).cover_file is not None


def test_the_cover_address_survives_the_snapshot(tmp_path: Path, monkeypatch) -> None:
    """Sie stand in der Kachel, wurde ausgelesen, gesetzt — und beim Speichern
    weggeworfen, weil es die Spalte nicht gab. Für Watchlist-Titel fiel das nie
    auf: dort holt derselbe Lauf das Bild. Für eine Entdeckung war sie weg."""
    from ebook_watchlist import paths
    from ebook_watchlist.models import MatchReason, Observation
    from ebook_watchlist.store import Store

    monkeypatch.setenv("EBW_DATA_DIR", str(tmp_path))
    store = Store(paths.db_path())
    beobachtung = Observation(
        source="beam", source_item_id="1", title="Ein Fund",
        match_reason=MatchReason.GENRE_CATEGORY,
        cover_url="https://beam.invalid/media/9783104911854_200x200.jpg",
    )
    run = store.start_run("t", "cli", NOW)
    store.append(run, "t", [beobachtung], NOW)

    zurueck = store.latest_observations("t", [("beam", "1")])[("beam", "1")]

    assert zurueck.cover_url == beobachtung.cover_url
