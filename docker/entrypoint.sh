#!/bin/sh
# Oberflaeche im Vordergrund, Lauf nebenher.
#
# Es gibt bewusst keinen eingebauten Zeitplaner (ADR 4) — im Container gibt es
# aber auch keinen Wirt, der hineinruft: Docker Desktop laeuft erst ab der
# Anmeldung, eine Aufgabe um 06:00 fiele ins Leere. Also taktet der Container
# sich selbst.
#
# Erst laufen, dann schlafen: nach einer Pause holt der Container damit sofort
# nach, was liegen blieb — dieselbe Rolle wie `Persistent=true` beim
# systemd-Timer.
#
# ponytail: fester Abstand statt fester Uhrzeit. Ein echter Zeitplaner im
# Container braeuchte einen Prozessverwalter, und der Lauf ist
# zeitplanunabhaengig: er vergleicht gegen die letzte Aufzeichnung, nie gegen
# "gestern" (docs/betrieb.md). Wer eine feste Uhrzeit braucht, nimmt supercronic.
set -e

PYTHON=/app/.venv/bin/python

# `|| true`: ein gescheiterter Lauf — ausgefallene Quelle, kaputte
# Konfiguration — darf die Schleife nicht beenden. Der naechste versucht es neu,
# und der Tagesbericht nennt den Fehler ohnehin.
# Nur, wenn der letzte Lauf lange genug her ist. Sonst kostet jedes
# `docker compose up` einen vollen Lauf gegen die echten Quellen — an einem
# Nachmittag mit fuenf Neubauten waren das fuenf Laeufe in 25 Minuten, und in
# der Preisgeschichte jedes Buchs stehen sie bis heute. Der Lauf selbst nimmt
# das nicht uebel (er vergleicht gegen die letzte Aufzeichnung, nie gegen
# "gestern"), die Shops moeglicherweise schon.
#
# Zwanzig statt vierundzwanzig Stunden: sonst schoebe sich der taegliche Lauf
# bei jedem Neustart um die angebrochene Wartezeit nach hinten.
faellig() {
  "$PYTHON" - <<'PY'
import sys
from datetime import datetime, timedelta
from ebook_watchlist import paths
from ebook_watchlist.config import load_profile
from ebook_watchlist.store import ENTRY_TRIGGER, Store

# Ohne Eintraege: ein enger Lauf und ein nachgeladener Klappentext schreiben
# ebenfalls eine Zeile, sind aber kein Rundgang. Zaehlten sie mit, fiele der
# taegliche Lauf aus, weil die Leserin abends einmal "nachsehen" gedrueckt hat.
laeufe = Store(paths.db_path()).recent_runs(load_profile().slug, limit=20)
letzter = next((r for r in laeufe if r.trigger != ENTRY_TRIGGER), None)
frisch = letzter is not None and letzter.started_at is not None and (
    datetime.now() - letzter.started_at < timedelta(hours=20)
)
if frisch:
    print(f"Lauf uebersprungen — der letzte ist von {letzter.started_at:%d.%m. %H:%M}.")
sys.exit(1 if frisch else 0)
PY
}

(
  while true; do
    if faellig; then
      "$PYTHON" -m ebook_watchlist.run --trigger cron || true
    fi
    sleep 86400
  done
) &

# `exec`, damit die Oberflaeche die Signale von `docker stop` selbst bekommt
# statt einer Shell dazwischen. Die Hintergrundschleife wird dann von tini
# eingesammelt (`init: true` in der Compose-Datei).
exec "$PYTHON" -m ebook_watchlist.web
