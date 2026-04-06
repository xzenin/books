from dataclasses import dataclass

@dataclass
class ProjectSettings:
    book_name: str
    chapter_count: int
    root_folder: str
    date_created: str
    location: str
    user: str
