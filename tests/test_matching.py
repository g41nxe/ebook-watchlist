"""The matcher, driven by its labelled corpus plus unit tests for the pieces."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ebook_watchlist.matching import (
    Candidate,
    Confidence,
    Query,
    match,
    normalize_author,
    normalize_title,
    score,
    split_authors,
)

CORPUS = yaml.safe_load(
    (Path(__file__).parent / "fixtures" / "matching.yaml").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("case", CORPUS, ids=[case["name"] for case in CORPUS])
def test_corpus(case: dict) -> None:
    query = Query(**case["query"])
    candidates = [Candidate(**raw) for raw in case["candidates"]]

    resolution = match(query, candidates)

    assert resolution.confidence is Confidence(case["expect"]), resolution.reason
    if "winner" in case:
        assert resolution.best is not None
        assert resolution.best.candidate.title == case["winner"]


# --- normalisation --------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Der Schwarm", "schwarm"),
        ("Die Straße", "strasse"),
        ("Schätzing", "schatzing"),
        ("The Hobbit", "hobbit"),
        ("Die sieben Schwestern - Roman", "sieben schwestern"),
        ("Atlas: Die Geschichte von Pa Salt", "atlas"),
        ("Der Schwarm (ungekürzt)", "schwarm"),
        ("Faust [Neue Auflage]", "faust"),
        ("Der Schwarm (2004)", "schwarm"),
        ("Ein Buch, zwei Bücher!", "buch zwei bucher"),
        ("1,000 Meilen", "1000 meilen"),
        ("  Der   Schwarm  ", "schwarm"),
    ],
)
def test_normalize_title(raw: str, expected: str) -> None:
    assert normalize_title(raw) == expected


def test_leading_articles_are_dropped_repeatedly() -> None:
    assert normalize_title("Der Die Das Buch") == "buch"


def test_a_title_that_is_only_a_subtitle_marker_is_not_gutted() -> None:
    """Cutting must never leave a single stray character behind."""
    assert normalize_title("R - Ein Roman") == "r ein roman"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Frank Schätzing", "frank schatzing"),
        ("Schätzing, Frank", "frank schatzing"),
        ("Dr. Johann Wolfgang von Goethe", "johann wolfgang goethe"),
        ("Goethe, Johann Wolfgang von", "johann wolfgang goethe"),
        ("Lucinda Riley (Übersetzerin)", "lucinda riley"),
        ("Martin Luther King Jr.", "martin luther king"),
    ],
)
def test_normalize_author(raw: str, expected: str) -> None:
    assert normalize_author(raw).full == expected


def test_initials_survive_the_main_form_but_not_the_looser_one() -> None:
    """Calibre drops every short token outright; that loses real information."""
    normalized = normalize_author("J. R. R. Tolkien")
    assert normalized.full == "j r r tolkien"
    assert normalized.substantial == "tolkien"


def test_an_imprint_is_not_reordered_like_a_person() -> None:
    assert normalize_author("Beispiel Verlag GmbH").full == "beispiel verlag gmbh"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Riley, Lucinda", ["Riley, Lucinda"]),
        ("Riley, Lucinda; Whittaker, Harry", ["Riley, Lucinda", "Whittaker, Harry"]),
        ("Anna Meier & Bernd Schulz", ["Anna Meier", "Bernd Schulz"]),
        ("Anna Meier und Bernd Schulz", ["Anna Meier", "Bernd Schulz"]),
        ("Anna Meier and Bernd Schulz", ["Anna Meier", "Bernd Schulz"]),
        ("Anna Meier, Bernd Schulz", ["Anna Meier", "Bernd Schulz"]),
    ],
)
def test_split_authors(raw: str, expected: list[str]) -> None:
    assert split_authors(raw) == expected


def test_a_lone_comma_between_single_words_stays_a_sort_order() -> None:
    """`Riley, Lucinda` is one person; splitting it would invent a second."""
    assert split_authors("Riley, Lucinda") == ["Riley, Lucinda"]


# --- ranking --------------------------------------------------------------


def test_the_sort_key_prefers_exact_title_over_a_better_author_score() -> None:
    query = Query(title="Der Schwarm", author="Frank Schätzing")
    exact_title = score(query, Candidate(title="Der Schwarm", author="F. Schätzing"))
    better_author = score(query, Candidate(title="Der Schwarm 2", author="Frank Schätzing"))
    assert exact_title.sort_key < better_author.sort_key


def test_year_breaks_a_tie_only_after_everything_else() -> None:
    query = Query(title="Faust", author="Johann Wolfgang von Goethe", year=2015)
    near = score(query, Candidate(title="Faust", author="Goethe, Johann Wolfgang", year=2015))
    far = score(query, Candidate(title="Faust", author="Goethe, Johann Wolfgang", year=1999))
    assert near.sort_key < far.sort_key
    # Alles bis zum Jahr ist gleich; das Jahr steht an Stelle 6, seit
    # 'Enthaltensein' als eigenes Kriterium dazugekommen ist (Ticket 36).
    assert near.sort_key[:6] == far.sort_key[:6]


def test_fuzzy_scores_are_bucketed_so_a_single_point_does_not_decide() -> None:
    query = Query(title="Der Schwarm", author="Frank Schätzing")
    scored = score(query, Candidate(title="Der Schwarm", author="Frank Schätzing"))
    assert scored.title_fuzzy == 100
    assert scored.sort_key[3] == -20  # 100 // 5, hinter id/exakt/enthalten


def test_source_order_is_the_last_resort_tie_break() -> None:
    query = Query(title="Faust")
    first = score(query, Candidate(title="Faust"), source_rank=0)
    second = score(query, Candidate(title="Faust"), source_rank=1)
    assert first.sort_key < second.sort_key


def test_ranking_is_returned_in_full_for_the_needs_attention_list() -> None:
    query = Query(title="Die sieben Schwestern", author="Lucinda Riley")
    resolution = match(
        query,
        [
            Candidate(title="Die Sturmschwester", author="Riley, Lucinda"),
            Candidate(title="Die sieben Schwestern", author="Riley, Lucinda"),
        ],
    )
    assert len(resolution.ranked) == 2
    assert resolution.ranked[0].candidate.title == "Die sieben Schwestern"


def test_no_match_withholds_the_best_candidate() -> None:
    resolution = match(
        Query(title="Der Schwarm", author="Frank Schätzing"),
        [Candidate(title="Kochen mit Kräutern", author="Erika Mustermann")],
    )
    assert resolution.confidence is Confidence.NO_MATCH
    assert resolution.best is None
    assert resolution.accepted is None
    assert resolution.ranked  # still available for diagnostics


def test_only_auto_accept_yields_an_accepted_candidate() -> None:
    resolution = match(
        Query(title="Der Schwarm", author="Frank Schätzing"),
        [Candidate(title="Der Schwarm", author="Erika Mustermann")],
    )
    assert resolution.confidence is Confidence.PROVISIONAL
    assert resolution.best is not None
    assert resolution.accepted is None


def test_the_matcher_touches_nothing_outside_itself() -> None:
    """A pure function: same inputs, same answer, no state carried between calls."""
    query = Query(title="Der Schwarm", author="Frank Schätzing")
    candidates = [Candidate(title="Der Schwarm", author="Schätzing, Frank")]
    first = match(query, candidates)
    second = match(query, candidates)
    assert first == second
