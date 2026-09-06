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
from ..models import Availability, MatchReason
from ..rating import RatingUnavailable, load_leseprofil
from ..ratings import (
    BY_CONVERSATION,
    BY_MODEL,
    BY_READER,
    HUMAN_ORIGINS,
    LABELS,
    book_subject,
    subject_of,
)
from ..reasons import short_why, why_shown
from ..relations import RELATION_KINDS, RelationKind
from ..sources import registry
from ..store import Store
from .watchlist import SourceState

#: Die Reihenfolge, in der Urteile auf der Seite stehen: was ein Mensch gesagt
#: hat, zuerst.
ORIGIN_ORDER: tuple[str, ...] = (BY_READER, BY_CONVERSATION, BY_MODEL)

#: Was die Leserin über ein Buch sagen kann, in der Reihenfolge, in der es auf
#: der Seite steht. Mehrere gelten gleichzeitig — das ist der Normalfall.
KINDS: tuple[tuple[str, str], ...] = (
    (str(RelationKind.WATCHING), "beobachten"),
    (str(RelationKind.OWNED), "besitze ich"),
    (str(RelationKind.LIKED), "gefiel mir"),
    (str(RelationKind.DISLIKED), "gefiel mir nicht"),
    (str(RelationKind.DISMISSED), "nicht mehr vorschlagen"),
)

#: Nur für den Vergleich zweier Zeitstempel, von denen einer fehlen darf.
_EPOCH = datetime.min

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
class Origin:
    """Was dieses Buch hereingebracht hat — in den Worten des Digests.

    Ein Watchlist-Titel braucht das nicht: warum er da ist, weiß die Leserin,
    sie hat ihn hingeschrieben. Eine Entdeckung ist der ganze Grund, aus dem
    die Frage überhaupt gestellt wird — und wer sie nicht über den Digest
    öffnet, bekam bisher keine Antwort darauf.
    """

    why: str
    short: str
    #: Autor:in oder Thema — dieselbe Farbtrennung wie in der Triage.
    author_driven: bool
    when: datetime | None


@dataclass(frozen=True, slots=True)
class Judgement:
    """Ein Urteil über dieses Buch, mit der Angabe, wer es gefällt hat.

    Der Unterschied ist der ganze Zweck der Zeile: eine 4 von der Leserin ist
    eine Tatsache, eine 4 vom Modell ein Vorschlag (ADR 17). Sie dürfen
    deswegen nicht gleich aussehen.
    """

    origin: str
    label: str
    stars: int
    reason: str
    confidence: str
    profile_version: int
    when: datetime | None

    @property
    def is_human(self) -> bool:
        return self.origin in HUMAN_ORIGINS

    def stale(self, current: int | None) -> bool:
        """Gegen eine ältere Profilfassung gefällt — und deshalb nur noch Auskunft.

        Gilt nur für Maschinenurteile: was ein Mensch gesagt hat, verfällt
        nicht, wenn er sein Profil schärft.
        """
        return not self.is_human and current is not None and self.profile_version != current


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
    judgements: tuple[Judgement, ...]
    #: Die heutige Profilversion, oder ``None``, wenn das Profil nicht lesbar ist.
    profile_version: int | None
    #: Warum dieser Fund überhaupt hereinkam — nur bei Entdeckungen (Ticket 22).
    origin: Origin | None
    #: An welcher Art Quelle geprüft wird — ``None`` heißt: an allen. Steht
    #: hier und nicht mehr in der Watchlist-Zeile: das ist eine Einstellung
    #: dieses Buchs, keine Handlung an der Liste (Ticket 48).
    restrict: str | None = None
    #: Ob das Buch überhaupt beobachtet wird — sonst gibt es nichts zu prüfen.
    watching: bool = False

    @property
    def my_stars(self) -> int | None:
        """Was die Leserin selbst vergeben hat — sonst ``None``.

        Ausdrücklich nicht ``0``: keine Bewertung und "passt überhaupt nicht"
        sind zwei verschiedene Auskünfte, und eine Reihe grauer Sterne würde
        die zweite behaupten, wo gar nichts gesagt wurde.
        """
        for judgement in self.judgements:
            if judgement.origin == BY_READER:
                return judgement.stars
        return None

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


def _origin(seen) -> Origin | None:
    """Die jüngste Sichtung, die keine Watchlist-Prüfung war.

    Ein Buch, das nur über die Watchlist beobachtet wird, hat keine solche
    Sichtung — und bekommt deshalb keine Zeile, ohne dass es dafür eine eigene
    Regel bräuchte. Die Formulierung kommt aus :mod:`ebook_watchlist.reasons`,
    damit Digest, Triage und diese Seite nicht dreimal dasselbe verschieden
    sagen (Ticket 14).
    """
    for observation in seen:
        if observation.match_reason is MatchReason.WATCHLIST:
            continue
        return Origin(
            why=why_shown(observation),
            short=short_why(observation),
            author_driven=observation.match_reason is MatchReason.PROFILE_AUTHOR,
            when=observation.observed_at,
        )
    return None


def _judgements(store: Store, book, seen) -> tuple[Judgement, ...]:
    """Alle Urteile, die zu diesem Buch gehören — an drei Sorten Schlüssel.

    Was ein Mensch gesagt hat, hängt am Buch. Das Tor schlüsselt dagegen am
    Fund, weil es dreihundert Funde bewertet, von denen die wenigsten je eine
    Buchzeile bekommen (ADR 18) — sein Urteil ist deshalb über die ISBN oder
    über die Produktnummern der Quellen zu finden, unter denen dieses Buch
    gesichtet wurde.
    """
    of_book = book_subject(book.id)
    subjects = {of_book}
    if book.isbn:
        subjects.add(f"isbn:{book.isbn}")
    subjects.update(subject_of(observation) for observation in seen)

    rows = store.ratings_for(subjects)
    found: dict[str, object] = {}
    for (subject, origin), row in rows.items():
        # Nur das Modell darf am Fund hängen: eine Leserin-Bewertung unter
        # einem Fund-Schlüssel gäbe es nur, wenn jemand sie dort hinschriebe.
        if origin != BY_MODEL and subject != of_book:
            continue
        previous = found.get(origin)
        if previous is None or (row.rated_at or _EPOCH) > (previous.rated_at or _EPOCH):
            found[origin] = row

    return tuple(
        Judgement(
            origin=origin,
            label=LABELS[origin],
            stars=row.stars,
            reason=row.reason,
            confidence=row.confidence,
            profile_version=row.profile_version,
            when=row.rated_at,
        )
        for origin in ORIGIN_ORDER
        if (row := found.get(origin)) is not None
    )


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

    seen = store.observations_for_book(profile.slug, book_id)
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
        for observation in seen
    )

    try:
        _, current_version = load_leseprofil()
    except RatingUnavailable:
        current_version = None

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
        judgements=_judgements(store, book, seen),
        profile_version=current_version,
        origin=_origin(seen),
        restrict=_details(known[str(RelationKind.WATCHING)]).get("restrict")
        if str(RelationKind.WATCHING) in known
        else None,
        watching=str(RelationKind.WATCHING) in known
        and known[str(RelationKind.WATCHING)].active,
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


def set_stars(store: Store, book_id: int, stars: int | None, *, now: datetime) -> None:
    """Die eigenen Sterne der Leserin setzen oder zurücknehmen.

    Sie stehen unter ihrer eigenen Herkunft und damit neben dem Modellurteil,
    nicht darüber: keines überschreibt das andere (ADR 17, Ticket 21). Der
    Profilfassung wird mitgeschrieben, damit später nachvollziehbar bleibt, wovon
    hier die Rede war — verfallen tut ihr Urteil deswegen nicht.
    """
    if stars is None:
        store.drop_rating(book_subject(book_id), BY_READER)
        return
    if not 0 <= stars <= 5:
        raise ValueError(f"Sterne müssen zwischen 0 und 5 liegen, nicht {stars}")
    try:
        _, version = load_leseprofil()
    except RatingUnavailable:
        # Ohne lesbares Profil bleibt ihre Bewertung trotzdem gültig — sie
        # hängt nicht an ihm. Die 0 sagt: unter keiner bekannten Fassung.
        version = 0
    store.put_rating(
        book_subject(book_id),
        stars=stars,
        confidence="belegt",
        reason="",
        profile_version=version,
        now=now,
        origin=BY_READER,
    )
