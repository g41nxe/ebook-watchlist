"""Die Startseite (Issue #5).

Was die Leserin jeden Tag zuerst sieht: ob das Werkzeug gelaufen ist, was
sich davon jetzt lohnt, und worüber sie entscheiden soll. Alles kommt aus dem
Store — der Tagesbericht wird nicht ein zweites Mal abgelegt, er ist eine
Darstellung dieser Daten, keine Quelle (docs/research/startseite-tracking-
werkzeuge.md, docs/reviews/design-review-2026-09-09.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..config import Profile
from ..store import Store
from . import triage, watchlist
from .triage import Suggestion
from .watchlist import Entry

#: Fünf Angebote und zwei Vorschläge. StoryGraph und BookWyrm ziehen bei fünf
#: dieselbe Linie; zwei Entscheidungen halten den Knopfblock lesbar. Der Rest
#: hängt am Link darunter, nicht an einer längeren Liste.
OFFERS = 5
SUGGESTIONS = 2

#: Ein Zeichen je Entscheidung, aus dem Sprite in ``base.html``. ``ic-play``
#: heißt in der Watchlist-Zeile "aktivieren" — dasselbe wie hier.
ICONS: dict[str, str] = {
    "dismissed": "ic-x",
    "owned": "ic-user",
    "watching": "ic-play",
}

#: Die drei Verkaufsargumente aus der README — nur im Leerzustand. Wer die
#: Seite täglich öffnet, kennt sie; wer sie zum ersten Mal öffnet, hat sonst
#: nichts zu sehen. Die Bilder dazu kommen aus Issue #3.
ARGUMENTS: tuple[tuple[str, str, str], ...] = (
    (
        "ic-star",
        "Jeder Stern hat einen Grund",
        "Ein Sprachmodell liest jeden Fund und schreibt in einem Satz, ob er zu dir passt.",
    ),
    (
        "ic-lib",
        "Zwei Quellen, eine Zeile",
        "Bibliothek und Shop für jeden Titel gleichzeitig — Preis hier, Verfügbarkeit dort.",
    ),
    (
        "ic-clock",
        "Der ganze Verlauf",
        "Jede Beobachtung wird angehängt, nie überschrieben.",
    ),
)


@dataclass(frozen=True, slots=True)
class Status:
    """Der letzte abgeschlossene Lauf, so wie die Statuszeile ihn braucht."""

    finished_at: datetime
    delta_count: int
    error: str | None
    now: datetime

    @property
    def when(self) -> str:
        """Dasselbe Format wie überall: Tag und Uhrzeit, kein Jahr, keine Sekunden."""
        return f"{self.finished_at:%d.%m. %H:%M}"

    @property
    def age_days(self) -> int:
        return (self.now - self.finished_at).days

    @property
    def stale(self) -> bool:
        """Ein Tageslauf, der einen Tag fehlt, ist eine Nachricht — keine Zahl."""
        return self.age_days >= 1

    @property
    def failed(self) -> bool:
        return bool(self.error)


@dataclass(frozen=True, slots=True)
class HomeView:
    status: Status | None
    #: Schnäppchen zuerst, das günstigste vorn, dann Ausleihbares.
    offers: tuple[Entry, ...]
    offers_total: int
    watchlist_total: int
    suggestions: tuple[Suggestion, ...]
    suggestions_total: int

    @property
    def first_run(self) -> bool:
        """Noch kein Lauf zu Ende — die Seite erklärt sich, statt Nullen zu zeigen."""
        return self.status is None


def build(store: Store, profile: Profile, *, now: datetime) -> HomeView:
    entries = watchlist.entries(store, profile, include_paused=False)
    offers = [entry for entry in entries if entry.deal or entry.borrowable]
    # Preis nur beim Schnäppchen ein Kriterium: ein ausleihbarer Titel ohne
    # Shop-Preis darf nicht zwischen zwei Preisen einsortiert werden.
    offers.sort(
        key=lambda entry: (
            not entry.deal,
            entry.latest.price_cents if entry.deal and entry.latest else 0,
            entry.title.casefold(),
        )
    )
    pile = triage.pending(store, profile, limit=SUGGESTIONS)
    return HomeView(
        status=_status(store, profile.slug, now),
        offers=tuple(offers[:OFFERS]),
        offers_total=len(offers),
        watchlist_total=len(entries),
        suggestions=pile.items,
        suggestions_total=pile.total,
    )


def _status(store: Store, profile_slug: str, now: datetime) -> Status | None:
    # Der jüngste *abgeschlossene* Rundgang. Ein Lauf, der gerade läuft oder
    # abgeschossen wurde, hat kein Ende — über den spricht die Übersicht.
    for run in store.recent_runs(profile_slug, limit=5):
        if run.finished_at is not None:
            return Status(run.finished_at, run.delta_count or 0, run.error, now)
    return None
