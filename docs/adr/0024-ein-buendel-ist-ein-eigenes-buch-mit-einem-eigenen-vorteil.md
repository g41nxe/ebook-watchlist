# 24. Ein Bündel ist ein eigenes Buch mit einem eigenen Vorteil

Eine Sammelausgabe ist ein eigenes Buch, das Beziehungen zu den enthaltenen
Bänden hat. Ihr Vorteil gegenüber den Einzelbänden ist ein **eigener
Meldegrund** — aber nur bei Büchern, die die Leserin ohnehin verfolgt.

## Context

Zwei Ausgaben im Bestand, die heute aussehen wie der gesuchte Einzelband:

- „Der Kruzifix-Killer / Der Vollstrecker" (zwei Bände, Chris Carter)
- „David Hunter: 3in1 Bundle" (drei Bände, Simon Beckett)

Zwei Prämissen des ursprünglichen Tickets erwiesen sich als falsch. Der Matcher
wird **nicht** unsicher: der Normalisierer schneidet am ` / ` ab und trifft
exakt. Und Bündel tragen sehr wohl eine ISBN — alle bekannten haben eine, 386
von 390 Produkten überhaupt.

Der Fachstandard kennt den Fall (`docs/research/bundles-and-omnibus-editions.md`):
ONIX-Codeliste 21 hat `CMB` — „An edition in which two or more works also
published separately are combined in a single volume" —, listet die enthaltenen
Titel in `ContentItem` und verknüpft mit `RelatedProduct` (01 includes /
02 is part of). MARC führt den Inhalt in `505` und legt `740`-Nebeneinträge an.

Entscheidend war ein Einwand der Leserin gegen meine erste Rechnung. Ich hatte
den Preis **je Band** gegen die 5-€-Grenze gehalten und geschlossen, die
Preisregel müsse man nicht anfassen. Der richtige Vergleich ist der gegen die
Einzelbände — und dann greift die vorhandene Regel ohne jede Änderung:

| Bündel | Preis | Einzelbände | Ersparnis |
|---|---|---|---|
| Der Kruzifix-Killer / Der Vollstrecker | 12,99 € | 21,98 € | 41 % |
| Kakerlaken / Rotkehlchen | 11,99 € | 21,98 € | 45 % |
| David Hunter 3in1 | 19,99 € | 29,97 € | 33 % |
| Achtsam morden 5in1 | 44,99 € | 59,95 € | 25 % |

Alle vier liegen über `min_discount_pct = 25`. Es braucht keine neue Schwelle,
nur den richtigen Vergleichspreis — und alle Einzelpreise stehen bereits in der
Aufzeichnung.

Der zweite Einwand: *„Ich will nicht über Ramsch informiert werden, nur weil es
ein vollständiger Band in einer Reihe ist, die zufällig in meine Themen fällt."*
Die 19 Bündel im Bestand teilen sich sauber: **14 vom Themenregal**
(„5 Spuk Thriller", „2 Gruselkrimis"), **4 von Referenzautor:innen**.

## Decision

**Ein Bündel ist ein eigenes Buch.** Nicht eine Ausgabe „von" einem der Bände.
Die Zugehörigkeit ist eine Beziehung — `book_relation` kann das, `book_source`
braucht nichts Neues. Das folgt ONIX (eigenes Produkt + `RelatedProduct`) und
MARC (eigener Datensatz + `505`/`740`).

**Der Bündelvorteil ist ein eigener Meldegrund**, wenn **alle drei** zutreffen:

1. Es ist als Sammelausgabe erkannt.
2. Der Anlass ist ein **Watchlist-Titel oder eine Referenzautor:in** — nie ein
   Themenregal. Diese Linie zieht `junk.py` schon, mit derselben Begründung.
3. Die enthaltenen Bände sind **bekannt, nicht geraten**, und ihre Einzelpreise
   ergeben eine Ersparnis über `min_discount_pct`.

Fehlt eines davon, bleibt es beim Abzeichen „Sammelausgabe" ohne Meldung.

**Geraten wird nicht.** Gemessen: eine Bandzahl aus dem Titel zu lesen geht bei
mindestens 3 von 19 Titeln schief — „5 Cottages – Haus der dunklen Geister" und
„7 Momente in Angst" sind einzelne Romane, „28m² – Die Probandenstudie /
Psychothriller / Verlagsbestseller" trägt Werbeschlagworte statt Bandtiteln.
Ein geratener Vergleichspreis wäre schlimmer als keine Meldung.

Verlässlich sind heute zwei Wege:

- **Schrägstrich-Form** — am ` / ` teilen, jeden Teil durch den Matcher. Beide
  Bände stehen mit Preis im Bestand. Kein Modell, keine Anfrage.
- **Ausdrückliche Formen** (`3in1`, `Bundle`, `N Gruselkrimis:`) — der Name gibt
  die Zahl, aber nicht die Titel; die stehen nur in der Prosa des Klappentexts.

**Der Einzelband gewinnt gegen das Bündel.** Findet die Suche beides, ist der
Einzelband gemeint — er ist es, der auf der Watchlist steht. Gemessen: heute
sind beide für den Matcher ununterscheidbar (beide exakter Titel, beide exakter
Autor), und wer gewinnt, entscheidet allein die Reihenfolge der Shop-Treffer.
Bei *Der Kruzifix-Killer* steht das Bündel vorn — ein Münzwurf, der die
Watchlist an die falsche Ausgabe hängen kann. „Ist eine Sammelausgabe" gehört
deshalb in den Rangschlüssel, direkt hinter den exakten Titel.

Das Bündel geht dabei nicht verloren: es ist ein eigenes Buch und wird über
seine Beziehung gefunden, nicht über die Watchlist-Verknüpfung.

## Consequences

- **Vier neue Meldungen, keine Flut** — und keine davon wird heute gemeldet,
  weil keine ein Schnäppchen nach absoluten Zahlen ist. Die 14 Bündel vom
  Themenregal bleiben draußen.
- Es entsteht eine **dritte Art von Angebot** neben Schnäppchen und Preissturz:
  ein Vorteil gegenüber *anderen Produkten*. Die Preisregel verglich bisher
  ausschließlich ein Produkt mit sich selbst.
- Der Weg über den Klappentext (Modell nennt die enthaltenen Titel) bleibt
  **offen** und braucht eine eigene Entscheidung: ob der Bewerter
  Sachinformationen extrahieren darf, ist etwas anderes als ein Urteil zu
  fällen.

**Offen und ausdrücklich nicht entschieden:** was gilt, wenn die Leserin einen
der enthaltenen Bände bereits besitzt. *Der Kruzifix-Killer* steht auf ihrer
Watchlist; hätte sie ihn schon, wäre das Bündel nur noch ein Vollstrecker zu
12,99 €. Die Beziehung `owned` wüssten wir, die Rechnung wäre machbar.
Empfehlung für den Fall, dass es gebaut wird: die Ersparnis **mindern** statt
das Bündel zu unterdrücken — „besitze ich" kann veraltet sein, und die Leserin
kann selbst urteilen, wenn die Zahl ehrlich ist.
