"""Der Vorschlagsstapel (Ticket 08).

Das ist der Vorgang, den ein Gespräch am schlechtesten kann — zwanzig Titel
einzeln diktiert — und ein Formular am besten.

Eine Entscheidung wirkt **buchweit**, nicht auf eine Produktnummer. Die alte
``dismissed.yaml`` konnte nur "dieser Shop soll das nicht mehr zeigen"; dasselbe
Buch bei der Onleihe wäre trotzdem wieder aufgetaucht (ADR 18).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..config import Profile
from ..deals import is_strong_deal
from ..diff import worth_announcing
from ..junk import is_junk
from ..models import MatchReason, Observation
from ..ratings import BY_MODEL, subject_of
from ..reasons import short_why, thema_name, why_shown
from ..relations import RelationKind
from ..sources import registry
from ..store import Store

#: Was mit einem Stapel geschehen kann. Alle drei schreiben eine Beziehung —
#: "verworfen" ist keine Löschung, sondern eine Aussage über das Buch.
ACTIONS: tuple[tuple[str, str], ...] = (
    (str(RelationKind.DISMISSED), "Verwerfen"),
    (str(RelationKind.OWNED), "Habe ich"),
    (str(RelationKind.WATCHING), "Beobachten"),
)

#: Wie viele Zeilen eine Seite zeigt. Der Rückstand ist dreistellig, und eine
#: Seite mit dreihundert Einträgen ist keine Aufgabe, sondern eine Strafe —
#: der eigentliche Schnitt kommt aber vom Bewertungstor (ADR 19), nicht hier.
#:
#: Zehn, nicht fünfzig: solange der Stapel aus einem einmaligen Rückstand
#: besteht, den das Tor ohnehin neu erzeugt, ist eine kurze Liste billiger —
#: gezeigt wird nur, was auch bewertet werden muss.
PAGE_SIZE = 10


@dataclass(frozen=True, slots=True)
class Suggestion:
    source: str
    source_item_id: str
    title: str
    author: str | None
    blurb: str | None
    url: str | None
    isbn: str | None
    price_cents: int | None
    thema: str | None
    reason: MatchReason
    deal: bool
    source_label: str
    source_category: str
    #: Warum dieser Fund hier steht — in denselben Worten wie im Digest, aus
    #: einer Stelle (Ticket 14).
    why: str
    why_short: str
    #: Was das Bewertungstor von dem Buch hält — ``None``, solange es nicht
    #: gelaufen ist.
    stars: int | None = None
    #: Ein Satz, warum das Buch in Frage kommt. Steht hier **statt** des
    #: Klappentexts: der sagt, wovon das Buch handelt, der Pitch sagt, warum es
    #: für diese Leserin zählt (bewertungsschema.yaml).
    pitch: str | None = None

    @property
    def key(self) -> str:
        """Was im Formular steht. Quelle und Nummer, nicht die Buch-Id — ein
        Buch gibt es zu diesem Fund ja noch gar nicht."""
        return f"{self.source}:{self.source_item_id}"

    @property
    def price(self) -> str | None:
        if self.price_cents is None:
            return None
        return f"{self.price_cents / 100:.2f} €".replace(".", ",")


@dataclass(frozen=True, slots=True)
class Pile:
    items: tuple[Suggestion, ...]
    #: Wie viele es insgesamt sind, auch wenn die Seite weniger zeigt.
    total: int
    hidden_junk: int
    #: Weder Schnäppchen noch ausleihbar — würde nie gemeldet, steht also auch
    #: nicht im Stapel. Verschwunden ist nichts: fällt der Preis, ist das Buch
    #: wieder da (ADR 19).
    hidden_priced: int = 0

    @property
    def is_empty(self) -> bool:
        return not self.items


def _suggestion(
    observation: Observation, profile: Profile, judgement=None
) -> Suggestion:
    return Suggestion(
        source=observation.source,
        source_item_id=observation.source_item_id,
        title=observation.title,
        author=observation.author,
        blurb=observation.blurb,
        url=observation.url,
        isbn=observation.isbn,
        price_cents=observation.price_cents,
        thema=thema_name(observation.category),
        reason=observation.match_reason,
        deal=is_strong_deal(observation.price_cents, profile),
        source_label=registry.label(profile, observation.source),
        source_category=registry.category(profile, observation.source),
        why=why_shown(observation),
        why_short=short_why(observation),
        stars=judgement.stars if judgement else None,
        pitch=(judgement.pitch or None) if judgement else None,
    )


def pending(
    store: Store,
    profile: Profile,
    *,
    reason: str | None = None,
    limit: int = PAGE_SIZE,
) -> Pile:
    """Die Funde, zu denen noch nichts gesagt wurde.

    Entschieden ist ein Fund, sobald es ein Buch mit einer Beziehung gibt, das
    diese Quelle unter dieser Nummer führt — oder das dieselbe ISBN trägt. Der
    zweite Weg ist der Grund, warum eine Entscheidung bei *jeder* Quelle wirkt.
    """
    decided_items = store.decided_items(profile.slug)
    decided_isbns = set(store.books_with_relations(profile.slug))
    found = store.latest_discoveries(profile.slug)
    # Ein Zugriff für den ganzen Stapel, nicht einer je Zeile.
    judgements = store.ratings_for(subject_of(observation) for observation in found)

    items: list[Suggestion] = []
    hidden_junk = 0
    hidden_priced = 0
    for observation in found:
        if (observation.source, observation.source_item_id) in decided_items:
            continue
        if observation.isbn and observation.isbn in decided_isbns:
            continue
        if is_junk(observation):
            hidden_junk += 1
            continue
        # Dieselbe Regel wie im Digest, aus einer Stelle: was dich nie
        # erreichen würde, ist keine Aufgabe. Und was hier nicht steht, kostet
        # weder eine Anfrage für den Klappentext noch ein Urteil.
        if not worth_announcing(observation, profile):
            hidden_priced += 1
            continue
        if reason and str(observation.match_reason) != reason:
            continue
        items.append(
            _suggestion(
                observation,
                profile,
                judgements.get((subject_of(observation), BY_MODEL)),
            )
        )

    # Das Beste zuerst. Ohne das stehen oben die Funde, die zufaellig zuletzt
    # gesehen wurden — und der Stapel faengt mit dem an, was das Profil gerade
    # abgelehnt hat. Unbewertetes kommt ans Ende: es ist keine Empfehlung,
    # sondern eine offene Frage.
    items.sort(key=lambda item: (item.stars is not None, item.stars or 0), reverse=True)

    return Pile(
        items=tuple(items[:limit]),
        total=len(items),
        hidden_junk=hidden_junk,
        hidden_priced=hidden_priced,
    )


def decide(
    store: Store,
    profile: Profile,
    keys: list[str],
    kind: str,
    *,
    now: datetime,
) -> int:
    """Eine Entscheidung auf mehrere Funde anwenden.

    Jeder Fund wird zu einem Buch — gegen vorhandene Bücher geprüft, bevor ein
    neues entsteht (ADR 18) — und bekommt die Beziehung. Die Verknüpfung zur
    Quelle wird mitgeschrieben, damit derselbe Fund beim nächsten Lauf nicht
    wieder im Stapel steht.
    """
    wanted = set(keys)
    if not wanted:
        return 0

    by_key = {
        f"{observation.source}:{observation.source_item_id}": observation
        for observation in store.latest_discoveries(profile.slug)
    }

    decided = 0
    for key in wanted:
        observation = by_key.get(key)
        if observation is None:
            continue
        book = store.find_or_create_book(
            isbn=observation.isbn,
            title=observation.title,
            author=observation.author,
            series=observation.series,
            now=now,
        )
        store.put_relation(profile.slug, book.id, kind, now=now)
        store.put_book_source(
            book.id,
            observation.source,
            outcome="confirmed",
            url=observation.url,
            source_item_id=observation.source_item_id,
            resolved_at=now,
            reason="aus der Triage",
        )
        decided += 1
    return decided
