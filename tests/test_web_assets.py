"""Was die Seite ausliefert, muss ein Browser auch zeichnen koennen.

Anlass: im Favicon stand ein XML-Kommentar mit ``--color-accent`` darin. Zwei
Bindestriche hintereinander sind in einem XML-Kommentar verboten, also war die
Datei nicht mehr wohlgeformt — und das Zeichen der Anwendung war in der
Kopfzeile ein leeres Kaestchen. Kein Test schlug an, kein Bau meckerte: SVG
faellt still aus.
"""

from __future__ import annotations

import xml.dom.minidom
from pathlib import Path

import pytest

ASSETS = Path(__file__).resolve().parents[1] / "src" / "ebook_watchlist" / "web" / "assets"


@pytest.mark.parametrize("svg", sorted(ASSETS.glob("*.svg")), ids=lambda p: p.name)
def test_every_delivered_svg_is_well_formed(svg: Path) -> None:
    xml.dom.minidom.parseString(svg.read_bytes().decode("utf-8"))
