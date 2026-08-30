from app.providers.base import LLMProvider
from app.providers.ollama import OllamaProvider

class RequestRouter:
    def __init__(self):
        self.providers = {
            "ollama": OllamaProvider()
        }
        # Configurable routing mappings (all mapped to qwen3:1.7b for now as requested)
        self.tier_mappings = {
            "small": "qwen3:1.7b",
            "medium": "qwen3:1.7b",
            "large": "qwen3:1.7b"
        }
    
    def get_provider_for_model(self, model: str) -> LLMProvider:
        # Phase 1/2: Route everything to Ollama provider instance
        return self.providers["ollama"]

    def route_by_complexity(self, complexity: float) -> tuple[str, str]:
        """Returns (tier_name, mapped_model)"""
        if complexity < 0.3:
            tier = "small"
        elif complexity < 0.7:
            tier = "medium"
        else:
            tier = "large"
            
        return tier, self.tier_mappings[tier]

router = RequestRouter()
