from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ..writables import SegmentBlueprint


@dataclass
class LayoutChapter:
    book_name: str
    use_cache: bool
    verbose: bool
    json_logs: bool
    call_genai: Callable[..., str]
    extract_json_payload: Callable[[str], Any]
    agent_name: str = "LayoutChapter"
    provider_instance_name: str | None = None

    def create_segment_layout(
        self,
        *,
        chapter_number: int,
        chapter_payload: dict[str, Any],
        outline_payload: dict[str, Any],
        history_root: Path,
    ) -> tuple[str, list[SegmentBlueprint]]:
        payload = {
            "chapter_number": chapter_number,
            "chapter": chapter_payload,
            "outline": {
                "novel_name": outline_payload.get("novel_name", ""),
                "running_summary": outline_payload.get("running_summary", ""),
                "all_characters": outline_payload.get("all_characters", []),
            },
        }
        prompt = (
            "Create a segmented chapter plan with 3 to 7 segments. "
            "For each segment include: goal, stakes, vulnerability, conflict, tension, "
            "rationalize, subversion, catharsis. Return JSON only in this format: "
            "{\"segments\":[{\"name\":\"segment-1\",\"goal\":\"\",\"stakes\":\"\",\"vulnerability\":\"\","
            "\"conflict\":\"\",\"tension\":\"\",\"rationalize\":\"\",\"subversion\":\"\",\"catharsis\":\"\"}]}"
            f"\n\nContext JSON:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )
        response = self.call_genai(
            prompt,
            conversation_id=f"{self.book_name}-chapter-layout-{chapter_number}",
            use_cache=self.use_cache,
            history_root=history_root,
            agent_name=self.agent_name,
            verbose=self.verbose,
            json_logs=self.json_logs,
            provider_instance_name=self.provider_instance_name,
        )

        parsed = self.extract_json_payload(response)
        segments_raw: list[Any]
        if isinstance(parsed, dict) and isinstance(parsed.get("segments"), list):
            segments_raw = parsed["segments"]
        elif isinstance(parsed, list):
            segments_raw = parsed
        else:
            segments_raw = []

        segments: list[SegmentBlueprint] = []
        for index, item in enumerate(segments_raw, start=1):
            if isinstance(item, dict):
                segments.append(SegmentBlueprint.from_payload(item, index=index))

        if not segments:
            chapter_sections = chapter_payload.get("chapter_segments", [])
            if isinstance(chapter_sections, list) and chapter_sections:
                for index, section in enumerate(chapter_sections, start=1):
                    seed = section if isinstance(section, dict) else {"segment_text": str(section)}
                    segments.append(
                        SegmentBlueprint.from_payload(
                            {
                                "name": str(seed.get("segment_title", seed.get("section-title", f"segment-{index}"))),
                                "goal": "Advance chapter objective.",
                                "stakes": "Failure escalates the chapter crisis.",
                                "vulnerability": "Character weakness is exposed.",
                                "conflict": str(seed.get("segment_text", seed.get("text", ""))).strip(),
                                "tension": "Time pressure is increasing.",
                                "rationalize": "Character reevaluates after setback.",
                                "subversion": "New information changes the plan.",
                                "catharsis": "Emotional beat closes the segment.",
                            },
                            index=index,
                        )
                    )
            else:
                segments.append(
                    SegmentBlueprint.from_payload(
                        {
                            "name": "segment-1",
                            "goal": "Establish immediate objective.",
                            "stakes": "Failure damages survival or relationships.",
                            "vulnerability": "Internal fear complicates action.",
                            "conflict": "External force blocks progress.",
                            "tension": "A deadline is approaching.",
                            "rationalize": "Character reframes the setback.",
                            "subversion": "Unexpected development alters strategy.",
                            "catharsis": "End with emotional release and forward hook.",
                        },
                        index=1,
                    )
                )

        return prompt, segments
