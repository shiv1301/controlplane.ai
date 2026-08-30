import logging
import sys
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Initializing explicit model download...")
    
    # Try importing spacy and downloading the model if missing
    try:
        import spacy
        spacy.load("en_core_web_sm")
        logger.info("spaCy en_core_web_sm is available.")
    except Exception as e:
        logger.warning(f"spaCy model not loaded natively, attempting download... {e}")
        os.system(f"{sys.executable} -m spacy download en_core_web_sm")

    from transformers import pipeline
    from sentence_transformers import SentenceTransformer

    models_to_download = [
        # Phase 2
        ("text-classification", "unitary/toxic-bert"),
        ("text-classification", "protectai/deberta-v3-base-prompt-injection"),
        # Phase 3
        ("text-classification", "BAAI/bge-reranker-v2-m3"),
        ("text-classification", "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli")
    ]

    for task, model_name in models_to_download:
        logger.info(f"Downloading {task} model: {model_name}...")
        try:
            pipeline(task, model=model_name)
            logger.info(f"Successfully downloaded {model_name}")
        except Exception as e:
            logger.error(f"Failed to download {model_name}: {e}")

    logger.info("Downloading Semantic Cache model (BAAI/bge-m3)...")
    try:
        SentenceTransformer("BAAI/bge-m3")
        logger.info("Semantic Cache model downloaded successfully.")
    except Exception as e:
        logger.error(f"Failed to download BAAI/bge-m3: {e}")

    logger.info("All explicit model downloads complete.")

if __name__ == "__main__":
    main()
