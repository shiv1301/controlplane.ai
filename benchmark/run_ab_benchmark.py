import json
import time
import asyncio
import httpx
import os

async def query_baseline(client: httpx.AsyncClient, query: str):
    start = time.time()
    try:
        res = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen3:1.7b",
                "prompt": query,
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 300}
            },
            timeout=120.0
        )
        latency = time.time() - start
        
        if res.status_code != 200:
            return {"error": res.text}, latency
            
        data = res.json()
        
        return {
            "response": data.get("response", ""),
            "input_tokens": data.get("prompt_eval_count", 0),
            "output_tokens": data.get("eval_count", 0)
        }, latency
    except Exception as e:
        return {"error": str(e)}, time.time() - start

async def query_controlplane(client: httpx.AsyncClient, query: str):
    start = time.time()
    try:
        res = await client.post(
            "http://localhost:8000/v1/chat/completions",
            json={
                "model": "qwen3:1.7b",
                "messages": [{"role": "user", "content": query}],
                "stream": False,
                "temperature": 0.0,
                "max_tokens": 300
            },
            timeout=120.0,
            headers={"Authorization": "Bearer 4266b9d7-6eaf-46d2-9001-5e69aaca75163746a3cc-ec78-4493-8c63-b180de5de5a9"}
        )
        latency = time.time() - start
        
        if res.status_code != 200:
            return {"error": res.text}, latency
            
        return res.json(), latency
    except Exception as e:
        return {"error": str(e)}, time.time() - start

async def evaluate_response(client: httpx.AsyncClient, query: str, ai_response: str):
    prompt = f"""
Evaluate the following customer service interaction.
User Query: "{query}"
AI Response: "{ai_response}"

Determine if the AI Response contains hallucinations (invented facts, fake tracking numbers, policies not in the query).
Output ONLY a valid JSON object with boolean values. Do not output anything else.
Example: {{"hallucination": false}}
"""
    try:
        res = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen3:1.7b",
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.0, "num_predict": 20}
            },
            timeout=120.0
        )
        if res.status_code == 200:
            return json.loads(res.json().get("response", "{}"))
    except Exception:
        pass
    
    return {"hallucination": False}

async def process_item(client, item, semaphore, fp):
    async with semaphore:
        # 1. Baseline
        base_res, base_latency = await query_baseline(client, item["query"])
        base_text = base_res.get("response", "ERROR") if isinstance(base_res, dict) else "ERROR"
        base_in_tok = base_res.get("input_tokens", len(item["query"]) // 4) if isinstance(base_res, dict) else 0
        base_out_tok = base_res.get("output_tokens", 0) if isinstance(base_res, dict) else 0
        
        # 2. ControlPlane
        cp_res, cp_latency = await query_controlplane(client, item["query"])
        if "error" in cp_res:
            cp_text = "ERROR: " + cp_res["error"]
            cp_metrics = {}
        else:
            cp_text = cp_res.get("message", {}).get("content", "")
            cp_metrics = cp_res.get("controlplane_metrics", {})
            
        cp_in_tok = cp_res.get("usage", {}).get("prompt_tokens", base_in_tok)
        cp_out_tok = cp_res.get("usage", {}).get("completion_tokens", 0)
        
        # 3. Evaluate Hallucinations
        base_eval = await evaluate_response(client, item["query"], base_text)
        cp_eval = await evaluate_response(client, item["query"], cp_text)
        
        result = {
            "conversation_id": item["conversation_id"],
            "category": item["category"],
            "query": item["query"],
            
            "baseline_latency": base_latency,
            "baseline_response": base_text,
            "baseline_in_tokens": base_in_tok,
            "baseline_out_tokens": base_out_tok,
            "baseline_hallucination": base_eval.get("hallucination", False),
            
            "cp_latency": cp_latency,
            "cp_response": cp_text,
            "cp_in_tokens": cp_in_tok,
            "cp_out_tokens": cp_out_tok,
            "cp_hallucination": cp_eval.get("hallucination", False),
            
            "cp_cache_hit": cp_metrics.get("cache_hit", False),
            "cp_cache_type": cp_metrics.get("cache_type", None),
            "cp_model_routed": cp_metrics.get("model_routed", "unknown"),
            "cp_risk_blocked": cp_metrics.get("risk_blocked", False),
            "cp_pii_redacted": cp_metrics.get("pii_redacted", False)
        }
        
        fp.write(json.dumps(result) + "\n")
        fp.flush()
        return result

async def main():
    with open('benchmark/business_dataset.json', 'r') as f:
        dataset = json.load(f)
        
    processed_ids = set()
    if os.path.exists('benchmark/business_results.jsonl'):
        with open('benchmark/business_results.jsonl', 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        processed_ids.add(json.loads(line)["conversation_id"])
                    except:
                        pass
                        
    remaining_dataset = [item for item in dataset if item["conversation_id"] not in processed_ids]
    
    total_to_process = 15 - len(processed_ids)
    if total_to_process > 0:
        remaining_dataset = remaining_dataset[:total_to_process]
    else:
        remaining_dataset = []
        
    print(f"Total: {len(dataset)}, Already processed: {len(processed_ids)}, Remaining to hit 15 limit: {len(remaining_dataset)}")
        
    # Concurrency 3 to keep Ollama responsive
    semaphore = asyncio.Semaphore(3)
    
    with open('benchmark/business_results.jsonl', 'a') as fp:
        async with httpx.AsyncClient() as client:
            tasks = [process_item(client, item, semaphore, fp) for item in remaining_dataset]
            completed = 0
            for task in asyncio.as_completed(tasks):
                await task
                completed += 1
                if completed % 10 == 0:
                    print(f"Processed {completed}/{len(remaining_dataset)}...", flush=True)

    print("Done generating JSONL results.")

if __name__ == "__main__":
    asyncio.run(main())

