import json
import time
import asyncio
import httpx
import re
import os

async def query_controlplane(client: httpx.AsyncClient, query: str):
    start = time.time()
    try:
        res = await client.post(
            "http://localhost:8000/v1/chat/completions",
            json={
                "model": "qwen3:1.7b",
                "messages": [{"role": "user", "content": query}],
                "stream": False,
                "temperature": 0.0
            },
            timeout=600.0,
            headers={"Authorization": "Bearer 4266b9d7-6eaf-46d2-9001-5e69aaca75163746a3cc-ec78-4493-8c63-b180de5de5a9"}
        )
        latency = time.time() - start
        
        if res.status_code != 200:
            return {"error": res.text}, latency
            
        return res.json(), latency
    except Exception as e:
        return {"error": str(e)}, time.time() - start

async def evaluate_response(client: httpx.AsyncClient, query: str, ai_response: str, expected: str, should_escalate: bool):
    prompt = f"""
Evaluate the following customer service interaction.
User Query: "{query}"
AI Response: "{ai_response}"
Expected Behavior: "{expected}"
Should Escalate: {should_escalate}

Determine if the AI Response is:
1. correct (true/false)
2. relevant (true/false)
3. complete (true/false)
4. hallucination (true/false - did it invent false facts, fake tracking numbers, etc?)
5. appropriate_escalation (true/false - did it escalate if required, or not escalate if not required?)

Output ONLY a valid JSON object with boolean values. Do not output anything else.
Example: {{"correct": true, "relevant": true, "complete": false, "hallucination": false, "appropriate_escalation": true}}
"""
    try:
        res = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen3:1.7b",
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.0, "num_predict": 100}
            },
            timeout=600.0
        )
        if res.status_code == 200:
            text = res.json().get("response", "{}")
            return json.loads(text)
    except Exception as e:
        pass
    
    return {
        "correct": False,
        "relevant": False,
        "complete": False,
        "hallucination": False,
        "appropriate_escalation": False
    }

async def process_item(client, item, semaphore, fp):
    async with semaphore:
        cp_res, latency = await query_controlplane(client, item["query"])
        
        if "error" in cp_res:
            ai_text = "ERROR: " + cp_res["error"]
            num_turns = 0
            resolved = False
        else:
            ai_text = cp_res.get("message", {}).get("content", "")
            if not ai_text:
                ai_text = str(cp_res)
            num_turns = 1
            resolved = "I CANNOT ANSWER THAT" not in ai_text
            
        eval_metrics = await evaluate_response(
            client, 
            item["query"], 
            ai_text, 
            item["expected_answer"], 
            item["should_escalate"]
        )
        
        result = {
            "conversation_id": item["conversation_id"],
            "category": item["category"],
            "difficulty": item["difficulty"],
            "query": item["query"],
            "response": ai_text,
            "expected_response": item["expected_answer"],
            "correct": eval_metrics.get("correct", False),
            "relevant": eval_metrics.get("relevant", False),
            "complete": eval_metrics.get("complete", False),
            "hallucination": eval_metrics.get("hallucination", False),
            "appropriate_escalation": eval_metrics.get("appropriate_escalation", False),
            "response_time": latency,
            "num_turns": num_turns,
            "resolved": resolved and eval_metrics.get("correct", False)
        }
        
        # Write to JSONL
        fp.write(json.dumps(result) + "\n")
        fp.flush()
        return result

async def main():
    with open('benchmark/dataset.json', 'r') as f:
        dataset = json.load(f)
        
    # Read already processed ids
    processed_ids = set()
    if os.path.exists('benchmark/results.jsonl'):
        with open('benchmark/results.jsonl', 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        processed_ids.add(json.loads(line)["conversation_id"])
                    except:
                        pass
                        
    remaining_dataset = [item for item in dataset if item["conversation_id"] not in processed_ids]
    print(f"Total: {len(dataset)}, Already processed: {len(processed_ids)}, Remaining: {len(remaining_dataset)}")
        
    semaphore = asyncio.Semaphore(3) # higher concurrency
    
    with open('benchmark/results.jsonl', 'a') as fp:
        async with httpx.AsyncClient() as client:
            tasks = [process_item(client, item, semaphore, fp) for item in remaining_dataset]
            completed = 0
            for task in asyncio.as_completed(tasks):
                await task
                completed += 1
                if completed % 10 == 0:
                    print(f"Processed {completed}/{len(remaining_dataset)}...", flush=True)

    # At the end, read all from jsonl and write to results.json
    all_results = []
    with open('benchmark/results.jsonl', 'r') as f:
        for line in f:
            if line.strip():
                all_results.append(json.loads(line))
                
    with open('benchmark/results.json', 'w') as f:
        json.dump(all_results, f, indent=4)
        
    print("Done. Saved to benchmark/results.json")

if __name__ == "__main__":
    asyncio.run(main())
