import json
import httpx
from typing import AsyncGenerator, Dict, Any
from app.providers.base import LLMProvider
from app.config import settings

class OllamaProvider(LLMProvider):
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=300.0)

    def _convert_messages(self, messages: list[dict]) -> list[dict]:
        # Inject system prompt to disable thinking for reasoning models to save tokens
        has_system = any(m.get("role") == "system" for m in messages)
        if not has_system:
            messages = [{"role": "system", "content": "You are a direct, concise assistant. Do NOT use <think> blocks. Do not explain your reasoning. Provide only the final answer directly."}] + messages
        return messages

    async def generate_stream(self, messages: list[dict], model: str, temperature: float, max_tokens: int) -> AsyncGenerator[Dict[str, Any], None]:
        payload = {
            "model": model,
            "messages": self._convert_messages(messages),
            "options": {
                "temperature": temperature,
            },
            "stream": True
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        async with self.client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    yield data

    async def generate(self, messages: list[dict], model: str, temperature: float, max_tokens: int) -> Dict[str, Any]:
        payload = {
            "model": model,
            "messages": self._convert_messages(messages),
            "options": {
                "temperature": temperature,
            },
            "stream": False
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        response = await self.client.post("/api/chat", json=payload)
        response.raise_for_status()
        return response.json()
