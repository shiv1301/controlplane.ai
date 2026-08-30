import redis.asyncio as redis
import json
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class RedisAuditQueue:
    def __init__(self):
        self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        self.stream_name = "audit:human_review"

    async def publish_for_review(self, request_id: str, payload: dict):
        """Pushes a flagged payload to the Redis Stream for human review."""
        try:
            # XADD: stream_name, *, field value ...
            await self.redis_client.xadd(
                self.stream_name,
                {"request_id": request_id, "payload": json.dumps(payload)}
            )
            logger.info(f"Published request {request_id} to HUMAN_REVIEW audit queue.")
        except Exception as e:
            logger.error(f"Failed to publish to audit queue: {e}")

audit_queue = RedisAuditQueue()

