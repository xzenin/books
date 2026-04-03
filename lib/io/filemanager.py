from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from lib.io.manager import SnapshotManager
from lib.models import WorkspaceSnapshot


class FileSnapshotManager(SnapshotManager):
    """Concrete filesystem-backed snapshot manager. All workspace IO goes through this class."""

    @property
    def storage_backend(self) -> str:
        return "filesystem"

    # ---- Path display ----

    def _relative_path_text(self, path: str | Path) -> str:
        raw_path = Path(path)
        parts = [segment for segment in raw_path.parts if segment not in ("", ".")]
        pkbook_index = -1
        for index, segment in enumerate(parts):
            if segment.lower() == ".pkbook":
                pkbook_index = index
                break

        if pkbook_index >= 0:
            return "/".join(parts[pkbook_index:])

        if not raw_path.is_absolute():
            return str(raw_path).replace("\\", "/")

        cwd = Path.cwd().resolve()
        try:
            return str(raw_path.resolve().relative_to(cwd)).replace("\\", "/")
        except ValueError:
            return raw_path.name

    # ---- Abstract IO implementations ----

    def ensure_dir(self, path: str | Path) -> Path:
        resolved = Path(path)
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved

    def path_exists(self, path: str | Path) -> bool:
        return Path(path).exists()

    def read_text_file(self, path: str | Path) -> str:
        fs_path = Path(path)
        if not fs_path.exists():
            return ""
        return fs_path.read_text(encoding=self.encoding)

    def write_text_file(self, path: str | Path, content: str) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding=self.encoding)

    def load_json_file(self, path: str | Path) -> Any:
        text = self.read_text_file(path)
        if not text.strip():
            raise ValueError(f"JSON file is empty: {self._relative_path_text(path)}")
        return json.loads(text)

    def write_json_file(self, path: str | Path, content: Any) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding=self.encoding) as handle:
            json.dump(content, handle, ensure_ascii=False, indent=2)

    def write_dummy_file(self, path: str | Path, content: Any) -> None:
        target = Path(path)
        if target.suffix.lower() == ".json":
            self.write_json_file(target, content)
        else:
            self.write_text_file(target, str(content))

    def write_snapshot_json(self, snapshot: WorkspaceSnapshot, snapshot_path: str | Path) -> None:
        self._verbose_print(f"Writing snapshot JSON to: {self._relative_path_text(snapshot_path)}")
        self.write_json_file(snapshot_path, snapshot.to_dict())

    def load_snapshot_json(self, snapshot_path: str | Path) -> WorkspaceSnapshot:
        self._verbose_print(f"Loading snapshot JSON from: {self._relative_path_text(snapshot_path)}")
        payload = self.load_json_file(snapshot_path)
        return WorkspaceSnapshot.from_dict(payload)

    def discover_chapter_numbers(self) -> list[int]:
        chapter_root = self.get_chapter_root()
        if not chapter_root.exists():
            return []

        folder_pattern = self.config.chapters.chapterFolderPattern
        if "{n}" in folder_pattern:
            prefix, suffix = folder_pattern.split("{n}", 1)
        else:
            prefix, suffix = folder_pattern, ""

        chapter_numbers: list[int] = []
        for child in chapter_root.iterdir():
            if not child.is_dir():
                continue
            name = child.name
            if not name.startswith(prefix):
                continue
            if suffix and not name.endswith(suffix):
                continue
            middle = name[len(prefix):]
            if suffix:
                middle = middle[:-len(suffix)]
            try:
                chapter_numbers.append(int(middle))
            except ValueError:
                continue

        return sorted(chapter_numbers)

    def list_book_names(self, workspace_root: str | Path) -> list[str]:
        root = Path(workspace_root)
        if not root.exists():
            return []
        return sorted(child.name for child in root.iterdir() if child.is_dir())

    def remove_book(self, workspace_root: str | Path, book_name: str) -> None:
        import shutil
        book_path = Path(workspace_root) / book_name
        if book_path.exists():
            shutil.rmtree(book_path)

    def purge_workspace(self, workspace_root: str | Path) -> int:
        import shutil
        root = Path(workspace_root)
        if not root.exists():
            return 0
        count = 0
        for child in root.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
                count += 1
        return count

    def export_workspace(self, workspace_root: str | Path, export_path: str | Path) -> None:
        """Export entire workspace to a single JSON file."""
        root = Path(workspace_root)
        export_file = Path(export_path)
        export_file.parent.mkdir(parents=True, exist_ok=True)

        export_data = {
            "version": "1.0",
            "backend": "universal",
            "workspace_root": str(workspace_root),
            "files": {},
            "dirs": [],
            "snapshots": {}
        }

        if not root.exists():
            with export_file.open("w", encoding=self.encoding) as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            return

        # Walk filesystem and collect all entries
        for dirpath, dirnames, filenames in root.walk():
            dir_path = Path(dirpath)
            rel_dir = dir_path.relative_to(root)
            if rel_dir != Path("."):
                export_data["dirs"].append(str(rel_dir).replace("\\", "/"))

            for filename in filenames:
                file_path = dir_path / filename
                try:
                    rel_file = file_path.relative_to(root)
                    content = file_path.read_text(encoding=self.encoding)
                    export_data["files"][str(rel_file).replace("\\", "/")] = content
                except (OSError, UnicodeDecodeError):
                    pass

        with export_file.open("w", encoding=self.encoding) as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

    def import_workspace(self, export_path: str | Path, workspace_root: str | Path) -> int:
        """Import workspace from JSON file."""
        export_file = Path(export_path)
        if not export_file.exists():
            raise FileNotFoundError(f"Export file not found: {export_file}")

        with export_file.open("r", encoding=self.encoding) as f:
            export_data = json.load(f)

        if not isinstance(export_data, dict):
            raise ValueError("Invalid export file format")

        root = Path(workspace_root)
        count = 0

        # Create directories
        for dir_rel in export_data.get("dirs", []):
            dir_path = root / dir_rel
            dir_path.mkdir(parents=True, exist_ok=True)
            count += 1

        # Write files
        for file_rel, content in export_data.get("files", {}).items():
            file_path = root / file_rel
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding=self.encoding)
            count += 1

        return count

    def _resolve_existing_path(self, parent: Path, name: str, chapter_number: int) -> Path:
        for candidate in self._name_candidates(name, chapter_number):
            candidate_path = parent / candidate
            if candidate_path.exists():
                return candidate_path
        return parent / name
