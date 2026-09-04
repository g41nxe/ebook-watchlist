# Metadata sources for German ebooks

Ticket 13. **In progress** — Google Books is not yet measured.

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
over a second; this is a source we want to keep.

| Source | found | title | author | language | series | cover |
|---|---|---|---|---|---|---|
| **DNB** `MARC21-xml` | **5/8** | 5 | 5 | 5 | **3/8** | – |
| DNB `oai_dc` | 21/30 | 21 | 21 | **21** | 0 | – |
| **DNB cover** (`opac/mvb/cover`) | | | | | | **4/8** |
| Open Library (`api/books`) | 0/30 | – | – | – | – | – |
| Open Library (covers by ISBN) | 0/8 | | | | | 0 |
| Google Books | *not measured* | | | | | |

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

**Google Books answered `429 Quota exceeded`, not "not found".** Zero hits there
is a blocked measurement and must not be read as a result. It needs an API key
before it can be judged.

## Recommendation

**Split the two questions, as Calibre does.**

- **Identity** — canonical title, author, series, volume, language — from the
  DNB over `MARC21-xml`. It is the register of record for German publishing, it
  is free, it has no licence problem, and it answers for most of these books.
  Where it does not answer, the record falls back to what the Source said,
  marked unverified rather than silently.
- **Cover** — the DNB cover service first, the listing Source second. The DNB's
  picture is of the edition the register knows; beam's is of the edition it
  sells. Either is fetched once and stored locally, never hotlinked, so no third
  party learns what the reader is looking at.

That ordering keeps the point of the instruction — the shop must not decide what
a book *is*, nor what it looks like — while making sure a book always ends up
with a picture.

## Open

- Terms and rate limits for a daily automated caller, at both the SRU interface
  and the cover service. The cover endpoint exists to serve the DNB's own portal;
  a few dozen requests a day is modest, but it should be asked rather than
  assumed.
- Measure Google Books with a key: does it add anything over the DNB for the
  books the DNB misses?
- Capture the print edition's ISBN so the cover fallback Calibre uses becomes
  available.
- What the Onleihe offers for the books only it stocks.
