"""Builds the Sources a Profile asks for.

``profile.yaml`` names them::

    sources:
      voebb:
      fake:
        kind: fake
        fixture: fake-source.yaml

The key is the Source's name in the Snapshot; ``kind`` picks the implementation
and defaults to the key, so the common case needs no options at all.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .. import paths
from ..config import ConfigError, Profile
from ..http import HttpClient
from .base import Source
from .beam import BeamSource
from .fake import FakeSource
from .voebb import VoebbSource
from .voebb import selectors as voebb_selectors


def _build_fake(name: str, options: dict, client: HttpClient) -> Source:
    fixture = options.get("fixture")
    if not fixture:
        raise ConfigError(f"profile.yaml: source {name!r} needs a 'fixture' path")
    path = Path(fixture)
    if not path.is_absolute():
        path = paths.data_dir() / path
    return FakeSource(fixture=path, name=name)


def _build_voebb(name: str, options: dict, client: HttpClient) -> Source:
    raw_media = options.get("media")
    if raw_media is None:
        media = voebb_selectors.DEFAULT_MEDIA
    else:
        if not isinstance(raw_media, list):
            raise ConfigError(f"profile.yaml: source {name!r}: 'media' must be a list")
        media = []
        for wanted in raw_media:
            icon = voebb_selectors.MEDIUM_BY_NAME.get(str(wanted).casefold())
            if icon is None:
                known = ", ".join(sorted(voebb_selectors.MEDIUM_BY_NAME))
                raise ConfigError(
                    f"profile.yaml: source {name!r}: unknown medium {wanted!r} (known: {known})"
                )
            media.append(icon)
    return VoebbSource(client=client, name=name, media=media)


def _build_beam(name: str, options: dict, client: HttpClient) -> Source:
    return BeamSource(client=client, name=name)


#: Welcher Art eine Quelle ist. Die Oberflaeche zeigt die Art, nicht den Namen:
#: "voebb" war nie ein Wort fuer die Leserin, und wie ihre Bibliothek in dieser
#: Installation heisst, entscheidet die Konfiguration (Ticket 14).
#:
#: Hier und nicht in einer Vorlage, weil die Registry ohnehin die Stelle ist,
#: die weiss, *was* eine Quelle ist.
KINDS: dict[str, str] = {"voebb": "library", "beam": "shop", "fake": "shop"}

LIBRARY = "Bibliothek"
SHOP = "Shop"


def category(profile: Profile, name: str) -> str:
    """``"library"`` oder ``"shop"`` fuer eine konfigurierte Quelle."""
    options = profile.sources.get(name) or {}
    kind = options.get("kind", name) if isinstance(options, dict) else name
    return KINDS.get(kind, "shop")


def label(profile: Profile, name: str) -> str:
    """Wie die Quelle der Leserin gegenueber heisst."""
    return LIBRARY if category(profile, name) == "library" else SHOP


_BUILDERS: dict[str, Callable[[str, dict, HttpClient], Source]] = {
    "fake": _build_fake,
    "voebb": _build_voebb,
    "beam": _build_beam,
}


def build_sources(profile: Profile, client: HttpClient) -> list[Source]:
    if not profile.sources:
        raise ConfigError("profile.yaml: no 'sources' configured — nothing to check")

    sources: list[Source] = []
    for name, options in profile.sources.items():
        options = options or {}
        if not isinstance(options, dict):
            raise ConfigError(f"profile.yaml: options for source {name!r} must be a mapping")
        kind = options.get("kind", name)
        builder = _BUILDERS.get(kind)
        if builder is None:
            known = ", ".join(sorted(_BUILDERS))
            raise ConfigError(f"profile.yaml: unknown source {kind!r} (known: {known})")
        sources.append(builder(name, options, client))
    return sources
