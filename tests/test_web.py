"""The Dashboard, driven through FastAPI's test client — no live server."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ebook_watchlist import paths
from ebook_watchlist.run import main as run_main
from ebook_watchlist.store import Store
from ebook_watchlist.web import create_app


@pytest.fixture
def client(data_dir: Path) -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


def test_an_untouched_installation_says_so_instead_of_looking_broken(
    client: TestClient,
) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Noch kein Lauf verzeichnet" in response.text


def test_the_run_journal_is_shown(client: TestClient) -> None:
    run_main([])
    run_main([])

    body = client.get("/").text

    assert body.count("<tr") >= 3  # header plus two runs
    assert "cli" in body
    assert "ok" in body


def test_a_failing_source_is_named_on_the_dashboard(
    client: TestClient, data_dir: Path
) -> None:
    (data_dir / "fake-source.yaml").write_text("not: a list\n", encoding="utf-8")
    run_main([])

    body = client.get("/").text

    assert "schiefgegangen" in body
    assert "must be a list of items" in body


def test_digests_are_listed_and_servable(client: TestClient, data_dir: Path) -> None:
    run_main([])
    fixture = data_dir / "fake-source.yaml"
    fixture.write_text(
        fixture.read_text(encoding="utf-8").replace("price_cents: 1299", "price_cents: 499"),
        encoding="utf-8",
    )
    run_main([])

    name = f"digest-{datetime.now():%Y-%m-%d}.html"
    assert name in client.get("/").text

    digest = client.get(f"/digest/{name}")
    assert digest.status_code == 200
    assert "Der Schwarm" in digest.text


def test_the_digest_route_is_not_a_file_browser(client: TestClient, data_dir: Path) -> None:
    """The data directory holds the config and the database; only digests are public."""
    (data_dir / "digests").mkdir(exist_ok=True)

    for attempt in [
        "../profile.yaml",
        "..%2Fprofile.yaml",
        "digest-2026-09-04.html/../../snapshots.db",
        "snapshots.db",
        "digest-evil.html",
    ]:
        response = client.get(f"/digest/{attempt}")
        assert response.status_code == 404, attempt


def test_a_missing_digest_is_a_404_not_a_crash(client: TestClient) -> None:
    assert client.get("/digest/digest-2001-01-01.html").status_code == 404


def test_broken_configuration_is_reported_rather_than_a_stack_trace(
    client: TestClient, data_dir: Path
) -> None:
    (data_dir / "profile.yaml").unlink()

    response = client.get("/")

    assert response.status_code == 500
    assert "lässt sich nicht laden" in response.text
    assert "Traceback" not in response.text


def test_the_web_process_never_takes_the_run_lock(client: TestClient) -> None:
    """Killing the dashboard must never be able to strand a Run."""
    from filelock import FileLock

    held = FileLock(str(paths.lock_path()), timeout=0)
    held.acquire()
    try:
        assert client.get("/").status_code == 200
    finally:
        held.release()


# --- Quellen-Zustand (Ticket 03) -------------------------------------------


def test_each_source_gets_a_line_of_its_own(client: TestClient) -> None:
    """Bisher musste die Seite Gesundheit aus Laufergebnissen erraten."""
    run_main([])

    body = client.get("/").text

    assert "Quellen" in body
    assert "zuletzt geprüft" in body


def test_a_paused_source_says_so_rather_than_vanishing(
    client: TestClient, data_dir: Path
) -> None:
    run_main([])
    store = Store(data_dir / "snapshots.db")
    name = store.sources()[0].name
    store.set_enabled(name, False, now=datetime.now())

    body = client.get("/").text

    assert "pausiert" in body
    assert name in body


def test_a_source_broken_for_days_is_marked_as_such(
    client: TestClient, data_dir: Path
) -> None:
    run_main([])
    store = Store(data_dir / "snapshots.db")
    name = store.sources()[0].name
    for _ in range(3):
        store.record_probe(name, ok=False, error="kaputt", now=datetime.now())

    body = client.get("/").text

    assert "seit 3 Prüfungen" in body
