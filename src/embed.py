"""
Stage 5: Embedding Generation
-------------------------------
Converts text chunks into numerical vectors (embeddings) that capture
their meaning. Chunks with similar meaning end up with similar vectors
— this is what makes semantic search possible in Stage 7.

Model: all-MiniLM-L6-v2 (small, fast, free, runs locally — no API key).
"""

import os

# We only need the PyTorch backend for sentence-transformers.
# This stops transformers from trying to import TensorFlow/Keras,
# which avoids Keras-3-vs-Keras-2 version conflicts entirely.
os.environ["USE_TF"] = "0"
os.environ["USE_FLAX"] = "0"

from sentence_transformers import SentenceTransformer

_model = None


def get_model():
    """Load the embedding model once and reuse it (loading is slow)."""
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_chunks(chunks):
    """
    Given a list of text chunks, return a list of embedding vectors
    (one vector per chunk).
    """
    model = get_model()
    embeddings = model.encode(chunks, convert_to_numpy=True)
    return embeddings
