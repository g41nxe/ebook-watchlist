# 27. Ein eigener Titel, den niemand findet, ist eine Frage

`not_found` bleibt eine Antwort — außer bei einem Titel, den die Leserin selbst
geschrieben hat und den **keine** Quelle findet.

## Kontext

Ticket 04 hat festgelegt: `not_found` gehört nicht auf die Liste, die um
Mithilfe bittet — sonst füllt sie sich mit Zeilen, bei denen es nichts zu
entscheiden gibt. Für einen Fund aus der Genre-Suche stimmt das unverändert.

Am 6.9.2026 standen neun der fünfzehn Watchlist-Titel auf `not_found`. Von Hand
aufgelöst in einer Viertelstunde:

| Ausgang | Zahl |
|---|---|
| der Titel war falsch, umbenannt → sofort `linked` | **7** |
| tatsächlich nicht im Katalog | 2 |

„Der Bosch-Fall" war eine Beschreibung aus einem Dokument, kein Titel;
„Dunkle Gefilde" hieß auf Deutsch „Profit"; „Das Knochennest" heißt
„Das Knochenband". Kein einziger existierte unter dem eingetragenen Namen.
Darunter ein Schnäppchen zu 2,99 €, das über einen Tag unsichtbar blieb.

`not_found` sagt hier nichts über das Buch. Es sagt etwas über die **Eingabe**.

## Entscheidung

**Ausgelöst wird, wenn alle geprüften Quellen `not_found` melden** — nicht
schon bei einer. Gemessen:

```
Shop linked      Bibliothek not_found   10
Shop not_found   Bibliothek not_found    2
Shop unsure      Bibliothek not_found    1
Shop confirmed   Bibliothek not_found    1
```

**Vierzehn von vierzehn** Einträgen stehen bei der Onleihe auf `not_found` — sie
führt die meisten schlicht nicht. „Eine Quelle reicht" hätte jeden Titel jeden
Tag gemeldet. „Alle Quellen" hätte gestern acht gemeldet, sechs davon zu Recht.

Geprüft heißt: was `restrict` zulässt. Wer einen Eintrag auf „nur Shop" gestellt
hat, wartet nicht auf die Bibliothek.

**Der Hinweis lässt sich wegklicken, und das hält** — wie die Ablehnung in
Ticket 41. Die beiden heute gemeldeten Titel sind richtig benannt; ein Hinweis,
der dafür täglich erscheint, wird zu Tapete.

**Gemerkt wird der Titel, nicht das Buch.** Wer „Hardware" als bekannt
weggeklickt hat und den Eintrag später umbenennt, bekommt den Hinweis wieder —
denn dann ist es eine neue Behauptung über eine neue Eingabe.

**Und der Eintrag lässt sich an Ort und Stelle umbenennen.** Ein Hinweis ohne
Abhilfe wäre ein Vorwurf: die Oberfläche konnte einen Watchlist-Titel bisher
gar nicht ändern, die sieben Korrekturen liefen über SQL von Hand.

Umbenannt wird die **bestehende** Buch-Zeile, nicht eine neue angelegt. Notiz,
Beziehung, Urteile und Geschichte hängen daran; ein Ersatz ließe sie am alten
Eintrag zurück. Die Zuordnungen dagegen fallen weg — sie galten für den alten
Titel und wären nach einer Umbenennung eine Behauptung über etwas anderes.

## Folgen

- Ein falscher Titel ist sichtbar, statt still zu bleiben.
- Die Watchlist bekommt ihre erste Bearbeitungsmöglichkeit über den Titel selbst.
- Ein Fund aus der Genre-Suche löst weiterhin nichts aus — Ticket 04 gilt dort
  unverändert.
- Die Umbenennung wirft die Zuordnungen weg und stößt damit eine neue Suche an.
  Das ist beabsichtigt und der ganze Zweck.
