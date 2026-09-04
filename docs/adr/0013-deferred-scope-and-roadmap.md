# 13. Deferred Scope and Roadmap

Consolidates what is intentionally not in v1 and roughly when it is expected.

## Context

Several capabilities were discussed and deferred while grilling the spec. This
ADR is the single place that lists them so they are not lost or silently
re-scoped.

## Decision

### v1
- **Phase 1:** headless core — Sources (VÖBB public, beam-shop), matcher, SQLite
  Observations/Runs, YAML config, text Digest, `ebw doctor` self-check.
- **Phase 2:** local FastAPI + HTMX web UI over the same DB; config moves from
  YAML into SQLite (ADR 3, ADR 10).

### v2
- **Library holds** — authenticated VÖBB account scraping, "notify when my
  Vormerkung is ready" (ADR 6).
- **Reliable genre classification** — LLM classification of unknown-author
  titles, tightly bounded (prefilter, permanent cache, cost cap). Supersedes the
  category-only heuristic of ADR 11 if it proves insufficient.
- **Keyword refinement** of category discovery (`genre_keywords`,
  `no_go_keywords`) if v1's category feed is noisy.
- **Series tracking** — a Watchlist Entry that names a *series* rather than a
  title, so the next volume is caught the moment it appears instead of having to
  be added by hand. The reader's profile leans heavily on investigator and
  profiler series, which makes this the most-wanted gap after v1. Both Sources
  expose the raw material already: the Onleihe has a `Reihe:` field on the
  detail page, and beam-shop carries the series in the tile subtitle
  ("Die sieben Schwestern 1"). Needs its own matching rules — a series name is
  a much weaker signal than a title — so it gets an ADR of its own when it
  arrives.

  There is already concrete evidence of the shape of the problem. A Watchlist
  Entry for "Otherland" was reported as not stocked, while beam-shop in fact
  carries all four volumes as "Otherland. Band 1" … "Band 4". The title guard
  that stops "Der Schwarm" from accepting "Der Schwarm 2" (ADR 8) scores
  "otherland" against "otherland band 1" at 72, below the 85 floor. The same
  mechanism that prevents a sequel being mistaken for its predecessor prevents
  a series name from finding its own volumes — which is exactly the distinction
  series tracking has to make explicit rather than leave to one threshold.
- **Profile matching of discoveries** — deciding whether a *found* title fits
  the reader's profile, not just whether its author or shelf does. This is what
  the LLM classification above is ultimately for; the atmosphere criteria in the
  profile ("beklemmend", "isolierte Settings", "Katz-und-Maus") are exactly the
  kind of thing a shelf label cannot capture. `profile.liked_books` is collected
  from day one as the raw material, and the profile is expected to sharpen as
  that list grows. Belongs together with the category-matching rework.
- **Books already owned** — the reader kept saying "I have that one". Today the
  only lever is `dismissed.yaml`, which says "stop suggesting this" rather than
  "I own this", and it does nothing for a Watchlist Entry. A real owned-or-read
  list is the honest concept, and it converges with the v3 Calibre integration
  below: Calibre *is* the owned library, so the two should be designed together
  rather than inventing a second list first.
- **Additional Sources** — a second German-language shop and/or library,
  exercising the pluggable Source interface. (A non-fixed-price / English-language
  shop is explicitly *not* planned — the focus is German-language literature,
  ADR 1.)

### v3
- **Calibre + device management integration:** on a confirmed Deal / availability,
  optionally **auto-purchase** the title and **push the asset** into the Calibre
  library and onward to the reading device. This deliberately revisits the
  original spec's "no automatic purchase" exclusion, which stays firm for v1/v2.

## Consequences

- v1 stays small and login-free.
- Auto-purchase remains explicitly out until v3 and will need its own ADRs
  (payment path, confirmation model, legal review).
