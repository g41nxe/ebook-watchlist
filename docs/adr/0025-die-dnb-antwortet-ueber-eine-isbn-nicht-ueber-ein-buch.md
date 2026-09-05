# 25. Die DNB antwortet über eine ISBN, nicht über ein Buch

Die Deutsche Nationalbibliothek wird nach einer **ISBN** gefragt, und ihre
Antwort wird an der ISBN gespeichert — nicht an einem Buch. Gefragt wird
einmal je ISBN, mit einer Obergrenze je Lauf.

## Context

Vier Tickets warten auf Angaben, die keine unserer Quellen nennt: die
enthaltenen Bände einer Sammelausgabe (29), Titel und Untertitel getrennt (36),
die Sprache (31, 39), die Reihe (16). Die Recherche zu Ticket 13 hatte die DNB
über `MARC21-xml` empfohlen und gemessen: 21 von 30 Büchern beantwortet.

Der Anlass war ein konkreter Fehlschlag. Für „David Hunter: 3in1 Bundle" stehen
die enthaltenen Bände nur im Klappentext, und zwei Versuche, sie ohne fremde
Hilfe zu lesen, sind gescheitert:

- **Textabgleich gegen bekannte Titel** fand acht statt drei — der Klappentext
  nennt auch die übrige Bibliografie des Autors.
- **Guillemets als Ausschluss** kehrte den Fall um: bei Beckett stehen dort die
  *anderen* Bücher, bei Dusse die *enthaltenen*. Dieselbe Auszeichnung,
  entgegengesetzte Bedeutung; was sie trennt, ist der Satz davor.

Daraufhin war ein Modellaufruf vorgesehen — bis die DNB gefragt wurde und
`770 $i Enthält $z <ISBN>` lieferte, MARCs Entsprechung zu ONIX „01 includes".

## Decision

**Die DNB ist keine Quelle in unserem Sinn.** Eine `Source` liefert Preis und
Verfügbarkeit, hat `probe`, `search`, `check`, `item` und wird bei jedem Lauf
befragt. Die DNB liefert nichts davon. Sie steht neben den Quellen, in einem
eigenen Modul.

**Geschlüsselt wird nach ISBN.** Der erste Entwurf hängte die Auskunft an ein
Buch — und der Fall, der ihn ausgelöst hat, zeigte den Fehler: „David Hunter:
3in1 Bundle" ist bei uns **kein Buch**. Eine `book`-Zeile entsteht erst durch
eine Entscheidung der Leserin (ADR 18), ein Fund hat keine. An der ISBN gilt
die Antwort für Bücher und Funde gleichermaßen.

**Gefragt wird einmal je ISBN, höchstens `dnb_budget` (50) je Lauf.** Der
Rückstand von 388 ISBNs ist damit nach acht Läufen abgearbeitet. Auch das
**Schweigen wird festgehalten**: neun von dreißig kennt die DNB nicht, und ohne
diesen Vermerk fragte jeder Lauf dieselben erneut.

Die Zurückhaltung hat keinen technischen Grund. Die DNB dokumentiert **keine**
zulässige Anfragefrequenz (`docs/research/metadata-sources-legal.md`). Wo
niemand sagt, was erlaubt ist, fragt man wenig — dieselbe Überlegung wie bei
der Pause zwischen zwei Shop-Anfragen.

**Nichts wird ersetzt.** Die DNB liefert Angaben, die wir *nicht haben* —
Sprache, Reihe, Bandnummer, enthaltene Bände. Titel und Autor:in am Buch
bleiben unangetastet. Eine Liste, in der Einträge ihren Namen ändern, weil eine
Bibliothek anderer Meinung ist, verlöre das Vertrauen, für das Bewertungstor
und Bestätigungsweg gebaut wurden.

**Eine unerreichbare DNB kostet keinen Lauf.** Sie antwortet dann wie bei einem
unbekannten Buch — dieselbe Zurückhaltung wie bei einem Titelbild, wo ein 403
einmal den ganzen Lauf gerissen hat.

## Consequences

Der Fall, der alles ausgelöst hat, löst sich ohne Modell:

    3 Bände für 19,99 € statt 29,97 € — 33 % gespart
    David Hunter: 3in1 Bundle

Drei ISBNs aus `770`, drei Preise aus dem eigenen Bestand. Der Vergleich ist
exakt statt namensbasiert — und damit fällt die Falle weg, dass „Achtsam
morden" ein Teilstring aller vier anderen Bandtitel ist.

- Der Vorschlagsstapel wächst von 28 auf 29.
- **Die Frage aus ADR 24, ob der Bewerter Sachinformationen lesen darf, ist
  vertagt, nicht beantwortet.** Für „Achtsam morden (5in1)" und „Claire Douglas
  Bundle (3in1)" hat die DNB kein `770`. Bleibt die Lücke spürbar, ist der Weg
  über den Klappentext weiterhin offen — dann aber mit gemessener Abdeckung
  statt einer Vermutung.
- Das Schema bekam zwei Tabellen: `dnb_record` (auch das Schweigen) und
  `dnb_contains`. Der erste, buchgebundene Entwurf wurde mit einer angehängten
  Migration zurückgenommen statt umgeschrieben (ADR 16).
- Sprache und Reihe liegen jetzt vor, ohne dass sie schon benutzt würden.
  Tickets 31, 36 und 39 können darauf aufsetzen.
