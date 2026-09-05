"""Die Profilübersicht — ausdrücklich nur lesend (Ticket 09)."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ebook_watchlist import paths
from ebook_watchlist.config import load_profile
from ebook_watchlist.relations import InterestKey, RelationKind
from ebook_watchlist.store import Store
from ebook_watchlist.web import create_app
from ebook_watchlist.web import profile_page as view

NOW = datetime(2026, 9, 4, 22, 0)


@pytest.fixture
def client(data_dir: Path) -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False, follow_redirects=True)


@pytest.fixture
def db(data_dir: Path) -> Store:
    return Store(paths.db_path())


def test_interests_are_grouped_by_kind(client: TestClient, db: Store) -> None:
    db.put_interest("test", str(InterestKey.AUTHOR), "Chris Carter", now=NOW, tier="core")
    db.put_interest(
        "test", str(InterestKey.THEMA),
        "belletristik/krimi-thriller/psychothriller", now=NOW, tier="core",
    )

    body = client.get("/profil").text

    assert "Chris Carter" in body
    assert "Psychothriller" in body


def test_a_weekly_author_says_so(client: TestClient, db: Store) -> None:
    """core wird jeden Lauf gefegt, extended einmal die Woche."""
    db.put_interest("test", str(InterestKey.AUTHOR), "Dave Eggers", now=NOW, tier="extended")
    assert "wöchentlich" in client.get("/profil").text


def test_a_theme_shows_its_readable_name_not_the_shop_path(
    client: TestClient, db: Store
) -> None:
    db.put_interest(
        "test", str(InterestKey.THEMA),
        "belletristik/horror-mystery/horror-mystery-allgemein", now=NOW,
    )
    body = client.get("/profil").text
    assert "Horror &amp; Mystery" in body or "Horror & Mystery" in body


def test_the_thresholds_are_stated(client: TestClient) -> None:
    body = client.get("/profil").text
    assert "5,00 €" in body
    assert "10,00 €" in body
    assert "25 %" in body


def test_an_overdue_sweep_says_so(db: Store) -> None:
    """Ein Lauf, der nie stattfand, darf keine ganze Woche kosten (ADR 4)."""
    db.set_state("test", view.EXTENDED_SWEEP_KEY, NOW - timedelta(days=9))
    assert "überfällig" in view.build(db, load_profile()).next_sweep


def test_a_sweep_that_just_ran_names_the_day(db: Store) -> None:
    db.set_state("test", view.EXTENDED_SWEEP_KEY, datetime.now())
    assert "überfällig" not in view.build(db, load_profile()).next_sweep


def test_the_counts_cover_every_relation(client: TestClient, db: Store) -> None:
    book = db.books()[0]
    db.put_relation("test", book.id, str(RelationKind.OWNED), now=NOW)

    body = client.get("/profil").text

    for label in ("beobachtet", "besessen", "gefiel", "verworfen"):
        assert label in body


def test_the_leseprofil_is_shown_with_its_version(client: TestClient) -> None:
    body = client.get("/profil").text
    assert "Profilversion" in body  # Beschriftung der Seite
    assert "Die Figur trägt alles" in body


def test_the_page_says_the_leseprofil_is_not_editable_here(client: TestClient) -> None:
    """Ein Formular hier würde das Änderungsverfahren aus ADR 17 umgehen."""
    body = client.get("/profil").text
    assert "nicht änderbar" in body
    assert "leseprofil-schaerfen" in body


def test_no_write_route_exists_for_the_profile(client: TestClient) -> None:
    """Die Entscheidung steht im Ticket, also gehört sie geprüft."""
    app = create_app()
    writable = [
        route.path
        for route in app.routes
        if getattr(route, "methods", set()) - {"GET", "HEAD"}
    ]
    assert not any(path.startswith("/profil") for path in writable)


def test_the_scheme_is_shown_beside_the_profile_and_without_a_version(
    client: TestClient,
) -> None:
    """Zwei Dokumente, nicht eins (ADR 21). Nur eines trägt eine Version — und
    die Seite muss sagen, welches, sonst hilft die Trennung niemandem."""
    body = client.get("/profil").text

    assert "Das Leseprofil" in body
    assert "Das Bewertungsschema" in body
    assert "Ohne Version" in body


def test_neither_document_is_shown_as_a_python_object(client: TestClient) -> None:
    """Die Seite zeigte eine Weile Scheme(text='…', min_stars=0, …) — dasselbe
    Datenobjekt, das schon einmal im Prompt gelandet war."""
    body = client.get("/profil").text

    assert "Scheme(" not in body
    assert "withhold_from" not in body
