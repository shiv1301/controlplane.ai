import logging
from app.verification.lazy_models import lazy_loader

logger = logging.getLogger(__name__)

class NLIVerifier:
    def verify(self, claim: str, evidence: str) -> dict:
        """Returns {'result': 'SUPPORTED' | 'UNSUPPORTED' | 'CONTRADICTED', 'score': float}"""
        if not evidence:
            return {"result": "UNSUPPORTED", "score": 0.0}
            
        nli_model = lazy_loader.get_pipeline("text-classification", "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli")
        if not nli_model:
            # Fallback if model fails to load
            logger.error("NLI model unavailable. Failsafe: UNSUPPORTED")
            return {"result": "UNSUPPORTED", "score": 0.0}
            
        # Format input for this specific model: "Premise [SEP] Hypothesis"
        # The pipeline for text-classification often accepts {"text": evidence, "text_pair": claim}
        # But wait, DeBERTa v3 text-classification pipeline usually accepts `[evidence, claim]` or just `evidence + " [SEP] " + claim`
        # Using `[{"text": evidence, "text_pair": claim}]` is standard for huggingface pipeline `text-classification` on MNLI.
        
        try:
            result = nli_model({"text": evidence, "text_pair": claim})
            
            # The model labels are usually: 'entailment', 'neutral', 'contradiction'
            label = result['label'].lower()
            score = result['score']
            
            if 'entailment' in label:
                res = "SUPPORTED"
            elif 'contradiction' in label:
                res = "CONTRADICTED"
            else:
                res = "UNSUPPORTED"
                
            return {"result": res, "score": score}
        except Exception as e:
            logger.error(f"NLI verification failed: {e}")
            return {"result": "UNSUPPORTED", "score": 0.0}
            
    def unload(self):
        lazy_loader.unload("MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli")

nli_verifier = NLIVerifier()

