"""Unklare Zuordnungen entscheiden — auf der Watchlist (Ticket 41).

Der Bestätigungsweg ist der Regelfall für schwierige Titel, nicht der
Notausgang — nur gab es dafür keine Stelle: die Vorlage war schon eine
Radio-Liste, hatte aber genau eine Option.

Entschieden wird in der Zeile, nicht auf einer eigenen Seite: der Titel, wie
die Leserin ihn geschrieben hat, steht dann direkt darüber.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ebook_watchlist import paths
from ebook_watchlist.config import load_profile
from ebook_watchlist.models import LinkOutcome
from ebook_watchlist.relations import RelationKind
from ebook_watchlist.store import Store
from ebook_watchlist.web import create_app, watchlist

NOW = datetime(2026, 9, 6, 12, 0)


@pytest.fixture
def db(data_dir: Path) -> Store:
    return Store(paths.db_path())


@pytest.fixture
def client(data_dir: Path) -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False, follow_redirects=True)


def unklar(db: Store, *kandidaten: tuple[str, str]) -> int:
    """Ein beobachtetes Buch mit einer unsicheren Zuordnung."""
    profile = load_profile()
    buch = db.find_or_create_book(isbn=None, title="Red Rising", author="Pierce Brown", now=NOW)
    db.put_relation(profile.slug, buch.id, str(RelationKind.WATCHING), now=NOW)
    db.put_book_source(
        buch.id,
        "beam",
        outcome=str(LinkOutcome.UNSURE),
        url=None,
        resolved_at=NOW,
        reason="zwei Kandidaten sind gleich gut",
        candidates=[
            {"title": titel, "author": "Brown, Pierce", "url": url, "cover_url": None}
            for titel, url in kandidaten
        ],
    )
    return buch.id


def test_every_candidate_is_offered_not_just_the_winner(client: TestClient, db: Store) -> None:
    """Der Befund, der das Ticket ausgelöst hat: gespeichert wurde nur der
    Sieger, obwohl `Resolution.ranked` die übrigen kannte."""
    unklar(db, ("Red Rising", "https://beam.invalid/1"), ("Red Rising - Asche", "https://beam.invalid/2"))

    body = client.get("/watchlist?nur=unklar").text

    assert "Red Rising - Asche" in body
    assert body.count("bestaetigen") == 2


def test_confirming_says_a_human_decided(client: TestClient, db: Store) -> None:
    """`confirmed` statt `linked` — das ist der ganze Unterschied (ADR 9)."""
    buch_id = unklar(db, ("Red Rising", "https://beam.invalid/1"))

    client.post(
        f"/watchlist/{buch_id}/zuordnen",
        data={"source": "beam", "url": "https://beam.invalid/1", "was": "bestaetigen"},
    )

    zeile = db.get_book_source(buch_id, "beam")
    assert zeile is not None
    assert zeile.url == "https://beam.invalid/1"
    assert json.loads(zeile.details)["outcome"] == str(LinkOutcome.CONFIRMED)


def test_a_rejected_candidate_is_not_offered_again(client: TestClient, db: Store) -> None:
    buch_id = unklar(
        db, ("Red Rising", "https://beam.invalid/1"), ("Falsch", "https://beam.invalid/2")
    )

    client.post(
        f"/watchlist/{buch_id}/zuordnen",
        data={"source": "beam", "url": "https://beam.invalid/2", "was": "ablehnen"},
    )

    eintrag = next(e for e in watchlist.entries(db, load_profile()) if e.needs_choice)
    assert [k.title for k in eintrag.candidates] == ["Red Rising"]
    assert len(eintrag.rejected) == 1


def test_a_rejection_can_be_taken_back(client: TestClient, db: Store) -> None:
    """Ein Irrtum beim Wegklicken darf nicht dauerhaft sein (ADR 18)."""
    buch_id = unklar(db, ("Red Rising", "https://beam.invalid/1"))
    db.reject_candidate(buch_id, "beam", "https://beam.invalid/1", now=NOW)

    client.post(
        f"/watchlist/{buch_id}/zuordnen",
        data={"source": "beam", "url": "https://beam.invalid/1", "was": "zurueck"},
    )

    eintrag = next(e for e in watchlist.entries(db, load_profile()) if e.needs_choice)
    assert not eintrag.rejected
    assert len(eintrag.candidates) == 1


def test_rejecting_twice_records_it_once(db: Store) -> None:
    buch_id = unklar(db, ("Red Rising", "https://beam.invalid/1"))

    db.reject_candidate(buch_id, "beam", "https://beam.invalid/1", now=NOW)
    db.reject_candidate(buch_id, "beam", "https://beam.invalid/1", now=NOW)

    zeile = db.get_book_source(buch_id, "beam")
    assert json.loads(zeile.details)["rejected"] == ["https://beam.invalid/1"]


def test_a_book_no_longer_watched_is_no_longer_a_question(db: Store) -> None:
    """Eine unklare Zuordnung zu einem Buch, das niemand mehr beobachtet, ist
    keine Frage an die Leserin."""
    profile = load_profile()
    buch_id = unklar(db, ("Red Rising", "https://beam.invalid/1"))
    db.deactivate_relation(profile.slug, buch_id, str(RelationKind.WATCHING), now=NOW)

    assert not any(e.needs_choice for e in watchlist.entries(db, profile))


def test_an_empty_pile_says_so(client: TestClient, db: Store) -> None:
    assert "Nichts offen" in client.get("/watchlist?nur=unklar").text


def test_a_bundle_candidate_is_marked_as_one(client: TestClient, db: Store) -> None:
    """Ohne das Abzeichen sieht „Titel A / Titel B" aus wie eine
    Schreibvariante, nicht wie zwei Bücher (ADR 24)."""
    unklar(
        db,
        ("Der Kruzifix-Killer", "https://beam.invalid/1"),
        ("Der Kruzifix-Killer / Der Vollstrecker", "https://beam.invalid/2"),
    )

    body = client.get("/watchlist?nur=unklar").text

    assert "2 Bände" in body


def test_an_old_row_without_a_candidate_list_still_asks(client: TestClient, db: Store) -> None:
    """Zeilen aus der Zeit vor der Kandidatenliste tragen nur den Sieger. Ohne
    Rückfall hörten sie stillschweigend auf zu fragen — der teuerste denkbare
    Weg, eine Entscheidung zu verlieren."""
    profile = load_profile()
    buch = db.find_or_create_book(isbn=None, title="Red Rising", author="Pierce Brown", now=NOW)
    db.put_relation(profile.slug, buch.id, str(RelationKind.WATCHING), now=NOW)
    db.put_book_source(
        buch.id,
        "beam",
        outcome=str(LinkOutcome.UNSURE),
        url="https://beam.invalid/alt",
        resolved_at=NOW,
        matched_title="Red Rising - Asche zu Asche",
        matched_author="Brown, Pierce",
        reason="zwei Kandidaten sind gleich gut",
    )

    body = client.get("/watchlist?nur=unklar").text

    assert "Red Rising - Asche zu Asche" in body
    assert "https://beam.invalid/alt" in body


def test_a_paused_entry_asks_nothing(db: Store) -> None:
    """Pausiert heißt: wird nicht mehr geprüft. Dann ist die Zuordnung auch
    keine offene Frage."""
    profile = load_profile()
    buch_id = unklar(db, ("Red Rising", "https://beam.invalid/1"))
    db.deactivate_relation(profile.slug, buch_id, str(RelationKind.WATCHING), now=NOW)

    eintrag = next(e for e in watchlist.entries(db, profile) if e.book_id == buch_id)
    assert eintrag.candidates
    assert not eintrag.needs_choice
