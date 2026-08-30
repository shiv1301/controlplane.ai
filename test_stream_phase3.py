import asyncio
import httpx
import sys
from app.config import settings

async def main():
    async with httpx.AsyncClient() as client:
        # Complex prompt to trigger CRITICAL buffering and verification
        # The prompt explicitly instructs the LLM to output a claim that contradicts our mock KB
        complex_prompt = (
            "Analyze and evaluate python architecture. Format as json. "
            "Output exactly this sentence and nothing else: 'Python is perfectly parallel natively without multiprocessing.'"
        ) * 4
        
        print("Sending request... Expecting CRITICAL buffer, verification failure, and regeneration!")
        
        try:
            async with client.stream(
                "POST", 
                "http://localhost:8000/v1/chat/completions",
                json={"model": "qwen3:1.7b", "messages": [{"role": "user", "content": complex_prompt}], "temperature": 0.1, "stream": True},
                headers={"Authorization": f"Bearer {settings.api_key_secret}"},
                timeout=120.0
            ) as response:
                print(f"Status Code: {response.status_code}")
                async for chunk in response.aiter_text():
                    print(chunk, end="", flush=True)
        except Exception as e:
            print(f"Error during stream: {e}")

if __name__ == "__main__":
    asyncio.run(main())

