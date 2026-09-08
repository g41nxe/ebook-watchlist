# 28. Tests bleiben unabhängig, geteilt wird der Aufbau

Die Suite tauscht keine Unabhängigkeit gegen Geschwindigkeit. Sie teilt, was
nach dem Bau keinen Zustand trägt, und misst, bevor sie optimiert.

## Kontext

Ticket 18 hat die Suite von 108 s auf 28 s gedrückt, das Ziel von zehn
Sekunden verfehlt und den Rest als „diffus" beschrieben: kein Ausreißer, Tests,
die echte Arbeit tun. Der damals benannte nächste Schritt war, Ende-zu-Ende-
Tests zusammenzulegen — Unabhängigkeit gegen Geschwindigkeit. Diese
Entscheidung blieb acht Wochen offen. Ticket 55 maß am 6.9.2026 768 Tests in
78 s auf acht Kernen; die Messung hier ist vom 7.9., 803 Tests, 95 s auf
acht Kernen, 254 s einkernig.

Einkernig, je Modul:

| Modul | Zeit | Tests | je Test |
|---|---|---|---|
| test_run_now | 62,7 s | 12 | 5,2 s |
| test_web_book | 23,9 s | 43 | 0,56 s |
| test_web_triage | 23,6 s | 34 | 0,69 s |
| übrige Web-Module | je 6–13 s | | ~0,6 s |
| test_rating | 6,2 s | 85 | 0,07 s |

Die Zeit ist **nicht diffus**. Zwei Posten tragen sie:

- **Sieben Tests starten je einen echten Kindprozess** `python -m
  ebook_watchlist.run`. Ein Prozessstart kostet 7 s, weil allein der Import
  des Pakets 4,5 s dauert: `store` zieht SQLAlchemy (1,1 s), `gate` zieht
  `rating`, das `requests` auf Modulebene importiert (zusammen 1,0 s),
  `filelock` allein kostet 0,7 s. Das ist ein Viertel der einkernigen Suite.
- **Jeder Web-Test baut die Anwendung neu.** `create_app()` kostet 0,30 s —
  FastAPI registriert 24 Routen samt Pydantic-Modellen —, die erste Anfrage
  danach 0,22 s, weil Jinja die Vorlagen übersetzt. Jede weitere 0,09 s.
  182 Tests bauen einen Client; das sind rund 95 s einkernig für Aufbau,
  der sich zwischen zwei Tests nie unterscheidet.

Die zwei Tests, die laut Ticket 55 seriell umfallen, fielen am 7.9. nicht
um: 803 seriell grün, die zwei Module auch zu zweit hintereinander. Ohne
Reproduktion gibt es nichts zu reparieren.

## Entscheidung

**Die Suite hat keine absolute Zielzeit.** Gemessen wird einkernig je Modul,
vor jedem Eingriff neu. Angegangen wird, was mehr als ein Zehntel der
Gesamtzeit trägt und sich ohne Verlust an Unabhängigkeit senken lässt. Was
darunter liegt, bleibt liegen.

**Geteilt werden darf, was nach dem Bau keinen Zustand hält.** Das ist die
Schema-Vorlage und die geparsten Fixtures (Ticket 18) und jetzt die
Anwendung: `create_app()` läuft einmal je Test-Session. Das ist das Muster
der FastAPI-Dokumentation — dort ist `app` ein Modul-Singleton, und die
Isolation kommt aus dem Zustand je Test. Bei uns ist dieser Zustand das
Datenverzeichnis, das die Anwendung bei jeder Anfrage neu aus `EBW_DATA_DIR`
auflöst.

**Nie geteilt:** Datenbank, Datenverzeichnis, Kindprozesse — und die zwei
Dinge, die die Anwendung selbst hält: der `RunLauncher` mit dem gestarteten
Kind und der `Rechecker` mit den laufenden engen Läufen. Beide sind
ausdrücklich eine Instanz je Anwendung, damit nichts zwischen Tests leckt.
Ein Modul, das eines von beiden treibt, baut seine Anwendung weiter je Test.

**Ein echter Prozess je Beweis, nicht je Zustand.** Dass der Knopf ein
eigenes Kind startet, das den Request überlebt und ins Journal schreibt,
beweist einmal ein echter Lauf. Die übrigen Zustände der Seite — hört auf zu
pollen, zeigt den Fehler, prallt an der Sperre ab — sind Zustände des
Journals und des Kindes, und beide kann der Test selbst herstellen: die
Journalzeile über den Store, das Kind als Prozess, der nichts importiert.

**Der Importpreis ist ein Produktproblem.** Jeder `ebw`-Aufruf und jeder
Lauf-Knopf zahlt die 4,5 s, die Suite zahlt sie je xdist-Arbeiter. Gesenkt
wird er im Paket, nicht in der Suite: Ticket 57.

## Folgen

- Kein Test wird zusammengelegt. Fällt einer, fällt einer.
- Der `/covers`-Mount zeigt für die ganze Session auf das Verzeichnis des
  ersten Tests. Wer künftig Titelbilder über den Client abruft, braucht eine
  eigene Anwendung — die Fixture sagt das.
- Die Zahl nach dem Eingriff steht im Commit, nicht hier.
