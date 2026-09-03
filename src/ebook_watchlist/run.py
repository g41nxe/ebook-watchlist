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
from datetime import datetime, timedelta
from pathlib import Path

from filelock import FileLock, Timeout

from . import paths
from .config import ConfigError, load_dismissals, load_profile, load_watchlist
from .diff import compute_deltas, keys_of, suppress_unseeded
from .digest import build_digest
from .http import HttpClient, build_user_agent
from .models import Observation, SourceFailure
from .render import render_html, render_text
from .sources import build_sources
from .sources.base import RunContext
from .store import Store

EXIT_OK = 0
EXIT_ALREADY_RUNNING = 0
EXIT_CONFIG_ERROR = 2
EXIT_SOURCE_FAILURE = 1

EXTENDED_SWEEP_KEY = "last_extended_sweep"
#: Past this, the weekly sweep happens on the next Run whatever day it is.
EXTENDED_SWEEP_OVERDUE = timedelta(days=7)


def _survive_a_narrow_console() -> None:
    """Never lose a whole Run's Digest to a console that cannot render an arrow.

    Windows still hands us a cp1252 stdout, which raises on "→" and on the
    warning sign in the error heading. The HTML digest is always written in full
    UTF-8; this only softens what the terminal gets.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="replace")
        except (ValueError, OSError):  # pragma: no cover - stream not reconfigurable
            pass


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="ebw", description="Run one check cycle.")
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "doctor"],
        help="'run' checks everything; 'doctor' only asks each Source whether it still parses",
    )
    parser.add_argument(
        "--skip-probes",
        action="store_true",
        help="do not self-check the Sources before the Run",
    )
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


def _probe(sources) -> tuple[list, list[SourceFailure]]:
    """Ask every Source whether its parsers still recognise a known-good page.

    A Source that fails here is sat out for the Run: half-reading a redesigned
    site would write nonsense into the Snapshot and quietly poison every future
    diff (ADR 7).
    """
    healthy, failures = [], []
    for source in sources:
        try:
            source.probe()
        except Exception as exc:  # noqa: BLE001 - deliberate: isolate one Source
            failures.append(
                SourceFailure(
                    source=source.name,
                    message=f"Selbsttest fehlgeschlagen — {type(exc).__name__}: {exc}",
                )
            )
        else:
            healthy.append(source)
    return healthy, failures


def _collect(
    sources, profile, watchlist, context: RunContext
) -> tuple[list[Observation], list[SourceFailure]]:
    """Poll every Source. One failing Source does not stop the others (ADR 7)."""
    observations: list[Observation] = []
    failures: list[SourceFailure] = []
    for source in sources:
        try:
            observations.extend(source.collect(profile, watchlist, context))
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
    _survive_a_narrow_console()
    args = _parse_args(argv)
    if args.data_dir is not None:
        os.environ["EBW_DATA_DIR"] = str(args.data_dir)

    try:
        profile = load_profile()
        watchlist = load_watchlist()
        dismissed = load_dismissals()
        client = HttpClient(user_agent=build_user_agent(profile.contact))
        sources = build_sources(profile, client)
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
        if args.command == "doctor":
            return _doctor(sources)
        return _run(
            profile,
            watchlist,
            sources,
            dismissed,
            trigger=args.trigger,
            skip_probes=args.skip_probes,
        )
    finally:
        lock.release()


def _doctor(sources) -> int:
    """Say, per Source, whether its parsers still recognise a known-good page."""
    _, failures = _probe(sources)
    broken = {failure.source for failure in failures}
    for source in sources:
        print(f"  {'FEHLER' if source.name in broken else 'ok    '}  {source.name}")
    for failure in failures:
        print(f"\n{failure.source}: {failure.message}", file=sys.stderr)
    return EXIT_SOURCE_FAILURE if failures else EXIT_OK


def _should_sweep_extended(profile, store: Store, now: datetime) -> bool:
    """The weekly long tail, on the configured day.

    A Run that never happened must not cost a whole week, so a sweep that is
    more than seven days overdue happens on the next Run whatever day it is —
    the same schedule-statelessness the diff has (ADR 4).
    """
    if not profile.extended_authors:
        return False
    last = store.get_state(profile.slug, EXTENDED_SWEEP_KEY)
    if last is None:
        return True
    if now - last >= EXTENDED_SWEEP_OVERDUE:
        return True
    return now.weekday() == profile.extended_sweep_weekday and last.date() != now.date()


def _run(
    profile, watchlist, sources, dismissed, *, trigger: str, skip_probes: bool = False
) -> int:
    store = Store(paths.db_path())
    started_at = datetime.now()
    run_id = store.start_run(profile.slug, trigger, started_at)

    probe_failures: list[SourceFailure] = []
    if not skip_probes:
        sources, probe_failures = _probe(sources)

    sweep_extended = _should_sweep_extended(profile, store, started_at)
    context = RunContext(
        profile_slug=profile.slug,
        store=store,
        now=started_at,
        dismissed=dismissed,
        sweep_extended=sweep_extended,
    )
    observations, failures = _collect(sources, profile, watchlist, context)
    failures = [*probe_failures, *failures]
    if sweep_extended and not failures:
        store.set_state(profile.slug, EXTENDED_SWEEP_KEY, started_at)
    previous = store.latest_observations(profile.slug, keys_of(observations))
    known_scopes = store.known_discovery_scopes(profile.slug)
    deltas = suppress_unseeded(compute_deltas(observations, previous), known_scopes)

    store.append(run_id, profile.slug, observations, started_at)

    last_run = store.last_finished_run(profile.slug, run_id)
    digest = build_digest(
        profile_name=profile.name,
        generated_at=started_at,
        since=last_run.started_at if last_run else None,
        deltas=deltas,
        failures=failures,
        attention=context.attention,
        profile=profile,
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
