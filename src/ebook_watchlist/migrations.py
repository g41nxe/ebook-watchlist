"""Keeping an existing snapshots.db usable across schema changes.

SQLAlchemy's ``create_all`` adds missing *tables* but never touches an existing
one, so a new column on a live database would simply not appear and every query
touching it would fail. That is the whole gap this module closes.

The version counter is SQLite's own ``PRAGMA user_version`` — a slot that
already exists in every database file, so tracking it costs no schema of our
own. ``MIGRATIONS[n]`` upgrades a database at version ``n`` to ``n + 1``; a
database created from scratch is stamped at the current version and skips them
all, because ``create_all`` has already built the finished schema.

Alembic does all this and generates the steps for you. It is the right tool once
Phase 2 moves the Profile and the Watchlist into the database and the contents
stop being reproducible; while the store holds nothing but a rebuildable
Snapshot, thirty lines here are the cheaper trade (ADR 5, ADR 10).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from sqlalchemy import Connection, Engine, inspect

Migration = Callable[[Connection], None]


class SchemaTooNew(Exception):
    """The file was written by a newer version of this program."""


def _has_table(connection: Connection, table: str) -> bool:
    """Ob es die Tabelle ueberhaupt (noch) gibt.

    Eine Migration beschreibt die Welt, in der sie geschrieben wurde. Wird ihre
    Tabelle spaeter fallengelassen, muss sie wirkungslos werden statt zu
    scheitern — entfernen darf man sie nicht, das verschoebe die Indizes.
    """
    rows = connection.exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return rows.first() is not None


def _columns(connection: Connection, table: str) -> set[str]:
    return {row[1] for row in connection.exec_driver_sql(f"PRAGMA table_info({table})")}


def add_column(connection: Connection, table: str, column: str, ddl: str) -> None:
    """``ALTER TABLE … ADD COLUMN``, skipped when the column is already there.

    Idempotent on purpose: a half-applied migration must be safe to re-run.
    """
    if column not in _columns(connection, table):
        connection.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def _backfill_seeded_scopes(connection: Connection) -> None:
    """Teach an existing database which discovery scopes it has already seen.

    Without this, the first Run after the upgrade would find no seeded scopes,
    treat every shelf as brand new and swallow a day of genuine arrivals. On a
    real database from before this change that was 163 titles.

    The match reasons are spelled out rather than imported: a migration describes
    what the world looked like when it was written, and must keep doing the same
    thing however the enum grows later.
    """
    # Die Tabelle gibt es seit Ticket 05 nicht mehr — ``interest_seeded`` hat
    # sie abgeloest. Diese Migration bleibt trotzdem in der Kette stehen und
    # wird nur wirkungslos, wenn ihre Tabelle fehlt: die Indizes duerfen sich
    # nicht verschieben, sonst wuerde ein Datenbestand mittlerer Version die
    # falschen Schritte ueberspringen.
    #
    # Ohne diese Pruefung scheiterte jedes Upgrade von Version 0 an einer
    # Tabelle, die ``create_all`` nicht mehr anlegt.
    if not _has_table(connection, "seeded_scope"):
        return
    connection.exec_driver_sql(
        """
        INSERT OR IGNORE INTO seeded_scope (profile_slug, source, match_reason, category)
        SELECT DISTINCT profile_slug, source, match_reason, COALESCE(category, '')
        FROM observation
        WHERE match_reason IN ('profile_author', 'genre_category')
        """
    )


def _add_blurb_columns(connection: Connection) -> None:
    """Room for the blurb, subtitle and series we had been discarding.

    All three ride along on pages the Run already fetches, and they are the only
    signal from which cat-and-mouse, isolated settings and tone can be read at
    all (ADR 17). Existing rows stay NULL — history cannot be backfilled, which
    is precisely why the columns arrive now rather than when the classifier is
    built.
    """
    for column in ("blurb", "subtitle", "series"):
        add_column(connection, "observation", column, "TEXT")


#: Index ``n`` upgrades a database at version ``n``. Append only, never reorder.
def _add_isbn_column(connection: Connection) -> None:
    """The identifier ADR 18 makes book identity out of.

    Both Sources hand it over on pages the Run already fetches - beam in the
    tile order number, the Onleihe in a labelled row - so it costs no extra
    request. Existing rows stay NULL; history cannot be backfilled.
    """
    add_column(connection, "observation", "isbn", "TEXT")


def _add_book_id_column(connection: Connection) -> None:
    """Der Bezugspunkt, der ``watchlist_key`` abloest (ADR 18).

    Bestehende Zeilen bleiben NULL. Ein Backfill waere Ratearbeit: der alte
    Schluessel ist ``titel|autor`` in Kleinschreibung und traegt keine ISBN,
    also liesse er sich nur ueber denselben Matcher auf ein Buch abbilden, den
    wir gerade erst einfuehren. Die Historie verliert dadurch nichts - sie
    behaelt ihren ``watchlist_key``.
    """
    add_column(connection, "observation", "book_id", "INTEGER")


def _drop_resolution_table(connection: Connection) -> None:
    """``resolution`` geht in ``book_source`` auf (ADR 18, Ticket 04).

    Die Zeilen werden bewusst *nicht* uebernommen. Ihr Schluessel ist
    ``titel|autor`` in Kleinschreibung, und daraus ein Buch zu bauen haette
    Buecher mit kleingeschriebenen Titeln erzeugt, die der Leserin dauerhaft so
    angezeigt wuerden. Die Tabelle ist ein Cache: was hier verlorengeht, ist
    ein Suchlauf je Eintrag und Quelle - bei 24 Zeilen und der Hoeflichkeitspause
    gut eine Minute, einmalig. Ein dauerhaft haesslicher Titel waere teurer.

    Beobachtungen sind davon nicht beruehrt; die Historie bleibt vollstaendig.
    """
    connection.exec_driver_sql("DROP TABLE IF EXISTS resolution")


def _add_cover_column(connection: Connection) -> None:
    """Der Dateiname des lokal abgelegten Titelbilds (Ticket 15)."""
    add_column(connection, "book", "cover_file", "TEXT")


def _drop_seeded_scope_table(connection: Connection) -> None:
    """``seeded_scope`` geht in ``interest_seeded`` auf (Ticket 05).

    Nicht uebernommen: der alte Schluessel liess ``category`` bei Autor:innen
    leer, so dass *alle* Autor:innen sich eine Zeile teilten. Aus einer Zeile,
    die nichts unterscheidet, laesst sich nicht rekonstruieren, welche
    Autor:in schon einmal gefegt wurde — das ist genau der Fehler, den die
    neue Tabelle behebt.

    Die Folge ist einmalig sichtbar: nach dem Umstieg saeen alle Interessen
    neu an, also bleibt genau ein Lauf still. Ein geratener Backfill haette
    stattdessen dauerhaft falsche Aussaat behauptet.
    """
    connection.exec_driver_sql("DROP TABLE IF EXISTS seeded_scope")


def _add_run_pid_column(connection: Connection) -> None:
    """Which process is doing a Run, so an abandoned one can be told from a live one.

    An unfinished run row means "started and never wrote an ending", which a
    killed process and a Run still working produce alike. Existing rows stay
    NULL and are therefore judged by their age instead — the pid of a process
    that ended before this column existed cannot be recovered (Ticket 10).
    """
    add_column(connection, "run", "pid", "INTEGER")


def _add_rating_origin(connection: Connection) -> None:
    """Woher ein Urteil stammt (Ticket 21).

    Die Tabelle wird neu gebaut statt ergaenzt: der alte eindeutige Schluessel
    lag auf ``subject`` allein, und genau der muss fallen — sonst koennten das
    Urteil der Leserin und das des Modells nicht nebeneinander stehen, und eins
    wuerde das andere ueberschreiben. SQLite kann eine Eindeutigkeit nicht
    aendern, also gibt es dafuer keinen kleineren Weg.

    Bestehende Zeilen wandern mit und gelten als Modellurteile — die einzige
    Herkunft, die es bis hierher gab.

    Die Spalte heißt hier weiterhin ``rubric_version``. Sie wird erst von der
    *naechsten* Migration umbenannt, und eine Migration muss weiter tun, was sie
    tat, als sie geschrieben wurde (ADR 16) — sonst liest sie aus einer alten
    Datenbank eine Spalte, die es dort noch nicht gibt.
    """
    if not _has_table(connection, "rating"):
        return
    if "origin" in _columns(connection, "rating"):
        return
    connection.exec_driver_sql("ALTER TABLE rating RENAME TO rating_old")
    connection.exec_driver_sql(
        """
        CREATE TABLE rating (
            id INTEGER NOT NULL PRIMARY KEY,
            subject VARCHAR NOT NULL,
            origin VARCHAR NOT NULL,
            stars INTEGER NOT NULL,
            confidence VARCHAR NOT NULL,
            reason VARCHAR NOT NULL,
            rubric_version INTEGER NOT NULL,
            rated_at DATETIME NOT NULL,
            CONSTRAINT uq_rating UNIQUE (subject, origin)
        )
        """
    )
    connection.exec_driver_sql(
        """
        INSERT INTO rating (id, subject, origin, stars, confidence, reason,
                            rubric_version, rated_at)
        SELECT id, subject, 'model', stars, confidence, reason,
               rubric_version, rated_at
        FROM rating_old
        """
    )
    connection.exec_driver_sql("DROP TABLE rating_old")


def _rename_rubric_version(connection: Connection) -> None:
    """``rubric_version`` heißt ``profile_version`` (ADR 21, Ticket 25).

    Der alte Name behauptete, ein Urteil hänge am *Maßstab* — an dem Dokument
    also, das inzwischen das Verfahren ist und ausdrücklich keine Bewertung
    entwertet. Es hängt am Leseprofil, und der Name sagt das jetzt.

    Eine reine Umbenennung, kein Neubau: SQLite kann ``RENAME COLUMN`` seit
    3.25 (ADR 16).
    """
    if not _has_table(connection, "rating"):
        return
    spalten = _columns(connection, "rating")
    if "profile_version" in spalten or "rubric_version" not in spalten:
        return
    connection.exec_driver_sql(
        "ALTER TABLE rating RENAME COLUMN rubric_version TO profile_version"
    )


def _add_rating_pitch(connection: Connection) -> None:
    """Der Satz, der die Leserin hinsehen lässt — neben der Begründung.

    Eine eigene Spalte und kein Anhängsel an ``reason``: die beiden haben
    verschiedene Adressaten, und zusammengelegt hätte der Digest entweder ein
    Protokoll gezeigt oder die Begründung ihre Prüfbarkeit verloren.
    """
    if not _has_table(connection, "rating"):
        return
    add_column(connection, "rating", "pitch", "VARCHAR NOT NULL DEFAULT ''")


def _add_observation_cover_url(connection: Connection) -> None:
    """Die Adresse des Titelbilds mitschreiben (Ticket 15, nachgereicht).

    Der Parser liest sie seit jeher aus der Kachel, die Quelle setzt sie auf
    die Beobachtung — und hier ging sie verloren, weil es die Spalte nicht gab.
    Für Watchlist-Titel fiel das nicht auf: dort holt derselbe Lauf das Bild,
    solange das Feld noch im Speicher steht. Für eine Entdeckung war sie nach
    dem Lauf weg, und ein Bild liess sich nachträglich nur über die
    Detailseite wiederfinden — eine Anfrage je Buch für etwas, das schon
    dagewesen war.

    Nicht rückwirkend zu füllen: was ein Shop vor drei Wochen als Bildadresse
    nannte, weiss heute niemand mehr. Die nächsten Läufe tragen sie ein.
    """
    add_column(connection, "observation", "cover_url", "TEXT")


def _add_dnb_columns(connection: Connection) -> None:
    """Platz für das, was nur die DNB weiß (Ticket 42).

    ``dnb_checked_at`` hält auch ein *erfolgloses* Nachfragen fest: neun von
    dreißig Büchern kennt die DNB nicht, und ohne diesen Vermerk würde jeder
    Lauf sie erneut fragen.

    ``book_contains`` bekommt keine Fremdschlüssel-Klausel: SQLite prüft sie
    ohne ``PRAGMA foreign_keys`` ohnehin nicht. Für eine frische Datei legt
    ``create_all`` die Tabelle an; hier steht sie für die bestehenden.
    """
    add_column(connection, "book", "series_index", "TEXT")
    add_column(connection, "book", "language", "TEXT")
    add_column(connection, "book", "dnb_checked_at", "DATETIME")
    connection.exec_driver_sql(
        "CREATE TABLE IF NOT EXISTS book_contains "
        "(book_id INTEGER NOT NULL, isbn TEXT NOT NULL, "
        "PRIMARY KEY (book_id, isbn))"
    )


def _dnb_is_keyed_by_isbn(connection: Connection) -> None:
    """Die DNB-Auskunft gehört an die ISBN, nicht an ein Buch (Ticket 42).

    Der Schritt davor war falsch, und der Fall, der ihn ausgelöst hat, zeigt
    es: „David Hunter: 3in1 Bundle" ist bei uns **kein Buch**. Eine
    ``book``-Zeile entsteht erst durch eine Entscheidung der Leserin (ADR 18),
    ein Fund hat keine. ``book_contains(book_id, …)`` konnte damit ausgerechnet
    die Sammelausgabe nicht speichern, für die es gebaut wurde.

    Die DNB antwortet ohnehin über eine ISBN. Danach wird jetzt geschlüsselt —
    dann gilt die Antwort für Bücher und Funde gleichermaßen.

    Angehängt statt eingeschoben: eine Datei auf Version 13 muss denselben Weg
    gehen wie eine neue (ADR 16).
    """
    connection.exec_driver_sql("DROP TABLE IF EXISTS book_contains")
    for spalte in ("series_index", "language", "dnb_checked_at"):
        if spalte in _columns(connection, "book"):
            connection.exec_driver_sql(f"ALTER TABLE book DROP COLUMN {spalte}")
    connection.exec_driver_sql(
        "CREATE TABLE IF NOT EXISTS dnb_record ("
        "isbn TEXT PRIMARY KEY, checked_at DATETIME NOT NULL, found INTEGER NOT NULL, "
        "title TEXT, subtitle TEXT, author TEXT, series TEXT, series_index TEXT, "
        "language TEXT)"
    )
    connection.exec_driver_sql(
        "CREATE TABLE IF NOT EXISTS dnb_contains ("
        "isbn TEXT NOT NULL, contained TEXT NOT NULL, PRIMARY KEY (isbn, contained))"
    )


MIGRATIONS: tuple[Migration, ...] = (
    _backfill_seeded_scopes,
    _add_blurb_columns,
    _add_isbn_column,
    _add_book_id_column,
    _drop_resolution_table,
    _add_cover_column,
    _drop_seeded_scope_table,
    # Angehaengt, nie eingeschoben: der Zaehler ist die Version einer
    # bestehenden Datei, und eine verschobene Reihenfolge liesse einen
    # Datenbestand mittlerer Version die falschen Schritte ueberspringen.
    _add_run_pid_column,
    _add_rating_origin,
    _rename_rubric_version,
    _add_rating_pitch,
    _add_observation_cover_url,
    _add_dnb_columns,
    _dnb_is_keyed_by_isbn,
)

SCHEMA_VERSION = len(MIGRATIONS)


def _version(connection: Connection) -> int:
    return int(connection.exec_driver_sql("PRAGMA user_version").scalar_one())


def _stamp(connection: Connection, version: int) -> None:
    # PRAGMA takes no bound parameters, hence the literal; version is our own int.
    connection.exec_driver_sql(f"PRAGMA user_version = {int(version)}")


def migrate(engine: Engine, metadata, migrations: Sequence[Migration] = MIGRATIONS) -> None:
    """Bring the database at ``engine`` up to the current schema."""
    fresh = not inspect(engine).get_table_names()
    metadata.create_all(engine)

    with engine.begin() as connection:
        target = len(migrations)
        if fresh:
            # create_all just built the finished schema; there is nothing to upgrade.
            _stamp(connection, target)
            return

        version = _version(connection)
        if version > target:
            raise SchemaTooNew(
                f"snapshots.db is at schema version {version}, this program knows {target} "
                "— it was written by a newer version of ebook-watchlist"
            )
        for migration in migrations[version:]:
            migration(connection)
        _stamp(connection, target)


__all__ = ["MIGRATIONS", "SCHEMA_VERSION", "SchemaTooNew", "add_column", "migrate"]
