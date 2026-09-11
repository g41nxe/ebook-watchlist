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
(
  while true; do
    "$PYTHON" -m ebook_watchlist.run --trigger cron || true
    sleep 86400
  done
) &

# `exec`, damit die Oberflaeche die Signale von `docker stop` selbst bekommt
# statt einer Shell dazwischen. Die Hintergrundschleife wird dann von tini
# eingesammelt (`init: true` in der Compose-Datei).
exec "$PYTHON" -m ebook_watchlist.web
