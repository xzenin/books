from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(
        prog="generateprompt.py",
        description="Generate sample content for all template files in a book workspace.",
        epilog=(
            "Examples:\n"
            "  python generateprompt.py --book-name DemoBook --user-input \"Courage and Duty\"\n"
            "  python generateprompt.py --book-name DemoBook\n"
            "  python generateprompt.py --book-name DemoBook --workspace-root .\\_workspace --config-path .\\init.json --user-input Leadership"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--workspace-root",
        default=str(script_dir / "_workspace"),
        help="Optional. Root folder where the book folder is created.",
    )
    parser.add_argument(
        "--book-name",
        required=True,
        help="Mandatory. Name of the target book folder under workspace root.",
    )
    parser.add_argument(
        "--config-path",
        default=str(script_dir / "init.json"),
        help="Optional. Path to init.json template config.",
    )
    parser.add_argument(
        "--user-input",
        default="",
        help="Optional. Theme/topic used to generate content. Prompted if omitted.",
    )

    return parser.parse_args()


def ensure_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)


def append_text(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


def write_json(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=True, indent=2)


def write_settings_json(path: Path, book_name: str, user_input: str) -> None:
    write_json(
        path,
        {
            "bookName": book_name,
            "theme": user_input,
            "language": "en",
            "tone": "Narrative",
            "createdAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        },
    )


def write_book_outline_json(path: Path, book_name: str, user_input: str) -> None:
    write_json(
        path,
        {
            "title": book_name,
            "concept": user_input,
            "outline": [
                f"Introduction to {user_input}",
                f"Rising conflict around {user_input}",
                "Resolution and conclusion",
            ],
        },
    )


def write_book_summary_json(path: Path, book_name: str, user_input: str) -> None:
    write_json(
        path,
        {
            "title": book_name,
            "summary": f"This book explores {user_input} through progressive chapters.",
        },
    )


def write_all_characters_json(path: Path, user_input: str) -> None:
    write_json(
        path,
        {
            "characters": [
                {"name": "Lead", "role": "Protagonist", "relationToTheme": user_input},
                {"name": "Guide", "role": "Mentor", "relationToTheme": "Supports the journey"},
            ]
        },
    )


def write_all_settings_json(path: Path, user_input: str) -> None:
    write_json(
        path,
        {
            "world": "Sample world",
            "backdrop": f"Built around {user_input}",
            "timeline": "Ancient to modern transition",
        },
    )


def write_book_references_json(path: Path, user_input: str) -> None:
    write_json(
        path,
        {
            "references": [
                f"Primary source for {user_input}",
                "Secondary context and notes",
            ]
        },
    )


def write_book_prompt_txt(path: Path, book_name: str, user_input: str) -> None:
    append_text(path, f"Create a cohesive narrative for '{book_name}' focused on '{user_input}'.")


def write_book_foreword_txt(path: Path, book_name: str, user_input: str) -> None:
    append_text(path, f"Foreword: '{book_name}' introduces the journey of {user_input}.")


def write_chapter_parameter_json(path: Path, chapter_number: int, user_input: str) -> None:
    write_json(
        path,
        {
            "chapter": chapter_number,
            "objective": f"Advance the narrative around {user_input}",
            "targetWords": 1200,
        },
    )


def write_chapter_references_txt(path: Path, chapter_number: int, user_input: str) -> None:
    append_text(path, f"Chapter {chapter_number} references for {user_input}: add source notes here.")


def write_chapter_prompt_txt(path: Path, chapter_number: int, book_name: str, user_input: str) -> None:
    append_text(
        path,
        f"Write Chapter {chapter_number} of '{book_name}' centered on '{user_input}' with continuity.",
    )


def write_chapter_summary_txt(path: Path, chapter_number: int, user_input: str) -> None:
    append_text(path, f"Summary: Chapter {chapter_number} develops the theme '{user_input}'.")


def write_chapter_characters_txt(path: Path, chapter_number: int, user_input: str) -> None:
    append_text(
        path,
        f"Characters in Chapter {chapter_number} affected by '{user_input}': Lead, Guide.",
    )


def write_chapter_generated_txt(path: Path, chapter_number: int, book_name: str, user_input: str) -> None:
    append_text(
        path,
        f"Generated draft for Chapter {chapter_number} of '{book_name}' on '{user_input}'.",
    )


def write_chapter_running_summary_txt(path: Path, chapter_number: int, user_input: str) -> None:
    append_text(
        path,
        f"Running summary up to Chapter {chapter_number}: key progress on '{user_input}'.",
    )


def write_root_file_content(file_name: str, file_path: Path, book_name: str, user_input: str) -> None:
    if file_name == "Settings.json":
        write_settings_json(file_path, book_name, user_input)
    elif file_name == "BookOutline.json":
        write_book_outline_json(file_path, book_name, user_input)
    elif file_name == "BookSummary.json":
        write_book_summary_json(file_path, book_name, user_input)
    elif file_name == "AllCharacters.json":
        write_all_characters_json(file_path, user_input)
    elif file_name == "AllSettings.json":
        write_all_settings_json(file_path, user_input)
    elif file_name == "BookReferences.json":
        write_book_references_json(file_path, user_input)
    elif file_name == "BookPrompt.txt":
        write_book_prompt_txt(file_path, book_name, user_input)
    elif file_name == "BookForeword.txt":
        write_book_foreword_txt(file_path, book_name, user_input)
    else:
        append_text(file_path, f"Sample content for {file_name} using '{user_input}'.")


def write_chapter_file_content(
    file_name: str,
    file_path: Path,
    chapter_number: int,
    book_name: str,
    user_input: str,
) -> None:
    if re.match(r"^Chapter\d+Parameter\.json$", file_name):
        write_chapter_parameter_json(file_path, chapter_number, user_input)
    elif re.match(r"^Chapter\d+References\.txt$", file_name):
        write_chapter_references_txt(file_path, chapter_number, user_input)
    elif re.match(r"^Chapter\d+Prompt\.txt$", file_name):
        write_chapter_prompt_txt(file_path, chapter_number, book_name, user_input)
    elif re.match(r"^Chapter\d+Summary\.txt$", file_name):
        write_chapter_summary_txt(file_path, chapter_number, user_input)
    elif re.match(r"^Chapter\d+Characters\.txt$", file_name):
        write_chapter_characters_txt(file_path, chapter_number, user_input)
    elif re.match(r"^Chapter\d+Generated\.txt$", file_name):
        write_chapter_generated_txt(file_path, chapter_number, book_name, user_input)
    elif re.match(r"^Chapter\d+RunningSummary\.txt$", file_name) or file_name == "ChapterRunningSummary.txt":
        write_chapter_running_summary_txt(file_path, chapter_number, user_input)
    else:
        append_text(file_path, f"Sample chapter content for {file_name} using '{user_input}'.")


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    args = parse_args()

    user_input = (args.user_input or "").strip()
    if not user_input:
        user_input = input("Enter the theme/topic to generate sample content: ").strip()
    if not user_input:
        raise ValueError("User input cannot be empty.")

    workspace_root = Path(args.workspace_root)
    book_name = args.book_name
    config = load_config(Path(args.config_path))

    book_path = workspace_root / book_name
    chapters_root = book_path / "BookChapters"

    book_path.mkdir(parents=True, exist_ok=True)
    chapters_root.mkdir(parents=True, exist_ok=True)

    for file_name in config["rootFiles"]:
        file_path = book_path / file_name
        ensure_file(file_path)
        write_root_file_content(file_name, file_path, book_name, user_input)

    chapters_cfg = config["chapters"]
    start = int(chapters_cfg["start"])
    end = int(chapters_cfg["end"])

    for n in range(start, end + 1):
        chapter_folder_name = chapters_cfg["chapterFolderPattern"].replace("{n}", str(n))
        chapter_path = chapters_root / chapter_folder_name
        chapter_path.mkdir(parents=True, exist_ok=True)

        for chapter_file_pattern in chapters_cfg["chapterFiles"]:
            chapter_file_name = chapter_file_pattern.replace("{n}", str(n))
            chapter_file_path = chapter_path / chapter_file_name
            ensure_file(chapter_file_path)
            write_chapter_file_content(chapter_file_name, chapter_file_path, n, book_name, user_input)

        out_folder_name = chapters_cfg["chapterOutFolderPattern"].replace("{n}", str(n))
        out_path = chapter_path / out_folder_name
        out_path.mkdir(parents=True, exist_ok=True)

        for out_file_pattern in chapters_cfg["chapterOutFiles"]:
            out_file_name = out_file_pattern.replace("{n}", str(n))
            if n == 1 and out_file_name == "Chapter1RunningSummary.txt":
                out_file_name = chapters_cfg["chapter1RunningSummaryFile"]

            out_file_path = out_path / out_file_name
            ensure_file(out_file_path)
            write_chapter_file_content(out_file_name, out_file_path, n, book_name, user_input)

    print(f"Structure and sample content generated at: {book_path}")


if __name__ == "__main__":
    main()
