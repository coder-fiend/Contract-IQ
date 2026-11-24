import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_community.vectorstores import FAISS
from backend.config import settings
from backend.services.embedding_service import embedding_service

class LegalRetriever:
    def __init__(self, index_dir: Path = settings.LEGAL_VECTOR_DIR):
        self.index_dir = Path(index_dir)
        self._vector_store: Optional[FAISS] = None

    def load_index(self) -> Optional[FAISS]:
        if self._vector_store is not None:
            return self._vector_store

        index_file = self.index_dir / "index.faiss"
        if not index_file.exists():
            return None

        embeddings = embedding_service.get_embeddings()
        self._vector_store = FAISS.load_local(
            str(self.index_dir),
            embeddings,
            allow_dangerous_deserialization=True
        )
        return self._vector_store

    def retrieve(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        store = self.load_index()
        if not store:
            return []

        docs_and_scores = store.similarity_search_with_score(query, k=k)
        results = []
        for doc, score in docs_and_scores:
            meta = doc.metadata or {}
            results.append({
                "content": doc.page_content,
                "act_name": meta.get("act_name", ""),
                "section_number": meta.get("section_number", ""),
                "section_title": meta.get("section_title", ""),
                "status": meta.get("status", "Active"),
                "source_url": meta.get("source_url", ""),
                "effective_date": meta.get("effective_date", ""),
                "score": float(score)
            })
        return results

legal_retriever = LegalRetriever()
