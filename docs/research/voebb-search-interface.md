# VÖBB Onleihe — Search & Availability Interface (Research Spike)

Research for ADR 9 (VÖBB entry resolution) and ADR 7 (`LibrarySource`).
Investigated 2026-09-03/04 against the live site.

- **Instance base:** `https://voebb.onleihe.de/berlin/`
- **Frontend path:** `https://voebb.onleihe.de/berlin/frontend/`
- **Software:** DiViBib "Onleihe" **Version 2024.09**, build `06edafa`. Plain
  Apache Tomcat 9 (no CDN/WAF in front — see "Bot defense" below).
- **Consortium note:** The VÖBB Onleihe catalogue is frozen — a site banner
  states no new acquisitions are being added. Good for us: the catalogue and
  markup are unlikely to churn.

---

## TL;DR / RECOMMENDATION

**Build the `LibrarySource` on the server-rendered HTML search + detail pages,
scraped with `requests` + BeautifulSoup (`lxml`).** There is **no** JSON API,
**no** OpenSearch endpoint, and **no** autocomplete/suggest service on this
instance — HTML is the only machine interface, and it is fully static
(server-side rendered, no JS needed to see results or availability).

Concretely:

1. **Search (free-text, title + author in one box):**
   `GET https://voebb.onleihe.de/berlin/frontend/search,0-0-0-0-0-0-0-0-0-0-0.html`
   `?cmdId=703&sK=1000&pText=<title>+<author-lastname>&pMediaType=-1`
   The form is declared `method="post"` but the endpoint honours **GET** with
   the same params — use GET (cacheable, no body, no session needed for page 1).

2. **Parse the results list** for candidate `(title, author, medium, detailUrl)`
   tuples, rank with the Calibre-informed matcher (ADR 8), pin the winning
   `mediaInfo,…` URL on the entry.

3. **Availability** = fetch the pinned `mediaInfo,…` detail page and read the
   **Exemplarinformationen** block (`.exemplar-count` / `.availability-count` /
   `.reservation-count`). No login required (confirmed).

**Risks:** (a) `pText` is a single relevance-ranked box — no fielded
title/author search exists on this theme, so ranking must tolerate loose
matches; (b) pagination beyond page 1 works statelessly only if you re-supply
the query in the URL (details below); (c) hCaptcha JS is present site-wide and
DiViBib is known to gate suspected bots — obey ADR 7 politeness (2–4 s serial,
hard stop on 429) and set a descriptive `User-Agent` with contact info.

---

## 1. The search form

From the welcome page (`welcome,51-0-0-100-0-0-1-0-0-0-0.html`) and every
results page, the only search UI is a single free-text box:

```html
<form class="searchInput" method="post"
      action="search,0-0-0-0-0-0-0-0-0-0-0.html">
    <input type="hidden" name="cmdId" value="703"/>
    <input type="hidden" name="sK"    value="1000"/>
    <input type="search"  name="pText" placeholder="Suche"/>
    <select name="pMediaType" id="mediatype">
        <option value="-1">alle Medien</option>
        <option value="400001">eBook</option>
        <option value="400002">Hörbuch</option>     <!-- eAudio -->
        <option value="400006">ePaper</option>
        <option value="400005">eMagazine</option>
        <!-- also: eLearning, Hörspiel, eVideo -->
    </select>
    <button type="submit" name="Suchen" value="Suchen">Suchen</button>
</form>
```

### Parameters

| Param        | Value used                    | Meaning |
|--------------|-------------------------------|---------|
| `cmdId`      | `703`                         | "new search" command. Required. |
| `sK`         | `1000`                        | Search-context key. Hard-coded in the form; echoed into pagination URLs. Send `1000`. |
| `pText`      | `Die sieben Schwestern Riley` | The query. Space-separated words; `+`/`%20` encoded. Relevance-ranked, **not** strict AND (see §2). |
| `pMediaType` | `-1`                          | `-1` = all media. Or a single type id from the table above. We want `-1` and filter client-side by medium. |

### Method: GET works

The form says POST, but

```
GET /berlin/frontend/search,0-0-0-0-0-0-0-0-0-0-0.html?cmdId=703&sK=1000&pText=Die+sieben+Schwestern&pMediaType=-1
```

returns HTTP 200 with the full results HTML, **no cookie required**. Verified
repeatedly. Use GET.

### Query behaviour — important for the matcher

`pText` is a **single relevance-ranked full-text field** across title + author +
subtitle + blurb. There is **no** "Erweiterte Suche" / fielded title vs. author
search on this Onleihe theme (checked the welcome page, the results page, and
the loaded JS — none exists).

Observed:

| Query (`pText`)                | Result |
|--------------------------------|--------|
| `Die sieben Schwestern`        | 49 Titeltreffer, series #1 is hit 1 |
| `Der Distelfink Tartt`         | 2 Titeltreffer (title + author words together narrow well) |
| `Verity Hoover`                | 3 Titeltreffer |
| `Dead Silence Barnes`          | 0 — true negative (title not in VÖBB) |
| `Dead Silence`                 | 0 |
| `Project Hail Mary Weir`       | 0 — true negative |

Take-aways for resolution:
- Sending `"<title> <author-lastname>"` in one `pText` is the right call — it
  tightens results without needing fielded search.
- English-language titles are frequently genuinely absent (VÖBB is
  predominantly German; tiny "Engl. eBooks von B&T" section). A 0-hit result is
  a legitimate "not found" → `LibrarySource.check` returns `None`, not raise.
- Because ranking is loose, the matcher must compare each candidate's parsed
  title/author against the entry and apply the ADR 9 confidence gate; do not
  assume hit #1 is correct.

---

## 2. Results page — structure & selectors

Server-rendered static HTML. `Content-Type: text/html`. No XHR/fetch, no JSON.
Confirmed by fetching with plain `curl` (no JS engine) and getting the complete
list.

### Page-level

- **Result count / "not found":** the `<title>`, the `<h1 class="hidden">`, and
  the active breadcrumb all contain one of:
  - `… ergab 49 Titeltreffer. S. 1 (1 bis 20)` — parse the integer before
    `Titeltreffer` for the total; `S. N (a bis b)` is the page window.
  - `… ergab keine Titeltreffer` — zero hits. Also rendered as a body block:
    ```html
    <div class="alert alert-info" role="alert">
      Ihre Suchanfrage „<q>“ ergab leider keine Treffer. …
    </div>
    ```
  - Session lost (see pagination): `… Ihre Sitzung ist abgelaufen! Bitte
    versuchen sie es erneut.`
- **Broken-parser guard (ADR 7):** if `Titeltreffer` count > 0 but zero
  `[test-id='mediaCard']` nodes parse → raise "structure changed".

### One result item

Container: `section.row.row-cols-1 > div.col.card-group > div.card[test-id='mediaCard']`

```html
<div class="card shadow-sm h-100" test-id='mediaCard'>
  <img test-id='cardImage' src="https://static.onleihe.de/images/…/tn…s.jpg">

  <p test-id='cardAuthor'><small><a href="simpleMediaList,0-0-373164461-103-…-0.html">
      Riley, Lucinda</a></small></p>

  <h3 class="headline card-title truncate2Lines" test-id='cardTitle'>Die sieben Schwestern</h3>
  <h4 class="headline card-subtitle …"          test-id='cardSubTitle'>Roman - Die sieben Schwestern 1</h4>

  <!-- link to detail page (appears 2× per card: stretched-link on title and on the icon col) -->
  <a class="link stretched-link"
     href="mediaInfo,0-0-373164461-200-0-0-0-0-0-0-0.html"
     test-id='mediaInfoLink' title="zum Titel: …"></a>

  <!-- medium/format icon -->
  <svg class="icon ic_ebook" test-id="ic_ebook"><use xlink:href="#ic_ebook"></use></svg>

  <p test-id='cardAbstract'>Der Anfang der Geschichte …</p>
  <small test-id="cardInsertDate"><b>Im Bestand seit:</b> <span>01.05.2015</span></small>

  <!-- AVAILABILITY (two shapes, see below) -->
  …

  <!-- action button (mutually exclusive) -->
  <a href="mediaInfo,0-0-373164461-200-…-0.html"
     class="btn btn-secondary fw-bold" test-id='setMarkerButton'
     title="Vormerker setzen">Vormerker setzen</a>
</div>
```

### Selector cheat-sheet (results card)

| Field           | Selector | Notes |
|-----------------|----------|-------|
| Card            | `[test-id="mediaCard"]` | iterate these |
| Title           | `[test-id="cardTitle"]` (text) | |
| Subtitle/series | `[test-id="cardSubTitle"]` (text) | e.g. `Roman - Die sieben Schwestern 1` |
| Author          | `[test-id="cardAuthor"]` (text) | `Nachname, Vorname`; multiple authors `;`-joined |
| Detail URL      | `a[test-id="mediaInfoLink"]` → `href` | relative to `…/berlin/frontend/`; form `mediaInfo,0-0-<ID>-200-0-0-0-0-0-0-0.html` |
| Medium/format   | `svg[test-id^="ic_"]` inside the card's right column → read the `test-id` / class | `ic_ebook`, `ic_eaudio`, `ic_epaper`, `ic_emagazine`, `ic_evideo`, `ic_elearning`, `ic_ehoerspiel` |
| Availability    | `[test-id="cardAvailability"]` (+ `[test-id="cardLabelAvailability"]`) | see next |
| Action button   | `[test-id="mediaLendButton"]` XOR `[test-id="setMarkerButton"]` | primary vs secondary state |

### Availability on the results card — two shapes

**Available now:**
```html
<small class="text-muted" test-id="cardAvailability"><p>Verfügbar</p></small>
<!-- and: -->
<a class="btn btn-primary fw-bold" test-id='mediaLendButton'
   title="Jetzt ausleihen">Jetzt ausleihen</a>
```

**Not available (forecast date):**
```html
<b class="pe-2" test-id='cardLabelAvailability'>Voraussichtlich verfügbar ab:</b>
<span test-id='cardAvailability'>18.12.2026</span>
<!-- and: -->
<a class="btn btn-secondary fw-bold" test-id='setMarkerButton'
   title="Vormerker setzen">Vormerker setzen</a>
```

Rule: presence of `[test-id="mediaLendButton"]` / text `Verfügbar` with **no**
`cardLabelAvailability` ⇒ available. Presence of
`[test-id="cardLabelAvailability"]` with label `Voraussichtlich verfügbar ab:`
⇒ not available, and the sibling `[test-id="cardAvailability"]` holds a
`DD.MM.YYYY` date. `[test-id="setMarkerButton"]` corroborates "not available".

The results card does **not** show copy/reservation counts — only the detail
page does. For a watchlist we should pin the detail URL and read the detail
page anyway (§4), so the card availability is just a bonus / sanity check
during resolution.

### Sort & page-size controls (not needed, documented for completeness)

- Sort: a `<form>` posting to `search,0-0-0-700-0-0-0-1000-0-0-0.html` with a
  `<select>` (`Relevanz`, `… absteigend`, `Erscheinungsdatum …`).
- Page size: `<form id="pagehits-form" method="post"
  action="search,0-0-0-700-0-0-0-1000-0-0-0.html">` with
  `<select name="elementsPerPage">` options `10 / 20 / 50 / 70 / 100`
  (default 20). This is POST + session-backed; a bare
  `&pMod=100` on the GET search URL did **not** change page size. If you want
  100/page you likely need the stateful POST (cookie jar). Simpler: just walk
  pages (§3) — resolution only ever needs the first 1–2 pages.

---

## 3. Pagination

Results paginate 20/page. Nav markup:

```html
<nav id="pagination" aria-label="Seiten Pagination">
  <ul class="pagination">
    <li class="page-item active"><a test-id='pagination_1' href="#">1</a></li>
    <li class="page-item"><a test-id='pagination_2' href="search,0-0-0-700-0-0-1-1000-0-0-0.html">2</a></li>
    <li class="page-item"><a test-id='pagination_3' href="search,0-0-0-700-0-0-2-1000-0-0-0.html">3</a></li>
    <li class="page-item"><a test-id='pagination_weiter' href="search,0-0-0-700-0-0-1-1000-0-0-0.html">weiter</a></li>
  </ul>
</nav>
```

URL shape: `search,0-0-0-700-0-0-<pageIndex0>-1000-0-0-0.html`
- 4th numeric slot `700` = "paged results" command (vs `703` = new search).
- 7th slot = **0-based page index** (`0` = page 1, `1` = page 2, …).
- 8th slot = `sK` = `1000`.

### Stateful vs stateless

- **As emitted (bare href, no query):** requires the JSESSIONID cookie from the
  original search request. Fetching it cold returns
  *"Ihre Sitzung ist abgelaufen"*. So: either keep a `requests.Session` /
  cookie jar and follow the hrefs verbatim, **or**
- **Stateless (recommended):** re-append the original query params to the paged
  path:
  ```
  GET /berlin/frontend/search,0-0-0-700-0-0-1-1000-0-0-0.html
      ?cmdId=703&sK=1000&pText=Die+sieben+Schwestern&pMediaType=-1
  ```
  Verified: returns `S. 2 (21 bis 40)` correctly with **no cookie**. Increment
  the 7th path slot for further pages.

For entry resolution you normally only read page 1 (top candidates). Cap at
~2 pages.

---

## 4. Title detail page (`mediaInfo`)

### URL pattern

```
https://voebb.onleihe.de/berlin/frontend/mediaInfo,0-0-<TITLE_ID>-200-0-0-0-0-0-0-0.html
```

`<TITLE_ID>` is the integer from the results `mediaInfoLink` (e.g. `373164461`).
The `-200-` slot is the "media info" view command. Store the whole relative
path on the entry (ADR 8 pinned link); prefix with `…/berlin/frontend/`.

`Content-Type: text/html`, HTTP 200, **no login, no cookie required**
(confirmed with plain `curl`). ~58 KB, fully server-rendered.

### Bibliographic fields

Each is a `<p class="horizontalDescription"> <b class="pe-2">LABEL:</b>
<span>VALUE</span> </p>`. Match on the **label text**:

| Label (`<b>` text)            | Example value |
|-------------------------------|---------------|
| `Autor*in:`                   | `Riley, Lucinda;` (link; `;`-joined for multiple) |
| `Reihe:`                      | `Die sieben Schwestern` |
| `Jahr:`                       | `2015` |
| `Sprache:`                    | `Deutsch` |
| `Umfang:`                     | `576 S.` (eBook) |
| `Dauer:`                      | `xx:xx Std.` (eAudio) |
| `Max. Ausleihdauer:`          | `21 Tage` |
| `Voraussichtlich verfügbar ab:` | `18.12.2026` (only when unavailable) |

Title: `<h3 class="headline title-name" test-id='cardTitle'>…</h3>`
Subtitle/series line: `<h4 class="headline subtitle">…</h4>`
Medium: nav tab `<p class="float-end … eaudio">Hörbuch</p>` / an identifier
table row `<td>eAudio:</td>`, plus `svg[test-id="ic_eaudio"]`.

### Availability — the reliable signal: "Exemplarinformationen"

```html
<h3 class="headline">Exemplarinformationen</h3>

<div class="exemplar-count mb-1">
    <svg class="icon ic_ebook" test-id="ic_ebook">…</svg>
    5
    Exemplare
</div>
<div class="availability-count mb-1">
    <svg class="icon ic_checkmark ic_small" test-id="ic_checkmark">…</svg>
    5
    Verfügbar
</div>
<div class="reservation-count mb-1">
    <svg class="icon ic_bell ic_small" test-id="ic_bell">…</svg>
    0
    Vormerker
</div>
<div class="lending-duration">
    <p><b>Max. Ausleihdauer:</b> <span>21 Tage</span></p>
</div>
```

| Selector             | Meaning | Parse |
|----------------------|---------|-------|
| `.exemplar-count`    | total licensed copies | leading integer in the element's text |
| `.availability-count`| copies **available right now** | leading integer |
| `.reservation-count` | active reservations (Vormerker) | leading integer |

**Derived state:**
- `availability-count >= 1` → **available** ("Verfügbar").
- `availability-count == 0` → **not available**; queue length =
  `reservation-count`; ETA = the `Voraussichtlich verfügbar ab:` date
  (`DD.MM.YYYY`) elsewhere on the page (may be absent if no forecast).

Text integers are surrounded by whitespace/newlines and an SVG — extract with
e.g. `re.search(r"\d+", el.get_text())`.

### Secondary availability text (less structured — use as fallback only)

In the left column near the subtitle:
- available: bare `<p>Verfügbar</p>` (no label).
- unavailable: `<p class="horizontalDescription"><b class="pe-2">Voraussichtlich
  verfügbar ab:</b> <span>18.12.2026</span></p>`.

There is **no** distinguishing wrapper class/id around this bare `<p>Verfügbar</p>`,
so prefer the `.availability-count` integer as the source of truth.

### Action links on the detail page (state hints, do not click)

| Selector / text | State |
|-----------------|-------|
| `test-id='buttonDownloadDropdown'` / `#dropdownLend…` / button text `Jetzt ausleihen` | available |
| `a[href^="mediaReserve,"]` text `Vormerken` | not available |
| `a[href^="myBib,"]` text `Auf den Merkzettel legen` | always present |
| `Leseprobe` → `reader.onleihe.de/#/read?url=…` | always present |

### Exact German strings seen (for reference / assertions)

```
Verfügbar
Voraussichtlich verfügbar ab: 18.12.2026
Exemplare
Vormerker
Vormerker pro Nutzer:
Max. Ausleihdauer: 21 Tage
Jetzt ausleihen
Vormerker setzen        (results card button)
Vormerken               (detail page link)
Im Bestand seit: 01.05.2015
… ergab 49 Titeltreffer. S. 1 (1 bis 20)
… ergab keine Titeltreffer
Ihre Suchanfrage „…“ ergab leider keine Treffer.
Ihre Sitzung ist abgelaufen! Bitte versuchen sie es erneut.
```

Worked example, `mediaInfo,0-0-373164461-…` ("Die sieben Schwestern", Riley),
fetched 2026-09: `4 Exemplare`, `0 Verfügbar`, `16 Vormerker`,
`Voraussichtlich verfügbar ab: 18.12.2026` → state = **not available**, queue 16.
And `mediaInfo,0-0-1474715999-…` ("Sieben Richtige", Jarck): `5 Exemplare`,
`5 Verfügbar`, `0 Vormerker` → **available**.

---

## 5. Login not required — confirmed

Every URL above (`search,…`, `mediaInfo,…`, paginated `search,…-700-…`) returns
full content — hits, bibliographic data, and the Exemplarinformationen
copy/reservation counts — over plain `curl` with **no session cookie and no
credentials**. Availability is entirely public. `check_holds` (personal holds)
is the only login-gated part and is explicitly v2 (ADR 6 / ADR 7).

---

## 6. Bot defense / rate-limiting signals

- **No Cloudflare / no WAF.** Response headers expose no `Server`, no `CF-*`,
  no `X-*` security headers. Just Tomcat 9 setting:
  - `Set-Cookie: JSESSIONID=…; Path=/berlin; Secure; HttpOnly`
  - `Set-Cookie: DVBLBROUTE=…` (load-balancer sticky route)
- **No `robots.txt`** — `https://voebb.onleihe.de/robots.txt` returns a generic
  divibib "Wartungsseite/404" HTML page, not a rules file. (No explicit crawl
  permission or prohibition; still crawl politely.)
- **hCaptcha is loaded site-wide:** every page includes
  `/berlin/static/js/hcaptcha-api-modified-7924fcbf.js`. It fronts the login
  form; DiViBib is also known to interpose an hCaptcha challenge on the search
  path when it flags a client as a bot (rapid/serial automated requests). A
  challenge page would break the parser → our ADR 7 broken-parser guard would
  raise loudly, which is the desired behaviour.
- **Cookie consent banner** is pure client-side JS (`privacyDiscardAll` /
  `privacyAcceptChoice` / `privacyAcceptAll` buttons). It does **not** gate
  server HTML — `curl` with no cookies gets full content. Ignore it for
  scraping. (In a real browser, choose "Alle ablehnen" for privacy.)
- **Mitigations (all already mandated by ADR 7):** serial requests only, fixed
  2–4 s delay, one retry with backoff on 5xx/timeout, **hard stop on HTTP 429**,
  descriptive `User-Agent` with contact info. Additionally: reuse one pinned
  detail URL per entry per Run (ADR 8) so a Run is ≈ N cheap GETs, and
  re-resolve (1 search + candidate reads) only on repeated fetch failure.
- **Observed while researching:** a browser-automation session repeatedly got
  redirected to `beam-shop.de` (DiViBib's "buy instead" partner). This was an
  artifact of the browser tooling/extension in the research environment, **not**
  reproducible with `curl`/server-side fetches of the same URLs — a
  `requests`-based client is unaffected. Noted so an implementer doesn't chase
  it.

---

## 7. Endpoints NOT found (so nobody re-checks)

- **No JSON/REST API.** No `application/json` anywhere, no `/api/`, no
  `*Fragment` AJAX partial, no `mediaList` JSON variant.
- **No OpenSearch.** No `<link rel="search" type="application/opensearchdescription+xml">`,
  no `search.xml`.
- **No autocomplete/suggest/typeahead endpoint.** `selectize.js` is loaded but
  only wired to the static facet-filter `<select>`s, not to an async
  suggestion service.
- **No fielded "Erweiterte Suche"** (separate title/author inputs) on the
  VÖBB `berlin` theme.

HTML scraping of `search,…` + `mediaInfo,…` is the interface. Build there.

---

## 8. Implementation notes for `LibrarySource`

- **Selector module (ADR 7 "one place per Source"):** keep every string above in
  a `selectors`/`strings` block — CSS selectors are `[test-id="…"]` +
  `.exemplar-count` / `.availability-count` / `.reservation-count`; German label
  literals (`Voraussichtlich verfügbar ab:`, `Verfügbar`, `Titeltreffer`, …)
  live beside them.
- **`doctor` probe (ADR 7):** hard-code a known-good query + title id.
  Suggested: `pText="Die sieben Schwestern"` must yield `Titeltreffer > 0` and a
  first card with a parseable `cardTitle` + `mediaInfoLink`; and
  `mediaInfo,0-0-373164461-200-0-0-0-0-0-0-0.html` must yield a parseable
  integer from `.exemplar-count` and `.availability-count`. (Don't assert the
  *values* — copies/queue change — assert the fields still parse.)
- **`check(entry)` flow:** GET pinned `mediaInfo` URL → parse
  `.availability-count` int → `>=1` ⇒ available; `0` ⇒ unavailable + queue
  (`.reservation-count`) + ETA date. Return the `AvailabilityObservation` with
  the raw scraped title/author too (ADR 9 consequence: makes wrong
  auto-resolves visible).
- **Resolution flow (ADR 9):** GET search URL (§1, GET form) → iterate
  `[test-id="mediaCard"]` → build candidates `{title: cardTitle,
  subtitle: cardSubTitle, author: cardAuthor, medium: ic_* class,
  url: mediaInfoLink href}` → matcher + confidence gate → pin URL. 0
  `mediaCard` **with** `keine Titeltreffer` in the title ⇒ `None` (not found,
  don't raise). 0 `mediaCard` **without** that marker ⇒ raise (structure
  changed).
- **URL resolution:** hrefs in the HTML are relative to
  `https://voebb.onleihe.de/berlin/frontend/`. `urljoin` against that base.
- **Encoding:** page is UTF-8; German umlauts in `pText` encode fine as UTF-8
  percent-encoding.
