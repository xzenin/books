# Reference Registry

A catalog of every reference text available in `context/references/`. Each reference is a source text — the raw material the writer agent reads for direct stylistic and thematic grounding.

The writer agent reads this registry to discover available references, then reads the individual reference file for the source text itself.

---

## Available References

| # | Reference File | Work | Author | Format | Language | Status |
|---|---------------|------|--------|--------|----------|--------|
| 1 | [`aurilus_book_reference.txt`](aurilus_book_reference.txt) | *The Meditations* | Marcus Aurelius | Plain text (full text) | English | ✅ Active |

---

## Reference Details

### 1. `aurilus_book_reference.txt` — The Meditations of Marcus Aurelius

- **Work:** *The Meditations of Marcus Aurelius*
- **Author:** Marcus Aurelius (121–180 CE), Roman Emperor and Stoic philosopher
- **Translation:** Jeremy Collier, revised by Alice Zimmern (1887)
- **Format:** Plain text (`.txt`), full text of the work
- **Language:** English
- **Structure:** 12 Books of aphorisms, reflections, and moral teachings

**Associated Quality:** [`../qualities/aurilus.md`](../qualities/aurilus.md) — the seed analysis of this work.

**Associated Themes:** [`../themes/generic.md`](../themes/generic.md) — the ten Stoic themes derived from this work.

**Associated Index:** `bookseed.txt` (physics/science terms in Bengali)

---

## How to Add a New Reference

1. Add the source text file to `context/references/` (e.g. `rumi_masnavi.txt`, `tagore_gitanjali.txt`).
2. Add a row to the table above and a detail section below.
3. Create a matching quality file in `context/qualities/` (the seed analysis of the reference).
4. Create a matching theme set in `context/themes/` if the reference introduces new themes.
5. Point a book instance (`writer.md`) at the new reference.

---

## Conventions

- **One reference = one source text.** Each file holds a single work.
- **Reference files are read-only inputs.** The writer agent reads them; it never modifies them.
- **References are distinct from qualities.** A reference (`context/references/`) is the raw source text; a quality (`context/qualities/`) is the *analysis* of that text (voice, metaphor families, quality metrics).
- **References are distinct from themes.** A theme set (`context/themes/`) is the *philosophical lens* derived from the reference.
