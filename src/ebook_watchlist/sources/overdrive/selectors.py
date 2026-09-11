"""Jeder OverDrive-spezifische String an einer Stelle (ADR 7).

Dieselbe Rolle wie ``onleihe/selectors.py``, nur tragen die Konstanten hier
Pfade, Abfrageparameter und Feldnamen statt CSS-Selektoren: OverDrive liefert
den Katalog als JSON. Baut OverDrive um, ist dieses Modul der ganze Diff.

Recherche: ``docs/research/overdrive-interface.md``.
"""

from __future__ import annotations

#: Die JSON-Schnittstelle. Die Seite ``voebb.overdrive.com`` baut ihre Treffer
#: im Browser zusammen und traegt im HTML keine einzige Trefferkarte; dieselben
#: Daten stehen hier ohne Umweg und ohne Schluessel.
BASE = "https://thunder.api.overdrive.com/v2/"

#: Welche Einrichtung. Steht auf jeder Seite der Instanz als
#: ``window.OverDrive.libraryKey``.
LIBRARY = "voebb"

#: Wohin die Leserin klickt. Nicht die Schnittstelle — eine API-Adresse ist
#: fuer einen Menschen keine Auskunft.
TITLE_URL = "https://voebb.overdrive.com/media/{title_id}"

SEARCH_PATH = "libraries/{library}/media"
TITLE_PATH = "libraries/{library}/media/{title_id}"

#: Nur deutsche EPUB-E-Books, wie bei der Onleihe (``media: [ebook]``).
#: ``ebook-epub-adobe`` ist das Format, das die Leserin auf einem E-Reader
#: oeffnen kann; ``ebook-overdrive`` ist der Browser-Leser derselben Ausgabe.
SEARCH_PARAMS: dict[str, str] = {
    "format": "ebook-epub-adobe",
    "language": "de",
}

#: Wie viele Treffer je Seite. Thunder erlaubt bis 100 und antwortet darueber
#: mit 400; zwanzig reicht fuer eine Zuordnung und haelt die Antwort klein.
PER_PAGE = 20

#: Der Selbsttest. Ein Titel, den diese Bibliothek fuehrt — geprueft wird, dass
#: die Felder noch da sind, nie welche Werte sie tragen.
PROBE_TITLE_ID = "3222096"
PROBE_QUERY = "Der Zeitenläufer"
