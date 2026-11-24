import os
import threading
from typing import Optional
from langchain_huggingface import HuggingFaceEmbeddings
from backend.config import settings

class EmbeddingService:
    _instance: Optional['EmbeddingService'] = None
    _lock = threading.Lock()
    _embeddings: Optional[HuggingFaceEmbeddings] = None

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(EmbeddingService, cls).__new__(cls)
        return cls._instance

    def get_embeddings(self) -> HuggingFaceEmbeddings:
        if self._embeddings is None:
            with self._lock:
                if self._embeddings is None:
                    # Prefer local cached files if available to avoid network delays
                    try:
                        self._embeddings = HuggingFaceEmbeddings(
                            model_name=settings.EMBEDDING_MODEL_NAME,
                            model_kwargs={"local_files_only": True},
                            encode_kwargs={"normalize_embeddings": True}
                        )
                    except Exception:
                        # Fallback without local_files_only if model hasn't been cached yet
                        self._embeddings = HuggingFaceEmbeddings(
                            model_name=settings.EMBEDDING_MODEL_NAME,
                            encode_kwargs={"normalize_embeddings": True}
                        )
        return self._embeddings

embedding_service = EmbeddingService()
