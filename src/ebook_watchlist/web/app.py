"""The local web application (ADR 3).

Deliberately small: server-rendered Jinja, no build step, no websocket, no
scheduler. It reads the Snapshot and serves the Digests a Run has already
written — it never scrapes and never holds the Run lock, so restarting or
killing it cannot disturb a Run in progress.

No authentication. It is meant to be bound to a trusted home network; put a
password in front of it before exposing it anywhere else.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .. import paths
from ..config import ConfigError, load_profile
from ..models import LinkOutcome
from ..relations import RelationKind
from ..store import RunRow, Store
from . import book, profile_page, triage, watchlist

STATIC = Path(__file__).parent / "static"


def asset_version() -> str:
    """Der Zeitstempel des gebauten Stylesheets.

    Haengt an der Adresse, damit ein Browser nach einem Neubau nicht seine
    alte Kopie behaelt. Ohne das sieht jede CSS-Aenderung kaputt aus, und
    zwar so ueberzeugend, dass man den Fehler im Template sucht.
    """
    try:
        return str(int((STATIC / "app.css").stat().st_mtime))
    except OSError:  # pragma: no cover - fehlt nur ohne Build
        return "0"
TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _sum_chars(text: str) -> int:
    """Quersumme eines Titels — der Farbton des Platzhalter-Covers.

    Deterministisch, damit dasselbe Buch immer gleich aussieht und zwei
    nebeneinander sich unterscheiden.
    """
    return sum(ord(char) for char in text or "")


TEMPLATES.env.filters["sum_chars"] = _sum_chars

#: Digest files are named by the Run that wrote them. Serving anything else
#: from the data directory would turn a read-only page into a file browser.
DIGEST_NAME = re.compile(r"^digest-\d{4}-\d{2}-\d{2}(?:-\d{4})?\.html$")

#: FastAPI liest Formularfelder ueber diese Marker. Als Modulkonstante,
#: damit im Funktionskopf kein Aufruf steht (ruff B008).
_SELECTED = Form(default=[])


@dataclass(frozen=True, slots=True)
class DigestFile:
    name: str
    written_at: datetime

    @property
    def label(self) -> str:
        return self.written_at.strftime("%d.%m.%Y %H:%M")


def digest_files(limit: int = 30) -> list[DigestFile]:
    directory = paths.digests_dir()
    if not directory.exists():
        return []
    found = [
        DigestFile(path.name, datetime.fromtimestamp(path.stat().st_mtime))
        for path in directory.glob("digest-*.html")
        if DIGEST_NAME.match(path.name)
    ]
    return sorted(found, key=lambda digest: digest.name, reverse=True)[:limit]


@lru_cache(maxsize=4)
def _store_for(path: Path) -> Store:
    """One Store per database file.

    Building it runs the schema migration, so creating one per request would
    re-check the schema on every page load.
    """
    return Store(path)


@dataclass(frozen=True, slots=True)
class SourceHealth:
    """One Source as the Dashboard shows it (Ticket 03)."""

    name: str
    enabled: bool
    ok: bool | None
    last_probe_at: datetime | None
    error: str | None
    consecutive_failures: int

    @property
    def state(self) -> str:
        if not self.enabled:
            return "pausiert"
        if self.ok is None:
            return "ungeprüft"
        return "ok" if self.ok else "Fehler"

    @property
    def note(self) -> str | None:
        """A Source failing for days is a different problem from one that just
        broke: the first needs a human, the second may be a redesign in flight."""
        if self.consecutive_failures > 1:
            return f"seit {self.consecutive_failures} Prüfungen"
        return None

    @property
    def seen(self) -> str:
        return f"{self.last_probe_at:%d.%m. %H:%M}" if self.last_probe_at else "nie"


def source_health(store: Store) -> list[SourceHealth]:
    return [
        SourceHealth(
            name=row.name,
            enabled=row.enabled,
            ok=row.last_probe_ok,
            last_probe_at=row.last_probe_at,
            error=row.last_error,
            consecutive_failures=row.consecutive_failures or 0,
        )
        for row in store.sources()
    ]


def source_trouble(runs: list[RunRow]) -> list[str]:
    """What the most recent Run complained about.

    Kept alongside the per-Source health: a Source can parse fine and still
    fail mid-collect, and that failure is recorded only on the Run.
    """
    for run in runs:
        if run.finished_at is None:
            continue
        return [part.strip() for part in (run.error or "").split(";") if part.strip()]
    return []


def create_app() -> FastAPI:
    app = FastAPI(title="eBook-Watchlist", docs_url=None, redoc_url=None)
    # Build output is not in the repository (ADR 20), so say so plainly rather
    # than serving an unstyled page that looks like a CSS bug.
    if not (STATIC / "app.css").is_file():
        raise RuntimeError(
            "web assets are missing — run: uv run python -m ebook_watchlist.web.build"
        )
    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    # Titelbilder liegen im Datenverzeichnis, nicht im Paket (Ticket 15).
    # StaticFiles verweigert Pfade ausserhalb des Wurzelordners, also kann
    # ein Dateiname von aussen nicht in das Datenverzeichnis greifen.
    covers = paths.covers_dir()
    covers.mkdir(parents=True, exist_ok=True)
    app.mount("/covers", StaticFiles(directory=covers), name="covers")

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request) -> HTMLResponse:
        try:
            profile = load_profile()
        except ConfigError as exc:
            return TEMPLATES.TemplateResponse(
                request,
                "error.html",
                {"message": str(exc), "asset_version": asset_version()},
                status_code=500,
            )

        store = _store_for(paths.db_path())
        runs = store.recent_runs(profile.slug)
        return TEMPLATES.TemplateResponse(
            request,
            "dashboard.html",
            {
                "profile": profile,
                "asset_version": asset_version(),
                "runs": runs,
                "digests": digest_files(),
                "sources": source_health(store),
                "trouble": source_trouble(runs),
            },
        )

    # --- Watchlist (Ticket 06) ---------------------------------------------

    def _watchlist_page(request: Request, message: str | None = None) -> HTMLResponse:
        profile = load_profile()
        store = _store_for(paths.db_path())
        return TEMPLATES.TemplateResponse(
            request,
            "watchlist.html",
            {
                "profile": profile,
                "asset_version": asset_version(),
                "entries": watchlist.entries(store, profile),
                "restrictions": watchlist.RESTRICTIONS,
                "message": message,
            },
        )

    @app.get("/watchlist", response_class=HTMLResponse)
    def watchlist_page(request: Request) -> HTMLResponse:
        try:
            return _watchlist_page(request)
        except ConfigError as exc:
            return TEMPLATES.TemplateResponse(
                request,
                "error.html",
                {"message": str(exc), "asset_version": asset_version()},
                status_code=500,
            )

    @app.post("/watchlist/add")
    def watchlist_add(title: str = Form(...), author: str = Form("")) -> RedirectResponse:
        # Aufgeloest wird hier nicht: die Oberflaeche scrapt nie (ADR 3). Der
        # Eintrag steht als "noch nicht gesucht" da, bis ein Lauf ihn ansieht.
        if not title.strip():
            return RedirectResponse("/watchlist", status_code=303)
        profile = load_profile()
        watchlist.add(
            _store_for(paths.db_path()),
            profile.slug,
            title=title,
            author=author,
            now=datetime.now(),
        )
        return RedirectResponse("/watchlist", status_code=303)

    @app.post("/watchlist/{book_id}/active")
    def watchlist_active(book_id: int, active: str = Form("")) -> RedirectResponse:
        """Pausieren und fortsetzen — nie loeschen (ADR 18)."""
        profile = load_profile()
        store = _store_for(paths.db_path())
        wanted = active == "1"
        if wanted:
            store.put_relation(
                profile.slug, book_id, str(RelationKind.WATCHING), now=datetime.now()
            )
        else:
            store.deactivate_relation(
                profile.slug, book_id, str(RelationKind.WATCHING), now=datetime.now()
            )
        return RedirectResponse("/watchlist", status_code=303)

    @app.post("/watchlist/{book_id}/restrict")
    def watchlist_restrict(book_id: int, restrict: str = Form("")) -> RedirectResponse:
        profile = load_profile()
        # Leer heisst "alle eingeschalteten Quellen", nicht "keine". Ein
        # unbekannter Wert scheitert in der Validierung des Ladens (Ticket 05).
        watchlist.set_restriction(
            _store_for(paths.db_path()),
            profile.slug,
            book_id,
            restrict or None,
            now=datetime.now(),
        )
        return RedirectResponse("/watchlist", status_code=303)

    @app.post("/watchlist/{book_id}/confirm")
    def watchlist_confirm(
        book_id: int, source: str = Form(...), url: str = Form(...)
    ) -> RedirectResponse:
        """Eine unklare Zuordnung von Hand festmachen.

        Das ist der Vorgang, der im Texteditor und im Gespraech gleichermassen
        schlecht ist: eine URL suchen und in eine YAML kleben. Hier ist es ein
        Klick, und das Ergebnis heisst ``confirmed`` statt ``linked`` — ein
        Mensch hat entschieden, keine Heuristik.
        """
        _store_for(paths.db_path()).put_book_source(
            book_id,
            source,
            outcome=str(LinkOutcome.CONFIRMED),
            url=url,
            resolved_at=datetime.now(),
            reason="von Hand bestätigt",
        )
        return RedirectResponse("/watchlist", status_code=303)

    # --- Buchseite (Ticket 07) ---------------------------------------------

    @app.get("/book/{book_id}", response_class=HTMLResponse)
    def book_page(request: Request, book_id: int) -> HTMLResponse:
        try:
            profile = load_profile()
        except ConfigError as exc:
            return TEMPLATES.TemplateResponse(
                request,
                "error.html",
                {"message": str(exc), "asset_version": asset_version()},
                status_code=500,
            )
        page = book.build(_store_for(paths.db_path()), profile, book_id)
        if page is None:
            raise HTTPException(status_code=404, detail="kein solches Buch")
        return TEMPLATES.TemplateResponse(
            request,
            "book.html",
            {
                "profile": profile,
                "asset_version": asset_version(),
                "page": page,
                "kinds": book.KINDS,
                "price_points": book.price_points(page.history),
            },
        )

    @app.post("/book/{book_id}/relation")
    def book_relation(
        book_id: int, kind: str = Form(...), active: str = Form("")
    ) -> RedirectResponse:
        """Eine Beziehung setzen oder stilllegen.

        Stilllegen statt loeschen: dass ein Buch einmal beobachtet wurde, ist
        selbst eine Auskunft (ADR 18).
        """
        book.set_relation(
            _store_for(paths.db_path()),
            load_profile(),
            book_id,
            kind,
            active=active == "1",
            now=datetime.now(),
        )
        return RedirectResponse(f"/book/{book_id}", status_code=303)

    # --- Triage (Ticket 08) -------------------------------------------------

    @app.get("/vorschlaege", response_class=HTMLResponse)
    def triage_page(request: Request, anlass: str = "") -> HTMLResponse:
        try:
            profile = load_profile()
        except ConfigError as exc:
            return TEMPLATES.TemplateResponse(
                request,
                "error.html",
                {"message": str(exc), "asset_version": asset_version()},
                status_code=500,
            )
        pile = triage.pending(
            _store_for(paths.db_path()), profile, reason=anlass or None
        )
        return TEMPLATES.TemplateResponse(
            request,
            "triage.html",
            {
                "profile": profile,
                "asset_version": asset_version(),
                "pile": pile,
                "actions": triage.ACTIONS,
                "anlass": anlass,
            },
        )

    @app.post("/vorschlaege/entscheiden")
    def triage_decide(
        kind: str = Form(...), keys: list[str] = _SELECTED, anlass: str = Form("")
    ) -> RedirectResponse:
        """Eine Entscheidung auf die Auswahl anwenden.

        Alle drei schreiben eine Beziehung auf Buchebene — "verworfen" ist
        keine Loeschung, sondern eine Aussage ueber das Buch, und sie gilt
        dadurch bei *jeder* Quelle statt nur fuer eine Produktnummer (ADR 18).
        """
        triage.decide(
            _store_for(paths.db_path()),
            load_profile(),
            keys,
            kind,
            now=datetime.now(),
        )
        target = f"/vorschlaege?anlass={anlass}" if anlass else "/vorschlaege"
        return RedirectResponse(target, status_code=303)

    # --- Profiluebersicht (Ticket 09) ---------------------------------------

    @app.get("/profil", response_class=HTMLResponse)
    def profile_overview(request: Request) -> HTMLResponse:
        """Nur lesend, und das ist die Entscheidung.

        Der Massstab hat ein eigenes Aenderungsverfahren mit asymmetrischer
        Beweislast (ADR 17). Ein Formular hier wuerde es umgehen — deshalb gibt
        es zu dieser Seite keine schreibende Route.
        """
        try:
            profile = load_profile()
        except ConfigError as exc:
            return TEMPLATES.TemplateResponse(
                request,
                "error.html",
                {"message": str(exc), "asset_version": asset_version()},
                status_code=500,
            )
        return TEMPLATES.TemplateResponse(
            request,
            "profile.html",
            {
                "profile": profile,
                "asset_version": asset_version(),
                "view": profile_page.build(_store_for(paths.db_path()), profile),
            },
        )

    @app.get("/digest/{name}", response_class=HTMLResponse)
    def digest(name: str) -> HTMLResponse:
        # The Run already rendered this through the HTML renderer; serving the
        # file is what keeps there from being a second implementation.
        if not DIGEST_NAME.match(name):
            raise HTTPException(status_code=404, detail="no such digest")
        path = paths.digests_dir() / name
        if not path.is_file():
            raise HTTPException(status_code=404, detail="no such digest")
        return HTMLResponse(path.read_text(encoding="utf-8"))

    return app


app = create_app()
