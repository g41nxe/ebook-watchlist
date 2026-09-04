# Bewerten ohne API-Schlüssel

Recherche zu ADR 19: das Bewertungstor verlangt ein Modellurteil, und die
Leserin hat kein Anthropic-Guthaben und will keins anlegen. Untersucht am
2026-09-04, Schreibtischrecherche gegen offizielle Quellen plus die Dateien
dieses Repositorys. Keine Live-Messung an einem Modell — wo unten eine Zahl
steht, steht dabei, wer sie gemessen hat.

Durchgängig heißt **belegt** eine zitierbare Aussage des Betreibers oder eine
hier nachgerechnete Zahl, **offen** heißt: niemand sagt es, und ich erfinde es
nicht. Die Unterscheidung trägt dieses Dokument, denn die wichtigste Frage —
darf man `claude -p` aus einem Cron-Job aufrufen? — hat eine Antwort, aber
keine so eindeutige, wie es die Aufregung im Netz vermuten lässt.

---

## TL;DR

- **Die tägliche Last ist nicht 40, sondern eine Handvoll.** Das Tor sitzt
  *hinter* der Preisregel (ADR 19). Bewertet wird nur, was ohnehin gemeldet
  würde — eine neue Entdeckung unter 5,00 €. `rating_budget: 40` ist eine
  Obergrenze gegen den einmaligen Rückstand von 316, keine Tageserwartung. Das
  verschiebt die ganze Rechnung, und zwar zugunsten der billigsten Option.
- **`claude -p` ist nicht verboten.** Die Consumer Terms untersagen
  automatisierten Zugriff *„except … where we otherwise explicitly permit it"* —
  und Anthropic benennt `claude -p` in einem eigenen Hilfeartikel als eine
  Nutzungsform, die das Abonnement abdeckt. Verboten ist etwas anderes: die
  Anmeldedaten für *fremde* Nutzer zu vermitteln, sie zu speichern, oder das
  Binary zu verändern. Nichts davon tut ein privater Cron-Job auf dem eigenen
  Rechner.
- **Offen bleibt der Rand.** Anthropic bindet die Grenzwerte an *„ordinary,
  individual usage"* und behält sich Durchsetzung ohne Vorankündigung vor. Wo
  „ordinary" endet, sagt keine Quelle. Ein Buchklassifikator ist keine
  Programmierarbeit; das ist die einzige belastbare Unschärfe in dieser Frage.
- **Ein lokales Modell läuft auf dem Pi, aber vermutlich nicht gut genug.**
  Gemessen sind 5–7 Token/s für ein 3-B-Modell in Q4 auf dem Pi 5 bei ~3,8 GB
  RAM. Das reicht zeitlich bequem. Ob ein 3-B-Modell einen deutschen
  219-Zeichen-Anriss gegen fünf Achsen beurteilen kann, ohne genau die
  „confident nonsense" zu erzeugen, gegen die ADR 19 argumentiert: **ungemessen**
  und nach Lage der Dinge unwahrscheinlich.
- **Einbettungen können das Tor nicht ersetzen** — nicht wegen der Hardware,
  sondern wegen der Aufgabe. Sie liefern keine Begründung, und die Begründung
  ist laut ADR 19 (Ticket 14/20) der Grund, den ein Vorschlag mitbringt. Dazu
  kommt: die Datenlage ist elf Bücher mit zwei Gegenbeispielen, und beide
  Gegenbeispiele sind für eine Einbettung unsichtbar.
- **Empfehlung: Option 1 heute, Option 2 als dokumentierter Ausbau.** Beides
  ist dasselbe Modell gegen denselben Maßstab; der Unterschied ist nur, ob ein
  Mensch den Knopf drückt. Die Gegenrede steht am Ende.

---

## 1. Wie groß die Aufgabe wirklich ist

Bevor irgendein Werkzeug gewählt wird, lohnt die Rechnung, denn sie fällt anders
aus als die Aufgabenstellung vermutet.

ADR 19 ordnet die beiden Regeln ausdrücklich: „The gate below therefore runs
*after* this rule, not before it: rating a book nobody will be shown is waste."
Der Code hält sich daran — `run._apply_gate` bekommt die bereits meldefähigen
`deltas` und reicht sie an `gate.apply` weiter. Bewertet wird also nicht jede
Entdeckung, sondern jede Entdeckung, die am Tag ihres Fundes unter der
Strong-Deal-Linie liegt. ADR 19 hält dazu fest, dass von 300 Entdeckungen eines
echten Laufs allein 65 bei 10,00 € oder mehr lagen und dass Lauf 3 **null** neue
Titel brachte.

Die 40 aus der Aufgabenstellung ist die Voreinstellung von `rating_budget` —
und ADR 19 sagt, wofür sie da ist: „Der erste Lauf mit einem Schlüssel trifft
den einmaligen Rückstand von 316 Entdeckungen." Sie ist eine Bremse gegen den
Rückstand, keine Prognose für den Alltag.

Zweitens ist die Genauigkeitsanforderung hier ausdrücklich niedriger als sonst.
`docs/leseprofil.md` sagt: „`vermutet` ist für den automatischen Vorfilter
zulässig — bei hundert Funden pro Lauf kann er nicht hundertmal recherchieren.
Für eine Bewertung von Hand ist es **ein Fehler**." Das Tor darf also raten. Das
ist der teuerste Posten jeder Bewertung — der Skill `buch-bewerten` verlangt in
Schritt 3 ausdrücklich, fehlendes Wissen nachzuschlagen — und für diesen Zweck
ist er erlassen.

Drittens fällt das Tor nie zu. Was nicht bewertet wird, wird angezeigt. Ein
ausgefallener Bewerter kostet Ruhe im Digest, nie einen Fund.

Diese drei Punkte zusammen entscheiden die Recherche mehr als alles, was unten
noch kommt: gesucht wird ein Verfahren für **wenige Bücher am Tag**, das
**ausdrücklich raten darf** und dessen **Ausfall billig** ist.

---

## 2. Claude Code im Gespräch — die Warteschlange

Der Lauf legt an, was noch kein Urteil hat; die Leserin arbeitet die Liste mit
`buch-bewerten` ab; die Ergebnisse gehen zurück in den Store.

**Das ist zur Hälfte schon gebaut.** `ratings.py` kennt drei Herkünfte —
`model`, `conversation`, `reader` — und `BY_CONVERSATION` ist genau diese: „im
Gespräch bewertet". `seed.py` importiert die dreizehn Urteile aus `owned.yaml`
bereits unter dieser Herkunft, und `gate._judgement` fragt vor jedem
Modellaufruf erst am Buch nach einem menschlichen oder Gesprächsurteil — „ein
menschliches Urteil erspart den Aufruf ganz" (ADR 19, Ticket 21). Der Skill
schreibt YAML in einem Format, das dem sehr nahe ist, was `seed.py` schon liest.
Was fehlt, ist ein Export der offenen Fälle und ein Rückimport; beides ist ein
Nachmittag, kein Vorhaben.

**Aufwand.** Für den Regelfall — sagen wir fünf bis zehn neue Schnäppchen am Tag
— ist das ein Vorgang von wenigen Minuten: Datei öffnen, Skill anwerfen,
Ergebnis prüfen. Für den einmaligen Rückstand von 316 ist es eine Sitzung von
mehreren Stunden, aufteilbar über Tage, weil ein gespeichertes Urteil nie
erneuert wird.

Die Zahlen dahinter sind hier nachgerechnet und deshalb als Schätzung markiert:
der Maßstab in `docs/leseprofil.md` sind rund 8 000 Zeichen, also grob 2 500
Token, und er wird einmal pro Sitzung gelesen, nicht pro Buch. Ein Buch bringt
Titel, Autor:in, Reihe, Preis, Regal und 219 Zeichen Anriss — unter 150 Token.
Eine Begründung nach den vier Regeln aus Abschnitt 4 des Maßstabs sind gut
hundert Wörter, also ~200 Token. Zehn Bücher in einem Rutsch kosten damit
ungefähr 5 000 Token, ein Bruchteil dessen, was eine normale Arbeitssitzung in
diesem Repository ohnehin verbraucht. Bei vierzig Titeln und der teuren Route
mit Recherche je Buch sieht es anders aus: dann sind es vierzig bis hundert
Websuchen und eine Sitzung, die ein Nutzungsfenster füllt.

**Was dagegen spricht.**

- *Der Skill verlangt heute mehr, als das Tor braucht.* `buch-bewerten`
  Schritt 6: „`vermutet` ist hier ein Fehler: in diesem Skill wird recherchiert,
  bis mindestens `teils` erreicht ist." Für dreizehn eigene Bücher ist das
  richtig, für die tägliche Vorsortierung ist es die teure Route. Der Skill
  braucht entweder einen zweiten Modus oder einen Schwesterskill mit
  ausdrücklich gesenktem Anspruch. Das ist keine Schwäche der Option, aber
  Arbeit, die dazugehört.
- *Ein Mensch in der Schleife ist das, was ADR 4 und ADR 12 vermeiden wollten.*
  Ein Lauf soll ohne Aufsicht durchgehen. Hier tut er das nicht mehr ganz.
- *Und die Gewohnheit hält nicht.* Nach zwei Wochen bleibt die Warteschlange
  liegen. Dann wirkt wieder nur die Preisregel, und weil das Tor offen
  scheitert, sieht das aus wie vorher und nicht wie ein Defekt. Das ist der
  ernsthafteste Einwand, und er ist gleichzeitig entschärft: verloren geht
  nichts, es wird nur wieder lauter.

---

## 3. `claude -p` aus einem Skript — die Rechtsfrage

Das ist die Frage, um die es geht, und sie zerfällt in zwei.

### Technisch

Belegt, aber trivial: `claude -p` (`--print`) ist der dokumentierte
nicht-interaktive Modus — Prompt hinein, Ergebnis auf stdout, Prozess endet
([Claude Code Docs, headless SDK](https://docs.anthropic.com/en/docs/claude-code/sdk/sdk-headless)).
Ein Cron-Job kann ihn aufrufen. Für unseren Zweck wäre der richtige Zuschnitt
**ein Aufruf pro Lauf mit allen offenen Titeln**, nicht einer pro Buch: der
Maßstab wird dann einmal gelesen statt vierzigmal, und der Kaltstart eines
`claude -p` in einem Repository-Wurzelverzeichnis lädt ohnehin alles, was eine
interaktive Sitzung auch lädt. Wie viel das genau ist, behaupten mehrere Blogs
mit sehr großen Zahlen; eine offizielle Angabe habe ich nicht gefunden —
**ungemessen**.

### Erlaubt

Hier ist die Quellenlage besser als erwartet, und sie zeigt in die andere
Richtung als das Gerücht.

**Die Consumer Terms enthalten das Verbot — und die Ausnahme im selben Satz.**
Die [Consumer Terms of Service](https://www.anthropic.com/legal/consumer-terms)
(Stand 8. Oktober 2025) untersagen, „Except when you are accessing our Services
via an Anthropic API Key **or where we otherwise explicitly permit it**, to
access the Services through automated or non-human means, whether through a bot,
script, or otherwise." Der Halbsatz nach dem *or* ist der ganze Punkt: die Frage
ist nicht, ob automatisierter Zugriff generell verboten ist, sondern ob
Anthropic diesen hier ausdrücklich erlaubt hat.

**Hat es.** Der Hilfeartikel
[Use the Claude Agent SDK with your Claude plan](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan)
(zuletzt geändert 16. Juni 2026) behandelt „Claude Agent SDK usage, the
`claude -p` command, and third-party apps built on the Agent SDK" als eine
Nutzungsform, die ein Abonnement trägt. Der Artikel beschreibt eine zum
15. Juni 2026 angekündigte Umstellung auf ein eigenes Monatsguthaben — und einen
Hinweis am Kopf, dass diese Umstellung **pausiert** wurde und sich vorerst
nichts ändert: `claude -p` zieht weiterhin vom Kontingent des Abonnements. Für
uns ist die Abrechnung nebensächlich; entscheidend ist, dass Anthropic
`claude -p` unter einem Abonnement überhaupt als reguläre Nutzungsform
beschreibt statt als Verstoß.

**Was tatsächlich verboten ist, steht auf der Rechtsseite von Claude Code** und
ist etwas anderes, als das Gerücht behauptet. Die Seite
[Legal and compliance](https://code.claude.com/docs/en/legal-and-compliance)
sagt unter *Authentication and credential use*:

> „**OAuth authentication** is intended exclusively for purchasers of Claude
> Free, Pro, Max, Team, and Enterprise subscription plans and is designed to
> support ordinary use of Claude Code and other native Anthropic applications."

und im nächsten Absatz:

> „Anthropic does not permit third-party developers to offer Claude.ai login
> into their own applications, or to route requests through Free, Pro, or Max
> plan credentials **on behalf of their users**. Moreover, developers may not
> collect, store, or intermediate Claude.ai credentials or session tokens."

Beide Verbote zielen auf dieselbe Figur: jemand, der die Abo-Anmeldung *anderer
Leute* durch sein Produkt schleust. Dieselbe Seite verbietet außerdem, das
Claude-Code-Binary zu verändern, und verlangt, dass jeder Endnutzer sich mit
seinen eigenen Zugangsdaten anmeldet. Ein Skript auf dem Rechner der Leserin,
das die unveränderte `claude`-CLI mit ihrer eigenen Anmeldung für ihre eigenen
Bücher aufruft, ist keine dieser Figuren: es gibt keinen Endnutzer außer ihr, es
sammelt keine Token, es vermittelt nichts.

Daraus folgt allerdings eine harte Grenze für die Umsetzung: erlaubt ist, **die
CLI aufzurufen**. Den OAuth-Ablauf in Python nachzubauen oder ein Token aus der
Konfiguration zu lesen und selbst an einen Endpunkt zu schicken, wäre genau das
„collect, store, or intermediate", das der Absatz verbietet. Der Aufruf muss
über `subprocess` gehen, oder gar nicht.

**Was offen bleibt, und es ist nicht nichts.** Dieselbe Seite sagt unter
*Acceptable use*: „Advertised usage limits for Pro and Max plans assume
**ordinary, individual** usage of Claude Code and the Agent SDK", und schließt
mit „Anthropic reserves the right to take measures to enforce these restrictions
and may do so without prior notice." Was „ordinary" bedeutet, definiert keine
Quelle, die ich gefunden habe. Ein täglicher Cron-Job, der ein
Buchempfehlungs-Werkzeug bedient, ist individuell und klein — aber er ist nicht
„Claude Code" im Sinne von Programmierarbeit, und er läuft ohne Menschen. Dass
die Dokumentation an dieser Stelle unklar ist, ist im Übrigen kein
Außenseiterbefund: es liegt ein
[Dokumentations-Ticket](https://github.com/anthropics/claude-code/issues/36324)
im Claude-Code-Repository, das genau beklagt, dass die Headless-Dokumentation
nicht sagt, ob sie mit einer Abo-Anmeldung benutzt werden darf. Das ist keine
offizielle Aussage — es ist der Beleg dafür, dass die offizielle Aussage fehlt.

**Fazit für Punkt 2.** Belegt: kein Verbot trifft diesen Fall, und `claude -p`
unter Abo wird von Anthropic selbst als gedeckte Nutzung beschrieben. Offen: die
Auslegung von „ordinary, individual". Die Konsequenz eines Irrtums wäre keine
Rechnung, sondern eine Sperre — und die träfe den Account als Ganzes, nicht nur
dieses Spielzeug. Das ist der Grund, diese Option nicht *zuerst* zu bauen,
sondern nachdem Option 1 gezeigt hat, wie klein die tägliche Last wirklich ist.

---

## 4. Ein lokales Sprachmodell

### Läuft es auf dem Pi?

Zeitlich ja, und das ist die einzige Zahl in diesem Abschnitt, die belegt ist.
Die [Stratosphere-Messung auf einem Raspberry Pi 5](https://www.stratosphereips.org/blog/2025/6/5/how-well-do-llms-perform-on-a-raspberry-pi-5)
gibt für Q4-Quantisierungen unter Ollama:

| Modell | RAM | Token/s |
|---|---|---|
| gemma3:1b | ~1,5 GB | 13–14 |
| llama3.2:1b | ~2 GB | 10–11 |
| qwen2.5:1.5b | ~2,5 GB | 10–12 |
| llama3.2:3b | ~3,5 GB | 5–6 |
| qwen2.5:3b | ~3,8 GB | 5–7 |

Eine Bewertung erzeugt nach der Rechnung aus Abschnitt 2 rund 200 Token
Begründung. Bei 6 Token/s sind das gut 30 Sekunden je Buch, für vierzig also
etwa zwanzig Minuten reine Erzeugung. Für einen nächtlichen Lauf ist das
belanglos. Die Zeit für die Prompt-Auswertung — der Maßstab sind rund 2 500
Token, und die müssen bei jedem Aufruf oder zumindest einmal je Sitzung durch —
steht in dieser Messung nicht: **ungemessen**. Ein 3-B-Modell in Q4 passt mit
~3,8 GB auf einen 8-GB-Pi neben allem, was dieses Werkzeug sonst braucht.

### Beurteilt es gut genug?

Hier finde ich keine belastbare Antwort, und ich behaupte auch keine. Was sich
sagen lässt:

- Auf der Zielhardware kommt nur die 1–3-B-Klasse in Frage. Empfehlungen für
  Gemma 3 4B oder Qwen 2.5 7B beziehen sich auf 8-GB-Knoten mit deutlich mehr
  Rechenleistung als ein Pi
  ([Turing Pi, RK3588](https://turingpi.com/run-llm-locally-arm-rk3588-ollama-llama-cpp/)).
- Für deutschsprachige Klappentexte gegen eine fünfachsige Rubrik habe ich für
  keine dieser Größen einen Benchmark gefunden. **Ungemessen.**
- Die Aufgabe ist unangenehm schwer für ein kleines Modell: sie verlangt nicht
  Klassifikation, sondern eine Begründung, die nach `docs/leseprofil.md`
  Abschnitt 4 vier Dinge leisten muss — benannte Achse, konkreter Beleg, Brücke
  zum Leser, und was den Stern kostet. Die dort verbotenen Untugenden („Trifft
  den Kern", „Cyberpunk-Dystopie", Tatsache statt Grund) sind exakt das, was ein
  3-B-Modell erzeugt, wenn es aus 219 Zeichen ein Urteil pressen soll. ADR 19
  hat eine Keyword-Regel mit genau dieser Begründung verworfen: „would produce
  confident nonsense".

Auf dem Windows-PC sähe das anders aus — ein 8- bis 14-B-Modell in Q4 wäre
plausibel besser, und der PC hat die Zeit. Aber ADR 12 verlangt, dass derselbe
Lauf auf dem Pi funktioniert. Ein Bewerter, der nur auf dem PC brauchbar ist,
ist ein Modul, das die Migration blockiert — genau die Sorte Abhängigkeit, die
ADR 12 verhindern soll.

**Wenn man es dennoch probiert**, dann als Messung, nicht als Umsetzung: die
dreizehn Urteile aus `owned.yaml` liegen mitsamt Begründung vor und sind ein
fertiger, wenn auch kleiner Prüfstand. Ein Nachmittag mit Ollama auf dem PC
gegen diese dreizehn beantwortet die Frage, die keine Websuche beantwortet.

---

## 5. Einbettungen statt Urteil

### Die technische Seite ist die einfachste

Ein mehrsprachiges Satzmodell — `paraphrase-multilingual-MiniLM-L12-v2` oder
`multilingual-e5-small` — braucht ein paar hundert MB und rechnet vierzig kurze
Texte auf einem Pi in Sekunden. Für Deutsch gibt es bessere:
[jina-embeddings-v3](https://jina.ai/models/jina-embeddings-v3/) (570 M
Parameter, 89 Sprachen, MTEB-Multilingual 64,4) und das ältere
`jina-embeddings-v2-base-de`, das
[Jina ausdrücklich als deutsch-englisch zweisprachig](https://jina.ai/news/ich-bin-ein-berliner-german-english-bilingual-embeddings-with-8k-token-length/)
gebaut hat. Das ist alles machbar. Es ist trotzdem nicht die Lösung.

### Drei Gründe, die unabhängig voneinander reichen

**Die Datenlage trägt es nicht, und zwar an der falschen Stelle.** Vorhanden
sind neun `liked_books`, zwei `disliked_books` und dreizehn bewertete Bücher in
`owned.yaml`. ADR 17 hat den Defekt selbst benannt: „all thirteen rated books
landed between three and five stars. A scale where nothing ever reaches the
bottom does not discriminate, it confirms." Ein Ähnlichkeitsmaß braucht eine
Gegenseite, und es gibt zwei Bücher auf ihr.

Schlimmer: die beiden Gegenbeispiele sind für eine Einbettung unsichtbar. *Der
Schwarm* steht auf der Liste wegen langsamen Erzähltempos — ein Buch, das nach
Klappentext genau wie die Positivliste aussieht (düster, Katastrophe,
isoliertes Setting) und trotzdem verloren hat. *Herr der Ringe* steht dort wegen
des mythischen Tons, während *Otherland* und *Yendi* als Fantasy auf der
Positivliste stehen. `docs/leseprofil.md` Abschnitt 5 hält beides fest. Eine
Kosinus-Ähnlichkeit würde *Der Schwarm* dicht an die Positivliste rücken. Das
ist kein Randfall, sondern nach ADR 17 „the most valuable entry" — der Fall, an
dem sich ein Maßstab von einem Genre-Filter unterscheidet.

**219 Zeichen sind Werbetext.** Das sind etwa 35 Wörter, geschrieben, um zu
verkaufen. Eine Einbettung davon misst Genre und Register — und ADR 19 hat
gerade gemessen, dass Genre-Regale untargeted sind. Die stärkste Achse A (eine
wiederkehrende **Figur**, nicht nur eine Reihe) steht laut `docs/leseprofil.md`
„in keinen Metadaten"; sie wird von einem Vektor über einen Anriss nicht
gerettet.

**Es kommt keine Begründung heraus.** ADR 19 verlangt seit Ticket 14/20, dass
Sterne, Konfidenz und Begründung im Digest unter dem Vorschlag stehen —
„gespeichert und nie gezeigt war die Begründung für niemanden nachprüfbar". Eine
Zahl zwischen 0 und 1 erfüllt keine der vier Anforderungen aus Abschnitt 4 des
Maßstabs. Man kann sie zu Sternen skalieren; man kann sie nicht begründen.

**Wofür es dennoch taugt.** Nicht als Urteil, sondern als Reihenfolge: wenn ein
Rückstand von 316 gegen ein Budget von 40 steht, ist die Frage „welche vierzig
zuerst" eine reine Sortierfrage, und dafür ist eine grobe Ähnlichkeit besser als
das Zufallsdatum eines Regals. Das ist ein kleiner, ehrlicher Nutzen und wäre
eine spätere Verfeinerung, kein Ersatz für das Tor.

---

## 6. Fremde Anbieter mit Freikontingent

Der Vollständigkeit halber, mit dem Hinweis, den die Frage verlangt: hier
verlässt der Geschmack der Leserin die Maschine an einen *weiteren* Dritten.
ADR 19 hält fest, dass diese Abwägung bei Anthropic bewusst getroffen wurde —
„The reader was told this before choosing and chose the model." Eine solche
Entscheidung überträgt sich nicht automatisch auf den nächsten Anbieter, und bei
mindestens einem ist der Handel deutlich schlechter.

**Google Gemini.** Der Freiplan ist großzügig genug für vierzig Aufrufe am Tag.
Der Preis steht in Googles eigenen
[Gemini-API-Bedingungen](https://ai.google.dev/gemini-api/terms): im unbezahlten
Tarif nutzt Google die eingereichten Inhalte, um „Google products and services"
zu verbessern und zu entwickeln, und „human reviewers may read, annotate, and
process your API input and output". Für den bezahlten Tarif gilt ausdrücklich
das Gegenteil. Der Prompt trägt nach ADR 19 den Maßstab, also das
aufgeschriebene Lesegeschmacksprofil. Ihn kostenlos in ein Trainingskorpus zu
geben, ist ein anderer Handel als der, dem die Leserin zugestimmt hat, und er
sollte ihr in diesen Worten vorgelegt werden, falls die Option je erwogen wird.

**Groq.** Freies Kontingent mit veröffentlichten Grenzen, für
`llama-3.3-70b-versatile` in der Größenordnung 30 Anfragen/Minute und 1 000/Tag
— mehr als genug. Groq ist ein Inferenz-Anbieter, das Modell ist Meta Llama. Zur
Qualität auf deutschen Klappentexten: **ungemessen**.

**Mistral.** Freier „Experiment"-Zugang ohne Kreditkarte, europäischer Anbieter
und mit ordentlichem Deutsch — die datenschutzrechtlich am wenigsten
unangenehme der drei. Auch hier: die genauen Bedingungen zur Datennutzung im
Freitarif habe ich **nicht geprüft**; wer diese Option ernsthaft erwägt, muss
das nachholen, bevor der Maßstab hinausgeht.

Die Vergleichszahlen zu Groq und Mistral stammen aus einer Sekundärquelle
([Übersicht Freitarife 2026](https://ianlpaterson.com/blog/free-llm-api-2026/)),
nicht von den Betreibern selbst; verlässlich zitierbar sind hier nur die
Google-Bedingungen. Bei allen dreien gilt außerdem der praktische Einwand: ein
Freitarif ist kein Versprechen, und ein Werkzeug, das jeden Tag laufen soll,
hängt dann an einer Zusage, die niemand gegeben hat.

---

## 7. Empfehlung

**Option 1 jetzt bauen, Option 2 als benannten Ausbau dokumentieren.**

Konkret:

1. Der Lauf schreibt die offenen Fälle als YAML in `data/` — dasselbe Format,
   das `buch-bewerten` erzeugt. Ein Rückimport legt die Urteile unter der
   Herkunft `conversation` ab, die `ratings.py` schon kennt und die `seed.py`
   bereits benutzt. Der Digest nennt, wie viele Fälle offen sind, in derselben
   Zeile, in der er heute die zurückgehaltenen und die über das Budget
   durchgelassenen nennt.
2. Der Skill bekommt einen Vorfilter-Modus, in dem `vermutet` zulässig ist —
   nicht als Aufweichung, sondern weil `docs/leseprofil.md` das für den
   automatischen Vorfilter ausdrücklich so vorsieht. Der bestehende, strenge
   Modus bleibt der für die eigenen Bücher.
3. Erst danach, und nur wenn die tägliche Warteschlange sich als lästig
   erweist, derselbe Ablauf ohne Menschen: ein `subprocess`-Aufruf der
   unveränderten `claude`-CLI mit `-p`, **ein** Aufruf je Lauf für alle offenen
   Titel, Anmeldung ausschließlich über den regulären Login der CLI, niemals
   über ein selbst gelesenes Token.

Warum diese und nicht die anderen: es ist dasselbe Modell und derselbe Maßstab,
gegen den die dreizehn vorhandenen Urteile entstanden sind — die Qualität ist
also die einzige in diesem Projekt bereits belegte. Es kostet keine neue
Abhängigkeit, kein Modell im Speicher, keinen Schlüssel, keinen weiteren
Dritten. Es funktioniert auf dem Pi genauso wie auf dem PC, weil dort gar nichts
läuft außer einer YAML-Datei. Und es passt zu dem Umfang, den Abschnitt 1
ausgerechnet hat: für eine Handvoll Bücher am Tag eine Maschinerie zu bauen,
wäre die teurere Sorte Fehler.

## 8. Was dagegen spricht

Ehrlich, und in der Reihenfolge, in der es weh tut.

**Der Mensch fällt aus, und niemand merkt es.** Das Tor scheitert offen; eine
liegengebliebene Warteschlange sieht aus wie ein ruhiger Tag mit vielen
Vorschlägen. Der Digest muss die Zahl der offenen Fälle deshalb genauso
mitführen wie die zurückgehaltenen — Ticket 20 hat dieselbe Lehre schon einmal
gezogen, als das Zurückhalten auf stderr stand, wo ein Cron-Job es wegwirft.

**Es ist ein Rückschritt gegenüber ADR 4 und ADR 12.** Ein Lauf sollte ohne
Aufsicht durchgehen. Diese Empfehlung baut eine Handbremse ein und nennt die
Automatisierung „später". Wer die Automatisierung ohnehin will, baut hier zwei
Mal.

**Die Rechtsfrage bleibt trotzdem stehen.** Sie wird verschoben, nicht
beantwortet. Und die Antwort, die diese Recherche findet, ist nicht „verboten",
sondern „nicht verboten, mit einer undefinierten Randbedingung" — wer daraus
Sicherheit macht, überinterpretiert. Sollte Anthropic „ordinary, individual
usage" je enger fassen, trifft eine Durchsetzung nach eigener Ankündigung „ohne
Vorankündigung" den ganzen Account, nicht nur dieses Werkzeug.

**Und die interessanteste Möglichkeit bleibt ungemessen.** Ob ein 3-B-Modell auf
dem Pi diese Aufgabe kann, weiß nach dieser Recherche niemand. Der Prüfstand
dafür — dreizehn Bücher mit Sternen und Begründung — liegt fertig in
`data/owned.yaml`. Diese Empfehlung schiebt die Messung auf; das ist eine
Entscheidung gegen Wissen, und sie sollte irgendwann zurückgenommen werden.
