# Calibre metadata-matching rules (research spike for ADR 0008)

Goal: lift concrete, reusable rules from Calibre's metadata code so we can port the
*ideas* (not the code) into a small Python normalize-then-fuzzy matcher built on
`rapidfuzz`. Everything below is cited by file. Calibre is GPLv3, so we do **not**
copy code — we re-implement the heuristics.

Sources read (all under `github.com/kovidgoyal/calibre/master/src/calibre/`):

- `ebooks/metadata/__init__.py` — `title_sort`, `string_to_authors`,
  `author_to_author_sort`, `get_title_sort_pat`, `normalize`.
- `ebooks/metadata/sources/base.py` — `Source.get_title_tokens`,
  `Source.get_author_tokens`, `cleanup_title`, `clean_downloaded_metadata`,
  `fixcase`/`fixauthors`, and `InternalMetadataCompareKeyGen` (the per-source
  relevance sort key).
- `ebooks/metadata/sources/identify.py` — `identify()` flow, `ISBNMerge`,
  `merge_metadata_results`, `average_source_relevance` ranking.
- `utils/icu.py` — collation strength concept only.

Key finding up front: **Calibre does no fuzzy string matching (no Levenshtein /
SequenceMatcher / soundex) anywhere in the identify pipeline.** Its "matching" is
(a) aggressive normalization into token streams that get sent to each source as an
AND query, and (b) a deterministic multi-key sort of the returned candidates.
Equality checks (`cleanup_title`, lowercased title+authors) are exact-after-
normalization. The fuzzy layer is ours to add; Calibre gives us the normalization
recipe and the ranking-key design.

---

## 1. Title normalization

Calibre has **three** different title transforms with different jobs. Pick per use:

### 1a. `cleanup_title(s)` — the equality/coarse-key normalizer (`sources/base.py`)

Used by `InternalMetadataCompareKeyGen` to decide "exact title match" and by
dedup grouping. This is the one closest to what we want for the normalized-exact
rung of our match ladder.

Module-level regexes (quoted verbatim):

```python
words = ('the', 'a', 'an', 'of', 'and')
prefix_pat        = re.compile(r'^(%s)\s+' % ('|'.join(words)))   # ^(the|a|an|of|and)\s+
trailing_paren_pat = re.compile(r'\(.*\)$')
whitespace_pat     = re.compile(r'\s+')
```

Steps, in order:

1. If empty, substitute the localized string for `Unknown`.
2. `s = s.strip().lower()`
3. `s = prefix_pat.sub(' ', s)` — drop a **single** leading article/preposition
   (`the a an of and`). Note: leaves a leading space, cleaned in step 5.
4. `s = trailing_paren_pat.sub('', s)` — drop one trailing `(...)` group at end of
   string (greedy `\(.*\)$`, so it eats from the first `(` to the last `)`).
5. `s = whitespace_pat.sub(' ', s)` then `.strip()`.

What it does **not** do: no accent folding, no `ß`→`ss`, no punctuation stripping
beyond the trailing paren, no subtitle/`:` handling, no bracket `[...]` handling,
only ONE leading article removed (not recursive).

### 1b. `Source.get_title_tokens(title, strip_joiners=True, strip_subtitle=False)` — the search-query tokenizer (`sources/base.py`)

Produces the token list Calibre feeds to a source's search API. Much more
aggressive. Regexes verbatim:

```python
# optional subtitle strip (only if strip_subtitle=True):
subtitle = re.compile(r'([\(\[\{].*?[\)\]\}]|[/:\\].*$)')
#   -> removes any (...) [...] {...} group, OR everything from the first / : \ to EOL

title_patterns = [
    # Remove things like: (2010) (Omnibus) etc.
    (r'(?i)[({\[](\d{4}|omnibus|anthology|hardcover|audiobook|audio\scd|paperback|turtleback|mass\s*market|edition|ed\.)[\])}]', ''),
    # Remove any bracketed string containing the substring "edition"/"ed."
    (r'(?i)[({\[].*?(edition|ed.).*?[\]})]', ''),
    # Join digit groups split by comma: 1,000 -> 1000
    (r'(\d+),(\d+)', r'\1\2'),
    # Remove hyphens only if preceded by whitespace
    (r'(\s-)', ' '),
    # Replace remaining punctuation / separators with a space:
    (r'''[:,;!@$%^&*(){}.`~"\s\[\]/]《》「」“”‘’''', ' '),
]
```

Then `tokens = title.split()`; each token is `.strip().strip('"').strip("'")`;
and if `strip_joiners` (default True) the tokens `a and the &` are dropped
(case-insensitive).

Notably `strip_subtitle` defaults to **False** — Calibre keeps subtitles in the
search query by default and relies on the source's own relevance. For our matcher
we want the opposite (strip subtitle noise before compare).

### 1c. `title_sort(title, order, lang)` — article-to-suffix mover (`__init__.py`)

This is the "The Hobbit" → "Hobbit, The" transform, used for sort order, not
matching. Body verbatim:

```python
title = title.strip()
if order == 'strictly_alphabetic': return title
# strip one matching pair of surrounding quotes (quote_pairs incl. “” «» etc.)
match = get_title_sort_pat(lang).search(title)
if match:
    prep = match.group(1)
    if prep:
        title = title[len(prep):] + ', ' + prep
        # strip surrounding quotes again
return title.strip()
```

`get_title_sort_pat` default (English) verbatim:

```python
ans = re.compile(r'^(A|The|An)\s+', re.IGNORECASE)
```

Language-aware: articles come from `tweaks['per_language_title_sort_articles']`
(e.g. German adds `der|die|das|den|dem|des|ein|eine|...`). Pattern is
`^(art1|art2|...)` joined with `|`, `re.IGNORECASE`, cached per language.

**For our matcher:** don't *move* the article to a suffix — just *drop* leading
articles (as `cleanup_title` does). But steal the per-language article list idea:
German titles need `der/die/das/ein/eine` stripped, not just English `the/a/an`.

### Number handling

Only two number rules exist, both in `get_title_tokens`:
`1,000` → `1000` (strip thousands separators), and `(2010)` as a bracketed
4-digit year gets removed. There is **no** roman-numeral ↔ arabic normalization
and no digit-word normalization anywhere. If we want "Part 2" == "Part II" we
build it ourselves.

### Title normalization checklist to implement

- [ ] NFKD + strip combining marks (Calibre does NOT; we want it — see §5).
- [ ] `ß` → `ss`, other language-specific folds (Calibre does NOT).
- [ ] lowercase.
- [ ] Drop bracketed year / edition / format groups:
      `(?i)[({\[](\d{4}|omnibus|anthology|hardcover|audiobook|audio\scd|paperback|turtleback|mass\s*market|edition|ed\.)[\])}]`
      and `(?i)[({\[].*?(edition|ed\.).*?[\]})]`.
- [ ] Drop trailing `(...)` / `[...]` group: `[\(\[].*[\)\]]$` (anchor to end;
      Calibre only does parens, we add brackets per ADR 0008).
- [ ] Cut subtitle: everything after the first ` - `, ` — `, ` / `, ` : ` /
      ` \ ` — Calibre's `[/:\\].*$` plus our ` - `/` — ` dashes. Guard: only cut
      if the remainder is still non-trivial (`len(subtitle.sub('', title)) > 1`
      in Calibre).
- [ ] `1,000` → `1000`.
- [ ] Replace punctuation with space:
      `[:,;!@$%^&*(){}.`~"\s\[\]/《》「」“”‘’]` (plus the ` -` hyphen rule).
- [ ] Drop leading article(s) — extend Calibre's `^(the|a|an|of|and)\s+` with
      German articles; consider looping so "The The The" collapses (Calibre
      doesn't loop).
- [ ] Drop known format/edition word tokens anywhere:
      `ebook`, `ungekürzt`, `gekürzt`, `hörbuch`, `audiobook`, `omnibus`, ...
      (extend Calibre's bracketed list to bare tokens).
- [ ] collapse whitespace, strip.
- [ ] Optionally drop join-word tokens `a and the & und` before fuzzy compare.

---

## 2. Author normalization

### 2a. `string_to_authors(raw)` — split a multi-author field (`__init__.py`)

Verbatim:

```python
_author_pat = re.compile(r'(?i),?\s+(and|with)\s+')   # default; tweakable
...
raw = raw.replace('&&', '￿')          # protect literal '&&'
raw = _author_pat.sub('&', raw)            # "X and Y", "X, with Y" -> "X&Y"
authors = [a.strip().replace('￿', '&') for a in raw.split('&')]
return [a for a in authors if a]
```

Delimiters Calibre recognizes: `&`, and the words `and` / `with` (case-insensitive,
optionally preceded by a comma). It does **not** split on a bare `;` or a bare `,`
(a lone comma is treated as "Last, First", not a separator). `&&` is an escape for
a literal ampersand in a name.

**For our matcher (per ADR 0008)** we additionally split on `;` and German `und`,
and must be careful: a bare `,` is ambiguous (separator vs. "Last, First"). Safe
rule: only treat `,` as a separator when there are ≥2 commas or when a segment
already looks like "First Last". Otherwise treat a single `,` as sort-order.

### 2b. `author_to_author_sort(author)` — "First Last" → "Last, First" (`__init__.py`)

Steps:

1. Empty → `''`. Method `'copy'` → return unchanged.
2. Strip bracketed text; if a comma is already present, assume already sorted →
   return as-is.
3. Tokenize on whitespace. `< 2` tokens → return as-is.
4. If any token matches `author_name_copywords` (company/organisation words like
   `Corporation, Company, Co., Agency, Council, Committee, Inc., Institute,
   Society, Club, Team`) → return as-is (it's an org, not a person).
5. Build `prefixes` from `tweaks['author_name_prefixes']`
   (`Mr Mrs Ms Dr Prof`, plus each with a trailing `.`) and `suffixes` from
   `tweaks['author_name_suffixes']` (`Jr Sr Inc Ph.D Phd MD M.D I II III IV
   Junior Senior`, plus trailing-`.` variants), lowercased.
6. Find the last "real" token index `last` (skipping trailing suffix tokens);
   `first` is 0 (skipping leading prefix tokens).
7. Reorder: `atokens = tokens[last:last+1] + tokens[first:last]` (i.e.
   `[surname] + [given names/middle]`), suffixes appended after; a comma is
   inserted after the surname.
   → `"Arthur Conan Doyle"` → `"Doyle, Arthur Conan"`;
   `"Dr John Smith Jr"` → `"Smith, John"` (+ `Jr`).

`authors_to_sort_string(authors)` = `' & '.join(author_to_author_sort(a) ...)`.

### 2c. `Source.get_author_tokens(authors, only_first_author=True)` — author search tokens (`sources/base.py`)

Verbatim regexes + logic:

```python
remove_pat  = re.compile(r'[!@#$%^&*()（）「」{}`~"\s\[\]/]')
replace_pat = re.compile(r'[-+.:;,，。；：]')
# only first author by default
for au in authors:
    has_comma = ',' in au
    au = replace_pat.sub(' ', au)     # punctuation -> space
    parts = au.split()
    if has_comma:                     # "Last, First ..." -> rotate last chunk to front
        parts = parts[1:] + parts[:1]
    for tok in parts:
        tok = remove_pat.sub('', tok).strip()
        if len(tok) > 2 and tok.lower() not in ('von', 'van', 'unknown'):
            yield tok
```

Reusable heuristics:

- **Comma ⇒ "Last, First"**: if the string contains a comma, rotate the first
  comma-delimited chunk (the surname) to the end to get first-name-first order.
  (`get_author_tokens` rotates `parts[1:] + parts[:1]` after replacing the comma
  with a space — slightly lossy for multi-word surnames, but a good default.)
- **Drop name-particle tokens** `von`, `van` (and we should add `de`, `der`,
  `di`, `del`, `la`, `le`) so "Ludwig von Mises" matches "Ludwig Mises".
- **Drop tokens ≤ 2 chars** — kills initials (`J.`, `R.`) and noise. Good for
  token-set fuzzy compare; risky for exact compare of CJK names, but fine for us.
- **Drop the literal `Unknown`.**
- **`only_first_author=True`** — for search Calibre compares on the first author
  only. We should compare against *all* our reference authors but can weight the
  first-listed author highest.

### Author normalization checklist to implement

- [ ] NFKD + strip diacritics; `ß`→`ss`; lowercase.
- [ ] Split multi-author field on `;`, `&`, ` and `, ` with `, ` und `
      (case-insensitive), guarding the ambiguous bare `,`.
- [ ] Per author: if it contains a comma and looks like "Last, First", swap to
      "First Last".
- [ ] Strip bracketed text, trailing role markers (`(Übersetzer)`, `(ed.)`).
- [ ] Drop honorific prefixes (`dr prof mr mrs ms`) and generational suffixes
      (`jr sr ii iii iv phd md`).
- [ ] Drop nobiliary particles (`von van de der di del la le du`) as tokens.
- [ ] Return to org-name early if it matches company copywords (don't reorder).
- [ ] Produce a normalized token set; keep initials only for a secondary looser
      compare.

---

## 3. Ranking / relevance

Two layers.

### Layer A — per-source result ordering: `InternalMetadataCompareKeyGen` (`sources/base.py`)

An `@total_ordering` class turned into a sort key; ascending sort ⇒ most relevant
first. Docstring lists the priority order; `__init__` builds
`self.base = (same_identifier, has_cover, all_fields, language, exact_title)` —
a tuple of small ints where **1 beats 2** — plus two tie-break scalars.

Fields, highest priority first:

1. **`same_identifier`** — `1` if the candidate shares any identifier (ISBN,
   goodreads id, ...) with the query, else `2`. Strongest signal.
2. **`has_cover`** — `1` if the source has a reliable cached cover URL for it,
   else `2`. (A "this is a real, well-populated record" proxy — not relevant to
   us.)
3. **`all_fields`** — `1` if `source_plugin.test_fields(mi)` reports no missing
   required field, else `2`. Prefer complete records.
4. **`language`** — `1` if the candidate language is undefined or equals the UI
   language, `2` if it's a *different* defined language. Penalize wrong-language
   hits.
5. **`exact_title`** — `1` if `cleanup_title(query_title) == cleanup_title(mi.title)`,
   else `2`. Note: this is exact-after-normalization, binary, not graded.

Then tie-breakers in `compare_to_other`:

6. **`comments_len`** — longer blurb wins, but only if the difference exceeds
   `(cx + cy) / 20` (~10% of the mean). Ignore tiny differences.
7. **`extra`** = `mi.source_relevance` — the position the source's own search
   engine returned it at (0 = first). Final fallback.

Design points to steal:

- Ranking key is a **lexicographic tuple of cheap comparable fields**, not a
  weighted sum. Each field is a tiny enum. Deterministic, debuggable, no magic
  weights.
- Identifier match dominates everything. If we ever have an ISBN/ASIN on both
  sides, that alone should decide.
- Title match is **binary exact-after-normalization** here — the graded/fuzzy
  part is entirely the search engine's `source_relevance`. We are adding a fuzzy
  score, so our tuple looks like:
  `(id_match, title_exact, author_exact, fuzzy_bucket, year_delta, source_rank)`
  where `fuzzy_bucket` is e.g. `floor(score/5)` so near-ties fall through to the
  next key.
- "Only compare within one source" — Calibre explicitly says this key is not
  valid across sources (see Layer B).

Interesting omissions: **year and publisher are NOT in the key** despite the task
hypothesis. Calibre does not rank on publication year or publisher at all in the
identify pipeline. (Year is used elsewhere only as a display/merge detail.)

### Layer B — cross-source merge & final order: `identify.py`

`identify()` collects results from every plugin, tags each with
`result.relevance_in_source = i` (its index after the per-source sort above),
then:

- **`ISBNMerge` / `merge_metadata_results(merge_on_identifiers=False)`** groups
  results with **identical lowercased title AND identical lowercased author
  tuple**:

  ```python
  title = lower(result.title or '')
  key = (title, tuple(lower(x) for x in result.authors))
  ```

  (Optionally also merges groups that share an identifier.) `xisbn` was an
  external "same work, different ISBN" service — **now decommissioned, dead code**;
  don't port it.

- Within a merged group, fields are filled in from whichever source has them; the
  group's rank is the **mean** of member ranks:

  ```python
  avg = sum(x.relevance_in_source for x in results) / len(results)
  ans.average_source_relevance = avg
  ```

- Final: `self.results.sort(key=attrgetter('average_source_relevance'))`.

So cross-source ranking is purely "agreed-upon by multiple sources AND ranked
highly by each" → averaged position. There is **no fuzzy cross-source title
reconciliation** — if two sources spell the title differently they simply don't
merge and compete as separate candidates.

### Ranking algorithm for our matcher (rapidfuzz)

Given a query `(title, authors[])` and candidate `(title, authors[])`:

1. Normalize both sides per §1 and §2.
2. `id_match` = 1 if any shared strong identifier (ISBN-13/ASIN), else 0.
3. `title_exact` = 1 if `norm(qtitle) == norm(ctitle)`.
4. `title_fuzzy` = `rapidfuzz.fuzz.token_set_ratio(norm(qtitle), norm(ctitle))`
   (0–100). token_set is right here because it's order- and duplicate-insensitive
   and shrugs off leftover subtitle words.
5. `author_exact` = 1 if normalized author token-sets intersect on a full name;
   `author_fuzzy` = best `token_set_ratio` over query-author × candidate-author
   pairs (compare against *all* our reference authors, not just the first).
6. `year_delta` = `abs(qyear - cyear)` if both known else a large sentinel — used
   only as a **late tie-breaker** (Calibre doesn't even do this; we add it
   because scrape data has year and it disambiguates reissues).
7. Sort key (ascending = best), each element chosen so 0/low = better:

   ```
   (
     0 if id_match else 1,
     0 if title_exact else 1,
     -(title_fuzzy // 5),          # 5-point buckets, so near-ties defer
     0 if author_exact else 1,
     -(author_fuzzy // 5),
     year_delta,
     source_rank,                  # position the source returned it at
   )
   ```

8. Best candidate = min by this key.

---

## 4. Confident vs. ambiguous

Calibre's identify pipeline has **no numeric confidence threshold and no
"ambiguous, ask the user" branch.** It always returns the full ranked list and
lets the GUI show all of them for the user to pick. The only gating that exists:

- **`abort` / timeout**: sources are given a time budget
  (`abort.set()` after `msprefs['wait_after_first_result']` once at least one
  result is in). Not a confidence mechanism.
- **Dedup**: exact (title, authors) duplicates within a source are dropped before
  ranking:

  ```python
  key = (r.title, tuple(r.authors))
  if key not in filter_results: filtered_results.append(r)
  ```

- **`test_fields`**: a result missing a *required* field is de-prioritized (bucket
  `all_fields = 2`), not discarded.

So Calibre gives us the *ordering* recipe but not the *accept/reject* line — that
is entirely our design (ADR 0008 + ADR 9). Recommended, built on the key above:

- **Confident (auto-accept, ADR 9 gate):** `id_match`, OR
  (`title_exact` AND `author_fuzzy >= 90`), OR
  (`title_fuzzy >= 95` AND `author_exact`).
- **Ambiguous (surface for confirmation):** top candidate is provisional if
  `title_fuzzy` in ~[85, 95) or author only fuzzy-matches; **also** flag as
  ambiguous when the #1 and #2 candidates are within a small margin on the sort
  key (e.g. `title_fuzzy` within 3 points AND same author bucket) — the
  "close results" case Calibre punts to the GUI. Borrow Calibre's ~10% relative
  margin idea from `comments_len` (`(cx+cy)/20`) for "are these two scores
  effectively tied".
- **No match:** `title_fuzzy < ~85` (or `< 90` token_set per ADR 0008) and no id.

---

## 5. Accent- / case-insensitive comparison

### What Calibre does (`utils/icu.py`)

Calibre wraps ICU collators and exposes helpers at graded **collation strength**:

- **Primary strength** — ignores case *and* accents *and* most punctuation
  (`a` == `A` == `á` == `à`). Used for "loose" equality / search matching.
- **Secondary strength** — accent-sensitive but still case-insensitive
  (`a` == `A` but `a` != `á`).
- **Tertiary** — the default, case- and accent-sensitive.

Functions like `primary_contains`, `primary_find`, `primary_sort_key`,
`primary_no_punctuation_*` build a transform key at primary strength and compare
those. This is locale-aware (correct handling of `ß`, `Æ`, Turkish dotless-i,
CJK ordering, etc.) — better than naive stripping, at the cost of the ICU
dependency.

Note: the **identify pipeline does not use ICU primary compare** — it uses plain
`str.lower()` and the regex normalizers above. ICU primary compare is used in
library search / sorting. So we are not obliged to match ICU behavior for the
matcher.

### Pure-Python equivalent (what we implement)

```python
import unicodedata, re

_COMBINING = re.compile(r'[̀-ͯ]')

def fold(s: str) -> str:
    # NFKD splits base + combining marks; drop the marks; also handles ﬁ, ², etc.
    s = unicodedata.normalize('NFKD', s)
    s = _COMBINING.sub('', s)
    # language folds NFKD misses:
    s = s.replace('ß', 'ss').replace('ẞ', 'ss')
    s = s.replace('ø', 'o').replace('Ø', 'O')
    s = s.replace('ł', 'l').replace('Ł', 'L')
    s = s.replace('æ', 'ae').replace('Æ', 'AE')
    s = s.replace('œ', 'oe').replace('Œ', 'OE')
    s = s.replace('ð', 'd').replace('þ', 'th')
    return s.casefold()
```

- `unicodedata.normalize('NFKD', ...)` + strip `U+0300–U+036F` = accent folding
  and, as a bonus, compatibility normalization (`ﬁ`→`fi`, full-width→ASCII,
  `²`→`2`). This is the ADR 0008 recipe.
- NFKD does **not** decompose `ß`, `ø`, `ł`, `æ`, `œ`, `đ`, `þ`, `ı` — handle
  those with an explicit table (above). ADR 0008 already calls out `ß`→`ss`.
- Use `str.casefold()` not `.lower()` (correct for `ß`, `ﬆ`, Greek final sigma).
- This is ~95% of ICU-primary behavior for Latin/German/Nordic names and titles,
  with zero dependencies. It will differ from ICU on locale-specific collation
  (Turkish `i`/`İ`, CJK ordering) — acceptable for our sources.

---

## 6. Things Calibre does that we should deliberately NOT copy

- **`title_sort` article→suffix rewriting** ("Hobbit, The"). Good for a sort
  column, wrong for matching — just *drop* leading articles.
- **`titlecase()` in `clean_downloaded_metadata` / `fixcase` / `fixauthors`** —
  Calibre re-cases downloaded English titles/authors ("the hobbit" → "The
  Hobbit"). That's a display concern and English-only; our matcher normalizes
  *downward* (lowercase) and must not run titlecase (it would mangle German nouns
  and `McDonald`/`O'Brien`).
- **`xisbn` / OCLC "same work, different edition" lookup** — external service,
  **decommissioned**, dead code in the tree. Don't port. If we want edition
  grouping we do it ourselves.
- **`has_cover` / cached-cover-URL ranking bucket** — proxy signal specific to
  Calibre's source plugins; meaningless for us.
- **`only_first_author=True`** in `get_author_tokens` — Calibre compares author
  on the first author only. We have a curated reference-author list; compare
  against all of them (weight first-listed higher).
- **Dropping every token ≤ 2 chars** in `get_author_tokens` — fine for building a
  loose search query, too lossy as a hard rule (kills valid short surnames like
  "Ng", "Wu", "Xi", initials that matter for disambiguation). Use it only for the
  *fuzzy* pass, keep a full-token pass alongside.
- **`get_title_tokens(strip_subtitle=False)` default** — Calibre keeps subtitles.
  ADR 0008 wants them stripped; do that.
- **Plain `str.lower()` for the cross-source merge key** — no accent folding, so
  "Böll" and "Boll" never merge. We fold first (§5).
- **Binary/exact `cleanup_title` equality as the only title signal** — that's why
  Calibre needs the search engine's own relevance. We replace it with a graded
  `rapidfuzz` score.
- **No confidence gate at all** — Calibre always shows the list. We need the
  auto-accept / provisional / no-match trichotomy (§4).
- **`cleanup_title` removes only ONE leading article and only a trailing `(...)`
  (not `[...]`), non-recursively** — extend both (loop articles, handle
  brackets) per ADR 0008.

---

## 7. Consolidated normalization checklist (implementation-ready)

**`normalize_title(s)`**
1. `fold(s)` (§5: NFKD + strip marks + ß/ø/… table + casefold).
2. Remove bracketed year/edition/format:
   `(?i)[({\[](\d{4}|omnibus|anthology|hardcover|audiobook|audio ?cd|paperback|turtleback|mass ?market|edition|ed\.|ebook|ungek[uü]rzt|gek[uü]rzt|h[oö]rbuch)[\])}]`
   then `(?i)[({\[][^\]})]*?(edition|ed\.|auflage)[^\]})]*?[\]})]`.
3. Remove trailing bracket group: `[\(\[][^\)\]]*[\)\]]\s*$` (repeat once).
4. Cut subtitle: split on first of ` - `, ` — `, ` – `, `: `, ` / `, ` \ `;
   keep head if head length > 1.
5. `\d,\d` thousands: `(\d+),(\d+)` → `\1\2`.
6. Punctuation → space: `[:,;!@$%^&*(){}.\`~"\[\]/《》「」“”‘’–—]` and ` -` → ` `.
7. Drop leading articles, looping: `^(the|a|an|of|and|der|die|das|den|dem|des|ein|eine|einen|einem|einer|le|la|les|el|los|il)\s+`.
8. Drop bare format tokens anywhere: `ebook`, `hörbuch`, `audiobook`, `ungekürzt`,
   `gekürzt`, `omnibus`, `unabridged`, `abridged`.
9. `\s+` → ` `, strip.
10. (for fuzzy pass) optionally drop join tokens `a and the & und of`.

**`normalize_author(s)`** — per §2 checklist. Split first, then per name:
`fold` → strip brackets/roles → comma-swap → drop prefixes/suffixes/particles →
token set. Keep an initials-included variant for a secondary looser compare.

**Compare** — `rapidfuzz.fuzz.token_set_ratio` on the normalized strings;
assemble the lexicographic sort key from §3; apply the §4 gate.
