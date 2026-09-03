# 15. Digest Rendering and Run Cadence

## Context

Phase 1 has no web UI, so the Digest is the only output surface. It needs to read
well in a terminal / cron mail and also as a browsable file, and Phase 2's
Dashboard should not re-implement it.

## Decision

### Rendering

- The Run produces a structured **`Digest`** model: ordered sections
  (Bibliothek, Watchlist - Preise, Neue Titel deiner Autor:innen,
  Genre-Vorschläge (unsicher), Fehler - always last), each with typed entries
  (title, author, price, prior price, flag, link, status). Empty sections
  omitted.
- Two renderers over that model:
  - **text** -> stdout / cron logs;
  - **HTML** -> `data/digests/digest-<date>.html`, and HTML email later.
- Markdown is not produced.
- Phase 2's Dashboard renders the same model with shared HTML partials.
- An error-only Digest still renders; fully silent only when no Deltas and no
  errors.

### Cadence

- **Once per day**, time configurable, default ~06:00 local. Windows Task
  Scheduler now; cron / systemd-timer on the Pi.
- Every Run: all Watchlist entries, library checks, `core` Reference Authors,
  genre categories.
- `extended` Reference Author list: **weekly** (configurable day), to keep the
  daily Run short.
- No intraday runs in v1. Manual runs available any time.

## Consequences

- One Digest implementation serves Phase 1 output and Phase 2 Dashboard.
- Daily Run stays short; the long author sweep is amortised weekly.
