import io
import os
import sys
import json
import PyPDF2
from fastapi.testclient import TestClient
from main import app
from backend.services.pdf_processor import pdf_processor, PDFProcessingError
from backend.services.query_classifier import query_classifier, QueryType
from backend.services.legal_retriever import legal_retriever
from backend.services.contract_analyzer import contract_analyzer

client = TestClient(app)

def test_health_check():
    print("[1/7] Testing health check...", flush=True)
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["app"] == "Contract IQ"
    assert data["status"] == "healthy"
    print("Health check endpoint test: PASS", flush=True)

def test_pdf_validation_and_errors():
    print("[2/7] Testing PDF validation and errors...", flush=True)
    # Corrupt / Empty PDF direct service tests
    empty_bytes = b""
    try:
        pdf_processor.extract_text_with_pages(empty_bytes, "empty.pdf")
        assert False, "Should raise PDFProcessingError"
    except PDFProcessingError as e:
        assert "empty" in str(e).lower()
        print("Empty PDF error handling: PASS", flush=True)

    corrupt_bytes = b"NOT_A_REAL_PDF_HEADER"
    try:
        pdf_processor.extract_text_with_pages(corrupt_bytes, "corrupt.pdf")
        assert False, "Should raise PDFProcessingError"
    except PDFProcessingError as e:
        assert "corrupted" in str(e).lower() or "failed" in str(e).lower()
        print("Corrupt PDF error handling: PASS", flush=True)

def test_query_classification_rules():
    print("[3/7] Testing query classification rules...", flush=True)
    # Real-world situation
    q_landlord = "My landlord is refusing to return my security deposit"
    assert query_classifier.classify(q_landlord, has_document=False) == QueryType.REAL_WORLD_QUERY

    q_employer = "My employer terminated me without notice and withheld pay"
    assert query_classifier.classify(q_employer, has_document=False) == QueryType.REAL_WORLD_QUERY

    # General legal inquiry
    q_bns = "What is Section 318 of Bharatiya Nyaya Sanhita?"
    assert query_classifier.classify(q_bns, has_document=False) == QueryType.LEGAL_QUERY

    q_contract = "What is the consequence of breach of contract under Section 73?"
    assert query_classifier.classify(q_contract, has_document=False) == QueryType.LEGAL_QUERY

    # Document-specific query
    q_doc = "What does clause 4 say about my notice period?"
    assert query_classifier.classify(q_doc, has_document=True) == QueryType.DOCUMENT_QUERY

    # Hybrid query (evaluating contract clause against Indian law)
    q_hybrid = "Is the non-compete clause in this agreement valid under Indian law?"
    assert query_classifier.classify(q_hybrid, has_document=True) == QueryType.HYBRID_QUERY

    print("Query classification and routing: PASS", flush=True)

def test_legal_knowledge_retrieval():
    print("[4/7] Testing legal knowledge retrieval...", flush=True)
    # 1. Indian Contract Act (Section 27 non-compete)
    res_ica = legal_retriever.retrieve("employment restraint of trade non-compete void", k=2)
    assert len(res_ica) > 0
    top_ica = res_ica[0]
    assert "Contract Act" in top_ica["act_name"]
    assert "27" in top_ica["section_number"]
    print("Legal retrieval (Contract Act Sec 27): PASS", flush=True)

    # 2. BNS 2023 vs IPC (Cheating / Fraud)
    res_bns = legal_retriever.retrieve("cheating and dishonest inducement of property 420", k=2)
    assert len(res_bns) > 0
    found_cheating = any("318" in r["section_number"] or "420" in r["section_number"] for r in res_bns)
    assert found_cheating, "Should retrieve cheating provision from BNS or IPC"
    print("Legal retrieval (BNS 318 / IPC 420): PASS", flush=True)

    # 3. Criminal Breach of Trust (Security Deposit withholding)
    res_cbt = legal_retriever.retrieve("security deposit misappropriation criminal breach of trust", k=2)
    assert len(res_cbt) > 0
    found_cbt = any("316" in r["section_number"] or "405" in r["section_number"] for r in res_cbt)
    assert found_cbt, "Should retrieve criminal breach of trust provision"
    print("Legal retrieval (BNS 316 / IPC 405): PASS", flush=True)

    # 4. Consumer Protection Act 2019
    res_cpa = legal_retriever.retrieve("online seller refund refusal deficiency unfair trade practice", k=2)
    assert len(res_cpa) > 0
    found_cpa = any("Consumer Protection" in r["act_name"] for r in res_cpa)
    assert found_cpa, "Should retrieve Consumer Protection Act"
    print("Legal retrieval (Consumer Protection Act): PASS", flush=True)

def test_contract_clause_risk_analyzer():
    print("[5/7] Testing contract clause risk analyzer...", flush=True)
    sample_risky_contract = """
    EMPLOYMENT AND NON-DISCLOSURE AGREEMENT
    Clause 1: Term of Employment shall be 2 years.
    Clause 2: Post-Termination Non-Compete. The Employee shall not engage or work with any competing firm for 2 years after leaving.
    Clause 3: Termination. The Employer may terminate at any time without notice or cause.
    Clause 4: Penalty. In the event of early resignation, the entire security deposit of INR 100,000 shall be forfeited as penalty.
    Clause 5: Indemnity. The Employee agrees to defend, indemnify and hold harmless the Company against any and all liabilities whatsoever.
    """
    analysis = contract_analyzer.analyze_contract_heuristics(sample_risky_contract, [])
    assert analysis["overall_risk"] == "High"
    assert len(analysis["findings"]) >= 3
    titles = [f["clause_name"] for f in analysis["findings"]]
    assert any("Non-Compete" in t for t in titles)
    assert any("Forfeiture" in t or "Penalty" in t for t in titles)
    assert any("Termination" in t for t in titles)
    assert len(analysis["missing_clauses"]) > 0
    print("Contract clause risk auditor heuristic test: PASS", flush=True)

def test_web_routes():
    print("[6/7] Testing web routes...", flush=True)
    pages = ["/", "/documents", "/legal", "/analysis", "/history", "/about"]
    for p in pages:
        res = client.get(p)
        assert res.status_code == 200, f"Page {p} returned status {res.status_code}"
    print("Web UI templates and pages: PASS", flush=True)

def test_chat_endpoint_e2e():
    print("[7/7] Testing chat endpoint e2e...", flush=True)
    # Test real-world chat query
    res = client.post("/api/chat", json={
        "message": "My landlord is refusing to return my security deposit of 50000 after I vacated the flat."
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["query_type"] == QueryType.REAL_WORLD_QUERY
    assert "answer" in data
    assert len(data["sources"]) > 0
    print("Chat API endpoint (Real-World situation with legal citations): PASS", flush=True)

    # Test legal query
    res_legal = client.post("/api/chat", json={
        "message": "What is Section 27 of the Indian Contract Act regarding non-compete agreements?"
    })
    assert res_legal.status_code == 200
    data_legal = res_legal.json()
    assert data_legal["status"] == "success"
    assert data_legal["query_type"] == QueryType.LEGAL_QUERY
    assert len(data_legal["sources"]) > 0
    print("Chat API endpoint (Legal Query with citations): PASS", flush=True)

if __name__ == "__main__":
    print("--- STARTING CONTRACT IQ FULL VERIFICATION SUITE ---", flush=True)
    test_health_check()
    test_pdf_validation_and_errors()
    test_query_classification_rules()
    test_legal_knowledge_retrieval()
    test_contract_clause_risk_analyzer()
    test_web_routes()
    test_chat_endpoint_e2e()
    print("--- ALL VERIFICATION SUITE TESTS PASSED SUCCESSFULLY! ---", flush=True)
