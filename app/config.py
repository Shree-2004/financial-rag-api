import os
from dotenv import load_dotenv

# Load variables from .env if present
load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./financial_dms.db")
    JWT_SECRET_KEY: str = os.getenv("SECRET_KEY", os.getenv("JWT_SECRET_KEY", "9a7c36a8d8e5e8e811c757c9a6bf825e3649ef2c3b889a7491cf3315fb291f03"))
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    
    # Qdrant settings
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "")
    QDRANT_PORT: str = os.getenv("QDRANT_PORT", "6333")
    QDRANT_PATH: str = os.getenv("QDRANT_PATH", "./qdrant_storage")
    
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    RERANKING_MODEL: str = os.getenv("RERANKING_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    STORAGE_DIR: str = "./storage/documents"

    # LLM settings (for RAG generation)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")        # ollama | openai | gemini
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3")              # model name for the provider
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

settings = Settings()
