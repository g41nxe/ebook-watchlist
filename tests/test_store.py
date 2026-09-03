from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ebook_watchlist.models import MatchReason, Observation
from ebook_watchlist.store import Store

NOW = datetime(2026, 9, 4, 6, 0)


def observation(source: str, item_id: str, price: int) -> Observation:
    return Observation(
        source=source,
        source_item_id=item_id,
        title=f"{source}/{item_id}",
        match_reason=MatchReason.WATCHLIST,
        price_cents=price,
    )


def test_latest_observations_returns_the_newest_row_per_item(tmp_path: Path) -> None:
    store = Store(tmp_path / "snapshots.db")
    for run, price in enumerate([1299, 1199, 999], start=1):
        run_id = store.start_run("p", "cli", NOW)
        store.append(run_id, "p", [observation("beam", "1", price)], NOW)
        store.finish_run(run_id, status="ok", delta_count=0, finished_at=NOW)
        assert run == run_id

    latest = store.latest_observations("p", [("beam", "1")])
    assert latest[("beam", "1")].price_cents == 999


def test_latest_observations_does_not_cross_sources_or_profiles(tmp_path: Path) -> None:
    """Two Sources can legitimately use the same item id; profiles never share rows."""
    store = Store(tmp_path / "snapshots.db")
    run_id = store.start_run("p", "cli", NOW)
    store.append(
        run_id,
        "p",
        [observation("beam", "1", 100), observation("voebb", "1", 200)],
        NOW,
    )
    other = store.start_run("other", "cli", NOW)
    store.append(other, "other", [observation("beam", "1", 999)], NOW)

    latest = store.latest_observations("p", [("beam", "1")])
    assert set(latest) == {("beam", "1")}
    assert latest[("beam", "1")].price_cents == 100


def test_unknown_items_are_simply_absent(tmp_path: Path) -> None:
    store = Store(tmp_path / "snapshots.db")
    assert store.latest_observations("p", [("beam", "nope")]) == {}


def test_last_finished_run_ignores_the_current_one(tmp_path: Path) -> None:
    store = Store(tmp_path / "snapshots.db")
    first = store.start_run("p", "cli", NOW)
    store.finish_run(first, status="ok", delta_count=0, finished_at=NOW)
    current = store.start_run("p", "cli", NOW)

    previous = store.last_finished_run("p", current)
    assert previous is not None
    assert previous.id == first
    assert store.last_finished_run("p", first) is None
