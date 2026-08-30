# ControlPlane.ai Project Summary

## Core Architecture
ControlPlane.ai is a real-time reverse proxy and API gateway designed to sit between customer-facing AI applications and underlying LLMs. It focuses on optimizing Cost, Responsibility, and Performance.

### 1. Cost & Efficiency
- **Semantic Caching**: Implemented using the `BAAI/bge-m3` embedding model. It vectorizes incoming user prompts and compares them against cached prompts using Cosine Similarity. If the similarity exceeds a threshold (e.g., 0.90), it serves the cached response instantly without invoking the LLM, saving both time and money.
- **Intelligent Model Routing**: Uses a Zero-Shot Classifier (`facebook/bart-large-mnli`) to dynamically assess the complexity of an incoming prompt. Simple prompts (e.g., "Where is my order?") are routed to cheaper, smaller models, while complex multi-step prompts are routed to premium, larger models.
- **Dynamic Token Budgeting**: The router assigns a strict maximum output token limit based on the complexity tier, preventing runaway generation costs for simple queries.

### 2. Responsibility & Safety
- **Real-Time PII Redaction**: Uses the `Microsoft Presidio` analyzer (via NLP models) to identify and redact Personally Identifiable Information (PII) such as credit cards, phone numbers, and SSNs from the model's output *while* it is streaming.
- **Prompt Injection Detection**: Uses the `ProtectAI/deberta-v3-base-injection` model to detect malicious jailbreaks and prompt injections. If a critical risk is detected, the API drops the request and instantly returns "I CANNOT ANSWER THAT".
- **Toxicity Filtering**: Employs `s-nlp/roberta_toxicity_classifier` to evaluate generated output. If the model attempts to emit toxic or abusive language, the gateway intercepts and blocks it.

### 3. Performance & Hallucination Prevention
- **Factual Verification (RAG)**: Integrates a cross-encoder (`cross-encoder/nli-deberta-v3-base`) to verify the factual consistency of the LLM's response against an external knowledge base or the prompt's context. 
- **Self-Healing Generation**: If a response is flagged as hallucinated or contradictory, the gateway automatically intercepts the output, appends a correction prompt, and forces the LLM to regenerate a valid response before returning it to the user.

## Technology Stack
- **Backend Framework**: FastAPI (Python)
- **Local LLM Engine**: Ollama (running `qwen3:1.7b`)
- **ML Pipeline**: HuggingFace `transformers` and `sentence-transformers`
- **Frontend**: React + Vite with Recharts for telemetry dashboards.
- **Observability**: Prometheus metrics mapped to all gateway functions.
- **Concurrency**: Asyncio for non-blocking stream interception.

