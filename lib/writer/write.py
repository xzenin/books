from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .manager import SnapshotManager
from .models import SnapshotConfig


TEXT_DUMMY_CONTENT = "hello"
JSON_DUMMY_CONTENT = {"root": "hello"}


@dataclass
class ProjectSettings:
    book_name: str
    chapter_count: int
    root_folder: str = ""
    date_created: str = ""
    location: str = ""
    user: str = ""


def _write_json(path: Path, content: Any, *, encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding) as handle:
        json.dump(content, handle, ensure_ascii=False, indent=2)


def _write_text(path: Path, content: str, *, encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding=encoding)


def _verbose_print(verbose: bool, json_logs: bool, message: str, event: str = "trace") -> None:
    if not verbose:
        return

    if json_logs:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": "write",
            "event": event,
            "message": message,
        }
        print(json.dumps(payload, ensure_ascii=False))
        return

    print(f"[verbose][write] {message}")


def _relative_path_text(path: str | Path) -> str:
    raw_path = Path(path)
    cwd = Path.cwd()
    try:
        return str(raw_path.resolve().relative_to(cwd.resolve()))
    except ValueError:
        return os.path.relpath(str(raw_path), start=str(cwd))


def _read_text(path: Path, *, encoding: str) -> str:
    return path.read_text(encoding=encoding)


def _normalize_json_content(raw: str) -> Any:
    stripped = raw.strip()
    if not stripped:
        return JSON_DUMMY_CONTENT

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return {"root": stripped}

    if isinstance(parsed, (dict, list)):
        return parsed
    return {"root": str(parsed)}


def _load_json_file(path: Path, *, encoding: str) -> Any:
    return json.loads(_read_text(path, encoding=encoding))


def _extract_json_payload(raw: str) -> Any:
    stripped = raw.strip()
    if not stripped:
        raise ValueError("Model response is empty.")

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    fenced_match = re.search(r"```(?:json)?\s*(.*?)```", stripped, re.DOTALL | re.IGNORECASE)
    if fenced_match:
        fenced_payload = fenced_match.group(1).strip()
        try:
            return json.loads(fenced_payload)
        except json.JSONDecodeError:
            pass

    decoder = json.JSONDecoder()
    for index, character in enumerate(stripped):
        if character not in "[{":
            continue
        try:
            payload, _ = decoder.raw_decode(stripped[index:])
        except json.JSONDecodeError:
            continue
        return payload

    raise ValueError("Unable to parse JSON from model response.")


def _load_project_settings(book_path: Path, *, encoding: str) -> ProjectSettings:
    settings_path = book_path / "Settings.json"
    payload = _load_json_file(settings_path, encoding=encoding)
    return ProjectSettings(
        book_name=str(payload.get("book_name", book_path.name)),
        chapter_count=int(payload["chapter_count"]),
        root_folder=str(payload.get("root_folder", "")),
        date_created=str(payload.get("date_created", "")),
        location=str(payload.get("location", "")),
        user=str(payload.get("user", "")),
    )


def _prompt_for_gist(book_name: str) -> str:
    gist = input(f"Novel gist for {book_name}: ").strip()
    if not gist:
        raise ValueError("Novel gist is required.")
    return gist


def _load_template_payload(template_name: str, *, encoding: str) -> Any:
    template_path = Path(__file__).resolve().parents[2] / "templates" / template_name
    return _load_json_file(template_path, encoding=encoding)


def _build_novel_prompt(*, settings: ProjectSettings, gist: str, template_payload: Any) -> str:
    settings_json = json.dumps(settings.__dict__, ensure_ascii=False, indent=2)
    template_json = json.dumps(template_payload, ensure_ascii=False, indent=2)
    return (
        "You are a renowned author and novelist. You have published 30 novels in Bengali Literature. "
        "Create a JSON for a novel layout. Return valid JSON only and do not wrap it in markdown.\n\n"
        f"Book settings:\n{settings_json}\n\n"
        f"Novel gist:\n{gist}\n\n"
        f"Use this JSON shape as the target output:\n{template_json}\n\n"
        "Requirements:\n"
        f"- Please generate exactly {settings.chapter_count} chapters.\n"
        "- Fill the title, summary, chapter list, characters, and running summary fields.\n"
        "- Keep the output as a single JSON object."
    )


def _build_chapter_prompt(
    *,
    settings: ProjectSettings,
    gist: str,
    outline_payload: dict[str, Any],
    chapter_payload: dict[str, Any],
    template_payload: Any,
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
    return (
        "You are a renowned author and novelist. You have published 30 novels in Bengali Literature. "
        "Create a JSON for the next chapter. Return valid JSON only and do not wrap it in markdown.\n\n"
        f"Book settings:\n{json.dumps(settings.__dict__, ensure_ascii=False, indent=2)}\n\n"
        f"Novel gist:\n{gist}\n\n"
        f"Novel context:\n{outline_context}\n\n"
        f"Current chapter plan:\n{chapter_json}\n\n"
        f"Use this JSON shape as the target output:\n{template_json}\n\n"
        "Requirements:\n"
        "- Keep the response focused on this chapter only.\n"
        "- Preserve alignment with the novel outline and running summary.\n"
        "- Keep the output as a single JSON object."
    )


def _call_genai(
    prompt: str,
    *,
    conversation_id: str,
    use_cache: bool,
    verbose: bool = False,
    json_logs: bool = False,
) -> str:
    from lib.genai import chat

    return chat(
        prompt,
        conversation_id=conversation_id,
        use_cache=use_cache,
        verbose=verbose,
        json_logs=json_logs,
    )


def _chapter_sort_key(chapter_payload: dict[str, Any], fallback_index: int) -> int:
    raw_value = chapter_payload.get("sl", fallback_index)
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return fallback_index


def _chapter_paths(book_path: Path, config: SnapshotConfig, chapter_number: int) -> tuple[Path, Path, Path]:
    chapter_cfg = config.chapters
    chapter_folder = chapter_cfg.chapterFolderPattern.replace("{n}", str(chapter_number))
    chapter_root = book_path / "BookChapters" / chapter_folder
    prompt_name = chapter_cfg.chapterFiles[1].replace("{n}", str(chapter_number))
    parameter_name = chapter_cfg.chapterFiles[0].replace("{n}", str(chapter_number))
    return chapter_root, chapter_root / prompt_name, chapter_root / parameter_name


def _prompt_content_for_file(path: Path) -> Any:
    if path.suffix.lower() == ".json":
        raw = input(
            f"JSON content for {path.name} (JSON string or plain text for root; empty=default): "
        )
        return _normalize_json_content(raw)

    raw = input(f"Text content for {path.name} (empty=default): ")
    if not raw:
        return TEXT_DUMMY_CONTENT
    return raw


def _write_dummy_file(path: Path, content: Any, *, encoding: str) -> None:
    if path.suffix.lower() == ".json":
        _write_json(path, content, encoding=encoding)
        return

    _write_text(path, str(content), encoding=encoding)


def _iter_configured_files(book_path: Path, config: SnapshotConfig) -> list[Path]:
    paths: list[Path] = []

    for file_name in config.bookRootFiles:
        paths.append(book_path / file_name)

    chapter_root = book_path / "BookChapters"
    chapter_cfg = config.chapters
    for number in range(chapter_cfg.start, chapter_cfg.end + 1):
        chapter_folder = chapter_cfg.chapterFolderPattern.replace("{n}", str(number))
        chapter_path = chapter_root / chapter_folder

        for pattern in chapter_cfg.chapterFiles:
            paths.append(chapter_path / pattern.replace("{n}", str(number)))

        out_folder = chapter_cfg.chapterOutFolderPattern.replace("{n}", str(number))
        out_path = chapter_path / out_folder
        for pattern in chapter_cfg.chapterOutFiles:
            file_name = pattern.replace("{n}", str(number))
            paths.append(out_path / file_name)

    return paths


def write_dummy_content(
    *,
    workspace_root: str | Path,
    book_name: str,
    config_path: str | Path,
    chapter_count: int | None = None,
    encoding: str = "utf-8",
    content_provider: Callable[[Path], Any] | None = None,
    verbose: bool = False,
    json_logs: bool = False,
) -> Path:
    config = SnapshotConfig.from_json_file(config_path)
    manager = SnapshotManager(config, encoding=encoding, verbose=verbose, json_logs=json_logs)
    book_path = manager.initialize_workspace(workspace_root, book_name, number_of_chapters=chapter_count)
    _verbose_print(
        verbose,
        json_logs,
        f"Writing dummy content under: {_relative_path_text(book_path)}",
        "dummy.start",
    )

    provider = content_provider or _prompt_content_for_file

    for path in _iter_configured_files(book_path, config):
        content = provider(path)
        _write_dummy_file(path, content, encoding=encoding)

    _verbose_print(verbose, json_logs, f"Dummy content write completed for: {book_name}", "dummy.done")

    return book_path


def write_generated_content(
    *,
    workspace_root: str | Path,
    book_name: str,
    config_path: str | Path,
    encoding: str = "utf-8",
    gist: str | None = None,
    use_cache: bool = True,
    verbose: bool = False,
    json_logs: bool = False,
) -> Path:
    config = SnapshotConfig.from_json_file(config_path)
    manager = SnapshotManager(config, encoding=encoding, verbose=verbose, json_logs=json_logs)
    book_path = Path(workspace_root) / book_name

    settings = _load_project_settings(book_path, encoding=encoding)
    _verbose_print(
        verbose,
        json_logs,
        f"Loaded Settings.json for {settings.book_name} with chapter_count={settings.chapter_count}",
        "settings.loaded",
    )
    manager.initialize_workspace(
        workspace_root,
        book_name,
        number_of_chapters=settings.chapter_count,
    )
    novel_gist = gist.strip() if gist else _prompt_for_gist(book_name)
    if not novel_gist:
        raise ValueError("Novel gist is required.")

    novel_template = _load_template_payload("book.json", encoding=encoding)
    chapter_template = _load_template_payload("chapter.json", encoding=encoding)
    _verbose_print(verbose, json_logs, "Loaded book and chapter JSON templates", "templates.loaded")

    book_prompt = _build_novel_prompt(settings=settings, gist=novel_gist, template_payload=novel_template)
    book_prompt_path = book_path / "BookPrompt.txt"
    _write_text(book_prompt_path, book_prompt, encoding=encoding)
    _verbose_print(
        verbose,
        json_logs,
        f"Saved novel prompt to: {_relative_path_text(book_prompt_path)}",
        "prompt.novel.saved",
    )

    outline_response = _call_genai(
        book_prompt,
        conversation_id=f"{book_name}-novel-outline",
        use_cache=use_cache,
        verbose=verbose,
        json_logs=json_logs,
    )
    outline_payload = _extract_json_payload(outline_response)
    if not isinstance(outline_payload, dict):
        raise ValueError("Novel layout response must be a JSON object.")

    outline_path = book_path / "BookOutline.json"
    _write_json(outline_path, outline_payload, encoding=encoding)
    _verbose_print(
        verbose,
        json_logs,
        f"Saved novel outline to: {_relative_path_text(outline_path)}",
        "outline.saved",
    )

    chapters = outline_payload.get("chapters", [])
    if not isinstance(chapters, list):
        raise ValueError("BookOutline.json must contain a chapters array.")

    sorted_chapters = sorted(
        (chapter for chapter in chapters if isinstance(chapter, dict)),
        key=lambda chapter: _chapter_sort_key(chapter, 0),
    )
    _verbose_print(
        verbose,
        json_logs,
        f"Generating chapter prompts and parameters for {len(sorted_chapters)} chapters",
        "chapters.start",
    )

    for fallback_index, chapter_payload in enumerate(sorted_chapters, start=1):
        chapter_number = _chapter_sort_key(chapter_payload, fallback_index)
        chapter_root, prompt_path, parameter_path = _chapter_paths(book_path, config, chapter_number)
        chapter_root.mkdir(parents=True, exist_ok=True)

        chapter_prompt = _build_chapter_prompt(
            settings=settings,
            gist=novel_gist,
            outline_payload=outline_payload,
            chapter_payload=chapter_payload,
            template_payload=chapter_template,
        )
        _write_text(prompt_path, chapter_prompt, encoding=encoding)
        _verbose_print(
            verbose,
            json_logs,
            f"Saved chapter {chapter_number} prompt to: {_relative_path_text(prompt_path)}",
            "prompt.chapter.saved",
        )

        chapter_response = _call_genai(
            chapter_prompt,
            conversation_id=f"{book_name}-chapter-{chapter_number}",
            use_cache=use_cache,
            verbose=verbose,
            json_logs=json_logs,
        )
        chapter_json = _extract_json_payload(chapter_response)
        _write_json(parameter_path, chapter_json, encoding=encoding)
        _verbose_print(
            verbose,
            json_logs,
            f"Saved chapter {chapter_number} parameters to: {_relative_path_text(parameter_path)}",
            "chapter.parameters.saved",
        )

    _verbose_print(verbose, json_logs, f"Generated content write completed for: {book_name}", "generated.done")
    return book_path


def _build_author_prompt(
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
        "- Prepend chapter title to the generated chapter text (the caller will also persist title separately).\n"
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


def _normalize_author_payload(payload: dict[str, Any]) -> dict[str, Any]:
    title = str(payload.get("chapter_title", "")).strip() or "Untitled Chapter"
    chapter_text = str(payload.get("chapter_text", "")).strip()
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
        "chapter_summary": summary,
        "next_running_summary": next_running_summary,
        "next_characters": normalized_characters,
    }


def _render_character_text(characters: list[dict[str, str]]) -> str:
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


def _extend_outline_characters(outline_payload: dict[str, Any], new_characters: list[dict[str, str]]) -> None:
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


def write_authored_content(
    *,
    workspace_root: str | Path,
    book_name: str,
    config_path: str | Path,
    encoding: str = "utf-8",
    gist: str | None = None,
    use_cache: bool = True,
    verbose: bool = False,
    json_logs: bool = False,
) -> Path:
    config = SnapshotConfig.from_json_file(config_path)
    manager = SnapshotManager(config, encoding=encoding, verbose=verbose, json_logs=json_logs)
    book_path = Path(workspace_root) / book_name

    settings = _load_project_settings(book_path, encoding=encoding)
    manager.initialize_workspace(
        workspace_root,
        book_name,
        number_of_chapters=settings.chapter_count,
    )

    outline_path = book_path / "BookOutline.json"
    outline_payload = _load_json_file(outline_path, encoding=encoding)
    if not isinstance(outline_payload, dict):
        raise ValueError("BookOutline.json must be a JSON object.")

    chapters = outline_payload.get("chapters", [])
    if not isinstance(chapters, list):
        raise ValueError("BookOutline.json must contain a chapters array.")

    novel_gist = (gist or str(outline_payload.get("gist", "")).strip() or _prompt_for_gist(book_name)).strip()
    if not novel_gist:
        raise ValueError("Novel gist is required for draft command.")

    sorted_chapters = sorted(
        (chapter for chapter in chapters if isinstance(chapter, dict)),
        key=lambda chapter: _chapter_sort_key(chapter, 0),
    )
    _verbose_print(
        verbose,
        json_logs,
        f"Drafting {len(sorted_chapters)} chapters for: {book_name} (cache={'on' if use_cache else 'off'})",
        "draft.start",
    )

    for fallback_index, chapter_payload in enumerate(sorted_chapters, start=1):
        chapter_number = _chapter_sort_key(chapter_payload, fallback_index)
        chapter_root, _, parameter_path = _chapter_paths(book_path, config, chapter_number)
        chapter_cfg = config.chapters
        out_folder = chapter_cfg.chapterOutFolderPattern.replace("{n}", str(chapter_number))
        out_path = chapter_root / out_folder
        out_path.mkdir(parents=True, exist_ok=True)

        if parameter_path.exists():
            chapter_parameter_payload = _load_json_file(parameter_path, encoding=encoding)
            if not isinstance(chapter_parameter_payload, dict):
                chapter_parameter_payload = chapter_payload
        else:
            chapter_parameter_payload = chapter_payload

        previous_running_summary = str(outline_payload.get("running_summary", "")).strip()
        _verbose_print(
            verbose,
            json_logs,
            f"Drafting chapter {chapter_number} using context: {_relative_path_text(parameter_path)}",
            "draft.chapter.start",
        )
        prompt = _build_author_prompt(
            settings=settings,
            gist=novel_gist,
            outline_payload=outline_payload,
            chapter_payload=chapter_payload,
            chapter_parameter_payload=chapter_parameter_payload,
            chapter_number=chapter_number,
            previous_running_summary=previous_running_summary,
        )
        response = _call_genai(
            prompt,
            conversation_id=f"{book_name}-draft-chapter-{chapter_number}",
            use_cache=use_cache,
            verbose=verbose,
            json_logs=json_logs,
        )
        author_payload_raw = _extract_json_payload(response)
        if not isinstance(author_payload_raw, dict):
            raise ValueError(f"Draft response for chapter {chapter_number} must be a JSON object.")
        author_payload = _normalize_author_payload(author_payload_raw)

        chapter_title = author_payload["chapter_title"]
        chapter_text = author_payload["chapter_text"]
        chapter_summary = author_payload["chapter_summary"]
        next_running_summary = author_payload["next_running_summary"]
        next_characters = author_payload["next_characters"]

        generated_text = f"{chapter_title}\n\n{chapter_text}".strip() + "\n"
        chapter_generated_path = out_path / "ChapterGenerated.txt"
        chapter_summary_path = out_path / "ChapterSummary.txt"
        chapter_character_path = out_path / "ChapterCharacter.txt"
        chapter_characters_compat_path = out_path / "ChapterCharacters.txt"

        _write_text(chapter_generated_path, generated_text, encoding=encoding)
        _write_text(chapter_summary_path, chapter_summary + "\n", encoding=encoding)
        character_text = _render_character_text(next_characters)
        _write_text(chapter_character_path, character_text, encoding=encoding)
        _write_text(chapter_characters_compat_path, character_text, encoding=encoding)

        _verbose_print(
            verbose,
            json_logs,
            (
                f"Wrote chapter {chapter_number} outputs: "
                f"{_relative_path_text(chapter_generated_path)}, "
                f"{_relative_path_text(chapter_summary_path)}, "
                f"{_relative_path_text(chapter_character_path)}"
            ),
            "draft.chapter.files",
        )

        chapter_payload["chapter_title"] = chapter_title
        chapter_payload["chapter_summary"] = chapter_summary
        chapter_payload["chatper_text"] = chapter_text
        outline_payload["running_summary"] = next_running_summary
        _extend_outline_characters(outline_payload, next_characters)

        _verbose_print(
            verbose,
            json_logs,
            f"Drafted chapter {chapter_number}: {_relative_path_text(chapter_generated_path)}",
            "draft.chapter.done",
        )

    _write_json(outline_path, outline_payload, encoding=encoding)
    _verbose_print(
        verbose,
        json_logs,
        f"Updated running summary and characters in: {_relative_path_text(outline_path)}",
        "draft.outline.updated",
    )
    _verbose_print(verbose, json_logs, f"Draft command completed for: {book_name}", "draft.done")
    return book_path
