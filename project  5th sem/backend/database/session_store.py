import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from backend.config import settings

class SessionStore:
    def __init__(self, db_path: Path = settings.DB_PATH):
        self.db_path = str(db_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP,
                    last_active TIMESTAMP
                )
            """)
            
            # Documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    filename TEXT,
                    file_path TEXT,
                    page_count INTEGER,
                    vector_path TEXT,
                    created_at TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            """)
            
            # Messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    document_id TEXT,
                    sender TEXT,
                    content TEXT,
                    query_type TEXT,
                    sources TEXT,
                    created_at TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            """)
            
            # Analysis results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contract_analyses (
                    analysis_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    document_id TEXT,
                    result_json TEXT,
                    created_at TIMESTAMP
                )
            """)
            
            conn.commit()

    def ensure_session(self, session_id: Optional[str] = None) -> str:
        if not session_id:
            session_id = str(uuid.uuid4())
            
        now = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO sessions (session_id, created_at, last_active) VALUES (?, ?, ?)",
                (session_id, now, now)
            )
            cursor.execute(
                "UPDATE sessions SET last_active = ? WHERE session_id = ?",
                (now, session_id)
            )
            conn.commit()
        return session_id

    def add_document(self, session_id: str, filename: str, file_path: str, page_count: int, vector_path: str, document_id: Optional[str] = None) -> str:
        if not document_id:
            document_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO documents (document_id, session_id, filename, file_path, page_count, vector_path, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (document_id, session_id, filename, file_path, page_count, vector_path, now)
            )
            conn.commit()
        return document_id

    def get_document(self, document_id: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if session_id:
                cursor.execute("SELECT * FROM documents WHERE document_id = ? AND session_id = ?", (document_id, session_id))
            else:
                cursor.execute("SELECT * FROM documents WHERE document_id = ?", (document_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_session_documents(self, session_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE session_id = ? ORDER BY created_at DESC", (session_id,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_latest_document(self, session_id: str) -> Optional[Dict[str, Any]]:
        docs = self.get_session_documents(session_id)
        return docs[0] if docs else None

    def delete_document(self, document_id: str, session_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE document_id = ? AND session_id = ?", (document_id, session_id))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    def add_message(self, session_id: str, sender: str, content: str, 
                    document_id: Optional[str] = None, query_type: Optional[str] = None, 
                    sources: Optional[List[Dict[str, Any]]] = None) -> str:
        message_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        sources_json = json.dumps(sources) if sources else "[]"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO messages (message_id, session_id, document_id, sender, content, query_type, sources, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (message_id, session_id, document_id, sender, content, query_type or "GENERAL", sources_json, now)
            )
            conn.commit()
        return message_id

    def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
                (session_id, limit)
            )
            rows = cursor.fetchall()
            history = []
            for r in rows:
                item = dict(r)
                try:
                    item["sources"] = json.loads(item["sources"]) if item.get("sources") else []
                except Exception:
                    item["sources"] = []
                history.append(item)
            return history

    def clear_chat_history(self, session_id: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.commit()

    def save_analysis(self, session_id: str, document_id: str, analysis_data: Dict[str, Any]) -> str:
        analysis_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO contract_analyses (analysis_id, session_id, document_id, result_json, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (analysis_id, session_id, document_id, json.dumps(analysis_data), now)
            )
            conn.commit()
        return analysis_id

    def get_analysis(self, document_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM contract_analyses WHERE document_id = ? AND session_id = ? ORDER BY created_at DESC LIMIT 1",
                (document_id, session_id)
            )
            row = cursor.fetchone()
            if row:
                res = dict(row)
                res["result"] = json.loads(res["result_json"])
                return res
            return None

session_store = SessionStore()
