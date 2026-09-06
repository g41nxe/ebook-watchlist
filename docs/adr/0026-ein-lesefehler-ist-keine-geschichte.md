# 26. Ein Lesefehler ist keine Geschichte

Die Aufzeichnung wird nicht umgeschrieben — eine **kaputt geparste Spalte**
schon.

## Kontext

Der Shop rendert den Klappentext auf jeder Detailseite zweimal: den sichtbaren
Anriss und den eingeklappten vollen Text, als zwei Kinder unter
`[itemprop=description]`. Für eine Leserin im Browser ist immer nur eins davon
da. Unser Parser nahm `get_text()` über den **Elternknoten** und damit beides.

Gemessen an den gespeicherten Beobachtungen:

| | |
|---|---|
| lange Klappentexte (> 400 Zeichen) | 116, davon **110** doppelt |
| betroffene Bücher | **102** von 393 |
| Ballast, Median je Text | **32 %** |
| die als „abgeschnitten" gelten und deshalb neu geholt würden | **0** |

Die letzte Zeile ist der Kern. `_with_full_blurbs` lädt nur nach, wo
`is_truncated(blurb) or not blurb`. Ein doppelter Text endet auf dem vollen und
nicht auf „…" — er gilt als vollständig. Diese 102 Bücher wären **nie** wieder
angefasst worden, und der Ballast wäre bei jeder neuen Profilversion (Ticket
25) erneut in die Bewertungs-Prompts geflossen.

ADR 5 hält fest, dass `observation` anhängend ist und nie überschrieben wird.
Danach wäre eine Korrektur verboten und der einzige saubere Weg das erneute
Holen von 102 Detailseiten — 102 Anfragen für eine Information, die wir bereits
haben.

## Entscheidung

Zwei Dinge, und die Reihenfolge ist wichtig.

**Der Fehler wird an der Quelle behoben, nicht am Text.** Der Parser greift
`.description--full` und fällt sonst auf `.description--preview` zurück. Ein
Klassenname im Seitengerüst ist stabiler als ein deutsches Wort auf einem
Knopf, und wenn er sich ändert, bricht er zusammen mit allen anderen
Selektoren — laut, in den Tests. Der Schnitt am Aufklapp-Knopf
(`cleaning.without_teaser`) bleibt als **Sicherheitsnetz** für den Fall, dass
der Shop die Klassen umbenennt.

**Die 110 gespeicherten Zeilen werden gekürzt**, in einer Migration, ohne eine
einzige Anfrage. Das Append-only aus ADR 5 schützt die **Zeitreihe** — Preis
und Verfügbarkeit, was der Shop wann gesagt hat. Der Klappentext ist keine:
`diff.py` erwähnt ihn nirgends, niemand vergleicht ihn über die Zeit. Und
korrigiert wird nicht, *was der Shop gesagt hat* — das steht unverändert da —,
sondern **unser Lesefehler beim Einsammeln**. Eine kaputt geparste Spalte zu
reparieren ist eine Migration, keine Geschichtsfälschung.

Der Schnitt ist nachweislich verlustfrei: in **110 von 110** Fällen beginnt der
volle Text mit dem Anriss, und in **keinem einzigen** ist er kürzer.

## Folgen

- Ein Bewertungs-Prompt über 25 betroffene Bücher schrumpft von 74.230 auf
  57.895 Zeichen — **22 % kürzer**, rund 4.000 Tokens je Bündel.
- In der Datenbank stehen 72.630 Zeichen weniger.
- Die Grenze ist gezogen und gilt über diesen Fall hinaus: **was eine Quelle
  gesagt hat, bleibt stehen; wie wir es gelesen haben, darf korrigiert
  werden.** Wer künftig eine Spalte anfassen will, muss zeigen, auf welcher
  Seite dieser Grenze sie liegt.
- `is_truncated` meldet für diese Texte künftig seltener „abgeschnitten" —
  richtig, aber es verändert die Prompts sichtbar. Wer alte und neue Urteile
  vergleicht, sieht dort einen Sprung.
