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
import shutil
import subprocess
from collections.abc import Sequence
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

# Die Herkunft steht in ``ratings`` — der Store braucht sie und darf
# dieses Modul nicht importieren.


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


#: Wieviele Bücher höchstens in einen Aufruf gehen. Der Maßstab ist der weitaus
#: größte Teil eines Prompts — das Buch selbst sind ein paar Zeilen —, also spart
#: ein Bündel nicht ein paar Prozent, sondern den Großteil. Zwanzig, weil eine
#: Antwort, die für zwanzig Bücher je eine belegte Begründung liefern soll,
#: lang genug ist.
BATCH_SIZE = 20

_HOW_TO_ANSWER = (
    "Erfinde nichts. Was der Klappentext nicht hergibt, ist nicht belegt — "
    "dann ist die confidence 'vermutet' und die Begründung sagt das."
)


def _facts(observation: Observation) -> list[str]:
    """Die *öffentlichen* Angaben zu einem Buch — mehr nicht.

    Keine Watchlist, kein Besitz, keine Identität der Leserin (ADR 19). Eine
    Stelle, damit Einzel- und Bündelprompt nicht auseinanderlaufen.
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
    return facts


def prompt_for(observation: Observation, rubric: str) -> str:
    """Was das Modell zu einem einzelnen Buch zu sehen bekommt.

    Dass der Klappentext abgeschnitten ist, wird ausdrücklich gesagt. Ein Modell,
    das nicht weiß, wie dünn seine Grundlage ist, gibt zu sichere Urteile ab.
    """
    facts = _facts(observation)

    return (
        "Du bewertest ein Buch gegen den folgenden Maßstab. Halte dich strikt "
        "daran, auch an die Regeln für Begründungen.\n\n"
        f"--- MASSSTAB ---\n{rubric}\n--- ENDE MASSSTAB ---\n\n"
        f"--- BUCH ---\n" + "\n".join(facts) + "\n--- ENDE BUCH ---\n\n"
        "Antworte ausschließlich mit JSON in genau dieser Form:\n"
        '{"stars": <0-5>, "confidence": "belegt|teils|vermutet", '
        '"reason": "<ein Satz, der eine Achse benennt und einen Beleg nennt>"}\n\n'
        + _HOW_TO_ANSWER
    )


def prompt_for_many(observations: Sequence[Observation], rubric: str) -> str:
    """Ein Aufruf für mehrere Bücher.

    Der Maßstab geht einmal raus statt einmal je Buch — er ist der weitaus
    größte Teil des Prompts. Jedes Buch bekommt eine Nummer, und die Antwort
    wird darüber zugeordnet: ohne Kennung liesse sich eine Antwort, die ein Buch
    auslässt oder umsortiert, nicht mehr sicher zuordnen.
    """
    blocks = [
        f"--- BUCH {number} ---\n" + "\n".join(_facts(observation))
        for number, observation in enumerate(observations, start=1)
    ]

    return (
        f"Du bewertest {len(observations)} Bücher gegen den folgenden Maßstab. "
        "Halte dich strikt daran, auch an die Regeln für Begründungen. Beurteile "
        "jedes Buch für sich; die Reihenfolge sagt nichts über seine Passung.\n\n"
        f"--- MASSSTAB ---\n{rubric}\n--- ENDE MASSSTAB ---\n\n"
        + "\n\n".join(blocks)
        + "\n--- ENDE BÜCHER ---\n\n"
        "Antworte ausschließlich mit JSON in genau dieser Form, mit der Nummer "
        "des Buches als Schlüssel:\n"
        '{"1": {"stars": <0-5>, "confidence": "belegt|teils|vermutet", '
        '"reason": "<ein Satz, der eine Achse benennt und einen Beleg nennt>"}, '
        '"2": {…}}\n\n'
        + _HOW_TO_ANSWER
    )


def parse_many(
    text: str, observations: Sequence[Observation], version: int
) -> dict[tuple[str, str], Rating]:
    """Die Antwort auf ein Bündel, buchweise gelesen.

    **Ein unbrauchbarer Eintrag kostet ein Buch, nicht das Bündel.** Ohne das
    machte eine einzige krumme Zeile zwanzig Bücher unbewertet — der Sinn der
    Bündelung wäre dahin, und der Schaden wäre zwanzigmal so groß wie beim
    Einzelaufruf.

    Was fehlt, fehlt: der Aufrufer behandelt jedes Buch ohne Urteil als
    unbewertet und zeigt es trotzdem.
    """
    match = re.search(r"\{.*\}", text, re.S)
    if match is None:
        raise RatingUnavailable("Antwort enthält kein JSON")
    try:
        data = json.loads(match.group(0))
    except ValueError as exc:
        raise RatingUnavailable(f"Antwort ist kein gültiges JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise RatingUnavailable("Antwort ist kein Objekt mit Buchnummern")

    ratings: dict[tuple[str, str], Rating] = {}
    for number, observation in enumerate(observations, start=1):
        entry = data.get(str(number))
        if not isinstance(entry, dict):
            continue
        try:
            ratings[observation.key] = parse_answer(json.dumps(entry), version)
        except RatingUnavailable:
            continue
    return ratings


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


def rate_in_batches(
    rater: Rater, observations: Sequence[Observation], *, size: int = BATCH_SIZE
) -> dict[tuple[str, str], Rating]:
    """Bücher bündelweise beurteilen — die eine Stelle, die das Tor benutzt.

    Ein Bewerter, der ``rate_many`` anbietet, wird gebündelt gefragt; wer nur
    ``rate`` kann, wird einzeln gefragt. So bleibt der HTTP-Weg, bei dem ein
    Aufruf fast nichts kostet, unverändert.

    Was nicht zurückkommt, fehlt einfach: der Aufrufer behandelt jedes Buch ohne
    Urteil als unbewertet und zeigt es trotzdem. Auch ein ganzes Bündel, das
    scheitert, kostet deshalb kein einziges Buch die Anzeige.
    """
    ratings: dict[tuple[str, str], Rating] = {}
    many = getattr(rater, "rate_many", None)
    for start in range(0, len(observations), size):
        chunk = list(observations[start : start + size])
        if many is not None:
            try:
                ratings.update(many(chunk))
            except RatingUnavailable:
                continue
            continue
        for observation in chunk:
            try:
                ratings[observation.key] = rater.rate(observation)
            except RatingUnavailable:
                continue
    return ratings


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


#: Der Weg ohne Schlüssel: Claude Code hat bereits eine Anmeldung, und ``-p``
#: führt genau einen Auftrag aus und beendet sich. Es gibt kein Abo-Guthaben
#: für die API (die Console rechnet getrennt ab), also ist das für ein privates
#: Werkzeug auf dem eigenen Rechner der naheliegende Weg. Die Leserin hat
#: bestätigt, dass sie das so nutzen darf.
CLI_NAME = "claude"
#: Ein Buendel von zwanzig braucht laenger als ein einzelnes Buch — die 34
#: Sekunden einer Einzelmessung sind fast ganz Startkosten, aber die Denkzeit
#: waechst mit jedem Buch. Grosszuegig, weil eine Zeitueberschreitung hier das
#: ganze Buendel unbewertet macht.
CLI_TIMEOUT = 300.0


@dataclass(slots=True)
class ClaudeCodeRater:
    """Fragt die lokal angemeldete Claude-Code-Installation statt der API.

    Kein Schlüssel, kein Guthaben, keine zweite Anmeldung. Dafür ein
    Unterprozess je Buch, und der ist **teuer**: eine Messung an einem echten
    Titel ergab 34 Sekunden — gegenüber wenigen Sekunden für einen POST.

    Das ist tragbar, weil vor dem Tor schon die Preisregel steht: es sieht nur,
    was ohnehin gemeldet würde, und jedes Buch wird genau einmal beurteilt. Der
    Alltag sind einzelne Titel, nicht vierzig — ``rating_budget`` ist die Bremse
    gegen den einmaligen Rückstand, keine Tageserwartung. Genau dieser Rückstand
    ist aber der Fall, in dem der Unterschied weh tut: wer ihn zügig abarbeiten
    will, setzt einen Schlüssel.

    ``--output-format json`` liefert eine Hülle mit dem Ergebnis in ``result``;
    kommt sie nicht, wird die rohe Ausgabe gelesen. Beides landet in derselben
    Auswertung wie die API-Antwort, damit es nur *eine* Stelle gibt, die eine
    Antwort in Sterne übersetzt.
    """

    executable: str = CLI_NAME
    timeout: float = CLI_TIMEOUT
    rubric: str = ""
    version: int = 0

    def __post_init__(self) -> None:
        if not self.rubric:
            self.rubric, self.version = load_rubric()

    def rate(self, observation: Observation) -> Rating:
        return parse_answer(self._ask(prompt_for(observation, self.rubric)), self.version)

    def rate_many(
        self, observations: Sequence[Observation]
    ) -> dict[tuple[str, str], Rating]:
        """Ein Aufruf für bis zu :data:`BATCH_SIZE` Bücher.

        Der eigentliche Gewinn: der Maßstab geht einmal raus statt einmal je
        Buch. Die 34 Sekunden eines Aufrufs sind zudem fast ganz Startkosten
        des Unterprozesses, nicht Denkzeit — zwanzig Bücher kosten kaum mehr
        als eines.
        """
        if not observations:
            return {}
        answer = self._ask(prompt_for_many(observations, self.rubric))
        return parse_many(answer, observations, self.version)

    def _ask(self, prompt: str) -> str:
        command = [self.executable, "-p", prompt, "--output-format", "json"]
        try:
            completed = subprocess.run(  # noqa: S603 - fester Befehl, kein Shell
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
            )
        except FileNotFoundError as exc:
            raise RatingUnavailable(f"{self.executable} nicht gefunden") from exc
        except subprocess.TimeoutExpired as exc:
            raise RatingUnavailable(
                f"{self.executable} antwortete nicht in {self.timeout}s"
            ) from exc
        if completed.returncode != 0:
            detail = (completed.stderr or "").strip().splitlines()
            raise RatingUnavailable(
                f"{self.executable} endete mit {completed.returncode}"
                + (f": {detail[-1]}" if detail else "")
            )
        return _cli_text(completed.stdout)


def _cli_text(stdout: str) -> str:
    """Die Antwort aus der JSON-Hülle — oder die rohe Ausgabe.

    Die Hülle kann sich ändern; auf ihr Format zu bestehen hiesse, an einer
    fremden Version zu hängen. Fehlt sie oder sieht sie anders aus, geht der
    Text unverändert weiter und ``parse_answer`` sucht sich das JSON darin.
    """
    try:
        envelope = json.loads(stdout)
    except (ValueError, TypeError):
        return stdout
    if isinstance(envelope, dict):
        result = envelope.get("result")
        if isinstance(result, str):
            return result
    return stdout


def build_rater(model: str | None = None) -> Rater | None:
    """Der Bewerter, falls einer möglich ist — sonst ``None``.

    Zwei Wege, in dieser Reihenfolge:

    1. **Ein API-Schlüssel in der Umgebung.** Schneller, weil ein POST statt
       eines Unterprozesses, und der Weg für einen Rechner ohne Claude Code.
    2. **Die lokal angemeldete Claude-Code-Installation** über ``claude -p``.
       Kein Schlüssel, kein zusätzliches Guthaben — API-Zugang ist in keinem
       Claude-Abo enthalten, die Console rechnet getrennt ab.

    Der Schlüssel geht vor, wo beides da ist: wer ihn setzt, hat sich für ihn
    entschieden. Ist keiner von beiden verfügbar, ist das **kein Fehler**,
    sondern der Zustand ohne Tor — alles bleibt unbewertet und wird gezeigt.
    """
    try:
        rubric, version = load_rubric()
    except RatingUnavailable:
        return None

    key = os.environ.get(KEY_ENV)
    if key:
        return ModelRater(
            api_key=key, model=model or DEFAULT_MODEL, rubric=rubric, version=version
        )

    executable = shutil.which(CLI_NAME)
    if executable:
        return ClaudeCodeRater(executable=executable, rubric=rubric, version=version)
    return None
