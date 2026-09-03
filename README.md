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

Design abgeschlossen, Implementierung läuft.

- **Phase 1 — Headless Core** *(in Arbeit)*: Quellen, Matcher, SQLite-Snapshot,
  YAML-Konfiguration, Text- und HTML-Digest, `ebw doctor`.
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
- `data/dismissed.yaml` — dauerhaft ausgeblendete Vorschläge (ab Ticket 07)

Daneben legt der Run dort `snapshots.db` und `digests/` an. Der Datenpfad lässt
sich über `EBW_DATA_DIR` umbiegen.

## Benutzung

Einen Run starten:

```bash
uv run python -m ebook_watchlist.run
```

Selbsttest aller Quellen-Parser (kommt mit Ticket 08):

```bash
uv run python -m ebook_watchlist.run doctor
```

Tests und Linter:

```bash
uv run pytest && uv run ruff check .
```

Die Live-Smoke-Tests gegen die echten Seiten sind mit `@pytest.mark.live` markiert
und laufen standardmäßig **nicht** mit.

## Betrieb

Es gibt keinen eigenen Scheduler — der Run wird von außen getaktet: Windows Task
Scheduler auf dem Arbeitsrechner, systemd-Timer oder Cron auf dem Raspberry Pi.
Der Code ist host-agnostisch (nur `pathlib`, keine plattformspezifischen
Abhängigkeiten); ein Umzug ist *Repo kopieren, `uv sync`, `data/` mitnehmen*.

Ein `filelock` serialisiert parallele Runs.

## Dokumentation

- [CONTEXT.md](CONTEXT.md) — Glossar der Domänenbegriffe
- [docs/adr/](docs/adr) — Architecture Decision Records (Nummer 1–15)
- [docs/research/](docs/research) — Rechercheergebnisse zu den Schnittstellen von
  VÖBB und beam-shop sowie zu Calibres Metadaten-Matching

Beim Scrapen gilt: serielle Requests, 2–4 s Pause, sprechender User-Agent mit
Kontaktadresse, harter Stopp bei HTTP 429.
