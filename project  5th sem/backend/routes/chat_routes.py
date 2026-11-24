from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from backend.database.session_store import session_store
from backend.services.query_classifier import query_classifier, QueryType
from backend.services.document_retriever import document_retriever
from backend.services.legal_retriever import legal_retriever
from backend.services.legal_explainer import legal_explainer

router = APIRouter(prefix="/api/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    message: str
    document_id: Optional[str] = None
    language: Optional[str] = "en"
    override_query_type: Optional[str] = None

@router.post("")
async def unified_chat(request: Request, payload: ChatRequest):
    """
    Intelligent unified chat endpoint:
    Classifies the user's inquiry, retrieves evidence from documents and/or the legal knowledge base,
    and returns a structured explanation.
    """
    session_id = request.cookies.get("session_id")
    session_id = session_store.ensure_session(session_id)

    # Determine document availability
    active_doc = None
    if payload.document_id:
        active_doc = session_store.get_document(payload.document_id, session_id=session_id)
    if not active_doc:
        active_doc = session_store.get_latest_document(session_id)

    has_document = active_doc is not None
    doc_id = active_doc["document_id"] if active_doc else None

    # Classify query
    query_type = payload.override_query_type
    if not query_type:
        query_type = query_classifier.classify(payload.message, has_document=has_document)

    chat_history = session_store.get_chat_history(session_id, limit=20)

    # Route based on query classification
    if query_type == QueryType.DOCUMENT_QUERY and has_document:
        doc_chunks = document_retriever.retrieve(session_id, doc_id, payload.message, k=4)
        response_data = legal_explainer.answer_document_query(
            question=payload.message,
            retrieved_chunks=doc_chunks,
            chat_history=chat_history,
            language=payload.language or "en"
        )
    elif query_type == QueryType.LEGAL_QUERY:
        legal_chunks = legal_retriever.retrieve(payload.message, k=4)
        response_data = legal_explainer.answer_legal_query(
            question=payload.message,
            retrieved_legal_chunks=legal_chunks,
            chat_history=chat_history,
            language=payload.language or "en"
        )
    elif query_type == QueryType.REAL_WORLD_QUERY:
        legal_chunks = legal_retriever.retrieve(payload.message, k=4)
        response_data = legal_explainer.answer_real_world_query(
            question=payload.message,
            retrieved_legal_chunks=legal_chunks,
            chat_history=chat_history,
            language=payload.language or "en"
        )
    elif query_type == QueryType.HYBRID_QUERY and has_document:
        doc_chunks = document_retriever.retrieve(session_id, doc_id, payload.message, k=3)
        legal_chunks = legal_retriever.retrieve(payload.message, k=3)
        response_data = legal_explainer.answer_hybrid_query(
            question=payload.message,
            retrieved_doc_chunks=doc_chunks,
            retrieved_legal_chunks=legal_chunks,
            chat_history=chat_history,
            language=payload.language or "en"
        )
    else:
        # Fallback to legal query if no document exists
        legal_chunks = legal_retriever.retrieve(payload.message, k=4)
        response_data = legal_explainer.answer_legal_query(
            question=payload.message,
            retrieved_legal_chunks=legal_chunks,
            chat_history=chat_history,
            language=payload.language or "en"
        )
        query_type = QueryType.LEGAL_QUERY

    # Persist in session conversation history
    session_store.add_message(
        session_id=session_id,
        sender="user",
        content=payload.message,
        document_id=doc_id,
        query_type=query_type
    )
    session_store.add_message(
        session_id=session_id,
        sender="assistant",
        content=response_data["answer"],
        document_id=doc_id,
        query_type=query_type,
        sources=response_data.get("sources", [])
    )

    return {
        "status": "success",
        "query_type": query_type,
        "answer": response_data["answer"],
        "sources": response_data.get("sources", []),
        "model": response_data.get("model", "")
    }

@router.get("/history")
async def get_history(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return {"history": []}
    return {"history": session_store.get_chat_history(session_id)}

@router.post("/clear")
async def clear_history(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id:
        session_store.clear_chat_history(session_id)
    return {"status": "success", "message": "Chat history cleared."}
