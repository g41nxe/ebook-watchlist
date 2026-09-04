from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

PROFILE_YAML = """
slug: test
name: Testprofil
sources:
  fake:
    fixture: fake-source.yaml
"""

WATCHLIST_YAML = """
- title: Die sieben Schwestern
  author: Lucinda Riley
"""

FAKE_SOURCE_YAML = """
- id: fake-1
  title: Die sieben Schwestern
  author: Lucinda Riley
  availability: unavailable
  reservation_count: 3
- id: fake-2
  title: Der Schwarm
  author: Frank Schätzing
  price_cents: 1299
"""


@pytest.fixture
def unseeded_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Die YAML-Dateien, aber noch kein Import — eine frische Installation."""
    directory = tmp_path / "data"
    directory.mkdir()
    monkeypatch.setenv("EBW_DATA_DIR", str(directory))
    for name, body in (
        ("profile.yaml", PROFILE_YAML),
        ("watchlist.yaml", WATCHLIST_YAML),
        ("fake-source.yaml", FAKE_SOURCE_YAML),
    ):
        (directory / name).write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")
    return directory


@pytest.fixture
def data_dir(unseeded_data_dir: Path) -> Path:
    """Wie oben, plus der einmalige Import.

    Seit Ticket 05 liest der Lauf seine Konfiguration aus der Datenbank; YAML
    ist Saatgut. Eine Installation ohne Import ist damit ein eigener Zustand,
    und den prüft ``unseeded_data_dir``.
    """
    from ebook_watchlist.run import main

    main(["seed"])
    return unseeded_data_dir
