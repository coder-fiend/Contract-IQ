import os
from pathlib import Path
from fastapi import FastAPI, Request, Response, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.config import settings
from backend.database.session_store import session_store
from backend.routes.document_routes import router as document_router
from backend.routes.chat_routes import router as chat_router
from backend.routes.analysis_routes import router as analysis_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered legal document understanding and assistance platform focused on Indian law."
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Register API Routers
app.include_router(document_router)
app.include_router(chat_router)
app.include_router(analysis_router)

import uuid

@app.middleware("http")
async def ensure_session_cookie(request: Request, call_next):
    # Skip session cookie handling for static assets and health check
    if request.url.path.startswith("/static") or request.url.path == "/api/health":
        return await call_next(request)

    session_id = request.cookies.get("session_id")
    is_new = False
    if not session_id:
        session_id = str(uuid.uuid4())
        is_new = True

    response: Response = await call_next(request)
    if is_new:
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 30  # 30 days
        )
    return response

# ----------------- Web UI Page Routes -----------------

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    session_id = request.cookies.get("session_id")
    docs = session_store.get_session_documents(session_id) if session_id else []
    return templates.TemplateResponse("index.html", {
        "request": request,
        "page_title": "Contract IQ | AI-Powered Indian Legal Assistant",
        "documents": docs
    })

@app.get("/documents", response_class=HTMLResponse)
async def document_assistant_page(request: Request):
    session_id = request.cookies.get("session_id")
    docs = session_store.get_session_documents(session_id) if session_id else []
    history = session_store.get_chat_history(session_id) if session_id else []
    active_doc = docs[0] if docs else None
    return templates.TemplateResponse("document_assistant.html", {
        "request": request,
        "page_title": "Document Assistant | Contract IQ",
        "documents": docs,
        "active_doc": active_doc,
        "history": history
    })

@app.get("/legal", response_class=HTMLResponse)
async def legal_assistant_page(request: Request):
    session_id = request.cookies.get("session_id")
    history = session_store.get_chat_history(session_id) if session_id else []
    return templates.TemplateResponse("legal_assistant.html", {
        "request": request,
        "page_title": "Legal Assistant | Contract IQ",
        "history": history
    })

@app.get("/analysis", response_class=HTMLResponse)
async def contract_analysis_page(request: Request):
    session_id = request.cookies.get("session_id")
    docs = session_store.get_session_documents(session_id) if session_id else []
    active_doc = docs[0] if docs else None
    saved_analysis = None
    if active_doc:
        analysis_record = session_store.get_analysis(active_doc["document_id"], session_id)
        if analysis_record:
            saved_analysis = analysis_record.get("result")
    
    return templates.TemplateResponse("contract_analysis.html", {
        "request": request,
        "page_title": "Contract Risk Analysis | Contract IQ",
        "documents": docs,
        "active_doc": active_doc,
        "analysis": saved_analysis
    })

@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    session_id = request.cookies.get("session_id")
    history = session_store.get_chat_history(session_id) if session_id else []
    return templates.TemplateResponse("history.html", {
        "request": request,
        "page_title": "Chat History | Contract IQ",
        "history": history
    })

@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse("about.html", {
        "request": request,
        "page_title": "About | Contract IQ"
    })

@app.get("/api/health")
async def health_check():
    has_key = bool(settings.OPENAI_API_KEY or settings.GOOGLE_API_KEY)
    provider = "openai" if settings.OPENAI_API_KEY else ("gemini" if settings.GOOGLE_API_KEY else "offline")
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "has_llm_key": has_key,
        "provider": provider
    }

# ----------------- Legacy Compatibility Endpoints -----------------

@app.get("/chat", response_class=HTMLResponse)
def legacy_chat_redirect():
    return RedirectResponse(url="/documents", status_code=303)

@app.get("/rag", response_class=HTMLResponse)
def legacy_rag_redirect():
    return RedirectResponse(url="/documents", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)
