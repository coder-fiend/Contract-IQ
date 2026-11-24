import os
import re
import logging
from typing import List, Dict, Any, Optional
from backend.config import settings
from backend.prompts.document_prompt import DOCUMENT_QA_PROMPT
from backend.prompts.legal_prompts import LEGAL_QA_PROMPT, REAL_WORLD_PROMPT, HYBRID_QA_PROMPT

logger = logging.getLogger(__name__)

class LegalExplainer:
    def __init__(self):
        self._provider = settings.AI_PROVIDER
        self._gemini_client = None
        self._openai_llm = None

    def get_provider_name(self) -> str:
        return settings.AI_PROVIDER

    def _init_gemini_client(self):
        """Initializes the official Google Gen AI SDK client."""
        if self._gemini_client is None:
            api_key = settings.GEMINI_API_KEY
            if not api_key:
                logger.warning("GEMINI_API_KEY is not configured in .env.")
                return None
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=api_key)
                # Mask key in logs for security
                masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
                logger.info(f"Initialized official Google GenAI SDK (Key: {masked_key}, Model: {settings.GEMINI_MODEL})")
            except Exception as e:
                logger.error(f"Failed to initialize Google GenAI SDK: {str(e)}")
                self._gemini_client = None
        return self._gemini_client

    def _init_openai_client(self):
        """Initializes OpenAI client when configured."""
        if self._openai_llm is None:
            api_key = settings.OPENAI_API_KEY
            if not api_key:
                logger.warning("OPENAI_API_KEY is not configured in .env.")
                return None
            try:
                from langchain_openai import ChatOpenAI
                self._openai_llm = ChatOpenAI(
                    model=settings.OPENAI_MODEL,
                    temperature=settings.LLM_TEMPERATURE,
                    api_key=api_key
                )
                logger.info(f"Initialized OpenAI provider with model {settings.OPENAI_MODEL}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {str(e)}")
                self._openai_llm = None
        return self._openai_llm

    def generate_text(self, prompt: str) -> Optional[str]:
        """Unified text generation helper supporting both Gemini (official SDK) and OpenAI."""
        provider = settings.AI_PROVIDER
        if provider == "gemini":
            client = self._init_gemini_client()
            if not client:
                return None
            try:
                res = client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt
                )
                return res.text if hasattr(res, "text") and res.text else str(res)
            except Exception as e:
                logger.error(f"Gemini generate_text error: {e}")
                return None
        elif provider == "openai":
            client = self._init_openai_client()
            if not client:
                return None
            try:
                res = client.invoke(prompt)
                return res.content if hasattr(res, "content") else str(res)
            except Exception as e:
                logger.error(f"OpenAI generate_text error: {e}")
                return None
        return None

    def get_llm(self):
        """Returns the active LLM client based on settings.AI_PROVIDER."""
        provider = settings.AI_PROVIDER
        if provider == "openai":
            return self._init_openai_client()
        else:
            return self._init_gemini_client()

    def format_history_for_prompt(self, history: List[Dict[str, Any]]) -> str:
        if not history:
            return "No previous messages."
        formatted = []
        for msg in history[-6:]:
            sender = "User" if msg.get("sender") == "user" else "Contract IQ"
            content = msg.get("content", "")
            formatted.append(f"{sender}: {content}")
        return "\n".join(formatted)

    def answer_document_query(
        self,
        question: str,
        retrieved_chunks: List[Dict[str, Any]],
        chat_history: List[Dict[str, Any]],
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Answers questions about uploaded documents strictly grounded in retrieved clauses.
        If no relevant clauses are retrieved, explains that clearly rather than hallucinating.
        """
        if not retrieved_chunks:
            return {
                "answer": (
                    "### Direct Answer\n"
                    f"No relevant clauses regarding \"{question}\" were found in the uploaded document.\n\n"
                    "### What Your Document Says\n"
                    "The text extraction and vector search scanned your contract, but found no matching provisions or operative language on this specific topic.\n\n"
                    "### Simple Explanation\n"
                    "Your agreement appears to be silent on this subject, or it may be referred to under a different legal heading or in a separate appendix/schedule.\n\n"
                    "### Suggested Next Steps\n"
                    "- Check if this issue is covered under an addendum, verbal agreement, or custom clause.\n"
                    "- If this right or obligation is critical, consider requesting an amendment or side-letter from the other party."
                ),
                "sources": [],
                "model": f"{settings.AI_PROVIDER}-grounded"
            }

        context_parts = []
        sources = []
        for i, chunk in enumerate(retrieved_chunks):
            page = chunk.get("page_number", 1)
            clause = chunk.get("detected_clause") or f"Clause (Page {page})"
            filename = chunk.get("filename", "Document.pdf")
            content = chunk.get("content", "")
            
            header = f"[Document Excerpt {i+1} | Filename: {filename} | Page: {page} | Reference: {clause}]"
            context_parts.append(f"{header}\n{content}")
            
            sources.append({
                "type": "document",
                "page_number": page,
                "clause": clause,
                "filename": filename,
                "preview": content[:180] + "..." if len(content) > 180 else content
            })

        formatted_context = "\n\n".join(context_parts)
        formatted_history = self.format_history_for_prompt(chat_history)

        prompt_text = DOCUMENT_QA_PROMPT.format(
            context=formatted_context,
            chat_history=formatted_history,
            question=question
        )

        if language.lower() in ("hi", "hindi"):
            prompt_text += "\nNote: Please provide the explanation in Hindi (or English with Hindi translation)."

        return self._generate_response(prompt_text, sources, formatted_context)

    def answer_legal_query(
        self,
        question: str,
        retrieved_legal_chunks: List[Dict[str, Any]],
        chat_history: List[Dict[str, Any]],
        language: str = "en"
    ) -> Dict[str, Any]:
        """Answers general Indian legal inquiries grounded in the statutory knowledge base."""
        if not retrieved_legal_chunks:
            return {
                "answer": (
                    "### Direct Answer\n"
                    f"No specific statutory provisions matching \"{question}\" were found in the current legal knowledge base.\n\n"
                    "### Explanation\n"
                    "Our verified knowledge base currently covers the Indian Contract Act 1872, Bharatiya Nyaya Sanhita 2023, IPC 1860, Consumer Protection Act 2019, and IT Act 2000. Please verify the relevant Act or consult an advocate."
                ),
                "sources": [],
                "model": f"{settings.AI_PROVIDER}-grounded"
            }

        context_parts = []
        sources = []
        for i, chunk in enumerate(retrieved_legal_chunks):
            act = chunk.get("act_name", "Indian Law")
            sec = chunk.get("section_number", "")
            title = chunk.get("section_title", "")
            status = chunk.get("status", "Active")
            url = chunk.get("source_url", "")
            content = chunk.get("content", "")
            
            header = f"[Statutory Authority {i+1} | {act} - Section {sec}: {title} | Status: {status}]"
            context_parts.append(f"{header}\n{content}")
            
            sources.append({
                "type": "legal",
                "act_name": act,
                "section_number": sec,
                "section_title": title,
                "status": status,
                "source_url": url,
                "preview": content[:180]
            })

        formatted_context = "\n\n".join(context_parts)
        formatted_history = self.format_history_for_prompt(chat_history)

        prompt_text = LEGAL_QA_PROMPT.format(
            context=formatted_context,
            chat_history=formatted_history,
            question=question
        )

        if language.lower() in ("hi", "hindi"):
            prompt_text += "\nNote: Please provide the explanation in clear Hindi."

        return self._generate_response(prompt_text, sources, formatted_context)

    def answer_real_world_query(
        self,
        question: str,
        retrieved_legal_chunks: List[Dict[str, Any]],
        chat_history: List[Dict[str, Any]],
        language: str = "en"
    ) -> Dict[str, Any]:
        """Provides structured legal guidance for everyday real-world disputes."""
        context_parts = []
        sources = []
        for i, chunk in enumerate(retrieved_legal_chunks):
            act = chunk.get("act_name", "Indian Law")
            sec = chunk.get("section_number", "")
            title = chunk.get("section_title", "")
            status = chunk.get("status", "Active")
            content = chunk.get("content", "")
            
            header = f"[Statutory Authority {i+1} | {act} - Sec {sec}: {title}]"
            context_parts.append(f"{header}\n{content}")
            
            sources.append({
                "type": "legal",
                "act_name": act,
                "section_number": sec,
                "section_title": title,
                "status": status,
                "source_url": chunk.get("source_url", ""),
                "preview": content[:180]
            })

        formatted_context = "\n\n".join(context_parts) if context_parts else "General Indian legal remedies."
        formatted_history = self.format_history_for_prompt(chat_history)

        prompt_text = REAL_WORLD_PROMPT.format(
            context=formatted_context,
            chat_history=formatted_history,
            question=question
        )

        if language.lower() in ("hi", "hindi"):
            prompt_text += "\nNote: Please provide practical steps and explanations in clear Hindi."

        return self._generate_response(prompt_text, sources, formatted_context)

    def answer_hybrid_query(
        self,
        question: str,
        retrieved_doc_chunks: List[Dict[str, Any]],
        retrieved_legal_chunks: List[Dict[str, Any]],
        chat_history: List[Dict[str, Any]],
        language: str = "en"
    ) -> Dict[str, Any]:
        """Evaluates uploaded contract clauses against governing Indian statutory provisions."""
        doc_parts = []
        sources = []
        for i, chunk in enumerate(retrieved_doc_chunks):
            page = chunk.get("page_number", 1)
            clause = chunk.get("detected_clause") or f"Clause {i+1}"
            doc_parts.append(f"[Document Excerpt {i+1} | Page {page} | Ref: {clause}]\n{chunk.get('content', '')}")
            sources.append({
                "type": "document",
                "page_number": page,
                "clause": clause,
                "filename": chunk.get("filename", "Document.pdf"),
                "preview": chunk.get("content", "")[:180]
            })

        legal_parts = []
        for i, chunk in enumerate(retrieved_legal_chunks):
            act = chunk.get("act_name", "Indian Law")
            sec = chunk.get("section_number", "")
            title = chunk.get("section_title", "")
            legal_parts.append(f"[Statutory Provision {i+1} | {act} - Sec {sec}: {title}]\n{chunk.get('content', '')}")
            sources.append({
                "type": "legal",
                "act_name": act,
                "section_number": sec,
                "section_title": title,
                "status": chunk.get("status", "Active"),
                "source_url": chunk.get("source_url", ""),
                "preview": chunk.get("content", "")[:180]
            })

        formatted_doc_context = "\n\n".join(doc_parts) if doc_parts else "No direct document clause found."
        formatted_legal_context = "\n\n".join(legal_parts) if legal_parts else "General Indian legal provisions."
        formatted_history = self.format_history_for_prompt(chat_history)

        prompt_text = HYBRID_QA_PROMPT.format(
            doc_context=formatted_doc_context,
            legal_context=formatted_legal_context,
            chat_history=formatted_history,
            question=question
        )

        return self._generate_response(prompt_text, sources, f"{formatted_doc_context}\n\n{formatted_legal_context}")

    def _generate_response(self, prompt_text: str, sources: List[Dict[str, Any]], context_snippet: str) -> Dict[str, Any]:
        """Dispatches generation to the active AI provider (Gemini or OpenAI) with graceful error handling."""
        provider = settings.AI_PROVIDER

        # ----------------- 1. GOOGLE GEMINI (Default) -----------------
        if provider == "gemini":
            client = self._init_gemini_client()
            if not client:
                return {
                    "answer": (
                        "### Notice Regarding AI Provider (Gemini)\n"
                        "Gemini API key is not configured in `.env`. Please add `GEMINI_API_KEY` to your `.env` file to enable AI answers.\n\n"
                        "### Retrieved Evidence:\n"
                        f"{context_snippet[:1200]}\n\n"
                        "### Verified Sources:\n" +
                        "\n".join([f"- {s.get('act_name', s.get('filename', 'Source'))} ({s.get('section_number', s.get('clause', ''))})" for s in sources])
                    ),
                    "sources": sources,
                    "model": "offline-fallback"
                }

            try:
                response = client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt_text
                )
                text = response.text if hasattr(response, "text") and response.text else str(response)
                return {
                    "answer": text,
                    "sources": sources,
                    "model": settings.GEMINI_MODEL
                }
            except Exception as e:
                err_msg = str(e)
                logger.error(f"Gemini API Error: {err_msg}")

                if "404" in err_msg or "not found" in err_msg.lower():
                    clean_error = f"Gemini model `{settings.GEMINI_MODEL}` is unavailable. Please check the model name in `.env`."
                elif "429" in err_msg or "quota" in err_msg.lower() or "exhausted" in err_msg.lower():
                    clean_error = "Gemini API rate limit or quota exceeded. Please wait a few moments before trying again."
                elif "503" in err_msg or "unavailable" in err_msg.lower():
                    clean_error = "Gemini servers are currently experiencing temporary high demand (Status 503). Please retry in a few seconds."
                elif "400" in err_msg or "403" in err_msg or "invalid" in err_msg.lower():
                    clean_error = "Invalid Gemini API Key or authentication error. Please check your `GEMINI_API_KEY` in `.env`."
                else:
                    clean_error = f"Gemini API error: {err_msg[:120]}"

                return {
                    "answer": (
                        f"### Notice Regarding AI Service\n"
                        f"{clean_error}\n\n"
                        f"### Retrieved Evidence:\n"
                        f"{context_snippet[:1200]}"
                    ),
                    "sources": sources,
                    "model": "gemini-error-fallback"
                }

        # ----------------- 2. OPENAI (Configurable Alternative) -----------------
        elif provider == "openai":
            openai_llm = self._init_openai_client()
            if not openai_llm:
                return {
                    "answer": (
                        "### Notice Regarding AI Provider (OpenAI)\n"
                        "OpenAI API key is not configured in `.env`. Please add `OPENAI_API_KEY` to your `.env` file to enable OpenAI answers.\n\n"
                        "### Retrieved Evidence:\n"
                        f"{context_snippet[:1200]}"
                    ),
                    "sources": sources,
                    "model": "offline-fallback"
                }

            try:
                res = openai_llm.invoke(prompt_text)
                text = res.content if hasattr(res, "content") else str(res)
                return {
                    "answer": text,
                    "sources": sources,
                    "model": settings.OPENAI_MODEL
                }
            except Exception as e:
                err_msg = str(e)
                logger.error(f"OpenAI API Error: {err_msg}")
                if "429" in err_msg or "quota" in err_msg.lower() or "credits" in err_msg.lower():
                    clean_error = "OpenAI API quota exceeded or rate limit reached (Error 429). Please check your OpenAI account billing."
                elif "401" in err_msg or "invalid_api_key" in err_msg.lower():
                    clean_error = "Invalid OpenAI API Key. Please verify your `OPENAI_API_KEY` in `.env`."
                else:
                    clean_error = f"OpenAI API error: {err_msg[:120]}"

                return {
                    "answer": (
                        f"### Notice Regarding AI Service\n"
                        f"{clean_error}\n\n"
                        f"### Retrieved Evidence:\n"
                        f"{context_snippet[:1200]}"
                    ),
                    "sources": sources,
                    "model": "openai-error-fallback"
                }

        else:
            return {
                "answer": f"Unknown AI provider `{provider}` configured in settings.",
                "sources": sources,
                "model": "unknown-provider"
            }

legal_explainer = LegalExplainer()
