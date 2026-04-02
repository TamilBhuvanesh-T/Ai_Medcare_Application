from sentence_transformers import SentenceTransformer
import numpy as np

# 🔐 Global cached model (loaded once)
_model = None

def get_model():
    global _model
    if _model is None:
        print("[EMBEDDER] Loading local embedding model...")
        _model = SentenceTransformer(
            "all-MiniLM-L6-v2",
            cache_folder="model_cache"   # force local cache
        )
        print("[EMBEDDER] Model loaded from disk.")
    return _model


def embed_texts(texts):
    """
    Offline-safe embedding generator
    """
    model = get_model()
    return model.encode(texts, convert_to_numpy=True)
