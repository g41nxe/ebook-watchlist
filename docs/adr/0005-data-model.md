# 5. Data Model

> **Nachtrag:** Die Tabellenskizze unten ist ab Phase 2 durch **ADR 18**
> ersetzt — bis auf `run` und `observation`, die weitgehend bleiben. Die
> Deal-Logik, das Append-only-Prinzip und die Match Reasons gelten
> unverändert.

SQLite via SQLAlchemy for Snapshot/Run history from Phase 1; for Profile and
Watchlist from Phase 2 (Phase 1 keeps those in YAML — see ADR 10).

## Context

The UI edits Profile and Watchlist and shows results over time, so state must be
queryable and support history, not a flat file overwritten each Run. In Phase 1
there is no UI, so Profile/Watchlist stay in `profile.yaml` / `watchlist.yaml`
and only Observations and Runs go to SQLite. Phase 2 imports the YAML into the
`profile` / `watchlist_entry` tables below and the UI becomes the editor.

## Decision

Tables (fields indicative, not final):

- **profile** — `id`, `slug`, `name`, `strong_deal_max_cents` (default 500),
  `deal_max_cents` (default 1000), `min_discount_pct` (default 25),
  `reference_authors` (list), `genre_categories` (list of shop category paths,
  ADR 11), `no_gos` (list, dormant until keyword refinement / v2).
  In Phase 1 these live in `profile.yaml`.
- **watchlist_entry** — `id`, `profile_id`, `title`, `author`,
  `check_library` (bool), `check_shop` (bool), `active` (bool), `added_at`,
  `notes`, `resolved_links` (per-Source pinned URL/id, ADR 8),
  `hold_state` (`none` | `placed` | `ready`, unused until v2),
  `hold_expected_date` (nullable, unused until v2). See ADR 6.
  In Phase 1 entries live in `watchlist.yaml` (no `id`; keyed by title+author).
- **observation** — `id`, `profile_id`, `watchlist_entry_id` (nullable),
  `match_reason` (`watchlist` | `profile_author` | `genre_category`), `source`
  (e.g. `voebb`, `beam`), `source_item_id` (stable per Source), `title`,
  `author`, `price_cents` (nullable), `original_price_cents` (nullable, struck
  price when shown), `availability` (enum/text, nullable), `category` (nullable,
  for genre_category hits), `observed_at`, `run_id`. Append-only.
- **dismissal** — `source`, `source_item_id`. A dismissed genre suggestion never
  resurfaces. Phase 1: `dismissed.yaml`; Phase 2: this table + a UI button.
- **run** — `id`, `profile_id`, `trigger` (`cron` | `ui` | `cli`),
  `started_at`, `finished_at`, `status`, `delta_count`, `error` (nullable).

Derived, not stored: Deltas (latest vs previous Observation of the same
`(source, source_item_id)`), Deals (Delta price ≤ effective ceiling), the Digest.

## Decisions folded in

- **4a** Append-only Observations, not mutable current-state — history for the UI
  is worth the negligible row growth.
- **4b** Discoveries are stored as Observation rows with
  `watchlist_entry_id = NULL` and `match_reason = profile_author`; each Source
  must emit a stable `source_item_id` for dedup. A discovery can be promoted to a
  Watchlist Entry from the UI.
- **4c (superseded)** Two deal tiers, not a single ceiling:
  - **strong deal** — current price `< strong_deal_max_cents` (default 5,00 €),
    no discount check;
  - **deal** — `strong_deal_max_cents <= price < deal_max_cents`
    (5,00-9,99 €) **and** genuinely discounted: struck `original_price_cents`
    present and `price <= (1 - min_discount_pct/100) * original`, **or** the
    price fell by at least `min_discount_pct` vs. the previous Observation.
    A standing 9,99 € does not qualify.
  - Any price decrease is still reported as a Delta regardless of tier. No
    per-entry price override in v1 (dropped for simplicity).
  - **First sighting** of a Watchlist Entry is normally only the baseline the
    next Run diffs against, with one exception: a title that is *already* below
    `strong_deal_max_cents` is reported once, on sight. Waiting for a 3,99 €
    title to get cheaper still would be a strange way to answer "tell me when it
    is a bargain".
  - **beam-shop caveat** (research, ADR 11): German fixed-book-price law means
    beam-shop *never* shows a struck original price, so
    `original_price_cents` is always null for `source = beam`. The "deal" tier's
    struck-price branch is dead there; only the price-drop-vs-previous-Observation
    branch can fire, and only once history exists. The "strong deal" tier
    (absolute `< strong_deal_max_cents`) works fully.
- **4d** `no_gos` stays dormant until keyword refinement (ADR 11) or v2
  classification. `genre_categories` (a short curated list of shop category
  paths, ADR 11) is used from v1.

## Consequences

- Price-over-time and "changed since when" are answerable.
- Adding a Source needs no schema change — only a stable `source_item_id`.
- Old Observation rows can be pruned later if size ever matters; measured at
  ~25 MB per three years of daily runs, so not soon (ADR 16).
- Schema changes reach an existing database through migrations (ADR 16).
