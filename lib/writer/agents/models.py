from ..writables import ProjectSettings
from ..io.io_helpers import read_text, load_json_file
import json
from pathlib import Path
from typing import Any

class Book:
    def __init__(self, settings: ProjectSettings, gist: str, template_payload: Any):
        self.settings = settings
        self.gist = gist
        self.template_payload = template_payload

    @staticmethod
    def load_template(encoding: str = "utf-8"):
        path = Path(__file__).resolve().parents[2] / "templates" / "book_prompt.txt"
        return read_text(path, encoding=encoding)

    def build_prompt(self) -> str:
        template_text = self.load_template()
        book_template_json = json.dumps(self.template_payload, ensure_ascii=False, indent=2)
        return template_text.format(
            book_gist=self.gist,
            book_template_json=book_template_json,
            chapter_count=self.settings.chapter_count,
        )

    # Add more methods for layout, output, etc.

class Chapter:
    def __init__(self, settings: ProjectSettings, book_gist: str, book_summary: str, chapter_summary: str, chapter_payload: Any, chapter_template_json: Any):
        self.settings = settings
        self.book_gist = book_gist
        self.book_summary = book_summary
        self.chapter_summary = chapter_summary
        self.chapter_payload = chapter_payload
        self.chapter_template_json = chapter_template_json

    @staticmethod
    def load_template(encoding: str = "utf-8"):
        path = Path(__file__).resolve().parents[2] / "templates" / "chapter_prompt.txt"
        return read_text(path, encoding=encoding)

    def build_prompt(self) -> str:
        template_text = self.load_template()
        chapter_template_json_str = json.dumps(self.chapter_template_json, ensure_ascii=False, indent=2)
        return template_text.format(
            book_gist=self.book_gist,
            book_summary=self.book_summary,
            chapter_summary=self.chapter_summary,
            chapter_template_json=chapter_template_json_str,
        )

    # Add more methods for layout, output, etc.

class ChapterSegment:
    def __init__(self, book_gist: str, book_summary: str, chapter_gist: str, segment_summary: str, segment_template_json: Any, segment_index: int, carry_over: str):
        self.book_gist = book_gist
        self.book_summary = book_summary
        self.chapter_gist = chapter_gist
        self.segment_summary = segment_summary
        self.segment_template_json = segment_template_json
        self.segment_index = segment_index
        self.carry_over = carry_over

    @staticmethod
    def load_template(encoding: str = "utf-8"):
        path = Path(__file__).resolve().parents[2] / "templates" / "segment_prompt.txt"
        return read_text(path, encoding=encoding)

    def build_prompt(self) -> str:
        template_text = self.load_template()
        segment_template_json_str = json.dumps(self.segment_template_json, ensure_ascii=False, indent=2)
        return template_text.format(
            book_gist=self.book_gist,
            book_summary=self.book_summary,
            chapter_gist=self.chapter_gist,
            segment_summary=self.segment_summary,
            segment_template_json=segment_template_json_str,
            segment_index=self.segment_index,
            carry_over=self.carry_over,
        )

    # Add more methods for layout, output, etc.
