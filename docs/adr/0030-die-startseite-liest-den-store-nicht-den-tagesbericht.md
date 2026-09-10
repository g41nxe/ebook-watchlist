# 30. Die Startseite liest den Store, nicht den Tagesbericht

`/` zeigt, was heute zählt — zuletzt geprüft, jetzt zu haben, zu entscheiden —
und rechnet das bei jedem Aufruf aus dem Store aus. Der Tagesbericht wird dafür
nicht ein zweites Mal gespeichert. Die Übersicht zieht nach `/uebersicht`.

## Kontext

Bis Issue #5 war `/` die Übersicht: Quellen, Läufe, Tagesberichte, der
Lauf-Knopf — eine Wartungsansicht als Begrüßung. Die neue Startseite sollte
„die besten Deals aus der Watchlist" und „was seit der letzten Aktualisierung
neu ist" zeigen. Der erste Entwurf wollte dafür den Tagesbericht des letzten
Laufs lesen, und weil der nur als gerendertes HTML liegt, standen drei Wege
zur Wahl: das HTML parsen, den Tagesbericht zusätzlich strukturiert ablegen
(JSON neben dem HTML, eine `digest_entry`-Tabelle oder eine `digest_json`-Spalte
auf `run`), oder ihn beim Aufruf neu berechnen.

Die Frage war falsch gestellt. Ein Tagesbericht enthält nichts, was der Store
nicht schon hätte: Titel, Preis und Verfügbarkeit stehen in `observation`,
die Art einer Änderung ist eine reine Funktion aus zwei Beobachtungen
(`diff.compare`), das Schnäppchen eine aus Beobachtung und Profil
(`deals.deal_flags`), das Urteil steht in `rating`, Fehler und Anzahl der
Änderungen an der `run`-Zeile. ADR 15 sagt es seit jeher: ein Modell, zwei
Renderer — der Tagesbericht ist eine *Darstellung*, keine Quelle.

## Entscheidung

**Die Startseite liest den Store**, über dieselben Wege wie Watchlist und
Stapel: `watchlist.entries()` für das, was jetzt zu haben ist, `triage.pending()`
für das, was zu entscheiden ist, `recent_runs()` für die Statuszeile. Kein neuer
Speicher, keine Migration, keine dritte Darstellung des Tagesberichts.

**Der Preis dafür ist bekannt und gewollt.** Neu berechnet ist nicht identisch
mit „was der Lauf damals sagte": ändert die Leserin die Schwellwerte in
`profile.yaml`, zeigt die Startseite das heutige Urteil über gestrige Daten.
Für eine Seite, die den aktuellen Stand zeigen soll, ist das richtig. Die
archivierten Tagesberichte bleiben das Protokoll dessen, was gemeldet wurde.

**Die Übersicht zieht nach `/uebersicht`** und bleibt sonst, wie sie ist.
Es gibt keinen Navigationspunkt „Start": fünf Punkte brechen auf 375 px in
zwei Zeilen — genau der Fehler, den `4e2ea5e` behoben hatte. Zeichen und Name
in der Kopfzeile führen auf `/`.

**Was die Startseite nicht zeigt** — nach Design-Review und Nutzerrecherche
(docs/reviews/design-review-2026-09-09.md,
docs/research/startseite-tracking-werkzeuge.md): keine Zahlenleiste, deren
Zahlen die Liste darunter zählen; nicht den Slogan als Überschrift, der schon
in der Kopfzeile steht; keine Verkaufsargumente über den eigenen Daten. Die
stehen nur im Leerzustand vor dem ersten Lauf — Rückkehrer blenden sie aus,
und die oberste Bildschirmhälfte gehört ihren Daten.

## Folgen

- `web/home.py` ist ein View-Builder wie `watchlist.py` und `triage.py`, ohne
  eigenen Zustand. Wer die Startseite ändert, ändert Auswahl und Darstellung,
  nie Speicherung.
- Wer später Historie über viele Läufe auswerten will („alle Schnäppchen der
  letzten 30 Tage"), braucht dafür eine Abfrage über `observation`, keinen
  gespeicherten Tagesbericht — die Daten sind da.
- Die Statuszeile ist die einzige Stelle der Startseite, die vom *Lauf*
  spricht; alles über den Zustand des Werkzeugs bleibt auf der Übersicht.
