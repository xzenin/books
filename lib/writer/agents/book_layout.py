from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass
class BookLayout:
    book_name: str
    history_root: Path
    use_cache: bool
    verbose: bool
    json_logs: bool
    call_genai: Callable[..., str]
    extract_json_payload: Callable[[str], Any]
    agent_name: str = "BookLayout"
    provider_instance_name: str | None = None

    def create_master_plan(self, *, base_prompt: str) -> tuple[str, dict[str, Any]]:
        scaffold = (
            "\n\nNarrative architecture requirements for chapter progression:\n"
            "- The Hook: Start as close to the action as possible.\n"
            "- The Goal: Remind the reader what the character wants right now.\n"
            "- The Conflict: Introduce obstacles that prevent the goal.\n"
            "- The Reaction: The character processes the disaster (Rationalize).\n"
            "- The Dilemma: They realize they have no easy choices left.\n"
            "- The Decision: They pick a new Goal, which starts the next chapter.\n"
            "Return JSON only."
        )
        prompt = base_prompt + scaffold
        response = self.call_genai(
            prompt,
            conversation_id=f"{self.book_name}-novel-outline",
            use_cache=self.use_cache,
            history_root=self.history_root,
            agent_name=self.agent_name,
            verbose=self.verbose,
            json_logs=self.json_logs,
            provider_instance_name=self.provider_instance_name,
        )
        payload = self.extract_json_payload(response)
        if not isinstance(payload, dict):
            raise ValueError("Novel layout response must be a JSON object.")
        return prompt, payload
