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


def file_name(url: str) -> str:
    """``3f9a2b4c.jpg`` — der Name ist die Adresse, gehasht.

    **Keine Buch-Id im Namen**, und das ist der Punkt: dasselbe Bild ist eine
    Datei, gleichgueltig ob es an einem Vorschlag oder an einer ``book``-Zeile
    haengt. Ein Vorschlag hat keine Buch-Id (ADR 18) — waere sie Teil des
    Namens, wuerde dasselbe Cover ein zweites Mal geholt, sobald aus dem
    Vorschlag ein Buch wird.

    Der Hash sorgt ausserdem dafuer, dass ein gewechseltes Cover eine neue
    Datei bekommt statt die alte still zu ueberschreiben — und dass ein alter
    Verweis nie auf ein anderes Bild zeigt.

    Und weil der Name sich allein aus der Adresse ergibt, kann die Oberflaeche
    ihn ausrechnen und nachsehen, ob die Datei daliegt, statt ihn fuer jede
    Beobachtung zu speichern.
    """
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    return f"{digest}{_suffix(url)}"


class CoverStore:
    """Der Ordner mit den Titelbildern."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def path(self, name: str) -> Path:
        return self.directory / name

    def has(self, name: str) -> bool:
        return self.path(name).is_file()

    def fetch(self, client: HttpClient, url: str) -> str | None:
        """Das Bild holen, falls es noch nicht daliegt. Gibt den Dateinamen zurueck.

        Ein fehlgeschlagener Bilddownload ist kein Grund, einen Lauf scheitern zu
        lassen — ein Buch ohne Bild ist ein Buch mit einem Platzhalter. Nur eine
        Drosselung wird durchgereicht: da hat der Shop ausdruecklich Halt gesagt,
        und das gilt fuer alles Weitere mit (ADR 7).
        """
        name = file_name(url)
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
