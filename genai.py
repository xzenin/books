from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from copilot import CopilotClient


DEFAULT_CONVERSATION_ID = "default"


@dataclass
class ChatMessage:
    role: str
    content: str
    created_at: str


async def allow_permissions(_request, _context):
    return {"behavior": "allow"}


class GenAIChat:
    def __init__(
        self,
        conversation_id: str = DEFAULT_CONVERSATION_ID,
        storage_root: Optional[Path] = None,
        verbose: bool = False,
        json_logs: bool = False,
    ) -> None:
        self.conversation_id = conversation_id or DEFAULT_CONVERSATION_ID
        self.storage_root = storage_root or Path(__file__).resolve().parent / ".pkbook" / "_genai"
        self.verbose = verbose
        self.json_logs = json_logs
        self.history_dir = self.storage_root / "history"
        self.cache_dir = self.storage_root / "cache"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.history_file = self.history_dir / f"{self._safe_name(self.conversation_id)}.json"
        self._messages = self._load_history()

    @property
    def messages(self) -> list[ChatMessage]:
        return list(self._messages)

    def clear_history(self) -> None:
        self._messages = []
        self._save_history()

    def last_message(self, role: Optional[str] = None) -> Optional[ChatMessage]:
        for message in reversed(self._messages):
            if role is None or message.role == role:
                return message
        return None

    async def send(self, prompt: str, use_cache: bool = True) -> str:
        normalized_prompt = prompt.strip()
        if not normalized_prompt:
            raise ValueError("Prompt cannot be empty.")

        self._verbose_print(
            f"Sending prompt in conversation '{self.conversation_id}' (cache={'on' if use_cache else 'off'})"
        )

        request_payload = {
            "conversationId": self.conversation_id,
            "messages": [asdict(message) for message in self._messages],
            "prompt": normalized_prompt,
        }
        cache_file = self.cache_dir / f"{self._cache_key(request_payload)}.json"

        if use_cache and cache_file.exists():
            cached_response = self._load_cached_response(cache_file)
            self._verbose_print(f"Cache hit for conversation '{self.conversation_id}'")
            self._append_turn(normalized_prompt, cached_response)
            return cached_response

        response = await self._request_model(self._build_prompt(normalized_prompt))
        self._write_cache(cache_file, request_payload, response)
        self._append_turn(normalized_prompt, response)
        self._verbose_print(f"Received response for conversation '{self.conversation_id}'")
        return response

    def _append_turn(self, prompt: str, response: str) -> None:
        timestamp = self._utc_now()
        self._messages.append(ChatMessage(role="user", content=prompt, created_at=timestamp))
        self._messages.append(ChatMessage(role="assistant", content=response, created_at=timestamp))
        self._save_history()

    def _build_prompt(self, prompt: str) -> str:
        if not self._messages:
            return prompt

        transcript = "\n\n".join(
            f"{message.role.title()}: {message.content}" for message in self._messages
        )
        return (
            "Continue this conversation and answer only as the assistant.\n\n"
            f"Conversation so far:\n{transcript}\n\n"
            f"User: {prompt}\n\nAssistant:"
        )

    async def _request_model(self, prompt: str) -> str:
        client = CopilotClient()
        await client.start()

        try:
            session = await client.create_session(on_permission_request=allow_permissions)
            response_event = await session.send_and_wait(prompt)
            return self._render_response(response_event)
        finally:
            await client.stop()

    def _render_response(self, response_event) -> str:
        content = None
        if response_event is not None and getattr(response_event, "data", None) is not None:
            content = getattr(response_event.data, "content", None)

        if content:
            return content.strip()
        if hasattr(response_event, "model_dump"):
            return json.dumps(response_event.model_dump(), ensure_ascii=False, indent=2)
        return str(response_event).strip()

    def _load_history(self) -> list[ChatMessage]:
        if not self.history_file.exists():
            return []

        with self.history_file.open("r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)

        messages = payload.get("messages", [])
        return [ChatMessage(**message) for message in messages]

    def _save_history(self) -> None:
        payload = {
            "conversationId": self.conversation_id,
            "updatedAt": self._utc_now(),
            "messages": [asdict(message) for message in self._messages],
        }
        with self.history_file.open("w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, ensure_ascii=False, indent=2)

    def _load_cached_response(self, cache_file: Path) -> str:
        with cache_file.open("r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)
        return payload["response"]

    def _write_cache(self, cache_file: Path, request_payload: dict, response: str) -> None:
        payload = {
            "createdAt": self._utc_now(),
            "conversationId": self.conversation_id,
            "request": request_payload,
            "response": response,
        }
        with cache_file.open("w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, ensure_ascii=False, indent=2)

    def _cache_key(self, request_payload: dict) -> str:
        encoded = json.dumps(request_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _safe_name(self, raw_name: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", raw_name).strip("-._")
        if not slug:
            slug = DEFAULT_CONVERSATION_ID
        suffix = hashlib.sha1(raw_name.encode("utf-8")).hexdigest()[:10]
        return f"{slug}-{suffix}"

    def _utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _verbose_print(self, message: str) -> None:
        if self.verbose:
            if self.json_logs:
                payload = {
                    "timestamp": self._utc_now(),
                    "component": "genai",
                    "event": "trace",
                    "message": message,
                    "conversation_id": self.conversation_id,
                }
                print(json.dumps(payload, ensure_ascii=False))
                return
            print(f"[verbose][genai] {message}")


async def generate_async(
    text: str,
    conversation_id: str = DEFAULT_CONVERSATION_ID,
    use_cache: bool = True,
    storage_root: Optional[Path] = None,
    client: Optional[GenAIChat] = None,
    verbose: bool = False,
    json_logs: bool = False,
) -> str:
    chat_client = client or GenAIChat(
        conversation_id=conversation_id,
        storage_root=storage_root,
        verbose=verbose,
        json_logs=json_logs,
    )
    return await chat_client.send(text, use_cache=use_cache)


def chat(
    prompt: str,
    conversation_id: str = DEFAULT_CONVERSATION_ID,
    use_cache: bool = True,
    storage_root: Optional[Path] = None,
    client: Optional[GenAIChat] = None,
    verbose: bool = False,
    json_logs: bool = False,
) -> str:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            generate_async(
                prompt,
                conversation_id=conversation_id,
                use_cache=use_cache,
                storage_root=storage_root,
                client=client,
                verbose=verbose,
                json_logs=json_logs,
            )
        )

    raise RuntimeError("chat() cannot be used inside a running event loop. Use await generate_async(...).")


async def main():
    client = GenAIChat(conversation_id="demo")
    response = await client.send("How do I parse JSON in Python?")
    print(response)
