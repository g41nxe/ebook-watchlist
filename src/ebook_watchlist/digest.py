"""The Digest model — one structured object, two renderers (ADR 15).

Sections are fixed and ordered; empty ones are dropped. The error section is
always last and is enough on its own to make a Digest worth emitting: a broken
scraper must never look like a quiet day.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .config import Profile
from .deals import deal_flags
from .models import Attention, Delta, DeltaKind, MatchReason, SourceFailure
from .reasons import why_shown

SECTION_LIBRARY = "Bibliothek"
SECTION_PRICES = "Watchlist — Preise"
SECTION_AUTHORS = "Neue Titel deiner Autor:innen"
SECTION_GENRE = "Genre-Vorschläge (unsicher)"
SECTION_ATTENTION = "Braucht Aufmerksamkeit"
SECTION_ERRORS = "⚠️ Fehler"

SECTION_ORDER: tuple[str, ...] = (
    SECTION_LIBRARY,
    SECTION_PRICES,
    SECTION_AUTHORS,
    SECTION_GENRE,
    SECTION_ATTENTION,
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


_SECTION_BY_REASON = {
    MatchReason.WATCHLIST: SECTION_PRICES,
    MatchReason.PROFILE_AUTHOR: SECTION_AUTHORS,
    MatchReason.GENRE_CATEGORY: SECTION_GENRE,
}


def _entry_for(delta: Delta, profile: Profile | None) -> tuple[str, DigestEntry]:
    current, previous = delta.current, delta.previous

    if delta.kind is DeltaKind.BECAME_AVAILABLE:
        detail = "jetzt verfügbar"
        if previous and previous.reservation_count:
            detail += f" (zuvor {previous.reservation_count} Vormerkungen)"
        return SECTION_LIBRARY, DigestEntry(
            title=current.title, author=current.author, detail=detail, url=current.url
        )

    if delta.kind is DeltaKind.FIRST_SEEN:
        # Der Anlass zuerst, der Preis danach: die alte Reihenfolge las sich,
        # als sei der Preis der Grund (Ticket 14).
        detail = why_shown(current)
        price = _format_price(current.price_cents)
        if price != "—":
            detail += f" · {price}"
    elif delta.kind is DeltaKind.PRICE_DROP and previous is not None:
        detail = f"{_format_price(previous.price_cents)} → {_format_price(current.price_cents)}"
    else:
        raise ValueError(f"no Digest section defined for delta kind {delta.kind!r}")

    section = _SECTION_BY_REASON[current.match_reason]
    flags = deal_flags(current, previous, profile) if profile else ()
    return section, DigestEntry(
        title=current.title,
        author=current.author,
        detail=detail,
        flags=flags,
        url=current.url,
    )


def build_digest(
    *,
    profile_name: str,
    generated_at: datetime,
    since: datetime | None,
    deltas: list[Delta],
    failures: list[SourceFailure],
    attention: list[Attention] | None = None,
    profile: Profile | None = None,
) -> Digest:
    buckets: dict[str, list[DigestEntry]] = {title: [] for title in SECTION_ORDER}

    for delta in deltas:
        section, entry = _entry_for(delta, profile)
        buckets[section].append(entry)

    for item in attention or []:
        detail = f"{item.source}: {item.reason}"
        if item.best_guess:
            detail += f" — bester Treffer: „{item.best_guess}“"
        buckets[SECTION_ATTENTION].append(
            DigestEntry(
                title=item.entry_title,
                author=item.entry_author,
                detail=detail,
                url=item.best_guess_url,
            )
        )

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
