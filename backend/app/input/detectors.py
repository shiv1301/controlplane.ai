import logging

logger = logging.getLogger(__name__)

class DetectorInterface:
    def detect(self, text: str) -> dict:
        raise NotImplementedError

class PIIDetector(DetectorInterface):
    def __init__(self):
        self.is_installed = False
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_analyzer.nlp_engine import NlpEngineProvider
            from presidio_anonymizer import AnonymizerEngine
            
            nlp_config = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
            }
            provider = NlpEngineProvider(nlp_configuration=nlp_config)
            nlp_engine = provider.create_engine()
            
            self.analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
            self.anonymizer = AnonymizerEngine()
            self.is_installed = True
        except Exception as e:
            logger.error(f"PIIDetector failed to load: {e}")

    def detect(self, text: str) -> dict:
        if not self.is_installed:
            raise RuntimeError("PIIDetector unavailable (fail closed)")
        
        results = self.analyzer.analyze(text=text, entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "IP_ADDRESS", "CREDIT_CARD"], language='en')
        anonymized = self.anonymizer.anonymize(text=text, analyzer_results=results)
        
        return {
            "detected": len(results) > 0,
            "status": "OK",
            "text": anonymized.text,
            "details": f"Found {len(results)} PII entities." if len(results) > 0 else ""
        }

class ToxicityDetector(DetectorInterface):
    def __init__(self):
        self.is_installed = False
        try:
            from transformers import pipeline
            self.classifier = pipeline("text-classification", model="unitary/toxic-bert", device=-1)
            self.is_installed = True
        except Exception as e:
            logger.error(f"ToxicityDetector failed to load: {e}")

    def detect(self, text: str) -> dict:
        if not self.is_installed:
            raise RuntimeError("ToxicityDetector unavailable (fail closed)")
        
        safe_text = text[:1500]
        
        # toxic-bert can output multiple labels like toxic, severe_toxic, obscene, threat, insult, identity_hate
        # We need to get all scores to check if any of them exceed the threshold.
        results = self.classifier(safe_text, top_k=None)
        if isinstance(results, list) and isinstance(results[0], list):
            results = results[0]  # pipeline sometimes wraps in double list
            
        is_toxic = False
        highest_score = 0.0
        highest_label = "none"
        
        for res in results:
            if res['label'] in ['toxic', 'severe_toxic', 'obscene', 'threat', 'insult', 'identity_hate'] and res['score'] > 0.5:
                is_toxic = True
            if res['score'] > highest_score:
                highest_score = res['score']
                highest_label = res['label']
        
        return {
            "detected": is_toxic,
            "status": "OK",
            "score": highest_score if is_toxic else 0.0,
            "details": highest_label
        }

class PromptInjectionDetector(DetectorInterface):
    def __init__(self):
        self.is_installed = False
        try:
            from transformers import pipeline
            self.classifier = pipeline("text-classification", model="protectai/deberta-v3-base-prompt-injection", device=-1)
            self.is_installed = True
        except Exception as e:
            logger.error(f"PromptInjectionDetector failed to load: {e}")

    def detect(self, text: str) -> dict:
        if not self.is_installed:
            raise RuntimeError("PromptInjectionDetector unavailable (fail closed)")
        
        safe_text = text[:1500]
        result = self.classifier(safe_text)[0]
        is_injection = result['label'] == 'INJECTION' and result['score'] > 0.5
        
        return {
            "detected": is_injection,
            "status": "OK",
            "score": result['score'] if is_injection else 0.0,
            "details": result['label']
        }

pii_detector = PIIDetector()
class HarmfulIntentDetector(DetectorInterface):
    def __init__(self):
        self.is_installed = False
        try:
            from transformers import pipeline
            # Using toxic-bert as a fallback for general harm/self-harm if we don't have a specific lightweight self-harm model
            # Or better, we can use a zero-shot classifier for specific intents
            self.classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=-1)
            self.is_installed = True
        except Exception as e:
            logger.error(f"HarmfulIntentDetector failed to load: {e}")

    def detect(self, text: str) -> dict:
        if not self.is_installed:
            return {"detected": False, "status": "UNAVAILABLE", "score": 0.0, "details": "unavailable"}
        
        safe_text = text[:1000]
        candidate_labels = ["self harm", "suicide", "terrorism", "violence", "safe", "question"]
        
        try:
            result = self.classifier(safe_text, candidate_labels)
            
            highest_score = 0.0
            highest_label = "safe"
            
            for label, score in zip(result['labels'], result['scores']):
                if score > highest_score:
                    highest_score = score
                    highest_label = label
                    
            is_harmful = highest_label in ["self harm", "suicide", "terrorism", "violence"] and highest_score > 0.6
            
            return {
                "detected": is_harmful,
                "status": "OK",
                "score": highest_score if is_harmful else 0.0,
                "details": highest_label
            }
        except Exception as e:
            logger.error(f"Harm intent detection failed: {e}")
            return {"detected": False, "status": "ERROR", "score": 0.0, "details": str(e)}

pii_detector = PIIDetector()
toxicity_detector = ToxicityDetector()
injection_detector = PromptInjectionDetector()
harm_intent_detector = HarmfulIntentDetector()
