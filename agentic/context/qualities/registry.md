# Quality Registry

A catalog of every writing quality available in `context/qualities/`. Each quality is a seed analysis of a reference book — defining the philosophical framework, metaphor families, quality metrics, and thematic grounding that the writer agent uses to render chapters in the Gibran-esque voice.

The writer agent reads this registry to discover available qualities, then reads the individual quality file for the full analysis.

---

## Available Qualities

| # | Quality File | Reference Work | Author | Genre | Language | Status |
|---|-----------|----------------|--------|-------|----------|--------|
| 1 | [`aurilus.md`](aurilus.md) | *The Meditations* | Marcus Aurelius | Stoic Philosophy / Personal Reflections | Bengali (বাংলা) | ✅ Active |

---

## Quality Details

### 1. `aurilus.md` — The Meditations of Marcus Aurelius

- **Reference Work:** *The Meditations* (Translated by Jeremy Collier, Revised by Alice Zimmern, 1887)
- **Author:** Marcus Aurelius (121–180 CE), Roman Emperor and Stoic philosopher
- **Genre:** Stoic Philosophy / Personal Reflections / Philosophical Memoir
- **Structure:** 12 Books of aphorisms, reflections, and moral teachings
- **Target Language:** Bengali (বাংলা) — archaic/literary register
- **Book Title:** অদৃশ্য বিধান: বিজ্ঞান ও আত্মার নবী (The Invisible Law: A Prophet of Science and Soul)

**Core Philosophical Themes:**
- Virtue as Sole Good
- Cosmopolitanism (brotherhood of mankind)
- Transience and impermanence
- Divine Reason (Logos)
- Self-Governance (the guiding principle within)
- Acceptance of Fate (amor fati)

**Dominant Metaphor Families:**
- Nature (river, vine, blade of grass, wax)
- Theatrical/Performance (actor, stage, play)
- Architectural/Structural (arch, commonwealth, body politic)
- Fire/Element (fiery ether, conflagration)
- Body/Medical (feet, hands, eyelids, teeth)

**Quality Ratings:**
- Philosophical Depth: 9.5/10
- Metaphorical Richness: 8.5/10
- Human Accessibility: 9/10
- Civilizational Relevance: 10/10
- Literary Quality: 7.5/10
- Ethical Framework: 9/10
- **Overall: 9.2/10**

**Thematic Categories:** See [`../themes/generic.md`](../themes/generic.md) for the ten Stoic themes derived from this work.

**Associated Index:** `bookseed.txt` (physics/science terms in Bengali)

---

## How to Add a New Quality

1. Create a new seed analysis file in `context/qualities/` (e.g. `rumi.md`, `tagore.md`, `nietzsche.md`).
2. Follow the same structure as `aurilus.md`:
   - Document Overview (source, work, genre, structure)
   - Quality Metrics Analysis (philosophical depth, metaphorical richness, accessibility, relevance, literary quality, ethical framework)
   - Metaphorical Landscape (conceptual framework, recurring imagery)
   - Philosophical Innovations
   - Relevance Patterns for Gibran-style treatment
   - Linguistic/Stylistic DNA
   - Quality Assessment Summary
   - Recommendations for seed topics
3. Add a row to the table above and a detail section below.
4. Create a matching thematic categories file in `context/themes/` if the quality introduces new themes.
5. Point a book instance (`writer.md`) at the new quality file.

---

## Conventions

- **One quality = one reference book.** Each file analyzes a single source text.
- **Quality files are read-only inputs.** The writer agent reads them; it never modifies them.
- **Themes live separately.** Thematic categories derived from a quality belong in `context/themes/`, not in the quality file itself.
- **References live separately.** The source text itself belongs in `context/references/`, not in the quality file.
