"""
Contract IQ - Core Chatbot & RAG Services
Upgraded from legacy PDF-chatbot implementation.
Provides backward-compatible helper functions while routing to modular services.
"""

from typing import List, Dict, Any, Optional
from langchain_core.prompts import PromptTemplate
from backend.config import settings
from backend.services.pdf_processor import pdf_processor
from backend.services.chunking_service import chunking_service
from backend.services.embedding_service import embedding_service
from backend.services.document_retriever import document_retriever
from backend.services.legal_explainer import legal_explainer

# Backwards compatibility handles for legacy imports
llm = legal_explainer.get_llm()

final_prompt = PromptTemplate(
    template="""You are Contract IQ, a legal assistant.
Analyze the following context from the user's uploaded legal document and answer their question accurately.
Provide citations with page numbers when available.

Document Context:
{pdf-text}

Chat History:
{message}

Question:
{question}

Answer:""",
    input_variables=["pdf-text", "question", "message"]
)

def chunk(state: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy helper for chunking text in state dict"""
    text = state.get("text", "")
    if isinstance(text, str):
        pages_data = [{"page_number": 1, "text": text, "filename": "document.pdf"}]
        chunks = chunking_service.split_document_pages(pages_data, "default_doc", "document.pdf")
        state["text"] = chunks
    return state

def indexing(state: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy helper for indexing chunks in state dict"""
    chunks = state.get("text", [])
    if isinstance(chunks, list):
        embeddings = embedding_service.get_embeddings()
        from langchain_community.vectorstores import FAISS
        vector_store = FAISS.from_documents(chunks, embeddings)
        state["text"] = vector_store
    return state

def retrieval(state: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy helper for retriever in state dict"""
    vs = state.get("text")
    if vs is not None and hasattr(vs, "as_retriever"):
        retriever = vs.as_retriever(search_type="similarity", search_kwargs={"k": 4})
        state["text"] = retriever
    return state
