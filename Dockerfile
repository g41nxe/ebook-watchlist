# Buchfink in einem Container.
#
# Ein Container, nicht zwei: der Webprozess startet den Lauf als abgekoppeltes
# Kind (`runs.py`) und verfolgt ihn danach ueber dessen pid. Zusaetzlich laeuft
# der enge Lauf als Thread im Webprozess selbst und nimmt dieselbe Dateisperre.
# Getrennte Container haetten getrennte pid-Namensraeume — die Lauf-Liste zeigte
# dann willkuerlich "laeuft" fuer laengst beendete Laeufe.
#
# Der Quellbaum wandert mit, nicht ein Wheel: `rating.py` loest Leseprofil und
# Bewertungsschema ueber `parents[2]/docs/...` auf, also relativ zum Paket. In
# `site-packages` zeigten diese Pfade ins Leere.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Die Anwendung rechnet durchgaengig in lokaler naiver Zeit — der Dateiname des
# Tagesberichts ist das lokale Kalenderdatum, der woechentliche Streifzug haengt
# am lokalen Wochentag (ADR 12, "Time: local time"). Ohne tzdata bliebe der
# Container bei UTC, und ein Lauf um 00:30 schriebe den Bericht auf den Vortag.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    EBW_DATA_DIR=/data

WORKDIR /app

# Abhaengigkeiten vor dem Quelltext, damit diese Schicht haelt, solange sich
# `uv.lock` nicht aendert.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-install-project

COPY . .
RUN uv sync --frozen

# Ohne gebaute statische Dateien verweigert `app.py` den Start. Tailwind und die
# zwei Bibliotheken kommen hier aus dem Netz — einmal, zur Bauzeit. Zur Laufzeit
# holt die Oberflaeche nichts mehr nach (`build.py`).
RUN uv run tailwindcss_install && uv run python -m ebook_watchlist.web.build

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8437
ENTRYPOINT ["/entrypoint.sh"]
