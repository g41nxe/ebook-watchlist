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
from .rating import BATCH_SIZE, VERMUTET, Rater, Rating, rate_in_batches
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
    #: Unter dem Schwellwert, aber nur vermutet — und deshalb gezeigt statt
    #: zurückgehalten (bewertungsschema.md, 3).
    shown_unsure: int = 0
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

    ``budget`` begrenzt die *Bücher* eines Laufs, nicht die Aufrufe. Der erste
    Lauf trifft einen Rückstand von dreihundert Entdeckungen, und die alle am
    Stück abzufeuern widerspräche derselben Zurückhaltung, die jede andere
    ausgehende Anfrage in diesem Projekt bindet (ADR 7). Ein gespeichertes
    Urteil kostet nichts und zählt deshalb nicht mit.
    """
    report = GateReport()
    if rater is None:
        return deltas, unrated_report(deltas)

    # Erst sammeln, wer ein frisches Urteil braucht, dann gebündelt fragen.
    # Einzeln zu fragen schickte den Maßstab je Buch erneut mit — und er ist
    # der weitaus größte Teil des Prompts (Ticket 12).
    #
    # Das Budget zählt weiterhin *Bücher*, nicht Aufrufe: sonst hiesse "40"
    # plötzlich achthundert.
    wanted = [
        delta.current
        for delta in deltas
        if _is_discovery(delta)
        and _judgement(store, delta.current, subject_of(delta.current), rubric_version) is None
    ][:budget]
    fresh = rate_in_batches(rater, wanted, size=BATCH_SIZE) if wanted else {}
    attempted = {observation.key for observation in wanted}

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
            elif stored.stars < threshold and stored.confidence != VERMUTET:
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
        elif delta.current.key not in attempted:
            # Ueber dem Budget und deshalb gar nicht erst gefragt: der Rest
            # wartet auf den naechsten Lauf und wird solange gezeigt.
            # Uebersprungen heisst unbewertet, nicht aussortiert — sonst
            # verschluckte ausgerechnet das Sparen die Neuzugaenge.
            report.over_budget += 1
            kept.append(delta)
            continue
        else:
            judged = fresh.get(delta.current.key)
            if judged is None:
                # Gefragt, aber ohne Antwort: kein Schluessel, kein Netz, eine
                # unlesbare Zeile im Buendel. Das Buch bleibt unbewertet und
                # wird trotzdem gezeigt — ein Tor, das im Zweifel schliesst,
                # verschluckt Neuzugaenge stillschweigend.
                report.unrated += 1
                kept.append(delta)
                continue
            rating = judged
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

        if rating.withholds(threshold):
            report.held_back += 1
        else:
            if not rating.passes(threshold):
                # Zu schwach, aber nur vermutet: gezeigt und mitgezählt, damit
                # es im Digest steht statt still zu wirken.
                report.shown_unsure += 1
            report.judgements[delta.current.key] = rating
            kept.append(delta)
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
