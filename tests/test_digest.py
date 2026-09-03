from __future__ import annotations

from datetime import datetime

from ebook_watchlist.digest import (
    SECTION_ERRORS,
    SECTION_GENRE,
    SECTION_LIBRARY,
    SECTION_PRICES,
    build_digest,
)
from ebook_watchlist.models import (
    Availability,
    Delta,
    DeltaKind,
    MatchReason,
    Observation,
    SourceFailure,
)
from ebook_watchlist.render import render_html, render_text

NOW = datetime(2026, 9, 4, 6, 0)
THEN = datetime(2026, 9, 3, 6, 0)


def build(**kwargs):
    defaults = dict(
        profile_name="Testprofil",
        generated_at=NOW,
        since=THEN,
        deltas=[],
        failures=[],
    )
    return build_digest(**{**defaults, **kwargs})


def observation(**overrides) -> Observation:
    defaults = dict(
        source="fake",
        source_item_id="1",
        title="Ein Titel",
        author="Eine Autorin",
        match_reason=MatchReason.WATCHLIST,
    )
    return Observation(**{**defaults, **overrides})


def test_nothing_to_report_is_empty() -> None:
    assert build().is_empty


def test_empty_sections_are_omitted_and_order_is_fixed() -> None:
    digest = build(
        deltas=[
            Delta(
                DeltaKind.PRICE_DROP,
                observation(
                    source_item_id="2",
                    price_cents=499,
                    match_reason=MatchReason.GENRE_CATEGORY,
                ),
                observation(
                    source_item_id="2",
                    price_cents=999,
                    match_reason=MatchReason.GENRE_CATEGORY,
                ),
            ),
            Delta(
                DeltaKind.BECAME_AVAILABLE,
                observation(availability=Availability.AVAILABLE),
                observation(availability=Availability.UNAVAILABLE),
            ),
        ]
    )
    assert [section.title for section in digest.sections] == [SECTION_LIBRARY, SECTION_GENRE]


def test_error_section_is_always_last_and_renders_on_its_own() -> None:
    digest = build(failures=[SourceFailure("voebb", "structure changed")])
    assert [section.title for section in digest.sections] == [SECTION_ERRORS]
    assert not digest.is_empty
    assert "structure changed" in render_text(digest)


def test_price_delta_shows_both_prices() -> None:
    digest = build(
        deltas=[
            Delta(
                DeltaKind.PRICE_DROP,
                observation(price_cents=499),
                observation(price_cents=1299),
            )
        ]
    )
    section = digest.sections[0]
    assert section.title == SECTION_PRICES
    assert section.entries[0].detail == "12,99 € → 4,99 €"


def test_headline_names_the_previous_check() -> None:
    assert build().headline == "Änderungen seit letztem Check 03.09.2026 06:00"
    assert build(since=None).headline == "Erster Check"


def test_renderers_cover_every_entry() -> None:
    digest = build(
        deltas=[
            Delta(
                DeltaKind.BECAME_AVAILABLE,
                observation(availability=Availability.AVAILABLE, url="https://example.invalid/x"),
                observation(availability=Availability.UNAVAILABLE, reservation_count=3),
            )
        ]
    )
    text = render_text(digest)
    assert "Ein Titel" in text
    assert "jetzt verfügbar (zuvor 3 Vormerkungen)" in text
    assert "https://example.invalid/x" in text

    html = render_html(digest)
    assert html.startswith("<!doctype html>")
    assert 'href="https://example.invalid/x"' in html
    assert "Ein Titel" in html


def test_html_escapes_scraped_text() -> None:
    digest = build(
        deltas=[
            Delta(
                DeltaKind.PRICE_DROP,
                observation(title="<script>alert(1)</script>", price_cents=499),
                observation(title="<script>alert(1)</script>", price_cents=999),
            )
        ]
    )
    html = render_html(digest)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
