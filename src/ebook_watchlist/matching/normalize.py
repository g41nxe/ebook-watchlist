"""Getting two spellings of the same book into the same shape.

The recipe is the one distilled from Calibre in
``docs/research/calibre-matching-rules.md`` §7 — with the parts that only make
sense for a local library (``title_sort`` rewriting, ``titlecase``, dropping
every token of two characters or fewer) deliberately left out.

Everything here is a pure function on strings.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_COMBINING = re.compile(r"[̀-ͯ]")

#: NFKD leaves these alone, so they need an explicit table.
_LANGUAGE_FOLDS = {
    "ß": "ss",
    "ẞ": "ss",
    "ø": "o",
    "Ø": "o",
    "ł": "l",
    "Ł": "l",
    "æ": "ae",
    "Æ": "ae",
    "œ": "oe",
    "Œ": "oe",
    "ð": "d",
    "Ð": "d",
    "þ": "th",
    "Þ": "th",
    "đ": "d",
    "Đ": "d",
}


def fold(text: str) -> str:
    """Case-, accent- and compatibility-insensitive form.

    ``casefold`` rather than ``lower`` because German ``ß`` and Greek final
    sigma need it.
    """
    text = unicodedata.normalize("NFKD", text)
    text = _COMBINING.sub("", text)
    for source, target in _LANGUAGE_FOLDS.items():
        text = text.replace(source, target)
    return text.casefold()


# --- titles ---------------------------------------------------------------

_BRACKETED_EDITION = re.compile(
    r"[({\[]\s*(\d{4}|omnibus|anthology|hardcover|audiobook|audio ?cd|paperback"
    r"|turtleback|mass ?market|edition|ed\.|ebook|ungek[uü]rzt|gek[uü]rzt"
    r"|h[oö]rbuch|auflage)\s*[\])}]"
)
_BRACKETED_EDITION_PHRASE = re.compile(r"[({\[][^\])}]*?(edition|ed\.|auflage)[^\])}]*?[\])}]")
_TRAILING_BRACKET = re.compile(r"[(\[][^)\]]*[)\]]\s*$")
_THOUSANDS = re.compile(r"(\d+),(\d+)")
_PUNCTUATION = re.compile(r"[:,;!@$%^&*(){}.`~\"\[\]/《》「」“”‘’–—]|(?<=\s)-|-(?=\s)")
_SUBTITLE = re.compile(r"\s[-–—]\s|:\s|\s/\s|\s\\\s")
_LEADING_ARTICLE = re.compile(
    r"^(the|a|an|of|and|der|die|das|den|dem|des|ein|eine|einen|einem|einer"
    r"|le|la|les|el|los|il)\s+"
)
_FORMAT_TOKENS = frozenset(
    {
        "ebook",
        "e-book",
        "horbuch",  # 'hörbuch' after folding
        "audiobook",
        "ungekurzt",
        "gekurzt",
        "omnibus",
        "unabridged",
        "abridged",
        "taschenbuch",
        "gebundene",
    }
)
_JOIN_TOKENS = frozenset({"a", "and", "the", "und", "of", "de"})
_WHITESPACE = re.compile(r"\s+")


def normalize_title(title: str) -> str:
    """The comparable form of a title.

    Subtitles, edition noise and format words are exactly the parts two sources
    disagree about, so they come off before anything is compared.
    """
    text = fold(title)
    text = _BRACKETED_EDITION.sub(" ", text)
    text = _BRACKETED_EDITION_PHRASE.sub(" ", text)
    text = _TRAILING_BRACKET.sub(" ", text)
    text = _TRAILING_BRACKET.sub(" ", text)  # once more: "(Roman) (Band 2)"

    head = _SUBTITLE.split(text, maxsplit=1)[0]
    # Only cut when something recognisable survives — "R - Ein Roman" must not
    # collapse to "r".
    if len(head.strip()) > 1:
        text = head

    text = _THOUSANDS.sub(r"\1\2", text)
    text = _PUNCTUATION.sub(" ", text)
    text = _WHITESPACE.sub(" ", text).strip()

    while True:
        stripped = _LEADING_ARTICLE.sub("", text, count=1)
        if stripped == text:
            break
        text = stripped

    tokens = [token for token in text.split() if token not in _FORMAT_TOKENS]
    return " ".join(tokens)


def title_tokens(title: str) -> list[str]:
    """Normalized tokens with join words dropped — the looser comparison form."""
    return [token for token in normalize_title(title).split() if token not in _JOIN_TOKENS]


# --- authors --------------------------------------------------------------

_AND_SEPARATOR = re.compile(r"(?i),?\s+(and|with|und|mit)\s+")
_ROLE_SUFFIX = re.compile(r"[({\[][^)\]}]*[)\]}]")
_AUTHOR_PUNCTUATION = re.compile(r"[-+.:;,。；：!@#$%^&*()（）「」{}`~\"\[\]/]")

_PREFIXES = frozenset({"mr", "mrs", "ms", "dr", "prof", "herr", "frau"})
_SUFFIXES = frozenset({"jr", "sr", "ii", "iii", "iv", "phd", "md", "junior", "senior"})
_PARTICLES = frozenset(
    {"von", "van", "de", "der", "den", "di", "del", "della", "la", "le", "du", "dos", "da"}
)
_ORGANISATION_WORDS = frozenset(
    {
        "verlag",
        "corporation",
        "company",
        "co",
        "agency",
        "council",
        "committee",
        "inc",
        "institute",
        "society",
        "club",
        "team",
        "gmbh",
        "redaktion",
    }
)
_NON_NAMES = frozenset({"unknown", "unbekannt", "diverse", "verschiedene"})


def split_authors(raw: str) -> list[str]:
    """Split a scraped author field into individual names.

    A bare comma is the hard case: it separates people in
    ``Anna Meier, Bernd Schulz`` but means sort order in ``Riley, Lucinda``.
    We read it as a separator when at least half the pieces it produces already
    look like a full name — a majority rather than a unanimous vote, because
    real anthology credits carry stray fragments like ``Jr.`` between the names.
    """
    if not raw:
        return []

    protected = raw.replace("&&", "￿")
    protected = _AND_SEPARATOR.sub("&", protected)
    segments = [
        piece.strip().replace("￿", "&")
        for chunk in protected.split(";")
        for piece in chunk.split("&")
    ]

    authors: list[str] = []
    for segment in segments:
        if not segment:
            continue
        parts = [part.strip() for part in segment.split(",") if part.strip()]
        full_names = sum(1 for part in parts if len(part.split()) >= 2)
        if len(parts) > 1 and full_names * 2 >= len(parts):
            authors.extend(parts)
        else:
            authors.append(segment)
    return authors


@dataclass(frozen=True, slots=True)
class NormalizedAuthor:
    #: All name tokens, initials included.
    full: str
    #: Tokens of more than two characters — survives "J. R. R. Tolkien" vs "Tolkien".
    substantial: str

    def __bool__(self) -> bool:
        return bool(self.full)


def normalize_author(name: str) -> NormalizedAuthor:
    """One name in comparable form, in first-name-first order."""
    text = fold(name)
    text = _ROLE_SUFFIX.sub(" ", text)

    words = _AUTHOR_PUNCTUATION.sub(" ", text).split()
    if any(word in _ORGANISATION_WORDS for word in words):
        # An imprint is not a person; reordering its words only does damage.
        return NormalizedAuthor(full=" ".join(words), substantial=" ".join(words))

    if "," in text:
        surname, _, given = text.partition(",")
        text = f"{given.strip()} {surname.strip()}".strip()

    tokens = [
        token
        for token in _AUTHOR_PUNCTUATION.sub(" ", text).split()
        if token
        and token not in _PREFIXES
        and token not in _SUFFIXES
        and token not in _PARTICLES
        and token not in _NON_NAMES
    ]
    substantial = [token for token in tokens if len(token) > 2]
    return NormalizedAuthor(
        full=" ".join(tokens),
        substantial=" ".join(substantial) or " ".join(tokens),
    )


def normalize_authors(raw: str | None) -> list[NormalizedAuthor]:
    if not raw:
        return []
    return [author for author in (normalize_author(name) for name in split_authors(raw)) if author]
