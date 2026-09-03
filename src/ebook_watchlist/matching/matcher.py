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

from .normalize import NormalizedAuthor, normalize_authors, normalize_title

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

    @property
    def sort_key(self) -> tuple[int, int, int, int, int, int, int]:
        """Ascending = better. Fuzzy scores go in five-point buckets so that
        near-ties fall through to the next criterion instead of being decided by
        a point of noise."""
        return (
            0 if self.id_match else 1,
            0 if self.title_exact else 1,
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
    )


def _is_tied(best: Scored, runner_up: Scored) -> bool:
    """Two hits we cannot honestly tell apart — the case Calibre punts to its GUI."""
    return (
        abs(best.title_fuzzy - runner_up.title_fuzzy) <= TIE_MARGIN
        and best.author_fuzzy // 5 == runner_up.author_fuzzy // 5
        and best.title_exact == runner_up.title_exact
    )


def _confidence(query: Query, ranked: Sequence[Scored]) -> tuple[Confidence, str]:
    best = ranked[0]

    if best.id_match:
        return Confidence.AUTO_ACCEPT, "identifier matched"

    if best.title_fuzzy < NO_MATCH_BELOW:
        return Confidence.NO_MATCH, f"best title score {best.title_fuzzy} below {NO_MATCH_BELOW}"

    runner_up = ranked[1] if len(ranked) > 1 else None
    tied = runner_up is not None and _is_tied(best, runner_up)

    if query.author:
        confident = (best.title_exact and best.author_fuzzy >= STRONG_AUTHOR) or (
            best.title_fuzzy >= STRONG_TITLE and best.author_exact
        )
        if confident and tied:
            return Confidence.PROVISIONAL, "two candidates score the same"
        if confident:
            return Confidence.AUTO_ACCEPT, "title and author both agree"
        return (
            Confidence.PROVISIONAL,
            f"title {best.title_fuzzy}, author {best.author_fuzzy} — not conclusive",
        )

    # No author to corroborate with: an exact, unrivalled title is the only
    # thing we will accept unattended.
    if best.title_exact and not tied:
        return Confidence.AUTO_ACCEPT, "exact title, no competing hit, no author given"
    return Confidence.PROVISIONAL, "no author on the entry to confirm the title with"


def match(query: Query, candidates: Sequence[Candidate]) -> Resolution:
    """Rank ``candidates`` against ``query`` and say how much to trust the winner."""
    if not candidates:
        return Resolution(confidence=Confidence.NO_MATCH, reason="no candidates")

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
