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
    connection.exec_driver_sql(
        """
        INSERT OR IGNORE INTO seeded_scope (profile_slug, source, match_reason, category)
        SELECT DISTINCT profile_slug, source, match_reason, COALESCE(category, '')
        FROM observation
        WHERE match_reason IN ('profile_author', 'genre_category')
        """
    )


#: Index ``n`` upgrades a database at version ``n``. Append only, never reorder.
MIGRATIONS: tuple[Migration, ...] = (_backfill_seeded_scopes,)

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
