# Leseprofil — was für Bücher ich mag

**Profilversion: 1**

Diese Datei beschreibt einen Geschmack. Sie ist die Grundlage der Entscheidung,
ob eine Beobachtung interessant ist — und sie ist das einzige Dokument in diesem
Projekt, von dem die Leserin sagen können muss: *ja, das bin ich.*

Die Versionsnummer bedeutet genau eine Sache: **den Stand dieses Geschmacks.**
Sie steigt, wenn sich am Inhalt hier etwas ändert, und jede Bewertung schreibt
mit, gegen welche Fassung sie entstand. Nachbewertet wird **nicht** automatisch
(ADR 17). Geändert wird ausschließlich über den Skill `leseprofil-schaerfen`,
mit Beleg und Zustimmung je Änderung.

Wie geurteilt wird, steht **nicht** hier, sondern in
[`bewertungsschema.md`](bewertungsschema.md): Sterne, Begründungspflicht,
`confidence`, Gegenprobe. Das ist Verfahren und gilt für jedes Profil; eine
Änderung dort entwertet keine Bewertung (ADR 21).

Abgeleitet aus dieser Beschreibung, aber nicht selbst Teil von ihr, sind die
**Reference Authors** und die **Genre Categories** in `data/profile.yaml` — das,
wonach ein Shop tatsächlich gefragt werden kann. Sie liegen lokal, zusammen mit
`owned.yaml`: die Beschreibung gehört ins Repo, die Lesedaten nicht.

---

## 1. Die Kernachsen

Nach Gewicht geordnet. **Genre ist zweitrangig** — Thriller, Science-Fiction,
Fantasy, Dystopie und schwarzhumoriger Krimi sind alle zulässig, solange die
Achsen tragen.

> **Maschinell lesbar?** Hinter jeder Achse steht, woraus sie sich ohne Menschen
> ableiten ließe. Das ist keine Spitzfindigkeit: dieselbe Beschreibung soll später
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

## 3. Notizen — Beobachtungen ohne Regelkraft

Einzelne Belege, die eine Achse betreffen, aber noch keine Änderung
rechtfertigen. Stufe-3-Änderungen brauchen **zwei unabhängige** Bücher (ADR 17);
bis dahin steht die Beobachtung hier, damit sie nicht verlorengeht — und wirkt
ausdrücklich **nicht** auf Bewertungen.

- **Achse E bündelt womöglich zwei Dinge.** *Der Schwarm* (Frank Schätzing)
  steht auf `disliked_books`, Grund: langsames Erzähltempo. Das Buch ist dabei
  ausgesprochen düster. Düsternis und Tempo sind also trennbar, und das Tempo
  scheint allein zu genügen, um ein Buch zu verlieren. Ob E deshalb in zwei
  Achsen zerfallen sollte, entscheidet der zweite Beleg.
  *(Eintrag 2026-09-04, ein Beleg)*

- **Nicht Fantasy stört, sondern der mythische Ton.** *Herr der Ringe* steht auf
  `disliked_books` — „klassische Fantasy ist nicht meins". Dem stehen *Yendi*
  und *Otherland* auf der Positivliste gegenüber, beide Fantasy, beide mit
  ausgiebigem Weltenbau. Das Genre trennt die Fälle also nicht. Was sie trennt,
  sind A und B: Vlad Taltos ist ein Auftragsmörder mit loser Zunge in der
  Ich-Form, Tolkien erzählt ein Ensemble in erhabenem Ton. Insoweit bestätigt
  der Fall die bestehenden Achsen.

  Offen bleibt, ob „mythisch-archaischer Erzählmodus" eine eigene Gegenanzeige
  verdient oder ob A und B ihn ohnehin schon abfangen. Zweiter Beleg nötig.
  *(Eintrag 2026-09-04, ein Beleg)*

---
