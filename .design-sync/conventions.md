# Der Buchfink — visual system

A reading-room palette for a personal ebook watchlist: warm paper, ink-brown
text, a teal accent for what the reader chose and an amber one for what is
merely suggested. German UI copy.

## There are no components here

The source application is server-rendered Jinja with htmx and Alpine, so it has
no importable components to ship. **This system is the look only: tokens, a
compiled utility layer, and the handful of classes the project wrote itself.**
Build screens out of plain elements and the classes below.

## Setup

None. Load `styles.css` and write markup — no provider, no wrapper, no theme
class, no initialisation.

**Dark mode is automatic and must not be reimplemented.** The tokens redefine
themselves under `@media (prefers-color-scheme: dark)`, so every utility and
every `var(--color-*)` swaps on its own. There are deliberately **no `dark:`
variants in this stylesheet** — writing `dark:bg-card` produces no rule. Never
add a theme toggle, a `.dark` class, or a second palette.

## The idiom: Tailwind utilities over semantic colour roles

Colour is never literal. Every colour is one of twelve roles, and the role names
are the whole vocabulary — there is no `gray-700`, no `blue-500`, no arbitrary
hex. Each works with any Tailwind colour prefix (`bg-`, `text-`, `border-`,
`ring-`, `fill-`, `stroke-`, `divide-`, `outline-`, `caret-`, `accent-`,
`decoration-`, `placeholder-`), plus `hover:`, `focus-visible:` and
`group-hover:`.

| Role | Meaning |
|---|---|
| `paper` | the page ground |
| `card` | a sheet lying on the page |
| `ink` | body text |
| `soft` | secondary text, captions, metadata |
| `rule` | a visible border |
| `hair` | a barely-there divider |
| `accent` / `accent-bg` | the channel the reader chose herself (author) |
| `amber` / `amber-bg` | the shelf nobody has agreed to yet (topic) |
| `danger` | errors, destructive actions |
| `gold` | ratings, highlights |

So: `bg-card text-ink border border-rule`, `text-soft text-sm`,
`bg-accent-bg text-accent`, `hover:border-accent`.

Two more project tokens: **`font-serif`** (Georgia stack — headings and book
titles; body text stays sans) and **`shadow-sheet`** (the one elevation, for a
card lifted off the paper; it has a light and a dark form). Everything else —
spacing, layout, radii, type scale — is stock Tailwind.

For CSS of your own, use the properties directly: `var(--color-ink)`,
`var(--color-rule)`, `var(--shadow-sheet)`. They resolve in both modes.

## The project's own classes

Real CSS in the stylesheet, usable as-is:

- `.badge` — a 20px round marker meant to sit **on** a cover: set the background
  to a role colour, put a stroked `<svg>` inside. `.badge-gross` is the 28px
  variant for the book page. `.zipfel` nudges an asymmetric glyph back to centre.
- `.kachel-klickbar` — a tile that is entirely a link; the border takes
  `currentColor` on hover. `.kachelbild` is its faint watermark icon, absolutely
  placed right-centre (leave room with `pr-16`).
- `.streifen` — a horizontally scrolling, snapping row of cover choices.
  `.wahl` wraps one radio choice inside it, with `.feld` (the ringed frame),
  `.haken` (the tick) and `.beschriftung` (the caption). Unpicked covers
  desaturate once a choice is made.
- `.klappentext` — a `<details>` blurb clamped to five lines, with a `.mehr`
  element whose label flips between "mehr anzeigen" and "weniger anzeigen".
- `.wenn-auf` / `.wenn-zu` — inside a `<summary>`, show content only when the
  `<details>` is open / closed.
- `svg.i` — sprite icons; they inherit `1em` size and `currentColor`.
- `.tun` — an action; gets a 44px minimum height on touch devices.

## Read before styling

`_ds/<folder>/tokens/tokens.css` is the whole palette in twenty readable lines,
both modes. `_ds/<folder>/styles.css` is the compiled sheet — grep it to confirm
a utility exists before relying on it.

## A screen, idiomatically

```html
<main class="bg-paper text-ink max-w-3xl mx-auto p-6 flex flex-col gap-4">
  <h1 class="font-serif text-3xl">Beobachtete Bücher</h1>

  <article class="bg-card border border-rule rounded-lg p-4 shadow-sheet
                  flex gap-4 items-start">
    <img src="…" alt="" class="w-16 rounded-md border border-hair">
    <div class="flex flex-col gap-1">
      <h2 class="font-serif text-lg">Die Vermessung der Welt</h2>
      <p class="text-soft text-sm">Daniel Kehlmann · 2005</p>
      <span class="bg-accent-bg text-accent text-xs rounded-full px-2 py-0.5">
        Autor:in
      </span>
    </div>
  </article>
</main>
```
