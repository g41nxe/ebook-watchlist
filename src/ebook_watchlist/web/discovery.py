"""Die Seite zu einem Fund (Issue #9).

Ein unentschiedener Fund hat keine Buch-Zeile — ADR 18 legt sie erst an, wenn
die Leserin etwas über ihn gesagt hat. Er hat aber alles andere: Titel, Autor,
Klappentext, den Anlass, das Urteil des Bewertungstors und eine Geschichte über
mehrere Läufe. Diese Seite ist deshalb die Buchseite ohne die Teile, die es
noch nicht gibt, und der einzige Ort, an dem die **Begründung** des Tors
ausgeschrieben steht (ADR 19 wollte sie nachprüfbar machen; der Stapel zeigt
nur den Pitch).

Sie baut auf denselben Bausteinen wie ``book.py`` — ``Sighting``, ``Judgement``,
``Origin`` und deren Erzeuger —, damit dieselbe Auskunft nicht zweimal
verschieden entsteht.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Profile
from ..deals import is_strong_deal
from ..reasons import thema_name
from ..sources import registry
from ..store import Store
from .book import _AVAILABILITY, Judgement, Origin, Sighting, _judgements, _origin, _price
from .triage import _cover_file


@dataclass(frozen=True, slots=True)
class Page:
    """Was die Seite über einen Fund weiß."""

    source: str
    source_item_id: str
    title: str
    author: str | None
    series: str | None
    isbn: str | None
    cover_file: str | None
    blurb: str | None
    #: Die Quelle, die ihn gefunden hat — Name, Art und Adresse dort.
    source_label: str
    source_category: str
    url: str | None
    origin: Origin | None
    judgements: tuple[Judgement, ...]
    history: tuple[Sighting, ...]
    thema: str | None
    deal: bool

    @property
    def key(self) -> str:
        """Was die Entscheidungs-Formulare schicken — Quelle und Nummer, denn
        eine Buch-Nummer gibt es noch nicht."""
        return f"{self.source}:{self.source_item_id}"

    @property
    def price(self) -> str | None:
        return self.history[0].price if self.history else None

    @property
    def seen_count(self) -> int:
        return len(self.history)


def build(store: Store, profile: Profile, source: str, item_id: str) -> Page | None:
    """Die Seite zu einem Fund, oder ``None``, wenn ihn nie jemand gesehen hat."""
    seen = store.observations_for_item(profile.slug, source, item_id)
    if not seen:
        return None

    newest = seen[0]
    history = tuple(
        Sighting(
            when=observation.observed_at,
            source=registry.label(profile, observation.source),
            price=_price(observation.price_cents),
            availability=_AVAILABILITY.get(observation.availability)
            if observation.availability
            else None,
            # Ein Titel, der sich unter derselben Nummer ändert, heißt: die
            # Quelle hat die Ausgabe getauscht. Das ist eine Auskunft, keine
            # Kleinigkeit (ADR 18) — deshalb steht sie in der Zeile.
            other_title=(
                observation.title
                if observation.title.strip() != newest.title.strip()
                else None
            ),
            deal=is_strong_deal(observation.price_cents, profile),
        )
        for observation in seen
    )

    return Page(
        source=source,
        source_item_id=item_id,
        title=newest.title,
        author=newest.author,
        series=newest.series,
        isbn=newest.isbn,
        cover_file=_cover_file(newest),
        blurb=newest.blurb,
        source_label=registry.label(profile, source),
        source_category=registry.category(profile, source),
        url=newest.url,
        origin=_origin(seen),
        judgements=_judgements(store, None, seen, isbn=newest.isbn),
        history=history,
        thema=thema_name(newest.category),
        deal=is_strong_deal(newest.price_cents, profile),
    )
