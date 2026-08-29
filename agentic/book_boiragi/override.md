# Override — Transformation Layer (Human-in-the-Loop)

This file is the **human's review and transformation layer**. It is optional. If present, the writer agent reads it **before** writing each chapter and applies the instructions here to transform the generated poetry.

Unlike `bookseed.txt` (which lists *what* to write), `override.md` describes *how to reshape* the output — the human's thought process, local preferences, and contextual flavor.

Leave any section empty (or delete it) if you have no instruction for it. The agent applies only what is filled in.

---

## 1. Prompt Transformation

How to transform the base text into a different prompt/voice. Describe the shift you want — e.g. "make it more conversational", "shorten the oration", "write in first person", "turn the benediction into a question".

<!-- Example:
- Shift the prophet's voice from formal sermon to intimate whisper.
- Replace "And he answered, saying:" with a direct, unannounced reply.
- End every chapter with a question instead of a statement.
-->

## 2. Local Preferences

Your stylistic preferences — what you like and dislike. These override the default style rules.

<!-- Example:
- Prefer short sentences; avoid long compound clauses.
- Avoid the word "verily" — it feels archaic to my readers.
- Use more river and boat imagery; less fire imagery.
-->

## 3. Local Dialects

Dialect words, phrases, and grammatical forms to weave in, so the poetry feels rooted in a specific region.

<!-- Example:
- Use Sylheti forms: "আইজ" for "আজ", "কিতা" for "কি".
- Use the Barisal "হ" ending: "করতেছি" → "করতেছি হ" (soft).
- Sprinkle in "গো" and "রে" as endearment particles.
-->

## 4. Slug / Location / Era Context

Contextual anchors that make the poetry feel contemporary and place-specific — slugs, place names, and era markers.

<!-- Example:
- Location: the rivers of Barisal, the Sundarbans, the Padma's banks.
- Era: the 2026 monsoon, the digital age, the post-flood village.
- Slugs: "the boatman of the Padma", "the weaver of Tangail", "the fisherman of the Meghna".
-->

---

## How the Agent Applies This

1. Read `override.md` (if it exists) before writing.
2. Generate the base chapter from quality + theme + reference.
3. Apply each filled section as a transformation pass, in order:
   - **Prompt Transformation** → reshape the voice/structure.
   - **Local Preferences** → adjust style to the human's taste.
   - **Local Dialects** → weave in dialect words and forms.
   - **Slug / Location / Era** → anchor the text in place and time.
4. Write the transformed chapter to disk.

If `override.md` is empty or absent, the agent writes the base chapter unchanged.
