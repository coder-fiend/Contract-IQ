import os
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from backend.database.session_store import session_store
from backend.services.pdf_processor import pdf_processor
from backend.services.contract_analyzer import contract_analyzer

router = APIRouter(prefix="/api/contracts", tags=["Contract Analysis"])

class AnalyzeRequest(BaseModel):
    document_id: Optional[str] = None

@router.post("/analyze")
async def analyze_contract(request: Request, payload: AnalyzeRequest):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="No active session found. Please upload a contract first.")

    doc = None
    if payload.document_id:
        doc = session_store.get_document(payload.document_id, session_id=session_id)
    if not doc:
        doc = session_store.get_latest_document(session_id)

    if not doc:
        raise HTTPException(status_code=400, detail="No document found in current session to analyze.")

    file_path = doc.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Underlying document file is missing.")

    # Extract text
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        pages_data = pdf_processor.extract_text_with_pages(file_bytes, filename=doc["filename"])
        full_text = "\n\n".join(p["text"] for p in pages_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read contract text: {str(e)}")

    # Run analysis
    heuristic_findings = contract_analyzer.analyze_contract_heuristics(full_text, pages_data)
    final_analysis = contract_analyzer.analyze_with_gemini(full_text, heuristic_findings)

    # Save analysis in session store
    session_store.save_analysis(session_id, doc["document_id"], final_analysis)

    return {
        "status": "success",
        "document_id": doc["document_id"],
        "filename": doc["filename"],
        "analysis": final_analysis
    }

@router.get("/analyze/{document_id}")
async def get_saved_analysis(document_id: str, request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="No active session.")

    saved = session_store.get_analysis(document_id, session_id)
    if not saved:
        raise HTTPException(status_code=404, detail="No previous analysis found for this document.")

    return saved
