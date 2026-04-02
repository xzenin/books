from __future__ import annotations

import json
from pathlib import Path

from snapshot_lib import SnapshotConfig, SnapshotManager


TEXT_DUMMY_CONTENT = "hello"
JSON_DUMMY_CONTENT = {"root": "hello"}


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


def write_dummy_content(
    *,
    workspace_root: str | Path,
    book_name: str,
    config_path: str | Path,
    encoding: str = "utf-8",
) -> Path:
    config = SnapshotConfig.from_json_file(config_path)
    manager = SnapshotManager(config, encoding=encoding)
    book_path = manager.initialize_workspace(workspace_root, book_name)

    for path in _iter_configured_files(book_path, config):
        _write_dummy_file(path, encoding=encoding)

    return book_path
