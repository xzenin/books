from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProjectSettings:
    book_name: str
    chapter_count: int
    root_folder: str = ""
    date_created: str = ""
    location: str = ""
    user: str = ""


@dataclass
class SegmentBlueprint:
    name: str
    goal: str = ""
    stakes: str = ""
    vulnerability: str = ""
    conflict: str = ""
    tension: str = ""
    rationalize: str = ""
    subversion: str = ""
    catharsis: str = ""

    @classmethod
    def from_payload(cls, payload: dict, *, index: int) -> "SegmentBlueprint":
        return cls(
            name=str(payload.get("name", f"segment-{index}")).strip() or f"segment-{index}",
            goal=str(payload.get("goal", "")).strip(),
            stakes=str(payload.get("stakes", "")).strip(),
            vulnerability=str(payload.get("vulnerability", "")).strip(),
            conflict=str(payload.get("conflict", "")).strip(),
            tension=str(payload.get("tension", "")).strip(),
            rationalize=str(payload.get("rationalize", "")).strip(),
            subversion=str(payload.get("subversion", "")).strip(),
            catharsis=str(payload.get("catharsis", "")).strip(),
        )


@dataclass
class DraftedSegmentPrompt:
    index: int
    segment: SegmentBlueprint
    prompt: str
    prompt_path: Path


@dataclass
class ChapterSegmentText:
    section_title: str
    section: str
    text: str

    def to_dict(self) -> dict[str, str]:
        return {
            "section-title": self.section_title,
            "section": self.section,
            "text": self.text,
        }
