# eBook-Watchlist & Deal-Finder

Ein persönliches Werkzeug, das täglich prüft, ob Titel von meiner Watchlist neu in
der Bibliothek verfügbar sind oder im Shop günstiger geworden sind — und nur dann
einen Digest schreibt, wenn sich tatsächlich etwas geändert hat.

Fokus: **deutschsprachige Literatur**. Quellen in v1:

| Quelle | Art | Was sie liefert |
| --- | --- | --- |
| [VÖBB Onleihe](https://www.voebb.de) (Berlin) | Library Source | Verfügbarkeit / Vormerk-Warteschlange |
| [beam-shop.de](https://www.beam-shop.de) | Shop Source | Preis, Neuerscheinungen, Genre-Regale |

Beide Quellen liegen hinter einer gemeinsamen Schnittstelle — weitere Shops und
Bibliotheken lassen sich ergänzen, ohne den Kern anzufassen.

## Wie es funktioniert

Ein **Run** ist ein Durchlauf von *scrapen → diffen → berichten*:

1. Profil und Watchlist laden.
2. Jede Quelle nach dem aktuellen Zustand fragen → **Observations**.
3. Observations append-only in SQLite schreiben.
4. Die neueste Observation je `(source, source_item_id)` gegen die vorherige
   diffen → **Deltas**.
5. Bei Deltas oder Fehlern einen **Digest** rendern (Text auf stdout, HTML nach
   `data/digests/`).

Der Run ist **stateless gegenüber dem Zeitplan**: er vergleicht gegen den letzten
gespeicherten Snapshot, nicht gegen "gestern". Ausgefallene Cron-Läufe gehen
deshalb nicht verloren — der nächste Run meldet die aufgelaufenen Deltas.

Ausgelöst wird derselbe Entrypoint auf drei Wegen: Cron/Task Scheduler, der
"Run now"-Button der UI (Phase 2) und die Kommandozeile.

### Deal-Logik

Zwei Stufen (Schwellen pro Profil konfigurierbar):

- **Strong Deal** — Preis unter `strong_deal_max_cents` (Default 5,00 €). Kein
  Rabatt-Check, billig genug ist billig genug.
- **Deal** — Preis zwischen 5,00 € und `deal_max_cents` (Default 9,99 €) **und**
  echt reduziert: mindestens `min_discount_pct` (Default 25 %) unter dem
  durchgestrichenen Originalpreis, oder unter dem zuletzt beobachteten Preis.
  Ein Dauerpreis von 9,99 € ist kein Deal.

Wegen der deutschen Buchpreisbindung zeigt beam-shop nie einen durchgestrichenen
Preis. Deals dort werden also erst erkannt, sobald genug Preishistorie da ist.

## Status

- **Phase 1 — Headless Core** *(fertig)*: beide Quellen, Matcher mit
  automatischer Titelauflösung, SQLite-Snapshot, YAML-Konfiguration, Text- und
  HTML-Digest, Selbsttest.
- **Phase 2 — Lokale Web-UI**: FastAPI + Jinja + HTMX, Dashboard und Editoren für
  Profil/Watchlist, Konfiguration wandert aus YAML in die Datenbank.
- **v2**: Bibliotheks-Vormerkungen mit Login, verlässliche Genre-Klassifikation,
  weitere Quellen.
- **v3**: Calibre- und Geräte-Anbindung.

v1 ist bewusst **komplett login-frei** — es werden nirgends Bibliotheks-Zugangs-
daten gespeichert.

## Setup

Voraussetzung: Python 3.12+ und [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

Konfiguration liegt unter `data/` (gitignored). Vorlagen liegen in
[`examples/`](examples) und werden einmalig kopiert:

```bash
mkdir -p data && cp examples/*.yaml data/
```

- `data/profile.yaml` — Referenzautor:innen, Genre-Kategorien, Deal-Schwellen
- `data/watchlist.yaml` — die beobachteten Titel
- `data/dismissed.yaml` — Altbestand: dauerhaft ausgeblendete Vorschläge als
  Produktnummer je Shop. Der Lauf liest die Datei nicht mehr; ausgeblendet wird
  über die Beziehung `dismissed` am Buch, und die gilt an jeder Quelle
  (ADR 18). `ebw dismissals` löst übrig gebliebene Nummern einmalig auf.

Daneben legt der Run dort `snapshots.db` und `digests/` an. Der Datenpfad lässt
sich über `EBW_DATA_DIR` umbiegen.

Schema-Änderungen wandern beim nächsten Start automatisch in eine bestehende
`snapshots.db`; die Historie bleibt erhalten. Den Stand hält SQLites eingebautes
`PRAGMA user_version`. Eine Datei, die von einer *neueren* Version geschrieben
wurde, wird nicht geöffnet, sondern gemeldet.

## Benutzung

Einen Run starten:

```bash
uv run python -m ebook_watchlist.run
```

Er schreibt nur dann etwas, wenn sich etwas geändert hat oder eine Quelle
gestreikt hat. Der Exit-Code ist `0` bei Erfolg, `1` wenn eine Quelle
fehlgeschlagen ist, `2` bei kaputter Konfiguration.

Selbsttest: jede Quelle bekommt eine bekannte Seite vorgelegt und muss sie
parsen können.

```bash
uv run python -m ebook_watchlist.run doctor
```

Derselbe Test läuft am Anfang jedes Runs. Eine Quelle, die ihn nicht besteht,
setzt diesen Run aus und taucht im Digest unter „⚠️ Fehler" auf — eine
halb gelesene, umgebaute Seite würde sonst Unsinn in den Snapshot schreiben und
jeden künftigen Vergleich vergiften. Mit `--skip-probes` lässt er sich abschalten.

## Oberfläche

Ein zweiter, unabhängiger Prozess zeigt Läufe und Digests im Browser:

```bash
uv run python -m ebook_watchlist.web
```

Danach unter `http://<rechner>:8437/` erreichbar, auch vom Telefon im selben
Netz. Port und Bindung über `--port` / `--host` oder `EBW_WEB_PORT` /
`EBW_WEB_HOST`; `--host 127.0.0.1` beschränkt den Zugriff auf diesen Rechner.

**Es gibt keine Anmeldung** (ADR 3) — die Oberfläche gehört ins vertraute
Heimnetz, nicht ins offene Internet.

Der Webprozess **scrapt nichts** und hält nie die Run-Sperre. Ihn zu beenden
oder neu zu starten stört einen laufenden Run nicht, und umgekehrt.

Tests und Linter:

```bash
uv run pytest && uv run ruff check .
```

Die Live-Smoke-Tests gegen die echten Seiten sind mit `@pytest.mark.live` markiert
und laufen standardmäßig **nicht** mit.

## Kadenz

Ein Lauf pro Tag reicht. Jeder Lauf prüft die komplette Watchlist, die
Bibliothek, die `core`-Referenzautor:innen und alle Genre-Kategorien. Die
`extended`-Liste — der lange Schwanz, bei dem ein verpasster Tag nichts kostet —
wird einmal pro Woche an dem in `extended_sweep_weekday` gesetzten Tag
mitgenommen (0 = Montag). Fällt dieser Lauf aus, holt der nächste Lauf ihn nach,
sobald mehr als sieben Tage vergangen sind.

```yaml
reference_authors:
  core: [Frank Schätzing]        # jeden Lauf
  extended: [Andreas Eschbach]   # einmal pro Woche
extended_sweep_weekday: 6        # Sonntag
```

## Betrieb

Es gibt keinen eigenen Scheduler — der Run wird von außen getaktet. Der Code ist
host-agnostisch (nur `pathlib`, keine plattformspezifischen Abhängigkeiten); ein
Umzug ist *Repo kopieren, `uv sync`, `data/` mitnehmen*. Ein `filelock`
serialisiert parallele Runs, ein zweiter Start beendet sich sofort wieder.

### Windows — Task Scheduler

[`scripts/run-daily.cmd`](scripts/run-daily.cmd) wechselt ins Repo, startet den
Run und hängt die Ausgabe an `data/run.log` an. Die Task zeigt einfach auf diese
Datei — die ganze Kommandozeile bei `schtasks` zu hinterlegen heißt sonst, sich
mit den Anführungszeichen-Regeln von `cmd` zu prügeln.

```bash
schtasks /create /tn "eBook-Watchlist" /sc daily /st 06:00 /tr "C:\Users\g41nx\Repositories\ebook-watchlist\scripts\run-daily.cmd"
```

### Linux / Raspberry Pi — systemd-Timer

`~/.config/systemd/user/ebook-watchlist.service`:

```ini
[Unit]
Description=eBook-Watchlist & Deal-Finder

[Service]
Type=oneshot
WorkingDirectory=%h/ebook-watchlist
ExecStart=%h/ebook-watchlist/scripts/run-daily.sh
```

`~/.config/systemd/user/ebook-watchlist.timer`:

```ini
[Unit]
Description=Taeglicher eBook-Watchlist-Lauf

[Timer]
OnCalendar=*-*-* 06:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl --user enable --now ebook-watchlist.timer
```

`Persistent=true` holt einen verpassten Lauf nach dem Einschalten nach. Nötig ist
das nicht — ein Run vergleicht immer gegen den letzten gespeicherten Snapshot,
nie gegen „gestern", ausgefallene Läufe gehen also ohnehin nicht verloren.

Alle Zeiten sind Ortszeit; bei der Zeitumstellung kann ein Lauf ausfallen oder
doppelt laufen. Beides ist unkritisch.

## Dokumentation

- [CONTEXT.md](CONTEXT.md) — Glossar der Domänenbegriffe
- [docs/adr/](docs/adr) — Architecture Decision Records (Nummer 1–18)
- [docs/leseprofil.md](docs/leseprofil.md) — der Maßstab für Buchbewertungen
- [.agents/skills/](.agents/skills) — `buch-bewerten` und `leseprofil-schaerfen`
- [docs/research/](docs/research) — Rechercheergebnisse zu den Schnittstellen von
  VÖBB und beam-shop sowie zu Calibres Metadaten-Matching

Beim Scrapen gilt: serielle Requests, 2–4 s Pause, sprechender User-Agent mit
Kontaktadresse, harter Stopp bei HTTP 429.
