# 31. Eine Quelle nimmt die Tür, die offensteht

OverDrive wird über seine JSON-Schnittstelle gefragt, nicht über die Website.
Das ist kein Bruch mit ADR 9, sondern dieselbe Regel an einer anderen Tür: wir
nehmen den Weg, den die Quelle anbietet — bei der Onleihe ist das
server-gerendertes HTML, bei OverDrive JSON.

## Kontext

Der VÖBB betreibt **zwei** digitale Plattformen mit getrennten Beständen: die
Onleihe unter `voebb.onleihe.de` und OverDrive unter `voebb.overdrive.com`.
Buchfink kannte nur die erste. Aufgefallen ist das an „Dark Matter" von Blake
Crouch: bei der Onleihe nicht im Katalog, bei OverDrive als „Der Zeitenläufer
(Dark Matter)" mit acht Vormerkungen. Vier der fünfzehn beobachteten Titel
stehen dort und nirgends sonst.

ADR 9 hält für die Onleihe fest: *kein JSON, kein OpenSearch, nur
server-gerendertes HTML.* Das liest sich wie eine Regel gegen Schnittstellen,
war aber eine **Feststellung über die Onleihe** — sie hat keine. Ohne diesen
Satz hier stünde im Repository ein scheinbarer Widerspruch, den in einem halben
Jahr niemand mehr auflösen kann.

Bei OverDrive ist die Lage umgekehrt, gemessen am 11.09.2026:

- Die HTML-Seite trägt **keine einzige Trefferkarte**. Die Kacheln baut
  JavaScript im Browser; im gelieferten HTML stehen die Daten als JSON in einem
  `<script>`-Block. Auch die Wörter „Ausleihen" und „Vormerken" fehlen — sie
  kommen aus einem Sprachpaket, das nach `Accept-Language` geladen wird. Auf
  solche Textmarker zu prüfen wäre doppelt zerbrechlich.
- `thunder.api.overdrive.com/v2/libraries/voebb/media?query=…` antwortet mit
  **200** ohne Schlüssel, ohne Anmeldung, mit strukturierten Feldern: `title`,
  `firstCreatorName`, `formats[].isbn`, `isAvailable`, `availableCopies`,
  `ownedCopies`, `holdsCount`.
- `robots.txt` der Instanz sperrt `/account*` und **jede paginierte Seite**
  (`/*?*page=*`). Eine Zuordnung braucht mehrere Trefferseiten — der HTML-Weg
  wäre also ausgerechnet für das gesperrt, wofür wir ihn bräuchten. Auf dem
  Thunder-Host gibt es keine `robots.txt`.

Damit ist der HTML-Weg nicht der konservativere, sondern derselbe JSON mit
einem Umweg über eine Seite, die ihn nur transportiert — plus einem
Regelverstoß.

Die zweite Frage ist keine technische. OverDrives Nutzungsbedingungen
untersagen automatisiertes Auslesen ausdrücklich („data mining, robots,
scraping, or similar data gathering and extraction tools"). Technisch offen
heißt nicht vertraglich erlaubt, und das gilt für den HTML-Weg genauso.

## Entscheidung

**Gefragt wird Thunder.** `sources/overdrive/selectors.py` trägt Basis-Adresse,
Pfade, Abfrageparameter und Feldnamen — dieselbe Rolle wie die CSS-Selektoren
der Onleihe: Baut OverDrive um, ist dieses Modul der ganze Diff.

**Die Bauform bleibt die der Onleihe.** `LibrarySource` mit `check`, `resolve`
und `probe`, dieselbe Dreiteilung in `source` / `parse` / `selectors`, dieselbe
Lautstärke aus ADR 7: „nicht gefunden" ist `None`, eine geänderte Gestalt
wirft. Ein fehlendes `ownedCopies` ist kein leerer Wert, sondern ein Umbau —
es still als „nichts verfügbar" zu lesen wäre der eine Fehler, den dieses
Werkzeug nicht machen darf (ADR 15).

**Sparsam, und zwar ausdrücklich.** Gefragt wird nur nach Titeln, die auf der
Watchlist stehen, ein Abruf je Titel und Lauf, bei einer Kadenz von einem Lauf
am Tag. Das ist weniger Last als ein einziger Seitenaufruf im Browser, der
dieselben Daten plus Skripte, Schriften und Bilder zieht. Der User-Agent nennt
eine Kontaktadresse (`profile.contact`), bei 429 hält der `HttpClient` hart an.
Ein Vollabzug des Katalogs findet nicht statt und wäre auch ohne die
Nutzungsbedingungen die falsche Bauweise.

**Die eigenen Ausleihen bleiben draußen** (ADR 6, v2). Der Weg zu
`/account/loans` führt über sieben Weiterleitungen durch einen OIDC-Fluss,
dessen Identitätsanbieter `voebb.de` ist, mit einer WAF davor — und
`robots.txt` sperrt `/account*` ausdrücklich. Der gangbare Weg wäre die
Libby-Schnittstelle mit einem Sync-Code; das ist ein eigenes Vorhaben mit
eigenen Geheimnissen, kein Nebeneffekt dieser Quelle.

## Folgen

- Wer eine dritte Quelle baut, fragt zuerst, **was die Quelle anbietet**, und
  nicht, was die vorige Quelle getan hat. ADR 9 beschreibt die Onleihe, nicht
  das Werkzeug.
- `parse.py` einer Quelle darf JSON lesen. Was gleich bleibt, ist die Grenze:
  reine Funktionen, kein Netz, keine Konfiguration, und laut bei jeder Gestalt,
  die die Recherche nicht beschreibt.
- Die Begründung für das Abrufen liegt schriftlich vor. Wenn OverDrive
  widerspricht, ist die Entscheidung an einer Stelle zurückzunehmen — Eintrag
  aus `profile.yaml` entfernen — und dieser Abschnitt sagt, was abgewogen
  wurde.
- Die Beschriftung „Bibliothek" trägt nicht mehr: es gibt zwei. Quellen mit
  einem Namen, den die Leserin kennt, zeigen ihn (`registry.DISPLAY`).
