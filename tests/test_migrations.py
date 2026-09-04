"""Schema migrations: an existing snapshots.db must survive a schema change."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

from ebook_watchlist.migrations import SchemaTooNew, add_column, migrate
from ebook_watchlist.store import Base, Store


def user_version(path: Path) -> int:
    with sqlite3.connect(path) as connection:
        return connection.execute("PRAGMA user_version").fetchone()[0]


def columns(path: Path, table: str) -> set[str]:
    with sqlite3.connect(path) as connection:
        return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


# --- versioning -----------------------------------------------------------


def test_a_fresh_database_is_stamped_at_the_current_version(tmp_path: Path) -> None:
    """create_all already built the finished schema — nothing to upgrade."""
    path = tmp_path / "s.db"
    Store(path)

    from ebook_watchlist.migrations import SCHEMA_VERSION

    assert user_version(path) == SCHEMA_VERSION


def test_a_fresh_database_never_runs_a_migration(tmp_path: Path) -> None:
    ran: list[str] = []
    engine = create_engine(f"sqlite:///{tmp_path / 's.db'}")

    migrate(engine, Base.metadata, migrations=[lambda _c: ran.append("boom")])

    assert ran == []


def test_an_existing_database_runs_the_pending_migrations(tmp_path: Path) -> None:
    path = tmp_path / "s.db"
    Store(path)  # v1 schema on disk
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version = 0")

    ran: list[int] = []
    engine = create_engine(f"sqlite:///{path}")
    migrate(engine, Base.metadata, migrations=[lambda _c: ran.append(0), lambda _c: ran.append(1)])

    assert ran == [0, 1]
    assert user_version(path) == 2


def test_only_the_migrations_after_the_current_version_run(tmp_path: Path) -> None:
    path = tmp_path / "s.db"
    Store(path)
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version = 1")

    ran: list[int] = []
    engine = create_engine(f"sqlite:///{path}")
    migrate(engine, Base.metadata, migrations=[lambda _c: ran.append(0), lambda _c: ran.append(1)])

    assert ran == [1]


def test_a_database_from_the_future_refuses_to_open(tmp_path: Path) -> None:
    """Better a clear error than silently writing rows a newer schema owns."""
    path = tmp_path / "s.db"
    Store(path)
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version = 99")

    engine = create_engine(f"sqlite:///{path}")
    with pytest.raises(SchemaTooNew, match="newer version"):
        migrate(engine, Base.metadata)


# --- the column helper ----------------------------------------------------


def test_add_column_adds_it_and_keeps_the_data(tmp_path: Path) -> None:
    path = tmp_path / "s.db"
    Store(path)
    engine = create_engine(f"sqlite:///{path}")

    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO state (profile_slug, key, value) VALUES ('t', 'k', '2026-01-01')"
        )
        add_column(connection, "state", "note", "TEXT")

    assert "note" in columns(path, "state")
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT key FROM state").fetchone() == ("k",)


def test_add_column_is_safe_to_run_twice(tmp_path: Path) -> None:
    """A half-applied migration must be re-runnable."""
    path = tmp_path / "s.db"
    Store(path)
    engine = create_engine(f"sqlite:///{path}")

    with engine.begin() as connection:
        add_column(connection, "state", "note", "TEXT")
        add_column(connection, "state", "note", "TEXT")

    assert "note" in columns(path, "state")


# --- the real migration: backfilling seeded scopes ------------------------


def test_an_old_database_upgrades_all_the_way(tmp_path: Path) -> None:
    """Die Kette laeuft bis zum Ende durch, auch von Version 0 aus.

    ``seeded_scope`` ist unterwegs erst befuellt und dann fallengelassen worden
    (Ticket 05): eine Migration beschreibt die Welt, in der sie geschrieben
    wurde, und muss das weiter tun, auch wenn eine spaetere sie ueberholt.
    """
    path = tmp_path / "s.db"
    Store(path)

    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO observation (run_id, profile_slug, source, source_item_id, "
            "match_reason, title, category, observed_at) "
            "VALUES (1, 'default', 'beam', '1', 'genre_category', 'Titel', 'krimi', "
            "'2026-09-04')"
        )
        connection.execute("PRAGMA user_version = 0")

    Store(path)  # darf nicht scheitern
    tables = inspect(create_engine(f"sqlite:///{path}")).get_table_names()
    assert "seeded_scope" not in tables
    assert "interest_seeded" in tables


def test_the_observations_survive_the_upgrade(tmp_path: Path) -> None:
    """Die Aussaat war ein Cache; die Historie ist es nicht."""
    path = tmp_path / "s.db"
    Store(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO observation (run_id, profile_slug, source, source_item_id, "
            "match_reason, title, observed_at) "
            "VALUES (1, 'default', 'beam', '1', 'watchlist', 'Titel', '2026-09-04')"
        )
        connection.execute("PRAGMA user_version = 0")

    Store(path)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT count(*) FROM observation").fetchone()[0] == 1
