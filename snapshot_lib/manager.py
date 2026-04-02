from __future__ import annotations

from pathlib import Path

from .models import ChapterSnapshot, SnapshotConfig, WorkspaceSnapshot


class SnapshotManager:
    def __init__(self, config: SnapshotConfig, *, encoding: str = "utf-8") -> None:
        self.config = config
        self.encoding = encoding

    @classmethod
    def from_config_file(cls, config_path: str | Path, *, encoding: str = "utf-8") -> "SnapshotManager":
        config = SnapshotConfig.from_json_file(config_path)
        return cls(config, encoding=encoding)

    def read_from_workspace(self, workspace_root: str | Path, book_name: str) -> WorkspaceSnapshot:
        root = Path(workspace_root)
        book_path = root / book_name
        chapter_root = book_path / "BookChapters"

        snapshot = WorkspaceSnapshot(bookName=book_name)

        for filename in self.config.bookRootFiles:
            snapshot.rootFiles[filename] = self._read_text(book_path / filename)

        chapter_cfg = self.config.chapters
        for number in range(chapter_cfg.start, chapter_cfg.end + 1):
            chapter_folder = chapter_cfg.chapterFolderPattern.replace("{n}", str(number))
            chapter_path = chapter_root / chapter_folder
            chapter_out_folder = chapter_cfg.chapterOutFolderPattern.replace("{n}", str(number))

            chapter = ChapterSnapshot(
                chapterNumber=number,
                chapterFolder=chapter_folder,
                outFolder=chapter_out_folder,
            )

            for pattern in chapter_cfg.chapterFiles:
                file_name = pattern.replace("{n}", str(number))
                chapter.files[file_name] = self._read_text(chapter_path / file_name)

            out_path = chapter_path / chapter_out_folder
            for pattern in chapter_cfg.chapterOutFiles:
                file_name = pattern.replace("{n}", str(number))
                if number == 1 and file_name == "Chapter1RunningSummary.txt" and chapter_cfg.chapter1RunningSummaryFile:
                    file_name = chapter_cfg.chapter1RunningSummaryFile
                chapter.outFiles[file_name] = self._read_text(out_path / file_name)

            snapshot.chapters.append(chapter)

        return snapshot

    def initialize_workspace(self, workspace_root: str | Path, book_name: str) -> Path:
        root = Path(workspace_root)
        book_path = root / book_name
        chapter_root = book_path / "BookChapters"

        book_path.mkdir(parents=True, exist_ok=True)
        chapter_root.mkdir(parents=True, exist_ok=True)

        for filename in self.config.bookRootFiles:
            self._ensure_file(book_path / filename)

        chapter_cfg = self.config.chapters
        for number in range(chapter_cfg.start, chapter_cfg.end + 1):
            chapter_folder = chapter_cfg.chapterFolderPattern.replace("{n}", str(number))
            chapter_path = chapter_root / chapter_folder
            chapter_path.mkdir(parents=True, exist_ok=True)

            for pattern in chapter_cfg.chapterFiles:
                file_name = pattern.replace("{n}", str(number))
                self._ensure_file(chapter_path / file_name)

            chapter_out_folder = chapter_cfg.chapterOutFolderPattern.replace("{n}", str(number))
            out_path = chapter_path / chapter_out_folder
            out_path.mkdir(parents=True, exist_ok=True)

            for pattern in chapter_cfg.chapterOutFiles:
                file_name = pattern.replace("{n}", str(number))
                if number == 1 and file_name == "Chapter1RunningSummary.txt" and chapter_cfg.chapter1RunningSummaryFile:
                    file_name = chapter_cfg.chapter1RunningSummaryFile
                self._ensure_file(out_path / file_name)

        return book_path

    def initialize_snapshot(self, book_name: str) -> WorkspaceSnapshot:
        snapshot = WorkspaceSnapshot(bookName=book_name)
        snapshot.rootFiles = {filename: "" for filename in self.config.bookRootFiles}

        chapter_cfg = self.config.chapters
        for number in range(chapter_cfg.start, chapter_cfg.end + 1):
            chapter_folder = chapter_cfg.chapterFolderPattern.replace("{n}", str(number))
            chapter_out_folder = chapter_cfg.chapterOutFolderPattern.replace("{n}", str(number))

            chapter = ChapterSnapshot(
                chapterNumber=number,
                chapterFolder=chapter_folder,
                files={},
                outFolder=chapter_out_folder,
                outFiles={},
            )

            for pattern in chapter_cfg.chapterFiles:
                file_name = pattern.replace("{n}", str(number))
                chapter.files[file_name] = ""

            for pattern in chapter_cfg.chapterOutFiles:
                file_name = pattern.replace("{n}", str(number))
                if number == 1 and file_name == "Chapter1RunningSummary.txt" and chapter_cfg.chapter1RunningSummaryFile:
                    file_name = chapter_cfg.chapter1RunningSummaryFile
                chapter.outFiles[file_name] = ""

            snapshot.chapters.append(chapter)

        return snapshot

    def restore_to_workspace(self, snapshot: WorkspaceSnapshot, workspace_root: str | Path, *, book_name: str | None = None) -> None:
        target_book_name = book_name or snapshot.bookName
        root = Path(workspace_root)
        book_path = root / target_book_name
        chapter_root = book_path / "BookChapters"

        for filename, content in snapshot.rootFiles.items():
            self._write_text(book_path / filename, content)

        for chapter in snapshot.chapters:
            chapter_path = chapter_root / chapter.chapterFolder
            for filename, content in chapter.files.items():
                self._write_text(chapter_path / filename, content)

            out_path = chapter_path / chapter.outFolder
            for filename, content in chapter.outFiles.items():
                self._write_text(out_path / filename, content)

    def write_snapshot_json(self, snapshot: WorkspaceSnapshot, snapshot_path: str | Path) -> None:
        snapshot.to_json_file(snapshot_path)

    def load_snapshot_json(self, snapshot_path: str | Path) -> WorkspaceSnapshot:
        return WorkspaceSnapshot.from_json_file(snapshot_path)

    def export_workspace_to_json(self, workspace_root: str | Path, book_name: str, snapshot_path: str | Path) -> WorkspaceSnapshot:
        snapshot = self.read_from_workspace(workspace_root, book_name)
        self.write_snapshot_json(snapshot, snapshot_path)
        return snapshot

    def clone_workspace(
        self,
        workspace_root: str | Path,
        source_book_name: str,
        target_book_name: str,
    ) -> WorkspaceSnapshot:
        snapshot = self.read_from_workspace(workspace_root, source_book_name)
        snapshot.bookName = target_book_name
        self.restore_to_workspace(snapshot, workspace_root, book_name=target_book_name)
        return snapshot

    def refresh_snapshot_json_from_workspace(
        self,
        workspace_root: str | Path,
        snapshot_path: str | Path,
        *,
        book_name: str | None = None,
    ) -> WorkspaceSnapshot:
        if book_name is None:
            existing = self.load_snapshot_json(snapshot_path)
            book_name = existing.bookName

        snapshot = self.read_from_workspace(workspace_root, book_name)
        self.write_snapshot_json(snapshot, snapshot_path)
        return snapshot

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
