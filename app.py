import asyncio
import json
from pathlib import Path
from lib.genai import chat, generate_async

PROMPT = "Why is the sky blue? Answer in two sentences."

_CONFIG_PATH = Path(__file__).resolve().parent / ".pkbook" / "config.json"

def _load_config() -> dict:
    if _CONFIG_PATH.exists():
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    return {}

async def main():
    config = _load_config()
    provider = str(config.get("genai", {}).get("provider", "copilot")).strip().lower()

    print(f"=== Global provider (async): {provider} ===")
    safe_rendered = await generate_async(PROMPT, verbose=True)
    print(safe_rendered)


if __name__ == "__main__":
    asyncio.run(main())

    config = _load_config()
    provider = str(config.get("genai", {}).get("provider", "copilot")).strip().lower()
    print(f"\n=== Global provider (sync): {provider} ===")
    print(chat(PROMPT, verbose=True))