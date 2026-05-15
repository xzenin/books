import json
import os
from crewai.tools import tool
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from models import BookState

# Initialize standard CrewAI tools
search_tool = SerperDevTool()
scrape_tool = ScrapeWebsiteTool()

STATE_FILE = "book_writing_state.json"

@tool("ReadStateTool")
def read_state_tool() -> str:
    """Reads the current book state from the state file and returns it as a JSON string."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return f.read()
    return "{}"

@tool("FileWriteTool")
def file_write_tool(content: str, filename: str = "book_draft.md") -> str:
    """Writes the final assembled book content to a markdown file."""
    with open(filename, "w", encoding='utf-8') as f:
        f.write(content)
    return f"Successfully wrote content to {filename}"
