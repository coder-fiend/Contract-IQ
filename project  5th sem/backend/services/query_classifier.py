import re
from typing import Dict, Any, Optional

class QueryType:
    DOCUMENT_QUERY = "DOCUMENT_QUERY"
    LEGAL_QUERY = "LEGAL_QUERY"
    REAL_WORLD_QUERY = "REAL_WORLD_QUERY"
    HYBRID_QUERY = "HYBRID_QUERY"

class QueryClassifier:
    """
    Intelligent query classifier that routes user queries to the appropriate RAG retrieval pipeline:
    - DOCUMENT_QUERY: Questions regarding the uploaded agreement / PDF.
    - LEGAL_QUERY: General inquiries about Indian statutes, sections, and legal principles.
    - REAL_WORLD_QUERY: Fact scenarios and dispute situations.
    - HYBRID_QUERY: Evaluating document clauses against Indian statutory law.
    """

    # Indicators that reference the document
    DOCUMENT_PATTERNS = [
        r"\b(?:this|the|my)\s+(?:agreement|contract|document|pdf|clause|section|lease|nda|terms|policy)\b",
        r"\bpage\s+\d+\b",
        r"\bclause\s+\d+\b",
        r"\baccording\s+to\s+(?:the|this)\b",
        r"\bmentioned\s+in\b",
        r"\bwhat\s+does\s+(?:the|this|my)\b",
        r"\bnotice\s+period\b",
        r"\btermination\s+period\b",
        r"\bparties\b",
        r"\brent\s+amount\b",
        r"\bsecurity\s+deposit\s+amount\b"
    ]

    # Indicators that reference Indian statutory law
    LEGAL_PATTERNS = [
        r"\b(?:indian\s+contract\s+act|contract\s+act)\b",
        r"\b(?:bns|bharatiya\s+nyaya\s+sanhita)\b",
        r"\b(?:ipc|indian\s+penal\s+code)\b",
        r"\b(?:consumer\s+protection\s+act|consumer\s+forum|e-daakhil)\b",
        r"\b(?:it\s+act|information\s+technology\s+act)\b",
        r"\bsection\s+\d+\b",
        r"\bunder\s+indian\s+law\b",
        r"\bas\s+per\s+law\b",
        r"\blegally\s+valid\b",
        r"\benforceable\s+in\s+court\b",
        r"\bvoid\s+(?:ab\s+initio|agreement)\b",
        r"\brestraint\s+of\s+trade\b"
    ]

    # Indicators of real-world problem scenarios
    REAL_WORLD_PATTERNS = [
        r"\bmy\s+(?:landlord|tenant|employer|boss|company|seller|builder|buyer|neighbor)\b",
        r"\b(?:refusing|refused|denied)\s+to\s+(?:return|pay|refund|give)\b",
        r"\b(?:fired|terminated|laid\s+off)\s+(?:me|without)\b",
        r"\b(?:threatening|threatened|blackmailing|harassing)\s+me\b",
        r"\bcheated\s+me\b",
        r"\bonline\s+(?:seller|shopping|fraud|scam)\b",
        r"\bdefective\s+(?:product|goods|service)\b",
        r"\bbreached\s+(?:the|our)\s+agreement\b",
        r"\bwhat\s+(?:should|can)\s+i\s+do\b",
        r"\bwhat\s+are\s+my\s+(?:legal\s+)?rights\b",
        r"\bhow\s+to\s+file\s+a\s+complaint\b"
    ]

    @classmethod
    def classify(cls, query: str, has_document: bool = False) -> str:
        query_lower = query.lower().strip()

        has_doc_match = any(re.search(pat, query_lower) for pat in cls.DOCUMENT_PATTERNS)
        has_legal_match = any(re.search(pat, query_lower) for pat in cls.LEGAL_PATTERNS)
        has_real_world_match = any(re.search(pat, query_lower) for pat in cls.REAL_WORLD_PATTERNS)

        # If a document is present
        if has_document:
            # If query mentions both document clauses AND legal validity/statutes: HYBRID
            if (has_doc_match or "clause" in query_lower or "contract" in query_lower) and (has_legal_match or "valid" in query_lower or "legal" in query_lower or "allowed under law" in query_lower):
                return QueryType.HYBRID_QUERY

            # If user mentions document references specifically: DOCUMENT_QUERY
            if has_doc_match:
                return QueryType.DOCUMENT_QUERY

            # If explicit real-world personal situation without referencing document
            if has_real_world_match and not has_doc_match:
                return QueryType.REAL_WORLD_QUERY

            # If general legal query
            if has_legal_match and not has_doc_match:
                return QueryType.LEGAL_QUERY

            # Default to document query when a document is uploaded
            return QueryType.DOCUMENT_QUERY

        # When NO document is uploaded
        else:
            if has_real_world_match:
                return QueryType.REAL_WORLD_QUERY
            if has_legal_match:
                return QueryType.LEGAL_QUERY
            
            # Default to real-world query if situation-like, else legal query
            if any(w in query_lower for w in ["what if", "can i", "is it illegal", "rights", "remedy", "help", "police", "court"]):
                return QueryType.REAL_WORLD_QUERY

            return QueryType.LEGAL_QUERY

query_classifier = QueryClassifier()
