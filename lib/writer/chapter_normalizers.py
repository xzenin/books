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
            # Try segment_text first (from chapter_segments), then text (from chapter_texts)
            value = str(item.get("segment_text", item.get("text", ""))).strip()
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


def normalize_chapter_segments(raw_segments: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_segments, list):
        return []

    normalized_segments: list[dict[str, Any]] = []
    for index, item in enumerate(raw_segments, start=1):
        if isinstance(item, ChapterSegmentText):
            segment_title = item.section_title.strip() or f"Segment {index}"
            segment_text = item.text.strip()
            normalized_segments.append(
                {
                    "segment_title": segment_title,
                    "segment_text": segment_text,
                }
            )
            continue

        if isinstance(item, dict):
            payload = dict(item)
            segment_title = str(
                payload.get(
                    "segment_title",
                    payload.get("segment-title", payload.get("section-title", payload.get("section", f"Segment {index}"))),
                )
            ).strip() or f"Segment {index}"
            segment_text = str(payload.get("segment_text", payload.get("text", ""))).strip()

            payload.pop("segment-title", None)
            payload.pop("section-title", None)
            payload.pop("section", None)
            payload.pop("text", None)
            payload["segment_title"] = segment_title
            payload["segment_text"] = segment_text
            normalized_segments.append(payload)
            continue

        if isinstance(item, str):
            segment_text = item.strip()
            if segment_text:
                normalized_segments.append(
                    {
                        "segment_title": f"Segment {index}",
                        "segment_text": segment_text,
                    }
                )

    return normalized_segments


def normalize_chapter_payload(payload: dict[str, Any], chapter_number: int) -> dict[str, Any]:
    """Normalize chapter payload while preserving the new JSON structure with chapter_segments."""
    normalized = dict(payload)

    # Remove deprecated chapter text fields so they do not get re-persisted.
    normalized.pop("chapter_texts", None)
    normalized.pop("chapter_text", None)
    normalized.pop("chatper_text", None)
    
    # Preserve all top-level fields and just ensure required ones are set
    normalized["sl"] = chapter_sort_key(normalized, chapter_number)
    normalized["name"] = str(normalized.get("name", f"Chapter {chapter_number}")).strip() or f"Chapter {chapter_number}"
    normalized["chapter_title"] = str(normalized.get("chapter_title", "")).strip() or f"Chapter {chapter_number}"
    normalized["chapter_summary"] = str(normalized.get("chapter_summary", "")).strip()
    
    normalized["chapter_segments"] = normalize_chapter_segments(normalized.get("chapter_segments", []))
    
    # Preserve all additional fields
    normalized["included_characters"] = normalized.get("included_characters", [])
    normalized["historical_accuracy"] = normalized.get("historical_accuracy", "")
    normalized["human_in_the_loop"] = normalized.get("human_in_the_loop", "")
    normalized["literary_style"] = normalized.get("literary_style", "")
    normalized["symbolism_and_motifs"] = normalized.get("symbolism_and_motifs", "")
    normalized["novel_name"] = normalized.get("novel_name", "")
    normalized["novel_long_title"] = normalized.get("novel_long_title", "")
    
    # Handle references properly
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
    chapter_segments = normalize_chapter_segments(payload.get("chapter_segments", []))
    chapter_texts = payload.get("chapter_texts", [])
    fallback_array = chapter_segments if chapter_segments else chapter_texts
    chapter_text = str(payload.get("chapter_text", chapter_texts_to_text(fallback_array))).strip()
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
        "chapter_segments": chapter_segments,
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
