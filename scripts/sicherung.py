"""Eine konsistente Kopie der Datenbank, im Container aufgerufen.

    docker compose exec buchfink /app/.venv/bin/python scripts/sicherung.py

Nicht `cp`: eine SQLite-Datenbank im WAL-Modus besteht aus drei Dateien, und
waehrend der Lauf schreibt, ist eine Dateikopie irgendein Zwischenzustand.
``Connection.backup`` nimmt stattdessen einen konsistenten Stand, auch bei
laufenden Schreibern — dasselbe Verfahren, mit dem die Uebergabe vom alten
Rechner gemacht wurde.

Eine eigene Datei statt eines ``python -c``-Einzeilers, weil dessen
Anfuehrungszeichen in jeder Shell anders zerfallen: Git Bash uebersetzt
``/app/...`` in einen Windows-Pfad, PowerShell schluckt die inneren
Anfuehrungszeichen. Hier gibt es nichts zu zitieren.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

QUELLE = Path("/data/snapshots.db")
#: Im Container auf `./data-sicherung` des Wirts eingehaengt (docker-compose.yml).
ZIEL_VERZEICHNIS = Path("/sicherung")


def main(argv: list[str] | None = None) -> int:
    argumente = argv if argv is not None else sys.argv[1:]
    ziel_verzeichnis = Path(argumente[0]) if argumente else ZIEL_VERZEICHNIS

    if not QUELLE.exists():
        print(f"{QUELLE} gibt es nicht", file=sys.stderr)
        return 1
    if not ziel_verzeichnis.is_dir():
        print(
            f"{ziel_verzeichnis} ist nicht eingehaengt — fehlt der Eintrag in "
            "docker-compose.yml?",
            file=sys.stderr,
        )
        return 1

    ziel = ziel_verzeichnis / f"snapshots-{datetime.now():%Y-%m-%d}.db"
    quelle = sqlite3.connect(f"file:{QUELLE}?mode=ro", uri=True)
    try:
        kopie = sqlite3.connect(ziel)
        try:
            quelle.backup(kopie)
            # Die Gegenprobe gehoert dazu: eine Sicherung, die niemand
            # aufmacht, ist eine Behauptung.
            zustand = kopie.execute("PRAGMA integrity_check").fetchone()[0]
            buecher = kopie.execute("select count(*) from book").fetchone()[0]
        finally:
            kopie.close()
    finally:
        quelle.close()

    if zustand != "ok":
        print(f"Sicherung ist beschaedigt: {zustand}", file=sys.stderr)
        return 1

    print(f"{ziel}  ({ziel.stat().st_size // 1024} KB, {buecher} Buecher, integrity ok)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
