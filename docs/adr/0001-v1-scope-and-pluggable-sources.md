# 1. v1 Scope and Pluggable Sources

v1 is a single-user personal tool that runs on a schedule, checks a small number
of Sources for changes relevant to one Profile, and emits a Digest only when
something changed.

## Context

The original spec named Amazon Kindle Deals as the shop source. That was dropped.
The VÖBB Onleihe currently adds no new titles, so library-side genre discovery
has nothing to match against.

## Decision

- **Library Source:** VÖBB Onleihe first. Job: detect when a Watchlist title
  changes to available/borrowable (including becoming free again after being
  lent out).
- **Shop Source:** beam-shop.de first. Jobs: (a) watchlist price-watch —
  report price drops / threshold crossings for Watchlist titles; (b)
  profile-author discovery — surface new or discounted titles whose author is on
  the Profile's reference-author whitelist.
- **Out of v1:** Amazon; LLM genre *classification* of unknown-author titles;
  automatic purchases; other library systems. (Library holds: deferred to v2,
  ADR 6. Category-based genre *discovery* is in v1 via ADR 11 — a small curated
  set of shop categories, no classifier.)
- **Architecture:** Sources are pluggable behind a `library` / `shop` interface.
  Adding a Source must not require core changes.
- **Storage/runtime:** cron-driven, no auth, no hosted database. (The
  flat-files / no-UI part of this decision is superseded by ADR 3 and ADR 4:
  SQLite is the store and a local web UI is in v1.)
- The Profile is a keyed first-class entity; the model supports multiple
  Profiles though v1 ships one.
- **German-language literature is the deliberate focus.** Consequence
  (beam-shop research): German ebooks are under fixed-book-price law, so
  beam-shop shows no struck prices and real discounts are rare/shallow. The
  shop side is accepted as discovery + new-release awareness + "strong deal"
  (absolute price) alerts; the "deal" (discount) tier is expected to fire
  rarely. No non-fixed-price / English-language shop is planned.

## Consequences

- The shop side needs no LLM cost or prompt tuning in v1.
- "New passende Titel" from the library is not delivered in v1.
- A second shop or library can be added later as a new Source implementation.
