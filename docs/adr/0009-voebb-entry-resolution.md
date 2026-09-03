# 9. VÖBB Entry Resolution

A Watchlist Entry is resolved to a concrete Onleihe title automatically from the
title + author the user typed. No manual URL entry.

## Context

The user will not paste Onleihe URLs. The only manual input is title + author in
the Watchlist "Add entry" form (or one-click promotion of a discovery). The spec
flagged Onleihe's free-text search as unverified.

## Decision

- **v1 implements VÖBB free-text search + auto-resolve.** Submit the search,
  parse candidates, rank with the Calibre-informed matcher (ADR 8), store the
  resolved title link on the entry.
- **Research done** — see `docs/research/voebb-search-interface.md`. Outcome:
  there is **no** JSON API, OpenSearch, or autocomplete on the VÖBB `berlin`
  instance. Build on the **server-rendered HTML**, scraped with `requests` +
  BeautifulSoup:
  - search: `GET .../frontend/search,0-0-0-0-0-0-0-0-0-0-0.html`
    `?cmdId=703&sK=1000&pText=<title> <author-lastname>&pMediaType=-1`
    (form declares POST, honours GET, no cookie for page 1);
  - single relevance-ranked free-text box — no fielded title/author search — so
    the matcher must rank candidates, not trust hit #1;
  - results: iterate `[test-id="mediaCard"]` → `cardTitle` / `cardSubTitle` /
    `cardAuthor` / `mediaInfoLink` href (`mediaInfo,0-0-<ID>-200-...html`) /
    `svg[test-id^="ic_"]` medium;
  - `keine Titeltreffer` ⇒ `check` returns `None`; count > 0 but zero cards ⇒
    raise (structure changed);
  - availability (public, no login) from the detail page
    *Exemplarinformationen* block: `.availability-count >= 1` ⇒ available, else
    unavailable with `.reservation-count` queue + `Voraussichtlich verfügbar ab:`
    date;
  - `doctor` probe: `pText="Die sieben Schwestern"` yields cards; title id
    `373164461` detail page yields parseable `.exemplar-count` /
    `.availability-count`.
- **Confidence gate (no manual confirm on the happy path):**
  - top candidate above a high similarity threshold -> accepted automatically;
  - ambiguous (nothing clears the bar, or two candidates are close) -> entry
    flagged "couldn't resolve, needs attention" in the UI and skipped until
    fixed. This is an exception surface, not routine work.
- **No manual-paste fallback.** (No JSON/OpenSearch alternative exists; HTML is
  the only interface. hCaptcha is loaded site-wide and DiViBib is known to
  challenge flagged bots — a challenge page trips the broken-parser guard, which
  is the intended loud failure. Mitigate with ADR 7 politeness + reusing the
  pinned detail URL each Run.)
- Once resolved, the pinned link is reused every Run (ADR 8 escape hatch);
  re-resolution only on repeated fetch failure.

## Consequences

- The matcher and the search spike are v1 critical path.
- A wrong auto-resolve is possible; raw scraped title/author on Observations and
  the Dashboard make it visible, and the entry can be re-pointed from the UI.
