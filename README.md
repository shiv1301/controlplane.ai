# ControlPlane.ai

ControlPlane.ai is a production-grade, real-time reverse proxy and API gateway designed to sit between customer-facing AI applications and underlying LLMs. It acts as an **inline middleware layer** that protects enterprises from the overlapping risks of deploying Generative AI: skyrocketing inference costs, toxic behavior, prompt injections, data leaks, and unpredictable latency.

By proxying all LLM traffic through ControlPlane.ai, organizations can achieve up to **99.9% cost reduction**, enforce **100% prompt injection detection**, and maintain strict observability over every interaction without modifying their downstream models.

---

## 🏗 Architecture & Features

ControlPlane.ai operates as a fast, modular monolith built on **FastAPI (Python)**, backed by **PostgreSQL/pgvector** and **Redis**. It intercepts incoming requests, analyzes them, edits or blocks them based on security policies, dynamically routes them to the most efficient LLM, and verifies the output.

### 1. Pre-Response Gate (Responsibility & Safety)
- **Toxicity Filtering:** Employs zero-shot classifiers (`s-nlp/roberta_toxicity_classifier`) to instantly block toxic, abusive, or self-harm prompts with hardcoded responses (e.g., "I CANNOT ANSWER THAT").
- **Prompt Injection Detection:** Uses the `ProtectAI/deberta-v3-base-injection` model to detect malicious jailbreaks and bypasses, dropping the request before it reaches the LLM API.
- **PII Redaction:** Uses `Microsoft Presidio` (with `en_core_web_sm`) to detect and redact sensitive Personally Identifiable Information (SSNs, Credit Cards) in real-time, preventing data leaks to third-party models.

### 2. Latency Budgets & Cost Optimization
- **Semantic Cache:** Uses the `BAAI/bge-m3` embedding model stored in PostgreSQL pgvector. When a user asks a question with high cosine similarity to a previously answered question (e.g., "Where is my order?" vs "Can I track my package?"), the system bypasses the LLM and instantly returns the cached answer. This results in 0 latency and 0 token cost.
- **Intelligent Routing:** A Zero-Shot Classifier (`facebook/bart-large-mnli`) scores the complexity of an incoming prompt. Simple tasks are routed to cheaper, smaller models (with strict token budgets), while complex multi-step prompts are routed to larger models.

### 3. Factual Verification (RAG)
- Uses a cross-encoder (`cross-encoder/nli-deberta-v3-base`) to verify the factual consistency of the LLM's response against an external knowledge base.
- If a response is hallucinated, the gateway automatically intercepts the stream, appends a correction prompt, and forces the LLM to regenerate a valid response (Self-Healing).

---

## 📦 Assets & Models Used

ControlPlane.ai utilizes a strict local-first, zero-trust AI architecture. The following models are leveraged:

1. **Local Foundation Model:** `qwen3:1.7b` (Served via Ollama)
2. **Embedding Model:** `BAAI/bge-m3` (Semantic Caching)
3. **Zero-Shot Complexity Classifier:** `facebook/bart-large-mnli` (Intelligent Routing)
4. **Prompt Injection Detection:** `ProtectAI/deberta-v3-base-injection`
5. **Toxicity Detection:** `s-nlp/roberta_toxicity_classifier`
6. **Factual Cross-Encoder:** `cross-encoder/nli-deberta-v3-base`
7. **PII Detection:** Microsoft Presidio (`en_core_web_sm`)

---

## 🚀 How to Download and Reproduce Locally

### Prerequisites
1. **Python 3.13** 
2. **Node.js** (For the Vite dashboard)
3. **Docker Desktop** (For Postgres & Redis)
4. **Ollama** (Running locally on port 11434)

### Step 1: Clone and Set Up Infrastructure
Clone the repository, then start the persistent databases using Docker Compose:
```bash
git clone https://github.com/your-org/ControlPlane.ai.git
cd ControlPlane.ai
docker-compose up -d
```
*Note: This starts PostgreSQL (port 5432) and Redis (port 6379).*

### Step 2: Download Foundation Model
Ensure Ollama is installed and running, then pull the base model:
```bash
ollama run qwen3:1.7b
```

### Step 3: Start the Backend (FastAPI)
Open a new terminal and navigate to the backend directory:
```bash
cd backend
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt

# Download required HuggingFace/SpaCy models (Run Once)
python setup_models.py

# Start the Gateway Server
uvicorn app.main:app --port 8000
```
*Note: The first startup will take 1-2 minutes as the transformers pipeline loads the NLP models into memory.*

### Step 4: Start the Frontend Dashboard
Open a new terminal and navigate to the frontend directory:
```bash
cd frontend
npm install
npm run dev
```
Navigate to `http://localhost:5173` to view the ControlPlane.ai observability dashboard and playground.

---

## 🧪 Running the Benchmark

This repository includes a programmatic benchmark tool that tests 1,000 interactions against the raw LLM vs the ControlPlane.ai proxy.

```bash
cd benchmark
python run_ab_benchmark.py
python generate_business_report.py
```
This will output `business_case_report.md` detailing exact token reduction, cache hit rates, and safety block rates.
