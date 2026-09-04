"""Wer den Stapel erreicht — und wer nicht (ADR 19, Ticket 12).

Das Tor sitzt zwischen der Meldelogik und dem Digest. Es läuft **nach** dem
Snapshot: ein Ausfall kostet damit ein Urteil, nie Geschichte. Und es läuft
**nach** der Preisregel, weil ein Buch zu bewerten, das ohnehin niemand zu
sehen bekommt, Verschwendung wäre.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .models import Delta, DeltaKind, MatchReason, Observation
from .rating import Rater, Rating, RatingUnavailable
from .ratings import BY_CONVERSATION, BY_MODEL, BY_READER, book_subject, subject_of
from .store import Store


def _judgement(store: Store, observation: Observation, subject: str, rubric_version: int):
    """Das Urteil, das für diesen Fund schon vorliegt — Mensch vor Maschine.

    Was die Leserin selbst gesagt hat, schlägt jedes Modellurteil und verfällt
    auch nicht mit einer neuen Maßstabsversion (ADR 17). Ihre Sterne und die
    aus dem Gespräch hängen am *Buch*, nicht am Fund: sie hat sie auf der
    Buchseite vergeben, und sie sollen gelten, egal über welche Quelle das Buch
    das nächste Mal hereinkommt. Nur das Tor selbst schlüsselt am Fund.
    """
    if observation.book_id is not None:
        of_book = book_subject(observation.book_id)
        for origin in (BY_READER, BY_CONVERSATION):
            stored = store.rating(of_book, rubric_version, origin=origin)
            if stored is not None:
                return stored
    return store.rating(subject, rubric_version, origin=BY_MODEL)


@dataclass(slots=True)
class GateReport:
    """Was das Tor getan hat.

    Der Digest nennt die Zahlen, damit ein zu scharf gesetzter Schwellwert und
    ein aufgebrauchtes Budget sichtbar sind statt still zu wirken (ADR 19).
    """

    held_back: int = 0
    rated: int = 0
    reused: int = 0
    unrated: int = 0
    #: Über dem Budget und deshalb ungefragt durchgelassen — unbewertet und
    #: gezeigt, nie verworfen.
    over_budget: int = 0
    #: Das Urteil zu jedem durchgelassenen Fund, am Schlüssel der Beobachtung.
    #: Der Digest zeigt es: die Begründung ist der Grund, den ein Vorschlag
    #: mitbringt (ADR 19, Ticket 14).
    judgements: dict[tuple[str, str], Rating] = field(default_factory=dict)

    @property
    def calls(self) -> int:
        return self.rated


def unrated_report(deltas: list[Delta]) -> GateReport:
    """Der Bericht für einen Lauf ohne Tor.

    Eine Stelle für beide Wege dorthin — der Lauf zählte hier einmal *jedes*
    Delta als unbewertet, auch Watchlist-Titel, die das Tor nie beurteilt
    (Ticket 20).
    """
    return GateReport(unrated=sum(1 for delta in deltas if _is_discovery(delta)))


def apply(
    deltas: list[Delta],
    *,
    store: Store,
    rater: Rater | None,
    rubric_version: int,
    threshold: int,
    budget: int,
    now: datetime,
) -> tuple[list[Delta], GateReport]:
    """Entdeckungen unter dem Schwellwert aussortieren.

    Ohne Bewerter passiert nichts — das ist der Zustand ohne Schlüssel, und er
    ist ausdrücklich erlaubt: gezeigt wird dann alles, was die Preisregel
    durchgelassen hat.

    ``budget`` begrenzt die *Aufrufe* eines Laufs. Der erste Lauf mit einem
    Schlüssel trifft einen Rückstand von dreihundert Entdeckungen, und die alle
    am Stück abzufeuern widerspräche derselben Zurückhaltung, die jede andere
    ausgehende Anfrage in diesem Projekt bindet (ADR 7). Ein gespeichertes
    Urteil kostet nichts und zählt deshalb nicht mit.
    """
    report = GateReport()
    if rater is None:
        return deltas, unrated_report(deltas)

    kept: list[Delta] = []
    for delta in deltas:
        if delta.current.match_reason is MatchReason.WATCHLIST:
            # Von der Leserin selbst gewaehlt; sie gegen ihr eigenes Profil
            # abzulehnen waere anmassend.
            kept.append(delta)
            continue

        subject = subject_of(delta.current)

        if delta.kind is not DeltaKind.FIRST_SEEN:
            # Ein Preissturz kostet nie ein neues Urteil — aber das vorhandene
            # gilt weiter. Vorher lief er am Tor vorbei, und ein Buch, das mit
            # einem Stern zurueckgehalten worden war, meldete sich beim
            # naechsten Nachlass doch: streng an der Vordertuer, offen an der
            # Hintertuer.
            stored = _judgement(store, delta.current, subject, rubric_version)
            if stored is None:
                kept.append(delta)
            elif stored.stars < threshold:
                report.held_back += 1
            else:
                report.reused += 1
                report.judgements[delta.current.key] = Rating(
                    stars=stored.stars,
                    reason=stored.reason,
                    confidence=stored.confidence,
                    rubric_version=stored.rubric_version,
                )
                kept.append(delta)
            continue

        # Ein vorhandenes Urteil - auch das der Leserin - erspart den Aufruf.
        stored = _judgement(store, delta.current, subject, rubric_version)
        if stored is not None:
            report.reused += 1
            rating = Rating(
                stars=stored.stars,
                reason=stored.reason,
                confidence=stored.confidence,
                rubric_version=stored.rubric_version,
            )
        elif report.rated + report.unrated >= budget:
            # Budget aufgebraucht: der Rest wartet auf den naechsten Lauf und
            # wird solange gezeigt. Uebersprungen heisst unbewertet, nicht
            # aussortiert — sonst verschluckte ausgerechnet das Sparen die
            # Neuzugaenge.
            #
            # Gezaehlt werden *Versuche*, nicht Urteile: ein totes Netz haette
            # sonst dreihundert vergebliche Anfragen am Stueck gekostet, also
            # genau den Ausbruch, den das Budget verhindern soll.
            report.over_budget += 1
            kept.append(delta)
            continue
        else:
            try:
                rating = rater.rate(delta.current)
            except RatingUnavailable:
                # Kein Schlüssel, kein Netz, unlesbare Antwort: das Buch bleibt
                # unbewertet und wird trotzdem gezeigt. Ein Tor, das im Zweifel
                # schliesst, verschluckt Neuzugaenge stillschweigend.
                report.unrated += 1
                kept.append(delta)
                continue
            report.rated += 1
            store.put_rating(
                subject,
                stars=rating.stars,
                confidence=rating.confidence,
                reason=rating.reason,
                rubric_version=rating.rubric_version,
                now=now,
                origin=BY_MODEL,
            )

        if rating.passes(threshold):
            report.judgements[delta.current.key] = rating
            kept.append(delta)
        else:
            report.held_back += 1
    return kept, report


def _is_discovery(delta: Delta) -> bool:
    """Die Erstsichtung einer Entdeckung — das, wofür ein Modell gefragt wird.

    Ein Watchlist-Titel wurde von der Leserin selbst gewählt; ihn gegen ihr
    eigenes Profil abzulehnen wäre anmassend. Ein Preissturz wird ebenfalls
    nicht *bewertet* — aber er wird sehr wohl am vorhandenen Urteil gemessen,
    und das tut :func:`apply` an seiner eigenen Stelle.
    """
    return (
        delta.kind is DeltaKind.FIRST_SEEN
        and delta.current.match_reason is not MatchReason.WATCHLIST
    )
