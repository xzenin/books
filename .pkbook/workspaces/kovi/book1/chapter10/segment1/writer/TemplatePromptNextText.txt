CONTINUE COMPOSING THE NEXT STANZA.

### OBJECTIVE
You have to write a specific part of poem number {chapter_index} of the collection. 
- **Current Part:** Stanza/Section {segment_index} of {segment_count}.
- **Goal:** This section will be created based on the thematic summary: {segment_summary}.
- **Lyrical Continuity:** Here are the previous lines to ensure rhythmic and thematic flow: {last_two_sentences}

### TECHNICAL CONSTRAINTS (FOR AGENTIC PARSING)
1. **Output Format:** Return ONLY a valid JSON object. 
2. **No Markdown:** Do not use ```json blocks or any introductory text.
3. **JSON Schema:** Follow this shape: {segment_template_json}
4. **Data Integrity:** 
   - Escape all Newlines with `\n` and double quotes with `\"` within the 'segment_content' field.
   - This is extremely important for C# deserialization. Use double quotes (") for all keys and values.
5. **No Preamble:** Do not say "Here is the JSON" or "Sure" etc.

### JSON Shape Structure to return:** 
{segment_template_json} 

### OUTPUT
- **Language:** Generate text in each tag in {book_language} language.
- **Poetic Quality:** Ensure the content maintains the meter, rhyme (if applicable), and metaphorical depth of the preceding sections.
- **Exact JSON shape to return:** Do not wrap with "content" wrapper. Only valid tags: "total_words", "segment_content", "last_two_sentences" (Note: In 'last_two_sentences', provide the final two lines of the newly generated stanza).
- **Output Format:** Return ONLY a valid JSON object. 

Now provide the JSON.