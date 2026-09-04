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

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .. import paths
from ..config import ConfigError, load_profile
from ..store import RunRow, Store

STATIC = Path(__file__).parent / "static"
TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

#: Digest files are named by the Run that wrote them. Serving anything else
#: from the data directory would turn a read-only page into a file browser.
DIGEST_NAME = re.compile(r"^digest-\d{4}-\d{2}-\d{2}(?:-\d{4})?\.html$")


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


def source_trouble(runs: list[RunRow]) -> list[str]:
    """What the most recent Run complained about.

    A placeholder until Sources record their own health (ticket 03) — until
    then the Run journal is the only place failures are written down.
    """
    for run in runs:
        if run.finished_at is None:
            continue
        return [part.strip() for part in (run.error or "").split(";") if part.strip()]
    return []


def create_app() -> FastAPI:
    app = FastAPI(title="eBook-Watchlist", docs_url=None, redoc_url=None)
    # Built by `uv run tailwindcss` and committed, so a checkout serves without
    # a toolchain — the Pi never builds anything (ADR 20).
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request) -> HTMLResponse:
        try:
            profile = load_profile()
        except ConfigError as exc:
            return TEMPLATES.TemplateResponse(
                request, "error.html", {"message": str(exc)}, status_code=500
            )

        store = _store_for(paths.db_path())
        runs = store.recent_runs(profile.slug)
        return TEMPLATES.TemplateResponse(
            request,
            "dashboard.html",
            {
                "profile": profile,
                "runs": runs,
                "digests": digest_files(),
                "trouble": source_trouble(runs),
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
