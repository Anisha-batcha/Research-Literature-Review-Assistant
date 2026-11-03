"""
Stage 6 & 7: Vector Database + Semantic Retrieval
----------------------------------------------------
Stores chunk embeddings in a FAISS index so we can quickly find the
chunks most relevant to a user's question (nearest-neighbor search in
vector space, not keyword matching).
"""

import numpy as np
import faiss


def build_index(embeddings):
    """
    Build a FAISS index from a set of embeddings.
    Uses L2 (Euclidean) distance - smaller distance = more similar.
    """
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings).astype("float32"))
    return index


def search_index(index, query_embedding, k=3):
    """
    Search the index for the k chunks closest to the query embedding.
    Returns (indices, distances) - indices point back into the
    original chunks list.
    """
    query_vector = np.array([query_embedding]).astype("float32")
    distances, indices = index.search(query_vector, k)
    return indices[0], distances[0]
