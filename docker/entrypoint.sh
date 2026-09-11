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
# Beim Start ruft die Schleife sofort — und der Lauf entscheidet selbst, ob er
# faellig ist (`MIN_RUN_GAP`, 20 Stunden). Ohne das kostete jedes
# `docker compose up` einen vollen Lauf gegen die echten Quellen; an einem
# Nachmittag mit fuenf Neubauten waren das fuenf Laeufe in 25 Minuten, und in
# der Preisgeschichte jedes Buchs stehen sie bis heute.
#
# Hier steht deshalb keine Zahl: die Regel gehoert dem Lauf und gilt fuer jeden
# Weg — Oberflaeche und Kommandozeile eingeschlossen.
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
