"""Was die Watchlist-Seite über ein beobachtetes Buch weiß (Ticket 06).

Getrennt von den Routen, damit die Zusammenstellung testbar ist, ohne einen
HTTP-Client zu bemühen — und damit die Vorlage nichts rechnet.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from ..config import Profile
from ..deals import is_strong_deal
from ..matching.bundles import looks_like_bundle
from ..models import Availability, LinkOutcome, Observation
from ..relations import RelationKind
from ..sources import registry
from ..store import Store

#: Was die Leserin je Eintrag einschränken kann. Leer heißt: alle Quellen, die
#: eingeschaltet sind — nicht "keine".
RESTRICTIONS = ("library", "shop")


def _details(row) -> dict:
    try:
        return json.loads(row.details or "{}")
    except (TypeError, ValueError):  # pragma: no cover - defekte Zeile
        return {}


@dataclass(frozen=True, slots=True)
class SourceState:
    """Was eine Quelle über dieses Buch sagt."""

    name: str
    outcome: str
    url: str | None
    matched_title: str | None
    matched_author: str | None
    reason: str
    #: "library" oder "shop" — was diese Quelle *ist*. Die Registry sagt es,
    #: nicht eine Namensliste in der Vorlage (Ticket 14).
    category: str = "shop"
    #: Wie sie der Leserin gegenueber heisst.
    display: str = "Shop"

    @property
    def is_question(self) -> bool:
        """Ob hier ein Mensch entscheiden muss.

        ``not_found`` ist eine Antwort und braucht niemanden; nur ``unsure``
        ist eine Frage (Ticket 04).
        """
        return self.outcome == LinkOutcome.UNSURE

    @property
    def label(self) -> str:
        return {
            LinkOutcome.LINKED: "gefunden",
            LinkOutcome.CONFIRMED: "bestätigt",
            LinkOutcome.UNSURE: "unklar",
            LinkOutcome.NOT_FOUND: "nicht im Katalog",
        }.get(self.outcome, self.outcome)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class Entry:
    """Eine Zeile der Watchlist."""

    book_id: int
    title: str
    author: str | None
    active: bool
    restrict: str | None
    note: str | None
    cover_file: str | None
    sources: tuple[SourceState, ...]
    latest: Observation | None
    #: Unter der Schnaeppchen-Grenze. Faerbt den Preis und setzt das
    #: Abzeichen aufs Cover — dieselbe Farbe bedeutet ueberall dasselbe.
    deal: bool = False

    @property
    def is_bundle(self) -> bool:
        """Siehe ``triage.Suggestion.is_bundle`` — dieselbe Ableitung."""
        return looks_like_bundle(self.title)

    @property
    def needs_attention(self) -> bool:
        return any(state.is_question for state in self.sources)

    @property
    def price(self) -> str | None:
        if self.latest is None or self.latest.price_cents is None:
            return None
        return f"{self.latest.price_cents / 100:.2f} €".replace(".", ",")

    @property
    def availability(self) -> str | None:
        if self.latest is None or self.latest.availability is None:
            return None
        return {
            Availability.AVAILABLE: "ausleihbar",
            Availability.UNAVAILABLE: "verliehen",
            Availability.UNKNOWN: "unklar",
        }.get(self.latest.availability)

    @property
    def borrowable(self) -> bool:
        return self.latest is not None and self.latest.availability is Availability.AVAILABLE

    @property
    def seen(self) -> str | None:
        if self.latest is None or self.latest.observed_at is None:
            return None
        return self.latest.observed_at.strftime("%d.%m. %H:%M")

    @property
    def unresolved(self) -> bool:
        """Noch kein Lauf hat dieses Buch angesehen.

        Die Weboberfläche sucht nicht selbst (ADR 3) — sie schreibt die
        Beziehung, und der nächste Lauf löst auf.
        """
        return not self.sources


def entries(
    store: Store, profile: Profile, *, include_paused: bool = True
) -> list[Entry]:
    """Die Watchlist, wie die Seite sie zeigt."""
    profile_slug = profile.slug
    relations = store.relations(
        profile_slug, kind=str(RelationKind.WATCHING), active_only=not include_paused
    )
    book_ids = [relation.book_id for relation in relations]
    latest = store.latest_by_book(profile_slug, book_ids)

    rows = []
    for relation in relations:
        book = store.book(relation.book_id)
        if book is None:  # pragma: no cover - nur bei geloeschtem Buch
            continue
        details = _details(relation)
        states = tuple(
            SourceState(
                name=link.source,
                outcome=_details(link).get("outcome", ""),
                url=link.url,
                matched_title=_details(link).get("matched_title"),
                matched_author=_details(link).get("matched_author"),
                reason=_details(link).get("reason", ""),
                category=registry.category(profile, link.source),
                display=registry.label(profile, link.source),
            )
            for link in store.book_sources(book.id)
        )
        rows.append(
            Entry(
                book_id=book.id,
                title=book.title,
                author=book.author,
                active=relation.active,
                restrict=details.get("restrict"),
                note=details.get("note"),
                cover_file=book.cover_file,
                sources=states,
                latest=latest.get(book.id),
                deal=is_strong_deal(
                    getattr(latest.get(book.id), "price_cents", None), profile
                ),
            )
        )
    rows.sort(key=lambda entry: (not entry.needs_attention, entry.title.casefold()))
    return rows


def add(store: Store, profile_slug: str, *, title: str, author: str | None, now: datetime) -> int:
    """Ein Buch auf die Watchlist setzen.

    Aufgelöst wird hier **nicht**: die Weboberfläche scrapt nie (ADR 3). Sie
    schreibt die Beziehung, der nächste Lauf sucht das Buch bei den Quellen.
    Bis dahin steht der Eintrag als „noch nicht gesucht“ da — sichtbar, statt
    so zu tun, als sei schon etwas passiert.
    """
    book = store.find_or_create_book(
        isbn=None, title=title.strip(), author=(author or "").strip() or None, now=now
    )
    store.put_relation(profile_slug, book.id, str(RelationKind.WATCHING), now=now)
    return book.id


def set_restriction(
    store: Store, profile_slug: str, book_id: int, restrict: str | None, *, now: datetime
) -> None:
    """Auf welche Art Quelle der Eintrag geprüft wird. ``None`` heißt: alle."""
    details = {}
    for relation in store.relations_of(profile_slug, book_id):
        if relation.kind == RelationKind.WATCHING:
            details = _details(relation)
            break
    details.pop("restrict", None)
    if restrict:
        details["restrict"] = restrict
    # Ersetzen, nicht ergaenzen: sonst liesse sich eine Einschraenkung setzen,
    # aber nie wieder aufheben.
    store.set_relation_details(
        profile_slug, book_id, str(RelationKind.WATCHING), details, now=now
    )
