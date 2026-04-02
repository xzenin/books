from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(
        prog="init.py",
        description="Create book folder/file structure from init.json template.",
        epilog=(
            "Examples:\n"
            "  python init.py --book-name Ramayan\n"
            "  python init.py --book-name Sita --workspace-root .\\_workspace\n"
            "  python init.py --book-name Demo --config-path .\\init.json"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--workspace-root",
        default=str(script_dir / "_workspace"),
        help="Optional. Root directory where the book folder will be created.",
    )
    parser.add_argument(
        "--book-name",
        required=True,
        help="Mandatory. Book folder name to create under workspace root.",
    )
    parser.add_argument(
        "--config-path",
        default=str(script_dir / "init.json"),
        help="Optional. Path to JSON config template.",
    )

    return parser.parse_args()


def ensure_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    args = parse_args()

    workspace_root = Path(args.workspace_root)
    book_name = args.book_name
    config_path = Path(args.config_path)

    config = load_config(config_path)

    book_path = workspace_root / book_name
    chapters_root = book_path / "BookChapters"

    book_path.mkdir(parents=True, exist_ok=True)
    chapters_root.mkdir(parents=True, exist_ok=True)

    for file_name in config["rootFiles"]:
        ensure_file(book_path / file_name)

    chapters_cfg = config["chapters"]
    start = int(chapters_cfg["start"])
    end = int(chapters_cfg["end"])

    for n in range(start, end + 1):
        chapter_folder_name = chapters_cfg["chapterFolderPattern"].replace("{n}", str(n))
        chapter_path = chapters_root / chapter_folder_name
        chapter_path.mkdir(parents=True, exist_ok=True)

        for chapter_file_pattern in chapters_cfg["chapterFiles"]:
            chapter_file_name = chapter_file_pattern.replace("{n}", str(n))
            ensure_file(chapter_path / chapter_file_name)

        out_folder_name = chapters_cfg["chapterOutFolderPattern"].replace("{n}", str(n))
        out_path = chapter_path / out_folder_name
        out_path.mkdir(parents=True, exist_ok=True)

        for out_file_pattern in chapters_cfg["chapterOutFiles"]:
            out_file_name = out_file_pattern.replace("{n}", str(n))

            # Keep chapter 1 running summary file aligned with current convention.
            if n == 1 and out_file_name == "Chapter1RunningSummary.txt":
                out_file_name = chapters_cfg["chapter1RunningSummaryFile"]

            ensure_file(out_path / out_file_name)

    print(f"Structure created at: {book_path}")


if __name__ == "__main__":
    main()
