import hashlib
import json
from app.redis.client import get_redis
from app.observability.logging import logger

def generate_cache_key(prompt: str, model: str, system_prompt_version: str, temperature: float, policy_version: str) -> str:
    # Normalize prompt by stripping whitespace and lowering case for more robust exact matching
    normalized_prompt = prompt.strip().lower()
    data = {
        "prompt": normalized_prompt,
        "model": model,
        "system_prompt_version": system_prompt_version,
        "temperature": temperature,
        "policy_version": policy_version
    }
    encoded = json.dumps(data, sort_keys=True).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()

async def get_cached_response(cache_key: str) -> dict | None:
    try:
        redis = get_redis()
        if not redis:
            return None
        data = await redis.get(f"cache:{cache_key}")
        if data:
            return json.loads(data)
    except Exception as e:
        logger.error(f"Redis cache error: {e}")
    return None

async def set_cached_response(cache_key: str, response_data: dict, ttl: int = 3600):
    try:
        redis = get_redis()
        if redis:
            await redis.setex(f"cache:{cache_key}", ttl, json.dumps(response_data))
    except Exception as e:
        logger.error(f"Redis cache set error: {e}")
