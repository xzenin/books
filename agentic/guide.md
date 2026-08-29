# Implementation Guide for the Writer Agent

This guide explains how to set up and run the **dynamic writer agent** — a subject-agnostic literary engine that transforms a list of topics/terms into Gibran-esque philosophical poetic prose chapters.

The writing *style* (Kahlil Gibran's *The Prophet*, 1923) is fixed, but the *subject matter, language, and philosophical grounding* are fully parameterized by three inputs you supply at runtime.

---

## Architecture Overview

The system is split into two layers:

| File | Role |
|------|------|
| `write.md` | **The writing engine.** Defines the voice, structural formula, style rules, and execution steps. Subject-agnostic — never changes between books. |
| `source/book_speed/config.json` | **A book-specific instance.** Supplies the subject inputs (seed file, index file, reference book) and the subject-specific configuration (language, title, sacred vocabulary, thematic categories, translation table). |
| `context/qualities/aurilus.md` | **The seed file.** An analysis of a reference book, defining the philosophical framework, themes, metaphors, and quality metrics. |
| `source/book_speed/bookseed.txt` | **The index file.** The list of topics/terms, one per line. Each becomes one chapter. |
| `context/references/aurilus.txt` | **The reference book** (optional). The source text for direct stylistic grounding. |

To write a *new* book on a *new* subject, you only create a new book folder under `source/` with a new `config.json`, a new seed file, and a new index file. The engine in `write.md` stays untouched.

---

## 1. Set the System Prompt (Kiro / Cursor / GitHub Copilot)

Paste the contents of `write.md` into your `.cursorrules`, the System Prompt, or the agent definition. This tells the AI *who it is* and *how to write*.

```text
Act as "The Prophet Agent" — a dynamic, subject-agnostic literary engine.
Context: It is 2026, a world fractured by dissent and digital noise.
Task: Expand a list of topics/terms into Gibran-style philosophical poetic prose chapters.
Constraint: Maintain the 1923 aesthetic of Kahlil Gibran's "The Prophet".
  Never use the words 'Internet', 'Smartphone', or 'Algorithm'.
  Use 'The Invisible Web', 'The Talking Glass', and 'The Hidden Calculation' instead.
Structure (every chapter):
  1. The Question (from the seeker).
  2. The Oration (the core philosophy).
  3. The Benediction (a short, final wise thought).
```

> **Note:** The subject, language, and philosophical grounding are NOT fixed in the system prompt. They are supplied at runtime through the seed file, index file, and reference book. The system prompt only fixes the *voice*.

---

## 2. The "Write-the-Book" Command (Prompt to trigger the work)

Once the system prompt is set, invoke the agent with the three inputs:

> "Writer, here are my inputs:
> - **Seed file**: `context/qualities/aurilus.md`
> - **Index file**: `source/book_speed/bookseed.txt`
> - **Reference book**: `context/references/aurilus.txt`
>
> Write [N] chapters on the next [N] topics from the index, conforming to the seed file's themes and quality metrics."

The agent will:
1. Read the seed file to understand the reference book, themes, categories, and quality metrics.
2. Read the index file to get the list of topics/terms.
3. Read the reference book (if provided) for stylistic grounding.
4. Initialize or read `progress.json` to determine the next chapter.
5. Generate, save, and append each chapter, then update progress.

---

## 3. The Three Inputs (What You Provide)

### Seed File (`context/qualities/aurilus.md`)
An analysis of a reference book. It defines:
- The reference book's identity, genre, and structure
- **Quality metrics** (philosophical depth, metaphorical richness, accessibility, etc.)
- **Core philosophical themes**
- **Metaphor families** and recurring imagery
- **Thematic categories** to assign to chapters
- Recommendations for chapter topics

### Index File (`bookseed.txt`)
The list of topics/terms, one per line. Each becomes one chapter. For example:

```
ত্বরণ (Acceleration),
বল (Force),
শক্তি (Energy),
...
```

### Reference Book (`context/references/aurilus.txt`)
The source text itself (optional), for direct stylistic and thematic reference.

---

## 4. Example of how the Agent transforms a term

**Input (term):** `The Echoing Cave` — *the danger of only hearing one's own voice / confirmation bias.*

**Agent Output:**

> "And a young man, who carried a tablet of glowing glass, said, 'Speak to us of the Echoes.'
> And he answered, saying:
> You have built for yourselves caves of crystal, where every wall is a mirror of your own desire. You cry out into the darkness, 'Is this the truth?' and the darkness answers back with your own voice, and you are comforted.
> But I say to you, comfort is the thief of the soul's height.
> The bird does not learn to fly by listening to its own wings; it learns by wrestling with the wind that comes from the North, a wind it did not choose.
> Verily, a man who only speaks to his own shadow shall soon forget the language of the sun..."

---

## Recommended Workflow

1. **Feed the System Prompt** — tell the AI who it is (using `write.md`).
2. **Create the book instance** — a new `config.json` in a new `source/book_<bookname>/` folder, pointing to its seed file, index file, and reference book.
3. **Upload the inputs** — provide the seed file, index file, and (optionally) the reference book.
4. **Batch Generate** — ask the AI to write 3 chapters at a time to ensure quality control.
5. **Refine** — if the AI becomes too "modern," say: *"More metaphors, less logic. Speak to me as if we are standing on the hills of Orphalese."*

---

## Output Files (What the Agent Writes)

For each book, the agent writes directly to disk:

- **Individual chapters**: `chapters\Chapter_XXX_[term].md` — one file per chapter, starting with the heading `# অধ্যায় XXX: [term]` (or the target-language equivalent).
- **Consolidated book**: `book.md` — the assembled book (title, introduction, and every chapter in order).
- **Progress tracking**: `progress.json` — tracks completed chapters, current chapter, and per-chapter status.
- **Run metadata**: `metadata_code<number>.json` — records the plan for each writing or revision run before the text is written.

---

## Progress Tracking (`progress.json`)

The agent maintains a `progress.json` at the book's root level:

```json
{
  "title": "অদৃশ্য বিধান: বিজ্ঞান ও আত্মার নবী",
  "language": "bn",
  "source_terms": "bookseed.txt",
  "context": "../context/qualities/aurilus.md + writer.md",
  "total_chapters": 199,
  "completed_chapters": 5,
  "current_chapter": 5,
  "chapters": [
    {
      "chapter_number": 1,
      "topic": "মহাকর্ষ",
      "category": "এক রক্তের বিধান",
      "status": "completed",
      "file_path": "chapters\\Chapter_001_মহাকর্ষ.md",
      "completed_date": "2026-08-29T00:00:00Z"
    }
  ]
}
```

The agent always checks `progress.json` first to **resume** from where it left off — never restarting from Chapter 1 unless explicitly asked.

---

## Run Metadata (`metadata_code<number>.json`)

Before writing or revising chapters, create the next numbered metadata file in the book folder. Never overwrite an existing metadata file.

Use it as the pre-writing plan and revision memory for the run:

```json
{
  "run_type": "write",
  "created_at": "2026-08-29T00:00:00Z",
  "bookname": "Muktii",
  "title": "মুক্তি",
  "language": "bn",
  "quality": "../context/qualities/aurilus.md",
  "themes": "../context/themes/generic.md",
  "reference": "../context/references/aurilus.txt",
  "chapters_planned": [
    {
      "chapter_number": 7,
      "topic": "ধারকত্ব",
      "category": "রাজসেবা",
      "metaphor_plan": ["vessel", "empty cup", "servant's lamp"],
      "sacred_vocabulary": ["রাজসেবা", "শূন্য পাত্র", "নীরব বিধান"],
      "revision_notes": []
    }
  ]
}
```

For revision runs, set `"run_type": "revision"` and record the requested transformation, the files to be changed, and the audit findings that caused the revision.

---

## Revision Workflow

Use revision mode when a chapter already exists and the user asks to improve it, tighten it, shift its voice, make it more archaic, make it more Baul, or audit completed chapters.

Recommended revision commands:

```text
revise chapter 7: more Baul, less Stoic
tighten chapter 3
make chapter 5 more archaic Bengali
audit completed chapters
```

Revision rules:

1. Read `config.json`, the relevant chapter file, `progress.json`, and the latest metadata file.
2. Create a new `metadata_code<number>.json` with `"run_type": "revision"` before editing.
3. Preserve the chapter number, topic, and completed status unless the user asks to change them.
4. Update both the individual chapter file and its corresponding section in `book.md`.
5. Add revision notes to the new metadata file, including the user's instruction and a short before/after rationale.
6. Do not mark new chapters completed during a revision-only run.
