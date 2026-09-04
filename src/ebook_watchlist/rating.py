"""Das Bewertungstor: passt dieses Buch zur Leserin? (ADR 19, Ticket 12)

Bewertet wird gegen ``docs/leseprofil.md`` — den Maßstab, den die Leserin selbst
geschrieben hat, mitsamt seiner Version. Ein Buch wird **einmal** beurteilt; ein
Lauf, der es wiedersieht, kostet keinen Aufruf mehr. Erst eine neue
Maßstabsversion macht die Urteile ungültig, und das ist die eine Änderung, bei
der das auch richtig ist.

**Das Tor scheitert nie zu.** Kein Schlüssel, kein Netz, eine Absage, eine
unlesbare Antwort: das Buch gilt als unbewertet und wird trotzdem angezeigt. Ein
Tor, das im Zweifel schließt, verschluckt Neuzugänge stillschweigend — das eine
Verhalten, das dieses Werkzeug nicht haben darf (ADR 7, ADR 15).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import requests

from .cleaning import is_truncated
from .models import Observation
from .reasons import THEMA, thema_name

RUBRIC_PATH = Path(__file__).resolve().parents[2] / "docs" / "leseprofil.md"
_VERSION = re.compile(r"Maßstabsversion:\s*(\d+)", re.IGNORECASE)

#: Voreinstellung. Ein beschränktes Urteil gegen einen mitgelieferten Maßstab —
#: dafür ist das kleinste Modell das richtige.
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
#: Der Schlüssel kommt aus der Umgebung, bewusst und nur von dort (Ticket 20).
#: ADR 6 sieht eine Secrets-Datei für die Bibliothekskennung vor, weil ein Lauf
#: sich dort *anmelden* muss und die Kennung der Leserin gehört. Dieser
#: Schlüssel gehört dem Host, nicht dem Profil: ein Cron-Job setzt ihn, und
#: eine zweite Fundstelle im Datenverzeichnis wäre ein weiterer Ort, an dem ein
#: Geheimnis versehentlich in ein Backup gerät.
KEY_ENV = "ANTHROPIC_API_KEY"

#: Unter wie vielen Sternen ein Vorschlag gar nicht erst erscheint. Großzügig
#: gesetzt, nicht vorsichtig: wenige gut passende Vorschläge schlagen viele
#: unpassende, und ein leerer Stapel ist ein gutes Ergebnis (ADR 19).
DEFAULT_THRESHOLD = 3


class RatingUnavailable(Exception):
    """Es konnte nicht bewertet werden. Kein Fehler des Buches."""


@dataclass(frozen=True, slots=True)
class Rating:
    stars: int
    reason: str
    #: ``belegt`` | ``teils`` | ``vermutet`` — der Maßstab verlangt sie, weil ein
    #: Urteil über einen 219 Zeichen langen Anriss etwas anderes ist als eines
    #: über ein gelesenes Buch.
    confidence: str
    rubric_version: int

    def passes(self, threshold: int) -> bool:
        return self.stars >= threshold


def rubric_version(text: str) -> int:
    match = _VERSION.search(text)
    if match is None:
        raise RatingUnavailable("docs/leseprofil.md nennt keine Maßstabsversion")
    return int(match.group(1))


def load_rubric(path: Path | None = None) -> tuple[str, int]:
    target = path or RUBRIC_PATH
    try:
        text = target.read_text(encoding="utf-8")
    except OSError as exc:
        raise RatingUnavailable(f"Maßstab nicht lesbar: {exc}") from exc
    return text, rubric_version(text)


def prompt_for(observation: Observation, rubric: str) -> str:
    """Was das Modell zu sehen bekommt.

    Der Maßstab und die *öffentlichen* Angaben zum Buch — mehr nicht. Keine
    Watchlist, kein Besitz, keine Identität der Leserin (ADR 19).

    Dass der Klappentext abgeschnitten ist, wird ausdrücklich gesagt. Ein Modell,
    das nicht weiß, wie dünn seine Grundlage ist, gibt zu sichere Urteile ab.
    """
    facts = [f"Titel: {observation.title}"]
    if observation.subtitle:
        facts.append(f"Untertitel: {observation.subtitle}")
    facts.append(f"Autor:in: {observation.author or 'unbekannt'}")
    if observation.series:
        facts.append(f"Reihe: {observation.series}")
    if observation.category:
        # "Thema", nicht "Regal des Shops": das Wort, das die Leserin sieht, ist
        # auch hier das richtige — und der lesbare Name sagt dem Modell mehr als
        # ein Pfad aus dem Shop (Ticket 14, Ticket 20).
        facts.append(f"{THEMA}: {thema_name(observation.category)}")
    if observation.price_cents is not None:
        facts.append(f"Preis: {observation.price_cents / 100:.2f} EUR")
    if observation.blurb:
        cut = " (vom Shop abgeschnitten)" if is_truncated(observation.blurb) else ""
        facts.append(f"Klappentext{cut}: {observation.blurb}")

    return (
        "Du bewertest ein Buch gegen den folgenden Maßstab. Halte dich strikt "
        "daran, auch an die Regeln für Begründungen.\n\n"
        f"--- MASSSTAB ---\n{rubric}\n--- ENDE MASSSTAB ---\n\n"
        f"--- BUCH ---\n" + "\n".join(facts) + "\n--- ENDE BUCH ---\n\n"
        "Antworte ausschließlich mit JSON in genau dieser Form:\n"
        '{"stars": <0-5>, "confidence": "belegt|teils|vermutet", '
        '"reason": "<ein Satz, der eine Achse benennt und einen Beleg nennt>"}\n\n'
        "Erfinde nichts. Was der Klappentext nicht hergibt, ist nicht belegt — "
        "dann ist die confidence 'vermutet' und die Begründung sagt das."
    )


def parse_answer(text: str, version: int) -> Rating:
    """Die Antwort des Modells, streng gelesen.

    Eine unlesbare Antwort ist kein Anlass zu raten: sie fuehrt dazu, dass das
    Buch unbewertet bleibt und trotzdem erscheint.
    """
    match = re.search(r"\{.*\}", text, re.S)
    if match is None:
        raise RatingUnavailable("Antwort enthält kein JSON")
    try:
        data = json.loads(match.group(0))
    except ValueError as exc:
        raise RatingUnavailable(f"Antwort ist kein gültiges JSON: {exc}") from exc

    try:
        stars = int(data["stars"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RatingUnavailable("Antwort nennt keine Sterne") from exc
    if not 0 <= stars <= 5:
        raise RatingUnavailable(f"Sterne außerhalb 0-5: {stars}")

    confidence = str(data.get("confidence", "")).strip().lower()
    if confidence not in {"belegt", "teils", "vermutet"}:
        raise RatingUnavailable(f"unbekannte confidence {confidence!r}")

    reason = str(data.get("reason", "")).strip()
    if not reason:
        raise RatingUnavailable("Antwort nennt keine Begründung")

    return Rating(stars=stars, reason=reason, confidence=confidence, rubric_version=version)


class Rater(Protocol):
    """Was der Lauf braucht. Absichtlich klein, damit ein Stub genügt."""

    def rate(self, observation: Observation) -> Rating: ...


@dataclass(slots=True)
class ModelRater:
    """Fragt ein Modell. Keine eigene Bibliothek — die Messages-API ist ein POST."""

    api_key: str
    model: str = DEFAULT_MODEL
    timeout: float = 30.0
    rubric: str = ""
    version: int = 0
    session: requests.Session | None = None

    def __post_init__(self) -> None:
        if not self.rubric:
            self.rubric, self.version = load_rubric()
        if self.session is None:
            self.session = requests.Session()

    def rate(self, observation: Observation) -> Rating:
        payload = {
            "model": self.model,
            "max_tokens": 300,
            "messages": [{"role": "user", "content": prompt_for(observation, self.rubric)}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        }
        try:
            response = self.session.post(
                API_URL, json=payload, headers=headers, timeout=self.timeout
            )
        except requests.RequestException as exc:
            raise RatingUnavailable(f"Modell nicht erreichbar: {exc}") from exc
        if response.status_code != 200:
            raise RatingUnavailable(f"Modell antwortete {response.status_code}")
        try:
            blocks = response.json()["content"]
            text = "".join(block.get("text", "") for block in blocks)
        except (ValueError, KeyError, TypeError) as exc:
            raise RatingUnavailable(f"unerwartete Antwortform: {exc}") from exc
        return parse_answer(text, self.version)


def build_rater(model: str | None = None) -> Rater | None:
    """Der Bewerter, falls einer möglich ist — sonst ``None``.

    Ohne Schlüssel ist das kein Fehler, sondern der Zustand ohne Tor: alles
    bleibt unbewertet und wird gezeigt.
    """
    key = os.environ.get(KEY_ENV)
    if not key:
        return None
    try:
        rubric, version = load_rubric()
    except RatingUnavailable:
        return None
    return ModelRater(api_key=key, model=model or DEFAULT_MODEL, rubric=rubric, version=version)
