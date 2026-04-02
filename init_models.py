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
    chapter1RunningSummaryFile: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ChapterConfig":
        return cls(
            start=int(payload["start"]),
            end=int(payload["end"]),
            chapterFolderPattern=str(payload["chapterFolderPattern"]),
            chapterFiles=[str(item) for item in payload.get("chapterFiles", [])],
            chapterOutFolderPattern=str(payload["chapterOutFolderPattern"]),
            chapterOutFiles=[str(item) for item in payload.get("chapterOutFiles", [])],
            chapter1RunningSummaryFile=str(payload["chapter1RunningSummaryFile"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InitConfig:
    rootFiles: list[str]
    chapters: ChapterConfig

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "InitConfig":
        return cls(
            rootFiles=[str(item) for item in payload.get("rootFiles", [])],
            chapters=ChapterConfig.from_dict(payload["chapters"]),
        )

    @classmethod
    def from_json_file(cls, path: str | Path) -> "InitConfig":
        json_path = Path(path)
        with json_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return cls.from_dict(payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rootFiles": list(self.rootFiles),
            "chapters": self.chapters.to_dict(),
        }

    def to_json_file(self, path: str | Path) -> None:
        json_path = Path(path)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, ensure_ascii=False, indent=2)


@dataclass
class ChapterContent:
    chapterNumber: int
    chapterFolder: str
    files: dict[str, str] = field(default_factory=dict)
    outFolder: str = ""
    outFiles: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ChapterContent":
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
    chapters: list[ChapterContent] = field(default_factory=list)

    @classmethod
    def from_workspace(
        cls,
        workspace_root: str | Path,
        book_name: str,
        config: InitConfig,
        *,
        encoding: str = "utf-8",
    ) -> "WorkspaceSnapshot":
        root = Path(workspace_root)
        book_path = root / book_name
        chapter_root = book_path / "BookChapters"

        snapshot = cls(bookName=book_name)

        for filename in config.rootFiles:
            snapshot.rootFiles[filename] = _read_text(book_path / filename, encoding=encoding)

        chapter_cfg = config.chapters
        for n in range(chapter_cfg.start, chapter_cfg.end + 1):
            chapter_folder = chapter_cfg.chapterFolderPattern.replace("{n}", str(n))
            chapter_path = chapter_root / chapter_folder

            chapter_entry = ChapterContent(
                chapterNumber=n,
                chapterFolder=chapter_folder,
                outFolder=chapter_cfg.chapterOutFolderPattern.replace("{n}", str(n)),
            )

            for pattern in chapter_cfg.chapterFiles:
                file_name = pattern.replace("{n}", str(n))
                chapter_entry.files[file_name] = _read_text(chapter_path / file_name, encoding=encoding)

            out_folder_path = chapter_path / chapter_entry.outFolder
            for pattern in chapter_cfg.chapterOutFiles:
                out_name = pattern.replace("{n}", str(n))
                if n == 1 and out_name == "Chapter1RunningSummary.txt":
                    out_name = chapter_cfg.chapter1RunningSummaryFile
                chapter_entry.outFiles[out_name] = _read_text(out_folder_path / out_name, encoding=encoding)

            snapshot.chapters.append(chapter_entry)

        return snapshot

    def restore_to_workspace(
        self,
        workspace_root: str | Path,
        config: InitConfig,
        *,
        encoding: str = "utf-8",
    ) -> None:
        root = Path(workspace_root)
        book_path = root / self.bookName
        chapter_root = book_path / "BookChapters"

        for filename, content in self.rootFiles.items():
            _write_text(book_path / filename, content, encoding=encoding)

        chapter_cfg = config.chapters
        chapter_index = {chapter.chapterNumber: chapter for chapter in self.chapters}

        for n in range(chapter_cfg.start, chapter_cfg.end + 1):
            chapter = chapter_index.get(n)
            if chapter is None:
                continue

            chapter_path = chapter_root / chapter.chapterFolder
            for filename, content in chapter.files.items():
                _write_text(chapter_path / filename, content, encoding=encoding)

            out_path = chapter_path / chapter.outFolder
            for filename, content in chapter.outFiles.items():
                _write_text(out_path / filename, content, encoding=encoding)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bookName": self.bookName,
            "rootFiles": dict(self.rootFiles),
            "chapters": [chapter.to_dict() for chapter in self.chapters],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WorkspaceSnapshot":
        return cls(
            bookName=str(payload["bookName"]),
            rootFiles={str(k): str(v) for k, v in payload.get("rootFiles", {}).items()},
            chapters=[ChapterContent.from_dict(item) for item in payload.get("chapters", [])],
        )

    def to_json_file(self, path: str | Path) -> None:
        json_path = Path(path)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, ensure_ascii=False, indent=2)

    @classmethod
    def from_json_file(cls, path: str | Path) -> "WorkspaceSnapshot":
        json_path = Path(path)
        with json_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return cls.from_dict(payload)


def _read_text(path: Path, *, encoding: str) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding=encoding)


def _write_text(path: Path, content: str, *, encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding=encoding)
