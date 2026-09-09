"""Die Startseite unter ``/`` und der Umzug der Übersicht nach ``/uebersicht`` (Issue #5)."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ebook_watchlist import paths
from ebook_watchlist.config import load_profile
from ebook_watchlist.models import MatchReason, Observation
from ebook_watchlist.run import main as run_main
from ebook_watchlist.store import Store
from ebook_watchlist.web import create_app, home, watchlist
from test_web_triage import found


@pytest.fixture
def client(data_dir: Path) -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


@pytest.fixture
def db(data_dir: Path) -> Store:
    return Store(paths.db_path())


def seen(db: Store, book_id: int, *, price: int | None, available: bool) -> None:
    """Eine Beobachtung *an einem Buch*, wie ein echter Lauf sie schreibt.

    Die Attrappe ``fake`` verknüpft ihre Funde nicht mit Büchern (kein
    ``book_id``, keine Quelle) — über sie bekäme die Watchlist nie einen Preis
    zu sehen. Hier steht deshalb, was der Matcher sonst tut.
    """
    from ebook_watchlist.models import Availability

    now = datetime.now()
    run_id = db.start_run("test", "cron", now)
    db.append(
        run_id,
        "test",
        [
            Observation(
                source="fake",
                source_item_id=f"buch-{book_id}",
                title="",
                match_reason=MatchReason.WATCHLIST,
                book_id=book_id,
                price_cents=price,
                availability=Availability.AVAILABLE if available else Availability.UNAVAILABLE,
            )
        ],
        now,
    )
    db.finish_run(run_id, status="ok", delta_count=1, finished_at=now)


def finished_run(
    db: Store, *, finished_at: datetime, deltas: int = 0, error: str | None = None
) -> None:
    run_id = db.start_run("test", "cron", finished_at - timedelta(minutes=5))
    db.finish_run(
        run_id,
        status="error" if error else "ok",
        delta_count=deltas,
        finished_at=finished_at,
        error=error,
    )


# --- vor dem ersten Lauf ----------------------------------------------------


def test_the_root_is_the_start_page_not_the_dashboard(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Tagesberichte" not in response.text
    assert "Läufe" not in response.text


def test_before_the_first_run_the_page_explains_and_points_to_the_watchlist(
    client: TestClient,
) -> None:
    """Drei Aufgaben eines Leerzustands: Zustand, nächster Schritt, Erklärung."""
    body = client.get("/").text

    assert "Noch kein Lauf" in body
    assert 'href="/watchlist"' in body
    assert "Jeder Stern hat einen Grund" in body
    assert "zuletzt geprüft" not in body


def test_a_broken_configuration_is_reported_on_the_start_page_too(
    client: TestClient, data_dir: Path
) -> None:
    (data_dir / "profile.yaml").unlink()

    response = client.get("/")

    assert response.status_code == 500
    assert "Traceback" not in response.text


# --- die Statuszeile --------------------------------------------------------


def test_after_a_run_the_status_line_says_when_and_how_much(client: TestClient) -> None:
    run_main([])

    body = client.get("/").text

    assert "zuletzt geprüft" in body
    assert f"{datetime.now():%d.%m.}" in body
    assert "Änderung" in body
    assert "Noch kein Lauf" not in body
    # Die Vorstellung gehoert dem Erstbesuch — wer laeuft, kennt sie.
    assert "Jeder Stern hat einen Grund" not in body


def test_a_run_older_than_a_day_says_so_in_words(client: TestClient, db: Store) -> None:
    """Eine Farbe allein wäre für jemanden mit Farbsehschwäche keine Information."""
    finished_run(db, finished_at=datetime.now() - timedelta(days=2, hours=1))

    body = client.get("/").text

    assert "vor 2 Tagen" in body


def test_a_failed_last_run_is_named_not_counted(client: TestClient, db: Store) -> None:
    finished_run(db, finished_at=datetime.now(), error="beam: kaputt")

    body = client.get("/").text

    assert "letzter Lauf fehlgeschlagen" in body
    assert "0 Änderungen" not in body


# --- jetzt zu haben ---------------------------------------------------------


def test_a_cheap_and_borrowable_watchlist_title_is_offered(
    client: TestClient, db: Store
) -> None:
    schwestern = next(b for b in db.books() if b.title == "Die sieben Schwestern")
    seen(db, schwestern.id, price=399, available=True)

    body = client.get("/").text

    assert "1 jetzt zu haben" in body
    assert "Die sieben Schwestern" in body
    assert "3,99 €" in body
    assert "ausleihbar" in body


def test_a_title_that_is_neither_cheap_nor_borrowable_stays_off_the_front(
    client: TestClient,
) -> None:
    run_main([])

    body = client.get("/").text

    assert "0 jetzt zu haben" in body
    assert "Die sieben Schwestern" not in body


def test_at_most_five_offers_are_shown_cheapest_first(db: Store) -> None:
    now = datetime.now()
    for number in range(6):
        book_id = watchlist.add(db, "test", title=f"Billig {number}", author=None, now=now)
        run_id = db.start_run("test", "cli", now)
        db.append(
            run_id, "test",
            [Observation(source="fake", source_item_id=f"b{number}", title=f"Billig {number}",
                         match_reason=MatchReason.WATCHLIST, book_id=book_id,
                         price_cents=100 + number * 50)],
            now,
        )

    view = home.build(db, load_profile(), now=now)

    assert [entry.title for entry in view.offers] == [f"Billig {n}" for n in range(5)]
    assert view.offers_total == 6


# --- zu entscheiden ---------------------------------------------------------


def test_open_suggestions_are_offered_with_the_three_decisions(
    client: TestClient, db: Store
) -> None:
    # ``found`` beendet seinen Lauf nicht — ohne einen abgeschlossenen sähe die
    # Seite zu Recht "noch kein Lauf".
    finished_run(db, finished_at=datetime.now())
    found(db, item_id="7", title="Der Kannibalenhügel", author="Viktor Sauer")

    body = client.get("/").text

    assert "1 von 1 zu entscheiden" in body
    assert "Der Kannibalenhügel" in body
    assert 'action="/vorschlaege/entscheiden"' in body
    for kind in ("dismissed", "owned", "watching"):
        assert f'value="{kind}"' in body


def test_at_most_two_suggestions_are_shown_and_the_rest_is_counted(
    client: TestClient, db: Store
) -> None:
    finished_run(db, finished_at=datetime.now())
    for number in range(4):
        found(db, item_id=str(number), title=f"Fund {number}")

    body = client.get("/").text

    assert "2 von 4 zu entscheiden" in body
    assert body.count('action="/vorschlaege/entscheiden"') == 2


# --- Der Umzug --------------------------------------------------------------


def test_the_dashboard_lives_at_uebersicht(client: TestClient) -> None:
    response = client.get("/uebersicht")

    assert response.status_code == 200
    assert "Noch kein Lauf verzeichnet" in response.text


def test_the_navigation_points_at_the_new_address_and_has_no_start_entry(
    client: TestClient,
) -> None:
    """Fünf Punkte brechen auf 375 px um — der Weg nach Hause ist das Zeichen."""
    body = client.get("/uebersicht").text

    assert 'href="/uebersicht"' in body
    assert ">Start<" not in body


def test_the_emblem_and_the_name_lead_home(client: TestClient) -> None:
    body = client.get("/uebersicht").text

    assert re.search(r'<a href="/"[^>]*>\s*<img', body), "das Zeichen führt nicht auf /"
    assert re.search(r'<a href="/"[^>]*>Buchfink</a>', body), "der Name führt nicht auf /"
