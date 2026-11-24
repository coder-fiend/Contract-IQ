import os
import io
import PyPDF2
from pathlib import Path
from backend.services.pdf_processor import pdf_processor
from backend.services.chunking_service import chunking_service
from backend.services.document_retriever import document_retriever
from backend.database.session_store import session_store

def create_sample_pdf_bytes() -> bytes:
    """Creates a 2-page in-memory PDF for testing."""
    writer = PyPDF2.PdfWriter()
    
    # Page 1
    page1 = PyPDF2.PageObject.create_blank_page(width=612, height=792)
    writer.add_page(page1)
    
    # Page 2
    page2 = PyPDF2.PageObject.create_blank_page(width=612, height=792)
    writer.add_page(page2)
    
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

def run_pipeline_test():
    print("Testing session store...")
    session_id = session_store.ensure_session()
    assert session_id, "Session ID should be created"
    print(f"Created session: {session_id}")

    print("Testing PDF processor with sample text data...")
    # Simulate pages data
    pages_data = [
        {
            "page_number": 1,
            "text": "RENTAL AGREEMENT. Clause 1: The tenancy shall be for 11 months commencing from Jan 1, 2025. "
                    "Clause 2: Security Deposit of INR 50,000 shall be paid by Tenant. Clause 3: Rent is INR 20,000 per month.",
            "char_count": 180,
            "filename": "lease.pdf"
        },
        {
            "page_number": 2,
            "text": "Clause 4: Termination. Either party may terminate this agreement before 11 months by giving 1 month prior written notice. "
                    "If Tenant vacates without notice, 1 month rent will be deducted from security deposit. "
                    "Clause 5: Dispute Resolution shall be under Courts of Delhi.",
            "char_count": 250,
            "filename": "lease.pdf"
        }
    ]

    print("Testing chunking service...")
    doc_id = "test_doc_001"
    chunks = chunking_service.split_document_pages(pages_data, doc_id, "lease.pdf")
    assert len(chunks) >= 2, f"Expected at least 2 chunks, got {len(chunks)}"
    print(f"Generated {len(chunks)} chunks with page preservation:")
    for c in chunks:
        print(f"  Chunk ID: {c.metadata['chunk_id']}, Page: {c.metadata['page_number']}, Clause: {c.metadata.get('detected_clause')}")

    print("Testing FAISS index creation and persistence...")
    index_path = document_retriever.build_and_save_index(session_id, doc_id, chunks)
    assert os.path.exists(index_path), f"Index directory {index_path} must exist"
    print(f"Saved FAISS index at {index_path}")

    print("Testing retrieval with citation...")
    results = document_retriever.retrieve(session_id, doc_id, "What happens if I terminate before 11 months?", k=2)
    assert len(results) > 0, "Should retrieve at least one result"
    top_result = results[0]
    print(f"Top retrieved chunk from Page {top_result['page_number']}:")
    print(f"Content: {top_result['content']}")
    assert top_result['page_number'] == 2, f"Expected page 2 for termination clause, got page {top_result['page_number']}"
    print("Page number preservation verified!")

    print("Testing document isolation...")
    other_session = "unrelated_session_999"
    isolated_results = document_retriever.retrieve(other_session, doc_id, "termination", k=2)
    assert len(isolated_results) == 0, "Other session should not access this index"
    print("Document isolation verified!")

    print("ALL PHASE 2 PIPELINE TESTS PASSED!")

if __name__ == "__main__":
    run_pipeline_test()
