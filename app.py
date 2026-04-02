import asyncio
import json
from pathlib import Path
from lib.genai import chat, generate_async, OllamaChat

PROMPT = "Why is the sky blue? Answer in two sentences."

_CONFIG_PATH = Path(__file__).resolve().parent / ".pkbook" / "config.json"

def _load_config() -> dict:
    if _CONFIG_PATH.exists():
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    return {}

async def main():
    config = _load_config()

    print("=== Copilot (async) ===")
    safe_rendered = await generate_async(PROMPT)
    print(safe_rendered)

    print("\n=== Ollama (async) ===")
    ollama_client = OllamaChat.from_config(config, verbose=True)
    print(f"  model: {ollama_client.model}  host: {ollama_client._ollama_host}")
    response = await ollama_client.send(PROMPT)
    print(response)

if __name__ == "__main__":
    asyncio.run(main())

    print("\n=== Copilot (sync) ===")
    print(chat(PROMPT))

    print("\n=== Ollama (sync) ===")
    config = _load_config()
    print(chat(PROMPT, client=OllamaChat.from_config(config)))