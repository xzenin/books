from __future__ import annotations

from dataclasses import dataclass

from ...io.manager import SnapshotManager
from ..prompt_builders import build_segment_prompt
from ..writables import ProjectSettings
from ..writables import DraftedSegmentPrompt, SegmentBlueprint


@dataclass
class DraftChapterSegment:
    encoding: str
    manager: SnapshotManager

    def draft_segment_prompts(
        self,
        *,
        settings: ProjectSettings,
        gist: str,
        chapter_number: int,
        outline_payload: dict,
        chapter_payload: dict,
        segments: list[SegmentBlueprint],
        template_payload: dict,
    ) -> list[DraftedSegmentPrompt]:
        segment_dir = self.manager.get_runtime_segment_prompt_dir(chapter_number)
        self.manager.ensure_dir(segment_dir)

        drafted: list[DraftedSegmentPrompt] = []
        for index, segment in enumerate(segments, start=1):
            carry_over = ""
            if index > 1:
                carry_over = f"Carry-over from Segment {index - 1}: preserve emotional momentum and consequence."

            segment_payload = {
                "name": str(segment.name).strip() or f"segment-{index}",
                "goal": segment.goal,
                "stakes": segment.stakes,
                "vulnerability": segment.vulnerability,
                "conflict": segment.conflict,
                "tension": segment.tension,
                "rationalize": segment.rationalize,
                "subversion": segment.subversion,
                "catharsis": segment.catharsis,
            }
            prompt = build_segment_prompt(
                settings=settings,
                gist=gist,
                outline_payload=outline_payload,
                chapter_payload=chapter_payload,
                segment_payload=segment_payload,
                template_payload=template_payload,
                segment_index=index,
                carry_over=carry_over,
                encoding=self.encoding,
            )

            prompt_path = self.manager.get_runtime_segment_prompt_path(chapter_number, index)
            self.manager.write_text_file(prompt_path, prompt + "\n")
            drafted.append(DraftedSegmentPrompt(index=index, segment=segment, prompt=prompt, prompt_path=prompt_path))

        return drafted
