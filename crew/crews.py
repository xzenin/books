# pyrefly: ignore [missing-import]
from crewai import Crew, Process
from agents import chief_strategist, topic_researcher, creative_writer, content_editor, synthesizer_assembler
from tasks import (
    get_define_structure_task,
    get_chapter_research_task,
    get_draft_sections_task,
    get_chapter_edit_task,
    get_final_assembly_task
)
from llm_config import get_embedder_config

def create_planning_crew(topic: str, overview: str) -> Crew:
    return Crew(
        agents=[chief_strategist],
        tasks=[get_define_structure_task(topic, overview)],
        process=Process.sequential,
        verbose=True
    )

def create_chapter_crew(chapter_number: int, chapter_title: str, book_overview: str, sections_info: str) -> Crew:
    return Crew(
        agents=[topic_researcher, creative_writer, content_editor],
        tasks=[
            get_chapter_research_task(chapter_number, chapter_title, sections_info),
            get_draft_sections_task(chapter_number, chapter_title, book_overview, sections_info),
            get_chapter_edit_task(chapter_number, chapter_title)
        ],
        process=Process.sequential,
        verbose=True
    )

def create_synthesis_crew(book_title: str) -> Crew:
    return Crew(
        agents=[synthesizer_assembler],
        tasks=[get_final_assembly_task(book_title)],
        process=Process.sequential,
        verbose=True
    )
