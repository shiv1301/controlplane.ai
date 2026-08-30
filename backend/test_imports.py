import sys

try:
    import torch
    print("Torch imported successfully.")
except Exception as e:
    print(f"Torch failed: {e}")

try:
    from transformers import pipeline
    print("Transformers imported successfully.")
except Exception as e:
    print(f"Transformers failed: {e}")

try:
    from sentence_transformers import SentenceTransformer
    print("SentenceTransformers imported successfully.")
except Exception as e:
    print(f"SentenceTransformers failed: {e}")

