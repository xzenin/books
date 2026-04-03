from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from .models import ChapterSnapshot, SnapshotConfig, WorkspaceSnapshot


class SnapshotManager:
    def __init__(
        self,
        config: SnapshotConfig,
        *,
        workspace_root: str | Path | None = None,
        book_name: str | None = None,
        encoding: str = "utf-8",
        verbose: bool = False,
        json_logs: bool = False,
    ) -> None:
        self.config = config
        self.workspace_root = Path(workspace_root) if workspace_root is not None else None
        self.book_name = book_name
        self.encoding = encoding
        self.verbose = verbose
        self.json_logs = json_logs

    @classmethod
    def from_config_file(
        cls,
        config_path: str | Path,
        *,
        workspace_root: str | Path | None = None,
        book_name: str | None = None,
        encoding: str = "utf-8",
        verbose: bool = False,
        json_logs: bool = False,
    ) -> "SnapshotManager":
        config = SnapshotConfig.from_json_file(config_path)
        return cls(
            config,
            workspace_root=workspace_root,
            book_name=book_name,
            encoding=encoding,
            verbose=verbose,
            json_logs=json_logs,
        )

    # Path getter methods
    def get_book_path(self, workspace_root: str | Path | None = None, book_name: str | None = None) -> Path:
        """Get the book directory path."""
        root = Path(workspace_root) if workspace_root is not None else self.workspace_root
        name = book_name or self.book_name
        if root is None or name is None:
            raise ValueError("workspace_root and book_name must be provided or set during initialization")
        return root / name

    def get_chapter_root(self, workspace_root: str | Path | None = None, book_name: str | None = None) -> Path:
        """Get the BookChapters directory path."""
        book_path = self.get_book_path(workspace_root, book_name)
        return book_path / "BookChapters"

    def get_chapter_path(
        self,
        chapter_number: int,
        workspace_root: str | Path | None = None,
        book_name: str | None = None,
    ) -> Path:
        """Get a specific chapter directory path."""
        chapter_root = self.get_chapter_root(workspace_root, book_name)
        chapter_folder = self._configured_chapter_folder(chapter_number)
        return chapter_root / chapter_folder

    def get_chapter_out_path(
        self,
        chapter_number: int,
        workspace_root: str | Path | None = None,
        book_name: str | None = None,
    ) -> Path:
        """Get a chapter's out directory path."""
        chapter_path = self.get_chapter_path(chapter_number, workspace_root, book_name)
        out_folder = self._configured_out_folder(chapter_number)
        return chapter_path / out_folder

    def get_segment_path(
        self,
        chapter_number: int,
        segment_number: int,
        workspace_root: str | Path | None = None,
        book_name: str | None = None,
    ) -> Path:
        """Get a specific segment directory path."""
        chapter_path = self.get_chapter_path(chapter_number, workspace_root, book_name)
        segment_folder = self._configured_segment_folder(chapter_number, segment_number)
        return chapter_path / segment_folder

    def get_segment_out_path(
        self,
        chapter_number: int,
        segment_number: int,
        workspace_root: str | Path | None = None,
        book_name: str | None = None,
    ) -> Path:
        """Get a segment's out directory path."""
        segment_path = self.get_segment_path(chapter_number, segment_number, workspace_root, book_name)
        out_folder = self._configured_segment_out_folder(chapter_number, segment_number)
        return segment_path / out_folder

    def read_from_workspace(self, workspace_root: str | Path | None = None, book_name: str | None = None) -> WorkspaceSnapshot:
        root = workspace_root or self.workspace_root
        name = book_name or self.book_name
        if root is None or name is None:
            raise ValueError("workspace_root and book_name must be provided")

        book_path = self.get_book_path(root, name)
        chapter_root = self.get_chapter_root(root, name)

        self._verbose_print(f"Reading workspace snapshot from: {self._relative_path_text(book_path)}")

        snapshot = WorkspaceSnapshot(bookName=str(name))

        for filename in self.config.bookRootFiles:
            snapshot.rootFiles[filename] = self._read_text(book_path / filename)

        chapter_cfg = self.config.chapters
        for number in range(chapter_cfg.start, chapter_cfg.end + 1):
            chapter_path = self.get_chapter_path(number, root, name)
            chapter_out_path = self.get_chapter_out_path(number, root, name)

            chapter = ChapterSnapshot(
                chapterNumber=number,
                chapterFolder=self._configured_chapter_folder(number),
                outFolder=self._configured_out_folder(number),
            )

            for pattern in chapter_cfg.chapterFiles:
                file_name = pattern.replace("{n}", str(number))
                source_path = self._resolve_existing_path(chapter_path, file_name, number)
                chapter.files[file_name] = self._read_text(source_path)

            for pattern in chapter_cfg.chapterOutFiles:
                file_name = pattern.replace("{n}", str(number))
                source_path = self._resolve_existing_path(chapter_out_path, file_name, number)
                chapter.outFiles[file_name] = self._read_text(source_path)

            snapshot.chapters.append(chapter)

        self._verbose_print(
            f"Collected snapshot for {name} with {len(snapshot.rootFiles)} root files and {len(snapshot.chapters)} chapters"
        )
        return snapshot

    def initialize_workspace(
        self,
        workspace_root: str | Path | None = None,
        book_name: str | None = None,
        *,
        number_of_chapters: int | None = None,
    ) -> Path:
        root = workspace_root or self.workspace_root
        name = book_name or self.book_name
        if root is None or name is None:
            raise ValueError("workspace_root and book_name must be provided")

        book_path = self.get_book_path(root, name)
        chapter_root = self.get_chapter_root(root, name)

        self._verbose_print(
            f"Initializing workspace for {name} at: {self._relative_path_text(book_path)}"
        )

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
            chapter_path = self.get_chapter_path(number, root, name)
            chapter_path.mkdir(parents=True, exist_ok=True)

            for pattern in chapter_cfg.chapterFiles:
                file_name = pattern.replace("{n}", str(number))
                self._ensure_file(chapter_path / file_name)

            chapter_out_path = self.get_chapter_out_path(number, root, name)
            chapter_out_path.mkdir(parents=True, exist_ok=True)

            for pattern in chapter_cfg.chapterOutFiles:
                file_name = pattern.replace("{n}", str(number))
                self._ensure_file(chapter_out_path / file_name)

            segments_cfg = chapter_cfg.segments
            if segments_cfg is not None:
                for segment_number in range(segments_cfg.start, segments_cfg.end + 1):
                    segment_path = self.get_segment_path(number, segment_number, root, name)
                    segment_path.mkdir(parents=True, exist_ok=True)

                    for pattern in segments_cfg.segmentFiles:
                        file_name = self._render_segment_pattern(pattern, number, segment_number)
                        self._ensure_file(segment_path / file_name)

                    segment_out_path = self.get_segment_out_path(number, segment_number, root, name)
                    segment_out_path.mkdir(parents=True, exist_ok=True)

                    for pattern in segments_cfg.segmentOutFiles:
                        file_name = self._render_segment_pattern(pattern, number, segment_number)
                        self._ensure_file(segment_out_path / file_name)

        self._verbose_print(f"Workspace ready with chapters {chapter_start} to {chapter_end}")
        return book_path

    def restore_to_workspace(
        self,
        snapshot: WorkspaceSnapshot,
        workspace_root: str | Path | None = None,
        *,
        book_name: str | None = None,
    ) -> None:
        root = workspace_root or self.workspace_root
        name = book_name or self.book_name or snapshot.bookName
        if root is None or name is None:
            raise ValueError("workspace_root and book_name must be provided")

        book_path = self.get_book_path(root, name)
        chapter_root = self.get_chapter_root(root, name)

        self._verbose_print(
            f"Restoring snapshot {snapshot.bookName} into: {self._relative_path_text(book_path)}"
        )

        for filename in self.config.bookRootFiles:
            content = snapshot.rootFiles.get(filename, "")
            self._write_text(book_path / filename, content)

        for chapter in snapshot.chapters:
            chapter_number = chapter.chapterNumber
            chapter_path = self.get_chapter_path(chapter_number, root, name)

            for pattern in self.config.chapters.chapterFiles:
                filename = pattern.replace("{n}", str(chapter_number))
                content = self._lookup_snapshot_content(chapter.files, filename, chapter_number)
                self._write_text(chapter_path / filename, content)

            chapter_out_path = self.get_chapter_out_path(chapter_number, root, name)
            for pattern in self.config.chapters.chapterOutFiles:
                filename = pattern.replace("{n}", str(chapter_number))
                content = self._lookup_snapshot_content(chapter.outFiles, filename, chapter_number)
                self._write_text(chapter_out_path / filename, content)

        self._verbose_print(f"Snapshot restore completed for: {name}")

    def export_workspace_to_json(
        self,
        workspace_root: str | Path | None = None,
        book_name: str | None = None,
        snapshot_path: str | Path | None = None,
    ) -> WorkspaceSnapshot:
        root = workspace_root or self.workspace_root
        name = book_name or self.book_name
        if root is None or name is None:
            raise ValueError("workspace_root and book_name must be provided")

        self._verbose_print(
            f"Exporting workspace '{name}' to snapshot: {self._relative_path_text(snapshot_path)}"
        )
        snapshot = self.read_from_workspace(root, name)
        if snapshot_path is not None:
            self.write_snapshot_json(snapshot, snapshot_path)
        return snapshot

    def clone_workspace(
        self,
        workspace_root: str | Path | None = None,
        source_book_name: str | None = None,
        target_book_name: str | None = None,
    ) -> WorkspaceSnapshot:
        root = workspace_root or self.workspace_root
        src_name = source_book_name or self.book_name
        if root is None or src_name is None or target_book_name is None:
            raise ValueError("workspace_root, source_book_name, and target_book_name must be provided")

        self._verbose_print(f"Cloning workspace '{src_name}' -> '{target_book_name}'")
        snapshot = self.read_from_workspace(root, src_name)
        snapshot.bookName = target_book_name
        self.restore_to_workspace(snapshot, root, book_name=target_book_name)
        return snapshot

    def write_snapshot_json(self, snapshot: WorkspaceSnapshot, snapshot_path: str | Path) -> None:
        self._verbose_print(f"Writing snapshot JSON to: {self._relative_path_text(snapshot_path)}")
        snapshot.to_json_file(snapshot_path)

    def load_snapshot_json(self, snapshot_path: str | Path) -> WorkspaceSnapshot:
        self._verbose_print(f"Loading snapshot JSON from: {self._relative_path_text(snapshot_path)}")
        return WorkspaceSnapshot.from_json_file(snapshot_path)

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

    def _configured_segment_folder(self, chapter_number: int, segment_number: int) -> str:
        segments_cfg = self.config.chapters.segments
        if segments_cfg is None:
            raise ValueError("Segment config is not defined.")
        return self._render_segment_pattern(segments_cfg.segmentFolderPattern, chapter_number, segment_number)

    def _configured_segment_out_folder(self, chapter_number: int, segment_number: int) -> str:
        segments_cfg = self.config.chapters.segments
        if segments_cfg is None:
            raise ValueError("Segment config is not defined.")
        return self._render_segment_pattern(segments_cfg.segmentOutFolderPattern, chapter_number, segment_number)

    def _render_segment_pattern(self, pattern: str, chapter_number: int, segment_number: int) -> str:
        return pattern.replace("{n}", str(chapter_number)).replace("{s}", str(segment_number))

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

    def _relative_path_text(self, path: str | Path) -> str:
        raw_path = Path(path)
        cwd = Path.cwd()
        try:
            return str(raw_path.resolve().relative_to(cwd.resolve()))
        except ValueError:
            return os.path.relpath(str(raw_path), start=str(cwd))
