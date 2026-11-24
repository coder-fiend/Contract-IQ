import os
import json
from pathlib import Path
from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from backend.config import settings
from backend.services.embedding_service import embedding_service
from backend.services.chunking_service import chunking_service

def load_all_statutes(acts_dir: Path) -> List[Dict[str, Any]]:
    statutes = []
    for filepath in acts_dir.glob("*.json"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                statutes.append(data)
        except Exception as err:
            print(f"Error loading {filepath}: {err}")
    return statutes

def build_documents_from_statutes(statutes: List[Dict[str, Any]]) -> List[Document]:
    documents = []
    for act in statutes:
        act_name = act.get("act_name", "Unknown Act")
        source_url = act.get("source_url", "")
        status = act.get("status", "Active")
        effective_date = act.get("commencement_date", "")

        for sec in act.get("sections", []):
            sec_num = str(sec.get("section_number", ""))
            sec_title = sec.get("title", "")
            sec_text = sec.get("text", "")
            explanation = sec.get("explanation", "")
            keywords = ", ".join(sec.get("keywords", []))

            combined_content = (
                f"Statute: {act_name}\n"
                f"Section: {sec_num} - {sec_title}\n"
                f"Status: {status}\n"
                f"Provisions: {sec_text}\n"
                f"Practical Interpretation: {explanation}\n"
                f"Keywords: {keywords}"
            )

            metadata = {
                "act_name": act_name,
                "section_number": sec_num,
                "section_title": sec_title,
                "source_url": source_url,
                "effective_date": effective_date,
                "status": status,
                "source_type": "legal_knowledge",
                "chunk_id": f"{act.get('short_code', 'ACT')}_sec_{sec_num}"
            }

            documents.append(Document(page_content=combined_content, metadata=metadata))
    return documents

def run_legal_ingestion():
    print("Beginning legal knowledge ingestion pipeline...")
    acts_dir = settings.LEGAL_DATA_DIR / "acts"
    if not acts_dir.exists():
        print(f"Acts directory not found at {acts_dir}")
        return

    statutes = load_all_statutes(acts_dir)
    print(f"Loaded {len(statutes)} statutes.")

    docs = build_documents_from_statutes(statutes)
    print(f"Constructed {len(docs)} legal provision documents.")

    if not docs:
        print("No documents found to index.")
        return

    print("Embedding legal provisions using local model...")
    embeddings = embedding_service.get_embeddings()
    vector_store = FAISS.from_documents(docs, embeddings)

    dest_dir = settings.LEGAL_VECTOR_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(dest_dir))
    print(f"Successfully saved persistent legal knowledge index at {dest_dir}")

if __name__ == "__main__":
    run_legal_ingestion()
