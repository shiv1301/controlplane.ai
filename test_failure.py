import asyncio
import httpx
import time
from app.config import settings

async def main():
    async with httpx.AsyncClient(timeout=120.0) as client:
        print("--- Testing API with all services UP ---")
        res = await client.post("http://localhost:8000/v1/chat/completions",
            json={"model": "qwen3:1.7b", "messages": [{"role": "user", "content": "Hello"}], "temperature": 0.5, "stream": False},
            headers={"Authorization": f"Bearer {settings.api_key_secret}"}
        )
        print("Status:", res.status_code)
        print("Response:", res.text)

if __name__ == "__main__":
    asyncio.run(main())
