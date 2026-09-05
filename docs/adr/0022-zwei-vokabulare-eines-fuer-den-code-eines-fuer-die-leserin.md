# 22. Zwei Vokabulare: eines für den Code, eines für die Leserin

Der Code und das Glossar bleiben englisch. Alles, was die Leserin liest, ist
deutsch — und für jeden englischen Fachbegriff gibt es genau **ein** deutsches
Wort, das im Glossar danebensteht.

## Context

Die Oberfläche spricht deutsch, `CONTEXT.md` spricht englisch. Beides für sich
ist konsistent; in Fließtext rutschen sie ineinander, und dann steht in einem
deutschen Satz „Lauf/Tor/Digest".

Gezählt, statt geschätzt:

| Fläche | deutsch | englisch |
|---|---|---|
| Oberfläche (Templates) | Lauf 13, Schnäppchen 5, Urteil 4, Vorschlag 2 | **Digest 4** |
| README | Lauf 7 | Run 18, Deal 8, Digest 5, Snapshot 4, Observation 3 |

Die Oberfläche war also fast sauber — mit *einem* Eindringling. Die README war
die eigentliche Baustelle: sie sprach die Codebegriffe, während die Anwendung
deutsch mit der Leserin redet.

Dazu ein Wackler ohne Sprachgrenze: *Fund* und *Entdeckung* standen für
dieselbe Sache.

## Decision

**Der Code bleibt englisch.** Klassennamen, Tabellen, Routen, Dateinamen. Ein
deutsch-englischer Mischcode wäre schlimmer als die Sprachgrenze, und das
Glossar beschreibt den Code.

**Alles Gelesene wird deutsch.** Oberfläche, Tagesbericht, README, `docs/`.

**Das Glossar trägt beide.** Jeder Eintrag nennt hinter dem englischen Namen
sein deutsches Wort — das ist die Brücke, die bisher fehlte.

Die Zuordnung:

| Code / Glossar | Leserin |
|---|---|
| Run | Lauf |
| Digest | **Tagesbericht** |
| Rating Gate | Bewertungstor, kurz „das Tor" |
| Rating | Urteil |
| Observation | Beobachtung |
| Discovery | **Fund** |
| Snapshot | **Aufzeichnung** |
| Deal / Strong Deal | Schnäppchen |
| Reading Profile | Leseprofil |
| Rating Scheme | Bewertungsschema |
| Reference Author | Referenzautor:in |
| Genre Category | Thema |

**Fund und Vorschlag sind nicht dasselbe.** Ein **Fund** ist, was ein Lauf
gesehen hat. Ein **Vorschlag** ist ein Fund, der auf eine Entscheidung wartet —
also einer, der es durch Müllfilter, Preisregel und Tor geschafft hat. Das
benutzten wir schon halb unbewusst; jetzt ist es festgelegt.

**In einem Kommentar zählt, wovon die Rede ist.** Wer das Codeobjekt meint,
schreibt `Digest` in Backticks. Wer die Sache meint, die bei der Leserin
ankommt, schreibt Tagesbericht. Deshalb bleiben Kommentare, die eine Klasse
benennen, wie sie sind.

## Consequences

- Eine Umbenennung im Code steht ausdrücklich **nicht** an. Der Preis dafür
  wäre eine Migration und ein Bruch mit ADR 16 (Migrationen werden nur
  angehängt) — für null Gewinn bei der Leserin.
- Wer ein neues Wort einführt, trägt es ins Glossar, oder es gibt zwei.
- Die Tabelle oben ist die Prüfliste für jede neue Seite und jeden neuen Text.
