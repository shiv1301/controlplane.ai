import json
import uuid
import time
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.gateway.auth import verify_api_key
from app.config import settings
from app.routing.router import router as llm_router
from app.policy.engine import policy_engine
from app.cache.exact_cache import generate_cache_key, get_cached_response, set_cached_response
from app.cache.semantic_cache import semantic_cache_manager
from app.input.detectors import pii_detector, toxicity_detector, injection_detector, harm_intent_detector
from app.input.scoring import complexity_scorer, budget_manager
from app.input.compression import compressor
from app.verification.pipeline import verification_pipeline
from app.audit.redis_queue import audit_queue
from app.observability.metrics import REQUEST_COUNT, REQUEST_LATENCY, CACHE_HITS, MODEL_ROUTING, VERIFICATION_RESULTS, REGENERATION_ATTEMPTS, POLICY_DECISIONS
from app.observability.logging import logger

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = Field(default_factory=lambda: settings.default_model)
    messages: List[ChatMessage]
    temperature: float = 1.0
    max_tokens: Optional[int] = None
    stream: bool = False

from app.gateway.rate_limiter import rate_limiter

@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    user_id: str = Depends(verify_api_key)
):
    start_time = time.time()
    await rate_limiter.check_rate_limit(user_id)
    
    REQUEST_COUNT.labels(method='POST', endpoint='/v1/chat/completions', status='200').inc()
    request_id = f"req-{uuid.uuid4().hex}"
    prompt = " ".join([m.content for m in request.messages])

    # 1. Input Inspection
    import asyncio
    inj_res, tox_res, pii_res, harm_res = await asyncio.gather(
        asyncio.to_thread(injection_detector.detect, prompt),
        asyncio.to_thread(toxicity_detector.detect, prompt),
        asyncio.to_thread(pii_detector.detect, prompt),
        asyncio.to_thread(harm_intent_detector.detect, prompt),
    )

    is_critical_risk = False
    if inj_res.get("detected") or tox_res.get("detected"):
        is_critical_risk = True
        
    if harm_res.get("detected"):
        is_critical_risk = True
        if harm_res.get("details") in ["self harm", "suicide"]:
            await audit_queue.publish_for_review(request_id, {"text": prompt, "reason": "semantic_self_harm_detected"})

    harmful_keywords = ["bomb", "kill", "murder", "terrorist", "hack", "attack"]
    if any(kw in prompt.lower() for kw in harmful_keywords):
        is_critical_risk = True

    self_harm_keywords = ["suicide", "kill myself", "end my life", "self harm", "cut myself", "rope around my neck", "hang myself"]
    if any(kw in prompt.lower() for kw in self_harm_keywords):
        await audit_queue.publish_for_review(request_id, {"text": prompt, "reason": "self_harm_detected"})
        is_critical_risk = True

    if pii_res.get("detected"):
        prompt = pii_res["text"]
        if request.messages:
            request.messages[-1].content = prompt

    # 2. Complexity & Budget
    complexity = await complexity_scorer.score(prompt)
    if not budget_manager.check_budget(user_id, len(prompt), complexity):
        REQUEST_LATENCY.labels(endpoint='/v1/chat/completions').observe(time.time() - start_time)
        raise HTTPException(status_code=429, detail="Token budget exceeded for this complexity")

    # Risk level determination based on continuous risk score
    max_risk_score = max([
        inj_res.get("score", 0.0), 
        tox_res.get("score", 0.0), 
        harm_res.get("score", 0.0)
    ])
    
    if is_critical_risk or max_risk_score >= 0.75:
        risk_level = "CRITICAL"
    elif max_risk_score >= 0.50:
        risk_level = "HIGH"
    elif max_risk_score >= 0.25:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
        
    # Complexity tier determination based on continuous complexity score
    if complexity < 0.25:
        complexity_tier = "LOW"
    elif complexity < 0.50:
        complexity_tier = "MEDIUM"
    elif complexity < 0.75:
        complexity_tier = "HIGH"
    else:
        complexity_tier = "NO LIMIT"
    # 3. Exact Cache
    cache_key = generate_cache_key(
        prompt=prompt,
        model=request.model,
        system_prompt_version="v1",
        temperature=request.temperature,
        policy_version="v1"
    )
    if not is_critical_risk:
        cached_data = await get_cached_response(cache_key)
        if cached_data:
            CACHE_HITS.labels(cache_type='exact').inc()
            REQUEST_LATENCY.labels(endpoint='/v1/chat/completions').observe(time.time() - start_time)
            if request.stream:
                async def cache_streamer():
                    msg = cached_data.get("message", {}).get("content", "")
                    words = msg.split(" ")
                    for w in words:
                        yield {"event": "message", "data": json.dumps({"model": cached_data.get("model", ""), "message": {"role": "assistant", "content": w + " "}, "done": False})}
                        await asyncio.sleep(0.01)
                    yield {"event": "message", "data": json.dumps({"model": cached_data.get("model", ""), "message": {"role": "assistant", "content": ""}, "done": True})}
                    
                    yield {"event": "message", "data": json.dumps({
                        "is_latency_stats": True,
                        "stats": {
                            "preprocessing": (time.time() - start_time) * 1000,
                            "generation": 0.0,
                            "verification": 0.0,
                            "total": (time.time() - start_time) * 1000
                        },
                        "complexity": complexity,
                        "risk_level": risk_level
                    })}
                    yield {"event": "message", "data": "[DONE]"}
                return EventSourceResponse(cache_streamer())
            
            cached_data["latency_stats"] = {
                "preprocessing": (time.time() - start_time) * 1000,
                "generation": 0.0,
                "verification": 0.0,
                "total": (time.time() - start_time) * 1000
            }
            cached_data["complexity"] = complexity
            cached_data["risk_level"] = risk_level
            cached_data["controlplane_metrics"] = {
                "cache_hit": True,
                "cache_type": "exact",
                "model_routed": cached_data.get("model", ""),
                "risk_blocked": False,
                "pii_redacted": False
            }
            return cached_data

        # 4. Semantic Cache
        semantic_cached = await semantic_cache_manager.get_semantic_cache(
            prompt=prompt, model=request.model, policy_version="v1"
        )
        if semantic_cached:
            CACHE_HITS.labels(cache_type='semantic').inc()
            REQUEST_LATENCY.labels(endpoint='/v1/chat/completions').observe(time.time() - start_time)
            if request.stream:
                async def cache_streamer():
                    msg = semantic_cached.get("message", {}).get("content", "")
                    words = msg.split(" ")
                    for w in words:
                        yield {"event": "message", "data": json.dumps({"model": semantic_cached.get("model", ""), "message": {"role": "assistant", "content": w + " "}, "done": False})}
                        await asyncio.sleep(0.01)
                    yield {"event": "message", "data": json.dumps({"model": semantic_cached.get("model", ""), "message": {"role": "assistant", "content": ""}, "done": True})}
                    
                    yield {"event": "message", "data": json.dumps({
                        "is_latency_stats": True,
                        "stats": {
                            "preprocessing": (time.time() - start_time) * 1000,
                            "generation": 0.0,

                            "verification": 0.0,
                            "total": (time.time() - start_time) * 1000
                        },
                        "complexity": complexity,
                        "risk_level": risk_level
                    })}
                    yield {"event": "message", "data": "[DONE]"}
                return EventSourceResponse(cache_streamer())
            
            semantic_cached["latency_stats"] = {
                "preprocessing": (time.time() - start_time) * 1000,
                "generation": 0.0,
                "verification": 0.0,
                "total": (time.time() - start_time) * 1000
            }
            semantic_cached["complexity"] = complexity
            semantic_cached["risk_level"] = risk_level
            semantic_cached["controlplane_metrics"] = {
                "cache_hit": True,
                "cache_type": "semantic",
                "model_routed": semantic_cached.get("model", ""),
                "risk_blocked": False,
                "pii_redacted": False
            }
            return semantic_cached

    # 5. Compression (skip for streaming — compression calls LLM synchronously, adding huge latency)
    if not request.stream:
        compressed_prompt = await compressor.compress(prompt)
        if request.messages:
            request.messages[-1].content = compressed_prompt

    # 6. Routing
    tier, target_model = llm_router.route_by_complexity(complexity)
    MODEL_ROUTING.labels(model_name=target_model).inc()
    provider = llm_router.get_provider_for_model(target_model)

    # Set Max Tokens
    max_tokens = budget_manager.get_max_tokens_for_complexity(complexity)
    if max_tokens is not None:
        if request.max_tokens is not None:
            request.max_tokens = min(request.max_tokens, max_tokens)
        else:
            request.max_tokens = max_tokens

    # Helper to cache streamed response
    async def cache_stream_result(final_text: str):
        full_resp = {
            "model": target_model,
            "message": {"role": "assistant", "content": final_text},
            "done": True
        }
        await set_cached_response(cache_key, full_resp)
        # We can also populate semantic cache here! But wait, semantic cache blocks.
        # Let's run semantic cache population async.
        asyncio.create_task(semantic_cache_manager.set_semantic_cache(prompt, full_resp, target_model, "v1"))

    prep_end_time = time.time()
    from app.observability.metrics import PREPROCESSING_LATENCY, GENERATION_LATENCY, VERIFICATION_LATENCY
    PREPROCESSING_LATENCY.labels(endpoint='/v1/chat/completions').observe(prep_end_time - start_time)

    # 7. Execution & Risk-Adaptive Streaming
    if request.stream:
        from app.observability.metrics import RISK_LEVELS
        RISK_LEVELS.labels(risk_level=risk_level).inc()
            
        async def stream_generator():
            if risk_level == "CRITICAL":
                msg = "I CANNOT ANSWER THAT"
                words = msg.split()
                for w in words:
                    yield {"event": "message", "data": json.dumps({"model": target_model, "message": {"role": "assistant", "content": w + " "}, "done": False})}
                    await asyncio.sleep(0.05)
                yield {"event": "message", "data": json.dumps({"model": target_model, "message": {"role": "assistant", "content": ""}, "done": True})}
                
                total_time = time.time() - start_time
                GENERATION_LATENCY.labels(endpoint='/v1/chat/completions').observe(0.0)
                VERIFICATION_LATENCY.labels(endpoint='/v1/chat/completions').observe(0.0)
                REQUEST_LATENCY.labels(endpoint='/v1/chat/completions').observe(total_time)
                
                yield {"event": "message", "data": json.dumps({
                    "is_latency_stats": True,
                    "stats": {
                        "preprocessing": (prep_end_time - start_time) * 1000,
                        "generation": 0.0,
                        "verification": 0.0,
                        "total": total_time * 1000
                    },
                    "complexity": complexity,
                    "risk_level": risk_level
                })}
                return

            max_attempts = 3
            attempt = 0
            current_messages = [m.model_dump() for m in request.messages]
            gen_time_total = 0.0
            verif_time_total = 0.0
            
            while attempt < max_attempts:
                attempt += 1
                try:
                    stream = provider.generate_stream(
                        messages=current_messages,
                        model=target_model,
                        temperature=request.temperature,
                        max_tokens=request.max_tokens
                    )
                    
                    if risk_level == "LOW":
                        full_text = ""
                        while True:
                            t0 = time.time()
                            try:
                                chunk = await stream.__anext__()
                            except StopAsyncIteration:
                                break
                            gen_time_total += (time.time() - t0)
                            
                            content = chunk.get("message", {}).get("content", "")
                            full_text += content
                            yield {"event": "message", "data": json.dumps(chunk)}
                            if chunk.get("done", False):
                                break
                                
                        if full_text:
                            t_v0 = time.time()
                            try:
                                tox = await asyncio.to_thread(toxicity_detector.detect, full_text)
                                if tox.get("detected"):
                                    yield {"event": "error", "data": json.dumps({"error": "Warning: toxic content detected in response"})}
                            except Exception:
                                pass
                            verif_time_total += (time.time() - t_v0)
                            await cache_stream_result(full_text)
                        break

                    elif risk_level == "MEDIUM":
                        buffer = []
                        buffer_text = ""
                        full_text = ""
                        while True:
                            t0 = time.time()
                            try:
                                chunk = await stream.__anext__()
                            except StopAsyncIteration:
                                break
                            gen_time_total += (time.time() - t0)
                            
                            content = chunk.get("message", {}).get("content", "")
                            buffer.append(chunk)
                            buffer_text += content
                            is_done = chunk.get("done", False)
                            
                            if is_done or len(buffer) >= 10:
                                t_v0 = time.time()
                                out_tox, out_pii = await asyncio.gather(
                                    asyncio.to_thread(toxicity_detector.detect, buffer_text),
                                    asyncio.to_thread(pii_detector.detect, buffer_text),
                                )
                                verif_time_total += (time.time() - t_v0)
                                
                                if out_tox.get("detected"):
                                    yield {"event": "error", "data": json.dumps({"error": "Toxic output blocked"})}
                                    return
                                if out_pii.get("detected"):
                                    redacted_chunk = buffer[-1].copy()
                                    redacted_chunk["message"]["content"] = out_pii["text"]
                                    buffer = [redacted_chunk]
                                    buffer_text = out_pii["text"]
                                for b in buffer:
                                    full_text += b.get("message", {}).get("content", "")
                                    yield {"event": "message", "data": json.dumps(b)}
                                buffer = []
                                buffer_text = ""
                                if is_done:
                                    break
                        if full_text:
                            await cache_stream_result(full_text)
                        break

                    else:
                        buffer = []
                        buffer_text = ""
                        full_text = ""
                        needs_regeneration = False
                        
                        while True:
                            t0 = time.time()
                            try:
                                chunk = await stream.__anext__()
                            except StopAsyncIteration:
                                break
                            gen_time_total += (time.time() - t0)
                            
                            content = chunk.get("message", {}).get("content", "")
                            buffer.append(chunk)
                            buffer_text += content
                            
                            if chunk.get("done", False):
                                t_v0 = time.time()
                                out_tox, out_pii = await asyncio.gather(
                                    asyncio.to_thread(toxicity_detector.detect, buffer_text),
                                    asyncio.to_thread(pii_detector.detect, buffer_text),
                                )
                                if out_tox.get("detected"):
                                    yield {"event": "error", "data": json.dumps({"error": "Toxic output blocked"})}
                                    return
                                if out_pii.get("detected"):
                                    redacted_chunk = buffer[-1].copy()
                                    redacted_chunk["message"]["content"] = out_pii["text"]
                                    buffer = [redacted_chunk]
                                    buffer_text = out_pii["text"]
                                    
                                v_res = await verification_pipeline.verify_text(request_id, buffer_text, attempt)
                                verif_time_total += (time.time() - t_v0)
                                
                                if not v_res["is_valid"]:
                                    if attempt < max_attempts:
                                        needs_regeneration = True
                                        REGENERATION_ATTEMPTS.inc()
                                        contra = ", ".join(v_res["contradicted_claims"])
                                        current_messages.append({"role": "assistant", "content": buffer_text})
                                        current_messages.append({"role": "user", "content": f"Contradicted claims: {contra}. Regenerate."})
                                        break
                                    else:
                                        await audit_queue.publish_for_review(request_id, {"text": buffer_text, "v_res": v_res})
                                if not needs_regeneration:
                                    for b in buffer:
                                        full_text += b.get("message", {}).get("content", "")
                                        yield {"event": "message", "data": json.dumps(b)}
                        if needs_regeneration:
                            continue
                        if full_text:
                            await cache_stream_result(full_text)
                        break

                except Exception as e:
                    yield {"event": "error", "data": json.dumps({"error": str(e)})}
                    break
            
            GENERATION_LATENCY.labels(endpoint='/v1/chat/completions').observe(gen_time_total)
            VERIFICATION_LATENCY.labels(endpoint='/v1/chat/completions').observe(verif_time_total)
            total_time = time.time() - start_time
            REQUEST_LATENCY.labels(endpoint='/v1/chat/completions').observe(total_time)
            
            yield {"event": "message", "data": json.dumps({
                "is_latency_stats": True,
                "stats": {
                    "preprocessing": (prep_end_time - start_time) * 1000,
                    "generation": gen_time_total * 1000,
                    "verification": verif_time_total * 1000,
                    "total": total_time * 1000
                },
                "complexity": complexity,
                "risk_level": risk_level
            })}
                
        return EventSourceResponse(stream_generator())
    
    else:
        # Non-streaming
        from app.observability.metrics import RISK_LEVELS
        RISK_LEVELS.labels(risk_level=risk_level).inc()
        if is_critical_risk:
            total_time = time.time() - start_time
            GENERATION_LATENCY.labels(endpoint='/v1/chat/completions').observe(0.0)
            VERIFICATION_LATENCY.labels(endpoint='/v1/chat/completions').observe(0.0)
            REQUEST_LATENCY.labels(endpoint='/v1/chat/completions').observe(total_time)
            return {
                "model": target_model,
                "message": {"role": "assistant", "content": "I CANNOT ANSWER THAT"},
                "done": True,
                "latency_stats": {
                    "preprocessing": (prep_end_time - start_time) * 1000,
                    "generation": 0.0,
                    "verification": 0.0,
                    "total": total_time * 1000
                },
                "complexity": complexity,
                "risk_level": risk_level,
                "controlplane_metrics": {
                    "cache_hit": False,
                    "cache_type": None,
                    "model_routed": target_model,
                    "risk_blocked": True,
                    "pii_redacted": False
                }
            }

        gen_start = time.time()
        response = await provider.generate(
            messages=[m.model_dump() for m in request.messages],
            model=target_model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        gen_time = time.time() - gen_start
        
        response_text = response.get("message", {}).get("content", "")
        
        verif_start = time.time()
        out_tox = toxicity_detector.detect(response_text)
        if out_tox.get("detected"):
            REQUEST_LATENCY.labels(endpoint='/v1/chat/completions').observe(time.time() - start_time)
            raise HTTPException(status_code=403, detail="Toxic response blocked")
            
        out_pii = pii_detector.detect(response_text)
        if out_pii.get("detected"):
            response["message"]["content"] = out_pii["text"]
            
        verif_time = time.time() - verif_start
            
        await set_cached_response(cache_key, response)
        await semantic_cache_manager.set_semantic_cache(prompt, response, target_model, "v1")
        
        total_time = time.time() - start_time
        GENERATION_LATENCY.labels(endpoint='/v1/chat/completions').observe(gen_time)
        VERIFICATION_LATENCY.labels(endpoint='/v1/chat/completions').observe(verif_time)
        REQUEST_LATENCY.labels(endpoint='/v1/chat/completions').observe(total_time)
        
        response["latency_stats"] = {
            "preprocessing": (prep_end_time - start_time) * 1000,
            "generation": gen_time * 1000,
            "verification": verif_time * 1000,
            "total": total_time * 1000
        }
        response["complexity"] = complexity
        response["risk_level"] = risk_level
        response["controlplane_metrics"] = {
            "cache_hit": False,
            "cache_type": None,
            "model_routed": target_model,
            "risk_blocked": False,
            "pii_redacted": out_pii.get("detected", False)
        }
        
        return response


