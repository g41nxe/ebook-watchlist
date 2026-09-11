"""Smoke tests against the real sites.

Excluded from the default suite (``-m 'not live'``). Run them deliberately when
a Source looks broken, or to refresh confidence before a release::

    uv run pytest -m live

They assert that the documented fields still *parse* — never their values.
Copies, queue lengths, and prices change by the hour.
"""

from __future__ import annotations

from urllib.parse import urljoin

import pytest

from ebook_watchlist.http import HttpClient
from ebook_watchlist.sources.onleihe import parse
from ebook_watchlist.sources.onleihe import selectors as sel

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def client() -> HttpClient:
    return HttpClient()


def test_onleihe_detail_page_still_parses(client: HttpClient) -> None:
    detail = parse.parse_detail(client.get(urljoin(sel.BASE, sel.PROBE_DETAIL_PATH)))
    assert detail.copies >= 0
    assert detail.available_copies >= 0
    assert detail.title


def test_onleihe_search_still_parses(client: HttpClient) -> None:
    html = client.get(
        urljoin(sel.BASE, sel.SEARCH_PATH),
        params=dict(sel.SEARCH_PARAMS, pText=sel.PROBE_QUERY),
    )
    candidates = parse.parse_search_results(html)
    assert candidates, "the probe query must keep returning hits"
    assert candidates[0].title
    assert candidates[0].url.startswith("http")


# --- OverDrive ---------------------------------------------------------------


def test_overdrive_probe_still_parses(client: HttpClient) -> None:
    """Der Selbsttest der Quelle gegen das echte Thunder. Er prueft, dass die
    Felder noch da sind — nie, welche Werte sie tragen: Lizenzen, Vormerkungen
    und Wartezeiten aendern sich stuendlich."""
    from ebook_watchlist.sources.overdrive import OverdriveSource

    OverdriveSource(client=client).probe()


def test_overdrive_finds_the_german_edition_of_dark_matter(client: HttpClient) -> None:
    """Der Titel, an dem die zweite Bibliothek haengt. Faellt dieser Test, hat
    OverDrive den Titel abgegeben oder umbenannt — beides ist eine Nachricht."""
    from ebook_watchlist.config import WatchlistEntry
    from ebook_watchlist.matching import Confidence
    from ebook_watchlist.sources.overdrive import OverdriveSource

    resolution = OverdriveSource(client=client).resolve(
        WatchlistEntry(title="Dark Matter", author="Blake Crouch", isbn="9783641171421")
    )

    assert resolution is not None
    assert resolution.confidence is Confidence.AUTO_ACCEPT
