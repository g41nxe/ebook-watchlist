"""Title/author matching, shared by every Source's resolution step (ADR 8)."""

from .matcher import (
    Candidate,
    Confidence,
    Query,
    Resolution,
    Scored,
    author_matches,
    authors_contradict,
    match,
    score,
    worth_confirming,
)
from .normalize import fold, normalize_author, normalize_authors, normalize_title, split_authors

__all__ = [
    "Candidate",
    "Confidence",
    "Query",
    "Resolution",
    "Scored",
    "author_matches",
    "authors_contradict",
    "fold",
    "match",
    "normalize_author",
    "normalize_authors",
    "normalize_title",
    "score",
    "split_authors",
    "worth_confirming",
]
