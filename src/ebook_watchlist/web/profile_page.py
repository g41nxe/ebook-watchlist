"""Was das Werkzeug über die Leserin zu wissen glaubt (Ticket 09).

Ausdrücklich **nur lesend**. Der Maßstab liegt als Repo-Datei mit eigenem
Änderungsverfahren und einer asymmetrischen Beweislast (ADR 17): ein Formular
hier würde genau dieses Verfahren umgehen. Die Seite zeigt ihn, verlinkt ihn
und nennt den Weg, auf dem er sich ändert.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..config import Profile
from ..rating import RUBRIC_PATH, RatingUnavailable, load_rubric
from ..reasons import thema_name
from ..relations import InterestKey, RelationKind
from ..store import Store

#: Wie oft der lange Ausläufer gefegt wird — dieselbe Frist, die der Lauf
#: benutzt. Hier nur zur Anzeige.
EXTENDED_SWEEP_KEY = "last_extended_sweep"
SWEEP_INTERVAL = timedelta(days=7)

_WEEKDAYS = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")

_RELATION_LABELS: tuple[tuple[str, str], ...] = (
    (str(RelationKind.WATCHING), "beobachtet"),
    (str(RelationKind.OWNED), "besessen"),
    (str(RelationKind.LIKED), "gefiel"),
    (str(RelationKind.DISLIKED), "gefiel nicht"),
    (str(RelationKind.DISMISSED), "verworfen"),
)


def _details(row) -> dict:
    try:
        return json.loads(row.details or "{}")
    except (TypeError, ValueError):  # pragma: no cover - defekte Zeile
        return {}


@dataclass(frozen=True, slots=True)
class Interest:
    value: str
    label: str
    tier: str
    active: bool

    @property
    def weekly(self) -> bool:
        return self.tier == "extended"


@dataclass(frozen=True, slots=True)
class Overview:
    authors: tuple[Interest, ...]
    themen: tuple[Interest, ...]
    counts: tuple[tuple[str, int], ...]
    strong_deal: str
    deal: str
    min_discount: int
    sweep_weekday: str
    last_sweep: datetime | None
    no_gos: tuple[str, ...]
    rubric: str | None
    rubric_version: int | None
    rubric_path: str

    @property
    def next_sweep(self) -> str:
        """Wann der wöchentliche Durchgang wieder ansteht.

        Ein Lauf, der nie stattfand, darf keine ganze Woche kosten — deshalb
        ist ein überfälliger Sweep sofort fällig, nicht erst am Wochentag
        (ADR 4). Die Anzeige sagt das genauso.
        """
        if self.last_sweep is None:
            return "beim nächsten Lauf"
        due = self.last_sweep + SWEEP_INTERVAL
        if due <= datetime.now():
            return "überfällig — beim nächsten Lauf"
        return f"{self.sweep_weekday}, frühestens {due:%d.%m.}"


def _money(cents: int) -> str:
    return f"{cents / 100:.2f} €".replace(".", ",")


def build(store: Store, profile: Profile) -> Overview:
    rows = store.interests(profile.slug, active_only=False)

    def collect(key: InterestKey) -> tuple[Interest, ...]:
        return tuple(
            Interest(
                value=row.value,
                label=thema_name(row.value) or row.value
                if key is InterestKey.THEMA
                else row.value,
                tier=_details(row).get("tier", "core"),
                active=row.active,
            )
            for row in rows
            if row.key == key
        )

    counts = tuple(
        (label, len(store.relations(profile.slug, kind=kind)))
        for kind, label in _RELATION_LABELS
    )

    try:
        rubric, version = load_rubric()
    except RatingUnavailable:
        rubric, version = None, None

    return Overview(
        authors=collect(InterestKey.AUTHOR),
        themen=collect(InterestKey.THEMA),
        counts=counts,
        strong_deal=_money(profile.strong_deal_max_cents),
        deal=_money(profile.deal_max_cents),
        min_discount=profile.min_discount_pct,
        sweep_weekday=_WEEKDAYS[profile.extended_sweep_weekday % 7],
        last_sweep=store.get_state(profile.slug, EXTENDED_SWEEP_KEY),
        no_gos=tuple(profile.no_gos),
        rubric=rubric,
        rubric_version=version,
        rubric_path=str(RUBRIC_PATH.name),
    )
