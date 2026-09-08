# Design-Review: Buchfink

**Aufgenommen**: 2026-09-08, gegen `a3bd8c5`
**Abgearbeitet**: 2026-09-08, Zweig `fix/design-review`
**Geprüfte Breiten**: Mobil (375 px), Tablet (768 px), Desktop (1440 px), hell und dunkel
**Belege**: [`screenshots/`](screenshots/) — `<seite>-<breite>-<schema>.png`, ganzseitig,
über das DevTools-Protokoll mit emuliertem `prefers-color-scheme` aufgenommen. Der Stand
ist der **nach** der Abarbeitung.
**Daten**: ein Demo-Datensatz in einem eigenen `EBW_DATA_DIR` (sechs Watchlist-Titel, neun
Funde mit Urteilen, fünf Läufe, zwei Tagesberichte), damit jede Seite mit Inhalt beurteilt
werden konnte. Keine echte Quelle wurde angefragt.

Das war eine Sichtprüfung auf Professionalität und Konsistenz, kein UX-Audit. Gemessen wurde
im Browser (`getComputedStyle`, `getBoundingClientRect`, Kontrast aus den Farbtoken), nicht
geschätzt.

## Gesamteindruck

Die Oberfläche hatte schon vorher eine eigene, ruhige Handschrift: warmes Papier, Serifen für
Titel und Preise, eine strenge Palette, grün für die Bibliothek und bernstein für den Shop,
überall gleich. Auf dem Desktop wirkte sie gemacht. Sie zerfiel auf dem Telefon, und sie hatte
keinen Hellmodus, obwohl das Stylesheet einen beschrieb.

## Zwei Irrtümer im ersten Durchgang

Die nützlichere Liste, wie in [offene-punkte.md](../offene-punkte.md).

**Der Hellmodus war beim Schreiben des Berichts schon repariert.** Der Befund stimmte, als er
aufgenommen wurde, war aber elf Minuten später hinfällig: `50d202f` hat ihn behoben, während
dieser Bericht entstand. Alle 42 Bilder des ersten Durchgangs zeigten deshalb Dunkel, auch die
mit `-light` im Namen. Der Fix dort ging über meinen Vorschlag hinaus — `--shadow-*` löst
Tailwind beim Bauen auf, sodass `--shadow-sheet` im Ergebnis gar nicht existiert und der dunkle
Schatten ausgeschrieben werden musste. Mein Vorschlag allein hätte den Schatten kaputtgelassen.

**„Eine Zeile wird 450 px hoch"** stimmte nicht mehr, als sie behoben werden sollte. Nach den
kleineren Bedienelementen und dem neuen Grundtext waren es gut 200. Der Defekt an der Stelle
war nicht die Höhe, sondern 143 px Leerraum zwischen Betrag und Symbol.

## Befunde und was daraus wurde

### Hoch

| Befund | Ausgang |
| --- | --- |
| **Der Hellmodus existiert nicht.** `@theme` in einer Medienabfrage wird von Tailwind 4 hochgezogen; das gebaute Stylesheet enthielt keine `prefers-color-scheme`-Regel und nur dunkle Werte, während `color-scheme: light dark` die Bedienelemente des Browsers weiter hell rendern ließ. | **Behoben in `50d202f`** (andere Sitzung), nicht hier. Nachgeprüft: beide Paletten stehen im Bau, und der Hellmodus trägt auf allen Seiten. |
| **Die Seite ist mindestens 451 px breit.** Kopfzeile ohne Umbruch, deshalb zoomte ein Telefon mit 375 px jede Seite heraus. | **Behoben in `4e2ea5e`.** Navigation bricht unter `sm` in eine eigene Reihe, die Zeile entfällt dort. Sechs von sieben Seiten passen jetzt auf 375 px. |
| **Der Tagesbericht ist eine fremde Seite.** Eigenes helles Stylesheet, „Strong Deal" und „Check" auf Englisch, kein `viewport`-Meta, auf dem Telefon 981 px breit. | **Ausgeklammert.** Wird später umgebaut. Es ist die einzige Seite, die auf 375 px noch überläuft. |

### Mittel

| Befund | Ausgang |
| --- | --- |
| Beobachtungstabelle quetscht sich auf dem Telefon, statt zu scrollen | **Behoben in `76eea02`** — `min-w-xl` und `whitespace-nowrap`; 576 px im 327-px-Rahmen. Die Laufliste der Übersicht hatte dasselbe Problem und ist mitgekommen. |
| Steuerelemente in fünf Höhen (26/28/30/32/34) | **Behoben in `2f02582`** — zwei Tailwind-Stufen, `h-7` und `h-9`. |
| Tap-Ziele unter 44 px | **Behoben in `2f02582`** — `.tun` an allen Bedienelementen, Sterne über `aspect-square` auf 44 × 44. Nachgemessen auf einem emulierten Berührungsgerät. |
| Drei Datumsformate auf einer Seite | **Behoben in `3ca6e27`** — ein Format, `TT.MM. HH:MM`, ohne Sekunden. |
| Quellenliste ohne Achse | **Behoben in `3ca6e27`** — feste Spalte für den Namen, Zeitpunkt auf dem Telefon in eigener Zeile. |
| Tagesberichte heißen wie Dateien | **Behoben in `3ca6e27`** — Linktext „Tagesbericht", daneben der Tag, den der Bericht meint. Dabei fiel auf, dass links die *Dateizeit* stand: zwei Berichte verschiedener Tage trugen dieselbe Zahl. |
| Kein aktiver Navigationspunkt | **Behoben in `4e2ea5e`** — `aria-current="page"` und `bg-hair text-ink`. |
| Fokus bleibt dem Browser überlassen | **Behoben in `3ca6e27`** — ein `:focus-visible`-Ring in Petrol für alles, für `.wahl` am Cover-Rahmen. |
| Nullen im Profil unsichtbar (1,4 : 1) | **Behoben in `3ca6e27`** — `text-soft`, 5,9 : 1. |
| Preis der Vorschläge steht allein | **Behoben in `76eea02`** — `justify-between` erst ab `sm`; Lücke von 143 auf 12 px. |
| Rechter Block der Watchlist-Zeile fällt herunter | **Behoben in `76eea02`**, dasselbe Muster. |

### Niedrig

| Befund | Ausgang |
| --- | --- |
| Zwei h2-Stile auf der Buchseite | **Bewusst gelassen.** Über der kleinen Überschrift „Zuordnung" steht, warum: Werkzeug, keine Auskunft, also klein und am Ende. |
| Kaum Übergänge | **Behoben in `3ca6e27`** — Farbübergänge global, mit `prefers-reduced-motion`. |
| Sieben Schriftgrößen | **Behoben in `2f02582`** — 12/14/16/18/24, alles Tailwind-Stufen. Grundtext von 15 auf 16 px. |
| Zeilenlänge auf dem Desktop | **Behoben in `3ca6e27`** — `max-w-prose` für den Klappentext. |
| Zwei Schriften für gleichwertige Werte in den Kacheln | **Offen.** Preis in Serif-Gold, „ausleihbar" in Sans-Petrol. Kein Defekt, eine Frage des Geschmacks. |
| README-Screenshot veraltet | **Offen, gehört dir.** `make_screenshots.py` fotografiert die laufende Oberfläche mit **echten** Daten; ein Titelbild mit erfundenen Büchern wäre schlechter als ein veraltetes. |

## Nebenher gefunden

Beim Prüfen des Vokabulars, nicht beim Ansehen der Seiten. Behoben in `7cc1931`.

- **„Interesse" bedeutete auf der Profilseite zweierlei**: im Glossar den Entdeckungskanal,
  in der Pille „Kein Interesse" die Buchbeziehung `disliked`. Aufgelöst im Glossar — der Kanal
  heißt jetzt Entdeckungskanal, wie ihn `relations.py` ohnehin zweimal nennt. Kein
  Codebezeichner wurde angefasst, keine Migration nötig.
- **Die fünf Beziehungsarten hatten im Glossar kein deutsches Wort**, obwohl die Oberfläche für
  jede eines zeigt. Jetzt stehen sie in einer Tabelle daneben.
- **Der Unterschied zwischen `disliked` und `dismissed`** stand weder im Glossar noch in ADR 18.
  Er steht jetzt da: `disliked` ist ein Urteil nach dem Lesen, `dismissed` eine Anweisung an den
  Stapel — ausschließen lässt sich auch ungelesen.
- **Der Hinweis im Vorschlagsstapel** nannte die Handlung „Verwerfen", während der Knopf daneben
  „Ausgeschlossen" heißt, und erklärte sie mit der Bedeutung von `disliked`.
- **`_watchlist_row.html` schrieb zwei Beschriftungen hart hin**, statt sie aus `RELATION_LABELS`
  zu holen — genau die Doppelung, gegen die es die Tabelle gibt.

**Nicht angefasst, obwohl vorgeschlagen:** `disliked` von „Kein Interesse" in „Mag ich nicht"
umzubenennen. Über der Tabelle in `relations.py` steht die Regel, die das verbietet — Substantive
statt Ich-Sätze, und keine zwei Namen, die sich nur durch ein „nicht" unterscheiden. Dass die
Beschriftung eine Haltung *vor* dem Lesen nahelegt, während der Wert ein Urteil *danach* ist,
bleibt damit stehen.

## Was gut ist und bleiben soll

- **Die Palette hält.** Sechs Textfarben auf einer ganzen Seite, alle aus Token, keine rohen
  Tailwind-Farben. Jeder gemessene Kontrast über 5 : 1.
- **Farbe bedeutet überall dasselbe.** Grün ist die Bibliothek, bernstein der Shop, in Abzeichen,
  Kacheln, Preisen, Pillen und Zuordnung.
- **Radien und Schatten sind ein System.** 4 px für Knöpfe, 8 px für Kacheln, Pillen rund, ein
  einziger Schatten.
- **Das Cover-Abzeichen** — Ring in Papierfarbe statt Weiß, damit es im Dunkeln auf 8,8 : 1 kommt.
- **Leere Zustände** sind überall ein ganzer Satz, nie „No data".
- **Tablet (768 px)** war von Anfang an sauber und ist es geblieben.
- **Wo das Projekt ein Maß festgelegt hat, hält es sich daran** — die Zeilen des Stapels sind
  alle gleich hoch, die Eingabefelder auch.

## Was offen bleibt

1. **Der Tagesbericht** — eigene Seite, eigenes Stylesheet, englische Wörter, kein
   `viewport`-Meta. Ausdrücklich vertagt.
2. **Das Titelbild der README** — braucht deine echten Daten.
3. **Zwei Schriften in den Kacheln der Buchseite** — Geschmacksfrage, kein Defekt.
4. **`.design-sync/validate.py` läuft nicht**: ihm fehlt `tinycss2`, das keine Abhängigkeit des
   Projekts ist. Gehört zur anderen Sitzung, hier nicht angefasst.
5. **Zwei Ruff-Fehler in `.design-sync/`** (eine zu lange Zeile, ein unbenutzter Import) —
   ebenfalls aus dem fremden Commit, ebenfalls nicht angefasst.
