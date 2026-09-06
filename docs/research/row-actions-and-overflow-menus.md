# Was gehört in das Drei-Punkte-Menü einer Zeile?

Recherche zu Ticket 48/50, September 2026. Anlass: das Menü der Watchlist-Zeile
enthält heute genau **eine** Sache, und die ist keine Handlung, sondern eine
Einstellung — „Prüfen bei: allen Quellen / nur Bibliothek / nur Shop".

## Was heute in der Zeile steht

| Steuerelement | Art | sichtbar |
|---|---|---|
| Titel → `/book/{id}` | Hauptweg | ja, als Verweis |
| Drei-Punkte → „Prüfen bei" | **Einstellung** | Symbol sichtbar, Inhalt verborgen |
| Pause / Fortsetzen | Handlung | ja |
| Zuordnung entscheiden | Handlung, nur im Sonderfall | aufklappbar (Ticket 41) |
| Titel berichtigen | Handlung, nur im Sonderfall | aufklappbar (ADR 27) |

Das Menü trägt also einen einzigen Eintrag, und zwar den untypischsten.

## Was die Praxis sagt

**Ab wann überhaupt ein Menü.** Carbon (IBM) zieht die Grenze bei drei: unter
drei Optionen sollen die Handlungen als einzelne Symbole in der Zeile stehen —
das spart einen Klick und zeigt auf einen Blick, was möglich ist. Ab mehr als
drei gehört alles außer den ein bis zwei häufigsten in ein Überlaufmenü, damit
die Zeile lesbar bleibt.

Für uns heißt das: mit *einem* Eintrag ist das Menü zu viel, mit den vier bis
fünf, die absehbar hineingehören, ist es genau richtig.

**Zerstörerisches wird abgetrennt.** Übereinstimmende Empfehlung: Handlungen
wie Löschen, Deaktivieren, Entfernen gehören in eine **eigene Gruppe** im
Menü, durch eine Linie getrennt — das senkt die Zahl der Fehlgriffe. „Gekauft"
und „nicht mehr relevant" sind in unserem Fall zwar nicht zerstörerisch (ADR 18
löscht nichts), aber sie **beenden** etwas und nehmen den Eintrag aus der
Liste. Sie verdienen dieselbe Trennung.

**Sichtbarkeit hat einen Preis.** Das Drei-Punkte-Symbol wird schlecht
gefunden — die verbreitetste Kritik am Muster. Carbon lässt deshalb die Wahl,
das Symbol dauerhaft oder erst beim Überfahren zu zeigen, **erkennt aber
Berührungsgeräte** und blendet es dort dauerhaft ein. Unsere Zeile zeigt es
dauerhaft, und das ist mit derselben Begründung richtig, mit der die
Zuordnung nichts vom Überfahren abhängig macht: auf einem Telefon gibt es
kein Überfahren.

**Was nicht ins Menü gehört.** Handlungen, die offensichtlich sein müssen oder
schnell rückgängig zu machen sein sollen, bleiben in der Zeile. Das spricht
dafür, Pause dort zu lassen, wo es ist.

**Einstellung ist keine Handlung.** Das ist der Punkt, an dem das heutige Menü
schief liegt. „Prüfen bei" ändert man einmal und selten; es steht zu Recht
verborgen — aber es in denselben Topf zu werfen wie „gekauft" macht aus dem
Menü eine Resterampe. Beides braucht eine eigene, beschriftete Gruppe.

## Was das für uns heißt

Eine Gliederung in drei Abschnitte, durch Linien getrennt:

```
┌─────────────────────────────┐
│ ÖFFNEN                      │
│   Buchseite                 │   ← der Verweis, den heute nur der Titel trägt
├─────────────────────────────┤
│ PRÜFEN BEI                  │
│   allen Quellen             │   ← die heutige Einstellung, unverändert
│   nur Bibliothek            │
│   nur Shop                  │
├─────────────────────────────┤
│   pausieren                 │   ← beendet vorläufig
│   habe ich gekauft          │   ← beendet endgültig, nimmt aus der Liste
│   nicht mehr relevant       │
└─────────────────────────────┘
```

Offen bleibt, ob Pause zusätzlich als Symbol in der Zeile bleibt. Dafür
spricht die schlechte Auffindbarkeit des Menüs und dass Pause reversibel ist;
dagegen, dass dieselbe Handlung dann an zwei Stellen steht.

Für Berührungsgeräte gilt weiterhin das Mindestmaß von 44 px, das `.tun` schon
setzt — die Menüeinträge tragen es heute **nicht**, sie sind auf `py-1.5`
gesetzt.

## Quellen

- [Data table – Carbon Design System](https://carbondesignsystem.com/components/data-table/usage/)
- [Best Practices for Providing Actions in Data Tables – UX Design World](https://uxdworld.com/best-practices-for-providing-actions-in-data-tables/)
- [Design Tip #14 – Destructive Actions in Drop-Down Menu – UX Design World](https://uxdworld.com/design-tip-14-drop-down-menu/)
- [Progressive disclosure – Primer (GitHub)](https://primer.style/product/ui-patterns/progressive-disclosure/)
- [Lists – Material Design 3](https://m3.material.io/components/lists/guidelines)
- [SaaS Data Table & List View UX Patterns (2026)](https://www.saasui.design/blog/saas-data-table-ux-patterns)
