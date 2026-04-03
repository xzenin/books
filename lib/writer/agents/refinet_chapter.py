from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any


@dataclass
class RefinetChapter:
    randomize_thoughts: bool = True
    human_in_loop: bool = False

    def refine_chapter_context(self, *, chapter_payload: dict[str, Any], chapter_number: int) -> dict[str, Any]:
        refined = dict(chapter_payload)
        notes: list[str] = [
            "Goal: Validate that chapter intent is explicit.",
            "Conflict: Ensure obstacle is difficult and costly.",
            "Logic: Verify continuity with prior chapters.",
            "Sensory: Ensure at least two non-visual sensory cues.",
            "Ending: Add a hook into next chapter rationalization.",
        ]

        if self.randomize_thoughts:
            thought_bank = [
                "Inject a contradictory memory that changes trust.",
                "Shift emotional temperature from confidence to dread.",
                "Use smell and touch to anchor the setting.",
                "Force a moral tradeoff with no clean win.",
                "End on an irreversible choice, not an explanation.",
            ]
            notes.append(f"Randomized thought: {random.choice(thought_bank)}")

        if self.human_in_loop:
            user_note = input(
                f"Optional refinement note for chapter {chapter_number} (blank to skip): "
            ).strip()
            if user_note:
                notes.append(f"Human note: {user_note}")

        refined["refinement_notes"] = notes
        return refined
