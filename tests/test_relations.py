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
    Dinge. Jetzt lesen alle aus derselben.

    Seit Issue #5 sind es zwei Listen mit klarer Zustaendigkeit: der
    Zustandsname sagt, was ein Buch *ist* (Buchseite, Profil), das
    Handlungswort steht auf dem Knopf, der es dazu *macht* (Stapel,
    Startseite, Watchlist-Menue). Keine Ansicht mischt."""
    from ebook_watchlist.relations import ACTION_LABELS, RELATION_LABELS, RelationKind
    from ebook_watchlist.web import book, profile_page, triage, watchlist

    fuer_alle = dict(book.KINDS)
    assert fuer_alle == {str(k): v for k, v in RELATION_LABELS.items()}
    for schluessel, name in profile_page._RELATION_LABELS:
        assert name == RELATION_LABELS[RelationKind(schluessel)]
    for schluessel, name in (*triage.ACTIONS, *watchlist.ABSCHLUSS):
        assert name == ACTION_LABELS[RelationKind(schluessel)]


def test_every_kind_has_a_name() -> None:
    from ebook_watchlist.relations import RELATION_LABELS, RelationKind

    assert set(RELATION_LABELS) == set(RelationKind)


def test_every_decision_has_a_word_for_the_button() -> None:
    """Die drei Handlungen des Stapels — mehr Knoepfe gibt es nicht."""
    from ebook_watchlist.relations import ACTION_LABELS, RelationKind

    assert set(ACTION_LABELS) == {
        RelationKind.DISMISSED, RelationKind.OWNED, RelationKind.WATCHING
    }


def test_an_action_word_is_never_a_state_name() -> None:
    """Sonst rutscht "im Besitz" irgendwann wieder auf einen Knopf — an einer
    Stelle, und die Drift beginnt von vorn."""
    from ebook_watchlist.relations import ACTION_LABELS, RELATION_LABELS

    assert not set(ACTION_LABELS.values()) & set(RELATION_LABELS.values())


def test_no_two_names_differ_only_by_a_negation() -> None:
    """„Mag ich" und „Mag ich nicht" sahen beim Ueberfliegen gleich aus."""
    from ebook_watchlist.relations import ACTION_LABELS, RELATION_LABELS

    for liste in (RELATION_LABELS, ACTION_LABELS):
        namen = list(liste.values())
        for name in namen:
            assert f"{name} nicht" not in namen
