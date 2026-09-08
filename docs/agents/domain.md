# Domain-Dokumentation

Wie die Engineering-Skills die Domain-Dokumentation dieses Repos lesen sollen,
bevor sie den Code erkunden.

**Dieses Repo ist ein Einzel-Kontext**: eine `CONTEXT.md` und ein `docs/adr/` im
Wurzelverzeichnis.

## Vor dem Erkunden lesen

- **`CONTEXT.md`** — das Glossar. Jeder Begriff ist englisch und trägt genau ein
  deutsches Wort darunter (ADR 22).
- **`docs/adr/`** — die festgehaltenen Entscheidungen, nummeriert
  `NNNN-<deutscher-slug>.md`. Die ADRs lesen, die den Bereich berühren, an dem
  gearbeitet wird; viele tragen einen *Nachtrag*, der festhält, was sich in der
  Umsetzung als falsch erwies.
- **`docs/offene-punkte.md`** — was fehlt, und welche Behauptungen sich als
  falsch herausgestellt haben.

Fehlt eine dieser Dateien, **stillschweigend weitermachen**. Nicht anmahnen,
nicht vorab anlegen. `/domain-modeling` legt sie an, sobald ein Begriff oder eine
Entscheidung tatsächlich geklärt wird.

## Das Vokabular des Glossars benutzen

Wer in seiner Ausgabe einen Domainbegriff nennt (Issue-Titel,
Refactoring-Vorschlag, Hypothese, Testname), benutzt den Begriff so, wie
`CONTEXT.md` ihn definiert. Code und Bezeichner nehmen den englischen Namen,
lesbarer Text das deutsche Wort. Keine Synonyme, die das Glossar ausdrücklich
meidet — *Fund* und *Vorschlag* sind zum Beispiel nicht dasselbe.

Fehlt der gebrauchte Begriff im Glossar, ist das ein Signal: entweder wird
Sprache erfunden, die das Projekt nicht spricht (nochmal überlegen), oder es gibt
eine echte Lücke (für `/domain-modeling` notieren).

## ADR-Konflikte benennen

Widerspricht eine Ausgabe einem bestehenden ADR, das ausdrücklich sagen, statt es
stillschweigend zu übergehen:

> _Widerspricht ADR 18 (Phase-2-Datenmodell) — aber es lohnt sich, das neu
> aufzumachen, weil …_

Neue ADRs setzen die Nummerierung fort (als Nächstes 0028), sind deutsch
geschrieben und folgen demselben Dateinamenmuster. Die Abschnittsüberschriften
bleiben `Context`, `Decision`, `Consequences`.
