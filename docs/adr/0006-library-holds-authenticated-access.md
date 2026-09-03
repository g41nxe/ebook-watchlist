# 6. Library Holds and Authenticated Access

## Status

**v1: deferred.** v1 stays entirely login-free. Hold tracking ("notify when my
Vormerkung is ready") is planned for **v2** using the authenticated design below.

## Context

Public availability data ("verfügbar ab <date>", Vormerker count) is a poor proxy
for "your turn has come". A reliable "hold ready" signal requires reading the
user's own library account, which needs login.

The risks of authenticated scraping — brittle login/session handling, the
clearest ToS breach in the design, and a real chance of the library card being
flagged or blocked by DiViBib abuse detection — are not worth taking on for v1.
Everything else in the tool works without it.

## Decision

- **v1:** no credentials, no login. Library checks are public-page only. The
  `not-available -> available` transition still works for titles that are not
  permanently hold-gated.
- **v1 data model:** `watchlist_entry.hold_state` and `hold_expected_date`
  columns are created but unused (cheap forward-compatibility, same treatment as
  `genres` / `no_gos`).
- **v2 (planned):** authenticated account scraping —
  - per-Profile VÖBB card number + password; OS keyring, else a `secrets` file
    outside git (`chmod 600`); never entered through the assistant;
  - `LibrarySource.check_holds(credentials) -> list[HoldObservation]`;
  - reported transition `placed -> ready`, plus wait estimate / queue position;
  - login <= 1x/day, hard stop on any auth error, config kill-switch, honest
    identifying User-Agent;
  - preceding research spike on the VÖBB login/session flow (captcha? 2FA?);
    if brittle, fall back to a manual hold hint in the UI rather than public
    auto-detection.

## Consequences

- v1 is legally and technically simpler and cannot get the library card blocked.
- The "hold ready" notification is not available until v2.
- v2 adds a managed secret on the host.
