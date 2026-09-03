#!/usr/bin/env sh
# Daily run for cron or a systemd timer.
set -eu
cd "$(dirname "$0")/.."
exec uv run python -m ebook_watchlist.run --trigger cron
