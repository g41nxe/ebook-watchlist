---
name: buch-bewerten
description: Bewertet Bücher mit 0-5 Sternen danach, wie gut sie zum Leseprofil passen. Nimmt einzelne Titel entgegen oder verarbeitet eine YAML-Datei und schreibt die Bewertung dort hinein.
---

# Buch bewerten

Beantwortet die Frage „passt dieses Buch zu mir?" gegen einen versionierten
Maßstab statt gegen ein Bauchgefühl. Bewertet wird die **Passung zum Profile**
(siehe `CONTEXT.md`), ausdrücklich *nicht* die Qualität des Buches — ein
hervorragender Cozy-Krimi bekommt null Sterne.

## Ablauf

1. **Maßstab laden.** Immer zuerst [`docs/leseprofil.md`](../../../docs/leseprofil.md)
   vollständig lesen. Dort stehen die Kernachsen, die Gegenanzeigen, die
   Sternedefinition und die Regeln für Begründungen. Nichts davon aus dem
   Gedächtnis rekonstruieren — die Datei ist die Wahrheit und ändert sich.

   Ergänzend `data/profile.yaml` lesen (Reference Authors, `liked_books`,
   `no_gos`) und, falls vorhanden, `data/owned.yaml`. Diese Listen liegen lokal
   und sind nicht im Repo; fehlen sie, wird ohne sie bewertet und das im
   Ergebnis vermerkt.

2. **Eingabeart bestimmen.**
   - **Einzelne Titel** (im Gespräch genannt): bewerten und im Chat antworten.
     Keine Datei anfassen, außer der Benutzer verlangt es.
   - **YAML-Datei** (Pfad genannt): jeden Eintrag bewerten und `stars` sowie
     `why` **in die Datei zurückschreiben**. Bestehende Kommentare und die
     Reihenfolge der Einträge bleiben erhalten.

3. **Fehlendes Wissen auflösen, nicht etikettieren.** Bevor ein Buch bewertet
   wird, müssen drei Dinge bekannt sein: Ist es Teil einer Reihe mit
   wiederkehrender Hauptfigur? Aus welcher Perspektive wird erzählt? Für welche
   Zielgruppe? Ist eines davon unklar, **erst nachschlagen** — Websuche, oder
   der Klappentext auf der Produktseite der Shop Source.

   Eine Bewertung mit dem Vermerk „dazu kann ich nichts sagen" ist kein
   Ergebnis, sondern eine ausgelassene Arbeit.

4. **Bewerten.** Sterne strikt nach der Tabelle in `docs/leseprofil.md`. Für
   jedes Buch festhalten, welche Kernachsen tragen und welche nicht — das ist
   die Grundlage der Begründung und entscheidet die Sterne.

5. **Begründen.** Jede Begründung muss die vier Anforderungen aus Abschnitt 4
   von `docs/leseprofil.md` erfüllen: benannte Achse, konkreter Beleg aus dem
   Buch, Brücke zum Leser, und bei allem unter fünf Sternen die ausdrückliche
   Angabe, was den Stern kostet.

6. **Belastbarkeit und Version festhalten.** Jede Bewertung trägt `confidence`
   (`belegt` / `teils` / `vermutet`, Bedeutung in `docs/leseprofil.md`) und die
   **Maßstabsversion**, gegen die sie entstand. `vermutet` ist hier ein Fehler:
   in diesem Skill wird recherchiert, bis mindestens `teils` erreicht ist.

7. **Ergebnis sichern.** Bei einer YAML-Datei nach dem Schreiben einmal einlesen
   und prüfen, dass die Datei gültig ist und alle Einträge eine Bewertung haben.
   Im Chat die Verteilung nennen, damit auffällt, wenn alles gleich bewertet
   wurde — eine Bewertung, die nicht unterscheidet, ist wertlos.

## Richtlinien & Best Practices

- **Nichts erfinden.** Lieber eine Recherche mehr als eine plausible Behauptung.
  Bleibt etwas nach der Recherche offen, wird es benannt und *nicht* in die
  Bewertung eingerechnet.
- **Keine Gefälligkeitsbewertung.** Wenn die Verteilung keine Bücher unter vier
  Sternen kennt, unterscheidet der Maßstab nicht mehr. Gegenanzeigen ziehen
  wirklich auf null.
- **Widersprüche melden, nicht glattbügeln.** Passt ein Buch, das der Benutzer
  offensichtlich mag, schlecht zum Maßstab, ist das ein Befund über den
  *Maßstab*. Melden und `leseprofil-schaerfen` vorschlagen, nicht die Bewertung
  hochdrehen.
- **Begriffe aus `CONTEXT.md`** verwenden: Profile, Watchlist, Watchlist Entry,
  Reference Author, Source, Observation, Digest.
- **Der Maßstab wird nie angefasst.** Dieser Skill liest `docs/leseprofil.md`
  und schreibt ausschließlich in die übergebene Buchliste — nie in den Maßstab,
  nie in `data/profile.yaml`. Ein Messgerät, das sich selbst kalibriert, misst
  nichts mehr. Änderungen am Profil gehören zu `leseprofil-schaerfen`.
- **Persönliche Lesedaten bleiben in `data/`.** Nie nach `docs/` oder in einen
  Commit schreiben, außer der Benutzer verlangt es ausdrücklich.

<yaml-format>
Erwartetes und erzeugtes Format einer Buchliste:

```yaml
- title: 1942 - Das Labor
  author: Paul Schüler
  stars: 3            # 0-5, null nur solange unbewertet
  why: >
    Begründung nach den vier Regeln aus docs/leseprofil.md.
  confidence: belegt   # belegt | teils | vermutet
  massstab: 1          # Version aus docs/leseprofil.md
  hinweis: optional - Unklarheiten, abweichende Titelvarianten, Rückfragen
```

`title` und `author` sind Pflicht, alles andere wird vom Skill ergänzt.
Ein Eintrag ohne `author` wird vor der Bewertung recherchiert.
</yaml-format>
