"""Die Seite zu einem Fund (Issue #9).

Die Buchseite ohne die Teile, die es vor einer Entscheidung nicht gibt — und
mit den zweien, die sonst nirgends stehen: die ausgeschriebene Begründung des
Bewertungstors und der Preisverlauf des Funds.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ebook_watchlist import paths
from ebook_watchlist.models import MatchReason, Observation
from ebook_watchlist.ratings import subject_of
from ebook_watchlist.store import Store
from ebook_watchlist.web import create_app

NOW = datetime(2026, 9, 4, 21, 0)


@pytest.fixture
def client(data_dir: Path) -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False, follow_redirects=False)


@pytest.fixture
def db(data_dir: Path) -> Store:
    return Store(paths.db_path())


def fund(
    db: Store,
    *,
    item_id: str = "7",
    title: str = "Der Kannibalenhügel",
    author: str = "Viktor Sauer",
    price: int | None = 399,
    isbn: str | None = None,
    blurb: str | None = "Ein Schiff, allein im Dunkeln.",
    series: str | None = None,
    when: datetime = NOW,
) -> Observation:
    observation = Observation(
        source="beam",
        source_item_id=item_id,
        title=title,
        author=author,
        match_reason=MatchReason.GENRE_CATEGORY,
        price_cents=price,
        isbn=isbn,
        blurb=blurb,
        series=series,
        category="belletristik/krimi-thriller/psychothriller",
        url=f"https://beam.invalid/{item_id}",
    )
    run_id = db.start_run("test", "cli", when)
    db.append(run_id, "test", [observation], when)
    db.finish_run(run_id, status="ok", delta_count=1, finished_at=when)
    return observation


# --- die Seite --------------------------------------------------------------


def test_a_find_has_a_page_of_its_own(client: TestClient, db: Store) -> None:
    fund(db)

    response = client.get("/discovery/beam/7")

    assert response.status_code == 200
    assert "Der Kannibalenhügel" in response.text
    assert "Viktor Sauer" in response.text
    assert "Ein Schiff, allein im Dunkeln." in response.text


def test_a_find_nobody_ever_saw_is_a_404(client: TestClient, db: Store) -> None:
    assert client.get("/discovery/beam/gibtsnicht").status_code == 404


def test_the_page_names_the_reason_it_turned_up(client: TestClient, db: Store) -> None:
    """Derselbe Anlass wie im Stapel und im Tagesbericht, aus einer Stelle."""
    fund(db)

    body = client.get("/discovery/beam/7").text

    assert "Psychothriller" in body


def test_the_gate_reasoning_is_readable_here_and_only_here(
    client: TestClient, db: Store
) -> None:
    """Der Stapel zeigt den Pitch, nie die Begründung — ADR 19 wollte sie
    nachprüfbar machen, und dies ist der Ort dafür."""
    observation = fund(db)
    db.put_rating(
        subject_of(observation),
        stars=4,
        confidence="belegt",
        reason="Täterstimme ohne Reue, genau die Tonlage aus deinem Profil.",
        profile_version=3,
        now=NOW,
        pitch="Ein Metzger mit Regeln statt Gewissen.",
    )

    body = client.get("/discovery/beam/7").text

    assert "Täterstimme ohne Reue, genau die Tonlage aus deinem Profil." in body
    assert "belegt" in body
    assert client.get("/vorschlaege").text.count("Täterstimme ohne Reue") == 0


def test_the_price_history_of_the_find_is_shown(client: TestClient, db: Store) -> None:
    """Der Snapshot ist anhängend — ein über mehrere Läufe gesehener Fund hat
    eine Geschichte, auch ohne Buch-Zeile."""
    for tage, preis in ((3, 1299), (2, 1199), (1, 999)):
        fund(db, price=preis, when=NOW - timedelta(days=tage))

    body = client.get("/discovery/beam/7").text

    for preis in ("12,99 €", "11,99 €", "9,99 €"):
        assert preis in body, preis


def test_the_page_leaves_out_what_a_find_does_not_have(client: TestClient, db: Store) -> None:
    """Kein Buch heißt: keine Beziehungen, keine Notiz, kein "Prüfen bei"."""
    fund(db)

    body = client.get("/discovery/beam/7").text

    assert "Prüfen bei" not in body
    assert "Beziehungen" not in body
    assert "Notiz" not in body


def test_a_find_that_became_a_book_leads_to_its_book_page(
    client: TestClient, db: Store
) -> None:
    """Nach einer Entscheidung gibt es eine Buchseite — die ist dann die
    reichere Ansicht, und ein alter Link soll nicht daran vorbeiführen."""
    fund(db)
    client.post("/vorschlaege/entscheiden", data={"kind": "owned", "keys": ["beam:7"]})

    response = client.get("/discovery/beam/7")

    assert response.status_code == 303
    book = next(b for b in db.books() if b.title == "Der Kannibalenhügel")
    assert response.headers["location"] == f"/book/{book.id}"


def test_the_title_links_to_the_source(client: TestClient, db: Store) -> None:
    fund(db)

    body = client.get("/discovery/beam/7").text

    assert 'href="https://beam.invalid/7"' in body
