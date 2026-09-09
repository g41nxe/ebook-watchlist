"""Die Startseite unter ``/`` und der Umzug der Übersicht nach ``/uebersicht`` (Issue #5)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ebook_watchlist.web import create_app


@pytest.fixture
def client(data_dir: Path) -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


# --- Der Umzug --------------------------------------------------------------


def test_the_dashboard_lives_at_uebersicht(client: TestClient) -> None:
    response = client.get("/uebersicht")

    assert response.status_code == 200
    assert "Noch kein Lauf verzeichnet" in response.text


def test_the_navigation_points_at_the_new_address_and_has_no_start_entry(
    client: TestClient,
) -> None:
    """Fünf Punkte brechen auf 375 px um — der Weg nach Hause ist das Zeichen."""
    body = client.get("/uebersicht").text

    assert 'href="/uebersicht"' in body
    assert ">Start<" not in body


def test_the_emblem_and_the_name_lead_home(client: TestClient) -> None:
    body = client.get("/uebersicht").text

    assert re.search(r'<a href="/"[^>]*>\s*<img', body), "das Zeichen führt nicht auf /"
    assert re.search(r'<a href="/"[^>]*>Buchfink</a>', body), "der Name führt nicht auf /"
