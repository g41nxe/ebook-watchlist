# Triage-Labels

Die Skills sprechen von fünf kanonischen Triage-Rollen. Diese Datei ordnet den
Rollen die Label-Strings zu, die im Issue Tracker dieses Repos tatsächlich benutzt
werden.

| Label in mattpocock/skills | Label in unserem Tracker | Bedeutung |
| --- | --- | --- |
| `needs-triage` | `needs-triage` | Maintainer muss das Issue bewerten |
| `needs-info` | `needs-info` | Wartet auf Rückmeldung des Meldenden |
| `ready-for-agent` | `ready-for-agent` | Vollständig spezifiziert, ein Agent kann es ohne Kontext übernehmen |
| `ready-for-human` | `ready-for-human` | Braucht einen Menschen |
| `wontfix` | `wontfix` | Wird nicht gemacht |

Nennt ein Skill eine Rolle (etwa „apply the AFK-ready triage label"), gilt der
Label-String aus dieser Tabelle.

## Labels anlegen

`wontfix` bringt GitHub von Haus aus mit; die anderen vier müssen existieren, bevor
`/triage` läuft. Nach `gh auth login`:

```bash
gh label create needs-triage    --color e4e669 --description "Maintainer muss bewerten"
gh label create needs-info      --color d876e3 --description "Wartet auf Rueckmeldung"
gh label create ready-for-agent --color 0e8a16 --description "Vollstaendig spezifiziert, ein Agent kann uebernehmen"
gh label create ready-for-human --color 1d76db --description "Braucht einen Menschen"
```
