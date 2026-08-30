import logging
import gc

logger = logging.getLogger(__name__)

class LazyModelManager:
    """
    Manages lazy loading of heavy HuggingFace models to conserve RAM.
    Models are loaded when needed and can be unloaded after use.
    """
    def __init__(self):
        self._models = {}
        
    def get_pipeline(self, task: str, model_name: str, device=-1):
        if model_name not in self._models:
            logger.info(f"Lazy loading model {model_name}...")
            try:
                from transformers import pipeline
                self._models[model_name] = pipeline(task, model=model_name, device=device)
            except Exception as e:
                logger.error(f"Failed to load {model_name}: {e}")
                return None
        return self._models[model_name]
        
    def get_sentence_transformer(self, model_name: str):
        if model_name not in self._models:
            logger.info(f"Lazy loading SentenceTransformer {model_name}...")
            try:
                from sentence_transformers import SentenceTransformer
                self._models[model_name] = SentenceTransformer(model_name)
            except Exception as e:
                logger.error(f"Failed to load {model_name}: {e}")
                return None
        return self._models[model_name]

    def get_cross_encoder(self, model_name: str):
        if model_name not in self._models:
            logger.info(f"Lazy loading CrossEncoder {model_name}...")
            try:
                from sentence_transformers import CrossEncoder
                self._models[model_name] = CrossEncoder(model_name)
            except Exception as e:
                logger.error(f"Failed to load {model_name}: {e}")
                return None
        return self._models[model_name]

    def unload(self, model_name: str):
        if model_name in self._models:
            logger.info(f"Unloading model {model_name} to free RAM...")
            del self._models[model_name]
            gc.collect()

    def unload_all(self):
        self._models.clear()
        gc.collect()

lazy_loader = LazyModelManager()
