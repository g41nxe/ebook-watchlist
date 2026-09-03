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
