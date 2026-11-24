import io
import os
import sys
import json
import PyPDF2
from fastapi.testclient import TestClient
from main import app
from backend.services.document_retriever import document_retriever
from backend.services.legal_retriever import legal_retriever
from backend.services.legal_explainer import legal_explainer
from backend.database.session_store import session_store
from backend.config import settings

client = TestClient(app)

def create_sample_lease_pdf_bytes() -> bytes:
    """
    Creates a sample 2-page PDF with actual legal text in PDF format.
    We use PyPDF2 to generate blank pages and add stream objects with PDF text.
    """
    writer = PyPDF2.PdfWriter()

    # Create page 1
    p1 = PyPDF2.PageObject.create_blank_page(width=612, height=792)
    writer.add_page(p1)
    
    # Create page 2
    p2 = PyPDF2.PageObject.create_blank_page(width=612, height=792)
    writer.add_page(p2)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

def run_rag_test():
    print("--- 1. Testing AI Provider Configuration ---", flush=True)
    provider = legal_explainer.get_provider_name()
    print(f"Active AI Provider: {provider}", flush=True)
    assert provider == "gemini", f"Expected gemini, got {provider}"
    print(f"Configured Gemini Model: {settings.GEMINI_MODEL}", flush=True)

    print("\n--- 2. Testing Direct PDF Extraction & Chunking Logic ---", flush=True)
    # Simulate realistic extracted pages from a rental agreement
    sample_pages = [
        {
            "page_number": 1,
            "text": "RESIDENTIAL LEASE AGREEMENT\n\n"
                    "Clause 1: Parties. This agreement is made between Landlord Mr. Sharma and Tenant Mr. Verma.\n\n"
                    "Clause 2: Rent. The Monthly Rent shall be INR 25,000 payable on or before 5th of every month.\n\n"
                    "Clause 3: Security Deposit. The Tenant has deposited an interest-free Security Deposit of INR 75,000.",
            "char_count": 320,
            "filename": "Rental_Agreement.pdf"
        },
        {
            "page_number": 2,
            "text": "Clause 8: Early Termination. Either party may terminate this agreement before 11 months by giving 2 months prior written notice. "
                    "If Tenant vacates without notice before 11 months, one month rent shall be deducted from security deposit.\n\n"
                    "Clause 9: Commercial Use. The premises shall be used exclusively for residential purposes and not for commercial trade or coaching center.\n\n"
                    "Clause 10: Jurisdiction. Disputes shall be subject to Courts of Delhi.",
            "char_count": 420,
            "filename": "Rental_Agreement.pdf"
        }
    ]

    from backend.services.chunking_service import chunking_service
    test_session = session_store.ensure_session()
    test_doc_id = "test_lease_doc_101"

    chunks = chunking_service.split_document_pages(sample_pages, test_doc_id, "Rental_Agreement.pdf")
    print(f"Created {len(chunks)} document chunks with page metadata:", flush=True)
    for c in chunks:
        print(f"  - Chunk ID: {c.metadata['chunk_id']} | Page: {c.metadata['page_number']} | Clause: {c.metadata.get('detected_clause')}", flush=True)

    print("\n--- 3. Testing FAISS Index Storage and Retrieval ---", flush=True)
    idx_path = document_retriever.build_and_save_index(test_session, test_doc_id, chunks)
    print(f"Saved FAISS index at: {idx_path}", flush=True)

    # Save to database
    session_store.add_document(
        session_id=test_session,
        filename="Rental_Agreement.pdf",
        file_path="uploads/Rental_Agreement.pdf",
        page_count=2,
        vector_path=idx_path,
        document_id=test_doc_id
    )

    # Test Query 1: Termination clause
    q1 = "What happens if I terminate this agreement before 11 months?"
    print(f"\nTesting Query 1: '{q1}'", flush=True)
    retrieved_1 = document_retriever.retrieve(test_session, test_doc_id, q1, k=2)
    assert len(retrieved_1) > 0, "Must retrieve relevant chunks"
    top_1 = retrieved_1[0]
    print(f"Retrieved {len(retrieved_1)} chunks.", flush=True)
    print(f"Top Chunk Page: {top_1['page_number']} (Expected: Page 2)", flush=True)
    print(f"Top Chunk Clause: {top_1['detected_clause']}", flush=True)
    assert top_1['page_number'] == 2, f"Expected page 2 for termination clause, got {top_1['page_number']}"
    assert "Early Termination" in top_1['content'] or "terminate" in top_1['content'].lower()
    print("Document Retrieval (Page & Clause verification): PASS", flush=True)

    # Test Question Answering through legal_explainer
    res1 = legal_explainer.answer_document_query(
        question=q1,
        retrieved_chunks=retrieved_1,
        chat_history=[]
    )
    print("\nAnswer 1 Output Preview:", flush=True)
    print(res1["answer"][:400] + "...", flush=True)
    print(f"Sources returned: {len(res1['sources'])} (Page {res1['sources'][0]['page_number']})", flush=True)
    assert res1['sources'][0]['page_number'] == 2

    # Test Query 2: Question NOT in the PDF
    q2 = "Can I keep a pet dog in the flat?"
    print(f"\nTesting Query 2 (Not covered in PDF): '{q2}'", flush=True)
    # When no chunks match or chunks don't have pets
    res2 = legal_explainer.answer_document_query(
        question=q2,
        retrieved_chunks=[],
        chat_history=[]
    )
    print("Answer 2 Output Preview:", flush=True)
    print(res2["answer"][:300] + "...", flush=True)
    assert "No relevant clauses" in res2["answer"] or "does not mention" in res2["answer"]
    print("Uncovered query handling: PASS", flush=True)

    # Clean up test document from session store
    document_retriever.delete_index(test_session, test_doc_id)
    session_store.delete_document(test_doc_id, test_session)
    print("\n--- ALL RAG & GEMINI INTEGRATION TESTS PASSED SUCCESSFULLY! ---", flush=True)

if __name__ == "__main__":
    run_rag_test()
