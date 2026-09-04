from __future__ import annotations

import functools
import shutil
import textwrap
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

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


# --- Schema einmal bauen, dann kopieren (Ticket 18) -------------------------
#
# ``create_all`` kostet 0,26 s — elf CREATE TABLE, jedes mit einem Schreibvorgang
# auf die Platte. Bei über hundert Testaufbauten sind das dreißig Sekunden für
# ein Schema, das sich zwischen zwei Tests nie unterscheidet. Eine fertige Datei
# zu kopieren kostet 0,009 s.


@pytest.fixture(scope="session")
def schema_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Eine leere, fertig migrierte Datenbank — einmal je Testlauf."""
    from ebook_watchlist.store import Store

    path = tmp_path_factory.mktemp("schema") / "template.db"
    Store(path)
    return path


@pytest.fixture
def store(tmp_path: Path, schema_template: Path):
    """Ein frischer Store, aus der Vorlage kopiert statt neu gebaut."""
    from ebook_watchlist.store import Store

    target = tmp_path / "snapshots.db"
    shutil.copy(schema_template, target)
    return Store(target)


# --- Fixtures einmal lesen und einmal parsen (Ticket 18) --------------------
#
# Die beam-Seiten sind 200 bis 700 KB. Ein lxml-Durchlauf ueber die
# Trefferseite kostet 0,70 s, und einunddreissig Tests holen sie sich. Die
# Dateien aendern sich nicht, also gehoert das einmal getan.


@functools.cache
def _read(area: str, name: str) -> str:
    return (FIXTURES / area / name).read_text(encoding="utf-8")


@functools.cache
def _tiles(name: str) -> tuple:
    from ebook_watchlist.sources.beam import parse

    return tuple(parse.parse_tiles(_read("beam", name)))


def beam_fixture(name: str) -> str:
    """Der rohe HTML-Text einer beam-Fixture."""
    return _read("beam", name)


def voebb_fixture(name: str) -> str:
    return _read("voebb", name)


@functools.cache
def beam_detail(name: str):
    """Die geparste beam-Detailseite. 720 KB, und mehrere Tests brauchen sie."""
    from ebook_watchlist.sources.beam import parse

    return parse.parse_detail(_read("beam", name))


@functools.cache
def voebb_detail(name: str):
    from ebook_watchlist.sources.voebb import parse

    return parse.parse_detail(_read("voebb", name))


def beam_tiles(name: str) -> list:
    """Die geparsten Kacheln — als frische Liste, damit ein Test sie umsortieren
    darf, ohne die naechsten zu stoeren. Die Kacheln selbst sind unveraenderlich.
    """
    return list(_tiles(name))


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
def data_dir(unseeded_data_dir: Path, schema_template: Path) -> Path:
    """Wie oben, plus der einmalige Import.

    Seit Ticket 05 liest der Lauf seine Konfiguration aus der Datenbank; YAML
    ist Saatgut. Eine Installation ohne Import ist damit ein eigener Zustand,
    und den prüft ``unseeded_data_dir``.

    Das Schema liegt vorher schon da, damit der Import nicht noch einmal elf
    Tabellen anlegen muss.
    """
    from ebook_watchlist.run import main

    shutil.copy(schema_template, unseeded_data_dir / "snapshots.db")
    main(["seed"])
    return unseeded_data_dir
