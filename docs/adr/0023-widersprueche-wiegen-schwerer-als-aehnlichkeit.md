# 23. Widersprüche wiegen schwerer als Ähnlichkeit

Beim Zuordnen eines Titels entscheidet nicht mehr ein einzelner
Ähnlichkeitswert. Drei Signale kommen dazu, und zwei davon sind
**Widersprüche**, die eine Annahme verhindern, statt sie nur nicht zu stützen.

## Context

*Dark Matter* (Blake Crouch) hatte keine einzige Beobachtung, obwohl der Shop
das Buch als ersten Treffer führt. Der Shoptitel lautet „Dark Matter. Der
Zeitenläufer"; unser Wert war 56 von nötigen 85.

Die Recherche (`docs/research/title-matching-practices.md`) ergab drei Dinge:

1. **Der Fachstandard löst das gar nicht im String.** MARC trennt Titel (`245
   $a`), Untertitel (`$b`) und Teilnummer (`$n`); ONIX genauso, und das
   zusammengesetzte `TitleText` ist dort formal abgekündigt. Der Shop hat drei
   Felder in eines gequetscht — das ist Datenverlust, kein Algorithmusproblem.
2. **Wo doch verglichen wird, entscheidet niemand über einen Wert.** Primo
   trennt Kandidatensuche von der Entscheidung und rechnet mit negativen
   Gewichten: ein widersprechender Titel kostet 600 Punkte, eine passende ISBN
   bringt nur 85.
3. **Die Robustesten vermeiden Titelvergleiche.** Book Data Tools clustert nur
   über ISBN-Graphen; Open Library hält das Zusammenführen manuell.

Dazu zwei Messungen an den eigenen Daten:

- **13 von 15 Watchlist-Titeln haben höchstens zwei Token** (`morgen`, `judas`,
  `strasse`). „Enthaltensein" als Treffer zu werten wäre bei dieser Liste
  gefährlich, nicht bei einer mit langen Titeln.
- **Die vier Watchlist-Bücher mit ISBN sind genau die vier aufgelösten.** Die
  ISBN entsteht *aus* einer gelungenen Zuordnung und kann eine offene nicht
  lösen.

Und ein Fehler, der dabei auffiel: **„Der Schwarm – Band 2" wurde als „Der
Schwarm" automatisch angenommen.** Der Untertitel-Schnitt entfernte die
Bandangabe, bevor sie jemand sehen konnte, danach war der Titel exakt gleich.

## Decision

**Die Bandnummer wird herausgelöst, nicht mitverglichen.** `volume_of` liest
sie aus dem *ganzen* Titel, bevor der Untertitel abgeschnitten wird — so wie
MARC `245 $n`, ONIX die `SequenceNumber` und Calibre `series_index` führen.
Eine nackte Zahl am Ende zählt nur, wenn noch etwas anderes dasteht und sie
klein ist (`MAX_VOLUME = 20`): „1984" ist kein Band, „Fahrenheit 451" auch
nicht.

**Enthaltensein ist ein eigenes Signal und trägt nie eine Annahme.** Steckt der
gesuchte Titel vollständig im gefundenen, hebt das den Kandidaten von „kein
Treffer" auf „zur Bestätigung" — nie auf „automatisch". Ein Klick, und die
Zuordnung heißt danach `confirmed` statt `linked`.

**Zwei Widersprüche verhindern die Automatik:**

| Widerspruch | Wirkung |
|---|---|
| beide Seiten nennen einen Band, und einen verschiedenen | zur Bestätigung |
| die Anfrage nennt keinen, der Treffer einen späteren | zur Bestätigung |
| beide Seiten tragen eine Kennung, und eine verschiedene | zur Bestätigung |

Beide stehen **hinter** der Titelschwelle: sonst würde ein völlig fremdes Buch
mit einer 2 im Titel zum Kandidaten.

**Zur Bestätigung, nicht in den Papierkorb.** Ein Widerspruch macht einen
Treffer verdächtig, nicht falsch. Ihn wegzuwerfen hieße, der Leserin einen
Kandidaten zu verschweigen, den nur sie beurteilen kann (ADR 9).

## Consequences

Gemessen an den elf ungelösten Watchlist-Titeln, mit elf echten Suchanfragen:

| | |
|---|---|
| gelöst | **1** (*Dark Matter* → „Dark Matter. Der Zeitenläufer") |
| Kandidat zur Bestätigung, inhaltlich fraglich | **1** (*Judas* → „Kinder des Judas") |
| unverändert ohne Treffer | 7 |
| vorher schon zur Bestätigung | 2 |

Das ist ein bescheidenes Ergebnis, und es ist das ehrliche: die übrigen sieben
scheitern nicht am Verfahren, sondern daran, dass die deutsche Ausgabe schlicht
anders heißt (*Hardwired* 29, *Dunkle Gefilde* 25). Kein Titelvergleich löst
das — nur eine Metadatenquelle (Ticket 13) oder ein Mensch.

Der eine Fehlkandidat ist der vorhergesagte Preis der Enthaltensein-Regel bei
Ein-Wort-Titeln. Er wird vorgelegt, nicht angenommen — genau dafür ist die
Stufe da.

Gegen die 389 verschiedenen bisher beobachteten Titel gehalten, liest die
Bandregel in 9,5 % eine Nummer, und die Stichprobe zeigt ausschließlich echte
Reihenbände.

**Nicht entschieden und ausdrücklich offen:** die Trennung von Kandidatensuche
und Entscheidung nach Primos Bauweise. Sie bleibt der nächste Schritt, wenn
dieser nicht reicht.
