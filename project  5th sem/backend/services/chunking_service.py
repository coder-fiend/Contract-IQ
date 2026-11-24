import re
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from backend.config import settings

class ChunkingService:
    def __init__(
        self,
        chunk_size: int = settings.DOCUMENT_CHUNK_SIZE,
        chunk_overlap: int = settings.DOCUMENT_CHUNK_OVERLAP
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Split on legal and paragraph boundaries first:
        # 1. Section/Clause headers
        # 2. Numbered paragraphs (e.g., 1. , 2. )
        # 3. Double newline (paragraphs)
        # 4. Single newline
        # 5. Sentence endings
        # 6. Spaces
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=[
                "\n\nClause ",
                "\n\nSection ",
                "\n\nArticle ",
                "\n\nWHEREAS",
                "\n\nNOW THEREFORE",
                "\n\n",
                "\n",
                ". ",
                "; ",
                " "
            ],
            keep_separator=True
        )

    def split_document_pages(
        self, 
        pages_data: List[Dict[str, Any]], 
        document_id: str, 
        filename: str
    ) -> List[Document]:
        """
        Splits extracted pages into chunks while strictly preserving page numbers and metadata.
        """
        all_chunks: List[Document] = []
        global_chunk_idx = 0

        for page in pages_data:
            page_num = page["page_number"]
            page_text = page["text"]

            if not page_text.strip():
                continue

            page_chunks = self.text_splitter.split_text(page_text)

            for idx_in_page, chunk_text in enumerate(page_chunks):
                global_chunk_idx += 1
                chunk_id = f"{document_id}_p{page_num}_c{idx_in_page + 1}"
                
                # Check for possible clause/section indicator in chunk
                clause_match = re.search(r'(?:Clause|Section|Article)\s+([0-9]+(?:\.[0-9]+)*)', chunk_text, re.IGNORECASE)
                detected_clause = clause_match.group(0) if clause_match else None

                metadata = {
                    "document_id": document_id,
                    "filename": filename,
                    "page_number": page_num,
                    "chunk_id": chunk_id,
                    "chunk_index": global_chunk_idx,
                    "char_count": len(chunk_text),
                    "detected_clause": detected_clause,
                    "source_type": "document"
                }

                doc = Document(page_content=chunk_text, metadata=metadata)
                all_chunks.append(doc)

        return all_chunks

    def split_legal_text(
        self, 
        text: str, 
        act_name: str, 
        section_number: str, 
        section_title: str,
        source_url: str = "",
        effective_date: str = "",
        status: str = "Active"
    ) -> List[Document]:
        """
        Splits statutory legal text into chunks, preserving Act name and Section metadata.
        """
        chunks = self.text_splitter.split_text(text)
        legal_docs = []

        for idx, chunk_text in enumerate(chunks):
            # Prepend context header if chunk is split
            header = f"[{act_name} - Section {section_number}: {section_title}]\n"
            content = header + chunk_text if not chunk_text.startswith("[") else chunk_text
            
            metadata = {
                "act_name": act_name,
                "section_number": section_number,
                "section_title": section_title,
                "source_url": source_url,
                "effective_date": effective_date,
                "status": status,
                "chunk_id": f"{act_name}_sec{section_number}_c{idx+1}",
                "source_type": "legal_knowledge"
            }
            legal_docs.append(Document(page_content=content, metadata=metadata))

        return legal_docs

chunking_service = ChunkingService()
