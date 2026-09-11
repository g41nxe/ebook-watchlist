"""Aus OverDrive-JSON Werte machen. Reine Funktionen — kein Netz, keine Config.

Dasselbe Versprechen wie im Onleihe-Parser: Jede Funktion wirft
:class:`SourceStructureError`, sobald die Antwort nicht mehr aussieht wie das,
was die Recherche beschrieben hat. Diese Lautstaerke ist der Zweck — ein still
leeres Ergebnis ist von "heute nichts Neues" nicht zu unterscheiden (ADR 7).

Ein JSON-Feld, das *fehlen darf*, ist etwas anderes als eine Antwort, die nicht
mehr die erwartete Gestalt hat. Ein fehlender Klappentext ist Alltag; eine
Antwort ohne ``items`` ist ein Umbau.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from ...models import Availability
from ..base import SourceStructureError


def payload(text: str) -> dict:
    """Die Antwort als Objekt — oder ein lauter Fehler."""
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise SourceStructureError(f"OverDrive: Antwort ist kein JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SourceStructureError(f"OverDrive: Antwort ist kein Objekt, sondern {type(data)}")
    return data


@dataclass(frozen=True, slots=True)
class Detail:
    """Was OverDrive ueber einen Titel sagt."""

    title: str
    author: str | None
    isbn: str | None
    #: Wie viele Lizenzen die Bibliothek haelt und wie viele davon frei sind.
    owned_copies: int
    available_copies: int
    #: Wie viele Vormerkungen anstehen.
    holds: int
    blurb: str | None = None
    cover_url: str | None = None

    @property
    def availability(self) -> Availability:
        """Verliehen ist nicht dasselbe wie "fuehrt die Bibliothek nicht".

        Ohne eine einzige Lizenz weiss OverDrive ueber diesen Titel nichts zu
        sagen, was eine Verfuegbarkeit waere — das ist ``unknown`` und nicht
        ``unavailable``, denn "verliehen" verspricht, dass er zurueckkommt.
        """
        if self.owned_copies <= 0:
            return Availability.UNKNOWN
        return Availability.AVAILABLE if self.available_copies > 0 else Availability.UNAVAILABLE


def _int(item: dict, field: str) -> int:
    """Eine Zahl, die dasein muss. Fehlt sie, hat sich die Antwort geaendert."""
    wert = item.get(field)
    if not isinstance(wert, int) or isinstance(wert, bool):
        raise SourceStructureError(
            f"OverDrive: Titel {item.get('id')!r} nennt kein {field} (sondern {wert!r})"
        )
    return wert


def _isbn(item: dict) -> str | None:
    """Die ISBN des Formats, das die Leserin wirklich oeffnen kann.

    OverDrive fuehrt dieselbe Ausgabe in mehreren Formaten; ``ebook-kobo``
    traegt gar keine. Genommen wird die erste, die eine nennt — sie ist bei den
    gemessenen Titeln fuer alle Formate dieselbe.
    """
    for format_ in item.get("formats") or []:
        if isinstance(format_, dict) and format_.get("isbn"):
            return str(format_["isbn"])
    return None


def parse_title(item: dict) -> Detail:
    """Ein Titel, so wie er in der Trefferliste und als Einzelabruf steht.

    Beide Wege liefern dieselbe Gestalt — deshalb liest sie auch dieselbe
    Funktion, statt dass zwei Fassungen auseinanderlaufen.
    """
    titel = item.get("title")
    if not isinstance(titel, str) or not titel.strip():
        raise SourceStructureError(f"OverDrive: Titel {item.get('id')!r} hat keinen Titel")
    autor = item.get("firstCreatorName")
    bilder = item.get("covers") or {}
    gross = bilder.get("cover510Wide") or bilder.get("cover300Wide") or {}
    return Detail(
        title=titel.strip(),
        author=str(autor).strip() if autor else None,
        isbn=_isbn(item),
        owned_copies=_int(item, "ownedCopies"),
        available_copies=_int(item, "availableCopies"),
        holds=_int(item, "holdsCount"),
        blurb=str(item["description"]).strip() if item.get("description") else None,
        cover_url=gross.get("href") if isinstance(gross, dict) else None,
    )


def title_id(item: dict) -> str:
    """Woran der Snapshot geschluesselt ist.

    Lieber laut scheitern als eine Identitaet erfinden: eine ausgedachte Nummer
    spaltete die Geschichte eines Titels still in zwei (wie ``require_title_id``
    bei der Onleihe).
    """
    kennung = item.get("id")
    if kennung is None or not str(kennung).strip():
        raise SourceStructureError("OverDrive: ein Treffer ohne id")
    return str(kennung)


@dataclass(frozen=True, slots=True)
class Candidate:
    """Ein Treffer der Suche, so weit die Zuordnung ihn braucht."""

    title: str
    author: str | None
    title_id: str
    #: Die ISBN des Treffers. Sie ist der Grund, warum diese Quelle "Dark
    #: Matter" ueberhaupt findet: der Titel-Normalisierer macht aus
    #: "Dark Matter - der Zeitenlaeufer" ein "dark matter" und aus
    #: "Der Zeitenläufer (Dark Matter)" ein "zeitenlaufer" — die Klammer gilt
    #: ihm als Ausgabenrauschen, hier steht aber der Originaltitel darin.
    isbn: str | None = None


def parse_search(text: str) -> list[Candidate] | None:
    """Die Treffer einer Suche — ``None`` heisst: die Bibliothek fuehrt ihn nicht.

    Kein Treffer ist eine **Antwort**, kein Fehler: der Katalog hat
    nachgesehen. Fehlt dagegen ``items`` ganz, hat sich die Schnittstelle
    geaendert, und das darf nicht wie "nichts gefunden" aussehen (ADR 7).
    """
    data = payload(text)
    items = data.get("items")
    if not isinstance(items, list):
        raise SourceStructureError("OverDrive: Antwort ohne Trefferliste 'items'")
    if not items:
        return None
    gefunden = []
    for item in items:
        if not isinstance(item, dict):
            raise SourceStructureError(f"OverDrive: ein Treffer ist kein Objekt: {item!r}")
        detail = parse_title(item)
        gefunden.append(
            Candidate(
                title=detail.title,
                author=detail.author,
                title_id=title_id(item),
                isbn=detail.isbn,
            )
        )
    return gefunden
