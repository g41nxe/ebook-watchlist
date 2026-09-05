"""Der Vorschlagsstapel (Ticket 08).

Der Vorgang, den ein Gespräch am schlechtesten kann und ein Formular am besten.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ebook_watchlist import paths
from ebook_watchlist.config import load_profile
from ebook_watchlist.models import MatchReason, Observation
from ebook_watchlist.relations import RelationKind
from ebook_watchlist.store import Store
from ebook_watchlist.web import create_app
from ebook_watchlist.web import triage as view

NOW = datetime(2026, 9, 4, 21, 0)


@pytest.fixture
def client(data_dir: Path) -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False, follow_redirects=True)


@pytest.fixture
def db(data_dir: Path) -> Store:
    return Store(paths.db_path())


def found(
    db: Store,
    *,
    item_id: str = "1",
    title: str = "Ein Fund",
    author: str = "Wer Auch Immer",
    price: int | None = 399,
    isbn: str | None = None,
    reason: MatchReason = MatchReason.GENRE_CATEGORY,
    source: str = "beam",
    blurb: str | None = "Ein Schiff, allein im Dunkeln.",
) -> Observation:
    observation = Observation(
        source=source,
        source_item_id=item_id,
        title=title,
        author=author,
        match_reason=reason,
        price_cents=price,
        isbn=isbn,
        blurb=blurb,
        category="belletristik/krimi-thriller/psychothriller",
        url=f"https://beam.invalid/{item_id}",
    )
    run_id = db.start_run("test", "cli", NOW)
    db.append(run_id, "test", [observation], NOW)
    return observation


# --- der Stapel -------------------------------------------------------------


def test_a_discovery_shows_up_with_what_is_known(client: TestClient, db: Store) -> None:
    found(db, title="Der Kannibalenhügel", author="Viktor Sauer")

    body = client.get("/vorschlaege").text

    assert "Der Kannibalenhügel" in body
    assert "Viktor Sauer" in body
    assert "3,99 €" in body
    assert "Ein Schiff, allein im Dunkeln." in body


def test_the_page_says_why_each_find_is_there(client: TestClient, db: Store) -> None:
    """Dieselben Worte wie im Digest, aus einer Stelle (Ticket 14)."""
    found(db, reason=MatchReason.PROFILE_AUTHOR)
    assert "Autor:in" in client.get("/vorschlaege").text


def test_junk_never_reaches_the_pile(client: TestClient, db: Store) -> None:
    found(db, item_id="ok", title="Ein echter Fund")
    found(db, item_id="j1", title="3 Gruselkrimis: A / B / C")
    found(db, item_id="j2", title="Gratis dabei", price=0)

    body = client.get("/vorschlaege").text

    assert "Ein echter Fund" in body
    assert "3 Gruselkrimis" not in body
    assert "Gratistitel ausgeblendet" in body


def test_the_pile_can_be_filtered_by_origin(client: TestClient, db: Store) -> None:
    found(db, item_id="a", title="Vom Autor", reason=MatchReason.PROFILE_AUTHOR)
    found(db, item_id="t", title="Vom Thema", reason=MatchReason.GENRE_CATEGORY)

    body = client.get("/vorschlaege?anlass=profile_author").text

    assert "Vom Autor" in body
    assert "Vom Thema" not in body


def test_a_watchlist_title_is_not_a_suggestion(client: TestClient, db: Store) -> None:
    found(db, title="Beobachtet", reason=MatchReason.WATCHLIST)
    assert "Beobachtet" not in client.get("/vorschlaege").text


# --- entscheiden ------------------------------------------------------------


def test_a_decision_creates_the_book_and_the_relation(client: TestClient, db: Store) -> None:
    found(db, item_id="7", title="Der Kannibalenhügel", author="Viktor Sauer")

    client.post(
        "/vorschlaege/entscheiden", data={"kind": "owned", "keys": ["beam:7"]}
    )

    book = next(b for b in db.books() if b.title == "Der Kannibalenhügel")
    kinds = {row.kind for row in db.relations_of("test", book.id) if row.active}
    assert str(RelationKind.OWNED) in kinds


def test_a_decided_find_never_comes_back(client: TestClient, db: Store) -> None:
    found(db, item_id="7", title="Der Kannibalenhügel")

    client.post("/vorschlaege/entscheiden", data={"kind": "dismissed", "keys": ["beam:7"]})

    assert "Der Kannibalenhügel" not in client.get("/vorschlaege").text


def test_dismissing_suppresses_the_book_at_every_source(client: TestClient, db: Store) -> None:
    """Die alte dismissed.yaml konnte nur "dieser Shop soll das nicht mehr
    zeigen" — dasselbe Buch bei der Onleihe wäre wiedergekommen (ADR 18)."""
    isbn = "9783104911854"
    found(db, item_id="7", title="Der Kannibalenhügel", isbn=isbn)
    found(db, item_id="99", title="Der Kannibalenhügel", isbn=isbn, source="voebb")

    client.post("/vorschlaege/entscheiden", data={"kind": "dismissed", "keys": ["beam:7"]})

    pile = view.pending(db, load_profile())
    assert all(item.isbn != isbn for item in pile.items)


def test_several_finds_are_decided_at_once(client: TestClient, db: Store) -> None:
    for number in range(3):
        found(db, item_id=str(number), title=f"Fund {number}")

    client.post(
        "/vorschlaege/entscheiden",
        data={"kind": "dismissed", "keys": ["beam:0", "beam:1", "beam:2"]},
    )

    body = client.get("/vorschlaege").text
    assert "Fund 0" not in body and "Fund 2" not in body


def test_an_existing_book_is_matched_rather_than_duplicated(
    client: TestClient, db: Store
) -> None:
    """Jede Buchanlage sucht zuerst — sonst verteilen sich die Beziehungen
    eines Buchs auf zwei Zeilen (ADR 18)."""
    before = len(db.books())
    found(db, item_id="7", title="Die sieben Schwestern", author="Lucinda Riley")

    client.post("/vorschlaege/entscheiden", data={"kind": "owned", "keys": ["beam:7"]})

    assert len(db.books()) == before


def test_the_source_link_is_recorded(client: TestClient, db: Store) -> None:
    """Sonst stünde derselbe Fund beim nächsten Lauf wieder im Stapel."""
    found(db, item_id="7", title="Der Kannibalenhügel")

    client.post("/vorschlaege/entscheiden", data={"kind": "owned", "keys": ["beam:7"]})

    book = next(b for b in db.books() if b.title == "Der Kannibalenhügel")
    link = db.get_book_source(book.id, "beam")
    assert link is not None and link.source_item_id == "7"


def test_deciding_nothing_changes_nothing(client: TestClient, db: Store) -> None:
    before = len(db.books())
    client.post("/vorschlaege/entscheiden", data={"kind": "dismissed"})
    assert len(db.books()) == before


def test_an_unknown_key_is_ignored_not_fatal(client: TestClient, db: Store) -> None:
    response = client.post(
        "/vorschlaege/entscheiden", data={"kind": "owned", "keys": ["beam:gibtsnicht"]}
    )
    assert response.status_code == 200


def test_an_unknown_action_is_refused(client: TestClient, db: Store) -> None:
    found(db, item_id="7")
    response = client.post(
        "/vorschlaege/entscheiden", data={"kind": "verschlungen", "keys": ["beam:7"]}
    )
    assert response.status_code == 500


# --- die Zusammenstellung für sich -----------------------------------------


def test_the_pile_counts_what_it_does_not_show(db: Store) -> None:
    for number in range(60):
        found(db, item_id=f"n{number}", title=f"Fund {number}")

    pile = view.pending(db, load_profile(), limit=50)

    assert len(pile.items) == 50
    assert pile.total >= 60


# --- flüchtiger Browserzustand (Ticket 23) ----------------------------------


def test_alpine_is_actually_loaded(client: TestClient) -> None:
    """Der Build holte Alpine und kein Template lud es — 55 KB Abhängigkeit
    ohne Nutzen. Entweder eine Seite braucht es, oder es fliegt raus (ADR 20)."""
    assert "vendor/alpine.min.js" in client.get("/vorschlaege").text


def test_the_pile_counts_what_is_ticked_in_the_browser(client: TestClient, db: Store) -> None:
    """Bei fünfzig Zeilen ist "wie viele habe ich angehakt" die Frage vor jedem
    Knopfdruck — und reiner Browserzustand: kein Server kennt sie."""
    found(db)
    body = client.get("/vorschlaege").text

    assert 'x-data="{' in body
    assert 'x-text="chosen"' in body
    assert ':disabled="chosen === 0"' in body


def test_without_alpine_the_page_stays_a_plain_form(client: TestClient, db: Store) -> None:
    """x-cloak verbirgt, was ohne Alpine sinnlos wäre. Fällt das Skript aus,
    fehlt der Zähler — die Seite funktioniert weiter."""
    found(db)
    body = client.get("/vorschlaege").text

    assert "x-cloak" in body
    assert '<form method="post" action="/vorschlaege/entscheiden"' in body


# --- die Zeile wie in der Übersicht (Vorschlagsseite) -----------------------




# --- die Zeile, wie in der Übersicht -----------------------------------------


def urteil(db: Store, observation: Observation, *, stars: int, pitch: str) -> None:
    from ebook_watchlist.ratings import BY_MODEL, subject_of

    db.put_rating(subject_of(observation), stars=stars, confidence="teils",
                  reason="Begründung zum Nachprüfen.", profile_version=1,
                  now=NOW, origin=BY_MODEL, pitch=pitch)


def test_the_pitch_replaces_the_blurb(client: TestClient, db: Store) -> None:
    """Der Klappentext sagt, wovon das Buch handelt — der steht im Shop. Hier
    zählt, warum es für diese Leserin in Frage kommt."""
    beobachtet = found(db, title="Der Kannibalenhügel",
                       blurb="Ein Schiff, allein im Dunkeln.")
    urteil(db, beobachtet, stars=4, pitch="Ein Ermittler am Limit, und die Jagd beginnt sofort.")

    body = client.get("/vorschlaege").text

    assert "Ein Ermittler am Limit" in body
    assert "Ein Schiff, allein im Dunkeln." not in body


def test_without_a_judgement_the_blurb_still_shows(client: TestClient, db: Store) -> None:
    """Solange das Tor nicht gelaufen ist, ist der Klappentext besser als
    nichts."""
    found(db, blurb="Ein Schiff, allein im Dunkeln.")

    assert "Ein Schiff, allein im Dunkeln." in client.get("/vorschlaege").text


def test_the_stars_of_the_gate_are_shown(client: TestClient, db: Store) -> None:
    beobachtet = found(db, title="Der Kannibalenhügel")
    urteil(db, beobachtet, stars=4, pitch="Kurz und knapp.")

    body = client.get("/vorschlaege").text

    assert "4 von 5" in body
    assert "ic-star" in body


def test_an_unjudged_find_shows_no_stars(client: TestClient, db: Store) -> None:
    """Null Sterne wären eine Aussage. "Noch nicht bewertet" ist keine."""
    found(db, title="Der Kannibalenhügel")

    assert "von 5 — Urteil des Werkzeugs" not in client.get("/vorschlaege").text


def test_the_row_carries_a_cover_and_the_source_symbol(client: TestClient, db: Store) -> None:
    """Dieselbe Sprache wie auf der Watchlist: grün Bibliothek, bernstein Shop."""
    found(db, title="Der Kannibalenhügel", price=399)

    body = client.get("/vorschlaege").text

    assert "ic-shop" in body
    assert "ic-tag" in body  # Schnäppchen-Abzeichen auf dem Cover, 3,99 €
    assert "text-amber" in body


def test_the_page_shows_ten_not_fifty(client: TestClient, db: Store) -> None:
    """Der Stapel wird vom Tor ohnehin neu erzeugt — gezeigt wird nur, was auch
    bewertet werden muss."""
    for number in range(15):
        found(db, item_id=f"n{number}", title=f"Fund {number}")

    pile = view.pending(db, load_profile())

    assert len(pile.items) == view.PAGE_SIZE == 10
    assert pile.total >= 15


def test_the_best_stand_at_the_top(client: TestClient, db: Store) -> None:
    """Sonst faengt der Stapel mit dem an, was das Profil gerade abgelehnt hat."""
    schwach = found(db, item_id="a", title="Schwacher Fund")
    stark = found(db, item_id="b", title="Starker Fund")
    urteil(db, schwach, stars=1, pitch="Kaum Beruehrung.")
    urteil(db, stark, stars=4, pitch="Genau die kaputte Stimme.")

    titel = [item.title for item in view.pending(db, load_profile()).items]

    assert titel.index("Starker Fund") < titel.index("Schwacher Fund")


def test_an_unjudged_find_sinks_below_the_judged(client: TestClient, db: Store) -> None:
    """Ohne Urteil ist es keine Empfehlung, sondern eine offene Frage."""
    found(db, item_id="a", title="Ohne Urteil")
    schwach = found(db, item_id="b", title="Ein Stern")
    urteil(db, schwach, stars=1, pitch="Kaum Beruehrung.")

    titel = [item.title for item in view.pending(db, load_profile()).items]

    assert titel.index("Ein Stern") < titel.index("Ohne Urteil")
