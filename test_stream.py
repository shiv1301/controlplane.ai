import asyncio
import httpx
from app.config import settings

async def main():
    async with httpx.AsyncClient() as client:
        # A CRITICAL complexity prompt to trigger full-response buffering
        complex_prompt = (
            "Analyze this python algorithm architecture mathematically step by step. "
            "Compare and evaluate different microservices formats. "
            "Format the output as a json table."
        ) * 5
        
        print("Sending request... Expecting CRITICAL buffer (all at once)")
        async with client.stream(
            "POST", 
            "http://localhost:8000/v1/chat/completions",
            json={"model": "qwen3:1.7b", "messages": [{"role": "user", "content": complex_prompt}], "temperature": 0.5, "stream": True},
            headers={"Authorization": f"Bearer {settings.api_key_secret}"},
            timeout=120.0
        ) as response:
            print(f"Status Code: {response.status_code}")
            async for chunk in response.aiter_text():
                print(chunk, end="", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
