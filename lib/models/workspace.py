from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ..io.manager import SnapshotManager


@dataclass
class SegmentConfig:
    start: int
    end: int
    segmentFolderPattern: str
    segmentFiles: list[str]
    segmentOutFolderPattern: str
    segmentOutFiles: list[str]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SegmentConfig":
        return cls(
            start=int(payload["start"]),
            end=int(payload["end"]),
            segmentFolderPattern=str(payload["segmentFolderPattern"]),
            segmentFiles=[str(item) for item in payload.get("segmentFiles", [])],
            segmentOutFolderPattern=str(payload["segmentOutFolderPattern"]),
            segmentOutFiles=[str(item) for item in payload.get("segmentOutFiles", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChapterConfig:
    start: int
    end: int
    chapterFolderPattern: str
    chapterFiles: list[str]
    chapterOutFolderPattern: str
    chapterOutFiles: list[str]
    segments: SegmentConfig | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ChapterConfig":
        segments_payload = payload.get("segments")
        return cls(
            start=int(payload["start"]),
            end=int(payload["end"]),
            chapterFolderPattern=str(payload["chapterFolderPattern"]),
            chapterFiles=[str(item) for item in payload.get("chapterFiles", [])],
            chapterOutFolderPattern=str(payload["chapterOutFolderPattern"]),
            chapterOutFiles=[str(item) for item in payload.get("chapterOutFiles", [])],
            segments=SegmentConfig.from_dict(segments_payload) if isinstance(segments_payload, dict) else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SnapshotConfig:
    bookRootFiles: list[str]
    chapters: ChapterConfig

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SnapshotConfig":
        root_files = payload.get("bookRootFiles")
        if root_files is None:
            root_files = payload.get("rootFiles", [])

        return cls(
            bookRootFiles=[str(item) for item in root_files],
            chapters=ChapterConfig.from_dict(payload["chapters"]),
        )

    @classmethod
    def from_json_file(cls, path: str | Path) -> "SnapshotConfig":
        json_path = Path(path)
        with json_path.open("r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
        return cls.from_dict(payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bookRootFiles": list(self.bookRootFiles),
            "chapters": self.chapters.to_dict(),
        }

    def to_json_file(self, path: str | Path) -> None:
        json_path = Path(path)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, ensure_ascii=False, indent=2)


@dataclass
class ChapterSnapshot:
    chapterNumber: int
    chapterFolder: str
    files: dict[str, str] = field(default_factory=dict)
    outFolder: str = ""
    outFiles: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ChapterSnapshot":
        return cls(
            chapterNumber=int(payload["chapterNumber"]),
            chapterFolder=str(payload["chapterFolder"]),
            files={str(k): str(v) for k, v in payload.get("files", {}).items()},
            outFolder=str(payload.get("outFolder", "")),
            outFiles={str(k): str(v) for k, v in payload.get("outFiles", {}).items()},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapterNumber": self.chapterNumber,
            "chapterFolder": self.chapterFolder,
            "files": dict(self.files),
            "outFolder": self.outFolder,
            "outFiles": dict(self.outFiles),
        }


@dataclass
class WorkspaceSnapshot:
    _singleton: ClassVar["WorkspaceSnapshot | None"] = None

    implimentor: str = "filesystem"
    bookName: str = ""
    rootFiles: dict[str, str] = field(default_factory=dict)
    chapters: list[ChapterSnapshot] = field(default_factory=list)
    manager: "SnapshotManager | None" = field(default=None, repr=False, compare=False)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WorkspaceSnapshot":
        return cls(
            implimentor=str(payload.get("implimentor", "filesystem")),
            bookName=str(payload["bookName"]),
            rootFiles={str(k): str(v) for k, v in payload.get("rootFiles", {}).items()},
            chapters=[ChapterSnapshot.from_dict(item) for item in payload.get("chapters", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "implimentor": self.implimentor,        
            "bookName": self.bookName,
            "rootFiles": dict(self.rootFiles),
            "chapters": [chapter.to_dict() for chapter in self.chapters],
        }

    def inject_manager(self, manager: "SnapshotManager") -> None:
        self.manager = manager
        self.implimentor = str(manager.storage_backend)

    @classmethod
    def set_singleton(cls, snapshot: "WorkspaceSnapshot") -> "WorkspaceSnapshot":
        cls._singleton = snapshot
        return snapshot

    @classmethod
    def get_singleton(cls) -> "WorkspaceSnapshot | None":
        return cls._singleton

    @classmethod
    def init_singleton(
        cls,
        *,
        book_name: str,
        implimentor: str = "filesystem",
        manager: "SnapshotManager | None" = None,
    ) -> "WorkspaceSnapshot":
        if cls._singleton is None:
            cls._singleton = cls(
                implimentor=str(implimentor),
                bookName=str(book_name),
            )
        if manager is not None:
            cls._singleton.inject_manager(manager)
        elif implimentor:
            cls._singleton.implimentor = str(implimentor)
        if book_name:
            cls._singleton.bookName = str(book_name)
        return cls._singleton

    @classmethod
    def reset_singleton(cls) -> None:
        cls._singleton = None

    @classmethod
    def from_json_file(cls, path: str | Path) -> "WorkspaceSnapshot":
        json_path = Path(path)
        with json_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)     
        return cls.from_dict(payload)

    def to_json_file(self, path: str | Path) -> None:
        json_path = Path(path)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, ensure_ascii=False, indent=2)

    def get_chapter(self, chapter_number: int) -> ChapterSnapshot | None:
        for chapter in self.chapters:
            if chapter.chapterNumber == chapter_number:
                return chapter
        return None

    def ensure_chapter(self, chapter_number: int, chapter_folder: str | None = None) -> ChapterSnapshot:
        chapter = self.get_chapter(chapter_number)
        if chapter is not None:
            if chapter_folder:
                chapter.chapterFolder = chapter_folder
            return chapter

        inferred_folder = chapter_folder or f"Chapter{chapter_number}"
        chapter = ChapterSnapshot(chapterNumber=chapter_number, chapterFolder=inferred_folder)
        self.chapters.append(chapter)
        self.chapters.sort(key=lambda item: item.chapterNumber)
        return chapter

    def set_root_file(self, filename: str, content: str) -> None:
        self.rootFiles[str(filename)] = str(content)

    def set_chapter_file(self, chapter_number: int, filename: str, content: str) -> None:
        chapter = self.ensure_chapter(chapter_number)
        chapter.files[str(filename)] = str(content)

    def set_chapter_out_file(self, chapter_number: int, filename: str, content: str) -> None:
        chapter = self.ensure_chapter(chapter_number)
        chapter.outFiles[str(filename)] = str(content)


@dataclass
class RuntimeWorkspaceState:
    snapshot: WorkspaceSnapshot
    dirtyPaths: set[str] = field(default_factory=set)
    version: int = 0

    def mark_dirty(self, path: str | Path) -> None:
        self.dirtyPaths.add(str(path))

    def bump_version(self) -> None:
        self.version += 1
