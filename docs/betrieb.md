# Betrieb: den Lauf täglich anstoßen

Es gibt keinen eigenen Zeitplaner — der Lauf wird von außen getaktet, einmal
am Tag reicht ([Kadenz](../README.md#konfiguration)). Eine Dateisperre
serialisiert parallele Läufe: ein zweiter Start beendet sich sofort wieder.
Ein Umzug auf einen anderen Rechner ist *Repository kopieren, `uv sync`,
`data/` mitnehmen*.

## Windows — Aufgabenplanung

[`scripts/run-daily.cmd`](../scripts/run-daily.cmd) wechselt ins Repository,
startet den Lauf und hängt die Ausgabe an `data/run.log` an. Die Aufgabe
zeigt einfach auf diese Datei — die ganze Kommandozeile bei `schtasks` zu
hinterlegen heißt sonst, sich mit den Anführungszeichen-Regeln von `cmd` zu
prügeln:

```bash
schtasks /create /tn "Buchfink" /sc daily /st 06:00 /tr "C:\Pfad\zum\repo\scripts\run-daily.cmd"
```

## Linux / Raspberry Pi — systemd-Timer

[`scripts/run-daily.sh`](../scripts/run-daily.sh) übernimmt dieselbe Rolle.
Zwei Dateien unter `~/.config/systemd/user/`:

```ini
# ebook-watchlist.service
[Unit]
Description=Buchfink

[Service]
Type=oneshot
WorkingDirectory=%h/ebook-watchlist
ExecStart=%h/ebook-watchlist/scripts/run-daily.sh
```

```ini
# ebook-watchlist.timer
[Unit]
Description=Taeglicher Buchfink-Lauf

[Timer]
OnCalendar=*-*-* 06:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl --user enable --now ebook-watchlist.timer
```

`Persistent=true` holt einen verpassten Lauf nach dem Einschalten nach. Nötig
ist das nicht, weil ein Lauf immer gegen die letzte Aufzeichnung vergleicht,
nie gegen „gestern". Alle Zeiten sind Ortszeit; bei der Zeitumstellung kann
ein Lauf ausfallen oder doppelt laufen. Beides ist unkritisch.
