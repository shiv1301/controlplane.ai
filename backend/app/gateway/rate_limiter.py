from fastapi import HTTPException
import time
from app.redis.client import redis_client

class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute

    async def check_rate_limit(self, user_id: str):
        if not redis_client:
            return # Fail open if Redis is down (to not break requests as per user prompt: 'Use Redis rate limiting without breaking existing requests.')
            
        current_minute = int(time.time() / 60)
        key = f"rate_limit:{user_id}:{current_minute}"
        
        try:
            current_count = await redis_client.incr(key)
            if current_count == 1:
                await redis_client.expire(key, 60)
                
            if current_count > self.requests_per_minute:
                raise HTTPException(status_code=429, detail="Too Many Requests")
        except HTTPException:
            raise
        except Exception:
            # If Redis connection fails, we fail open (do not break existing requests)
            pass

rate_limiter = RateLimiter(requests_per_minute=100) # Default for testing

