# Die Zugangsfläche von voebb.overdrive.com

Untersucht am 11.09.2026, ohne Anmeldung und ohne Zugangsdaten. Grundlage für
[ADR 31](../adr/0031-eine-quelle-nimmt-die-tuer-die-offensteht.md) und für
`sources/overdrive/selectors.py` — das Gegenstück zu
[`voebb-search-interface.md`](voebb-search-interface.md), das dasselbe für die
Onleihe tut.

> Alles unter **geprüft** wurde selbst abgerufen. **Recherchiert** heißt: aus
> fremden Quellen übernommen und nicht nachgestellt.

## 1. Zwei Plattformen, zwei Bestände

Der VÖBB betreibt die Onleihe (`voebb.onleihe.de`) **und** OverDrive
(`voebb.overdrive.com`). Die Bestände sind getrennt. Der Anlass dieser
Recherche: „Dark Matter" von Blake Crouch steht bei OverDrive als „Der
Zeitenläufer (Dark Matter)", bei der Onleihe gar nicht — deren einziger Treffer
auf `Dark Matter Crouch` ist „Cold Storage" von David Koepp (geprüft).

Deshalb heißt eine Quelle nach der **Plattform**, nie nach der Bibliothek
(`CONTEXT.md`, Eintrag *Source*).

## 2. Die Website ist eine leere Hülle

**Geprüft:** `GET /search?query=Dark%20Matter&format=ebook-epub-adobe&language=de`
→ 200, 114 KB HTML, keine Anmeldung, keine Bot-Abwehr.

Im DOM steht **keine einzige Trefferkarte** — die baut JavaScript. Die Daten
liegen serverseitig als JSON in einem `<script>`-Block
(`window.OverDrive.mediaItems`, `…titleCollection`). Die Wörter „Ausleihen"
und „Vormerken" kommen aus einem Sprachpaket nach `Accept-Language` und stehen
nicht im HTML; auf sie zu prüfen wäre doppelt zerbrechlich.

Ein HTML-Parser würde hier also denselben JSON lesen, nur über einen Umweg.

## 3. Die JSON-Schnittstelle, ohne Schlüssel

**Geprüft**, alle ohne Header und ohne Token:

| Adresse | Status | Inhalt |
|---|---|---|
| `thunder.api.overdrive.com/v2/libraries/voebb` | 200 | Angaben zur Einrichtung |
| `…/libraries/voebb/media?query=…&format=…&language=de` | 200 | Trefferliste |
| `…/libraries/voebb/media/3222096` | 200 | ein Titel, gleiche Gestalt wie ein Treffer |
| `…/libraries/voebb/media/availability?titleIds=…` | 200 | nur Verfügbarkeit, ohne Beiwerk |
| `api.overdrive.com/v1/libraries/100645` | 401 | die alte Partner-API, nur mit Vertrag |

Paginiert wird mit `page` (1-basiert) und `perPage`; **geprüft:**
`perPage=100` → 200, `perPage=101` → 400. Keine Rate-Limit-Kopfzeilen, kein
`Retry-After`, keine `robots.txt` auf dem Thunder-Host (404).

Die Kennung der Einrichtung steht auf jeder Seite der Instanz als
`window.OverDrive.libraryKey = "voebb"`; `websiteId`/`tenant` ist `100645`,
`fulfillmentId` ist `berlinbiblio`.

## 4. Die Felder, auf die es ankommt

**Geprüft** an „Der Zeitenläufer (Dark Matter)", Titelnummer `3222096`:

```json
{"isAvailable": false, "isHoldable": true, "isOwned": true,
 "availableCopies": 0, "ownedCopies": 1,
 "holdsCount": 8, "holdsRatio": 8, "estimatedWaitDays": 126,
 "availabilityType": "normal"}
```

- **ausleihbar**: `availableCopies > 0`
- **Exemplare**: `ownedCopies` sind die Lizenzen, `availableCopies` die freien
- **Vormerkungen**: `holdsCount`
- **Wartezeit**: `estimatedWaitDays`, serverseitig geschätzt

Buchfink speichert Verfügbarkeit und Vormerkungen — dieselben Felder, die die
Onleihe füllt. Ohne eine einzige Lizenz gilt `unknown`, nicht `unavailable`:
„verliehen" verspricht eine Rückkehr.

Die **ISBN** steht je Format (`formats[].isbn`); `ebook-kobo` trägt keine. Sie
ist der Grund, warum die Zuordnung überhaupt gelingt — siehe Abschnitt 6.

## 5. Der Anmeldebereich bleibt draußen

**Geprüft** wurde nur die Weiterleitungskette, ohne Anmeldung:
`/account/loans` → `/account/sign-in` → `/account/ozone/sign-in` →
`auth.overdrive.com/v2/connect/authorize` → `…/v2/login` →
`…/external/oauth/initiate` → `www.voebb.de/oidcp/authorize` → Loginformular
mit `LLOGIN`/`LPASSW` hinter einer F5-WAF.

Also kein einfaches Formular, sondern ein OIDC-Fluss, dessen Identitätsanbieter
die VÖBB ist. **Recherchiert:** der praktikable Weg für Kontodaten wäre die
Libby-Schnittstelle (`sentry-read.svc.overdrive.com`) mit einem Sync-Code aus
der App. Beides ist v2-Gebiet (ADR 6), und `robots.txt` sperrt `/account*`.

## 6. Warum der Titelvergleich hier nicht reicht

Gemessen: `title_similarity("Dark Matter - der Zeitenläufer",
"Der Zeitenläufer (Dark Matter)")` ergibt **80** — aber `match()` kommt auf
**26**, und die Schwelle liegt bei 85. Der Grund steht in
`matching/normalize.py`:

```
'Dark Matter - der Zeitenläufer'  ->  'dark matter'      (Untertitel ab)
'Der Zeitenläufer (Dark Matter)'  ->  'zeitenlaufer'     (Klammer ab, Artikel ab)
```

Die Klammer gilt dem Normalisierer als Ausgabenrauschen („(Roman)", „(Band 2)")
— bei deutschen Übersetzungen steht darin aber oft der **Originaltitel**. Zwei
Schreibweisen desselben Buchs werden so zu disjunkten Zeichenketten.

Gelöst wird das über die Kennung, mit der Mechanik, die beam längst benutzt
(`Query.identifier` → „Kennung stimmt überein"). Sie kostet keine Anfrage: die
ISBN steht in derselben Antwort. **Gemessen im echten Bestand:** 13 von 15
beobachteten Büchern tragen eine ISBN, und alle 13 sind bei der Onleihe *nicht*
zugeordnet — die ISBN kommt vom Shop, nicht aus einer Bibliothekszuordnung.
Der Kommentar in `config.py`, sie könne eine offene Zuordnung nicht lösen, galt
für einen Stand mit vier Büchern.

Ohne ISBN bleibt es beim Titelvergleich, und dieses eine Buch fände er nicht.
`tests/test_overdrive.py` hält beides fest — den Treffer über die Kennung und
die Grenze ohne sie.

## 7. Was andere tun

**Recherchiert.** Niemand parst hier ernsthaft HTML: Katalog und Verfügbarkeit
laufen über Thunder (`agent-skill-libby-book-monitor` ohne jede
Authentifizierung), Kontodaten über `sentry-read` mit Sync-Code (`odmpy`,
`libbydl`). Die offizielle Partner-API `api.overdrive.com` braucht einen
Vertrag mit OverDrive (Library Simplified / Palace).

## 8. Die Regeln

**Geprüft**, `https://voebb.overdrive.com/robots.txt`, vollständig:

```
User-Agent: bytespider
Disallow: /

User-agent: *
Disallow: /account*
Disallow: /*/account*
Disallow: /accessibility-conformance-report
Disallow: /*/related/*
Disallow: /*?*page=*
```

`/search` und `/media/*` sind nicht gesperrt, **paginierte Seiten schon** — und
eine Zuordnung braucht mehrere Trefferseiten. Auf dem Thunder-Host gibt es
keine `robots.txt`.

**Recherchiert:** OverDrives Nutzungsbedingungen untersagen automatisiertes
Auslesen ausdrücklich. Technisch offen heißt also nicht vertraglich erlaubt.
Die Abwägung — nur Watchlist-Titel, ein Abruf je Titel und Tag,
identifizierender User-Agent, harter Stopp bei 429 — steht in ADR 31.
