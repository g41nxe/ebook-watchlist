"""Ein Name je Beziehung, überall derselbe.

Vier Module hatten sich je eine eigene Liste geschrieben, und die waren
auseinandergelaufen: `owned` hieß "besitze ich" auf der Buchseite, "besessen"
im Profil, "Habe ich" im Stapel und "im Besitz" im Watchlist-Menü. Vier Namen
für dieselbe Sache entstehen nicht aus Absicht, sondern daraus, dass es vier
Stellen gab.
"""

from __future__ import annotations


def test_one_list_of_names_feeds_every_view() -> None:
    """Vier Module hatten sich je eine eigene Liste geschrieben, und die waren
    auseinandergelaufen — `owned` hiess an vier Stellen vier verschiedene
    Dinge. Jetzt lesen alle aus derselben."""
    from ebook_watchlist.relations import RELATION_LABELS, RelationKind
    from ebook_watchlist.web import book, profile_page, triage

    fuer_alle = dict(book.KINDS)
    assert fuer_alle == {str(k): v for k, v in RELATION_LABELS.items()}
    for schluessel, name in (*profile_page._RELATION_LABELS, *triage.ACTIONS):
        assert name == RELATION_LABELS[RelationKind(schluessel)]


def test_every_kind_has_a_name() -> None:
    from ebook_watchlist.relations import RELATION_LABELS, RelationKind

    assert set(RELATION_LABELS) == set(RelationKind)


def test_no_two_names_differ_only_by_a_negation() -> None:
    """„Mag ich" und „Mag ich nicht" sahen beim Ueberfliegen gleich aus."""
    from ebook_watchlist.relations import RELATION_LABELS

    namen = list(RELATION_LABELS.values())
    for name in namen:
        assert f"{name} nicht" not in namen
