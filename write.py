from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from snapshot_lib import SnapshotConfig, SnapshotManager


TEXT_DUMMY_CONTENT = "hello"
JSON_DUMMY_CONTENT = {"root": "hello"}


def _write_json(path: Path, content: Any, *, encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding) as handle:
        json.dump(content, handle, ensure_ascii=False, indent=2)


def _write_text(path: Path, content: str, *, encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding=encoding)


def _filename_to_method(file_name: str) -> str:
    stem = Path(file_name).stem
    stem = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", stem)
    stem = re.sub(r"\d+", "", stem)
    stem = re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_")
    return stem.lower()


def json_settings(path: Path, content: Any, *, encoding: str) -> None:
    _write_json(path, content, encoding=encoding)


def json_book_outline(path: Path, content: Any, *, encoding: str) -> None:
    _write_json(path, content, encoding=encoding)


def json_book_summary(path: Path, content: Any, *, encoding: str) -> None:
    _write_json(path, content, encoding=encoding)


def json_all_characters(path: Path, content: Any, *, encoding: str) -> None:
    _write_json(path, content, encoding=encoding)


def json_all_settings(path: Path, content: Any, *, encoding: str) -> None:
    _write_json(path, content, encoding=encoding)


def json_book_references(path: Path, content: Any, *, encoding: str) -> None:
    _write_json(path, content, encoding=encoding)


def json_chapter_parameter(path: Path, content: Any, *, encoding: str) -> None:
    _write_json(path, content, encoding=encoding)


def json_default(path: Path, content: Any, *, encoding: str) -> None:
    _write_json(path, content, encoding=encoding)


def text_book_prompt(path: Path, content: str, *, encoding: str) -> None:
    _write_text(path, content, encoding=encoding)


def text_book_foreword(path: Path, content: str, *, encoding: str) -> None:
    _write_text(path, content, encoding=encoding)


def text_book_running_summary(path: Path, content: str, *, encoding: str) -> None:
    _write_text(path, content, encoding=encoding)


def text_chapter_references(path: Path, content: str, *, encoding: str) -> None:
    _write_text(path, content, encoding=encoding)


def text_chapter_prompt(path: Path, content: str, *, encoding: str) -> None:
    _write_text(path, content, encoding=encoding)


def text_chapter_summary(path: Path, content: str, *, encoding: str) -> None:
    _write_text(path, content, encoding=encoding)


def text_chapter_characters(path: Path, content: str, *, encoding: str) -> None:
    _write_text(path, content, encoding=encoding)


def text_chapter_generated(path: Path, content: str, *, encoding: str) -> None:
    _write_text(path, content, encoding=encoding)


def text_chapter_running_summary(path: Path, content: str, *, encoding: str) -> None:
    _write_text(path, content, encoding=encoding)


def text_default(path: Path, content: str, *, encoding: str) -> None:
    _write_text(path, content, encoding=encoding)


def _normalize_json_content(raw: str) -> Any:
    stripped = raw.strip()
    if not stripped:
        return JSON_DUMMY_CONTENT

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return {"root": stripped}

    if isinstance(parsed, (dict, list)):
        return parsed
    return {"root": str(parsed)}


def _prompt_content_for_file(path: Path) -> Any:
    if path.suffix.lower() == ".json":
        raw = input(
            f"JSON content for {path.name} (JSON string or plain text for root; empty=default): "
        )
        return _normalize_json_content(raw)

    raw = input(f"Text content for {path.name} (empty=default): ")
    if not raw:
        return TEXT_DUMMY_CONTENT
    return raw


def _write_dummy_file(path: Path, content: Any, *, encoding: str) -> None:
    extension = path.suffix.lower()
    method = _filename_to_method(path.name)

    if extension == ".json":
        writer = globals().get(f"json_{method}", json_default)
        writer(path, content, encoding=encoding)
        return

    writer = globals().get(f"text_{method}", text_default)
    writer(path, str(content), encoding=encoding)


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
    content_provider: Callable[[Path], Any] | None = None,
) -> Path:
    config = SnapshotConfig.from_json_file(config_path)
    manager = SnapshotManager(config, encoding=encoding)
    book_path = manager.initialize_workspace(workspace_root, book_name)

    provider = content_provider or _prompt_content_for_file

    for path in _iter_configured_files(book_path, config):
        content = provider(path)
        _write_dummy_file(path, content, encoding=encoding)

    return book_path
