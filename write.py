from __future__ import annotations

import argparse
import json
from pathlib import Path

from snapshot_lib import SnapshotConfig, SnapshotManager


TEXT_DUMMY_CONTENT = "hello"
JSON_DUMMY_CONTENT = {"root": "hello"}


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(
        prog="write.py",
        description="Write dummy content to all configured files in a book workspace.",
        epilog=(
            "Examples:\n"
            "  python write.py --book-name Sita\n"
            "  python write.py --book-name Ramayan --workspace-root .\\_workspace\n"
            "  python write.py --book-name Demo --config-path .\\init.json"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--workspace-root",
        default=str(script_dir / "_workspace"),
        help="Optional. Root folder where the book folder exists.",
    )
    parser.add_argument(
        "--book-name",
        required=True,
        help="Mandatory. Target book folder under workspace root.",
    )
    parser.add_argument(
        "--config-path",
        default=str(script_dir / "init.json"),
        help="Optional. Path to init.json template config.",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Optional. Text encoding used for read/write.",
    )

    return parser.parse_args()


def _write_dummy_file(path: Path, *, encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".json":
        with path.open("w", encoding=encoding) as handle:
            json.dump(JSON_DUMMY_CONTENT, handle, ensure_ascii=False, indent=2)
        return

    path.write_text(TEXT_DUMMY_CONTENT, encoding=encoding)


def _iter_configured_files(book_path: Path, config: SnapshotConfig) -> list[Path]:
    paths: list[Path] = []

    for file_name in config.bookRootFiles:
        paths.append(book_path / file_name)

    chapter_root = book_path / "BookChapters"
    chapter_cfg = config.chapters
    for number in range(chapter_cfg.start, chapter_cfg.end + 1):
        chapter_folder = chapter_cfg.chapterFolderPattern.replace("{n}", str(number))
        chapter_path = chapter_root / chapter_folder

        for pattern in chapter_cfg.chapterFiles:
            paths.append(chapter_path / pattern.replace("{n}", str(number)))

        out_folder = chapter_cfg.chapterOutFolderPattern.replace("{n}", str(number))
        out_path = chapter_path / out_folder
        for pattern in chapter_cfg.chapterOutFiles:
            file_name = pattern.replace("{n}", str(number))
            if number == 1 and file_name == "Chapter1RunningSummary.txt" and chapter_cfg.chapter1RunningSummaryFile:
                file_name = chapter_cfg.chapter1RunningSummaryFile
            paths.append(out_path / file_name)

    return paths


def main() -> None:
    args = parse_args()

    config = SnapshotConfig.from_json_file(args.config_path)
    manager = SnapshotManager(config, encoding=args.encoding)
    book_path = manager.initialize_workspace(args.workspace_root, args.book_name)

    for path in _iter_configured_files(book_path, config):
        _write_dummy_file(path, encoding=args.encoding)

    print(f"Dummy content written to: {book_path}")


if __name__ == "__main__":
    main()
