# Metadata sources for German ebooks

Ticket 13. **Complete** — Google Books was measured with an API key on
2026-09-04; see [the legal companion](metadata-sources-legal.md) for what its
terms allow.

Everything below was measured against ISBNs taken from a real Run
(2026-09-04), not against a demo ISBN. The corpus matters: these are German
ebook editions from a small shop's Psychothriller and Horror shelves, a large
share of them self-published. A source that answers well for English print
fiction can still be useless here, and one of them is.

## What Calibre does, and what it taught us

Calibre has solved this problem for twenty years, so it was worth reading
before measuring anything else.

**Built-in sources:** Google Books, **Google Images**, Amazon, Edelweiss, Open
Library. The interesting one is Google Images: it is a *cover-only* source.
Calibre does not assume one source answers both questions — it lets a book take
its facts from one plugin and its picture from another. That is the same split
this document arrives at below, and it is reassuring to find it as settled
practice rather than an improvisation.

Amazon is out for us regardless: its plugin scrapes product pages, which the
terms forbid and which this project would not do to a shop anyway.

**The German plugin is [`DNB_DE`](https://github.com/citronalco/calibre-dnb)**,
and reading it corrected a mistake in the first version of this document. It
does two things differently from my first probe:

- It asks for `recordSchema=MARC21-xml`, not `oai_dc`. Series and volume number
  live in MARC fields 830, 800, 490 and 245 — `oai_dc` simply does not carry
  them, so "the DNB has no series" was a statement about my query, not about
  the DNB.
- It fetches covers from a **different service**:
  `https://portal.dnb.de/opac/mvb/cover?isbn=<isbn>`. Behind it sits MVB, the
  German books-in-print register — the commercially licensed source this
  document had written off as unreachable. Through this endpoint it answers.

It also tries the ISBNs of *related editions* — the print edition of an ebook —
when the ebook's own ISBN has no cover. We capture only one ISBN per book today,
so that trick is not available to us yet, but it is the obvious way to raise the
hit rate later.

## Measured

Sample: 30 ISBNs for the first data probe, 8 for the second and for covers,
drawn evenly across the shelf discoveries of one Run. Requests are spaced by
over a second; this is a source we want to keep. The Google Books run uses
**exactly the same 30 ISBNs** as the `oai_dc` and Open Library rows, so those
three columns are directly comparable.

| Source | found | title | author | language | series | cover |
|---|---|---|---|---|---|---|
| **DNB** `MARC21-xml` | **5/8** | 5 | 5 | 5 | **3/8** | – |
| DNB `oai_dc` | 21/30 | 21 | 21 | **21** | 0 | – |
| **DNB cover** (`opac/mvb/cover`) | | | | | | **4/8** |
| Open Library (`api/books`) | 0/30 | – | – | – | – | – |
| Open Library (covers by ISBN) | 0/8 | | | | | 0 |
| **Google Books** (with key) | **13/30** | 13 | 13 | **13** | **0/30** | **13/30** |

**The DNB answers for about seven in ten** of these books and is the only
measured source that states the **language** — the filter that had no data
behind it at all.

**Covers come back for half**, and the notable part is *which* half: two of the
four covers belong to ISBNs the DNB catalogue itself had no record for. The
cover service is a different database, so it must be asked separately rather
than treated as a field of the catalogue record.

**Open Library is genuinely empty for this corpus** — both APIs, including for a
mainstream title (*Krieg der Klone*, Scalzi). It is not a rate limit; it answers
`{}` and `404`.

**Google Books, measured at last.** With an API key all 30 requests returned
`HTTP 200` — no `429`, so the earlier zero really was the blocked measurement it
was assumed to be. The result is a clean split rather than a verdict:

- **It answers for 13 of 30**, well under the DNB's 21, and when it answers it
  answers completely: title, author, `language` and `imageLinks` were present for
  **every one of the 13**, never partially. Language came back `de` in all 13.
- **`seriesInfo` was absent from all 30 responses.** Not empty — absent. Google
  Books is not a series source for this corpus at all, which is worse than the
  DNB's thin 3-of-8.
- **The two sets overlap only partly.** 9 of the 13 are books the DNB also has;
  **4 are books the DNB missed**. Asking both would lift identity coverage from
  21/30 to **25/30** — a real gain, at the cost of a second HTTP call per book
  and a dependency on a keyed commercial API.
- **`imageLinks` carried exactly `smallThumbnail` and `thumbnail` on all 13** —
  the `zoom=1` thumbnail is about 128 px wide and roughly 15 KB. Even setting the
  licence question aside, that is a list thumbnail, not a cover.

So Google Books is the first measured source that returns a picture at all for
this corpus. Whether we may keep that picture is decided in
[the legal companion](metadata-sources-legal.md), section 5 — and the answer is
no.

## Recommendation

**Split the two questions, as Calibre does.**

- **Identity** — canonical title, author, series, volume, language — from the
  DNB over `MARC21-xml`. It is the register of record for German publishing, it
  is free, it has no licence problem, and it answers for most of these books.
  Where it does not answer, the record falls back to what the Source said,
  marked unverified rather than silently.
- **Cover** — the listing Source, and nothing in front of it. This is the one
  place where the first version of this document was wrong: the DNB cover service
  is not the DNB's to give away, and Google Books' thumbnails may not be kept for
  longer than a day. Both are set out in
  [the legal companion](metadata-sources-legal.md), sections 2 and 5. The shop's
  image is fetched once from a page we already fetch and stored locally, never
  hotlinked, so no third party learns what the reader is looking at.

That keeps the point of the instruction — the shop must not decide what a book
*is* — while making sure a book always ends up with a picture. What it no longer
claims is that the picture comes from somewhere other than the shop. It does not,
because no free and licensed source for these covers was found.

**Google Books changes nothing about this recommendation, and the measurement
says why.** It cannot be the cover source: it may not be cached beyond 24 hours
and every displayed result would owe Google a logo and a backlink. It cannot be
the series source: `seriesInfo` never appeared. It cannot replace the DNB for
identity: 13 of 30 against 21 of 30. What it could be is a **top-up for the four
books in thirty the DNB does not have** — optional, keyed, and worth adding only
if those four in thirty are felt as a gap. Identity from the DNB, cover from the
shop, stands.

## Open

- Terms and rate limits for a daily automated caller — answered for the DNB and
  for Google Books in [the legal companion](metadata-sources-legal.md); what
  remains open there is request *frequency* at the DNB, which nobody documents.
- Whether the four-in-thirty top-up from Google Books is worth a second keyed
  API. Measured, not decided.
- Capture the print edition's ISBN so the cover fallback Calibre uses becomes
  available.
- What the Onleihe offers for the books only it stocks.
