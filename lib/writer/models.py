from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ChapterConfig:
    start: int
    end: int
    chapterFolderPattern: str
    chapterFiles: list[str]
    chapterOutFolderPattern: str
    chapterOutFiles: list[str]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ChapterConfig":
        return cls(
            start=int(payload["start"]),
            end=int(payload["end"]),
            chapterFolderPattern=str(payload["chapterFolderPattern"]),
            chapterFiles=[str(item) for item in payload.get("chapterFiles", [])],
            chapterOutFolderPattern=str(payload["chapterOutFolderPattern"]),
            chapterOutFiles=[str(item) for item in payload.get("chapterOutFiles", [])],
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
        with json_path.open("r", encoding="utf-8") as handle:
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
    bookName: str
    rootFiles: dict[str, str] = field(default_factory=dict)
    chapters: list[ChapterSnapshot] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WorkspaceSnapshot":
        return cls(
            bookName=str(payload["bookName"]),
            rootFiles={str(k): str(v) for k, v in payload.get("rootFiles", {}).items()},
            chapters=[ChapterSnapshot.from_dict(item) for item in payload.get("chapters", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "bookName": self.bookName,
            "rootFiles": dict(self.rootFiles),
            "chapters": [chapter.to_dict() for chapter in self.chapters],
        }

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
