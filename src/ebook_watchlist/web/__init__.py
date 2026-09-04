"""The local web application (ADR 3, Phase 2).

``app`` und ``create_app`` werden **verzögert** geladen. Der Grund ist ein
Henne-Ei-Problem, das ein frischer Klon sonst nicht auflösen kann: ``app.py``
baut die Anwendung beim Import und verlangt dabei das gebaute Stylesheet
(ADR 20). ``ebook_watchlist.web.build`` liegt aber *in* diesem Paket, also
führte sein Import zuerst diesen Import aus — und der Bauvorgang scheiterte an
genau den Dateien, die er erzeugen soll. Die Fehlermeldung nannte dann einen
Befehl, der selbst nicht laufen konnte.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - nur für Typprüfer
    from .app import app, create_app

__all__ = ["app", "create_app"]


def __getattr__(name: str):
    if name in __all__:
        # importlib, nicht ``from . import app``: der Untermodulname ist
        # derselbe wie einer der gesuchten Namen, und der kurze Weg riefe
        # dieses ``__getattr__`` erneut auf — bis zum Stapelüberlauf.
        module = importlib.import_module(f"{__name__}.app")
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
