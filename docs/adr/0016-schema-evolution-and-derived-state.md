# 16. Schema evolution and derived-state tables

## Context

Two problems surfaced once Phase 1 ran against real data.

**The store could not change shape.** SQLAlchemy's `create_all` adds missing
tables but never touches an existing one, so a new column on a live
`snapshots.db` would simply not appear and every query touching it would fail.
The documented remedy was "delete the database", which throws away the price and
availability history the whole tool exists to accumulate.

**Deriving the seeded discovery scopes did not scale.** `suppress_unseeded`
(ADR 11) needs to know which `(source, match_reason, category)` scopes have been
seen before. Deriving that with a `DISTINCT` over the Observation history costs a
full table scan on every Run. Measured against a simulated three years of daily
runs — 175,200 rows, 25 MB — that query took **1,253 ms** and grows linearly. A
covering index brought it to 48 ms but still grows; the storage itself was never
the problem, and `latest_observations` stayed at 0.1 ms throughout thanks to its
index.

## Decision

**Schema versioning with SQLite's own `PRAGMA user_version`.** `MIGRATIONS[n]`
upgrades a database at version `n` to `n + 1`. A database created from scratch is
stamped at the current version and skips them all, because `create_all` has
already built the finished schema. A database at a *higher* version than this
program knows is refused rather than written to. Migration steps are idempotent
(`add_column` checks `PRAGMA table_info` first) so a half-applied upgrade is safe
to re-run. SQLite 3.25+/3.35+ supports `RENAME COLUMN` and `DROP COLUMN`, so no
table-rebuild dance is needed.

**Not Alembic — yet.** It would add a dependency, an `alembic.ini`, an `env.py`,
a `versions/` tree and a CLI step per change. While the store holds nothing but a
rebuildable Snapshot and the configuration lives in YAML (ADR 10), thirty lines
are the cheaper trade. This is worth revisiting when Phase 2 moves the Profile
and the Watchlist *into* the database: at that point the contents stop being
reproducible and the schema starts churning, which is exactly where autogenerate
earns its keep. Alembic can baseline an existing schema, so nothing is foreclosed.

**A `seeded_scope` table instead of a derived query.** Seeded scopes are recorded
as they are seen. There is only ever a handful, so the cost is constant
(**0.12 ms**) rather than proportional to history. Migration 0 backfills the
table from existing Observations.

The Snapshot stays append-only (ADR 5). Not appending unchanged rows would keep
the table smaller, but 25 MB per three years is not a problem worth changing the
model for.

## Consequences

- History survives schema changes; `snapshots.db` is no longer disposable.
- Each schema change needs a migration function appended to `MIGRATIONS` —
  append only, never reorder, and a migration must keep doing what it did when it
  was written even as the code around it moves on. The backfill therefore spells
  out its match reasons rather than importing the enum.
- Verified on a real pre-upgrade database: without the backfill the first Run
  after the upgrade would have reported **163** already-known titles as new
  arrivals; with it, zero.
