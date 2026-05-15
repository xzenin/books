# pyrefly: ignore [missing-import]
from crewai import Task
from agents import chief_strategist, topic_researcher, creative_writer, content_editor, synthesizer_assembler
from pydantic import BaseModel
from typing import List, Dict
from models import ChapterState

class OutlineOutput(BaseModel):
    chapters: List[ChapterState]

class DraftsOutput(BaseModel):
    sections_content: Dict[str, str]

def get_define_structure_task(topic: str, overview: str) -> Task:
    return Task(
        description=f"""
Role: You are the Chief Strategist.
Goal: Create a detailed outline for a book.
Context: {overview}.
Requirement: Generate a structured output defining chapters. For each chapter, define distinct sections, including a brief summary and key points for each.
Input: The initial idea is: '{topic}'.
""",
        expected_output="A structured output defining the book's chapters and their constituent sections.",
        agent=chief_strategist,
        output_pydantic=OutlineOutput
    )

def get_chapter_research_task(chapter_number: int, chapter_title: str, sections_info: str) -> Task:
    return Task(
        description=f"""
Perform deep research on the entire chapter's topics, covering all planned sections.
Chapter {chapter_number}: {chapter_title}
Sections to cover:
{sections_info}
""",
        expected_output="Comprehensive research notes covering all sections in the chapter.",
        agent=topic_researcher
    )

def get_draft_sections_task(chapter_number: int, chapter_title: str, book_overview: str, sections_info: str) -> Task:
    return Task(
        description=f"""
Role: You are the Creative Writer.
Goal: Write the content for all sections of Chapter {chapter_number}: "{chapter_title}".
Context: The broader book context is: {book_overview}. 
Instruction: For each of the sections listed below, write a minimum of 800 words of high-quality, engaging prose. Maintain a lucid and compelling voice. Base your writing on the research provided by the Topic Researcher.
Sections to write:
{sections_info}
""",
        expected_output="A mapping of section IDs to their written markdown content.",
        agent=creative_writer,
        output_pydantic=DraftsOutput
    )

def get_chapter_edit_task(chapter_number: int, chapter_title: str) -> Task:
    return Task(
        description=f"""
Review and edit the completed section drafts for Chapter {chapter_number}: "{chapter_title}" for logical flow and voice consistency. 
Ensure the content aligns with the overall book context and that transitions between sections are smooth.
""",
        expected_output="The finalized and polished content for all sections in the chapter.",
        agent=content_editor
    )

def get_final_assembly_task(book_title: str) -> Task:
    return Task(
        description=f"Read all completed chapters from the state, ensure smooth transitions, and write the final book titled '{book_title}' to a file named 'book_draft.md'.",
        expected_output="A confirmation string indicating the file has been written successfully.",
        agent=synthesizer_assembler
    )
