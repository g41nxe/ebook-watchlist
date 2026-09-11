"""Aus den zwei übrig gebliebenen Produktnummern werden Beziehungen (Ticket 17).

Nie gegen das Netz: die Produktseite kommt aus derselben Fixture, die
``test_beam`` benutzt, und der Client zählt mit, wie oft gefragt wurde.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from conftest import beam_fixture
from ebook_watchlist.dismissals import Dismissed, dismissed_books, resolve
from ebook_watchlist.http import NotFound
from ebook_watchlist.models import LinkOutcome
from ebook_watchlist.relations import RelationKind
from ebook_watchlist.run import EXIT_OK, EXIT_SOURCE_FAILURE, main
from ebook_watchlist.sources.beam import selectors as sel
from ebook_watchlist.sources.beam.source import BeamSource
from ebook_watchlist.store import Store

NOW = datetime(2026, 9, 4, 20, 0)
#: Die Nummer, unter der beam *Krieg der Klone* führt — die Fixture ist die
#: Seite dazu, und die Detailroute trägt genau diese Nummer.
PRODUCT_ID = "606983"


class StubClient:
    """Eine Seite, und ein Protokoll darüber, wonach gefragt wurde."""

    def __init__(self, page: str | None) -> None:
        self.page = page
        self.requests: list[str] = []

    def get(self, url: str, params: dict | None = None) -> str:
        self.requests.append(url)
        if self.page is None:
            raise NotFound(url)
        return self.page


def beam(page: str | None = None) -> BeamSource:
    html = beam_fixture("product-detail.html") if page is None else page
    return BeamSource(client=StubClient(html))  # type: ignore[arg-type]


def gone() -> BeamSource:
    return BeamSource(client=StubClient(None))  # type: ignore[arg-type]


# --- eine Nummer nachschlagen ----------------------------------------------


def test_a_product_number_is_asked_for_by_number_not_searched_for() -> None:
    """Suchen hieße raten und wieder abgleichen. Die Nummer ist exakt — es gibt
    nichts zu vergleichen und nichts, worüber man unsicher sein könnte."""
    source = beam()
    item = source.item(PRODUCT_ID)

    assert item is not None
    assert source.client.requests == [  # type: ignore[attr-defined]
        f"{sel.BASE}detail/index/sArticle/{PRODUCT_ID}"
    ]


def test_the_page_says_which_book_the_number_means() -> None:
    item = beam().item(PRODUCT_ID)

    assert item is not None
    assert item.title == "Krieg der Klone"
    # Die Autor:in steht sonst nur auf der Kachel, und wer über die Nummer
    # kommt, sieht keine.
    assert item.author == "John Scalzi"
    assert item.isbn == "9783104911854"
    # Die sprechende Adresse, nicht der Nummernweg dorthin.
    assert item.url and item.url.endswith("/606983/krieg-der-klone")


def test_a_delisted_number_is_an_answer_not_a_crash() -> None:
    assert gone().item(PRODUCT_ID) is None


# --- auflösen ---------------------------------------------------------------


def test_a_number_becomes_a_book_with_both_relations(store: Store) -> None:
    """``dismissed`` **und** ``owned``: die Datei sagt in ihrer ersten Zeile,
    dass es um bereits besessene Bücher geht, und nach ADR 18 gelten mehrere
    Beziehungen gleichzeitig."""
    report = resolve(
        store, [beam()], {"beam": [PRODUCT_ID]}, profile_slug="t", now=NOW
    )

    assert report.requests == 1
    assert not report.needs_attention
    book = store.books()[0]
    assert book.title == "Krieg der Klone"
    assert book.isbn == "9783104911854"
    kinds = {row.kind for row in store.relations_of("t", book.id)}
    assert kinds == {str(RelationKind.DISMISSED), str(RelationKind.OWNED)}


def test_the_number_is_kept_so_the_next_run_recognises_the_find(store: Store) -> None:
    resolve(store, [beam()], {"beam": [PRODUCT_ID]}, profile_slug="t", now=NOW)

    link = store.book_sources(store.books()[0].id)[0]
    assert link.source == "beam"
    assert link.source_item_id == PRODUCT_ID
    assert str(LinkOutcome.CONFIRMED) in link.details


def test_resolving_twice_costs_the_shop_nothing(store: Store) -> None:
    """Die zweite Antwort steht schon in der Datenbank. Noch einmal zu fragen
    wäre eine Anfrage ohne Anlass — und die schulden wir dem Shop nicht."""
    resolve(store, [beam()], {"beam": [PRODUCT_ID]}, profile_slug="t", now=NOW)

    second = beam()
    report = resolve(store, [second], {"beam": [PRODUCT_ID]}, profile_slug="t", now=NOW)

    assert second.client.requests == []  # type: ignore[attr-defined]
    assert report.requests == 0
    assert report.resolved[0].already_known is True
    assert len(store.books()) == 1


def test_a_withdrawn_dismissal_is_not_revived_by_a_second_pass(store: Store) -> None:
    """Beziehungen werden deaktiviert statt gelöscht (ADR 18). Ein zweiter Lauf,
    der sie blind wieder einschaltet, machte das Deaktivieren wertlos."""
    resolve(store, [beam()], {"beam": [PRODUCT_ID]}, profile_slug="t", now=NOW)
    book = store.books()[0]
    store.deactivate_relation("t", book.id, str(RelationKind.DISMISSED), now=NOW)

    resolve(store, [beam()], {"beam": [PRODUCT_ID]}, profile_slug="t", now=NOW)

    active = {row.kind for row in store.relations("t")}
    assert str(RelationKind.DISMISSED) not in active


def test_a_number_that_no_longer_resolves_is_reported(store: Store) -> None:
    """Still zu verwerfen hieße, eine Ablehnung zu verlieren, ohne dass jemand
    davon erfährt."""
    report = resolve(store, [gone()], {"beam": ["999999"]}, profile_slug="t", now=NOW)

    assert report.resolved == []
    assert report.needs_attention
    assert "beam:999999" in report.unresolved[0]
    assert store.books() == []


def test_a_source_that_no_longer_exists_is_reported_too(store: Store) -> None:
    report = resolve(store, [], {"buecherheld": ["1"]}, profile_slug="t", now=NOW)

    assert report.needs_attention
    assert "buecherheld:1" in report.unresolved[0]


def test_a_paused_source_is_not_asked(store: Store) -> None:
    """Der Schalter heißt "frag diese Quelle nicht". Eine Ausnahme für einen
    einmaligen Auflöser stand nirgends geschrieben (Ticket 23)."""
    source = beam()
    report = resolve(
        store, [source], {"beam": [PRODUCT_ID]}, profile_slug="t", now=NOW, paused=["beam"]
    )

    assert source.client.requests == []  # type: ignore[attr-defined]
    assert report.requests == 0
    assert report.needs_attention
    assert "pausiert" in report.unresolved[0]
    assert store.books() == []


def test_a_pause_stops_requests_not_work_already_done(store: Store) -> None:
    """Was einmal aufgelöst wurde, steht in der Datenbank — dafür braucht es
    keine Anfrage, und der Schalter verbietet Anfragen, nicht Arbeit."""
    resolve(store, [beam()], {"beam": [PRODUCT_ID]}, profile_slug="t", now=NOW)

    report = resolve(
        store, [], {"beam": [PRODUCT_ID]}, profile_slug="t", now=NOW, paused=["beam"]
    )

    assert not report.needs_attention
    assert report.resolved[0].already_known is True


def test_the_subcommand_honours_the_switch(data_dir: Path) -> None:
    """Ende zu Ende: pausiert die Leserin eine Quelle, fragt auch der Auflöser
    nicht — und meldet, was deshalb offen blieb."""
    (data_dir / "dismissed.yaml").write_text("fake:\n  - fake-2\n", encoding="utf-8")
    store = Store(data_dir / "snapshots.db")
    store.set_enabled("fake", False, now=NOW)

    assert main(["dismissals"]) == EXIT_SOURCE_FAILURE
    assert store.relations("test", kind=str(RelationKind.DISMISSED)) == []


# --- was danach unterdrückt wird -------------------------------------------


def test_the_relation_suppresses_at_the_shop_and_at_every_other_source(
    store: Store,
) -> None:
    """Der Anlass des Tickets: die alte Liste kannte nur beam, und die Onleihe
    hätte dasselbe Buch weiter angeboten."""
    resolve(store, [beam()], {"beam": [PRODUCT_ID]}, profile_slug="t", now=NOW)

    dismissed = dismissed_books(store, "t")

    assert dismissed.covers("beam", PRODUCT_ID)
    assert dismissed.covers("onleihe", "eine-ganz-andere-nummer", "9783104911854")


def test_a_withdrawn_dismissal_may_be_suggested_again(store: Store) -> None:
    resolve(store, [beam()], {"beam": [PRODUCT_ID]}, profile_slug="t", now=NOW)
    store.deactivate_relation(
        "t", store.books()[0].id, str(RelationKind.DISMISSED), now=NOW
    )

    assert dismissed_books(store, "t") == Dismissed()


# --- der Unterbefehl --------------------------------------------------------


def test_the_subcommand_resolves_what_the_file_still_holds(data_dir: Path) -> None:
    (data_dir / "dismissed.yaml").write_text("fake:\n  - fake-2\n", encoding="utf-8")

    assert main(["dismissals"]) == EXIT_OK

    store = Store(data_dir / "snapshots.db")
    book = next(row for row in store.books() if row.title == "Der Schwarm")
    kinds = {row.kind for row in store.relations_of("test", book.id)}
    assert kinds == {str(RelationKind.DISMISSED), str(RelationKind.OWNED)}


def test_the_subcommand_says_so_when_a_number_will_not_resolve(data_dir: Path) -> None:
    """Kein stiller Erfolg: ein Cron-Job, der "fertig" meldet, während eine
    Ablehnung verloren ging, wäre genau die Sorte Schweigen, die dieses
    Werkzeug vermeiden soll."""
    (data_dir / "dismissed.yaml").write_text("fake:\n  - gibt-es-nicht\n", encoding="utf-8")

    assert main(["dismissals"]) == EXIT_SOURCE_FAILURE


def test_the_run_itself_never_opens_the_file_any_more(data_dir: Path) -> None:
    """Ticket 17s letzter Punkt. Eine unlesbare Datei bringt einen Lauf nicht
    mehr zu Fall, weil er sie nicht mehr anfasst."""
    (data_dir / "dismissed.yaml").write_text("das ist keine Zuordnung", encoding="utf-8")

    assert main([]) == EXIT_OK


def test_the_lookup_does_not_grow_with_the_number_of_dismissals(tmp_path) -> None:
    """Zwei Abfragen, nicht zwei je Ablehnung.

    Der naheliegende Weg — über die Beziehungen laufen und je Buch
    nachschlagen — kostet bei dreihundert Ablehnungen rund zweieinhalb
    Sekunden pro Lauf. Genau diese Sorte Wachstum hat schon einmal eine
    Tabelle gekostet (ADR 16).
    """
    from datetime import datetime

    from ebook_watchlist.dismissals import dismissed_books
    from ebook_watchlist.models import LinkOutcome
    from ebook_watchlist.relations import RelationKind
    from ebook_watchlist.store import Store

    now = datetime(2026, 9, 4, 22, 0)
    store = Store(tmp_path / "s.db")
    for number in range(50):
        book = store.find_or_create_book(
            isbn=f"978000000{number:04d}", title=f"Buch {number}", now=now
        )
        store.put_relation("t", book.id, str(RelationKind.DISMISSED), now=now)
        store.put_book_source(
            book.id, "beam", outcome=str(LinkOutcome.CONFIRMED),
            source_item_id=str(number), resolved_at=now,
        )

    found = dismissed_books(store, "t")

    assert len(found.items) == 50
    assert len(found.isbns) == 50
    assert found.covers("beam", "7")
    assert found.covers("onleihe", "irgendwas", isbn="9780000000007")


def test_a_withdrawn_dismissal_is_suggested_again(tmp_path) -> None:
    """Der Sinn davon, sie zu deaktivieren statt zu löschen."""
    from datetime import datetime

    from ebook_watchlist.dismissals import dismissed_books
    from ebook_watchlist.relations import RelationKind
    from ebook_watchlist.store import Store

    now = datetime(2026, 9, 4, 22, 0)
    store = Store(tmp_path / "s.db")
    book = store.find_or_create_book(isbn="9783104911854", title="Buch", now=now)
    store.put_relation("t", book.id, str(RelationKind.DISMISSED), now=now)

    store.deactivate_relation("t", book.id, str(RelationKind.DISMISSED), now=now)

    assert not dismissed_books(store, "t").covers("beam", "1", isbn="9783104911854")
