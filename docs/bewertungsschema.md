# Bewertungsschema — wie ein Buch gegen ein Leseprofil gehalten wird

Dieses Dokument beschreibt das **Verfahren**: was ein Stern bedeutet, was eine
Begründung leisten muss, worauf ein Urteil ruhen darf und was es dann noch darf.

Es nennt **keinen einzigen inhaltlichen Maßstab.** Was jemand mag, steht in
`leseprofil.md`; hier steht nur, wie man ein Buch dagegen hält. Für eine andere
Leserin mit einem anderen Profil bliebe dieses Dokument unverändert brauchbar.

**Es ist nicht versioniert.** Eine Änderung hier entwertet keine einzige
gespeicherte Bewertung. Nur eine Änderung am Leseprofil tut das — und zwar,
weil sich dann der Geschmack geändert hat, gegen den geurteilt wurde (ADR 21).

Es gilt für **beide** Bewerter: den Skill `buch-bewerten` und das Bewertungstor
im Lauf. Bevor es dieses Dokument gab, hatten die beiden bereits verschiedene
Regeln — mit demselben Sternemaß.

---

## 1. Was bewertet wird

Die **Passung zum Profil, nicht die Qualität des Buches.** Ein hervorragender
Roman, der nichts von dem trägt, was das Profil verlangt, bekommt wenige Sterne;
das ist kein Urteil über das Buch, sondern über die Passung.

Es gibt **eine** Skala. Auch der automatische Vorfilter vergibt Sterne, nicht
eine zweite Größe — sonst bedeutet dieselbe Zahl je nach Herkunft etwas anderes.

---

## 2. Sterne

Das Profil benennt selbst, was ihm am wichtigsten ist. Diese Tabelle spricht
deshalb vom **Kern** des Profils und nicht von einer festen Liste von
Kriterien — welche das sind und wie sie wiegen, entscheidet allein das Profil.

| Sterne | Bedeutung |
|---|---|
| **5** | Trifft den Kern des Profils, und keine wesentliche Erwartung wird verfehlt. |
| **4** | Trifft den Kern, mit **einer klar benennbaren** Lücke. |
| **3** | Trifft eine Sache überzeugend, sonst nur Genre-Nähe. |
| **2** | Nur Genre-Nähe. Nichts, was das Profil ausdrücklich verlangt. |
| **1** | Kaum Berührung mit dem Profil. |
| **0** | Eine Gegenanzeige des Profils greift. |

Zwei Regeln zur Tabelle:

- **Eine Gegenanzeige schlägt alles.** Sie zieht auf null, gleichgültig wie viel
  sonst passt. Sonst ist sie keine.
- **Vier ist kein Trostpreis.** Der Unterschied zwischen fünf und vier ist eine
  Lücke, die sich *benennen* lässt. Findet sich keine, sind es fünf.

Wenn eine Bewertung keine Bücher unter vier Sternen kennt, unterscheidet sie
nicht mehr, sondern bestätigt nur. Das ist ein Befund über das Verfahren, nicht
über die Bücher.

---

## 3. Worauf ein Urteil ruht — `confidence`

Manches, was ein Profil verlangt, steht in keinen Metadaten und oft nicht einmal
im Klappentext. Ob eine Erzählstimme trägt, lässt sich selten ablesen; dass der
Klappentext dazu schweigt, beweist nichts. Deshalb trägt jedes Urteil mit, worauf
es ruht:

| Wert | Bedeutung |
|---|---|
| `belegt` | Alles, was das Urteil trägt, ist aus Daten oder geprüfter Quelle nachgewiesen. |
| `teils` | Mindestens eines ist erschlossen — die Begründung sagt, welches. |
| `vermutet` | Ruht überwiegend auf Ableitung. |

`vermutet` heißt **nicht** „ich habe nicht nachgesehen". Es heißt „ich habe
nachgesehen und es steht nirgends". Der Unterschied ist der, an dem dieses
Verfahren schon einmal gescheitert ist.

### Was ein vermutetes Urteil darf

**Es darf kein Buch zurückhalten.**

Ein Buch durchzulassen oder einzuordnen darf auf Ableitung ruhen. Ein Buch aus
dem Digest zu nehmen verlangt mindestens `teils`.

Der Grund ist eine Asymmetrie, die dieses Projekt an mehreren Stellen trägt: ein
zu Unrecht gezeigtes Buch kostet eine Zeile, die die Leserin überspringt. Ein zu
Unrecht verschwiegenes ist **unsichtbar** — sie erfährt nie, dass es das Buch
gab, und kann den Fehler nicht bemerken. Wo geraten werden muss, wird deshalb zu
Gunsten des Zeigens geraten.

### Wann recherchiert werden muss

Wer **recherchieren kann, muss es**. Ein Mensch mit einer Websuche schlägt nach,
bis mindestens `teils` erreicht ist; dort ist `vermutet` ein Fehler und keine
Auskunft.

Ein automatischer Lauf kann das nicht — bei hundert Funden kann er nicht
hundertmal recherchieren. Für ihn ist `vermutet` zulässig, und die Regel oben
sagt, was daraus folgen darf.

---

## 4. Die Gegenprobe

Ein Profil, das nur aus Zustimmung gebaut ist, weiß nicht, wo seine Grenze
verläuft. Wird alles zwischen drei und fünf Sternen bewertet, bestätigt die
Skala nur.

Deshalb gehören Bücher, die **enttäuscht** haben, ebenso ins Profil wie die
gemochten — jeweils mit dem Grund. Am wertvollsten ist dabei nicht das Buch, das
ohnehin an einer Gegenanzeige scheitert, sondern **eines, das auf dem Papier
perfekt passte und trotzdem verloren hat.** Genau das trennt ein Profil von
einem Genre-Filter.

Und die Richtung der Schlussfolgerung steht fest: **ein gemochtes Buch, das
schlecht bewertet wird, ist ein Befund über das Profil — nicht über das Buch.**
Ein Widerspruch wird nie dadurch aufgelöst, dass das Buch nachträglich
schlechtgeredet wird.

---

## 5. Wie eine Begründung auszusehen hat

Vier Dinge. Fehlt eines, ist die Begründung unbrauchbar.

1. **Welcher Teil des Profils** getroffen oder verfehlt wird — benannt, nicht
   angedeutet. Mit den Worten des Profils.
2. **Woran im Buch** das festzumachen ist: die konkrete Figur, Konstellation oder
   Situation. Nicht das Etikett.
3. **Warum das für diese Leserin zählt** — nach Möglichkeit die Brücke zu einem
   Buch, das sie nachweislich mochte.
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
> während die Gestapo ihr im Nacken sitzt: ein Duell mit tödlichem Einsatz, bei
> dem beide Seiten handeln — nur mit vertauschten Rollen, gejagt statt jagend.
> Zwei Sterne kostet, dass die Erzählstimme keine der Bruchstellen hat, die das
> Profil verlangt, und dass das historische Setting keine der engen
> Konstellationen aufbaut, aus denen die Handlung sonst ihren Druck bezieht.

Der Unterschied zum Verbotenen: es steht da, *was im Buch passiert* und *welche
Erwartung des Profils* das bedient — und der fehlende Stern ist begründet, nicht
bloß vergeben.

---

## 6. Nichts erfinden

Ist unklar, was ein Buch trägt, wird **nachgeschlagen**, bevor bewertet wird —
soweit die Lage das zulässt (siehe 3). Unsicherheit zu etikettieren statt sie
aufzulösen hat sich als teurer Fehler erwiesen: bei der ersten Bewertung eines
Bestands waren drei von vier so markierten Büchern zu niedrig eingestuft, und in
einem Fall war die Autorin schlicht nicht ermittelt worden.

Was auch nach der Recherche offen bleibt, wird **benannt** und nicht in die
Bewertung eingerechnet. Eine Begründung, die eine Lücke verschweigt, ist
schlimmer als eine, die sie ausspricht: die erste sieht aus wie ein Ergebnis.
