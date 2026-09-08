# Issue Tracker: GitHub

Issues und PRDs dieses Repos leben als GitHub Issues in `g41nxe/ebook-watchlist`.
Alle Operationen laufen über die `gh`-CLI.

## Konventionen

- **Issue anlegen**: `gh issue create --title "..." --body "..."`. Für mehrzeilige Texte ein Heredoc.
- **Issue lesen**: `gh issue view <nummer> --comments`; Kommentare mit `jq` filtern, Labels mitladen.
- **Issues auflisten**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'`, bei Bedarf mit `--label` und `--state` eingegrenzt.
- **Kommentieren**: `gh issue comment <nummer> --body "..."`
- **Labels setzen / entfernen**: `gh issue edit <nummer> --add-label "..."` / `--remove-label "..."`
- **Schließen**: `gh issue close <nummer> --comment "..."`

Das Repo ergibt sich aus `git remote -v`; innerhalb des Klons findet `gh` es von selbst.

Titel und Text eines Issues sind deutsch — sie werden von einem Menschen gelesen.
Bezeichner aus dem Code bleiben darin englisch und stehen in Backticks (ADR 22).

## Pull Requests als Triage-Oberfläche

**PRs als Anfrage-Oberfläche: nein.** Privates Solo-Repo; `/triage` liest nur Issues.

## Ticketnummern vor GitHub Issues

Bis September 2026 wurden Aufgaben als lokale Markdown-Tickets unter
`.scratch/ebook-watchlist-phase2/issues/` geführt (gitignored, nie eingecheckt).
Verweise wie „Ticket 04" bis „Ticket 56" in ADRs, Commit-Nachrichten und
`docs/offene-punkte.md` meinen **diese Dateien**, nicht GitHub-Issue-Nummern.
Nicht mit `gh issue view` auflösen, sondern als historische Bezeichnungen lesen.

## Wenn ein Skill sagt „publish to the issue tracker"

Ein GitHub Issue anlegen.

## Wenn ein Skill sagt „fetch the relevant ticket"

`gh issue view <nummer> --comments` ausführen.
