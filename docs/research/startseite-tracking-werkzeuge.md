# Was gehört auf die Startseite eines Werkzeugs, das man jeden Tag wieder öffnet?

Recherche zu Issue #5, September 2026. Anlass: `/` wird Startseite, die
Übersicht zieht nach `/uebersicht`. Der Prototyp stellt oben drei
Verkaufsargumente mit Bildern, darunter eine Zahlenleiste und zwei Spalten
(„Jetzt zu haben", „Zu entscheiden") mit Icon-only-Knöpfen. Die Frage ist, was
davon einem Nutzer hilft, der die Seite **täglich wieder** aufruft, und was nur
dem Erstbesucher.

Quellenlage vorweg: NN/g, Baymard, die Design-Systeme und die Blogs der
Produkte selbst waren erreichbar. `camelcamelcamel.com`, die Keepa-Deals-Seite
und `literal.club` haben den Abruf verweigert; dort stütze ich mich auf
Herstellertexte in Add-on-Verzeichnissen oder markiere Sekundärquellen. Zu
Zahlenleisten und zu Buchcovern in Listen gibt es **keine** peer-reviewte
Studie, die ich belastbar nennen könnte; ich sage jeweils, worauf die Aussage
stattdessen ruht.

## Was heute geplant ist

| Element | Für wen | Was die Quellen sagen |
|---|---|---|
| Drei Verkaufsargumente mit runden Bildern, oben | Erstbesucher | Rückkehrer blenden Werbeartiges aus; oberste Bildschirmhälfte ist der teuerste Platz (NN/g 2018a, 2018b) |
| Überschrift „Weniger Suchen. Mehr Lesen." | Erstbesucher | `tagline` ja, aber klein und nicht als Hauptüberschrift (Nielsen 2001, Nr. 2 und 19) |
| Zahlenleiste: Schnäppchen · ausleihbar · neue Funde · zuletzt geprüft | beide | Zahl ohne Vergleich trägt wenig; Zählungen der Listen darunter sind redundant (Few 2004, 2007; Nielsen 2001, Nr. 18) |
| „Jetzt zu haben", max. 5, mit Cover und Preis | Rückkehrer | entspricht dem, was Goodreads, StoryGraph, BookWyrm oben zeigen; 5 ist auch deren Grenze |
| „Zu entscheiden", max. 2, KI-Pitch, Sterne, drei Icon-only-Knöpfe | Rückkehrer | Ein-Klick ja, aber mit sichtbarer Beschriftung und `undo` (NN/g 2014, 2018c, 2019) |
| Zwei Spalten gleicher Höhe | beide | auf Mobilgeräten wird daraus eine Reihenfolge; die will entschieden sein (NN/g 2014b) |
| Leerzustand „Noch kein Lauf" mit zwei Knöpfen | Erstbesucher | richtig platziert; eine Haupt-, eine Nebenhandlung (Polaris, Carbon, NN/g 2021) |

## Was die Praxis sagt

### 1. Vorstellung oder persönliche Daten?

**Rückkehrer sehen Werbeartiges nicht mehr.** Pernice (NN/g 2018a) hat mit
Blickaufzeichnung bestätigt, was seit 1997 gilt: Nutzer ignorieren, was
„resembles ads, is close to ads, or appears in locations traditionally
dedicated to ads" — kennzeichnend sind kleine Rechtecke, farbige Flächen auf
weißem Grund, „fancy formatting". Einmal als Reklame eingestuft, wird die Zone
danach gemieden („hot potato"). Drei gleichförmige Kacheln mit runden Bildern
und Slogan über dem eigentlichen Inhalt haben genau diese Anmutung.

**Dekorative Bilder werden übersprungen, Produktbilder gelesen.** Nielsen
(NN/g 2010) unterscheidet in Blickdaten scharf: „big feel-good images that are
purely decorative" werden komplett ignoriert, Fotos von Produkten und echten
Menschen dagegen als Inhalt behandelt. Whitenton (NN/g 2014a) zeigt an
Southwest, wie ein großes Stimmungsbild die eigentliche Funktion unter die
Falz drückt. Flaherty u. a. (NN/g 2023) nennen die Kombination aus
`mobile-first`, Minimalismus und großen Bildern `content dispersion` und
messen auf dem Desktop längere Wege und schlechtere Vergleichbarkeit.

**Die oberste Bildschirmhälfte ist der teuerste Platz.** Fessenden (NN/g
2018b): 57 % der Betrachtungszeit liegen über der Falz, 74 % in den ersten
zwei Bildschirmhöhen. Empfehlung wörtlich: „reserve the top of the page for
high-priority content: key business and user goals." Das Nutzerziel eines
täglichen Besuchers ist nicht, Buchfink kennenzulernen.

**Werbung mit Zurückhaltung.** Fogg (Stanford 2002), Richtlinie 9: „Use
restraint with any promotional content." Nielsen (2001) in den 113
Startseiten-Richtlinien: Nr. 2 verlangt eine `tagline`, die sagt, was die
Seite tut; Nr. 19 warnt vor „clever phrases and marketing lingo"; Nr. 56: „Use
graphics to show real content, not just to decorate your homepage"; Nr. 18:
Wiederholung identischer Inhalte „reduces their impact".

**Was bringt Nutzer zurück?** Nielsen (NN/g 1997): „the classic way to
increase loyalty on the Web is to have fresh content that changes on a
predictable basis" — plus Personalisierung. Schade (NN/g 2016): Personalisierung
kostet den Nutzer nichts, weil das System entscheidet, was gezeigt wird.

**Was die Produkte tun.** Goodreads (Blog 2016a) hat die Startseite in drei
Spalten gebaut: links das Persönliche („Currently Reading" als „beautiful
visual reminder"), Mitte die Freundes-Updates, rechts Empfehlungen; erklärtes
Ziel ist das Gefühl „serendipitous discovery". Kein Marketing für
Eingeloggte. StoryGraph zeigt eingeloggt „Currently Reading", darunter den
Stapel, darunter Empfehlungen — und hat 2022 den Stapel über die Empfehlungen
gezogen, weil Nutzer schneller an ihre eigenen Daten wollten (StoryGraph
Roadmap 2021–2026). BookWyrm (Docs) stellt „Your Books" mit bis zu fünf
Büchern an den Kopf, die Zeitleiste nimmt zwei Drittel der Breite. mydealz
(FAQ) öffnet eingeloggt direkt auf „Highlights", dessen Reihenfolge sich nach
dem Verhalten richtet; der Slogan ist eine Zeile im Kopf. Keepa und
camelcamelcamel führen Eingeloggte auf Beobachtungsliste bzw. Preisfälle;
Selbstbeschreibung gibt es nur für Ausgeloggte.

Gegenposition: keine gefunden. Kein Primärtext empfiehlt Verkaufsargumente
oberhalb persönlicher Daten für eingerichtete Nutzer.

### 2. Zahlenleisten

**Eine Zahl ohne Vergleich sagt wenig.** Few (2007): Anzeigemittel auf einem
Dashboard müssen Maße „usually in the context of some comparison, such as a
target" zeigen, und zwar so, dass sie „at a glance" verstanden werden. Seine
Definition (Few 2004): die wichtigsten Informationen „consolidated and
arranged on a single screen so the information can be monitored at a glance".
Das ist ein Praktikerurteil, keine kontrollierte Studie — eine
peer-reviewte Quelle für „Zahl ohne Vergleich ist wertlos" habe ich nicht
gefunden, und NN/g (Laubheimer 2017) schweigt zur Anzahl von Kacheln.

**Weniger Ansichten, wichtigste oben links.** Tableau (Hilfe) rät, „the
number of views you include in your dashboard to two or three" zu begrenzen,
und die wichtigste Ansicht oben links zu setzen, weil dort das Scannen
beginnt. Miller's Law ist dafür kein Argument: Laws of UX warnt ausdrücklich,
die „magical number seven" nicht für Designgrenzen zu missbrauchen.

**Betonung nur an einer Stelle.** Von-Restorff-Effekt (Laws of UX): das
Abweichende bleibt hängen, aber „exercise restraint with emphasis", sonst
konkurrieren die Hervorhebungen — und werden für Werbung gehalten.

**Was die Zahl verschweigt.** Growth.Design (2020) am Corona-Dashboard: die
Leitfrage ist „What is this not saying?"; kumulierte Zahlen verzerren die
Wahrnehmung, tägliche Deltas nicht.

Für unsere Leiste: „Schnäppchen: 3" und „ausleihbar: 2" zählen die Liste,
die direkt darunter steht — Nielsens Redundanzregel. Der einzige Wert mit
Vergleichscharakter ist „neue Funde" (neu gegenüber dem letzten Lauf); der
einzige Statuswert ist „zuletzt geprüft", und der gehört nicht in eine
KPI-Kachel, sondern in eine Statuszeile (Abschnitt 4).

### 3. Ein-Klick-Triage und Icon-only-Knöpfe

**Icons brauchen sichtbare Beschriftung.** Harley (NN/g 2014): nur Home,
Drucken und Lupe gelten als verstanden; „Icon labels should be visible at all
times, without any interaction from the user", und: „Don't rely on hover to
reveal text labels: not only does it increase the interaction cost, but it
also fails to translate well on touch devices." Kendrick (NN/g 2019) zu
Tooltips: „Users shouldn't need to find a tooltip in order to complete their
task"; auf Touch-Geräten gibt es sie normalerweise gar nicht. Budiu (NN/g
2014c/2024): Icons ohne Label fördern kein Wiedererkennen; ein Label „would
help at least the first few times".

**Empirie dazu.** Wiedenbeck (1999, *Behaviour & Information Technology*
18(2)): Icon-only war in der ersten Sitzung deutlich langsamer und brauchte
mehr Hilfe; der Rückstand schmolz in Sitzung zwei, aber die wahrgenommene
Bedienbarkeit war für Icon + Label durchgehend am besten. Baymard (2012)
zählt Icon-Leisten, deren Bedeutung man per `hover` erraten muss, zur
„false simplicity" — teuer gerade bei selten genutzten Oberflächen, weil man
die Bedeutung zwischen zwei Besuchen vergisst. Baymard (2022) beobachtete im
Kontodashboard, dass Nutzer erst das Icon suchen und dann den Text lesen, „to
confirm it's the one they want".

**Design-Systeme sind sich einig.** Carbon: Icon-only nur, wenn „the icon
must be standardized and recognizable without label", ein Tooltip ist
„always required", und Gefahr-Knöpfe dürfen nie Icon-only sein. Primer: nur,
wenn der Zweck „may be easily understood using an icon", plus Tooltip. Apple
HIG (Toolbars): „Prefer simple, recognizable symbols … except for actions
like *edit* that aren't well-represented by symbols." Pernice (NN/g 2017b):
ein Stern steht für Bewertung und Merken — auf einer Karte, die schon
Bewertungssterne trägt, ist ein Stern für etwas anderes ein direkter Konflikt.
Im Prototyp trifft das die Überschrift „Zu entscheiden" (`ic-star` neben den
Sternen der Urteile); die Knöpfe selbst tragen `ic-x`, `ic-user` und `ic-play`
— und `ic-play` heißt in der Watchlist-Zeile „aktivieren", `ic-user` kommt
sonst nirgends vor.

**Ein Klick ist gut, wenn er zurückgenommen werden kann.** Nielsen (NN/g
2018c): Bestätigungsdialoge nutzen sich ab („if you cry wolf too many times,
people will stop paying attention"); für häufige, umkehrbare Handlungen gilt
„do go to great lengths to provide undo". Li (NN/g 2017a) zu
Listenaktionen: leicht auslösbare Handlungen brauchen „a highly salient" `undo`
auf dem Bildschirm. Laubheimer (NN/g 2015a): Fehlgriffe („slips") treffen
gerade geübte Nutzer im Autopilot; Abhilfe sind Abstand, gute Voreinstellung
und Umkehrbarkeit — nicht Nachfragen. Gmail (Hilfe) macht es vor: Archiv,
Löschen, Erinnern, Gelesen als `hover`-Aktionen in der Zeile, jede mit
„Rückgängig"-Hinweis.

**Wischen ist schlechter als Tippen.** Yamanaka, Usuba, Sato (CHI 2024):
„longer operation times, higher error rates, and significantly shifted touch
points for swipe compared to tap." Ma & Gajos (CHI 2022): die Tinder-Geste
„encourages quick decision making based on superficial attributes"; erst
wenn substanzielle Information vor dem Bild kam, sank die Verzerrung. Für uns
heißt das: Knöpfe statt Wischen, und Thema, Pitch und Preis **vor** dem
Cover lesbar — was der Entwurf schon tut.

**Drei Optionen sind wenig genug.** Hick's Law (Laws of UX): Entscheidungszeit
wächst mit Zahl und Komplexität der Wahl; drei klar getrennte Handlungen
liegen weit unter der Schwelle. Harley (NN/g 2018d) dämpft die Erwartung an
„Verwerfen": Nutzer ignorieren schlechte Empfehlungen eher, als dass sie
Rückmeldung geben. Der Knopf muss also billig sein — und sichtbar, sonst
wird er gar nicht gefunden.

### 4. „Zuletzt geprüft" und Vertrauen

**Sichtbare Aktualität schafft Glaubwürdigkeit.** Fogg (Stanford 2002),
Richtlinie 8: „Update your site's content often (at least show it's been
reviewed recently)" — „People assign more credibility to sites that show they
have been recently updated or reviewed." Harley (NN/g 2018e): Sichtbarkeit des
Systemzustands ist Heuristik Nr. 1; „the predictability of the interaction
creates trust". Kaplan (NN/g 2021) warnt vor Statusmeldungen, die „no items"
behaupten, obwohl der Lauf noch nicht oder fehlerhaft lief.

**Relativ zeigen, absolut hinterlegen.** Atlassian (Date and time): „ago"
für Kürzliches, „you should always provide a way for people to see the actual
timestamp, usually via a tooltip"; ab sieben Tagen absolutes Datum.
Cloudscape (AWS): „relative timestamps are easier for users to read, so we
recommend them for most use cases", mit `<time datetime title>` für den
absoluten Wert. Gegenstimme: Nielsen (2001), Nr. 84 — Datumsangaben nur, wenn
sie frisch sind, sonst wirkt die Seite alt. Für einen Tageslauf heißt das:
„heute 06:12" trägt beides, relativ und absolut; „vor 3 Tagen" wäre schon
ein Warnsignal und sollte auch so aussehen.

**„Neu seit dem letzten Besuch" ist ein Indikator, kein KPI.** Flaherty (NN/g
2024): Indikatoren sind passive, bedingte Hinweise; sie „can introduce noise
and clutter" und sind nur dort gerechtfertigt, wo Nutzer die Information
erwarten und vermissen würden. Whitenton (NN/g 2015b): Änderungen nach einem
Seitenaufbau werden übersehen; neue Elemente brauchen Kontrast, Nähe zum Fokus
oder Bewegung.

### 5. Leerzustände

**Drei Aufgaben.** Kaplan (NN/g 2021): Systemstatus mitteilen, Lernhinweis
geben („Star your favorites to list them here"), direkten Weg zur Kernaufgabe
anbieten. Carbon unterscheidet „No data" (Erstnutzung), „User action" und
„Error"; Anatomie: Bild optional, kurzer Titel, Text mit nächstem Schritt,
Primärhandlung, optional Sekundärlink; positiv formulieren („Start by adding
data assets" statt „You don't have any"). Polaris: „a clear explanation of
what will appear here and a prominent call-to-action"; eine Primär-, optional
eine Sekundärhandlung. Atlassian: Grund und nächster Schritt, ein bis zwei
Sätze (Schreibrichtlinie nur als Suchauszug gesehen, die Seite selbst lud
leer).

**Hier gehört die Erklärung hin.** Material (Empty states): Bild „subtle and
neutral", Zeile „without appearing to be actionable"; wenn der Zweck nicht
offensichtlich ist, „educational content" einblenden, das sich wegklicken
lässt; alternativ „starter content" mit Löschmöglichkeit. Das ist der Ort für
die drei Argumente und die drei Bilder aus #3 — beim ersten Besuch, nicht bei
jedem.

### 6. Cover in Listen

**Bilder werden erkannt, bevor Text gelesen ist.** Standing (1973, *QJEP*
25): nach einmaliger Darbietung von bis zu 10 000 Bildern blieb das
Wiedererkennen hoch; Bildmaterial schlägt Wortmaterial durchgängig. Nielsen
(NN/g 2010): Produktfotos werden geprüft, weil sie unterscheiden helfen.
Baymard (2024): Nutzer entscheiden anhand der Vorschaubilder, „which items
warrant further investigation"; ohne genug Bild verlassen sie die Liste — das
ist E-Commerce mit mehreren Bildern pro Artikel, nicht direkt Buchlisten, aber
der Mechanismus (Bild als Filter vor dem Lesen) ist derselbe. Eine Studie zu
Covern in Katalogen oder Lese-Apps habe ich nicht gefunden; ein
Cover-Experiment zu italienischen Romanen (MDPI, Titel „Judging Books by Their
Covers") berichtet, dass Bildmerkmale die Erinnerbarkeit stärker stützen als
Textmerkmale — ich habe nur den Abstract-Auszug gesehen.

**Größe ist der Streitpunkt.** Goodreads (Blog 2016a) machte „books the star
of the page" mit größeren Covern; in der Community-Diskussion (Goodreads
Forum 2016) lautete die häufigste Klage „Images are too big and there's too
much scrolling". Das deckt sich mit NN/g (2014a, 2023): große Bilder
verdrängen Funktion. Kleine Cover in Zeilen — nicht Karten — halten fünf
Einträge auf einer Bildschirmhöhe.

### 7. Zwei Spalten auf dem Telefon

**Das F-Muster ist der Notfall, nicht das Ziel.** Pernice (NN/g 2017c): F
entsteht bei unformatiertem Text ohne Anker — „the default pattern when there
are no strong cues"; erste Zeilen und der linke Rand bekommen die Blicke.
Gegenmittel: Überschriften mit Schlüsselwort vorn, Fettung, Gruppierung,
Überflüssiges streichen. Auf Mobilgeräten bleibt das Muster bestehen.

**Linearisierung hat einen Preis.** Budiu (NN/g 2014b): aus 2 × 3 wird 1 × 6;
wer Block 4 will, „will need to sequentially scroll down through chunks 1–3".
Schade (NN/g 2014d): „Content prioritization is one key aspect to doing
responsive design well." Welche Spalte oben gewinnt, sagt keine Quelle — die
Antwort folgt aus Nr. 2: die Spalte, deren Inhalt verfällt. Schnäppchen und
Ausleihbarkeit haben ein Ablaufdatum, eine Entscheidung wartet. Also „Jetzt zu
haben" zuerst, „Zu entscheiden" darunter, beide mit Überschrift als Anker.
Gleiche Spaltenhöhe belegt keine Quelle; bei fünf gegen zwei Einträgen erzeugt
sie Leerraum — genau die `content dispersion` aus Nr. 1.

### 8. Was die Produkte konkret tun

**Goodreads.** Blog 2016a/b (Pinchuk, Chandler): schneller (React),
persönliche Lesedaten links, Feed mit Endlos-Scroll, Cover größer, hunderte
Mitglieder im Test. Forum 2016 (Sekundär, Nutzerstimmen): zu große Bilder, zu
viel Scrollen, „Currently Reading" verbrauche Platz für Leute, die ihre Regale
ohnehin direkt öffnen, Diskussionen aus der Startseite verschwunden.

**StoryGraph.** Changelog 2021: „Up Next" ist auf **fünf** Bücher begrenzt,
sitzt „at the top of your To-Read page" und erscheint auf der Startseite.
Roadmap: 2022 wandert der Stapel über die Empfehlungen; 2024 Nutzerwünsche,
„Currently Reading" und „Up Next" direkt untereinander zu zeigen und Up Next
mit einem Klick statt drei zu erreichen; ein Nutzer 2026: die Startseite sei
„empty and confusing", gewünscht sei ein „dashboard … in one place".

**BookWyrm.** Docs: „Your Books" oben mit bis zu fünf Büchern aus den Regalen,
dann Ziel und Interaktion, Zeitleiste auf zwei Dritteln der Breite.

**mydealz.** FAQ: Tabs „Heiß" (ab 100 Grad, sortiert nach Erreichen der
Schwelle), „Aktuell" (Eingangsreihenfolge), „Diskutiert"; die
Highlights-Reihenfolge wird „basierend auf Deinem Verhalten" angepasst; neue
Deals zeigen zehn Minuten lang keine Temperatur, damit die erste Bewertung
fair bleibt. Hervorhebung ist also ein Vergleichswert (Grad), nicht ein
absoluter.

**Keepa.** Herstellertext (Add-on-Verzeichnis): Preisbeobachtung meldet, wenn
ein Produkt „drops below your target price or returns to stock". Die
Deals-Seite selbst war nicht abrufbar; nach Sekundärquellen (Reseller-Blogs)
stellt sie aktuellen Preis gegen 30-Tage-Durchschnitt mit Prozentfall und
filtert das Fallintervall („last 24 hours"). Kernidee jedenfalls: Fall
relativ zum Durchschnitt, nicht zum Vortag.

**camelcamelcamel.** Site verweigert den Abruf. Herstellertext („The
Camelizer"): „tell us how much you would like to pay for a product, and we
will email you when the price drops". Die Startseite verweist auf „Top Price
Drops" und „Popular Products" — Listen mit Prozentfall, soweit aus den URLs
ersichtlich; Details nicht prüfbar.

**Literal.** Nicht prüfbar; ein Suchtreffer behauptet eine kompakte
„Currently reading"-Zeile oben mit Empfehlungen in der Seitenleiste.

## Für uns heißt das

1. **Die Verkaufsargumente wandern in den Leerzustand.** „Noch kein Lauf" wird
   der Ort für die drei Bilder aus #3 und je einen Satz; dazu **eine**
   Primärhandlung („Watchlist füllen") und ein Sekundärlink zur Übersicht.
   Nach dem ersten erfolgreichen Lauf verschwinden sie von `/`. Wer sie
   danach lesen will, findet sie im README (#6) und über einen Fußzeilenlink.

2. **Oben steht der Tag, nicht der Slogan.** Erste Zeile ist eine Statuszeile,
   kein Kachelband: „Heute 06:12 geprüft · 2 neue Funde · 1 Preisfall". Sie
   trägt das Delta seit dem letzten Lauf (das ist der Vergleich, den Few
   verlangt) und die Frische (Fogg 8). Absolute Zeit im `title`, relative
   Fassung erst ab „gestern"; ab dem dritten Tag ohne Lauf wird die Zeile
   zur Warnung. Ist der letzte Lauf fehlgeschlagen, sagt sie das — nicht
   „0 Schnäppchen".

3. **Die Zahlenleiste entfällt.** „Schnäppchen: 3" und „ausleihbar: 2" zählen
   nur die Liste darunter. Zwei Zahlen mit Vergleichscharakter (neu, Preisfall)
   sind in der Statuszeile besser aufgehoben als in vier Kacheln.

4. **„Weniger Suchen. Mehr Lesen." bleibt als `tagline`**, klein neben dem
   Namen in der Kopfzeile und im Leerzustand als Überschrift — nicht als
   `h1` der Startseite für Rückkehrer.

5. **Icon plus Wort auf den drei Knöpfen.** „Verwerfen", „Hab ich",
   „Beobachten" sind nicht universell: `ic-play` bedeutet in der Watchlist
   „aktivieren", `ic-user` hat sonst keine Bedeutung, und der Stern der
   Überschrift „Zu entscheiden" kollidiert mit den Bewertungssternen
   derselben Karte. Icon links, kurzes Wort rechts,
   `title` zusätzlich; 44 px Mindesthöhe wie `.tun`. Wer Platz sparen will,
   kürzt das Wort, nicht das Label.

6. **Ein Klick, keine Nachfrage, aber `undo`.** ADR 18 löscht nichts, also ist
   jede der drei Handlungen umkehrbar; deshalb kein Bestätigungsdialog,
   sondern eine Zeile „Verworfen — rückgängig" an der Stelle der Karte, die
   einige Sekunden steht. Kein Wischen.

7. **„Jetzt zu haben" vor „Zu entscheiden"** — auf dem Telefon als Reihenfolge,
   auf dem Desktop links. Begründung ist das Ablaufdatum, nicht das F-Muster.
   Beide Blöcke bekommen eine Überschrift mit dem Zählwort vorn („3 jetzt zu
   haben") als Scan-Anker; keine erzwungene gleiche Höhe.

8. **Cover klein, in Zeilen.** Ein Cover in Zeilenhöhe (etwa 48–64 px) reicht
   zum Wiedererkennen und hält fünf Einträge in einer Bildschirmhöhe. Große
   Cover-Karten sind der Goodreads-Fehler von 2016.

9. **Hervorhebung nur an einer Stelle pro Zeile:** der Preis (Schnäppchen)
   bzw. „ausleihbar" (Bibliothek) — nicht zusätzlich Titel, Sterne und
   Quelle. Was alles betont ist, sieht aus wie Reklame.

10. **„Neu" meint „seit deinem letzten Besuch", nicht „seit dem letzten Lauf".**
    Für den Tagesbesucher fällt das zusammen; wer drei Tage aussetzt, will
    danach alles Neue sehen. Ein gespeicherter Zeitstempel „zuletzt gesehen"
    reicht; die Markierung ist ein passiver Indikator (ein Punkt, ein Wort),
    kein Banner. Das ist eine Erweiterung, kein Blocker für #5.

11. **Fünf und zwei sind gute Grenzen.** StoryGraph und BookWyrm ziehen bei
    fünf dieselbe Linie; zwei Entscheidungen pro Tag halten den Knopfblock
    lesbar. Was darüber liegt, bekommt einen Link „alle 7 ansehen" in die
    Übersicht statt einer längeren Liste.

## Offen

Ob die Statuszeile auch Fehlschläge einzelner Quellen (nur Shop, nur
Bibliothek) benennt oder nur den Gesamtlauf, ist eine Frage an die Übersicht,
nicht an die Startseite. Und ob „Hab ich" gegenüber „Beobachten" die häufigere
Handlung ist, wissen wir erst nach einigen Wochen Nutzung — die Reihenfolge der
drei Knöpfe sollte deshalb noch nicht zementiert werden.

## Quellen

NN/g (Nielsen Norman Group)

- 1997 — Jakob Nielsen, [Loyalty on the Web](https://www.nngroup.com/articles/loyalty-on-the-web/)
- 2001 — Jakob Nielsen, [113 Design Guidelines for Homepage Usability](https://www.nngroup.com/articles/113-design-guidelines-homepage-usability/)
- 2010 — Jakob Nielsen, [Photos as Web Content](https://www.nngroup.com/articles/photos-as-web-content/)
- 2014 — Aurora Harley, [Icon Usability](https://www.nngroup.com/articles/icon-usability/)
- 2014a — Kathryn Whitenton, [Image-Focused Design: Is Bigger Better?](https://www.nngroup.com/articles/image-focused-design/)
- 2014b — Raluca Budiu, [Scaling User Interfaces](https://www.nngroup.com/articles/scaling-user-interfaces/)
- 2014c/2024 — Raluca Budiu, [Memory Recognition and Recall in User Interfaces](https://www.nngroup.com/articles/recognition-and-recall/)
- 2014d — Amy Schade, [Responsive Web Design (RWD) and User Experience](https://www.nngroup.com/articles/responsive-web-design-definition/)
- 2015a — Page Laubheimer, [Preventing User Errors: Avoiding Unconscious Slips](https://www.nngroup.com/articles/slips/)
- 2015b — Kathryn Whitenton, [Change Blindness in UX](https://www.nngroup.com/articles/change-blindness/)
- 2016 — Amy Schade, [Customization vs. Personalization](https://www.nngroup.com/articles/customization-personalization/)
- 2017 — Page Laubheimer, [Dashboards: Making Charts and Graphs Easier to Understand](https://www.nngroup.com/articles/dashboards-preattentive/)
- 2017a — Angie Li, [Using Swipe to Trigger Contextual Actions](https://www.nngroup.com/articles/contextual-swipe/)
- 2017b — Kara Pernice, [Bad Icons: How to Identify and Improve Them](https://www.nngroup.com/articles/bad-icons/)
- 2017c — Kara Pernice, [F-Shaped Pattern of Reading on the Web: Misunderstood, But Still Relevant](https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content/)
- 2018a — Kara Pernice, [Banner Blindness Revisited](https://www.nngroup.com/articles/banner-blindness-old-and-new-findings/)
- 2018b — Therese Fessenden, [Scrolling and Attention](https://www.nngroup.com/articles/scrolling-and-attention/)
- 2018c — Jakob Nielsen, [Confirmation Dialogs Can Prevent User Errors — If Not Overused](https://www.nngroup.com/articles/confirmation-dialog/)
- 2018d — Aurora Harley, [Individualized Recommendations: Users' Expectations & Assumptions](https://www.nngroup.com/articles/recommendation-expectations/)
- 2018e — Aurora Harley, [Visibility of System Status (Usability Heuristic #1)](https://www.nngroup.com/articles/visibility-system-status/)
- 2019 — Alita Kendrick, [Tooltip Guidelines](https://www.nngroup.com/articles/tooltip-guidelines/)
- 2021 — Kate Kaplan, [Designing Empty States in Complex Applications: 3 Guidelines](https://www.nngroup.com/articles/empty-state-interface-design/)
- 2023 — Kim Flaherty, Tim Neusesser, Nishi Chitale, [The Negative Impact of Mobile-First Web Design on Desktop](https://www.nngroup.com/articles/content-dispersion/)
- 2024 — Kim Flaherty, [Indicators, Validations, and Notifications](https://www.nngroup.com/articles/indicators-validations-notifications/)

Baymard Institute

- 2012 — [3 Types of False Simplicity](https://baymard.com/blog/false-simplicity)
- 2022 — [Consider Having an "Icon-Based" Account Dashboard](https://baymard.com/blog/use-icons-in-the-account-dashboard)
- 2024 — [Always Provide 3 or More Product Thumbnails in Product Lists](https://baymard.com/blog/secondary-hover-information)

Peer-reviewed und Forschung

- Susan Wiedenbeck (1999), The use of icons and labels in an end user application program, *Behaviour & Information Technology* 18(2), 68–82 — [DOI](https://www.tandfonline.com/doi/abs/10.1080/014492999119129)
- Lionel Standing (1973), Learning 10,000 pictures, *Quarterly Journal of Experimental Psychology* 25(2), 207–222 — [DOI](https://doi.org/10.1080/14640747308400340)
- Shota Yamanaka, Hiroki Usuba, Junichi Sato (2024), Behavioral Differences between Tap and Swipe, *CHI '24* — [DOI](https://doi.org/10.1145/3613904.3642272)
- Zilin Ma, Krzysztof Z. Gajos (2022), Not Just a Preference: Reducing Biased Decision-making on Dating Websites, *CHI '22* — [DOI](https://doi.org/10.1145/3491102.3517587)
- B. J. Fogg u. a. (2002), [Stanford Guidelines for Web Credibility](https://credibility.stanford.edu/guidelines/index.html)
- Stephen Few (2004), [Dashboard Confusion](https://www.perceptualedge.com/articles/ie/dashboard_confusion.pdf); (2007), [Pervasive Hurdles to Effective Dashboard Design](https://www.perceptualedge.com/articles/visual_business_intelligence/pervasive_hurdles_to_dd.pdf)
- MDPI, [Judging Books by Their Covers: … Memorability of Italian Novels](https://www.mdpi.com/2410-9789/5/2/13) — nur Abstract-Auszug gesehen

Design-Systeme und Gesetze

- Carbon, [Button – Usage](https://carbondesignsystem.com/components/button/usage/) · [Empty states](https://carbondesignsystem.com/patterns/empty-states-pattern/)
- Primer (GitHub), [IconButton – Guidelines](https://primer.style/product/components/icon-button/guidelines)
- Apple HIG, [Toolbars](https://developer.apple.com/design/human-interface-guidelines/toolbars)
- Material Design 1, [Empty states](https://m1.material.io/patterns/empty-states.html)
- Shopify Polaris, [Empty state composition](https://shopify.dev/docs/api/app-home/latest/patterns/compositions/empty-state)
- Atlassian, [Empty state](https://atlassian.design/components/empty-state/) · [Date and time](https://atlassian.design/content/date-time/)
- Cloudscape (AWS), [Timestamps](https://cloudscape.design/patterns/general/timestamps/)
- Tableau, [Best Practices for Effective Dashboards](https://help.tableau.com/current/pro/desktop/en-us/dashboards_best_practices.htm)
- Laws of UX, [Hick's Law](https://lawsofux.com/hicks-law/) · [Miller's Law](https://lawsofux.com/millers-law/) · [Von Restorff Effect](https://lawsofux.com/von-restorff-effect/)
- Growth.Design (2020), [Coronavirus Dashboard UX](https://growth.design/case-studies/coronavirus-dashboard-ux)

Produkte

- Goodreads Blog 2016a — Maryana Pinchuk, [A New Look for the Goodreads Homepage](https://www.goodreads.com/blog/show/652-a-new-look-for-the-goodreads-homepage); 2016b — [New Goodreads Homepage Now Rolling Out to Everyone](https://www.goodreads.com/blog/show/670-new-goodreads-homepage-now-rolling-out-to-everyone); Forum 2016 (Sekundär) — [New Goodreads home page](https://www.goodreads.com/topic/show/18132602-new-goodreads-home-page)
- StoryGraph — [Changelog: Up Next and Suggestions](https://roadmap.thestorygraph.com/changelog/up-next-and-suggestions) (2021) · [Design, UI and UX Improvements](https://roadmap.thestorygraph.com/features/posts/-mobile-design-user-interface-and-user-experience-review) · [Showing Up-Next on Home Page](https://roadmap.thestorygraph.com/requests-ideas/posts/showing-up-next-on-home-page)
- BookWyrm — [Docs: Main Menu & Timelines](https://docs.joinbookwyrm.com/main-menu.html)
- mydealz — [FAQ: Nutzung der Seite](https://www.mydealz.de/seite/faq-nutzung)
- Keepa — [Herstellertext im Firefox-Add-on-Verzeichnis](https://addons.mozilla.org/en-US/firefox/addon/keepa/); Deals-Mechanik nach Sekundärquelle (Reseller-Blog)
- camelcamelcamel — [The Camelizer, Herstellertext](https://addons.mozilla.org/en-US/firefox/addon/the-camelizer-price-history-ch/); [Top Price Drops](https://camelcamelcamel.com/top_drops) (Abruf verweigert)
- Gmail-Hilfe — [Buttons in your Gmail toolbar](https://support.google.com/mail/answer/2473038) (`hover`-Aktionen)
