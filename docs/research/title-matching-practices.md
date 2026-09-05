# Wie andere Titel zuordnen — Recherche zu Ticket 36

Anlass: *Dark Matter* (Blake Crouch) bekommt bei uns keine Beobachtung, obwohl
der Shop das Buch als ersten Treffer führt. Der Shoptitel lautet
„Dark Matter. Der Zeitenläufer", unser Matcher kommt auf 56 von nötigen 85.

Bevor an der Schwelle gedreht wird: was machen andere?

---

## 0. Was bei uns gemessen wurde

Eine Anfrage an den Shop, dann der echte Matcher:

| gesucht | Kachel | normalisiert | Wert | Ergebnis |
|---|---|---|---|---|
| Dark Matter | `Dark Matter. Der Zeitenläufer` | `dark matter der zeitenlaufer` | 56 | kein Treffer |
| Der Schwarm | `Der Schwarm 2 - Die Rückkehr` | `schwarm 2` | 88 | zur Bestätigung |
| Der Kruzifix-Killer | `Der Kruzifix-Killer / Der Vollstrecker` | `kruzifix-killer` | 100, exakt | angenommen |

Zwei Dinge fielen dabei auf:

- Das `subtitle`-Feld der Kachel trägt **„Roman"** — eine Gattungsangabe. Der
  eigentliche Untertitel steckt im Titel. Das vorhandene Feld hilft also nicht.
- Unser `_SUBTITLE`-Trennzeichen kennt ` - `, `: `, ` / `, ` \ ` — **keinen
  Punkt**. Deshalb der Unterschied zwischen Zeile 1 und Zeile 3.
- Der Autor passt in **allen drei** Fällen zu 100 %. Er kann die Fälle nicht
  unterscheiden.

---

## 1. Der Fachstandard löst das nicht im String, sondern im Datenmodell

**MARC 21** (Bibliotheken, auch die DNB) zerlegt den Titel in Unterfelder:

| Unterfeld | Inhalt |
|---|---|
| `245 $a` | der eigentliche Titel |
| `245 $b` | Untertitel / „remainder of the title" |
| `245 $n` | **Nummer** eines Teils oder Abschnitts |
| `245 $p` | **Name** eines Teils oder Abschnitts |
| `490` / `830` | Reihe, wie aufgedruckt / in normierter Form |

**ONIX für Bücher** (Verlage und Handel) macht dasselbe: im `TitleElement`
stehen `TitleWithoutPrefix` und `Subtitle` getrennt, Reihen liegen im
`Collection`-Komposit mit eigener `PartNumber`/`SequenceNumber`. Das
zusammengesetzte `TitleText` ist in ONIX 3.0 **abgeraten** und in 3.1 formal
abgekündigt — genau weil eine Zeichenkette diese Information verliert.

BIC und BISG schärfen zusätzlich ein, dass `Subtitle` **nur** den Untertitel
vom Titelblatt tragen darf, keine Marketingzeile.

> **Folgerung für uns:** „Dark Matter. Der Zeitenläufer" ist kein
> Algorithmusproblem, sondern ein **Datenverlust**. Der Shop hat drei Felder in
> eines gequetscht. Die Antwort der Fachwelt lautet: hol dir den strukturierten
> Datensatz. Das ist unser Ticket 13 (DNB über MARC21-xml) — dieselbe Quelle,
> die uns auch Sprache, Reihe und Bandnummer bringen würde.

---

## 2. Wo doch verglichen wird: nie *ein* Wert mit *einer* Schwelle

**Ex Libris Primo** (Bibliothekssuchmaschine, Dublettenerkennung) benutzt einen
Vektor aus drei Teilen:

- **Kandidatenfelder** (`C1`–`C10`) finden mögliche Partner: UnivID, ISBN,
  **Kurztitel (erste 25 Zeichen)**, Jahr — mit ODER verknüpft.
- **Vergleichsfelder** (`F1`–`F20`) werden dann gewichtet verrechnet.
- Entschieden wird über Punkte: Quick match ab 850, Full match ab 875.

Bemerkenswert sind die **negativen Gewichte**: Titel stimmt nicht = **−600**,
Jahr stimmt nicht = **−250**, während ein exakter Volltitel +600 bringt und
eine gültige ISBN nur +85. Ein Widerspruch *kostet* also, statt bloß nicht zu
belohnen.

Das ist die allgemeine Lehre aus der **Record-Linkage-Literatur**: erst
**Blocking** (billiger Schlüssel, auf Ausbeute gebaut), dann **Scoring**
(teuer, auf Genauigkeit gebaut). Ein Ähnlichkeitswert allein gilt als
unzuverlässig; er muss durch Zusatzmerkmale gestützt werden.

> **Folgerung für uns:** unser `NO_MATCH_BELOW = 85` macht **beides auf
> einmal** — es sucht Kandidaten aus *und* entscheidet. Genau das trennt die
> Literatur. Ein Kurztitel-Präfix als Kandidatenschlüssel hätte *Dark Matter*
> gefunden; die Entscheidung wäre danach eine eigene Frage gewesen.

---

## 3. Die Robustesten vermeiden Titelvergleiche, wo es geht

**Book Data Tools** (offene Sammlung aus LoC-, OpenLibrary- und
GoodReads-Daten) clustert Buchausgaben **ausschließlich über einen
ISBN-Graphen** — Zusammenhangskomponenten über gemeinsame ISBNs. Von
Fuzzy-Matching auf Titel oder Autor ist im ganzen Verfahren keine Rede. Die
dokumentierten Schwächen sind entsprechend andere: wiederverwendete ISBNs und
Sammelausgaben mit eigener ISBN, die Unzusammengehöriges verbinden.

**Open Library** kombiniert Algorithmus und Mensch — und hält ausdrücklich
fest, dass das Zusammenführen von *Works* **manuell** bleibt.

> **Folgerung für uns:** unsere Dreiteilung *automatisch annehmen /
> zur Bestätigung / kein Treffer* (ADR 9) ist keine Notlösung, sondern das,
> was auch Open Library tut. Die neun ungelösten Titel sind kein Versagen des
> Verfahrens — sie sind der Fall, für den der Bestätigungsweg gebaut wurde.
> Was fehlt, ist nicht Automatik, sondern eine bequeme Stelle zum Bestätigen.
>
> Der ISBN-Weg ist bei uns übrigens schon da: die Bestellnummer trägt sie
> (`SW9783104911854…`), und `subject_of` benutzt sie. Wo eine ISBN auf beiden
> Seiten steht, sollte sie den Titelvergleich schlicht überstimmen.

---

## 4. Bandnummern werden herausgelöst, nicht mitverglichen

Wo Reihen vorkommen, ziehen die Werkzeuge die Nummer in ein **eigenes Feld**,
statt sie im Titelstring stehen zu lassen. Calibre benutzt dafür benannte
Gruppen — `(?P<series>…)` und `(?P<series_index>[0-9.]+)` —, MARC hat `245 $n`
und `490 $v`, ONIX die `SequenceNumber`.

> **Folgerung für uns:** die Unterscheidung, die wir suchen — „Zusatz ist ein
> Untertitel" gegen „Zusatz bezeichnet einen anderen Band" — ist nirgends eine
> Frage der Ähnlichkeit. Sie wird beim **Zerlegen** entschieden, bevor
> verglichen wird.

---

## 5. Was das für Ticket 36 bedeutet

Drei Wege, in der Reihenfolge, in der die Fachwelt sie empfiehlt:

1. **Strukturierte Daten holen** (Ticket 13). Löst das Problem an der Wurzel und
   nebenbei Sprache, Reihe und Bandnummer. Teuerster Weg, größter Gewinn.
2. **Kandidatensuche von der Entscheidung trennen.** Ein billiger
   Präfix-/Kurztitel-Schlüssel findet Kandidaten; die Annahme entscheidet
   danach über Titel *und* Autor *und* ISBN, mit Widersprüchen als Abzug. Das
   ist Primos Bauweise und kostet uns keine externe Quelle.
3. **Bandbezeichnung vor dem Vergleich herauslösen.** Kleinster Schritt, löst
   den konkreten Fall, und er ist in jedem der anderen Wege ohnehin nötig.

Was die Recherche **nicht** hergibt: eine Schwelle, die man einfach senken
könnte. Kein untersuchtes System entscheidet über einen einzelnen
Ähnlichkeitswert.

---

## Quellen

- [MARC 21 Format for Bibliographic Data: 245 Title Statement](https://www.loc.gov/marc/bibliographic/bd245.html)
- [MARC 21: 490 Series Statement](https://www.loc.gov/marc/bibliographic/bd490.html)
- [ONIX for Books Implementation and Best Practice Guide 3.0.2](https://www.hanmoto.com/pub/onix/ONIX_for_Books_Global_Best_Practice_3.0.2.html)
- [ONIX Books Sets and Series (EDItEUR)](https://www.editeur.org/files/ONIX%203/ONIX_Books_Sets_and_Series_3.pdf)
- [BIC Statement on Best Practice for Subtitle Field in Metadata Feeds](https://bic.org.uk/press-releases/bic-statement-on-best-practice-for-subtitle-field-in-metadata-feeds/)
- [BISG: Support for effective use of the title and subtitle fields](https://www.bisg.org/support-for-effective-use-of-the-title-and-subtitle-fields)
- [Ex Libris Primo: Duplicate Detection Vector](https://knowledge.exlibrisgroup.com/Primo/Product_Documentation/Primo/Technical_Guide/030Duplicate_Detection_Process/030Duplicate_Detection_Vector)
- [Book Data Tools: Book Clusters](https://bookdata.inertial.science/data/cluster.html)
- [Open Library: About Librarianship](https://openlibrary.org/about/lib)
- [Sven Lieber: Clustering Book editions](https://sven-lieber.org/en/2023/10/16/clustering-book-editions/)
- [A Comparison of Blocking Methods for Record Linkage (arXiv 1407.3191)](https://arxiv.org/pdf/1407.3191)
- [calibre: All about using regular expressions](https://manual.calibre-ebook.com/regexp.html)

Nicht auswertbar: [OCLC, Clustering in WorldCat Discovery](https://www.oclc.org/content/dam/oclc/worldcat-discovery/Clustering-WorldCat-Discovery.pdf)
— das PDF ließ sich nicht in Text überführen.
