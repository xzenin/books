from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from copilot import CopilotClient

try:
    import ollama  # type: ignore[import-not-found]
except ImportError:
    ollama = None


DEFAULT_CONVERSATION_ID = "default"


def _default_storage_root() -> Path:
    return Path(__file__).resolve().parent.parent / ".pkbook" / "_genai"


def _load_runtime_config() -> dict:
    config_path = Path(__file__).resolve().parent.parent / ".pkbook" / "config.json"
    if not config_path.exists():
        return {}
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


_RUNTIME_CONFIG = _load_runtime_config()
_CLIENT_CACHE: dict[tuple[str, str, str, str, str, bool, bool], "GenAIChat"] = {}


@dataclass
class ChatMessage:
    role: str
    content: str
    created_at: str


async def allow_permissions(_request, _context):
    return {"behavior": "allow"}


class GenAIChat(ABC):
    def __init__(
        self,
        conversation_id: str = DEFAULT_CONVERSATION_ID,
        storage_root: Optional[Path] = None,
        history_root: Optional[Path] = None,
        agent_name: str = "default-agent",
        verbose: bool = False,
        json_logs: bool = False,
    ) -> None:
        self.conversation_id = conversation_id or DEFAULT_CONVERSATION_ID
        self.storage_root = Path(storage_root) if storage_root is not None else _default_storage_root()
        self.verbose = verbose
        self.json_logs = json_logs
        self.agent_name = agent_name.strip() or "default-agent"
        self.agent_dir_name = self._safe_name(self.agent_name)
        self.base_genai_dir = self.storage_root
        self.history_root: Optional[Path] = None
        self.history_dir = self.storage_root / self.agent_dir_name
        self.cache_dir = self.storage_root / self.agent_dir_name / "cache"
        self.history_file = self.history_dir / f"{self._safe_name(self.conversation_id)}.json"
        self._messages: list[ChatMessage] = []
        self._apply_storage_scope(history_root=history_root, agent_name=agent_name)

    @property
    def messages(self) -> list[ChatMessage]:
        return list(self._messages)

    def clear_history(self) -> None:
        self._messages = []
        self._save_history()

    def _resolve_base_genai_dir(self, history_root: Optional[Path]) -> Path:
        if history_root is None:
            return self.storage_root

        normalized_root = Path(history_root).resolve()
        if normalized_root.name.lower() == "_genai":
            return normalized_root
        return normalized_root / "_genai"

    def _apply_storage_scope(self, history_root: Optional[Path], agent_name: Optional[str]) -> None:
        if agent_name is not None:
            normalized_agent = agent_name.strip() or "default-agent"
            self.agent_name = normalized_agent
            self.agent_dir_name = self._safe_name(normalized_agent)

        base_dir = self._resolve_base_genai_dir(history_root)
        normalized_root = Path(history_root).resolve() if history_root is not None else None
        if (
            normalized_root == self.history_root
            and base_dir == self.base_genai_dir
            and self.history_file.exists()
        ):
            return

        self.history_root = normalized_root
        self.base_genai_dir = base_dir
        self.history_dir = self.base_genai_dir / self.agent_dir_name
        self.cache_dir = self.base_genai_dir / self.agent_dir_name / "cache"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.history_dir / f"{self._safe_name(self.conversation_id)}.json"
        self._messages = self._load_history()

    def set_history_root(self, history_root: Optional[Path]) -> None:
        self._apply_storage_scope(history_root=history_root, agent_name=None)

    def set_agent_name(self, agent_name: str) -> None:
        self._apply_storage_scope(history_root=self.history_root, agent_name=agent_name)

    def last_message(self, role: Optional[str] = None) -> Optional[ChatMessage]:
        for message in reversed(self._messages):
            if role is None or message.role == role:
                return message
        return None

    async def send(
        self,
        prompt: str,
        use_cache: bool = True,
        history_root: Optional[Path] = None,
        agent_name: Optional[str] = None,
    ) -> str:
        if history_root is not None or agent_name is not None or self.history_root is None:
            self._apply_storage_scope(history_root=history_root, agent_name=agent_name)

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
                    "history_root": str(self.history_root) if self.history_root is not None else "",
                    "agent_name": self.agent_name,
                }
                print(json.dumps(payload, ensure_ascii=False))
                return
            print(f"[verbose][genai] {message}")

    @abstractmethod
    async def _request_model(self, prompt: str) -> str:
        raise NotImplementedError


class CopilotAIChat(GenAIChat):
    async def _request_model(self, prompt: str) -> str:
        timeout_seconds = _copilot_timeout_seconds(_RUNTIME_CONFIG)
        attempts: list[float] = [timeout_seconds, max(timeout_seconds * 1.5, timeout_seconds + 60.0)]
        last_error: Exception | None = None

        for attempt_index, attempt_timeout in enumerate(attempts, start=1):
            client = CopilotClient()
            await client.start()

            try:
                session = await client.create_session(on_permission_request=allow_permissions)
                response_event = await session.send_and_wait(prompt, timeout=attempt_timeout)
                return self._render_response(response_event)
            except TimeoutError as exc:
                last_error = exc
                self._verbose_print(
                    (
                        f"Copilot timeout after {attempt_timeout:.1f}s on attempt {attempt_index}/{len(attempts)} "
                        f"for conversation '{self.conversation_id}'"
                    )
                )
            finally:
                await client.stop()

        if last_error is not None:
            raise TimeoutError(
                (
                    "Copilot request timed out after retry. "
                    "Increase genai.timeout_seconds in .pkbook/config.json or reduce prompt size. "
                    f"Last error: {last_error}"
                )
            )
        raise RuntimeError("Copilot request failed without a captured exception.")

    def _render_response(self, response_event) -> str:
        content = None
        if response_event is not None and getattr(response_event, "data", None) is not None:
            content = getattr(response_event.data, "content", None)

        if content:
            return content.strip()
        if hasattr(response_event, "model_dump"):
            return json.dumps(response_event.model_dump(), ensure_ascii=False, indent=2)
        return str(response_event).strip()


class OllamaChat(GenAIChat):
    DEFAULT_MODEL = "llama3"
    DEFAULT_HOST = "http://127.0.0.1:11434"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        host: Optional[str] = None,
        **kwargs,
    ) -> None:
        self.model = model
        self._ollama_host = host or self.DEFAULT_HOST
        super().__init__(**kwargs)

    @classmethod
    def from_config(
        cls,
        config: dict,
        *,
        provider_instance_name: Optional[str] = None,
        **kwargs,
    ) -> "OllamaChat":
        """Create an OllamaChat instance from config, optionally pinned to a credential instance."""
        providers = config.get("genai", {}).get("credentials", [])
        ollama_cfg: dict = {}

        if provider_instance_name:
            normalized_instance = provider_instance_name.strip().lower()
            for provider in providers if isinstance(providers, list) else []:
                if not isinstance(provider, dict):
                    continue
                name = str(provider.get("name", "")).strip().lower()
                provider_type = str(provider.get("type", "ollama")).strip().lower()
                if name == normalized_instance and provider_type == "ollama":
                    ollama_cfg = provider
                    break

        if not ollama_cfg and isinstance(providers, list):
            for provider in providers:
                if not isinstance(provider, dict):
                    continue
                provider_type = str(provider.get("type", "")).strip().lower()
                if provider_type == "ollama":
                    ollama_cfg = provider
                    break

        model = ollama_cfg.get("model", cls.DEFAULT_MODEL)
        url = ollama_cfg.get("url", cls.DEFAULT_HOST)
        # Normalise URL: replace localhost with 127.0.0.1 to avoid IPv6 issues on Windows
        host = url.replace("localhost", "127.0.0.1") if url else cls.DEFAULT_HOST
        return cls(model=model, host=host, **kwargs)

    async def _request_model(self, prompt: str) -> str:
        if ollama is None:
            raise ModuleNotFoundError(
                "Ollama provider requires the 'ollama' package. Install it with: pip install ollama"
            )
        client = ollama.AsyncClient(host=self._ollama_host)
        response = await client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.message.content.strip()


def _find_credential_by_instance_name(config: dict, instance_name: str) -> tuple[str, dict]:
    """Find credential config by instance name and return (provider_type, credential_config)."""
    genai_cfg = config.get("genai", {})
    if not isinstance(genai_cfg, dict):
        return "", {}

    credentials = genai_cfg.get("credentials", [])
    if not isinstance(credentials, list):
        return "", {}

    normalized_name = str(instance_name).strip().lower()
    for cred in credentials:
        if not isinstance(cred, dict):
            continue
        if str(cred.get("name", "")).strip().lower() == normalized_name:
            provider_type = str(cred.get("type", "ollama")).strip().lower()
            return provider_type, cred

    return "", {}


def _resolve_provider_name(config: dict) -> str:
    override = str(os.environ.get("BOOK_AI_PROVIDER_OVERRIDE", "")).strip().lower()
    if override:
        return override

    genai_cfg = config.get("genai", {})
    if not isinstance(genai_cfg, dict):
        return "ollama"
    provider = str(genai_cfg.get("provider", "ollama")).strip().lower()
    return provider or "ollama"


def _copilot_timeout_seconds(config: dict) -> float:
    genai_cfg = config.get("genai", {})
    if not isinstance(genai_cfg, dict):
        return 180.0

    timeout_value = genai_cfg.get("timeout_seconds")
    copilot_cfg = genai_cfg.get("copilot", {})
    if isinstance(copilot_cfg, dict) and "timeout_seconds" in copilot_cfg:
        timeout_value = copilot_cfg.get("timeout_seconds")

    try:
        timeout = float(timeout_value)
    except (TypeError, ValueError):
        timeout = 180.0

    if timeout < 30.0:
        timeout = 30.0
    return timeout


def _create_provider_client(
    provider: str,
    config: dict,
    conversation_id: str,
    storage_root: Optional[Path],
    history_root: Optional[Path],
    agent_name: str,
    verbose: bool,
    json_logs: bool,
    provider_instance_name: Optional[str] = None,
) -> GenAIChat:
    kwargs = {
        "conversation_id": conversation_id,
        "storage_root": storage_root,
        "history_root": history_root,
        "agent_name": agent_name,
        "verbose": verbose,
        "json_logs": json_logs,
    }

    if provider == "copilot":
        return CopilotAIChat(**kwargs)

    # Default and fallback provider is Ollama.
    return OllamaChat.from_config(
        config,
        provider_instance_name=provider_instance_name,
        **kwargs,
    )


def _default_client(
    conversation_id: str,
    storage_root: Optional[Path],
    history_root: Optional[Path],
    agent_name: str,
    verbose: bool,
    json_logs: bool,
    provider_instance_name: Optional[str] = None,
) -> GenAIChat:
    resolved_instance_name: Optional[str] = provider_instance_name
    if provider_instance_name:
        provider_type, credential = _find_credential_by_instance_name(_RUNTIME_CONFIG, provider_instance_name)
        provider = provider_type if credential else _resolve_provider_name(_RUNTIME_CONFIG)
    else:
        configured_provider = _resolve_provider_name(_RUNTIME_CONFIG)
        provider_type, credential = _find_credential_by_instance_name(_RUNTIME_CONFIG, configured_provider)
        if credential:
            provider = provider_type
            resolved_instance_name = configured_provider
        else:
            # Backward compatible mode: provider is a type (copilot/ollama/etc.)
            provider = configured_provider

    storage_key = str(storage_root) if storage_root is not None else ""
    history_key = str(Path(history_root).resolve()) if history_root is not None else ""
    cache_key = (
        provider,
        resolved_instance_name or "",
        conversation_id,
        storage_key,
        history_key,
        agent_name,
        verbose,
        json_logs,
    )
    cached = _CLIENT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    client = _create_provider_client(
        provider=provider,
        config=_RUNTIME_CONFIG,
        conversation_id=conversation_id,
        storage_root=storage_root,
        history_root=history_root,
        agent_name=agent_name,
        verbose=verbose,
        json_logs=json_logs,
        provider_instance_name=resolved_instance_name,
    )
    _CLIENT_CACHE[cache_key] = client
    return client


async def generate_async(
    text: str,
    conversation_id: str = DEFAULT_CONVERSATION_ID,
    use_cache: bool = True,
    storage_root: Optional[Path] = None,
    history_root: Optional[Path] = None,
    agent_name: str = "default-agent",
    client: Optional[GenAIChat] = None,
    verbose: bool = False,
    json_logs: bool = False,
    provider_instance_name: Optional[str] = None,
) -> str:
    chat_client = client or _default_client(
        conversation_id=conversation_id,
        storage_root=storage_root,
        history_root=history_root,
        agent_name=agent_name,
        verbose=verbose,
        json_logs=json_logs,
        provider_instance_name=provider_instance_name,
    )
    return await chat_client.send(
        text,
        use_cache=use_cache,
        history_root=history_root,
        agent_name=agent_name,
    )


def chat(
    prompt: str,
    conversation_id: str = DEFAULT_CONVERSATION_ID,
    use_cache: bool = True,
    storage_root: Optional[Path] = None,
    history_root: Optional[Path] = None,
    agent_name: str = "default-agent",
    client: Optional[GenAIChat] = None,
    verbose: bool = False,
    json_logs: bool = False,
    provider_instance_name: Optional[str] = None,
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
                history_root=history_root,
                agent_name=agent_name,
                client=client,
                verbose=verbose,
                json_logs=json_logs,
                provider_instance_name=provider_instance_name,
            )
        )

    raise RuntimeError("chat() cannot be used inside a running event loop. Use await generate_async(...).")


async def main():
    client = _default_client(
        conversation_id="demo",
        storage_root=None,
        history_root=None,
        agent_name="demo-agent",
        verbose=False,
        json_logs=False,
    )
    response = await client.send("How do I parse JSON in Python?")
    print(response)
