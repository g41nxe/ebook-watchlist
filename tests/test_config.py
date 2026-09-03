from __future__ import annotations

from pathlib import Path

import pytest

from ebook_watchlist.config import ConfigError, load_profile, load_watchlist


def test_loads_profile_with_defaults(data_dir: Path) -> None:
    profile = load_profile()
    assert profile.slug == "test"
    assert profile.strong_deal_max_cents == 500
    assert profile.deal_max_cents == 1000
    assert profile.min_discount_pct == 25
    assert profile.sources == {"fake": {"fixture": "fake-source.yaml"}}


def test_loads_watchlist(data_dir: Path) -> None:
    entries = load_watchlist()
    assert [entry.title for entry in entries] == ["Die sieben Schwestern"]
    assert entries[0].check_library is True
    assert entries[0].check_shop is True


def test_missing_profile_fails_loudly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EBW_DATA_DIR", str(tmp_path))
    with pytest.raises(ConfigError, match="profile.yaml not found"):
        load_profile()


def test_empty_watchlist_file_fails_loudly(data_dir: Path) -> None:
    (data_dir / "watchlist.yaml").write_text("", encoding="utf-8")
    with pytest.raises(ConfigError, match="is empty"):
        load_watchlist()


def test_broken_yaml_fails_loudly(data_dir: Path) -> None:
    (data_dir / "profile.yaml").write_text("slug: [unclosed", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid YAML"):
        load_profile()


def test_missing_required_field_fails_loudly(data_dir: Path) -> None:
    (data_dir / "profile.yaml").write_text("name: Ohne Slug\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="'slug'"):
        load_profile()


def test_inverted_deal_thresholds_rejected(data_dir: Path) -> None:
    (data_dir / "profile.yaml").write_text(
        "slug: t\nname: T\nstrong_deal_max_cents: 2000\ndeal_max_cents: 1000\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="must be below"):
        load_profile()


def test_duplicate_watchlist_entry_rejected(data_dir: Path) -> None:
    (data_dir / "watchlist.yaml").write_text(
        "- title: A\n  author: B\n- title: a\n  author: b\n", encoding="utf-8"
    )
    with pytest.raises(ConfigError, match="duplicate"):
        load_watchlist()


def test_shipped_examples_load(monkeypatch: pytest.MonkeyPatch) -> None:
    examples = Path(__file__).resolve().parents[1] / "examples"
    monkeypatch.setenv("EBW_DATA_DIR", str(examples))
    assert load_profile().slug == "default"
    assert len(load_watchlist()) == 2
