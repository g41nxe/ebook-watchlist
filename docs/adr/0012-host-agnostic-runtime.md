# 12. Host-Agnostic Runtime

Developed and run on the user's Windows PC now; deployable to the home Linux Pi
later with no code changes.

## Context

The user wants to run locally on Windows for now and move to the regular home Pi
(a roomier Pi, not the Zero W) later. Neither phase should hard-wire an OS.

## Decision

- **Entrypoint:** `python -m ebook_watchlist.run`. Scheduling is external and
  documented for both targets: Windows Task Scheduler now, cron or a
  systemd-timer on the Pi. No code assumes cron.
- **Paths:** `pathlib` only, no POSIX literals.
- **Data directory:** `./data/` in the repo, gitignored, overridable via
  `EBW_DATA_DIR`. Holds `snapshots.db`, `digests/`, and in Phase 1
  `watchlist.yaml`, `profile.yaml`, `dismissed.yaml`.
- **Dependencies:** cross-platform only — `requests`, `beautifulsoup4`,
  `rapidfuzz`, `filelock`, `pyyaml`; Phase 2 adds `fastapi`, `uvicorn`,
  `jinja2`, `sqlalchemy`. `uv` on both hosts.
- **Locking:** `filelock` (cross-platform) for the Run lock (ADR 4).
- **Time:** local time; note DST in the schedule docs.
- **Migration to Pi:** copy the repo, `uv sync`, copy or re-seed `data/`, add a
  systemd-timer. No build step.

> **Nachtrag (ADR 20):** Für die Weboberfläche gilt der letzte Satz nicht mehr.
> `uv run python -m ebook_watchlist.web.build` erzeugt Stylesheet und
> Bibliotheken; das Ergebnis liegt nicht im Repository. Der Lauf selbst braucht
> weiterhin nichts davon.

## Consequences

- The scheduler is a per-host setup step, documented in the README, not shipped.
- `./data/` in the repo keeps everything portable in one directory.
