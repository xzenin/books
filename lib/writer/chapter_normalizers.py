from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from lib.models import SnapshotConfig
from .writables import ChapterSegmentText


def chapter_sort_key(chapter_payload: dict[str, Any], fallback_index: int) -> int:
    raw_value = chapter_payload.get("sl", fallback_index)
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return fallback_index


def chapter_texts_to_text(raw_sections: Any) -> str:
    if not isinstance(raw_sections, list):
        return ""

    parts: list[str] = []
    for item in raw_sections:
        if isinstance(item, ChapterSegmentText):
            value = item.text.strip()
            if value:
                parts.append(value)
        elif isinstance(item, dict):
            value = str(item.get("text", "")).strip()
            if value:
                parts.append(value)
        elif isinstance(item, str):
            value = item.strip()
            if value:
                parts.append(value)
    return "\n\n".join(parts).strip()


def chapter_text_to_sections(chapter_text: str) -> list[dict[str, str]]:
    text = chapter_text.strip()
    if not text:
        return []

    blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    if not blocks:
        return [{"section": "body", "text": text}]

    return [
        {"section-title": f"part-{index}", "section": f"part-{index}", "text": block}
        for index, block in enumerate(blocks, start=1)
    ]


def normalize_chapter_payload(payload: dict[str, Any], chapter_number: int) -> dict[str, Any]:
    normalized = dict(payload)
    chapter_title = str(normalized.get("chapter_title", "")).strip() or f"Chapter {chapter_number}"
    chapter_summary = str(normalized.get("chapter_summary", "")).strip()
    chapter_text_from_array = chapter_texts_to_text(normalized.get("chapter_texts", []))
    chapter_text = str(
        normalized.get("chapter_text", normalized.get("chatper_text", chapter_text_from_array))
    ).strip()
    if not chapter_text:
        chapter_text = chapter_text_from_array

    normalized["sl"] = chapter_sort_key(normalized, chapter_number)
    normalized["name"] = str(normalized.get("name", f"Chapter {chapter_number}")).strip() or f"Chapter {chapter_number}"
    normalized["chapter_title"] = chapter_title
    normalized["chapter_summary"] = chapter_summary
    normalized["chapter_text"] = chapter_text
    raw_chapter_texts = normalized.get("chapter_texts")
    if isinstance(raw_chapter_texts, list):
        normalized_sections: list[dict[str, str]] = []
        for index, item in enumerate(raw_chapter_texts, start=1):
            if isinstance(item, dict):
                text_value = str(item.get("text", "")).strip()
                if not text_value:
                    continue
                section_name = str(item.get("section-title", item.get("section", f"part-{index}"))).strip()
                if not section_name:
                    section_name = f"part-{index}"
                normalized_sections.append(
                    {"section-title": section_name, "section": section_name, "text": text_value}
                )
            elif isinstance(item, str):
                text_value = item.strip()
                if text_value:
                    section_name = f"part-{index}"
                    normalized_sections.append(
                        {"section-title": section_name, "section": section_name, "text": text_value}
                    )
        normalized["chapter_texts"] = normalized_sections if normalized_sections else chapter_text_to_sections(chapter_text)
    else:
        normalized["chapter_texts"] = chapter_text_to_sections(chapter_text)
    normalized["included_characters"] = normalized.get("included_characters", [])
    references = normalized.get("references", normalized.get("further_references", []))
    if not isinstance(references, list):
        references = []
    normalized["references"] = references
    normalized["further_references"] = references
    return normalized


def discover_chapter_numbers_from_workspace(book_path: Path, config: SnapshotConfig) -> list[int]:
    chapter_root = book_path / "BookChapters"
    if not chapter_root.exists():
        return []

    folder_pattern = config.chapters.chapterFolderPattern
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


def normalize_author_payload(payload: dict[str, Any]) -> dict[str, Any]:
    title = str(payload.get("chapter_title", "")).strip() or "Untitled Chapter"
    chapter_text = str(payload.get("chapter_text", chapter_texts_to_text(payload.get("chapter_texts", [])))).strip()
    summary = str(payload.get("chapter_summary", "")).strip()
    next_running_summary = str(payload.get("next_running_summary", "")).strip() or summary

    raw_characters = payload.get("next_characters", [])
    normalized_characters: list[dict[str, str]] = []
    if isinstance(raw_characters, list):
        for item in raw_characters:
            if isinstance(item, dict):
                normalized_characters.append(
                    {
                        "name": str(item.get("name", "")).strip(),
                        "role": str(item.get("role", "")).strip(),
                        "notes": str(item.get("notes", "")).strip(),
                    }
                )
            elif isinstance(item, str):
                normalized_characters.append({"name": item.strip(), "role": "", "notes": ""})

    if len(normalized_characters) < 3:
        filler_count = 3 - len(normalized_characters)
        for idx in range(1, filler_count + 1):
            normalized_characters.append(
                {
                    "name": f"Character {idx}",
                    "role": "Supporting role",
                    "notes": "To be refined in next chapter.",
                }
            )

    return {
        "chapter_title": title,
        "chapter_text": chapter_text,
        "chapter_texts": chapter_text_to_sections(chapter_text),
        "chapter_summary": summary,
        "next_running_summary": next_running_summary,
        "next_characters": normalized_characters,
    }


def render_character_text(characters: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for index, item in enumerate(characters, start=1):
        name = item.get("name", "").strip() or f"Character {index}"
        role = item.get("role", "").strip()
        notes = item.get("notes", "").strip()
        lines.append(f"{index}. {name}")
        if role:
            lines.append(f"   role: {role}")
        if notes:
            lines.append(f"   notes: {notes}")
    return "\n".join(lines).strip() + "\n"


def extend_outline_characters(outline_payload: dict[str, Any], new_characters: list[dict[str, str]]) -> None:
    existing = outline_payload.get("all_characters")
    if not isinstance(existing, list):
        existing = []

    existing_names = {
        str(item.get("friendly_name", "")).strip().lower()
        for item in existing
        if isinstance(item, dict)
    }
    next_id = max(
        [int(item.get("character_id", 0)) for item in existing if isinstance(item, dict)] or [0]
    )

    for item in new_characters:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        key = name.lower()
        if key in existing_names:
            continue
        next_id += 1
        existing.append(
            {
                "character_id": next_id,
                "friendly_name": name,
                "role": str(item.get("role", "")).strip() or "Supporting character",
                "notes": str(item.get("notes", "")).strip(),
            }
        )
        existing_names.add(key)

    outline_payload["all_characters"] = existing
