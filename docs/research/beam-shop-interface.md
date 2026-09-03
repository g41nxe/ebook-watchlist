# beam-shop.de — machine interface research

Research spike for ADR 0011 (heuristic genre discovery) and the Shop Source half of
ADR 0009 / ADR 0005. Goal: programmatic, **no-login** access to (a) title+author
search, (b) all titles by an author, (c) new arrivals per category, (d) reading
title / author / price (/ struck price) off listing pages.

Investigated 2026-09-03/04 against the live site.

---

## 0. TL;DR / RECOMMENDATION

- **Platform: Shopware 5** (classic server-rendered PHP/Smarty storefront), custom
  "Beam" theme. nginx 1.22 + Varnish 7.1 + PHP 8.2. **No Shopware 6 `/store-api`,
  no REST API, no `sw-access-key` anywhere.** → **HTML scraping is the only option.**
- Every listing (search results, category pages, author hub pages) is **fully
  server-rendered HTML** and carries **title + author + price + product-id +
  order-number + category** on each product tile. **No per-product detail fetch is
  needed** for check / by_author / genre-discovery.
- **No struck / pseudo / UVP price is *ever* shown** (German fixed-book-price law).
  `original_price_cents` will always be null from this source. The ADR 0005 "deal"
  tier that needs a struck original price is **not feasible** here; the price-drop-
  vs-previous-Observation half of that tier **is** feasible (we keep history).
- **check(entry):** `GET /search?sSearch=<title> <author>&n=48`, then match tiles
  with the ADR 8 matcher. Fuzzy AND-ish relevance; exact title+author lands rank 1
  in practice, but the result set is noisy — strict client-side matching required.
- **by_author(author):**
  - For the ~30 *curated* authors: `GET /autor-innenwelt/<slug>/?p=<n>` — an
    authoritative, paginated category listing of that author's full catalogue.
  - For everyone else (the common case): `GET /search?sSearch=<author>&n=100`
    (+ `&p=`), then keep only tiles whose `.product--author` matches the author.
    There is **no** generic per-author index or supplier filter.
- **genre-category new arrivals:** `GET /belletristik/<cat>/<subcat>/?o=1&p=<n>`
  (`o=1` = sort by release date, newest/preorders first). Diff `source_item_id`s
  against past Observations per ADR 11. Optionally also honour the `NEU`
  (`badge--newcomer`) / `Vorbestellbar` (`badge--preorder`) tile badges.
- **Bot defence:** none beyond `robots.txt` (`Crawl-delay: 3`, blocks named SEO
  bots only) and Varnish. No Cloudflare, no WAF, no captcha, no rate-limit seen.
  Use a real browser UA and stay ≤ ~1 req/s.

---

## 1. Platform fingerprint

| Signal | Value |
|---|---|
| Server | `nginx/1.22.1`, `X-Powered-By: PHP/8.2.33` |
| Cache | `Via: 1.1 varnish (Varnish/7.1)`; listing pages `X-Cacheable: NO:backend sent Set-Cookie` (session cookie ⇒ not edge-cached) |
| CMS | Shopware **5** — paths `/themes/Frontend/Beam/frontend/_public/src/...`, endpoints `/widgets/index/refreshStatistic`, `/RememberSearch/ajaxGetTermListMarkup`, `/notes/articlesInWishlist`, `/checkout/ajaxAddArticleCart`, compiled assets under `/web/cache/<ts>_<hash>.js|css` |
| Store API | **absent.** `/store-api/*` → not present. No `sw-access-key`, no `window.storeApi`, no `application/ld+json` on product pages. |
| Sitemap | `/sitemap.xml` = sitemapindex → `/web/sitemap/shop-1/sitemap-N.xml.gz` (13+ gzipped parts). Product URLs only, not author-indexed. |
| CSP | `content-security-policy: frame-ancestors 'self'; report-uri /csp_report_enforcing` (irrelevant to scraping) |

**Consequence:** treat it as a plain HTML site. All URLs below are plain `GET`,
no auth, no CSRF for reads (CSRF tokens exist only on the add-to-cart / wishlist
POST forms embedded in tiles — ignore them).

---

## 2. Search  — `check(entry)`

### URL / params
```
GET https://www.beam-shop.de/search?sSearch=<urlencoded query>
        &n=<page size>     # optional, default 12, MAX 100 (n=200/500 clamp to 100)
        &p=<page>          # optional, 1-based, paginates beyond the first n
        &o=<sort>          # optional; 1=release date, 2=popularity, 3=price asc,
                           #           4=price desc, 5=title, 7=best match (default)
```
- **Minimum query length = 4 characters.** 1–3 chars (`"abc"`, `"Tod"`, `"War"`,
  `"Le"`) → page renders with `<title>Suchergebnisse | Beam Shop</title>` and **0**
  product tiles. 4+ chars (`"Dune"`, `"Mars"`, `"Ende"`) → `<title>Suchergebnis
  für <q> | Beam Shop</title>` with results.
- Fully server-rendered. No JSON endpoint. (Shopware 5 also has an ajax
  autosuggest at `/widgets/listing/searchSuggestions?sSearch=…` returning a small
  HTML fragment of ~8 items — **not** worth using; the main page is richer.)
- Result page has **no visible total count** and the `.listing--actions` block
  often carries the class `without-pagination`, but **pagination still works** via
  `&p=` / `&n=` regardless of that class. Practical ceiling: `n=100`, then page.

### Relevance behaviour (important)
Shopware fuzzy search over-matches. Observations:
- `sSearch=Redshirts` → tile #1 is exactly *Redshirts* by "Scalzi, John"; tiles
  #2+ are `Amazon Redshift Cookbook`, `The Red Badge of Courage`, … (token /
  substring noise).
- `sSearch=Krieg der Klone Scalzi` → tile #1 is exactly *Krieg der Klone*
  (id 606983). Multi-word queries behave AND-ish and rank the true hit first.
- `sSearch=Scalzi&n=100` → 94 tiles: real John Scalzi editions **plus**
  "Scali, Lucrezia", "Giordano Scalzo…", "H. Beam Piper", "Jules Verne",
  multi-author anthologies, etc.
- `sSearch=John Scalzi` top-12 were all *Hungarian* Scalzi editions
  (`…/fremdsprachige-romane/…`); the German editions appeared only further down
  the `n=100` list. **Do not trust rank/top-N alone — always re-match every tile.**

### Recommended check() flow
1. `GET /search?sSearch=<title> <author>&n=48`.
2. Parse tiles (§5). For each tile compute similarity with the ADR 8 /
   Calibre-informed matcher against `(title, author)`.
3. Accept the best tile above the high threshold; else mark the entry
   "couldn't resolve" (same gate as ADR 9). Store `product_id` + product URL as
   the pinned `resolved_links["beam"]` and reuse it on later Runs; re-resolve only
   on repeated fetch failure.
4. Price / availability come straight off the pinned product URL's own tile-less
   detail page, or simpler: re-run the search and read the pinned tile. The
   detail page price node is
   `.product--price .price--content > meta[itemprop="price"]@content` (e.g.
   `content="4.99"`), text `"4,99 €"` beside it.

---

## 3. Author listings — `by_author(author)`

### 3a. Curated author hubs — `/autor-innenwelt/<slug>/`
- **Only ~30 hand-picked authors have a page.** Full list found on the index
  `GET /autor-innenwelt/` (page 1 of a flyout; these are all of them):

  `agatha-christie, andreas-brandhorst, andrew-bannister, andreas-eschbach,
  andrzej-sapkowski, brandon-sanderson, cixin-liu, charlotte-link, dan-brown,
  dirk-van-den-boom, frank-herbert, george-r.-r.-martin, isaac-asimov,
  james-corey, john-scalzi, j.r.r.-tolkien, ken-follett, lee-child, leigh-bardugo,
  lucinda-riley, peter-f.-hamilton, peter-v.-brett, rebecca-yarros, rick-riordan,
  robert-jordan, sarah-j.-maas, sebastian-fitzek, stephen-king, terry-pratchett,
  ursula-k.-le-guin`

- **Slug rule (observed):** lowercase; spaces → `-`; **periods are kept**
  (`j.r.r.-tolkien`, `george-r.-r.-martin`, `peter-f.-hamilton`,
  `ursula-k.-le-guin`, `t.-c.-boyle` would be the form). Comma-form "Nachname,
  Vorname" is *not* used — it is "vorname-nachname". Umlaut handling unverified
  (no curated author has one); Shopware's default transliteration is
  `ä→ae, ö→oe, ü→ue, ß→ss` — assume that, but it is moot because non-curated
  names 404 anyway (`wolfgang-hohlbein`, `frank-schaetzing`, `t.-c.-boyle` all
  → HTTP 404, `<h1>Beam Shop</h1>`).

- **Structure:** the hub page IS a Shopware category listing.
  `<div class="listing" data-categoryid="614" data-pages="2" data-infinite-scrolling="true">`
  (614 = John Scalzi, 611 = Andreas Brandhorst, …). It lists that author's
  **entire** beam catalogue (all languages, bundles, single episodes).
  - Pagination: `?p=<n>` (1-based). `data-pages` = number of pages at the default
    12 tiles/page. `?n=` also honoured (≤100).
  - `?o=1` works here too (release-date sort) if you want the author's newest.
  - `<h1>` = the author's display name; `<title>` = `"<Name> eBooks ohne hartes
    DRM | Beam Shop"`.

- **`/autor-innenwelt/` (no slug)** = aggregate landing of all 30 authors' books
  (`data-categoryid="609"`, `data-pages="68"`). Not useful for a single author.

### 3b. Everyone else — search fallback
No generic author index, no `sSupplier` / manufacturer filter for authors
(Shopware "supplier" here = **Verlag/publisher**, exposed as the `Verlag` filter
facet, not the author). So:
```
GET /search?sSearch=<author name>&n=100&p=<n>
```
then keep tiles whose `.product--author` (`"von …"` stripped) matches the target
author under a name-equality check that tolerates:
- `"von Nachname, Vorname"` vs `"von Vorname Nachname"` (both forms occur,
  sometimes for the *same* author on the same page — e.g. "von John Scalzi" and
  "von Scalzi, John"),
- multi-author strings (`"von A, B, C"` for anthologies — match if the target is
  one of the members, or reject, per profile intent),
- minor spelling noise (fuzzy search returns "Scali", "Scalzo", …).

Expect to page through several `n=100` blocks for prolific authors and to discard
50–70% of tiles as noise.

---

## 4. Category taxonomy & new arrivals — genre discovery (ADR 11)

### 4a. URL structure
Category URLs are path-based, always trailing-slash, nestable 2–3 deep:
```
/<top>/                         e.g. /belletristik/
/<top>/<cat>/                   e.g. /belletristik/science-fiction/
/<top>/<cat>/<subcat>/          e.g. /belletristik/science-fiction/space-opera/
```
Product URLs: `/<top>/<cat>/<subcat>/<productId>/<title-slug>?c=<catId>`
(the `?c=` / `?number=` query params are context only — strip them; the
canonical product URL is the path without query).

Each listing page exposes its numeric id + size:
`<div class="listing" data-categoryid="233" data-pages="1030" …>`.

### 4b. Genre category paths relevant to the profile

**Science Fiction** — `/belletristik/science-fiction/` (catId **233**, ~1030 pp.):
| subcat path | label |
|---|---|
| `/belletristik/science-fiction/science-fiction-allgemein/` | Science Fiction allgemein |
| `/belletristik/science-fiction/space-opera/` | **Space Opera** (catId 245, ~236 pp.) |
| `/belletristik/science-fiction/military-sf/` | Military SF |
| `/belletristik/science-fiction/dystopie/` | Dystopie |
| `/belletristik/science-fiction/postapokalypse/` | Postapokalypse |
| `/belletristik/science-fiction/sf-klassiker/` | SF-Klassiker |
| `/belletristik/science-fiction/alternative-geschichte/` | Alternative Geschichte |
| `/belletristik/science-fiction/cyberpunk/` | Cyberpunk |
| `/belletristik/science-fiction/science-fantasy/` | Science Fantasy |
| `/belletristik/science-fiction/steampunk/` | Steampunk |
| `/belletristik/science-fiction/zeitreisen/` | Zeitreisen |
| `/belletristik/science-fiction/dirk-van-den-boom/` | (author shelf inside SF) |

**Krimi & Thriller** — `/belletristik/krimi-thriller/` (catId **258**, ~3892 pp.):
| subcat path | label |
|---|---|
| `/belletristik/krimi-thriller/krimi-thriller-allgemein/` | Krimi & Thriller allgemein |
| `/belletristik/krimi-thriller/psychothriller/` | Psychothriller |
| `/belletristik/krimi-thriller/spionage/` | Spionage |
| `/belletristik/krimi-thriller/regionalkrimis/` | Regionalkrimis |
| `/belletristik/krimi-thriller/true-crime/` | True Crime |

**Horror & Mystery** — `/belletristik/horror-mystery/` (catId **267**, ~409 pp.):
| subcat path | label |
|---|---|
| `/belletristik/horror-mystery/horror-mystery-allgemein/` | Horror & Mystery allgemein (only child) |

**Mapping to the profile's wanted genres:**
| profile genre | best beam category path(s) |
|---|---|
| space opera / SF | `/belletristik/science-fiction/space-opera/`, `…/science-fiction-allgemein/`, `…/military-sf/` |
| space horror / SF-horror | **no dedicated shelf.** Use `/belletristik/horror-mystery/horror-mystery-allgemein/` and/or `/belletristik/science-fiction/science-fiction-allgemein/`; there is no cross-tag. |
| thriller | `/belletristik/krimi-thriller/krimi-thriller-allgemein/`, `…/psychothriller/` |
| crime / "harte" thriller | `/belletristik/krimi-thriller/krimi-thriller-allgemein/` (no "hard/tough" sub-shelf exists), `…/psychothriller/`, `…/spionage/` |

Other top-level trees exist (`/sachbuch/…`, `/belletristik/fantasy/…`,
`/belletristik/romance/…`, `/belletristik/horror-mystery/…`,
`/belletristik/fremdsprachige-romane/`) — enumerate a category's children by
fetching it and reading the sidebar `<a href*="/belletristik/…/">` links, or the
flyout endpoint `GET /widgets/listing/getCategory/categoryId/<id>`.

### 4c. "New arrivals in a category"
- **No RSS feed** (`<link type="application/rss+xml">` absent; no `/feed`).
- **No per-category "Neuheiten" page.** `/neuerscheinungen` (linked from menus as
  "Vorbestellen"/"Neuerscheinungen") renders an emotion/CMS page with **0**
  scrapable tiles — ignore it.
- **Mechanism = release-date sort:** append `?o=1` to any category/subcategory
  URL. `o=1` ("Erscheinungsdatum") sorts **newest first**, with not-yet-released
  `Vorbestellbar` (preorder) items at the very top, then `NEU` items, then the
  back-catalogue.
  ```
  GET /belletristik/science-fiction/space-opera/?o=1          # page 1
  GET /belletristik/science-fiction/space-opera/?o=1&p=2      # page 2 …
  ```
- **Pagination:** `?p=<n>` 1-based; works to arbitrary depth (`?p=50` still
  returns a full page). Default 12 tiles/page; `?n=<k>` raises it (**cap 100**).
  `data-pages` on `.listing` = total pages at 12/page. Infinite-scroll on the
  live site just fetches `?p=n+1` and appends — the plain paginated URLs give the
  same HTML.
- **Tile badges** (optional secondary signal, `.product--badge` text):
  `Vorbestellbar` = `badge--preorder`, `NEU` = `badge--newcomer`. Shopware
  auto-assigns `NEU` to products released within its "mark as new" window. Filter
  out `badge--preorder` if you only want already-released titles, or use the
  `Bereits erschienen` vs `Vorbestellbar` filter facet.
- **Recommended per ADR 11:** pull the first few pages of `?o=1` for each
  configured category, diff tile `product_id` (or order-number) against prior
  Observations, emit the new ones as `match_reason = genre_category` with the
  category path recorded. Stop paging once you hit a page of all-already-seen ids.

---

## 5. Product tile — selectors (identical on search / category / author pages)

Container (repeats **2–3×** per product in the DOM: overlay slot, image slot,
list-view slot — **dedupe by `data-ordernumber`**):

```html
<div class="product--box box--basic"
     data-ordernumber="SW9783641358792450428"   <!-- order number, see §5b -->
     data-category-id="245">
  <div class="product--badges">
    <div class="product--badge badge--preorder">Vorbestellbar</div>
    <div class="product--badge badge--newcomer">NEU</div>
  </div>
  <a class="product--title"
     href="https://www.beam-shop.de/belletristik/science-fiction/space-opera/1278797/star-wars-die-verschollenen?c=245"
     title="Star Wars™ - Die Verschollenen">
     Star Wars™ - Die Verschollenen
     <span class="product--subtitle" title="…">Feiern du musst! …</span>   <!-- optional -->
  </a>
  <a class="product--author" href="…same product url…" title="…">
     von Zahn, Timothy
  </a>
  <div class="product--description"><a href="…">… teaser …</a></div>
  <div class="product--price-info">
    <div class="price--unit" title="Inhalt"></div>
    <div class="product--price">
      <span class="price--default is--nowrap">9,99&nbsp;€</span>
    </div>
  </div>
  <div class="product--actions">
    <button class="action--note" data-note-article="1278797" …>   <!-- numeric product id -->
    <input type="hidden" name="sAdd" value="SW9783641358792450428">
  </div>
  <a class="product--image" …>
     <img class="lazy" data-srcset="https://www.beam-shop.de/media/image/…/9783473513215_200x200.jpg, …">
  </a>
</div>
```

| field | extraction |
|---|---|
| **title** | `.product--title` first text node, trimmed (exclude the nested `.product--subtitle` span). Also in the `title=""` attr (clean, no subtitle). |
| **subtitle** | `.product--title > .product--subtitle` (optional) |
| **author** | `.product--author` text, strip leading `"von "`. Format is **inconsistent**: `"Nachname, Vorname"` or `"Vorname Nachname"` or a comma-joined multi-author list. |
| **price (current)** | `.product--price-info .price--default` → `"9,99 €"`. Parse `de-DE` (`.` thousands, `,` decimal) → cents. Always exactly one price. |
| **struck / original price** | **never present.** No `.price--pseudo`, `.price--discount` (as a value), `UVP`, or `statt …` anywhere — checked search, all genre categories, `/specials/*`, `/ebook-bestseller-des-monats`, bundles, free books. |
| **product URL** | `.product--title@href`; strip `?c=` / query for canonical. |
| **product id** (stable `source_item_id`) | numeric, from `[data-note-article]` in the tile, or the 2nd-to-last URL path segment (`…/1278797/star-wars-…`). Recommended primary id. |
| **order number** | `data-ordernumber` on `.product--box` (also `input[name=sAdd]`). Form `SW` + 13-digit ISBN + optional supplier suffix, e.g. `SW9783641358792450428` → ISBN `9783641358792`, suffix `450428`; `SW9783641113414` → ISBN `9783641113414`, no suffix. Handy for cross-matching Calibre / Onleihe by ISBN. |
| **category id** | `data-category-id` on the tile / `data-categoryid` on `.listing`. |
| **cover** | `.product--image img@data-srcset` (lazy; real URLs under `/media/image/…`). |
| **badges** | `.product--badge` text: `Vorbestellbar`, `NEU`. |

**Listing-level:** `<div class="listing" data-categoryid data-pages>`.
`<h1>` = category / author / `"Suchergebnis für …"`. No total-item count in markup.

### Detail page (only needed for a pinned watchlist entry, not for discovery)
`GET <canonical product url>`. Price: `.product--price .price--content >
meta[itemprop="price"]@content` (decimal-point form, e.g. `4.99`) plus visible
`"4,99 €"`. ISBN: `.entryTextAdditional` after an `ISBN` label. Breadcrumb:
`.breadcrumb--link`. Article no.: `Artikel-Nr.: SW…`. No `ld+json`, no struck
price. (Note the detail page also embeds cross-sell `.product--box` tiles for
*other* products — scope your selectors to the main `#detail` / `.product--detail`
region if you ever parse it.)

---

## 6. Two-tier deal logic — feasibility

ADR 0005 §4c defines: **strong deal** = current price `< strong_deal_max_cents`
(no discount check) — **feasible**, just read the tile price. **deal** =
`5–9,99 €` **and** genuinely discounted, evidenced *either* by a struck
`original_price_cents` *or* by a ≥ `min_discount_pct` drop vs the previous
Observation.

- The **struck-price evidence is not available** — beam-shop never renders one.
  So `observation.original_price_cents` is always `NULL` for `source = beam`.
- The **price-drop-vs-previous-Observation evidence is available** and is the only
  way the "deal" tier can fire for this source. It needs ≥ 2 Observations of the
  same `(beam, product_id)`, so the tier is naturally dormant on first sight and
  becomes usable once history exists.
- Net: implement the "deal" tier for beam using only the previous-Observation
  delta; drop / short-circuit the struck-price branch. "strong deal" works fully.
  Prices do move (e.g. *Die letzte Einheit* full 14,99 € vs its single episodes at
  0,99 €; catalogue titles at 4,93–7,17 €), so drop detection is worthwhile.

---

## 7. Bot detection / politeness

- `robots.txt`: leading `Crawl-delay: 3`; explicit `Disallow: /` blocks **only**
  named crawlers (AhrefsBot, SemrushBot, BLEXBot, Baiduspider, MJ12Bot,
  meta-external*, …). No blanket `User-agent: *` disallow of the storefront; the
  category/search/author paths used here are not disallowed for a normal client.
- **No Cloudflare, no bot-management JS, no captcha, no `429`/challenge** observed
  across ~40 rapid `fetch()` calls in testing.
- Varnish sits in front but listing pages set a session cookie ⇒ served from
  backend (`X-Cacheable: NO`). Pages are ~150–1100 KB of HTML each.
- Recommendation: browser-like `User-Agent`, `Accept-Language: de-DE`, sequential
  requests ≤ ~1/s (honour the advertised crawl-delay of 3 s if being
  conservative), no parallel fan-out. Cache within a Run. Pin resolved product
  URLs (ADR 8) so steady-state traffic is a handful of requests.

---

## 8. Concrete request recipes

```
# check(entry): resolve + read price
GET /search?sSearch=<title>%20<author>&n=48
  → parse tiles (§5), match (ADR 8), pin product_id + url.

# by_author(author) — curated (~30 names)
GET /autor-innenwelt/<vorname-nachname-with-dots>/?p=1..data-pages
  → every tile is this author; read title/author/price/id.

# by_author(author) — general
GET /search?sSearch=<author>&n=100&p=1..
  → keep tiles whose .product--author matches; expect noise.

# genre new-arrivals (per configured category path, ADR 11)
GET /belletristik/science-fiction/space-opera/?o=1&p=1
GET /belletristik/science-fiction/space-opera/?o=1&p=2 ...
  → dedupe tiles by product_id, diff vs prior Observations,
     stop when a whole page is already-seen.
  Category paths + ids: §4b.
```

### Known category ids (for reference / `getCategory` flyout)
`belletristik 232 · science-fiction 233 · space-opera 245 · krimi-thriller 258 ·
horror-mystery 267 · autor-innenwelt(landing) 609 · autor-innenwelt/andreas-brandhorst 611 ·
autor-innenwelt/john-scalzi 614 · specials/gratis 366 · specials/booktok-ebooks 975`.
(Others: fetch the page and read `.listing@data-categoryid`.)
