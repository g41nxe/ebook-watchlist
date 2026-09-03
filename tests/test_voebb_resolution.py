"""Automatic resolution: a bare title and author become a pinned detail page."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from ebook_watchlist.config import Profile, WatchlistEntry
from ebook_watchlist.matching import Confidence
from ebook_watchlist.sources.base import RESOLUTION_RETRY_AFTER, RunContext
from ebook_watchlist.sources.voebb import selectors as sel
from ebook_watchlist.sources.voebb.source import VoebbSource
from ebook_watchlist.store import Store

FIXTURES = Path(__file__).parent / "fixtures" / "voebb"
NOW = datetime(2026, 9, 4, 6, 0)

RILEY = "mediaInfo,0-0-373164461-200-0-0-0-0-0-0-0.html"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class ScriptedClient:
    """Answers each GET from a queue, so a multi-page walk can be scripted."""

    def __init__(self, *pages: str) -> None:
        self.pages = list(pages)
        self.requests: list[tuple[str, dict | None]] = []

    def get(self, url: str, params: dict | None = None) -> str:
        self.requests.append((url, params))
        return self.pages.pop(0) if len(self.pages) > 1 else self.pages[0]


@pytest.fixture
def context(tmp_path: Path) -> RunContext:
    return RunContext(profile_slug="test", store=Store(tmp_path / "s.db"), now=NOW)


def source(*pages: str, **kwargs) -> VoebbSource:
    return VoebbSource(client=ScriptedClient(*pages), **kwargs)  # type: ignore[arg-type]


# --- the search query -----------------------------------------------------


def test_only_the_surname_goes_into_the_single_search_box() -> None:
    voebb = source(fixture("search-hits.html"))
    assert voebb._query_for(WatchlistEntry(title="Der Schwarm", author="Frank Schätzing")) == (
        "Der Schwarm Schätzing"
    )
    assert voebb._query_for(WatchlistEntry(title="Der Schwarm", author="Schätzing, Frank")) == (
        "Der Schwarm Schätzing"
    )
    assert voebb._query_for(WatchlistEntry(title="Der Schwarm")) == "Der Schwarm"


def test_the_search_is_a_get_with_the_query_in_the_url() -> None:
    voebb = source(fixture("search-hits.html"))
    voebb.resolve(WatchlistEntry(title="Die sieben Schwestern", author="Lucinda Riley"))

    url, params = voebb.client.requests[0]  # type: ignore[attr-defined]
    assert url.endswith(sel.SEARCH_PATH)
    assert params["pText"] == "Die sieben Schwestern Riley"
    assert params["cmdId"] == "703"


# --- the resolution decision ----------------------------------------------


def test_a_confident_hit_resolves_to_its_detail_page() -> None:
    voebb = source(fixture("search-hits.html"))
    resolution = voebb.resolve(
        WatchlistEntry(title="Die sieben Schwestern", author="Lucinda Riley")
    )

    assert resolution is not None
    assert resolution.confidence is Confidence.AUTO_ACCEPT, resolution.reason
    assert resolution.accepted is not None
    assert resolution.accepted.payload.endswith(RILEY)


def test_the_ebook_is_preferred_over_the_audiobook_of_the_same_novel() -> None:
    """Both are listed under the identical title and author; without a format
    preference the matcher can only call it a tie and nothing ever resolves."""
    voebb = source(fixture("search-hits.html"), media=("ic_eaudio",))
    resolution = voebb.resolve(
        WatchlistEntry(title="Die sieben Schwestern", author="Lucinda Riley")
    )

    assert resolution is not None
    assert resolution.accepted is not None
    assert not resolution.accepted.payload.endswith(RILEY)


def test_a_format_nobody_stocks_falls_back_instead_of_vanishing() -> None:
    voebb = source(fixture("search-hits.html"), media=("ic_evideo",))
    resolution = voebb.resolve(
        WatchlistEntry(title="Die sieben Schwestern", author="Lucinda Riley")
    )
    assert resolution is not None
    assert resolution.ranked


def test_no_hits_means_not_in_this_catalogue_not_an_error() -> None:
    voebb = source(fixture("search-no-hits.html"))
    assert voebb.resolve(WatchlistEntry(title="Project Hail Mary", author="Andy Weir")) is None


def test_a_wrong_looking_hit_is_not_accepted() -> None:
    voebb = source(fixture("search-hits.html"))
    entry = WatchlistEntry(title="Kochen mit Kräutern", author="Erika Mustermann")
    resolution = voebb.resolve(entry)

    assert resolution is not None
    assert resolution.confidence is Confidence.NO_MATCH
    assert resolution.accepted is None


def test_resolution_stops_after_the_first_page_when_it_is_already_sure() -> None:
    voebb = source(fixture("search-hits.html"))
    voebb.resolve(WatchlistEntry(title="Die sieben Schwestern", author="Lucinda Riley"))
    assert len(voebb.client.requests) == 1  # type: ignore[attr-defined]


# --- caching and the attention list ---------------------------------------


def test_a_resolved_link_is_remembered_and_not_searched_again(context: RunContext) -> None:
    voebb = source(fixture("search-hits.html"))
    entry = WatchlistEntry(title="Die sieben Schwestern", author="Lucinda Riley")

    first = voebb.linked_entry(entry, context)
    assert first is not None
    assert first.resolved_links["voebb"].endswith(RILEY)
    assert len(voebb.client.requests) == 1  # type: ignore[attr-defined]

    second = voebb.linked_entry(entry, context)
    assert second is not None
    assert second.resolved_links == first.resolved_links
    assert len(voebb.client.requests) == 1  # type: ignore[attr-defined]


def test_a_hand_pinned_link_is_never_second_guessed(context: RunContext) -> None:
    voebb = source(fixture("search-hits.html"))
    entry = WatchlistEntry(
        title="Irgendwas", resolved_links={"voebb": "mediaInfo,0-0-1-200-0.html"}
    )

    linked = voebb.linked_entry(entry, context)

    assert linked is entry
    assert voebb.client.requests == []  # type: ignore[attr-defined]


def test_an_unresolvable_entry_is_named_in_the_digest_and_skipped(context: RunContext) -> None:
    voebb = source(fixture("search-hits.html"))
    entry = WatchlistEntry(title="Die sieben Schwestern", author="Jemand Anders")

    assert voebb.linked_entry(entry, context) is None
    assert len(context.attention) == 1
    assert context.attention[0].entry_title == "Die sieben Schwestern"
    assert context.attention[0].source == "voebb"
    assert context.attention[0].reason


def test_a_failed_lookup_is_not_repeated_on_the_next_run(context: RunContext) -> None:
    voebb = source(fixture("search-no-hits.html"))
    entry = WatchlistEntry(title="Project Hail Mary", author="Andy Weir")

    assert voebb.linked_entry(entry, context) is None
    assert len(voebb.client.requests) == 1  # type: ignore[attr-defined]

    assert voebb.linked_entry(entry, context) is None
    assert len(voebb.client.requests) == 1  # type: ignore[attr-defined]
    # A cached miss must not nag every single day.
    assert context.attention == []


def test_a_stale_miss_gets_another_chance(context: RunContext) -> None:
    voebb = source(fixture("search-no-hits.html"))
    entry = WatchlistEntry(title="Project Hail Mary", author="Andy Weir")
    voebb.linked_entry(entry, context)

    context.now = NOW + RESOLUTION_RETRY_AFTER + timedelta(seconds=1)
    voebb.linked_entry(entry, context)

    assert len(voebb.client.requests) == 2  # type: ignore[attr-defined]


def test_editing_the_entry_forces_a_fresh_lookup(context: RunContext) -> None:
    """Resolutions are keyed on title+author, so correcting either re-resolves."""
    voebb = source(fixture("search-no-hits.html"))
    voebb.linked_entry(WatchlistEntry(title="Projekt Hail Mary", author="Andy Weir"), context)
    voebb.linked_entry(WatchlistEntry(title="Project Hail Mary", author="Andy Weir"), context)
    assert len(voebb.client.requests) == 2  # type: ignore[attr-defined]


# --- through collect() ----------------------------------------------------


def test_collect_resolves_then_reads_availability(context: RunContext) -> None:
    voebb = source(fixture("search-hits.html"), fixture("detail-unavailable.html"))
    entry = WatchlistEntry(title="Die sieben Schwestern", author="Lucinda Riley")

    observations = voebb.collect(Profile(slug="test", name="Test"), [entry], context)

    assert len(observations) == 1
    assert observations[0].source_item_id == "373164461"
    assert observations[0].reservation_count == 16
