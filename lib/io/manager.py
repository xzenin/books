from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from lib.models import ChapterSnapshot, SnapshotConfig, WorkspaceSnapshot

if TYPE_CHECKING:
    from ..writer.writables import ProjectSettings


class SnapshotManager(ABC):
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

    @property
    @abstractmethod
    def storage_backend(self) -> str:
        """Concrete backend identifier (e.g. filesystem, mongo)."""
        raise NotImplementedError

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

    def initialize_workspace_snapshot(self, *, book_name: str | None = None) -> WorkspaceSnapshot:
        resolved_book_name = str(book_name or self.book_name or "")
        existing = WorkspaceSnapshot.get_singleton()
        if existing is None:
            snapshot = WorkspaceSnapshot.init_singleton(
                book_name=resolved_book_name,
                implimentor=self.storage_backend,
                manager=self,
            )
            return snapshot

        existing.inject_manager(self)
        if resolved_book_name:
            existing.bookName = resolved_book_name
        return existing

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

    def get_book_file_path(
        self,
        filename: str,
        workspace_root: str | Path | None = None,
        book_name: str | None = None,
    ) -> Path:
        return self.get_book_path(workspace_root, book_name) / filename

    def get_outline_path(self, workspace_root: str | Path | None = None, book_name: str | None = None) -> Path:
        return self.get_book_file_path("BookOutline.json", workspace_root, book_name)

    def get_book_prompt_path(self, workspace_root: str | Path | None = None, book_name: str | None = None) -> Path:
        return self.get_book_file_path("BookPrompt.txt", workspace_root, book_name)

    def get_published_path(
        self,
        output_path: str | Path | None = None,
        workspace_root: str | Path | None = None,
        book_name: str | None = None,
    ) -> Path:
        if output_path:
            return Path(output_path)
        return self.get_book_file_path("BookPublished.txt", workspace_root, book_name)

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

    def get_chapter_file_paths(
        self,
        chapter_number: int,
        workspace_root: str | Path | None = None,
        book_name: str | None = None,
    ) -> tuple[Path, Path]:
        chapter_path = self.get_chapter_path(chapter_number, workspace_root, book_name)
        chapter_files = self.config.chapters.chapterFiles
        parameter_name = chapter_files[0].replace("{n}", str(chapter_number))
        prompt_name = chapter_files[1].replace("{n}", str(chapter_number)) if len(chapter_files) > 1 else "ChapterPrompt.txt"
        return chapter_path / prompt_name, chapter_path / parameter_name

    def get_chapter_layout_prompt_path(
        self,
        chapter_number: int,
        workspace_root: str | Path | None = None,
        book_name: str | None = None,
    ) -> Path:
        return self.get_chapter_path(chapter_number, workspace_root, book_name) / "ChapterLayoutPrompt.txt"

    def get_chapter_generated_path(
        self,
        chapter_number: int,
        workspace_root: str | Path | None = None,
        book_name: str | None = None,
    ) -> Path:
        chapter_out = self.get_chapter_out_path(chapter_number, workspace_root, book_name)
        out_files = self.config.chapters.chapterOutFiles
        generated_name = out_files[0].replace("{n}", str(chapter_number)) if out_files else "ChapterGenerated.txt"
        for candidate in out_files:
            lowered = candidate.lower()
            if "generated" in lowered:
                generated_name = candidate.replace("{n}", str(chapter_number))
                break
        return chapter_out / generated_name

    def get_chapter_summary_path(
        self,
        chapter_number: int,
        workspace_root: str | Path | None = None,
        book_name: str | None = None,
    ) -> Path:
        chapter_out = self.get_chapter_out_path(chapter_number, workspace_root, book_name)
        out_files = self.config.chapters.chapterOutFiles
        summary_name = "ChapterSummary.txt"
        for candidate in out_files:
            if "summary" in candidate.lower():
                summary_name = candidate.replace("{n}", str(chapter_number))
                break
        return chapter_out / summary_name

    def get_chapter_character_path(
        self,
        chapter_number: int,
        workspace_root: str | Path | None = None,
        book_name: str | None = None,
    ) -> Path:
        chapter_out = self.get_chapter_out_path(chapter_number, workspace_root, book_name)
        out_files = self.config.chapters.chapterOutFiles
        character_name = "ChapterCharacter.txt"
        for candidate in out_files:
            lowered = candidate.lower()
            if "character" in lowered:
                character_name = candidate.replace("{n}", str(chapter_number))
                break
        return chapter_out / character_name

    def get_runtime_segment_prompt_dir(
        self,
        chapter_number: int,
        workspace_root: str | Path | None = None,
        book_name: str | None = None,
    ) -> Path:
        return self.get_chapter_path(chapter_number, workspace_root, book_name) / "ChapterSegments"

    def get_runtime_segment_prompt_path(
        self,
        chapter_number: int,
        segment_number: int,
        workspace_root: str | Path | None = None,
        book_name: str | None = None,
    ) -> Path:
        return self.get_runtime_segment_prompt_dir(chapter_number, workspace_root, book_name) / f"Segment{segment_number}Prompt.txt"

    def get_segment_structured_paths(
        self,
        chapter_number: int,
        segment_number: int,
        workspace_root: str | Path | None = None,
        book_name: str | None = None,
    ) -> tuple[Path, Path | None, Path | None, Path | None]:
        segment_root = self.get_segment_path(chapter_number, segment_number, workspace_root, book_name)
        segments_cfg = self.config.chapters.segments
        if segments_cfg is None:
            return segment_root, None, None, None

        parameter_path: Path | None = None
        prompt_path: Path | None = None
        generated_path: Path | None = None

        if segments_cfg.segmentFiles:
            parameter_name = self._render_segment_pattern(segments_cfg.segmentFiles[0], chapter_number, segment_number)
            parameter_path = segment_root / parameter_name
        if len(segments_cfg.segmentFiles) > 1:
            prompt_name = self._render_segment_pattern(segments_cfg.segmentFiles[1], chapter_number, segment_number)
            prompt_path = segment_root / prompt_name

        if segments_cfg.segmentOutFiles:
            out_root = self.get_segment_out_path(chapter_number, segment_number, workspace_root, book_name)
            generated_name = self._render_segment_pattern(segments_cfg.segmentOutFiles[-1], chapter_number, segment_number)
            generated_path = out_root / generated_name

        return segment_root, parameter_path, prompt_path, generated_path

    def iter_configured_files(
        self,
        workspace_root: str | Path | None = None,
        book_name: str | None = None,
    ) -> list[Path]:
        paths: list[Path] = []
        chapter_cfg = self.config.chapters

        for file_name in self.config.bookRootFiles:
            paths.append(self.get_book_file_path(file_name, workspace_root, book_name))

        for number in range(chapter_cfg.start, chapter_cfg.end + 1):
            chapter_path = self.get_chapter_path(number, workspace_root, book_name)
            for pattern in chapter_cfg.chapterFiles:
                paths.append(chapter_path / pattern.replace("{n}", str(number)))

            chapter_out = self.get_chapter_out_path(number, workspace_root, book_name)
            for pattern in chapter_cfg.chapterOutFiles:
                paths.append(chapter_out / pattern.replace("{n}", str(number)))

            segments_cfg = chapter_cfg.segments
            if segments_cfg is None:
                continue

            for segment_number in range(segments_cfg.start, segments_cfg.end + 1):
                segment_root = self.get_segment_path(number, segment_number, workspace_root, book_name)
                for pattern in segments_cfg.segmentFiles:
                    paths.append(segment_root / self._render_segment_pattern(pattern, number, segment_number))

                segment_out = self.get_segment_out_path(number, segment_number, workspace_root, book_name)
                for pattern in segments_cfg.segmentOutFiles:
                    paths.append(segment_out / self._render_segment_pattern(pattern, number, segment_number))

        return paths

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

        snapshot = WorkspaceSnapshot(
            implimentor=self.storage_backend,
            bookName=str(name),
        )

        for filename in self.config.bookRootFiles:
            snapshot.rootFiles[filename] = self._read_text(book_path / filename)

        chapter_cfg = self.config.chapters
        for number in range(chapter_cfg.start, chapter_cfg.end + 1):
            chapter_path = self.get_chapter_path(number, root, name)
            chapter_out_path = self.get_chapter_out_path(number, root, name)

            # If a chapter was not initialized (e.g. chapter_count < template max), skip it.
            if not self.path_exists(chapter_path) and not self.path_exists(chapter_out_path):
                continue

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
        snapshot.inject_manager(self)
        WorkspaceSnapshot.set_singleton(snapshot)
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

        self.ensure_dir(book_path)
        self.ensure_dir(chapter_root)

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
            self.ensure_dir(chapter_path)

            for pattern in chapter_cfg.chapterFiles:
                file_name = pattern.replace("{n}", str(number))
                self._ensure_file(chapter_path / file_name)

            chapter_out_path = self.get_chapter_out_path(number, root, name)
            self.ensure_dir(chapter_out_path)

            for pattern in chapter_cfg.chapterOutFiles:
                file_name = pattern.replace("{n}", str(number))
                self._ensure_file(chapter_out_path / file_name)

            segments_cfg = chapter_cfg.segments
            if segments_cfg is not None:
                for segment_number in range(segments_cfg.start, segments_cfg.end + 1):
                    segment_path = self.get_segment_path(number, segment_number, root, name)
                    self.ensure_dir(segment_path)

                    for pattern in segments_cfg.segmentFiles:
                        file_name = self._render_segment_pattern(pattern, number, segment_number)
                        self._ensure_file(segment_path / file_name)

                    segment_out_path = self.get_segment_out_path(number, segment_number, root, name)
                    self.ensure_dir(segment_out_path)

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

    # Internal delegation helpers — call through abstract public IO methods
    def _read_text(self, path: Path) -> str:
        try:
            return self.read_text_file(path)
        except FileNotFoundError:
            return ""

    def _write_text(self, path: Path, content: str) -> None:
        self.write_text_file(path, content)

    def _ensure_file(self, path: Path) -> None:
        if not self.path_exists(path):
            self.write_text_file(path, "")

    # ---- Abstract IO contract: implemented by FileSnapshotManager / MongoSnapshotManager ----

    @abstractmethod
    def ensure_dir(self, path: str | Path) -> Path:
        """Create a directory (or logical container). Return the resolved Path."""
        raise NotImplementedError

    @abstractmethod
    def path_exists(self, path: str | Path) -> bool:
        """Return True if the path (file or directory) exists in the backend."""
        raise NotImplementedError

    @abstractmethod
    def read_text_file(self, path: str | Path) -> str:
        """Read text content from the backend. Return empty string if not found."""
        raise NotImplementedError

    @abstractmethod
    def write_text_file(self, path: str | Path, content: str) -> None:
        """Write text content to the backend."""
        raise NotImplementedError

    @abstractmethod
    def load_json_file(self, path: str | Path) -> Any:
        """Read and parse a JSON file from the backend."""
        raise NotImplementedError

    @abstractmethod
    def write_json_file(self, path: str | Path, content: Any) -> None:
        """Serialise and write a JSON file to the backend."""
        raise NotImplementedError

    @abstractmethod
    def write_dummy_file(self, path: str | Path, content: Any) -> None:
        """Write a dummy file (text or JSON depending on extension) to the backend."""
        raise NotImplementedError

    @abstractmethod
    def write_snapshot_json(self, snapshot: WorkspaceSnapshot, snapshot_path: str | Path) -> None:
        """Persist a WorkspaceSnapshot to the backend."""
        raise NotImplementedError

    @abstractmethod
    def load_snapshot_json(self, snapshot_path: str | Path) -> WorkspaceSnapshot:
        """Load a WorkspaceSnapshot from the backend."""
        raise NotImplementedError

    @abstractmethod
    def discover_chapter_numbers(self) -> list[int]:
        """Return sorted list of chapter numbers found in the backend workspace."""
        raise NotImplementedError

    @abstractmethod
    def list_book_names(self, workspace_root: str | Path) -> list[str]:
        """Return sorted list of book names found under workspace_root in the backend."""
        raise NotImplementedError

    @abstractmethod
    def remove_book(self, workspace_root: str | Path, book_name: str) -> None:
        """Delete all data for a single book from the backend."""
        raise NotImplementedError

    @abstractmethod
    def purge_workspace(self, workspace_root: str | Path) -> int:
        """Delete all books from workspace_root. Return count of removed books."""
        raise NotImplementedError

    @abstractmethod
    def export_workspace(self, workspace_root: str | Path, export_path: str | Path) -> None:
        """Export entire workspace to a single JSON file. Format is manager-agnostic."""
        raise NotImplementedError

    @abstractmethod
    def import_workspace(self, export_path: str | Path, workspace_root: str | Path) -> int:
        """Import workspace from JSON file. Return count of imported files/entries. Overwrites existing."""
        raise NotImplementedError

    def load_project_settings(self) -> "ProjectSettings":
        from ..writer.writables import ProjectSettings
        book_path = self.get_book_path()
        settings_path = self.get_book_file_path("Settings.json")
        payload = self.load_json_file(settings_path)
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid settings payload in: {settings_path}")
        return ProjectSettings(
            book_name=str(payload.get("book_name", book_path.name)),
            chapter_count=int(payload["chapter_count"]),
            root_folder=str(payload.get("root_folder", "")),
            date_created=str(payload.get("date_created", "")),
            location=str(payload.get("location", "")),
            user=str(payload.get("user", "")),
        )

    def load_genai_mapping(self) -> dict[str, str]:
        config_path = Path(__file__).resolve().parents[2] / ".pkbook" / "config.json"
        try:
            payload = self.load_json_file(config_path)
        except (OSError, ValueError, json.JSONDecodeError):
            return {}
        if not isinstance(payload, dict):
            return {}
        genai_cfg = payload.get("genai", {})
        if not isinstance(genai_cfg, dict):
            return {}
        mapping = genai_cfg.get("mapping", {})
        if not isinstance(mapping, dict):
            return {}

        normalized: dict[str, str] = {}
        for key, value in mapping.items():
            if isinstance(key, str) and isinstance(value, str):
                normalized[key.strip().lower()] = value.strip()
        return normalized

    def load_template_payload(self, template_name: str) -> Any:
        template_path = Path(__file__).resolve().parents[2] / "templates" / template_name
        return self.load_json_file(template_path)

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
            if self.path_exists(candidate_path):
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
