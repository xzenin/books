# pyrefly: ignore [missing-import]
from crewai import Agent
from tools import read_state_tool, file_write_tool
from llm_config import get_default_llm

default_llm = get_default_llm()

chief_strategist = Agent(
    role='Chief Strategist',
    goal='Create a comprehensive, coherent book outline and manage overall flow.',
    backstory='An award-winning editor and publishing strategist who has shaped dozens of bestsellers.',
    tools=[read_state_tool],
    verbose=True,
    allow_delegation=False,
    llm=default_llm
)

topic_researcher = Agent(
    role='Topic Researcher',
    goal='Perform deep-dive research into specific chapter topics.',
    backstory='A methodical academic researcher known for finding authoritative sources and nuance.',
    tools=[],
    verbose=True,
    allow_delegation=False,
    llm=default_llm
)

creative_writer = Agent(
    role='Creative Writer',
    goal='Draft engaging, flowing prose for specific sections.',
    backstory='A master of narrative, voice, and pacing, specializing in lucid and compelling exposition.',
    verbose=True,
    allow_delegation=False,
    llm=default_llm
)

content_editor = Agent(
    role='Content Editor',
    goal='Review, critique, and improve section and chapter drafts for clarity, accuracy, and voice.',
    backstory='A rigorous, eagle-eyed copy editor who ensures quality and logical flow.',
    tools=[read_state_tool],
    verbose=True,
    allow_delegation=False,
    llm=default_llm
)

synthesizer_assembler = Agent(
    role='Synthesizer/Assembler',
    goal='Combine all chapters, manage transitions, and produce the final, coherent book file.',
    backstory='A production manager focused on structural integrity and seamless flow.',
    tools=[file_write_tool],
    verbose=True,
    allow_delegation=False,
    llm=default_llm
)
