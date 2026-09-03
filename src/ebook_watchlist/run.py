"""The single entrypoint: ``python -m ebook_watchlist.run`` (ADR 4, ADR 12).

Cron, the CLI, and later the UI's "Run now" button all land here. There is no
scheduler inside — the host's scheduler decides *when*, this decides *what
changed*.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from filelock import FileLock, Timeout

from . import paths
from .config import ConfigError, load_profile, load_watchlist
from .diff import compute_deltas, keys_of
from .digest import build_digest
from .models import Observation, SourceFailure
from .render import render_html, render_text
from .sources import build_sources
from .store import Store

EXIT_OK = 0
EXIT_ALREADY_RUNNING = 0
EXIT_CONFIG_ERROR = 2
EXIT_SOURCE_FAILURE = 1


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="ebw", description="Run one check cycle.")
    parser.add_argument(
        "--trigger",
        default="cli",
        choices=["cli", "cron", "ui"],
        help="what fired this Run; recorded on the run row",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="override the data directory for this invocation",
    )
    return parser.parse_args(argv)


def _collect(sources, profile, watchlist) -> tuple[list[Observation], list[SourceFailure]]:
    """Poll every Source. One failing Source does not stop the others (ADR 7)."""
    observations: list[Observation] = []
    failures: list[SourceFailure] = []
    for source in sources:
        try:
            observations.extend(source.collect(profile, watchlist))
        except Exception as exc:  # noqa: BLE001 - deliberate: isolate one Source
            failures.append(
                SourceFailure(source=source.name, message=f"{type(exc).__name__}: {exc}")
            )
    return observations, failures


def _write_html(digest, generated_at: datetime) -> Path:
    directory = paths.digests_dir()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"digest-{generated_at:%Y-%m-%d}.html"
    target.write_text(render_html(digest), encoding="utf-8")
    return target


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.data_dir is not None:
        os.environ["EBW_DATA_DIR"] = str(args.data_dir)

    try:
        profile = load_profile()
        watchlist = load_watchlist()
        sources = build_sources(profile)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    paths.data_dir().mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(paths.lock_path()), timeout=0)
    try:
        lock.acquire()
    except Timeout:
        print("another Run is already in progress — exiting", file=sys.stderr)
        return EXIT_ALREADY_RUNNING

    try:
        return _run(profile, watchlist, sources, trigger=args.trigger)
    finally:
        lock.release()


def _run(profile, watchlist, sources, *, trigger: str) -> int:
    store = Store(paths.db_path())
    started_at = datetime.now()
    run_id = store.start_run(profile.slug, trigger, started_at)

    observations, failures = _collect(sources, profile, watchlist)
    previous = store.latest_observations(profile.slug, keys_of(observations))
    deltas = compute_deltas(observations, previous)

    store.append(run_id, profile.slug, observations, started_at)

    last_run = store.last_finished_run(profile.slug, run_id)
    digest = build_digest(
        profile_name=profile.name,
        generated_at=started_at,
        since=last_run.started_at if last_run else None,
        deltas=deltas,
        failures=failures,
    )

    finished_at = datetime.now()
    status = "error" if failures else "ok"
    store.finish_run(
        run_id,
        status=status,
        delta_count=len(deltas),
        finished_at=finished_at,
        error="; ".join(f.message for f in failures) or None,
    )

    # Nothing changed and nothing broke — stay quiet.
    if digest.is_empty:
        return EXIT_OK

    print(render_text(digest))
    _write_html(digest, started_at)
    return EXIT_SOURCE_FAILURE if failures else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
