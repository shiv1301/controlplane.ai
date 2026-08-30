from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any

class LLMProvider(ABC):
    @abstractmethod
    async def generate_stream(self, messages: list[dict], model: str, temperature: float, max_tokens: int) -> AsyncGenerator[Dict[str, Any], None]:
        pass
    
    @abstractmethod
    async def generate(self, messages: list[dict], model: str, temperature: float, max_tokens: int) -> Dict[str, Any]:
        pass
