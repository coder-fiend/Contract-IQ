import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Settings(BaseSettings):
    APP_NAME: str = "Contract IQ"
    APP_VERSION: str = "2.0.0"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "contract-iq-secret-key-change-in-production")
    
    # Active AI Provider: "gemini" (default) or "openai"
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini").lower()

    # Google Gemini Configuration (Official Google Gen AI SDK)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    
    # OpenAI Configuration (Optional / Configurable)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    LLM_TEMPERATURE: float = 0.2
    
    # Embedding Model Configuration
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    
    # Chunking Configuration
    DOCUMENT_CHUNK_SIZE: int = 900
    DOCUMENT_CHUNK_OVERLAP: int = 120
    LEGAL_CHUNK_SIZE: int = 800
    LEGAL_CHUNK_OVERLAP: int = 100
    
    # Base Directories
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    UPLOADS_DIR: Path = BASE_DIR / "uploads"
    VECTORSTORES_DIR: Path = BASE_DIR / "vectorstores"
    DOCUMENTS_VECTOR_DIR: Path = VECTORSTORES_DIR / "documents"
    LEGAL_VECTOR_DIR: Path = VECTORSTORES_DIR / "legal_knowledge"
    LEGAL_DATA_DIR: Path = BASE_DIR / "legal_data"
    DB_PATH: Path = BASE_DIR / "contract_iq.db"
    
    # File Upload Restrictions
    MAX_FILE_SIZE_MB: int = 25
    ALLOWED_EXTENSIONS: set = {"pdf"}

settings = Settings()

# Ensure directories exist
settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
settings.DOCUMENTS_VECTOR_DIR.mkdir(parents=True, exist_ok=True)
settings.LEGAL_VECTOR_DIR.mkdir(parents=True, exist_ok=True)
settings.LEGAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
