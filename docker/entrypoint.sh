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
# Einmal am Tag rufen. Die Schleife ist absichtlich dumm: sie kennt die Kadenz
# nicht, sie ruft nur. Ob gelaufen wird, entscheidet der Lauf selbst — er weiss
# aus dem Journal, wann zuletzt einer war, und die Kadenz steht im Profil
# (`run_every_hours`, Voreinstellung 20 Stunden).
#
# Deshalb kostet ein Neustart keinen Lauf mehr. Vorher stiess jeder einen an:
# ein Nachmittag mit fuenf Neubauten ergab fuenf volle Laeufe gegen die echten
# Quellen in 25 Minuten, und die stehen bis heute in der Preisgeschichte jedes
# Buchs.
#
# Dass die Schwelle (20 h) unter dem Schlaf (24 h) liegt, ist kein Zufall: der
# Ruf verrutscht um die Dauer jedes Laufs nach hinten, und die vier Stunden
# Luft fangen das ab, damit nie ein Tag ausfaellt.
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
