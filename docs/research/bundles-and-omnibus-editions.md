# Wie andere Sammelausgaben behandeln — Recherche zu Ticket 29

Anlass: „Der Kruzifix-Killer / Der Vollstrecker" (zwei Bände in einer Ausgabe)
und „David Hunter: 3in1 Bundle" (drei Bände, kein Bandtitel im Namen).

---

## 0. Zwei Prämissen des Tickets waren falsch

Beides gemessen, bevor recherchiert wurde.

**„Der Matcher wird unsicher."** Nein. Der Normalisierer schneidet am ` / ` ab,
„Der Kruzifix-Killer / Der Vollstrecker" wird zu `kruzifix-killer` und trifft
**exakt**. Das Bündel wird sauber dem richtigen Titel zugeordnet.

**„Ein Bündel trägt in der Regel keine ISBN."** Nein. Alle bekannten Bündel im
Bestand tragen eine:

| Titel | ISBN |
|---|---|
| Der Kruzifix-Killer / Der Vollstrecker | 9783843714594 |
| David Hunter: 3in1 Bundle | 9783644025028 |
| Kakerlaken / Rotkehlchen | 9783843713474 |
| Claire Douglas Bundle (3in1) | 9783641357009 |

Von 390 beobachteten Produkten haben **386 eine ISBN**. Sie taugt nicht als
Bündelmerkmal.

Was bleibt, ist der eigentliche Punkt: **niemand sieht, dass zwei oder drei
Bände drinstecken**, und der Bündelpreis ist kein Preis für den gesuchten Band.

---

## 1. Der Handel hat dafür einen eigenen Code

ONIX kennt in Codeliste 21 (`EditionType`) den Wert **`CMB`**:

> „An edition in which two or more works also published separately are combined
> in a single volume; AKA 'omnibus edition' or occasionally 'bind-up'"
> — [EDItEUR, Codeliste 21](https://ns.editeur.org/onix/en/21/CMB)

Das ist unser Fall, wörtlich. Dazu drei Bausteine:

| Element | Wofür |
|---|---|
| `ContentItem` | listet jeden enthaltenen Titel einzeln |
| `ContainedItem` | für mehrteilige *Pakete* (Schuber, Klassensatz) |
| `RelatedProduct` | verknüpft die Sammelausgabe mit den Einzelbänden |

Die Verknüpfung ist in Codeliste 51 (`ProductRelationCode`) benannt:

- **01 — Includes:** „Product includes RelatedProduct (inverse of code 02)"
- **02 — Is part of:** „Product is part of RelatedProduct"

Bemerkenswert für uns: die ONIX-Praxisleitfäden nennen ausdrücklich **beide**
Schreibweisen für den Titel einer Sammelausgabe — die Einzeltitel *mit
Schrägstrichen aneinandergereiht*, **oder** ein eigener Name plus `ContentItem`
je Titel. Genau diese zwei Formen liegen bei uns auf dem Tisch:

| Form | Beispiel | ONIX-Entsprechung |
|---|---|---|
| Titel mit Schrägstrichen | Der Kruzifix-Killer / Der Vollstrecker | Titelzeile, Bände im Namen |
| eigener Name | David Hunter: 3in1 Bundle | Name + `ContentItem` |

Die Schrägstrich-Form ist also keine Nachlässigkeit des Shops, sondern die vom
Standard vorgesehene Kurzform.

---

## 2. Bibliotheken schreiben den Inhalt in ein eigenes Feld

MARC 21 führt den Inhalt einer Sammelausgabe in **`505`** (formatted contents
note, `$t` je Titel) und legt für die enthaltenen Werke **`740`**-Nebeneinträge
an, damit sie einzeln auffindbar sind.

„Aggregates" — Ausgaben, die mehrere Werke bündeln — gelten in FRBR/RDA
ausdrücklich als schwieriger, ungelöster Sonderfall; sie werden in
Arbeitsgruppen bis heute diskutiert.

> **Folgerung:** die Fachwelt behandelt eine Sammelausgabe als **eigenes
> Produkt mit Beziehungen zu den enthaltenen Werken** — nicht als eine Ausgabe
> „von" einem der Bände. Das beantwortet die offene Frage des Tickets: ein
> Bündel ist ein eigenes Buch, und die Zugehörigkeit ist eine Beziehung.
> Bei uns heißt das: `book_relation` kann das, `book_source` bräuchte nichts
> Neues.

---

## 3. Was der Shop tatsächlich hergibt

Eine Anfrage an die Detailseite des 3in1-Bündels:

- **Keine strukturierte Liste.** Kein `ContentItem`, keine Aufzählung, nichts
  Maschinenlesbares.
- **Die Bände stehen in der Prosa:** „In *Die Chemie des Todes* …", „In *Kalte
  Asche* …", „In *Leichenblässe* …". Drei Titel, erkennbar an der Wendung
  „In <Titel>", aber ohne Auszeichnung.
- **Die Kachel sagt nichts**, außer über den Namen selbst.

Damit gibt es genau drei Wege an die enthaltenen Bände:

1. **Aus dem Namen** — funktioniert bei der Schrägstrich-Form, nicht bei
   „3in1 Bundle".
2. **Aus dem Klappentext** — Prosa, also entweder ein brüchiges Muster oder das
   Modell, das wir ohnehin schon für die Bewertung fragen.
3. **Aus einer Metadatenquelle** (Ticket 13). Ob die DNB `505` liefert, ist
   nicht geprüft.

---

## 4. Was bei uns schon da ist

`junk.py` erkennt Bündel bereits — `Sammelband`, `Bundle`, `3 in 1`, „N Genre:"
— und der Docstring nennt *David Hunter: 3in1 Bundle* ausdrücklich als Fall,
der **kein** Ramsch ist, weil Simon Beckett Referenzautor ist. Was fehlt, ist
nicht die Erkennung, sondern dass daraus eine **Eigenschaft** wird, die man
sehen kann.

Die Schrägstrich-Form fehlt dem Muster. Sie ist aber nicht harmlos: von neun
Titeln mit ` / ` im Bestand ist einer keine Sammelausgabe, sondern Werbung —
„28m² – Die Probandenstudie / Psychothriller / Verlagsbestseller".

---

## Quellen

- [ONIX Codeliste 21, Code CMB](https://ns.editeur.org/onix/en/21/CMB)
- [ONIX Codeliste 51 — ProductRelationCode](https://ns.editeur.org/onix/en/51)
- [ONIX for Books: Sets and Series (EDItEUR)](https://www.editeur.org/files/ONIX%203/ONIX_Books_Sets_and_Series_3.pdf)
- [ONIX: Related products and other product links (EDItEUR)](https://www.editeur.org/files/ONIX%203/APPNOTE%20Related%20products%20and%20other%20product%20links.pdf)
- [BISG Best Practices for Product Metadata](https://static1.squarespace.com/static/550334cbe4b0e08b6885e88f/t/55d2277be4b0a2c68568aaec/1439836027770/BISG_Best_Practices_for_Product_Metadata_6.1.15.pdf)
- [MARC 21: 505 Formatted Contents Note](https://www.loc.gov/marc/bibliographic/bd505.html)
- [Cataloging with MARC, RDA and Classification Systems — major fields](https://idaho.pressbooks.pub/cataloging/chapter/major-marc-fields-subfields-and-indicators/)

Nicht auswertbar: die beiden EDItEUR-PDFs oben ließen sich nicht in Text
überführen; die Codes stammen aus der offiziellen Codelisten-Namensraumseite.
