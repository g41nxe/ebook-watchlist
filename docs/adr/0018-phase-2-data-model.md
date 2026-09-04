# 18. Phase 2 data model

Supersedes the table sketch in ADR 5 for everything except `run` and
`observation`, which survive largely intact.

## Context

Phase 2 moves configuration out of YAML and into the database (ADR 3, ADR 10).
ADR 5 sketched those tables before Phase 1 was built, and running the tool
against real data for a day showed the sketch no longer fits.

Four separate files had grown up around the same books. *Cold Eternity* lived in
`owned.yaml` as a title and author, in `dismissed.yaml` as beam product id
`1067554`, and had been a row in `watchlist.yaml`. Marking one book as already
owned took two edits in two formats, and the dismissal only covered one shop —
the Onleihe would have offered it again. `liked_books` held free text
("Cry Baby - Gillian Flynn") that nothing could match against anything.

The unifying observation is that all of these say something about *a book*, and
what differs is only the relationship the reader has to it.

## Decision

### The book is first class, and it exists only with a relationship

```sql
book   id, isbn, title, author, series, created_at
       UNIQUE (isbn)
```

A row is created when a relationship is formed — watched, owned, liked,
disliked, dismissed — never for a bare discovery. A discovery stays what it is
today: an Observation keyed by `(source, source_item_id)`.

The alternative, a row per discovered item, was rejected: 243 items came in on
the first real Run, most of them duplicates of each other across sources and
editions, and a table called `book` whose majority is unvetted duplicates does
not deserve the name. Every book creation therefore looks for an existing match
first; the table holds dozens of rows, so that lookup is free.

### Identity is the ISBN where there is one

Verified against both live sources: *Die sieben Schwestern* carries ISBN
`9783641117009` at the Onleihe **and** at beam-shop. Both stock the same
publisher's ebook edition, so the identifier links them exactly, with no fuzzy
comparison at all.

beam exposes it for free in the tile's order number (`SW` + ISBN-13); 40 of 48
tiles in a real result page carried a valid one. The Onleihe states it as an
`ISBN:` row in the same labelled block we already parse for `Autor*in:` and
`Reihe:`.

Where no ISBN exists — 8 of those 48, being bundles, collections and single
episodes — identity falls back to the matcher and its confidence gate (ADR 8).

An ISBN identifies an *edition*, not a work — and the fallback is not an edge
case. Measured across the books this watchlist has at both sources:

| Title | beam | Onleihe | |
|---|---|---|---|
| Der Ruf des Kuckucks | `9783641130008` | `9783641130008` | same edition |
| Der Knochenjäger | `9783641157180` | `9783837110951` | different editions |

One of two. The ISBN is therefore a strong identifier where two sources happen
to stock the same edition, not a general key across them; the matcher and its
confidence gate carry the rest and will keep doing so.

> **Nachtrag aus der Umsetzung (Ticket 04):** Beide Fälle landen korrekt auf
> *einer* Buch-Zeile — der Matcher fängt den zweiten ab. Damit trägt
> `book.isbn` aber die ISBN **einer** der beiden Ausgaben, nämlich der zuerst
> beobachteten: *Der Knochenjäger* steht unter `9783837110951` (Onleihe),
> obwohl beam ihn als `9783641157180` führt. Das ist hinnehmbar, solange die
> ISBN als *Identität* dient und nicht als Behauptung darüber, welche Ausgabe
> die Leserin bekommt — welche das ist, sagt `book_source`. Sobald eine
> Metadatenquelle das Werk kennt (Ticket 13), gehört die Werkebene dorthin und
> nicht auf die Ausgabe.

> **Nachtrag:** Titel, Autor:in, Reihe und Cover auf der `book`-Zeile stammen
> aus einer Metadatenquelle, nicht aus dem Shop, der das Buch zufällig zuerst
> gelistet hat. Was ein Shop daraus macht — `Jo Nesbø`, `Jo Nesbo` und
> `Nesbø, Jo` stehen alle im heutigen Snapshot — bleibt auf `book_source`.
> Der Matcher rät sonst an etwas herum, das eine Metadatenquelle schlicht
> weiß. Welche Quelle das leisten kann, klärt die Recherche (Ticket 13);
> bis dahin bleibt die Herkunft offen, die Trennung nicht.

### One table for every relationship

```sql
book_relation   profile_id, book_id, kind, active, details, created_at
                UNIQUE (profile_id, book_id, kind)
```

`kind` is `watching`, `owned`, `liked`, `disliked`, `dismissed` — and several
hold at once, which is the normal case rather than the exception: *Cold Eternity*
is owned **and** was watched. A single status column could not have expressed it.

Relations are **deactivated, not deleted**. Removing *Providence* from the
watchlist today destroyed the fact that it was ever watched; `active = false`
keeps it — "watched until you bought it".

### The link to a source, including its absence

```sql
book_source   book_id, source, source_item_id, url, resolved_at, details
              PK (book_id, source)
```

One row per source: the Onleihe's title id and beam's product id are different
values for the same book, so they are different rows, not competing keys in one
bag.

A row with no `url` is not a contradiction but an answer — "searched here, not
stocked". Eight of the reader's ten watchlist titles are in that state at the
Onleihe, and the row is what stops them being searched for again every day.

`details` carries the outcome (`linked`, `confirmed`, `unsure`, `not_found`),
the reason, and the title and author *as that source rendered them* — the last
two exist so a wrong automatic resolution stays visible in the Digest (ADR 9).

### Authors and shelves are the same thing

```sql
interest          profile_id, key, value, active, details, created_at
                  UNIQUE (profile_id, key, value)
interest_seeded   interest_id, source, seeded_at
```

A Reference Author and a Genre Category both answer one question: *where should
the tool look for new books for me.* They are the two discovery channels, and
they produce the two discovery Match Reasons. `key` is free text so a third
channel — publisher, series, keyword — costs a handler, not a migration.

`tier` (`core` / `extended`) turned out not to be author-specific at all; a shelf
could equally be swept weekly. It lives in `details`.

`interest_seeded` replaces `seeded_scope` and fixes a defect found while
documenting it: the old key `(source, match_reason, category)` left `category`
empty for authors, so **all** authors shared one scope. Adding a Reference Author
therefore reported their whole backlist as new arrivals, while adding a shelf
seeded silently. Keyed per interest, both behave the same.

### The source table holds state, not a catalogue

```sql
source   name, enabled, last_probe_at, last_probe_ok,
         last_error, consecutive_failures, updated_at
```

Selectors, paths and base URLs stay with the parser they are versioned and
tested with — a selector in a database would let someone break the parser
without touching code. What the table holds is what running produces: the
`doctor` probe result, which is currently printed and thrown away, and an
`enabled` switch so a broken source can be paused without editing a file.

Rows are never entered by hand; one appears when a source first runs.

### Columns steer, bags remember

Three tables share a shape — keys, the few columns that steer behaviour, and a
JSON `details` bag:

```
book_source     book_id, source | url, resolved_at | details
book_relation   profile_id, book_id, kind | active | details
interest        profile_id, key, value | active    | details
```

> **Column** when the database filters or sorts on it, or when a typo would
> silently change behaviour. **Bag** for what is merely remembered and shown.

Displaying a value needs no column — the row is loaded anyway. A key/value table
was considered and rejected: it gives no more validation than JSON, loses types,
and turns loading one relation into a join and a reassembly.

### Constraints live in the loader, not the schema

`interest.key`, `book_relation.kind` and `source` are free text validated
against the registry of handlers that can act on them. A key nothing handles is
a configuration error and must fail loudly at load — an interest filed under
`autor` would otherwise never be swept, and nothing would say so.

The `details` bags are validated per kind for the same reason: `tier: "extendet"`
would quietly promote a weekly author to the daily list, and `activ: false`
would be ignored entirely.

### Observation keeps recording what was *seen*

```sql
observation   ... book_id, isbn, hold_state, hold_expected_date ...
```

- `book_id` (nullable) replaces `watchlist_key`: set for watchlist checks, NULL
  for discoveries. Without it a library availability report has no referent.
- `isbn`, `title` and `author` are stored even when `book_id` is set. The
  Observation records what the source said at that moment; the book record is
  what we believe. If a source silently switches editions under the same product
  id, the divergence is visible only because both are kept.
- `hold_state` and `hold_expected_date` move here from `watchlist_entry`
  (ADR 6). A hold *is* observed — v2 reads it off the account page — so the
  `placed` to `ready` transition falls out of the existing diff machinery
  instead of needing its own code, and it gains history.
- Everything is keyed on `profile_id`, not `profile_slug`. The old mix would
  have made joins impossible.

### Not stored

`normalized_title` and `normalized_author` are computed at query time. The
normalisation rules changed twice in a single day; stored values would have gone
quietly stale and the matcher would compare against a rule nobody uses any more.
With dozens of books the cost is unmeasurable.

## Consequences

- Four YAML files and five tables become four concepts: **Profile**, **Book**,
  **Relation**, **Observation**.
- Marking a book as owned becomes one act, and it suppresses suggestions at
  *every* source rather than one shop.
- Dismissing a genre suggestion now creates a book row. That is more work per
  click than the old id list, and it is the price of source-independent
  suppression.
- `book_source` allows one item per book per source. Where a shop lists two
  equivalent editions — *Trigger* by Wulf Dorn does — one is chosen, and the
  confidence gate asks rather than guessing. Tracking several editions would
  need a manifestation layer, which is one layer more than a personal tool earns.
- The import from today's YAML is not trivial and gets its own ticket:
  `liked_books` is free text that has to be resolved to book rows, and the same
  confidence gate applies — what cannot be resolved goes to "needs attention"
  rather than being guessed.
- `docs/leseprofil.md` stays a repo file with its own change procedure (ADR 17).
  A web form editing it would bypass that procedure entirely.
