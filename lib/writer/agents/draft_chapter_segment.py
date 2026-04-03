from __future__ import annotations

from dataclasses import dataclass

from ..writables import DraftedSegmentPrompt, SegmentBlueprint


@dataclass
class DraftChapterSegment:
    encoding: str
    manager: SnapshotManager

    def draft_segment_prompts(
        self,
        *,
        chapter_number: int,
        chapter_payload: dict,
        segments: list[SegmentBlueprint],
    ) -> list[DraftedSegmentPrompt]:
        segment_dir = self.manager.get_runtime_segment_prompt_dir(chapter_number)
        self.manager.ensure_dir(segment_dir)

        chapter_mission = str(chapter_payload.get("chapter_summary", "")).strip() or str(
            chapter_payload.get("chapter_title", f"Chapter {chapter_number}")
        )

        drafted: list[DraftedSegmentPrompt] = []
        for index, segment in enumerate(segments, start=1):
            carry_over = ""
            if index > 1:
                carry_over = f"Carry-over from Segment {index - 1}: preserve emotional momentum and consequence."

            prompt = (
                f"Chapter Mission: {chapter_mission}\\n"
                f"Segment {index} Prep:\\n"
                f"- Goal: {segment.goal}\\n"
                f"- Stakes: {segment.stakes}\\n"
                f"- Vulnerability: {segment.vulnerability}\\n"
                f"- Conflict: {segment.conflict}\\n"
                f"- Tension: {segment.tension}\\n"
                f"- Rationalize: {segment.rationalize}\\n"
                f"- Subversion: {segment.subversion}\\n"
                f"- Catharsis: {segment.catharsis}\\n"
                f"{carry_over}\\n"
                "Return JSON only with keys: segment_text, physical_state, emotional_state, information_state."
            ).strip()

            prompt_path = self.manager.get_runtime_segment_prompt_path(chapter_number, index)
            self.manager.write_text_file(prompt_path, prompt + "\n")
            drafted.append(DraftedSegmentPrompt(index=index, segment=segment, prompt=prompt, prompt_path=prompt_path))

        return drafted
