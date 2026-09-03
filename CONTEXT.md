# Context: eBook-Watchlist & Deal-Finder

## Glossary

### Profile
A reader's taste definition: Reference Authors (a whitelist), Genre Categories,
deal thresholds (`strong_deal_max_cents`, `deal_max_cents`, `min_discount_pct`),
and no-gos (dormant in v1). A first-class, keyed entity. v1 runs with a single
profile, but nothing hard-codes that — the data model and code support multiple
profiles.

### Watchlist
The set of Watchlist Entries belonging to one Profile. Titles/authors actively
watched regardless of whether they fit the Profile's genres.

### Watchlist Entry
One watched item. Holds: title, author, which Source kinds to check, pinned
per-Source links once resolved, and (v2) hold fields. Current price/availability
is not stored on the entry — it lives in the Snapshot as Observations.

### Hold
The user's reservation ("Vormerkung") on a Library Source title that is
currently lent out. **v2 feature** (see ADR 6). Modelled now via unused
`watchlist_entry.hold_state` (`none` → `placed` → `ready`) and
`hold_expected_date` columns; detecting `placed` → `ready` needs an
authenticated scrape of the user's library account, which v1 deliberately
avoids.

### Source
A place that is polled for data, behind a common interface. Two kinds in v1:

- **Library Source** — reports availability/borrowable status for a title.
  First implementation: VÖBB Onleihe (Berlin).
- **Shop Source** — reports price and catalogue presence for a title.
  First implementation: beam-shop.de (DRM-free German ebook shop).

More Sources of either kind can be added without changing the core.

### Snapshot
The stored history of Observations. A Run compares the latest Observation of an
item against the previous one and reports only what changed. Append-only, not a
single mutable current-state row.

### Observation
One recording of an item's state as seen by a Source during a Run: title,
author, price, availability status, `observed_at`, the Source, a stable
`source_item_id` from that Source, the matching Watchlist Entry (or NULL for a
discovery), and a Match Reason.

### Match Reason
Why an item is in the Snapshot: `watchlist` (hard title/author match),
`profile_author` (the item's author is on the Profile's reference-author list),
or `genre_category` (the item is a new arrival in one of the Profile's
Genre Categories — a low-confidence suggestion).

### Genre Category
A Shop Source category path listed in `profile.yaml`'s `genre_categories`. v1
genre discovery trusts the shop's own shelving: new arrivals in this small
curated set are surfaced as suggestions, with no classifier and no keyword
filtering in v1.0. Dismissed suggestions (`source_item_id`) never resurface.

### Reference Author
An author on the Profile's whitelist. Any item by a Reference Author is a
Profile Match, discovered even if not on the Watchlist.

### Strong Deal
An item whose current price is below `strong_deal_max_cents` (default 5,00 €).
No discount check — cheap outright is enough.

### Deal
An item priced between `strong_deal_max_cents` and `deal_max_cents`
(5,00-9,99 € by default) **and** genuinely discounted: at least
`min_discount_pct` (default 25%) below its struck original price, or below the
last price we observed. A standing 9,99 € is not a Deal. Note: beam-shop never
shows a struck price (German Buchpreisbindung), so beam Deals can only be
detected via an observed price drop, once history exists.

### Price Delta
Any decrease in an item's price versus the previous Observation. Always reported
in the Digest, independent of whether it also qualifies as a Deal or Strong Deal.

### Delta
The umbrella term for a reportable change between the latest Observation and the
previous one: an availability change (`not-available → available`), a Price
Delta, or a new discovery appearing. Deal / Strong Deal are flags on a Delta,
not separate things.

### Watchlist Match
A hard match: a scraped item resolves to a Watchlist Entry — by normalized
title/author comparison, a fuzzy fallback above threshold, or a previously
pinned per-Source link (see ADR 8).

### Profile Match
A soft match for titles not on the Watchlist: the scraped item's author is on
the Profile's Reference Author whitelist. LLM genre classification of
unknown-author titles is out of scope for v1 (a possible v2 feature); v1 genre
discovery is category-based instead (see Genre Category). The Profile's `no_gos`
stay dormant until keyword refinement or v2.

### Digest
A structured object a Run produces when it finds one or more Deltas or a Source
errored: an ordered list of sections (Bibliothek, Watchlist — Preise, Neue Titel
deiner Autor:innen, Genre-Vorschläge (unsicher), ⚠️ Fehler — always last), each
with typed entries. Empty sections are omitted. Rendered two ways from the one
model: a **text renderer** (stdout / cron logs) and an **HTML renderer**
(`data/digests/digest-<date>.html`, and HTML email later). Phase 2's Dashboard
renders the same model with shared HTML partials. Worded "Änderungen seit
letztem Check <date>", never "today". Fully silent only when there are no Deltas
and no errors — an error-only Digest still renders.

### Run
One execution of the scrape-diff-report cycle for a Profile. Fired three ways
against one entrypoint: cron (best-effort), the UI "Run now" button, or the CLI.
A Run is stateless with respect to schedule: it diffs current reality against the
Snapshot whenever the Snapshot was last written, so skipped runs lose nothing —
the next Run reports the accumulated Deltas. A lock serialises concurrent Runs.

### Seed file
An optional YAML file used to import/bootstrap a Profile and its Watchlist into
the database. Not the live store — once imported, the database is the source of
truth and edits happen through the UI.
