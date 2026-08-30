import json
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import SemanticCache
from app.database.session import AsyncSessionLocal
import hashlib

logger = logging.getLogger(__name__)

class SemanticCacheManager:
    def __init__(self):
        self.is_installed = False
        self.embedding_model = None
        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer("BAAI/bge-m3")
            self.is_installed = True
        except Exception as e:
            logger.error(f"Semantic Cache failed to load embedding model: {e}")

    def _hash_prompt(self, prompt: str) -> str:
        return hashlib.sha256(prompt.strip().lower().encode('utf-8')).hexdigest()

    async def get_semantic_cache(self, prompt: str, model: str, policy_version: str, max_age_hours: int = 24) -> dict | None:
        if not self.is_installed:
            return None
            
        try:
            # 1. Embed the prompt
            embedding = self.embedding_model.encode(prompt, normalize_embeddings=True).tolist()
            prompt_hash = self._hash_prompt(prompt)
            
            async with AsyncSessionLocal() as session:
                # 2. Query for similarity + constraints
                freshness_limit = datetime.utcnow() - timedelta(hours=max_age_hours)
                
                # We use cosine distance. For pgvector, `<=>` operator means cosine distance (1 - cosine_similarity).
                # Similarity > 0.95 means Distance < 0.05
                stmt = select(SemanticCache).where(
                    SemanticCache.model == model,
                    SemanticCache.policy_version == policy_version,
                    SemanticCache.created_at >= freshness_limit,
                    SemanticCache.prompt_embedding.cosine_distance(embedding) < 0.05
                ).order_by(
                    SemanticCache.prompt_embedding.cosine_distance(embedding)
                ).limit(1)
                
                result = await session.execute(stmt)
                cache_entry = result.scalars().first()
                
                if cache_entry:
                    # Update hits
                    cache_entry.hits += 1
                    cache_entry.last_accessed = datetime.utcnow()
                    await session.commit()
                    return cache_entry.response
                    
        except Exception as e:
            logger.error(f"Semantic cache retrieval failed: {e}")
            
        return None

    async def set_semantic_cache(self, prompt: str, response: dict, model: str, policy_version: str):
        if not self.is_installed:
            return
            
        try:
            embedding = self.embedding_model.encode(prompt, normalize_embeddings=True).tolist()
            prompt_hash = self._hash_prompt(prompt)
            
            async with AsyncSessionLocal() as session:
                new_entry = SemanticCache(
                    prompt_hash=prompt_hash,
                    prompt_embedding=embedding,
                    model=model,
                    policy_version=policy_version,
                    response=response
                )
                session.add(new_entry)
                await session.commit()
        except Exception as e:
            logger.error(f"Semantic cache setting failed: {e}")

semantic_cache_manager = SemanticCacheManager()

