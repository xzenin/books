from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ..writables import ChapterSegmentText, DraftedSegmentPrompt


@dataclass
class GenerateChapterSegment:
    book_name: str
    use_cache: bool
    verbose: bool
    json_logs: bool
    call_genai: Callable[..., str]
    extract_json_payload: Callable[[str], Any]
    agent_name: str = "GenerateChapterSegment"
    provider_instance_name: str | None = None

    def generate_segment_content(
        self,
        *,
        chapter_number: int,
        chapter_root: Path,
        drafted_segments: list[DraftedSegmentPrompt],
        segment_history_roots: dict[int, Path] | None = None,
    ) -> list[ChapterSegmentText]:
        generated_segments: list[ChapterSegmentText] = []
        for item in drafted_segments:
            segment_index = int(item.index)
            segment_payload = item.segment
            prompt = str(item.prompt)

            response = self.call_genai(
                prompt,
                conversation_id=f"{self.book_name}-chapter-{chapter_number}-segment-{segment_index}",
                use_cache=self.use_cache,
                history_root=(segment_history_roots or {}).get(segment_index, chapter_root),
                agent_name=self.agent_name,
                verbose=self.verbose,
                json_logs=self.json_logs,
                provider_instance_name=self.provider_instance_name,
            )

            try:
                payload = self.extract_json_payload(response)
            except ValueError:
                payload = {"segment_text": response}

            if not isinstance(payload, dict):
                payload = {"segment_text": str(payload)}

            segment_text = str(
                payload.get(
                    "segment_text",
                    payload.get("generated_text", payload.get("chapter_text", payload.get("text", ""))),
                )
            ).strip()
            physical_state = str(payload.get("physical_state", "")).strip()
            emotional_state = str(payload.get("emotional_state", "")).strip()
            information_state = str(payload.get("information_state", "")).strip()

            state_lines: list[str] = []
            if physical_state:
                state_lines.append(f"Physical State: {physical_state}")
            if emotional_state:
                state_lines.append(f"Emotional State: {emotional_state}")
            if information_state:
                state_lines.append(f"Information State: {information_state}")

            text = segment_text
            if state_lines:
                text = (text + "\\n\\n" + "\\n".join(state_lines)).strip()

            segment_name = str(segment_payload.name).strip() or f"segment-{segment_index}"
            generated_segments.append(
                ChapterSegmentText(
                    section_title=segment_name,
                    section=f"segment-{segment_index}",
                    text=text,
                )
            )

        return generated_segments
