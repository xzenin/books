### TASK
You have to write the first poetic prose of poem number {chapter_number} of a collection. This part will be created entirely based on the 'Central Metaphor' given below.

### INPUT DATA
- **Collection Context:** {book_summary} | {book_summary}
- **Poem Summary:** {chapter_summary}
- **Thematic Core (Previous Stanzas):** {segment_summary}
- **Central Metaphor (Symbol of Hope):** {segment_title}

### WRITING INSTRUCTIONS
1. **Focus:** Focus only on the themes of the 'Central Metaphor'. Do not bring in irrelevant external events or prose-style exposition.
2. **Metaphor Integration:** Use the metaphor "{segment_title}" 3 to 5 times throughout the poems. It must emerge as a "Light of Hope" woven into the imagery, never directly stated as a fact. Vary the phrasing and abstract context each time (Randomized poetic phrasing).
3. **Style & Mood:** Apply deep philosophical reflection and atmospheric historical motifs. The mood must be elegiac yet resonant, aligning with the 'Central Metaphor'.
4. **Length:** Must be at least {number_of_words_per_segment} words or more (ensure the density of the language meets this length without losing poetic quality).
5. **Language:** Use high-quality literary {book_language} language, rich in phonetic beauty and evocative diction.
6. **Consistency:** Maintain lyrical continuity and stay consistent with the 'Poem Summary' and 'Collection Context'.
7. **Avoid Repetition:** Avoid mundane repetition. Every line should offer a new image, a deeper layer of meaning, or a fresh sensory perspective.
8. **Imagery:** Make the description vivid and visceral. Each line should paint a new, haunting, or beautiful picture in the reader's mind.
9. **Emotional Resonance:** Strive to evoke deep, piercing emotions. Use the rhythm of the language to create waves of feeling in the reader's heart.
10. **Poetic Voice:** Instead of literal dialogue, use "The Voice of the Soul" or internal monologue. If a character speaks, it must be in the form of a verse or a dramatic fragment.
11. **Symbolic Development:** Emphasize the spiritual and emotional weight of the subjects. Each "character" mentioned should be treated as a living symbol of the era's pain or resilience.
12. **Historical Motifs:** Weave historical facts into the poetry as symbols (e.g., the dust of 1947, the silence of the border). Each event must be felt through a lyrical lens.
13. **Metaphor Usage:** The metaphor "{segment_title}" should haunt the folds of the verses, acting as a beacon of light. It should blend into the rhythm rather than appearing as a label.
14. **Subject Presence:** When referencing figures from the 'Book Context', present them as archetypes or spirits of the narrative, painting their presence with strokes of poetic intensity.

### TECHNICAL CONSTRAINTS (MANDATORY)
- **Format:** Return only a valid JSON object.
- **No Markdown:** Do not write any ```json blocks or any other text.
- **Escaping:** Escape all Newlines with `\n` and double quotes with `\"` within the 'segment_content' field. This is critical for programmatic parsing.
- **Quotes:** Use only double quotes (") for all keys and values in JSON.

### JSON Shape Structure to return:
{segment_template_json} 

### OUTPUT
- **Generate text in {book_language} language.
- **Exact JSON shape to return. Do not wrap with "content" wrapper. Only valid tags: "total_words", "segment_content".
- **Output Format:** Return ONLY a valid JSON object. 

Now provide the JSON.