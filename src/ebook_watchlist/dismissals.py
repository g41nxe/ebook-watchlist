"""Aus alten Ablehnungen werden Beziehungen (Ticket 17, ADR 18).

``dismissed.yaml`` kannte nur Produktnummern eines Shops::

    beam:
      - "623935"     # Providence - Max Barry
      - "1067554"    # Cold Eternity - S.A. Barnes

Das reichte für "dieser Shop soll das nicht mehr zeigen" und für sonst nichts:
die Onleihe hätte dieselben Bücher weiter angeboten. Der Import hat sie deshalb
bewusst nicht geraten — eine Nummer sagt nicht, welches Buch gemeint ist, und
das zu erfinden wäre genau die stille Erfindung, die dieses Werkzeug vermeidet
(ADR 8).

Nur der Shop kann es sagen. Das hier ist deshalb kein Import, sondern eine
kleine Auflösung: einmal nachfragen, das Buch anlegen oder wiederfinden, die
Beziehung am *Buch* festhalten. Danach unterdrückt sie an jeder Quelle, und die
YAML-Datei wird nicht mehr gebraucht.

Eine Anfrage je Nummer, und keine zweite: was schon aufgelöst ist, erkennt der
Weg an der gespeicherten Nummer und fragt nicht noch einmal. Eine Nummer, die
der Shop nicht mehr kennt, wird **gemeldet** — still zu verwerfen hieße, eine
Ablehnung zu verlieren, ohne dass jemand davon erfährt.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from .models import LinkOutcome
from .relations import RelationKind
from .store import Store

if TYPE_CHECKING:  # pragma: no cover - nur fuer die Typprüfung
    from .sources.base import Source

#: Beide Beziehungen, nicht nur eine. Die Datei sagt in ihrer ersten Zeile,
#: wozu sie angelegt wurde — "Bereits im Besitz - die Autor:innen-Discovery
#: soll sie nicht wieder anbieten" —, und nach ADR 18 gelten mehrere
#: Beziehungen gleichzeitig. ``owned`` wegzulassen würde die einzige Auskunft
#: wegwerfen, die die Datei über das *Warum* macht, und die Leserin müsste
#: hinterher von Hand nachtragen, was schon dastand.
KINDS: tuple[RelationKind, ...] = (RelationKind.DISMISSED, RelationKind.OWNED)


@dataclass(frozen=True, slots=True)
class Dismissed:
    """Was nie wieder vorgeschlagen werden soll — aus den Beziehungen gelesen.

    Zwei Schlüssel, weil eine Ablehnung zwei Reichweiten hat: die Nummer trifft
    genau den Shop, von dem sie stammt, die ISBN trifft jede Quelle, die
    dieselbe Ausgabe führt. Ohne die ISBN wäre die Beziehung zwar am Buch
    gespeichert, würde aber weiterhin nur an einem Shop wirken — und das war
    der ganze Anlass (ADR 18).
    """

    items: frozenset[tuple[str, str]] = frozenset()
    isbns: frozenset[str] = frozenset()

    def covers(self, source: str, source_item_id: str, isbn: str | None = None) -> bool:
        if (source, source_item_id) in self.items:
            return True
        return bool(isbn) and isbn in self.isbns


def dismissed_books(store: Store, profile_slug: str) -> Dismissed:
    """Die aktiven ``dismissed``-Beziehungen als Nachschlagewerk für einen Lauf.

    Deaktivierte zählen nicht: eine zurückgenommene Ablehnung soll wieder
    vorgeschlagen werden dürfen — das ist der Sinn davon, sie zu deaktivieren
    statt sie zu löschen.
    """
    items, isbns = store.dismissed_keys(profile_slug)
    return Dismissed(items=frozenset(items), isbns=frozenset(isbns))


@dataclass(frozen=True, slots=True)
class Resolved:
    """Eine Produktnummer, die jetzt ein Buch ist."""

    source: str
    source_item_id: str
    book_id: int
    title: str
    author: str | None
    #: Ohne neue Anfrage erledigt, weil die Nummer schon einem Buch zugeordnet
    #: war. Ein zweiter Aufruf kostet den Shop damit gar nichts.
    already_known: bool = False


@dataclass(slots=True)
class ResolutionReport:
    resolved: list[Resolved] = field(default_factory=list)
    #: Was sich nicht auflösen ließ, im Klartext. Keine Ausnahme, sondern eine
    #: Frage an einen Menschen — und die einzige Zeile, bei der es etwas zu tun
    #: gibt.
    unresolved: list[str] = field(default_factory=list)
    #: Wie oft wirklich beim Shop nachgefragt wurde. Steht hier, weil
    #: Sparsamkeit bei den Anfragen eine Zusage ist und keine Absicht.
    requests: int = 0

    @property
    def needs_attention(self) -> bool:
        return bool(self.unresolved)


def _record(store: Store, profile_slug: str, book_id: int, now: datetime) -> None:
    """Die Beziehungen schreiben, ohne eine bestehende zu überfahren.

    ``put_relation`` setzt ``active`` immer auf wahr. Blind aufgerufen würde ein
    zweiter Durchgang also eine Ablehnung wiederbeleben, die die Leserin
    inzwischen zurückgenommen hat — deshalb wird nur ergänzt, was fehlt.
    """
    present = {relation.kind for relation in store.relations_of(profile_slug, book_id)}
    for kind in KINDS:
        if str(kind) not in present:
            store.put_relation(profile_slug, book_id, str(kind), now=now)


def resolve(
    store: Store,
    sources: Iterable[Source],
    dismissed: Mapping[str, Iterable[str]],
    *,
    profile_slug: str,
    now: datetime,
) -> ResolutionReport:
    """Jede übrig gebliebene Produktnummer einmal auflösen."""
    by_name = {source.name: source for source in sources}
    report = ResolutionReport()

    for source_name, item_ids in (dismissed or {}).items():
        for item_id in sorted(item_ids):
            known = store.book_by_source_item(source_name, item_id)
            if known is not None:
                book = store.book(known)
                _record(store, profile_slug, known, now)
                report.resolved.append(
                    Resolved(
                        source=source_name,
                        source_item_id=item_id,
                        book_id=known,
                        title=book.title if book else "",
                        author=book.author if book else None,
                        already_known=True,
                    )
                )
                continue

            source = by_name.get(source_name)
            if source is None:
                # Eine Quelle, die es nicht mehr gibt, kann nicht gefragt
                # werden — und raten wäre hier so falsch wie überall sonst.
                report.unresolved.append(
                    f"{source_name}:{item_id} — die Quelle {source_name!r} gibt es nicht mehr"
                )
                continue

            report.requests += 1
            item = source.item(item_id)
            if item is None:
                report.unresolved.append(
                    f"{source_name}:{item_id} — {source_name} kennt diese Nummer nicht mehr"
                )
                continue

            book = store.find_or_create_book(
                isbn=item.isbn, title=item.title, author=item.author, now=now
            )
            # Die Nummer wird mitgeschrieben, nicht nur die Adresse: sie ist
            # der Schlüssel, an dem ein Fund im nächsten Lauf wiedererkannt
            # wird, und ohne sie fragte dieser Weg jedes Mal neu beim Shop nach.
            store.put_book_source(
                book.id,
                source_name,
                outcome=str(LinkOutcome.CONFIRMED),
                url=item.url,
                source_item_id=item_id,
                resolved_at=now,
                reason="aus dismissed.yaml über die Produktnummer aufgelöst",
                matched_title=item.title,
                matched_author=item.author,
            )
            _record(store, profile_slug, book.id, now)
            report.resolved.append(
                Resolved(
                    source=source_name,
                    source_item_id=item_id,
                    book_id=book.id,
                    title=book.title,
                    author=book.author,
                )
            )
    return report
