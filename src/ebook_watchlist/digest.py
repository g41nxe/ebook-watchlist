"""The Digest model — one structured object, two renderers (ADR 15).

Sections are fixed and ordered; empty ones are dropped. The error section is
always last and is enough on its own to make a Digest worth emitting: a broken
scraper must never look like a quiet day.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .models import Delta, DeltaKind, MatchReason, SourceFailure

SECTION_LIBRARY = "Bibliothek"
SECTION_PRICES = "Watchlist — Preise"
SECTION_AUTHORS = "Neue Titel deiner Autor:innen"
SECTION_GENRE = "Genre-Vorschläge (unsicher)"
SECTION_ERRORS = "⚠️ Fehler"

SECTION_ORDER: tuple[str, ...] = (
    SECTION_LIBRARY,
    SECTION_PRICES,
    SECTION_AUTHORS,
    SECTION_GENRE,
    SECTION_ERRORS,
)


@dataclass(frozen=True, slots=True)
class DigestEntry:
    title: str
    author: str | None = None
    detail: str | None = None
    flags: tuple[str, ...] = ()
    url: str | None = None


@dataclass(frozen=True, slots=True)
class DigestSection:
    title: str
    entries: tuple[DigestEntry, ...]


@dataclass(frozen=True, slots=True)
class Digest:
    profile_name: str
    generated_at: datetime
    since: datetime | None
    sections: tuple[DigestSection, ...] = field(default_factory=tuple)

    @property
    def is_empty(self) -> bool:
        return not self.sections

    @property
    def headline(self) -> str:
        if self.since is None:
            return "Erster Check"
        return f"Änderungen seit letztem Check {self.since:%d.%m.%Y %H:%M}"


def _format_price(cents: int | None) -> str:
    if cents is None:
        return "—"
    return f"{cents / 100:.2f} €".replace(".", ",")


def _entry_for(delta: Delta) -> tuple[str, DigestEntry]:
    current, previous = delta.current, delta.previous

    if delta.kind is DeltaKind.BECAME_AVAILABLE:
        detail = "jetzt verfügbar"
        if previous.reservation_count:
            detail += f" (zuvor {previous.reservation_count} Vormerkungen)"
        return SECTION_LIBRARY, DigestEntry(
            title=current.title, author=current.author, detail=detail, url=current.url
        )

    if delta.kind is not DeltaKind.PRICE_DROP:
        raise ValueError(f"no Digest section defined for delta kind {delta.kind!r}")

    detail = f"{_format_price(previous.price_cents)} → {_format_price(current.price_cents)}"
    section = {
        MatchReason.WATCHLIST: SECTION_PRICES,
        MatchReason.PROFILE_AUTHOR: SECTION_AUTHORS,
        MatchReason.GENRE_CATEGORY: SECTION_GENRE,
    }[current.match_reason]
    return section, DigestEntry(
        title=current.title, author=current.author, detail=detail, url=current.url
    )


def build_digest(
    *,
    profile_name: str,
    generated_at: datetime,
    since: datetime | None,
    deltas: list[Delta],
    failures: list[SourceFailure],
) -> Digest:
    buckets: dict[str, list[DigestEntry]] = {title: [] for title in SECTION_ORDER}

    for delta in deltas:
        section, entry = _entry_for(delta)
        buckets[section].append(entry)

    for failure in failures:
        buckets[SECTION_ERRORS].append(
            DigestEntry(title=failure.source, detail=failure.message)
        )

    sections = tuple(
        DigestSection(title=title, entries=tuple(buckets[title]))
        for title in SECTION_ORDER
        if buckets[title]
    )
    return Digest(
        profile_name=profile_name,
        generated_at=generated_at,
        since=since,
        sections=sections,
    )
