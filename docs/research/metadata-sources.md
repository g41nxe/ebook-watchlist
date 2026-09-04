# Metadata sources for German ebooks

Ticket 13. **In progress** — Google Books is not yet measured.

Everything below was measured against ISBNs taken from a real Run
(2026-09-04), not against a demo ISBN. The corpus matters: these are German
ebook editions from a small shop's Psychothriller and Horror shelves, a large
share of them self-published. A source that answers well for English print
fiction can still be useless here, and two of them are.

## Measured

Sample: 30 ISBNs for the data APIs, 8 for the cover API, drawn evenly across the
shelf discoveries of one Run.

| Source | found | title | author | language | cover | series |
|---|---|---|---|---|---|---|
| **DNB** (SRU, `oai_dc`) | **21/30** | 21 | 21 | **21** | 0 | 0 |
| Open Library (`api/books`) | 0/30 | – | – | – | – | – |
| Open Library (covers by ISBN) | 0/8 | | | | 0 | |
| Google Books | *not measured* | | | | | |

**Google Books answered `429 Quota exceeded`, not "not found".** Zero hits there
is a blocked measurement, not a result, and must not be read as one. It needs an
API key before it can be judged.

**Open Library is genuinely empty for this corpus** — both the data API and the
cover API, including for a mainstream title (*Krieg der Klone*, Scalzi). It is
not a rate limit; it answers `{}` and `404`.

**The DNB is the find.** Seventy percent, and it is the only measured source
that states the **language** — the filter that had no data behind it at all. It
returns no covers and no series in the `oai_dc` schema; whether a richer schema
(MARC21) carries the series is still open.

## The cover problem

No free metadata source measured so far has a cover for these books. That
conflicts with the instruction to take covers from a metadata source rather than
from the shop, so it is worth being explicit about why the recommendation below
deviates.

Unmeasured candidates, with what stands against each:

- **Google Books** — has thumbnails. Needs a key; quota unknown for a daily
  caller. Worth measuring next.
- **VLB / buchhandel.de** — the German books-in-print register, the natural home
  for exactly these titles. Cover access is a commercial licence, which a
  personal tool is not going to hold.
- **The Sources themselves** — beam carries the cover in the listing tile it
  already serves us, named by ISBN, at 200×200 and 2×. The Onleihe pictures its
  own catalogue.

## Recommendation

**Split the two questions rather than forcing one source to answer both.**

- **Identity** — canonical title, author, series, language — from the DNB. It is
  the register of record for German publishing, it is free, it has no licence
  problem, and it answers for seven in ten of these books. Where it does not
  answer, the record falls back to what the Source said, marked unverified.
- **Cover** — from the Source that listed the book. It is free, it needs no
  extra request, and a shop's own product image is a fair likeness of the
  edition it sells. Fetched once and stored locally, never hotlinked, so no
  third party learns what the reader is looking at.

This keeps the point of the original instruction — the shop must not decide what
a book *is* — while accepting that for this corpus the shop is the only place a
picture of it exists.

## Open

- Measure Google Books with a key: does it add covers or language over the DNB?
- Does the DNB's MARC21 schema carry series and volume number?
- Rate limits and terms for a daily automated caller at the DNB.
- What the Onleihe offers for the books only it stocks.
