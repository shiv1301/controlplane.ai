from redis.asyncio import Redis
from app.config import settings

redis_client: Redis = None

async def init_redis():
    global redis_client
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)

async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.aclose()

def get_redis() -> Redis:
    return redis_client
