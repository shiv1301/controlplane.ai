from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "api_requests_total", 
    "Total API requests", 
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    'api_request_latency_seconds',
    'Total request latency',
    ['endpoint']
)

PREPROCESSING_LATENCY = Histogram(
    'api_preprocessing_latency_seconds',
    'Latency of preprocessing prompt before generation',
    ['endpoint']
)

GENERATION_LATENCY = Histogram(
    'api_generation_latency_seconds',
    'Latency in response generation',
    ['endpoint']
)

VERIFICATION_LATENCY = Histogram(
    'api_verification_latency_seconds',
    'Latency in response checks and verification',
    ['endpoint']
)

CACHE_HITS = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_type"] # 'exact' or 'semantic'
)

MODEL_ROUTING = Counter(
    "model_routing_total",
    "Total requests routed by model",
    ["model_name"]
)

VERIFICATION_RESULTS = Counter(
    "verification_results_total",
    "Total verification results",
    ["result_type"] # 'SUPPORTED', 'UNSUPPORTED', 'CONTRADICTED'
)

REGENERATION_ATTEMPTS = Counter(
    "regeneration_attempts_total",
    "Total regeneration attempts"
)

POLICY_DECISIONS = Counter(
    "policy_decisions_total",
    "Total policy engine decisions",
    ["decision"]
)

RISK_LEVELS = Counter(
    "risk_levels_total",
    "Total requests by risk level",
    ["risk_level"]
)

