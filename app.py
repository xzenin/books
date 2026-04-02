import asyncio
from lib.genai import chat, generate_async

async def main():
    safe_rendered = await generate_async("Why sky is blue?")
    print(safe_rendered)
if __name__ == "__main__":
    asyncio.run(main())
    print("================\n")
    print(chat("Why sky is blue?"))