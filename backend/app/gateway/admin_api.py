from fastapi import APIRouter, Depends, HTTPException
from app.gateway.auth import verify_admin_key
from app.database.session import AsyncSessionLocal
from app.database.models import RequestLog, CacheMetadata, SemanticCache, VerificationLog
from sqlalchemy import select, func
import app.audit.redis_queue as audit_q
import json

router = APIRouter(
    prefix="/api",
    tags=["admin"],
    dependencies=[Depends(verify_admin_key)]
)

@router.get("/metrics")
async def get_metrics():
    from app.observability.metrics import (
        REQUEST_COUNT, REQUEST_LATENCY, CACHE_HITS, 
        VERIFICATION_RESULTS, RISK_LEVELS,
        PREPROCESSING_LATENCY, GENERATION_LATENCY, VERIFICATION_LATENCY
    )
    
    # Extract values from prometheus metrics
    total_reqs = sum(m._value.get() for m in REQUEST_COUNT._metrics.values()) if REQUEST_COUNT._metrics else 0
    
    # Calculate average latency from Histogram
    latency_sum = sum(m._sum.get() for m in REQUEST_LATENCY._metrics.values()) if REQUEST_LATENCY._metrics else 0
    latency_count = sum(sum(b.get() for b in m._buckets) for m in REQUEST_LATENCY._metrics.values()) if REQUEST_LATENCY._metrics else 0
    avg_latency = (latency_sum / latency_count * 1000) if latency_count > 0 else 0
    
    # Sub-latencies
    def get_avg(histogram):
        if not histogram._metrics: return 0
        l_sum = sum(m._sum.get() for m in histogram._metrics.values())
        l_count = sum(sum(b.get() for b in m._buckets) for m in histogram._metrics.values())
        return (l_sum / l_count * 1000) if l_count > 0 else 0
        
    avg_prep = get_avg(PREPROCESSING_LATENCY)
    avg_gen = get_avg(GENERATION_LATENCY)
    avg_verif = get_avg(VERIFICATION_LATENCY)
    
    total_cache_hits = sum(m._value.get() for m in CACHE_HITS._metrics.values()) if CACHE_HITS._metrics else 0
    
    verifications = {}
    if VERIFICATION_RESULTS._metrics:
        for labels, metric in VERIFICATION_RESULTS._metrics.items():
            verifications[labels[0]] = metric._value.get()
            
    risk_stats = {}
    if RISK_LEVELS._metrics:
        for labels, metric in RISK_LEVELS._metrics.items():
            risk_stats[labels[0]] = metric._value.get()

    return {
        "total_requests": total_reqs,
        "average_latency_ms": avg_latency,
        "prep_latency_ms": avg_prep,
        "gen_latency_ms": avg_gen,
        "verif_latency_ms": avg_verif,
        "cache_hits": total_cache_hits,
        "verification_stats": verifications,
        "risk_stats": risk_stats
    }

@router.get("/audit")
async def get_audit_queue():
    """Reads pending HUMAN_REVIEW items from Redis Stream."""
    try:
        # XREAD from start of stream
        messages = await audit_q.audit_queue.redis_client.xread(
            {audit_q.audit_queue.stream_name: '0-0'}, count=50
        )
        if not messages:
            return {"queue": []}
            
        stream_name, stream_msgs = messages[0]
        results = []
        for msg_id, data in stream_msgs:
            results.append({
                "message_id": msg_id,
                "request_id": data.get("request_id"),
                "payload": json.loads(data.get("payload", "{}"))
            })
        return {"queue": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/audit/{message_id}/resolve")
async def resolve_audit_item(message_id: str, action: str):
    """Acknowledge and delete item from queue."""
    try:
        await audit_q.audit_queue.redis_client.xdel(audit_q.audit_queue.stream_name, message_id)
        return {"status": "resolved", "action": action}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
