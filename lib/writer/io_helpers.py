from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .writables import ProjectSettings

TEXT_DUMMY_CONTENT = "hello"
JSON_DUMMY_CONTENT = {"root": "hello"}


def write_json(path: Path, content: Any, *, encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding) as handle:
        json.dump(content, handle, ensure_ascii=False, indent=2)


def write_text(path: Path, content: str, *, encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding=encoding)


def verbose_print(verbose: bool, json_logs: bool, message: str, event: str = "trace") -> None:
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


def relative_path_text(path: str | Path) -> str:
    raw_path = Path(path)
    cwd = Path.cwd()
    try:
        return str(raw_path.resolve().relative_to(cwd.resolve()))
    except ValueError:
        return os.path.relpath(str(raw_path), start=str(cwd))


def read_text(path: Path, *, encoding: str) -> str:
    return path.read_text(encoding=encoding)


def normalize_json_content(raw: str) -> Any:
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


def load_json_file(path: Path, *, encoding: str) -> Any:
    return json.loads(read_text(path, encoding=encoding))


def extract_json_payload(raw: str) -> Any:
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


def load_project_settings(book_path: Path, *, encoding: str) -> ProjectSettings:
    settings_path = book_path / "Settings.json"
    payload = load_json_file(settings_path, encoding=encoding)
    return ProjectSettings(
        book_name=str(payload.get("book_name", book_path.name)),
        chapter_count=int(payload["chapter_count"]),
        root_folder=str(payload.get("root_folder", "")),
        date_created=str(payload.get("date_created", "")),
        location=str(payload.get("location", "")),
        user=str(payload.get("user", "")),
    )


def prompt_for_gist(book_name: str) -> str:
    gist = input(f"Novel gist for {book_name}: ").strip()
    if not gist:
        raise ValueError("Novel gist is required.")
    return gist


def prompt_content_for_file(path: Path) -> Any:
    if path.suffix.lower() == ".json":
        raw = input(
            f"JSON content for {path.name} (JSON string or plain text for root; empty=default): "
        )
        return normalize_json_content(raw)

    raw = input(f"Text content for {path.name} (empty=default): ")
    if not raw:
        return TEXT_DUMMY_CONTENT
    return raw


def write_dummy_file(path: Path, content: Any, *, encoding: str) -> None:
    if path.suffix.lower() == ".json":
        write_json(path, content, encoding=encoding)
        return

    write_text(path, str(content), encoding=encoding)


def call_genai(
    prompt: str,
    *,
    conversation_id: str,
    use_cache: bool,
    history_root: str | Path | None = None,
    agent_name: str = "default-agent",
    verbose: bool = False,
    json_logs: bool = False,
    provider_instance_name: str | None = None,
) -> str:
    from lib.genai import chat

    return chat(
        prompt,
        conversation_id=conversation_id,
        use_cache=use_cache,
        history_root=Path(history_root) if history_root is not None else None,
        agent_name=agent_name,
        verbose=verbose,
        json_logs=json_logs,
        provider_instance_name=provider_instance_name,
    )
