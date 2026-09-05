"""Nimmt das Titelbild der README auf.

    uv run python scripts/make_hero.py

Voraussetzung: die Oberfläche läuft (``uv run python -m ebook_watchlist.web``).

Gebaut statt erzeugt: die Szene ist ``scripts/hero.html``, aufgenommen wird
sie mit dem Chrome, der ohnehin auf dem Rechner liegt. Kein Playwright, kein
Browser-Download — eine neue Abhängigkeit für ein einziges Bild wäre teurer
als der Nutzen.

Das Bild zeigt die **echte** Oberfläche mit den echten Daten. Es ist damit
immer so aktuell wie der letzte Aufruf dieses Skripts, und ändert sich die
Seite, ist es mit einem Befehl neu gemacht.
"""

from __future__ import annotations

import os
import subprocess
import sys
import urllib.request
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
SZENE = WURZEL / "scripts" / "hero.html"
ZIEL = WURZEL / "docs" / "bilder" / "hero.png"
OBERFLAECHE = "http://127.0.0.1:8439/vorschlaege"

BREITE, HOEHE = 1600, 900

#: Die Klammern in "ProgramFiles(x86)" sind kein gueltiger Formatname —
#: deshalb die Umgebungsvariablen einzeln nachschlagen statt zu formatieren.
ORTE = (
    ("ProgramFiles", r"Google\Chrome\Application\chrome.exe"),
    ("ProgramFiles(x86)", r"Google\Chrome\Application\chrome.exe"),
    ("LOCALAPPDATA", r"Google\Chrome\Application\chrome.exe"),
    ("ProgramFiles", r"Microsoft\Edge\Application\msedge.exe"),
    ("ProgramFiles(x86)", r"Microsoft\Edge\Application\msedge.exe"),
)


def browser() -> str:
    for variable, rest in ORTE:
        wurzel = os.environ.get(variable)
        if not wurzel:
            continue
        pfad = Path(wurzel) / rest
        if pfad.exists():
            return str(pfad)
    raise SystemExit("weder Chrome noch Edge gefunden")

def oberflaeche_laeuft() -> bool:
    """Sonst zeigt das Bild einen leeren Rahmen — und das fiele erst auf,
    wenn es schon in der README steht."""
    try:
        with urllib.request.urlopen(OBERFLAECHE, timeout=5) as antwort:
            return antwort.status == 200
    except OSError:
        return False


def main() -> int:
    if not oberflaeche_laeuft():
        print(
            f"Die Oberfläche antwortet nicht auf {OBERFLAECHE} — erst "
            "'uv run python -m ebook_watchlist.web --port 8439' starten.",
            file=sys.stderr,
        )
        return 1

    ZIEL.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(  # noqa: S603 - fester Befehl, keine Nutzereingabe
        [
            browser(),
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            f"--window-size={BREITE},{HOEHE}",
            # Zweifache Auflösung: das Bild wird in der README auf halbe
            # Breite skaliert und ist damit auf jedem Bildschirm scharf.
            "--force-device-scale-factor=2",
            "--virtual-time-budget=4000",
            f"--screenshot={ZIEL}",
            SZENE.as_uri(),
        ],
        check=True,
        capture_output=True,
    )
    print(f"{ZIEL}  ({ZIEL.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
