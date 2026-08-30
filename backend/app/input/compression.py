import logging
from app.config import settings
from app.routing.router import router

logger = logging.getLogger(__name__)

class PromptCompressor:
    def __init__(self):
        self.compression_model = settings.compression_model
        
    async def compress(self, original_prompt: str) -> str:
        # Avoid compressing already short prompts
        if len(original_prompt) < 100:
            return original_prompt
            
        provider = router.get_provider_for_model(self.compression_model)
        
        system_prompt = {
            "role": "system",
            "content": (
                "Compress the following prompt while preserving the task, constraints, "
                "entities, format, exclusions, and important context. Do not blindly shorten. "
                "Return only the compressed prompt."
            )
        }
        user_prompt = {
            "role": "user",
            "content": original_prompt
        }
        
        try:
            response = await provider.generate(
                messages=[system_prompt, user_prompt],
                model=self.compression_model,
                temperature=0.1,
                max_tokens=None
            )
            compressed_text = response.get("message", {}).get("content", "").strip()
            if compressed_text:
                return compressed_text
        except Exception as e:
            logger.error(f"Prompt compression failed: {e}")
            
        # Fallback to original if compression fails
        return original_prompt

compressor = PromptCompressor()

