"""Where the runtime keeps its data.

Everything mutable lives under one directory so a move to another host is a copy
(ADR 12). ``EBW_DATA_DIR`` overrides the default ``./data`` next to the repo.
"""

from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    override = os.environ.get("EBW_DATA_DIR")
    root = Path(override).expanduser() if override else _REPO_ROOT / "data"
    return root.resolve()


def profile_path() -> Path:
    return data_dir() / "profile.yaml"


def watchlist_path() -> Path:
    return data_dir() / "watchlist.yaml"


def db_path() -> Path:
    return data_dir() / "snapshots.db"


def digests_dir() -> Path:
    return data_dir() / "digests"


def lock_path() -> Path:
    return data_dir() / "run.lock"
