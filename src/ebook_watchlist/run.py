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
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

from filelock import FileLock, Timeout

from . import gate, paths
from .cleaning import clean_blurb
from .config import ConfigError, Profile, load_dismissals, load_profile, load_watchlist
from .configuration import NotSeeded
from .configuration import load as load_configuration
from .covers import CoverStore
from .diff import compute_deltas, keys_of, suppress_unseeded_interests
from .digest import GateNote, build_digest
from .http import HttpClient, RateLimited, build_user_agent
from .models import Observation, SourceFailure
from .rating import DEFAULT_THRESHOLD, RatingUnavailable, build_rater, load_rubric
from .render import render_html, render_text
from .seed import seed
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
        choices=["run", "doctor", "sources", "seed"],
        help=(
            "'run' checks everything; 'doctor' only asks each Source whether it still "
            "parses; 'sources' lists them and can pause one; 'seed' imports the YAML "
            "files into the database once"
        ),
    )
    parser.add_argument("--enable", metavar="QUELLE", help="eine pausierte Quelle wieder aufnehmen")
    parser.add_argument("--disable", metavar="QUELLE", help="eine Quelle pausieren")
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


def _probe(
    sources, store: Store | None = None, now: datetime | None = None
) -> tuple[list, list[SourceFailure]]:
    """Ask every Source whether its parsers still recognise a known-good page.

    A Source that fails here is sat out for the Run: half-reading a redesigned
    site would write nonsense into the Snapshot and quietly poison every future
    diff (ADR 7).

    The outcome is recorded rather than printed and forgotten (Ticket 03), so
    the Dashboard can tell a Source that just broke from one that has been
    broken for a week.
    """
    healthy, failures = [], []
    at = now or datetime.now()
    for source in sources:
        message = None
        try:
            source.probe()
        except Exception as exc:  # noqa: BLE001 - deliberate: isolate one Source
            message = f"Selbsttest fehlgeschlagen — {type(exc).__name__}: {exc}"
            failures.append(SourceFailure(source=source.name, message=message))
        else:
            healthy.append(source)
        if store is not None:
            store.record_probe(source.name, ok=message is None, error=message, now=at)
    return healthy, failures


def _partition_enabled(sources, store: Store) -> tuple[list, list[str]]:
    """Sources the reader has paused are sat out — and named for it.

    Silently skipping one would look exactly like a quiet day at that shop,
    which is the failure mode this tool exists to avoid (ADR 15).
    """
    active, paused = [], []
    for source in sources:
        if store.is_enabled(source.name):
            active.append(source)
        else:
            paused.append(source.name)
    return active, paused


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
    # One place, every Source, before anything is compared or stored. Cleaning
    # inside each parser would mean two implementations that drift (Ticket 16).
    return [_cleaned(observation) for observation in observations], failures


def _cleaned(observation: Observation) -> Observation:
    blurb = clean_blurb(observation.blurb)
    if blurb == observation.blurb:
        return observation
    return replace(observation, blurb=blurb)


def _fetch_covers(store: Store, client: HttpClient, observations: Sequence[Observation]) -> None:
    """Titelbilder holen — einmal pro Buch, und nur für Bücher (Ticket 15).

    Eine Entdeckung bekommt keins: das wären dreihundert Anfragen pro Lauf statt
    einer Handvoll, und für ein Buch, zu dem die Leserin keine Beziehung hat,
    gibt es ohnehin keine Zeile, an der ein Bild hängen könnte (ADR 18).

    Ein Bild ist Beiwerk. Schlägt es fehl, läuft der Rest weiter — nur eine
    Drosselung bricht ab, denn dann hat der Shop Halt gesagt.
    """
    covers = CoverStore(paths.covers_dir())
    done: set[int] = set()
    for observation in observations:
        book_id, url = observation.book_id, observation.cover_url
        if not book_id or not url or book_id in done:
            continue
        done.add(book_id)
        book = store.book(book_id)
        if book is None or book.cover_file:
            continue
        try:
            name = covers.fetch(client, book_id, url)
        except RateLimited:
            print("Titelbilder: der Shop drosselt — Rest übersprungen", file=sys.stderr)
            return
        if name:
            store.set_cover(book_id, name)


def _apply_gate(store: Store, deltas, profile: Profile, now: datetime):
    """Entdeckungen gegen das Leseprofil pruefen (ADR 19).

    Ohne Schluessel gibt es kein Tor — dann bleibt alles unbewertet und wird
    gezeigt. Das ist der Zustand vor Ticket 12 und ausdruecklich erlaubt.
    """
    rater = build_rater()
    if rater is None:
        return deltas, gate.unrated_report(deltas)
    try:
        _, version = load_rubric()
    except RatingUnavailable as exc:
        print(f"Bewertung übersprungen: {exc}", file=sys.stderr)
        return deltas, gate.unrated_report(deltas)

    kept, report = gate.apply(
        deltas,
        store=store,
        rater=rater,
        rubric_version=version,
        threshold=DEFAULT_THRESHOLD,
        budget=profile.rating_budget,
        now=now,
    )
    if report.held_back or report.over_budget:
        # Fuer das Log. Was die Leserin sehen muss, steht im Digest — stderr
        # wirft ein Cron-Job weg (Ticket 20).
        print(
            f"Bewertungstor: {report.held_back} unter {DEFAULT_THRESHOLD} Sternen "
            f"zurückgehalten, {report.over_budget} über dem Budget "
            f"({report.rated} bewertet, {report.reused} aus dem Speicher)",
            file=sys.stderr,
        )
    return kept, report


def _write_html(digest, generated_at: datetime) -> Path:
    directory = paths.digests_dir()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"digest-{generated_at:%Y-%m-%d}.html"
    if target.exists():
        # A second Run on the same day must not silently erase the first one's
        # digest; the plain daily name stays the one a cron job produces.
        target = directory / f"digest-{generated_at:%Y-%m-%d-%H%M}.html"
    target.write_text(render_html(digest), encoding="utf-8")
    return target


def main(argv: Sequence[str] | None = None) -> int:
    _survive_a_narrow_console()
    args = _parse_args(argv)
    if args.data_dir is not None:
        os.environ["EBW_DATA_DIR"] = str(args.data_dir)

    try:
        profile = load_profile()
        dismissed = load_dismissals()
        # Die Watchlist-Datei ist Saatgut (ADR 10) und wird nur noch fuer den
        # Import gebraucht. Sie weiterhin bei jedem Lauf zu verlangen hiesse,
        # dass "nur noch Saatgut" nicht stimmt: wer sie nach dem Import
        # loescht, koennte gar nicht mehr laufen.
        watchlist = load_watchlist() if args.command == "seed" else []
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
        if args.command == "sources":
            return _sources(sources, enable=args.enable, disable=args.disable)
        if args.command == "seed":
            return _seed(profile, watchlist, dismissed)
        try:
            return _run(
                profile,
                watchlist,
                sources,
                dismissed,
                client=client,
                trigger=args.trigger,
                skip_probes=args.skip_probes,
            )
        except NotSeeded as exc:
            # Kein stiller Rückfall auf YAML: sonst liefe der Lauf monatelang
            # gegen eine Datei, von der alle annehmen, sie sei abgelöst.
            print(f"{exc}", file=sys.stderr)
            return EXIT_CONFIG_ERROR
    finally:
        lock.release()


def _seed(profile, watchlist, dismissed) -> int:
    """Die YAML-Dateien in die Datenbank überführen (Ticket 05).

    Wiederholbar: ein zweiter Aufruf legt nichts doppelt an und setzt nichts
    zurück, was inzwischen woanders geändert wurde.
    """
    store = Store(paths.db_path())
    report = seed(store, profile, watchlist, dismissed)

    print(f"  {report.books:>4}  Bücher neu angelegt")
    print(f"  {report.relations:>4}  Beziehungen")
    print(f"  {report.interests:>4}  Interessen")
    if report.needs_attention:
        print(f"\n  {len(report.unresolved)} Einträge brauchen Aufmerksamkeit:")
        for item in report.unresolved:
            print(f"    - {item}")
        print("\n  Nicht geraten: diese Zeilen nennen kein Buch, das sich")
        print("  zweifelsfrei auflösen ließe (ADR 8).")
    return EXIT_OK


def _sources(sources, *, enable: str | None, disable: str | None) -> int:
    """List the Sources with their health, and pause or resume one.

    The switch exists so a Source that has broken can be stopped without
    editing a file and without commenting out configuration — which is how a
    pause becomes permanent by forgetting.
    """
    store = Store(paths.db_path())
    known = {source.name for source in sources}
    now = datetime.now()

    for name, wanted in ((enable, True), (disable, False)):
        if name is None:
            continue
        if name not in known:
            print(
                f"unbekannte Quelle {name!r} (bekannt: {', '.join(sorted(known))})",
                file=sys.stderr,
            )
            return EXIT_CONFIG_ERROR
        store.set_enabled(name, wanted, now=now)
        print(f"{name}: {'aufgenommen' if wanted else 'pausiert'}")

    for source in sources:
        row = store.source(source.name)
        if row is None:
            print(f"  ?         {source.name}  (noch nie gelaufen)")
            continue
        if not row.enabled:
            state = "pausiert"
        elif row.last_probe_ok is None:
            state = "?       "
        else:
            state = "ok      " if row.last_probe_ok else "FEHLER  "
        seen = f"{row.last_probe_at:%d.%m. %H:%M}" if row.last_probe_at else "nie"
        streak = (
            f"  seit {row.consecutive_failures} Prüfungen"
            if row.consecutive_failures > 1
            else ""
        )
        print(f"  {state}  {source.name}  zuletzt {seen}{streak}")
        if row.last_error:
            print(f"            {row.last_error}")
    return EXIT_OK


def _doctor(sources) -> int:
    """Say, per Source, whether its parsers still recognise a known-good page.

    The verdict is written down as well as printed (Ticket 03): a doctor run is
    the same evidence as a Run's probe, and throwing it away is why the
    Dashboard had to infer health from Run failures.
    """
    store = Store(paths.db_path())
    active, paused = _partition_enabled(sources, store)
    _, failures = _probe(active, store, datetime.now())

    broken = {failure.source for failure in failures}
    for source in sources:
        if source.name in paused:
            state = "pausiert"
        elif source.name in broken:
            state = "FEHLER  "
        else:
            state = "ok      "
        row = store.source(source.name)
        streak = ""
        if row is not None and row.consecutive_failures > 1:
            streak = f"  (seit {row.consecutive_failures} Prüfungen)"
        print(f"  {state}  {source.name}{streak}")
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
    profile,
    watchlist,
    sources,
    dismissed,
    *,
    client: HttpClient,
    trigger: str,
    skip_probes: bool = False,
) -> int:
    store = Store(paths.db_path())
    started_at = datetime.now()

    # Die Konfiguration kommt aus der Datenbank; YAML ist Saatgut (ADR 10).
    # Kein stiller Rueckfall: eine leere Datenbank heisst "noch nicht
    # importiert", und das gehoert gesagt.
    configured = load_configuration(store, profile)
    profile = configured.profile
    watchlist = configured.watchlist

    run_id = store.start_run(profile.slug, trigger, started_at)

    sources, paused = _partition_enabled(sources, store)
    for name in paused:
        print(f"{name}: pausiert — übersprungen", file=sys.stderr)

    probe_failures: list[SourceFailure] = []
    if not skip_probes:
        sources, probe_failures = _probe(sources, store, started_at)

    sweep_extended = _should_sweep_extended(profile, store, started_at)
    context = RunContext(
        profile_slug=profile.slug,
        store=store,
        now=started_at,
        dismissed=dismissed,
        sweep_extended=sweep_extended,
        interests={
            (row.key, row.value): row.id
            for table in (configured.author_interests, configured.thema_interests)
            for row in table.values()
        },
    )
    observations, failures = _collect(sources, profile, watchlist, context)
    failures = [*probe_failures, *failures]
    if sweep_extended and not failures:
        store.set_state(profile.slug, EXTENDED_SWEEP_KEY, started_at)
    # Ein Watchlist-Eintrag kommt ohne ISBN aus der YAML; die Beobachtung
    # bringt sie mit. Erst dadurch bekommt das Buch die Identitaet, an der zwei
    # Quellen sich treffen koennen (ADR 18).
    for observation in observations:
        if observation.book_id and observation.isbn:
            store.learn_isbn(observation.book_id, observation.isbn)
    _fetch_covers(store, client, observations)

    previous = store.latest_observations(profile.slug, keys_of(observations))
    # Angesaet ist je *Quelle*: ein Interesse, das beam kennt, ist der Onleihe
    # deswegen nicht vertraut. Vorher genuegte "irgendeine Quelle", und die
    # zweite Quelle haette dieselbe Backlist noch einmal gemeldet.
    seeded = {
        interest_id
        for source_name, interest_id in context.swept
        if store.is_interest_seeded(interest_id, source_name)
    }
    deltas = suppress_unseeded_interests(
        compute_deltas(observations, previous, profile), context.origin, seeded
    )

    store.append(run_id, profile.slug, observations, started_at)

    # Das Tor sitzt hinter dem Snapshot: ein Ausfall kostet ein Urteil, nie
    # Geschichte. Und hinter der Preisregel: ein Buch zu bewerten, das ohnehin
    # niemand zu sehen bekommt, waere Verschwendung (ADR 19).
    deltas, gate_report = _apply_gate(store, deltas, profile, started_at)
    for source_name, interest_id in context.swept:
        store.mark_interest_seeded(interest_id, source_name, now=started_at)

    last_run = store.last_finished_run(profile.slug, run_id)
    digest = build_digest(
        profile_name=profile.name,
        generated_at=started_at,
        since=last_run.started_at if last_run else None,
        deltas=deltas,
        failures=failures,
        attention=context.attention,
        profile=profile,
        judgements=gate_report.judgements,
        gate=GateNote(
            held_back=gate_report.held_back,
            threshold=DEFAULT_THRESHOLD,
            over_budget=gate_report.over_budget,
        ),
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
