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
One watched item. From Phase 2 this is a Book Relation of kind `watching`
(ADR 18) — the title and author live on the Book, the per-Source links in
`book_source`, and current price/availability in the Snapshot as Observations.
Never on the entry itself.

### Book
A book as a thing in itself — title, author, ISBN, series — independent of any
Source. A Book row exists **only where the reader has a relationship to it**
(ADR 18); a bare discovery stays an Observation. Identity is the ISBN where one
is available, otherwise title and author through the matcher.

### Book Relation
What a Profile has to do with a Book: `watching`, `owned`, `liked`, `disliked`,
`dismissed`. Several hold at once — a book can be owned *and* have been watched.
Relations are deactivated rather than deleted, so "watched until you bought it"
stays visible.

### Interest
Where the tool should look for new books: a Reference Author or a Genre
Category, unified into one concept because both answer the same question and
produce the two discovery Match Reasons. Extensible by a free-text key —
publisher, series, keyword — each needing a handler, not a migration.

### Hold
The user's reservation ("Vormerkung") on a Library Source title that is
currently lent out. **v2 feature** (see ADR 6). A hold is *observed*, not set —
v2 reads it off the authenticated account page — so it lives on the Observation
as `hold_state` (`none` → `placed` → `ready`) and `hold_expected_date`
(ADR 18, correcting ADR 6). The `placed` → `ready` transition is therefore an
ordinary Delta, with history, rather than a mutable flag on an entry.

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
author, ISBN, blurb, series, price, availability status, hold state,
`observed_at`, the Source, a stable `source_item_id` from that Source, the
matching Book (or NULL for a discovery), and a Match Reason.

An Observation records **what the Source said at that moment**, not what we
believe. Title, author and ISBN are kept even when the Book is known, so that a
source quietly switching editions under the same id stays detectable.

### Match Reason
Why an item is in the Snapshot: `watchlist` (hard title/author match),
`profile_author` (the item's author is on the Profile's reference-author list),
or `genre_category` (the item is a new arrival in one of the Profile's
Genre Categories — a low-confidence suggestion).

### Genre Category
A Shop Source category path listed in `profile.yaml`'s `genre_categories`. v1
genre discovery trusts the shop's own shelving: new arrivals in this small
curated set are surfaced as suggestions. Dismissed suggestions
(`source_item_id`) never resurface.

Since ADR 19 a discovery from here is judged against the reading profile before
it reaches the reader, and it has to be a deal to be reported at all.

**Reader-facing name: *Thema*.** "Regal" was the shop's word for its own
shelving, not the reader's word for what interests them. The code keeps
`genre_category`; every string a reader sees says Thema, and both come from
`reasons.py`.

### Discovery
An item a Source turned up that the reader never asked for by name — its Match
Reason is `profile_author` or `genre_category`, never `watchlist`. A Discovery
stays an Observation and gets **no** Book row until the reader says something
about it (ADR 18). It is the case every filtering rule in this tool exists for:
a Watchlist title is always reported, a Discovery has to earn it.

### Rating Gate
The step that decides whether a Discovery reaches the reader at all (ADR 19).
It sits **behind** the Snapshot, so a failure costs a judgement and never
history, and **behind** the price rule, so nothing is judged that would not be
shown anyway. Without an API key it does nothing and everything is shown —
that is the intended degraded state, not an outage.

Its standing principle: **quality before quantity.** A handful of well-fitting
suggestions beats a pile of poor ones, and an empty pile is a good result.

**Reader-facing name: *Bewertungstor*.**

### Rating
What someone thinks of a book, on the Rubric's 0–5 scale, with a justification
and a confidence (`belegt` | `teils` | `vermutet`).

A Rating carries an **Origin** — who judged: `model` (the Rating Gate in a
Run), `conversation` (judged against the same Rubric in conversation; the
entries in `owned.yaml`), or `reader` (the reader's own stars, set on the book
page). The Origin is part of the key, because the difference is the point: a 4
from the reader is a fact, a 4 from a model is a suggestion (ADR 17). Both may
stand side by side, neither overwrites the other, and the two never render the
same.

A machine Rating is keyed to the *find* — the ISBN, else `(Source, item id)` —
because most finds never become a Book. A human Rating is keyed to the **Book**,
because that is where a person gives it and it should hold whichever Source the
book next arrives through.

A new Rubric version invalidates machine Ratings, and only those: that the
reader sharpened their own yardstick is no reason to void what they said.

### Rubric
The written yardstick a Rating is made against: `docs/leseprofil.md`, carrying
its own version number. It lives in the repository with its own change
procedure and an asymmetric burden of proof (ADR 17) — the web UI shows it and
refuses to edit it, because a form there would bypass that procedure.

**Reader-facing name: *Maßstab*.**

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
