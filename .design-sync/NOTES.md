# design-sync notes

Findings worth keeping between syncs. Corrections belong in `config.json` when
they map to a setting, and here when they do not.

## This repo has no components to sync

The interface is server-rendered Jinja with htmx and Alpine (ADR 20), so there
is nothing importable to hand a design agent. The sync therefore carries the
look only — tokens, the compiled utility layer, and the project's own classes.
`shape` is `css-only`; neither of the skill's two shapes (storybook, package)
applies, and there is no `dist/`, no `package.json` and no `_ds_bundle.js`.

## The dark palette was overwriting the light one at build time

Tailwind v4 does **not** support `@theme` nested inside `@media`. It hoists the
declarations into the single `:root` block and discards the condition, so the
dark `@theme` in `assets/app.css` silently overwrote the light one. Confirmed
against the shipped `web/static/app.css`: every token appears exactly once with
its dark value, no light value appears anywhere, and the file contains no
`prefers-color-scheme` rule at all.

**Fixed at the source.** `assets/app.css` now uses `:root` inside the media
query, which is the v4-correct idiom — utilities compile to `var(--color-paper)`,
so overriding the property is enough. The rebuilt `static/app.css` carries both
palettes and one `prefers-color-scheme` rule.

`build.py` keeps its transform as a guard and now reports "source already uses
`:root`", so it costs nothing and catches a regression if the nested form ever
comes back.

Shadows needed separate handling: Tailwind resolves `--shadow-*` theme keys at
build time and inlines them into `.shadow-sheet`, never emitting
`--shadow-sheet`, so there is no property left for a `:root` block to override.
`app.css` therefore restates the dark shadow as an explicit unlayered rule.
`styles.src.css` used to carry a copy of it; that was dropped once the source
had its own, because the two compiled into the sheet twice.

## Tailwind scans the repository, including prose

Automatic source detection reads every non-gitignored file, so a class name
merely *mentioned* in `conventions.md` becomes a real rule — `dark:bg-card`,
named there as the thing an agent must not write, was compiled into the sheet.
`styles.src.css` excludes `.design-sync` and `ds-bundle`; `validate.py` asserts
no `dark:` variant survives.

## The venv was broken on arrival

`.venv` points at a uv-managed interpreter that no longer exists, and `uv sync`
cannot replace it because something holds `.venv/Lib` open. Untouched. The sync
uses an isolated `uv tool install pytailwindcss` instead.

## The Bash tool eats backslashes in heredocs

Writing these scripts through a shell heredoc silently dropped one backslash
per escape, corrupting two regexes in `validate.py`. Both now build the
backslash with `chr(92)`. Worth remembering when editing them.
