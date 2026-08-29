# Override — Transformation Layer (Human-in-the-Loop)

This file is the **human's review and transformation layer**. It is optional. If present, the writer agent reads it **before** writing each chapter and applies the instructions here to transform the generated poetry.

Unlike `bookseed.txt` (which lists *what* to write), `override.md` describes *how to reshape* the output — the human's thought process, local preferences, and contextual flavor.

Leave any section empty (or delete it) if you have no instruction for it. The agent applies only what is filled in.

---

## 1. Prompt Transformation

How to transform the base text into a different prompt/voice. Describe the shift you want — e.g. "make it more conversational", "shorten the oration", "write in first person", "turn the benediction into a question".

**Transform the base text into the voice of Lalon Shah.** Shift the prophet's sermon into the riddling, question-turning register of the Baul master — the seeker who answers every question with a deeper question, and dissolves every division into one humanity.

- **Answer with a question.** Lalon never hands down a verdict; he turns the seeker's question back on itself. Where the base text states a truth, Lalon asks: "কি জাত সংসারে?" (what caste in this world?), "মনের মানুষ কোথায়?" (where is the man of the heart?). Let the oration be a chain of questions that lead the seeker inward.
- **Deny every label.** Refuse caste, creed, sect, and name: "হিন্দু না মুসলিম, মানুষ আগে" (not Hindu, not Muslim — human first). Whatever the subject, return to the one blood, the one breath, the one humanity.
- **Point to the "মনের মানুষ" (the man of the heart).** The true shrine is not outside — not in temple or mosque — but within. Every chapter should lead the seeker to the inner chamber where the beloved dwells.
- **Use the boat and the river.** Lalon's world is the Padma: the boat (তরী), the oarsman (মাঝি), the crossing (পার), the far shore (ওপার). Frame the journey of the soul as a river-crossing.
- **End in a riddle, not a statement.** Close each chapter with an open question or a paradox that lingers — "কে জানে?" (who knows?) — rather than a declarative benediction.
- **Keep the question-and-answer frame**, but let the answer feel like a song overheard on the riverbank, sung by a man who has seen both the mosque and the temple and found in both the same beloved.

<!-- Example:
- Shift the prophet's voice from formal sermon to intimate whisper.
- Replace "And he answered, saying:" with a direct, unannounced reply.
- End every chapter with a question instead of a statement.
-->

## 2. Local Preferences

Your stylistic preferences — what you like and dislike. These override the default style rules.

**Root the poetry in the Bengali-speaking world across borders and diasporas.** Let the imagery, place-names, and everyday texture draw from the whole Bengali landscape:

- **Bangladesh** — the Padma, Meghna, and Jamuna; the Sundarbans; the haor wetlands of Sylhet; the boatman, the jute farmer, the rickshaw-puller of Dhaka.
- **West Bengal** — the Hooghly and the Ganga; the terracotta temples of Bishnupur; the tea gardens of the Dooars; the tram and the adda of Kolkata.
- **Assam** — the Brahmaputra valley; the Barak Valley's Bengali speakers; the tea estate and the river island (majuli).
- **Tripura** — the hill streams, the bamboo groves, the Bengali settlements of Agartala.
- **Delhi Bengali Colony** — the diaspora: Chittaranjan Park, the Durga Puja pandals of the capital, the migrant who carries Bengal in a suitcase.

The poetry should feel at home in all of these — one Bengali soul, many rivers, many cities. Prefer concrete, lived place-texture over abstract scenery.

<!-- Example:
- Prefer short sentences; avoid long compound clauses.
- Avoid the word "verily" — it feels archaic to my readers.
- Use more river and boat imagery; less fire imagery.
-->

## 3. Local Dialects

Dialect words, phrases, and grammatical forms to weave in, so the poetry feels rooted in a specific region.

**Follow the syntax and voice of Bengal's great folk preachers — the Baul, Fakir, Sufi, and the lineages of Lalon Shah and Hasan Raja.** These are the preachers of Bengal who, for generations, served their communities through both spiritual practice and social uplift — and, above all, worked to **narrow the gap between Hindu and Muslim**, dissolving the walls of caste, creed, and sect into one shared humanity.

Weave in their signature forms:

- **Lalon's voice** — the seeker who denies all division: "সব লোকে কয় লালন কি জাত সংসারে" (everyone asks, Lalon, what caste are you in this world?). Use the question-as-answer, the refusal of labels, the "মনের মানুষ" (the man of the heart) as the one true shrine.
- **Hasan Raja's voice** — the zamindar-turned-mystic who sang of the beloved beyond name: "লোকে বলে বলেরে, ঘর-বাড়ি ভালা নাই আমার" (people say my house is no good). Use the paradox of wealth renounced, the beloved who is neither Hindu nor Muslim but simply the beloved.
- **Fakir / Sufi syntax** — the dervish's surrender: "আমি কিছু চাই না, শুধু চাই চাওয়া ছাড়া" (I want nothing, only the wanting of nothing). Use the negation of desire, the empty hand that receives the universe.
- **Baul endearment particles** — "গো", "রে", "ওরে", "ভাই" as tender address, the intimate "তুই" over the formal "আপনি".
- **The one-blood refrain** — "একই রক্ত, একই মানুষ" (one blood, one humanity); "হিন্দু না মুসলিম, মানুষ আগে" (not Hindu, not Muslim — human first). Let every chapter, whatever its subject, return to this bridge between faiths.

The dialect is not decoration — it is the very soul of the book. Every chapter should sound as if sung on the banks of the Padma by a preacher who has seen both the mosque and the temple, and found in both the same beloved.

<!-- Example:
- Use Sylheti forms: "আইজ" for "আজ", "কিতা" for "কি".
- Use the Barisal "হ" ending: "করতেছি" → "করতেছি হ" (soft).
- Sprinkle in "গো" and "রে" as endearment particles.
-->

## 4. Prompt Transformation

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
