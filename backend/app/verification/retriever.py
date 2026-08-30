from app.database.session import AsyncSessionLocal
from app.database.models import KnowledgeBase
from sqlalchemy import select
from app.verification.lazy_models import lazy_loader
from rank_bm25 import BM25Okapi
import numpy as np

class Retriever:
    async def retrieve(self, query: str, top_k: int = 3) -> list[str]:
        # 1. BGE-M3 Dense Retrieval (pgvector)
        bge_model = lazy_loader.get_sentence_transformer("BAAI/bge-m3")
        if not bge_model:
            return []
            
        query_emb = bge_model.encode(query, normalize_embeddings=True).tolist()
        
        dense_results = []
        all_docs = []
        async with AsyncSessionLocal() as session:
            # Get Dense Top 5
            stmt = select(KnowledgeBase).order_by(
                KnowledgeBase.embedding.cosine_distance(query_emb)
            ).limit(5)
            result = await session.execute(stmt)
            dense_results = [r.chunk_text for r in result.scalars().all()]
            
            # For BM25, fetch all mock docs (in real-world, we'd use pg_trgm or tsvector)
            result_all = await session.execute(select(KnowledgeBase.chunk_text))
            all_docs = [r[0] for r in result_all.all()]
            
        # 2. BM25 Sparse Retrieval
        if not all_docs:
            return []
            
        tokenized_docs = [doc.lower().split() for doc in all_docs]
        bm25 = BM25Okapi(tokenized_docs)
        tokenized_query = query.lower().split()
        bm25_scores = bm25.get_scores(tokenized_query)
        
        # Get Top 5 BM25
        top_n = np.argsort(bm25_scores)[::-1][:5]
        sparse_results = [all_docs[i] for i in top_n]
        
        # 3. Combine & Deduplicate
        combined_pool = list(set(dense_results + sparse_results))
        if not combined_pool:
            return []
            
        # 4. Reranking using BGE-Reranker-v2-m3
        reranker = lazy_loader.get_cross_encoder("BAAI/bge-reranker-v2-m3")
        if not reranker:
            return combined_pool[:top_k]
            
        # Reranker takes pairs: [[query, doc], [query, doc], ...]
        pairs = [[query, doc] for doc in combined_pool]
        scores = reranker.predict(pairs)
        
        # Sort docs by score
        scored_docs = list(zip(combined_pool, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Unload reranker (lazy logic allows freeing)
        lazy_loader.unload("BAAI/bge-reranker-v2-m3")
        
        return [doc for doc, score in scored_docs[:top_k]]

retriever = Retriever()
