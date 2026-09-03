# 14. Test-Data Strategy

Scrapers and the matcher are tested offline against committed fixtures.

## Context

Scraper and matcher correctness cannot be verified by running the tool and
eyeballing output, and that approach catches no regressions.

## Decision

- **Saved-HTML fixtures** under `tests/fixtures/<source>/`: search result page,
  title/product detail page, category listing, an availability-changed variant,
  a "not found" page. `ebw doctor --dump` re-captures them when a site
  legitimately changes.
- **Parser tests** run against those fixtures with no network; assert exact
  extracted fields.
- **Matcher corpus** `tests/fixtures/matching.yaml`: labelled
  `(query, candidate, expect: match | no-match)` pairs covering the ADR 8 cases,
  including near-misses that must not match. Grows whenever a real mismatch is
  found.
- **One live smoke test** marked `@pytest.mark.live`, excluded from the default
  run, hitting each real site once for manual use.
- TDD: fixture + failing parser test first, then the parser.

## Consequences

- The default test suite is offline, fast, deterministic.
- Fixtures must be refreshed deliberately when a site changes; the diff shows
  what moved.
