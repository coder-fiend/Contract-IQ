import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from backend.config import settings
from backend.services.embedding_service import embedding_service

class DocumentRetriever:
    def __init__(self, base_vector_dir: Path = settings.DOCUMENTS_VECTOR_DIR):
        self.base_vector_dir = Path(base_vector_dir)
        self.base_vector_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, FAISS] = {}

    def _get_index_dir(self, session_id: str, document_id: str) -> Path:
        return self.base_vector_dir / f"{session_id}_{document_id}"

    def build_and_save_index(
        self, 
        session_id: str, 
        document_id: str, 
        chunks: List[Document]
    ) -> str:
        """
        Builds a FAISS index from document chunks and persists it to disk.
        Returns the directory path where the index is saved.
        """
        if not chunks:
            raise ValueError("No chunks provided to build vector index.")

        embeddings = embedding_service.get_embeddings()
        vector_store = FAISS.from_documents(chunks, embeddings)
        
        index_dir = self._get_index_dir(session_id, document_id)
        index_dir.mkdir(parents=True, exist_ok=True)
        vector_store.save_local(str(index_dir))

        cache_key = f"{session_id}_{document_id}"
        self._cache[cache_key] = vector_store

        return str(index_dir)

    def load_index(self, session_id: str, document_id: str) -> Optional[FAISS]:
        cache_key = f"{session_id}_{document_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        index_dir = self._get_index_dir(session_id, document_id)
        if not (index_dir / "index.faiss").exists():
            # Check if database has saved vector_path
            try:
                from backend.database.session_store import session_store
                doc = session_store.get_document(document_id, session_id=session_id)
                if doc and doc.get("vector_path") and (Path(doc["vector_path"]) / "index.faiss").exists():
                    index_dir = Path(doc["vector_path"])
                else:
                    return None
            except Exception:
                return None

        embeddings = embedding_service.get_embeddings()
        vector_store = FAISS.load_local(
            str(index_dir), 
            embeddings, 
            allow_dangerous_deserialization=True
        )
        self._cache[cache_key] = vector_store
        return vector_store

    def retrieve(
        self, 
        session_id: str, 
        document_id: str, 
        query: str, 
        k: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top-k relevant chunks for a document query.
        Returns a list of dicts with content and citation metadata.
        """
        vector_store = self.load_index(session_id, document_id)
        if not vector_store:
            return []

        # Use similarity search with score
        docs_with_scores = vector_store.similarity_search_with_score(query, k=k)
        
        results = []
        for doc, score in docs_with_scores:
            results.append({
                "content": doc.page_content,
                "page_number": doc.metadata.get("page_number", 1),
                "detected_clause": doc.metadata.get("detected_clause"),
                "filename": doc.metadata.get("filename", "document.pdf"),
                "chunk_id": doc.metadata.get("chunk_id", ""),
                "score": float(score)
            })
            
        return results

    def delete_index(self, session_id: str, document_id: str) -> bool:
        cache_key = f"{session_id}_{document_id}"
        self._cache.pop(cache_key, None)
        
        index_dir = self._get_index_dir(session_id, document_id)
        if index_dir.exists():
            shutil.rmtree(index_dir)
            return True
        return False

document_retriever = DocumentRetriever()
