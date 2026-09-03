"""Phase 1 configuration: ``profile.yaml`` and ``watchlist.yaml`` are the source
of truth (ADR 10). Anything missing or malformed fails loudly — a silently empty
watchlist looks exactly like "no deals today"."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from . import paths


class ConfigError(Exception):
    """Raised for a missing, unreadable, or structurally invalid config file."""


@dataclass(frozen=True, slots=True)
class Profile:
    slug: str
    name: str
    strong_deal_max_cents: int = 500
    deal_max_cents: int = 1000
    min_discount_pct: int = 25
    reference_authors: list[str] = field(default_factory=list)
    genre_categories: list[str] = field(default_factory=list)
    no_gos: list[str] = field(default_factory=list)
    sources: dict[str, dict[str, Any]] = field(default_factory=dict)
    #: Appended to the outgoing User-Agent so a site operator can reach you.
    #: Opt-in — nothing personal is sent unless you put it here yourself.
    contact: str | None = None


@dataclass(frozen=True, slots=True)
class WatchlistEntry:
    title: str
    author: str | None = None
    check_library: bool = True
    check_shop: bool = True
    active: bool = True
    notes: str | None = None
    resolved_links: dict[str, str] = field(default_factory=dict)

    @property
    def key(self) -> str:
        """Phase 1 identity. Phase 2 replaces this with a database id (ADR 5)."""
        return f"{self.title}|{self.author or ''}".casefold()


def _load_yaml(path: Path, what: str) -> Any:
    if not path.exists():
        raise ConfigError(f"{what} not found at {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"{what} at {path} is not valid YAML: {exc}") from exc
    if data is None:
        raise ConfigError(f"{what} at {path} is empty")
    return data


def _require(mapping: dict[str, Any], key: str, what: str) -> Any:
    if key not in mapping or mapping[key] in (None, ""):
        raise ConfigError(f"{what} is missing the required field {key!r}")
    return mapping[key]


def _str_list(mapping: dict[str, Any], key: str, what: str) -> list[str]:
    value = mapping.get(key) or []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{what}: {key!r} must be a list of strings")
    return value


def _positive_int(mapping: dict[str, Any], key: str, default: int, what: str) -> int:
    value = mapping.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigError(f"{what}: {key!r} must be a positive integer, got {value!r}")
    return value


def load_profile(path: Path | None = None) -> Profile:
    path = path or paths.profile_path()
    data = _load_yaml(path, "profile.yaml")
    if not isinstance(data, dict):
        raise ConfigError(f"profile.yaml at {path} must be a mapping")

    what = "profile.yaml"
    profile = Profile(
        slug=str(_require(data, "slug", what)),
        name=str(_require(data, "name", what)),
        strong_deal_max_cents=_positive_int(data, "strong_deal_max_cents", 500, what),
        deal_max_cents=_positive_int(data, "deal_max_cents", 1000, what),
        min_discount_pct=_positive_int(data, "min_discount_pct", 25, what),
        reference_authors=_str_list(data, "reference_authors", what),
        genre_categories=_str_list(data, "genre_categories", what),
        no_gos=_str_list(data, "no_gos", what),
        sources=data.get("sources") or {},
        contact=str(data["contact"]) if data.get("contact") else None,
    )
    if profile.strong_deal_max_cents >= profile.deal_max_cents:
        raise ConfigError(
            "profile.yaml: strong_deal_max_cents must be below deal_max_cents "
            f"({profile.strong_deal_max_cents} >= {profile.deal_max_cents})"
        )
    if not isinstance(profile.sources, dict):
        raise ConfigError("profile.yaml: 'sources' must be a mapping of source name to options")
    return profile


def load_dismissals(path: Path | None = None) -> dict[str, frozenset[str]]:
    """Suggestions the reader has permanently waved away, per Source::

        beam:
          - "1278797"

    The one config file that is genuinely optional — an absent file just means
    nothing has been dismissed yet.
    """
    path = path or paths.dismissed_path()
    if not path.exists():
        return {}

    data = _load_yaml(path, "dismissed.yaml")
    if not isinstance(data, dict):
        raise ConfigError(f"dismissed.yaml at {path} must map a source name to a list of ids")

    dismissals: dict[str, frozenset[str]] = {}
    for source, ids in data.items():
        if not isinstance(ids, list):
            raise ConfigError(f"dismissed.yaml: entries for {source!r} must be a list")
        dismissals[str(source)] = frozenset(str(item) for item in ids)
    return dismissals


def load_watchlist(path: Path | None = None) -> list[WatchlistEntry]:
    path = path or paths.watchlist_path()
    data = _load_yaml(path, "watchlist.yaml")
    if isinstance(data, dict):
        data = data.get("entries")
    if not isinstance(data, list):
        raise ConfigError(f"watchlist.yaml at {path} must be a list of entries")

    entries: list[WatchlistEntry] = []
    for index, raw in enumerate(data, start=1):
        what = f"watchlist.yaml entry #{index}"
        if not isinstance(raw, dict):
            raise ConfigError(f"{what} must be a mapping")
        links = raw.get("resolved_links") or {}
        if not isinstance(links, dict):
            raise ConfigError(f"{what}: 'resolved_links' must be a mapping of source to URL")
        # Blank-but-present fields are a common hand-editing slip; treating them
        # as absent keeps every consumer from having to re-check.
        author = str(raw.get("author") or "").strip() or None
        entries.append(
            WatchlistEntry(
                title=str(_require(raw, "title", what)).strip(),
                author=author,
                check_library=bool(raw.get("check_library", True)),
                check_shop=bool(raw.get("check_shop", True)),
                active=bool(raw.get("active", True)),
                notes=str(raw["notes"]) if raw.get("notes") else None,
                resolved_links={str(k): str(v) for k, v in links.items()},
            )
        )

    seen: set[str] = set()
    for entry in entries:
        if entry.key in seen:
            raise ConfigError(
                f"watchlist.yaml has a duplicate entry: {entry.title} / {entry.author}"
            )
        seen.add(entry.key)
    return entries
