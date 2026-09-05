"""The Snapshot: an append-only SQLite log of Observations plus a Run journal (ADR 5).

Phase 1 keys rows by the profile *slug* — the ``profile`` and ``watchlist_entry``
tables arrive in Phase 2 when the UI takes ownership of configuration (ADR 10).
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    event,
    func,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .books import BookLike
from .books import find as find_book
from .cleaning import author_key, preferred_spelling
from .migrations import migrate
from .models import LINK_OUTCOMES, Availability, MatchReason, Observation
from .ratings import HUMAN_ORIGINS, RATING_ORIGINS
from .relations import RelationKind, check_details, check_interest_key, check_relation_kind


class Base(DeclarativeBase):
    pass


class RunRow(Base):
    __tablename__ = "run"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_slug: Mapped[str] = mapped_column(String, index=True)
    trigger: Mapped[str] = mapped_column(String)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default="running")
    delta_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The OS process doing the work. An unfinished row says nothing on its own
    #: — a killed Run never gets to write ``finished_at`` — so whoever asks
    #: "is a Run still going?" needs something it can check (Ticket 10).
    pid: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ObservationRow(Base):
    __tablename__ = "observation"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    profile_slug: Mapped[str] = mapped_column(String, index=True)
    source: Mapped[str] = mapped_column(String, index=True)
    source_item_id: Mapped[str] = mapped_column(String, index=True)
    match_reason: Mapped[str] = mapped_column(String)
    watchlist_key: Mapped[str | None] = mapped_column(String, nullable=True)
    #: Gesetzt bei Watchlist-Pruefungen, NULL bei Entdeckungen. Ohne das haette
    #: eine Verfuegbarkeitsmeldung der Bibliothek keinen Bezugspunkt (ADR 18).
    book_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    title: Mapped[str] = mapped_column(String)
    author: Mapped[str | None] = mapped_column(String, nullable=True)
    price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    availability: Mapped[str | None] = mapped_column(String, nullable=True)
    reservation_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_from: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    blurb: Mapped[str | None] = mapped_column(String, nullable=True)
    subtitle: Mapped[str | None] = mapped_column(String, nullable=True)
    isbn: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    series: Mapped[str | None] = mapped_column(String, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, index=True)

    # Serves the max-id-per-item lookup that every diff starts with.
    __table_args__ = (
        Index("ix_observation_item", "profile_slug", "source", "source_item_id", "id"),
    )


class BookRow(Base):
    """A book the reader has a relationship with (ADR 18).

    A row exists because something was said about this book — watched, owned,
    liked, dismissed — never for a bare discovery. 243 items arrived on the
    first real Run, most of them duplicates of each other across sources and
    editions, and a table called ``book`` whose majority is unvetted duplicates
    would not deserve the name.

    Identity is the ISBN where there is one. It identifies an *edition*, not a
    work, and it is not a general key across sources: of the two books this
    watchlist has at both, one shares an ISBN and one does not. The matcher and
    its confidence gate carry the rest (ADR 8, ADR 18).
    """

    __tablename__ = "book"

    id: Mapped[int] = mapped_column(primary_key=True)
    #: NULL for bundles, collections and single episodes, which carry no ISBN.
    isbn: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    title: Mapped[str] = mapped_column(String)
    author: Mapped[str | None] = mapped_column(String, nullable=True)
    series: Mapped[str | None] = mapped_column(String, nullable=True)
    #: Dateiname im Cover-Ordner, nicht die Adresse beim Shop: die Seite
    #: laedt nichts von einem Dritten nach (Ticket 15).
    cover_file: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (Index("ix_book_title", "title"),)


class BookSourceRow(Base):
    """Where one Source keeps this book — including the answer "nowhere".

    One row per Source: the Onleihe's title id and beam's product id are
    different values for the same book, so they are different rows rather than
    competing keys in one bag.

    A row with no ``url`` is not a contradiction but an answer — "searched
    here, not stocked". Eight of the reader's ten watchlist titles are in that
    state at the Onleihe, and this row is what stops them being searched for
    again every day.
    """

    __tablename__ = "book_source"

    book_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String, primary_key=True)
    source_item_id: Mapped[str | None] = mapped_column(String, nullable=True)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime)
    #: outcome, reason, and the title and author *as that Source rendered
    #: them* - the last two exist so a wrong automatic resolution stays visible
    #: (ADR 9). JSON rather than columns: nothing filters or sorts on them.
    details: Mapped[str] = mapped_column(String, default="{}")


class RatingRow(Base):
    """Was das Werkzeug von einem Buch hält (ADR 19).

    Bewusst **nicht** an der ``book``-Zeile. ADR 18 hält fest, dass ein Buch nur
    entsteht, wo die Leserin eine Beziehung hat — 243 Funde kamen im ersten
    echten Lauf herein, und eine Tabelle namens ``book``, die mehrheitlich aus
    ungeprüften Dubletten besteht, verdient den Namen nicht. Ratings an die
    Buch-Zeile zu hängen hätte genau das erzwungen: dreihundert Buch-Zeilen pro
    Lauf, damit das Tor irgendwo hinschreiben kann.

    Der Schlüssel ist deshalb der Fund selbst: die ISBN, wo es eine gibt,
    sonst ``(Quelle, Item-Id)``. Ein Buch, das später eine Beziehung bekommt,
    findet sein Urteil über die ISBN wieder.

    Was ein Mensch sagt, hängt dagegen am Buch — ``book:<id>``. Er vergibt seine
    Sterne auf der Buchseite, und sie sollen gelten, egal über welche Quelle das
    Buch das nächste Mal hereinkommt (Ticket 21).

    Maschinensterne und die der Leserin bleiben getrennt — und zwar dadurch,
    dass ``origin`` dabeisteht und Teil des Schlüssels ist: eine 4 von ihr ist
    eine Tatsache, eine 4 vom Modell ein Vorschlag. Beide dürfen nebeneinander
    stehen, und keines überschreibt das andere (ADR 17, ADR 19, Ticket 21).
    """

    __tablename__ = "rating"

    id: Mapped[int] = mapped_column(primary_key=True)
    #: ``isbn:978…`` oder ``item:beam:1279702`` beim Tor, ``book:42`` bei einem
    #: Urteil über ein Buch.
    subject: Mapped[str] = mapped_column(String)
    #: Wer geurteilt hat. Solange es nur eine Herkunft gab, war das entbehrlich;
    #: mit den Urteilen aus dem Gespräch und denen der Leserin sind es drei.
    origin: Mapped[str] = mapped_column(String, default="model")
    stars: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(String)
    #: Ein Satz für die Leserin, warum das Buch in Frage kommt — im Digest und
    #: auf der Vorschlagsseite. Getrennt von ``reason``: die Begründung ist ein
    #: Protokoll zum Nachprüfen und nennt auch, was fehlt.
    pitch: Mapped[str] = mapped_column(String, default="")
    #: Die Fassung des Leseprofils, gegen die geurteilt wurde. Eine neue
    #: Fassung macht ein Maschinenurteil ungültig — das ist die eine Änderung,
    #: bei der ein erneuter Aufruf richtig ist. Eine Änderung am
    #: Bewertungsschema tut das ausdrücklich nicht (ADR 21).
    profile_version: Mapped[int] = mapped_column(Integer)
    rated_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (UniqueConstraint("subject", "origin", name="uq_rating"),)


class BookRelationRow(Base):
    """Was die Leserin zu einem Buch sagt (ADR 18).

    Eine Tabelle für alle fünf Beziehungen, weil sie alle dasselbe sagen — nur
    die Art unterscheidet sich. Vorher lagen dieselben Bücher in vier Dateien:
    *Cold Eternity* stand in ``owned.yaml`` als Titel, in ``dismissed.yaml`` als
    beam-Produktnummer, und war einmal eine Zeile in ``watchlist.yaml``. Ein
    Buch als vorhanden zu markieren kostete zwei Bearbeitungen in zwei Formaten,
    und die Ablehnung galt nur für einen Shop.

    Beziehungen werden **deaktiviert, nicht gelöscht**. *Providence* heute von
    der Watchlist zu nehmen zerstörte die Tatsache, dass es je beobachtet wurde;
    ``active = false`` behält sie — "beobachtet, bis du es gekauft hast".
    """

    __tablename__ = "book_relation"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_slug: Mapped[str] = mapped_column(String, index=True)
    book_id: Mapped[int] = mapped_column(Integer, index=True)
    kind: Mapped[str] = mapped_column(String)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    details: Mapped[str] = mapped_column(String, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (
        UniqueConstraint("profile_slug", "book_id", "kind", name="uq_relation"),
    )


class InterestRow(Base):
    """Wo nach neuen Büchern gesehen werden soll (ADR 18).

    Referenzautor:in und Thema beantworten dieselbe Frage, also eine Tabelle.
    ``key`` ist Freitext, damit ein dritter Kanal — Verlag, Reihe, Schlagwort —
    einen Handler kostet und keine Migration; geprüft wird er beim Laden.
    """

    __tablename__ = "interest"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_slug: Mapped[str] = mapped_column(String, index=True)
    key: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(String)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    details: Mapped[str] = mapped_column(String, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (
        UniqueConstraint("profile_slug", "key", "value", name="uq_interest"),
    )


class InterestSeededRow(Base):
    """Dieses Interesse wurde bei dieser Quelle schon einmal angesehen.

    Löst ``seeded_scope`` ab und behebt einen Fehler, der beim Dokumentieren
    auffiel: der alte Schlüssel war ``(source, match_reason, category)``, und
    ``category`` blieb bei Autor:innen leer — **alle Autor:innen teilten sich
    also eine Aussaat**. Eine neue Referenzautor:in meldete daraufhin ihre
    ganze Backlist als Neuzugänge, während ein neues Thema still ansäte. Pro
    Interesse gehalten verhalten sich beide gleich.
    """

    __tablename__ = "interest_seeded"

    interest_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String, primary_key=True)
    seeded_at: Mapped[datetime] = mapped_column(DateTime)


class SourceRow(Base):
    """How a Source is faring — not what it is (ADR 18).

    Selectors, paths and base URLs stay with the parser they are versioned and
    tested with; a selector in a database would let someone break the parser
    without touching code. What lives here is what *running* produces: the
    probe result, which used to be printed and thrown away, and a switch to
    pause a Source without editing a file.

    Not keyed by profile: a Source is a shop or a library, and whether
    beam-shop's markup still parses is not a fact about a reader.

    Rows are never entered by hand; one appears when a Source first runs.
    """

    __tablename__ = "source"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_probe_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_probe_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)
    #: Zero after any success. Distinguishes a Source that just broke from one
    #: that has been broken for a week — the second needs a human, the first
    #: might be a redesign in progress.
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class StateRow(Base):
    """Small bits of bookkeeping that belong to no other table."""

    __tablename__ = "state"

    profile_slug: Mapped[str] = mapped_column(String, primary_key=True)
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[datetime] = mapped_column(DateTime)


def _to_observation(row: ObservationRow) -> Observation:
    return Observation(
        source=row.source,
        source_item_id=row.source_item_id,
        title=row.title,
        match_reason=MatchReason(row.match_reason),
        blurb=row.blurb,
        subtitle=row.subtitle,
        isbn=row.isbn,
        series=row.series,
        author=row.author,
        watchlist_key=row.watchlist_key,
        book_id=row.book_id,
        price_cents=row.price_cents,
        original_price_cents=row.original_price_cents,
        availability=Availability(row.availability) if row.availability else None,
        reservation_count=row.reservation_count,
        available_from=row.available_from,
        category=row.category,
        url=row.url,
        observed_at=row.observed_at,
    )


def _tune_sqlite(connection, _record) -> None:
    """Zwei Prozesse teilen sich diese Datei: der Lauf und die Weboberflaeche.

    Gemessen, und die Messung sagt weniger, als sie zuerst schien: 600
    verschraenkte Schreibvorgaenge aus zwei Prozessen liefen **ohne einen
    einzigen Fehler** durch — vorher in 6,56 s, mit WAL in 1,86 s. Ein
    "database is locked" liess sich nur erzwingen, indem eine Transaktion
    kuenstlich offen gehalten wurde; so schreibt dieses Programm nirgends.

    Das ist also keine Reparatur, sondern Luft: WAL macht aus jedem Commit ein
    Anhaengen statt eines Umschreibens und laesst Leser waehrend eines
    Schreibvorgangs durch. ``busy_timeout`` sorgt dafuer, dass ein zweiter
    Schreiber wartet statt aufzugeben — 15 s sind grosszuegig fuer Vorgaenge,
    die Millisekunden dauern, und Warten ist hier immer die richtige Antwort.
    """
    cursor = connection.cursor()
    try:
        cursor.execute("PRAGMA busy_timeout=15000")
    finally:
        cursor.close()


def _better_spelling(kept: str | None, seen: str | None) -> str | None:
    """Die bessere Schreibweise **derselben** Person, sonst die bisherige.

    Der Shop liefert ``Barnes, S. A.``, die Watchlist sagt ``S.A. Barnes``, und
    wer zuerst da war, bestimmte bisher, wie das Buch für immer heißt — bei
    *Cold Eternity* und *Providence* war das der einmalige Auflöser aus
    ``dismissed.yaml``. Die Regel steht seit Ticket 16 in
    :mod:`ebook_watchlist.cleaning` und wurde hier nie angewandt (Ticket 23).

    Ausdrücklich nur *dieselbe* Person: stimmen die Namen nicht überein, bleibt
    stehen, was dasteht. Eine spätere Quelle ist nicht automatisch die bessere,
    und ein Namenswechsel wäre keine Schreibweise, sondern ein anderer Mensch.
    """
    if not seen or not seen.strip():
        return kept
    if not kept or not kept.strip():
        return seen.strip()
    if author_key(kept) != author_key(seen):
        return kept
    return preferred_spelling([kept, seen]) or kept


class Store:
    """Owns the SQLite file. Schema is created on first use."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(f"sqlite:///{path}")
        event.listen(self._engine, "connect", _tune_sqlite)
        # Einmal je Datei, nicht je Verbindung: der Modus steht dauerhaft in
        # der Datenbank, ihn bei jedem Verbindungsaufbau zu setzen waere Arbeit
        # ohne Wirkung.
        with self._engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA journal_mode=WAL")
        migrate(self._engine, Base.metadata)

    def session(self) -> Session:
        return Session(self._engine)

    def start_run(
        self,
        profile_slug: str,
        trigger: str,
        started_at: datetime,
        pid: int | None = None,
    ) -> int:
        with self.session() as session:
            run = RunRow(
                profile_slug=profile_slug,
                trigger=trigger,
                started_at=started_at,
                status="running",
                pid=pid,
            )
            session.add(run)
            session.commit()
            return run.id

    def finish_run(
        self,
        run_id: int,
        *,
        status: str,
        delta_count: int,
        finished_at: datetime,
        error: str | None = None,
    ) -> None:
        with self.session() as session:
            run = session.get(RunRow, run_id)
            if run is None:  # pragma: no cover - only reachable if the row was deleted
                raise LookupError(f"run {run_id} vanished")
            run.status = status
            run.delta_count = delta_count
            run.finished_at = finished_at
            run.error = error
            session.commit()

    def recent_runs(self, profile_slug: str, limit: int = 20) -> list[RunRow]:
        """The Run journal, newest first — what the Dashboard shows."""
        with self.session() as session:
            stmt = (
                select(RunRow)
                .where(RunRow.profile_slug == profile_slug)
                .order_by(RunRow.id.desc())
                .limit(limit)
            )
            rows = list(session.scalars(stmt))
            for row in rows:
                session.expunge(row)
            return rows

    def latest_run(self, profile_slug: str) -> RunRow | None:
        """The most recent Run, finished or not — what "Run now" reports on."""
        runs = self.recent_runs(profile_slug, limit=1)
        return runs[0] if runs else None

    def last_finished_run(self, profile_slug: str, before_run_id: int) -> RunRow | None:
        """The previous completed Run — what the Digest means by 'last check'."""
        with self.session() as session:
            stmt = (
                select(RunRow)
                .where(
                    RunRow.profile_slug == profile_slug,
                    RunRow.id < before_run_id,
                    RunRow.finished_at.is_not(None),
                )
                .order_by(RunRow.id.desc())
                .limit(1)
            )
            row = session.scalars(stmt).first()
            if row is not None:
                session.expunge(row)
            return row

    def latest_observations(
        self, profile_slug: str, keys: Iterable[tuple[str, str]]
    ) -> dict[tuple[str, str], Observation]:
        """The most recent stored Observation for each ``(source, source_item_id)``.

        Resolved with a max-id-per-item subquery so the cost tracks the number of
        watched items, not the length of the append-only history.
        """
        wanted = set(keys)
        if not wanted:
            return {}
        sources = {source for source, _ in wanted}
        item_ids = {item_id for _, item_id in wanted}

        latest_ids = (
            select(func.max(ObservationRow.id))
            .where(
                ObservationRow.profile_slug == profile_slug,
                ObservationRow.source.in_(sources),
                ObservationRow.source_item_id.in_(item_ids),
            )
            .group_by(ObservationRow.source, ObservationRow.source_item_id)
        )

        found: dict[tuple[str, str], Observation] = {}
        with self.session() as session:
            stmt = select(ObservationRow).where(ObservationRow.id.in_(latest_ids))
            for row in session.scalars(stmt):
                key = (row.source, row.source_item_id)
                # in_() pairs the sets independently, so a cross-source id
                # collision can come back; keep only the pairs we asked for.
                if key in wanted:
                    found[key] = _to_observation(row)
        return found

    def latest_by_book(
        self, profile_slug: str, book_ids: Iterable[int]
    ) -> dict[int, Observation]:
        """Die zuletzt gesehene Beobachtung je Buch — was die Watchlist zeigt.

        Dieselbe max-id-Unterabfrage wie :meth:`latest_observations`, nur ueber
        ``book_id`` statt ueber das Quellen-Paar: die Kosten haengen an der Zahl
        der beobachteten Buecher, nicht an der Laenge der Historie.
        """
        wanted = set(book_ids)
        if not wanted:
            return {}
        latest_ids = (
            select(func.max(ObservationRow.id))
            .where(
                ObservationRow.profile_slug == profile_slug,
                ObservationRow.book_id.in_(wanted),
            )
            .group_by(ObservationRow.book_id)
        )
        found: dict[int, Observation] = {}
        with self.session() as session:
            stmt = select(ObservationRow).where(ObservationRow.id.in_(latest_ids))
            for row in session.scalars(stmt):
                if row.book_id is not None:
                    found[row.book_id] = _to_observation(row)
        return found

    def observations_for_book(
        self, profile_slug: str, book_id: int, limit: int = 200
    ) -> list[Observation]:
        """Die ganze Geschichte eines Buchs, neueste zuerst.

        Der Snapshot ist anhaengend (ADR 5), also *ist* das die Geschichte —
        sie muss nicht gesondert gefuehrt werden. Die Grenze schuetzt die Seite
        vor einem Buch, das seit Jahren jeden Tag beobachtet wird.
        """
        with self.session() as session:
            stmt = (
                select(ObservationRow)
                .where(
                    ObservationRow.profile_slug == profile_slug,
                    ObservationRow.book_id == book_id,
                )
                .order_by(ObservationRow.id.desc())
                .limit(limit)
            )
            return [_to_observation(row) for row in session.scalars(stmt)]

    def latest_discoveries(
        self, profile_slug: str, limit: int = 500
    ) -> list[Observation]:
        """Die zuletzt gesehene Fassung jeder Entdeckung.

        Der Snapshot ist anhaengend, also steht dasselbe Buch dort einmal je
        Lauf. Fuer die Triage zaehlt nur der letzte Stand — dieselbe
        max-id-je-Element-Unterabfrage wie ueberall sonst, damit die Kosten an
        der Zahl der Funde haengen und nicht an der Laenge der Geschichte.
        """
        latest_ids = (
            select(func.max(ObservationRow.id))
            .where(
                ObservationRow.profile_slug == profile_slug,
                ObservationRow.match_reason.in_(
                    [str(MatchReason.PROFILE_AUTHOR), str(MatchReason.GENRE_CATEGORY)]
                ),
            )
            .group_by(ObservationRow.source, ObservationRow.source_item_id)
        )
        with self.session() as session:
            stmt = (
                select(ObservationRow)
                .where(ObservationRow.id.in_(latest_ids))
                .order_by(ObservationRow.id.desc())
                .limit(limit)
            )
            return [_to_observation(row) for row in session.scalars(stmt)]

    def decided_items(self, profile_slug: str) -> set[tuple[str, str]]:
        """``(Quelle, Item-Id)``, zu denen es schon ein Buch mit Beziehung gibt.

        Ueber ``book_source``, weil dort steht, unter welcher Nummer eine
        Quelle ein Buch fuehrt. Das ist der Weg, auf dem eine Entscheidung
        *buchweit* wirkt statt nur fuer eine Produktnummer (ADR 18).
        """
        with self.session() as session:
            stmt = (
                select(BookSourceRow.source, BookSourceRow.source_item_id)
                .join(BookRelationRow, BookRelationRow.book_id == BookSourceRow.book_id)
                .where(
                    BookRelationRow.profile_slug == profile_slug,
                    BookSourceRow.source_item_id.is_not(None),
                )
            )
            return {(row[0], row[1]) for row in session.execute(stmt)}

    def dismissed_keys(self, profile_slug: str) -> tuple[set[tuple[str, str]], set[str]]:
        """``(Quelle, Nummer)`` und ISBNs aller aktiven Ablehnungen.

        Zwei Abfragen, nicht zwei je Ablehnung. Der naheliegende Weg — ueber
        die Beziehungen laufen und je Buch nachschlagen — kostet bei
        dreihundert Ablehnungen rund zweieinhalb Sekunden **pro Lauf**, und
        genau diese Sorte Wachstum hat schon einmal eine Tabelle gekostet
        (ADR 16, ``seeded_scope``).
        """
        with self.session() as session:
            dismissed = (
                select(BookRelationRow.book_id)
                .where(
                    BookRelationRow.profile_slug == profile_slug,
                    BookRelationRow.kind == str(RelationKind.DISMISSED),
                    BookRelationRow.active.is_(True),
                )
                .scalar_subquery()
            )
            items = {
                (row[0], row[1])
                for row in session.execute(
                    select(BookSourceRow.source, BookSourceRow.source_item_id).where(
                        BookSourceRow.book_id.in_(dismissed),
                        BookSourceRow.source_item_id.is_not(None),
                    )
                )
            }
            isbns = {
                row[0]
                for row in session.execute(
                    select(BookRow.isbn).where(
                        BookRow.id.in_(dismissed), BookRow.isbn.is_not(None)
                    )
                )
            }
        return items, isbns

    def books_with_relations(self, profile_slug: str) -> dict[str, int]:
        """ISBN -> Buch-Id, aber nur fuer Buecher, zu denen etwas gesagt wurde.

        So verschwindet ein Fund auch dann aus dem Stapel, wenn eine *andere*
        Quelle dasselbe Buch unter einer anderen Nummer fuehrt — die ISBN ist
        der Schluessel, an dem sich beide treffen (ADR 18).
        """
        with self.session() as session:
            stmt = (
                select(BookRow.isbn, BookRow.id)
                .join(BookRelationRow, BookRelationRow.book_id == BookRow.id)
                .where(
                    BookRelationRow.profile_slug == profile_slug,
                    BookRow.isbn.is_not(None),
                )
            )
            return {row[0]: row[1] for row in session.execute(stmt)}

    def get_state(self, profile_slug: str, key: str) -> datetime | None:
        with self.session() as session:
            row = session.get(StateRow, (profile_slug, key))
            return row.value if row is not None else None

    def set_state(self, profile_slug: str, key: str, value: datetime) -> None:
        with self.session() as session:
            row = session.get(StateRow, (profile_slug, key))
            if row is None:
                row = StateRow(profile_slug=profile_slug, key=key)
                session.add(row)
            row.value = value
            session.commit()

    # --- Bücher (Ticket 04) ------------------------------------------------

    def _book_index(self, session: Session) -> list[BookLike]:
        rows = session.execute(
            select(BookRow.id, BookRow.isbn, BookRow.title, BookRow.author)
        )
        return [BookLike(id=r[0], isbn=r[1], title=r[2], author=r[3]) for r in rows]

    def find_book(
        self, *, isbn: str | None, title: str, author: str | None = None
    ) -> BookRow | None:
        """Das Buch zu diesem Fund, falls es schon eines gibt."""
        with self.session() as session:
            found = find_book(self._book_index(session), isbn=isbn, title=title, author=author)
            if found is None:
                return None
            row = session.get(BookRow, found.book_id)
            if row is not None:
                session.expunge(row)
            return row

    def find_or_create_book(
        self,
        *,
        isbn: str | None,
        title: str,
        author: str | None = None,
        series: str | None = None,
        now: datetime,
    ) -> BookRow:
        """Ein Buch anlegen — aber erst nachsehen, ob es schon da ist.

        Jede Anlage sucht zuerst, weil sonst derselbe Titel unter zwei Quellen
        zweimal in der Tabelle stünde und die Beziehungen der Leserin sich auf
        zwei Zeilen verteilen würden.
        """
        with self.session() as session:
            found = find_book(self._book_index(session), isbn=isbn, title=title, author=author)
            if found is not None:
                row = session.get(BookRow, found.book_id)
                if row is not None:
                    # Was wir noch nicht wussten, tragen wir nach; was schon
                    # dasteht, wird nicht überschrieben - eine spätere Quelle
                    # ist nicht automatisch die bessere.
                    if row.isbn is None and isbn:
                        row.isbn = isbn
                    if row.series is None and series:
                        row.series = series
                    row.author = _better_spelling(row.author, author)
                    session.commit()
                    session.refresh(row)
                    session.expunge(row)
                    return row

            row = BookRow(
                isbn=isbn or None,
                title=title,
                author=author,
                series=series,
                created_at=now,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            session.expunge(row)
            return row

    def set_cover(self, book_id: int, file_name: str) -> None:
        with self.session() as session:
            row = session.get(BookRow, book_id)
            if row is None:
                return
            row.cover_file = file_name
            session.commit()

    def learn_isbn(self, book_id: int, isbn: str) -> bool:
        """Die ISBN nachtragen, die ein Watchlist-Eintrag selbst nicht mitbrachte.

        Ein Eintrag entsteht aus Titel und Autor:in; die ISBN erfaehrt erst die
        Beobachtung. Eine vorhandene wird nicht ueberschrieben - eine zweite
        ISBN bedeutet eine andere Ausgabe, und die stillschweigend zu
        uebernehmen wuerde die Identitaet des Buchs verschieben (ADR 18).

        Gibt zurueck, ob wirklich etwas gelernt wurde.
        """
        with self.session() as session:
            row = session.get(BookRow, book_id)
            if row is None or row.isbn or not isbn:
                return False
            # Eine andere Buch-Zeile kann dieselbe ISBN schon tragen: dann sind
            # es zwei Zeilen fuer ein Buch, und das Zusammenfuehren ist eine
            # eigene Entscheidung, keine Nebenwirkung eines Laufs.
            taken = session.scalars(
                select(BookRow.id).where(BookRow.isbn == isbn, BookRow.id != book_id)
            ).first()
            if taken is not None:
                return False
            row.isbn = isbn
            session.commit()
            return True

    def book(self, book_id: int) -> BookRow | None:
        with self.session() as session:
            row = session.get(BookRow, book_id)
            if row is not None:
                session.expunge(row)
            return row

    def books(self) -> list[BookRow]:
        with self.session() as session:
            rows = list(session.scalars(select(BookRow).order_by(BookRow.title)))
            for row in rows:
                session.expunge(row)
            return rows

    def get_book_source(self, book_id: int, source: str) -> BookSourceRow | None:
        with self.session() as session:
            row = session.get(BookSourceRow, (book_id, source))
            if row is not None:
                session.expunge(row)
            return row

    def book_sources(self, book_id: int) -> list[BookSourceRow]:
        with self.session() as session:
            rows = list(
                session.scalars(
                    select(BookSourceRow)
                    .where(BookSourceRow.book_id == book_id)
                    .order_by(BookSourceRow.source)
                )
            )
            for row in rows:
                session.expunge(row)
            return rows

    def book_by_source_item(self, source: str, source_item_id: str) -> int | None:
        """Welches Buch diese Quelle unter dieser Nummer fuehrt, falls bekannt.

        Der Weg zurueck von der Nummer zum Buch. Ohne ihn muesste jede
        Aufloesung noch einmal beim Shop nachfragen, obwohl die Antwort schon
        in der Datenbank steht (Ticket 17).
        """
        with self.session() as session:
            return session.scalars(
                select(BookSourceRow.book_id).where(
                    BookSourceRow.source == source,
                    BookSourceRow.source_item_id == source_item_id,
                )
            ).first()

    def put_book_source(
        self,
        book_id: int,
        source: str,
        *,
        outcome: str,
        url: str | None = None,
        source_item_id: str | None = None,
        resolved_at: datetime,
        **details: object,
    ) -> None:
        """Wo eine Quelle dieses Buch führt — oder dass sie es nicht führt.

        ``outcome`` wird gegen die bekannten Werte geprüft und nicht geduldet,
        wenn er unbekannt ist: ein Tippfehler fiele sonst still aus jeder
        Abfrage heraus, die fragt, was noch Aufmerksamkeit braucht.
        """
        if outcome not in LINK_OUTCOMES:
            raise ValueError(
                f"unknown link outcome {outcome!r} (known: {', '.join(sorted(LINK_OUTCOMES))})"
            )
        with self.session() as session:
            row = session.get(BookSourceRow, (book_id, source))
            if row is None:
                row = BookSourceRow(book_id=book_id, source=source)
                session.add(row)
            row.url = url
            row.source_item_id = source_item_id
            row.resolved_at = resolved_at
            row.details = json.dumps({"outcome": outcome, **details}, ensure_ascii=False)
            session.commit()

    # --- Bewertungen (Ticket 12) -------------------------------------------

    def rating(
        self, subject: str, profile_version: int, *, origin: str = "model"
    ) -> RatingRow | None:
        """Das gespeicherte Urteil einer Herkunft — wenn es zum Profil passt.

        Die Versionsprüfung gilt nur für Maschinenurteile; was die Leserin
        selbst gesagt hat, verfällt nicht, wenn sie ihr Profil schärft. Und sie
        gilt gegen das **Leseprofil**, nicht gegen das Bewertungsschema — das
        trägt gar keine Version (ADR 21).
        """
        with self.session() as session:
            row = session.scalars(
                select(RatingRow).where(
                    RatingRow.subject == subject, RatingRow.origin == origin
                )
            ).first()
            if row is None:
                return None
            if origin not in HUMAN_ORIGINS and row.profile_version != profile_version:
                return None
            session.expunge(row)
            return row

    def ratings_for(self, subjects: Iterable[str]) -> dict[tuple[str, str], RatingRow]:
        """Alle Urteile zu diesen Schlüsseln, nach ``(Schlüssel, Herkunft)``."""
        wanted = set(subjects)
        if not wanted:
            return {}
        with self.session() as session:
            rows = list(
                session.scalars(select(RatingRow).where(RatingRow.subject.in_(wanted)))
            )
            for row in rows:
                session.expunge(row)
            return {(row.subject, row.origin): row for row in rows}

    def drop_rating(self, subject: str, origin: str) -> bool:
        """Ein Urteil zurücknehmen; ``True``, wenn eines dastand.

        Nur die Leserin nimmt zurück, und sie tut es, indem sie ihre eigenen
        Sterne noch einmal anklickt. Eine Null wäre dafür kein Ersatz: sie
        hieße "passt überhaupt nicht" und ist selbst ein Urteil.
        """
        with self.session() as session:
            row = session.scalars(
                select(RatingRow).where(
                    RatingRow.subject == subject, RatingRow.origin == origin
                )
            ).first()
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True

    def put_rating(
        self,
        subject: str,
        *,
        stars: int,
        confidence: str,
        reason: str,
        profile_version: int,
        now: datetime,
        origin: str = "model",
        pitch: str = "",
    ) -> None:
        """Ein Urteil festhalten.

        Der Schlüssel ist ``(subject, origin)``: das Urteil der Leserin und das
        des Modells stehen nebeneinander, und keines überschreibt das andere
        (ADR 17, Ticket 21).
        """
        if origin not in RATING_ORIGINS:
            raise ValueError(
                f"unbekannte Herkunft {origin!r} "
                f"(bekannt: {', '.join(sorted(RATING_ORIGINS))})"
            )
        with self.session() as session:
            row = session.scalars(
                select(RatingRow).where(
                    RatingRow.subject == subject, RatingRow.origin == origin
                )
            ).first()
            if row is None:
                row = RatingRow(subject=subject, origin=origin)
                session.add(row)
            row.stars = stars
            row.confidence = confidence
            row.pitch = pitch
            row.reason = reason
            row.profile_version = profile_version
            row.rated_at = now
            session.commit()

    # --- Beziehungen und Interessen (Ticket 05) ----------------------------

    def put_relation(
        self,
        profile_slug: str,
        book_id: int,
        kind: str,
        *,
        active: bool = True,
        now: datetime,
        **details: object,
    ) -> None:
        """Was die Leserin zu einem Buch sagt. Mehrere Arten gelten gleichzeitig."""
        check_relation_kind(kind)
        check_details(kind, dict(details))
        with self.session() as session:
            row = session.scalars(
                select(BookRelationRow).where(
                    BookRelationRow.profile_slug == profile_slug,
                    BookRelationRow.book_id == book_id,
                    BookRelationRow.kind == kind,
                )
            ).first()
            if row is None:
                row = BookRelationRow(
                    profile_slug=profile_slug,
                    book_id=book_id,
                    kind=kind,
                    created_at=now,
                )
                session.add(row)
            row.active = active
            if details:
                row.details = json.dumps(details, ensure_ascii=False)
            session.commit()

    def set_relation_details(
        self, profile_slug: str, book_id: int, kind: str, details: dict, *, now: datetime
    ) -> None:
        """Den Beutel *ersetzen*, auch wenn er leer wird.

        ``put_relation`` laesst vorhandene Angaben in Ruhe, wenn der Aufrufer
        keine mitgibt — sonst loeschte jedes Pausieren die Notizen. Wer etwas
        wegnehmen will, braucht deshalb diesen Weg: sonst liesse sich eine
        Einschraenkung setzen, aber nie wieder aufheben.
        """
        check_relation_kind(kind)
        check_details(kind, details)
        with self.session() as session:
            row = session.scalars(
                select(BookRelationRow).where(
                    BookRelationRow.profile_slug == profile_slug,
                    BookRelationRow.book_id == book_id,
                    BookRelationRow.kind == kind,
                )
            ).first()
            if row is None:
                row = BookRelationRow(
                    profile_slug=profile_slug, book_id=book_id, kind=kind, created_at=now
                )
                session.add(row)
                row.active = True
            row.details = json.dumps(details, ensure_ascii=False)
            session.commit()

    def relations(
        self, profile_slug: str, *, kind: str | None = None, active_only: bool = True
    ) -> list[BookRelationRow]:
        with self.session() as session:
            stmt = select(BookRelationRow).where(BookRelationRow.profile_slug == profile_slug)
            if kind is not None:
                stmt = stmt.where(BookRelationRow.kind == kind)
            if active_only:
                stmt = stmt.where(BookRelationRow.active.is_(True))
            rows = list(session.scalars(stmt.order_by(BookRelationRow.id)))
            for row in rows:
                session.expunge(row)
            return rows

    def relations_of(self, profile_slug: str, book_id: int) -> list[BookRelationRow]:
        with self.session() as session:
            rows = list(
                session.scalars(
                    select(BookRelationRow).where(
                        BookRelationRow.profile_slug == profile_slug,
                        BookRelationRow.book_id == book_id,
                    )
                )
            )
            for row in rows:
                session.expunge(row)
            return rows

    def deactivate_relation(
        self, profile_slug: str, book_id: int, kind: str, *, now: datetime
    ) -> None:
        """Beziehungen werden deaktiviert, nicht geloescht — die Tatsache, dass
        ein Buch einmal beobachtet wurde, ist selbst eine Auskunft (ADR 18).

        Die Uhr wird uebergeben, nicht gelesen: ein Store, der selbst nach der
        Zeit sieht, laesst sich nicht mit einer festen Uhr pruefen.
        """
        self.put_relation(profile_slug, book_id, kind, active=False, now=now)

    def put_interest(
        self,
        profile_slug: str,
        key: str,
        value: str,
        *,
        active: bool = True,
        now: datetime,
        **details: object,
    ) -> InterestRow:
        check_interest_key(key)
        check_details(key, dict(details))
        with self.session() as session:
            row = session.scalars(
                select(InterestRow).where(
                    InterestRow.profile_slug == profile_slug,
                    InterestRow.key == key,
                    InterestRow.value == value,
                )
            ).first()
            if row is None:
                row = InterestRow(
                    profile_slug=profile_slug, key=key, value=value, created_at=now
                )
                session.add(row)
            row.active = active
            if details:
                row.details = json.dumps(details, ensure_ascii=False)
            session.commit()
            session.refresh(row)
            session.expunge(row)
            return row

    def interests(
        self, profile_slug: str, *, key: str | None = None, active_only: bool = True
    ) -> list[InterestRow]:
        with self.session() as session:
            stmt = select(InterestRow).where(InterestRow.profile_slug == profile_slug)
            if key is not None:
                stmt = stmt.where(InterestRow.key == key)
            if active_only:
                stmt = stmt.where(InterestRow.active.is_(True))
            rows = list(session.scalars(stmt.order_by(InterestRow.id)))
            for row in rows:
                session.expunge(row)
            return rows

    def is_interest_seeded(self, interest_id: int, source: str) -> bool:
        with self.session() as session:
            return session.get(InterestSeededRow, (interest_id, source)) is not None

    def mark_interest_seeded(self, interest_id: int, source: str, *, now: datetime) -> None:
        """Pro Interesse, nicht pro Anlass.

        Der alte Schluessel liess ``category`` bei Autor:innen leer, so dass
        sich *alle* Autor:innen eine Aussaat teilten: die erste saete still an,
        jede weitere meldete ihre ganze Backlist als Neuzugaenge.
        """
        with self.session() as session:
            if session.get(InterestSeededRow, (interest_id, source)) is None:
                session.add(
                    InterestSeededRow(interest_id=interest_id, source=source, seeded_at=now)
                )
                session.commit()

    # --- Quellen-Zustand (Ticket 03) ---------------------------------------

    def sources(self) -> list[SourceRow]:
        """Alle bekannten Quellen, alphabetisch — was das Dashboard zeigt."""
        with self.session() as session:
            rows = list(session.scalars(select(SourceRow).order_by(SourceRow.name)))
            for row in rows:
                session.expunge(row)
            return rows

    def source(self, name: str) -> SourceRow | None:
        with self.session() as session:
            row = session.get(SourceRow, name)
            if row is not None:
                session.expunge(row)
            return row

    def is_enabled(self, name: str) -> bool:
        """Eine unbekannte Quelle ist eingeschaltet.

        Die Zeile entsteht erst beim ersten Lauf; bis dahin wäre ein
        vorenthaltenes Ja gleichbedeutend damit, dass eine frisch
        konfigurierte Quelle stillschweigend nichts tut.
        """
        row = self.source(name)
        return True if row is None else row.enabled

    def set_enabled(self, name: str, enabled: bool, *, now: datetime) -> None:
        with self.session() as session:
            row = session.get(SourceRow, name)
            if row is None:
                row = SourceRow(name=name, enabled=True, consecutive_failures=0)
                session.add(row)
            row.enabled = enabled
            row.updated_at = now
            session.commit()

    def record_probe(
        self, name: str, *, ok: bool, error: str | None, now: datetime
    ) -> None:
        """Das Ergebnis eines Selbsttests festhalten statt es auszudrucken.

        ``consecutive_failures`` zählt hoch und wird bei jedem Erfolg auf null
        gesetzt: erst daran ist zu erkennen, ob eine Quelle gerade kaputtging
        oder seit Tagen kaputt ist.
        """
        with self.session() as session:
            row = session.get(SourceRow, name)
            if row is None:
                row = SourceRow(name=name, enabled=True, consecutive_failures=0)
                session.add(row)
            row.last_probe_at = now
            row.last_probe_ok = ok
            row.last_error = None if ok else error
            row.consecutive_failures = 0 if ok else (row.consecutive_failures or 0) + 1
            row.updated_at = now
            session.commit()

    def append(
        self,
        run_id: int,
        profile_slug: str,
        observations: Sequence[Observation],
        observed_at: datetime,
    ) -> None:
        if not observations:
            return
        with self.session() as session:
            session.add_all(
                ObservationRow(
                    run_id=run_id,
                    profile_slug=profile_slug,
                    source=obs.source,
                    source_item_id=obs.source_item_id,
                    match_reason=str(obs.match_reason),
                    watchlist_key=obs.watchlist_key,
                    book_id=obs.book_id,
                    title=obs.title,
                    author=obs.author,
                    price_cents=obs.price_cents,
                    original_price_cents=obs.original_price_cents,
                    availability=str(obs.availability) if obs.availability else None,
                    reservation_count=obs.reservation_count,
                    available_from=obs.available_from,
                    category=obs.category,
                    url=obs.url,
                    blurb=obs.blurb,
                    subtitle=obs.subtitle,
                    isbn=obs.isbn,
                    series=obs.series,
                    observed_at=obs.observed_at or observed_at,
                )
                for obs in observations
            )
            session.commit()
