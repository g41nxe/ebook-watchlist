"""Den engen Lauf anstoßen und sagen, wo er steht (Ticket 51).

Ein Faden, kein Prozess: gemessen dauert ein enger Lauf mit bekannter Adresse
**2,1 s**, und ein eigener Prozess käme mit rund einer Sekunde Python-Hochlauf
dazu — die Hälfte der Arbeit nochmal, für einen Vorgang, dessen ganzer Zweck
die sofortige Rückmeldung ist. ``uvicorn`` läuft ohne ``workers``, Zustand im
Speicher ist damit sicher.

Nebenläufiges Schreiben ist unkritisch: ``journal_mode=WAL`` und
``busy_timeout=15000`` stehen in :class:`~ebook_watchlist.store.Store` bereits.

Nachgefragt wird über htmx, genau wie beim großen Lauf (``_run_panel.html``):
der Trigger steht nur dran, solange etwas läuft, also hört die Seite von
selbst auf zu fragen. Kein Websocket (ADR 3).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime

from ..single import Report, check_one

#: Nach so langer Ruhe wird ein fertiger Zustand vergessen. Lang genug, dass
#: die Seite ihn sicher einmal abgeholt hat, kurz genug, dass die Ablage nicht
#: unbegrenzt waechst.
FORGET_AFTER_SECONDS = 300


@dataclass(frozen=True, slots=True)
class Check:
    """Wo der enge Lauf zu einem Eintrag gerade steht."""

    book_id: int
    started_at: datetime
    #: ``None``, solange er laeuft.
    report: Report | None = None
    finished_at: datetime | None = None

    @property
    def busy(self) -> bool:
        return self.report is None

    @property
    def trouble(self) -> str:
        return self.report.trouble if self.report else ""

    def label(self, *, now: datetime) -> str:
        """Was in der Zeile steht.

        Zwei Zustaende, nicht einer: ein enger Lauf, der auf einen grossen
        wartet, sieht sonst aus wie einer, der schon sucht — und wartet unter
        Umstaenden Minuten.
        """
        if self.report is not None:
            return self.report.trouble or "fertig"
        # Nach den gemessenen 2,1 s ist ein enger Lauf durch. Dauert es
        # laenger, haelt ein grosser Lauf die Sperre.
        return "sucht …" if (now - self.started_at).total_seconds() < 5 else "wartet …"


class Rechecker:
    """Haelt die laufenden engen Laeufe — einer je Buch.

    Eine Instanz je Anwendung und kein Modul-Global, damit der Zustand eines
    Tests nicht in den naechsten leckt — dieselbe Ueberlegung wie bei
    :class:`~ebook_watchlist.web.runs.RunLauncher`.
    """

    def __init__(self) -> None:
        self._checks: dict[int, Check] = {}
        self._guard = threading.Lock()

    def start(self, book_id: int, *, now: datetime | None = None) -> Check:
        """Anstossen, falls fuer dieses Buch nicht schon etwas laeuft."""
        now = now or datetime.now()
        with self._guard:
            self._forget_old(now)
            laufend = self._checks.get(book_id)
            if laufend is not None and laufend.busy:
                return laufend
            self._checks[book_id] = Check(book_id=book_id, started_at=now)
        threading.Thread(target=self._work, args=(book_id,), daemon=True).start()
        return self._checks[book_id]

    def state(self, book_id: int) -> Check | None:
        """Wo dieser eine Lauf steht — ``None``, wenn keiner bekannt ist."""
        with self._guard:
            return self._checks.get(book_id)

    def _work(self, book_id: int) -> None:
        try:
            report = check_one(book_id)
        except Exception as exc:  # noqa: BLE001 - ein Faden darf nichts mitreissen
            report = Report(trouble=f"{type(exc).__name__}: {exc}")
        with self._guard:
            vorher = self._checks.get(book_id)
            if vorher is not None:
                self._checks[book_id] = Check(
                    book_id=book_id,
                    started_at=vorher.started_at,
                    report=report,
                    finished_at=datetime.now(),
                )

    def _forget_old(self, now: datetime) -> None:
        self._checks = {
            key: check
            for key, check in self._checks.items()
            if check.busy
            or check.finished_at is None
            or (now - check.finished_at).total_seconds() < FORGET_AFTER_SECONDS
        }
