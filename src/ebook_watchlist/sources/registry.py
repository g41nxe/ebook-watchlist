"""Builds the Sources a Profile asks for.

``profile.yaml`` names them::

    sources:
      fake:
        fixture: fake-source.yaml

Real Sources register here as their tickets land.
"""

from __future__ import annotations

from pathlib import Path

from .. import paths
from ..config import ConfigError, Profile
from .base import Source
from .fake import FakeSource


def _build_fake(name: str, options: dict) -> Source:
    fixture = options.get("fixture")
    if not fixture:
        raise ConfigError(f"profile.yaml: source {name!r} needs a 'fixture' path")
    path = Path(fixture)
    if not path.is_absolute():
        path = paths.data_dir() / path
    return FakeSource(fixture=path, name=name)


_BUILDERS = {
    "fake": _build_fake,
}


def build_sources(profile: Profile) -> list[Source]:
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
        sources.append(builder(name, options))
    return sources
