"""Alles, was über ein Buch bekannt ist, an einer Stelle (Ticket 07).

Diese Seite zahlt das Modell aus ADR 18 zum ersten Mal aus: dieselben Angaben
lagen vorher über vier Dateien verstreut, die einander nicht kannten —
*Cold Eternity* als Titel in ``owned.yaml``, als Produktnummer in
``dismissed.yaml``, und einmal als Zeile in ``watchlist.yaml``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from ..config import Profile
from ..deals import is_strong_deal
from ..models import Availability
from ..relations import RELATION_KINDS, RelationKind
from ..sources import registry
from ..store import Store
from .watchlist import SourceState

#: Was die Leserin über ein Buch sagen kann, in der Reihenfolge, in der es auf
#: der Seite steht. Mehrere gelten gleichzeitig — das ist der Normalfall.
KINDS: tuple[tuple[str, str], ...] = (
    (str(RelationKind.WATCHING), "beobachten"),
    (str(RelationKind.OWNED), "besitze ich"),
    (str(RelationKind.LIKED), "gefiel mir"),
    (str(RelationKind.DISLIKED), "gefiel mir nicht"),
    (str(RelationKind.DISMISSED), "nicht mehr vorschlagen"),
)

_AVAILABILITY = {
    Availability.AVAILABLE: "ausleihbar",
    Availability.UNAVAILABLE: "verliehen",
    Availability.UNKNOWN: "unklar",
}


def _details(row) -> dict:
    try:
        return json.loads(row.details or "{}")
    except (TypeError, ValueError):  # pragma: no cover - defekte Zeile
        return {}


@dataclass(frozen=True, slots=True)
class Relation:
    kind: str
    label: str
    active: bool
    note: str | None
    since: datetime | None

    @property
    def is_history(self) -> bool:
        """Abgelegt, aber nicht vergessen.

        Eine deaktivierte Beziehung ist selbst eine Auskunft — "beobachtet, bis
        du es gekauft hast" (ADR 18).
        """
        return not self.active


@dataclass(frozen=True, slots=True)
class Sighting:
    """Eine Zeile der Geschichte."""

    when: datetime | None
    #: Die *Art* der Quelle, nicht ihr interner Name: "voebb" war nie ein Wort
    #: fuer die Leserin (Ticket 14).
    source: str
    price: str | None
    availability: str | None
    #: Wie *diese* Quelle das Buch damals nannte — aber nur, wenn es von
    #: unserem Titel abweicht. Sonst wiederholte die Spalte in jeder Zeile
    #: dasselbe, und der eine interessante Fall ginge darin unter.
    other_title: str | None
    deal: bool


@dataclass(frozen=True, slots=True)
class Page:
    book_id: int
    title: str
    author: str | None
    series: str | None
    isbn: str | None
    cover_file: str | None
    relations: tuple[Relation, ...]
    sources: tuple[SourceState, ...]
    history: tuple[Sighting, ...]

    @property
    def active_kinds(self) -> set[str]:
        return {row.kind for row in self.relations if row.active}

    @property
    def has_history(self) -> bool:
        return bool(self.history)

    @property
    def mismatch(self) -> tuple[SourceState, ...]:
        """Quellen, deren eigener Titel nicht nach demselben Buch klingt.

        Kein Urteil, nur ein Hinweis: der Vergleich ist absichtlich stumpf —
        er soll auffallen lassen, was ein Mensch nachsehen sollte, nicht selbst
        entscheiden (ADR 8).
        """
        mine = _words(self.title)
        odd = []
        for state in self.sources:
            if not state.matched_title:
                continue
            theirs = _words(state.matched_title)
            if mine and theirs and not (mine & theirs):
                odd.append(state)
        return tuple(odd)


def _words(text: str) -> set[str]:
    return {word for word in text.casefold().split() if len(word) > 3}


def _price(cents: int | None) -> str | None:
    if cents is None:
        return None
    return f"{cents / 100:.2f} €".replace(".", ",")


def build(store: Store, profile: Profile, book_id: int) -> Page | None:
    """Die Seite zu einem Buch, oder ``None``, wenn es das nicht gibt."""
    book = store.book(book_id)
    if book is None:
        return None

    known = {row.kind: row for row in store.relations_of(profile.slug, book_id)}
    relations = tuple(
        Relation(
            kind=kind,
            label=label,
            active=known[kind].active,
            note=_details(known[kind]).get("note"),
            since=known[kind].created_at,
        )
        for kind, label in KINDS
        if kind in known
    )

    sources = tuple(
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
        for link in store.book_sources(book_id)
    )

    history = tuple(
        Sighting(
            when=observation.observed_at,
            source=registry.label(profile, observation.source),
            price=_price(observation.price_cents),
            availability=_AVAILABILITY.get(observation.availability)
            if observation.availability
            else None,
            other_title=(
                observation.title if observation.title.strip() != book.title.strip() else None
            ),
            deal=is_strong_deal(observation.price_cents, profile),
        )
        for observation in store.observations_for_book(profile.slug, book_id)
    )

    return Page(
        book_id=book.id,
        title=book.title,
        author=book.author,
        series=book.series,
        isbn=book.isbn,
        cover_file=book.cover_file,
        relations=relations,
        sources=sources,
        history=history,
    )


def set_relation(
    store: Store, profile: Profile, book_id: int, kind: str, *, active: bool, now: datetime
) -> None:
    """Eine Beziehung setzen oder stilllegen — nie löschen (ADR 18)."""
    if kind not in RELATION_KINDS:
        raise ValueError(f"unbekannte Beziehung {kind!r}")
    store.put_relation(profile.slug, book_id, kind, active=active, now=now)


def price_points(history: tuple[Sighting, ...]) -> list[Sighting]:
    """Nur die Sichtungen, bei denen sich der Preis geändert hat.

    Eine Zeile je Lauf wäre nach einem Jahr eine Wand aus derselben Zahl. Was
    interessiert, ist die Änderung — und mit nur einem Punkt bleibt es eben
    ein Punkt, statt ein Diagramm zu behaupten.

    Ältestes zuerst, anders als die Tabelle darunter: eine Preisliste ist eine
    Entwicklung und liest sich von links nach rechts. Die Tabelle beantwortet
    dagegen "was war zuletzt".
    """
    seen: list[Sighting] = []
    last: str | None = None
    for sighting in reversed(history):
        if sighting.price is None or sighting.price == last:
            continue
        seen.append(sighting)
        last = sighting.price
    return seen
