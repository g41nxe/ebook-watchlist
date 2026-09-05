"""Titelbilder — einmal geholt, danach lokal (Ticket 15, ADR 20).

Nichts auf diesen Seiten laedt von einem Dritten nach. Ein verlinktes Bild
wuerde dem Shop bei jedem Seitenaufruf mitteilen, welches Buch die Leserin
gerade ansieht; ein einmal geholtes und lokal abgelegtes tut das nicht. Fuer
den Shop ist das ausserdem *weniger* Verkehr, nicht mehr.

Geholt wird nur, wo es sich lohnt: fuer Buecher mit einer ``book``-Zeile, also
solche, zu denen die Leserin eine Beziehung hat (ADR 18) — und fuer Entdeckungen
erst, wenn das Bewertungstor sie durchgelassen hat. Fuer jede Entdeckung ein
Bild zu ziehen waeren dreihundert Anfragen pro Lauf statt einer Handvoll; fuer
die zwanzig, die uebrig bleiben, sind es zwanzig.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import urlsplit

from .http import FetchError, HttpClient, NotFound, RateLimited

#: Bildformate, die ein Browser ohne Weiteres darstellt. Alles andere wird nicht
#: abgelegt: was wir nicht anzeigen koennen, muessen wir auch nicht speichern.
_SUFFIXES = {".jpg": ".jpg", ".jpeg": ".jpg", ".png": ".png", ".webp": ".webp", ".gif": ".gif"}

#: Ein Bild unter dieser Groesse ist praktisch immer ein Platzhalter — Shopware
#: liefert ein 1x1-Pixel, solange das echte Bild fehlt.
MIN_BYTES = 1024


def _suffix(url: str) -> str:
    match = re.search(r"(\.[A-Za-z]{3,4})(?:$|[?#])", urlsplit(url).path)
    return _SUFFIXES.get((match.group(1) if match else "").lower(), ".jpg")


def file_name(key: int | str, url: str) -> str:
    """``17-3f9a2b.jpg`` — oder ``beam-632330-3f9a2b.jpg``.

    Der Schluessel macht die Datei auffindbar, der Hash der Adresse sorgt
    dafuer, dass ein gewechseltes Cover eine neue Datei bekommt statt die alte
    still zu ueberschreiben — und dass ein alter Verweis nie auf ein anderes
    Bild zeigt.

    Eine Buch-Id, wo es eine gibt; sonst ``quelle-nummer``. Eine Entdeckung hat
    keine ``book``-Zeile (ADR 18), und der Name muss trotzdem eindeutig sein und
    sich ohne Datenbank ausrechnen lassen: die Seite prueft damit einfach, ob
    die Datei schon daliegt, statt den Namen irgendwo zu speichern.
    """
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:6]
    return f"{key}-{digest}{_suffix(url)}"


class CoverStore:
    """Der Ordner mit den Titelbildern."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def path(self, name: str) -> Path:
        return self.directory / name

    def has(self, name: str) -> bool:
        return self.path(name).is_file()

    def fetch(self, client: HttpClient, key: int | str, url: str) -> str | None:
        """Das Bild holen, falls es noch nicht daliegt. Gibt den Dateinamen zurueck.

        Ein fehlgeschlagener Bilddownload ist kein Grund, einen Lauf scheitern zu
        lassen — ein Buch ohne Bild ist ein Buch mit einem Platzhalter. Nur eine
        Drosselung wird durchgereicht: da hat der Shop ausdruecklich Halt gesagt,
        und das gilt fuer alles Weitere mit (ADR 7).
        """
        name = file_name(key, url)
        if self.has(name):
            return name
        try:
            data = client.get_bytes(url)
        except RateLimited:
            raise
        except (FetchError, NotFound):
            return None
        if len(data) < MIN_BYTES:
            return None
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path(name).write_bytes(data)
        return name
