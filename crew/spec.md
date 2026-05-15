# Specification: High-Performance CrewAI Book Writing Workflow

## 1. Executive Summary
This document specifies the architecture for an automated book writing system using CrewAI. The primary objective is to generate a high-quality, long-form non-fiction or fiction book. The system must handle a nested hierarchy (Book $\rightarrow$ Chapters $\rightarrow$ Sections), utilize parallel processing for efficiency, and maintain a robust, persistent state for stop/resume capabilities.

## 2. System Architecture & Philosophy
The system adopts a **Hierarchical Process** with managed decentralized execution. A top-level "Manager Agent" (or a main controlling script) handles the high-level orchestration, but delegates chapter-level and section-level creation to specialized crews that can run in parallel.

### 2.1 The "Divide and Conquer" Model
Writing a whole book is too complex for a single context window and prone to "forgetting." The system divides the problem into:

1.  **Orchestration Phase:** Define structure and manage state.
2.  **Chapter Phase (Parallel):** Research and draft chapters.
3.  **Synthesis Phase:** Review, refine, and compile.

## 3. Agents & Roles
We define a set of specialized agents with distinct personalities, goals, and tools.

| Role | Goal | Backstory | Required Tools |
| :--- | :--- | :--- | :--- |
| **Chief Strategist** | Create a comprehensive, coherent book outline and manage overall flow. | An award-winning editor and publishing strategist who has shaped dozens of bestsellers. | `SearchTool`, `ReadStateTool` |
| **Topic Researcher** | Perform deep-dive research into specific chapter topics. | A methodical academic researcher known for finding authoritative sources and nuance. | `SearchTool`, `ScrapeWebsiteTool`, `MemoryTool` |
| **Creative Writer** | Draft engaging, flowing prose for specific sections. | A master of narrative, voice, and pacing, specializing in lucid and compelling exposition. | `MemoryTool` |
| **Content Editor** | Review, critique, and improve section and chapter drafts for clarity, accuracy, and voice. | A rigorous, eagle-eyed copy editor who ensures quality and logical flow. | `ReadStateTool` |
| **Synthesizer/Assembler** | Combine all chapters, manage transitions, and produce the final, coherent book file. | A production manager focused on structural integrity and seamless flow. | `FileWriteTool` |

## 4. The Data Model (State & Hierarchy)
To manage state, resume capability, and the hierarchical nature, we need a formalized data structure. This is implemented using a Pydantic state model.

### 4.1 Input/Output Shapes

#### Final Output Shape (The Book)
```json
{
  "book_title": "Understanding Artificial Intelligence",
  "total_chapters": 12,
  "chapters": [
    {
      "chapter_number": 1,
      "chapter_title": "The Dawn of AI",
      "summary": "...",
      "sections": [
        {"id": "c1s1", "title": "History", "content": "..."},
        {"id": "c1s2", "title": "Key Figures", "content": "... "}
      ]
    }
  ]
}
```

#### Intermediate Section Input Shape
This object is passed *to* a section writer agent.
```json
{
  "book_context": { "title": "...", "target_audience": "...", "tone": "..." },
  "chapter_context": { "title": "...", "goal": "...", "sequence_position": 1 },
  "section_context": { "title": "...", "key_points_to_cover": ["...", "..."] }
}
```

#### Intermediate Section Output Shape
This object is returned *by* a section writer agent.
```json
{
  "id": "c1s1",
  "title": "History of AI",
  "content": "Full section text in markdown...",
  "status": "DRAFTED"
}
```

### 4.2 State Management Model (Pydantic)
We will use a central `BookState` class. This is *the* single source of truth and allows for saving/loading.

```python
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

class BookState(BaseModel):
    title: str
    overview: str
    chapters: List[ChapterState] = []
    current_phase: str = "PLANNING" # PLANNING, CHAPTER_EXECUTION, SYNTHESIS, COMPLETE
    config: Dict[str, Any] = {} # e.g., {'parallel_chapters': 3}
```

## 5. Workflow & Task Specifications

This workflow defines the clear tasks and their inputs/outputs.

### Phase 1: Planning (Sequential)

| Task ID | Task Description | Assigned Agent | Input | Expected Output (State Update) |
| :--- | :--- | :--- | :--- | :--- |
| **T1.1_DefineStructure** | Receive a book topic/idea. Create a detailed outline (chapters and sections) with key points. | Chief Strategist | Topic/Goal string. | Updates `state.chapters` with structure, all in `PENDING` status. |

**Task T1.1 Prompt Pattern:**
```text
Role: You are the Chief Strategist.
Goal: Create a detailed outline for a book titled '{state.title}'.
Context: {state.overview}.
Requirement: Generate a structured output (JSON or Pydantic format) defining [10] chapters. For each chapter, define [3-5] distinct sections, including a brief summary for each.
Input: The initial idea is: '{initial_idea}'.
Output format: {ChapterState Pydantic structure}
```

---

### Phase 2: Chapter Execution (Parallel)

This is where parallel execution happens. We use a **Chapter-Level Crew** for *each* chapter in the `state.chapters` list. The main execution script iterates over the state and launches these crews, potentially limiting concurrent crews (e.g., to 3) to manage API rate limits.

#### Inside the Chapter Crew (Managed Process)

This crew is instantiated for a *specific* chapter (e.g., Chapter 1).

| Task ID | Task Description | Assigned Agent | Input | Expected Output |
| :--- | :--- | :--- | :--- | :--- |
| **T2.1_ChapterResearch** | Perform deep research on the entire chapter's topics, covering all planned sections. | Topic Researcher | Chapter outline and `section.key_points`. | Comphrehensive research notes stored in `chapter.research_notes` in state. |
| **T2.2_DraftSections** | Draft the detailed prose for *all* sections in the chapter, utilizing the research notes and adhering to the planned points. | Creative Writer | `chapter.research_notes`, section structure, and book context. | Updates `section.content` and sets `section.status` to `DRAFTED`. |
| **T2.3_ChapterEdit** | Review and edit the completed section drafts for logical flow and voice consistency. | Content Editor | All `section.content` for the chapter. | Sets `chapter.status` to `COMPLETED`. |

**Task T2.2 Prompt Pattern (Writing):**
```text
Role: You are the Creative Writer.
Goal: Write the content for all sections of Chapter {chapter.number}: "{chapter.title}".
Context: The broader book context is: {state.overview}. The deep research findings for this chapter are: {chapter.research_notes}.
Instruction: For each of the sections listed below, write a minimum of 800 words of high-quality, engaging prose. Maintain a lucid and compelling voice.
Sections to write:
  - {section_1.title}: {section_1.key_points}
  - {section_2.title}: {section_2.key_points}
  ...
Output Format: A JSON object where keys are section IDs and values are the written markdown content.
```

---

### Phase 3: Synthesis (Sequential)

| Task ID | Task Description | Assigned Agent | Input | Expected Output |
| :--- | :--- | :--- | :--- | :--- |
| **T3.1_FinalAssembly** | Read all completed chapters from the state, ensure smooth transitions, and write the final book to a file. | Synthesizer / Assembler | The entire populated `state` object. | A final `book_draft.md` file. Sets `state.current_phase` to `COMPLETE`. |

## 6. Stop, Resume, and Complete

The system achieves robust persistence by synchronizing the in-memory `BookState` (Pydantic model) with a JSON file on disk *after every significant task completion*.

### The Stateful Execution Loop (Main Script)

The main Python script controls the flow. It does not execute the whole Crew at once; it orchestrates the process and manages state.

```python
import json
import os
from pydantic import ValidationError
# (Import agents, tasks, BookState, Chapter Crew definition)

STATE_FILE = "book_writing_state.json"

def load_state() -> BookState:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state_data = json.load(f)
                return BookState(**state_data)
        except (ValidationError, json.JSONDecodeError):
            print("Error loading state. Starting fresh.")
    return BookState(title="Untitled", overview="New Book")

def save_state(state: BookState):
    with open(STATE_FILE, "w") as f:
        f.write(state.model_dump_json(indent=2))

def run_workflow():
    state = load_state()
    # ----------------------------------------------------
    # PHASE 1: PLANNING
    # ----------------------------------------------------
    if state.current_phase == "PLANNING":
        # Check if structure already exists
        if not state.chapters:
            # 1. Instantiate definition task and Agent
            # 2. Run planning crew (single task)
            # 3. Update state
            # 4. Save state
            print("Running Planning Phase...")
            # ... execution logic ...
            # state.chapters = ... result ...
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
            # Use Python's concurrent.futures or a managed pool
            # to run Chapter Crews for each pending_chapter.
            
            # --- Inside the Parallel Chapter Process ---
            # 1. Run Chapter Crew (Research, Draft, Edit)
            # 2. IMPORTANT: Return the modified chapter object
            # --- End Parallel Process ---
            
            # 3. In the MAIN script: receive chapter updates,
            #    update 'state.chapters', and SAVE STATE after each chapter completes.
            # state.current_phase = "SYNTHESIS" # Set when all futures are done
            # save_state(state)

    # ----------------------------------------------------
    # PHASE 3: SYNTHESIS
    # ----------------------------------------------------
    if state.current_phase == "SYNTHESIS":
        print("Running Synthesis Phase...")
        # Run Synthesis Crew (T3.1)
        # Update state, set phase to COMPLETE
        save_state(state)

    if state.current_phase == "COMPLETE":
        print("Book writing workflow complete.")

# To stop: Simply terminate the script execution.
# To resume: Run 'run_workflow()' again. It will load from the file and continue.
```

## 7. Memory Management

This specification utilizes both CrewAI's built-in memory and explicit state injection.

1.  **Implicit Agent Memory:** We enable memory (e.g., RAG-based) for the **Topic Researcher** and **Creative Writer** agents. This allows them to "remember" findings *within* the context of a single chapter's execution.
2.  **Explicit State Injection (RAG replacement):** The best way to manage long-term context (e.g., the whole book's premise, audience, and the outcomes of previous chapters) is by injecting that data **directly into the task prompts**.
    *   For example, when writing Chapter 5, the prompt will explicitly include a summary of Chapters 1-4, which is pulled from the `BookState`. This prevents context window overflow while ensuring awareness of previous content.

## 8. Summary of Specifications Met

| User Goal | Implementation |
| :--- | :--- |
| **1) Multiple task** | Defined 5+ distinct tasks across planning, writing, editing, and synthesis. |
| **2) Multiple agent** | Defined 5 specialized agents with roles, backstories, and specific goals. |
| **3) Parallel execution** | The main script launches separate Chapter-Level Crews in parallel, utilizing a `ThreadPoolExecutor` or similar Python mechanism. |
| **4) Clear prompt** | Provided explicit prompt patterns with `Role`, `Goal`, `Context`, `Instruction`, and `Output Format`. |
| **5) Clear I/O shape** | Formalized using Pydantic models (BookState, ChapterState, SectionState) and defined JSON output shapes. |
| **6) Memory management** | Combination of CrewAI built-in memory for chapter context and explicit injection of prior chapter summaries into prompts for long-term coherence. |
| **7) State management** | Controlled by a central, serialized Pydantic `BookState` object, updated after every task or chapter completion. |
| **8) Maintain history** | The serialized state file acts as a history of progress. The `memory=True` setting also provides per-agent history. |
| **9) Stop, Resume, Complete** | The execution loop checks `state.current_phase` and `chapter.status` on startup. If a process stops, it resumes from the last *saved* state (the last completed chapter). |
| **10) Maintain hierarchy** | The Pydantic model itself is a tree-like data structure mirroring the physical book structure: `BookState -> ChapterState -> SectionState`. |