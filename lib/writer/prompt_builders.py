from __future__ import annotations

import json
import string
from pathlib import Path
from typing import Any

from ..io.io_helpers import load_json_file, read_text
from .writables import ProjectSettings


def _templates_root() -> Path:
    return Path(__file__).resolve().parents[2] / "templates"


def load_template_payload(template_name: str, *, encoding: str) -> Any:
    template_path = _templates_root() / template_name
    return load_json_file(template_path, encoding=encoding)


def build_novel_prompt(*, settings: ProjectSettings, gist: str, template_payload: Any) -> str:
    template_json = json.dumps(template_payload, ensure_ascii=False, indent=2)
    template_path = _templates_root() / "book_prompt.txt"
    template_text = read_text(template_path, encoding="utf-8")

    required_fields = {
        "gist",
        "template_json",
        "chapter_count",
    }
    formatter = string.Formatter()
    available_fields = {
        field_name
        for _, field_name, _, _ in formatter.parse(template_text)
        if field_name
    }
    missing_fields = sorted(required_fields - available_fields)
    if missing_fields:
        raise ValueError(
            f"Template {template_path} is missing required placeholders: {', '.join(missing_fields)}"
        )

    try:
        return template_text.format(
            gist=gist,
            template_json=template_json,
            chapter_count=settings.chapter_count,
        )
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Invalid novel prompt template format in {template_path}: {exc}") from exc


def build_chapter_prompt(
    *,
    settings: ProjectSettings,
    gist: str,
    outline_payload: dict[str, Any],
    chapter_payload: dict[str, Any],
    template_payload: Any,
    encoding: str = "utf-8",
) -> str:
    chapter_json = json.dumps(chapter_payload, ensure_ascii=False, indent=2)
    template_json = json.dumps(template_payload, ensure_ascii=False, indent=2)
    outline_context = json.dumps(
        {
            "novel_name": outline_payload.get("novel_name", ""),
            "novel_long_title": outline_payload.get("novel_long_title", ""),
            "generic": outline_payload.get("generic", ""),
            "era": outline_payload.get("era", ""),
            "language": outline_payload.get("language", ""),
            "target_audience": outline_payload.get("target_audience", ""),
            "running_summary": outline_payload.get("running_summary", ""),
            "all_characters": outline_payload.get("all_characters", []),
        },
        ensure_ascii=False,
        indent=2,
    )
    template_path = _templates_root() / "chapter_prompt.txt"
    template_text = read_text(template_path, encoding=encoding)

    required_fields = {
        "gist",
        "outline_context",
        "chapter_json",
        "template_json",
    }
    formatter = string.Formatter()
    available_fields = {
        field_name
        for _, field_name, _, _ in formatter.parse(template_text)
        if field_name
    }
    missing_fields = sorted(required_fields - available_fields)
    if missing_fields:
        raise ValueError(
            f"Template {template_path} is missing required placeholders: {', '.join(missing_fields)}"
        )

    try:
        return template_text.format(
            gist=gist,
            outline_context=outline_context,
            chapter_json=chapter_json,
            template_json=template_json,
        )
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Invalid chapter prompt template format in {template_path}: {exc}") from exc


def build_segment_prompt(
    *,
    settings: ProjectSettings,
    gist: str,
    outline_payload: dict[str, Any],
    chapter_payload: dict[str, Any],
    segment_payload: dict[str, Any],
    template_payload: Any,
    segment_index: int,
    carry_over: str,
    encoding: str = "utf-8",
) -> str:
    chapter_json = json.dumps(chapter_payload, ensure_ascii=False, indent=2)
    segment_json = json.dumps(segment_payload, ensure_ascii=False, indent=2)
    template_json = json.dumps(template_payload, ensure_ascii=False, indent=2)
    outline_context = json.dumps(
        {
            "novel_name": outline_payload.get("novel_name", ""),
            "novel_long_title": outline_payload.get("novel_long_title", ""),
            "generic": outline_payload.get("generic", ""),
            "era": outline_payload.get("era", ""),
            "language": outline_payload.get("language", ""),
            "target_audience": outline_payload.get("target_audience", ""),
            "running_summary": outline_payload.get("running_summary", ""),
            "all_characters": outline_payload.get("all_characters", []),
        },
        ensure_ascii=False,
        indent=2,
    )
    template_path = _templates_root() / "segment_prompt.txt"
    template_text = read_text(template_path, encoding=encoding)

    required_fields = {
        "gist",
        "outline_context",
        "chapter_json",
        "segment_json",
        "template_json",
        "segment_index",
        "carry_over",
    }
    formatter = string.Formatter()
    available_fields = {
        field_name
        for _, field_name, _, _ in formatter.parse(template_text)
        if field_name
    }
    missing_fields = sorted(required_fields - available_fields)
    if missing_fields:
        raise ValueError(
            f"Template {template_path} is missing required placeholders: {', '.join(missing_fields)}"
        )

    try:
        return template_text.format(
            gist=gist,
            outline_context=outline_context,
            chapter_json=chapter_json,
            segment_json=segment_json,
            template_json=template_json,
            segment_index=segment_index,
            carry_over=carry_over,
        )
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Invalid segment prompt template format in {template_path}: {exc}") from exc


def build_author_prompt(
    *,
    settings: ProjectSettings,
    gist: str,
    outline_payload: dict[str, Any],
    chapter_payload: dict[str, Any],
    chapter_parameter_payload: dict[str, Any],
    chapter_number: int,
    previous_running_summary: str,
) -> str:
    authoring_contract = {
        "required_json_keys": [
            "chapter_title",
            "chapter_text",
            "chapter_summary",
            "next_running_summary",
            "next_characters",
        ],
        "next_characters_shape": [
            {
                "name": "Character Name",
                "role": "Role in next chapter",
                "notes": "1-2 lines motivation/conflict",
            }
        ],
    }
    context_payload = {
        "book_settings": settings.__dict__,
        "novel_gist": gist,
        "novel_outline_context": {
            "novel_name": outline_payload.get("novel_name", ""),
            "novel_long_title": outline_payload.get("novel_long_title", ""),
            "generic": outline_payload.get("generic", ""),
            "era": outline_payload.get("era", ""),
            "language": outline_payload.get("language", ""),
            "target_audience": outline_payload.get("target_audience", ""),
            "running_summary": outline_payload.get("running_summary", ""),
            "all_characters": outline_payload.get("all_characters", []),
        },
        "chapter_outline": chapter_payload,
        "chapter_parameter": chapter_parameter_payload,
        "previous_running_summary": previous_running_summary,
    }
    return (
        "You are a renowned author and popular novelist. You have published 30 novels in Bengali literature. "
        "You are an expert in language development, poetic prose, and high-level narrative syntax. "
        "Use your strongest reasoning and storytelling quality for this response.\n\n"
        "Task:\n"
        "- Write this chapter as rich literary prose.\n"
        "- Finalize a strong chapter title.\n"
        "- Produce a concise chapter summary that carries forward continuity from previous running summary.\n"
        "- Produce a next running summary for upcoming chapter alignment.\n"
        "- Propose at least 3 new human characters for the next chapter.\n"
        "- Keep historical/geographical references aligned with provided context and references.\n"
        "- If external retrieval context is unavailable, rely on given outline, chapter parameters, and references only.\n\n"
        f"Current chapter number: {chapter_number}\n\n"
        f"Context JSON:\n{json.dumps(context_payload, ensure_ascii=False, indent=2)}\n\n"
        f"Response contract (JSON only):\n{json.dumps(authoring_contract, ensure_ascii=False, indent=2)}\n\n"
        "Return valid JSON only. Do not wrap in markdown."
    )
