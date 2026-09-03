# 2. Python Stack

We will build v1 in Python.

## Context

The scrape targets (VÖBB Onleihe result pages, beam-shop.de) serve
server-rendered HTML. No JavaScript rendering is needed for the data we want.

## Decision

- Python 3.12+.
- `requests` for HTTP, `BeautifulSoup4` for parsing.
- `uv` for dependency and virtualenv management.
- No headless browser. Add Playwright only if a specific Source later proves to
  require JS rendering.

## Consequences

- Light dependency footprint, fast cold start, easy to run from cron.
- If a Source moves behind client-side rendering, that Source needs a separate
  fetch strategy.
