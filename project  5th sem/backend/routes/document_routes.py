import os
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from backend.config import settings
from backend.database.session_store import session_store
from backend.services.pdf_processor import pdf_processor, PDFProcessingError
from backend.services.chunking_service import chunking_service
from backend.services.document_retriever import document_retriever

router = APIRouter(prefix="/api/documents", tags=["Documents"])

@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...)
):
    pdf_processor.validate_file(file, max_size_mb=settings.MAX_FILE_SIZE_MB)
    
    # Extract session_id from cookie or generate new one
    session_id = request.cookies.get("session_id")
    session_id = session_store.ensure_session(session_id)

    try:
        file_bytes = await file.read()
        pages_data = pdf_processor.extract_text_with_pages(file_bytes, filename=file.filename)
    except PDFProcessingError as pe:
        raise HTTPException(status_code=400, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

    # Save physical copy in uploads directory
    safe_filename = f"{session_id}_{file.filename}"
    saved_path = settings.UPLOADS_DIR / safe_filename
    with open(saved_path, "wb") as f:
        f.write(file_bytes)

    # Generate consistent document_id
    import uuid
    document_id = str(uuid.uuid4())

    # Chunk the extracted document
    chunks = chunking_service.split_document_pages(pages_data, document_id, file.filename)

    # Build and persist FAISS index
    index_path = document_retriever.build_and_save_index(session_id, document_id, chunks)

    # Record in database with the exact matching document_id
    session_store.add_document(
        session_id=session_id,
        filename=file.filename,
        file_path=str(saved_path),
        page_count=len(pages_data),
        vector_path=index_path,
        document_id=document_id
    )

    response = JSONResponse({
        "status": "success",
        "message": f"Successfully processed and indexed '{file.filename}'.",
        "document": {
            "document_id": document_id,
            "filename": file.filename,
            "page_count": len(pages_data),
            "chunks_count": len(chunks)
        }
    })
    response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="lax")
    return response

@router.get("")
async def list_documents(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return {"documents": []}
    
    docs = session_store.get_session_documents(session_id)
    return {"documents": docs}

@router.get("/{document_id}")
async def get_document_details(document_id: str, request: Request):
    session_id = request.cookies.get("session_id")
    doc = session_store.get_document(document_id, session_id=session_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or access denied.")
    return {"document": doc}

@router.delete("/{document_id}")
async def delete_document(document_id: str, request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="No active session.")

    doc = session_store.get_document(document_id, session_id=session_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Remove vector index
    document_retriever.delete_index(session_id, document_id)
    
    # Remove physical file if exists
    try:
        if os.path.exists(doc.get("file_path", "")):
            os.remove(doc["file_path"])
    except Exception:
        pass

    session_store.delete_document(document_id, session_id)
    return {"status": "success", "message": "Document deleted successfully."}
