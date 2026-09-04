---
name: leseprofil-schaerfen
description: Überarbeitet den Leseprofil-Maßstab anhand neu genannter Bücher. Misst den Maßstab gegen die Bücher, nicht umgekehrt, und holt vor jeder Änderung die Zustimmung des Benutzers ein.
---

# Leseprofil schärfen

Nimmt neu genannte Bücher entgegen und prüft, ob der **Maßstab** sie richtig
einordnet. Ein Buch, das der Benutzer mochte und das schlecht bewertet wird, ist
ein Befund über `docs/leseprofil.md` — nicht über das Buch.

Dieser Skill ist der einzige, der den Maßstab ändern darf. `buch-bewerten`
wendet ihn nur an; würde es ihn nachjustieren, kalibrierte sich das Messgerät
selbst und misst nichts mehr.

## Ablauf

1. **Bewerten lassen.** Die neuen Bücher durch `buch-bewerten` schicken —
   inklusive Recherche, sonst sind die Achsen unbekannt. Das Ergebnis ist die
   Messung, nicht schon die Schlussfolgerung.

2. **Drei Prüfungen pro Buch.**
   - Widerspricht es einer **Gegenanzeige**, obwohl der Benutzer es mochte?
   - Trägt es etwas, das der Maßstab **gar nicht kennt**?
   - Steht es auf `liked_books` und wird trotzdem **niedrig** bewertet — oder auf
     `disliked_books` und wird **hoch** bewertet?

   Die dritte ist der eigentliche Detektor. Beide Richtungen zählen gleich: ein
   fälschlich aussortiertes Buch wiegt so schwer wie ein fälschlich empfohlenes.

3. **Nach Stufe einsortieren.** Die Beweislast ist bewusst **asymmetrisch**.

   | Stufe | Änderung | Beweislast |
   |---|---|---|
   | 1 | `liked_books` / `disliked_books` ergänzen, Reference Author vorschlagen | keine |
   | 2 | Gegenanzeige streichen oder abschwächen | **ein** Widerspruch |
   | 3 | Achse hinzufügen, entfernen, umgewichten; Sternedefinition ändern | **zwei unabhängige** Bücher |

   Der Grund für die Asymmetrie: Eine falsche Gegenanzeige richtet sofort und
   unsichtbar Schaden an — sie sortiert Bücher aus, von denen der Benutzer nie
   erfährt. Eine falsch gewichtete Achse kostet nur Rangfolge, das Buch taucht
   auf, nur weiter unten. Deshalb: **Streichen billig, Gewichten teuer.**

   Reicht ein Beleg für Stufe 3 nicht aus, wird die Beobachtung trotzdem als
   **Notiz** im Maßstab festgehalten — sie wirkt noch nicht auf Bewertungen,
   geht aber nicht verloren. Kommt der zweite Beleg, wird ein Vorschlag daraus.

4. **Zustimmung einholen — pro Änderung, nicht als Paket.** Stufe 1 läuft still
   durch. Jede Änderung der Stufen 2 und 3 wird einzeln vorgelegt, mit dem
   Beleg, der sie auslöst, und mit den Alternativen. Nicht „ich habe das Profil
   überarbeitet, schau mal drüber".

5. **Schreiben.**
   - Stufe 1 → `data/profile.yaml` (bleibt lokal, nichts davon ins Repo).
   - Stufe 2 und 3 → `docs/leseprofil.md`, **Maßstabsversion erhöhen**, und
     committen. Die Commit-Nachricht nennt das Buch, das die Änderung ausgelöst
     hat. In einem halben Jahr ist das der Unterschied zwischen „warum steht das
     da" und `git log`.

6. **Veraltete Bewertungen melden, nicht neu rechnen.** Nach einer Stufe-2- oder
   Stufe-3-Änderung sagen, wie viele bestehende Bewertungen gegen eine ältere
   Maßstabsversion entstanden sind. Der Benutzer entscheidet, ob nachbewertet
   wird — bei dreizehn Büchern lohnt es, bei achthundert nicht.

## Richtlinien & Best Practices

- **Der Maßstab ist verdächtig, nicht der Leser.** Ein Widerspruch wird nie
  dadurch aufgelöst, dass das Buch nachträglich schlechtgeredet wird.
- **Nichts ohne Beleg ändern.** „Wirkt so" ist kein Beleg. Ein Beleg ist ein
  benanntes Buch mit einer benannten Achse.
- **Zwei Belege heißt zwei *unabhängige*.** Zwei Bände derselben Reihe oder zwei
  Bücher derselben Autorin sind ein Beleg.
- **Nie stillschweigend gewichten.** Jede Änderung an einer Achse verschiebt
  *alle* künftigen Bewertungen — auch die des automatischen Vorfilters.
- **Begriffe aus `CONTEXT.md`**: Profile, Reference Author, Watchlist, Source,
  Observation, Digest.

<vorlage-fuer-eine-rueckfrage>
So wird eine Stufe-2-Änderung vorgelegt:

> **Das Rosie-Projekt · Graeme Simsion** steht auf deiner Positivliste, wird vom
> Maßstab aber durch die Gegenanzeige „Romantik-Subplot" auf null Sterne
> gesetzt.
>
> Ein Kriterium, das deine eigenen Lieblingsbücher aussortiert, ist ein
> schlechtes Kriterium.
>
> **Streichen** / **Abschwächen** („dominante Romantik ohne eigenen Plot") /
> **Behalten** (dann bleibt das Buch eine bewusste Ausnahme)?

Immer mit dem auslösenden Buch, immer mit einer Alternative zum Streichen.
</vorlage-fuer-eine-rueckfrage>
