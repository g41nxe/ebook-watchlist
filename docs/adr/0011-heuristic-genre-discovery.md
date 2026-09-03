# 11. Heuristic Genre Discovery (v1)

Genre discovery in v1 is category-based, not classification-based: new arrivals
in a small curated set of Shop Source categories are surfaced as low-confidence
suggestions.

## Context

The spec wanted unknown-title genre discovery via an LLM classification call.
That was cut for v1 (cost, caching, reliability). A broad curated author
whitelist was considered as an alternative and set aside. The chosen mechanism
is to trust the shop's own shelving for a deliberately limited category set.

## Decision

- **`profile.yaml` gains `genre_categories`:** a short list (start 2-5) of
  beam-shop category paths.
- **Discovery flow:** enumerate the listings for those categories, diff
  `source_item_id`s against past Observations, report anything new as a genre
  suggestion. Records the same Observation fields as any other Shop item, with
  `match_reason = genre_category`.
- **No keyword refinement in v1.0.** Title / author / price / URL / category
  only — no blurb fetch. `genre_keywords` / `no_go_keywords` (reusing `no_gos`)
  may be added later if the category feed is noisy.
- **Presentation:** a separate Digest section, "Genre-Vorschläge (unsicher)",
  never merged with Watchlist or Reference-Author hits.
- **Dismissals:** a `dismissals` set keyed by `source_item_id`. Phase 1: a
  `dismissed.yaml` list. Phase 2: a UI button. A dismissed id never resurfaces.
- **Research done** — see `docs/research/beam-shop-interface.md` (Shopware 5, no
  Store API, HTML only):
  - **new arrivals per category:** no RSS, no "Neuheiten" page. Use
    `GET /belletristik/<cat>/<subcat>/?o=1&p=<n>` (`o=1` = sort by release date),
    diff `data-ordernumber` product ids against past Observations. `NEU`
    (`badge--newcomer`) / `Vorbestellbar` badges are a corroborating signal.
  - **listing tiles carry everything** — `.product--box[data-ordernumber]`
    (dedupe by ordernumber), `.product--title` (exclude nested
    `.product--subtitle`), `.product--author` (strip leading `"von "`),
    `.product--price .price--default` (`"9,99 €"`, de-DE). No per-product fetch.
  - **category paths are broad shelves; no niche cross-tags** — there is **no**
    "space horror" or "harter Thriller" shelf. Map `genre_categories` to the
    nearest real shelves, e.g. `belletristik/science-fiction/space-opera`,
    `.../military-sf`, `.../science-fiction-allgemein`,
    `belletristik/krimi-thriller/psychothriller`, `.../spionage`,
    `belletristik/horror-mystery/horror-mystery-allgemein`. Genre precision is
    coarser than the spec's niche framing (Blocker 4 "temper expectations").
  - **`by_author`** (feeds `profile_author` discovery — adjacent): author hub
    pages `/autor-innenwelt/<slug>/` exist for only ~30 curated authors. For
    every other Reference Author use `GET /search?sSearch=<author>&n=100` +
    strict client-side `.product--author` re-match (tolerating
    `"Nachname, Vorname"` vs `"Vorname Nachname"` and multi-author strings).

## Consequences

- No LLM and no classifier in v1; quality is entirely the shop's shelving, which
  is coarse-grained.
- `match_reason` enum grows to `watchlist` | `profile_author` | `genre_category`.
- Keeping the category list small bounds both noise and request volume.
- `by_author` for non-curated authors is a search + filter, not an index lookup —
  more requests and more noise to filter.
- Genuinely reliable genre classification remains a possible v2 feature.
