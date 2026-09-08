<p align="center">
  <img src="docs/bilder/hero.jpg" alt="Ein Buchfink zeigt drei Schritte: lesen, ohne zu suchen; kaufen, wenn es sich lohnt; Neues finden, das zu dir passt" width="900">
</p>

# Buchfink

**Weniger Suchen. Mehr Lesen.**

Buchfink liest deinen Geschmack aus einem Text, den du selbst geschrieben
hast, und findet damit Bücher, nach denen du nie gesucht hättest. Ein
Sprachmodell liest jeden Fund und schreibt in einem Satz, ob und warum er zu
dir passt — mehr, als jede Kaufhistorie hergibt.

Nebenbei behält es deine Watchlist im Auge, in der Bibliothek und im Shop,
jeden Tag, und meldet sich nur, wenn sich wirklich etwas ändert. Fokus:
deutschsprachige Literatur.

<p align="center">
  <img src="docs/bilder/vorschlaege.png" width="800"
       alt="Die Vorschlagsseite: Cover, Sterne und ein Satz, warum das Buch passt">
</p>

**Jeder Stern hat einen Grund.** Kein API-Schlüssel nötig, wenn
Claude Code schon bei dir angemeldet ist — dann urteilt die lokale
Installation.

**Zwei Quellen, eine Zeile.** [VÖBB Onleihe](https://www.voebb.de) und
[beam-shop.de](https://www.beam-shop.de) für jeden Titel gleichzeitig im
Blick, Preis hier, Verfügbarkeit dort. Weitere Quellen lassen sich ergänzen,
ohne den Kern anzufassen.

<p align="center">
  <img src="docs/bilder/watchlist.png" width="800"
       alt="Die Watchlist: jeder Titel mit Preis oder Verfügbarkeit, Shop- und Bibliotheks-Symbol">
</p>

**Der ganze Verlauf, nicht nur der letzte Preis.** Jede Beobachtung wird
angehängt, nie überschrieben.

<p align="center">
  <img src="docs/bilder/buchseite.png" width="800"
       alt="Die Buchseite: Klappentext, Bewertung und die Tabelle aller Beobachtungen">
</p>

**Läuft bei dir.** Kein Login, keine gespeicherten Zugangsdaten, keine
Cloud — eine SQLite-Datei auf deinem Rechner oder Raspberry Pi.

## Schnellstart

Voraussetzungen: Python 3.12 oder neuer und [uv](https://docs.astral.sh/uv/).

```bash
uv sync
mkdir -p data && cp examples/*.yaml data/
```

`data/profile.yaml` und `data/watchlist.yaml` anpassen, dann die Datenbank
füllen und einen ersten Lauf fahren:

```bash
uv run python -m ebook_watchlist.run seed
uv run python -m ebook_watchlist.run
```

Der erste Lauf sät Beobachtungen und schweigt; ab dem zweiten meldet er
Änderungen. Für die Oberfläche einmal die statischen Dateien bauen, dann
starten:

```bash
uv run tailwindcss_install && uv run python -m ebook_watchlist.web.build
uv run python -m ebook_watchlist.web
```

Danach unter `http://<rechner>:8437/` erreichbar, auch vom Telefon im selben
Netz.

## Entwickeln

```bash
uv run pytest && uv run ruff check .
```

Kein Netzzugriff in der Suite; Smoke-Tests gegen die echten Quellen laufen
nur mit `-m live`. Der Code ist englisch, alles Gelesene deutsch — die
Begriffe dazwischen stehen in [CONTEXT.md](CONTEXT.md).

## Betrieb

Läuft am besten als täglicher Cron- oder Zeitplaner-Job, eine Dateisperre
verhindert doppelte Läufe. Fertige Vorlagen für Windows und Linux/Raspberry
Pi: [docs/betrieb.md](docs/betrieb.md).

## Dokumentation

**Das Werkzeug verstehen**

- [docs/rundgang.md](docs/rundgang.md) — **hier anfangen**: was das Werkzeug
  kann und wie es funktioniert, ohne den Code zu lesen
- [CONTEXT.md](CONTEXT.md) — Glossar, englischer Name und deutsches Wort
- [docs/adr/](docs/adr) — alle Entscheidungen, mit Kontext und Konsequenzen

**Den Geschmack einstellen**

- [docs/leseprofil.yaml](docs/leseprofil.yaml) — der Lesegeschmack, als Prosa
- [docs/bewertungsschema.yaml](docs/bewertungsschema.yaml) — wie ein Buch
  dagegen gehalten und in Sterne übersetzt wird

**Geschichte und Recherche**

- [docs/offene-punkte.md](docs/offene-punkte.md) — was fehlt, und welche
  Behauptungen sich unterwegs als falsch erwiesen haben
- [docs/namensfindung.md](docs/namensfindung.md) — wie das Werkzeug zu seinem
  Namen kam
- [docs/research/](docs/research) — Recherche zu den Schnittstellen von VÖBB
  und beam-shop, zu Metadatenquellen und deren Rechtslage

## Für Agenten

Einstieg in [CLAUDE.md](CLAUDE.md) und [docs/agents/](docs/agents).

## Lizenz

[MIT](LICENSE).
