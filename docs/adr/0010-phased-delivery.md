# 10. Phased Delivery

> **Nachtrag:** Phase 2s Datenmodell steht in **ADR 18**. Der Satz „YAML
> drops to import-only" gilt für Watchlist und Profil, nicht für den
> Leseprofil-Maßstab (ADR 17).

The tool is built in two phases against one architecture.

## Context

Scope grew well beyond the spec's "cron script + digest". Building the web UI
before the scrapers have run against reality risks committing UI code to shapes
that turn out wrong, and delays any working tool.

## Decision

- **Phase 1 — headless core.** Source implementations + matcher + SQLite store +
  Run entrypoint (cron / CLI) + text Digest. Fully automated, no web UI.
  "Needs attention" cases (unresolved entries, Source errors) go into the Digest
  and a CLI listing.
- **Phase 2 — web UI.** FastAPI + Jinja + HTMX on the same database: Dashboard,
  Watchlist editor, Profile editor, "Run now". No change to the Phase 1 core;
  the UI is a presentation and editing layer.
- ADR 3 (web UI) and ADR 4 (triggers) still hold; the "Run now" button and the
  `ui` trigger simply arrive in Phase 2.
- **Phase 1 Digest output:** written as `digest-<date>.md` to a configured
  directory **and** echoed to stdout (so cron mail and on-disk history both
  work).
- **Phase 1 config:** `watchlist.yaml` + `profile.yaml` are the source of
  truth. SQLite in Phase 1 holds only Observations and Runs. No config CLI.
- **Phase 2 config:** introduce the `profile` / `watchlist_entry` tables, do a
  one-time import from the YAML files, and the web UI owns config from then on
  (ADR 5's end state). YAML drops to import-only. A CLI is added later only if
  a headless server actually needs one.

## Consequences

- A usable, cron-driven tool exists at the end of Phase 1.
- The scrapers and matcher are exercised against real sites before UI code
  depends on their behaviour.
- Phase 1 config editing is done in the Seed YAML / directly in SQLite until the
  Phase 2 editors exist.
