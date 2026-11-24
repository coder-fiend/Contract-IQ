# Contract IQ ⚖️
### AI-Powered Legal Document Understanding & Assistance Platform (Focused on Indian Law)

Contract IQ is an advanced legal-tech platform that transforms raw legal agreements, statutory Indian laws, and everyday disputes into clear, accessible, and source-grounded intelligence.

---

## 🌟 Key Capabilities

1. **Document Assistant (RAG on Legal PDFs)**
   - Upload rental agreements, employment contracts, NDAs, and business contracts.
   - Extracts text page-by-page, preserving exact page numbers and clause markers.
   - Session-isolated FAISS vector store ensuring user privacy and zero cross-user leakage.
   - AI answers with direct operative clause citations, plain-language explanations, risks, and next steps.

2. **Indian Legal Knowledge Base**
   - Permanent verified statutory vector store covering:
     - **Indian Contract Act, 1872** (Formation, breach damages Sec 73/74, non-compete Sec 27)
     - **Bharatiya Nyaya Sanhita (BNS), 2023** (Effective 1 July 2024, replacing IPC)
     - **Indian Penal Code, 1860 (IPC)** (Maintained for historical pre-July 2024 offences)
     - **Consumer Protection Act, 2019** (Deficiency in service, unfair contract terms Sec 2(46), e-Daakhil)
     - **Information Technology Act, 2000** (E-contracts, cyber fraud, data breach)
   - Built-in temporal reasoning (BNS vs IPC transition rules).

3. **Real-World Legal Problem Assistant**
   - No document needed! Describe real-world situations:
     - Landlord refusing to return security deposit
     - Employer termination without notice
     - Online seller refusing refunds for defective goods
     - Threats, harassment, or breach of verbal/written commitments
   - Outlines legal rights, applicable sections, practical next steps, and when to consult an advocate.

4. **Intelligent Query Classification & Hybrid Routing**
   - Automatically categorizes queries into:
     - `DOCUMENT_QUERY`
     - `LEGAL_QUERY`
     - `REAL_WORLD_QUERY`
     - `HYBRID_QUERY` (e.g. testing whether a specific contract clause is legally valid under Indian law)

5. **"Analyze My Contract" (Clause Risk Auditor)**
   - Scans agreements for high-risk, ambiguous, or one-sided terms.
   - Categorizes risks as **High**, **Medium**, or **Low**.
   - Identifies omitted standard protective clauses (Dispute Resolution, Force Majeure, Limitation of Liability).
   - Generates an overall Contract Health Score (0–100) and actionable negotiation tips.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10 or 3.11 installed.
- (Optional but recommended) Google Gemini API Key.

### 2. Configure Environment
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Open `.env` and add your Gemini API Key:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
```
*(Note: If no API key is provided, Contract IQ operates in offline fallback mode, still performing full FAISS retrieval, clause matching, risk heuristic scanning, and statutory citations!)*

### 3. Install Dependencies
Using `uv` (recommended) or `pip`:
```bash
# Using uv (fastest)
uv pip install -r requirements.txt

# Or using standard pip
pip install -r requirements.txt
```

### 4. (Optional) Re-index Legal Knowledge Base
The repository includes pre-built legal data. To re-index or add new acts:
```bash
python scripts/ingest_legal_data.py
```

### 5. Run the Application
Start the FastAPI server:
```bash
python main.py
```
or via Uvicorn:
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser at:
👉 **http://127.0.0.1:8000**

---

## 📁 Project Architecture

```
.
├── backend/
│   ├── config.py                 # Application settings & environment paths
│   ├── database/
│   │   └── session_store.py      # SQLite session isolation & history
│   ├── prompts/
│   │   ├── document_prompt.py    # Structured document QA template
│   │   └── legal_prompts.py      # Legal, Real-World & Hybrid templates
│   ├── routes/
│   │   ├── analysis_routes.py    # Contract risk audit endpoints
│   │   ├── chat_routes.py        # Unified & specialized chat endpoints
│   │   └── document_routes.py    # Upload, list, delete document endpoints
│   └── services/
│       ├── chunking_service.py   # Page-preserving legal text splitter
│       ├── contract_analyzer.py  # Clause risk auditor & heuristic engine
│       ├── document_retriever.py # Per-session FAISS document store
│       ├── embedding_service.py  # Local HuggingFace embedding singleton
│       ├── legal_explainer.py    # Gemini LLM explanation engine & offline fallback
│       ├── legal_retriever.py    # Permanent Indian statutes vector store
│       ├── pdf_processor.py      # PyPDF2 page-by-page text extractor & validator
│       └── query_classifier.py   # 4-way intelligent query classifier
├── legal_data/
│   └── acts/                     # Verified Indian statute JSON definitions
├── scripts/
│   └── ingest_legal_data.py      # Ingestion CLI for statutory knowledge
├── static/
│   ├── css/style.css             # Legal-tech modern responsive styling
│   └── js/app.js                 # Drag-drop upload, live chat & audit UI
├── templates/
│   ├── base.html                 # Common layout with navigation & footer
│   ├── index.html                # Landing page with 3 core feature cards
│   ├── document_assistant.html   # PDF upload, live QA & page citations
│   ├── legal_assistant.html      # Indian law Q&A & dispute advisor
│   ├── contract_analysis.html    # Risk summary & missing clause auditor
│   ├── history.html              # Conversation history viewer
│   └── about.html                # Platform details, sources & disclaimer
├── tests/                        # Full verification test suite
├── chatbot.py                    # Backward-compatible entrypoint
└── main.py                       # Application entrypoint
```

---

## ⚖️ Legal Safety & Disclaimer
Contract IQ is designed strictly for informational, educational, and preliminary document assessment purposes. It does **not** constitute formal legal advice and does **not** create an attorney-client relationship. For binding legal representation, please consult an advocate licensed by the Bar Council of India.
