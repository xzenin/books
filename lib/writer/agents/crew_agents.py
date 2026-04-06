from ..writables import ProjectSettings
from lib.io.io_helpers import read_text, load_json_file
import json
from pathlib import Path
from typing import Any

class BookLayout:
    """
    Crew Agent: BookLayout
    Responsible for creating the master plan for the book.
    Implements: The Hook, The Goal, The Conflict, The Reaction, The Dilemma, The Decision
    """
    def __init__(self, settings: ProjectSettings, gist: str, template_payload: Any):
        self.settings = settings
        self.gist = gist
        self.template_payload = template_payload

    @staticmethod
    def load_template(encoding: str = "utf-8"):
        # Find the project root (assume this file is always at lib/writer/agents/crew_agents.py)
        path = Path(__file__).resolve().parents[3] / "templates" / "book_prompt.txt"
        return read_text(path, encoding=encoding)

    def build_prompt(self) -> str:
        template_text = self.load_template()
        book_template_json = json.dumps(self.template_payload, ensure_ascii=False, indent=2)
        return template_text.format(
            book_gist=self.gist,
            book_template_json=book_template_json,
            chapter_count=self.settings.chapter_count,
        )

    def create_master_plan(self, call_genai, extract_json_payload, use_cache, history_root, verbose, json_logs, provider_instance_name=None) -> tuple[str, dict[str, Any]]:
        """
        Build the master plan prompt, call GenAI, and parse the output.
        Returns (prompt, outline_payload)
        """
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
        prompt = self.build_prompt() + scaffold
        response = call_genai(
            prompt,
            conversation_id=f"book-master-plan",
            use_cache=use_cache,
            history_root=history_root,
            agent_name="BookLayout",
            verbose=verbose,
            json_logs=json_logs,
            provider_instance_name=provider_instance_name,
        )
        outline_payload = extract_json_payload(response)
        return prompt, outline_payload

class RefinetChapter:
    """
    Crew Agent: RefinetChapter
    Adds context, randomizes thoughts, supports human-in-the-loop for a chapter.
    Implements: Goal, Conflict, Logic, Sensory, Ending
    """
    def __init__(self, randomize_thoughts: bool = True, human_in_loop: bool = False):
        self.randomize_thoughts = randomize_thoughts
        self.human_in_loop = human_in_loop

    def refine_chapter_context(self, chapter_payload: dict, chapter_number: int) -> dict:
        refined = dict(chapter_payload)
        notes = [
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
            import random
            notes.append(f"Randomized thought: {random.choice(thought_bank)}")
        if self.human_in_loop:
            user_note = input(
                f"Optional refinement note for chapter {chapter_number} (blank to skip): "
            ).strip()
            if user_note:
                notes.append(f"Human note: {user_note}")
        refined["refinement_notes"] = notes
        return refined

class LayoutChapter:
    """
    Crew Agent: LayoutChapter
    Responsible for creating multiple segments for a chapter.
    Implements: Goal, Stakes, Vulnerability, Conflict, Tension, Rationalize, Subversion, Catharsis
    """
    def __init__(self, book_name: str, use_cache: bool, verbose: bool, json_logs: bool, call_genai, extract_json_payload, agent_name: str = "LayoutChapter", provider_instance_name: str | None = None):
        self.book_name = book_name
        self.use_cache = use_cache
        self.verbose = verbose
        self.json_logs = json_logs
        self.call_genai = call_genai
        self.extract_json_payload = extract_json_payload
        self.agent_name = agent_name
        self.provider_instance_name = provider_instance_name

    def create_segment_layout(self, chapter_number: int, chapter_payload: dict, outline_payload: dict, history_root) -> tuple[str, list]:
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
            "For each segment, specify: Goal, Stakes, Vulnerability, Conflict, Tension, Rationalize, Subversion, Catharsis. "
            "Return JSON only."
        )
        response = self.call_genai(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n" + prompt,
            conversation_id=f"{self.book_name}-chapter-{chapter_number}-layout",
            use_cache=self.use_cache,
            history_root=history_root,
            agent_name=self.agent_name,
            verbose=self.verbose,
            json_logs=self.json_logs,
            provider_instance_name=self.provider_instance_name,
        )
        segments = self.extract_json_payload(response)
        return prompt, segments

class DraftChapterSegment:
    """
    Crew Agent: DraftChapterSegment
    Creates independent prompts for each segment and saves them.
    Implements: Mission, Segment Prep, Carry-over, Pivot, etc.
    """
    def __init__(self, encoding: str, manager, provider_instance_name: str | None = None):
        self.encoding = encoding
        self.manager = manager
        self.provider_instance_name = provider_instance_name

    def draft_segment_prompts(
        self,
        *,
        settings,
        gist,
        chapter_number,
        outline_payload,
        chapter_payload,
        segments,
        template_payload,
    ):
        segment_dir = self.manager.get_runtime_segment_prompt_dir(chapter_number)
        self.manager.ensure_dir(segment_dir)
        drafted = []
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
            # Here you would build the prompt using your template logic
            # For now, just a placeholder string
            prompt = f"Segment {index} prompt for {segment_payload['name']}"
            drafted.append(type('DraftedSegmentPrompt', (object,), {"index": index, "segment": segment, "prompt": prompt}))
        return drafted

class GenerateChapterSegment:
    """
    Crew Agent: GenerateChapterSegment
    Generates content for a segment based on the prompt.
    Implements: Physical State, Emotional State, Information State
    """
    def __init__(self, book_name: str, use_cache: bool, verbose: bool, json_logs: bool, call_genai, extract_json_payload, agent_name: str = "GenerateChapterSegment", provider_instance_name: str | None = None):
        self.book_name = book_name
        self.use_cache = use_cache
        self.verbose = verbose
        self.json_logs = json_logs
        self.call_genai = call_genai
        self.extract_json_payload = extract_json_payload
        self.agent_name = agent_name
        self.provider_instance_name = provider_instance_name

    def generate_segment_content(
        self,
        chapter_number: int,
        chapter_root,
        drafted_segments,
        segment_history_roots=None,
    ):
        generated_segments = []
        for item in drafted_segments:
            segment_index = int(item.index)
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
            # For now, just wrap the response in a simple object
            generated_segments.append(type('ChapterSegmentText', (object,), {"index": segment_index, "section": f"segment-{segment_index}", "text": response}))
        return generated_segments
