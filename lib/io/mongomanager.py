from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
import re

try:
    from pymongo import MongoClient  # type: ignore[import-not-found]
except ImportError:
    MongoClient = None

from lib.io.manager import SnapshotManager
from lib.models import WorkspaceSnapshot


class MongoSnapshotManager(SnapshotManager):
    """Concrete MongoDB-backed snapshot manager. All workspace IO goes through this class."""

    _in_memory_snapshots: dict[str, dict[str, Any]] = {}
    _in_memory_files: dict[str, dict[str, Any]] = {}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._client = None
        self._db = None
        self._pkbook_collection = None
        self._connect_mongo()

    @property
    def storage_backend(self) -> str:
        return "mongo"

    # ---- Connection ----

    def _connect_mongo(self) -> None:
        if MongoClient is None:
            self._verbose_print("pymongo not installed; MongoSnapshotManager is using in-memory fallback.")
            return

        runtime_config_path = Path(__file__).resolve().parents[2] / ".pkbook" / "config.json"
        if self.workspace_root is not None:
            workspace_config_path = Path(self.workspace_root).parent / "config.json"
            if workspace_config_path.exists():
                runtime_config_path = workspace_config_path

        uri = "mongodb://localhost:27017"
        database_name = "book"
        pkbook_collection_name = "pkbook"

        try:
            payload = json.loads(runtime_config_path.read_text(encoding="utf-8"))
            snapshot_cfg = payload.get("snapshot", {}).get("config", {}) if isinstance(payload, dict) else {}
            if isinstance(snapshot_cfg, dict):
                uri = str(snapshot_cfg.get("mongo_uri", uri)).strip() or uri
                database_name = str(snapshot_cfg.get("database", database_name)).strip() or database_name
                pkbook_collection_name = str(snapshot_cfg.get("pkbook_collection", pkbook_collection_name)).strip() or pkbook_collection_name
        except (OSError, json.JSONDecodeError):
            pass

        try:
            self._client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            # Test connection
            self._client.server_info()
            self._db = self._client[database_name]
            self._pkbook_collection = self._db[pkbook_collection_name]
            self._verbose_print(f"Connected to MongoDB at {uri}/{database_name}.{pkbook_collection_name}")
        except Exception as e:
            raise RuntimeError(
                f"Failed to connect to MongoDB at {uri}. "
                f"Ensure MongoDB is running. Error: {e}"
            ) from e

    # ---- Path helpers ----

    def _path_key(self, path: str | Path) -> str:
        return str(Path(path)).replace("\\", "/")

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _relative_path_text(self, path: str | Path) -> str:
        raw_path = Path(str(path))
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
        key = self._path_key(resolved)
        record = {"_id": key, "kind": "dir", "updated_at": self._now()}
        if self._pkbook_collection is not None:
            self._pkbook_collection.update_one({"_id": key}, {"$set": record}, upsert=True)
        else:
            self._in_memory_files[key] = record
        return resolved

    def path_exists(self, path: str | Path) -> bool:
        key = self._path_key(path)
        prefix = key.rstrip("/") + "/"
        if self._pkbook_collection is not None:
            if self._pkbook_collection.count_documents({"_id": key}, limit=1) > 0:
                return True
            regex = f"^{re.escape(prefix)}"
            if self._pkbook_collection.count_documents({"_id": {"$regex": regex}}, limit=1) > 0:
                return True
        else:
            if key in self._in_memory_files:
                return True
            if any(existing.startswith(prefix) for existing in self._in_memory_files):
                return True
        return False

    def read_text_file(self, path: str | Path) -> str:
        key = self._path_key(path)
        if self._pkbook_collection is not None:
            doc = self._pkbook_collection.find_one({"_id": key, "kind": "file"})
            if doc:
                return str(doc.get("content", ""))
        else:
            doc = self._in_memory_files.get(key)
            if doc and doc.get("kind") == "file":
                return str(doc.get("content", ""))
        # Fallback to filesystem ONLY for static template files, not workspace files
        fs_path = Path(path)
        if fs_path.parts and "templates" in fs_path.parts:
            if fs_path.exists() and fs_path.is_file():
                return fs_path.read_text(encoding=self.encoding)
        raise FileNotFoundError(f"File not found in MongoDB: {self._relative_path_text(path)}")

    def write_text_file(self, path: str | Path, content: str) -> None:
        target = Path(path)
        self.ensure_dir(target.parent)
        key = self._path_key(target)
        record = {"_id": key, "kind": "file", "content": content, "updated_at": self._now()}
        if self._pkbook_collection is not None:
            self._pkbook_collection.update_one({"_id": key}, {"$set": record}, upsert=True)
        else:
            self._in_memory_files[key] = record

    def load_json_file(self, path: str | Path) -> Any:
        text = self.read_text_file(path)
        if not text.strip():
            raise ValueError(f"JSON file is empty: {self._relative_path_text(path)}")
        return json.loads(text)

    def write_json_file(self, path: str | Path, content: Any) -> None:
        self.write_text_file(path, json.dumps(content, ensure_ascii=False, indent=2))

    def write_dummy_file(self, path: str | Path, content: Any) -> None:
        target = Path(path)
        if target.suffix.lower() == ".json":
            self.write_json_file(target, content)
        else:
            self.write_text_file(target, str(content))

    def write_snapshot_json(self, snapshot: WorkspaceSnapshot, snapshot_path: str | Path) -> None:
        key = str(snapshot_path)
        self._verbose_print(f"Writing snapshot to pkbook: {self._relative_path_text(key)}")
        payload = snapshot.to_dict()
        record = {"_id": key, "kind": "snapshot", "payload": payload, "updated_at": self._now()}
        if self._pkbook_collection is not None:
            self._pkbook_collection.update_one({"_id": key}, {"$set": record}, upsert=True)
        else:
            self._in_memory_snapshots[key] = payload

    def load_snapshot_json(self, snapshot_path: str | Path) -> WorkspaceSnapshot:
        key = str(snapshot_path)
        self._verbose_print(f"Loading snapshot from pkbook: {self._relative_path_text(key)}")
        payload = None
        if self._pkbook_collection is not None:
            doc = self._pkbook_collection.find_one({"_id": key, "kind": "snapshot"})
            if doc is not None:
                payload = doc.get("payload")
        else:
            payload = self._in_memory_snapshots.get(key)
        if payload is None:
            raise FileNotFoundError(f"Snapshot not found in pkbook: {self._relative_path_text(key)}")
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid snapshot payload in pkbook: {self._relative_path_text(key)}")
        return WorkspaceSnapshot.from_dict(payload)

    def discover_chapter_numbers(self) -> list[int]:
        chapter_root = self.get_chapter_root()
        if not self.path_exists(chapter_root):
            return []
        folder_pattern = self.config.chapters.chapterFolderPattern
        if "{n}" in folder_pattern:
            prefix, suffix = folder_pattern.split("{n}", 1)
        else:
            prefix, suffix = folder_pattern, ""
        chapter_root_key = self._path_key(chapter_root).rstrip("/") + "/"
        folder_names: set[str] = set()
        if self._pkbook_collection is not None:
            regex = f"^{re.escape(chapter_root_key)}"
            for doc in self._pkbook_collection.find({"_id": {"$regex": regex}}, {"_id": 1}):
                key = str(doc.get("_id", ""))
                if key.startswith(chapter_root_key):
                    remainder = key[len(chapter_root_key):]
                    if remainder:
                        folder_names.add(remainder.split("/", 1)[0])
        else:
            for key in self._in_memory_files:
                if key.startswith(chapter_root_key):
                    remainder = key[len(chapter_root_key):]
                    if remainder:
                        folder_names.add(remainder.split("/", 1)[0])
        chapter_numbers: list[int] = []
        for name in sorted(folder_names):
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
        workspace_key = self._path_key(workspace_root).rstrip("/") + "/"
        book_names: set[str] = set()
        if self._pkbook_collection is not None:
            regex = f"^{re.escape(workspace_key)}"
            for doc in self._pkbook_collection.find({"_id": {"$regex": regex}}, {"_id": 1}):
                key = str(doc.get("_id", ""))
                if key.startswith(workspace_key):
                    remainder = key[len(workspace_key):]
                    if remainder:
                        book_names.add(remainder.split("/", 1)[0])
        else:
            for key in self._in_memory_files:
                if key.startswith(workspace_key):
                    remainder = key[len(workspace_key):]
                    if remainder:
                        book_names.add(remainder.split("/", 1)[0])
        return sorted(book_names)

    def remove_book(self, workspace_root: str | Path, book_name: str) -> None:
        prefix = self._path_key(Path(workspace_root) / book_name).rstrip("/") + "/"
        exact = prefix.rstrip("/")
        if self._pkbook_collection is not None:
            regex = f"^{re.escape(prefix)}"
            self._pkbook_collection.delete_many({"_id": {"$regex": regex}})
            self._pkbook_collection.delete_one({"_id": exact})
        else:
            to_delete = [k for k in self._in_memory_files if k == exact or k.startswith(prefix)]
            for key in to_delete:
                del self._in_memory_files[key]

    def purge_workspace(self, workspace_root: str | Path) -> int:
        book_names = self.list_book_names(workspace_root)
        for book_name in book_names:
            self.remove_book(workspace_root, book_name)
        return len(book_names)

    def export_workspace(self, workspace_root: str | Path, export_path: str | Path) -> None:
        """Export entire workspace from MongoDB to a single JSON file."""
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

        workspace_key = self._path_key(workspace_root).rstrip("/") + "/"

        if self._pkbook_collection is not None:
            # Query all entries for this workspace
            regex = f"^{re.escape(workspace_key)}"
            for doc in self._pkbook_collection.find({"_id": {"$regex": regex}}):
                key = str(doc.get("_id", ""))
                if not key.startswith(workspace_key):
                    continue

                rel_key = key[len(workspace_key):].rstrip("/")
                kind = doc.get("kind", "")

                if kind == "dir":
                    export_data["dirs"].append(rel_key)
                elif kind == "file":
                    export_data["files"][rel_key] = str(doc.get("content", ""))
                elif kind == "snapshot":
                    export_data["snapshots"][rel_key] = doc.get("payload", {})
        else:
            # Use in-memory fallback
            for key in self._in_memory_files:
                if not key.startswith(workspace_key):
                    continue

                rel_key = key[len(workspace_key):].rstrip("/")
                doc = self._in_memory_files[key]
                kind = doc.get("kind", "")

                if kind == "dir":
                    export_data["dirs"].append(rel_key)
                elif kind == "file":
                    export_data["files"][rel_key] = str(doc.get("content", ""))

            for key in self._in_memory_snapshots:
                if not key.startswith(workspace_key):
                    continue

                rel_key = key[len(workspace_key):].rstrip("/")
                export_data["snapshots"][rel_key] = self._in_memory_snapshots[key]

        with export_file.open("w", encoding=self.encoding) as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

    def import_workspace(self, export_path: str | Path, workspace_root: str | Path) -> int:
        """Import workspace from JSON file to MongoDB."""
        export_file = Path(export_path)
        if not export_file.exists():
            raise FileNotFoundError(f"Export file not found: {export_file}")

        with export_file.open("r", encoding=self.encoding) as f:
            export_data = json.load(f)

        if not isinstance(export_data, dict):
            raise ValueError("Invalid export file format")

        workspace_key = self._path_key(workspace_root).rstrip("/") + "/"
        count = 0

        # Import directories
        for dir_rel in export_data.get("dirs", []):
            full_key = workspace_key.rstrip("/") + "/" + dir_rel
            self.ensure_dir(full_key)
            count += 1

        # Import files
        for file_rel, content in export_data.get("files", {}).items():
            full_key = workspace_key.rstrip("/") + "/" + file_rel
            self.write_text_file(full_key, content)
            count += 1

        # Import snapshots
        for snap_rel, payload in export_data.get("snapshots", {}).items():
            full_key = workspace_key.rstrip("/") + "/" + snap_rel
            record = {"_id": full_key, "kind": "snapshot", "payload": payload, "updated_at": self._now()}
            if self._pkbook_collection is not None:
                self._pkbook_collection.update_one({"_id": full_key}, {"$set": record}, upsert=True)
            else:
                self._in_memory_snapshots[full_key] = payload
            count += 1

        return count

    def _resolve_existing_path(self, parent: Path, name: str, chapter_number: int) -> Path:
        for candidate in self._name_candidates(name, chapter_number):
            candidate_path = parent / candidate
            if self.path_exists(candidate_path):
                return candidate_path
        return parent / name
