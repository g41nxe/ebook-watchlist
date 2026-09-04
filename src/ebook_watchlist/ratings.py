"""Woher ein Urteil über ein Buch stammt (Ticket 21, ADR 17).

Solange es nur eine Herkunft gab — das Bewertungstor —, war die Frage
entbehrlich. Mit den dreizehn Urteilen aus ``owned.yaml`` und den Sternen, die
die Leserin selbst vergibt, sind es drei, und der Unterschied ist nicht
kosmetisch:

    Eine 4 von der Leserin ist eine Tatsache.
    Eine 4 vom Modell ist ein Vorschlag.

Deshalb gehört die Herkunft in den Schlüssel und nicht in eine Spalte daneben:
beide dürfen zu einem Buch nebeneinander stehen, und keines überschreibt das
andere.

Dieses Modul steht für sich, damit ``store`` es kennt, ohne ``rating`` zu
importieren — dort hängt das Modell dran, und der Store hat damit nichts zu tun.
"""

from __future__ import annotations

from .models import Observation

#: Das Bewertungstor im Lauf (ADR 19).
BY_MODEL = "model"
#: Im Gespräch vergeben, gegen denselben Maßstab — die dreizehn aus
#: ``owned.yaml``. Maschinenurteile, auch wenn sie im Gespräch entstanden.
BY_CONVERSATION = "conversation"
#: Die Leserin selbst.
BY_READER = "reader"

RATING_ORIGINS: frozenset[str] = frozenset({BY_MODEL, BY_CONVERSATION, BY_READER})

#: Was ein Mensch gesagt hat. Verfällt nicht mit einer neuen Maßstabsversion,
#: und wird von keinem Modellurteil überschrieben.
HUMAN_ORIGINS: frozenset[str] = frozenset({BY_READER})

LABELS: dict[str, str] = {
    BY_MODEL: "vom Werkzeug bewertet",
    BY_CONVERSATION: "im Gespräch bewertet",
    BY_READER: "deine Bewertung",
}


def book_subject(book_id: int) -> str:
    """Der Schlüssel, an dem ein Urteil über ein *Buch* hängt.

    Das Tor schlüsselt seine Urteile am Fund (``isbn:…`` oder ``item:…``), weil
    es dreihundert Funde bewertet, von denen die wenigsten je eine Buchzeile
    bekommen (ADR 18). Was die Leserin sagt, gilt dagegen dem Buch: sie vergibt
    ihre Sterne auf der Buchseite, und dieselbe Zahl soll gelten, egal über
    welche Quelle das Buch das nächste Mal auftaucht.
    """
    return f"book:{book_id}"


def subject_of(observation: Observation) -> str:
    """Woran ein Urteil des Tors hängt.

    Die ISBN, wo es eine gibt — dann findet dasselbe Buch sein Urteil auch über
    eine andere Quelle wieder. Sonst der Fund selbst; Bündel und Einzelfolgen
    haben keine ISBN, und für die ist ein Urteil je Quelle ehrlicher als eines,
    das über Titel geraten wäre.
    """
    if observation.isbn:
        return f"isbn:{observation.isbn}"
    return f"item:{observation.source}:{observation.source_item_id}"
