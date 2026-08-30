from app.database.session import AsyncSessionLocal
from app.database.models import KnowledgeBase
from app.verification.lazy_models import lazy_loader
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)

MOCK_DATA = [
    "Microservices architecture prioritizes flexibility and independent deployment.",
    "Monolithic architecture is easier to deploy initially but hard to scale.",
    "Python is single-threaded due to the GIL, making CPU-bound scaling difficult without multiprocessing.",
    "The Control Plane AI is designed to inspect traffic and enforce policies.",
]

async def seed_mock_kb():
    """Seeds the mock database if empty."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(KnowledgeBase).limit(1))
        if result.scalars().first():
            return # Already seeded

        logger.info("Seeding Mock Knowledge Base...")
        bge_model = lazy_loader.get_sentence_transformer("BAAI/bge-m3")
        if not bge_model:
            return

        for idx, text in enumerate(MOCK_DATA):
            emb = bge_model.encode(text, normalize_embeddings=True).tolist()
            kb_entry = KnowledgeBase(
                document_id=f"doc_{idx}",
                chunk_text=text,
                embedding=emb
            )
            session.add(kb_entry)
        
        await session.commit()
        # lazy_loader.unload("BAAI/bge-m3") # Keep it loaded if needed often

