# Metadata sources — terms, limits and remaining alternatives

Companion to [`metadata-sources.md`](metadata-sources.md), which measured *whether*
the sources answer. This one asks whether we are *allowed* to ask, and how often.
Researched 2026-09-04, desk research plus a deliberately small number of live
probes.

Throughout, **proven** means a quotable statement from the operator or a
measurement taken here; **open** means nobody says, and I am not going to invent a
number. The distinction matters more than usual in this document, because one of
the four questions came back with an answer that changes the recommendation.

---

## TL;DR

- **The SRU interface is clean.** Free, explicitly no registration, data under
  CC0, no documented rate limit, not bot-gated. Daily automated use by a private
  tool is within what the DNB describes as its normal offer.
- **The cover endpoint is not clean.** The DNB says in so many words that it does
  not own or store these images, that display rests on a contract between the
  library association and VG Bild-Kunst which entitles *libraries*, and that
  anyone wanting to reuse them should ask the VLB. On top of that, `portal.dnb.de`
  is now behind an anti-bot challenge and no longer returns an image to a script.
  **This overturns "cover from the DNB first".**
- **MARC21 series fields**: 245 `$n`/`$p`, then 490 `$v`/`$a`, 246 `$a`, 800
  `$v`/`$t`, 830 `$v`/`$a` — in that order, first complete pair wins. The order in
  the reference plugin is the reverse of what we assumed.
- **Google Books works with a key, and still may not be our cover source.** All 30
  keyed requests answered `200`; it finds 13 of 30 and returns a thumbnail for
  every one of them. But its thumbnails come with `cache-control: private,
  max-age=86400`, and Google's API terms permit cached copies only as long as the
  cache header allows and forbid "permanent copies". A cover we keep is a permanent
  copy. **Out for covers, and a poor trade for identity against the CC0 DNB.**
- **No new cover source survives.** Wikidata has 273 German-language editions with
  a picture, in the whole database. Inventaire: 0 of 12. K10plus: 1 of 8, no
  covers. lobid: 2 of 6, no covers. DDB is digitised heritage, not the 2024 ebook
  shelf. ISBNdb is paid. openBD is Japanese. The shop remains the only cover
  source we may actually use.

---

## 1. The SRU interface

Everything here is proven, and it is unusually unambiguous for a legal question.

**Access.** The DNB's own SRU page states it plainly under *Zugangsvoraussetzungen*:
"Der Zugang zur SRU-Schnittstelle ist kostenfrei und ohne Registrierung möglich."
([DNB, SRU-Schnittstelle](https://www.dnb.de/DE/Professionell/Metadatendienste/Datenbezug/SRU/sru.html),
last changed 2026-06-12). No API key, no IP registration, no access token. Older
write-ups on the web claim registration and IP activation is required — that is
either about the OAI/SFTP bulk services or simply out of date, and the DNB's
current page is the better authority.

**Licence.** "Alle Titeldaten der Deutschen Nationalbibliothek […] sind kostenfrei
unter Creative-Commons-Zero-Bedingungen (CC0 1.0) zur freien Nutzung verfügbar."
([DNB, Geschäftsmodell für Metadatendienste](https://www.dnb.de/DE/Professionell/Metadatendienste/Datenbezug/geschaeftsmodell.html),
last changed 2024-12-17). CC0 means no attribution obligation and no restriction on
commercial or automated reuse — the title, author, language and series values we
take from a record carry no strings at all. The same page adds the expected
disclaimer: the data is offered "ohne Gewähr" for completeness or for not
infringing third-party rights.

The one carve-out worth knowing: the *Bestandsdaten* (holdings) are only "zum
größten Teil" free and are flagged per record, and GND cross-concordances are
CC BY 4.0. Neither touches what we read.

**Rate limits.** Documented per-response limits exist and are about paging, not
politeness: default 10 records, maximum 100 via `maximumRecords`, `startRecord`
up to 99,000, and a result-set ceiling of 99,000 records per query. **There is no
documented limit on request frequency anywhere on the DNB's interface pages.** I
looked at the SRU page, the business-model page and the metadata-services index and
found nothing. That is genuinely open, and "no documented limit" is not the same as
"no limit" — it means if we ever want certainty, the address is
`schnittstellen-service@dnb.de`, which the DNB publishes on the SRU page for
exactly this.

Two weak supporting signals, offered as signals and not as permission:
`https://services.dnb.de/robots.txt` disallows only `/fize-service`, so the SRU
path is not excluded from crawling; and a single live SRU query made during this
research (2026-09-04, `NUM=9783104026824`) returned normal MARC21 XML with no bot
challenge and no throttling header.

**Verdict.** Daily automated use by a private tool making a few dozen requests is
proven-compatible with everything the DNB documents. Keeping the existing
one-second spacing is courtesy, not compliance, and worth keeping anyway.

---

## 2. The cover endpoint — and why the recommendation has to change

This is where the previous document was wrong, and the correction is not a
judgement call. The DNB has a page about exactly this, and it says three things.

**Whose pictures they are.** "Grundlage für die Anzeige der Umschlagbilder im
Katalog der DNB ist eine Vereinbarung zwischen dem Deutschen Bibliotheksverband
e. V. (dbv) und der VG Bild-Kunst, die es **Bibliotheken** ermöglicht, den
Cover-Service des Verzeichnisses Lieferbarer Bücher (VLB) zu nutzen und
Umschlagbilder in ihre jeweilige Titelpräsentation einzubinden."
([DNB, Umschlagbilder](https://www.dnb.de/DE/Professionell/Metadatendienste/Kataloganreicherung/Cover/cover_node.html),
last changed 2026-06-12; emphasis mine). The picture belongs to the publisher, the
artist's rights are administered by VG Bild-Kunst, MVB distributes it, and the
permission to show it in a catalogue was negotiated for libraries as a class. We
are not a library, and this project is not a member of the dbv.

**Whether we may reuse them.** The same page has a heading that could not be more
on point — *"Darf ich Umschlagbilder aus dem Katalog der DNB nachnutzen?"* — and the
answer is a referral, not a yes: "Wenn Sie wissen möchten, welche Möglichkeiten es
gibt, die Umschlagbilder für eigene Zwecke zu nutzen, wenden Sie sich bitte an die
Kontaktadresse des Verzeichnisses Lieferbarer Bücher (VLB)." The DNB declines to
grant anything, because it has nothing to grant.

**Whether it is even the DNB's service.** "Die Hinterlegung, Speicherung oder der
Austausch von Abbildungen oder Bildern zu einzelnen Metadaten durch die DNB ist
daher nicht möglich." The DNB does not hold these images at all. So
`portal.dnb.de/opac/mvb/cover` is not a DNB cover database with a public face —
the `mvb` in the path is literal. It is the DNB's own consumption of the MVB
cover service, exposed at a URL that happens to take an ISBN. Reading it as a
public API was an inference from its shape, and the shape was misleading.

Two corroborations from outside the DNB. The GBV union catalogue's technical wiki
records that "Der Coverdienst von buchhandel.de wendet sich gezielt an
Bibliotheken" and points at the dbv agreement as the legal basis
([GBV Verbund-Wiki, Buchcover](https://verbundwiki.gbv.de/display/VZG/Buchcover)).
And MVB's own commercial interface makes the gating explicit: to fetch a cover over
the VLB REST API you need "die Berechtigung zur Anzeige der Mediendateien"
([VLB, REST-API](https://vlb.de/hilfe/datenbezug/rest-api)) — an authorisation
granted per customer, alongside credentials issued by the VLB. Publishers, for
their part, grant MVB an unlimited and *transferable* right to publish and
distribute the cover, and MVB "wird berechtigt, nicht aber verpflichtet" to pass
it on to third parties
([VLB Einstellbedingungen für Verlage](https://vlb.de/assets/images/vlb_Einstellbedingungen_Verlage_RZ.pdf)).
Transferable is the key word: the rights chain runs publisher → MVB → whoever MVB
chooses. It has never run to us.

**And now it does not even work.** One HEAD request to
`https://portal.dnb.de/opac/mvb/cover?isbn=9783104026824` on 2026-09-04 at 16:19 UTC
returned `HTTP/2 200` with `content-type: text/html` and Anubis cookies —
`portal.dnb.de` is now behind a proof-of-work anti-bot challenge, and a script gets
the challenge page rather than a JPEG. (The same guard sits in front of
`deutsche-digitale-bibliothek.de`, which is how I recognised it.) The 4-of-8 cover
hit rate in the previous document was measured earlier the same day; I did not
re-measure, and one HEAD is not a diagnosis — the guard may be adaptive, or
recent. But whatever the cause, a source that answers a browser and not a script,
whose operator says the images are not theirs to give, is not a source we can
build on.

**What this means.** The "cover from the DNB first, shop second" ordering does not
survive. What survives is the *principle* behind it — that the shop must not decide
what a book looks like any more than what it is — but there is no free, licensed,
machine-readable German cover source to put in front of the shop. The shop's own
listing image is the picture of the edition it sells, we are fetching a page we are
already fetching, and storing it locally rather than hotlinking keeps the reader's
attention private. That is now the whole cover strategy, not the fallback half of
one. If a licensed alternative is ever wanted, the honest route is the one the DNB
names: ask the VLB what a small private tool would need.

---

## 3. MARC21, series, and what the Calibre plugin actually does

Read from
[`citronalco/calibre-dnb`](https://github.com/citronalco/calibre-dnb) at
`master`, file `__init__.py` (1138 lines), fetched 2026-09-04.

**The fields.** Five carry series and volume, and the plugin reads all five:

| Field | MARC name | Subfields used | Shape |
|---|---|---|---|
| 245 | Title Statement | `$a` title, `$n` number of part, `$p` name of part | hierarchical; repeating `n`/`p` pairs |
| 490 | Series Statement | `$v` (name **and** index together), `$a` name | transcribed as printed |
| 246 | Varying Form of Title | `$a` | series and index in one string, `"Name ; 3"` |
| 800 | Series Added Entry — Personal Name | `$v` index, `$t` title | authority-controlled |
| 830 | Series Added Entry — Uniform Title | `$v` index, `$a` name | authority-controlled |

**The order is the opposite of what we assumed.** The blocks run 245 → 490 → 246 →
800 → 830, and each later block opens with

```python
if book['series'] and book['series_index'] and book['series_index'] != "0":
    break
```

so the **first** block that yields a complete name-plus-index pair wins and the rest
are skipped. 245 has priority; 830 is the last resort, not the first choice. (A
stale comment above the 490 block — "In theory book series are in field 830 […] So
let's look here if we could not extract series/series_index from 830 above" —
describes an earlier ordering and is worth not being misled by; 830 is 100 lines
*below*, not above.)

That ordering is defensible for our corpus. 830 and 800 are authority-controlled
and only get filled when a cataloguer linked the series to a GND record, which for
self-published thrillers usually did not happen. 245 `$n`/`$p` is filled from the
title page, which is where a self-published series number actually lives.

**Reliability.** Proven from our own measurement, not from the plugin: the DNB
supplied series for **3 of 8** records that came back at all. The plugin's own
author agrees that this is thin — there is a configurable fallback,
`guess_series_from_title`, that parses "Reihenname 3" out of the title string when
the MARC fields come up empty, and the plugin's test suite contains a case
(`Junipeei - Der Pfad der Gestrandeten`, index 5) that exists precisely because no
MARC field carried it. Two of the plugin's other regression tests pin series
extracted from 490 and from 245 respectively, which is direct evidence that the
DNB really does scatter series across fields rather than concentrating them in 830.

Two further details worth having, both from the same file:

- **Language** comes from 041 `$a`, converted from ISO 639-2/B to 639-3. This is
  the field behind the "5 of 5 records have a language" result.
- **Related editions** come from 776 `$w` ("Additional Physical Form Entry"), which
  holds the IDN of the print edition of an ebook. The plugin resolves each one with
  a second SRU query, then harvests 020 `$a` from those records for extra ISBNs.
  That is the mechanism behind the cover fallback the previous document wanted —
  and it is worth noting that it is a *second SRU round trip per book*, which
  roughly doubles our request count if we adopt it.

---

## 4. The alternatives, and why none of them is one

The question for each: does it have covers, does it know German ebook editions, and
may we use it freely. All three have to be yes.

**Wikidata** — free (CC0), and the coverage question is answerable with numbers.
Two aggregate queries against the
[Wikidata Query Service](https://query.wikidata.org/): items carrying an ISBN-13
(`P212`) at all: **365,062**. Items carrying an ISBN-13, declared German-language
(`P407 = Q188`), *and* an image (`P18`): **273**. Not thousand — two hundred and
seventy-three, in the entire database. An attempt to check our own 382 corpus ISBNs
directly did not produce a usable answer: WDQS rate-limited to one request per
minute during an active outage and then timed out at 504, and a retry against the
[QLever](https://qlever.cs.uni-freiburg.de/wikidata) mirror returned a
cross-product artefact whose six candidate items turned out to carry neither a
matching ISBN nor an image. So the per-ISBN hit rate is formally **not measured** —
but with 273 illustrated German editions in total, the expected overlap with 382
self-published thrillers is nil.

There is also a structural reason this will never improve, which is more useful than
the counts: `P18` points at Wikimedia Commons, and Commons "only accepts free
content" and explicitly refuses "scans or reproductive photographs of copyrighted
artwork, especially book covers"
([Commons:Licensing](https://commons.wikimedia.org/wiki/Commons:Licensing)). A
commercial publisher's cover cannot legally be on Commons. **Wikidata is
structurally incapable of being a cover source.** Out.

**Deutsche Digitale Bibliothek** — an aggregator of digitised cultural heritage from
some 30,000 museums, archives and libraries. Metadata is broadly CC0, binaries carry
per-institution licences, and the API needs a free key tied to a registered account
([DDB API-Nutzungsbedingungen](https://www.deutsche-digitale-bibliothek.de/content/api-nutzungsbedingungen)
— note the site is itself behind an Anubis challenge and I could only read it
through search results, so treat the licensing detail as second-hand). The decisive
point needs no key: the DDB's remit is digitised heritage, not the current trade
catalogue. It does ingest DNB records, so it would at best re-serve data we already
get from the DNB directly, one indirection further away. Out on content, before we
get to the key.

**Inventaire** — free (its own data CC0-ish, entities partly mirrored from
Wikidata), open API, no key. Measured here against 12 corpus ISBNs via
`api/entities?action=by-uris&uris=isbn:…`: **0 of 12** returned an entity. Out, and
for the same reason Open Library was — it is a community catalogue of what readers
catalogue, and nobody catalogues these.

**Bookwyrm** — not a separate source. It is federated reading software whose
instances draw metadata from Open Library and Inventaire, both of which we have now
measured at zero for this corpus. Nothing to test.

**K10plus (SRU)** — free, no key, the German academic union catalogue. Probed here
against 8 corpus ISBNs: **1 of 8** had any record, and that record carried no cover
reference. Predictable — academic libraries do not hold self-published ebook
editions. Its covers, where they exist, are the same buchhandel.de service under the
same dbv agreement, so it would inherit section 2's problem anyway. Out.

**lobid (hbz)** — free, CC0, JSON, no key. Probed against 6 corpus ISBNs: **2 of 6**.
Better than K10plus, still far below the DNB's ~7 in 10, and lobid carries no cover
images at all. It could conceivably serve as a small identity top-up for books the
DNB misses; it cannot help with pictures. Parked, not adopted.

**ISBNdb** — has covers, claims multilingual coverage including German, and is a
paid subscription ($14.99/month upward) with a one-request-per-second cap on the
entry plan ([ISBNdb pricing](https://isbndb.com/isbn-database)). Out on principle
for a private tool, and its cover images sit under the same publisher-rights
question as MVB's without any agreement in our favour.

**openBD** — free and does serve covers, but it is the Japanese books-in-print
service, carrying data from Japanese publishers and JPRO, and has been partly
frozen since JPRO stopped supplying it in June 2023
([openBD](https://openbd.jp/), [notice 2023-06-20](https://openbd.jp/news/20230620.html)).
Irrelevant to German ISBNs. Out.

**Perlentaucher** — a review aggregator (110,000-odd review notes on 67,000 books).
No public API is documented anywhere I could find, its text is editorial copyright
rather than open data, and its subject is literary criticism of mostly print
editions. Not a metadata source in our sense. Out.

**Google Books** — no longer unmeasured. A key was obtained and the probe run;
the numbers are in [`metadata-sources.md`](metadata-sources.md) and the terms have
a section of their own below, because the answer is more interesting than a bullet
allows. Short version: it works, it is the only measured source that returns a
picture, and its terms do not let us keep that picture.

---

## 5. Google Books, with a key — what its terms permit

Measured 2026-09-04 with an API key read from `data/secrets.env`: 30 requests,
one every 1.2 seconds, all `HTTP 200`. The `429` that blocked the earlier probe was
the unauthenticated quota and nothing else. Coverage and per-field results are in
[`metadata-sources.md`](metadata-sources.md); this section is only about permission.

**Access and cost.** Proven: an API key is free, needs a Google Cloud project, and
the anonymous path is unusable in practice — the earlier probe was refused on its
*first* request. The key is what turns Google Books from unmeasurable into usable.

**Quota.** Genuinely **open**, and I will not invent a figure. Neither
[*Using the API*](https://developers.google.com/books/docs/v1/using) nor
[*Getting started*](https://developers.google.com/books/docs/v1/getting_started)
states a requests-per-day or requests-per-second limit anywhere; the only numeric
limit either page carries is about paging — "The maximum number of results to
return. The default is 10, and the maximum allowable value is 40." The per-project
quota is a Cloud console figure, visible to whoever owns the project and adjustable
on request. Widely repeated numbers of 1,000 or 10,000 requests a day circulate on
blogs and forums; **none of them is on a Google page**, so treat them as hearsay.
What is proven is our own measurement: 30 keyed requests at roughly one per second
drew no throttling of any kind. A daily run over a few dozen ISBNs is very unlikely
to be near any ceiling, but "unlikely" is the honest word.

**Caching — this is the decisive clause.** The Google APIs Terms of Service forbid,
in §5.e.1, attempting to "Scrape, build databases, or otherwise create permanent
copies of such content", and permit cached copies only so long as you do not "keep
cached copies longer than permitted by the cache header"
([Google APIs Terms of Service](https://developers.google.com/terms)). §8.b closes
the loop on termination: you must "delete any cached or stored content that was
permitted by the cache header under Section 5."

So the cache header is the licence, and it is measurable. One HEAD request on
2026-09-04 against a thumbnail URL returned by the probe
(`books.google.com/books/content?id=…&printsec=frontcover&img=1&zoom=1`) came back
`HTTP/2 200`, `content-type: image/jpeg`, `content-length: 15035`, and:

```
cache-control: private, max-age=86400
```

**86,400 seconds is one day.** A cover we store and show for months is precisely the
"permanent copy" §5.e.1 names, and it outlives its cache header by orders of
magnitude. Under Google's own terms we would have to re-fetch every cover daily and
hold it no longer — which is not storage, it is hotlinking with extra steps, and it
hands Google a daily log of what the reader is looking at. That is the opposite of
why we store covers locally. The same clause applies to the title, author and
language fields, incidentally: they too are content under §5.e, and a metadata cache
that persists between Runs is the database §5.e.1 says not to build.

**Attribution, if we displayed it anyway.** The branding rules are not onerous but
they are not nothing. Google's
[branding guidelines](https://developers.google.com/books/branding) require that
"Google attribution is required", that "the 'powered by Google' logo must appear
adjacent to these results", that "Every book result displayed in your application
must have a prominent link to either (1) a page on your site featuring Google
Preview capabilities, or (2) the Google Books page for that book", and that "You
may not alter results or content made available through the Google Books API
Family" — so no resizing or re-cropping the thumbnail either. The Books API terms
add that "You may not charge users any fee for the use of your application" (not our
problem) and that content alleged to infringe third-party rights must be removed on
request.

**Verdict.** For **covers, out** — proven, on a quotable clause and a measured
header, not on a judgement call. For **identity fields**, the same caching clause
applies, so Google Books is only defensible as a *live lookup* whose answer is not
retained, or not at all. Given it finds 13 of 30 where the CC0 DNB finds 21 of 30,
paying that price for a four-book top-up is a poor trade. **The DNB's CC0 licence is
worth more here than Google's coverage**, and that is the finding: the one source
that had a picture for this corpus is the one source whose terms forbid keeping it.

---

## Still open

- **Request frequency at the DNB.** Nothing documented. If we want certainty rather
  than courtesy, `schnittstellen-service@dnb.de` is the published address.
- **Whether the Anubis guard on `portal.dnb.de` is permanent or adaptive.** One HEAD
  request is a data point, not a diagnosis. It does not change the licensing
  conclusion either way.
- **What the VLB would say** if asked what a private, non-commercial tool needs in
  order to display a cover. This is the only route to a licensed cover source, and
  it is a question for a human, not a script.
- **Google Books' actual quota.** Not documented on any Google page; the numbers
  repeated online are hearsay. If it ever matters, the project's own Cloud console
  shows the figure that applies to our key.
- **Whether the shop's own images carry any usage condition** we should read before
  storing them. We now depend on them entirely, which raises the stakes on a
  question nobody has asked yet.
