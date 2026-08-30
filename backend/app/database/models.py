from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    api_key_hash = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class RequestLog(Base):
    __tablename__ = "requests"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    model = Column(String)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    latency_ms = Column(Integer)
    cache_hit = Column(Boolean, default=False)
    
    # Phase 2 metrics
    complexity_score = Column(Float, nullable=True)
    compression_ratio = Column(Float, nullable=True)
    routing_tier = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    events = relationship("RequestEvent", back_populates="request")
    policy_decisions = relationship("PolicyDecision", back_populates="request")

class RequestEvent(Base):
    __tablename__ = "request_events"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id = Column(String, ForeignKey("requests.id"))
    event_type = Column(String)
    payload = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    request = relationship("RequestLog", back_populates="events")

class PolicyDecision(Base):
    __tablename__ = "policy_decisions"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id = Column(String, ForeignKey("requests.id"))
    decision = Column(String) # ALLOW, WARNING, REDACT, REGENERATE, BLOCK, HUMAN_REVIEW
    reason = Column(String)
    policy_version = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    request = relationship("RequestLog", back_populates="policy_decisions")

class ModelVersion(Base):
    __tablename__ = "model_versions"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_name = Column(String, unique=True, index=True)
    version = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class CacheMetadata(Base):
    __tablename__ = "cache_metadata"
    hash_key = Column(String, primary_key=True, index=True)
    request_id = Column(String, ForeignKey("requests.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    hits = Column(Integer, default=0)

class SemanticCache(Base):
    __tablename__ = "semantic_cache"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    prompt_hash = Column(String, index=True) # Checksum or fast lookup
    prompt_embedding = Column(Vector(1024)) # BGE-M3 generates 1024-d embeddings
    model = Column(String, index=True)
    policy_version = Column(String)
    response = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    hits = Column(Integer, default=0)

class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(String, index=True)
    chunk_text = Column(String)
    embedding = Column(Vector(1024)) # BGE-M3
    created_at = Column(DateTime, default=datetime.utcnow)

class VerificationLog(Base):
    __tablename__ = "verification_logs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id = Column(String, ForeignKey("requests.id"))
    claim_text = Column(String)
    evidence_text = Column(String, nullable=True)
    nli_result = Column(String) # SUPPORTED, UNSUPPORTED, CONTRADICTED
    nli_score = Column(Float)
    regeneration_attempt = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    request = relationship("RequestLog")

