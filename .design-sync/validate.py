"""Checks that the bundle says nothing untrue.

    uv run --with tinycss2 python .design-sync/validate.py

The conventions header is inlined into a design agent's prompt, and the agent
cannot tell a real class name from an invented one -- it will simply write what
it was told and ship silently unstyled markup. So every name the header
enumerates is checked against the compiled stylesheet here, and so is the one
claim the header makes about something *not* existing.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

#: A literal backslash, built rather than written: this file is generated
#: through shells that eat one.
BS = chr(92)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "ds-bundle"
CONVENTIONS = ROOT / ".design-sync" / "conventions.md"

ROLES = [
    "paper", "card", "ink", "soft", "rule", "hair",
    "accent", "accent-bg", "amber", "amber-bg", "danger", "gold",
]
#: The prefixes the header promises work with every role.
PREFIXES = [
    "bg", "text", "border", "ring", "fill", "stroke", "divide",
    "outline", "caret", "accent", "decoration", "placeholder",
]
#: The project's own classes, as named in the header.
CLASSES = [
    "badge", "badge-gross", "zipfel", "kachel-klickbar", "kachelbild",
    "streifen", "wahl", "feld", "haken", "beschriftung", "klappentext",
    "mehr", "wenn-auf", "wenn-zu", "tun",
]
#: Utilities the header names in prose rather than in the snippet.
PROSE = [
    "font-serif", "shadow-sheet", "pr-16",
    "hover:border-accent", "group-hover:text-accent", "focus-visible:ring-2",
]
SELECTORS = ["svg.i", "[x-cloak]"]
PROPERTIES = ["--color-ink", "--color-rule", "--shadow-sheet"]


def selector(name: str) -> str:
    """A class name as it appears in compiled CSS, where `:` `.` `/` are escaped."""
    escaped = "".join((BS + c) if c in ":./[]" else c for c in name)
    return "." + escaped


def present(css: str, name: str) -> bool:
    return selector(name) in css


def snippet_classes(text: str) -> set[str]:
    """Every class used in the header's example, so the example cannot rot."""
    found: set[str] = set()
    for value in re.findall(r'class="([^"]+)"', text):
        found.update(value.split())
    return found


def main() -> int:
    css = (OUT / "styles.css").read_text(encoding="utf-8")
    tokens = (OUT / "tokens" / "tokens.css").read_text(encoding="utf-8")
    header = CONVENTIONS.read_text(encoding="utf-8")

    import tinycss2

    rules = tinycss2.parse_stylesheet(css, skip_whitespace=True, skip_comments=True)
    errors = [r for r in rules if r.type == "error"]
    print(f"[parse]  {len(rules)} top-level rules, {len(errors)} errors")
    for error in errors[:5]:
        print("        ", error)

    checked: list[str] = [f"{p}-{r}" for r in ROLES for p in PREFIXES]
    checked += CLASSES + PROSE + sorted(snippet_classes(header))
    missing = [name for name in checked if not present(css, name)]
    missing += [s for s in SELECTORS if s not in css]
    missing += [p for p in PROPERTIES if p not in tokens]
    print(f"[names]  {len(checked) + len(SELECTORS) + len(PROPERTIES)} checked, "
          f"{len(missing)} missing")
    for name in missing:
        print("         MISSING:", name)

    # The header tells the agent that `dark:` variants do not exist and must not
    # be written. If one ever appears, that instruction becomes a lie.
    pattern = re.escape(".dark" + BS + ":") + "[a-z0-9-]+"
    strays = sorted(set(re.findall(pattern, css)))
    print(f"[dark]   {len(strays)} `dark:` variants (expected 0)")
    for stray in strays[:5]:
        print("         STRAY:", stray)

    # Both palettes have to survive; the whole point of the build's transform.
    light = "--color-paper: oklch(0.98 0.006 85)" in tokens
    dark = "--color-paper: oklch(0.17 0.008 285)" in tokens
    media = "@media (prefers-color-scheme: dark)" in css
    print(f"[theme]  light={light} dark={dark} media-query={media}")

    ok = not (errors or missing or strays) and light and dark and media
    print("OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
