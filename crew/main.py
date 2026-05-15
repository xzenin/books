import json
import os
import sys
import concurrent.futures
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

# Fix Windows console emoji encoding issues
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from pydantic import ValidationError
from models import BookState, ChapterState
from crews import create_planning_crew, create_chapter_crew, create_synthesis_crew

STATE_FILE = "book_writing_state.json"

def load_state() -> BookState:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state_data = json.load(f)
                return BookState(**state_data)
        except (ValidationError, json.JSONDecodeError):
            print("Error loading state. Starting fresh.")
    return BookState(
        title="Understanding Artificial Intelligence", 
        overview="A comprehensive guide to the history, concepts, and future of AI."
    )

def save_state(state: BookState):
    with open(STATE_FILE, "w") as f:
        f.write(state.model_dump_json(indent=2))

def format_sections_info(chapter: ChapterState) -> str:
    sections_info = []
    for section in chapter.sections:
        sections_info.append(f"- {section.id}: {section.title} - {', '.join(section.key_points)}")
    return "\n".join(sections_info)

def process_chapter(chapter: ChapterState, book_overview: str) -> ChapterState:
    print(f"Starting Chapter {chapter.number}: {chapter.title}")
    chapter.status = "IN_PROGRESS"
    
    sections_info = format_sections_info(chapter)
    
    crew = create_chapter_crew(
        chapter_number=chapter.number,
        chapter_title=chapter.title,
        book_overview=book_overview,
        sections_info=sections_info
    )
    
    # Run the crew
    crew.kickoff()
    
    # Extract the drafted sections content
    drafts_task = crew.tasks[1]
    if drafts_task.output and drafts_task.output.pydantic:
        drafts = drafts_task.output.pydantic
        content_dict = drafts.sections_content
        for section in chapter.sections:
            if section.id in content_dict:
                section.content = content_dict[section.id]
            else:
                section.content = "Drafting failed to generate content for this section."
            section.status = "COMPLETED"
    else:
        print(f"Warning: Draft task for chapter {chapter.number} did not return structured data.")
        for section in chapter.sections:
            section.status = "COMPLETED"

    # Assume editing task outputs the final combined chapter content, we could also capture it,
    # but based on spec we just need the sections to be drafted and chapter edited.
    
    chapter.status = "COMPLETED"
    print(f"Completed Chapter {chapter.number}: {chapter.title}")
    return chapter

def run_workflow():
    state = load_state()
    
    # ----------------------------------------------------
    # PHASE 1: PLANNING
    # ----------------------------------------------------
    if state.current_phase == "PLANNING":
        if not state.chapters:
            print("Running Planning Phase...")
            planning_crew = create_planning_crew(state.title, state.overview)
            planning_crew.kickoff()
            
            # Extract output Pydantic
            try:
                task_output = planning_crew.tasks[0].output
                if task_output and task_output.pydantic:
                    outline = task_output.pydantic
                    state.chapters = outline.chapters
                else:
                    print("Failed to get pydantic output. Output was:", task_output)
                    return
            except Exception as e:
                print(f"Error parsing planning output: {e}")
                return
                
            state.current_phase = "CHAPTER_EXECUTION"
            save_state(state)
        else:
            print("Structure already defined. Skipping Planning.")
            state.current_phase = "CHAPTER_EXECUTION"
            save_state(state)

    # ----------------------------------------------------
    # PHASE 2: CHAPTER EXECUTION (PARALLEL)
    # ----------------------------------------------------
    if state.current_phase == "CHAPTER_EXECUTION":
        pending_chapters = [c for c in state.chapters if c.status != "COMPLETED"]

        if not pending_chapters:
            print("All chapters complete.")
            state.current_phase = "SYNTHESIS"
            save_state(state)
        else:
            print(f"Executing {len(pending_chapters)} pending chapters...")
            
            max_workers = state.config.get('parallel_chapters', 3)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_chapter = {
                    executor.submit(process_chapter, chapter, state.overview): chapter 
                    for chapter in pending_chapters
                }
                
                for future in concurrent.futures.as_completed(future_to_chapter):
                    completed_chapter = future.result()
                    
                    for i, c in enumerate(state.chapters):
                        if c.number == completed_chapter.number:
                            state.chapters[i] = completed_chapter
                            break
                            
                    save_state(state)
            
            if all(c.status == "COMPLETED" for c in state.chapters):
                state.current_phase = "SYNTHESIS"
                save_state(state)

    # ----------------------------------------------------
    # PHASE 3: SYNTHESIS
    # ----------------------------------------------------
    if state.current_phase == "SYNTHESIS":
        print("Running Synthesis Phase...")
        synthesis_crew = create_synthesis_crew(state.title)
        synthesis_crew.kickoff()
        
        state.current_phase = "COMPLETE"
        save_state(state)

    if state.current_phase == "COMPLETE":
        print("Book writing workflow complete.")

if __name__ == "__main__":
    run_workflow()
