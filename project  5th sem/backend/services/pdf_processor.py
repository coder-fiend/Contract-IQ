import io
import re
from typing import List, Dict, Any, Tuple
import PyPDF2
from fastapi import UploadFile, HTTPException

class PDFProcessingError(Exception):
    pass

class PDFProcessor:
    @staticmethod
    def validate_file(file: UploadFile, max_size_mb: int = 25) -> None:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        ext = file.filename.split(".")[-1].lower()
        if ext != "pdf":
            raise HTTPException(status_code=400, detail=f"Invalid file type: .{ext}. Only PDF documents are supported.")
        
        # Check size if available
        if file.size and file.size > max_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=400, 
                detail=f"File exceeds maximum allowed size of {max_size_mb}MB"
            )

    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        # Normalize whitespace while preserving line breaks between paragraphs
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        return text.strip()

    @classmethod
    def extract_text_with_pages(cls, file_bytes: bytes, filename: str = "document.pdf") -> List[Dict[str, Any]]:
        """
        Extracts text from PDF bytes page by page.
        Returns a list of dicts: [{"page_number": int, "text": str, "char_count": int}]
        """
        if not file_bytes:
            raise PDFProcessingError("Uploaded file is empty (0 bytes).")

        try:
            stream = io.BytesIO(file_bytes)
            reader = PyPDF2.PdfReader(stream)
        except Exception as e:
            raise PDFProcessingError(f"Failed to parse PDF document. The file may be corrupted: {str(e)}")

        num_pages = len(reader.pages)
        if num_pages == 0:
            raise PDFProcessingError("The PDF document contains 0 pages.")

        pages_data = []
        total_text_length = 0

        for page_idx, page in enumerate(reader.pages):
            page_num = page_idx + 1
            try:
                raw_page_text = page.extract_text() or ""
                cleaned_page_text = cls.clean_text(raw_page_text)
                total_text_length += len(cleaned_page_text)
                
                pages_data.append({
                    "page_number": page_num,
                    "text": cleaned_page_text,
                    "char_count": len(cleaned_page_text),
                    "filename": filename
                })
            except Exception as e:
                # Log page extraction error but continue with other pages if possible
                pages_data.append({
                    "page_number": page_num,
                    "text": "",
                    "char_count": 0,
                    "error": str(e),
                    "filename": filename
                })

        if total_text_length == 0:
            raise PDFProcessingError(
                "No extractable text found in this PDF. It might be scanned/image-only or password-protected."
            )

        return pages_data

pdf_processor = PDFProcessor()
