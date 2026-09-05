"""Picking the right book out of a list of search hits.

Two decisions live here, and they are separate on purpose:

*Ranking* orders candidates by a lexicographic key — deterministic, no
weightings to tune, ties broken in a documented order (research doc §3).

*Confidence* then decides whether the winner may be used without a human ever
looking at it. v1 resolves entries automatically, so this gate is the only thing
standing between a loose search hit and a wrong title being watched for months
(ADR 9). It answers with three states, never a bare boolean.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from rapidfuzz import fuzz

from .bundles import looks_like_bundle
from .normalize import (
    NormalizedAuthor,
    normalize_authors,
    normalize_title,
    title_tokens,
    volumes_conflict,
)

#: Below this, nothing is a match.
NO_MATCH_BELOW = 85
#: At or above this, a fuzzy title is as good as an exact one.
STRONG_TITLE = 95
#: An author this close counts as the same person.
STRONG_AUTHOR = 90
#: Two candidates within this many points are effectively tied.
TIE_MARGIN = 3
#: Stands in for "no year on either side" so the tie-break stays sortable.
UNKNOWN_YEAR_DELTA = 9999


class Confidence(StrEnum):
    AUTO_ACCEPT = "auto_accept"
    PROVISIONAL = "provisional"
    NO_MATCH = "no_match"


@dataclass(frozen=True, slots=True)
class Query:
    """What we are looking for — normally a Watchlist Entry."""

    title: str
    author: str | None = None
    year: int | None = None
    identifier: str | None = None


@dataclass(frozen=True, slots=True)
class Candidate:
    """One search hit. ``payload`` carries whatever the Source needs back."""

    title: str
    author: str | None = None
    year: int | None = None
    identifier: str | None = None
    payload: Any = None


@dataclass(frozen=True, slots=True)
class Scored:
    candidate: Candidate
    id_match: bool
    title_exact: bool
    title_fuzzy: int
    author_exact: bool
    author_fuzzy: int
    year_delta: int
    source_rank: int
    #: Der gesuchte Titel steckt vollstaendig im Kandidaten — "Dark Matter" in
    #: "Dark Matter. Der Zeitenlaeufer". Ein eigenes Signal und nicht Teil von
    #: ``title_fuzzy``: es darf einen Kandidaten aus dem Nichts holen, aber nie
    #: allein eine Annahme tragen (Ticket 36).
    title_contained: bool = False
    #: Beide Seiten nennen einen Band, und einen verschiedenen — oder der
    #: Kandidat nennt einen spaeteren, wo die Anfrage keinen nennt.
    volume_conflict: bool = False
    #: Beide Seiten tragen eine Kennung, und eine verschiedene. Kein fehlendes
    #: Indiz, sondern ein **Widerspruch** — das Gegenstueck zu Primos negativem
    #: Gewicht (docs/research/title-matching-practices.md).
    id_conflict: bool = False
    #: Der Kandidat ist eine Sammelausgabe, die Anfrage nicht. Bisher waren
    #: "Der Kruzifix-Killer" und "Der Kruzifix-Killer / Der Vollstrecker"
    #: ununterscheidbar — beide exakter Titel, beide exakter Autor —, und wer
    #: gewann, entschied die Reihenfolge der Shop-Treffer (ADR 24).
    is_bundle: bool = False

    @property
    def sort_key(self) -> tuple[int, ...]:
        """Ascending = better. Fuzzy scores go in five-point buckets so that
        near-ties fall through to the next criterion instead of being decided by
        a point of noise."""
        return (
            0 if self.id_match else 1,
            0 if self.title_exact else 1,
            # Der gesuchte Einzelband schlaegt die Sammelausgabe: sie steht
            # nicht auf der Watchlist, und sie ist ein eigenes Buch (ADR 24).
            1 if self.is_bundle else 0,
            0 if self.title_contained else 1,
            -(self.title_fuzzy // 5),
            0 if self.author_exact else 1,
            -(self.author_fuzzy // 5),
            self.year_delta,
            self.source_rank,
        )


@dataclass(frozen=True, slots=True)
class Resolution:
    confidence: Confidence
    best: Scored | None = None
    ranked: tuple[Scored, ...] = field(default_factory=tuple)
    reason: str = ""

    @property
    def accepted(self) -> Candidate | None:
        if self.best is None or self.confidence is not Confidence.AUTO_ACCEPT:
            return None
        return self.best.candidate


def _author_scores(
    query_authors: Sequence[NormalizedAuthor], candidate_authors: Sequence[NormalizedAuthor]
) -> tuple[bool, int]:
    if not query_authors or not candidate_authors:
        return False, 0

    exact = any(q.full == c.full for q in query_authors for c in candidate_authors)
    best = max(
        max(
            fuzz.token_set_ratio(q.full, c.full),
            fuzz.token_set_ratio(q.substantial, c.substantial),
        )
        for q in query_authors
        for c in candidate_authors
    )
    return exact, int(round(best))


def title_similarity(left: str, right: str) -> int:
    """How alike two normalized titles are, 0–100.

    ``token_set_ratio`` alone is not enough: it scores a perfect 100 whenever one
    token set is a subset of the other, so "Der Schwarm" would happily accept
    "Der Schwarm 2 - Die Rückkehr". Taking the lower of it and
    ``token_sort_ratio`` keeps its tolerance for reordering and leftover subtitle
    words while still making extra tokens cost something.
    """
    return int(
        round(min(fuzz.token_set_ratio(left, right), fuzz.token_sort_ratio(left, right)))
    )


def title_is_contained(query: str, candidate: str) -> bool:
    """Steckt der gesuchte Titel vollstaendig im Titel des Kandidaten?

    Der Fall, den ``title_similarity`` nicht sehen kann: der Shop haengt einen
    Untertitel an den Titel, statt ihn in ein eigenes Feld zu schreiben —
    "Dark Matter. Der Zeitenlaeufer". Das Minimum aus Mengen- und Sortiermass
    bestraft jedes zusaetzliche Wort gleich hart, und der Titel faellt mit 56
    von noetigen 85 durch.

    Deshalb ein **eigenes Signal** statt einer gesenkten Schwelle. Es sagt nur,
    dass es sich lohnt hinzusehen; entschieden wird an anderer Stelle. Genau
    diese Trennung — billiger Kandidatenschluessel, teure Entscheidung — ist,
    was Primo und die Record-Linkage-Literatur empfehlen
    (docs/research/title-matching-practices.md).

    Ein Wort allein reicht nicht: von fuenfzehn Watchlist-Titeln haben
    dreizehn hoechstens zwei Token, und "Morgen" steckt in sehr vielen Titeln.
    """
    wanted = title_tokens(query)
    if not wanted:
        return False
    found = title_tokens(candidate)
    if len(found) <= len(wanted):
        return False
    return set(wanted).issubset(found)


def score(query: Query, candidate: Candidate, source_rank: int = 0) -> Scored:
    query_title = normalize_title(query.title)
    candidate_title = normalize_title(candidate.title)

    query_authors = normalize_authors(query.author)
    candidate_authors = normalize_authors(candidate.author)
    author_exact, author_fuzzy = _author_scores(query_authors, candidate_authors)

    if query.year is not None and candidate.year is not None:
        year_delta = abs(query.year - candidate.year)
    else:
        year_delta = UNKNOWN_YEAR_DELTA

    return Scored(
        candidate=candidate,
        id_match=bool(query.identifier) and query.identifier == candidate.identifier,
        title_exact=bool(query_title) and query_title == candidate_title,
        title_fuzzy=title_similarity(query_title, candidate_title),
        author_exact=author_exact,
        author_fuzzy=author_fuzzy,
        year_delta=year_delta,
        source_rank=source_rank,
        title_contained=title_is_contained(query.title, candidate.title),
        volume_conflict=volumes_conflict(query.title, candidate.title),
        is_bundle=looks_like_bundle(candidate.title) and not looks_like_bundle(query.title),
        id_conflict=bool(query.identifier)
        and bool(candidate.identifier)
        and query.identifier != candidate.identifier,
    )


def author_matches(target: str, credited: str | None, threshold: int = STRONG_AUTHOR) -> bool:
    """Is ``target`` one of the people credited on this item?

    Deliberately stricter than the author score used while ranking a title
    (:func:`_author_scores`). There the author only corroborates a title that
    already matched, so being generous costs little; here the author *is* the
    entire decision, and every false positive becomes a book recommendation for
    a stranger.

    Two traps, both found against real shop data:

    ``token_set_ratio`` alone scores a perfect 100 whenever one name's tokens
    are a subset of the other's, which makes "Chris Carter" match "Chris James
    Carter" and plain "Max" match "Max Barry". Taking the lower of it and
    ``token_sort_ratio`` makes the extra given name count against the match.

    And the initials-stripped variant is not consulted at all: it reduces
    "S.A. Barnes" and "J.S. Barnes" to the same bare "barnes", which would make
    every author sharing a surname the same person.
    """
    if not credited:
        return False
    targets = normalize_authors(target)
    credits = normalize_authors(credited)
    if not targets or not credits:
        return False

    for wanted in targets:
        for person in credits:
            if wanted.full == person.full:
                return True
            score = min(
                fuzz.token_set_ratio(wanted.full, person.full),
                fuzz.token_sort_ratio(wanted.full, person.full),
            )
            if score >= threshold:
                return True
    return False


def _is_tied(best: Scored, runner_up: Scored) -> bool:
    """Two hits we cannot honestly tell apart — the case Calibre punts to its GUI."""
    return (
        abs(best.title_fuzzy - runner_up.title_fuzzy) <= TIE_MARGIN
        and best.author_fuzzy // 5 == runner_up.author_fuzzy // 5
        and best.title_exact == runner_up.title_exact
        # Einzelband und Sammelausgabe sind nicht "gleich gut", sobald wir sie
        # auseinanderhalten koennen — genau das war vorher der Muenzwurf
        # (ADR 24).
        and best.is_bundle == runner_up.is_bundle
    )


def _confidence(query: Query, ranked: Sequence[Scored]) -> tuple[Confidence, str]:
    best = ranked[0]

    if best.id_match:
        return Confidence.AUTO_ACCEPT, "Kennung stimmt überein"

    if best.title_fuzzy < NO_MATCH_BELOW:
        # Der gesuchte Titel steckt ganz im gefundenen: das ist zu wenig fuer
        # eine Annahme und zu viel zum Wegwerfen. Es kommt der Leserin zur
        # Bestaetigung vor — ein Klick, und die Zuordnung heisst danach
        # "von Hand bestaetigt" (Ticket 36, ADR 9).
        if best.title_contained:
            return (
                Confidence.PROVISIONAL,
                "der gesuchte Titel steckt im gefundenen — bitte bestätigen",
            )
        return (
            Confidence.NO_MATCH,
            f"bester Titelwert {best.title_fuzzy} liegt unter {NO_MATCH_BELOW}",
        )

    # Ein anderer Band ist ein anderes Buch — aber nicht *kein* Buch. Bisher
    # wurde "Der Schwarm - Band 2" als "Der Schwarm" automatisch angenommen,
    # weil der Untertitel-Schnitt die Bandangabe entfernte, bevor sie jemand
    # sah. Jetzt kommt der Fall zur Bestaetigung statt durchzurutschen — und
    # nicht in den Papierkorb: wegwerfen hiesse, der Leserin einen Kandidaten
    # zu verschweigen, den nur sie beurteilen kann (ADR 9).
    #
    # Steht **nach** der Titelschwelle: sonst wuerde ein voellig fremdes Buch
    # mit einer 2 im Titel zum Kandidaten.
    if best.volume_conflict:
        return Confidence.PROVISIONAL, "der Treffer nennt einen anderen Band der Reihe"

    # Dieselbe Überlegung eine Stufe härter: eine abweichende ISBN ist kein
    # fehlendes Indiz, sondern ein Widerspruch. Bisher wog sie gar nichts — nur
    # eine *übereinstimmende* Kennung zählte, eine widersprechende nicht.
    if best.id_conflict:
        return Confidence.PROVISIONAL, "die Kennungen widersprechen sich"

    runner_up = ranked[1] if len(ranked) > 1 else None
    tied = runner_up is not None and _is_tied(best, runner_up)

    if query.author:
        confident = (best.title_exact and best.author_fuzzy >= STRONG_AUTHOR) or (
            best.title_fuzzy >= STRONG_TITLE and best.author_exact
        )
        if confident and tied:
            return Confidence.PROVISIONAL, "zwei Kandidaten sind gleich gut"
        if confident:
            return Confidence.AUTO_ACCEPT, "Titel und Autor stimmen beide"
        return (
            Confidence.PROVISIONAL,
            f"Titel {best.title_fuzzy}, Autor {best.author_fuzzy} — nicht eindeutig",
        )

    # No author to corroborate with: an exact, unrivalled title is the only
    # thing we will accept unattended.
    if best.title_exact and not tied:
        return (
            Confidence.AUTO_ACCEPT,
            "exakter Titel, kein konkurrierender Treffer, kein Autor angegeben",
        )
    return Confidence.PROVISIONAL, "kein Autor am Eintrag, mit dem sich der Titel bestätigen ließe"


def match(query: Query, candidates: Sequence[Candidate]) -> Resolution:
    """Rank ``candidates`` against ``query`` and say how much to trust the winner."""
    if not candidates:
        return Resolution(confidence=Confidence.NO_MATCH, reason="keine Kandidaten")

    ranked = tuple(
        sorted(
            (score(query, candidate, rank) for rank, candidate in enumerate(candidates)),
            key=lambda scored: scored.sort_key,
        )
    )
    confidence, reason = _confidence(query, ranked)
    return Resolution(
        confidence=confidence,
        best=ranked[0] if confidence is not Confidence.NO_MATCH else None,
        ranked=ranked,
        reason=reason,
    )
