# Betrieb: den Lauf täglich anstoßen, die Oberfläche dauerhaft halten

Es gibt keinen eigenen Zeitplaner — der Lauf wird von außen getaktet, einmal
am Tag reicht ([Kadenz](../README.md#konfiguration)). Eine Dateisperre
serialisiert parallele Läufe: ein zweiter Start beendet sich sofort wieder.
Ein Umzug auf einen anderen Rechner ist *Repository kopieren, `uv sync`,
`data/` mitnehmen*.

Zwei Dinge wollen eingerichtet werden, und sie sind unabhängig voneinander:
der **tägliche Lauf** und die **Oberfläche**, die dauerhaft erreichbar sein
soll. Ohne den Lauf zeigt die Oberfläche nie etwas Neues; ohne die Oberfläche
läuft das Werkzeug trotzdem.

## Windows — Aufgabenplanung

### Der tägliche Lauf

[`scripts/run-daily.cmd`](../scripts/run-daily.cmd) wechselt ins Repository,
startet den Lauf und hängt die Ausgabe an `data/run.log` an. Die Aufgabe
zeigt einfach auf diese Datei — die ganze Kommandozeile bei `schtasks` zu
hinterlegen heißt sonst, sich mit den Anführungszeichen-Regeln von `cmd` zu
prügeln:

```powershell
$repo = 'D:\Pfad\zum\repo'
$ich  = "$env:USERDOMAIN\$env:USERNAME"
Register-ScheduledTask -TaskName 'Buchfink Lauf' -Force `
  -Action (New-ScheduledTaskAction -Execute "$repo\scripts\run-daily.cmd" -WorkingDirectory $repo) `
  -Trigger (New-ScheduledTaskTrigger -Daily -At '06:00') `
  -Principal (New-ScheduledTaskPrincipal -UserId $ich -LogonType Interactive) `
  -Settings (New-ScheduledTaskSettingsSet -StartWhenAvailable `
      -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew)
```

`StartWhenAvailable` holt einen verpassten Lauf nach — dieselbe Rolle wie
`Persistent=true` beim systemd-Timer. Das Zeitlimit von zwei Stunden ist
keine Schätzung der Dauer, sondern eine Notbremse: ein hängender Lauf hält
sonst die Sperre und blockiert damit auch den von morgen.

### Die Oberfläche

Sie läuft unter `pythonw.exe` aus der bereits gebauten Umgebung — ohne `uv`,
weil das zur Laufzeit nichts beiträgt, und ohne Konsolenfenster, das sonst
dauerhaft offen stünde und beim versehentlichen Zuklicken den Server mitnähme.

```powershell
$repo = 'D:\Pfad\zum\repo'
$ich  = "$env:USERDOMAIN\$env:USERNAME"
Register-ScheduledTask -TaskName 'Buchfink Oberflaeche' -Force `
  -Action (New-ScheduledTaskAction -Execute "$repo\.venv\Scripts\pythonw.exe" `
      -Argument '-m ebook_watchlist.web' -WorkingDirectory $repo) `
  -Trigger (New-ScheduledTaskTrigger -AtLogOn -User $ich) `
  -Principal (New-ScheduledTaskPrincipal -UserId $ich -LogonType Interactive) `
  -Settings (New-ScheduledTaskSettingsSet -RestartCount 3 `
      -RestartInterval (New-TimeSpan -Minutes 5) `
      -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew)
```

Vier Einstellungen, die alle einen Grund haben:

- **`-User $ich` am Auslöser.** Ein Anmelde-Auslöser ohne Benutzerangabe gilt
  für *alle* Benutzer und braucht deshalb Administratorrechte. Mit
  Benutzerbindung registriert sich die Aufgabe ohne Erhöhung.
- **`LogonType Interactive`.** Die Aufgabe läuft mit deinem Token, wenn du
  angemeldet bist — kein gespeichertes Kennwort. Der Preis: nach einem
  Neustart läuft Buchfink erst ab der Anmeldung, nicht ab dem Einschalten.
- **`ExecutionTimeLimit` auf null**, also unbegrenzt. Die Vorgabe wäre drei
  Tage, und danach hätte die Aufgabenplanung den Server kommentarlos beendet.
- **`RestartCount`/`RestartInterval`.** Stirbt der Prozess, startet die
  Aufgabenplanung ihn dreimal im Abstand von fünf Minuten neu.

Danach ist die Oberfläche unter `http://localhost:8437/` erreichbar, im
selben Netz auch vom Telefon.

**Beenden und nachsehen:**

```powershell
Stop-ScheduledTask  -TaskName 'Buchfink Oberflaeche'   # anhalten
Start-ScheduledTask -TaskName 'Buchfink Oberflaeche'   # wieder starten
Get-ScheduledTask -TaskName 'Buchfink*' | Get-ScheduledTaskInfo
```

Im Task-Manager stehen **zwei** `pythonw.exe`, und das ist richtig so: die
`pythonw.exe` im `.venv` ist ein Trampolin, das den eigentlichen Interpreter
startet. Wer den Elternprozess abschießt, nimmt das Kind mit — deshalb hält
man die Aufgabe an, statt Prozesse zu suchen.

Die Ausgabe der Oberfläche landet in `data/web.log`. Ohne Konsole hat
`pythonw.exe` keine gültigen Ausgabe-Handles; die Oberfläche erkennt das beim
Start und schreibt stattdessen in diese Datei
([`web/__main__.py`](../src/ebook_watchlist/web/__main__.py)). Ohne diese
Vorkehrung beendete schon die erste Startzeile den Prozess mit Rückgabewert 1
— ohne Spur, weil die Fehlermeldung denselben kaputten Weg genommen hätte.

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

Für die Oberfläche gilt dort dasselbe Muster als eigener Dienst — `Type=simple`,
`ExecStart=%h/ebook-watchlist/.venv/bin/python -m ebook_watchlist.web`,
`Restart=on-failure`, `WantedBy=default.target`. Unter systemd braucht es die
Vorkehrung aus `web/__main__.py` nicht: das Journal nimmt die Ausgabe entgegen.
