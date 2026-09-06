# Woher Leserstimmen nehmen? (Ticket 37)

Recherche vom 6.9.2026. Anlass: die Sterne sollen nicht nur „passt zum Profil"
sagen, sondern auch, ob ein Buch etwas taugt — und schlechtes Leserfeedback
soll negativ eingehen.

**Ergebnis vorweg: für unser Korpus gibt es heute keine brauchbare Quelle.**
Die Regeln, wie eine Leserstimme wirken soll, sind entschieden (Ticket 37);
sie warten auf eine Quelle, die es nicht gibt.

## Was beurteilt wird

Das ist der Maßstab, an dem jede Quelle zu messen ist:

```
genre_category    beam    199 Produkte
profile_author    beam    178 Produkte
watchlist         beam     24 Produkte
watchlist         voebb     5 Produkte
```

Der Bewertungsstapel besteht zu **100 % aus Shop-Entdeckungen** — deutsche
E-Books, überwiegend Thriller, Horror und SF, viele davon Kleinverlage und
Sammelbände. Watchlist-Titel werden gar nicht beurteilt.

## Die Quellen, einzeln gemessen

### beam (der Shop selbst)

Das Markup ist da — `product--rating`, `product--rating-count`, Sternsymbole.
Gemessen an der abgelegten Trefferseite: **96 Kacheln, davon 0 mit Stimmen.**
Der Zähler steht überall auf null. beam ist kein Bewertungsportal; die Funktion
liegt brach.

### VÖBB-Onleihe

Die einzige Quelle mit **echten** Stimmen, und zwar reichlich:

```
Auslöschung           103 Stimmen    3/5
Der Knochenjäger       69 Stimmen    4/5
Der Ruf des Kuckucks  999 Stimmen    4/5
Autorität              26 Stimmen    2/5   (Karte: 2.8)
Akzeptanz              22 Stimmen    2/5
```

Der Mittelwert steht als Zahl auf der **Trefferkarte** (`<p cardAverageVote>`),
die Anzahl als Text auf der **Detailseite** („Anzahl Bewertungen: 1641"); dort
ist der Mittelwert auf ganze Sterne gerundet — 2.8 wird zu 2/5, was bei einer
Regel mit Angelpunkt „3 ist Durchschnitt" den Ausschlag geben kann.

**Der Haken ist die Abdeckung.** Die Onleihe kennt 5 unserer 404 Produkte, und
sie erzeugt keine Entdeckungen — sie wird nur für Titel gefragt, die die
Leserin selbst auf die Watchlist gesetzt hat. Sie deckt also genau die Bücher
ab, die **nicht** beurteilt werden.

### Google Books

Der Schlüssel liegt vor, die Abfrage läuft. Gemessen am 6.9.2026 an 15 ISBN
aus dem Bewertungsstapel:

```
gefunden          14 von 15
mit Bewertung      7
   Der Totschläger      2 aus 1
   Der Knochenbrecher   5 aus 1
   Die stille Bestie    5 aus 1
   Blutrausch           5 aus 1
   I Am Death           5 aus 1
   Bluthölle            5 aus 6
   Blutige Stufen       5 aus 5
```

**Die Abdeckung ist ausgezeichnet, die Substanz nicht.** Fünf der sieben
Bewertungen ruhen auf einer **einzigen** Stimme, der Median liegt bei 1, und
sechs von sieben sind glatte Fünfen. Das ist genau der Fall, vor dem Ticket 37
warnt: „4,8 aus sieben Bewertungen ist keine Auskunft."

**Zur Rechtslage — eine Korrektur an der früheren Recherche.**
[`metadata-sources-legal.md`](metadata-sources-legal.md) schließt Google Books
über den Cache-Header aus (`cache-control: private, max-age=86400`). Dieser
Header wurde an einem **Titelbild** gemessen. Die JSON-Antwort der Books-API
trägt am 6.9.2026 gemessen **gar keinen** Cache-Header, nur `vary` — das
Argument lässt sich also nicht übertragen.

Was bleibt, ist §5.e.1 („Scrape, build databases, or otherwise create
permanent copies"), und ob eine Zahl je Buch in der eigenen Sortierung
darunterfällt, ist eine **Auslegung**, keine Messung. Die Leserin prüft und
verantwortet die Rechtslage; diese Recherche trifft die Entscheidung nicht.

Praktisch ist sie ohnehin gegenstandslos: bei einem Median von einer Stimme
gibt es nichts, dessen Speichern sich lohnte.

### Open Library

Offen lizenziert (CC0/ODbL), ausdrücklich zum Weiterverwenden gedacht, mit
`ratings_average` und `ratings_count` in der Such-API. Zwei Messungen:

```
20 unserer E-Book-ISBNs           ->  0 gefunden
12 Titel + Autor:in (Entdeckungen) ->  5 gefunden, davon 0 mit Bewertung
```

Die Abfrage ist geprüft und funktioniert — die Gegenprobe findet Harry Potter
(4.2 aus 1024), eine deutsche Druckausgabe von *Thinner* (3.5 aus 37) und
*Der Schwarm* über den Titel (4.0 aus 15).

Zwei getrennte Befunde:

1. **E-Book-ISBNs sind unbekannt.** Open Library führt Druckausgaben; die
   eigene ISBN einer E-Book-Ausgabe steht dort nicht.
2. **Die gefundenen Werke haben keine Stimmen.** Chris Carters
   „Totenkünstler", „Der Vollstrecker", „Der Knochenbrecher" sind
   bibliografisch erfasst — `ratings_count` ist bei allen `None`.

Und selbst wo Stimmen stehen, sind es wenige: 15 für *Der Schwarm*, 37 für
*Thinner*. Gegen 1641 bei der Onleihe. Eine Quelle mit vielen *Büchern* ist
nicht dasselbe wie eine mit vielen *Stimmen je Buch* — und für die Regel zählt
das zweite.

### Goodreads

Die API ist seit 2020 abgeschaltet, es werden keine neuen Schlüssel vergeben.
Kein legaler programmatischer Zugang.

### Was nicht geprüft wurde, und warum

**Amazon PA-API** setzt ein Partnerkonto mit nachgewiesenen Verkäufen voraus —
für ein privates Werkzeug praktisch verschlossen. **LovelyBooks** ist die
größte deutsche Leser-Gemeinschaft und hätte vermutlich die Abdeckung, bietet
aber keine öffentliche Schnittstelle; es bliebe Auslesen der Seiten, mit einer
eigenen rechtlichen Frage. Beides wäre zu prüfen, wenn die Sache wichtig genug
wird — heute ist es das nicht.

## Empfehlung

**Nicht bauen.** Die Regeln aus Ticket 37 stehen und sind gut; es fehlt der
Rohstoff. Eine Regel für einen Fall zu bauen, der in 0 von 377 beurteilten
Büchern eintritt, ist teurer als keine.

Zwei Dinge lohnen sich trotzdem sofort und unabhängig davon:

* **Die Onleihe-Bewertung mitschreiben**, wo sie ohnehin anfällt — sie kostet
  keine Anfrage und beantwortet für Watchlist-Titel die Frage „taugt das was?",
  auch ohne dass das Bewertungstor sie benutzt. Das ist Ticket 54.
* **Die Frage neu stellen, wenn sich die Abdeckung ändert.** Sie hängt daran,
  wie viele Bücher in der Bibliothek stehen — und das sind gerade die, die
  nichts kosten.
