# Leseprofil — der Maßstab für Buchbewertungen

**Maßstabsversion: 1**

Diese Zahl wird bei jeder Änderung an den Achsen, ihrer Gewichtung, den
Gegenanzeigen oder der Sternedefinition erhöht. Jede Bewertung schreibt mit,
gegen welche Version sie entstand — sonst stehen irgendwann Sterne aus drei
Fassungen nebeneinander und die Liste ist nicht mehr sortierbar. Nachbewertet
wird **nicht** automatisch (ADR 17).

Dies ist der **standardisierte Teil** des Profile (siehe `CONTEXT.md`): woran sich
entscheidet, ob ein Buch passt, und was ein Stern bedeutet. Versioniert, damit
zwei Bewertungen desselben Buches zum selben Ergebnis kommen.

Die **persönlichen Listen** liegen bewusst nicht hier, sondern lokal in `data/`
(gitignored): `profile.yaml` (Reference Authors, Genre Categories, `no_gos`,
`liked_books`) und `owned.yaml`. Der Maßstab gehört ins Repo, die Lesedaten nicht.

---

## 1. Die Kernachsen

Nach Gewicht geordnet. **Genre ist zweitrangig** — Thriller, Science-Fiction,
Fantasy, Dystopie und schwarzhumoriger Krimi sind alle zulässig, solange die
Achsen tragen.

> **Maschinell lesbar?** Hinter jeder Achse steht, woraus sie sich ohne Menschen
> ableiten ließe. Das ist keine Spitzfindigkeit: derselbe Maßstab soll später
> jeden gefundenen Titel vorsortieren, und was in keinen Daten steht, kann er
> nicht bewerten.

### A. Reihe mit wiederkehrender Hauptfigur — stärkstes Signal

Empirisch: *alle* mit fünf Sternen bewerteten Bücher im Bestand sind Reihen,
fast alle Vier-Sterne-Bücher sind Einzelbände. Eine Figur, die über mehrere
Bände getragen wird, ist der verlässlichste Treffer.

Nicht ausreichend: dass ein Buch *Band 1* von irgendetwas ist. Es zählt, ob die
**Figur** wiederkehrt und trägt — eine Reihe aus wechselnden Ermittlern in
derselben Stadt ist etwas anderes.

*Maschinell: halb.* Die Onleihe benennt die Reihe in einem eigenen Feld, beam
versteckt sie im Titel („Otherland. Band 1"). Dass die **Figur** wiederkehrt,
steht in keinen Metadaten — dafür braucht es den Klappentext oder eine Recherche.

### B. Unverwechselbare Erzählstimme, meist beschädigt

Camille Preaker schneidet sich, Harry Hole säuft, David Hunter trauert, Vlad
Taltos ist ein Auftragsmörder mit loser Zunge, Don Tillman ist sozial verdrahtet
wie ein Schaltplan, Björn Diemel mordet achtsam. Die Figur hat einen Defekt oder
eine Eigenheit, durch die der ganze Text gefärbt ist.

Schwächer, wenn: mehrere gleichrangige Erzählperspektiven, auktoriale Distanz,
oder eine Hauptfigur ohne erkennbare Bruchstelle.

*Maschinell: unzuverlässig.* Klappentexte verraten es manchmal („Ein Ermittler
am Abgrund"), oft nicht — und das Fehlen beweist nichts. Diese Achse ist der
Grund, warum es das Feld `confidence` gibt.

### C. Katz-und-Maus

Ein psychologisches Duell oder eine Jagd mit tödlichem Einsatz, bei der beide
Seiten handeln. Profiler gegen Täter, Gejagte gegen Apparat.

Nicht dasselbe: eine Ermittlung, in der nur eine Seite agiert und die andere
Spuren hinterlässt.

*Maschinell: ja, aus dem Klappentext.* „Jagd", „Duell", „Profiler", „er weiß,
dass sie ihn sucht".

### D. Isoliertes Setting

Einsames Raumschiff, abgeriegelter Tatort, geschlossene Anstalt, Insel, Bunker.
Die Enge muss die Handlung erzwingen, nicht nur Kulisse sein.

*Maschinell: ja, aus dem Klappentext.* Ort und Konstellation stehen dort fast
immer.

### E. Düsternis und Tempo

Beklemmend, plotgetrieben, zügig. Ein Buch darf langsam brennen (*Cry Baby*,
*The Circle* stehen auf der Positivliste), aber nicht auf der Stelle treten.

*Maschinell: schwach.* Nur über den Ton des Klappentexts und die Kategorie.

---

## 2. Gegenanzeigen

- **Seichter Cozy-Krimi** — der einzige verbliebene harte No-Go.
- **Young-Adult-Register** — deutlich weicher als das Profil verlangt.
- Die ursprünglichen No-Gos *Romantik-Subplot* und *langatmiger Weltenbau* sind
  **gefallen**: *Das Rosie-Projekt* und *Otherland* stehen auf der Positivliste
  und wären an beiden gescheitert. Ein Kriterium, das die eigenen Lieblingsbücher
  aussortiert, ist ein schlechtes Kriterium.

---

## 3. Sterne

| Sterne | Bedeutung |
|---|---|
| **5** | Trägt mindestens drei Kernachsen, darunter zwingend **A und B**. |
| **4** | Trägt zwei bis drei Achsen, mit einer klar benennbaren Lücke — typisch: starker Einzelband ohne Reihe. |
| **3** | Trägt genau eine Achse überzeugend, sonst nur Genre-Nähe. |
| **2** | Nur Genre-Nähe, keine Achse trägt. |
| **1** | Kaum Berührung mit dem Profil. |
| **0** | Gegenanzeige (siehe 2). |

Bewertet wird die **Passung zum Profil, nicht die Qualität des Buches.** Ein
hervorragender Cozy-Krimi bekommt null Sterne.

Es gibt **eine** Skala. Auch der automatische Vorfilter vergibt Sterne, nicht
eine zweite Größe — sonst bedeuten Zahlen je nach Herkunft etwas anderes.

### Wie belastbar ist eine Bewertung? — `confidence`

Weil Achse B maschinell unzuverlässig bleibt, trägt jede Bewertung dazu, worauf
sie ruht:

| Wert | Bedeutung |
|---|---|
| `belegt` | Jede tragende Achse ist aus Daten oder geprüfter Quelle nachgewiesen. |
| `teils` | Mindestens eine tragende Achse ist erschlossen — die Begründung sagt welche. |
| `vermutet` | Ruht überwiegend auf Ableitung. |

`vermutet` ist für den automatischen Vorfilter zulässig — bei hundert Funden pro
Lauf kann er nicht hundertmal recherchieren. Für eine Bewertung von Hand ist es
**ein Fehler**: dort wird recherchiert, bis mindestens `teils` erreicht ist.

Das ist der Unterschied, an dem es schon einmal gescheitert ist: `low` hieß
damals „ich habe nicht nachgesehen", was etwas ganz anderes ist als „ich habe
nachgesehen und es steht nirgends".

---

## 3b. Die Gegenprobe

Der Maßstab war anfangs **ausschließlich aus Zustimmung gebaut** — neun Bücher,
die gefielen, keines, das enttäuschte. Entsprechend lagen alle dreizehn
bewerteten Bücher zwischen drei und fünf Sternen. Eine Skala, an deren unterem
Ende nie etwas landet, unterscheidet nicht, sie bestätigt.

Deshalb sammelt `data/profile.yaml` auch `disliked_books`, jeweils mit dem
Grund. Am wertvollsten ist dabei nicht der Cozy-Krimi, den der Maßstab ohnehin
aussortiert, sondern **ein Buch, das auf dem Papier perfekt passte und trotzdem
verloren hat**. Genau das trennt einen Maßstab von einem Genre-Filter.

Ein hoch bewertetes Buch auf dieser Liste ist ein Befund über den Maßstab,
nicht über den Leser.

---

## 4. Wie eine Begründung auszusehen hat

Eine Begründung muss vier Dinge leisten. Fehlt eines, ist sie unbrauchbar.

1. **Welche Achse** getroffen oder verfehlt wird — benannt, nicht angedeutet.
2. **Woran im Buch** das festzumachen ist: die konkrete Figur, Konstellation oder
   Situation. Nicht das Etikett.
3. **Warum das für diesen Leser zählt** — nach Möglichkeit die Brücke zu einem
   Buch von der Positivliste.
4. **Was den Stern kostet**, bei allem unter fünf. Ausdrücklich.

### Verboten

| Untugend | Beispiel |
|---|---|
| Tatsache statt Grund | „Band 1 einer Reihe um Margarete von Brühl." |
| Zirkelschluss | „Trifft den Kern." / „Passt gut zum Profil." |
| Genre-Etikett allein | „Cyberpunk-Dystopie." |
| Verstecktes Nichtwissen | „Zur Erzählstimme kann ich nichts sagen." → **nachschlagen** |

### Gut

> **1942 – Das Labor · Paul Schüler — ★★★**
> Eine Physikerin sabotiert die Uranmaschine, an der sie selbst gebaut hat,
> während die Gestapo ihr im Nacken sitzt — Katz-und-Maus (C) mit vertauschten
> Rollen, gejagt statt jagend. Margarete von Brühl trägt die Reihe über mehrere
> Bände (A). Zwei Sterne kostet, dass die Stimme (B) nicht die Bruchstelle hat,
> die Harry Hole oder Camille Preaker tragen, und dass das historische Setting
> keine der isolierten Konstellationen (D) aufbaut.

Der Unterschied zum Verbotenen: es steht da, *was passiert* und *welche Achse*
das bedient — und der fehlende Stern ist begründet, nicht bloß vergeben.

---

## 5. Nichts erfinden

Wenn Reihe, Erzählperspektive oder Zielgruppe eines Buches unklar sind, wird
**nachgeschlagen**, bevor bewertet wird. Unsicherheit zu etikettieren statt sie
aufzulösen hat sich als teurer Fehler erwiesen: bei der ersten Bewertung des
Bestands waren drei von vier so markierten Büchern zu niedrig eingestuft, und in
einem Fall war die Autorin schlicht nicht ermittelt worden.
