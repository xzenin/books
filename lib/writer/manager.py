from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .models import ChapterSnapshot, SnapshotConfig, WorkspaceSnapshot


class SnapshotManager:
    def __init__(
        self,
        config: SnapshotConfig,
        *,
        encoding: str = "utf-8",
        verbose: bool = False,
        json_logs: bool = False,
    ) -> None:
        self.config = config
        self.encoding = encoding
        self.verbose = verbose
        self.json_logs = json_logs

    @classmethod
    def from_config_file(
        cls,
        config_path: str | Path,
        *,
        encoding: str = "utf-8",
        verbose: bool = False,
        json_logs: bool = False,
    ) -> "SnapshotManager":
        config = SnapshotConfig.from_json_file(config_path)
        return cls(config, encoding=encoding, verbose=verbose, json_logs=json_logs)

    def read_from_workspace(self, workspace_root: str | Path, book_name: str) -> WorkspaceSnapshot:
        root = Path(workspace_root)
        book_path = root / book_name
        chapter_root = book_path / "BookChapters"

        self._verbose_print(f"Reading workspace snapshot from: {book_path}")

        snapshot = WorkspaceSnapshot(bookName=book_name)

        for filename in self.config.bookRootFiles:
            snapshot.rootFiles[filename] = self._read_text(book_path / filename)

        chapter_cfg = self.config.chapters
        for number in range(chapter_cfg.start, chapter_cfg.end + 1):
            chapter_folder = self._configured_chapter_folder(number)
            chapter_path = chapter_root / chapter_folder
            chapter_out_folder = self._configured_out_folder(number)
            out_path = self._resolve_existing_path(chapter_path, chapter_out_folder, number)

            chapter = ChapterSnapshot(
                chapterNumber=number,
                chapterFolder=chapter_folder,
                outFolder=chapter_out_folder,
            )

            for pattern in chapter_cfg.chapterFiles:
                file_name = pattern.replace("{n}", str(number))
                source_path = self._resolve_existing_path(chapter_path, file_name, number)
                chapter.files[file_name] = self._read_text(source_path)

            for pattern in chapter_cfg.chapterOutFiles:
                file_name = pattern.replace("{n}", str(number))
                if number == 1 and file_name == "Chapter1RunningSummary.txt" and chapter_cfg.chapter1RunningSummaryFile:
                    file_name = chapter_cfg.chapter1RunningSummaryFile
                source_path = self._resolve_existing_path(out_path, file_name, number)
                chapter.outFiles[file_name] = self._read_text(source_path)

            snapshot.chapters.append(chapter)

        self._verbose_print(
            f"Collected snapshot for {book_name} with {len(snapshot.rootFiles)} root files and {len(snapshot.chapters)} chapters"
        )
        return snapshot

    def initialize_workspace(
        self,
        workspace_root: str | Path,
        book_name: str,
        *,
        number_of_chapters: int | None = None,
    ) -> Path:
        root = Path(workspace_root)
        book_path = root / book_name
        chapter_root = book_path / "BookChapters"

        self._verbose_print(f"Initializing workspace for {book_name} at: {book_path}")

        book_path.mkdir(parents=True, exist_ok=True)
        chapter_root.mkdir(parents=True, exist_ok=True)

        for filename in self.config.bookRootFiles:
            self._ensure_file(book_path / filename)

        chapter_cfg = self.config.chapters
        chapter_start = chapter_cfg.start
        chapter_end = chapter_cfg.end
        if number_of_chapters is not None:
            if number_of_chapters < 1:
                raise ValueError("number_of_chapters must be >= 1")
            chapter_end = chapter_start + number_of_chapters - 1

        for number in range(chapter_start, chapter_end + 1):
            chapter_folder = self._configured_chapter_folder(number)
            chapter_path = chapter_root / chapter_folder
            chapter_path.mkdir(parents=True, exist_ok=True)

            for pattern in chapter_cfg.chapterFiles:
                file_name = pattern.replace("{n}", str(number))
                self._ensure_file(chapter_path / file_name)

            chapter_out_folder = self._configured_out_folder(number)
            out_path = chapter_path / chapter_out_folder
            out_path.mkdir(parents=True, exist_ok=True)

            for pattern in chapter_cfg.chapterOutFiles:
                file_name = pattern.replace("{n}", str(number))
                if number == 1 and file_name == "Chapter1RunningSummary.txt" and chapter_cfg.chapter1RunningSummaryFile:
                    file_name = chapter_cfg.chapter1RunningSummaryFile
                self._ensure_file(out_path / file_name)

        self._verbose_print(f"Workspace ready with chapters {chapter_start} to {chapter_end}")
        return book_path

    def restore_to_workspace(self, snapshot: WorkspaceSnapshot, workspace_root: str | Path, *, book_name: str | None = None) -> None:
        target_book_name = book_name or snapshot.bookName
        root = Path(workspace_root)
        book_path = root / target_book_name
        chapter_root = book_path / "BookChapters"

        self._verbose_print(f"Restoring snapshot {snapshot.bookName} into: {book_path}")

        for filename in self.config.bookRootFiles:
            content = snapshot.rootFiles.get(filename, "")
            self._write_text(book_path / filename, content)

        for chapter in snapshot.chapters:
            chapter_number = chapter.chapterNumber
            chapter_folder = self._configured_chapter_folder(chapter_number)
            chapter_path = chapter_root / chapter_folder

            for pattern in self.config.chapters.chapterFiles:
                filename = pattern.replace("{n}", str(chapter_number))
                content = self._lookup_snapshot_content(chapter.files, filename, chapter_number)
                self._write_text(chapter_path / filename, content)

            out_folder = self._configured_out_folder(chapter_number)
            out_path = chapter_path / out_folder
            for pattern in self.config.chapters.chapterOutFiles:
                filename = pattern.replace("{n}", str(chapter_number))
                content = self._lookup_snapshot_content(chapter.outFiles, filename, chapter_number)
                self._write_text(out_path / filename, content)

        self._verbose_print(f"Snapshot restore completed for: {target_book_name}")

    def write_snapshot_json(self, snapshot: WorkspaceSnapshot, snapshot_path: str | Path) -> None:
        self._verbose_print(f"Writing snapshot JSON to: {snapshot_path}")
        snapshot.to_json_file(snapshot_path)

    def load_snapshot_json(self, snapshot_path: str | Path) -> WorkspaceSnapshot:
        self._verbose_print(f"Loading snapshot JSON from: {snapshot_path}")
        return WorkspaceSnapshot.from_json_file(snapshot_path)

    def export_workspace_to_json(self, workspace_root: str | Path, book_name: str, snapshot_path: str | Path) -> WorkspaceSnapshot:
        self._verbose_print(f"Exporting workspace '{book_name}' to snapshot: {snapshot_path}")
        snapshot = self.read_from_workspace(workspace_root, book_name)
        self.write_snapshot_json(snapshot, snapshot_path)
        return snapshot

    def clone_workspace(
        self,
        workspace_root: str | Path,
        source_book_name: str,
        target_book_name: str,
    ) -> WorkspaceSnapshot:
        self._verbose_print(f"Cloning workspace '{source_book_name}' -> '{target_book_name}'")
        snapshot = self.read_from_workspace(workspace_root, source_book_name)
        snapshot.bookName = target_book_name
        self.restore_to_workspace(snapshot, workspace_root, book_name=target_book_name)
        return snapshot

    def _verbose_print(self, message: str) -> None:
        if self.verbose:
            if self.json_logs:
                payload = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "component": "snapshot",
                    "event": "trace",
                    "message": message,
                }
                print(json.dumps(payload, ensure_ascii=False))
                return
            print(f"[verbose][snapshot] {message}")

    def _read_text(self, path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding=self.encoding)

    def _write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=self.encoding)

    def _ensure_file(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)

    def _configured_chapter_folder(self, chapter_number: int) -> str:
        return self.config.chapters.chapterFolderPattern.replace("{n}", str(chapter_number))

    def _configured_out_folder(self, chapter_number: int) -> str:
        return self.config.chapters.chapterOutFolderPattern.replace("{n}", str(chapter_number))

    def _resolve_existing_path(self, parent: Path, name: str, chapter_number: int) -> Path:
        for candidate in self._name_candidates(name, chapter_number):
            candidate_path = parent / candidate
            if candidate_path.exists():
                return candidate_path
        return parent / name

    def _lookup_snapshot_content(self, content_by_name: dict[str, str], target_name: str, chapter_number: int) -> str:
        for candidate in self._name_candidates(target_name, chapter_number):
            if candidate in content_by_name:
                return content_by_name[candidate]
        return ""

    def _name_candidates(self, name: str, chapter_number: int) -> list[str]:
        candidates = [name]
        legacy_name = self._legacy_numbered_name(name, chapter_number)
        if legacy_name != name:
            candidates.append(legacy_name)
        return candidates

    def _legacy_numbered_name(self, name: str, chapter_number: int) -> str:
        return re.sub(r"^Chapter(?!\d)", f"Chapter{chapter_number}", name, count=1)
