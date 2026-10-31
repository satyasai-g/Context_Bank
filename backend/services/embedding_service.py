import math
from typing import List, Optional
import numpy as np
from backend.core.config import settings


class EmbeddingService:
    """
    Embedding Service:
    Provides semantic embeddings. Supports:
    1. Offline TF-IDF / hashing vectorizer (always works with scikit-learn, zero API key required!)
    2. Gemini embedding model (when GEMINI_API_KEY is configured)
    """

    DIM = 384

    @classmethod
    def get_embedding(cls, text: str) -> List[float]:
        """Generate normalized embedding vector for text."""
        if not text or not text.strip():
            return [0.0] * cls.DIM

        # Try Gemini if configured and requested
        if settings.gemini_available and settings.EMBEDDING_PROVIDER == "gemini":
            try:
                return cls._get_gemini_embedding(text)
            except Exception:
                # Graceful fallback to offline vectorizer
                pass

        return cls._get_offline_embedding(text)

    @classmethod
    def _get_offline_embedding(cls, text: str) -> List[float]:
        """
        Deterministic, robust offline hashing embedding vector.
        Uses scikit-learn's HashingVectorizer for 384-dimensional dense normalized vector.
        """
        try:
            from sklearn.feature_extraction.text import HashingVectorizer
            vectorizer = HashingVectorizer(n_features=cls.DIM, norm="l2", alternate_sign=False)
            vec = vectorizer.transform([text.lower()]).toarray()[0]
            return vec.tolist()
        except Exception:
            # Simple fallback if sklearn fails
            words = text.lower().split()
            vec = [0.0] * cls.DIM
            for w in words:
                idx = hash(w) % cls.DIM
                vec[idx] += 1.0
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            return [x / norm for x in vec]

    @classmethod
    def _get_gemini_embedding(cls, text: str) -> List[float]:
        """Call Gemini text-embedding-004 API."""
        try:
            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            response = client.models.embed_content(
                model="text-embedding-004",
                contents=text,
            )
            # Truncate or pad to DIM
            raw_emb = response.embeddings[0].values
            if len(raw_emb) >= cls.DIM:
                return list(raw_emb[:cls.DIM])
            return list(raw_emb) + [0.0] * (cls.DIM - len(raw_emb))
        except Exception as e:
            return cls._get_offline_embedding(text)

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity between two float vectors."""
        if not v1 or not v2:
            return 0.0
        a = np.array(v1, dtype=float)
        b = np.array(v2, dtype=float)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
