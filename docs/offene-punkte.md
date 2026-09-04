# Offene Punkte und was unterwegs schiefging

Stand 2026-09-04, nach Ticket 23. Zwei Listen: **was noch nicht stimmt oder fehlt**, und
**welche Behauptungen sich als falsch herausgestellt haben**. Die zweite ist
die nützlichere — sie sagt, wo dieses Projekt zum Irrtum neigt.

Die Tickets liegen in `.scratch/ebook-watchlist-phase2/issues/` und sind nicht
Teil des Repositories.

---

## 1. Was fehlt oder noch nicht stimmt

### Das Bewertungstor hat nie gelaufen

Es ist gebaut, getestet und eingebunden — aber **kein einziges Mal ausgeführt**,
weil kein `ANTHROPIC_API_KEY` gesetzt ist. Alles, was über sein Verhalten
gesagt wird, ist aus Tests mit einem Stub belegt, nicht aus Betrieb. Der erste
scharfe Lauf ist deshalb ein echtes Ereignis und kein Formsache.

### Die Metadatenquelle ist recherchiert, nicht angebunden

`docs/research/metadata-sources.md` empfiehlt die DNB über `MARC21-xml` für
Titel, Autor, Reihe und **Sprache**. Implementiert ist davon **nichts**. Damit
fehlt weiterhin:

- der Sprachfilter (Ticket 15) — es gibt kein Feld, aus dem er lesen könnte
- die kanonische Schreibweise auf Buchebene (Ticket 16 baut sie, wendet sie
  aber nicht auf `book.title` / `book.author` an)
- Reihe und Bandnummer, und damit die Grundlage für Serien-Tracking

### Cover: Mechanik ohne Bilder

Der Weg steht — Adresse aus der Kachel, einmal geholt, lokal abgelegt. Es liegt
aber **keine einzige Datei** im Ordner, weil Bilder beim Lauf geholt werden und
seitdem keiner lief. Die Oberfläche zeigt durchweg Platzhalter.

Und der Punkt, an dem wir jetzt allein hängen, ist ungeprüft: **die
Nutzungsbedingungen von beam für Produktbilder** hat niemand gelesen. Die
DNB-Cover sind rechtlich ausgeschieden, Google-Books-Thumbnails dürfen nur
24 Stunden zwischengespeichert werden.

### Die Testsuite verfehlt ihr Ziel

108 s → 28 s. Ticket 18 wollte unter zehn. Der Rest ist gleichmäßig verteilt
(0,08 s je Test, kein Ausreißer) und besteht aus Tests, die echte Arbeit tun.
Darunter zu kommen hieße, Ende-zu-Ende-Tests zusammenzulegen — Unabhängigkeit
gegen Geschwindigkeit. **Dieser Tausch ist nicht getroffen worden**, er steht
offen.

### Kleinere offene Punkte

- **Die Anfragefrequenz bei der DNB ist undokumentiert.** Nirgends eine Zahl;
  wer Gewissheit will, muss `schnittstellen-service@dnb.de` fragen.
- **Der Rückstand von 358 Vorschlägen ist unbearbeitet** — auf ausdrücklichen
  Wunsch, bis das Tor gefiltert hat (Ticket 19).

### Mit Ticket 23 geschlossen

- **Schreibweisen auf der Buch-Zeile.** `find_or_create_book` behält jetzt die
  bessere Schreibweise **derselben** Person; ein anderer Name bleibt liegen.
  *Cold Eternity* und *Providence* heißen wieder `S.A. Barnes` und `Max Barry`.
- **Alpine.** Es wird geladen und trägt den Fall, den ADR 20 selbst nennt: der
  Vorschlagsstapel zählt, was angehakt ist, und kennt "alle" und "keine".
- **`CONTEXT.md`.** Bewertungstor, Urteil (mit Herkunft), Maßstab und
  Entdeckung stehen im Glossar.
- **Der `dismissals`-Befehl** achtet den Quellen-Schalter. Was ohne Anfrage
  geht, geht weiter; der Rest wird gemeldet statt still zu scheitern.

---

## 2. Behauptungen, die sich als falsch erwiesen haben

Diese Liste ist wichtiger als die erste. Jede Zeile ist ein Fall, in dem etwas
plausibel klang, aufgeschrieben wurde und dann durch Messung fiel.

### Über die eigenen Daten

**Die Sterne in `owned.yaml` sind Maschinenurteile, nicht die der Leserin.**
Ticket 21 hieß zuerst „deine eigenen Sterne". Sie entstanden im Gespräch, von
einem Modell, gegen denselben Maßstab, den das Tor benutzt. Sie als menschlich
zu importieren hätte dreizehn Vorschläge dauerhaft zu Tatsachen gemacht — an
genau der Stelle, die ADR 17 einbaut, um das zu verhindern.

**Und sie tragen kein `confidence`-Feld.** Das Ticket behauptete es. Ein
einziger Eintrag trägt einen `hinweis`, und der bittet um Gegenprüfung der
Identifikation — etwas ganz anderes.

**„Die ISBN verbindet die Quellen."** Aus *einem* Buch geschlossen. Gemessen an
zweien: eines teilt die ISBN, eines nicht. Der Matcher-Rückfall ist der
Normalfall, nicht der Randfall. ADR 18 trägt die Korrektur mit Zahlen.

**316 Entdeckungen sind nicht der tägliche Stapel.** Ich hatte sie so
beschriftet. Es ist ein einmaliger Rückstand plus die Abrufmenge je Lauf; der
tägliche Zuwachs war **null**.

### Über Messungen

**„Die Testsuite braucht 88 Sekunden."** Sie brauchte 11,7. Frei erfunden.

**„Google Books findet nichts."** `429 Quota exceeded` ist kein Befund. Mit
Schlüssel: 13 von 30.

**„Die DNB hat keine Reihen und keine Cover."** Eine Aussage über meine
Abfrage, nicht über die DNB: `oai_dc` trägt beides nicht. Mit `MARC21-xml`
kommen Reihen, und Cover liegen hinter einem eigenen Dienst.

**„Der DNB-Cover-Dienst ist nutzbar."** Die DNB sagt selbst, dass sie diese
Bilder weder besitzt noch speichert und dass die Vereinbarung *Bibliotheken*
berechtigt.

### Über den eigenen Entwurf

**„Das Urteil gehört an die `book`-Zeile" (ADR 19).** Hätte dreihundert
ungeprüfte Buch-Zeilen pro Lauf erzwungen — genau das, was ADR 18 abgelehnt
hatte.

**Der Bündelfilter hätte echte Bücher weggeworfen.** „Zahl am Anfang" trifft
`5 Cottages`, `7 Momente in Angst`, `21 – Fremder Schatten`. Die stehen jetzt
als Gegenprobe im Test.

**Der Freitext-Trenner machte „Band 1" zur Autorin.** Der Ausdruck teilt an der
letzten Trennung, weil der Name hinten steht — ein angehängter Bandzusatz sieht
von hinten aus wie ein Name.

**Die Preisregel tut nicht, was sie verspricht.** „Entdeckungen nur als Deal"
heißt praktisch „unter 5,00 €", weil die Buchpreisbindung Streichpreise
verbietet und ein neuer Fund keine Vorgeschichte hat. Angewandt ließ sie neun
Titel eines Selfpublishers durch und schwieg zu einem neuen Nesbø.

### Über den eigenen Entwurf, zweiter Durchgang

**Eine Regel im ADR ist keine Regel im Code.** ADR 20 beschrieb die
Arbeitsteilung zwischen HTMX und Alpine so genau, dass „welche Zeilen sind
angehakt" wörtlich als Alpine-Fall dasteht. Acht Tickets lang wurde Alpine
geholt, gepinnt — und von keinem Template geladen. Es fiel niemandem auf, weil
nichts fehlte: eine ungenutzte Abhängigkeit sieht aus wie eine benutzte.

**Die uneinheitlichen Autorennamen waren kein Anzeigeproblem.** Notiert war
„der Shop liefert `Barnes, S. A.`". Die Ursache war, *wer zuerst da war*: den
Buch-Eintrag legte der einmalige Auflöser aus `dismissed.yaml` an, und
`find_or_create_book` überschrieb nie etwas. Die Regel dafür lag seit Ticket 16
ungenutzt in `cleaning.py`.

### Fehler in ausgeliefertem Code

- **Alle Autor:innen teilten sich eine Aussaat** — eine neue Referenzautor:in
  meldete ihre ganze Backlist als Neuzugänge.
- **Der Matcher hielt Teilmengen für Treffer** (`token_set_ratio` = 100).
- **Ein Watchlist-Titel wurde bei der ersten Sichtung verschwiegen**, außer er
  war schon billig.
- **Streng an der Vordertür, offen an der Hintertür**: die Erstsichtung
  brauchte einen Deal, ein Preissturz nicht.
- **`beam` und `voebb` sind dreimal in die Oberfläche gerutscht** — Watchlist,
  Buchseite, Übersicht. Dreimal dieselbe Entscheidung, dreimal eine übersehen.
  Jetzt beantwortet die Registry sie.
- **Der Import erfand Quellennamen** aus `check_library` / `check_shop`.
- **Eine Einschränkung ließ sich setzen, aber nie aufheben.**
- **Das Stylesheet hatte keine Version** — ein Browser behielt seine alte Kopie,
  und das sah überzeugend nach kaputtem Template aus.
- **Ein frischer Klon konnte nicht bauen**: die Fehlermeldung nannte einen
  Befehl, der selbst nicht laufen konnte.
- **Eine Migration verwies auf eine Tabelle, die eine spätere fallen ließ** —
  jedes Upgrade von Version 0 wäre gestorben.
- **Das Ablehnungs-Nachschlagewerk wuchs mit dem Stapel** (~2,5 s je Lauf bei
  dreihundert).
- **`ic-dots` fehlte im Sprite** — ein Menü mit unsichtbarem Griff.

---

## 3. Woran man das erkennt

Ein Muster zieht sich durch: **plausibel klingende Aussagen über Daten, die
niemand angesehen hat.** Fast jeder Eintrag oben ist so entstanden — eine
Stichprobe von eins, eine Abfrage mit dem falschen Schema, ein Muster, das an
den vorhandenen Beispielen funktionierte.

Was zuverlässig geholfen hat: **an den echten Daten messen, bevor die Regel
geschrieben wird.** Der Bündelfilter, die Preisregel und die Metadatenquellen
sind alle drei erst durch Zahlen richtig geworden — und alle drei klangen
vorher überzeugend.
