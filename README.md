<p align="center">
  <img src="docs/bilder/hero.png" alt="Die Vorschlagsseite: Funde mit Cover, Sternen und einer Zeile, warum sie in Frage kommen" width="900">
</p>

# eBook-Watchlist & Deal-Finder

Ein persönliches Werkzeug, das jeden Tag nachsieht, ob ein Titel von meiner
Watchlist in der Bibliothek ausleihbar geworden ist oder im Shop billiger — und
das nur dann etwas schreibt, wenn sich wirklich etwas geändert hat.

Darüber hinaus schlägt es Bücher vor, die es noch nicht kennt. Ein Modell hält
jeden Fund gegen ein schriftlich festgehaltenes **Leseprofil** und begründet in
einem Satz, warum ein Buch in Frage kommt — oder eben nicht.

Fokus: **deutschsprachige Literatur**. Zwei Quellen:

| Quelle | Art | Was sie liefert |
| --- | --- | --- |
| [VÖBB Onleihe](https://www.voebb.de) (Berlin) | Bibliothek | Verfügbarkeit, Länge der Vormerk-Warteschlange |
| [beam-shop.de](https://www.beam-shop.de) | Shop | Preis, Neuerscheinungen, Themenregale |

Beide liegen hinter derselben Schnittstelle; weitere Shops und Bibliotheken
lassen sich ergänzen, ohne den Kern anzufassen.

> **Sprachregelung:** der Code ist englisch, alles Gelesene deutsch. Welches
> deutsche Wort zu welchem Codebegriff gehört, steht in
> [CONTEXT.md](CONTEXT.md) und in [ADR 22](docs/adr/0022-zwei-vokabulare-eines-fuer-den-code-eines-fuer-die-leserin.md).

## Was ein Lauf tut

Ein **Lauf** ist ein Durchgang von *nachsehen → vergleichen → berichten*:

1. Profil und Watchlist aus der Datenbank laden.
2. Jede Quelle nach dem aktuellen Stand fragen → **Beobachtungen**.
3. Alles Gesehene **anhängend** in SQLite schreiben. Nie überschreiben: was der
   Shop gestern gesagt hat, bleibt nachlesbar ([ADR 5](docs/adr)).
4. Die neueste Beobachtung je Produkt gegen die vorherige halten → **Änderungen**.
5. Was gemeldet würde, durch das **Bewertungstor** schicken.
6. Bei Änderungen oder Fehlern einen **Tagesbericht** schreiben (Text auf die
   Konsole, HTML nach `data/digests/`).

Der Lauf ist **gleichgültig gegenüber dem Zeitplan**: er vergleicht gegen die
letzte gespeicherte Aufzeichnung, nicht gegen „gestern". Ein ausgefallener Lauf
geht deshalb nicht verloren — der nächste meldet, was aufgelaufen ist.

Ausgelöst wird derselbe Weg auf drei Arten: Zeitplaner, der Knopf „jetzt
prüfen" in der Oberfläche, und die Kommandozeile.

## Was gemeldet wird

**Ein Watchlist-Titel wird immer gemeldet** — bei jedem Preis, jeder
Verfügbarkeit. Er steht auf der Liste, weil er gewollt ist.

**Ein Fund muss sich qualifizieren.** Er erreicht die Leserin nur, wenn er
ausleihbar oder ein Schnäppchen ist. Von 358 offenen Funden eines echten
Laufs blieben so 107 übrig; die übrigen 251 kosteten weder eine Anfrage noch
ein Urteil. Fällt später ein Preis, sind sie wieder da.

Schnäppchen kennt zwei Stufen, beide je Profil einstellbar:

- **unter 5,00 €** — billig genug ist billig genug, kein Rabatt nötig.
- **5,00 bis 9,99 €** — nur mit echtem Nachlass: mindestens 25 % unter dem
  zuletzt beobachteten Preis. Ein Dauerpreis von 9,99 € ist kein Schnäppchen.

Wegen der Buchpreisbindung zeigt beam-shop nie einen durchgestrichenen Preis.
Ein Nachlass dort ist deshalb erst zu erkennen, wenn genug Preisgeschichte da
ist — was ein weiterer Grund für die anhängende Aufzeichnung ist.

**Kostenlose Titel sind kein Schnäppchen**, sondern Füllmaterial: jeder
Gratistitel eines echten Laufs war ein Bündel oder eine Werbebeigabe.

## Das Bewertungstor

Was die Preisregel durchgelassen hat, wird gegen das
[Leseprofil](docs/leseprofil.yaml) gehalten — eine Prosabeschreibung dessen,
was diese Leserin mag, entstanden im Gespräch darüber, *warum* sie welche
Bücher mag. Die Reihenfolge der Achsen darin **ist** die Gewichtung.

Wie daraus Sterne werden, steht getrennt davon im
[Bewertungsschema](docs/bewertungsschema.yaml). Die Trennung ist Absicht: der
Maßstab überlebt eine Änderung des Geschmacks
([ADR 21](docs/adr/0021-leseprofil-und-bewertungsschema-trennen.md)).

Jedes Urteil trägt Sterne, eine Begründung, eine Sicherheitsangabe (*belegt*,
*teils*, *vermutet*) und einen **Pitch** — einen Satz, warum das Buch für diese
Leserin zählt. Der Pitch steht auf der Vorschlagsseite **statt** des
Klappentexts: der sagt, wovon das Buch handelt, und das steht schon im Shop.

Aus 109 echten Urteilen:

| | |
|---|---|
| Verteilung | 5★ ×1, 4★ ×11, 3★ ×14, 2★ ×39, 1★ ×24, 0★ ×20 |
| Sicherheit | belegt 41, teils 67, vermutet 1 |
| zurückgehalten (unter drei Sternen) | 83 |

Ein Urteil ohne Schlüssel ist möglich: gibt es keinen `ANTHROPIC_API_KEY`,
fragt das Tor die lokal angemeldete Claude-Code-Installation über `claude -p`.

**Ein Modellurteil ersetzt nie ein eigenes.** Beide werden getrennt
gespeichert; eine 4 von einem Menschen ist eine Tatsache, eine 4 von einem
Modell ein Vorschlag ([ADR 17](docs/adr)).

## Die Oberfläche

Ein zweiter, unabhängiger Prozess:

```bash
uv run python -m ebook_watchlist.web
```

Danach unter `http://<rechner>:8437/` erreichbar, auch vom Telefon im selben
Netz. Vier Seiten:

| Seite | Wofür |
| --- | --- |
| **Übersicht** | Zustand der Quellen, die letzten Läufe, die Tagesberichte, der Knopf „jetzt prüfen" |
| **Watchlist** | die beobachteten Titel mit Preis und Verfügbarkeit je Quelle |
| **Vorschläge** | der Stapel: Funde mit Cover, Sternen und Pitch, entscheidbar in einem Rutsch |
| **Profil** | Leseprofil und Bewertungsschema, nur lesend |

Farbe bedeutet überall dasselbe: **grün = Bibliothek**, **bernstein = Shop**.

Eine Entscheidung auf dem Stapel gilt für das **Buch**, nicht für eine
Produktnummer — sie wirkt damit bei jeder Quelle
([ADR 18](docs/adr)). „Verwerfen" löscht nichts, sondern hält fest, dass dich
dieses Buch nicht interessiert.

**Es gibt keine Anmeldung** ([ADR 3](docs/adr)) — die Oberfläche gehört ins
vertraute Heimnetz, nicht ins offene Internet. Der Webprozess fragt selbst nie
eine Quelle und hält nie die Lauf-Sperre; ihn zu beenden stört keinen
laufenden Lauf, und umgekehrt.

## Stand

**Läuft im Betrieb.** Zwei Quellen, anhängende Aufzeichnung, buchweite
Entscheidungen, Bewertungstor mit echten Urteilen, Oberfläche, täglicher Lauf.
645 Tests, 22 ADRs.

Bekannte Lücken — vollständig in
[docs/offene-punkte.md](docs/offene-punkte.md):

- **Keine Sprache.** Es gibt kein Feld dafür. Eine japanische Ausgabe kann
  deshalb auf dem Stapel landen und ein vollständiges Urteil bekommen.
- **Bündel** („Titel A / Titel B", „3in1") werden keinem Watchlist-Titel
  zugeordnet, und ihr Preis ist kein Preis für den gesuchten Band.
- **Keine Metadatenquelle.** Reihe, Bandnummer und die kanonische Schreibweise
  fehlen; die DNB ist recherchiert, aber nicht angebunden.
- **Die Übersichtsseite zeigt die Maschine, nicht die Bücher** — Läufe und
  Quellenzustand statt „was gibt es Neues".
- **Neun Watchlist-Titel sind ungelöst**: der Matcher findet ihre deutsche
  Ausgabe nicht sicher genug.

Später: Vormerkungen mit Login, Bücher in mehreren Sprachen, ähnliche Bücher zu
gemochten finden, Calibre-Anbindung.

Diese Fassung ist bewusst **komplett login-frei** — es werden nirgends
Bibliotheks-Zugangsdaten gespeichert.

## Einrichten

Voraussetzung: Python 3.12+ und [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

Die Konfiguration liegt unter `data/` (nicht im Repository). Vorlagen stehen in
[`examples/`](examples):

```bash
mkdir -p data && cp examples/*.yaml data/
```

| Datei | Inhalt |
| --- | --- |
| `data/profile.yaml` | Referenzautor:innen, Themen, Schnäppchengrenzen, Bündelgröße und Modell für die Bewertung |
| `data/watchlist.yaml` | die beobachteten Titel |
| `data/owned.yaml` | Bücher im Besitz, optional mit einer Einschätzung — keine Vorlage, wird bei Bedarf angelegt |
| `data/dismissed.yaml` | Altbestand, optional: `ebw dismissals` löst übrig gebliebene Produktnummern einmalig auf |

Die YAML-Dateien sind **Saatgut** ([ADR 10](docs/adr)): `ebw seed` überführt
sie einmalig in die Datenbank, danach ist die Datenbank die Wahrheit. Ein
zweiter Aufruf legt nichts doppelt an.

```bash
uv run python -m ebook_watchlist.run seed
```

Daneben entstehen dort `snapshots.db`, `covers/` und `digests/` — die
Ordnernamen sind Codepfade und bleiben englisch (ADR 22). Der
Datenpfad lässt sich über `EBW_DATA_DIR` umbiegen.

Schemaänderungen wandern beim nächsten Start von selbst in eine bestehende
`snapshots.db`; die Geschichte bleibt erhalten. Den Stand hält SQLites
eingebautes `PRAGMA user_version`. Eine Datei, die von einer *neueren* Fassung
geschrieben wurde, wird nicht geöffnet, sondern gemeldet.

Für die Oberfläche werden die statischen Dateien einmal gebaut:

```bash
uv run tailwindcss_install && uv run python -m ebook_watchlist.web.build
```

## Benutzung

```bash
uv run python -m ebook_watchlist.run              # ein Lauf
uv run python -m ebook_watchlist.run rate         # den Rückstand beurteilen
uv run python -m ebook_watchlist.run doctor       # Selbsttest der Quellen
uv run python -m ebook_watchlist.run sources      # Quellen anzeigen, pausieren
uv run python -m ebook_watchlist.run seed         # YAML einlesen
```

Der Lauf schreibt nur, wenn sich etwas geändert hat oder eine Quelle gestreikt
hat. Rückgabewert `0` bei Erfolg, `1` wenn eine Quelle ausgefallen ist, `2` bei
kaputter Konfiguration.

`rate` beurteilt Funde, die das Tor nie gesehen hat — der Lauf sieht nur
Erstsichtungen, ein angesammelter Rückstand bliebe ihm sonst für immer
unsichtbar. Beurteilt wird nur, was auch gemeldet würde, und nur für diese
Bücher wird der ganze Klappentext nachgeladen (`--anzahl` begrenzt, Vorgabe 10).

Der Selbsttest legt jeder Quelle eine bekannte Seite vor und verlangt, dass sie
sie noch versteht. Er läuft zu Beginn jedes Laufs mit; eine Quelle, die ihn
nicht besteht, setzt diesen Lauf aus und erscheint im Tagesbericht unter
„⚠️ Fehler" — eine umgebaute Seite halb zu lesen schriebe Unsinn in die
Aufzeichnung und vergiftete jeden künftigen Vergleich. `--skip-probes` schaltet
ihn ab.

Tests und Linter:

```bash
uv run pytest && uv run ruff check .
```

Die Smoke-Tests gegen die echten Seiten sind mit `@pytest.mark.live` markiert
und laufen **nicht** mit.

Das Titelbild dieser Datei wird aus der laufenden Oberfläche aufgenommen:

```bash
uv run python scripts/make_hero.py
```

## Kadenz

Ein Lauf pro Tag reicht. Jeder Lauf prüft die ganze Watchlist, die Bibliothek,
die `core`-Referenzautor:innen und alle Themen. Die `extended`-Liste — der lange
Schwanz, bei dem ein verpasster Tag nichts kostet — kommt einmal pro Woche dazu.
Fällt dieser Lauf aus, holt der nächste ihn nach, sobald mehr als sieben Tage
vergangen sind.

```yaml
reference_authors:
  core: [Frank Schätzing]        # jeden Lauf
  extended: [Andreas Eschbach]   # einmal pro Woche
extended_sweep_weekday: 6        # Sonntag
```

## Betrieb

Es gibt keinen eigenen Zeitplaner — der Lauf wird von außen getaktet. Der Code
ist plattformunabhängig; ein Umzug ist *Repository kopieren, `uv sync`, `data/`
mitnehmen*. Eine Dateisperre serialisiert parallele Läufe: ein zweiter Start
beendet sich sofort wieder.

### Windows — Aufgabenplanung

[`scripts/run-daily.cmd`](scripts/run-daily.cmd) wechselt ins Repository,
startet den Lauf und hängt die Ausgabe an `data/run.log` an. Die Aufgabe zeigt
einfach auf diese Datei — die ganze Kommandozeile bei `schtasks` zu hinterlegen
heißt sonst, sich mit den Anführungszeichen-Regeln von `cmd` zu prügeln.

```bash
schtasks /create /tn "eBook-Watchlist" /sc daily /st 06:00 /tr "C:\Pfad\zum\repo\scripts\run-daily.cmd"
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

`Persistent=true` holt einen verpassten Lauf nach dem Einschalten nach. Nötig
ist das nicht — ein Lauf vergleicht immer gegen die letzte Aufzeichnung, nie
gegen „gestern". Alle Zeiten sind Ortszeit; bei der Zeitumstellung kann ein Lauf
ausfallen oder doppelt laufen. Beides ist unkritisch.

## Dokumentation

- [docs/rundgang.md](docs/rundgang.md) — **hier anfangen**: was das Werkzeug
  kann und wie es funktioniert, ohne den Code zu lesen
- [CONTEXT.md](CONTEXT.md) — Glossar, englischer Name und deutsches Wort
- [docs/adr/](docs/adr) — die 22 festgehaltenen Entscheidungen
- [docs/leseprofil.yaml](docs/leseprofil.yaml) — der Lesegeschmack, als Prosa
- [docs/bewertungsschema.yaml](docs/bewertungsschema.yaml) — wie ein Buch
  dagegen gehalten und in Sterne übersetzt wird
- [docs/offene-punkte.md](docs/offene-punkte.md) — was fehlt, und welche
  Behauptungen sich unterwegs als falsch erwiesen haben
- [.agents/skills/](.agents/skills) — `buch-bewerten`, `leseprofil-schaerfen`
- [docs/research/title-matching-practices.md](docs/research/title-matching-practices.md)
  — wie MARC, ONIX, Primo und Open Library Titel zuordnen, und was das für
  unseren Matcher heißt
- [docs/research/](docs/research) — Recherche zu den Schnittstellen von VÖBB und
  beam-shop, zu Metadatenquellen und deren Rechtslage

Beim Abfragen der Quellen gilt: eine Anfrage nach der anderen, 2–4 Sekunden
Pause, ein sprechender User-Agent mit Kontaktadresse, harter Stopp bei
HTTP 429.
