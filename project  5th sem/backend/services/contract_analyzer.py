import re
import json
import logging
from typing import List, Dict, Any, Optional
from backend.config import settings
from backend.services.legal_explainer import legal_explainer

logger = logging.getLogger(__name__)

# Standard standard-form risk patterns and missing clause checks
STANDARD_PROTECTIVE_CLAUSES = [
    {
        "name": "Dispute Resolution & Governing Law",
        "keywords": ["dispute", "arbitration", "jurisdiction", "governing law", "courts of"],
        "purpose": "Clarifies which court or arbitration mechanism has jurisdiction in case of dispute."
    },
    {
        "name": "Termination & Notice Period",
        "keywords": ["termination", "terminate", "notice period", "prior written notice", "cure period"],
        "purpose": "Provides clear procedure and fair notice period for ending the contract."
    },
    {
        "name": "Limitation of Liability",
        "keywords": ["limitation of liability", "consequential damages", "indirect damages", "maximum aggregate liability"],
        "purpose": "Caps exposure and prevents unlimited financial claims."
    },
    {
        "name": "Force Majeure",
        "keywords": ["force majeure", "act of god", "unforeseen events", "pandemic", "frustration"],
        "purpose": "Excuses performance without penalty during uncontrollable catastrophic events (Section 56 Indian Contract Act)."
    },
    {
        "name": "Confidentiality & Non-Disclosure",
        "keywords": ["confidential information", "non-disclosure", "proprietary data"],
        "purpose": "Protects sensitive trade secrets, business metrics, and personal data."
    }
]

class ContractAnalyzer:
    """
    Automated Legal Contract Clause Risk Analyzer.
    Evaluates agreements for high, medium, and low risks, ambiguous wording,
    one-sided clauses, and missing protective provisions under Indian law.
    """

    @classmethod
    def analyze_contract_heuristics(cls, document_text: str, chunks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fast heuristic static rule assessment based on Indian contract law.
        Runs even without an external LLM API key.
        """
        doc_lower = document_text.lower()
        findings: List[Dict[str, Any]] = []

        # 1. Non-Compete Risk Check (Section 27 Indian Contract Act)
        non_compete_patterns = [
            r"shall\s+not\s+(?:engage|work|enter|compete|join)",
            r"post[\s-]termination\s+non[\s-]compete",
            r"restrain(?:ed)?\s+from\s+(?:practicing|working|carrying\s+on)"
        ]
        for pat in non_compete_patterns:
            match = re.search(pat, doc_lower)
            if match:
                snippet = cls._extract_snippet(document_text, match.start(), match.end())
                findings.append({
                    "clause_name": "Post-Termination Non-Compete Restriction",
                    "risk_level": "High",
                    "snippet": snippet,
                    "reason": "Restrains the employee/party from practicing their profession or trade after agreement ends.",
                    "legal_context": "Section 27 of the Indian Contract Act, 1872 declares agreements in restraint of trade void to that extent. Post-employment non-compete covenants are rarely enforced by Indian courts.",
                    "recommendation": "Request removal of post-employment restrictions or limit solely to non-solicitation of clients and confidentiality."
                })
                break

        # 2. Penalty & Forfeiture of Deposit Check (Section 74 Indian Contract Act)
        penalty_patterns = [
            r"entire\s+(?:security\s+)?deposit\s+shall\s+be\s+forfeited",
            r"forfeit(?:ure)?\s+of\s+(?:all|entire)\s+(?:deposit|amount|funds)",
            r"penalty\s+of\s+inr\s*[\d,]+",
            r"unreasonable\s+liquidated\s+damages"
        ]
        for pat in penalty_patterns:
            match = re.search(pat, doc_lower)
            if match:
                snippet = cls._extract_snippet(document_text, match.start(), match.end())
                findings.append({
                    "clause_name": "Full Deposit Forfeiture / Disproportionate Penalty",
                    "risk_level": "High",
                    "snippet": snippet,
                    "reason": "Allows total retention of deposit or excessive penalty without requiring proof of actual damage.",
                    "legal_context": "Under Section 74 of the Indian Contract Act, courts only award reasonable compensation for actual proven damage; punitive forfeiture clauses can be challenged.",
                    "recommendation": "Replace blanket forfeiture with a clause stating deductions shall be limited to documented actual loss or unpaid dues with written receipts."
                })
                break

        # 3. Unilateral Termination Check (Consumer Protection / Unfair Terms)
        unilateral_patterns = [
            r"(?:terminate|cancel)\s+at\s+any\s+time\s+without\s+(?:notice|reason|cause)",
            r"sole\s+discretion\s+to\s+terminate",
            r"without\s+any\s+liability\s+whatsoever"
        ]
        for pat in unilateral_patterns:
            match = re.search(pat, doc_lower)
            if match:
                snippet = cls._extract_snippet(document_text, match.start(), match.end())
                findings.append({
                    "clause_name": "Unilateral / Summary Termination",
                    "risk_level": "Medium",
                    "snippet": snippet,
                    "reason": "Gives one party sole power to terminate immediately while potentially binding the other party to notice periods.",
                    "legal_context": "Unilateral termination rights create contractual imbalance and may be viewed as an unfair contract term under Section 2(46) of Consumer Protection Act, 2019.",
                    "recommendation": "Introduce mutual termination terms with a minimum 30-day prior written notice and cure period for both sides."
                })
                break

        # 4. Unlimited Indemnity Check
        indemnity_patterns = [
            r"indemnify\s+(?:and\s+hold\s+harmless)?\s+against\s+any\s+and\s+all",
            r"unlimited\s+indemnity",
            r"defend,\s+indemnify\s+and\s+hold\s+harmless"
        ]
        for pat in indemnity_patterns:
            match = re.search(pat, doc_lower)
            if match:
                snippet = cls._extract_snippet(document_text, match.start(), match.end())
                findings.append({
                    "clause_name": "Broad or Unlimited Indemnification",
                    "risk_level": "Medium",
                    "snippet": snippet,
                    "reason": "Exposes the signing party to open-ended legal claims, indirect damages, and third-party liabilities.",
                    "legal_context": "Standard commercial practice requires indemnity to be capped at the total contract value and restricted to direct, proven third-party losses caused by gross negligence or willful misconduct.",
                    "recommendation": "Insert a liability cap (e.g., fees paid in the past 6-12 months) and exclude consequential/indirect damages."
                })
                break

        # 5. Missing Essential Clauses Analysis
        missing_clauses = []
        for clause_def in STANDARD_PROTECTIVE_CLAUSES:
            present = any(kw in doc_lower for kw in clause_def["keywords"])
            if not present:
                missing_clauses.append({
                    "clause_name": clause_def["name"],
                    "importance": "Medium",
                    "purpose": clause_def["purpose"],
                    "recommendation": f"Consider adding an explicit clause covering {clause_def['name']} to prevent future ambiguity."
                })

        # Calculate overall score
        high_count = sum(1 for f in findings if f["risk_level"] == "High")
        med_count = sum(1 for f in findings if f["risk_level"] == "Medium")
        
        if high_count >= 2:
            overall_risk = "High"
            score = 35
        elif high_count == 1 or med_count >= 2:
            overall_risk = "Medium"
            score = 65
        else:
            overall_risk = "Low"
            score = 88

        return {
            "overall_risk": overall_risk,
            "overall_score": score,
            "total_risks_found": len(findings),
            "findings": findings,
            "missing_clauses": missing_clauses,
            "summary": f"Identified {len(findings)} potential clause risks ({high_count} High, {med_count} Medium) and {len(missing_clauses)} omitted standard provisions."
        }

    @classmethod
    def _extract_snippet(cls, text: str, start: int, end: int, window: int = 150) -> str:
        s = max(0, start - window)
        e = min(len(text), end + window)
        snippet = text[s:e].replace("\n", " ").strip()
        return f"... {snippet} ..."

    @classmethod
    def analyze_with_gemini(cls, document_text: str, heuristic_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhances heuristic results with Gemini AI contract analysis if API key is present.
        """
        prompt = f"""You are Contract IQ, an expert Indian contract risk auditor.
Analyze the following legal agreement text and review the preliminary risk findings.

CONTRACT EXCERPT:
{document_text[:4000]}

PRELIMINARY RISK FINDINGS:
{json.dumps(heuristic_result, indent=2)}

TASK:
Provide a refined JSON output with:
1. "overall_risk": "High" | "Medium" | "Low"
2. "overall_score": integer 0-100 (100 = completely safe, 0 = highly dangerous)
3. "executive_summary": 2-3 sentences summarizing the contract's risk posture.
4. "findings": list of evaluated clauses with "clause_name", "risk_level" (High/Medium/Low), "snippet", "reason", "legal_context", "recommendation".
5. "missing_clauses": list of important missing protections.
6. "actionable_advice": 3-4 concrete tips for negotiation.

Return STRICTLY valid JSON with no markdown formatting around it.
"""
        raw = legal_explainer.generate_text(prompt)
        if not raw:
            return heuristic_result

        try:
            # Strip markdown fences if present
            clean_raw = re.sub(r"^```json\s*", "", raw.strip())
            clean_raw = re.sub(r"^```\s*", "", clean_raw)
            clean_raw = re.sub(r"```$", "", clean_raw).strip()
            parsed = json.loads(clean_raw)
            return parsed
        except Exception as e:
            logger.warning(f"Contract analysis JSON parse fallback used: {e}")
            return heuristic_result

contract_analyzer = ContractAnalyzer()
