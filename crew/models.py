from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class SectionState(BaseModel):
    id: str
    title: str
    key_points: List[str]
    content: Optional[str] = None
    research_notes: Optional[str] = None
    status: str = "PENDING" # PENDING, RESEARCHING, DRAFTING, EDITED, COMPLETED

class ChapterState(BaseModel):
    number: int
    title: str
    summary: str
    sections: List[SectionState]
    status: str = "PENDING" # PENDING, IN_PROGRESS, COMPLETED
    research_notes: Optional[str] = None

class BookState(BaseModel):
    title: str
    overview: str
    chapters: List[ChapterState] = []
    current_phase: str = "PLANNING" # PLANNING, CHAPTER_EXECUTION, SYNTHESIS, COMPLETE
    config: Dict[str, Any] = {} # e.g., {'parallel_chapters': 3}
