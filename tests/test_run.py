"""End-to-end walking-skeleton tests: config in, Snapshot written, Digest out."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from filelock import FileLock

from ebook_watchlist import paths
from ebook_watchlist.digest import build_digest
from ebook_watchlist.models import SourceFailure
from ebook_watchlist.run import EXIT_CONFIG_ERROR, EXIT_OK, EXIT_SOURCE_FAILURE, main


def digest_files(data_dir: Path) -> list[Path]:
    return sorted((data_dir / "digests").glob("*.html"))


def test_the_first_run_reports_the_watched_titles_it_found(
    data_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A Watchlist Entry is news at any price (ADR 19). Discoveries are not:
    the shelves are seeded quietly and stay out of this first Digest."""
    assert main([]) == EXIT_OK

    out = capsys.readouterr().out
    assert "Erster Check" in out
    assert "Der Schwarm" in out
    assert len(digest_files(data_dir)) == 1
    assert paths.db_path().exists()


def test_second_unchanged_run_stays_silent(
    data_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main([])
    capsys.readouterr()
    after_first = digest_files(data_dir)

    assert main([]) == EXIT_OK
    assert capsys.readouterr().out == ""
    assert digest_files(data_dir) == after_first


def test_a_price_drop_produces_a_digest(data_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main([])
    capsys.readouterr()

    fixture = data_dir / "fake-source.yaml"
    fixture.write_text(
        fixture.read_text(encoding="utf-8").replace("price_cents: 1299", "price_cents: 499"),
        encoding="utf-8",
    )

    assert main([]) == EXIT_OK
    out = capsys.readouterr().out
    assert "Der Schwarm" in out
    assert "12,99 € → 4,99 €" in out
    assert "Änderungen seit letztem Check" in out

    # The first Run already wrote today's Digest, so the second is kept beside
    # it rather than overwriting it.
    today = f"digest-{datetime.now():%Y-%m-%d}"
    written = digest_files(data_dir)
    assert len(written) == 2
    assert {path.name for path in written} == {
        f"{today}.html",
        f"{today}-{datetime.now():%H%M}.html",
    }
    dropped = next(path for path in written if path.name != f"{today}.html")
    assert "4,99" in dropped.read_text(encoding="utf-8")


def test_availability_change_produces_a_digest(
    data_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main([])
    capsys.readouterr()

    fixture = data_dir / "fake-source.yaml"
    fixture.write_text(
        fixture.read_text(encoding="utf-8").replace(
            "availability: unavailable", "availability: available"
        ),
        encoding="utf-8",
    )

    assert main([]) == EXIT_OK
    out = capsys.readouterr().out
    assert "Die sieben Schwestern" in out
    assert "jetzt verfügbar" in out


def test_a_broken_source_is_reported_not_swallowed(
    data_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (data_dir / "fake-source.yaml").write_text("not: a list\n", encoding="utf-8")

    assert main([]) == EXIT_SOURCE_FAILURE
    captured = capsys.readouterr()
    assert "⚠️ Fehler" in captured.out
    assert "must be a list of items" in captured.out
    assert len(digest_files(data_dir)) == 1


def test_missing_config_fails_loudly(data_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (data_dir / "profile.yaml").unlink()
    assert main([]) == EXIT_CONFIG_ERROR
    assert "config error" in capsys.readouterr().err


def test_a_second_concurrent_run_backs_off(
    data_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    held = FileLock(str(paths.lock_path()), timeout=0)
    held.acquire()
    try:
        assert main([]) == EXIT_OK
        assert "already in progress" in capsys.readouterr().err
    finally:
        held.release()


def test_output_survives_a_console_that_cannot_render_the_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows hands us a cp1252 stdout, which raises on the price arrow. Losing
    a whole Run's Digest at the very last step is not an acceptable failure."""
    from ebook_watchlist.run import _survive_a_narrow_console

    class Narrow:
        def __init__(self) -> None:
            self.kwargs: dict = {}

        def reconfigure(self, **kwargs) -> None:
            self.kwargs = kwargs

    class Plain:
        """A stream with no reconfigure at all — must simply be left alone."""

    narrow, plain = Narrow(), Plain()
    monkeypatch.setattr("ebook_watchlist.run.sys.stdout", narrow)
    monkeypatch.setattr("ebook_watchlist.run.sys.stderr", plain)

    _survive_a_narrow_console()

    assert narrow.kwargs == {"errors": "replace"}


def test_run_journal_records_every_run(data_dir: Path) -> None:
    main([])
    main([])

    from ebook_watchlist.store import RunRow, Store

    store = Store(paths.db_path())
    with store.session() as session:
        runs = session.query(RunRow).order_by(RunRow.id).all()
        assert [run.status for run in runs] == ["ok", "ok"]
        assert all(run.finished_at is not None for run in runs)
        assert all(run.trigger == "cli" for run in runs)


def test_a_second_digest_on_the_same_day_does_not_erase_the_first(data_dir: Path) -> None:
    """A manual re-run must not silently overwrite what the cron job produced."""
    from ebook_watchlist.run import _write_html

    digests = data_dir / "digests"
    digest = build_digest(
        profile_name="T",
        generated_at=datetime(2026, 9, 4, 6, 0),
        since=None,
        deltas=[],
        failures=[SourceFailure(source="x", message="kaputt")],
    )

    first = _write_html(digest, datetime(2026, 9, 4, 6, 0))
    second = _write_html(digest, datetime(2026, 9, 4, 18, 30))

    assert first.name == "digest-2026-09-04.html"
    assert second.name == "digest-2026-09-04-1830.html"
    assert first.exists() and second.exists()
    assert {p.name for p in digests.iterdir()} == {first.name, second.name}


# --- den Rueckstand beurteilen (Ticket 19) ---------------------------------


def test_rating_the_backlog_asks_only_about_what_has_no_judgement(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Der Stapel ist bestbewertet-zuerst sortiert, Unbeurteiltes steht hinten.
    Wer die erste Seite nimmt, bekommt genau die Buecher, die schon ein Urteil
    haben — und die offenen nie."""
    from ebook_watchlist import run as run_module
    from ebook_watchlist.models import MatchReason, Observation
    from ebook_watchlist.rating import Rating, load_leseprofil
    from ebook_watchlist.ratings import BY_MODEL
    from ebook_watchlist.store import Store

    now = datetime(2026, 9, 5, 9, 0)
    store = Store(paths.db_path())

    def fund(item_id: str) -> Observation:
        return Observation(
            source="beam",
            source_item_id=item_id,
            title=f"Fund {item_id}",
            author="Wer Auch Immer",
            match_reason=MatchReason.GENRE_CATEGORY,
            price_cents=399,
            blurb="Ein Schiff, allein im Dunkeln. " * 20,
            url=f"https://beam.invalid/{item_id}",
        )

    run_id = store.start_run("test", "cli", now)
    store.append(run_id, "test", [fund("alt"), fund("neu")], now)
    store.put_rating(
        "item:beam:alt",
        stars=4,
        confidence="belegt",
        reason="Passt.",
        profile_version=load_leseprofil()[1],
        now=now,
        origin=BY_MODEL,
        pitch="Kurz und gut.",
    )

    class Stub:
        def __init__(self) -> None:
            self.calls: list[Observation] = []

        def rate(self, observation: Observation) -> Rating:
            self.calls.append(observation)
            return Rating(
                stars=4,
                reason="Passt.",
                confidence="belegt",
                profile_version=load_leseprofil()[1],
                pitch="Kurz und gut.",
            )

    stub = Stub()
    monkeypatch.setattr(run_module, "build_rater", lambda model: stub)

    assert main(["rate"]) == EXIT_OK
    assert [call.source_item_id for call in stub.calls] == ["neu"]
