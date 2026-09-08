# Brief: das Zeichen und die Bilder

Dieses Dokument hält fest, was die Anwendung an Zeichen und Bildern braucht, welche
Regeln dabei gelten und woran frühere Anläufe gescheitert sind. Es löst ein früheres,
gleichnamiges Briefing ab, das nur außerhalb des Repositories lag.

Anhang A ist die Arbeitsanweisung für ein Sprachmodell, das Entwürfe des Zeichens als
SVG liefern soll. Anhang B enthält die Prompts für die drei Bilder. Wer eine Runde
wiederholt, ändert die Anhänge, nicht das Briefing.

---

## Was Buchfink ist

Buchfink führt eine persönliche Leseliste und sieht täglich für sie nach: Ist der
Titel in der Stadtbibliothek ausleihbar geworden, ist er im Buchladen billiger?
Gemeldet wird nur, was sich geändert hat. Daneben schlägt Buchfink Bücher vor, die
zum Lesegeschmack passen, und begründet jeden Vorschlag in einem Satz.

Es läuft im eigenen Netz, hat eine Nutzerin, kein Konto und keine Werbung. Der Ton
ist ruhig. Die Zeile unter dem Namen lautet: *Weniger Suchen. Mehr Lesen.*

Der Name ist ein Wortspiel: Der Buchfink (*Fringilla coelebs*) ist ein häufiger
europäischer Singvogel, und im Deutschen steckt das Buch im Namen. Ein Vogel, der
Bücher findet. Artgenauigkeit ist nicht gefordert — niemand bestimmt in einer
Werkzeugleiste Vögel.

---

## Was gebraucht wird

Vier Dinge, in einer Bildsprache.

| Was | Größe | Form | Wo |
| --- | --- | --- | --- |
| Zeichen | 40 × 40 px | SVG, beide Farbfassungen in einer Datei | Kopfzeile, links neben dem Namen |
| Tab-Fassung | 16 × 16 px | SVG, eigene Datei, eigens für diese Größe gebaut | Browser-Tab |
| Drei Bilder | ~480 × 360 px, 4:3 | Rasterbild, ein Bild je Motiv | README und Startseite |

**Ein Stil für alles.** Das Zeichen ist der Vogel allein. Die Bilder zeigen denselben
Vogel im selben Stil, nur mit mehr Gegenständen. Sie sollen nicht wie zwei Marken
wirken, sondern wie ein Zeichen und seine ausführlicheren Verwandten.

**Zwei Größen, zwei Dateien.** Kopfzeile und Tab teilen sich keine Datei mehr. Was
bei 40 Pixeln trägt, trägt bei 16 nicht, und umgekehrt kostet die Rücksicht auf 16
Pixel dem größeren Zeichen zu viel. Wer eines ändert, muss ans andere denken.

---

## Farbe

In der Oberfläche steht jede der beiden Farben für eine Sache, durchgängig, in jeder
Liste und auf jedem Abzeichen. Sie sind Vokabular, kein Schmuck.

| Bedeutung | heller Modus | dunkler Modus |
| --- | --- | --- |
| Bibliothek, ausleihbar | `#28605A` | `#82BBB3` |
| Buchladen, Preis gefallen | `#876125` | `#CCAC76` |

Die Untergründe: `#FAF8F4` im hellen Modus, `#0F0F13` im dunklen; die Kopfzeile liegt
dort bei `#18181C`, beide mit 85 % Deckkraft über der Seite.

**Erlaubt und erwünscht ist eine Rampe aus diesen Tönen.** Die Bedeutung hängt an den
beiden Grundwerten; ihre Abstufungen sind Material für Flächen. Bewährt haben sich:

| Rolle | hell | dunkel |
| --- | --- | --- |
| Teal, dunkelste Stufe | `#00312C` | `#053631` |
| Teal, mittlere Stufe | `#558C85` | `#558C85` |
| Teal, hellste Stufe | `#9AC9C2` | `#B2D7D1` |
| Blaugrau als Unbunt | `#5D7A80` | `#809EA5` |

**Wirkung kommt aus Helligkeit, nicht aus Sättigung.** Im dunklen Modus stehen die
Akzente hell auf fast schwarzem Grund — ein Helligkeitsabstand von rund 0,58 bei einer
Sättigung von nur 0,06. Deshalb wirkt die Oberfläche dort, als leuchte sie. Das
Zeichen soll nicht kräftiger werden als die Oberfläche; ein satteres Grün wäre ein
anderes Grün als das, das „ausleihbar" bedeutet.

**Zwei gedämpfte Farben zu gleichen Teilen, ohne Neutral dazwischen, mischen sich
optisch zu Braun.** Ein erster Entwurf teilte die Fläche 51 : 49 auf und wirkte
schmutzig. Eine Farbe soll führen.

---

## Regeln

**So wenige Formen wie nötig, damit ein Buchfink erkennbar bleibt.** Keine feste
Obergrenze. Die Regel gilt für die 16-Pixel-Fassung, wo sie ihren Grund hat; beim
großen Zeichen und in den Bildern zählt stattdessen, dass eine Geste trägt, der sich
das Übrige unterordnet.

**Nichts, was bei 16 Pixeln verschwindet** — in der Tab-Fassung. Konturlinien,
Verläufe, Halbtransparenz und feine Binnenzeichnung fallen darunter, nicht aus
Geschmack, sondern weil sie rechnerisch nicht mehr da sind: Zwei von tausend
Bildpunkten Strichstärke sind bei 16 Pixeln 0,03 Pixel.

**Keine Wortmarke.** Der Name steht in der Kopfzeile daneben, in der Schrift der
Anwendung. Buchstaben im Zeichen stünden doppelt.

**Flache Flächen.** Keine Verläufe, keine Schlagschatten, keine Halbtransparenz, keine
Filter. Im Zeichen auch kein Korn und keine Textur — beides existiert bei 40 Pixeln
nicht. In den Bildern ist Textur erlaubt.

**Quadratisch und ohne Rahmen** beim Zeichen: kein umschließender Kreis, keine Kachel,
kein Behälter. Es liegt direkt auf der Leiste; ein Zeichen mit eigener Kachel fiele
als Fremdkörper auf.

---

## Was ausgeschieden wurde, und warum

| Richtung | Grund |
| --- | --- |
| Kupferstich, feine Schraffuren | Linien von ein bis zwei Bildpunkten bei 160 px sind bei 40 px ein Viertel Pixel |
| Vogelbuch-Tafel, wissenschaftliche Illustration | zu detailreich, trägt klein nicht |
| Art déco | Linienwelt, scheitert an derselben Grenze; wirkt außerdem fremd neben der ruhigen Oberfläche |
| Bleiglas mit dunklen Konturen | trägt groß, verliert bei 40 px die Kontur und damit die Figur |
| 3D und isometrisch | Sprache für Tech-Produkte und Arbeitsabläufe, nicht für ein stilles Lesewerkzeug |

Riso-Anmutung mit Korn und Fehlregistrierung wäre für die Bilder brauchbar, für das
Zeichen nicht: Das Korn existiert bei 40 Pixeln nicht.

---

## Erfahrung aus früheren Anläufen

Vier Durchläufe mit Bildmodellen wurden nachgemessen. Die Befunde sind Material, keine
Vorschriften.

- **Sieben Formen verschmolzen bei 16 Pixeln, vier trugen.**
- **Was breiter als hoch ist, verliert im quadratischen Feld Größe** (1,20 gegen 0,95).
- **Drei von vier Durchläufen verfehlten die vorgegebenen Farbwerte**, teils um bis zu
  50 Rotwerte, weil sie sie „in dieser Richtung" auslegten.
- **Ein Balken, der mitten in einer Fläche endet, liest sich als Schnitt, nicht als
  Kante** — das Auge sucht das zweite Ende und findet keins.
- **Vier Merkmale ergeben kein Zeichen.** Ein Entwurf, den man nur als Aufzählung
  beschreiben kann, bleibt nicht im Gedächtnis.

Und ein Befund aus dieser Runde: **Eine Größenprobe wird behauptet, nicht durchgeführt.**
In drei von vier Abgaben stand eine Kachel mit der Beschriftung „16 × 16, unvergrößert";
nachgemessen enthielt sie ein Bild vom Achtfachen. Wer klein nicht wirklich rechnet,
liefert eine Behauptung.

---

## Umgebung

Das Zeichen sitzt links außen in einer schmalen Leiste, unmittelbar neben dem Namen.
Die Leiste ist rund 64 Pixel hoch, das Zeichen 40; seitlich bleiben 12 Pixel bis zum
Namen. Der Name steht halbfett in der Systemschrift, darunter die Zeile in 11 Pixeln,
Versalien, gesperrt. Rechts liegt die Navigation in gedämpfter Farbe.

**In dieser Leiste gibt es sonst keine Farbe.** Was das Zeichen an Sättigung
mitbringt, steht allein; es hat nichts, wogegen es sich behaupten müsste, und nichts,
was es abfedert.

---

## Anhang A: Arbeitsanweisung für ein Sprachmodell

Der folgende Text weist ein Sprachmodell an, als Grafikerin zu arbeiten und das
Zeichen als SVG zu zeichnen. Das Briefing oben wird darunter mitgegeben.

```text
Du bist Grafikdesigner:in mit Schwerpunkt auf Zeichen, die bei sehr kleinen
Größen funktionieren — Favicons, App-Symbole, Zeichen in Werkzeugleisten. Du
lieferst SVG von Hand, kein Rasterbild und kein nachgezeichnetes Modellbild.

Unten steht ein Briefing. Arbeite es in dieser Reihenfolge ab.

1  ZWANG ZUERST
   Benenne in zwei Sätzen die Anforderung, an der jeder Entwurf scheitern wird,
   bevor du irgendetwas zeichnest.

2  SECHS VARIANTEN
   Zeichne sechs deutlich verschiedene Entwürfe des Zeichens, nicht sechs
   Fassungen desselben Gedankens. Variiere, was den Vogel ausmacht: ganzer
   Vogel im Profil, nur der Kopf, im Anflug, eine einzige Fläche mit einem
   Akzent, stärker abstrahiert, stärker naturnah. Jeder muss als kleiner
   Singvogel lesbar bleiben.

   Für jede Variante: SVG, viewBox 0 0 40 40, flache Flächen, keine
   Konturlinien, keine Verläufe, keine Transparenz, keine Filter, kein Text.
   Nenne die Zahl der Flächen und gib jedem Pfad einen Kommentar.

3  BEIDE FARBFASSUNGEN
   Jede Variante trägt beide Farbsätze in einer Datei, umgeschaltet per
   @media (prefers-color-scheme: dark) im eigenen <style>-Block. Eine Fläche,
   die auf einem der beiden Untergründe verschwindet, ist ein Fehler.

4  PROBE BEI 40 UND 16 PIXELN
   Rechne jede Variante wirklich auf 40 und auf 16 Pixel herunter und
   beschreibe, was dabei verschwindet. Wenn du das nicht kannst, sag das —
   eine ehrliche Fehlanzeige ist brauchbar, eine behauptete Prüfung nicht.

5  EMPFEHLUNG
   Sag, welche Variante du für die Kopfzeile empfiehlst und warum, an den
   Vorgaben des Briefings begründet, nicht am Geschmack. Sag auch, was du
   damit aufgibst.

REGELN
   - Halte die Farbwerte des Briefings exakt ein, Ziffer für Ziffer.
   - Kein Text, keine Buchstaben, kein umschließender Kreis, keine Kachel.
   - Vermeide, was jedes Modell zuerst vorschlägt: den Kreis mit Motiv darin,
     das Blatt mit umgeknickter Ecke, die aufgeschlagenen Seiten als Möwenform.
   - Weniger Formen ist besser, solange ein Buchfink erkennbar bleibt.

Hier ist das Briefing:
[BRIEFING EINFÜGEN]
```

---

## Anhang B: Prompts für die drei Bilder

Drei Bilder für die drei Verkaufsargumente. Der **Stilblock** steht in allen drei
Prompts wortgleich, damit derselbe Vogel darin auftritt; nur der **Szenenblock**
wechselt. Auf Englisch, weil Bildmodelle damit zuverlässiger arbeiten.

**Stilblock, unverändert in allen drei Prompts:**

```text
Flat vector illustration, 4:3 landscape, roughly 480x360.
Subject: a chaffinch — a small European songbird with a teal-grey cap running
down the nape, a rust-amber face and breast, and one clear off-white wing bar.
Built from simple geometric shapes: circles, arcs and straight tangents.
Hard edges, no outlines, no gradients, no shadows, no 3D, no lettering.
Calm and restrained, in the tradition of mid-century flat illustration.
Colours, exactly these and nothing else:
  #28605A desaturated teal green — the library colour
  #876125 muted amber brown — the bookshop colour
  #FAF8F4 warm off-white — wing bar and highlights
  a calm sage green background, mid-lightness, so the picture sits calmly on
  both a #FAF8F4 and a #0F0F13 page.
The bird is large in the frame and is the one dominant shape; the objects
around it are secondary.
```

**Szene 1, Bibliothek — „Lesen, ohne zu warten":**

```text
Scene: the chaffinch has just landed on a small stack of books and holds one
single book in its beak, tilted towards the viewer. That one book is teal
green; the books in the stack below it are muted and darker. Its wings are
just folding. The gesture reads as: he fetched it for you.
```

**Szene 2, Buchladen — „Kaufen, wenn es sich lohnt":**

```text
Scene: a price tag hangs from a book on a short string. The chaffinch has
gripped the tag in its beak and is pulling it downwards, so the string and
tag form a clear diagonal. The tag is amber brown and has the classic price
tag shape: a rounded corner at the top left with a small round hole in it,
tapering to a point at the bottom right. The gesture reads as: the price
falls.
```

**Szene 3, Entdecken — „Neues finden, das zu dir passt":**

```text
Scene: a tall tower built from stacked books, seen from the side. The
chaffinch sits on top of it and looks into the distance. At the foot of the
tower lie a few more books, muted; exactly one of them is bright amber brown
and stands out. The gesture reads as: from up here he spots the one that
suits you.
```
