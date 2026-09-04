"""Eine Seite je Buch (Ticket 07).

Die Seite, die das Modell aus ADR 18 zum ersten Mal auszahlt: dieselben
Angaben lagen vorher über vier Dateien verstreut, die einander nicht kannten.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ebook_watchlist import paths
from ebook_watchlist.config import load_profile
from ebook_watchlist.models import Availability, LinkOutcome, MatchReason, Observation
from ebook_watchlist.relations import RelationKind
from ebook_watchlist.store import Store
from ebook_watchlist.web import book as view
from ebook_watchlist.web import create_app

NOW = datetime(2026, 9, 4, 20, 0)


@pytest.fixture
def client(data_dir: Path) -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False, follow_redirects=True)


@pytest.fixture
def db(data_dir: Path) -> Store:
    return Store(paths.db_path())


def sighting(db: Store, book_id: int, *, when: datetime, price: int | None = None,
             availability: Availability | None = None, title: str = "Die sieben Schwestern",
             source: str = "beam") -> None:
    run_id = db.start_run("test", "cli", when)
    db.append(
        run_id,
        "test",
        [
            Observation(
                source=source,
                source_item_id="1",
                title=title,
                match_reason=MatchReason.WATCHLIST,
                book_id=book_id,
                price_cents=price,
                availability=availability,
                observed_at=when,
            )
        ],
        when,
    )


# --- die Seite --------------------------------------------------------------


def test_the_page_shows_the_book(client: TestClient, db: Store) -> None:
    book = db.books()[0]
    body = client.get(f"/book/{book.id}").text
    assert book.title in body


def test_an_unknown_book_is_a_404_not_a_crash(client: TestClient) -> None:
    assert client.get("/book/9999").status_code == 404


def test_the_watchlist_links_to_it(client: TestClient, db: Store) -> None:
    book = db.books()[0]
    assert f"/book/{book.id}" in client.get("/watchlist").text


# --- Beziehungen ------------------------------------------------------------


def test_every_relation_can_be_set_from_here(client: TestClient, db: Store) -> None:
    book = db.books()[0]

    client.post(f"/book/{book.id}/relation", data={"kind": "owned", "active": "1"})

    kinds = {row.kind for row in db.relations_of("test", book.id) if row.active}
    assert str(RelationKind.OWNED) in kinds


def test_several_relations_hold_at_once(client: TestClient, db: Store) -> None:
    """Cold Eternity ist owned *und* war watching — der Normalfall (ADR 18)."""
    book = db.books()[0]
    client.post(f"/book/{book.id}/relation", data={"kind": "owned", "active": "1"})
    client.post(f"/book/{book.id}/relation", data={"kind": "liked", "active": "1"})

    kinds = {row.kind for row in db.relations_of("test", book.id) if row.active}
    assert {"watching", "owned", "liked"} <= kinds


def test_switching_a_relation_off_keeps_it_as_history(client: TestClient, db: Store) -> None:
    """Dass ein Buch einmal beobachtet wurde, ist selbst eine Auskunft."""
    book = db.books()[0]

    client.post(f"/book/{book.id}/relation", data={"kind": "watching", "active": "0"})

    body = client.get(f"/book/{book.id}").text
    kept = [r for r in db.relations_of("test", book.id) if r.kind == "watching"]
    assert kept and kept[0].active is False
    assert "Früher" in body


def test_an_unknown_relation_is_refused(client: TestClient, db: Store) -> None:
    book = db.books()[0]
    response = client.post(f"/book/{book.id}/relation", data={"kind": "besitze", "active": "1"})
    assert response.status_code == 500


# --- was die Quellen sagen --------------------------------------------------


def test_each_source_shows_its_own_title(client: TestClient, db: Store) -> None:
    """Daran bleibt eine falsche automatische Zuordnung sichtbar (ADR 9)."""
    book = db.books()[0]
    db.put_book_source(
        book.id, "beam", outcome=str(LinkOutcome.LINKED), url="https://beam.invalid/1",
        resolved_at=NOW, matched_title="Die sieben Schwestern / Roman", matched_author="Riley",
    )

    body = client.get(f"/book/{book.id}").text
    assert "Die sieben Schwestern / Roman" in body
    assert "dort ansehen" in body


def test_a_wildly_different_title_is_flagged(client: TestClient, db: Store) -> None:
    """Kein Urteil, nur ein Hinweis — der Vergleich entscheidet nichts."""
    book = db.books()[0]
    db.put_book_source(
        book.id, "beam", outcome=str(LinkOutcome.LINKED), resolved_at=NOW,
        matched_title="Handbuch der Gartenbewässerung",
    )

    body = client.get(f"/book/{book.id}").text
    assert "ganz anders" in body
    assert "Handbuch der Gartenbewässerung" in body


def test_a_matching_title_is_not_flagged(client: TestClient, db: Store) -> None:
    book = db.books()[0]
    db.put_book_source(
        book.id, "beam", outcome=str(LinkOutcome.LINKED), resolved_at=NOW,
        matched_title="Die sieben Schwestern — Band 1",
    )
    assert "ganz anders" not in client.get(f"/book/{book.id}").text


# --- die Geschichte ---------------------------------------------------------


def test_a_book_nobody_has_seen_says_so(client: TestClient, db: Store) -> None:
    fresh = db.find_or_create_book(isbn=None, title="Ganz neu", now=NOW)
    body = client.get(f"/book/{fresh.id}").text
    assert "Noch nichts gesehen" in body


def test_one_price_is_not_called_a_history(client: TestClient, db: Store) -> None:
    """Ein Punkt ist kein Verlauf. Das zu sagen ist ehrlicher, als eine Linie
    zu zeichnen, die nichts zeigt."""
    book = db.books()[0]
    sighting(db, book.id, when=NOW, price=999)

    body = client.get(f"/book/{book.id}").text
    assert "nur ein Preis bekannt" in body


def test_unchanged_prices_do_not_fill_the_list(db: Store) -> None:
    """Eine Zeile je Lauf wäre nach einem Jahr eine Wand aus derselben Zahl."""
    book = db.books()[0]
    for day in range(4):
        sighting(db, book.id, when=NOW + timedelta(days=day), price=999)
    sighting(db, book.id, when=NOW + timedelta(days=5), price=499)

    page = view.build(db, load_profile(), book.id)
    points = view.price_points(page.history)

    assert [point.price for point in points] == ["9,99 €", "4,99 €"]


def test_the_full_history_is_still_there(db: Store) -> None:
    """Zusammengefasst wird nur die Preisliste; die Tabelle zeigt jede Sichtung."""
    book = db.books()[0]
    for day in range(3):
        sighting(db, book.id, when=NOW + timedelta(days=day), price=999)

    page = view.build(db, load_profile(), book.id)
    assert len(page.history) >= 3


def test_availability_appears_for_a_library(client: TestClient, db: Store) -> None:
    book = db.books()[0]
    sighting(db, book.id, when=NOW, availability=Availability.AVAILABLE, source="voebb")

    assert "ausleihbar" in client.get(f"/book/{book.id}").text


def test_the_newest_sighting_comes_first(db: Store) -> None:
    book = db.books()[0]
    sighting(db, book.id, when=NOW, price=999)
    sighting(db, book.id, when=NOW + timedelta(days=1), price=499)

    page = view.build(db, load_profile(), book.id)
    assert page.history[0].price == "4,99 €"


def test_a_bargain_is_marked_in_the_history(db: Store) -> None:
    book = db.books()[0]
    sighting(db, book.id, when=NOW, price=399)

    page = view.build(db, load_profile(), book.id)
    assert page.history[0].deal is True


# --- was der Review gefunden hat -------------------------------------------


def test_the_reader_never_sees_an_internal_source_name(client: TestClient, db: Store) -> None:
    """"voebb" war nie ein Wort für die Leserin — und welche Quelle eine
    Bibliothek ist, sagt die Registry, nicht eine Liste in der Vorlage."""
    book = db.books()[0]
    db.put_book_source(book.id, "voebb", outcome=str(LinkOutcome.LINKED), resolved_at=NOW)
    sighting(db, book.id, when=NOW, source="voebb", availability=Availability.AVAILABLE)

    body = client.get(f"/book/{book.id}").text

    assert "voebb" not in body
    assert "beam" not in body
    assert "Bibliothek" in body


def test_a_source_that_agrees_on_the_title_says_nothing(db: Store) -> None:
    """Sonst wiederholte die Spalte in jeder Zeile denselben Titel."""
    book = db.books()[0]
    sighting(db, book.id, when=NOW, title=book.title)

    page = view.build(db, load_profile(), book.id)
    assert page.history[0].other_title is None


def test_a_source_that_disagrees_is_recorded(db: Store) -> None:
    book = db.books()[0]
    sighting(db, book.id, when=NOW, title="Ganz anderer Titel")

    page = view.build(db, load_profile(), book.id)
    assert page.history[0].other_title == "Ganz anderer Titel"


def test_a_single_price_gets_a_sentence_not_a_list(client: TestClient, db: Store) -> None:
    """Bei einem Punkt stünde die Zahl sonst dreimal auf der Seite."""
    book = db.books()[0]
    sighting(db, book.id, when=NOW, price=999)

    body = client.get(f"/book/{book.id}").text
    assert "nur ein Preis bekannt" in body
    assert "Preisänderungen" not in body


def test_two_prices_get_the_list(client: TestClient, db: Store) -> None:
    book = db.books()[0]
    sighting(db, book.id, when=NOW, price=999)
    sighting(db, book.id, when=NOW + timedelta(days=1), price=499)

    body = client.get(f"/book/{book.id}").text
    assert "Preisänderungen" in body
