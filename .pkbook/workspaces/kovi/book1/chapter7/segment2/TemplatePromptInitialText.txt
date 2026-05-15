You are a narrative synthesis expert. Your task is to update a story's running summary by seamlessly integrating new plot developments into the existing summary.

### Inputs:
- **Existing Running Summary:** {running_summary}
- **Newly Added Text (to be integrated):** {newly_added_text}
- **Target Language:** {book_language}

### Instructions:
1. **Synthesize & Merge:** Do not simply append the new text to the end. Integrate the new events into the narrative flow, rewriting or condensing previous parts if necessary to maintain a smooth, chronological arc.
2. **Quality Control:** Ensure all key character motivations, plot twists, and historical context (relevant to the era) are preserved.
3. **Conciseness:** Keep the final summary dense but readable. Avoid unnecessary filler words while maintaining the literary tone of the novel.
4. **Consistency:** Ensure the summary reflects the "Historical Epic" genre and the specific psychological depth of the characters.

### OUTPUT
- **Generate text in each tag in {book_language} language 
- **Exact JSON shape to return. Do not wrap with "content" wrapper. Only valid tag:  "total_words","segment_content","last_two_sentences"
- **Output Format:** Return ONLY a valid JSON object. 

Now provide the JSON.
