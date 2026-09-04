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


def test_an_upgraded_database_remembers_the_shelves_it_already_saw(tmp_path: Path) -> None:
    """Without the backfill, the first Run after the upgrade would treat every
    shelf as brand new and swallow a day of genuine arrivals."""
    path = tmp_path / "s.db"
    Store(path)

    with sqlite3.connect(path) as connection:
        for reason, category in [
            ("genre_category", "belletristik/science-fiction/space-opera"),
            ("profile_author", None),
            ("watchlist", None),
        ]:
            connection.execute(
                "INSERT INTO observation (run_id, profile_slug, source, source_item_id, "
                "match_reason, title, category, observed_at) "
                "VALUES (1, 'default', 'beam', '1', ?, 'Titel', ?, '2026-09-04')",
                (reason, category),
            )
        # Pretend this file predates the seeded_scope table.
        connection.execute("DELETE FROM seeded_scope")
        connection.execute("PRAGMA user_version = 0")

    assert Store(path).seeded_scopes("default") == {
        ("beam", "genre_category", "belletristik/science-fiction/space-opera"),
        ("beam", "profile_author", ""),
    }


def test_the_backfill_leaves_watchlist_rows_alone(tmp_path: Path) -> None:
    """Watchlist entries are not a discovery scope; seeding them would be wrong."""
    path = tmp_path / "s.db"
    Store(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO observation (run_id, profile_slug, source, source_item_id, "
            "match_reason, title, observed_at) "
            "VALUES (1, 'default', 'beam', '1', 'watchlist', 'Titel', '2026-09-04')"
        )
        connection.execute("PRAGMA user_version = 0")

    assert Store(path).seeded_scopes("default") == set()


def test_opening_an_already_migrated_database_changes_nothing(tmp_path: Path) -> None:
    path = tmp_path / "s.db"
    store = Store(path)
    store.mark_seeded("default", {("beam", "genre_category", "krimi")})

    assert Store(path).seeded_scopes("default") == {("beam", "genre_category", "krimi")}
    assert "seeded_scope" in inspect(create_engine(f"sqlite:///{path}")).get_table_names()
