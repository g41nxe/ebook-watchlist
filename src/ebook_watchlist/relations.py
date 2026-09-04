"""Das Vokabular für Beziehungen und Interessen (ADR 18, Ticket 05).

Beides ist Freitext in der Datenbank und wird hier gegen die Liste der Handler
geprüft, die etwas damit anfangen können. Ein Schlüssel, den niemand bedient,
ist ein Konfigurationsfehler und muss beim Laden laut scheitern: ein Interesse
unter ``autor`` statt ``author`` würde sonst nie abgefragt, und **nichts würde
das sagen**.

Warum nicht als Enum in der Spalte? Weil ein dritter Entdeckungskanal —
Verlag, Reihe, Schlagwort — dann eine Migration kostet statt eines Handlers.
Die Prüfung gehört in den Lader, nicht ins Schema.
"""

from __future__ import annotations

from enum import StrEnum


class RelationKind(StrEnum):
    """Was die Leserin zu einem Buch sagt.

    Mehrere gelten gleichzeitig, und das ist der Normalfall, nicht die
    Ausnahme: *Cold Eternity* ist ``owned`` **und** war ``watching``. Eine
    einzelne Statusspalte hätte das nicht ausdrücken können.
    """

    WATCHING = "watching"
    OWNED = "owned"
    LIKED = "liked"
    DISLIKED = "disliked"
    DISMISSED = "dismissed"


class InterestKey(StrEnum):
    """Wo das Werkzeug nach neuen Büchern sehen soll.

    Referenzautor:in und Thema beantworten dieselbe Frage und sind deshalb eine
    Tabelle. Sie sind die zwei Entdeckungskanäle und erzeugen die zwei
    Entdeckungs-Anlässe.
    """

    AUTHOR = "author"
    THEMA = "thema"


RELATION_KINDS: frozenset[str] = frozenset(kind.value for kind in RelationKind)
INTEREST_KEYS: frozenset[str] = frozenset(key.value for key in InterestKey)

#: ``core`` wird jeden Lauf gefegt, ``extended`` einmal die Woche. Das ist
#: nicht autorenspezifisch — ein Thema könnte genauso wöchentlich laufen —,
#: deshalb steht es in ``details`` und nicht in einer eigenen Spalte (ADR 18).
TIERS: frozenset[str] = frozenset({"core", "extended"})

#: Worauf ein Watchlist-Eintrag eingeschraenkt sein kann. Bewusst die *Art*
#: einer Quelle und nicht ihr Name: wie eine Bibliothek heisst, entscheidet
#: die Konfiguration, und ein Import darf keine Namen erfinden.
RESTRICTIONS: frozenset[str] = frozenset({"library", "shop"})


class ConfigurationError(Exception):
    """Ein Wert, den kein Handler bedient. Laut, nicht geduldet."""


def check_relation_kind(kind: str) -> str:
    if kind not in RELATION_KINDS:
        raise ConfigurationError(
            f"unbekannte Beziehung {kind!r} (bekannt: {', '.join(sorted(RELATION_KINDS))})"
        )
    return kind


def check_interest_key(key: str) -> str:
    if key not in INTEREST_KEYS:
        raise ConfigurationError(
            f"unbekanntes Interesse {key!r} (bekannt: {', '.join(sorted(INTEREST_KEYS))})"
        )
    return key


def check_details(key: str, details: dict) -> dict:
    """Der Beutel wird geprüft, nicht nur die Spalten.

    ``tier: "extendet"`` würde eine wöchentliche Autor:in stillschweigend in die
    tägliche Liste befördern, und ``activ: false`` würde ganz ignoriert. Beides
    sind Tippfehler, die sich nur durch verändertes Verhalten bemerkbar machten
    — die teuerste Art, einen Fehler zu finden (ADR 18).
    """
    unknown = set(details) - {"tier", "sources", "note", "restrict"}
    if unknown:
        raise ConfigurationError(
            f"unbekannte Angaben zu {key!r}: {', '.join(sorted(unknown))} "
            "(bekannt: note, restrict, sources, tier)"
        )
    restrict = details.get("restrict")
    if restrict is not None and restrict not in RESTRICTIONS:
        raise ConfigurationError(
            f"unbekannte Einschraenkung {restrict!r} bei {key!r} "
            f"(bekannt: {', '.join(sorted(RESTRICTIONS))})"
        )
    tier = details.get("tier")
    if tier is not None and tier not in TIERS:
        raise ConfigurationError(
            f"unbekannte Stufe {tier!r} bei {key!r} (bekannt: {', '.join(sorted(TIERS))})"
        )
    sources = details.get("sources")
    if sources is not None and not (
        isinstance(sources, list) and all(isinstance(name, str) for name in sources)
    ):
        raise ConfigurationError(f"'sources' bei {key!r} muss eine Liste von Namen sein")
    return details
