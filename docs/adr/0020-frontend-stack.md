# 20. Frontend stack: Tailwind, Alpine, and a build step after all

Amends ADR 3, which said "no frontend build step". There is one now, and it
runs at development time only.

## Context

ADR 3 chose FastAPI, Jinja and HTMX and ruled out a build step. That was
decided before a single screen existed. One screen later the picture is
clearer:

- The Dashboard's styling is about forty lines of hand-written CSS inlined in
  the base template. The triage prototype needed roughly two hundred.
- Seven more screens are planned — watchlist, book page, triage, profile,
  run-now, plus what those pull in.
- Hand-written CSS across seven screens, inlined in templates, with no shared
  vocabulary, is how a codebase ends up with four slightly different card
  styles and nobody willing to touch any of them.

The reader's instruction was to do this properly rather than half-way, and to
follow common practice. That settles it: ad-hoc CSS scaling to seven screens
is the half-way option, not the disciplined one.

## Decision

### Tailwind CSS, built by a standalone binary, no Node

`pytailwindcss` installs the official Tailwind standalone executable through
pip, so it joins the project the same way `ruff` and `pytest` do — a
development dependency in `pyproject.toml`, resolved by `uv`. No Node, no
`package.json`, no `node_modules`.

The build runs at development time and produces one static stylesheet. The
machine that runs the tool serves that file and builds nothing; ADR 3's real
intent — that a Pi Zero W never runs a toolchain — is preserved. What changes
is that a developer now runs one command before committing.

The Tailwind Play CDN was rejected. It ships a compiler to the browser, it is
explicitly not for production, and it is a third-party request on every page
load — which contradicts the decision taken about covers, that nothing on these
pages tells an outside party what the reader is looking at.

### Alpine.js for browser state, HTMX for server state

The two have a clean division, and stating it is the point of naming both:

> **HTMX** when the server owns the answer — a row is dismissed, a book is
> watched, a Run is started. The server re-renders the fragment.
> **Alpine** when nothing outside the browser cares — which rows are ticked,
> which panel is open, keyboard navigation through a stack.

Bulk triage is the case that needs both: Alpine holds the selection, HTMX posts
it and swaps in the result.

Both are vendored into the static directory and pinned, not loaded from a CDN.
Same reason as above, plus the tool then works on a network that cannot reach
out at all.

### Design tokens are Tailwind's, not a second system

Colours, spacing and type scale live in the Tailwind theme. The prototype's
custom properties were a stand-in for exactly that and are replaced rather than
kept alongside — two token systems is worse than either.

Dark mode stays media-query driven, as it is today.

### Icons stay an inline SVG sprite

No icon font, no CDN, no per-icon request. The sprite lives in the base
template and icons are referenced by id.

## Consequences

- `uv run tailwindcss` becomes part of the development loop, and the built
  stylesheet is committed so a checkout can be served without building.
- CI has to fail when the committed stylesheet does not match its sources,
  otherwise it silently goes stale.
- ADR 3's "no build step" no longer holds literally. Its substance — no
  websocket, no client-side framework owning the page, server-rendered HTML —
  does.
- Alpine is a client-side framework in the narrow sense. It is bounded to
  ephemeral view state by the rule above; the moment application state starts
  living in Alpine rather than the database, this decision has been misused.
- The prototype's hand-written CSS is a throwaway and does not migrate.
